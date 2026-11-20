# Local agent workflow for exact quotations

## Problem

An agent can call the existing checker, but it must assemble flags and preserve the quote in another file. A maintainer needs one portable claim to replay and a way to triage several quotations from one submission.

## Solution and user stories

1. As an agent user, I can save a literal quotation with its pinned revision and path, then replay it from a local clone.
2. As a maintainer, I can check a bounded set of quotations at a caller-selected commit and match each result to the original proposal.
3. As an integrator, I can distinguish malformed items from valid claims with inconclusive evidence.
4. As a reviewer, I can trace a proposal to the original submission and see which statements the example leaves unresolved.
5. As an existing caller, I can keep using the existing flags, exit status and receipt schema.

## Council and grilling decisions

Product, contract and evidence reviewers raised three decisions. The existing CLI and its fixtures establish the interface and test seam, so the work can proceed directly to process tests.

| Question | Decision | Reason |
| --- | --- | --- |
| Who controls the scope? | The caller chooses the local repository and pins the commit when assembling the claim file or batch. A batch has one commit. The agent proposes paths and literal quotes. | A submission can cite the wrong branch or tell the agent to change scope. Keep the commit visible in the saved input and every completed receipt. |
| How does a batch fail? | Reject a malformed envelope with exit 2 and empty stdout. Once admitted, emit one ordered result per item, with a separate error for invalid claims. Output interruption or failure follows the existing process contract. | A bad item should leave the rest replayable. Only evidence can produce a verdict. |
| What counts as an agent test? | Run a fresh agent on synthetic submission text and format instructions. Check its captured proposal against independently inspected Git objects, then replay the same proposal in credential-free CI. | A live run proves the handoff. A frozen fixture measures deterministic checking. |

## Contract and testing decisions

- Keep the existing verifier and receipt schema. Test through the CLI process against a temporary Git repository. For the same checker version, successful single-file JSON is byte-identical to legacy input.
- Version the input. Take input from a named file or stdin, validate exact field names, reject duplicates, malformed UTF-8, unpaired UTF-16 surrogate escapes, trailing JSON, and oversized input. Quotes preserve whitespace and final newlines under the existing comparison rule. The input files can contain sensitive quotes.
- Accept 1–16 batch claims under a 1 MiB document limit with a shared five-second repository lookup window. Each ordered result contains either an existing receipt or a safe input error. Emit one complete JSON document with a trailing LF. The successful batch exit describes delivery, independent of verdicts and per-item errors.
- Exercise a real and a fabricated multiline citation, an unsupported source object and an unresolved behavioral assertion. Preserve source lines in the example's proposal. Confirm that the batch receipts equal individual replays and that Git independently supports the expected outcomes.
- Run the existing corpus and new process tests on the six native targets. Keep the GitHub pilot decision under the parent release plan. Submitted instructions remain text. This milestone requires no provider credentials, hosting, submission execution or publication.

## Follow-up

Reassess extraction coverage and ordinary review time before enabling a live pilot. A single synthetic run establishes the handoff only.
