package check

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"strings"
)

type FileChangeReceipt struct {
	path             string
	comparison, head fileObservation
	verdict          fileChangeVerdict
}

type fileChangeVerdict uint8

const (
	changeUnchecked fileChangeVerdict = iota
	changeContradicted
	changeVerified
)

type fileObservation struct {
	commit  string
	entry   pathEntry
	failure string
	detail  string
}

func VerifyFileChange(ctx context.Context, repo, comparison, head, path string) (FileChangeReceipt, error) {
	if err := ValidateRevision(comparison); err != nil {
		return FileChangeReceipt{}, fmt.Errorf("comparison commit: %w", err)
	}
	if err := Validate(head, path); err != nil {
		return FileChangeReceipt{}, err
	}
	receipt := FileChangeReceipt{
		path:       path,
		comparison: fileObservation{commit: strings.ToLower(comparison)},
		head:       fileObservation{commit: strings.ToLower(head)},
	}
	timeout := receipt
	timeout.comparison.failure = errLimit.Error()
	timeout.head.failure = errLimit.Error()
	timeout.comparison.detail = string(timeLimit)
	timeout.head.detail = string(timeLimit)
	if ctx.Err() != nil {
		return timeout, nil
	}
	// Allow the review deadline to expire even if a filesystem read blocks.
	type result struct {
		receipt FileChangeReceipt
		err     error
	}
	done := make(chan result, 1)
	go func() {
		checked, err := inspectFileChange(ctx, repo, receipt)
		done <- result{checked, err}
	}()
	select {
	case checked := <-done:
		if ctx.Err() == nil {
			return checked.receipt, checked.err
		}
	case <-ctx.Done():
	}
	return timeout, nil
}

func inspectFileChange(ctx context.Context, repo string, receipt FileChangeReceipt) (FileChangeReceipt, error) {
	s, err := openStore(ctx, repo)
	if err != nil {
		reason := objectFailure(err, "repository_unavailable")
		receipt.comparison.failure = reason
		receipt.head.failure = reason
		receipt.comparison.detail = failureDetail(err)
		receipt.head.detail = failureDetail(err)
		return receipt, nil
	}
	defer s.root.Close()
	if err := receipt.comparison.inspect(s, receipt.path); err != nil {
		return FileChangeReceipt{}, fmt.Errorf("comparison commit: %w", err)
	}
	if err := receipt.head.inspect(s, receipt.path); err != nil {
		return FileChangeReceipt{}, fmt.Errorf("head commit: %w", err)
	}
	if receipt.comparison.failure == "" && receipt.head.failure == "" {
		before, after := receipt.comparison.entry, receipt.head.entry
		receipt.verdict = changeContradicted
		if before.id != after.id || before.mode != after.mode {
			receipt.verdict = changeVerified
		}
	}
	return receipt, nil
}

func (side *fileObservation) inspect(s *store, path string) error {
	treeID, err := s.commitTree(side.commit)
	if err != nil {
		side.detail = failureDetail(err)
		switch {
		case errors.Is(err, errNotCommit):
			return err
		case errors.Is(err, errCommitTree):
			side.failure = "object_unavailable"
		default:
			side.failure = objectFailure(err, "revision_unavailable")
		}
		return nil
	}
	side.entry, err = s.findPath(treeID, path)
	entry := side.entry
	switch {
	case err != nil:
		side.failure = objectFailure(err, "object_unavailable")
		side.detail = failureDetail(err)
	case entry.id == "":
		// The verified tree proves this component is absent.
	case entry.blocked || (entry.mode != "100644" && entry.mode != "100755" && entry.mode != "120000"):
		side.failure = "unsupported_kind"
	default:
		if _, err := s.readBlob(entry.id); err != nil {
			side.failure = objectFailure(err, "object_unavailable")
			side.detail = failureDetail(err)
		}
	}
	return nil
}

func (r FileChangeReceipt) Text() string {
	verdict, reason := "Can't check", "The evidence is incomplete or unsupported."
	switch r.verdict {
	case changeContradicted:
		verdict, reason = "Contradicted", "The path is the same in both commits."
	case changeVerified:
		verdict, reason = "Verified", "The path differs between the two commits."
	}
	var out strings.Builder
	fmt.Fprintf(&out, "%s · file changed\nPath %s\n", verdict, strconv.QuoteToGraphic(r.path))
	r.comparison.writeEvidence(&out, "Comparison")
	r.head.writeEvidence(&out, "Head")
	fmt.Fprintln(&out, "Comparison rule · committed blob ID and Git mode at the exact path")
	fmt.Fprintln(&out, reason)
	return out.String()
}

func (side fileObservation) writeEvidence(out *strings.Builder, label string) {
	fmt.Fprintf(out, "%s commit %s\n", label, side.commit)
	entry := side.entry
	switch {
	case entry.tree == "":
	case entry.id == "":
		fmt.Fprintf(out, "  Tree %s · missing %s\n", entry.tree, strconv.QuoteToGraphic(entry.component))
	case side.failure == "":
		fmt.Fprintf(out, "  Tree %s · mode %s · Blob %s\n", entry.tree, entry.mode, entry.id)
	default:
		fmt.Fprintf(out, "  Tree %s · entry %s · mode %s · Object %s\n",
			entry.tree, strconv.QuoteToGraphic(entry.component), entry.mode, entry.id)
	}
	if side.failure != "" {
		fmt.Fprintf(out, "  %s\n", side.failure)
		if side.detail != "" {
			fmt.Fprintf(out, "  %s\n", side.detail)
		}
	}
}
