"""Exercise saved claim files through the built CLI."""

import json
import subprocess
import tempfile
from pathlib import Path

from acceptance import binary, git


def invoke(repo, *args, data=None, exit_code=0):
    process = subprocess.run(
        [binary, "check", "--repo", repo, *args],
        input=data,
        capture_output=True,
        timeout=20,
    )
    assert process.returncode == exit_code, process
    if exit_code:
        assert not process.stdout and process.stderr, process
        return process.stderr
    assert not process.stderr and process.stdout.endswith(b"\n"), process
    return process.stdout


def single_claim(repo, rev):
    quote = "café 🎉\r\n  second\n"
    legacy = invoke(
        repo, "--rev", rev, "--path", "sample.txt", "--quote-file", "-",
        "--format", "json", data=quote.encode("utf-8"),
    )
    claim = {"schema_major": 1, "rev": rev, "path": "sample.txt", "quote": quote}
    payload = json.dumps(claim).encode()
    file = repo / "saved claim.json"
    file.write_bytes(payload)
    assert invoke(repo, "--claim-file", file, "--format", "json") == legacy
    assert invoke(repo, "--claim-file", "-", "--format", "json", data=payload) == legacy
    assert json.loads(legacy)["evidence"]["lines"] == {"start": 2, "end": 3}
    for fmt in ("text", "markdown"):
        assert b"Verified" in invoke(repo, "--claim-file", file, "--format", fmt)

    malformed = [
        payload + b" {}",
        b'{"quote":"x","quote":"y",' + payload[1:],
        payload.replace(b'"schema_major": 1', b'"schema_major": 2'),
        payload.replace(b'"quote"', b'"Quote"'),
        payload.replace(b'"path"', b'"repo"'),
        payload.replace(b'"quote": ', b'"extra": null, "quote": '),
        payload.replace(rb"\ud83c\udf89", rb"\ud83c"),
        payload.replace(rb"\ud83c\udf89", rb"\udf89"),
        payload.replace(b"second", b"\xff"),
        b" " * (768 * 1024) + payload,
        json.dumps(dict(claim, quote="")).encode(),
        json.dumps(dict(claim, quote="x" * 65537)).encode(),
    ]
    for data in malformed:
        assert b"second" not in invoke(
            repo, "--claim-file", "-", data=data, exit_code=2,
        )
    for flag, value in (("--rev", rev), ("--path", ""), ("--quote-file", "-")):
        invoke(repo, "--claim-file", file, flag, value, exit_code=2)


def main():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        git(repo, "init", "-q", "--object-format=sha1")
        git(repo, "config", "core.autocrlf", "false")
        (repo / "sample.txt").write_bytes("first\ncafé 🎉\n  second\nlast".encode())
        git(repo, "add", "sample.txt")
        git(repo, "commit", "-qm", "fixture")
        rev = git(repo, "rev-parse", "HEAD")
        single_claim(repo, rev)
    print("Saved claim file and stdin contracts passed.")


if __name__ == "__main__":
    main()
