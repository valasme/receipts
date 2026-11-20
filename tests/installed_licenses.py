"""Compare license output and optional installed documents with the source files."""

import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
NOTICES = "THIRD-PARTY-NOTICES.txt"


def verify(binary, license_file=None, *, source=SOURCE):
    license_text = (source / "LICENSE").read_bytes()
    notices = (source / NOTICES).read_bytes()
    output = subprocess.check_output([binary.resolve(), "--licenses"], timeout=20)
    if output != license_text + b"\n" + notices:
        raise ValueError(f"{binary}: license output differs from source")
    if license_file is not None:
        for path, expected in [
            (license_file, license_text),
            (license_file.with_name(NOTICES), notices),
        ]:
            if path.read_bytes() != expected:
                raise ValueError(f"{path}: installed notice differs from source")


if __name__ == "__main__":
    verify(*(Path(arg) for arg in sys.argv[1:]))
