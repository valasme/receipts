# Receipts

Receipts is a planned open-source CLI for maintainers who want to check a factual statement in a pull request or report. Each finding will identify the claim, the revision checked, the verdict, and where a reader can inspect the evidence.

## Run the starter

From this checkout with Go 1.25 or newer installed, run:

```sh
go run ./cmd/receipts --help
go run ./cmd/receipts --version
go test ./...
```

To install the development CLI from this checkout, run `go install ./cmd/receipts` and add your Go binary directory to PATH. The starter supports help and version output. The first claim checker is in planning.

## First milestone proposal

1. Check a single explicitly supplied claim against a local repository and pinned commit. A good first case is “this exact quotation appears in this file.” Record the path, commit, and matching lines so a maintainer can repeat the check.
2. Exercise all three verdicts on a small fixture repository. An exact quote found in the named file is verified. A complete search of that file can contradict an exact-quote claim. An unavailable revision yields can't check. Include case-sensitive paths and line endings in the fixtures.
3. Render the same receipt as JSON and as a short Markdown comment. Pilot with maintainers using existing submissions and measure both time saved and incorrect contradictions before automating publication.
4. Integrate the proven checker with GitHub. On edits, refresh one comment for the current submission and revision. Keep private reports local. Add optional claim extraction after the receipt format works end to end.

## Distribution

The test workflow runs on Linux, macOS, and Windows. A version tag triggers GoReleaser to build amd64 and arm64 archives for each OS and publish them to GitHub Releases with SHA-256 checksums. A local packaging rehearsal uses `goreleaser release --snapshot --clean`. Package-manager installers and platform signing are future release work.

Licensed under [Apache-2.0](LICENSE).
