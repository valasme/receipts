# Can one person maintain and debug Receipts?

The current unsigned preview is v0.0.1-pre.2. Checked items have a test, inspection or rehearsal. The [verification record](../verification.md) gives results and limitations. The [review inventory](review-inventory.md) covers the broader product, and the [work queue](README.md) links the tickets.

## Follow one request

Start in `cmd/receipts/main.go`. The executable calls `execute` to parse arguments, read the quote and handle cancellation. Follow `Verify` and `inspect` in `internal/check/check.go` for verdicts and `internal/check/objects.go` for committed Git data. The matcher normalizes CRLF to LF, compares literal bytes and returns one receipt. Every renderer consumes that same result. A failed stdout write exits 1, invalid input exits 2 and a completed receipt exits 0. The optional GitHub adapter lives in `pilot/`.

Consider the claim “these two lines occur in this file.” Finding the lines establishes the claim. Searching the entire supported file and finding no match contradicts it. Losing access halfway through leaves it unresolved. The reader must preserve that distinction all the way to the UI.

## Checklist for the maintainer

### Can I change a command without guessing what broke? · PA01, PA02

- [x] Follow the starter from process entry to exit in one file.
- [x] Supply arguments and output writers to run without changing global process state.
- [x] Build from the checkout with the declared module and no third-party Go packages.
- [x] Assert stdout, stderr and actual process exit for help, version and bad usage.
- [x] Inject a failing writer and assert operational failure. Independently replay the Linux full-device case.
- [ ] Make a fresh checkout able to run the same required checks as CI using documented commands.
- [x] Exercise the minimum Go version and record the toolchain used for the shipped binary.
- [x] Show that a failed native check prevents publication of that exact commit.

### Can I locate a wrong verdict? · T01–T05

- [x] Reproduce a complaint with one synthetic repository, a commit, path, quote and expected receipt.
- [x] Inspect the original Git object independently; capture the checkout and blob IDs when they differ in meaning.
- [x] Keep repository lookup, comparison and rendering identifiable in a single request trace through the source.
- [x] Represent complete absence, unavailable evidence and invalid user input as distinct outcomes.
- [ ] Preserve underlying error causes internally while returning stable, safe reasons to users.
- [x] Assign verdicts in one place. A new output format should consume the existing decision.
- [x] Show that a worktree edit after the commit leaves the receipt unchanged.
- [ ] Test a quote ending in a newline, repeated quotes and incomplete reads against independently computed expected results.
- [ ] Make one regression fixture fail before repairing a false contradiction.
- [x] Prove that any diagnostic output leaves machine-readable stdout intact.

### Can I diagnose an installed copy privately? · PA01–PA04, T04

- [x] Read the revision and dirty-tree flag from a clean local debug build with go version -m.
- [x] Stop at main.run in a symbol-bearing build and inspect its caller on Linux.
- [x] Map a downloaded release to exact source, Go version, build flags and architecture.
- [x] Rebuild that revision with symbols and demonstrate a source breakpoint. GoReleaser requests stripped binaries for distribution.
- [ ] Reproduce a report on its actual OS or record the native test gap.
- [ ] Provide a support template asking for version, exit, reason and a synthetic fixture.
- [x] Check that normal errors omit absolute personal paths, raw quotes, source and secrets.
- [ ] On a private repository, let the maintainer investigate locally with networking disabled.
- [x] Demonstrate that failed delivery, user interruption and a valid inconclusive receipt are distinguishable.
- [ ] Verify support and troubleshooting links after extracting the archive on a clean machine.

### Will it stay understandable as it grows? · T01–T07

- [ ] Add a checker only when its proposition, evidence and inconclusive cases can be written down.
- [x] Evaluate the Git reader using packed, loose, incomplete and over-budget fixtures before adopting it.
- [x] Keep forge-specific identity, comment markup and credentials outside the local verdict code.
- [x] Keep path and quote handling identical across renderers and platforms.
- [ ] Add a field to a sample receipt and confirm an older supported consumer's behavior.
- [ ] Demonstrate a bounded reader stopping before a large allocation and releasing resources on cancellation.
- [ ] Measure a slow fixture with Go benchmarks before committing to an optimization.
- [ ] Use CPU or allocation profiles to distinguish a hot matcher from expensive object reads.
- [ ] Rehearse a dependency update with offline fixtures, the held-out cases and an artifact comparison.
- [ ] Let a returning solo owner find the decision, reproduce its test and identify the affected release from the ticket alone.

### Will the integrations remain supportable? · PA02–PA04, T08–T09

- [ ] Keep the pre-alpha install and smoke tests runnable independently of the checker.
- [ ] Verify each advertised install, upgrade and removal path; retain the native environment and actual result.
- [ ] Distinguish failed packaging from failed signing, upload and package-index propagation.
- [ ] Reproduce a bad release locally and identify which users need a corrected version.
- [ ] Use the same receipt for a future local check and GitHub preview of identical inputs.
- [x] Rehearse one stale event and one timed-out comment update without duplicating publication.
- [ ] Disable a faulty publisher and confirm the owner's local checks still work.
- [x] Keep private intake, a hosted inbox and optional AI extraction behind separate adoption decisions. Each adds new debugging and support obligations.

## Tool inventory and decisions

| Task | Tools and verification |
| --- | --- |
| Build and test | Go, gofmt, vet and Go tests. Git and Python 3 create independent fixtures. See the [six-runner test workflow](../../.github/workflows/test.yml) for commands, including golden, storage, edge-case and holdout tests. |
| Debug | Rebuild the exact tagged source with Go debugging information. The Linux GDB drill below reached the CLI entry point. Release binaries are stripped. |
| Hard cases and performance | Race detection, parser fuzzing, deadlines and synthetic near-limit measurements are exercised. Measurements cover particular fixtures and hardware. |
| Dependency health | The CLI uses the Go standard library. The release job runs govulncheck on the compiled files. The build record identifies the compiler shipped. |
| Workflow and package checks | actionlint validates workflow syntax. GoReleaser builds archives and OS packages. The [release pipeline](../../.github/workflows/release.yml) gates the draft on all six native install jobs. |
| Distribution and recovery | Checksum and provenance verification and the public install workflow exercise the published artifacts. Operating-system signing and credential recovery are open. |

The release needs one native executable and local repository data. The developer needs Go and a checkout. Forge access, release tooling and signing credentials belong to publishing. A database, cloud account, container engine or model key would add no capability to the first literal quote check.

## A debugging drill already performed

From a clean checkout on Linux, build a temporary debug executable:

    go build -gcflags='all=-N -l' -o /tmp/receipts-debug ./cmd/receipts
    go version -m /tmp/receipts-debug
    gdb -nx -batch -ex 'break main.execute' -ex 'run --help' -ex 'bt 2' /tmp/receipts-debug

Rebuilt the tagged v0.0.1-pre.1 source and stopped in main.execute, with main.main as the next frame. Redirecting its version output to /dev/full on Linux produced a diagnostic and exit 1. The portable failing-writer test checks this contract on all six targets.
