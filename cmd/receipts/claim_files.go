package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"slices"
	"strconv"
	"unicode/utf8"
)

const maxClaimFile = 768 << 10

var errInputTooLarge = errors.New("input exceeds the limit")

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
	// The process owns named files. The caller owns stdin. On interruption
	// the CLI exits, which also releases any OS read still blocked on stdin.
	go func() {
		reader := stdin
		if name != "-" {
			info, err := os.Stat(name)
			if err != nil {
				done <- result{err: fmt.Errorf("cannot open %s file; check its path and permissions", label)}
				return
			}
			if !info.Mode().IsRegular() {
				done <- result{err: fmt.Errorf("%s input must be a regular file or - for stdin", label)}
				return
			}
			file, err := openInput(name)
			if err != nil {
				done <- result{err: fmt.Errorf("cannot open %s file; check its path and permissions", label)}
				return
			}
			defer file.Close()
			info, err = file.Stat()
			if err != nil || !info.Mode().IsRegular() {
				done <- result{err: fmt.Errorf("%s input must be a regular file or - for stdin", label)}
				return
			}
			reader = file
		}
		data, err := io.ReadAll(io.LimitReader(reader, int64(limit)+1))
		if len(data) > limit {
			err = fmt.Errorf("%s %w of %d bytes", label, errInputTooLarge, limit)
		} else if err != nil {
			err = fmt.Errorf("cannot read %s input; check that it is readable", label)
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
	fields, err := objectFields(data, "schema_major", "rev", "path", "quote")
	if err != nil {
		return "", quotation{}, fmt.Errorf("claim file: %w", err)
	}
	if string(fields["schema_major"]) != "1" {
		return "", quotation{}, errors.New("claim file requires schema_major 1")
	}
	rev, ok := jsonString(fields["rev"])
	if !ok {
		return "", quotation{}, errors.New("claim file requires rev as an exact JSON string")
	}
	quote, err := readQuotation(fields)
	if err != nil {
		return "", quotation{}, fmt.Errorf("claim file: %w", err)
	}
	return rev, quote, nil
}

// JSON decoding into a struct permits case aliases and repeated keys.
func objectFields(data []byte, names ...string) (map[string]json.RawMessage, error) {
	if !utf8.Valid(data) || !json.Valid(data) {
		return nil, errors.New("expected a valid UTF-8 JSON object")
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	start, _ := decoder.Token()
	if start != json.Delim('{') {
		return nil, errors.New("expected a JSON object")
	}
	fields := make(map[string]json.RawMessage, len(names))
	for decoder.More() {
		token, _ := decoder.Token()
		name := token.(string)
		if !slices.Contains(names, name) {
			return nil, errors.New("unknown field")
		}
		if fields[name] != nil {
			return nil, fmt.Errorf("duplicate %s field", name)
		}
		var value json.RawMessage
		if err := decoder.Decode(&value); err != nil {
			return nil, fmt.Errorf("invalid %s field", name)
		}
		fields[name] = value
	}
	return fields, nil
}

func readQuotation(fields map[string]json.RawMessage) (quotation, error) {
	path, ok := jsonString(fields["path"])
	if !ok {
		return quotation{}, errors.New("path must be an exact JSON string")
	}
	quote, ok := jsonString(fields["quote"])
	if !ok {
		return quotation{}, errors.New("quote must be an exact JSON string")
	}
	return quotation{path, quote}, nil
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
