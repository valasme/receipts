"""Resume a partial draft, preserving any existing release assets."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def reconcile(bundle, existing, published, upload):
    local = {p.name: p for p in bundle.iterdir() if p.is_file()}
    if set(existing) - set(local):
        raise ValueError(
            "Unexpected remote assets; inspect the draft before continuing."
        )
    for name, entry in existing.items():
        digest = hashlib.sha256(local[name].read_bytes()).hexdigest()
        if (
            entry.get("digest") != "sha256:" + digest
            or entry.get("state") != "uploaded"
        ):
            raise ValueError("An existing asset differs from the candidate: " + name)
    missing = sorted(set(local) - set(existing))
    if published and missing:
        raise ValueError("Published release differs from the qualified bundle.")
    for name in missing:
        upload(local[name])


def stage(tag, bundle, notes):
    repo = os.environ["GITHUB_REPOSITORY"]

    def gh(*args):
        return subprocess.check_output(["gh", *args], text=True)

    def find_release():
        pages = json.loads(
            gh("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100")
        )
        return next((r for page in pages for r in page if r["tag_name"] == tag), None)

    release = find_release()
    if release is None:
        gh(
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--verify-tag",
            "--draft",
            "--prerelease",
            "--latest=false",
            "--title",
            f"Receipts {tag} · unsigned limited preview",
            "--notes-file",
            str(notes),
        )
        release = find_release()
    if not release or not release["prerelease"]:
        raise ValueError("Expected a prerelease for the selected tag.")
    assets = {a["name"]: a for a in release["assets"]}
    reconcile(
        bundle,
        assets,
        not release["draft"],
        lambda p: gh("release", "upload", tag, str(p), "--repo", repo),
    )


if __name__ == "__main__":
    stage(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]))
