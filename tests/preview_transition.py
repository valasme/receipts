"""Qualify fresh installations and public preview upgrades on their native targets."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from installed_check import invoke, native_target, output, qualify

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))
from bundle import (
    HISTORICAL_WITHOUT_NOTICES, NOTICES, RECORD, digest, extract_installers,
    extract_native, validate_tag, verify_bundle,
)
from stage import GitHub, REPO, public
from toolchain import MODULE, build_info

TARGET, ARCH = native_target()
EXE = "receipts.exe" if TARGET == "windows" else "receipts"
CHANNELS = ("archive", "go", "deb", "rpm", "brew", "winget", "scoop")


def transition_order(previous, current):
    def precedence(tag):
        core, sep, suffix = validate_tag(tag)[1:].partition("-")
        if not sep:
            raise ValueError("Both transition tags must be prereleases")
        identifiers = []
        for value in suffix.split("."):
            if value.isdigit():
                if len(value) > 1 and value.startswith("0"):
                    raise ValueError(f"Invalid numeric prerelease identifier: {tag}")
                identifiers.append((0, int(value)))
            else:
                identifiers.append((1, value))
        return tuple(map(int, core.split("."))), identifiers

    if precedence(previous) >= precedence(current):
        raise ValueError("The previous tag must precede the current tag")


def text(*argv, label):
    return output(*argv, label=label).decode().strip()


def installed_go(bundle, source, root, route):
    installed = root / "bin"
    installed.mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ, GOBIN=str(installed), GOMODCACHE=str(root / "modcache"),
        GOENV="off", GOTOOLCHAIN="local", GOWORK="off",
    )
    if route == "candidate":
        requirement = "./cmd/receipts"
    else:
        environment.pop("GOPROXY", None)
        environment.pop("GOSUMDB", None)
        environment.pop("GOPRIVATE", None)
        environment.pop("GONOPROXY", None)
        environment.pop("GONOSUMDB", None)
        if route == "direct":
            environment["GOPROXY"] = "direct"
        requirement = f"{MODULE}/cmd/receipts@{bundle.record['source_tag']}"
    invoke("go", "install", requirement, label=f"Go install using {route}",
           timeout=300, cwd=source if route == "candidate" else root, env=environment)
    return installed / EXE


def qualify_go(binary, bundle, channel):
    compiler, target, module, settings = build_info(binary)
    if target != (TARGET, ARCH):
        raise ValueError(f"{binary}: expected {TARGET}/{ARCH}, observed {target}")
    if channel == "candidate":
        if settings.get("vcs.revision") != bundle.record["source_commit"]:
            raise ValueError("Go candidate install does not match the pinned source commit")
        version = "dev" if module == "(devel)" else module
    else:
        version = bundle.record["source_tag"]
        if module != version:
            raise ValueError(f"Go module version is {module}, expected {version}")
    print(f"Go install ({channel}): {compiler}, {module}, {TARGET}/{ARCH}", flush=True)
    qualify(binary, version)


def verify_rpm(path):
    expected = {"amd64": "x86_64", "arm64": "aarch64"}[ARCH]
    arch = text("rpm", "-qp", "--queryformat", "%{ARCH}", path, label="Read RPM package architecture")
    if arch != expected:
        raise ValueError(f"RPM architecture is {arch}, expected {expected}")


class Installer:
    def __init__(self, channel, root):
        self.channel = channel
        self.root = root
        self.alias = None
        self.license = None
        self.tap_ready = False
        if channel == "archive":
            self.binary = root / "installed" / EXE
        elif channel == "deb":
            self.binary = Path("/usr/bin/receipts")
            self.license = Path("/usr/share/doc/receipts/copyright")
        elif channel == "rpm":
            rpm_root = self.root / "rpm"
            rpm_root.mkdir()
            self.rpm = ["sudo", "-n", "rpm", "--root", rpm_root]
            invoke(*self.rpm, "--initdb", label="Initialize isolated RPM root")
            self.binary = rpm_root / "usr/bin/receipts"
            self.license = rpm_root / "usr/share/licenses/receipts/LICENSE"
        elif channel == "brew":
            self.tap = "valasme/receipts-preview"
            self.formula = f"{self.tap}/receipts"
            self.binary = Path(text("brew", "--prefix", label="Read Homebrew prefix")) / "bin/receipts"
            self.license = self.binary.parent.parent / "opt/receipts/share/receipts/LICENSE"
        elif channel == "winget":
            self.winget = os.environ["RECEIPTS_WINGET"]
            self.winget_flags = ["--scope", "user", "--accept-source-agreements", "--disable-interactivity"]
            self.binary = Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Links/receipts.exe"
        elif channel == "scoop":
            self.scoop_dir = Path(os.environ["SCOOP"])
            self.scoop = ["pwsh", "-NoProfile", "-File", self.scoop_dir / "shims/scoop.ps1"]
            self.binary = self.scoop_dir / "apps/receipts/current/receipts.exe"
            self.alias = self.scoop_dir / "shims/receipts.exe"
            self.license = self.binary.with_name("LICENSE")
        else:
            raise ValueError(f"Unknown installer channel: {channel}")
        self.owned_paths = {self.binary}
        if self.alias:
            self.owned_paths.update(
                self.alias.with_suffix(suffix) for suffix in (".exe", ".shim", ".ps1", ".cmd")
            )
        if self.license:
            self.owned_paths.update({self.license, self.license.with_name(NOTICES)})

    def present(self):
        if any(path.exists() or path.is_symlink() for path in self.owned_paths):
            return True
        if self.channel == "archive":
            return self.binary.parent.is_dir()
        if self.channel == "deb":
            return subprocess.run(
                ["dpkg-query", "-W", "receipts"], capture_output=True, timeout=20,
            ).returncode == 0
        if self.channel == "rpm":
            return subprocess.run(
                [*self.rpm, "-q", "receipts"], capture_output=True, timeout=20,
            ).returncode == 0
        return False

    def remove(self):
        if not self.present():
            return
        if self.channel == "archive":
            shutil.rmtree(self.binary.parent)
        elif self.channel == "deb":
            invoke("sudo", "-n", "dpkg", "--purge", "receipts", label="Remove Debian package")
        elif self.channel == "rpm":
            invoke(*self.rpm, "-e", "receipts", label="Remove RPM")
        elif self.channel == "brew":
            invoke("brew", "uninstall", self.formula, label="Remove Homebrew formula", timeout=90)
        elif self.channel == "winget":
            invoke(self.winget, "uninstall", "--name", "Receipts Preview", "--exact",
                   *self.winget_flags, label="Remove WinGet package", timeout=90)
        elif self.channel == "scoop":
            invoke(*self.scoop, "uninstall", "receipts", label="Remove Scoop manifest", timeout=90)
        for path in self.owned_paths:
            if path.exists() or path.is_symlink():
                raise ValueError(f"Package-owned path survived uninstall: {path}")

    def close(self):
        try:
            self.remove()
        finally:
            if self.tap_ready:
                invoke("brew", "untap", self.tap, label="Remove preview tap", timeout=90)
            if self.channel == "rpm":
                invoke("sudo", "-n", "rm", "-rf", "--", self.root / "rpm", label="Remove isolated RPM root")

    def install(self, bundle, phase, candidate=False):
        ext = "zip" if TARGET == "windows" else "tar.gz"
        if self.channel == "archive":
            self.remove()
            self.binary.parent.mkdir()
            extract_native(bundle, TARGET, ARCH, self.binary.parent)
            self.owned_paths.update(self.binary.parent.iterdir())
        elif self.channel == "deb":
            invoke("sudo", "-n", "dpkg", "-i", bundle.asset(TARGET, ARCH, "deb"),
                   label="Install Debian package", timeout=90)
        elif self.channel == "rpm":
            package = bundle.asset(TARGET, ARCH, "rpm")
            verify_rpm(package)
            options = ["--oldpackage"] if phase == "restore" else []
            invoke(*self.rpm, "--nodeps", "--ignorearch", "-U", *options, package,
                   label="Install RPM", timeout=90)
        else:
            self.remove()
            with tempfile.TemporaryDirectory(dir=self.root) as directory:
                manifests = Path(directory)
                extract_installers(bundle, manifests)
                archive = bundle.asset(TARGET, ARCH, ext)
                self.install_manifest(bundle, manifests, archive, candidate)

    def install_manifest(self, bundle, manifests, archive, candidate):
        if self.channel == "brew":
            new_tap = not self.tap_ready
            if new_tap:
                invoke("brew", "tap-new", "--no-git", self.tap, label="Create preview tap")
                self.tap_ready = True
            tap_dir = Path(text("brew", "--repository", self.tap, label="Locate preview tap"))
            formula = tap_dir / "Formula/receipts.rb"
            formula.parent.mkdir(exist_ok=True)
            shutil.copyfile(manifests / "Formula/receipts.rb", formula)
            if new_tap and subprocess.run(["brew", "command", "trust"], capture_output=True, timeout=20).returncode == 0:
                invoke("brew", "trust", "--formula", self.formula, label="Trust preview formula")
            if candidate:
                cache = Path(text("brew", "--cache", "--build-from-source", self.formula,
                                  label="Find Homebrew candidate cache"))
                cache.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(archive, cache)
            invoke("brew", "install", "--build-from-source", self.formula,
                   label="Install Homebrew formula", timeout=180)
            invoke("brew", "test", self.formula, label="Test Homebrew formula", timeout=90)
        elif self.channel == "winget":
            if candidate:
                cache = Path(tempfile.gettempdir()) / "WinGet" / f"Valasme.Receipts.Preview.{bundle.version}"
                cache.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(archive, cache / digest(archive).upper())
            manifest = manifests / "winget"
            invoke(self.winget, "validate", "--manifest", manifest, label="Validate WinGet manifest")
            invoke(self.winget, "install", "--manifest", manifest, *self.winget_flags,
                   "--accept-package-agreements", label="Install WinGet manifest", timeout=180)
        elif self.channel == "scoop":
            manifest = manifests / "bucket/receipts.json"
            if candidate:
                record = json.loads(manifest.read_bytes())
                key = {"amd64": "64bit", "arm64": "arm64"}[ARCH]
                cache_key = re.sub(r"[^\w.\-]+", "_", record["architecture"][key]["url"])
                cache = self.scoop_dir / "cache"
                cache.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(archive, cache / f"receipts#{bundle.version}#{cache_key}")
            invoke(*self.scoop, "install", manifest, label="Install Scoop manifest", timeout=180)

    def qualify(self, bundle):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            expected = extract_native(bundle, TARGET, ARCH, Path(directory))
            qualify(self.binary, bundle.version, expected=expected, alias=self.alias)
            self.owned_paths.add(self.binary.resolve(strict=True))
            if self.license:
                for published, installed in [
                    ("LICENSE", self.license), (NOTICES, self.license.with_name(NOTICES)),
                ]:
                    if bundle.record["source_tag"] == HISTORICAL_WITHOUT_NOTICES:
                        if installed.is_file():
                            self.owned_paths.add(installed.resolve(strict=True))
                        continue
                    if installed.read_bytes() != expected.with_name(published).read_bytes():
                        raise ValueError(f"Installed notice differs: {installed}")
                    self.owned_paths.add(installed.resolve(strict=True))


def exercise(installer, phases, *, candidate=False):
    if installer.present():
        raise ValueError(f"Expected a clean {installer.channel} installation")
    try:
        for phase, bundle in phases:
            print(f"{installer.channel}: {phase} {bundle.version}", flush=True)
            installer.install(bundle, phase, candidate=candidate)
            installer.qualify(bundle)
    except BaseException:
        try:
            installer.close()
        except Exception as cleanup:
            print(f"Cleanup failed for {installer.channel}: {cleanup}", file=sys.stderr)
        raise
    else:
        installer.close()


def load_bundle(root, tag, commit=None):
    record = json.loads((root / RECORD).read_bytes())
    return verify_bundle(root, tag=tag, commit=commit or record["source_commit"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("retrieve", "transition"):
        command = modes.add_parser(mode)
        if mode == "transition":
            command.add_argument("channel", choices=CHANNELS)
        command.add_argument("previous")
        command.add_argument("current")
    install = modes.add_parser("install")
    install.add_argument("channel", choices=CHANNELS)
    install.add_argument("bundle", type=Path)
    install.add_argument("--tag", required=True)
    install.add_argument("--commit", required=True)
    install.add_argument("--source", type=Path)
    args = parser.parse_args()

    if args.mode in ("retrieve", "transition"):
        transition_order(args.previous, args.current)
        if args.mode == "retrieve":
            github = GitHub(os.environ.get("GITHUB_REPOSITORY", REPO))
            for tag in (args.previous, args.current):
                public(github, tag, Path(tag))
            return
        previous, current = [load_bundle(Path(tag).resolve(), tag) for tag in (args.previous, args.current)]
        phases = [("install", previous), ("update", current), ("restore", previous)]
        candidate = False
    else:
        phases = [("install", load_bundle(args.bundle.resolve(), args.tag, args.commit))]
        candidate = args.source is not None

    with tempfile.TemporaryDirectory(prefix=f"receipts-{args.channel}-") as directory:
        root = Path(directory)
        if args.channel == "go":
            routes = ["candidate"] if candidate else ["proxy-default", "direct"]
            for route in routes:
                for phase, bundle in phases:
                    # Reuse GOBIN across a transition while keeping routes independent.
                    go_root = root / route
                    print(f"go ({route}): {phase} {bundle.version}", flush=True)
                    binary = installed_go(bundle, args.source if candidate else None, go_root, route)
                    qualify_go(binary, bundle, route)
                binary.unlink()
                if binary.exists():
                    raise ValueError("Go-installed binary survived removal")
        else:
            exercise(Installer(args.channel, root), phases, candidate=candidate)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None
