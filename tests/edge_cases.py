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
    nested = repo / "nested" / "deep"
    nested.mkdir(parents=True)
    r = subprocess.run(args, cwd=nested, input=b"aa", capture_output=True)
    assert r.returncode == 0 and r.stdout.startswith(b"Verified"), r
    r = subprocess.run(args + ["--repo", "."], cwd=nested, input=b"aa", capture_output=True)
    assert r.returncode == 0 and b"repository_unavailable" in r.stdout, r
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


def storage_selection(root):
    repo = root / "clone"
    repo.mkdir()
    git(repo, "init", "-q", "--object-format=sha1")
    (repo / "item").write_bytes(b"original")
    git(repo, "add", "item")
    git(repo, "commit", "-qm", "initial")
    rev = git(repo, "rev-parse", "HEAD")
    baseline = check(repo, rev, "item", b"original")
    bare = root / "bare.git"
    git(root, "clone", "-q", "--bare", "--no-local", str(repo), str(bare))
    git(bare, "repack", "-Adq")
    git(bare, "prune-packed")
    assert list((bare / "objects" / "pack").glob("*.idx"))
    assert check(bare, rev, "item", b"original") == baseline

    (repo / "item").write_bytes(b"replacement")
    git(repo, "commit", "-qam", "replacement")
    replacement = git(repo, "rev-parse", "HEAD")
    git(repo, "replace", rev, replacement)
    assert git(repo, "cat-file", "blob", f"{rev}:item") == "replacement"
    assert git(repo, "--no-replace-objects", "cat-file", "blob", f"{rev}:item") == "original"
    assert check(repo, rev, "item", b"original") == baseline

    linked = root / "linked"
    git(repo, "worktree", "add", "-q", "--detach", str(linked), replacement)
    separate = root / "separate"
    git(root, "init", "-q", "--separate-git-dir", str(root / "gitdir"), str(separate))
    for path in [linked, separate]:
        r = check(path, rev, "item", b"original")
        assert r["reason"] == "unsupported_storage" and "clone or bare" in r["detail"], r

    assert check(root, rev, "item", b"x")["reason"] == "repository_unavailable"
    assert check(root / "missing", rev, "item", b"x")["reason"] == "repository_unavailable"
    (repo / ".git" / "objects").rename(repo / ".git" / "objects-old")
    r = check(repo, rev, "item", b"x")
    assert r["reason"] == "repository_unavailable" and "object directory" in r["detail"], r
    (repo / ".git" / "objects").mkdir()
    alt = repo / ".git" / "objects" / "info"
    alt.mkdir()
    (alt / "alternates").write_text(str(bare / "objects") + "\n", encoding="utf-8")
    r = check(repo, rev, "item", b"x")
    assert r["reason"] == "unsupported_storage" and "alternate" in r["detail"], r

    sha256 = root / "sha256"
    git(root, "init", "-q", "--object-format=sha256", str(sha256))
    r = check(sha256, rev, "item", b"x")
    assert r["reason"] == "unsupported_storage" and "SHA-256" in r["detail"], r
    for malformed, diagnostic in [("g" * 64, b"hexadecimal"), ("0" * 64, b"SHA-256")]:
        r = subprocess.run(
            [binary, "check", "--repo", sha256, "--rev", malformed, "--path", "item",
             "--quote-file", "-"],
            input=b"x", capture_output=True,
        )
        assert r.returncode == 2 and not r.stdout and diagnostic in r.stderr, r


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="receipts ü ") as directory:
        suite(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        storage_selection(Path(directory))
    print("Edge, repository discovery, object formats, privacy and tree limits passed.")
