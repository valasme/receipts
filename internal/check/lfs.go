package check

import (
	"bytes"
	"strconv"
	"strings"
)

const lfsVersion = "version https://git-lfs.github.com/spec/v1"

// Recognize bounded Git LFS v1 records, including CRLF and extension
// lines. The version marker by itself can be ordinary source text.
func lfsPointer(data []byte) bool {
	if len(data) >= 1024 || !bytes.HasPrefix(data, []byte(lfsVersion)) {
		return false
	}
	version, fields, ok := strings.Cut(string(normalize(data)), "\n")
	if !ok || version != lfsVersion {
		return false
	}
	var priorities [10]bool
	var oid, size bool
	for line := range strings.SplitSeq(strings.TrimSuffix(fields, "\n"), "\n") {
		key, value, ok := strings.Cut(line, " ")
		if !ok {
			return false
		}
		switch key {
		case "oid":
			if oid || !canonicalLFSOID(value) {
				return false
			}
			oid = true
		case "size":
			if _, err := strconv.ParseUint(value, 10, 63); size || err != nil {
				return false
			}
			size = true
		default:
			ext, found := strings.CutPrefix(key, "ext-")
			priority, name, ok := strings.Cut(ext, "-")
			if !found || !ok || len(priority) != 1 || priority[0] < '0' || priority[0] > '9' ||
				name == "" || !canonicalLFSOID(value) {
				return false
			}
			for _, c := range name {
				if !((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' || c == '-' || c == '_') {
					return false
				}
			}
			at := priority[0] - '0'
			if priorities[at] {
				return false
			}
			priorities[at] = true
		}
	}
	return oid && size
}

func canonicalLFSOID(value string) bool {
	oid, ok := strings.CutPrefix(value, "sha256:")
	return ok && len(oid) == 64 && lowercaseHex([]byte(oid))
}
