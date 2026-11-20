# Receipts

Check whether an exact quotation appears in a source file at a particular Git commit. Receipts reads local Git objects and returns the evidence for one claim. Your working copy can contain newer, uncommitted edits.

## Install and run

The [v0.0.1-pre.1 limited preview](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.1) provides native downloads for macOS, Linux and Windows on amd64 and arm64. The downloads have GitHub build attestations. Apple signing and notarization and Windows Authenticode are pending. [Verification and install instructions](https://github.com/valasme/receipts/blob/main/docs/release.md)

With a patched Go toolchain, install this exact preview and check the installed version:

```sh
go install github.com/valasme/receipts/cmd/receipts@v0.0.1-pre.1
receipts --version
```

From a checkout with Go 1.25 or newer, run `go install ./cmd/receipts`. Put your Go binary directory on PATH. For an archive, verify its checksum against the release manifest, extract it and run the included executable directly. On Windows use `.\receipts.exe --help`. On Linux or macOS use `./receipts --help`. To remove an archive installation, delete the extracted files. To switch versions, keep each extraction in its own directory and select the desired binary.

From the root of the Receipts repository, this POSIX example checks the README heading:

```sh
printf %s '# Receipts' > excerpt.txt
receipts check --repo . --rev "$(git rev-parse HEAD)" --path README.md --quote-file excerpt.txt
```

PowerShell:

```powershell
[IO.File]::WriteAllText("$PWD/excerpt.txt", '# Receipts')
receipts check --repo . --rev (git rev-parse HEAD) --path README.md --quote-file excerpt.txt
```

Use a full SHA-1 commit ID, a repository-root-relative path and UTF-8 input. Pass `--quote-file -` for stdin. A final newline is significant. CRLF and LF match. Other whitespace, letter case and Unicode composition remain significant.

## Read the result

**Verified** includes the blob ID and first matching line range. **Contradicted** cites a complete search or a tree proving that a path component was absent. **Can't check** explains missing objects, unsupported content or exhausted budgets. The verdict describes the citation only. Keep the original quote to replay the check.

Text is the default. Use `--format markdown` for a pasteable block and `--format json` for schema-major-1 output. All three verdicts exit 0. Invalid inputs exit 2. Output failures exit 1. Check both the exit status and complete JSON before using a receipt. A receipt can reveal a private path or guessable quote digest.

## Supported storage and limits

Use a regular local clone or bare SHA-1 repository. Receipts reads loose objects, v2 indexes, packed objects and bounded offset deltas. Reference deltas, alternate object databases and linked worktree indirections may return an inconclusive receipt. Symlinks, submodules, LFS pointers and binary source are unsupported. Reads never invoke Git or execute submitted code. The checker accepts a 64 KiB normalized quote, an 8 MiB source and up to 128 path components. Conservative limits on index bytes, total decoded bytes and a five-second object lookup deadline also apply.

## Contribute and report problems

For development, run `go test ./...`, `go vet ./...`, build the executable with `go build -o receipts-test.exe ./cmd/receipts`, and run `python tests/acceptance.py ./receipts-test.exe`, `python tests/storage.py ./receipts-test.exe` and `python tests/evaluate.py ./receipts-test.exe`. Test fixtures use Git and Python 3. The installed binary has no such dependencies. For a verdict change, include a synthetic repository, exact inputs and independently inspected expected result.

Report an ordinary bug with the version, OS, exit code and a small synthetic fixture. Use the private security channel for sensitive issues. Support is best effort. [Issue tracker](https://github.com/valasme/receipts/issues) · [Private security report](https://github.com/valasme/receipts/security/advisories/new) · [Project plan](https://github.com/valasme/receipts/tree/main/docs/planning)

Receipts uses Apache-2.0. Builds after the first preview include an offline copy of the project license and third-party notices in the executable. Run `receipts --licenses` to read them. [Project license](LICENSE) · [Third-party notices](THIRD-PARTY-NOTICES.txt)
