package main

import (
	"context"
	"errors"
	"io"
	"strings"
	"testing"
	"time"
)

type failedOutput struct{}

func (failedOutput) Write([]byte) (int, error) { return 0, errors.New("sink unavailable") }
func TestFailedDelivery(t *testing.T) {
	if code := run([]string{"--version"}, failedOutput{}, io.Discard); code != 1 {
		t.Fatalf("exit %d, want operational failure", code)
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
