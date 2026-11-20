"""The canonical names, digests and archive layout of a Receipts release."""

import hashlib
import json
import re
import shutil
import stat
import tarfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ARCHES = ("amd64", "arm64")
SUFFIXES = {
    "darwin": ("tar.gz",),
    "linux": ("tar.gz", "deb", "rpm"),
    "windows": ("zip",),
}
TARGETS = {(system, arch) for system in SUFFIXES for arch in ARCHES}
VERSION = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
SHA256 = r"[a-f0-9]{64}"
COMMIT = r"[a-f0-9]{40}"
MANIFEST = "checksums.txt"
RECORD = "build-record.json"
INSTALLERS = "preview-installers.zip"
NOTICES = "THIRD-PARTY-NOTICES.txt"
HISTORICAL_WITHOUT_NOTICES = "v0.0.1-pre.1"
WINGET = "winget/Valasme.Receipts.Preview"
INSTALLER_FILES = {
    "Formula/receipts.rb", "bucket/receipts.json",
    WINGET + ".yaml", WINGET + ".locale.en-US.yaml", WINGET + ".installer.yaml",
}


def validate_tag(tag):
    if not re.fullmatch("v" + VERSION, tag):
        raise ValueError(f"Expected a v-prefixed release tag, got {tag!r}")
    return tag


def asset_name(version, system, arch, suffix):
    return f"receipts_{version}_{system}_{arch}.{suffix}"


def release_assets(version):
    return {
        asset_name(version, system, arch, suffix)
        for system, arch in TARGETS
        for suffix in SUFFIXES[system]
    }


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def read_manifest(path):
    # Accept LF and CRLF, with exactly two ASCII spaces and one flat basename.
    entries = {}
    content = path.read_text(encoding="ascii").removesuffix("\n")
    for line in content.split("\n"):
        match = re.fullmatch(f"({SHA256})  ([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if not match or match[2] in entries:
            raise ValueError(f"Invalid or duplicate checksum entry: {line!r}")
        entries[match[2]] = match[1]
    return entries


@dataclass(frozen=True)
class Bundle:
    root: Path
    version: str
    record: dict
    hashes: dict

    def asset(self, system, arch, suffix):
        return self.root / asset_name(self.version, system, arch, suffix)


def verify_bundle(root, *, tag, commit, workflow=None):
    if tag:
        validate_tag(tag)
    files = {p.name: p for p in root.iterdir()}
    for path in files.values():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Expected a regular bundle file: {path.name}")
    if not {MANIFEST, RECORD, INSTALLERS} <= files.keys():
        raise ValueError("Bundle lacks a checksum manifest, build record or installer manifests")
    hashes = read_manifest(files[MANIFEST])
    if set(hashes) != files.keys() - {MANIFEST}:
        raise ValueError("Checksum manifest does not cover exactly the bundle files")
    for name, expected in hashes.items():
        if digest(files[name]) != expected:
            raise ValueError(f"Checksum mismatch: {name}")

    record = json.loads(files[RECORD].read_bytes())
    if (
        not re.fullmatch(COMMIT, commit)
        or record["source_commit"] != commit
        or record["source_tag"] != tag
        or not re.fullmatch(COMMIT, record["workflow_commit"])
        or (workflow is not None and record["workflow_commit"] != workflow)
        or not re.fullmatch(r"go version go[0-9][0-9A-Za-z.]* [a-z0-9]+/[a-z0-9]+", record["compiler"])
    ):
        raise ValueError("Build record does not match the expected source or workflow")
    version = record.get("version", tag.removeprefix("v"))
    if not re.fullmatch(VERSION, version) or (tag and tag != "v" + version):
        raise ValueError("Bundle version does not match the selected release")
    if set(hashes) != release_assets(version) | {RECORD, INSTALLERS}:
        raise ValueError("Bundle does not contain exactly the required release target assets")
    return Bundle(root, version, record, {**hashes, MANIFEST: digest(files[MANIFEST])})


@contextmanager
def zip_files(path, expected):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) != len(expected) or {m.filename for m in members} != expected:
            raise ValueError(f"Unexpected or duplicate ZIP members in {path.name}")
        for member in members:
            mode = stat.S_IFMT(member.external_attr >> 16)
            if member.is_dir() or member.external_attr & 0x10 or mode not in (0, stat.S_IFREG):
                raise ValueError(f"Expected a regular ZIP member: {member.filename}")
        yield archive


def extract_installers(bundle, dest):
    with zip_files(bundle.root / INSTALLERS, INSTALLER_FILES) as archive:
        for member in archive.infolist():
            path = dest / member.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, path.open("xb") as target:
                shutil.copyfileobj(source, target)


def extract_native(bundle, system, arch, dest):
    exe = "receipts.exe" if system == "windows" else "receipts"
    names = {exe, "README.md", "LICENSE"}
    if bundle.record["source_tag"] != HISTORICAL_WITHOUT_NOTICES:
        names.add(NOTICES)
    if system == "windows":
        with zip_files(bundle.asset(system, arch, "zip"), names) as archive:
            for member in archive.infolist():
                with archive.open(member) as source, (dest / member.filename).open("xb") as target:
                    shutil.copyfileobj(source, target)
    else:
        path = bundle.asset(system, arch, "tar.gz")
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            if len(members) != len(names) or {m.name for m in members} != names:
                raise ValueError(f"Unexpected or duplicate tar members in {path.name}")
            for member in members:
                if not member.isreg() or member.mode & ~0o777:
                    raise ValueError(f"Expected a regular tar member: {member.name}")
                if member.name == exe and not member.mode & stat.S_IXUSR:
                    raise ValueError(f"The packaged binary lacks owner execute permission: {path.name}")
            for member in members:
                target = dest / member.name
                with archive.extractfile(member) as source, target.open("xb") as file:
                    shutil.copyfileobj(source, file)
                target.chmod(member.mode)
    return dest / exe
