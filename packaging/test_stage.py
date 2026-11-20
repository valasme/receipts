import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from bundle import (
    MANIFEST, NOTICES, RECORD, TARGETS, asset_name, digest, extract_native,
    read_manifest, release_assets, verify_bundle,
)
from prepare import prepare
from stage import GitHub, promote, public, resolve_source, stage
from toolchain import release_binaries

TAG = "v0.2.0-pre.1"
VERSION = TAG[1:]
COMMIT = "a" * 40
WORKFLOW = "b" * 40
COMPILER = "go1.27.4"


def manifest(root):
    (root / MANIFEST).write_text(
        "".join(f"{digest(p)}  {p.name}\n" for p in sorted(root.iterdir()) if p.name != MANIFEST)
    )


def fixture(root):
    root.mkdir()
    for name in release_assets(VERSION) | {"preview-installers.zip"}:
        (root / name).write_text(name)
    (root / RECORD).write_text(json.dumps({
        "source_tag": TAG, "source_commit": COMMIT, "workflow_commit": WORKFLOW,
        "compiler": f"go version {COMPILER} linux/amd64",
    }))
    manifest(root)
    return root


class FakeRelease:
    def __init__(self, root):
        self.local = root
        self.data = {"id": 42, "tag_name": TAG, "draft": True, "prerelease": True}
        self.commit = COMMIT
        self.entries = []
        self.mutations = []
        self.attestations = []
        self.lost_response = False
        self.skip_asset = None

    def resolve_tag(self, tag):
        return self.commit

    def find_release(self, tag):
        return self.data.copy() if self.data else None

    def release(self, release_id):
        if release_id != 42:
            raise ValueError("wrong release identity")
        return self.data.copy()

    def public_release(self, tag):
        return self.data.copy()

    def assets(self, release_id):
        return self.entries.copy()

    def upload(self, release_id, path):
        self.mutations.append(("upload", path.name))
        if path.name != self.skip_asset:
            self.entries.append({
                "id": len(self.entries) + 1, "name": path.name, "state": "uploaded",
                "size": path.stat().st_size, "digest": "sha256:" + digest(path),
            })
        if self.lost_response:
            self.lost_response = False
            raise ValueError("upload response lost")

    def download(self, asset_id, target):
        self.assert_asset(asset_id, target.name)
        shutil.copyfile(self.local / target.name, target)

    def assert_asset(self, asset_id, target):
        assert any(a["id"] == asset_id and a["name"] == target for a in self.entries)

    def attest(self, path, workflow):
        self.attestations.append((path.name, workflow))

    def publish(self, release_id):
        self.mutations.append(("publish", release_id))
        return self.data.copy() | {"draft": False}


class DraftRecovery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = fixture(self.root / "bundle")
        self.github = FakeRelease(self.bundle)

    def stage(self):
        return stage(self.github, TAG, COMMIT, WORKFLOW, self.bundle, self.root / "notes")

    def test_resume_and_recheck(self):
        self.github.lost_response = True
        with self.assertRaisesRegex(ValueError, "response lost"):
            self.stage()
        self.assertEqual(len(self.github.entries), 1)
        self.stage()
        self.stage()
        self.assertEqual(len(self.github.mutations), 13)
        self.github.data["draft"] = False
        self.stage()
        self.assertEqual(len(self.github.mutations), 13)
        self.github.entries.pop()
        with self.assertRaisesRegex(ValueError, "Published"):
            self.stage()
        self.assertEqual(len(self.github.mutations), 13)

    def test_starter_requires_verified_draft_and_no_overwrite(self):
        self.github.entries = [{"name": MANIFEST, "state": "starter", "size": 0, "id": 500}]
        with self.assertRaisesRegex(ValueError, "asset 500.*draft 42"):
            self.stage()
        self.assertFalse(self.github.mutations)
        self.github.entries.clear()
        self.stage()
        self.github.entries[0]["digest"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(ValueError, "differs"):
            self.stage()
        self.assertEqual(len(self.github.mutations), 13)

    def test_invalid_bundle_never_mutates(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(ValueError):
            stage(self.github, TAG, COMMIT, WORKFLOW, empty, self.root / "notes")
        (self.bundle / "unknown").write_text("add")
        manifest(self.bundle)
        with self.assertRaisesRegex(ValueError, "required release target"):
            self.stage()
        (self.bundle / "unknown").unlink()
        manifest(self.bundle)
        (self.bundle / RECORD).write_text("tamper")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            self.stage()
        (self.bundle / RECORD).unlink()
        with self.assertRaises(ValueError):
            self.stage()
        self.assertFalse(self.github.mutations)

    def test_post_upload_observation_and_bound_approval(self):
        self.github.skip_asset = RECORD
        with self.assertRaisesRegex(ValueError, "missing qualified assets"):
            self.stage()
        with self.assertRaisesRegex(ValueError, "complete uploaded"):
            promote(self.github, TAG, COMMIT, 42, digest(self.bundle / MANIFEST))
        self.github.skip_asset = None
        release_id, checksum = self.stage()
        self.github.mutations.clear()
        with self.assertRaisesRegex(ValueError, "wrong release"):
            promote(self.github, TAG, COMMIT, 43, checksum)
        with self.assertRaisesRegex(ValueError, "approved candidate"):
            promote(self.github, TAG, COMMIT, release_id, "f" * 64)
        self.github.commit = WORKFLOW
        with self.assertRaisesRegex(ValueError, "moved"):
            promote(self.github, TAG, COMMIT, release_id, checksum)
        self.assertFalse(self.github.mutations)
        self.github.commit = COMMIT
        promote(self.github, TAG, COMMIT, release_id, checksum)
        self.assertEqual(self.github.mutations, [("publish", 42)])
        self.assertEqual(self.github.attestations, [(MANIFEST, WORKFLOW), (RECORD, WORKFLOW)])

    def test_competing_candidate_cannot_change_the_staged_snapshot(self):
        release_id, checksum = self.stage()
        alternate = fixture(self.root / "alternate")
        (alternate / "preview-installers.zip").write_text("second candidate")
        manifest(alternate)
        with self.assertRaisesRegex(ValueError, "differs from the candidate"):
            stage(self.github, TAG, COMMIT, WORKFLOW, alternate, self.root / "notes")
        self.assertEqual(len(self.github.mutations), 13)
        self.assertEqual(self.stage(), (release_id, checksum))

    def test_public_bundle_checks_pins_and_file_membership(self):
        _, checksum = self.stage()
        self.github.data["draft"] = False
        for tag, commit, manifest_hash, workflow, error in (
            ("v9.0.0-preview", COMMIT, checksum, WORKFLOW, "Expected a prerelease"),
            (TAG, WORKFLOW, checksum, WORKFLOW, "different commit"),
            (TAG, COMMIT, "f" * 64, WORKFLOW, "approved candidate"),
            (TAG, COMMIT, checksum, COMMIT, "Unexpected workflow commit"),
        ):
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    public(self.github, tag, self.root / f"public-{error}",
                           commit=commit, checksum=manifest_hash, workflow=workflow)
        retrieved = public(
            self.github, TAG, self.root / "public", commit=COMMIT,
            checksum=checksum, workflow=WORKFLOW,
        )
        self.assertEqual(retrieved.hashes[MANIFEST], checksum)

    def test_paginated_duplicate_trailing_asset(self):
        github = GitHub("org/repo")
        self.stage()
        with patch.object(github, "find_release", return_value=self.github.data), patch.object(
            github, "resolve_tag", return_value=COMMIT
        ), patch.object(github, "api", return_value=[self.github.entries, [{"name": "unexpected"}]]) as api:
            with self.assertRaisesRegex(ValueError, "Unexpected remote assets"):
                stage(github, TAG, COMMIT, WORKFLOW, self.bundle, self.root / "notes")
            self.assertEqual(api.call_args.args[1:], ("/releases/42/assets?per_page=100", "--paginate", "--slurp"))
            api.return_value = [self.github.entries, self.github.entries[:1]]
            with self.assertRaisesRegex(ValueError, "Duplicate remote asset"):
                stage(github, TAG, COMMIT, WORKFLOW, self.bundle, self.root / "notes")

    def test_timeout_identifies_current_operation(self):
        github = GitHub("org/repo")
        with patch("stage.subprocess.check_output", side_effect=subprocess.TimeoutExpired("gh", 90)) as gh:
            with self.assertRaisesRegex(ValueError, "list assets of release 42"):
                github.assets(42)
            with self.assertRaisesRegex(ValueError, "upload checksums.txt to draft 42"):
                github.upload(42, self.bundle / MANIFEST)
            self.assertEqual(gh.call_args.kwargs["timeout"], 90)

    def test_manifest_grammar(self):
        path = self.bundle / MANIFEST
        valid = path.read_text()
        self.assertEqual(len(read_manifest(path)), 12)
        for entry in (valid + valid, valid + "\n", valid + "f" * 63 + "  nope\n",
                      valid + "f" * 64 + "  ../file\n"):
            path.write_text(entry)
            with self.assertRaises(ValueError):
                read_manifest(path)

    def test_tag_takes_precedence_over_same_name_branch(self):
        def git(*args):
            return subprocess.check_output(["git", "-C", self.root, *args], text=True).strip()

        git("init", "-q")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@invalid", "commit", "-qm", "base", "--allow-empty")
        original = git("rev-parse", "HEAD")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
            "-c", "tag.gpgsign=false", "tag", "-m", "annotated", TAG)
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@invalid", "commit", "-qm", "second", "--allow-empty")
        head = git("rev-parse", "HEAD")
        git("branch", TAG)
        git("update-ref", "refs/remotes/origin/main", head)
        saved = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertEqual(resolve_source(TAG, head), original)
            with self.assertRaisesRegex(ValueError, "moved"):
                resolve_source(TAG, head, tag_push=True)
        finally:
            os.chdir(saved)


def archive(path, exe, *, mode=0o751, extra=None, symlink=False):
    members = [(exe, b"fixture"), ("LICENSE", b"license"), ("README.md", b"README"), (NOTICES, b"notice")]
    if symlink:
        members[0] = (exe, None)
    if extra:
        members.append(extra)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path, "w") as file:
            for name, data in members:
                file.writestr(name, data)
    else:
        with tarfile.open(path, "w:gz") as file:
            for name, data in members:
                info = tarfile.TarInfo(name)
                if data is None:
                    info.type = tarfile.SYMTYPE
                    info.linkname = "README.md"
                    file.addfile(info)
                    continue
                info.size = len(data)
                info.mode = mode if name == exe else 0o644
                file.addfile(info, io.BytesIO(data))


class PrepareBundle(unittest.TestCase):
    def test_prepare_retry_determinism_and_installer_manifest_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / "dist"
            dist.mkdir()
            binaries = {}
            for name in release_assets(VERSION):
                if name.endswith((".zip", ".tar.gz")):
                    archive(dist / name, "receipts.exe" if name.endswith(".zip") else "receipts")
                else:
                    (dist / name).write_text(name)
            for target in TARGETS:
                binaries[target] = root / "-".join(target)
                binaries[target].write_bytes(b"fixture")
            manifest(dist)
            (dist / "metadata.json").write_text(json.dumps({"version": VERSION, "commit": COMMIT}))
            options = dict(tag=TAG, commit=COMMIT, workflow=WORKFLOW, compiler=COMPILER, scanner=root / "scanner")
            missing = dist / asset_name(VERSION, "linux", "amd64", "rpm")
            missing.unlink()
            out = root / "bundle"
            with patch("prepare.subprocess.check_output", return_value=f"go version {COMPILER} linux/amd64"), patch(
                "prepare.release_binaries", return_value=binaries
            ), patch("prepare.scan") as scan:
                with self.assertRaises(FileNotFoundError):
                    prepare(dist, out, **options)
                self.assertFalse(out.exists())
                missing.write_text(missing.name)
                prepare(dist, out, **options)
                prepare(dist, root / "repeat", **options)
                self.assertEqual(scan.call_count, 2)
            bundle = verify_bundle(out, tag=TAG, commit=COMMIT, workflow=WORKFLOW)
            for name in bundle.hashes:
                self.assertEqual((out / name).read_bytes(), (root / "repeat" / name).read_bytes())
            with zipfile.ZipFile(out / "preview-installers.zip") as file:
                formula = file.read("Formula/receipts.rb").decode()
                self.assertIn('(bin/"receipts").to_s.shellescape', formula)
                scoop = file.read("bucket/receipts.json").decode()
                winget = file.read("winget/Valasme.Receipts.Preview.installer.yaml").decode()
                for system, doc in [("darwin", formula), ("windows", scoop), ("windows", winget)]:
                    for arch in ("amd64", "arm64"):
                        name = asset_name(VERSION, system, arch, "zip" if system == "windows" else "tar.gz")
                        self.assertIn(f"/download/{TAG}/{name}", doc)
                        self.assertIn(bundle.hashes[name], doc.lower())

    def test_archive_entries_and_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = fixture(root / "bundle")
            path = bundle / asset_name(VERSION, "linux", "amd64", "tar.gz")
            dest = root / "unpacked"
            for options, error in [
                ({"mode": 0o640}, "execute permission"),
                ({"extra": ("receipts", b"duplicate")}, "duplicate"),
                ({"extra": ("extra", None)}, "Unexpected"),
                ({"symlink": True}, "regular tar member"),
            ]:
                archive(path, "receipts", **options)
                manifest(bundle)
                verified = verify_bundle(bundle, tag=TAG, commit=COMMIT)
                dest.mkdir(exist_ok=True)
                with self.assertRaisesRegex(ValueError, error):
                    extract_native(verified, "linux", "amd64", dest)
                self.assertEqual(list(dest.iterdir()), [])
            archive(path, "receipts")
            manifest(bundle)
            exe = extract_native(verify_bundle(bundle, tag=TAG, commit=COMMIT), "linux", "amd64", dest)
            self.assertEqual(exe.stat().st_mode & 0o777, 0o751)

    def test_scan_requires_exact_targets_and_compiler(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            artifacts = []
            for system, arch in sorted(TARGETS):
                folder = dist / f"receipts_{system}_{arch}"
                folder.mkdir()
                executable = folder / ("receipts.exe" if system == "windows" else "receipts")
                executable.touch()
                artifacts.append({
                    "type": "Binary", "goos": system, "goarch": arch,
                    "path": "dist/" + executable.relative_to(dist).as_posix(),
                })
            metadata = dist / "artifacts.json"
            metadata.write_text(json.dumps(artifacts[1:]))

            def info(file):
                target = tuple(file.parent.name.split("_")[1:])
                return COMPILER, target, "", {"vcs.revision": COMMIT}

            with patch("toolchain.build_info", side_effect=info):
                with self.assertRaisesRegex(ValueError, "Missing binary scan targets"):
                    release_binaries(dist, COMPILER, COMMIT)
                metadata.write_text(json.dumps(artifacts))
                self.assertEqual(len(release_binaries(dist, COMPILER, COMMIT)), 6)
                with self.assertRaisesRegex(ValueError, "observed go1.27.4"):
                    release_binaries(dist, "go1.25.0", COMMIT)
                extra = dist / "receipts_darwin_arm64/other"
                extra.touch()
                artifacts.append({
                    "type": "Binary", "goos": "darwin", "goarch": "arm64",
                    "path": "dist/" + extra.relative_to(dist).as_posix(),
                })
                metadata.write_text(json.dumps(artifacts))
                with self.assertRaisesRegex(ValueError, "Unexpected or duplicate executable"):
                    release_binaries(dist, COMPILER, COMMIT)


if __name__ == "__main__":
    unittest.main()
