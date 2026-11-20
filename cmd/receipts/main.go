package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"runtime/debug"
	"strings"
	"time"

	"github.com/valasme/receipts/internal/check"
)

var version = "dev"

const help = `Usage: receipts check --rev COMMIT --path PATH --quote-file FILE [--repo DIR] [--format FORMAT]
       receipts --help | --version

Check an exact source quotation in a committed file. Use a full SHA-1
commit ID and a repository-relative path. The repository defaults to ".".
Pass - as the quote file to read stdin. Formats: text, json, markdown.
A final newline in the quotation is significant.

Create a quote without a trailing newline:
  POSIX:      printf %s 'example' > excerpt.txt
  PowerShell: [IO.File]::WriteAllText("$PWD/excerpt.txt", 'example')

Exit 0: completed receipt. Exit 2: invalid input. Exit 1: output failure.
`

func buildVersion() string {
	if version != "dev" {
		return version
	}
	if info, ok := debug.ReadBuildInfo(); ok && info.Main.Version != "" && info.Main.Version != "(devel)" {
		return info.Main.Version
	}
	return version
}
func deliver(out, diagnostics io.Writer, data string) int {
	n, err := io.WriteString(out, data)
	if err != nil || n != len(data) {
		fmt.Fprintln(diagnostics, "Could not write complete output.")
		return 1
	}
	return 0
}
func run(args []string, stdout, stderr io.Writer) int {
	return execute(context.Background(), args, os.Stdin, stdout, stderr)
}
func execute(ctx context.Context, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	if len(args) == 0 || (len(args) == 1 && (args[0] == "--help" || args[0] == "-h")) || (len(args) == 2 && args[0] == "check" && (args[1] == "--help" || args[1] == "-h")) {
		return deliver(stdout, stderr, help)
	}
	if len(args) == 1 && args[0] == "--version" {
		return deliver(stdout, stderr, "receipts "+buildVersion()+"\n")
	}
	if args[0] != "check" {
		fmt.Fprintln(stderr, "Unknown arguments. Run receipts --help for usage.")
		return 2
	}
	flags := flag.NewFlagSet("check", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	var repo, rev, path, file, format string
	for _, opt := range []struct {
		name     string
		dst      *string
		fallback string
	}{{"repo", &repo, "."}, {"rev", &rev, ""}, {"path", &path, ""}, {"quote-file", &file, ""}, {"format", &format, "text"}} {
		*opt.dst = opt.fallback
		seen := false
		flags.Func(opt.name, "", func(value string) error {
			if seen {
				return errors.New("duplicate option")
			}
			seen = true
			*opt.dst = value
			return nil
		})
	}
	if err := flags.Parse(args[1:]); err != nil || flags.NArg() != 0 || file == "" || repo == "" || (format != "text" && format != "json" && format != "markdown") {
		fmt.Fprintln(stderr, "Invalid check arguments. Run receipts check --help.")
		return 2
	}
	if err := check.Validate(rev, path); err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	type input struct {
		data []byte
		err  error
	}
	read := make(chan input, 1)
	go func() {
		if file != "-" {
			f, err := os.Open(file)
			if err != nil {
				read <- input{err: errors.New("cannot open quote file; check its path and permissions")}
				return
			}
			defer f.Close()
			stdin = f
		}
		data, err := io.ReadAll(io.LimitReader(stdin, 2*check.MaxQuote+1))
		if err != nil || len(data) > 2*check.MaxQuote {
			err = errors.New("cannot read quote within the 64 KiB normalized limit")
		}
		read <- input{data, err}
	}()
	var quote []byte
	select {
	case result := <-read:
		if result.err != nil {
			fmt.Fprintln(stderr, result.err)
			return 2
		}
		quote = result.data
	case <-ctx.Done():
		fmt.Fprintln(stderr, "Check interrupted.")
		return 130
	}
	clock, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	receipt, err := check.Verify(clock, repo, rev, path, quote, buildVersion())
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Check interrupted.")
		return 130
	}
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	output := receipt.Text()
	switch format {
	case "json":
		data, err := json.Marshal(receipt)
		if err != nil {
			fmt.Fprintln(stderr, "Cannot encode receipt.")
			return 1
		}
		output = string(data) + "\n"
	case "markdown":
		output = "    " + strings.ReplaceAll(strings.TrimSuffix(output, "\n"), "\n", "\n    ") + "\n"
	}
	return deliver(stdout, stderr, output)
}
func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	code := execute(ctx, os.Args[1:], os.Stdin, os.Stdout, os.Stderr)
	cancel()
	os.Exit(code)
}
