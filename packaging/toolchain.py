"""Read the compiler and target selected for the exact Go executable."""

from pathlib import Path
import subprocess

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
    files = sorted(
        p for directory in dist.glob("receipts_*") if directory.is_dir()
        for p in directory.iterdir()
    )
    binaries = {}
    for binary in files:
        actual, target, _, settings = build_info(binary)
        expected_name = "receipts.exe" if target[0] == "windows" else "receipts"
        if target not in TARGETS or target in binaries or binary.name != expected_name:
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
