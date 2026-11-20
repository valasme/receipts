"""Run the pinned source revision's process contracts on its archived executable."""

import argparse
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))
from bundle import extract_native, verify_bundle


def native_target():
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}[platform.system()]
    # An emulated Python may report its own architecture on native ARM runners.
    runner = os.environ.get("RUNNER_ARCH")
    arch = {"X64": "amd64", "ARM64": "arm64"}.get(runner)
    if arch is None:
        arch = {"amd64": "amd64", "x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[
            platform.machine().lower()
        ]
    return system, arch


def smoke(root, source, *, tag, commit, workflow=None):
    bundle = verify_bundle(root, tag=tag, commit=commit, workflow=workflow)
    system, arch = native_target()
    with tempfile.TemporaryDirectory() as directory:
        dest = Path(directory)
        binary = extract_native(bundle, system, arch, dest)
        actual = subprocess.check_output([binary, "--version"], text=True, timeout=20).strip()
        if actual != "receipts " + bundle.version:
            raise ValueError(f"Expected {bundle.version}, observed {actual}")
        for relative in (
            "tests/installed_licenses.py", "tests/acceptance.py", "tests/storage.py",
            "tests/golden.py", "tests/evaluate.py", "tests/claim_files.py",
            "tests/file_changes.py", "examples/agent/replay.py",
        ):
            script = source / relative
            if not script.is_file() and relative in {
                "tests/installed_licenses.py", "tests/claim_files.py",
                "tests/file_changes.py", "examples/agent/replay.py",
            }:
                # Historical source trees qualify the contracts they shipped.
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
