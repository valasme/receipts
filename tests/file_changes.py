"""Check file-change receipts through the public review CLI."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


from git_fixture import env, git_bytes


def git(repo, *args, data=None):
    return git_bytes(repo, *args, data=data).decode().rstrip("\n")


def tree(repo, files, extra=()):
    entries = list(extra)
    for path, content in files.items():
        blob = git(repo, "hash-object", "-w", "--stdin", data=content)
        entries.append(f"100644 blob {blob}\t{path}\n")
    return git(repo, "mktree", data="".join(entries).encode())


def commit(repo, files, parent=None, *, extra=()):
    parents = ("-p", parent) if parent else ()
    return git(repo, "commit-tree", tree(repo, files, extra), *parents, "-m", "Fixture")


def review(binary, repo, comparison, head, body, proposal):
    proposal_file = repo / "proposal.json"
    proposal_file.write_text(json.dumps(proposal), encoding="utf-8")
    pin = ["--compare", comparison] if comparison is not None else []
    return subprocess.run(
        [binary, "review", "--repo", repo, "--rev", head, *pin,
         "--submission", "-", "--proposal", proposal_file],
        input=body.encode(), capture_output=True, timeout=20,
    )


def file_change(path, line):
    return {"path": path, "statement": f"The PR updates `{path}`.", "source_lines": [line, line]}


def check_changes(binary, repo, comparison, head, expected):
    claims = [file_change(path, line) for line, path in enumerate(expected, 1)]
    body = "\n".join(claim["statement"] for claim in claims)
    proposal = {"claims": [], "file_changes": claims[::-1], "unresolved": []}
    result = review(binary, repo, comparison, head, body, proposal)
    assert result.returncode == 0 and not result.stderr, result
    preview = result.stdout.decode()
    sections = preview.split("\n\n")[1:]
    assert len(sections) == len(expected), preview
    receipts = {}
    for line, (section, (path, verdict)) in enumerate(zip(sections, expected.items()), 1):
        assert section.startswith(
            f"Submission line {line}\n{verdict} · file changed\nPath {json.dumps(path)}\n"
        ), section
        assert "Claim checked · The file at this exact path changed between the two commits.\n" in section, section
        assert section.rstrip("\n").endswith(f"Submission statement · {json.dumps(claims[line - 1]['statement'])}"), section
        for label, rev in (("Comparison", comparison), ("Head", head)):
            assert f"{label} commit {rev}\n" in section, section
        receipts[path] = section
    return receipts


def compare_paths(binary, repo):
    comparison = commit(repo, {"guide.txt": b"Old guide\n"})
    head = commit(repo, {"guide.txt": b"New guide\n"}, comparison)
    head_tree = git(repo, "rev-parse", f"{head}^{{tree}}")
    base_tip = git(repo, "commit-tree", head_tree,
                   "-p", comparison, "-m", "Divergent base tip")
    assert git(repo, "merge-base", base_tip, head) == comparison
    assert git(repo, "diff", "--name-status", f"{base_tip}...{head}") == "M\tguide.txt"
    assert git(repo, "diff", "--name-status", base_tip, head) == ""
    (repo / "guide.txt").write_bytes(b"Uncommitted guide\n")
    preview = check_changes(binary, repo, comparison, head, {"guide.txt": "Verified"})["guide.txt"]
    for side, rev in (("Comparison", comparison), ("Head", head)):
        tree_id = git(repo, "rev-parse", f"{rev}^{{tree}}")
        blob = git(repo, "rev-parse", f"{rev}:guide.txt")
        assert f"{side} commit {rev}\n  Tree {tree_id} · mode 100644 · Blob {blob}\n" in preview, preview
    assert git(repo, "ls-tree", head, "--", "Guide.txt") == ""
    equal = check_changes(binary, repo, base_tip, head, {"guide.txt": "Contradicted", "Guide.txt": "Contradicted"})
    assert equal["Guide.txt"].count(f'Tree {head_tree} · missing "Guide.txt"') == 2

    renamed = commit(repo, {"new guide.txt": b"New guide\n"}, head)
    assert git(repo, "diff", "-M", "--name-status", head, renamed) == "R100\tguide.txt\tnew guide.txt"
    assert git(repo, "diff", "--no-renames", "--name-status", head, renamed).splitlines() == [
        "D\tguide.txt", "A\tnew guide.txt",
    ]
    receipts = check_changes(binary, repo, head, renamed, {"guide.txt": "Verified", "new guide.txt": "Verified"})
    for path, side, rev in (("guide.txt", "Head", renamed), ("new guide.txt", "Comparison", head)):
        tree_id = git(repo, "rev-parse", f"{rev}^{{tree}}")
        assert f'{side} commit {rev}\n  Tree {tree_id} · missing "{path}"\n' in receipts[path], receipts[path]
    return comparison, head


def compare_modes_and_kinds(binary, repo):
    comparison = commit(repo, {"executable": b"shared", "link": b"target", "dir": b"file"})
    mode_blob = git(repo, "rev-parse", f"{comparison}:executable")
    link_blob = git(repo, "rev-parse", f"{comparison}:link")
    child = tree(repo, {"item.txt": b"nested file"})
    head = commit(repo, {}, comparison, extra=(
        f"100755 blob {mode_blob}\texecutable\n",
        f"120000 blob {link_blob}\tlink\n",
        f"040000 tree {child}\tdir\n",
        f"160000 commit {comparison}\tmodule\n",
    ))
    assert git(repo, "diff", "--name-status", comparison, head, "--", "executable", "link").splitlines() == [
        "M\texecutable", "T\tlink",
    ]
    receipts = check_changes(binary, repo, comparison, head, {
        "executable": "Verified",
        "link": "Verified",
        "dir": "Can't check",
        "dir/item.txt": "Can't check",
        "module": "Can't check",
    })
    assert f"mode 100755 · Blob {mode_blob}" in receipts["executable"]
    assert f"mode 120000 · Blob {link_blob}" in receipts["link"]
    for path in ("dir", "dir/item.txt", "module"):
        assert "unsupported_kind" in receipts[path]
    child_blob = git(repo, "rev-parse", f"{head}:dir/item.txt")
    assert f"Tree {child} · mode 100644 · Blob {child_blob}" in receipts["dir/item.txt"]


def unavailable_objects(binary, repo, comparison, head):
    missing_commit = "1" * 40
    absent = subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", missing_commit], env=env, capture_output=True, timeout=20,
    )
    assert absent.returncode != 0, absent
    missing = check_changes(binary, repo, missing_commit, head, {"guide.txt": "Can't check"})
    assert f"Comparison commit {missing_commit}\n  revision_unavailable\n" in missing["guide.txt"]

    blob = git(repo, "rev-parse", f"{head}:guide.txt")
    loose = repo / ".git" / "objects" / blob[:2] / blob[2:]
    loose.chmod(0o600)
    loose.unlink()
    absent = subprocess.run(
        ["git", "-C", repo, "cat-file", "-e", blob], env=env, capture_output=True, timeout=20,
    )
    assert absent.returncode != 0, absent
    missing = check_changes(binary, repo, comparison, head, {"guide.txt": "Can't check"})
    assert f"Object {blob}\n  object_unavailable\n" in missing["guide.txt"]

    tree_id = git(repo, "rev-parse", f"{head}^{{tree}}")
    loose = repo / ".git" / "objects" / tree_id[:2] / tree_id[2:]
    loose.chmod(0o600)
    loose.unlink()
    missing = check_changes(binary, repo, comparison, head, {"missing.txt": "Can't check"})
    assert f"Head commit {head}\n  object_unavailable\n" in missing["missing.txt"]


def validate_proposals(binary, repo, comparison, head):
    claim = file_change("guide.txt", 1)
    body = claim["statement"]
    proposal = {"claims": [], "file_changes": [claim], "unresolved": []}
    result = review(binary, repo, comparison, head, body + " (edited)", proposal)
    assert result.returncode == 2 and not result.stdout and b"does not match" in result.stderr, result
    result = review(binary, repo, comparison, head, body, {
        **proposal, "file_changes": [{**claim, "path": "Guide.txt"}],
    })
    assert result.returncode == 2 and not result.stdout and b"does not match" in result.stderr, result
    result = review(binary, repo, None, head, body, proposal)
    assert result.returncode == 2 and not result.stdout and b"require --compare" in result.stderr, result
    result = review(binary, repo, "main", head, body, proposal)
    assert result.returncode == 2 and not result.stdout and b"full 40-digit commit ID" in result.stderr, result
    result = review(binary, repo, comparison, head, body, {
        **proposal, "unresolved": [{"statement": body, "source_lines": [1, 1]}],
    })
    assert result.returncode == 2 and not result.stdout and b"must not overlap" in result.stderr, result
    invalid_path = file_change("../guide.txt", 1)
    result = review(binary, repo, comparison, head, invalid_path["statement"], {
        **proposal, "file_changes": [invalid_path],
    })
    assert result.returncode == 2 and not result.stdout and b"repository-relative file path" in result.stderr, result

    quote = {"path": "guide.txt", "quote": "New guide\n", "source_lines": [1, 4]}
    claim = {"path": "guide.txt", "statement": "This PR\r\nupdates `guide.txt` and makes export twice as fast.", "source_lines": [5, 6]}
    submission = "From `guide.txt`:\r\n```text\r\nNew guide\r\n```\r\n" + claim["statement"]
    proposal = {"claims": [quote], "file_changes": [claim], "unresolved": []}
    blob = git(repo, "rev-parse", f"{head}:guide.txt")
    result = review(binary, repo, None, blob, submission, proposal)
    assert result.returncode == 2 and not result.stdout and b"require --compare" in result.stderr, result
    result = review(
        binary, repo, comparison.upper(), head.upper(),
        submission, proposal,
    )
    assert result.returncode == 0 and not result.stderr, result
    preview = result.stdout.decode()
    assert preview.startswith(f"Review preview\nRequested commit {head}\n"), preview
    assert f"Comparison commit {comparison}\n" in preview and f"Head commit {head}\n" in preview, preview
    assert "Submission lines 1–4\nVerified · exact source quote" in preview, preview
    assert "Submission lines 5–6\nVerified · file changed" in preview, preview
    assert "Claim checked · The file at this exact path changed between the two commits.\n" in preview, preview
    assert 'Submission statement · "This PR\\nupdates `guide.txt` and makes export twice as fast."' in preview, preview


def run(binary, repo):
    git(repo, "init", "-q", "--template=", "--object-format=sha1")
    comparison, head = compare_paths(binary, repo)
    compare_modes_and_kinds(binary, repo)
    validate_proposals(binary, repo, comparison, head)
    unavailable_objects(binary, repo, comparison, head)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        run(Path(sys.argv[1]).resolve(), Path(directory))
    print("PASS file-change review")
