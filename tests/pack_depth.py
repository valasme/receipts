"""Use real Git to validate a known-depth pack and check its supported-depth boundary."""

import hashlib
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

from acceptance import check
from git_fixture import env, git, git_bytes


def suite(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    # Tiny distinct blobs form a valid linear offset-delta chain. Git's own
    # index-pack and cat-file independently verify each fixture object.
    count = 19
    pack = bytearray(b"PACK" + struct.pack(">II", 2, count))
    previous = 0
    ids = []
    for i in range(count):
        body = b"ab" + bytes([65 + i])
        start = len(pack)
        if i == 0:
            pack.append(0x33)
            pack.extend(zlib.compress(body))
        else:
            delta = b"\x03\x03\x90\x02\x01" + body[-1:]
            assert 0 < start - previous < 128
            pack.extend(bytes([0x60 + len(delta), start - previous]))
            pack.extend(zlib.compress(delta))
        previous = start
        ids.append(hashlib.sha1(b"blob 3\0" + body).hexdigest())
    digest = hashlib.sha1(pack).digest()
    pack.extend(digest)
    path = repo / ".git/objects/pack" / ("pack-" + digest.hex() + ".pack")
    path.write_bytes(pack)
    git(repo, "index-pack", str(path))
    for depth in [16, 17, 18]:
        oid = ids[depth]
        assert git(repo, "cat-file", "blob", oid) == "ab" + chr(65 + depth)
        entry = f"100644 blob {oid}\titem\n".encode()
        tree = git_bytes(repo, "mktree", data=entry).strip().decode()
        rev = git(repo, "commit-tree", tree, "-m", "depth boundary")
        receipt = check(repo, rev, "item", b"ab", "json-evidence")
        assert receipt["reason"] == (
            "quote_found" if depth == 16 else "resource_limit"
        ), receipt
        if depth > 16:
            assert "pack delta levels" in receipt["detail"], receipt


def reference_delta(repo):
    git(repo, "init", "-q", "--object-format=sha1")
    base = b"abc"
    base_id = hashlib.sha1(b"blob 3\0" + base).digest()
    delta = b"\x03\x03\x90\x02\x01z"
    oid = hashlib.sha1(b"blob 3\0abz").hexdigest()
    pack = (
        b"PACK" + struct.pack(">II", 2, 2) + b"\x33" + zlib.compress(base)
        + bytes([0x70 + len(delta)]) + base_id + zlib.compress(delta)
    )
    digest = hashlib.sha1(pack).digest()
    path = repo / ".git/objects/pack" / ("pack-" + digest.hex() + ".pack")
    path.write_bytes(pack + digest)
    git(repo, "index-pack", str(path))
    assert git(repo, "cat-file", "blob", oid) == "abz"
    tree = subprocess.check_output(
        ["git", "-C", repo, "mktree"], timeout=25, input=f"100644 blob {oid}\titem\n".encode(), env=env
    ).strip().decode()
    rev = git(repo, "commit-tree", tree, "-m", "reference delta")
    receipt = check(repo, rev, "item", b"abz", "json-evidence")
    assert receipt["reason"] == "unsupported_storage" and "reference delta" in receipt["detail"]
    loose = subprocess.check_output(
        ["git", "-C", repo, "hash-object", "-w", "--stdin"], timeout=25, input=b"abz", env=env
    ).strip().decode()
    assert loose == oid
    # Git may deduplicate against the pack. Ensure a supported copy is loose.
    leaf = repo / ".git/objects" / oid[:2] / oid[2:]
    leaf.parent.mkdir(exist_ok=True)
    leaf.write_bytes(zlib.compress(b"blob 3\0abz"))
    assert check(repo, rev, "item", b"abz")["verdict"] == "verified"


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        suite(Path(directory))
    with tempfile.TemporaryDirectory() as directory:
        reference_delta(Path(directory))
    print("Depth 16 verified, depths 17 and 18 hit their limit, and reference delta stayed unsupported.")
