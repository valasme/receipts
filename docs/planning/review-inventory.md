# Review inventory

520 review questions expressed as checks. Each section names its stage and owning ticket. Use a row to record a test, observation, accepted limit, or reason to defer when working that ticket. Marked boxes have supporting implementation, measurement or inspection in the [verification record](../verification.md) and the linked tests. Open boxes are unverified or await their stage. The release decisions in the spec govern shipment. Conditional discovery is parked until its use case exists. One owner can automate repeatable checks and explicitly mark unavailable native hardware or assistive technology as untested.

## Product boundary and solo ownership

Local alpha · T01

- [ ] R001 — Name the maintainer who reads the first receipt.
- [ ] R002 — Describe the contributor's pre-submission use case.
- [ ] R003 — Choose one literal quote as the first checkable claim.
- [ ] R004 — Show a true report with an erroneous citation in the product brief.
- [ ] R005 — Show a correct citation inside an otherwise mistaken submission.
- [ ] R006 — Identify which user selects the target commit.
- [ ] R007 — Identify who may decide the disposition of a report.
- [ ] R008 — Record whether reading the receipt saves a repository lookup.
- [ ] R009 — Price the manual effort of preparing the quote input.
- [ ] R010 — Include the time spent correcting an ambiguous claim.
- [ ] R011 — Give one person authority to pause an unreliable release.
- [ ] R012 — Cap active implementation work at one ticket.
- [ ] R013 — Separate owner-only account actions from offline work.
- [ ] R014 — Choose a fallback if the owner is unavailable for a week.
- [ ] R015 — Define a smallest usable release with no pilot participants.
- [ ] R016 — Record which assumptions came from the supplied research.
- [ ] R017 — List the evidence that would justify supporting a second claim kind.
- [ ] R018 — Give integrations an exit condition if adoption stalls.
- [ ] R019 — Define when a convenience feature can delay the core release.
- [ ] R020 — Describe the point at which maintaining the tool exceeds its measured benefit.

## Input and CLI contract

Local alpha · T01

- [x] R021 — Accept an explicit repository directory.
- [x] R022 — Resolve an omitted repository against the current directory.
- [x] R023 — Resolve the evidence path from the repository root.
- [x] R024 — Require a revision for every check.
- [x] R025 — Explain the supported commit ID form in help.
- [x] R026 — Accept a quote from an explicitly named local file.
- [x] R027 — Accept a quote from standard input using a single dash.
- [x] R028 — Preserve a final newline supplied through standard input.
- [x] R029 — Reject an empty quotation with a corrective diagnostic.
- [x] R030 — Reject an unrecognized output format before repository access.
- [x] R031 — Report conflicting singleton flag values consistently.
- [x] R032 — Reject extra positional arguments.
- [ ] R033 — Show how to pass an option value beginning with a dash.
- [ ] R034 — Show how to quote spaces in repository directory names.
- [x] R035 — Return help without opening any repository.
- [x] R036 — Return version without reading user configuration.
- [x] R037 — Complete a noninteractive check without a TTY.
- [x] R038 — Fail clearly when a quote file cannot be opened.
- [x] R039 — Handle a closed stdin pipe without waiting forever.
- [ ] R040 — Show the effective subcommand in usage errors.

## Revision identity and object storage

Local alpha · T02

- [x] R041 — Resolve a full commit ID from loose objects.
- [x] R042 — Resolve the same commit from packed storage.
- [x] R043 — Recognize SHA-1 hexadecimal IDs regardless of letter case.
- [x] R044 — Canonicalize accepted IDs to lowercase in receipts.
- [ ] R045 — Identify unsupported object formats before guessing ID length.
- [x] R046 — Reject a short unambiguous ID with full-ID guidance.
- [x] R047 — Reject a branch name even when it currently points at the requested content.
- [x] R048 — Reject a tag object passed as a commit.
- [x] R049 — Reject tree and blob IDs in the revision field.
- [x] R050 — Read the selected historical commit after HEAD advances.
- [x] R051 — Read the same object from a detached checkout.
- [x] R052 — Define the supported behavior for bare repositories.
- [ ] R053 — Read from linked worktrees or return their explicit unsupported reason.
- [ ] R054 — Keep a missing shallow-clone ancestor unresolved.
- [x] R055 — Prevent automatic fetching of promisor objects.
- [x] R056 — Exclude replacement references from the object identity calculation.
- [x] R057 — Return a corruption reason when object bytes fail integrity checks.
- [ ] R058 — Detect a missing pack index without guessing at file absence.
- [x] R059 — Bound recursive delta resolution in a packed object.
- [ ] R060 — Define a constrained policy for alternate object directories.

## Paths and tree traversal

Local alpha · T02

- [x] R061 — Compare path components case-sensitively.
- [x] R062 — Treat composed and decomposed Unicode paths as distinct.
- [x] R063 — Reject leading slash in an evidence path.
- [x] R064 — Reject a Windows drive-qualified evidence path.
- [x] R065 — Reject backslashes consistently across hosts.
- [x] R066 — Reject empty interior components.
- [x] R067 — Reject a trailing separator for a claimed source file.
- [x] R068 — Reject parent traversal segments.
- [x] R069 — Reject current-directory segments.
- [ ] R070 — Reject embedded NUL in machine-readable path inputs.
- [x] R071 — Reject unsafe direction overrides in a path.
- [x] R072 — Allow ordinary spaces within a path component.
- [x] R073 — Treat a leading dot in a normal filename literally.
- [x] R074 — Distinguish a missing leaf from an unreadable parent.
- [x] R075 — Capture the deepest proven tree for an absent entry.
- [x] R076 — Distinguish a directory entry from a regular source file.
- [x] R077 — Treat a symlink entry as its own unsupported kind.
- [ ] R078 — Treat a submodule entry as a repository boundary.
- [ ] R079 — Handle non-UTF-8 tree names without lossy aliasing.
- [x] R080 — Detect a non-directory intermediate component and explain the outcome.

## Text comparison and line evidence

Local alpha · T02

- [x] R081 — Match a literal substring in the middle of a line.
- [x] R082 — Find a quote spanning multiple source lines.
- [x] R083 — Preserve the case of the quotation.
- [x] R084 — Preserve tabs in indentation.
- [x] R085 — Preserve repeated spaces inside text.
- [x] R086 — Distinguish trailing whitespace before a newline.
- [ ] R087 — Normalize a CRLF pair split across read buffers.
- [x] R088 — Preserve a lone carriage return.
- [x] R089 — Treat a UTF-8 BOM as significant content.
- [x] R090 — Keep canonically equivalent Unicode sequences byte-distinct.
- [x] R091 — Distinguish an ellipsis character from three dots.
- [x] R092 — Treat regex punctuation as literal text.
- [x] R093 — Find the earliest occurrence of a repeated quote.
- [ ] R094 — Handle overlapping matches deterministically.
- [x] R095 — Report one-based lines for a match beginning at byte zero.
- [x] R096 — Count a final matched LF on its originating line.
- [x] R097 — Find a match ending at the last byte of a file.
- [x] R098 — Handle a source whose final line has no terminator.
- [x] R099 — Distinguish an empty source blob from missing source.
- [ ] R100 — Explain that a quote-only newline can match any qualifying line ending.

## Claim logic and limits of inference

Local alpha · T02

- [x] R101 — Bind one verdict to exactly one scoped proposition.
- [x] R102 — Keep the reported problem's validity outside the quote verdict.
- [x] R103 — Require complete search coverage before claiming a textual mismatch.
- [x] R104 — Record a distinct reason for provable path absence.
- [x] R105 — Keep unresolved revision separate from absent path.
- [ ] R106 — Keep an unavailable blob separate from an empty blob.
- [x] R107 — Keep denied repository access separate from a textual mismatch.
- [x] R108 — Use an explicit unsupported-encoding result for invalid source UTF-8.
- [x] R109 — Use an invocation diagnostic for invalid UTF-8 in the quote.
- [x] R110 — Recognize binary source through the documented NUL rule.
- [x] R111 — Classify a recognized Git LFS pointer as indirect content.
- [x] R112 — Avoid following a source redirect into another repository.
- [x] R113 — Prevent score or model confidence from assigning a verdict.
- [x] R114 — Use can't check when traversal exhausts its budget.
- [x] R115 — Ignore changes in the working tree when establishing facts.
- [x] R116 — Keep a verified match scoped to the inspected revision.
- [x] R117 — Give contradictory evidence its own reason code.
- [ ] R118 — Record how the checker distinguishes incomplete reads from EOF.
- [x] R119 — Explain the differing results for a wrong path and a missing object.
- [x] R120 — Keep lack of a reproduced runtime symptom outside the evidence for quote absence.

## Receipt fields and schema evolution

Local alpha · T03

- [x] R121 — Declare the schema major in every machine receipt.
- [x] R122 — Record the checker version independently of the schema.
- [x] R123 — Identify the claim kind with a stable enumeration.
- [x] R124 — Record the requested revision even when unavailable.
- [x] R125 — Record the observed commit only after validation.
- [x] R126 — Identify the repository object format for resolved evidence.
- [x] R127 — Record the source blob ID for both quote hits and textual misses.
- [x] R128 — Record the tree witness for a proven missing component.
- [x] R129 — Include a digest of the normalized quote.
- [x] R130 — Name the digest algorithm independently of Git's object hash.
- [x] R131 — Record the comparison rule version.
- [x] R132 — Keep reason codes independent of localized display strings.
- [x] R133 — Constrain line endpoints to positive integers.
- [x] R134 — Require the end line to be at least the start line.
- [x] R135 — Forbid a line range when there is no match.
- [ ] R136 — Omit unavailable evidence rather than inventing sentinel IDs.
- [ ] R137 — Define how a consumer handles new optional fields.
- [ ] R138 — Reject an unsupported major in the publication adapter.
- [ ] R139 — Make a future change to matching rules distinguishable in old receipts.
- [ ] R140 — Publish a minimal valid example for each verdict.

## Human interface and information design

Local alpha · T03

- [x] R141 — Lead each receipt with the verdict and claim kind.
- [x] R142 — Place the file path adjacent to the matching line range.
- [x] R143 — Display the complete commit in copyable form.
- [x] R144 — Place the reason immediately after the evidence.
- [ ] R145 — Use one next action for a recoverable failure.
- [ ] R146 — Expose a usable manual inspection route without a forge.
- [x] R147 — Keep the successful common case to a short terminal block.
- [x] R148 — Avoid duplicating the same claim in a summary and body.
- [x] R149 — Use a consistent line order across verdicts.
- [ ] R150 — Differentiate missing evidence from missing input in the headline.
- [ ] R151 — Explain which normalization rule affects a mismatch.
- [x] R152 — Identify the earliest match when several copies exist.
- [x] R153 — Keep prompts and decoration out of piped output.
- [x] R154 — Use neutral language when addressing a first-time contributor.
- [ ] R155 — Make the human-readable summary intelligible when pasted into email.
- [ ] R156 — Use a meaningful Markdown link label for source inspection.
- [ ] R157 — Render long paths without cutting off their identifying suffix.
- [ ] R158 — Keep text selection independent of any drawn border.
- [x] R159 — Separate tool failures visually from claim findings.
- [ ] R160 — Show the effect of correcting a citation in the onboarding example.

## Accessibility and inclusive interaction

Local alpha · T03

- [x] R161 — Announce verdicts with words even when color is disabled.
- [ ] R162 — Use meaningful reading order with a screen reader.
- [ ] R163 — Provide an ASCII-readable alternative to decorative separators.
- [x] R164 — Keep the terminal interaction fully operable by keyboard.
- [x] R165 — Test help navigation at 40 columns.
- [ ] R166 — Keep the output usable at 200 percent magnification in a rendered comment.
- [ ] R167 — Test reflow of the Markdown receipt at narrow mobile width.
- [ ] R168 — Give each evidence link a distinct spoken purpose.
- [x] R169 — Avoid Markdown tables for layout in the receipt.
- [x] R170 — Read a multiline example using VoiceOver or document the test gap.
- [x] R171 — Read a Windows example using Narrator or document the test gap.
- [x] R172 — Read a Linux terminal example with a nonvisual reader or record the gap.
- [x] R173 — Honor user terminal colors by using plain default styles.
- [ ] R174 — Ensure a provider's light theme does not hide explanatory text.
- [ ] R175 — Inspect the same comment in forced-colors mode.
- [x] R176 — Allow copying commands without copying the shell prompt.
- [x] R177 — Avoid spinner-only progress feedback.
- [x] R178 — Keep transient feedback available in final output.
- [ ] R179 — Pair each jargon term with a plain-language explanation in help.
- [x] R180 — Write down what automated accessibility checks cannot establish.

## Error behavior and recovery

Local alpha · T04

- [x] R181 — Assign a usage exit for missing required inputs.
- [ ] R182 — Assign an operational exit for an internal invariant failure.
- [x] R183 — Return a completed receipt for a supported inconclusive check.
- [x] R184 — Keep a contradicted receipt consumable under a successful process exit.
- [x] R185 — Reserve stdout for the requested result.
- [x] R186 — Route diagnostics to stderr.
- [ ] R187 — Explain a nonexistent repository directory.
- [ ] R188 — Explain a directory that is present but lacks Git metadata.
- [ ] R189 — Distinguish a read-only repository from one lacking read permission.
- [ ] R190 — Describe how to obtain a missing revision through the user's normal workflow.
- [ ] R191 — Offer a next action for an unsupported storage type.
- [x] R192 — Explain an input ceiling in the unit the user supplied.
- [x] R193 — Handle a full output device as failed delivery.
- [ ] R194 — Handle a broken stdout pipe without claiming delivery succeeded.
- [ ] R195 — Discard incomplete JSON after a short write.
- [x] R196 — Give a clear interruption outcome when the user cancels.
- [x] R197 — Distinguish cancellation from a configured deadline.
- [x] R198 — Make rerunning a failed local invocation safe.
- [ ] R199 — Include a stable diagnostic identifier for support requests.
- [x] R200 — Keep stack traces and raw library internals out of normal diagnostics.

## Privacy and data handling

Local alpha · T04

- [x] R201 — Run a successful local check with network access denied.
- [x] R202 — Run the failure path with network access denied.
- [x] R203 — Avoid including the local account name in a receipt.
- [x] R204 — Exclude the absolute checkout directory from shared evidence.
- [x] R205 — Exclude the absolute quote filename from shared evidence.
- [x] R206 — Omit raw quote contents in default output.
- [x] R207 — Omit source excerpts from default diagnostics.
- [x] R208 — Document that a quote hash can reveal a guessable quote.
- [x] R209 — Document that private path names themselves may be sensitive.
- [x] R210 — Keep author name and email out of object provenance.
- [ ] R211 — Avoid creating a persistent history of local checks.
- [ ] R212 — Avoid sending automatic crash reports.
- [ ] R213 — Avoid retaining per-user activity identifiers.
- [ ] R214 — Inspect temporary workspace cleanup after normal completion.
- [ ] R215 — Check temporary files after interruption if a worker uses disk.
- [ ] R216 — Document stdout redirection as a user-controlled export.
- [x] R217 — Ensure a private clone never infers a public evidence destination.
- [x] R218 — Provide an offline troubleshooting procedure.
- [x] R219 — Use synthetic paths and snippets in public bug examples.
- [ ] R220 — Describe deletion of an already-shared receipt as best-effort across copies.

## Defensive boundaries and resource control

Local alpha · T04

- [ ] R221 — Read report prose strictly as untrusted data.
- [x] R222 — Keep repository-supplied hooks outside the check path.
- [x] R223 — Ignore repository-supplied clean and smudge filters.
- [x] R224 — Prevent a repository from selecting the checker executable.
- [x] R225 — Keep shell command construction out of object lookup.
- [x] R226 — Do not interpret markup found in filenames as renderer instructions.
- [x] R227 — Keep terminal escape sequences inert in diagnostics.
- [x] R228 — Bound quote input before allocating its full contents.
- [x] R229 — Enforce the blob limit on uncompressed size.
- [x] R230 — Bound cumulative bytes across tree reads.
- [x] R231 — Bound path-component count before traversing the tree.
- [x] R232 — Bound memory used by pack index parsing.
- [ ] R233 — Limit total time across all object operations.
- [x] R234 — Stop decompression when its output exceeds policy.
- [ ] R235 — Ensure cancellations reach all child work.
- [ ] R236 — Verify fetched dependency provenance before adopting a reader library.
- [ ] R237 — Inventory environment variables that can influence repository resolution.
- [ ] R238 — Require explicit user selection for any path outside the repository's storage domain.
- [x] R239 — Treat a malformed tree with duplicate names as inconclusive.
- [ ] R240 — Record the integrity boundary assumed for local object storage.

## Performance and scale

Local alpha · T04

- [ ] R241 — Measure cold startup on the reference machine.
- [x] R242 — Measure check latency with a warm object cache.
- [x] R243 — Measure peak memory for a maximum-size valid blob.
- [x] R244 — Measure latency for the largest permitted quote.
- [x] R245 — Benchmark a quote that nearly matches many positions.
- [ ] R246 — Benchmark a hit located at the beginning of a large blob.
- [ ] R247 — Benchmark a hit located at the end of a large blob.
- [x] R248 — Benchmark a conclusive miss over the full permitted blob.
- [ ] R249 — Measure path traversal in a broad root tree.
- [ ] R250 — Measure traversal at the permitted nesting limit.
- [ ] R251 — Measure packed history access independently of total commit count.
- [ ] R252 — Record CPU time alongside wall clock to expose I/O waits.
- [x] R253 — Measure repeated invocations without a resident service.
- [ ] R254 — Track binary size for each distributed platform.
- [ ] R255 — Measure overhead of machine-readable rendering.
- [ ] R256 — Compare performance across native architecture classes when available.
- [x] R257 — Report timing dispersion over repeated runs.
- [ ] R258 — Separate watchdog overhead from actual matching cost.
- [ ] R259 — Record disk medium and Go version with the reference numbers.
- [ ] R260 — Define a regression threshold from baseline variability before enforcing it.

## Cross-platform behavior

Local alpha · T05

- [x] R261 — Run native Linux amd64 smoke checks.
- [x] R262 — Exercise Linux arm64 natively or mark that target preview.
- [x] R263 — Run native Apple Silicon smoke checks.
- [x] R264 — Exercise Intel macOS natively or mark that target preview.
- [x] R265 — Run native Windows amd64 smoke checks.
- [x] R266 — Exercise Windows arm64 natively or mark that target preview.
- [x] R267 — Compare normalized receipts across the three operating systems.
- [ ] R268 — Read committed LF bytes from a CRLF-configured Windows checkout.
- [x] R269 — Check a case-only path difference on a case-insensitive host.
- [ ] R270 — Pass a Windows repository path with a drive and spaces.
- [ ] R271 — Keep slash-based evidence paths usable from PowerShell.
- [ ] R272 — Document how text pipelines can change quote bytes on Windows.
- [ ] R273 — Test a repository directory with a non-ASCII account path.
- [ ] R274 — Test a POSIX checkout that has no writable working tree.
- [ ] R275 — Inspect Ctrl-C handling on Windows.
- [ ] R276 — Inspect SIGINT handling on Unix.
- [ ] R277 — Verify archive executable permissions after extraction on Unix.
- [x] R278 — Verify the Windows archive contains a usable executable suffix.
- [ ] R279 — Check long repository-directory paths under documented platform limits.
- [ ] R280 — Distinguish binary target architecture from the architecture used by emulation.

## Testing and verification design

Local alpha · T05

- [x] R281 — Build fixtures from portable repository descriptions.
- [x] R282 — Use the actual CLI process for golden receipt tests.
- [x] R283 — Check stderr separately from stdout in integration tests.
- [x] R284 — Capture process exit status for every fixture family.
- [x] R285 — Prove dirty working files leave a receipt unchanged.
- [x] R286 — Prove staging different content leaves the receipt unchanged.
- [x] R287 — Keep golden comparisons free of timestamps.
- [x] R288 — Validate generated JSON against its declared schema.
- [x] R289 — Compare visible Markdown evidence with the JSON equivalent.
- [x] R290 — Round-trip escaped Unicode evidence through a JSON reader.
- [x] R291 — Exercise truncation during object lookup using controlled fixtures.
- [x] R292 — Test resource ceilings at exactly the limit and one byte over.
- [x] R293 — Check comparison invariance when LF becomes CRLF on both sides.
- [ ] R294 — Check monotonicity of first-match offsets when appending content.
- [x] R295 — Exercise malformed input with a bounded property-test corpus.
- [x] R296 — Run validation with Go's race detector where supported.
- [ ] R297 — Confirm deterministic iteration ordering across repeated runs.
- [ ] R298 — Re-run isolated cases in random order to reveal fixture leakage.
- [ ] R299 — Store the fixture revision and generating tool versions with results.
- [ ] R300 — Require each corrected verdict bug to acquire a minimal regression case.

## Benchmark quality and evidence of value

Local alpha · T06

- [x] R301 — Define each corpus label as a claim-level verdict.
- [ ] R302 — Record the independent ground-truth method for each case.
- [ ] R303 — Include a true citation from an otherwise flawed report.
- [ ] R304 — Include an erroneous citation from an otherwise legitimate report.
- [x] R305 — Include inconclusive cases with valid underlying code.
- [x] R306 — Balance expected verdict strata in the initial set.
- [x] R307 — Split whole repository families together.
- [ ] R308 — Keep paraphrased copies of a quote on one side of the split.
- [x] R309 — Freeze holdout identifiers before changing checker rules.
- [x] R310 — Record whether benchmark text can be redistributed.
- [x] R311 — Measure false contradictions against eligible ground truth.
- [x] R312 — Measure false verifications separately.
- [x] R313 — Count unsupported cases in the full denominator.
- [x] R314 — Report decisive coverage alongside accuracy.
- [x] R315 — Publish the confusion matrix including can't check.
- [x] R316 — Report uncertainty for observed zero-error estimates.
- [ ] R317 — Include manual quote preparation time in both comparisons.
- [x] R318 — Counterbalance task order for the solo timing exercise.
- [ ] R319 — Record which timing tasks the evaluator has previously seen.
- [ ] R320 — Set a minimum improvement before allocating time to GitHub automation.

## CI and development infrastructure

Local release · T07

- [x] R321 — Document the minimum supported Go toolchain.
- [x] R322 — Pin actions to reviewed immutable commits.
- [ ] R323 — Record the upstream version associated with each pinned action.
- [x] R324 — Separate read-only tests from release credentials.
- [x] R325 — Disable persisted checkout credentials where unnecessary.
- [ ] R326 — Exercise PR jobs with a read-only token.
- [x] R327 — Test ordinary pushes independently from tagged releases.
- [ ] R328 — Keep privileged jobs on trusted workflow definitions.
- [x] R329 — Distinguish a native OS test from cross-compilation in CI output.
- [x] R330 — Keep fixtures self-contained when dependency fetching is disabled.
- [x] R331 — Name CI jobs so a failing platform is visible immediately.
- [x] R332 — Set finite timeouts on release and test jobs.
- [ ] R333 — Cancel redundant old validation jobs on new revisions.
- [ ] R334 — Avoid canceling a half-published release as ordinary CI churn.
- [ ] R335 — Retain small diagnostics long enough to inspect a failed run.
- [ ] R336 — Define retention for synthetic test artifacts.
- [ ] R337 — Keep CI logs free from raw submission text.
- [ ] R338 — Add a dependency update rehearsal to the maintenance cadence.
- [ ] R339 — Record how a solo owner reruns one failed platform job.
- [x] R340 — Document which checks must pass for the exact release commit.

## Packaging and installation

Local release · T07

- [x] R341 — Publish a mapping from OS and architecture to archive name.
- [x] R342 — Distinguish a source checkout install from an archive install.
- [x] R343 — Provide a user-local install path on Linux.
- [x] R344 — Provide a user-local install path on macOS.
- [x] R345 — Provide a user-local install path on Windows.
- [ ] R346 — Document PATH changes separately for common shells.
- [x] R347 — Show how to verify the installed version.
- [x] R348 — Include the license text with every archive.
- [x] R349 — Generate an artifact manifest from the actual release outputs.
- [x] R350 — Check each archive against the published checksum.
- [x] R351 — Explain what a checksum establishes about corruption.
- [x] R352 — Provide an independent authenticity verification route or declare its absence.
- [x] R353 — State signing and notarization status for macOS downloads.
- [x] R354 — State code-signing status for Windows downloads.
- [x] R355 — Avoid onboarding instructions that weaken OS protections.
- [x] R356 — Exercise installation into a clean temporary environment.
- [x] R357 — Exercise removal without deleting a user's repositories.
- [ ] R358 — Exercise upgrading from the oldest supported preview.
- [x] R359 — Document a reversible way to select a known-good binary.
- [ ] R360 — Gate each future package-manager channel on a named maintenance budget.

## Release management and recovery

Local release · T07

- [x] R361 — Allocate one version to one source revision.
- [x] R362 — Set a clear pre-release marker for experimental distributions.
- [ ] R363 — Write release notes that identify verdict-rule changes.
- [x] R364 — Publish known unsupported repository formats.
- [x] R365 — List which platform combinations were actually exercised.
- [x] R366 — Run the packaging rehearsal before creating a public tag.
- [x] R367 — Verify that the release manifest has one entry per intended target.
- [ ] R368 — Test downloaded artifacts from a staged or draft distribution.
- [x] R369 — Describe recovery from a failed upload before publication.
- [ ] R370 — Define how to withdraw an artifact with a bad checksum.
- [x] R371 — Define how to supersede a release with a bad verdict rule.
- [ ] R372 — Preserve prior provenance records after superseding a release.
- [ ] R373 — Explain how users recognize affected checker versions in saved receipts.
- [ ] R374 — Test a downgrade against the last compatible receipt schema.
- [ ] R375 — Record the restore path when a signing credential is unavailable.
- [ ] R376 — Keep dependency inventory per released version.
- [ ] R377 — Assign license-review responsibility to the project owner.
- [x] R378 — Record changes in toolchain and build inputs.
- [x] R379 — Rehearse the release sequence without a second approver.
- [ ] R380 — Choose the release communication channel before the first incident.

## Documentation, support and governance

Local release · T07

- [x] R381 — Give a newcomer one copyable successful local example.
- [x] R382 — Give a newcomer one deliberately contradicted example.
- [x] R383 — Give a newcomer one example requiring additional evidence.
- [x] R384 — Show how to obtain a full commit ID using familiar Git commands.
- [ ] R385 — Explain why quotes copied from rendered web pages can differ.
- [x] R386 — Explain how to include or omit a final newline deliberately.
- [ ] R387 — Provide an annotated receipt with every evidence field identified.
- [ ] R388 — Publish the policy for interpreting unknown result codes.
- [x] R389 — Describe independent manual verification using a pinned revision.
- [x] R390 — Document the boundary between reporting a bug and disclosing private material.
- [ ] R391 — Give issue reporters a redacted minimal reproduction template.
- [ ] R392 — Show how to reduce a case to a synthetic repository.
- [x] R393 — Route contact about sensitive Receipts bugs to a private project channel.
- [x] R394 — State that public support is best effort for a solo project.
- [ ] R395 — Describe the process for proposing a new check kind.
- [x] R396 — Define the contribution evidence expected for a verdict change.
- [ ] R397 — Record how a disputed fixture label gets reconsidered.
- [ ] R398 — Explain how old examples stay paired with their schema versions.
- [x] R399 — Make license and third-party notices discoverable from the project home.
- [ ] R400 — Describe a maintenance-mode path if the owner steps away.

## Forge intake and read-only preview

GitHub pilot · T08

- [ ] R401 — Start with one opt-in public repository.
- [ ] R402 — Select an explicit structured claim from the submission.
- [ ] R403 — Capture the repository identity from the trusted event envelope.
- [ ] R404 — Distinguish the base revision from the contributor's head revision.
- [ ] R405 — Require an explicit mapping from submitted revision to checked snapshot.
- [ ] R406 — Use the submission's stable numeric identity across title edits.
- [ ] R407 — Hash the relevant submission input to detect material edits.
- [ ] R408 — Skip comment-only events that cannot alter the claim.
- [ ] R409 — Bound the incoming Markdown size before parsing.
- [ ] R410 — Treat report instructions as literal text.
- [ ] R411 — Explain an issue that contains no supported claim.
- [ ] R412 — Keep ambiguous multiple candidates pending explicit selection.
- [ ] R413 — Display a preview without requesting comment-write permission.
- [ ] R414 — Make the preview discoverable to the opting-in maintainer.
- [ ] R415 — Exclude confidential disclosure channels from public preview triggers.
- [ ] R416 — Track whether a requested source object is available on the runner.
- [ ] R417 — Refuse a repository identity mismatch during event resolution.
- [ ] R418 — Calculate a preview's expected API call budget.
- [ ] R419 — Measure preview noise on old public submissions before enabling live events.
- [ ] R420 — Record the action version and expected configuration visible to adopters.

## Publication, concurrency and moderation

Opt-in publishing · T09

- [ ] R421 — Require explicit per-repository opt-in to publishing.
- [ ] R422 — Limit the writer to the smallest available comment permission.
- [ ] R423 — Build the comment from validated receipt fields.
- [ ] R424 — Bind a candidate result to the intended repository and issue.
- [ ] R425 — Recheck the current submission digest immediately before posting.
- [ ] R426 — Recheck the pinned head for moving PRs before posting.
- [ ] R427 — Serialize concurrent publications for the same submission.
- [ ] R428 — Recognize duplicate delivery of the same event.
- [ ] R429 — Handle an old event arriving after a newer update.
- [ ] R430 — Read back remote state after an ambiguous write timeout.
- [ ] R431 — Verify bot authorship before editing a marked comment.
- [ ] R432 — Ignore contributor-authored lookalike receipt markers.
- [ ] R433 — Use a stable identifier to find the canonical comment.
- [ ] R434 — Retire a stale comment when the underlying claim is removed.
- [ ] R435 — Respect an owner's intentional suppression of a bot comment.
- [ ] R436 — Cap comment body length without dropping a verdict qualification.
- [ ] R437 — Escape mentions so reports cannot summon unrelated users.
- [ ] R438 — Disable link previews or omit unsafe external URLs.
- [ ] R439 — Keep labels advisory with an explicit opt-in for any downstream automation.
- [ ] R440 — Reconcile a force-push that races with a successful post.

## Pilot infrastructure and operating costs

GitHub pilot · T08

- [ ] R441 — Estimate runner minutes per check from a measured pilot.
- [ ] R442 — Budget API calls per submission update.
- [ ] R443 — Set a per-repository cap on parallel pilot runs.
- [ ] R444 — Coalesce bursts of edits into one current preview.
- [ ] R445 — Respect provider rate-limit reset hints.
- [ ] R446 — Add bounded backoff for transient API failures.
- [ ] R447 — Set a retry ceiling per event to avoid a permanent queue.
- [ ] R448 — Drop obsolete work after newer input supersedes it.
- [ ] R449 — Keep read-only jobs free of publication credentials.
- [ ] R450 — Keep write jobs free of contributor-controlled execution.
- [ ] R451 — Prefer ephemeral environments for processing public submissions.
- [ ] R452 — Separate trusted workflow artifacts from PR-controlled artifacts.
- [ ] R453 — Define maximum accepted result artifact size.
- [ ] R454 — Bind any transported artifact to its producing run.
- [ ] R455 — Avoid using repository-shared caches as integrity evidence.
- [ ] R456 — Set a measurable monthly pilot spending cap before enabling writes.
- [ ] R457 — Preserve local checking when the forge is unavailable.
- [ ] R458 — Document what to do if the repository exhausts its CI allowance.
- [ ] R459 — Record who pays recurring costs for an installed integration.
- [ ] R460 — Drill disabling the pilot without deleting local checks or saved receipts.

## Observability and incidents

Opt-in publishing · T09

- [ ] R461 — Count completed receipts per verdict using synthetic or opt-in data.
- [ ] R462 — Count technical failures separately from verdicts.
- [ ] R463 — Record a histogram of unresolved reason codes.
- [ ] R464 — Track stale publications separately from failed API writes.
- [ ] R465 — Measure duplicate-comment incidence.
- [ ] R466 — Measure the distribution of time from edit to current receipt.
- [ ] R467 — Detect repeated failures isolated to one checker version.
- [ ] R468 — Use opaque correlation identifiers scoped to one run.
- [ ] R469 — Scrub tracker payloads before retaining diagnostics.
- [ ] R470 — Limit metric cardinality by excluding raw paths.
- [ ] R471 — Provide a human-readable health summary from bounded logs.
- [ ] R472 — Define the trigger for suspending a faulty claim rule.
- [ ] R473 — Define the trigger for disabling a faulty writer.
- [ ] R474 — Define the trigger for privately handling an unintended disclosure.
- [ ] R475 — Locate affected comments using minimal stored provenance.
- [ ] R476 — Publish a correction tied to the original receipt identity.
- [ ] R477 — Tell adopters when historical receipts need rechecking.
- [ ] R478 — Rehearse rotation of a compromised publication credential.
- [ ] R479 — Test returning to read-only shadow mode after an incident.
- [ ] R480 — Record incident cause and the fixture or operational change preventing recurrence.

## Future extraction and additional claim kinds

Conditional discovery · Parked

- [ ] R481 — Measure how often a human can supply a quote without assistance.
- [ ] R482 — Sample how often prose contains no checkable proposition.
- [ ] R483 — Require any proposed claim to cite its source text span.
- [ ] R484 — Track extraction precision independently from checker accuracy.
- [ ] R485 — Measure extraction omissions on multilingual prose.
- [ ] R486 — Require human confirmation when extracted scope is ambiguous.
- [ ] R487 — Test whether a local extractor meets time and memory budgets.
- [ ] R488 — Keep a fully deterministic path available when a model is unavailable.
- [ ] R489 — Make external inference opt-in with explicit data destinations.
- [ ] R490 — Record which model version proposed a claim.
- [ ] R491 — Treat model output as bounded typed data before validation.
- [ ] R492 — Reevaluate model cost after a change in average report length.
- [ ] R493 — Require evidence before investing in language-specific symbol indexing.
- [ ] R494 — Define language-version scope before a symbol check can contradict a claim.
- [ ] R495 — Treat generated code and conditional compilation as explicit symbol-check limitations.
- [ ] R496 — Read existing CI results only with their run identity and target revision.
- [ ] R497 — Keep test pass status separate from behavioral correctness.
- [ ] R498 — Present potential duplicate reports as suggestions for human review.
- [ ] R499 — Require a new decision record before introducing persistent local storage.
- [ ] R500 — Require a second real forge use case before designing a shared adapter interface.

## Future interfaces and ecosystem decisions

Conditional discovery · Parked

- [ ] R501 — Validate whether private teams actually need a shared inbox.
- [ ] R502 — Model the work a dashboard would remove from the local CLI flow.
- [ ] R503 — Estimate self-hosted maintenance time before selecting a web stack.
- [ ] R504 — Define local binding defaults before considering a private server.
- [ ] R505 — Define authentication needs before sharing a private inbox.
- [ ] R506 — Define tenant separation before retaining data from multiple projects.
- [ ] R507 — Choose retention by report sensitivity before storing report history.
- [ ] R508 — Design export and deletion together before adding an inbox database.
- [ ] R509 — Plan keyboard focus restoration if a receipt detail panel is introduced.
- [ ] R510 — Plan explicit accessible names for future icon-only controls.
- [ ] R511 — Plan focus visibility through modals and sticky headers.
- [ ] R512 — Plan zoom and text-spacing tests for any new web layout.
- [ ] R513 — Plan touch target sizing for a future interactive dashboard.
- [ ] R514 — Plan reduced-motion behavior before introducing animated status changes.
- [ ] R515 — Plan a plain-language empty state for an inbox with zero reports.
- [ ] R516 — Plan distinguishable loading, offline and permission-denied views.
- [ ] R517 — Estimate localization upkeep before supporting a second UI language.
- [ ] R518 — Validate demand before maintaining a desktop installer.
- [ ] R519 — Require a reproducible installation channel before advertising one-line package installs.
- [ ] R520 — Define archival access to receipts if any future hosted service closes.
