package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"

	"github.com/valasme/receipts/internal/check"
)

const (
	maxBatchFile = 1 << 20
	maxClaims    = 16
	checkTimeout = 5 * time.Second
)

type batchResult struct {
	Receipt *check.Receipt `json:"receipt,omitempty"`
	Error   string         `json:"error,omitempty"`
}

func executeBatch(ctx context.Context, stdin io.Reader, stdout, stderr io.Writer, repo, file string, detailed bool) int {
	data, err := readInput(ctx, stdin, file, maxBatchFile, "batch")
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Check interrupted.")
		return 130
	}
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	rev, claims, err := readBatch(data)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}

	clock, cancel := context.WithTimeout(ctx, checkTimeout)
	defer cancel()
	inspection := check.NewInspection(clock, repo, buildVersion())
	defer inspection.Close()
	if err := inspection.ValidateSharedRevision(rev); err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	results := make([]batchResult, 0, len(claims))
	for _, item := range claims {
		if ctx.Err() != nil {
			break
		}
		fields, err := objectFields(item, "path", "quote")
		if err != nil {
			results = append(results, batchResult{Error: err.Error()})
			continue
		}
		quote, err := readQuotation(fields)
		if err != nil {
			results = append(results, batchResult{Error: err.Error()})
			continue
		}
		receipt, err := inspection.Verify(rev, quote.path, []byte(quote.text))
		if err != nil {
			results = append(results, batchResult{Error: err.Error()})
			continue
		}
		if !detailed {
			receipt = baseQuotationJSON(receipt)
		}
		results = append(results, batchResult{Receipt: &receipt})
	}
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Check interrupted.")
		return 130
	}
	return deliverJSON(ctx, stdout, stderr, struct {
		Schema  int           `json:"schema_major"`
		Results []batchResult `json:"results"`
	}{Schema: 1, Results: results})
}

func readBatch(data []byte) (string, []json.RawMessage, error) {
	fields, err := objectFields(data, "schema_major", "rev", "claims")
	if err != nil {
		return "", nil, fmt.Errorf("batch file: %w", err)
	}
	rev, ok := jsonString(fields["rev"])
	if string(fields["schema_major"]) != "1" || !ok {
		return "", nil, errors.New("invalid batch file; expected schema_major 1, rev, and claims")
	}
	if err := check.ValidateRevision(rev); err != nil {
		return "", nil, err
	}
	var claims []json.RawMessage
	if err := json.Unmarshal(fields["claims"], &claims); err != nil || len(claims) == 0 || len(claims) > maxClaims {
		return "", nil, fmt.Errorf("supply an array of 1 to %d claims", maxClaims)
	}
	return rev, claims, nil
}
