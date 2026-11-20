"""Additional black-box storage and budget tests; requires working Git."""
from pathlib import Path
import subprocess
import tempfile
import zlib
from acceptance import check, env, git

def exercise(repo):
    git(repo, "init","-q","--object-format=sha1")
    git(repo,"config","core.autocrlf","false")
    path = repo/"log.txt"
    # Similar historical blobs encourage a genuine pack delta chain.
    base = b"".join(f"row {i}: shared text\n".encode() for i in range(800))
    commits = []
    for i in range(12):
        path.write_bytes(base + f"iteration {i}\n".encode())
        git(repo,"add","log.txt")
        git(repo,"commit","-qm",str(i))
        commits.append(git(repo,"rev-parse","HEAD"))
    git(repo,"gc","--aggressive","--prune=now")
    idx = next((repo/".git/objects/pack").glob("*.idx"))
    listing = git(repo,"verify-pack","-v",str(idx))
    assert any(len(line.split())==7 and line.split()[1]=="blob" for line in listing.splitlines())
    for i, rev in enumerate(commits):
        assert check(repo,rev,"log.txt",f"iteration {i}\n".encode())["verdict"]=="verified"
    # Force valid checksum-independent facts using Git's own object tools.
    path.write_bytes(b"A"*(8*1024*1024)+b"!")
    git(repo,"add","log.txt")
    git(repo,"commit","-qm","too large")
    rev = git(repo,"rev-parse","HEAD")
    assert check(repo,rev,"log.txt",b"!")["reason"]=="resource_limit"
    tree = git(repo,"rev-parse","HEAD^{tree}")
    loose = repo/".git/objects"/tree[:2]/tree[2:]
    loose.chmod(0o600)
    loose.write_bytes(zlib.compress(b"tree 0\x00"))
    assert check(repo,rev,"absent",b"x")["reason"]=="object_unavailable"
    loose.unlink()
    assert check(repo,rev,"absent",b"x")["verdict"]=="cant_check"
    assert check(repo,commits[0],"log.txt",b"a"*65536)["verdict"]=="contradicted"
    assert check(repo,commits[0],"log.txt",b"\r\n"*65536)["verdict"]=="contradicted"

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        exercise(Path(d))
    print("Deltas, damaged and absent objects, and byte limits passed")
