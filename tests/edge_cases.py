"""Boundary inputs and independent Git witnesses against the installed CLI."""

import os
import subprocess
import tempfile
from pathlib import Path

from acceptance import binary, check, env, git


def raw_object(repo, kind, body):
    return subprocess.check_output(
        ["git", "-C", repo, "hash-object", "--literally", "-w", "-t", kind, "--stdin"],
        input=body,
        env=env,
    ).strip().decode()


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
            input=b"a",
            capture_output=True,
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

    commit = git(repo, "cat-file", "commit", rev)
    tree_header, _, rest = commit.partition("\n")
    identity = "Fixture <test@example.invalid> 1735689600 +0000"
    required = f"author {identity}\ncommitter {identity}\n"
    for body in [
        tree_header + "\n",
        tree_header + "\nauthor missing-email\n" + rest,
        tree_header.upper().replace("TREE ", "tree ") + "\n" + rest,
        tree_header + "\nparent invalid\n" + required + "\n",
        tree_header + "\n" + required + "tree " + tree_header[5:] + "\n\n",
    ]:
        bad = raw_object(repo, "commit", body.encode())
        receipt = check(repo, bad, name, b"aaa")
        assert (receipt["verdict"], receipt["reason"]) == (
            "cant_check",
            "object_unavailable",
        ), receipt
    # The parent is outside this shallow history. Continuation lines are part of
    # an optional header and cannot be mistaken for required commit headers.
    shallow = raw_object(
        repo,
        "commit",
        (
            tree_header + "\nparent " + "c" * 40 + "\n" + required
            + "encoding UTF-8\ngpgsig example\n continuation\n\nmessage\n"
        ).encode(),
    )
    (repo / ".git" / "shallow").write_text(shallow + "\n", encoding="ascii")
    assert check(repo, shallow, name, b"aaa")["verdict"] == "verified"

    with tempfile.TemporaryDirectory() as directory:
        quote = Path(directory) / "private-excerpt"
        quote.write_bytes(b"aaa\n")
        args = [binary, "check", "--rev", rev, "--path", name, "--quote-file", quote]
        r = subprocess.run(args, check=False, cwd=repo, capture_output=True)
        assert r.returncode == 0 and r.stdout.startswith(b"Verified")
        for private in [
            str(repo).encode(),
            str(quote).encode(),
            b"aaa\n",
            b"test@example.invalid",
        ]:
            assert private not in r.stdout + r.stderr
        quote.unlink()
        r = subprocess.run(args, check=False, cwd=repo, capture_output=True)
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
            )
            assert r.returncode == 1 and r.stderr
        blob = repo / ".git/objects" / original[:2] / original[2:]
        blob.chmod(0)
        try:
            if os.geteuid() != 0:
                assert check(repo, rev, name, b"a")["verdict"] == "cant_check"
        finally:
            blob.chmod(0o444)
    lines = b"".join(
        f"100644 blob {original}\tentry{i:05d}\n".encode() for i in range(32769)
    )
    tree = (
        subprocess.check_output(["git", "-C", repo, "mktree"], input=lines, env=env)
        .strip()
        .decode()
    )
    broad = git(repo, "commit-tree", tree, "-m", "wide")
    assert check(repo, broad, "absent", b"x")["reason"] == "resource_limit"


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="receipts ü ") as directory:
        suite(Path(directory))
    print("Edge, permission, privacy and tree limit checks passed.")
