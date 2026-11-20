"""Offline process-level contract. Run with Python 3 and Git: python tests/acceptance.py <binary>."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
           GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="test@example.invalid",
           GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="test@example.invalid",
           GIT_AUTHOR_DATE="2025-01-01T00:00:00Z", GIT_COMMITTER_DATE="2025-01-01T00:00:00Z")

validator = None
if os.getenv("RECEIPTS_VALIDATE_SCHEMA") == "1":
    from jsonschema import Draft202012Validator
    schema = json.loads((Path(__file__).resolve().parents[1]/"schema/receipt-v1.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env).strip().decode()

def check(repo, rev, path, quote, fmt="json", expected=0):
    p = subprocess.run([binary, "check", "--repo", repo, "--rev", rev, "--path", path,
                        "--quote-file", "-", "--format", fmt], input=quote, capture_output=True)
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
    (repo / "bin").write_bytes(b"x\x00y")
    (repo / "invalid").write_bytes(b"\xff")
    (repo / "pointer").write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"f"*64 + b"\nsize 3\n")
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
        assert r["claim"]["quote_sha256"] == hashlib.sha256(quote.replace(b"\r\n", b"\n")).hexdigest()
        if verdict == "verified":
            assert r["evidence"]["blob_id"] == blob
            assert r["evidence"]["lines"] == {"start": 2, "end": 3}
    assert check(repo, "0"*40, "src/a.txt", b"x")["verdict"] == "cant_check"
    for path in ["../x", "/etc/passwd", "c:/x", "a//b", "a\\b", "a\u202eb"]:
        check(repo, rev, path, b"x", expected=2)
    for quote in [b"", b"a\0b", b"\xff", b"x"*65537]:
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
