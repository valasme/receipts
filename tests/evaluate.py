"""Replay the frozen synthetic corpus. Usage: python tests/evaluate.py <receipts>."""

import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from acceptance import check
from git_fixture import git, git_bytes

VERDICTS = ("verified", "contradicted", "cant_check")


def fixture(repo, family, holdout):
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
    missing = []
    for kind, path, quote, _ in holdout:
        name = path.split("/")[0]
        if kind == "malformed-encoding":
            (repo / name).write_bytes(b"\xff" + quote.encode())
        elif kind == "missing-blob":
            (repo / name).write_bytes(quote.encode())
            missing.append(name)
        elif kind == "regular-ancestor":
            (repo / name).write_text(quote, encoding="utf-8")
        elif kind == "overlarge":
            (repo / name).write_bytes(b"A" * (8 << 20) + quote.encode())
        elif kind != "gitlink":
            raise ValueError(f"unknown holdout fixture {kind}")
    git(repo, "add", ".")
    target = git_bytes(repo, "hash-object", "-w", "--stdin", data=b"bin").strip().decode()
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{target},link")
    for kind, path, _, _ in holdout:
        if kind == "gitlink":
            empty_tree = git_bytes(repo, "mktree", data=b"").strip().decode()
            commit = git(repo, "commit-tree", empty_tree, "-m", "Synthetic gitlink")
            git(repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},{path}")
    git(repo, "commit", "-qm", family["family"])
    rev = git(repo, "rev-parse", "HEAD")
    for name in missing:
        oid = git(repo, "rev-parse", f"{rev}:{name}")
        obj = repo / ".git/objects" / oid[:2] / oid[2:]
        obj.chmod(0o600)
        obj.unlink()
    return rev


def observe(repo, rev, path, quote, expected, reason):
    receipt = check(repo, rev, path, quote)
    actual = receipt["verdict"]
    if actual not in VERDICTS:
        raise ValueError(f"unknown verdict {actual!r}")
    if actual == expected and expected != "cant_check":
        blob = git(repo, "rev-parse", f"{rev}:{path}")
        assert blob == receipt["evidence"]["blob_id"], "blob identity disagrees with Git"
        raw = git_bytes(repo, "cat-file", "blob", blob)
        found = quote.replace(b"\r\n", b"\n") in raw.replace(b"\r\n", b"\n")
        assert found == (actual == "verified"), "normalized match disagrees with Git"
    matches = actual == expected and (reason is None or receipt["reason"] == reason)
    return actual, matches


def evaluate():
    counts = Counter()
    failures = []
    families = json.loads(Path(__file__).with_name("corpus.json").read_text(encoding="utf-8"))
    holdout = json.loads(
        Path(__file__).with_name("holdout-inconclusive.json").read_text(encoding="utf-8")
    )
    for family in families:
        split = family["split"]
        variant = holdout.get(family["family"], [])
        cases = [
            ("shared control" if split == "holdout" and expected == "cant_check" else split,
             path, quote, expected, None)
            for path, quote, expected in family["cases"]
        ]
        cases += [(split, path, quote, "cant_check", reason) for _, path, quote, reason in variant]
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            try:
                rev = fixture(repo, family, variant)
            except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as error:
                failures.append(f"{family['family']} fixture: {error}")
                for group, _, _, expected, _ in cases:
                    counts[group, expected, "error"] += 1
                continue
            for group, path, quote, expected, reason in cases:
                try:
                    actual, matches = observe(repo, rev, path, quote.encode(), expected, reason)
                    if not matches:
                        failures.append(
                            f"{family['family']} {path}: expected {expected}"
                            f"{' / ' + reason if reason else ''}, got {actual}"
                        )
                except (AssertionError, KeyError, OSError, subprocess.SubprocessError,
                        RuntimeError, ValueError) as error:
                    actual = "error"
                    failures.append(f"{family['family']} {path}: {error}")
                counts[group, expected, actual] += 1

    for group in ("development", "holdout", "shared control"):
        columns = (*VERDICTS, "error")
        print(f"{group}: expected / observed", *columns)
        for expected in VERDICTS:
            print(expected, *(counts[group, expected, actual] for actual in columns))
        total = sum(counts[group, expected, actual] for expected in VERDICTS for actual in columns)
        decisive = sum(counts[group, expected, actual] for expected in VERDICTS for actual in VERDICTS[:2])
        eligible = sum(counts[group, expected, actual] for expected in ("verified", "cant_check") for actual in VERDICTS)
        false_contradictions = sum(counts[group, expected, "contradicted"] for expected in ("verified", "cant_check"))
        print(f"Decisive {decisive}/{total}. False contradictions {false_contradictions}/{eligible} evaluated eligible cases.")
    for failure in failures:
        print(failure, file=sys.stderr)
    assert sum(counts.values()) == 70
    return bool(failures)


if __name__ == "__main__":
    sys.exit(evaluate())
