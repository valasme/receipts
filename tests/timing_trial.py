"""Counterbalanced one-person timing study. Run outside CI; evidence stays local."""

import argparse
import json
import os
import secrets
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from git_fixture import git

PAIRS = 12
VERDICTS = {"verified", "contradicted", "cant_check"}


def trials():
    for pair in range(PAIRS):
        order = ("manual", "receipts") if pair % 2 == 0 else ("receipts", "manual")
        rows = secrets.SystemRandom().sample(range(24, 96), 2)
        for sequence, (mode, row) in enumerate(zip(order, rows), start=1):
            yield pair + 1, sequence, mode, row


def summarize(results):
    groups = {}
    for observation in results:
        if observation["status"] == "completed":
            groups.setdefault(observation["pair"], {})[observation["mode"]] = observation
    pairs = [group for group in groups.values() if set(group) == {"manual", "receipts"}]
    savings = [
        (pair["manual"]["seconds"] - pair["receipts"]["seconds"]) / pair["manual"]["seconds"]
        for pair in pairs
    ]
    median = statistics.median(savings) if savings else None
    correct = sum(r["status"] == "completed" and r["correct"] for r in results)
    qualified = (
        len(pairs) == PAIRS and correct == PAIRS * 2
        and median is not None and median >= 0.25
    )
    return len(pairs), correct, median, qualified


def record(path, report):
    fd, pending = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(report, output, indent=2, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(pending, path)
    finally:
        Path(pending).unlink(missing_ok=True)


def task(pair, sequence, mode, row, repo):
    nonce = secrets.token_hex(4)
    name = f"catalog-{nonce}.txt"
    text = "".join(f"item-{i}-{nonce} = {i + pair}\n" for i in range(120))
    expected = "verified" if pair % 3 == 1 else "contradicted"
    value = row + pair + (expected == "contradicted")
    quote = f"item-{row}-{nonce} = {value}\n"

    git(repo, "init", "-q", "--object-format=sha1")
    git(repo, "config", "core.autocrlf", "false")
    (repo / name).write_bytes(text.encode())
    git(repo, "add", name)
    git(repo, "commit", "-qm", "trial snapshot")
    git(repo, "tag", "submitted")
    revision = git(repo, "rev-parse", "submitted^{commit}")
    blob = git(repo, "rev-parse", f"{revision}:{name}")
    (repo / name).write_text("Working copy differs.\n", encoding="utf-8")

    observation = {
        "pair": pair, "sequence": sequence, "mode": mode,
        "expected": expected, "assigned_revision": revision, "expected_blob": blob,
        "path": name, "quote": quote, "status": "aborted",
    }
    try:
        input(f"Pair {pair}/{PAIRS}, mode {mode}. Press Enter when ready. ")
        print(
            f"Repository: {repo}\nRevision: submitted\nPath: {name}\nClaimed line (includes LF):\n{quote}",
            flush=True,
        )
        start = time.monotonic()
        answer = input("Complete the review, then enter verified, contradicted or cant_check: ").strip()
        elapsed = time.monotonic() - start
        if answer not in VERDICTS:
            print("Discarded unrecognized verdict. This pair cannot qualify.")
            return {**observation, "status": "discarded"}
        observed_revision = input("Full commit ID observed in your check: ").strip()
        observed_blob = input("Full blob ID observed in your check: ").strip()
    except (KeyboardInterrupt, EOFError):
        return observation
    return {
        **observation,
        "status": "completed", "seconds": elapsed, "answer": answer,
        "observed_revision": observed_revision, "observed_blob": observed_blob,
        "correct": answer == expected and observed_revision == revision and observed_blob == blob,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new private JSON results file")
    parser.add_argument("--binary", default="receipts", help="installed checker to use")
    args = parser.parse_args()
    version = subprocess.check_output([args.binary, "--version"], text=True, timeout=10).strip()
    try:
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.error("choose a new output file")
    os.close(fd)
    print(
        f"Use Git/manual inspection for manual trials and {args.binary} ({version}) for receipts trials. "
        "Include finding the revision, preparing the quote and interpreting the result. "
        "Keep your commands and results available to transcribe evidence after entering the verdict."
    )
    results = []
    report = {"checker_version": version, "samples": results}
    record(args.output, report)
    for pair, sequence, mode, row in trials():
        with tempfile.TemporaryDirectory() as d:
            results.append(task(pair, sequence, mode, row, Path(d)))
        record(args.output, report)
        if results[-1]["status"] == "aborted":
            print("\nTrial interrupted. Observations recorded.")
            break
    paired, correct, median, qualified = summarize(results)
    if median is not None:
        print(f"Median paired time saving: {median:.1%}.")
    print(f"Complete pairs: {paired}/{PAIRS}. Correct with evidence: {correct}/{PAIRS * 2}.")
    print("Self-evaluation on synthetic tasks covered by an independent correctness gate.")
    print("Timing gate passed." if qualified else "Timing gate unqualified.")
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
