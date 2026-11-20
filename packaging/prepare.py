"""Stage the exact outputs of one GoReleaser run with preview-channel manifests."""
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

def prepare(dist, out):
    metadata=json.loads((dist/"metadata.json").read_text())
    version=metadata["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?",version):
        raise ValueError("invalid version")
    base=f"https://github.com/valasme/receipts/releases/download/v{version}/"
    out.mkdir(exist_ok=False)
    assets={}
    for system in ["darwin","linux","windows"]:
        for arch in ["amd64","arm64"]:
            for suffix in {"darwin":["tar.gz"],"linux":["tar.gz","deb","rpm"],"windows":["zip"]}[system]:
                name=f"receipts_{version}_{system}_{arch}.{suffix}"
                shutil.copyfile(dist/name,out/name)
                assets[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    original={name:digest for digest,name in (line.split() for line in (dist/"checksums.txt").read_text().splitlines())}
    if assets!=original:
        raise ValueError("release outputs differ from generated checksums")

    def package(system,arch,suffix):
        name=f"receipts_{version}_{system}_{arch}.{suffix}"
        return base+name,assets[name]

    website="https://github.com/valasme/receipts"
    formula=['class Receipts < Formula','  desc "Check a quotation against a Git commit"',
             f'  homepage "{website}"', f'  version "{version}"','  license "Apache-2.0"']
    for arch,clause in [("arm64","on_arm"),("amd64","on_intel")]:
        url,digest=package("darwin",arch,"tar.gz")
        formula += [f"  {clause} do",f'    url "{url}"',f'    sha256 "{digest}"',"  end"]
    formula += ['  def install','    bin.install "receipts"','  end','  test do',
                '    assert_match version.to_s, shell_output("#{bin}/receipts --version")','  end','end']
    scoop={"version":version,"description":"Offline source quotation checker","homepage":website,
           "license":"Apache-2.0","architecture":{},"bin":"receipts.exe"}
    installers=[]
    for arch,key,warch in [("amd64","64bit","x64"),("arm64","arm64","arm64")]:
        url,digest=package("windows",arch,"zip")
        scoop["architecture"][key]={"url":url,"hash":digest}
        installers.append({"Architecture":warch,"InstallerUrl":url,"InstallerSha256":digest.upper()})
    winget={"PackageIdentifier":"Valasme.Receipts.Preview","PackageVersion":version,
            "PackageLocale":"en-US","Publisher":"valasme","PackageName":"Receipts Preview",
            "License":"Apache-2.0","ShortDescription":"Offline source quotation checker",
            "InstallerType":"zip","NestedInstallerType":"portable",
            "NestedInstallerFiles":[{"RelativeFilePath":"receipts.exe","PortableCommandAlias":"receipts"}],
            "Installers":installers,"ManifestType":"singleton","ManifestVersion":"1.6.0"}
    # JSON is YAML-compatible. Use ordinary YAML for WinGet's manifest reader.
    def scalar(x):
        return json.dumps(x)
    lines=[]
    for k,v in winget.items():
        if isinstance(v,list):
            lines.append(k+":")
            for item in v:
                for i,(k2,v2) in enumerate(item.items()):
                    lines.append(("  - " if i==0 else "    ")+k2+": "+scalar(v2))
        else:
            lines.append(k+": "+scalar(v))
    with zipfile.ZipFile(out/"preview-installers.zip","w",zipfile.ZIP_DEFLATED) as z:
        for name,content in [("Formula/receipts.rb","\n".join(formula)),("bucket/receipts.json",json.dumps(scoop,indent=2)),
                             ("winget/receipts.yaml","\n".join(lines))]:
            z.writestr(zipfile.ZipInfo(name),content+"\n")
    assets["preview-installers.zip"]=hashlib.sha256((out/"preview-installers.zip").read_bytes()).hexdigest()
    (out/"checksums.txt").write_text("".join(f"{assets[n]}  {n}\n" for n in sorted(assets)),encoding="ascii")
if __name__=="__main__":
    prepare(Path(sys.argv[1]),Path(sys.argv[2]))
