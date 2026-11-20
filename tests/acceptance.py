"""Offline process-level contract. Run with Python 3 and Git: python tests/acceptance.py <binary>."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from git_fixture import git

binary = Path(sys.argv[1]).resolve()

validator = None
if os.getenv("RECEIPTS_VALIDATE_SCHEMA") == "1":
    from jsonschema import Draft202012Validator

    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schema/receipt-v1.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)


def check(repo, rev, path, quote, fmt="json", expected=0, *, quote_file=None):
    p = subprocess.run(
        [
            binary,
            "check",
            "--repo",
            repo,
            "--rev",
            rev,
            "--path",
            path,
            "--quote-file",
            quote_file if quote_file is not None else "-",
            "--format",
            fmt,
        ],
        check=False,
        input=quote if quote_file is None else None,
        capture_output=True,
        timeout=20,
    )
    assert p.returncode == expected, (p.returncode, p.stdout, p.stderr)
    if expected:
        assert not p.stdout and p.stderr
        return
    assert not p.stderr
    if fmt != "json":
        return p.stdout.decode()
    receipt = json.loads(p.stdout)
    if validator:
        validator.validate(receipt)
    return receipt


def suite(repo, packed):
    git(repo, "init", "-q", "--object-format=sha1")
    git(repo, "config", "core.autocrlf", "false")
    (repo / "src").mkdir()
    (repo / "src/a.txt").write_bytes(b"first\r\nBlue\r\nBlue\r\nlast")
    (repo / "src/multiline.txt").write_bytes("first\ncafé\n  second\nlast".encode("utf-8"))
    (repo / "bin").write_bytes(b"x\x00y")
    (repo / "invalid").write_bytes(b"\xff")
    (repo / "pointer").write_bytes(
        b"version https://git-lfs.github.com/spec/v1\noid sha256:"
        + b"f" * 64
        + b"\nsize 3\n"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "baseline")
    rev = git(repo, "rev-parse", "HEAD")
    blob = git(repo, "rev-parse", "HEAD:src/a.txt")
    (repo / "src/a.txt").write_bytes(b"edited")
    if packed:
        git(repo, "gc", "--prune=now")
    cases = [
        ("src/a.txt", b"Blue\r\nBlue\n", "verified", "quote_found"),
        ("src/a.txt", b"blue", "contradicted", "quote_absent"),
        ("src/A.txt", b"Blue", "contradicted", "path_absent"),
        ("missing/path", b"Blue", "contradicted", "path_absent"),
        ("src/a.txt", b"edited", "contradicted", "quote_absent"),
        ("src", b"Blue", "cant_check", "unsupported_kind"),
        ("bin", b"x", "cant_check", "unsupported_content"),
        ("pointer", b"version", "cant_check", "unsupported_content"),
        ("invalid", b"x", "cant_check", "unsupported_content"),
    ]
    for path, quote, verdict, reason in cases:
        r = check(repo, rev, path, quote)
        assert (r["verdict"], r["reason"]) == (verdict, reason), r
        assert (
            r["claim"]["quote_sha256"]
            == hashlib.sha256(quote.replace(b"\r\n", b"\n")).hexdigest()
        )
        label = {
            "verified": "Verified",
            "contradicted": "Contradicted",
            "cant_check": "Can't check",
        }[verdict]
        for fmt in ["text", "markdown"]:
            human = check(repo, rev, path, quote, fmt)
            assert human.strip().startswith(label) and reason in human and rev in human
            for key in ("blob_id", "tree_id", "missing_component"):
                if key in r["evidence"]:
                    assert r["evidence"][key] in human
        assert r == check(repo, rev, path, quote)
        if verdict == "verified":
            assert r["evidence"]["blob_id"] == blob
            assert r["evidence"]["lines"] == {"start": 2, "end": 3}
    with tempfile.TemporaryDirectory() as directory:
        quote_file = Path(directory) / "multiline excerpt.txt"
        for text, normalized, verdict, lines in [
            ("café\r\n  second\r\n", "café\n  second\n", "verified", {"start": 2, "end": 3}),
            ("  second\nlast", "  second\nlast", "verified", {"start": 3, "end": 4}),
            ("  second\nlast\n", "  second\nlast\n", "contradicted", None),
        ]:
            quote = text.encode("utf-8")
            quote_file.write_bytes(quote)
            receipt = check(repo, rev, "src/multiline.txt", quote)
            assert check(repo, rev, "src/multiline.txt", None, quote_file=quote_file) == receipt
            assert receipt["verdict"] == verdict
            assert receipt["claim"]["quote_sha256"] == hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest()
            assert receipt["evidence"].get("lines") == lines
    assert check(repo, "0" * 40, "src/a.txt", b"x")["verdict"] == "cant_check"
    for path in ["../x", "/etc/passwd", "c:/x", "a//b", "a\\b", "a\u202eb"]:
        check(repo, rev, path, b"x", expected=2)
    for quote in [b"", b"a\0b", b"\xff", b"x" * 65537]:
        check(repo, rev, "src/a.txt", quote, expected=2)
    check(repo, "HEAD", "src/a.txt", b"x", expected=2)
    check(repo, blob, "src/a.txt", b"x", expected=2)
    for fmt in ["text", "markdown"]:
        result = check(repo, rev, "src/a.txt", b"Blue", fmt)
        assert "Verified" in result and blob in result and rev in result


if __name__ == "__main__":
    for packed in [False, True]:
        with tempfile.TemporaryDirectory() as d:
            suite(Path(d), packed)
    print("Loose and packed CLI contracts passed")
