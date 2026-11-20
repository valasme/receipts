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
