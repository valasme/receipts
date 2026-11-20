package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"slices"
	"strconv"
	"unicode/utf8"
)

const maxClaimFile = 768 << 10

type quotation struct {
	path string
	text string
}

func readInput(ctx context.Context, stdin io.Reader, name string, limit int, label string) ([]byte, error) {
	type result struct {
		data []byte
		err  error
	}
	done := make(chan result, 1)
	go func() {
		reader := stdin
		if name != "-" {
			file, err := os.Open(name)
			if err != nil {
				done <- result{err: errors.New("cannot open " + label + " file; check its path and permissions")}
				return
			}
			defer file.Close()
			reader = file
		}
		data, err := io.ReadAll(io.LimitReader(reader, int64(limit)+1))
		if err != nil || len(data) > limit {
			err = errors.New("cannot read " + label + " within the input size limit")
		}
		done <- result{data, err}
	}()
	select {
	case input := <-done:
		return input.data, input.err
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

func readClaim(data []byte) (string, quotation, error) {
	fields := objectFields(data, "schema_major", "rev", "path", "quote")
	rev, okRev := jsonString(fields["rev"])
	quote, okQuote := readQuotation(fields)
	if string(fields["schema_major"]) != "1" || !okRev || !okQuote {
		return "", quotation{}, errors.New("invalid claim file; expected schema_major 1, rev, path, and quote")
	}
	return rev, quote, nil
}

// JSON decoding into a struct permits case aliases and repeated keys.
func objectFields(data []byte, names ...string) map[string]json.RawMessage {
	if !utf8.Valid(data) || !json.Valid(data) {
		return nil
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	start, _ := decoder.Token()
	if start != json.Delim('{') {
		return nil
	}
	fields := make(map[string]json.RawMessage, len(names))
	for decoder.More() {
		token, _ := decoder.Token()
		name := token.(string)
		if !slices.Contains(names, name) || fields[name] != nil {
			return nil
		}
		var value json.RawMessage
		if err := decoder.Decode(&value); err != nil {
			return nil
		}
		fields[name] = value
	}
	return fields
}

func readQuotation(fields map[string]json.RawMessage) (quotation, bool) {
	path, okPath := jsonString(fields["path"])
	quote, okQuote := jsonString(fields["quote"])
	return quotation{path, quote}, okPath && okQuote
}

func jsonString(raw json.RawMessage) (string, bool) {
	if len(raw) == 0 || raw[0] != '"' || !pairedSurrogates(raw) {
		return "", false
	}
	var value string
	if err := json.Unmarshal(raw, &value); err != nil {
		return "", false
	}
	return value, true
}

// Go's JSON decoder replaces unpaired UTF-16 surrogates with U+FFFD.
// Check escapes first so an exact quote never changes during decoding.
func pairedSurrogates(raw []byte) bool {
	for i := 1; i < len(raw)-1; i++ {
		if raw[i] != '\\' {
			continue
		}
		i++
		if raw[i] != 'u' {
			continue
		}
		code, _ := strconv.ParseUint(string(raw[i+1:i+5]), 16, 16)
		i += 4
		switch {
		case code >= 0xdc00 && code <= 0xdfff:
			return false
		case code >= 0xd800 && code <= 0xdbff:
			if i+6 >= len(raw)-1 || raw[i+1] != '\\' || raw[i+2] != 'u' {
				return false
			}
			low, _ := strconv.ParseUint(string(raw[i+3:i+7]), 16, 16)
			if low < 0xdc00 || low > 0xdfff {
				return false
			}
			i += 6
		}
	}
	return true
}
