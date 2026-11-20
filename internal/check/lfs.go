package check

import (
	"strconv"
	"strings"
)

// Recognize bounded Git LFS v1 records, including CRLF and extension
// lines. The version marker by itself can be ordinary source text.
func lfsPointer(data []byte) bool {
	if len(data) >= 1024 {
		return false
	}
	version, fields, ok := strings.Cut(strings.TrimSpace(string(data)), "\n")
	if !ok {
		return false
	}
	// Recognize the version aliases read by Git LFS as well as its current URL.
	switch strings.TrimSuffix(version, "\r") {
	case "version https://git-lfs.github.com/spec/v1", "version https://hawser.github.com/spec/v1", "version http://git-media.io/v/2":
	default:
		return false
	}
	var priorities [10]bool
	var oid, size bool
	for line := range strings.SplitSeq(fields, "\n") {
		line = strings.TrimSuffix(line, "\r")
		if line == "" {
			continue
		}
		key, value, ok := strings.Cut(line, " ")
		if !ok || size {
			return false
		}
		switch key {
		case "oid":
			if oid || !canonicalLFSOID(value) {
				return false
			}
			oid = true
		case "size":
			n, err := strconv.ParseInt(value, 10, 64)
			if !oid || err != nil || n < 0 {
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
				if !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '-' || c == '_') {
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
