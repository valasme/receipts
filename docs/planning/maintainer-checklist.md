# Can one person maintain and debug Receipts?

Baseline: e3cd928 on Linux amd64, Go 1.27.4. The starter is easy to inspect and step through. Release debugging and the future checker's maintainability still need evidence. This checklist supplements the [520 product and operations checks](review-inventory.md). Checked boxes below denote observed results. Open boxes name the demonstration needed to close them. Ticket IDs resolve in the [work queue](README.md).

## Follow one request

Today, main passes arguments and two output writers to run. Help or version writes one line to stdout and returns 0. An unknown command writes usage guidance to stderr and returns 2. The source has a concrete bug at the output boundary: the successful paths ignore write errors.

In the planned checker, a person supplies a local repository, a full commit ID, a path inside that commit, and the quoted text. The CLI validates those inputs. The Git reader locates the tree entry and reads the committed blob, even if the working copy has since changed. The matcher normalizes CRLF to LF on both sides and compares literal text. The decision records the rule, revision and evidence. Text, Markdown and JSON render that same decision. A later GitHub integration is another consumer. See the [CLI examples](receipt-examples.md) for actual proposed output.

Consider the claim “these two lines occur in this file.” Finding the lines establishes the claim. Searching the entire supported file and finding no match contradicts it. Losing access halfway through leaves it unresolved. The reader must preserve that distinction all the way to the UI.

## Checklist for the maintainer

### Can I change a command without guessing what broke? · PA01, PA02

- [x] Follow the starter from process entry to exit in one file.
- [x] Supply arguments and output writers to run without changing global process state.
- [x] Build from the checkout with the declared module and no third-party Go packages.
- [ ] Assert stdout, stderr and actual process exit for help, version and bad usage.
- [ ] Inject a failing writer and assert operational failure. Independently replay the Linux full-device case.
- [ ] Make a fresh checkout able to run the same required checks as CI using documented commands.
- [ ] Exercise the minimum Go version and record the toolchain used for the shipped binary.
- [ ] Show that a failed native check prevents publication of that exact commit.

### Can I locate a wrong verdict? · T01–T05

- [ ] Reproduce a complaint with one synthetic repository, a commit, path, quote and expected receipt.
- [ ] Inspect the original Git object independently; capture the checkout and blob IDs when they differ in meaning.
- [ ] Keep repository lookup, comparison and rendering identifiable in a single request trace through the source.
- [ ] Represent complete absence, unavailable evidence and invalid user input as distinct outcomes.
- [ ] Preserve underlying error causes internally while returning stable, safe reasons to users.
- [ ] Assign verdicts in one place. A new output format should consume the existing decision.
- [ ] Show that a worktree edit after the commit leaves the receipt unchanged.
- [ ] Test a quote ending in a newline, repeated quotes and incomplete reads against independently computed expected results.
- [ ] Make one regression fixture fail before repairing a false contradiction.
- [ ] Prove that any diagnostic output leaves machine-readable stdout intact.

### Can I diagnose an installed copy privately? · PA01–PA04, T04

- [x] Read the revision and dirty-tree flag from a clean local debug build with go version -m.
- [x] Stop at main.run in a symbol-bearing build and inspect its caller on Linux.
- [ ] Map a downloaded release to exact source, Go version, build flags and architecture.
- [ ] Rebuild that revision with symbols and demonstrate a source breakpoint. GoReleaser requests stripped binaries for distribution.
- [ ] Reproduce a report on its actual OS or record the native test gap.
- [ ] Provide a support template asking for version, exit, reason and a synthetic fixture.
- [ ] Check that normal errors omit absolute personal paths, raw quotes, source and secrets.
- [ ] On a private repository, let the maintainer investigate locally with networking disabled.
- [ ] Demonstrate that failed delivery, user interruption and a valid inconclusive receipt are distinguishable.
- [ ] Verify support and troubleshooting links after extracting the archive on a clean machine.

### Will it stay understandable as it grows? · T01–T07

- [ ] Add a checker only when its proposition, evidence and inconclusive cases can be written down.
- [ ] Evaluate the Git reader using packed, loose, incomplete and over-budget fixtures before adopting it.
- [ ] Keep forge-specific identity, comment markup and credentials outside the local verdict code.
- [ ] Keep path and quote handling identical across renderers and platforms.
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
- [ ] Rehearse one stale event and one timed-out comment update without duplicating publication.
- [ ] Disable a faulty publisher and confirm the owner's local checks still work.
- [ ] Keep private intake, a hosted inbox and optional AI extraction behind separate adoption decisions. Each adds new debugging and support obligations.

## Tool inventory and decisions

| Task | Available or configured here | Gap and disposition |
| --- | --- | --- |
| Build, formatting, static checks | Go, gofmt and go vet available; vet passed | Document the development commands and assert formatting and vet in candidate CI. |
| Repeatable tests | go test works; current CI calls it | Zero test files. Starter process and failing-writer tests are first priority. Add fixtures as behaviors land. |
| Source debugging | GDB worked with a local unoptimized build. Delve and gopls were absent from PATH | Keep the verified GDB recipe. Delve and editor navigation are developer conveniences. No editor requirement. |
| Hard cases and performance | Go toolchain supplies fuzzing, benchmarks, profiling and race testing on supported platforms | Choose targets when parsing or concurrent work exists. Record fixtures, baseline and bounded run time. An installed profiler by itself provides no performance baseline. |
| Dependency health | Current Go module declares zero external modules. govulncheck and staticcheck absent from PATH | Plan a pinned vulnerability check covering the toolchain and future dependencies. Adopt additional lint rules when they catch a demonstrated problem. |
| Workflow validation | Git and gh available; actionlint absent from PATH | A pinned workflow lint check can catch configuration mistakes. An actual failed-job publication rehearsal is still needed. |
| Packaging | CI selects GoReleaser v2.20.3; a temporary local copy exists outside PATH | Document a repeatable versioned setup for another machine. Verify source and release installs separately. |
| Signing and publication | Cross-build configuration exists | Native runner evidence, signing access, signed artifacts, verified public install channels and rollback drills remain open in PA02–PA04. |

For the planned end user installing a release, the runtime target is one native executable and local repository data. The developer needs Go and a checkout. Forge access, release tooling and signing credentials belong to publishing. A database, cloud account, container engine or model key would add no capability to the first literal quote check.

## A debugging drill already performed

From a clean checkout on Linux, build a temporary debug executable:

    go build -gcflags='all=-N -l' -o /tmp/receipts-debug ./cmd/receipts
    go version -m /tmp/receipts-debug
    gdb -nx -batch -ex 'break main.run' -ex 'run --help' -ex 'bt 2' /tmp/receipts-debug

The breakpoint reached main.run and the next frame was main.main. To reproduce the delivery defect, run the compiled executable with --version redirected to /dev/full and inspect the exit status immediately. Expected operational exit is 1; observed exit was 0. When PA01 is implemented, rerun this drill and its portable failing-writer counterpart. A clean go vet result and a successful compilation did not detect the fault.
