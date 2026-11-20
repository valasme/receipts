"""Read the compiler and target selected for the exact Go executable."""

import json
import subprocess
from pathlib import Path

from bundle import TARGETS

MODULE = "github.com/valasme/receipts"


def build_info(binary):
    lines = subprocess.check_output(
        ["go", "version", "-m", binary], timeout=30, text=True,
    ).splitlines()
    _, compiler = lines[0].rsplit(": ", 1)
    fields = [line.strip().split("\t") for line in lines[1:]]
    if ["path", MODULE + "/cmd/receipts"] not in fields:
        raise ValueError(f"Unexpected Go executable: {binary}")
    settings = dict(field[1].split("=", 1) for field in fields if field[0] == "build")
    module = next(field[2] for field in fields if field[:2] == ["mod", MODULE])
    return compiler, (settings["GOOS"], settings["GOARCH"]), module, settings


def release_binaries(dist, compiler, commit):
    artifacts = json.loads((dist / "artifacts.json").read_bytes())
    binaries = {}
    for artifact in artifacts:
        if artifact["type"] != "Binary":
            continue
        relative = Path(artifact["path"]).relative_to("dist")
        if len(relative.parts) != 2 or ".." in relative.parts:
            raise ValueError(f"Unexpected GoReleaser binary path: {relative}")
        binary = dist / relative
        if binary.is_symlink() or not binary.is_file():
            raise ValueError(f"Missing regular GoReleaser binary: {binary}")
        actual, target, _, settings = build_info(binary)
        expected_name = "receipts.exe" if target[0] == "windows" else "receipts"
        declared = (artifact["goos"], artifact["goarch"])
        if target != declared or target not in TARGETS or target in binaries or binary.name != expected_name:
            raise ValueError(f"Unexpected or duplicate executable target {target}: {binary}")
        if actual != compiler or settings.get("vcs.revision") != commit:
            raise ValueError(
                f"{binary}: expected {compiler} at {commit}, "
                f"observed {actual} at {settings.get('vcs.revision')}"
            )
        binaries[target] = binary
    if binaries.keys() != TARGETS:
        raise ValueError(f"Missing binary scan targets: {sorted(TARGETS - binaries.keys())}")
    return binaries


def scan(binaries, scanner):
    for (system, arch), binary in sorted(binaries.items()):
        print(f"Scanning {system}/{arch}: {binary}", flush=True)
        subprocess.run([Path(scanner), "-mode=binary", binary], check=True, timeout=180)
