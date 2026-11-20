"""Stage the exact outputs of one GoReleaser run with preview-channel manifests."""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


from bundle import (
    INSTALLERS, MANIFEST, RECORD, VERSION, digest, extract_native,
    read_manifest, release_assets, verify_bundle,
)
from toolchain import release_binaries, scan


def prepare(dist, out, *, tag, commit, workflow, compiler, scanner):
    metadata = json.loads((dist / "metadata.json").read_text())
    version = metadata["version"]
    if not re.fullmatch(VERSION, version) or metadata["commit"] != commit:
        raise ValueError("GoReleaser metadata does not match the selected revision")
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    toolchain = subprocess.check_output(["go", "version"], text=True, timeout=30).strip()
    if toolchain.split()[2] != compiler:
        raise ValueError(f"Expected compiler {compiler}, observed {toolchain}")
    binaries = release_binaries(dist, compiler, commit)

    with tempfile.TemporaryDirectory(prefix=f".{out.name}-", dir=out.parent) as staging:
        candidate = Path(staging) / "bundle"
        candidate.mkdir()
        assets = {}
        for name in sorted(release_assets(version)):
            shutil.copyfile(dist / name, candidate / name)
            assets[name] = digest(candidate / name)
        if assets != read_manifest(dist / MANIFEST):
            raise ValueError("Release outputs differ from GoReleaser checksums")
        installer_manifests(candidate, version, assets)
        record = {
            "source_commit": commit, "source_tag": tag, "workflow_commit": workflow,
            "compiler": toolchain, "version": version,
        }
        (candidate / RECORD).write_text(json.dumps(record, sort_keys=True) + "\n", encoding="ascii")
        assets.update({name: digest(candidate / name) for name in (RECORD, INSTALLERS)})
        (candidate / MANIFEST).write_bytes(
            "".join(f"{sha}  {name}\n" for name, sha in sorted(assets.items())).encode("ascii")
        )
        bundle = verify_bundle(candidate, tag=tag, commit=commit, workflow=workflow)
        for (system, arch), binary in binaries.items():
            with tempfile.TemporaryDirectory(dir=staging) as extraction:
                archived = extract_native(bundle, system, arch, Path(extraction))
                if digest(archived) != digest(binary):
                    raise ValueError(f"Archive contains a different executable: {system}/{arch}")
        scan(binaries, scanner)
        candidate.rename(out)


def installer_manifests(out, version, assets):
    base = f"https://github.com/valasme/receipts/releases/download/v{version}/"

    def package(system, arch, suffix):
        name = f"receipts_{version}_{system}_{arch}.{suffix}"
        return base + name, assets[name]

    website = "https://github.com/valasme/receipts"
    formula = [
        "class Receipts < Formula",
        '  desc "Check a quotation against a Git commit"',
        f'  homepage "{website}"',
        f'  version "{version}"',
        '  license "Apache-2.0"',
    ]
    for arch, clause in [("arm64", "on_arm"), ("amd64", "on_intel")]:
        url, digest = package("darwin", arch, "tar.gz")
        formula += [
            f"  {clause} do",
            f'    url "{url}"',
            f'    sha256 "{digest}"',
            "  end",
        ]
    formula += [
        "  def install",
        '    bin.install "receipts"',
        '    pkgshare.install "LICENSE", "THIRD-PARTY-NOTICES.txt"',
        "  end",
        "  test do",
        '    executable = (bin/"receipts").to_s.shellescape',
        '    assert_equal "receipts #{version}", shell_output("#{executable} --version").strip',
        '    notices = (pkgshare/"LICENSE").read + "\\n" + (pkgshare/"THIRD-PARTY-NOTICES.txt").read',
        '    assert_equal notices, shell_output("#{executable} --licenses")',
        "  end",
        "end",
    ]
    scoop = {
        "version": version,
        "description": "Offline source quotation checker",
        "homepage": website,
        "license": "Apache-2.0",
        "architecture": {},
        "bin": "receipts.exe",
    }
    installers = []
    for arch, key, warch in [("amd64", "64bit", "x64"), ("arm64", "arm64", "arm64")]:
        url, digest = package("windows", arch, "zip")
        scoop["architecture"][key] = {"url": url, "hash": digest}
        installers.append(
            {
                "Architecture": warch,
                "InstallerUrl": url,
                "InstallerSha256": digest.upper(),
            }
        )
    identity = {
        "PackageIdentifier": "Valasme.Receipts.Preview",
        "PackageVersion": version,
    }
    name = identity["PackageIdentifier"]
    documents = {
        f"winget/{name}.yaml": {"DefaultLocale": "en-US", "ManifestType": "version"},
        f"winget/{name}.locale.en-US.yaml": {
            "PackageLocale": "en-US",
            "Publisher": "valasme",
            "PackageName": "Receipts Preview",
            "License": "Apache-2.0",
            "ShortDescription": "Offline source quotation checker",
            "ManifestType": "defaultLocale",
        },
        f"winget/{name}.installer.yaml": {
            "InstallerType": "zip",
            "NestedInstallerType": "portable",
            "NestedInstallerFiles": [
                {"RelativeFilePath": "receipts.exe", "PortableCommandAlias": "receipts"}
            ],
            "Installers": installers,
            "ManifestType": "installer",
        },
    }
    manifests = {}
    for filename, document in documents.items():
        lines = []
        for k, v in {**identity, **document, "ManifestVersion": "1.6.0"}.items():
            if isinstance(v, list):
                lines.append(k + ":")
                for item in v:
                    for i, (k2, v2) in enumerate(item.items()):
                        lines.append(
                            ("  - " if i == 0 else "    ") + k2 + ": " + json.dumps(v2)
                        )
            else:
                lines.append(k + ": " + json.dumps(v))
        manifests[filename] = "\n".join(lines)
    with zipfile.ZipFile(
        out / "preview-installers.zip", "w", zipfile.ZIP_DEFLATED
    ) as z:
        for name, content in [
            ("Formula/receipts.rb", "\n".join(formula)),
            ("bucket/receipts.json", json.dumps(scoop, indent=2)),
            *manifests.items(),
        ]:
            z.writestr(zipfile.ZipInfo(name), content + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--scanner", type=Path, required=True)
    prepare(**vars(parser.parse_args()))
