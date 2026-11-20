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
	"syscall"

	"github.com/valasme/receipts"
	"github.com/valasme/receipts/internal/check"
)

var version = "dev"

const help = `Check source claims against local Git commits.

Usage: receipts <command> [options]

Commands:
  check      Check an exact source quotation, a saved claim, or a batch.
  review     Preview proposal entries alongside their submission lines.

Options:
  --help      Show this help.
  --version   Print the installed version.
  --licenses  Print the license and third-party notices.

Run receipts check --help or receipts review --help for command options.
`

const checkHelp = `Check an exact source quotation in a committed file.

Usage: receipts check --rev COMMIT --path PATH --quote-file FILE
       receipts check --claim-file FILE
       receipts check --batch-file FILE

Options:
  --rev COMMIT       Full SHA-1 commit ID (40 hexadecimal digits).
  --path PATH        File path relative to the repo root, using slashes.
  --quote-file FILE  Literal UTF-8 quotation, including any final LF.
  --claim-file FILE  One saved claim in schema-major-1 JSON.
  --batch-file FILE  Up to 16 claims at one commit, returned in order.
  --repo DIR         Clone root or bare repo (default: search upward from here).
  --format FORMAT    text (default), json, or markdown. Batches use json.

Use - for a file read from stdin. CRLF and LF compare equally.
To prepare a quotation without a final newline:

  POSIX:      printf %s 'example' > excerpt.txt
  PowerShell: [IO.File]::WriteAllText("$PWD/excerpt.txt", 'example')

Exit 0    Complete receipt or batch, including any per-item errors.
Exit 1    Output failure.
Exit 2    Invalid input or arguments.
Exit 130  Interrupted.
`

const reviewHelp = `Preview receipts and unresolved statements in a submission.

Usage: receipts review --submission FILE --proposal FILE --rev COMMIT
       [--compare COMMIT] [--repo DIR]

Options:
  --submission FILE  UTF-8 submission text.
  --proposal FILE    JSON proposal with source line ranges.
  --rev COMMIT       Full SHA-1 commit ID (40 hexadecimal digits).
  --compare COMMIT   Full comparison commit ID for file-change claims.
  --repo DIR         Clone root or bare repo (default: search upward from here).

Use - for one input file to read it from stdin. Each file may be up to 1 MiB.

Exit 0    Complete preview.
Exit 1    Output failure.
Exit 2    Invalid input or arguments.
Exit 130  Interrupted.
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
func deliver(ctx context.Context, out, diagnostics io.Writer, data, interrupted string) int {
	if ctx.Err() != nil {
		fmt.Fprintln(diagnostics, interrupted)
		return 130
	}
	// A full OS pipe can block a write. The process must still exit on Ctrl+C.
	written := make(chan error, 1)
	go func() { written <- writeComplete(out, data) }()
	var err error
	select {
	case err = <-written:
	case <-ctx.Done():
	}
	if ctx.Err() != nil {
		fmt.Fprintln(diagnostics, interrupted)
		return 130
	}
	if err != nil {
		fmt.Fprintln(diagnostics, "Could not write complete output.")
		return 1
	}
	return 0
}

func writeComplete(out io.Writer, data string) error {
	n, err := io.WriteString(out, data)
	if err == nil && n != len(data) {
		return io.ErrShortWrite
	}
	return err
}

type stringOption struct {
	name     string
	dst      *string
	fallback string
}

func registerOptions(flags *flag.FlagSet, options ...stringOption) map[string]bool {
	provided := make(map[string]bool)
	for _, opt := range options {
		*opt.dst = opt.fallback
		flags.Func(opt.name, "", func(value string) error {
			if provided[opt.name] {
				return errors.New("duplicate option")
			}
			provided[opt.name] = true
			*opt.dst = value
			return nil
		})
	}
	return provided
}

func run(args []string, stdout, stderr io.Writer) int {
	return execute(context.Background(), args, os.Stdin, stdout, stderr)
}

func execute(ctx context.Context, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	if len(args) == 0 || wantsHelp(args) {
		return deliver(ctx, stdout, stderr, help, "Output interrupted.")
	}
	if len(args) == 1 && args[0] == "--version" {
		return deliver(ctx, stdout, stderr, "receipts "+buildVersion()+"\n", "Output interrupted.")
	}
	if len(args) == 1 && args[0] == "--licenses" {
		return deliver(ctx, stdout, stderr, receipts.LicenseText(), "Output interrupted.")
	}
	switch args[0] {
	case "review":
		if wantsHelp(args[1:]) {
			return deliver(ctx, stdout, stderr, reviewHelp, "Output interrupted.")
		}
		return executeReview(ctx, args[1:], stdin, stdout, stderr)
	case "check":
		if wantsHelp(args[1:]) {
			return deliver(ctx, stdout, stderr, checkHelp, "Output interrupted.")
		}
		return executeCheck(ctx, args[1:], stdin, stdout, stderr)
	default:
		fmt.Fprintln(stderr, "Unknown arguments. Run receipts --help for usage.")
		return 2
	}
}

func wantsHelp(args []string) bool {
	return len(args) == 1 && (args[0] == "--help" || args[0] == "-h")
}

func executeCheck(ctx context.Context, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("check", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	var repo, rev, path, file, claimFile, batchFile, format string
	provided := registerOptions(flags, stringOption{"repo", &repo, ""}, stringOption{"rev", &rev, ""},
		stringOption{"path", &path, ""}, stringOption{"quote-file", &file, ""}, stringOption{"claim-file", &claimFile, ""},
		stringOption{"batch-file", &batchFile, ""}, stringOption{"format", &format, "text"})
	if err := flags.Parse(args); err != nil || flags.NArg() != 0 {
		fmt.Fprintln(stderr, "Invalid check arguments. Run receipts check --help.")
		return 2
	}
	if provided["repo"] && repo == "" {
		fmt.Fprintln(stderr, "Invalid check arguments. Supply a directory for --repo, or omit it.")
		return 2
	}
	if format != "text" && format != "json" && format != "markdown" {
		fmt.Fprintln(stderr, "Invalid check arguments. Use --format text, json, or markdown.")
		return 2
	}
	legacyFlags := provided["rev"] || provided["path"] || provided["quote-file"]
	if provided["batch-file"] {
		if batchFile == "" || provided["claim-file"] || legacyFlags || (provided["format"] && format != "json") {
			fmt.Fprintln(stderr, "Supply --batch-file on its own with optional --repo and --format json.")
			return 2
		}
		return executeBatch(ctx, stdin, stdout, stderr, repo, batchFile)
	}
	var quote []byte
	var err error
	if provided["claim-file"] {
		if claimFile == "" || legacyFlags {
			fmt.Fprintln(stderr, "Supply --claim-file on its own with optional --repo and --format.")
			return 2
		}
		var data []byte
		data, err = readInput(ctx, stdin, claimFile, maxClaimFile, "claim")
		if err == nil {
			var claim quotation
			rev, claim, err = readClaim(data)
			path, quote = claim.path, []byte(claim.text)
		}
	} else {
		if file == "" {
			fmt.Fprintln(stderr, "Supply --quote-file with --rev and --path, or use --claim-file or --batch-file.")
			return 2
		}
		err = check.Validate(rev, path)
		if err == nil {
			quote, err = readInput(ctx, stdin, file, 2*check.MaxQuote, "quote")
			if errors.Is(err, errInputTooLarge) {
				err = errors.New("quote exceeds the 64 KiB normalized limit")
			}
		}
	}
	if ctx.Err() != nil {
		fmt.Fprintln(stderr, "Check interrupted.")
		return 130
	}
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	clock, cancel := context.WithTimeout(ctx, checkTimeout)
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
	if format == "json" {
		return deliverJSON(ctx, stdout, stderr, receipt)
	}
	output := receipt.Text()
	if format == "markdown" {
		output = "    " + strings.ReplaceAll(strings.TrimSuffix(output, "\n"), "\n", "\n    ") + "\n"
	}
	return deliver(ctx, stdout, stderr, output, "Check interrupted.")
}
func deliverJSON(ctx context.Context, stdout, stderr io.Writer, value any) int {
	data, err := json.Marshal(value)
	if err != nil {
		fmt.Fprintln(stderr, "Cannot encode receipt.")
		return 1
	}
	return deliver(ctx, stdout, stderr, string(data)+"\n", "Check interrupted.")
}

func main() {
	// Use the same output failure contract when a reader closes a pipeline.
	signal.Ignore(syscall.SIGPIPE)
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	code := execute(ctx, os.Args[1:], os.Stdin, os.Stdout, os.Stderr)
	cancel()
	os.Exit(code)
}
