# Receipts planning index

**Build one dependable local answer first.** A maintainer supplies a quote, repository path and full commit ID, then receives a scoped verdict with the evidence needed to repeat it. An inaccurate citation changes the verdict on that citation only. The local release is a useful stopping point for a one-person project.

| Read this | Decision it supports |
| --- | --- |
| [Local agent workflow](agent-workflow.md) · [tracked spec](https://github.com/valasme/receipts/issues/18) | How agents propose and replay exact quotations in a local clone |
| [Product and engineering spec](spec.md) · [tracked spec](https://github.com/valasme/receipts/issues/1) | What the owner can promise, how to prove it, and when to ship |
| [Walk through four receipt surfaces](receipt-examples.md) | What a contributor sees in success, mismatch, unresolved and export flows |
| [Council decisions](council.md) | Which objections changed the plan and what would reopen a choice |
| [Maintainer and debugging checklist](maintainer-checklist.md) | How to diagnose a broken command, which tools exist and which skills the release still needs to demonstrate |
| [520-point review inventory](review-inventory.md) | Which individual concerns belong to local alpha, release, pilot or later discovery |

The [implementation verification record](../verification.md) gives the source revision, test outcomes, council decisions and human evidence still needed.

## Infrastructure pre-alpha

[Readiness review and comparison with the original brief](readiness-review.md) · [GitHub milestone](https://github.com/valasme/receipts/milestone/1)

This track can finish before the claim checker. Start with PA01 for the requested infrastructure release. Its dependencies are independent of the product tickets below.

| Ticket | Outcome | Blocked by |
| --- | --- | --- |
| [PA01](https://github.com/valasme/receipts/issues/11) | Starter CLI and bundled documentation | None |
| [PA02](https://github.com/valasme/receipts/issues/12) | Same-revision native CI and six-target release candidate | PA01 |
| [PA03](https://github.com/valasme/receipts/issues/13) | Verified installation, upgrades and removal across preview channels | PA02 |
| [PA04](https://github.com/valasme/receipts/issues/14) | Public prerelease, independent consumer checks and correction drill | PA03 |

## Solo work queue

Take one eligible ticket at a time. Completion means attaching the evidence in the ticket and closing it after its checks pass. The ticket graph permits either T03 or T04 after T02. Prefer T04 first if the object reader's bounds are uncertain. A ready label describes the ticket's completeness; the dependency links still govern when work starts.

| Ticket | Verifiable outcome | Blocked by |
| --- | --- | --- |
| [T01](https://github.com/valasme/receipts/issues/2) | Verify a supplied quote in a pinned local commit | None |
| [T02](https://github.com/valasme/receipts/issues/3) | Distinguish contradictions from unavailable evidence | T01 |
| [T03](https://github.com/valasme/receipts/issues/4) | Export a readable receipt and a stable JSON contract | T02 |
| [T04](https://github.com/valasme/receipts/issues/5) | Return bounded, private results on incomplete and hostile inputs | T02 |
| [T05](https://github.com/valasme/receipts/issues/6) | Replay the receipt contract across native operating systems | T03, T04 |
| [T06](https://github.com/valasme/receipts/issues/7) | Measure correctness and solo review time on held-out claims | T03, T04 |
| [T07](https://github.com/valasme/receipts/issues/8) | Rehearse installation, release correction and rollback | T05, T06 |
| [T08](https://github.com/valasme/receipts/issues/9) | Preview an opted-in GitHub submission in read-only mode | T06, T07 |
| [T09](https://github.com/valasme/receipts/issues/10) | Publish and reconcile one current receipt comment | T08 |

T01–T07 cover the local release. T08–T09 form an optional GitHub pilot. Each pilot ticket has a product decision gate as well as its tracker dependencies. The last 40 inventory items cover ideas that need fresh demand before scheduling.

## Readiness record for one person

For each milestone, record the tested checker revision, corpus or fixture version, platform, actual result, known gaps and decision in its ticket. Use “passed”, “failed”, “untested” or “deferred with reason” and link to the evidence. Keep confidential examples local; public evidence should use redacted or synthetic cases.

- **Local usefulness.** Time the complete job from reading a claim to understanding the receipt. Include finding the commit and preparing the quote. Track the median of the 12 paired percentage savings, calculated as (manual time − assisted time) / manual time. A result below 25% holds the GitHub pilot.
- **Verdict correctness.** One false contradiction on the holdout blocks shipment. A surviving set of zero errors warrants reporting the sample size, never a guarantee about all future reports.
- **Accessible operation.** Complete success and recovery flows using a keyboard, a narrow view and available assistive technology. Publish the tested combinations and any gaps.
- **Recovery.** Rehearse a bad archive, incorrect historical verdict and a failed publication. Document the smallest action that contains the fault and how users determine which receipts need replay.
- **Capacity.** The owner may defer a new platform, package channel or adapter if there is no credible way to maintain it. Local-only operation has no standing cloud bill or on-call requirement.

## Planning review

The starter review predates implementation. The [published limited preview](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.2) includes the local quotation checker. The [qualification record](../verification.md) covers correctness, native installs, limits and open pilot gates. Native signing is deferred until the owner approves v1. [Signing decision](../adr/0002-defer-native-signing-until-v1.md) The 12 paired human timings are outstanding.
