"""Replay the captured agent proposal against a synthetic local Git repository."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ENV = {
    **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "Demo",
    "GIT_AUTHOR_EMAIL": "demo@example.invalid",
    "GIT_AUTHOR_DATE": "2025-01-01T00:00:00Z",
    "GIT_COMMITTER_NAME": "Demo",
    "GIT_COMMITTER_EMAIL": "demo@example.invalid",
    "GIT_COMMITTER_DATE": "2025-01-01T00:00:00Z",
}


def git(repo, *args, data=None):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], input=data, env=ENV, timeout=20,
    )


def fixture(repo):
    git(repo, "init", "-q", "--template=", "--object-format=sha1")
    files = {
        "guide.txt": b"Export starts offline.\n  Save the receipt locally.\n",
        "legacy.dat": b"Legacy export enabled.\n\x00",
    }
    entries = b""
    for path, content in files.items():
        blob = git(repo, "hash-object", "-w", "--stdin", data=content).strip()
        entries += b"100644 blob " + blob + b"\t" + path.encode() + b"\n"
    tree = git(repo, "mktree", data=entries).decode().strip()
    return git(repo, "commit-tree", tree, "-m", "Receipts demo").decode().strip()


def check(binary, repo, option, data):
    process = subprocess.run(
        [binary, "check", "--repo", repo, option, "-", "--format", "json"],
        input=json.dumps(data).encode(),
        capture_output=True,
        check=True,
        timeout=20,
    )
    if process.stderr:
        raise RuntimeError(process.stderr.decode())
    return json.loads(process.stdout)


def source_lines(lines, span):
    start, end = span
    if not 1 <= start <= end <= len(lines):
        raise ValueError("proposal points outside the submission")
    return lines[start - 1 : end]


def replay(binary, proposal_file):
    proposal = json.loads(proposal_file.read_bytes())
    submission = (HERE / "submission.md").read_text(encoding="utf-8").splitlines()
    claims = []
    for item in proposal["claims"]:
        lines = source_lines(submission, item["source_lines"])
        path, quote = item["path"], item["quote"]
        assert f"`{path}`" in lines[0]
        assert lines[1] == "```text" and lines[-1] == "```"
        assert quote == "\n".join(lines[2:-1]) + "\n"
        claims.append({"path": path, "quote": quote})

    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        rev = fixture(repo)
        scope = {"schema_major": 1, "rev": rev}
        result = check(binary, repo, "--batch-file", {**scope, "claims": claims})
        assert result["schema_major"] == 1
        assert len(result["results"]) == len(claims) == 3
        observed = set()
        for item, claim, entry in zip(proposal["claims"], claims, result["results"]):
            receipt = entry["receipt"]
            assert receipt == check(binary, repo, "--claim-file", {**scope, **claim})
            ref = f'{rev}:{claim["path"]}'
            blob = git(repo, "show", ref)
            exact = claim["quote"].encode()
            if b"\x00" in blob:
                expected = "cant_check", "unsupported_content"
            elif exact in blob:
                expected = "verified", "quote_found"
                start = blob[:blob.index(exact)].count(b"\n") + 1
                end = start + exact[:-1].count(b"\n")
                assert receipt["evidence"]["lines"] == {"start": start, "end": end}
            else:
                assert exact.count(b"\n") >= 2
                expected = "contradicted", "quote_absent"
            assert (receipt["verdict"], receipt["reason"]) == expected
            assert receipt["evidence"]["blob_id"] == git(repo, "rev-parse", ref).decode().strip()
            observed.add(receipt["verdict"])
            print(f'{item["source_lines"]} {claim["path"]}: {receipt["verdict"]} ({receipt["reason"]})')
        assert observed == {"verified", "contradicted", "cant_check"}

    assert len(proposal["unresolved"]) == 1
    for item in proposal["unresolved"]:
        lines = source_lines(submission, item["source_lines"])
        assert lines == [item["statement"]] == ["This change makes export twice as fast."]
        print(f'{item["source_lines"]} Unresolved: {item["statement"]}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--proposal", type=Path, default=HERE / "proposal.json")
    args = parser.parse_args()
    replay(args.binary.resolve(), args.proposal)
