"""Replay the frozen synthetic corpus. Usage: python tests/evaluate.py <receipts>."""

import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from acceptance import check, git, env


def evaluate():
    counts = Counter()
    families = json.loads(
        Path(__file__).with_name("corpus.json").read_text(encoding="utf-8")
    )
    for family in families:
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            git(repo, "init", "-q", "--object-format=sha1")
            git(repo, "config", "core.autocrlf", "false")
            (repo / family["path"]).write_bytes(family["source"].encode())
            (repo / "bin").write_bytes(b"x\0y")
            (repo / "dir").mkdir()
            (repo / "dir/keep").touch()
            (repo / "ptr").write_bytes(
                b"version https://git-lfs.github.com/spec/v1\noid sha256:"
                + b"1" * 64
                + b"\nsize 1\n"
            )
            git(repo, "add", ".")
            # Create a Git symlink entry independently of OS symlink privileges.
            target = (
                subprocess.check_output(
                    ["git", "-C", d, "hash-object", "-w", "--stdin"],
                    input=b"bin",
                    env=env,
                )
                .strip()
                .decode()
            )
            git(
                repo,
                "update-index",
                "--add",
                "--cacheinfo",
                "120000," + target + ",link",
            )
            git(repo, "commit", "-qm", family["family"])
            rev = git(repo, "rev-parse", "HEAD")
            for path, quote, expected in family["cases"]:
                result = check(repo, rev, path, quote.encode())
                actual = result["verdict"]
                counts[family["split"], expected, actual] += 1
                assert expected == actual, (
                    family["family"],
                    path,
                    quote,
                    expected,
                    result,
                )
                if expected != "cant_check":
                    blob = git(repo, "rev-parse", rev + ":" + path)
                    assert blob == result["evidence"]["blob_id"]
                    raw = subprocess.check_output(
                        ["git", "-C", d, "cat-file", "blob", blob], env=env
                    )
                    assert (
                        quote.encode().replace(b"\r\n", b"\n")
                        in raw.replace(b"\r\n", b"\n")
                    ) == (actual == "verified")
    for k, v in sorted(counts.items()):
        print(*k, v)
    assert sum(counts.values()) == 60


if __name__ == "__main__":
    evaluate()
