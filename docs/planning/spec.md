# Receipts v0.1 product and engineering plan

## Problem and first outcome

A maintainer reads “this file contains this code,” pauses review, switches revisions, searches, then tries to explain what they saw. A contributor can do the same work before submitting. Give both people the same local answer and enough information to repeat it. The launch question is whether the receipt saves a reader a trip through Git while preserving the meaning of the original claim. Market-size figures, vendor roadmaps and grant availability are unnecessary assumptions for this decision.

The starting checkout has a help/version CLI, release configuration and CI configuration. All commands, receipts, budgets and acceptance results below describe future work. One person can deliver the local release, entirely offline after installation, without a collaborator, design reviewer, external pilot, paid account or API key.

## User stories

1. As a contributor, I can check a quote before sharing a report, so I can correct the cited revision.
2. As a maintainer, I can check a report against a historical commit while keeping my current edits.
3. As a reader, I can see the precise proposition checked so a wrong citation never decides the merits of the report.
4. As a reviewer, I can find the matching lines in the immutable source.
5. As a reporter, I can distinguish an absent quotation from evidence the checker could not inspect.
6. As a Windows user, I can supply a multiline quote without shell-specific escaping.
7. As a screen-reader user, I can hear the verdict, location and next action in order.
8. As a private maintainer, I can use a local path without sending content or usage events elsewhere.
9. As an integrator, I can parse a versioned receipt even when the verdict is inconclusive.
10. As a contributor whose claim was contradicted, I can rerun it with corrected input and retain both receipts.
11. As the sole operator, I can reproduce an error from a redacted fixture and diagnose a bad release.
12. As a prospective adopter, I can see accuracy, unsupported cases and timing on previously unseen examples.
13. As an opted-in GitHub maintainer, I can preview a comment and disable publication independently of local checking.
14. As a casual reader, I can tell when an edited submission makes an earlier receipt stale.

## Proposed interaction

From a local clone, run `receipts check --repo . --rev <full-commit-id> --path src/example.go --quote-file excerpt.txt`. The quote file designates explicit user input. Use `--quote-file -` for stdin. Omit `--repo` to select the current repository. Require the revision and repository-root-relative path. Offer `--format text|json|markdown`; default to text. Read the supplied quote literally, including any final newline. Help includes creating a quote file in PowerShell and POSIX shells. A running check never prompts.

Example of proposed text output on a synthetic file:

    Verified · exact source quote
    src/example.go · lines 8–9 · first match
    Commit 0123456789abcdef0123456789abcdef01234567
    Blob 1111111111111111111111111111111111111111
    Compared the supplied quote with the committed file. CRLF and LF count as the same line ending.

A mismatch reads “Contradicted · exact source quote”, then “The complete file at this commit contains no matching quotation.” Follow with “Check the revision, file path and final newline.” An unavailable object reads “Can't check · revision unavailable”, then “Provide a local clone containing this commit and rerun.” Use plain text labels. Print a receipt once. Human-readable evidence defaults to path, commit, range and reason. Omit raw source, absolute local paths, reporter identity and full quote from shared output. Include the observed blob ID in the detailed human receipt. Supply the original quote alongside the receipt when independent replay is needed and disclosure is appropriate.

## Decision contract

| Input at the named revision | Verdict or outcome | Evidence the reader receives |
| --- | --- | --- |
| Supported file contains normalized quote | Verified | Full commit, path, blob ID, first inclusive line range |
| Complete supported file searched, quote absent | Contradicted | Same commit, path and blob ID, search scope and comparison rule |
| Parent tree was read completely and named entry provably absent | Contradicted | Commit, path, deepest resolved tree ID and first missing component |
| Directory, symlink, submodule, LFS pointer, binary or unsupported encoding at path | Can't check | Kind or encoding reason, observed object identity if known |
| Missing tree/blob/commit, malformed repository, read failure or resource ceiling | Can't check | Bounded reason, available provenance, recovery action |
| Empty quote, malformed commit ID, invalid path, invalid format over-limit or invalidly encoded quote, or unreadable user-supplied quote file | Invocation error | Diagnostic and correction on stderr |
| Internal invariant failure or output-write failure | Operational error | Error category on stderr; consumers discard incomplete output |

The predicate is “the named path at this commit is a source file containing this literal quotation.” Incomplete tree traversal can never establish absence. v0.1 accepts full SHA-1 commit IDs in SHA-1 repositories. Report unsupported object formats explicitly. Reject branch names, abbreviated IDs, tag objects and revision expressions as unsupported input. Read canonical Git objects without checkout, replacement refs, filters, hooks, history traversal, credential helpers, or automatic fetching. Start with a pure-Go object reader behind one internal boundary. Prove packed/loose objects and offline behavior before committing to a library. A local dependency failure becomes an explicit unsupported case.

Reject an invalid UTF-8 or NUL-bearing quote as invalid user input. Return an unsupported-content reason for an invalid UTF-8 or NUL-bearing source. A non-tree intermediate component yields an inconclusive result with its kind recorded. Require valid UTF-8 quote and source. Reject NUL as binary. Normalize CRLF to LF on both sides. Preserve BOM, lone CR, case, whitespace, Unicode normalization form and trailing newline. Use literal substring matching. First match means smallest start offset. One-based inclusive lines span the first and last matched bytes, so a match ending in LF ends on the line containing that LF. The path uses literal UTF-8 segments separated by slash. Reject absolute paths, dot segments, backslash, NUL and control characters, including bidi overrides. Path case and Unicode composition remain significant. Unsupported inputs stay visible in benchmark coverage.

## Data and errors

One receipt per invocation. Schema major 1 requires schema version, checker version, claim kind, requested commit and path, normalized quote SHA-256, comparison rule ID, verdict, stable reason code and evidence. Distinguish commit requested from commit observed. Successful evidence includes object format and blob ID or a tree witness. Optional range uses start/end integers. An unavailable object has no invented object ID. Keep durations, machine names and wall-clock times outside the deterministic payload. Show the same reason and evidence in every renderer. Hashes can disclose guessable text by trial, so treat exported receipts as potentially sensitive.

Use exit 0 for any completed receipt, including contradicted and can't check. Use 2 for invocation errors and 1 for internal, I/O delivery or encoding failures while emitting the result. Cancellation reports interruption without a verdict; POSIX exit 130 for interrupt where supported. JSON is one complete UTF-8 document plus LF on stdout. Diagnostics go to stderr. Consumers must check process success and validate the complete document before use. Never silently discard an unknown verdict. Preserve existing help/version behavior.

Proposed budgets for the first measurement: 64 KiB normalized quote, 8 MiB uncompressed source blob, 4 KiB path, 128 path components, 5 seconds for object access and comparison, 128 MiB peak memory on a documented reference runner. Bound reads before allocation/decompression and apply cumulative ceilings to tree enumeration and delta resolution. After input validation, unsupported storage features or exhausted repository-read budgets yield can't check with the limiting resource named. If safe cancellation cannot be guaranteed in the library, isolate the read in a bounded worker or reduce supported storage before release. Benchmark on both a cold and warm cache. Treat these values as starting decisions, and record evidence before raising them.

## Architecture and trust

The main test seam is the public CLI process against a temporary committed repository. The pipeline is input validation → read-only object lookup → deterministic comparison → receipt → renderer. Keep forge URLs, identity, presentation and publication outside verdict assignment. Run without accounts, outbound networking, an app database, a web server or a model. Generate evidence links only when there is an explicitly trusted repository mapping and immutable object reference. Local evidence always works with the commit and path. A future adapter may ingest existing CI statuses with their original scope. Submitted programs, patches and reproduction instructions remain inert data.

For the optional GitHub pilot, start with a read-only preview from trusted workflow code on one opt-in public repository. Separate any future writer from the reader. A trusted writer independently checks destination, current head, submission digest, bounds and permitted fields and recomputes the receipt from trusted inputs or verifies trusted provenance. Treat artifacts, quote text, refs, workflow logs and comment markers as untrusted. Recheck freshness immediately before the write, serialize updates per submission, and reconcile after a race. Only update a comment owned by the expected publisher. Maintain a local-only path for confidential submissions. Commenting is a later rollout with a separate off switch.

## Testing and release decisions

Reconstruct labeled fixture repositories and use the installed CLI as a reader would. Include negative controls for incomplete searches, wrong revisions, unavailable trees, normalized offsets, hostile display text, interrupted output, and conflicting worktree edits. Inspect JSON against a versioned schema and render it in a narrow terminal and linear screen-reader order. Compare semantic output across native Linux, macOS and Windows jobs. The starter has a smoke command; checker coverage is future work.

Ship local alpha when all normative contract cases pass, there are zero false contradictions in a frozen holdout, every decisive result replays, required artifacts match their checksums, and installation plus removal succeeds on each supported platform class. Report numerator and denominator and cases skipped per platform. Cross-compilation proves packaging only. Mark unexercised OS/architecture combinations explicitly as preview. If an artifact fails its own integrity check, withhold that artifact. If verdict correctness fails, hold the release. Publish benchmark misses, support tier and known limits alongside archives.

## Infrastructure pre-alpha

The [infrastructure pre-alpha milestone](https://github.com/valasme/receipts/milestone/1) qualifies the starter before the first checker. It covers the CLI shell, accessible help, error delivery, bundled documentation, native CI, packaging, verified unsigned install paths, publication and recovery. Native signing and provider recovery begin when the owner approves v1. PA01–PA04 are independent of T01–T09. A limited archive-only preview is permissible when described precisely. Full channel coverage requires evidence for every promised installer and target. These added distribution requirements supersede M3 timing for the full distribution milestone; external approval lead times are unknown. M1–M4 below describe delivery of claim checking. [Signing decision](../adr/0002-defer-native-signing-until-v1.md)

## Milestones and solo capacity

| Milestone | Indicative focused time | Exit evidence | Fallback |
| --- | --- | --- | --- |
| M1 local result | 1–2 weeks | One command reads the pinned blob and returns an inspectable match | Limit storage support and report the unsupported reason |
| M2 reliable local alpha | 2–4 more weeks | Three verdicts, adverse I/O, accessible renderers, frozen benchmark and install rehearsal | Keep local preview until gates pass |
| M3 public release | 1–2 more weeks | Verified artifacts, release notes, recovery drill and a documented support route | Label individually untested targets preview |
| M4 optional GitHub pilot | 2–4 additional weeks if useful | Read-only shadow data, replay-safe publication and removal drill | Keep Markdown export and pause automation |

Estimates assume one person, one active ticket, and ordinary interruptions. Reserve one session per week for fixture and documentation upkeep. No grants, paid signing service, always-on support rotation, second approver or upstream project participation is on the critical path. Stop after M3 if reviewing an explicit quote costs as much as checking it manually. Private dashboards, reputation scores, semantic symbol analysis, package-manager distribution, paid hosting, duplicate suggestions and optional model extraction each require a fresh use case. Enforcement, automated vulnerability reproduction, and grading contributors are outside this roadmap.

## Evaluation and decision to expand

Use at least 60 self-authored or redistribution-cleared cases, with at least 15 per expected verdict. Freeze at least 30 before tuning, stratified by expected verdict and repository family. Keep near-duplicates in one split. Establish ground truth by manual inspection of the pinned objects independent of the checker. Record exact counts, false contradiction rate on eligible non-contradicted claims, decisive coverage and skipped reasons. Zero observed false contradictions in a small set carries uncertainty. Ground truth concerns the quote only.

As a solo operator, perform a within-person timed replay on 12 fresh, paired tasks. Alternate manual-first and tool-first order across matched tasks. Include quote preparation, revision lookup and reading the receipt. Proposed expansion threshold: at least 25% median paired end-to-end time saving, calculated per pair as (manual time − assisted time) / manual time, with no false contradictions or lost evidence. Report paired differences and label self-testing bias. Optional volunteer feedback improves confidence but never blocks the CLI. Stop automatic publication immediately on a wrong contradiction, stale target, private-data leak or duplicate comment loop. Restore local-only mode, correct affected receipts and rerun the frozen set before re-enabling.

Technical references: [Git tree entry semantics](https://git-scm.com/docs/git-ls-tree), [GitHub Actions trust and permissions](https://docs.github.com/en/actions/reference/security/secure-use), [workflow command handling](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands), [W3C accessibility reference for web surfaces](https://www.w3.org/WAI/WCAG22/quickref/).
