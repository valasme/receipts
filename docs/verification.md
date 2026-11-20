# Limited preview verification

## Corrected unsigned preview v0.0.1-pre.2

GitHub published the immutable prerelease on 2026-11-20 at 19:02 UTC. The tagged source and build workflow both resolve to `57f6601e0c52aaf835f8930ebc2ff81a603f8ffd`. All six native candidate install jobs passed for the exact tag, including the 60-case quotation corpus. The signed build record identifies Go 1.27.4. [Release](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.2) · [Tagged qualification](https://github.com/valasme/receipts/actions/runs/44797012853) · [Public installer jobs](https://github.com/valasme/receipts/actions/runs/44798403802)

All 13 public assets matched GitHub's digests. All 12 files listed in the attested checksum manifest matched the listed hashes. The SHA-256 of the manifest itself is `e6364759df3af594cf05638ac87dfe96cde3a5298180d663c8c12afd15ebb49e`. The manifest and build record were verified against the release workflow and tagged commit. Candidate checks compared the Apache license and third-party notices byte for byte inside the installed archives, Debian and RPM packages, and through the installed CLI. The manifest drives the same native install suite for the public downloads. [Install and notice locations](release.md)

### Upgrade, rollback and removal

All 22 installer and native target combinations completed the transition from v0.0.1-pre.1 to v0.0.1-pre.2, back to v0.0.1-pre.1, and through removal. Each step checked the exact version, ran help with outbound network blocked, and replayed the frozen Git fixture byte for byte. The test ran from a temporary directory outside the source checkout. [Public transition matrix](https://github.com/valasme/receipts/actions/runs/44800250124) · [Workflow revision](https://github.com/valasme/receipts/commit/13cc444)

| Channel | Linux amd64 | Linux arm64 | macOS Intel | macOS Apple Silicon | Windows x64 | Windows ARM64 | Transition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GitHub archive | Pass | Pass | Pass | Pass | Pass | Pass | Replace the extracted directory |
| Pinned Go module | Pass | Pass | Pass | Pass | Pass | Pass | Replace the executable with the named module tag |
| Debian | Pass | Pass | — | — | — | — | Install each pinned package in place with dpkg |
| RPM | Pass | Pass | — | — | — | — | RPM update and explicit older-package restore in an isolated root |
| Homebrew | — | — | Pass | Pass | — | — | Replace via uninstall and install with the named local formula |
| WinGet | — | — | — | — | Pass | Pass | Replace via uninstall and install with the named local manifest |
| Scoop | — | — | — | — | Pass | Pass | Replace via uninstall and install with the named local manifest |

The tagged source commits, signed build records and signed checksum manifests were verified for both releases. The test matched 12 manifest entries per version. It compared installed binary bytes to the exact native archive, or inspected the pinned module identity and GOOS/GOARCH from Go build metadata. Go reports the version with a leading `v`. Packaged builds omit the leading `v`. Linux used a network namespace, macOS a deny-network sandbox and Windows a per-executable active firewall rule. The restored executable was removed through the same installer and its installed path checked. Stable package indexes and unattended updates remain outside this qualification.

### Publication recovery exercises

The immutable v0.0.1-pre.2 superseded v0.0.1-pre.1 to correct bundled license notices. Its six native qualification jobs and six postpublication install jobs passed. GitHub initially created an empty draft before it became visible to the staging job. Attempt 2 resumed with the same qualification artifact and the same source commit, `57f6601e0c52aaf835f8930ebc2ff81a603f8ffd`. Both tags and immutable releases remained available when checked. [Failed staging attempt](https://github.com/valasme/receipts/actions/runs/44797012853/attempts/1) · [Recovered staging attempt](https://github.com/valasme/receipts/actions/runs/44797012853/attempts/2) · [Public consumer run](https://github.com/valasme/receipts/actions/runs/44798403802)

The sole-operator rehearsal took all 13 verified v0.0.1-pre.2 assets through the staging code with a simulated GitHub release state. The first upload was recorded on the simulated service and its response was lost. A retry accepted the one matching asset and uploaded the 12 missing ones. A complete publication was a no-op. Substituting an incorrect remote digest stopped staging before a write. The response-loss case is now replayable in `python -m unittest discover -s packaging -v`. [Recovery instructions](release.md#recover-an-interrupted-or-superseded-preview)

**Simulated withdrawal notice, exercise only.** Withdraw v0.0.1-pre.1 from install recommendations because its Linux packages omit license notices. The scenario concerns packaging. For recovery, install v0.0.1-pre.2 from the immutable GitHub release after verifying the manifest attestation and asset digest. Confirm the installed version and help, then replay a representative receipt. Use the raw archive if a preview installer is unavailable. Share only a synthetic fixture in public support. [Verified replacement](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.2)

On Linux amd64, the rehearsal identified the installed pre.1 version, rejected a truncated pre.2 download against the attested checksum, installed the genuine archive and confirmed pre.2 help offline and the same frozen fixture. The receipt replay passed on both versions. The live repository's private reporting endpoint was enabled. No real withdrawal notice was posted or release state changed. Signing-provider recovery remains in [#15](https://github.com/valasme/receipts/issues/15).

## Earlier qualification for v0.0.1-pre.1

Application source: tag v0.0.1-pre.1, commit b82aa5a3246a82e8fc5ae0f10ed3878f1d8e84fd. Test tools and workflow recipes can advance separately. The build record shipped with the release identifies both revisions and the compiler. [Source checks](https://github.com/valasme/receipts/actions/runs/44786114150) · [Patched release qualification](https://github.com/valasme/receipts/actions/runs/44786692521)

## First public preview

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

The original 60-case corpus was frozen at `1240308`. Its ten inconclusive holdout rows duplicate development fixtures and are reported as shared controls. The replacement holdout supplies ten predeclared cases with unique paths and quotations. They cover invalid UTF-8, missing blobs, non-tree ancestors, gitlinks, and blobs above the read budget. Git builds the pinned fixtures and independently opens every decisive blob for corroboration.

`python tests/evaluate.py <receipts>` reports confusion matrices for development, holdout, and shared controls even if an observation fails. The local replay for [the audit qualification ticket](https://github.com/valasme/receipts/issues/28) observed 30/30 correct and 20/30 decisive in each evaluated split, plus 10/10 shared controls. The holdout produced zero false contradictions among 20 eligible claims. These are synthetic examples from six families.

On Linux, run `python tests/benchmark.py <receipts> --runs 4` with Git and GNU coreutils available. The harness creates a fixed 8 MiB loose blob and searches for a 64 KiB near match. It reports wall time and the per-invocation Linux peak RSS. It requests page-cache eviction for the fixture object files before each first sample and runs the paired warm sample immediately afterward. The eviction request is advisory. The kernel, binary and filesystem metadata can stay cached. Retain the JSON report with the checker and host versions when comparing runs.

## Solo release, support and pilot gates

The Go-install route was tested against the public pinned module. A local rehearsal restored an earlier working starter after running the tagged binary. One person can verify a failed download, identify the checker version, return to an earlier binary and submit a synthetic fixture privately. Credential rotation and native signing-provider recovery remain untested.

### Human timing and pilot decision

One human evaluator completed 12 fresh paired tasks using the counterbalanced timing harness. Six pairs ran manual first and six ran Receipts first. The timed window started when the task appeared and ended when the evaluator entered a verdict. The protocol includes finding the revision, preparing the quote and reading the result.

| Method | Correct | Median elapsed time | False contradictions |
| --- | ---: | ---: | ---: |
| Manual | 4/12 | 1.84 s | 0/4 |
| Receipts | 4/12 | 1.43 s | 0/4 |

The median of the 12 paired savings was **21.4%**, below the 25% expansion gate. Receipts was faster in 7/12 pairs. Both methods were answered Verified on every task, including the eight expected contradictions per method. These measurements provide weak evidence of completed review effort. The historical timing file captured only the entered verdict and elapsed time. The revised harness independently assigns balanced verdicts to both methods and includes evidence entry in the measured review. It records the installed version, observed revision and blob, plus completed, discarded and aborted tasks in an atomic private report. A fresh human trial is still required. A single evaluator on synthetic paired tasks is vulnerable to familiarity, recall and procedure effects. The working file stays private.

**Decision: stop pilot work for this preview.** The 60-case correctness run remains a separate gate with 60/60 correct and 40/40 decisive cases replayed. No live read-only preview or publisher was enabled. Revisit the pilot only after a fresh qualified timing result. [Human timing](https://github.com/valasme/receipts/issues/7) · [Read-only pilot](https://github.com/valasme/receipts/issues/9) · [Comment pilot](https://github.com/valasme/receipts/issues/10)


### Readiness before another release

A maintainer-style review used the installed Linux amd64 preview to verify the support instructions quoted from the tagged README. Supplying the tag name returned exit 2 and a short diagnostic on stderr. The annotated tag's object ID was also rejected. Resolving the tag to the commit with `git rev-parse 'v0.0.1-pre.2^{commit}'` and saving the exact line with its final LF produced a Verified receipt with the reported path, line, commit and blob. The main preparation steps were resolving the commit and writing the exact quote. The receipt pinpointed where to inspect the original text.

The success and invocation-error outputs were exercised in a 40-column terminal and converted to speech independently with eSpeak NG. Speech synthesis read the linear CLI text and produced audio for both flows. Interactive screen-reader navigation and a listener's comprehension remain untested. VoiceOver, Narrator and Orca testing on their respective terminals is still open.

**Recommendation: keep v0.0.1-pre.2 as the current unsigned preview.** Improve the instructions for turning a revision and quote into a claim, then observe ordinary reviews and repeat the paired test with independent task variants, explicit evidence capture and the installed version recorded. Include an accessibility pass with real users or assistive technology on the supported platforms. The current result leaves ordinary maintainer time savings unproven. Keep the optional GitHub pilots off until the evidence qualifies them. Native signing work starts only on the owner's v1 decision.

The demonstrated product is a local, exact-quotation CLI with deterministic, replayable evidence. Broader intake, prose extraction, symbol and version-range checks, CI-result interpretation, duplicate detection, other forges and a self-hosted inbox require their own scope decisions. Report-supplied programs and reproduction instructions stay inert. [Parent plan](https://github.com/valasme/receipts/issues/1) · [Signing decision](adr/0002-defer-native-signing-until-v1.md)
