"""Use real Git to validate a known-depth pack and check its supported-depth boundary."""

import hashlib
import struct
import tempfile
import zlib
from pathlib import Path

from acceptance import check
from git_fixture import git, git_bytes


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
        receipt = check(repo, rev, "item", b"ab")
        assert receipt["reason"] == (
            "quote_found" if depth == 16 else "resource_limit"
        ), receipt


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        suite(Path(directory))
    print("Depth 16 replay succeeded, depths 17 and 18 returned resource_limit.")
