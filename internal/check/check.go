package check

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"strings"
	"unicode"
	"unicode/utf8"
)

const MaxQuote = 64 << 10

type Claim struct {
	Kind        string `json:"kind"`
	Revision    string `json:"requested_commit"`
	Path        string `json:"path"`
	QuoteDigest string `json:"quote_sha256"`
}
type Lines struct {
	Start int `json:"start"`
	End   int `json:"end"`
}
type Evidence struct {
	Format  string `json:"object_format,omitempty"`
	Commit  string `json:"observed_commit,omitempty"`
	Blob    string `json:"blob_id,omitempty"`
	Tree    string `json:"tree_id,omitempty"`
	Missing string `json:"missing_component,omitempty"`
	Lines   *Lines `json:"lines,omitempty"`
}
type Receipt struct {
	Schema   int      `json:"schema_major"`
	Version  string   `json:"checker_version"`
	Claim    Claim    `json:"claim"`
	Rule     string   `json:"comparison_rule"`
	Verdict  string   `json:"verdict"`
	Reason   string   `json:"reason"`
	Evidence Evidence `json:"evidence"`
}

func normalize(b []byte) []byte { return bytes.ReplaceAll(b, []byte("\r\n"), []byte("\n")) }

const resolveCommitHint = " Run git rev-parse --verify 'TAG^{commit}' with your tag or branch, then supply the resulting commit ID."

func ValidateRevision(rev string) error {
	if len(rev) == 64 {
		return errors.New("SHA-256 repositories are unsupported; supply a SHA-1 commit ID")
	}
	if len(rev) != 40 {
		return errors.New("supply a full 40-digit commit ID." + resolveCommitHint)
	}
	if _, err := hex.DecodeString(rev); err != nil {
		return errors.New("commit ID must be hexadecimal")
	}
	return nil
}

func Validate(rev, path string) error {
	if err := ValidateRevision(rev); err != nil {
		return err
	}
	if !fs.ValidPath(path) || path == "." || strings.Contains(path, "\\") || (len(path) > 1 && path[1] == ':') || len(path) > 4096 || strings.Count(path, "/") >= 128 {
		return errors.New("supply a repository-relative file path using slash separators")
	}
	for _, r := range path {
		if unicode.IsControl(r) || unicode.Is(unicode.Cf, r) || r == '\u2028' || r == '\u2029' {
			return errors.New("path contains an unsupported control character")
		}
	}
	return nil
}

func Verify(ctx context.Context, repo, rev, path string, quote []byte, version string) (Receipt, error) {
	if err := Validate(rev, path); err != nil {
		return Receipt{}, err
	}
	quote = normalize(quote)
	if len(quote) == 0 || len(quote) > MaxQuote || bytes.IndexByte(quote, 0) >= 0 || !utf8.Valid(quote) {
		return Receipt{}, errors.New("supply 1 to 65536 bytes of UTF-8 quote text without NUL")
	}
	rev = strings.ToLower(rev)
	digest := sha256.Sum256(quote)
	r := Receipt{Schema: 1, Version: version, Rule: "utf8-crlf-to-lf-v1", Claim: Claim{"exact_source_quote", rev, path, hex.EncodeToString(digest[:])}, Verdict: "cant_check", Reason: "revision_unavailable"}
	if ctx.Err() != nil {
		return unresolved(r, errLimit), nil
	}
	// A blocking filesystem read can outlive a cooperative deadline.
	// Return the inconclusive receipt on time.
	type result struct {
		receipt Receipt
		err     error
	}
	done := make(chan result, 1)
	go func() { checked, err := inspect(ctx, repo, r, quote); done <- result{checked, err} }()
	select {
	case completed := <-done:
		if ctx.Err() != nil {
			return unresolved(r, errLimit), nil
		}
		return completed.receipt, completed.err
	case <-ctx.Done():
		return unresolved(r, errLimit), nil
	}
}

func inspect(ctx context.Context, repo string, r Receipt, quote []byte) (Receipt, error) {
	rev, path := r.Claim.Revision, r.Claim.Path
	s, err := openStore(ctx, repo)
	if err != nil {
		r.Reason = "repository_unavailable"
		return unresolved(r, err), nil
	}
	defer s.root.Close()
	treeID, err := s.commitTree(rev)
	if err != nil {
		if errors.Is(err, errNotCommit) {
			return Receipt{}, err
		}
		if errors.Is(err, errCommitTree) {
			r.Reason = "object_unavailable"
		}
		return unresolved(r, err), nil
	}
	r.Evidence = Evidence{Format: "sha1", Commit: rev}
	r.Reason = "object_unavailable"
	entry, err := s.findPath(treeID, path)
	if err != nil {
		return unresolved(r, err), nil
	}
	if entry.id == "" {
		r.Verdict = "contradicted"
		r.Reason = "path_absent"
		r.Evidence.Tree = entry.tree
		r.Evidence.Missing = entry.component
		return r, nil
	}
	if entry.blocked || (entry.mode != "100644" && entry.mode != "100755") {
		r.Reason = "unsupported_kind"
		return r, nil
	}
	blob, err := s.readBlob(entry.id)
	if err != nil {
		return unresolved(r, err), nil
	}
	r.Evidence.Blob = entry.id
	if !utf8.Valid(blob) || bytes.IndexByte(blob, 0) >= 0 || bytes.HasPrefix(blob, []byte("version https://git-lfs.github.com/spec/v1")) {
		r.Reason = "unsupported_content"
		return r, nil
	}
	source := normalize(blob)
	at := bytes.Index(source, quote)
	if ctx.Err() != nil {
		return unresolved(r, errLimit), nil
	}
	if at < 0 {
		r.Verdict = "contradicted"
		r.Reason = "quote_absent"
		return r, nil
	}
	start := bytes.Count(source[:at], []byte("\n")) + 1
	r.Evidence.Lines = &Lines{start, start + bytes.Count(quote[:len(quote)-1], []byte("\n"))}
	r.Verdict = "verified"
	r.Reason = "quote_found"
	return r, nil
}

func unresolved(r Receipt, err error) Receipt {
	r.Reason = objectFailure(err, r.Reason)
	return r
}

func objectFailure(err error, fallback string) string {
	switch {
	case errors.Is(err, errLimit):
		return errLimit.Error()
	case errors.Is(err, errStorage):
		return errStorage.Error()
	default:
		return fallback
	}
}

// Inspect the complete tree before trusting either a positive or negative lookup.
func lookup(data []byte, wanted string) (string, string, error) {
	var mode, id, previous string
	seen := make(map[string]bool)
	for len(data) > 0 {
		if len(seen) >= 32768 {
			return "", "", errLimit
		}
		field, tail, ok := bytes.Cut(data, []byte{0})
		if !ok || len(tail) < 20 {
			return "", "", errObject
		}
		m, name, ok := bytes.Cut(field, []byte{' '})
		n := string(name)
		if !ok || n == "" || n == "." || n == ".." || strings.Contains(n, "/") || seen[n] {
			return "", "", errObject
		}
		sortKey := n
		switch string(m) {
		case "40000":
			sortKey += "/"
		case "100644", "100755", "120000", "160000":
		default:
			return "", "", errObject
		}
		if sortKey <= previous {
			return "", "", errObject
		}
		previous = sortKey
		seen[n] = true
		if n == wanted {
			mode = string(m)
			id = hex.EncodeToString(tail[:20])
		}
		data = tail[20:]
	}
	return mode, id, nil
}

func (r Receipt) Text() string {
	labels := map[string]string{"verified": "Verified", "contradicted": "Contradicted", "cant_check": "Can't check"}
	reasons := map[string]string{
		"quote_found":            "First match. CRLF and LF count as the same line ending.",
		"quote_absent":           "The complete committed file contains no matching quotation. Check the revision, path and final newline.",
		"path_absent":            "The named path is absent from the committed tree. Check the spelling and case.",
		"revision_unavailable":   "Provide a local repository containing the requested commit.",
		"repository_unavailable": "Provide a readable local repository directory.",
		"object_unavailable":     "A required Git object could not be read and verified. Check the local clone.",
		"unsupported_content":    "This file has binary, indirect or unsupported text content.",
		"unsupported_kind":       "The path crosses or names an unsupported entry.",
		"resource_limit":         "The check exceeded its resource budget.",
		"unsupported_storage":    "This Git storage representation is unsupported.",
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s · exact source quote\n%s", labels[r.Verdict], r.Claim.Path)
	e := r.Evidence
	if e.Lines != nil {
		fmt.Fprintf(&b, " · lines %d–%d", e.Lines.Start, e.Lines.End)
	}
	fmt.Fprintf(&b, "\nRequested commit %s\n", r.Claim.Revision)
	if e.Blob != "" {
		fmt.Fprintln(&b, "Blob", e.Blob)
	}
	if e.Tree != "" {
		fmt.Fprintf(&b, "Tree %s · missing %s\n", e.Tree, e.Missing)
	}
	fmt.Fprintf(&b, "%s · %s\n", r.Reason, reasons[r.Reason])
	return b.String()
}
