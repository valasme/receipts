"""Boundary inputs and independent Git witnesses against the installed CLI."""

import json
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
    # Each individual lookup fits. The fifth lookup shares the same
    # command-wide tree budget as the earlier four.
    boundary = subprocess.check_output(
        ["git", "-C", repo, "mktree"], input=lines.rsplit(b"\n", 2)[0] + b"\n",
        env=env,
    ).strip().decode()
    rev = git(repo, "commit-tree", boundary, "-m", "batch tree budget")
    batch = {
        "schema_major": 1, "rev": rev,
        "claims": [{"path": f"missing{i}", "quote": "x"} for i in range(5)],
    }
    output = subprocess.check_output(
        [binary, "check", "--repo", repo, "--batch-file", "-"],
        input=json.dumps(batch).encode(),
    )
    receipts = [item["receipt"] for item in json.loads(output)["results"]]
    assert [r["reason"] for r in receipts] == ["path_absent"] * 4 + ["resource_limit"]
    assert "cumulative tree entries" in receipts[-1]["detail"]


def quote_witnesses(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    contents = "\ufeffcafé\nsecond\n".encode()
    text = raw_object(repo, "blob", contents)
    prose = raw_object(repo, "blob", b"version https://git-lfs.github.com/spec/v1 is a marker\n")
    prefix = b"version https://git-lfs.github.com/spec/v1"
    oid = b"sha256:" + b"e" * 64
    pointer = raw_object(repo, "blob", b"\r\n".join([
        prefix, b"ext-0-sample " + oid, b"oid " + oid, b"size 3", b""
    ]))
    marker = raw_object(repo, "blob", prefix + b"\nordinary text\n")
    empty_tree = raw_object(repo, "tree", b"")
    missing = "d" * 40
    submodule = git(repo, "commit-tree", empty_tree, "-m", "module")
    empty_dir = f"040000 tree {empty_tree}\trepeat\n"
    repeated_tree = subprocess.check_output(
        ["git", "-C", repo, "mktree"], input=empty_dir.encode(), env=env
    ).strip().decode()
    entries = [
        f"100644 blob {text}\t1:note",
        f"100644 blob {text}\t spaced ",
        f"100644 blob {prose}\tprose",
        f"100644 blob {marker}\tmarker",
        f"100644 blob {pointer}\tpointer",
        f"120000 blob {text}\tlink",
        f"100644 blob {missing}\tmissing",
        f"040000 tree {repeated_tree}\trepeat",
        f"040000 tree {missing}\tunavailable-dir",
        f"160000 commit {submodule}\tmodule",
    ]
    tree = subprocess.check_output(
        ["git", "-C", repo, "mktree", "--missing"],
        input=("\n".join(entries) + "\n").encode(), env=env,
    ).strip().decode()
    rev = git(repo, "commit-tree", tree, "-m", "quote witnesses")
    original = subprocess.check_output(
        ["git", "-C", repo, "cat-file", "blob", rev + ":1:note"], env=env
    )
    assert original == contents
    assert check(repo, rev, "1:note", "\ufeffcafé".encode())["verdict"] == "verified"
    assert check(repo, rev, "1:note", "cafe\u0301".encode())["verdict"] == "contradicted"
    assert check(repo, rev, "1:note", "\ufeffsecond".encode())["verdict"] == "contradicted"
    check(repo, rev, "a:note", b"x", expected=2)
    assert check(repo, rev, "prose", b"marker")["verdict"] == "verified"
    assert check(repo, rev, "marker", b"ordinary text")["verdict"] == "verified"
    assert check(repo, rev, "pointer", b"version")["reason"] == "unsupported_content"
    for path, component in [
        ("link", "link"), ("link/item", "link"), ("repeat", "repeat"),
        ("missing", "missing"), ("module", "module"),
        ("unavailable-dir/item", "unavailable-dir"),
    ]:
        git_mode, _, entry_id = git(repo, "ls-tree", rev, "--", component).split()[:3]
        mode = git_mode.lstrip("0")
        receipt = check(repo, rev, path, b"x")
        assert receipt["verdict"] == "cant_check", receipt
        evidence = receipt["evidence"]
        assert (evidence["tree_id"], evidence["entry_path"], evidence["entry_mode"], evidence["entry_id"]) == (
            tree, component, mode, entry_id,
        ), receipt
        assert "blob_id" not in evidence
        for fmt in ["text", "markdown"]:
            out = check(repo, rev, path, b"x", fmt)
            assert f"Observed commit {rev}" in out
            assert f'Tree {tree} · entry "{component}" · mode {mode} · Object {entry_id}' in out
    for fmt in ["text", "markdown"]:
        observed = check(repo, rev, " spaced ", b"second\n", fmt)
        assert '" spaced " · line 2' in observed
        assert f"Observed commit {rev}" in observed
        multiline = check(repo, rev, " spaced ", "café\nsecond\n".encode(), fmt)
        assert '" spaced " · lines 1–2' in multiline
        unresolved = check(repo, "0" * 40, " spaced ", b"x", fmt)
        assert "Requested commit " + "0" * 40 in unresolved
    for path, expected in [("repeat/repeat/repeat", "repeat/repeat/repeat"), ("repeat/other/repeat", "repeat/other")]:
        r = check(repo, rev, path, b"x")
        assert r["reason"] == "path_absent" and r["evidence"]["missing_path"] == expected, r
        assert f'missing "{expected}"' in check(repo, rev, path, b"x", "text")


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
    git(root, "clone", "-q", "--bare", "--no-hardlinks", str(repo), str(bare))
    request = [binary, "check", "--rev", rev, "--path", "item", "--quote-file", "-", "--format", "json"]
    quote = b"original"
    expected = subprocess.check_output(request + ["--repo", repo], input=quote)
    assert subprocess.check_output(request + ["--repo", bare], input=quote) == expected
    git(bare, "repack", "-Adq")
    git(bare, "prune-packed")
    assert list((bare / "objects" / "pack").glob("*.idx"))
    assert subprocess.check_output(request, cwd=bare, input=quote) == expected
    assert subprocess.check_output(request + ["--repo", bare], input=quote) == expected
    outside = json.loads(subprocess.check_output(request, cwd=root, input=quote))
    assert outside["reason"] == "repository_unavailable"

    (repo / "item").write_bytes(b"replacement")
    git(repo, "commit", "-qam", "replacement")
    replacement = git(repo, "rev-parse", "HEAD")
    git(repo, "replace", rev, replacement)
    assert git(repo, "cat-file", "blob", f"{rev}:item") == "replacement"
    assert git(repo, "--no-replace-objects", "cat-file", "blob", f"{rev}:item") == "original"
    assert check(repo, rev, "item", b"original") == baseline

    shallow = root / "shallow"
    git(root, "clone", "-q", "--no-local", "--depth=1", str(repo), str(shallow))
    assert git(shallow, "rev-parse", "--is-shallow-repository") == "true"
    assert check(shallow, replacement, "item", b"replacement")["verdict"] == "verified"

    linked = root / "linked"
    git(repo, "worktree", "add", "-q", "--detach", str(linked), replacement)
    separate = root / "separate"
    git(root, "init", "-q", "--separate-git-dir", str(root / "gitdir"), str(separate))
    for path in [linked, separate]:
        r = check(path, rev, "item", b"original")
        assert r["reason"] == "unsupported_storage" and "clone or bare" in r["detail"], r

    assert check(root, rev, "item", b"x")["reason"] == "repository_unavailable"
    assert check(root / "missing", rev, "item", b"x")["reason"] == "repository_unavailable"
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        metadata = repo / ".git"
        metadata.chmod(0)
        try:
            r = check(repo, rev, "item", b"x")
            assert r["reason"] == "repository_unavailable" and "metadata is inaccessible" in r["detail"], r
            assert "--repo" not in r["detail"] and str(repo) not in r["detail"]
        finally:
            metadata.chmod(0o755)
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
    (sha256 / "item").write_bytes(b"sha256")
    git(sha256, "add", "item")
    git(sha256, "commit", "-qm", "sha256 history")
    oid = git(sha256, "rev-parse", "HEAD")
    assert len(oid) == 64
    for malformed, diagnostic in [("g" * 64, b"hexadecimal"), (oid, b"SHA-256")]:
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
    with tempfile.TemporaryDirectory() as directory:
        quote_witnesses(Path(directory))
    print("Edge, repository discovery, quote evidence, privacy and tree limits passed.")
