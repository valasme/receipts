package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"slices"
	"strings"
	"testing"
	"time"
	"unicode/utf8"
)

type failedOutput struct{}

func (failedOutput) Write([]byte) (int, error) { return 0, errors.New("sink unavailable") }
func TestFailedDelivery(t *testing.T) {
	if code := run([]string{"--version"}, failedOutput{}, io.Discard); code != 1 {
		t.Fatalf("exit %d, want operational failure", code)
	}
}

type blockedOutput struct {
	started chan struct{}
	release chan struct{}
}

func (w blockedOutput) Write(data []byte) (int, error) {
	close(w.started)
	<-w.release
	return len(data), nil
}

func TestInterruptDuringDelivery(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	stdout := blockedOutput{started: make(chan struct{}), release: make(chan struct{})}
	defer close(stdout.release)
	var diag strings.Builder
	done := make(chan int, 1)
	go func() {
		done <- execute(ctx, []string{"--version"}, nil, stdout, &diag)
	}()
	select {
	case <-stdout.started:
	case <-time.After(time.Second):
		t.Fatal("output write did not start")
	}
	cancel()
	select {
	case code := <-done:
		if code != 130 || diag.String() != "Output interrupted.\n" {
			t.Fatalf("exit %d, stderr=%q", code, diag.String())
		}
	case <-time.After(time.Second):
		t.Fatal("cancelled output blocked")
	}
}

func TestLicenseNotices(t *testing.T) {
	var out, diag strings.Builder
	if code := run([]string{"--licenses"}, &out, &diag); code != 0 || diag.Len() != 0 {
		t.Fatalf("license command exited %d with %q", code, diag.String())
	}
	for _, want := range []string{"Apache License", "Copyright 2009 The Go Authors.", "Vita Nuova", "Unicode, Inc."} {
		if !strings.Contains(out.String(), want) {
			t.Errorf("missing notice %q", want)
		}
	}
	if code := run([]string{"--licenses"}, failedOutput{}, io.Discard); code != 1 {
		t.Fatalf("failed license delivery exited %d", code)
	}
}

func TestCommands(t *testing.T) {
	for _, tc := range []struct {
		args []string
		code int
		want string
	}{
		{nil, 0, "Usage:"}, {[]string{"--help"}, 0, "exact source quotation"}, {[]string{"-h"}, 0, "Usage:"}, {[]string{"--version"}, 0, "receipts "}, {[]string{"check", "--help"}, 0, "--quote-file"}, {[]string{"nope"}, 2, "Unknown arguments"}, {[]string{"check", "--format", "xml"}, 2, "Invalid check arguments"}, {[]string{"check", "--repo", "a", "--repo", "b"}, 2, "Invalid check arguments"},
	} {
		var out, diag strings.Builder
		code := run(tc.args, &out, &diag)
		got := out.String()
		unused := diag.String()
		if tc.code != 0 {
			got, unused = unused, got
		}
		if code != tc.code || unused != "" || !strings.Contains(got, tc.want) {
			t.Errorf("%q returned %d, stdout=%q stderr=%q", tc.args, code, out.String(), diag.String())
		}
	}
}

func TestCommandHelp(t *testing.T) {
	for _, tc := range []struct {
		command string
		want    string
		omit    string
	}{
		{"check", "--quote-file FILE", "--submission FILE"},
		{"review", "--submission FILE", "--quote-file FILE"},
	} {
		t.Run(tc.command, func(t *testing.T) {
			var out, diag strings.Builder
			code := run([]string{tc.command, "--help"}, &out, &diag)
			if text := out.String(); code != 0 || diag.Len() != 0 || !strings.Contains(text, tc.want) || strings.Contains(text, tc.omit) {
				t.Fatalf("exit %d, stdout=%q stderr=%q", code, text, diag.String())
			}
		})
	}
}

func TestUnreadableQuoteInput(t *testing.T) {
	reader, writer := io.Pipe()
	defer reader.Close()
	writer.CloseWithError(errors.New("reader detail"))
	var out, diag strings.Builder
	args := []string{"check", "--rev", strings.Repeat("0", 40), "--path", "file", "--quote-file", "-"}
	code := execute(context.Background(), args, reader, &out, &diag)
	if code != 2 || out.Len() != 0 || diag.String() != "cannot read quote input; check that it is readable\n" {
		t.Fatalf("exit %d, stdout=%q stderr=%q", code, out.String(), diag.String())
	}
}

func TestInterruptWhileWaitingForInput(t *testing.T) {
	reader, writer := io.Pipe()
	defer writer.Close()
	defer reader.Close()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan int, 1)
	go func() {
		done <- execute(ctx, []string{"check", "--rev", strings.Repeat("0", 40), "--path", "file", "--quote-file", "-"}, reader, io.Discard, io.Discard)
	}()
	cancel()
	select {
	case code := <-done:
		if code != 130 {
			t.Fatal(code)
		}
	case <-time.After(time.Second):
		t.Fatal("cancelled input blocked")
	}
}

func TestOptionDiagnostics(t *testing.T) {
	for command, options := range map[string][]string{
		"check":  {"repo", "rev", "path", "quote-file", "claim-file", "batch-file", "format"},
		"review": {"repo", "rev", "compare", "proposal", "submission"},
	} {
		for _, option := range options {
			var out, diagnostic strings.Builder
			flag := "--" + option
			code := run([]string{command, flag + "=first-private", flag, "second-private"}, &out, &diagnostic)
			if code != 2 || out.Len() != 0 || !strings.Contains(diagnostic.String(), "duplicate "+flag+" option") || strings.Contains(diagnostic.String(), "-private") {
				t.Errorf("%s duplicate %s: exit %d, stdout=%q stderr=%q", command, flag, code, out.String(), diagnostic.String())
			}
		}
		for _, help := range []string{"-h", "--help"} {
			var out, diagnostic strings.Builder
			if code := run([]string{command, help}, &out, &diagnostic); code != 0 || !strings.Contains(out.String(), "Usage:") {
				t.Errorf("%s %s did not show usage", command, help)
			}
			for _, option := range []string{"--repo=.", "--unknown=secret"} {
				out.Reset()
				diagnostic.Reset()
				if code := run([]string{command, option, help}, &out, &diagnostic); code != 2 || out.Len() != 0 || strings.Contains(diagnostic.String(), "secret") {
					t.Errorf("%s %s with other arguments returned %d, %q", command, help, code, diagnostic.String())
				}
			}
		}
	}
}

func FuzzSavedQuotationMatchesRaw(f *testing.F) {
	for _, seed := range []string{"literal", "café 🎉\r\n\t", "\"\\", "\x00", "e\u0301", "a\u2028b", ""} {
		f.Add(seed)
	}
	repo := f.TempDir()
	rev := strings.Repeat("0", 40)
	f.Fuzz(func(t *testing.T, quote string) {
		if !utf8.ValidString(quote) || len(quote) > 2048 {
			t.Skip()
		}
		claim, err := json.Marshal(map[string]any{
			"schema_major": 1, "rev": rev, "path": "sample.txt", "quote": quote,
		})
		if err != nil {
			t.Fatal(err)
		}
		base := []string{"check", "--repo", repo, "--format", "json"}
		var rawOutput, savedOutput, rawError, savedError strings.Builder
		raw := execute(context.Background(),
			append(slices.Clone(base), "--rev", rev, "--path", "sample.txt", "--quote-file", "-"),
			strings.NewReader(quote), &rawOutput, &rawError)
		saved := execute(context.Background(),
			append(slices.Clone(base), "--claim-file", "-"),
			bytes.NewReader(claim), &savedOutput, &savedError)
		if raw != saved || rawOutput.String() != savedOutput.String() {
			t.Fatalf("raw quote gave exit %d and %q, saved quote gave exit %d and %q", raw, rawOutput.String(), saved, savedOutput.String())
		}
	})
}
