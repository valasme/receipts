"""Counterbalanced, one-person timing study. Run outside CI; results stay local."""

import argparse
import json
import os
from pathlib import Path
import secrets
import statistics
import subprocess
import tempfile
import time


def trials():
    for pair in range(12):
        order = ("manual", "receipts") if pair % 2 == 0 else ("receipts", "manual")
        for sequence, mode in enumerate(order):
            yield pair, sequence, mode


def saving(results):
    groups = {}
    for r in results:
        groups.setdefault(r["pair"], {})[r["mode"]] = r["seconds"]
    if len(groups) != 12 or any(
        set(v) != {"manual", "receipts"} for v in groups.values()
    ):
        raise ValueError("12 complete, paired tasks required")
    return statistics.median(
        (v["manual"] - v["receipts"]) / v["manual"] for v in groups.values()
    )


def task(pair, sequence, mode, repo):
    nonce = secrets.token_hex(4)
    name = f"catalog-{nonce}.txt"
    text = "".join(f"item-{i}-{nonce} = {i + pair}\n" for i in range(120))
    expected = "verified" if pair % 3 == 0 else "contradicted"
    row = 43 + sequence
    value = row + pair + (expected == "contradicted")
    quote = f"item-{row}-{nonce} = {value}\n"
    env = dict(
        os.environ,
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Trial",
        GIT_AUTHOR_EMAIL="trial@example.invalid",
        GIT_COMMITTER_NAME="Trial",
        GIT_COMMITTER_EMAIL="trial@example.invalid",
    )

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], env=env)

    git("init", "-q", "--object-format=sha1")
    git("config", "core.autocrlf", "false")
    (repo / name).write_bytes(text.encode())
    git("add", name)
    git("commit", "-qm", "trial snapshot")
    git("tag", "submitted")
    (repo / name).write_text("Working copy differs.\n", encoding="utf-8")
    input(
        f"Pair {pair + 1}/12, mode {mode}. Open another terminal. Press Enter when ready. "
    )
    start = time.monotonic()
    print(
        f"Repository: {repo}\nRevision: submitted\nPath: {name}\nClaimed line (includes LF):\n{quote}",
        flush=True,
    )
    answer = input(
        "Use the assigned method, then type verified, contradicted or cant_check: "
    ).strip()
    elapsed = time.monotonic() - start
    return {
        "pair": pair + 1,
        "sequence": sequence + 1,
        "mode": mode,
        "seconds": elapsed,
        "expected": expected,
        "answer": answer,
        "correct": answer == expected,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new private JSON results file")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("choose a new output file")
    print(
        "Use Git/manual inspection for manual trials and the installed CLI for receipts trials. "
        "Include revision lookup, quote preparation and reading the result. Do not consult the fixture generator."
    )
    results = []
    with args.output.open("x", encoding="utf-8") as log:
        for pair, sequence, mode in trials():
            with tempfile.TemporaryDirectory() as d:
                results.append(task(pair, sequence, mode, Path(d)))
                log.seek(0)
                json.dump(results, log, indent=2)
                log.truncate()
                log.flush()
    percent = 100 * saving(results)
    print(
        f"Median paired time saving: {percent:.1f}%. Correct: {sum(r['correct'] for r in results)}/24."
    )
    print(
        "Self-evaluation on synthetic tasks. Review wrong answers and the correctness holdout before deciding on a pilot."
    )


if __name__ == "__main__":
    main()
