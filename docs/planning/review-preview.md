# Local review preview

A maintainer starts with the body of a PR or issue, a local clone and a caller-selected commit. The existing agent proposal provides the quotations and their locations. One CLI invocation checks the proposals and shows the result with the original submission line ranges. This is the first maintainer workflow slice.

## Council decisions

| Perspective | Objection | Decision |
| --- | --- | --- |
| Product | A new renderer only helps when a submission contains claims we can check. None of the 15 newest open `cli/cli` issues returned by a created-descending search on the review date contained an explicitly attributed quotation of committed source. Several referenced a file or line instead. | Make the existing check usable in review and keep unsupported statements visible. The owner chose to sample PR change claims before adding a new check. The issue sample is a directional coverage observation. |
| Evidence | A stale proposal or changed quote could attach a real verdict to words the submitter never wrote. | Check the proposed source span against the supplied Markdown before verification. A mismatch is a proposal error. Keep the caller-selected commit explicit and reuse the existing checker. |
| Operations | Direct forge intake adds authentication, freshness and publication requirements that can obscure the local usefulness test. | Keep this iteration offline and use text output. Revisit the read-only pilot after a completed-review timing trial. |

The public issue sample ran from [Agent hint for `gh event listen`](https://github.com/cli/cli/issues/15113) through [Add granular issue status support](https://github.com/cli/cli/issues/14996). [Escaped code-search quotes](https://github.com/cli/cli/issues/15060) and [Run rerun fails on workflow metadata](https://github.com/cli/cli/issues/15054) illustrate source references.

## CLI contract

`receipts review --submission FILE --proposal FILE --rev COMMIT [--compare COMMIT] [--repo DIR]` consumes a UTF-8 Markdown body and a proposal. One input may use stdin. The proposal accepts exact, case-sensitive keys, requires `claims` and `unresolved` arrays and accepts an optional `file_changes` array, with at most 16 total entries. Both files are limited to 1 MiB. Normalize CRLF to LF for matching source spans. Require full SHA-1 commit IDs.

A quotation claim points at one attribution line with a single backticked path, immediately followed by an unindented triple-backtick fence with optional `text` and its exact contents. An unresolved entry identifies its exact statement, which may span lines. Source spans are inclusive, one-based and nonoverlapping. See the [proposal schema](../../schema/review-proposal-v1.json). Supply `schema_major: 1` when you want an explicit version. Existing proposals without that field remain valid.

Matching uses literal source lines. A matching span can appear inside a larger fence or a comment. The maintainer decides whether the surrounding Markdown uses it as a citation. Revisit Markdown-aware matching if real submissions show repeated mistakes. The fence grammar requires the final LF before the closing fence and cannot represent paths containing a backtick. Use `receipts check --quote-file` for either quotation case. A file-change statement whose path contains a backtick can remain unresolved.

The preview shows each entry in submission order. Long quoted context uses indented continuation lines with escaped controls. The header shows both pins for file-change claims and marks a supplied comparison unused for other proposals. A checked quote includes the existing human-readable receipt and the safely quoted citation line. An unresolved statement is displayed with its source location and safely quoted text. An unsupported Git observation still produces Can't check. A citation mismatch, malformed input or invalid claim exits 2 without emitting a preview. Empty proposals display that no claims or statements were proposed. Successful delivery exits 0. Output failures exit 1 and cancellation exits 130. Checks share the existing five-second read budget.

Test at the public CLI process boundary with a committed Git fixture and the captured agent proposal. Independently replay the receipts. Include a changed quote, hostile display text, and an empty proposal. Keep the existing checker contract and use no network or model calls in the command.

## File-change council

| Perspective | Concern | Decision |
| --- | --- | --- |
| Maintainer | A branch tip can move and a rename can hide which exact path the author meant. | Compare one case-sensitive repository-relative path between a caller-pinned comparison commit and head commit. For a GitHub-style PR diff, supply the merge base as the comparison commit. A rename gives separate observations for the old and new paths. |
| Evidence | The same blob can acquire executable mode, and a regular file can become a symlink. An unreadable object cannot establish equality or absence. | Compare verified blob IDs and Git modes for regular files and symlinks. Read a symlink's committed target bytes as a blob. Additions, deletions, mode-only changes and transitions between these file kinds count. Equal entries or two proven absences contradict the claim. Directories and submodules at the exact path, non-tree ancestors, and missing or unreadable required objects yield Can't check. This applies the [claim-level evidence decision](../adr/0001-verdicts-require-evidence.md). |
| Implementation | A proposal can point at stale text, or a receipt could imply that the whole sentence was verified. | Add an optional collection to the local review proposal for explicit positive file-change claims. Require the verbatim statement, exact backticked path, and matching submission lines. Pin the comparison commit with a CLI option. Show each side's evidence with the claim and keep the statement visible for human review. Exercise the public CLI process with real Git fixtures. |

## File-change proposals

Add a `file_changes` array to a review proposal and supply `--compare COMMIT` when the array contains entries. The `--rev` commit is the head. Each entry has a `path`, `statement` and inclusive `source_lines`. The statement must match those submission lines after CRLF normalization and contain exactly one pair of backticks enclosing the literal path. The same entry limit and span rules apply across all three arrays. The maintainer confirms whether the statement makes the positive claim that this path changed.

The text receipt includes the checker version and comparison rule `git-path-blob-and-mode-v1`. It reports a change in presence, Git mode, or verified blob ID at the exact path. A verified tree can establish absence. The same blob ID and mode at both commits, or proven absence at both, contradicts the claim.

Compare the blob ID and mode at each exact path. Blob IDs reflect committed bytes, including line endings and symlink targets. If a verified tree proves a component is missing, show that tree and component. Show mode and blob ID for a verified file, or the reason evidence is incomplete or unsupported. A path absent in both trees yields Contradicted. Label the exact Git claim alongside its verdict and show the submission statement separately as context. The [walkthrough](../../examples/agent/README.md#check-whether-a-file-changed) includes a runnable fixture.

## PR change claim sample

Read the 15 consecutive public PR bodies returned by the `cli/cli` pull list across all states, ordered by creation, from [the setup-go update](https://github.com/cli/cli/pull/15117) through [the Zod update](https://github.com/cli/cli/pull/15086). Count a PR when its author explicitly says a named repository path changes in the proposed patch. Skip template comments, test commands, dependency release notes and general suggestions about where to start reviewing. Keep the three bot PRs in the denominator.

Four PRs (4/15 overall, 4/12 among the non-bot authors) made explicit claims about eight changed paths. GitHub's changed-file list contained all eight. Two other descriptions gave reviewer pointers to files that also changed. The sample supports testing a narrow claim about whether a path changed from a pinned comparison base to the PR head. It does not show that verifying these claims saves time or that the behavior described by a PR is correct. Measure against the usual Files changed view before extending the pilot.

| Sample PR | Explicit paths confirmed in the changed-file list |
| --- | --- |
| [Cyclic alias expansion](https://github.com/cli/cli/pull/15107/files) | `pkg/cmd/root/alias.go`, `pkg/cmd/root/alias_test.go` |
| [Preserve workflow cancel errors](https://github.com/cli/cli/pull/15103/files) | `pkg/cmd/run/cancel/cancel.go`, `pkg/cmd/run/cancel/cancel_test.go` |
| [Handle empty pager commands](https://github.com/cli/cli/pull/15098/files) | `pkg/iostreams/iostreams.go`, `pkg/iostreams/iostreams_test.go` |
| [Document duplicate events](https://github.com/cli/cli/pull/15094/files) | `pkg/cmd/event/listen/listen.go`, `skills/gh/SKILL.md` |

### Replay the sample

On 2026-11-20, the pagination order selected these 15 PR numbers. The last timestamp was shared with PR 15085. Keep 15086 and exclude 15085 when reproducing the fixed selection.

```text
15117 15111 15109 15108 15107 15105 15103 15102
15100 15098 15095 15094 15089 15087 15086
```

The creation window runs from `2026-11-17T19:19:51Z` through `2026-11-20T14:03:23Z`. Reconstruct the selected set from the creation window and the fixed IDs. For each of the four positive rows, `gh pr view NUMBER --repo cli/cli --json baseRefOid,headRefOid,files` returned the paths above and the following pins on the same date. PR descriptions and the GitHub Files changed view can change. The table records the observation at those pins.

| PR | Observed base tip | Observed head |
| --- | --- | --- |
| 15107 | `acee710547dcf7dfb6490afea77972187e74b819` | `ea7704b3a5a109db63b567670ffb9b239251dfb8` |
| 15103 | `acee710547dcf7dfb6490afea77972187e74b819` | `8adfa6237779f59c2e5e7349284e0842234ed3f9` |
| 15098 | `acee710547dcf7dfb6490afea77972187e74b819` | `213bebe276b060bb424308a6b61d746edf38ea63` |
| 15094 | `e1219499a578b69e3437adaa31cd60614e23c802` | `b11a0fb4cf95369b4460010a9cf4bbcdf432ffc1` |

File-change and review receipts remain text. Revisit versioned machine output when a caller needs to retain or replay both side observations. Any new format must be opt-in and preserve the existing quotation JSON.

## Human comparison trial

Use fresh PRs with explicit file-change claims. For each PR, record the submission and pin the base tip, merge base and head before reviewing. Use GitHub's **Files changed** view for the manual arm and the local review preview for the assisted arm, with the merge base as the comparison commit. Check both names of any displayed rename. Inspect discrepancies with `git diff --no-renames --name-status COMPARISON_COMMIT HEAD_COMMIT` and record unavailable evidence separately.

Use the [paired timing procedure in the product spec](spec.md#evaluation-and-decision-to-expand). Include proposal preparation, commit lookup, reading the result and resolving any gaps in the assisted time. Record verdict accuracy, inconclusive results and end-to-end time per pair. The sample and synthetic replay establish coverage and correctness on their examples. The pilot decision still requires the timing and accuracy evidence in the product spec.
