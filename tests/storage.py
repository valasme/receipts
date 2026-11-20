"""Additional black-box storage and budget tests; requires working Git."""

import os
import shutil
import subprocess
import tempfile
import zlib
from pathlib import Path

from acceptance import binary, check, env, git
from edge_cases import raw_object


def exercise(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    git(repo, "config", "core.autocrlf", "false")
    path = repo / "log.txt"
    # Similar historical blobs encourage a genuine pack delta chain.
    base = b"".join(f"row {i}: shared text\n".encode() for i in range(800))
    commits = []
    for i in range(12):
        path.write_bytes(base + f"iteration {i}\n".encode())
        git(repo, "add", "log.txt")
        git(repo, "commit", "-qm", str(i))
        commits.append(git(repo, "rev-parse", "HEAD"))
    git(repo, "gc", "--aggressive", "--prune=now")
    idx = next((repo / ".git/objects/pack").glob("*.idx"))
    listing = git(repo, "verify-pack", "-v", str(idx))
    assert any(
        len(line.split()) == 7 and line.split()[1] == "blob"
        for line in listing.splitlines()
    )
    for i, rev in enumerate(commits):
        assert (
            check(repo, rev, "log.txt", f"iteration {i}\n".encode())["verdict"]
            == "verified"
        )
    # Force valid checksum-independent facts using Git's own object tools.
    path.write_bytes(b"A" * (8 * 1024 * 1024) + b"!")
    git(repo, "add", "log.txt")
    git(repo, "commit", "-qm", "too large")
    rev = git(repo, "rev-parse", "HEAD")
    assert check(repo, rev, "log.txt", b"!")["reason"] == "resource_limit"
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    loose = repo / ".git/objects" / tree[:2] / tree[2:]
    loose.chmod(0o600)
    loose.write_bytes(zlib.compress(b"tree 0\x00"))
    assert check(repo, rev, "absent", b"x")["reason"] == "object_unavailable"
    loose.unlink()
    assert check(repo, rev, "absent", b"x")["verdict"] == "cant_check"
    assert check(repo, commits[0], "log.txt", b"a" * 65536)["verdict"] == "contradicted"
    assert (
        check(repo, commits[0], "log.txt", b"\r\n" * 65536)["verdict"] == "contradicted"
    )


def packed_candidates(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    blob = raw_object(repo, "blob", b"sample")
    tree = None
    nested = ""
    for depth in range(10):
        entries = f"100644 blob {blob}\titem\n"
        if depth:
            entries += f"040000 tree {tree}\tsub\n"
            nested += "sub/"
        tree = subprocess.check_output(
            ["git", "-C", repo, "mktree"], input=entries.encode(), env=env
        ).strip().decode()
    rev = git(repo, "commit-tree", tree, "-m", "packed paths")
    git(repo, "update-ref", "refs/heads/packed", rev)
    # Unrelated objects make rereading a valid index during the deep lookup
    # exceed the shared byte budget. Pack and validate them with Git itself.
    stream = b"".join(b"blob\ndata 6\n%06d\n" % i for i in range(120000))
    with tempfile.TemporaryFile() as emitted:
        subprocess.run(
            ["git", "-C", repo, "fast-import", "--quiet"],
            input=stream + b"done\n", stdout=emitted, env=env, check=True,
        )
    packdir = repo / ".git/objects/pack"
    objects = git(repo, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)")
    indexes = list(packdir.glob("*.idx"))
    subprocess.run(
        ["git", "-C", repo, "pack-objects", "--delta-base-offset", packdir / "pack"],
        input=(objects + "\n").encode(), env=env, check=True, stdout=subprocess.DEVNULL,
    )
    for old in indexes:
        old.unlink()
        old.with_suffix(".pack").unlink()
    git(repo, "prune-packed")
    idx = next(packdir.glob("*.idx"))
    assert idx.stat().st_size > 3 << 20
    assert git(repo, "cat-file", "blob", f"{rev}:{nested}item") == "sample"
    assert check(repo, rev, "item", b"sample")["verdict"] == "verified"
    assert check(repo, rev, nested + "item", b"sample")["verdict"] == "verified"

    # A matching but unreadable copy may appear before or after the usable one.
    valid_idx = packdir / "pack-mid.idx"
    idx.rename(valid_idx)
    idx.with_suffix(".pack").rename(valid_idx.with_suffix(".pack"))
    for name in ["pack-aaa.idx", "pack-zzz.idx"]:
        failed = packdir / name
        shutil.copyfile(valid_idx, failed)
        assert check(repo, rev, "item", b"sample")["verdict"] == "verified"
        failed.unlink()

    failed = packdir / "pack-aaa.idx"
    git(repo, "index-pack", "--index-version=1", "-o", str(failed), str(valid_idx.with_suffix(".pack")))
    for i in range(300):
        (packdir / f"auxiliary-{i:04d}").touch()
    assert check(repo, rev, "item", b"sample")["verdict"] == "verified"
    valid_idx.unlink()
    assert check(repo, rev, "item", b"sample")["reason"] == "unsupported_storage"


def special_object(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    # A directory or a pipe is not Git object storage even at an object name.
    rev = "a" * 40
    leaf = repo / ".git/objects" / rev[:2] / rev[2:]
    leaf.parent.mkdir()
    leaf.mkdir()
    assert check(repo, rev, "item", b"x")["reason"] == "unsupported_storage"
    leaf.rmdir()
    if hasattr(os, "mkfifo"):
        os.mkfifo(leaf)
        result = subprocess.run(
            [binary, "check", "--repo", repo, "--rev", rev, "--path", "item",
             "--quote-file", "-"],
            input=b"x", capture_output=True, timeout=2,
        )
        assert result.returncode == 0 and b"unsupported_storage" in result.stdout


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        exercise(Path(d))
    with tempfile.TemporaryDirectory() as d:
        packed_candidates(Path(d))
    with tempfile.TemporaryDirectory() as d:
        special_object(Path(d))
    print("Deltas, pack candidates, damaged and absent objects, file types, and byte limits passed")
