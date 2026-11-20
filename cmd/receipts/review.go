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
	start, end     int
	origin         string
	quote          *quotation
	citation       string
	statement      string
	fileChangePath string
}

func executeReview(ctx context.Context, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("review", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	var repo, rev, comparison, submissionFile, proposalFile string
	provided, parse := registerOptions(flags, stringOption{"repo", &repo, "."}, stringOption{"rev", &rev, ""},
		stringOption{"compare", &comparison, ""},
		stringOption{"submission", &submissionFile, ""}, stringOption{"proposal", &proposalFile, ""})
	if err := parse(args); err != nil {
		fmt.Fprintln(stderr, "Invalid review arguments:", err)
		return 2
	}
	if repo == "" || submissionFile == "" || proposalFile == "" || (submissionFile == "-" && proposalFile == "-") {
		fmt.Fprintln(stderr, "Supply --submission, --proposal, and --rev. At most one input may use stdin. Run receipts review --help.")
		return 2
	}
	if err := check.ValidateRevision(rev); err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	if provided["compare"] {
		if err := check.ValidateRevision(comparison); err != nil {
			fmt.Fprintln(stderr, "comparison commit:", err)
			return 2
		}
	}
	preview, err := review(ctx, stdin, repo, rev, comparison, submissionFile, proposalFile)
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Review interrupted.")
		return 130
	}
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	return deliver(ctx, stdout, stderr, preview, "Review interrupted.")
}

func review(ctx context.Context, stdin io.Reader, repo, rev, comparison, submissionFile, proposalFile string) (string, error) {
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
	hasFileChanges := slices.ContainsFunc(entries, func(entry reviewEntry) bool {
		return entry.fileChangePath != ""
	})
	if comparison == "" && hasFileChanges {
		return "", errors.New("file-change claims require --compare with a full commit ID")
	}
	clock, cancel := context.WithTimeout(ctx, checkTimeout)
	defer cancel()
	var out strings.Builder
	fmt.Fprintf(&out, "Review preview\nRequested commit %s\n", strings.ToLower(rev))
	if hasFileChanges {
		fmt.Fprintf(&out, "Comparison commit %s\n", strings.ToLower(comparison))
	} else if comparison != "" {
		fmt.Fprintln(&out, "Comparison commit unused.")
	}
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
		switch {
		case entry.fileChangePath != "":
			receipt, err := check.VerifyFileChange(clock, repo, comparison, rev, entry.fileChangePath)
			if err != nil {
				return "", fmt.Errorf("proposal file-change claim at submission line %d: %w", entry.start, err)
			}
			out.WriteString(receipt.Text())
			fmt.Fprintln(&out, "Claim checked · The file at this exact path changed between the two commits.")
			writeReviewContext(&out, "Submission statement", entry.statement)
		case entry.quote != nil:
			receipt, err := check.Verify(clock, repo, rev, entry.quote.path, []byte(entry.quote.text), version)
			if err != nil {
				return "", fmt.Errorf("proposal claim at submission line %d: %w", entry.start, err)
			}
			out.WriteString(receipt.Text())
			fmt.Fprintln(&out, "Claim checked · The committed file contains the exact quotation.")
			writeReviewContext(&out, "Submission citation", entry.citation)
		default:
			writeReviewContext(&out, "Unresolved", entry.statement)
		}
	}
	return out.String(), nil
}

// Long context uses quoted continuation lines. Control and bidi characters
// remain escaped, including newlines within one quoted segment.
func writeReviewContext(out *strings.Builder, label, value string) {
	quoted := strconv.QuoteToGraphic(value)
	if len(label)+len(quoted)+4 <= 72 {
		fmt.Fprintln(out, label+" ·", quoted)
		return
	}
	fmt.Fprintln(out, label)
	start, width := 0, 0
	space, beforeSpace := 0, 0
	var scratch [16]byte
	for index, r := range value {
		size := len(strconv.AppendQuoteRuneToGraphic(scratch[:0], r)) - 2
		if r == '"' {
			size++
		}
		if width+size > 34 {
			end, consumed := index, width
			if space > start && width-beforeSpace+size <= 34 {
				end, consumed = space, beforeSpace
			}
			fmt.Fprintln(out, "  "+strconv.QuoteToGraphic(value[start:end]))
			start, width = end, width-consumed
		}
		width += size
		if r == ' ' || r == '\n' || r == '\t' {
			space, beforeSpace = index+1, width
		}
	}
	fmt.Fprintln(out, "  "+strconv.QuoteToGraphic(value[start:]))
}

func parseReviewEntries(data []byte, lines []string) ([]reviewEntry, error) {
	fields, err := objectFields(data, "schema_major", "claims", "unresolved", "file_changes")
	if err != nil {
		return nil, fmt.Errorf("proposal: %w", err)
	}
	if raw := fields["schema_major"]; raw != nil && string(raw) != "1" {
		return nil, errors.New("proposal requires schema_major 1 when supplied")
	}
	var claims, unresolved, fileChanges []json.RawMessage
	if json.Unmarshal(fields["claims"], &claims) != nil || claims == nil {
		return nil, errors.New("proposal requires a claims array")
	}
	if json.Unmarshal(fields["unresolved"], &unresolved) != nil || unresolved == nil {
		return nil, errors.New("proposal requires an unresolved array")
	}
	if raw := fields["file_changes"]; raw != nil && (json.Unmarshal(raw, &fileChanges) != nil || fileChanges == nil) {
		return nil, errors.New("invalid proposal file_changes array")
	}
	count := len(claims) + len(unresolved) + len(fileChanges)
	if count > maxReviewEntries {
		return nil, fmt.Errorf("proposal may contain at most %d total entries", maxReviewEntries)
	}
	entries := make([]reviewEntry, 0, count)
	for index, raw := range claims {
		origin := fmt.Sprintf("proposal claim %d", index+1)
		fields, err := objectFields(raw, "path", "quote", "source_lines")
		if err != nil {
			return nil, fmt.Errorf("%s: %w", origin, err)
		}
		source, entry := reviewSpan(fields["source_lines"], lines)
		if source == nil {
			return nil, fmt.Errorf("%s requires a valid source_lines range", origin)
		}
		quote, err := readQuotation(fields)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", origin, err)
		}
		if strings.ContainsRune(quote.path, '`') {
			return nil, fmt.Errorf("%s path contains a backtick. Use receipts check for this path", origin)
		}
		if !matchesCitation(source, quote) {
			if !strings.HasSuffix(quote.text, "\n") && matchesCitation(source, quotation{quote.path, quote.text + "\n"}) {
				return nil, fmt.Errorf("%s quote must include the LF before the closing fence. Use receipts check for quotations without a final LF", origin)
			}
			return nil, fmt.Errorf("%s does not match an exact source citation in the submission", origin)
		}
		entry.origin = origin
		entry.quote = &quote
		entry.citation = source[0]
		entries = append(entries, entry)
	}
	for index, raw := range fileChanges {
		origin := fmt.Sprintf("proposal file-change claim %d", index+1)
		fields, err := objectFields(raw, "path", "statement", "source_lines")
		if err != nil {
			return nil, fmt.Errorf("%s: %w", origin, err)
		}
		source, entry := reviewSpan(fields["source_lines"], lines)
		if source == nil {
			return nil, fmt.Errorf("%s requires a valid source_lines range", origin)
		}
		path, ok := jsonString(fields["path"])
		if !ok || path == "" {
			return nil, fmt.Errorf("%s requires path as a nonempty exact JSON string", origin)
		}
		if strings.ContainsRune(path, '`') {
			return nil, fmt.Errorf("%s path contains a backtick, which the proposal syntax cannot represent", origin)
		}
		statement, ok := matchedStatement(fields["statement"], source)
		if !ok || !namesPath(statement, path) {
			return nil, fmt.Errorf("%s does not match a statement naming its exact path", origin)
		}
		entry.origin = origin
		entry.fileChangePath = path
		entry.statement = statement
		entries = append(entries, entry)
	}
	for index, raw := range unresolved {
		origin := fmt.Sprintf("unresolved entry %d", index+1)
		fields, err := objectFields(raw, "statement", "source_lines")
		if err != nil {
			return nil, fmt.Errorf("%s: %w", origin, err)
		}
		source, entry := reviewSpan(fields["source_lines"], lines)
		if source == nil {
			return nil, fmt.Errorf("%s requires a valid source_lines range", origin)
		}
		statement, ok := matchedStatement(fields["statement"], source)
		if !ok {
			return nil, fmt.Errorf("%s statement does not match the submission text", origin)
		}
		entry.origin = origin
		entry.statement = statement
		entries = append(entries, entry)
	}
	slices.SortStableFunc(entries, func(a, b reviewEntry) int { return a.start - b.start })
	for i := 1; i < len(entries); i++ {
		a, b := entries[i-1], entries[i]
		if b.start <= a.end {
			return nil, fmt.Errorf("proposal source spans must not overlap: %s (lines %d–%d) and %s (lines %d–%d)", a.origin, a.start, a.end, b.origin, b.start, b.end)
		}
	}
	return entries, nil
}

func matchedStatement(raw json.RawMessage, source []string) (string, bool) {
	statement, ok := jsonString(raw)
	statement = strings.ReplaceAll(statement, "\r\n", "\n")
	return statement, ok && source != nil && strings.TrimSpace(statement) != "" && strings.Join(source, "\n") == statement
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
	if !namesPath(lines[0], quote.path) {
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

func namesPath(statement, path string) bool {
	parts := strings.SplitN(statement, "`", 4)
	return len(parts) == 3 && parts[1] == path
}
