# Readiness review of the Receipts starter

**Historical starter audit.** The publication hold below applied to the starter. The published unsigned preview and its remaining release gates are covered in the [verification record](../verification.md). The baseline reviewed was the complete tree at e12fbb9, including the starter at 324b94a and the subsequent planning diff. The comparison source was the product research, product explanation and distribution brief supplied in the conversation. Market statistics, funding prospects and vendor pricing were background claims, outside this product-conformance audit.

## Standards and repository findings

- **High · publication can outrun validation.** The tag workflow runs its own Linux test step and immediately invokes the publisher. The separate OS matrix has no dependency relationship to publication. A tagged run could publish while a Windows or macOS job fails. The release job has write permission throughout. Require exact-revision validation and a narrowly privileged publisher in PA02.
- **Medium · delivery failure is reported as success.** On the packaged Linux executable, redirecting version output to a full device produced exit 0. The CLI ignores the write result before returning. PA01 owns a failing-writer regression for successful command output.
- **Medium · starter behavior lacks automated assertions.** The package contains no Go test files. CI exercises version invocation without checking the value, help text, streams or invalid-command exit. PA01 defines the contract and PA02 runs it on the release candidate.
- **Medium · offline archive documentation is incomplete.** The Linux archive contains LICENSE, README.md and receipts. The README points to docs/planning/README.md, which the archive omits, and foregrounds source-checkout commands. PA01 covers the extracted user's first run.
- **Medium · channel identity is ambiguous.** Source installation emits “receipts dev”; the tagged GoReleaser build includes the tag version. A consumer using the Go install channel needs a documented way to identify the installed module version. PA03 tests that channel independently.
- **Governance and style.** The glossary, evidence ADR, tracker conventions and triage labels are present. The short CLI has a straightforward command boundary. All three pinned action commits resolved upstream. These checks establish conformance to those conventions only.

## Spec and brief comparison

| Request in the supplied material | Reviewed state | Disposition |
| --- | --- | --- |
| Receipts name, self-hostable CLI, Go, Apache-2.0 | Present in local starter and license. Remote has no source refs at baseline. | Preserve and distribute in PA01–PA04. |
| Evidence per claim, three verdicts, immutable revision, human decides | Explicit contract, examples and ADR. CLI currently exposes help/version. | T01–T04 establish the first checker. |
| Incoming PRs and issues, comments and advisory labels | Read-only GitHub preview and comment publisher are scheduled conditionally. No installable checking Action exists today. Specific label behavior is not committed for the first pilot. | T08–T09. Private reports remain local. |
| Flexible prose input, local/remote pluggable extraction, version ranges, tree-sitter symbol checks, dependency and duplicate checks | Deferred or outside the first checker. The roadmap begins with a manually supplied quotation. | Separate future product decisions. |
| Report-supplied reproduction, sandbox, estimates about real usage | Submitted material stays inert. The plan limits future CI observations to existing results with provenance. | An explicit divergence from the supplied automation concept. |
| PR descriptions versus actual changes, test coverage, existing build status | Quote evidence is the first slice. Full semantic diff and coverage analysis have no implementation ticket. | Describe as broader vision in external copy. |
| HackerOne/PVR imports, Vouch bypass, GitLab, Codeberg, SQLite, private web inbox, SARIF | Outside the committed nine-ticket product backlog. JSON and Markdown export are scoped. | Revisit individually if the first release demonstrates value. |
| Public curl benchmark and named pilot partner | Replaced by independently labeled quote fixtures and a solo timing study; an upstream collaborator is optional. | T06 measures a different task. Its accuracy cannot be compared directly to a report-level benchmark. |
| Six Go builds, three native OS jobs, free release tooling | Six archives rehearsed locally. Native workflow configured. Remote repository had no Actions runs. | PA02 proves enforcement; PA03 records actual native results by target. |
| Source installs, Homebrew, WinGet, Scoop, deb and rpm | Local source install exercised. GoReleaser currently produces tar.gz and zip. Package-manager manifests and feeds are absent. | PA03 owns clean installation evidence for the full set. |
| Platform signing, macOS notarization, immutable GitHub release and authenticity evidence | Checksums generated. Signing and notarization absent from release configuration. Repository immutable releases setting returned false. | PA03–PA04. Document external account or approval dependencies. |
| Independent infrastructure-only pre-alpha | T07 originally depended on T05 and T06, which both need the checker. No GitHub milestone existed. | Added PA01–PA04 under an independent release milestone. |

## Evidence actually obtained

Disposable clones isolated verification from the project and from publication. A snapshot rehearsal and a local tag rehearsal using v0.0.1-pre.1 with publishing skipped both produced six archives. The tagged Linux binary identified itself as 0.0.1-pre.1. The temporary tag existed only in its disposable clone.

| Check | Result |
| --- | --- |
| Local source install, formatting, vet | Passed on Linux amd64 with Go 1.27.4. A second source install, help invocation and vet also passed with the declared minimum Go 1.25.0. |
| Go test | Command succeeded; zero test files. |
| GoReleaser config check and snapshot SHA-256 manifest | Passed, six of six checksums. All six archives contained the platform binary, license and README. |
| Extracted Linux binary | Default invocation, help, short help, version, unknown option and unsupported check command matched expected exits and streams. Output-device failure returned an incorrect success. |
| macOS, Windows, Linux arm64 | Archives built. Native execution, install and removal unverified in this review. |
| GitHub at baseline | Actions enabled. Remote ref listing, release listing and run listing were empty. Source and workflows were local. |
| Plan integrity at baseline | GitHub parent issue matched the local spec. Nine children were open with the documented dependency edges. Inventory had 520 distinct, sequentially numbered, unchecked entries. |
| External distribution | Public tag, binary downloads, package indexes, clean remote install, signing, authenticity verification, native accessibility and rollback remain unproven. |

## What counts as working for pre-alpha

The first public infrastructure milestone uses the real help/version/error CLI. It requires no claim extraction, verdict calculation or report publication. A local rehearsal, a public archive preview and a fully working distribution milestone are three different claims. The release record must identify which one was demonstrated.

PA01 establishes CLI behavior and usable bundled documentation. PA02 proves candidate CI and packaging. PA03 proves native and package-channel installs, including prerequisites that may need an external signing service. PA04 proves that the published assets are the qualified assets and can be recovered or superseded. A staged candidate or isolated feed can exercise PA03 before public promotion; PA04 repeats smoke tests from the final consumer endpoints. Any channel or platform without evidence remains explicitly unverified. A limited archive preview can ship separately; it cannot close the full milestone.

Only planning and tracker records were changed during this review. The discovered defects and release controls remain open implementation work.
