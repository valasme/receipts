"""Boundary inputs and independent Git witnesses against the installed CLI."""

import os
import subprocess
import tempfile
from pathlib import Path

from acceptance import binary, check
from git_fixture import git, git_bytes


def suite(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    git(repo, "config", "core.autocrlf", "false")
    name = ".space café"
    (repo / name).write_bytes(b"aaa\n\t  x...\rfin\n")
    (repo / "empty").touch()
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "edge cases")
    rev = git(repo, "rev-parse", "HEAD")
    original = git(repo, "rev-parse", rev + ":" + name)
    git(repo, "tag", "-am", "annotation", "sample")
    for invalid_rev in ["sample", git(repo, "rev-parse", "sample^{tag}")]:
        result = subprocess.run(
            [binary, "check", "--repo", repo, "--rev", invalid_rev,
             "--path", name, "--quote-file", "-"],
            check=False, input=b"a",
            capture_output=True,
            timeout=20,
        )
        assert result.returncode == 2 and not result.stdout
        assert b"git rev-parse --verify 'TAG^{commit}'" in result.stderr
    recovered = git(repo, "rev-parse", "--verify", "sample^{commit}")
    assert recovered == rev
    assert check(repo, recovered, name, b"a")["verdict"] == "verified"
    check(repo, git(repo, "rev-parse", "HEAD^{tree}"), name, b"a", expected=2)
    git(repo, "checkout", "-q", "--detach", rev)
    (repo / name).write_bytes(b"staged")
    git(repo, "add", name)
    for needle, verdict in [
        (b"aa", "verified"),
        (b"\n", "verified"),
        (b".*", "contradicted"),
        ("…".encode(), "contradicted"),
        (b"  x...\rf", "verified"),
    ]:
        receipt = check(repo, rev.upper(), name, needle)
        assert receipt["claim"]["requested_commit"] == rev
        assert (
            receipt["verdict"] == verdict and receipt["evidence"]["blob_id"] == original
        )
    assert (
        check(repo, rev, name.replace("é", "e\u0301"), b"a")["reason"] == "path_absent"
    )
    assert check(repo, rev, "empty", b"a")["reason"] == "quote_absent"
    assert check(repo, rev, name + "/leaf", b"a")["reason"] == "unsupported_kind"
    for path in ["a/", "./a", "a\x1bb", "a" * 4097, "/".join(["a"] * 129)]:
        check(repo, rev, path, b"x", expected=2)
    for path in ["a" * 4096, "/".join(["a"] * 128)]:
        assert check(repo, rev, path, b"x")["reason"] == "path_absent"

    with tempfile.TemporaryDirectory() as directory:
        quote = Path(directory) / "private-excerpt"
        quote.write_bytes(b"aaa\n")
        args = [binary, "check", "--rev", rev, "--path", name, "--quote-file", quote]
        r = subprocess.run(args, check=False, cwd=repo, capture_output=True, timeout=20)
        assert r.returncode == 0 and r.stdout.startswith(b"Verified")
        for private in [
            str(repo).encode(),
            str(quote).encode(),
            b"aaa\n",
            b"test@example.invalid",
        ]:
            assert private not in r.stdout + r.stderr
        quote.unlink()
        r = subprocess.run(args, check=False, cwd=repo, capture_output=True, timeout=20)
        assert (
            r.returncode == 2 and not r.stdout and str(quote).encode() not in r.stderr
        )
    args = [binary, "check", "--rev", rev, "--path", name, "--quote-file", "-"]
    if Path("/dev/full").exists():
        with open("/dev/full", "wb") as full:
            r = subprocess.run(
                args,
                check=False,
                cwd=repo,
                input=b"aa",
                stdout=full,
                stderr=subprocess.PIPE,
                timeout=20,
            )
            assert r.returncode == 1 and r.stderr
        print("Output failure (/dev/full): passed.")
    else:
        print("Output failure (/dev/full): skipped, device unavailable.")

    if os.name == "posix" and os.geteuid() != 0:
        blob = repo / ".git/objects" / original[:2] / original[2:]
        blob.chmod(0)
        try:
            assert check(repo, rev, name, b"a")["verdict"] == "cant_check"
        finally:
            blob.chmod(0o444)
        print("Denied object read: 1/1 passed.")
    else:
        print("Denied object read: 0/1 eligible, requires an unprivileged POSIX user.")
    lines = b"".join(
        f"100644 blob {original}\tentry{i:05d}\n".encode() for i in range(32769)
    )
    tree = git_bytes(repo, "mktree", data=lines).strip().decode()
    broad = git(repo, "commit-tree", tree, "-m", "wide")
    assert check(repo, broad, "absent", b"x")["reason"] == "resource_limit"


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="receipts ü ") as directory:
        suite(Path(directory))
    print("Edge, privacy and tree limit checks passed.")
