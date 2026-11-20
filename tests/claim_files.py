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
    invalid_rev = json.dumps(dict(claim, rev="HEAD")).encode()
    diagnostic = invoke(repo, "--claim-file", "-", data=invalid_rev, exit_code=2)
    assert b"rev-parse" in diagnostic and b"--rev" not in diagnostic
    legacy_limit = invoke(
        repo, "--rev", rev, "--path", "sample.txt", "--quote-file", "-",
        data=b"x" * 131073, exit_code=2,
    )
    assert b"64 KiB normalized limit" in legacy_limit
    for flag, value in (("--rev", rev), ("--path", ""), ("--quote-file", "-")):
        invoke(repo, "--claim-file", file, flag, value, exit_code=2)



def batch_claims(repo, rev):
    good = {"path": "sample.txt", "quote": "first\n"}
    fake = {"path": "sample.txt", "quote": "fabricated\n"}
    unsupported = {"path": "binary.dat", "quote": "first\n"}
    leak = "do not echo this submission"
    bad = {"path": "../outside", "quote": leak}
    batch = {"schema_major": 1, "rev": rev, "claims": [good, bad, fake, unsupported, good]}
    file = repo / "batch.json"
    file.write_text(json.dumps(batch), encoding="utf-8")
    output = invoke(repo, "--batch-file", file)
    assert output == invoke(repo, "--batch-file", "-", "--format", "json", data=file.read_bytes())
    assert leak.encode() not in output
    assert b"fabricated" not in output
    parsed = json.loads(output)
    assert parsed["schema_major"] == 1
    results = parsed["results"]
    assert len(results) == 5
    assert results[1] == {"error": "supply a repository-relative file path using slash separators"}
    for index, claim, verdict in (
        (0, good, "verified"), (2, fake, "contradicted"),
        (3, unsupported, "cant_check"), (4, good, "verified"),
    ):
        replay = invoke(
            repo, "--claim-file", "-", "--format", "json",
            data=json.dumps({"schema_major": 1, "rev": rev, **claim}).encode(),
        )
        assert results[index] == {"receipt": json.loads(replay)}
        assert results[index]["receipt"]["verdict"] == verdict
    unavailable = dict(batch, rev="0" * 40, claims=[good])
    missing = invoke(repo, "--batch-file", "-", data=json.dumps(unavailable).encode())
    assert json.loads(missing)["results"][0]["receipt"]["reason"] == "revision_unavailable"
    for claims in ([], [good] * 17, None):
        invoke(repo, "--batch-file", "-", data=json.dumps(dict(batch, claims=claims)).encode(), exit_code=2)
    for bad_item in (b'null', b'{"path":"x","quote":"x","quote":"y"}', b'{"path":"x","quote":"\\ud800"}'):
        header = json.dumps({"schema_major": 1, "rev": rev})[:-1].encode()
        data = header + b',"claims":[' + bad_item + b',' + json.dumps(good).encode() + b']}'
        items = json.loads(invoke(repo, "--batch-file", "-", data=data))["results"]
        assert "error" in items[0] and items[1] == results[0]
    for data in (
        b' ' * (1 << 20) + file.read_bytes(),
        file.read_bytes() + b' null',
        file.read_bytes().replace(rev.encode(), b'HEAD'),
    ):
        invoke(repo, "--batch-file", "-", data=data, exit_code=2)
    for flag, value in (("--format", "text"), ("--claim-file", "-"), ("--rev", rev)):
        invoke(repo, "--batch-file", file, flag, value, exit_code=2)


def main():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        git(repo, "init", "-q", "--object-format=sha1")
        git(repo, "config", "core.autocrlf", "false")
        (repo / "sample.txt").write_bytes("first\ncafé 🎉\n  second\nlast".encode())
        (repo / "binary.dat").write_bytes(b"first\x00")
        git(repo, "add", "sample.txt", "binary.dat")
        git(repo, "commit", "-qm", "fixture")
        rev = git(repo, "rev-parse", "HEAD")
        single_claim(repo, rev)
        batch_claims(repo, rev)
    print("Saved claim file and stdin contracts passed.")


if __name__ == "__main__":
    main()
