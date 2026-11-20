"""Run the pinned source revision's process contracts on its archived executable."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from installed_check import native_target, qualify

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))
from bundle import HISTORICAL_WITHOUT_NOTICES, extract_native, verify_bundle


def smoke(root, source, *, tag, commit, workflow=None):
    bundle = verify_bundle(root, tag=tag, commit=commit, workflow=workflow)
    revision = subprocess.check_output(
        ["git", "-C", source, "rev-parse", "--verify", "HEAD"], text=True, timeout=20,
    ).strip()
    if revision != commit:
        raise ValueError(f"Archived test source is {revision}, expected {commit}")
    system, arch = native_target()
    with tempfile.TemporaryDirectory() as directory:
        dest = Path(directory)
        binary = extract_native(bundle, system, arch, dest)
        qualify(binary, bundle.version)
        for relative in (
            "tests/installed_licenses.py", "tests/acceptance.py", "tests/storage.py",
            "tests/golden.py", "tests/evaluate.py", "tests/claim_files.py",
            "tests/file_changes.py", "examples/agent/replay.py",
        ):
            script = source / relative
            historical = (
                tag == HISTORICAL_WITHOUT_NOTICES and relative == "tests/installed_licenses.py"
                or tag in {HISTORICAL_WITHOUT_NOTICES, "v0.0.1-pre.2"} and relative in {
                    "tests/claim_files.py", "tests/file_changes.py", "examples/agent/replay.py",
                }
            )
            if historical and not script.is_file():
                print(f"{commit}: {relative} was not present", flush=True)
                continue
            print(f"Archived {system}/{arch} {bundle.version}: {relative}", flush=True)
            args = [sys.executable, script, binary]
            if relative == "tests/installed_licenses.py":
                args.append(dest / "LICENSE")
            subprocess.run(args, check=True, timeout=180, cwd=source)
    print(f"Verified and removed {system}/{arch} {bundle.version}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("source", type=lambda value: Path(value).resolve())
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--workflow")
    smoke(**vars(parser.parse_args()))
