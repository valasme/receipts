# Receipts

Check whether an exact quotation appears in a source file at a particular Git commit. Receipts reads local Git objects, so uncommitted edits do not affect the evidence. The development build can also preview quotations and exact-path file changes alongside the submission lines that proposed them.

## Install and run

The [v0.0.1-pre.2 limited preview](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.2) provides native downloads for macOS, Linux and Windows on amd64 and arm64. The downloads have GitHub build attestations. Apple signing and notarization and Windows Authenticode are pending. [Verification and install instructions](https://github.com/valasme/receipts/blob/main/docs/release.md)

With a patched Go toolchain, install this exact preview and check the installed version:

```sh
go install github.com/valasme/receipts/cmd/receipts@v0.0.1-pre.2
receipts --version
receipts --licenses
```

From a checkout with Go 1.25 or newer, run `go install ./cmd/receipts`. Put your Go binary directory on PATH. For an archive, verify its checksum against the release manifest, extract it and run the included executable directly. On Windows use `.\receipts.exe --help`. On Linux or macOS use `./receipts --help`. To remove an archive installation, delete the extracted files. To switch versions, keep each extraction in its own directory and select the desired binary.

## Try a first receipt

Run this from a local clone of Receipts with the preview installed. If your clone is missing the release tag, run `git fetch origin tag v0.0.1-pre.2`. The example checks the complete first line of the README, including its final newline. The `^{commit}` suffix resolves the release tag to the commit ID Receipts needs.

Linux or macOS:

```sh
rev=$(git rev-parse --verify 'v0.0.1-pre.2^{commit}') &&
  printf '%s\n' '# Receipts' |
  receipts check --repo . --rev "$rev" --path README.md --quote-file -
```

PowerShell:

```powershell
$rev = git rev-parse --verify 'v0.0.1-pre.2^{commit}'
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the release tag to a commit.' }
$quote = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($quote, "# Receipts`n")
    receipts check --repo . --rev $rev --path README.md --quote-file $quote
} finally {
    Remove-Item -LiteralPath $quote
}
```

Expect `Verified · exact source quote` and line 1. Change the quoted text to `# Receipts smoke test` and rerun to see `Contradicted`. Both checks exit 0 because both produced a receipt. To replay a receipt later, keep the full commit ID, the repository-relative path and the exact quote in UTF-8.

Use a full SHA-1 commit ID and a repository-root-relative path for your own claims. Pass `--quote-file -` for stdin. Include the final newline if it is part of the quotation. CRLF and LF match. Other whitespace, letter case and Unicode composition remain significant.

### Check a multiline quote

These examples check the first three lines of the tagged `go.mod`, including the blank line and the newline after `go 1.25.0`. Each should report **Verified** on lines 1–3.

On Linux or macOS, a quoted here-document sends literal text to stdin:

```sh
rev=$(git rev-parse --verify 'v0.0.1-pre.2^{commit}') &&
  receipts check --repo . --rev "$rev" --path go.mod --quote-file - <<'QUOTE'
module github.com/valasme/receipts

go 1.25.0
QUOTE
```

To use a UTF-8 file you already have, replace `--quote-file -` with `--quote-file path/to/excerpt.txt`. In PowerShell, write the text to a file so its encoding and final newline are explicit:

```powershell
$rev = git rev-parse --verify 'v0.0.1-pre.2^{commit}'
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the release tag to a commit.' }
$quote = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($quote, "module github.com/valasme/receipts`n`ngo 1.25.0`n")
    receipts check --repo . --rev $rev --path go.mod --quote-file $quote
} finally {
    Remove-Item -LiteralPath $quote
}
```

Keep indentation and blank lines from the original. Save UTF-8 without a byte-order mark unless the quotation itself contains one. To check a quote that ends without a newline, omit the final newline in the file. A POSIX here-document adds one after its last line.

## Check saved claims from an agent

The development build accepts versioned UTF-8 JSON claim files. As the caller, select the local repository and supply the full commit ID. An agent can propose the repository-relative path and literal quote. Save all three so another reader can replay the check.

```json
{"schema_major":1,"rev":"0123456789abcdef0123456789abcdef01234567","path":"README.md","quote":"# Receipts\n"}
```

Replace the example commit with your full commit ID. Run `receipts check --repo . --claim-file claim.json --format json`. Single claims support all three renderers and produce the same receipt as the corresponding flags. Keep the saved file private when it contains sensitive source text.

For a batch, use one commit and a list of quotations:

```json
{"schema_major":1,"rev":"0123456789abcdef0123456789abcdef01234567","claims":[{"path":"README.md","quote":"# Receipts\n"},{"path":"go.mod","quote":"go 1.25.0\n"}]}
```

Run `receipts check --repo . --batch-file batch.json`. The output is a JSON object with `schema_major: 1` and `results` in input order. Each result has a `receipt` using the existing receipt schema or an `error` with a diagnostic for invalid input. An unavailable object yields a receipt with verdict `cant_check`. A complete batch exits 0 even when some items have errors. An invalid envelope exits 2 with a diagnostic on stderr. Use `-` as either file name to read stdin.

The single-claim input limit is 768 KiB. A batch can contain 1–16 claims, with at most 1 MiB of input and a shared five-second lookup budget. Use the exact JSON field names and include each field once. Existing path and quote limits apply to each claim. See the [working agent example](examples/agent/README.md) for a PR-to-receipt walkthrough.

## Preview a submission locally

Save the PR or issue body as `submission.md` and its [claim proposal](examples/agent/proposal.json) as `proposal.json`. With the development build, run this from a local clone after replacing `COMMIT` with the full commit ID:

```sh
receipts review --submission submission.md --proposal proposal.json --rev COMMIT
```

The preview shows where each checked quote or unresolved statement appears in the submission. Each quote also shows its citation and Git evidence. A proposal whose source lines or text disagree with the submission returns an input error. Review the proposal and the surrounding submission text for context. Run `python examples/agent/replay.py ./receipts-demo.exe` with a development binary to try the worked example.

Previews include citation lines and verbatim statements from the submission. Review that text and the repository paths before sharing a preview.

To check whether a file changed, add a file-change proposal and pass `--compare COMMIT` alongside the head commit in `--rev`. The preview shows evidence for the exact path at both commits. [File-change walkthrough](examples/agent/README.md#check-whether-a-file-changed)

## Read the result

**Verified** includes the blob ID and first matching line range. **Contradicted** cites a complete search or a tree proving that a path component was absent. **Can't check** explains missing objects, unsupported content or exhausted budgets. The verdict describes the citation only. Keep the original quote to replay the check.

Text is the default. Use `--format markdown` for a pasteable block and `--format json` for schema-major-1 output. All three verdicts exit 0. Invalid inputs exit 2. Output failures exit 1. Check both the exit status and complete JSON before using a receipt. A receipt can reveal a private path or guessable quote digest.

Use `receipts check --help` for quotation input and output options, or `receipts review --help` for the review preview. Interrupting a check or review with Ctrl+C exits 130.

## Supported storage and limits

Use a regular local clone or bare SHA-1 repository. Receipts reads loose objects, v2 indexes, packed objects and bounded offset deltas. Reference deltas, alternate object databases and linked worktree indirections may return an inconclusive receipt. Quotation checks leave symlinks, submodules, LFS pointers and binary source unsupported. Reads never invoke Git or execute submitted code. The checker accepts a 64 KiB normalized quote, an 8 MiB source and up to 128 path components. Conservative limits on index bytes, total decoded bytes and a five-second object lookup deadline also apply.

## Contribute and report problems

For development, run `go test ./...`, `go vet ./...`, build the executable with `go build -o receipts-test.exe ./cmd/receipts`, and run `python tests/acceptance.py ./receipts-test.exe`, `python tests/storage.py ./receipts-test.exe` and `python tests/evaluate.py ./receipts-test.exe`. Test fixtures use Git and Python 3. The installed binary has no such dependencies. For a verdict change, include a synthetic repository, exact inputs and independently inspected expected result.

Report an ordinary bug with the version, OS, exit code and a small synthetic fixture. Use the private security channel for sensitive issues. Support is best effort. [Issue tracker](https://github.com/valasme/receipts/issues) · [Private security report](https://github.com/valasme/receipts/security/advisories/new) · [Project plan](https://github.com/valasme/receipts/tree/main/docs/planning)

Receipts uses Apache-2.0. Builds after the first preview include an offline copy of the project license and third-party notices in the executable. Run `receipts --licenses` to read them. [Project license](LICENSE) · [Third-party notices](THIRD-PARTY-NOTICES.txt)
