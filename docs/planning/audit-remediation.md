# Receipts audit remediation

The audit covered 123 findings against `c53e1c8`. The independent reviewers examined `fb34f73`, and the findings below include their corrections at `2be2e02`. [Specification and seven child tickets](https://github.com/valasme/receipts/issues/23) · [Integration pull request](https://github.com/valasme/receipts/pull/31)

The owner selected literal source lines for proposals and upward repository discovery when `--repo` is omitted. An explicit path accepts a clone root or bare repository. Linked worktrees get an actionable unsupported result. Renderers state the exact Git claim separately from the submission context. Existing quotation JSON keeps its layout. Choose `--format json-evidence` to opt in to the additional witnesses for single quotations and batches.

## Verification

The combined branch passed Go vet, race checks, the Go 1.25.0 source qualification command, six fuzz targets and the process suites. The quote golden test covers both a verified and an inconclusive receipt, including the default batch envelope and opt-in evidence. Each evaluated split recorded 30/30 correct and 20/30 decisive receipts, plus 10/10 shared controls. No false contradiction occurred among the 20 eligible holdout cases.

The local snapshot at `2be2e02` built all six release targets with Go 1.27.4. Pinned govulncheck reported no vulnerabilities in any of the six binaries. The Linux amd64 archive passed offline receipt replay, saved claims and both kinds of review. A separate read-only run used the published v0.0.1-pre.2 asset and attestation pins and rejected a mismatched tag. Staging and promotion used a simulated GitHub adapter. The snapshot's Linux amd64 Debian and RPM packages also passed real package-manager install and removal in disposable Debian 12 and UBI 9 userspaces. Both installed executables and notice files matched the archive. Each installed executable produced the frozen receipt inside a network namespace with Git off PATH. The Debian slim userspace's documentation-exclusion policy was disabled inside the disposable root for the notice check. [Local CI parity](maintainer-checklist.md#local-ci-parity) · [Pinned installer recipe](../release.md#verify-and-install-a-pinned-release)

At `5a7f4c5`, all 22 native published-preview transitions passed. The matrix covered both Linux architectures, both macOS architectures, Windows x64 and Windows ARM64. On Windows, the firewall harness captured the checker's stdout directly to a file, preserving the frozen receipt bytes. Both Windows fresh-install jobs also passed. The corrected branch snapshot passed archived-executable and installer qualification on all six native targets. Its draft and promotion jobs were skipped. [Native snapshot](https://github.com/valasme/receipts/actions/runs/44829264954) [Native transition matrix](https://github.com/valasme/receipts/actions/runs/44829265486) · [Windows fresh installs](https://github.com/valasme/receipts/actions/runs/44828928660)

## Verification still open

- **Human review.** Run a fresh 12-pair timing trial with an evaluator. Exercise terminal output with interactive assistive technology on the supported systems. [Timing, RCP-025](https://github.com/valasme/receipts/issues/28) · [Accessibility, RCP-036](https://github.com/valasme/receipts/issues/26)
- **Hosted release.** An owner-authorized candidate must demonstrate staging and promotion concurrency and the automatic postpromotion installer workflow. The source matrix retains every leg. A deliberate hosted failure drill remains open. [Release qualification](https://github.com/valasme/receipts/issues/25) · [Consumer qualification](https://github.com/valasme/receipts/issues/27)
- **Parked work.** A file-change or review serialization contract needs a real consumer. The optional pilot remains off after the failed human timing gate. Native signing awaits the owner's v1 decision. [CLI contract](https://github.com/valasme/receipts/issues/26) · [Pilot decision](../verification.md#human-timing-and-pilot-decision) · [Signing decision](../adr/0002-defer-native-signing-until-v1.md)

## Standards review

The independent review reported three documented gaps and one maintainability judgment. All four received changes.

- Git LFS v1 aliases and extension spellings accepted by the LFS decoder now remain inconclusive. Git fixtures prove the distinction between a pointer and prose containing its marker. [Git LFS specification](https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md#the-pointer) · [Git LFS decoder](https://github.com/git-lfs/git-lfs/blob/main/lfs/pointer.go)
- Stale-receipt reconciliation compares the digest in the existing receipt with the latest source. The fake covers consecutive updates and repeated checker failure.
- The local diagnostic recipe lists all six fuzz targets and the four schema suites run by CI.
- The quote and file-change modules share commit-failure reason mapping.

## Spec review

The independent review reported five implementation gaps, each with a correction.

- Zero-padded and overflowing commit timestamps can no longer support a decisive verdict. The corrections were checked against Git's strict validation.
- Ordinary nested `HEAD` and `config` files no longer interrupt discovery. Supplying a clone's internal Git directory reports the accepted repository choices.
- A failed preview can retire a stale comment when the publisher is enabled. That reconciliation path cannot create a new comment. The adapter remains disabled.
- Both timing arms receive independent verdict assignments and time evidence collection. An incorrect or incomplete trial cannot qualify.
- Public Go qualification verifies the module's origin commit against the authenticated release pin before installing through either route.

## Retrospective

Record audit dispositions and actual evidence in the tracker and planning index so they survive scratch-directory cleanup. The shared source verification and Git fixture helpers give maintainers reproducible commands for the next run. Keep human, native installer and hosted mutations identified as separate verification steps so a passing source test cannot stand in for them.

## Finding dispositions

| ID | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| RCP-001 | A malformed commit can produce a decisive receipt | Verified | Malformed author, committer and header sequencing leave the claim inconclusive. Optional headers and a real shallow clone passed. |
| RCP-002 | Regular-file enforcement applies to a different filesystem operation from the read | Verified on POSIX | Open-handle type checks reject directory and FIFO objects. A controlled Unix test swaps a regular object for a pipe between lookup and open. |
| RCP-003 | A closed stdout pipe bypasses the promised output error for check and batch | Verified | The POSIX broken-pipe replay checks help, licenses, check and batch for exit 1. |
| RCP-004 | SIGINT cannot interrupt check output blocked by pipe backpressure | Verified | The process tests interrupt a blocked output pipe and assert exit 130. |
| RCP-005 | Packed tree traversal repeatedly charges the same index against the byte budget | Verified | A nested lookup in a real Git pack reused an index larger than 3 MiB without exhausting the logical byte budget. |
| RCP-006 | A failed pack candidate can mask a usable copy of the object | Verified | Redundant damaged or unreadable pack candidates before and after a valid copy still returned verified evidence. |
| RCP-007 | Inconclusive quote receipts drop available Git evidence | Verified | Text and opt-in JSON preserve the tree witness and distinguish tree entry references from independently read blobs. Default JSON passed the expanded golden test. |
| RCP-008 | A text file that starts with the LFS version string is treated as a pointer | Verified | Real Git fixtures distinguish LFS pointer structure from prose sharing its marker. |
| RCP-009 | Drive-prefix guard rejects literal Git names with a non-letter before the colon | Verified | CLI tests accept a literal colon after a non-letter and reject a drive-prefixed input. |
| RCP-010 | Receipt schema validation leaves core evidence invariants unchecked | Verified | Schema validation rejects incompatible evidence. The semantic test rejects inverted lines and a mismatched observed commit. |
| RCP-011 | Object-format diagnosis relies on input length instead of repository format | Verified | The checker diagnoses SHA-256 from local metadata. Revision syntax is validated independently. |
| RCP-012 | Batch treats an invalid shared commit object as an item error | Verified | CLI tests reject known non-commit IDs at the batch envelope and return ordered unresolved receipts for unavailable evidence. |
| RCP-013 | Input diagnostics conflate failed reads and exceeded size limits | Verified | The CLI rejects unreadable input separately from raw and normalized size failures. |
| RCP-014 | The alternate-agent walkthrough fails for a valid reordered proposal | Verified | The worked replay passed with its quotation proposal reordered. |
| RCP-015 | The spec's current-repository default fails from a nested directory | Verified | Omitting --repo from a nested directory found its clone. An explicit non-root directory did not search upward. |
| RCP-016 | Resolve the release revision once for validation, packaging and install | Verified | Resolve a fully qualified tag once. A same-name branch fixture selected the tag, and a moved tag blocked simulated promotion. |
| RCP-017 | Start the public consumer matrix after workflow-driven publication | Hosted release verification open | Promotion invokes the public installer matrix with the reviewed pins. The workflow passed actionlint. |
| RCP-018 | Require every bundle file used by consumers to appear in the authenticated manifest | Verified | Candidate, public and transition consumers share exact manifest membership. Fakes reject missing, extra, duplicate and changed assets. |
| RCP-019 | Exercise saved claims and both review claim kinds using the archived executable | Verified on all six targets | The pinned snapshot archives ran saved claims and both review kinds on Linux, macOS and Windows for both supported architectures. |
| RCP-020 | Verify the Unix archive preserves executable permissions | Verified | Synthetic archives lacking Unix execute permission failed, and all six candidate archive layouts passed. |
| RCP-021 | Handle or document GitHub's interrupted-upload placeholder | Recovery documented and exercised | The fake identified the zero-byte starter asset by draft and asset ID. The retry succeeded after simulated removal of that asset. |
| RCP-022 | Retire an outdated public receipt even when the checker fails | Verified with simulated adapter | Pilot tests retire a changed-input receipt on checker failure and preserve a same-digest receipt. |
| RCP-023 | Use genuinely held-out inconclusive fixtures | Verified | Ten overlapping legacy controls are reported separately. The 30-case holdout uses independently specified replacement cases and passed. |
| RCP-024 | Emit the evaluation matrix even when the checker disagrees with expected labels | Verified | An injected wrong verdict and an injected failure produced a nonzero result and retained subsequent matrices. |
| RCP-025 | Qualify timing pairs using completed review work and evidence | Human trial open | The harness records completed tasks, installed version, pinned evidence and qualifying accuracy. It rejected a simulated fast, inaccurate trial. |
| RCP-026 | Record what the inventory checks actually established | Verified | The planning inventory links the native transition report and records the timing, accessibility and pilot dispositions. |
| RCP-027 | Give each command its own readable help | Verified | Go CLI tests check distinct help for check and review. |
| RCP-028 | Give actionable format and repository diagnostics | Verified | CLI tests exercise format, revision and repository argument diagnostics. |
| RCP-029 | Normalize the review header commit | Verified | The process review suite checks the canonical lowercase head. |
| RCP-030 | Make the checked file-change proposition explicit | Verified | File-change process tests check Claim checked and the distinct submission context. |
| RCP-031 | Choose how citations inside Markdown context should behave | Decision verified | The owner chose literal lines. The process suite admits the same span at top level, inside a longer fence and inside a comment. |
| RCP-032 | Support or explain review's final-newline restriction | Verified | Raw check accepts a no-final-LF quotation. The review command reports the fence rule. |
| RCP-033 | Report path syntax the citation grammar cannot represent | Verified | A real backtick path works through raw check and yields an actionable proposal diagnostic. |
| RCP-034 | Require comparison before starting evidence lookup | Verified | A file-change proposal without a comparison exits before evidence lookup. |
| RCP-035 | Include comparison identity in review-level scope | Verified | The mixed review shows both pins and a quote-only review identifies an unused comparison. |
| RCP-036 | Make review output navigable in narrow terminals | Assistive verification open | The mixed review test reconstructs exact text from continuation lines at up to 40 characters. Interactive screen reader checks remain open. |
| RCP-037 | Point to the colliding submission spans | Verified | An overlap across different proposal arrays identifies both entries and ranges. |
| RCP-038 | Clarify review proposal format compatibility | Verified | The tested v1 schema preserves omitted versions and the CLI rejects an unsupported version. |
| RCP-039 | Publish schemas for saved claim and batch input | Verified | Saved-claim and batch input schemas validate documented input and reject extension fields. CLI process cases cover independently invalid input. |
| RCP-040 | Specify the batch result envelope | Verified | The batch result schema rejects a result with both branches and a result with neither. |
| RCP-041 | Identify invalid JSON fields without echoing them | Verified | CLI tests check malformed, unknown, duplicate and wrong-type fields with sanitized diagnostics. |
| RCP-042 | Report a duplicated known option precisely | Verified | All known check and review options are duplicated in Go tests with redaction assertions. |
| RCP-043 | Resolve option syntax help discoverability | Verified | Go tests cover help alone and mixed valid and invalid options. Command help documents syntax. |
| RCP-044 | Explain size caps per input | Verified | Process tests cross each structured input limit independently and assert the label and byte count. |
| RCP-045 | Give blocked input an explicit lifecycle | Verified on POSIX | Named nonregular input returns exit 2. Both raw and saved blocked stdin return exit 130 in a process test. |
| RCP-046 | Account for the full admitted command budget | Verified | The documented five-second evidence deadline begins after input. A delayed-stdin process test and time-limit tests exercise the distinct admitted stages. |
| RCP-047 | Name the resource that hit its budget | Verified | The evidence suite checks distinct limit explanations in text and opt-in JSON with stable resource_limit reason codes. |
| RCP-048 | Bound cumulative filesystem and enumeration work explicitly | Verified | Batch fixtures cover filesystem operations, cumulative raw and decoded bytes, directory scans and tree entries. |
| RCP-049 | Reuse identical blob observations in a file comparison | Verified | A file-change fixture reuses the already verified blob for identical entry object IDs under the shared budget. |
| RCP-050 | Explain why unchanged and absent cases contradict the claim | Verified | File-change CLI tests distinguish unchanged files from absence at both commits. |
| RCP-051 | Version the file-change interpretation | Verified | File-change output includes a comparison rule and checker version. Fixture tests check both. |
| RCP-052 | Preserve file-change receipts in a machine-readable contract | Parked by decision | File-change and review serialization await a real consumer and a versioned opt-in contract. Quotation JSON passed the frozen golden comparison. |
| RCP-053 | Make the observed commit legible in text | Verified | Text identifies the observed commit separately from the request where evidence supplies it. |
| RCP-054 | Show the full location of an absent component | Verified | Repeated path-component fixtures confirm the complete missing prefix in text and opt-in JSON. |
| RCP-055 | Render a single matching line as singular | Verified | One matched line uses singular text while the original JSON line range stays unchanged. |
| RCP-056 | Delimit path whitespace in the human receipt | Verified | A real Git entry with leading and trailing whitespace is delimited in the human receipt. |
| RCP-057 | Define bare and linked worktree discovery explicitly | Decision verified | Real linked and separate Git-directory fixtures produce actionable unsupported results. Bare and clone roots pass. |
| RCP-058 | Differentiate no repository from inaccessible metadata | Verified | Tests distinguish absent root, inaccessible metadata and unavailable object directory without absolute path disclosure. |
| RCP-059 | Align hashed commit tree references with canonical encoding | Verified | Commit framing requires canonical lowercase tree identity before traversal. |
| RCP-060 | Count pack index candidates separately from irrelevant directory entries | Verified | Independent pack index and total-record thresholds are exercised with irrelevant pack companions. |
| RCP-061 | Distinguish unsupported storage representation from unavailable objects | Verified | Alternate storage, linked worktrees, reference deltas and old pack index formats are distinct from missing objects. |
| RCP-062 | Strengthen the tree fuzz oracle | Verified | The lookup fuzz target checks independent entry facts and malformed tree witnesses. |
| RCP-063 | Strengthen the delta fuzz oracle | Verified | The delta fuzz target checks decoded bytes against a generated delta oracle. |
| RCP-064 | Exercise object framing parsers through dedicated fuzz entry points | Verified | Commit, loose-object and pack-index framing have bounded fuzz targets in the diagnostics workflow. |
| RCP-065 | Cover JSON exactness with round-trip property tests | Verified | FuzzSavedQuotationMatchesRaw compares saved JSON and raw input outcomes byte for byte. |
| RCP-066 | State the receipt policy for extension keys | Verified | Schema tests accept extension members and reject misspelled required keys. |
| RCP-067 | Verify file-change evidence in the worked example | Verified | The file-change replay checks both commit, tree, blob and mode observations against Git. |
| RCP-068 | Keep example logic specific to the supplied proposal | Verified | Both the captured proposal and a well-formed subset replay against the bundled submission. |
| RCP-069 | Serialize staging and promotion for one release identity | Hosted release verification open | Both mutations share per-tag concurrency. Simulated competing candidates and retries preserved the first draft. |
| RCP-070 | Bind approval to the candidate that was reviewed | Verified with simulated adapter | Promotion requires the reviewed draft ID and manifest SHA-256. Wrong approval is rejected before any release mutation. |
| RCP-071 | Recheck the complete remote asset set after uploads | Verified with simulated adapter | Incomplete uploads and changes after upload are rejected by full remote re-observation. |
| RCP-072 | Read release assets through an explicit paginated adapter | Verified with simulated adapter | Paginated release inventory detects a trailing or duplicate remote asset. |
| RCP-073 | Bound external command waits during release recovery | Verified with simulated adapter | Bounded list and upload operations report the operation that timed out. |
| RCP-074 | Validate the candidate bundle contract at the staging seam | Verified | Invalid candidates failed bundle verification before any fake GitHub write. |
| RCP-075 | Make bundle construction atomic | Verified | An interrupted copy left no final directory and preparation could be retried. |
| RCP-076 | Validate manifest grammar and duplicate names | Verified | Strict manifest syntax and duplicate filename tests reject invalid checksums. |
| RCP-077 | Quote the Homebrew path when testing an installed binary | Verified on both macOS targets | Native Homebrew passed install, upgrade, rollback and removal on Apple Silicon and Intel. A separate formula test exercised a prefix containing spaces. |
| RCP-078 | Test release-manifest generation from a synthetic bundle | Verified | Synthetic preparation produced byte-identical installer references and manifest on repeated runs. |
| RCP-079 | Generate the full manifest in one implementation | Verified | One preparation path generates the complete manifest, including the build record. |
| RCP-080 | Bind the recorded compiler to binary build metadata | Verified | A real Go 1.25.0 target executable substituted into a Go 1.27.4 candidate failed the compiler pin. |
| RCP-081 | Require the vulnerability-scan target matrix explicitly | Verified | The scan collector rejects incomplete or duplicate targets. A real govulncheck binary scan succeeded for all six locally packaged targets. |
| RCP-082 | Exercise the default Go install route separately | Verified on Linux amd64 | Default-proxy and direct Go installs matched the published tag's attested commit, reported their installed identity and replayed the frozen offline receipt. |
| RCP-083 | Isolate Go installations in a job-specific GOBIN | Verified | Go routes use isolated binary and module directories. The isolation test preserved an existing installation. |
| RCP-084 | Prove the actual package-installed binaries match the qualified archive | Verified | Native installer checks compared the actual installed executable with the qualified archive. The source-install routes checked the authenticated Go module origin commit. |
| RCP-085 | Check RPM package architecture independently | Verified on Linux | Native RPM tests qualified both x86_64 and aarch64 packages. The wrong-header fixture was rejected. |
| RCP-086 | Exercise the Scoop command shim end to end | Verified on both Windows targets | Scoop installed and exercised the shim end to end on x64 and ARM64, including upgrade, rollback and removal. |
| RCP-087 | Ensure native teardown runs after a failed phase | Verified | Injecting a failure in upgrade preserved the original error through cleanup. The Linux archive and Go transition exercises removed the installed binary. |
| RCP-088 | Run an actual receipt while networking is disabled | Verified on all six targets | The native transition matrix replayed the frozen receipt with networking disabled and Git off PATH. |
| RCP-089 | Validate transition arguments and ordering explicitly | Verified | Missing, stable and reversed transition tags failed the transition argument tests. |
| RCP-090 | Check removal of package-owned notices as part of transitions | Verified | The native transition matrix passed removal checks for executables and package-owned notices across all 22 channel and target combinations. |
| RCP-091 | Bound installed executable checks | Verified | The installed executable helper reports its labeled timeout for a blocked child. |
| RCP-092 | Enforce the documented workflow lint gate | Verified | The pinned actionlint job rejects invalid workflow syntax. The integrated workflows passed locally. |
| RCP-093 | Retain failures for all native source targets | Hosted failure drill open | Native jobs use fail-fast false. All matrix results stay visible when GitHub finishes the jobs. |
| RCP-094 | Provide one fully pinned consumer verification recipe | Verified against published preview | The documented Linux recipe fetched the published bundle, verified both attestations and 12 asset hashes, checked the installed version and rejected a different tag. |
| RCP-095 | Give contributors a reproducible CI parity command | Verified | A clean Linux checkout passed the shared minimum-Go source command. The diagnostics guide lists the same tests as CI. |
| RCP-096 | Warn that review previews include submission text | Verified | The CLI guide identifies submission text in review output and the exposure before sharing. |
| RCP-097 | Correct the debugging entry-point pointer | Verified | The debugging checklist points to the Go CLI and checker paths. |
| RCP-098 | Separate the starter snapshot from the current contract | Verified | The original plan labels the historical starter and points to CLI, schemas and verification. |
| RCP-099 | Lead with both implemented claim kinds | Verified | The introduction distinguishes installed quotation checks from the development preview for both claim kinds. |
| RCP-100 | Record the PR sample as a replayable observation | Verified | Replayed the 15 selected PRs from the creation window. The observe-date record accounts for a tie and pins all four positive observations and eight paths. |
| RCP-101 | Isolate Git fixture environment across all process tests | Verified | The process fixtures use isolated Git settings. Deliberately contaminated GIT_DIR, GIT_WORK_TREE and Git config did not alter the acceptance run. |
| RCP-102 | Make the pack test deterministic across Git versions | Verified | The depth test generates and independently checks a deterministic offset-delta chain. Git gc serves as a separate-interop replay. |
| RCP-103 | Report permission-case eligibility separately | Verified | The edge suite passed as an unprivileged user and identified the ineligible privilege test in a mapped-root namespace. |
| RCP-104 | Bound Git subprocesses across the core process fixtures | Verified | Fixture subprocesses use a deadline and diagnostics name the fixture and Git command. Failure injection checked the deadline path. |
| RCP-105 | Preserve private timing evidence through interruption | Verified | A failed atomic write preserved the prior report byte for byte and POSIX mode 0600. |
| RCP-106 | Distinguish mistyped responses from completed verdicts | Verified | The trial distinguishes discarded answers and incomplete pairs. An interrupted trial retained its observation in a private report. |
| RCP-107 | Add a reproducible cold-cache and memory benchmark harness | Verified on Linux | Four eviction-requested and warm benchmark pairs completed and recorded wall time, per-process peak RSS, checker and fixture identity. |
| RCP-108 | Key pilot reconciliation on canonical submission identity | Verified with simulated adapter | Only canonical decimal numbers enter the publisher concurrency group. Tests reject aliases, signs and non-ASCII numerals. |
| RCP-109 | Bind pilot claims to one consistent submission observation | Verified with simulated adapter | PR body and head come from one observation. The preview discards a receipt when the observation changes. |
| RCP-110 | Align pilot JSON admission with exact saved-claim semantics | Verified with simulated adapter | Duplicate keys and lone surrogate escapes fail admission. The checker uses the saved claim interface. |
| RCP-111 | Distinguish exactly 400 comments from a partial scan | Verified with simulated adapter | Tests distinguish 399, 400 and 401 comment rows. |
| RCP-112 | Separate unavailable repository objects from unavailable fork refs | Decision verified | The disabled pilot explicitly scopes PRs to branches from the demo repository. Simulated fork input produces a user-facing explanation without invoking the checker. |
| RCP-113 | Record the current evidence gate for disabled pilot features | Parked by decision | The pilot guide links the failed timing result and the fresh-trial conditions for enablement. |
| RCP-114 | Exercise advertised bare repository support | Verified locally | Loose and packed bare repository receipts matched clone bytes on Linux. The native source matrix runs the same fixture. |
| RCP-115 | Verify the installed checker without Git on PATH | Verified on Linux amd64 | The installed checker replayed the frozen receipt with an empty PATH and network access disabled. |
| RCP-116 | Test that replace refs do not alter pinned evidence | Verified | Real replace refs did not change the pinned observation. |
| RCP-117 | Assert BOM and Unicode composition matching rules | Verified | Git fixtures assert BOM significance and Unicode composition exactness. |
| RCP-118 | Exercise review entry limits across all collections | Verified | Mixed proposals with 16 entries complete and with 17 entries exit 2 before preview. |
| RCP-119 | Assert raw quote receipt and saved claim parity under cancellation | Verified on POSIX | Raw and saved checks interrupt blocked stdin. A batch interrupts mid-delivery and cannot be parsed as a complete document. |
| RCP-120 | Clarify Windows-only filtering for transition dispatch | Verified | The Windows-only filter is scoped to fresh installs. The documented transition matrix remains independent. |
| RCP-121 | Record Go toolchain identity in transition evidence | Verified | The transition records compiler and module identity. Go 1.25.0 and 1.27.4 were distinguished in local evidence. |
| RCP-122 | Verify archive entries are unique and of the expected kind | Verified | Duplicate archive entries and a symlink replacing the executable were rejected. |
| RCP-123 | Make the dedicated minimum-Go test pin visible | Verified | The minimum-Go workflow logs the exact Go 1.25.0 selection and rejects a different compiler. |
