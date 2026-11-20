"""Measure Linux CLI wall time and per-process RSS on an 8 MiB loose Git blob."""

import argparse
import json
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from git_fixture import git


def sample(command):
    with tempfile.TemporaryFile() as output:
        start = time.monotonic()
        with subprocess.Popen(
            ["timeout", "--kill-after=1", "15", *command], stdin=subprocess.DEVNULL, stdout=output
        ) as proc:
            _, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
        seconds = time.monotonic() - start
        if proc.returncode:
            raise RuntimeError(f"checker failed with exit {proc.returncode}")
        output.seek(0)
        receipt = json.load(output)
        assert receipt["verdict"] == "contradicted", receipt
        return {"wall_ms": round(seconds * 1000, 3), "peak_rss_kib": usage.ru_maxrss}


def measure(binary, runs):
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        git(repo, "init", "-q", "--object-format=sha1")
        git(repo, "config", "core.autocrlf", "false")
        (repo / "sample.txt").write_bytes(b"a" * (8 << 20))
        git(repo, "add", "sample.txt")
        git(repo, "commit", "-qm", "8 MiB near-match fixture")
        revision = git(repo, "rev-parse", "HEAD")
        objects = sorted(p for p in (repo / ".git/objects").glob("??/*") if p.is_file())
        quote = repo / "quote"
        quote.write_bytes(b"a" * ((64 << 10) - 1) + b"b")
        command = [binary, "check", "--repo", repo, "--rev", revision, "--path",
                   "sample.txt", "--quote-file", quote, "--format", "json"]
        report = {
            "host": platform.platform(),
            "git": git(repo, "--version"),
            "checker": subprocess.check_output([binary, "--version"], text=True, timeout=10).strip(),
            "fixture_commit": revision,
            "samples": [],
        }
        for _ in range(runs):
            for state in ("eviction requested", "warm"):
                if state == "eviction requested":
                    for path in objects:
                        with path.open("rb") as f:
                            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
                report["samples"].append({"cache": state, **sample(command)})
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--runs", type=int, default=4, help="cold-requested and warm pairs")
    args = parser.parse_args()
    if platform.system() != "Linux" or not hasattr(os, "posix_fadvise") or args.runs < 1:
        parser.error("requires Linux with posix_fadvise and at least one pair")
    print(json.dumps(measure(args.binary.resolve(), args.runs), indent=2))
