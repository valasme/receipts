# Public demo integration

The released CLI works locally. The GitHub adapter is an opt-in pilot for valasme/receipts, with read-only preview and public commenting switched off by default. The completed timing attempt failed the expansion gate. Keep both modes off until a fresh paired trial records completed reviews, at least 25% median time saving, accurate verdicts and replayable evidence. Review noise and privacy in the read-only pilot before enabling writes. [Pilot decision and evidence](verification.md#human-timing-and-pilot-decision)

A public issue or PR may contain one fenced block:

````markdown
```receipts
{"rev":"0123456789abcdef0123456789abcdef01234567","path":"README.md","quote":"# Receipts"}
```
````

Use the full claimed revision on an issue. For a PR from a branch in the demo repository, the supplied revision must equal the current head. Fork and deleted-source PRs are outside the pilot cohort. They produce an explanatory preview rather than loading a fork ref. Unavailable objects within the cohort remain inconclusive. The trusted workflow builds its own checker, reads current issue state from the public demo, and treats submission text as data. The job summary contains the receipt. Private reports belong in the offline CLI.

Set the repository variable RECEIPTS_PREVIEW to true for a qualified read-only trial. Set RECEIPTS_PUBLISH to true only after reviewing the shadow results. For first publication a maintainer applies the receipts:publish label to the individual submission. The writer consumes that label, recomputes the receipt, checks freshness, and updates its own marked comment. Removing the comment suppresses further publication until the label is applied again. Use workflow dispatch with the canonical decimal issue or PR number for manual reconciliation. Use digits without a leading zero or sign. Disable the publish variable to stop writes and the preview variable to stop all future processing; cancel any already-running publisher when responding to an incident.

A concurrent edit can briefly expose an outdated receipt. The writer rechecks after the API call and marks the old receipt stale. If the checker fails after a submission changes, the writer marks its previous receipt stale. A transient failure on the same input preserves the current receipt. On an API failure use the run status and current issue state to reconcile; the writer never blindly repeats an uncertain create. The pilot bounds each comment scan to 400 comments and stops on duplicate bot-owned markers. A repository using multiple workflows under the same bot identity must trust those workflows before enabling writes.

Local tests use a simulated API for repeated deliveries, concurrent edits, deleted comments, spoofed markers and ambiguous create responses. Those tests alone do not establish pilot effectiveness.
