# Walk through a receipt

These are interface examples for the planned product. Identifiers are illustrative. The example repository has a committed file named src/example.go. The quotation file holds the two lines being asserted, with a newline after the closing brace. The working copy can contain newer text.

## Before submitting

A contributor copies the exact lines into excerpt.txt, obtains the full commit ID from the version they inspected, then supplies the local clone, revision, file path and quote file to the checker. The help example must show how to preserve UTF-8 and the final newline on each platform. If creating that file turns out to be the slow step, measure stdin and editor integrations before considering model extraction.

    receipts check --repo . --rev 0123456789abcdef0123456789abcdef01234567 --path src/example.go --quote-file excerpt.txt

Proposed default output:

    Verified · exact source quote
    src/example.go · lines 8–9 · first match
    Commit 0123456789abcdef0123456789abcdef01234567
    Blob 1111111111111111111111111111111111111111
    Compared the supplied quote with the committed file. CRLF and LF count as the same line ending.

The contributor can open the blob and compare the cited range. A maintainer who only has the receipt needs the original quote and repository to replay the check. A hash alone cannot reconstruct the input.

## When the wording differs

    Contradicted · exact source quote
    src/example.go · searched the complete committed file
    Commit 0123456789abcdef0123456789abcdef01234567
    Blob 1111111111111111111111111111111111111111
    The supplied quotation does not occur here.
    Check the revision, file path and final newline.

If the contributor corrects the citation, the rerun produces a new receipt bound to that input. Keep the original report eligible for human review even if the quotation differs.

## When a decisive answer is impossible

    Can't check · revision unavailable
    src/example.go
    Requested commit 0123456789abcdef0123456789abcdef01234567
    Provide a local clone containing this commit and rerun.

This is a completed receipt. Invalid command syntax instead prints an explanation to stderr, for example “A full commit ID is required. Copy it from git rev-parse HEAD if you mean the current commit.” For an output-write failure the caller discards the partial document and retries to a writable destination.

## Machine consumer

Illustrative version-1 payload for a successful check. The quote digest and Git object IDs below are example values. The normalized digest lets a party who already has the quote confirm which text was used. The renderer can omit a digest in its short human view.

```json
{
  "schema_major": 1,
  "checker_version": "0.1.0",
  "claim": {
    "kind": "exact_source_quote",
    "requested_commit": "0123456789abcdef0123456789abcdef01234567",
    "path": "src/example.go",
    "quote_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "comparison_rule": "utf8-crlf-to-lf-v1",
  "verdict": "verified",
  "reason": "quote_found",
  "evidence": {
    "object_format": "sha1",
    "observed_commit": "0123456789abcdef0123456789abcdef01234567",
    "blob_id": "1111111111111111111111111111111111111111",
    "lines": { "start": 8, "end": 9 }
  }
}
```

Machine verdicts are `verified`, `contradicted`, and `cant_check`. Example reasons are `quote_found`, `quote_absent`, `path_absent`, `revision_unavailable`, `unsupported_kind`, `object_unavailable` and `resource_limit`. Each version of the schema documents its reason-to-verdict mapping. A publication adapter refuses an unknown mapping. A generic local viewer can show an unfamiliar reason as text under a recognized verdict.

## Optional GitHub preview

**Verified · exact source quote**
Source file and line range form one link to the pinned blob. The visible text identifies the repository-relative path, lines and a readable commit abbreviation. The full revision is available in the receipt. A final sentence explains the comparison rule. A screen reader encounters the verdict before the link, and a contributor sees one factual result without a personal score.

If an edited submission no longer matches the receipt's input digest, the pilot labels the prior receipt stale and queues the new check. If publishing is disabled or unavailable the locally rendered Markdown remains available for the maintainer to inspect and share deliberately.
