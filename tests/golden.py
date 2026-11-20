"""Cross-platform byte-for-byte contract for a fixed, independently identified Git commit."""

import json
import subprocess
import tempfile
from pathlib import Path

from acceptance import binary, env, git

REV = "37fdc0ff48840283d170b8c2fac06d2e230a76e7"
BLOB = "42b7aba7a9b41f406f1a40c209f559faf0c42285"
DIGEST = "fd5e386761dd2ffb740d925d62107d7d96dfee5af824c180a88f97be376d6f02"


def golden():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        git(repo, "init", "-q", "--object-format=sha1")
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
        subprocess.run(
            ["git", "-C", directory, "fast-import", "--quiet"],
            input=stream,
            env=env,
            check=True,
        )
        assert git(repo, "rev-parse", "refs/heads/main") == REV
        version = (
            subprocess.check_output([binary, "--version"], text=True)
            .strip()
            .removeprefix("receipts ")
        )
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
        actual = subprocess.check_output(
            [
                binary,
                "check",
                "--repo",
                directory,
                "--rev",
                REV,
                "--path",
                "sample.txt",
                "--quote-file",
                "-",
                "--format",
                "json",
            ],
            input=b"line two",
        )
        assert actual == json.dumps(expected, separators=(",", ":")).encode() + b"\n", (
            actual
        )
    print("Matched frozen commit and exact receipt bytes.")


if __name__ == "__main__":
    golden()
