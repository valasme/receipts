"""Qualify the exact installed entry point with a frozen offline receipt."""

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from golden import REV, check_args, fixture, receipt


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


def invoke(*argv, label, timeout=20, **options):
    try:
        return subprocess.run(argv, check=True, timeout=timeout, **options)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"{label}: {error}") from None


def output(*argv, label, timeout=20):
    return invoke(*argv, label=label, timeout=timeout, capture_output=True).stdout


def offline_receipt(binary, version):
    system, _ = native_target()
    with tempfile.TemporaryDirectory(prefix="receipts-offline-") as directory:
        root = Path(directory)
        repo = root / "repo"
        repo.mkdir()
        empty = root / "empty"
        empty.mkdir()
        quote = root / "quote"
        quote.write_bytes(b"line two")
        fixture(repo)
        executable = binary.resolve(strict=True)
        argv = check_args(executable, repo, quote)
        if system == "linux":
            if subprocess.run(["unshare", "-Urn", "true"], timeout=10, capture_output=True).returncode == 0:
                prefix = ["unshare", "-Urn", "--"]
            else:
                user = output("id", "-un", label="Read runner username").decode().strip()
                prefix = ["sudo", "-n", "unshare", "--net", "--", "runuser", "-u", user, "--"]
        elif system == "darwin":
            prefix = ["sandbox-exec", "-p", "(version 1) (allow default) (deny network*)"]
        else:
            prefix = []
            argv = ["pwsh", "-NoProfile", "-File", Path(__file__).with_name("offline_receipt.ps1"),
                    "-Binary", executable, "-Repo", repo, "-Revision", REV,
                    "-Quote", quote, "-EmptyPath", empty]
        if prefix:
            argv = [*prefix, shutil.which("env"), f"PATH={empty}", *argv]
        actual = output(*argv, label="Frozen receipt with networking disabled and Git off PATH", timeout=40)
        if actual != receipt(version):
            raise ValueError(f"Offline receipt bytes differ for {binary}")


def qualify(binary, version, *, expected=None, alias=None, offline=True):

    if expected is not None and binary.read_bytes() != expected.read_bytes():
        raise ValueError(f"{binary}: installed binary differs from the qualified archive")
    for executable in [binary] if alias is None else [binary, alias]:
        actual = output(executable, "--version", label=f"{executable} version").decode().strip()
        if actual != f"receipts {version}":
            raise ValueError(f"{executable}: expected receipts {version}, observed {actual}")
        help_text = output(executable, "--help", label=f"{executable} help")
        if b"Usage:" not in help_text or b"receipts" not in help_text:
            raise ValueError(f"{executable}: unexpected help")
    if offline:
        offline_receipt(binary, version)
    if alias is not None:
        with tempfile.TemporaryDirectory(prefix="receipts-shim-") as directory:
            repo = Path(directory)
            fixture(repo)
            for executable in (binary, alias):
                actual = invoke(
                    *check_args(executable, repo, "-"), label=f"{executable} receipt",
                    capture_output=True, input=b"line two", cwd=repo,
                ).stdout
                if actual != receipt(version):
                    raise ValueError(f"{executable}: shim receipt differs")
    print(f"PASS {'/'.join(native_target())} {binary}: {version}, frozen offline receipt.", flush=True)
