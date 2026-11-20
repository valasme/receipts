package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"slices"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/valasme/receipts/internal/check"
)

const (
	maxReviewFile    = 1 << 20
	maxReviewEntries = 16
)

type reviewEntry struct {
	start, end int
	quote      *quotation
	citation   string
	statement  string
}

func executeReview(ctx context.Context, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("review", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	var repo, rev, submissionFile, proposalFile string
	registerOptions(flags, stringOption{"repo", &repo, "."}, stringOption{"rev", &rev, ""},
		stringOption{"submission", &submissionFile, ""}, stringOption{"proposal", &proposalFile, ""})
	if flags.Parse(args) != nil || flags.NArg() != 0 || repo == "" || submissionFile == "" || proposalFile == "" || (submissionFile == "-" && proposalFile == "-") {
		fmt.Fprintln(stderr, "Supply --submission, --proposal, and --rev. At most one input may use stdin. Run receipts review --help.")
		return 2
	}
	if err := check.ValidateRevision(rev); err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	preview, err := review(ctx, stdin, repo, rev, submissionFile, proposalFile)
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Review interrupted.")
		return 130
	}
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	written := make(chan error, 1)
	go func() { written <- writeComplete(stdout, preview) }()
	select {
	case err = <-written:
	case <-ctx.Done():
	}
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Review interrupted.")
		return 130
	}
	if err != nil {
		fmt.Fprintln(stderr, "Could not write complete output.")
		return 1
	}
	return 0
}

func review(ctx context.Context, stdin io.Reader, repo, rev, submissionFile, proposalFile string) (string, error) {
	body, err := readInput(ctx, stdin, submissionFile, maxReviewFile, "submission")
	if err != nil {
		return "", fmt.Errorf("submission: %w", err)
	}
	if !utf8.Valid(body) || strings.ContainsRune(string(body), 0) {
		return "", errors.New("submission must be UTF-8 text without NUL bytes")
	}
	data, err := readInput(ctx, stdin, proposalFile, maxReviewFile, "proposal")
	if err != nil {
		return "", fmt.Errorf("proposal: %w", err)
	}
	entries, err := parseReviewEntries(data, strings.Split(strings.ReplaceAll(string(body), "\r\n", "\n"), "\n"))
	if err != nil {
		return "", err
	}
	clock, cancel := context.WithTimeout(ctx, checkTimeout)
	defer cancel()
	var out strings.Builder
	fmt.Fprintf(&out, "Review preview\nRequested commit %s\n", rev)
	if len(entries) == 0 {
		fmt.Fprintln(&out, "No claims or unresolved statements were proposed.")
	}
	version := buildVersion()
	for _, entry := range entries {
		if err := ctx.Err(); err != nil {
			return "", err
		}
		fmt.Fprintln(&out)
		if entry.start == entry.end {
			fmt.Fprintf(&out, "Submission line %d\n", entry.start)
		} else {
			fmt.Fprintf(&out, "Submission lines %d–%d\n", entry.start, entry.end)
		}
		if entry.quote == nil {
			fmt.Fprintln(&out, "Unresolved ·", strconv.QuoteToGraphic(entry.statement))
			continue
		}
		receipt, err := check.Verify(clock, repo, rev, entry.quote.path, []byte(entry.quote.text), version)
		if err != nil {
			return "", fmt.Errorf("proposal claim at submission line %d: %w", entry.start, err)
		}
		out.WriteString(receipt.Text())
		fmt.Fprintln(&out, "Citation ·", strconv.QuoteToGraphic(entry.citation))
	}
	return out.String(), nil
}

func parseReviewEntries(data []byte, lines []string) ([]reviewEntry, error) {
	fields := objectFields(data, "claims", "unresolved")
	var claims, unresolved []json.RawMessage
	if json.Unmarshal(fields["claims"], &claims) != nil || json.Unmarshal(fields["unresolved"], &unresolved) != nil || claims == nil || unresolved == nil {
		return nil, errors.New("invalid proposal; expected claims and unresolved arrays")
	}
	if len(claims)+len(unresolved) > maxReviewEntries {
		return nil, fmt.Errorf("proposal may contain at most %d total entries", maxReviewEntries)
	}
	entries := make([]reviewEntry, 0, len(claims)+len(unresolved))
	for index, raw := range claims {
		fields := objectFields(raw, "path", "quote", "source_lines")
		source, entry := reviewSpan(fields["source_lines"], lines)
		quote, ok := readQuotation(fields)
		if !ok || !matchesCitation(source, quote) {
			return nil, fmt.Errorf("proposal claim %d does not match an exact source citation in the submission", index+1)
		}
		entry.quote = &quote
		entry.citation = source[0]
		entries = append(entries, entry)
	}
	for index, raw := range unresolved {
		fields := objectFields(raw, "statement", "source_lines")
		source, entry := reviewSpan(fields["source_lines"], lines)
		statement, ok := jsonString(fields["statement"])
		statement = strings.ReplaceAll(statement, "\r\n", "\n")
		if !ok || source == nil || strings.TrimSpace(statement) == "" || strings.Join(source, "\n") != statement {
			return nil, fmt.Errorf("unresolved entry %d does not match the submission text", index+1)
		}
		entry.statement = statement
		entries = append(entries, entry)
	}
	slices.SortFunc(entries, func(a, b reviewEntry) int { return a.start - b.start })
	for i := 1; i < len(entries); i++ {
		if entries[i].start <= entries[i-1].end {
			return nil, errors.New("proposal source spans must not overlap")
		}
	}
	return entries, nil
}

func reviewSpan(raw json.RawMessage, lines []string) ([]string, reviewEntry) {
	var span []int
	if json.Unmarshal(raw, &span) != nil || len(span) != 2 || span[0] < 1 || span[1] < span[0] || span[1] > len(lines) {
		return nil, reviewEntry{}
	}
	return lines[span[0]-1 : span[1]], reviewEntry{start: span[0], end: span[1]}
}

func matchesCitation(lines []string, quote quotation) bool {
	if len(lines) < 4 || (lines[1] != "```" && lines[1] != "```text") || lines[len(lines)-1] != "```" {
		return false
	}
	attribution := strings.Split(lines[0], "`")
	if len(attribution) != 3 || attribution[1] != quote.path {
		return false
	}
	quoted := lines[2 : len(lines)-1]
	for _, line := range quoted {
		if strings.HasPrefix(strings.TrimLeft(line, " \t"), "```") {
			return false
		}
	}
	return strings.Join(quoted, "\n")+"\n" == strings.ReplaceAll(quote.text, "\r\n", "\n")
}
