package check

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"strconv"
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
	Format      string `json:"object_format,omitempty"`
	Commit      string `json:"observed_commit,omitempty"`
	Blob        string `json:"blob_id,omitempty"`
	Tree        string `json:"tree_id,omitempty"`
	Missing     string `json:"missing_component,omitempty"`
	Lines       *Lines `json:"lines,omitempty"`
	MissingPath string `json:"missing_path,omitempty"`
	EntryPath   string `json:"entry_path,omitempty"`
	EntryMode   string `json:"entry_mode,omitempty"`
	EntryID     string `json:"entry_id,omitempty"`
}
type Receipt struct {
	Schema   int      `json:"schema_major"`
	Version  string   `json:"checker_version"`
	Claim    Claim    `json:"claim"`
	Rule     string   `json:"comparison_rule"`
	Verdict  string   `json:"verdict"`
	Reason   string   `json:"reason"`
	Evidence Evidence `json:"evidence"`
	Detail   string   `json:"detail,omitempty"`
}

func normalize(b []byte) []byte { return bytes.ReplaceAll(b, []byte("\r\n"), []byte("\n")) }

const resolveCommitHint = " Run git rev-parse --verify 'TAG^{commit}' with your tag or branch, then supply the resulting commit ID."

func ValidateRevision(rev string) error {
	if len(rev) != 40 && len(rev) != 64 {
		return errors.New("supply a full 40-digit commit ID." + resolveCommitHint)
	}
	if _, err := hex.DecodeString(rev); err != nil {
		return errors.New("commit ID must be hexadecimal")
	}
	if len(rev) == 64 {
		return errors.New("a 64-digit commit ID has SHA-256 length; supply a full 40-digit SHA-1 commit ID")
	}
	return nil
}

func Validate(rev, path string) error {
	if err := ValidateRevision(rev); err != nil {
		return err
	}
	if !fs.ValidPath(path) || path == "." || strings.Contains(path, "\\") || hasDrivePrefix(path) || len(path) > 4096 || strings.Count(path, "/") >= 128 {
		return errors.New("supply a repository-relative file path using slash separators")
	}
	for _, r := range path {
		if unicode.IsControl(r) || unicode.Is(unicode.Cf, r) || r == '\u2028' || r == '\u2029' {
			return errors.New("path contains an unsupported control character")
		}
	}
	return nil
}

func hasDrivePrefix(path string) bool {
	if len(path) < 2 || path[1] != ':' {
		return false
	}
	letter := path[0] | 0x20
	return letter >= 'a' && letter <= 'z'
}

func Verify(ctx context.Context, repo, rev, path string, quote []byte, version string) (Receipt, error) {
	i := NewInspection(ctx, repo, version)
	defer i.Close()
	return i.Verify(rev, path, quote)
}

func (i *Inspection) Verify(rev, path string, quote []byte) (Receipt, error) {
	if err := Validate(rev, path); err != nil {
		return Receipt{}, err
	}
	quote = normalize(quote)
	if len(quote) == 0 || len(quote) > MaxQuote || bytes.IndexByte(quote, 0) >= 0 || !utf8.Valid(quote) {
		return Receipt{}, errors.New("supply 1 to 65536 bytes of UTF-8 quote text without NUL")
	}
	rev = strings.ToLower(rev)
	digest := sha256.Sum256(quote)
	r := Receipt{Schema: 1, Version: i.version, Rule: "utf8-crlf-to-lf-v1", Claim: Claim{"exact_source_quote", rev, path, hex.EncodeToString(digest[:])}, Verdict: "cant_check", Reason: "revision_unavailable"}
	return observe(i, unresolved(r, timeLimit), func(s *store, err error) (Receipt, error) {
		if err != nil {
			r.Reason = "repository_unavailable"
			return unresolved(r, err), nil
		}
		return inspectQuote(s, r, quote)
	})
}

func inspectQuote(s *store, r Receipt, quote []byte) (Receipt, error) {
	rev, path := r.Claim.Revision, r.Claim.Path
	treeID, err := s.commitTree(rev)
	if err != nil {
		if errors.Is(err, errNotCommit) {
			return Receipt{}, err
		}
		if errors.Is(err, errCommitStructure) {
			r.Reason = "object_unavailable"
		}
		return unresolved(r, err), nil
	}
	r.Evidence = Evidence{Format: "sha1", Commit: rev}
	r.Reason = "object_unavailable"
	entry, err := s.findPath(treeID, path)
	if err != nil {
		if entry.id != "" {
			r.Evidence.recordEntry(entry)
		}
		return unresolved(r, err), nil
	}
	if entry.id == "" {
		r.Verdict = "contradicted"
		r.Reason = "path_absent"
		r.Evidence.Tree = entry.tree
		r.Evidence.Missing = entry.component
		if entry.path != entry.component {
			r.Evidence.MissingPath = entry.path
		}
		return r, nil
	}
	if entry.blocked || (entry.mode != "100644" && entry.mode != "100755") {
		r.Reason = "unsupported_kind"
		r.Evidence.recordEntry(entry)
		return r, nil
	}
	blob, err := s.readBlob(entry.id)
	if err != nil {
		r.Evidence.recordEntry(entry)
		return unresolved(r, err), nil
	}
	r.Evidence.Blob = entry.id
	if !utf8.Valid(blob) || bytes.IndexByte(blob, 0) >= 0 || lfsPointer(blob) {
		r.Reason = "unsupported_content"
		return r, nil
	}
	source := normalize(blob)
	at := bytes.Index(source, quote)
	if s.ctx.Err() != nil {
		return unresolved(r, timeLimit), nil
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

func (e *Evidence) recordEntry(entry pathEntry) {
	e.Tree = entry.tree
	e.EntryPath = entry.path
	e.EntryMode = entry.mode
	e.EntryID = entry.id
}

func unresolved(r Receipt, err error) Receipt {
	r.Reason = objectFailure(err, r.Reason)
	r.Detail = failureDetail(err)
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

func failureDetail(err error) string {
	var limit limitError
	if errors.As(err, &limit) {
		return string(limit)
	}
	switch {
	case err != errStorage && errors.Is(err, errStorage):
		return strings.TrimPrefix(err.Error(), errStorage.Error()+": ")
	case err != errRepository && errors.Is(err, errRepository):
		return strings.TrimPrefix(err.Error(), errRepository.Error()+": ")
	default:
		return ""
	}
}

// Inspect the complete tree before trusting either a positive or negative lookup.
func lookup(data []byte, wanted string, remaining *int) (string, string, error) {
	var mode, id, previous string
	seen := make(map[string]bool)
	for len(data) > 0 {
		if len(seen) >= maxTreeEntries {
			return "", "", treeSizeLimit
		}
		if *remaining == 0 {
			return "", "", treeWorkLimit
		}
		(*remaining)--
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
	fmt.Fprintf(&b, "%s · exact source quote\n%s", labels[r.Verdict], strconv.QuoteToGraphic(r.Claim.Path))
	e := r.Evidence
	switch {
	case e.Lines == nil:
	case e.Lines.Start == e.Lines.End:
		fmt.Fprintf(&b, " · line %d", e.Lines.Start)
	default:
		fmt.Fprintf(&b, " · lines %d–%d", e.Lines.Start, e.Lines.End)
	}
	if e.Commit == "" {
		fmt.Fprintf(&b, "\nRequested commit %s\n", r.Claim.Revision)
	} else {
		fmt.Fprintf(&b, "\nObserved commit %s\n", e.Commit)
	}
	if e.Blob != "" {
		fmt.Fprintln(&b, "Blob", e.Blob)
	}
	if e.EntryID != "" {
		fmt.Fprintf(&b, "Tree %s · entry %s · mode %s · Object %s\n",
			e.Tree, strconv.QuoteToGraphic(e.EntryPath), e.EntryMode, e.EntryID)
	} else if e.Tree != "" {
		missing := e.MissingPath
		if missing == "" {
			missing = e.Missing
		}
		fmt.Fprintf(&b, "Tree %s · missing %s\n", e.Tree, strconv.QuoteToGraphic(missing))
	}
	fmt.Fprintf(&b, "%s · %s\n", r.Reason, reasons[r.Reason])
	if r.Detail != "" {
		fmt.Fprintln(&b, r.Detail)
	}
	return b.String()
}
