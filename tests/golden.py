"""Cross-platform byte-for-byte contract for a fixed, independently identified Git commit."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from git_fixture import git, git_bytes

REV = "37fdc0ff48840283d170b8c2fac06d2e230a76e7"
BLOB = "42b7aba7a9b41f406f1a40c209f559faf0c42285"
DIGEST = "fd5e386761dd2ffb740d925d62107d7d96dfee5af824c180a88f97be376d6f02"


def fixture(repo):
    git(repo, "init", "-q", "--template=", "--object-format=sha1")
    data = b"first\nline two\nlast\n"
    identity = b"Golden <golden@example.invalid> 1609459200 +0000"
    stream = (
        b"commit refs/heads/main\nauthor "
        + identity
        + b"\ncommitter "
        + identity
        + b"\ndata 8\nfixture\nM 100644 inline sample.txt\ndata "
        + str(len(data)).encode()
        + b"\n"
        + data
        + b"\ndone\n"
    )
    git_bytes(repo, "fast-import", "--quiet", data=stream)
    assert git(repo, "rev-parse", "refs/heads/main") == REV


def receipt(version):
    expected = {
        "schema_major": 1,
        "checker_version": version,
        "claim": {
            "kind": "exact_source_quote",
            "requested_commit": REV,
            "path": "sample.txt",
            "quote_sha256": DIGEST,
        },
        "comparison_rule": "utf8-crlf-to-lf-v1",
        "verdict": "verified",
        "reason": "quote_found",
        "evidence": {
            "object_format": "sha1",
            "observed_commit": REV,
            "blob_id": BLOB,
            "lines": {"start": 2, "end": 2},
        },
    }
    return json.dumps(expected, separators=(",", ":")).encode() + b"\n"


def check_args(binary, repo, quote_file):
    return [
        binary, "check", "--repo", repo, "--rev", REV, "--path", "sample.txt",
        "--quote-file", quote_file, "--format", "json",
    ]


def golden():
    binary = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        fixture(repo)
        version = (
            subprocess.check_output([binary, "--version"], text=True, timeout=20)
            .strip()
            .removeprefix("receipts ")
        )
        def invoke(path, quote, fmt="json"):
            return subprocess.check_output(
                [binary, "check", "--repo", directory, "--rev", REV, "--path", path,
                 "--quote-file", "-", "--format", fmt],
                input=quote, timeout=20,
            )

        baseline = receipt(version)
        assert invoke("sample.txt", b"line two") == baseline
        expected = json.loads(baseline)

        # The inconclusive receipt originally retained the observed commit
        # but omitted the known tree entry. Its default bytes remain stable.
        scope = {"object_format": "sha1", "observed_commit": REV}
        blocked_path = "sample.txt/nested"
        blocked = {
            **expected,
            "claim": {**expected["claim"], "path": blocked_path},
            "verdict": "cant_check",
            "reason": "unsupported_kind",
            "evidence": scope,
        }
        assert invoke(blocked_path, b"line two") == json.dumps(blocked, separators=(",", ":")).encode() + b"\n"
        detail = json.loads(invoke(blocked_path, b"line two", "json-evidence"))
        tree = git(repo, "rev-parse", f"{REV}^{{tree}}")
        assert detail["evidence"] == {
            **scope, "tree_id": tree, "entry_path": "sample.txt",
            "entry_mode": "100644", "entry_id": BLOB,
        }

        data = json.dumps({"schema_major": 1, "rev": REV, "claims": [
            {"path": blocked_path, "quote": "line two"},
        ]}).encode()
        for fmt, document in (("json", blocked), ("json-evidence", detail)):
            output = subprocess.check_output(
                [binary, "check", "--repo", directory, "--batch-file", "-", "--format", fmt],
                input=data, timeout=20,
            )
            result = {"schema_major": 1, "results": [{"receipt": document}]}
            assert output == json.dumps(result, separators=(",", ":")).encode() + b"\n"
    print("Matched frozen commit and exact receipt bytes.")


if __name__ == "__main__":
    golden()
