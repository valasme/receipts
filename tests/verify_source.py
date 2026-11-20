"""Run the minimum-toolchain native source CI job in a clean checkout."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

MINIMUM_GO = "go1.25.0"
SUITES = (
    "tests/acceptance.py", "tests/storage.py", "tests/golden.py", "tests/evaluate.py",
    "tests/edge_cases.py", "tests/pack_depth.py", "tests/claim_files.py",
    "tests/file_changes.py", "examples/agent/replay.py",
)


def verify(source, historical):
    def run(*args):
        print("+", *args, flush=True)
        subprocess.run(args, cwd=source, check=True, timeout=300)

    actual = subprocess.check_output(
        ["go", "env", "GOVERSION"], cwd=source, text=True, timeout=30,
    ).strip()
    print(f"Minimum Go qualification: expected {MINIMUM_GO}, observed {actual}", flush=True)
    if actual != MINIMUM_GO:
        raise SystemExit("The minimum-Go runner must select the exact compiler pin")
    run("go", "env", "GOOS", "GOARCH")
    run("go", "vet", "./...")
    run("go", "test", "-count=1", "./...")
    with tempfile.TemporaryDirectory(prefix="receipts-source-") as temp:
        binary = Path(temp) / "receipts-test.exe"
        run("go", "build", "-o", binary, "./cmd/receipts")
        for relative in SUITES:
            if historical and relative not in SUITES[:4] and not (source / relative).is_file():
                print(f"Suite absent from the pinned historical source: {relative}", flush=True)
                continue
            run(sys.executable, source / relative, binary)
        run(binary, "--version")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=lambda path: Path(path).resolve())
    parser.add_argument("--historical", action="store_true")
    args = parser.parse_args()
    verify(args.source, args.historical)
