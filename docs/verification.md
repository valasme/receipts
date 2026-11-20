# Limited preview verification

Application source: tag v0.0.1-pre.1, commit b82aa5a3246a82e8fc5ae0f10ed3878f1d8e84fd. Test tools and workflow recipes can advance separately. The build record shipped with the release identifies both revisions and the compiler. [Source checks](https://github.com/valasme/receipts/actions/runs/44786114150) · [Patched release qualification](https://github.com/valasme/receipts/actions/runs/44786692521)

## Published release

GitHub published the immutable, unsigned prerelease at 17:52 UTC on November 20, 2026. Its 13 assets contain six native archives, four Linux packages, the local installer manifests, a build record and a checksum manifest. The public checksum manifest has SHA-256 `010d115251a09ff6575a3aebed68472d26d4a464ebac065cd466de61c19f5e96`. All 12 entries matched after download. GitHub provenance verifies against the release workflow at `e93e9b991f44c4643ac984f40e9096d7c550d7b3`. Apple Developer ID signing, notarization and Windows Authenticode remain open. [Download v0.0.1-pre.1](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.1) · [Installation and verification](release.md)

The prepublication qualification ran the archived executable, CLI contract, storage tests, golden receipt and 60-case corpus on Linux, macOS and Windows, each on amd64 and arm64. A separate consumer run downloaded the public assets, verified the two attestations and repeated the archive tests on all six runners. Linux deb/rpm installations and removals passed on both architectures. Homebrew install, formula test and uninstall passed on both Macs. These used the preview's local formula and packages. [Release qualification](https://github.com/valasme/receipts/actions/runs/44786692521) · [Public install results on Linux and macOS](https://github.com/valasme/receipts/actions/runs/44787463622)

Both Windows consumers installed the public archive through WinGet and Scoop, invoked the installed executable and removed it. WinGet removal used the installed display name, `Receipts Preview`. The Windows ARM64 runner required WinGet provisioning. Scoop used an isolated user directory on each runner. The tagged Go module gives an additional install path outside the checkout. [Public Windows installer results](https://github.com/valasme/receipts/actions/runs/44788408945)

## Decisions made during qualification

| Question | Competing considerations | Decision and evidence |
| --- | --- | --- |
| Can the object reader declare a path absent on a failed lookup? | A missing entry is a useful result. A damaged or truncated tree can hide the entry. | Validate identity and parse the entire bounded tree first. The damaged, missing, duplicate-name and oversized-tree tests exercise the distinction. |
| Should a reviewer have to install Git or grant network access? | Shelling out would delegate pack handling to Git, but it expands the runtime and configuration surface. | Pure Go, bounded read-only support for loose objects and v2-index packs including offset deltas. Return an inconclusive result for unsupported storage. Git independently checks fixture evidence in the test harness. |
| Can the package be released after compiling for six targets? | Cross-builds produced all archives, but Windows rejected an early WinGet manifest. | Exercise exact archives on native machines. Use a three-file WinGet manifest for the two architectures. A failed install job blocks the draft. |
| Is testing minimum Go sufficient for a distributed binary? | Consumers may compile with Go 1.25; a release built with the minimum compiler brought old library advisories into its scan. | Keep compatibility testing. Build distributed binaries from the unchanged source tag with Go 1.27.4 and scan the produced files before promotion. |
| Can an unsigned preview ship? | The owner wants a usable release now, and native signing accounts are unavailable. | Publish only the authorized, explicitly unsigned preview after native package checks. Publish independent GitHub provenance. Keep platform signing and notarization open. |
| Is the GitHub adapter useful enough to enable? | Six adapter contract tests establish important mechanics. They do not measure maintainer time or real comment noise. | Implement and test the adapter with a simulated API, keep both enablement variables off, and retain a separate one-time per-submission consent label. |

## CLI and storage

The process tests check the actual executable, outputs, exit status, quote digest, evidence and line span. A fixed commit made with Git fast-import has an independently pinned blob ID and expected JSON bytes, which include a single trailing LF. The public CLI is exercised with loose and packed objects, offset deltas, changed working and staged files, non-ASCII paths, exact and oversized inputs, and corrupted or missing parents.

A Linux run isolated with unshare -Urn passed both the valid and invalid process cases. A separate unprivileged run checked denied object read permission. A failed output device yielded operational exit 1. The installed binary was also run in a 40-column pseudo-terminal for help and recovery from invalid usage. This is a terminal exercise. VoiceOver, Narrator, Orca, screen magnification and live-rendered GitHub comments still require accessibility review on their actual surfaces.

Go vet, race tests, minimum-Go tests, JSON Schema checks and the two bounded fuzz targets were exercised. The Linux fuzz sessions completed 713,165 delta inputs and 916,455 tree inputs. They found no failing case in those runs. Fuzz throughput is not a measure of functional coverage.

On a Linux amd64 Ryzen 5 5600G, four new CLI processes searched an 8 MiB fixture for a near-matching 64 KiB quote. Wall times were 22.95, 23.95, 23.60 and 24.84 ms. The observed high-water mark across the fixture subprocesses was 30,472 KiB. This is a warm local fixture measurement, not a hard bound for every OS, repository or filesystem. The CLI also has explicit byte and depth budgets and a five-second object-read deadline.

## Ground truth and coverage

The frozen corpus commit is 1240308. All 60 synthetic cases have ground truth defined before evaluation. Three repository families are set aside as a 30-case holdout; each split contains 10 expected results in each verdict class. Git independently opens the committed blob for every decisive result.

| Expected across both splits | Verified | Contradicted | Can't check |
| --- | ---: | ---: | ---: |
| Verified | 20 | 0 | 0 |
| Contradicted | 0 | 20 | 0 |
| Can't check | 0 | 0 | 20 |

60/60 correct, 40/60 decisive, zero skipped. In the holdout, false contradictions were 0/20 claims whose expected verdict was verified or inconclusive. Synthetic cases from six families are a limited sample; this result cannot establish a real-world error rate. The process suite separately replays all three presentation formats and GitHub receipt publication logic is tested independently of the matcher.

## Solo release, support and pilot gates

The Go-install route was tested against the public pinned module. A local rehearsal restored an earlier working starter after running the tagged binary. One person can verify a failed download, identify the checker version, return to an earlier binary and submit a synthetic fixture privately. Credential rotation and native signing-provider recovery remain untested.

The 12-pair timing study is ready in tests/timing_trial.py. Launch it with a new local results filename, the current checker on PATH and a separate terminal for the assigned tasks. It counterbalances manual/assisted order, creates new tasks, includes quote preparation and records actual responses and elapsed time. No human timings have been collected. Live preview and commenting remain off. The broader checklist distinguishes observed behavior from review questions awaiting human evidence or future scope.
