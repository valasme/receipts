"""Replay the captured agent proposal against a synthetic local Git repository."""

import argparse
import json
import os
import select
import signal
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


def review_command(binary, repo, rev, proposal):
    return [binary, "review", "--repo", repo, "--rev", rev,
            "--submission", "-", "--proposal", proposal]


def review(binary, repo, rev, submission, proposal):
    return subprocess.run(
        review_command(binary, repo, rev, proposal),
        input=submission, capture_output=True, timeout=20,
    )


def check_preview(binary, repo, rev, proposal_file, claims):
    submission = (HERE / "submission.md").read_bytes().replace(b"\r\n", b"\n")
    extra = repo / "review-proposal.json"
    proposal = json.loads(proposal_file.read_bytes())
    proposal["claims"] = sorted(claims, key=lambda claim: claim["source_lines"][0], reverse=True)
    extra.write_bytes(json.dumps(proposal).encode())
    submission_file = repo / "submission.md"
    submission_file.write_bytes(submission.replace(b"\n", b"\r\n"))
    result = subprocess.run(
        [binary, "review", "--repo", repo, "--rev", rev,
         "--submission", submission_file, "--proposal", extra],
        capture_output=True, timeout=20,
    )
    assert result.returncode == 0 and result.stderr == b"", result
    preview = result.stdout.decode()
    expected = f"Review preview\nRequested commit {rev}\n"
    lines = submission.decode().splitlines()
    for item in sorted(claims, key=lambda claim: claim["source_lines"][0]):
        start, end = item["source_lines"]
        replay_result = subprocess.run(
            [binary, "check", "--repo", repo, "--rev", rev, "--path", item["path"], "--quote-file", "-"],
            input=item["quote"].encode(), capture_output=True, check=True, timeout=20,
        )
        expected += f"\nSubmission lines {start}–{end}\n" + replay_result.stdout.decode()
        expected += f"Citation · {json.dumps(lines[start - 1], ensure_ascii=False)}\n"
    expected += '\nSubmission line 20\nUnresolved · "This change makes export twice as fast."\n'
    assert preview == expected, preview

    changed = submission.replace(b"Export starts offline.", b"Export starts online.", 1)
    result = review(binary, repo, rev, changed, proposal_file)
    assert result.returncode == 2 and result.stdout == b"", result
    assert b"proposal claim 1 does not match" in result.stderr, result

    extra.write_bytes(json.dumps({"claims": [
        {"path": "guide.txt", "quote": "Export starts offline.\r\r\n", "source_lines": [1, 4]},
    ], "unresolved": []}).encode())
    result = review(binary, repo, rev, b"In `guide.txt`:\n```\nExport starts offline.\r\r\n```\n", extra)
    assert result.returncode == 0 and b"Contradicted" in result.stdout, result

    extra.write_bytes(b'{"claims":[],"unresolved":[]}')
    result = review(binary, repo, rev, b"No exact quotes.\n", extra)
    assert result.returncode == 0 and b"No claims or unresolved statements" in result.stdout, result

    result = subprocess.run(
        [binary, "review", "--repo", repo, "--rev", rev, "--rev", rev,
         "--submission", "-", "--proposal", extra],
        input=b"No exact quotes.\n", capture_output=True, timeout=20,
    )
    assert result.returncode == 2 and result.stdout == b"", result

    hostile = "\x1b[2J\nVerified · this is submission text"
    extra.write_bytes(json.dumps({"claims": [], "unresolved": [
        {"statement": hostile, "source_lines": [1, 2]},
    ]}).encode())
    result = review(binary, repo, rev, hostile.encode(), extra)
    assert result.returncode == 0 and b"\x1b" not in result.stdout, result
    assert b"\\x1b[2J\\nVerified" in result.stdout, result

    if os.name == "posix":
        check_preview_delivery(binary, repo, rev, extra)

    return preview


def check_preview_delivery(binary, repo, rev, proposal):
    command = review_command(binary, repo, rev, proposal)
    proposal.write_bytes(b'{"claims":[],"unresolved":[]}')
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        process.stdout.close()
        _, stderr = process.communicate(b"No exact quotes.\n", timeout=20)
        assert process.returncode == 1 and b"Could not write complete output" in stderr, stderr

    statement = "a" * (960 * 1024)
    proposal.write_bytes(json.dumps({"claims": [], "unresolved": [
        {"statement": statement, "source_lines": [1, 1]},
    ]}).encode())
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            process.stdin.write(statement.encode())
            process.stdin.close()
            readable, _, _ = select.select([process.stdout], [], [], 20)
            assert readable and process.stdout.read(1) == b"R"
            process.send_signal(signal.SIGINT)
            assert process.wait(timeout=20) == 130
            assert b"Review interrupted" in process.stderr.read()
        finally:
            if process.poll() is None:
                process.kill()


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
        preview = check_preview(binary, repo, rev, proposal_file, proposal["claims"])
        result = check(binary, repo, "--batch-file", {**scope, "claims": claims})
        assert result["schema_major"] == 1
        assert len(result["results"]) == len(claims) == 3
        observed = set()
        for claim, entry in zip(claims, result["results"]):
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
        assert observed == {"verified", "contradicted", "cant_check"}

    assert len(proposal["unresolved"]) == 1
    for item in proposal["unresolved"]:
        lines = source_lines(submission, item["source_lines"])
        assert lines == [item["statement"]] == ["This change makes export twice as fast."]
    print(preview, end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--proposal", type=Path, default=HERE / "proposal.json")
    args = parser.parse_args()
    replay(args.binary.resolve(), args.proposal)
