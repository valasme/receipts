"""Extract the candidate for this native OS and run the installed CLI contract."""

import hashlib
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from installed_licenses import NOTICES, verify


def smoke(bundle):
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}[
        platform.system()
    ]
    arch = {"amd64": "amd64", "x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[
        platform.machine().lower()
    ]
    # On emulated Python, CI passes the runner's actual architecture.
    arch = {"X64": "amd64", "ARM64": "arm64"}.get(
        os.environ.get("RECEIPTS_NATIVE_ARCH"), arch
    )
    ext = "zip" if system == "windows" else "tar.gz"
    (archive,) = bundle.glob(f"receipts_*_{system}_{arch}.{ext}")
    version = archive.name.split("_")[1]
    digests = {
        name: digest
        for digest, name in (
            x.split() for x in (bundle / "checksums.txt").read_text().splitlines()
        )
    }
    for name, digest in digests.items():
        assert hashlib.sha256((bundle / name).read_bytes()).hexdigest() == digest, name
    exe = "receipts.exe" if system == "windows" else "receipts"
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / exe
        files = [exe, "LICENSE", NOTICES]
        if ext == "zip":
            with zipfile.ZipFile(archive) as z:
                assert "README.md" in z.namelist()
                for name in files:
                    (dest.parent / name).write_bytes(z.read(name))
        else:
            with tarfile.open(archive) as z:
                assert "README.md" in z.getnames()
                for name in files:
                    (dest.parent / name).write_bytes(z.extractfile(name).read())
            dest.chmod(0o755)
        verify(dest, dest.parent / "LICENSE")
        actual = subprocess.check_output([dest, "--version"], text=True).strip()
        assert actual == "receipts " + version, (actual, version)
        for script in ["acceptance.py", "storage.py", "golden.py", "evaluate.py"]:
            subprocess.run(
                [sys.executable, Path(__file__).with_name(script), dest], check=True
            )
        dest.unlink()
    print(f"Verified and removed {system}/{arch} {version}.")


if __name__ == "__main__":
    smoke(Path(sys.argv[1]))
