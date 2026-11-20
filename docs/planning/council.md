# Decisions from the planning review

These are competing arguments considered by one planner. They are decision aids for the owner. They carry no claim of independent expert review, user research or accessibility certification.

## Round 1 · What deserves to exist?

| Decision | Strongest case for expanding | Strongest objection | Ruling and reopening condition |
| --- | --- | --- | --- |
| First user | A security team has high-volume intake and a budget. | Private intake brings permissions, storage and support obligations before we know if a receipt saves time. | Serve a maintainer with a local clone. Reopen team intake when voluntary users identify a repeated handoff. |
| First claim | A flexible assistant could extract everything in the report. | Users cannot audit a verdict if the extractor silently shrinks the proposition. | Start with one user-specified exact quote. Evaluate extraction separately when input preparation dominates measured time. |
| Surface | A dashboard would make the project easier to demonstrate. | A solo maintainer must then operate accounts, updates and recovery for a task already performed in a terminal or PR. | Ship CLI evidence and Markdown export. Reopen visual navigation when reviewing many saved receipts becomes a measured problem. |
| Meaning of success | Increase the number of bad reports caught. | A deliberately wrong citation can accompany a real defect. A report-level score invites dismissal. | Measure claim-level errors and review time. Keep the submitted report open for human judgment. |
| Pilot partner | Recruit a well-known OSS project before coding. | The owner has no partner, and a project's past complaints do not imply consent. | Use synthetic fixtures and licensed public examples. Do not rely on upstream maintainers to label or run anything. |

## Round 2 · What can the evidence actually support?

| Decision | Argument | Counterexample | Ruling and reopening condition |
| --- | --- | --- | --- |
| Exact matching | Match raw bytes to keep the rule simple. | A contributor copies the same three lines into a Windows quote file. | Normalize CRLF on both sides, preserve everything else, record the rule; revisit with versioned evidence if users need whitespace-insensitive claims. |
| Missing path | Any failed lookup could yield a useful contradiction. | A shallow or damaged clone lacks a tree. | Contradict only with a complete tree witness for an absent component. If traversal hits an unsupported indirection, return can't check. |
| Non-directory intermediate | A regular file in the middle proves the remaining path cannot exist. | A symlink or submodule at that location changes what “the file” means to the reporter. | For v0.1 return can't check with the encountered kind for any non-tree intermediate. Keep the conservative rule uniform. |
| Immutable revision | Accept branches and tags for convenience. | Two readers resolve the same name to different bytes. | Require a full commit ID initially. Later a resolver may convert a named ref to an explicit, visible ID for confirmation. |
| Exit code | Nonzero on contradiction is easy to use as a merge gate. | A shell script drops the receipt or blocks an unrelated fix. | Exit zero for a completed receipt. Integration policy can interpret its verdict explicitly. |
| Source link | Infer a repository URL from origin and link every finding. | A private remote can leak internal names or credentials. | Emit portable locators locally; allow only explicit trusted forge mappings in the pilot. |
| Built-in verification | Execute report-supplied reproduction steps for stronger evidence. | A single clean run cannot rule out the reported behavior, and execution changes the product's trust obligations. | Keep submissions inert. For later CI evidence, bind observations to a known job, environment and revision. |
| Corpus labels | Use an existing “slop” list as negative ground truth. | A low-quality report can contain an accurate quote. | Label propositions by independent source inspection. Hold out repository families and publish mistakes. |
| Content hashes | Share hashes freely to aid deduplication. | A common guessed snippet can be tested against its hash. | Treat receipts as sensitive when the source is sensitive. Share only at the user's direction. |

## Round 3 · What does one person operate?

| Decision | Argument | Counterexample | Ruling and reopening condition |
| --- | --- | --- | --- |
| Infrastructure | Standardize on a hosted queue and persistent worker early. | The local checker needs neither, and an unattended service still needs incident response. | Make the installed CLI stateless. Use ephemeral jobs for an opt-in pilot only if the measured benefit clears the threshold. |
| Native support | Six archives make a six-platform support claim. | A cross-compiled binary can still fail to install or handle file paths on the target. | Record native smoke results separately, with preview status for untested pairs. |
| Accessibility | A CLI with plain text is inherently accessible. | Unlabeled links, wide layouts and ambiguous status text still slow nonvisual readers. | Allocate tasks for reading order, reflow and actual assistive-tool checks. State gaps when a device is unavailable. |
| Publication | Reuse one editable comment to limit noise. | Concurrent edits can make an authoritative-looking comment stale. | Preview first. Verify origin, freshness and ownership, then reconcile after writes. Disable the writer if this cannot be demonstrated. |
| Solo review | Require two reviewers for every release. | This would make a solo release impossible and could encourage rubber-stamping. | Require replayable evidence, a clean installation rehearsal and a correction path. Record a second review if one actually occurs. |
| Completeness | Treat every inventory row as a v0.1 requirement. | An inbox keyboard test has no subject until an inbox exists. | Gate on explicit milestone outcomes. Keep later questions attached to their triggering decision. |
| Reliability target | Promise an uptime target to reassure adopters. | Local execution has no central service to keep up, and the owner has no on-call rotation. | Measure completion, correctness, performance and recovery. State best-effort support. |

## Solo operating rehearsal

Take a synthetic “wrong quote” complaint received while the owner is away. The installed offline tool continues working. On return, use the advertised version and redacted fixture to rerun the original receipt, inspect the pinned object independently, and identify the first affected rule version. If the complaint is correct, pause publication, mark affected versions, publish a correction, add the case to regression coverage and rerun the holdout. A corrected release identifies which old receipts need replay. Downgrade or inspect manually while a fix is pending.

For a missed target, trim scope in this order: automated comments, optional installation channels, then unsupported storage configurations with an explicit inconclusive result. Preserve the distinction between incomplete checks and contradictions throughout. Owner-bound actions such as publishing a release or approving paid signing can wait; implementation tickets, fixtures and local verification can be done asynchronously by one person.

## Remaining empirical questions

The spec chooses defaults so work can proceed. Only measurement can tell us whether quote entry is quick enough, the object reader honors its budgets, nonvisual output is easy to navigate, or pilot comments save attention. The ticket that owns each experiment records the outcome and triggers the associated continue, restrict, or stop decision. The large register records considerations, not evidence that those experiments have passed.
