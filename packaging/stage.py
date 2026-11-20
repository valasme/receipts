"""Resolve release identity, authenticate release assets, and reconcile drafts."""

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from bundle import COMMIT, MANIFEST, RECORD, SHA256, digest, release_assets, validate_tag, verify_bundle

REPO = "valasme/receipts"
COMMAND_TIMEOUT = 90


class GitHub:
    def __init__(self, repo):
        self.repo = repo
        self.endpoint = f"repos/{repo}"

    def gh(self, operation, *args, stdout=None):
        try:
            if stdout is not None:
                subprocess.run(["gh", *args], stdout=stdout, check=True, timeout=COMMAND_TIMEOUT)
                return None
            return subprocess.check_output(["gh", *args], text=True, timeout=COMMAND_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise ValueError(f"Timed out during {operation} after {COMMAND_TIMEOUT}s") from None
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"Failed to {operation} (gh exited {exc.returncode})") from None

    def api(self, operation, endpoint, *options):
        return json.loads(self.gh(operation, "api", self.endpoint + endpoint, *options))

    def paginated(self, operation, endpoint):
        pages = self.api(operation, endpoint + "?per_page=100", "--paginate", "--slurp")
        if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
            raise ValueError(f"Unexpected paginated response while attempting to {operation}")
        return [item for page in pages for item in page]

    def resolve_tag(self, tag):
        validate_tag(tag)
        obj = self.api(f"resolve refs/tags/{tag}", f"/git/ref/tags/{tag}")["object"]
        for _ in range(8):
            sha = obj["sha"]
            if not re.fullmatch(COMMIT, sha):
                break
            if obj["type"] == "commit":
                return sha
            if obj["type"] != "tag":
                break
            obj = self.api(f"peel annotated tag {tag}", f"/git/tags/{sha}")["object"]
        raise ValueError(f"Expected a commit at refs/tags/{tag}")

    def find_release(self, tag):
        releases = [
            r for r in self.paginated("list releases", "/releases")
            if r["tag_name"] == tag
        ]
        if len(releases) > 1:
            raise ValueError(f"Multiple releases found for {tag}")
        return releases[0] if releases else None

    def release(self, release_id):
        return self.api(f"read release {release_id}", f"/releases/{release_id}")

    def public_release(self, tag):
        return self.api(f"read public release {tag}", f"/releases/tags/{tag}")

    def assets(self, release_id):
        return self.paginated(f"list assets of release {release_id}", f"/releases/{release_id}/assets")

    def create(self, tag, commit, notes):
        self.gh(
            f"create draft {tag}", "release", "create", tag, "--repo", self.repo,
            "--verify-tag", "--target", commit, "--draft", "--prerelease",
            "--latest=false", "--title", f"Receipts {tag} · unsigned limited preview",
            "--notes-file", str(notes),
        )

    def upload(self, release_id, path):
        self.gh(
            f"upload {path.name} to draft {release_id}", "api", "--method", "POST",
            f"https://uploads.github.com/{self.endpoint}/releases/{release_id}/assets?name={path.name}",
            "-H", "Content-Type: application/octet-stream", "--input", str(path),
        )

    def download(self, asset_id, target):
        with target.open("xb") as file:
            self.gh(
                f"download {target.name}", "api", f"{self.endpoint}/releases/assets/{asset_id}",
                "-H", "Accept: application/octet-stream", stdout=file,
            )

    def attest(self, path, workflow):
        self.gh(
            f"verify provenance for {path.name}", "attestation", "verify", str(path),
            "--repo", self.repo, "--signer-workflow", f"{self.repo}/.github/workflows/release.yml",
            "--source-digest", workflow, "--deny-self-hosted-runners",
        )

    def publish(self, release_id):
        return self.api(
            f"publish draft {release_id}", f"/releases/{release_id}", "--method", "PATCH",
            "-F", "draft=false", "-F", "prerelease=true", "-f", "make_latest=false",
        )


def require_release(release, tag):
    if not release or release["tag_name"] != tag or not release["prerelease"]:
        raise ValueError(f"Expected a prerelease for {tag}")


def require_commit(github, tag, commit):
    if github.resolve_tag(tag) != commit:
        raise ValueError(f"refs/tags/{tag} moved from the expected commit {commit}")


def remote_assets(github, release):
    assets = {}
    for asset in github.assets(release["id"]):
        name = asset["name"]
        if name in assets:
            raise ValueError(f"Duplicate remote asset: {name}")
        assets[name] = asset
    return assets


def missing_assets(assets, hashes, release):
    unexpected = assets.keys() - hashes.keys()
    if unexpected:
        raise ValueError(f"Unexpected remote assets: {sorted(unexpected)}")
    for name, asset in assets.items():
        if release["draft"] and asset["state"] == "starter" and asset["size"] == 0:
            raise ValueError(
                f"Interrupted upload: zero-byte starter asset {name!r} (asset {asset['id']}) "
                f"in draft {release['id']} ({release['tag_name']}). "
                "Verify the draft and remove only that starter before retrying the same candidate."
            )
        if asset["state"] != "uploaded" or asset["digest"] != "sha256:" + hashes[name]:
            raise ValueError(f"Remote asset differs from the candidate: {name}")
    return sorted(hashes.keys() - assets.keys())


def stage(github, tag, commit, workflow, root, notes):
    bundle = verify_bundle(root, tag=validate_tag(tag), commit=commit, workflow=workflow)
    require_commit(github, tag, commit)
    release = github.find_release(tag)
    if release is None:
        github.create(tag, commit, notes)
        # Creation may be acknowledged before the draft appears in the listing.
        for delay in (0, 1, 2, 4, 8):
            time.sleep(delay)
            release = github.find_release(tag)
            if release is not None:
                break
    require_release(release, tag)
    release_id = release["id"]
    missing = missing_assets(remote_assets(github, release), bundle.hashes, release)
    if not release["draft"] and missing:
        raise ValueError("Published release differs from the qualified bundle")
    for name in missing:
        github.upload(release_id, root / name)
    observed = github.release(release_id)
    require_release(observed, tag)
    if observed["draft"] != release["draft"]:
        raise ValueError("Release changed publication state during staging")
    if missing_assets(remote_assets(github, observed), bundle.hashes, observed):
        raise ValueError("Remote release is missing qualified assets after staging")
    require_commit(github, tag, commit)
    return release_id, bundle.hashes[MANIFEST]


def fetch_verified(github, release, root, *, tag, commit, checksum=None, workflow=None):
    require_release(release, tag)
    assets = remote_assets(github, release)
    expected = release_assets(tag.removeprefix("v")) | {MANIFEST, RECORD, "preview-installers.zip"}
    if assets.keys() != expected or any(a["state"] != "uploaded" for a in assets.values()):
        raise ValueError("Remote release does not have the complete uploaded asset set")
    root.mkdir()
    for name in (MANIFEST, RECORD):
        github.download(assets[name]["id"], root / name)
    if checksum is not None and digest(root / MANIFEST) != checksum:
        raise ValueError("Checksum manifest differs from the approved candidate")
    record = json.loads((root / RECORD).read_bytes())
    observed_workflow = record["workflow_commit"]
    if not re.fullmatch(COMMIT, observed_workflow) or (workflow and observed_workflow != workflow):
        raise ValueError("Unexpected workflow commit in the build record")
    for name in (MANIFEST, RECORD):
        github.attest(root / name, observed_workflow)
    for name in sorted(expected - {MANIFEST, RECORD}):
        github.download(assets[name]["id"], root / name)
    return verify_bundle(root, tag=tag, commit=commit, workflow=observed_workflow)


def public(github, tag, root, *, commit=None, checksum=None, workflow=None):
    validate_tag(tag)
    current = github.resolve_tag(tag)
    if commit is not None and current != commit:
        raise ValueError("Published tag points to a different commit")
    release = github.public_release(tag)
    if release["draft"]:
        raise ValueError("Expected a published release")
    return fetch_verified(
        github, release, root, tag=tag, commit=current, checksum=checksum, workflow=workflow,
    )


def promote(github, tag, commit, release_id, checksum):
    validate_tag(tag)
    if release_id <= 0 or not re.fullmatch(SHA256, checksum):
        raise ValueError("Promotion requires the approved numeric release ID and SHA-256")
    require_commit(github, tag, commit)
    release = github.release(release_id)
    with tempfile.TemporaryDirectory() as temp:
        bundle = fetch_verified(
            github, release, Path(temp) / "bundle", tag=tag, commit=commit, checksum=checksum,
        )
        observed = github.release(release_id)
        require_release(observed, tag)
        if missing_assets(remote_assets(github, observed), bundle.hashes, observed):
            raise ValueError("Remote release changed before promotion")
        require_commit(github, tag, commit)
        if observed["draft"]:
            published = github.publish(release_id)
            require_release(published, tag)
            if published["draft"] or published["id"] != release_id:
                raise ValueError("GitHub did not confirm publication of the selected draft")


def resolve_source(tag, event_commit, *, tag_push=False):
    def git(*args):
        return subprocess.check_output(["git", *args], text=True, timeout=30).strip()

    if not re.fullmatch(COMMIT, event_commit):
        raise ValueError("Expected a pinned event commit")
    if not tag:
        return git("rev-parse", "--verify", event_commit + "^{commit}")
    commit = git("rev-parse", "--verify", f"refs/tags/{validate_tag(tag)}^{{commit}}")
    if tag_push and commit != git("rev-parse", "--verify", event_commit + "^{commit}"):
        raise ValueError("Pushed tag moved before release validation")
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "refs/remotes/origin/main"],
                   check=True, timeout=30)
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for name in ("resolve", "stage", "promote", "public"):
        command = commands.add_parser(name)
        command.add_argument("tag")
        command.add_argument("--commit", required=name != "public")
        if name in ("stage", "public"):
            command.add_argument("bundle", type=Path)
            command.add_argument("--workflow", required=name == "stage")
        if name == "stage":
            command.add_argument("--notes", required=True, type=Path)
        if name in ("promote", "public"):
            command.add_argument("--checksum", required=name == "promote")
        if name == "promote":
            command.add_argument("--release-id", required=True, type=int)
        if name == "resolve":
            command.add_argument("--tag-push", action="store_true")
    args = parser.parse_args()
    github = GitHub(os.environ.get("GITHUB_REPOSITORY", REPO))
    if args.mode == "resolve":
        print(resolve_source(args.tag, args.commit, tag_push=args.tag_push))
    elif args.mode == "stage":
        release_id, checksum = stage(github, args.tag, args.commit, args.workflow, args.bundle, args.notes)
        if "GITHUB_STEP_SUMMARY" in os.environ:
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                print(f"Reviewed release inputs for `{args.tag}`: draft `{release_id}`, "
                      f"checksums.txt SHA-256 `{checksum}`.", file=summary)
        print(f"Release {release_id}, checksums.txt SHA-256 {checksum}")
    elif args.mode == "promote":
        promote(github, args.tag, args.commit, args.release_id, args.checksum)
    else:
        bundle = public(github, args.tag, args.bundle, commit=args.commit,
                        checksum=args.checksum, workflow=args.workflow)
        print(f"{args.tag} source {bundle.record['source_commit']}, compiler {bundle.record['compiler']}, "
              f"verified {len(bundle.hashes) - 1} asset hashes.", flush=True)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                print("commit=" + bundle.record["source_commit"], file=output)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None
