"""Qualify the two public preview versions through installed entry points."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


TESTS = Path(__file__).resolve().parent
REPO = "valasme/receipts"
MODULE = "github.com/valasme/receipts/cmd/receipts"
TARGET = {"Windows": "windows", "Darwin": "darwin", "Linux": "linux"}[platform.system()]
ARCH = {"X64": "amd64", "ARM64": "arm64"}[os.environ["RUNNER_ARCH"]]
EXE = "receipts.exe" if TARGET == "windows" else "receipts"


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def retrieve(tag, dest):
    run("gh", "release", "download", tag, "--repo", REPO, "--dir", dest)
    record_path = dest / "build-record.json"
    manifest = dest / "checksums.txt"
    record = json.loads(record_path.read_bytes())
    commit = output("gh", "api", f"repos/{REPO}/commits/{tag}", "--jq", ".sha")
    assert record["source_tag"] == tag and record["source_commit"] == commit
    for file in (record_path, manifest):
        run(
            "gh", "attestation", "verify", file, "--repo", REPO,
            "--signer-workflow", f"{REPO}/.github/workflows/release.yml",
            "--source-digest", record["workflow_commit"],
        )
    checksums = {
        name: digest
        for digest, name in (line.split() for line in manifest.read_text().splitlines())
    }
    assert set(checksums) == {p.name for p in dest.iterdir()} - {"checksums.txt"}
    for name, digest in checksums.items():
        assert hashlib.sha256((dest / name).read_bytes()).hexdigest() == digest, name
    print(f"{tag} source {commit}; verified {len(checksums)} asset hashes.", flush=True)
    with zipfile.ZipFile(dest / "preview-installers.zip") as archive:
        archive.extractall(dest / "manifests")


def asset(bundle, suffix):
    (file,) = bundle.glob(f"receipts_*_{TARGET}_{ARCH}.{suffix}")
    return file


def offline_help(binary):
    if TARGET == "linux":
        prefix = ["sudo", "unshare", "--net", "--", "runuser", "-u", os.environ["USER"], "--"]
        if subprocess.run(["unshare", "-Urn", "true"], capture_output=True).returncode == 0:
            prefix = ["unshare", "-Urn", "--"]
        help_text = output(*prefix, binary, "--help")
    elif TARGET == "darwin":
        help_text = output("sandbox-exec", "-p", "(version 1) (allow default) (deny network*)", binary, "--help")
    else:
        help_text = output(
            "pwsh", "-NoProfile", "-File", TESTS / "offline_help.ps1",
            str(binary.resolve(strict=True)),
        )
    assert "Usage:" in help_text and "receipts" in help_text


def qualify(binary, bundle, channel, phase):
    tag = bundle.name
    expected = tag if channel == "go" else tag.removeprefix("v")
    assert output(binary, "--version") == f"receipts {expected}", (channel, phase)
    if channel == "go":
        metadata = output("go", "version", "-m", binary)
        assert f"GOOS={TARGET}" in metadata and f"GOARCH={ARCH}" in metadata
        assert f"mod\tgithub.com/valasme/receipts\t{tag}\t" in metadata
    else:
        if TARGET == "windows":
            with zipfile.ZipFile(asset(bundle, "zip")) as native:
                expected_binary = native.read(EXE)
        else:
            with tarfile.open(asset(bundle, "tar.gz")) as native:
                expected_binary = native.extractfile(EXE).read()
        assert binary.read_bytes() == expected_binary, (channel, phase, "native binary")
    offline_help(binary)
    run(sys.executable, TESTS / "golden.py", binary)
    print(f"PASS {TARGET}/{ARCH} {channel}: {phase}, {expected}; offline help and frozen receipt.", flush=True)


def channels(channel, root):
    installed = root / "installed"
    if channel == "archive":
        def install(bundle, phase):
            if installed.exists():
                shutil.rmtree(installed)
            installed.mkdir()
            if TARGET == "windows":
                with zipfile.ZipFile(asset(bundle, "zip")) as archive:
                    archive.extractall(installed)
            else:
                with tarfile.open(asset(bundle, "tar.gz")) as archive:
                    archive.extractall(installed, filter="data")
        return installed / EXE, install, lambda: shutil.rmtree(installed)

    if channel == "go":
        installed.mkdir()
        def install(bundle, phase):
            run("go", "install", f"{MODULE}@{bundle.name}", env=dict(
                os.environ, GOBIN=str(installed), GOPROXY="direct",
            ))
        binary = installed / EXE
        return binary, install, binary.unlink

    if channel == "deb":
        binary = Path("/usr/bin/receipts")
        def install(bundle, phase):
            run("sudo", "dpkg", "-i", asset(bundle, "deb"))
        return binary, install, lambda: run("sudo", "dpkg", "--purge", "receipts")

    if channel == "rpm":
        installed.mkdir()
        rpm = ["sudo", "rpm", "--root", installed]
        run(*rpm, "--initdb")
        def install(bundle, phase):
            options = ["--oldpackage"] if phase == "restore" else []
            run(*rpm, "--nodeps", "--ignorearch", "-U", *options, asset(bundle, "rpm"))
        return installed / "usr/bin/receipts", install, lambda: run(*rpm, "-e", "receipts")

    if channel == "brew":
        name = "valasme/receipts-preview/receipts"
        tap = "valasme/receipts-preview"
        run("brew", "tap-new", "--no-git", tap)
        formula = Path(output("brew", "--repository", tap)) / "Formula/receipts.rb"
        formula.parent.mkdir(exist_ok=True)
        binary = Path(output("brew", "--prefix")) / "bin/receipts"
        def remove():
            run("brew", "uninstall", name)
        def install(bundle, phase):
            if phase != "install":
                remove()
            shutil.copyfile(bundle / "manifests/Formula/receipts.rb", formula)
            if phase == "install" and subprocess.run(
                ["brew", "command", "trust"], capture_output=True,
            ).returncode == 0:
                run("brew", "trust", "--formula", name)
            run("brew", "install", "--build-from-source", name)
        def uninstall():
            remove()
            run("brew", "untap", tap)
        return binary, install, uninstall

    if channel == "winget":
        winget = str(Path(os.environ["RECEIPTS_WINGET"]))
        binary = Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Links/receipts.exe"
        common = ["--scope", "user", "--accept-source-agreements", "--disable-interactivity"]
        def remove():
            run(winget, "uninstall", "--name", "Receipts Preview", "--exact", *common)
        def install(bundle, phase):
            manifest = bundle / "manifests/winget"
            run(winget, "validate", "--manifest", manifest)
            if phase != "install":
                remove()
            run(winget, "install", "--manifest", manifest, *common, "--accept-package-agreements")
        return binary, install, remove

    assert channel == "scoop", channel
    scoop_dir = Path(os.environ["SCOOP"])
    scoop = ["pwsh", "-NoProfile", "-File", scoop_dir / "shims/scoop.ps1"]
    binary = scoop_dir / "apps/receipts/current/receipts.exe"
    alias = scoop_dir / "shims/receipts.exe"

    def remove():
        run(*scoop, "uninstall", "receipts")
        assert not alias.exists()

    def install(bundle, phase):
        if phase != "install":
            remove()
        run(*scoop, "install", bundle / "manifests/bucket/receipts.json")
        assert alias.is_file()

    return binary, install, remove


def transition(channel, previous, current):
    root = Path.cwd() / channel
    root.mkdir()
    binary, install, remove = channels(channel, root)
    assert not binary.exists(), binary
    for phase, bundle in [("install", previous), ("update", current), ("restore", previous)]:
        install(bundle, phase)
        qualify(binary, bundle, channel, phase)
    remove()
    assert not binary.exists() and not binary.is_symlink(), binary
    print(f"PASS {TARGET}/{ARCH} {channel}: removed {previous.name}.", flush=True)


if __name__ == "__main__":
    command, prev, curr = sys.argv[1:]
    previous, current = Path(prev).resolve(), Path(curr).resolve()
    if command == "retrieve":
        for dest in (previous, current):
            retrieve(dest.name, dest)
    else:
        transition(command, previous, current)
