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

const help = `Usage: receipts check --rev COMMIT --path PATH --quote-file FILE [--repo DIR] [--format FORMAT]
       receipts check --claim-file FILE [--repo DIR] [--format FORMAT]
       receipts check --batch-file FILE [--repo DIR] [--format json]
       receipts review --submission FILE --proposal FILE --rev COMMIT [--compare COMMIT] [--repo DIR]
       receipts --help | --version | --licenses

Check an exact source quotation in a committed file. Use a full SHA-1
commit ID and a repository-relative path. The repository defaults to ".".
Pass - as a file to read stdin. Single claim formats: text, json, markdown.
A batch checks up to 16 claims at one commit and returns ordered JSON results.
A review preview links receipts and unresolved statements to submission lines.
File-change claims require a pinned comparison commit with --compare.
A final newline in the quotation is significant.

Create a quote without a trailing newline:
  POSIX:      printf %s 'example' > excerpt.txt
  PowerShell: [IO.File]::WriteAllText("$PWD/excerpt.txt", 'example')

Exit 0: completed receipt or batch, including per-item errors in a batch.
Exit 2: invalid invocation. Exit 1: output failure.
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
	if err := writeComplete(out, data); err != nil {
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
	if len(args) == 0 || (len(args) == 1 && (args[0] == "--help" || args[0] == "-h")) || (len(args) == 2 && (args[0] == "check" || args[0] == "review") && (args[1] == "--help" || args[1] == "-h")) {
		return deliver(stdout, stderr, help)
	}
	if len(args) == 1 && args[0] == "--version" {
		return deliver(stdout, stderr, "receipts "+buildVersion()+"\n")
	}
	if len(args) == 1 && args[0] == "--licenses" {
		return deliver(stdout, stderr, receipts.LicenseText())
	}
	if args[0] == "review" {
		return executeReview(ctx, args[1:], stdin, stdout, stderr)
	}
	if args[0] != "check" {
		fmt.Fprintln(stderr, "Unknown arguments. Run receipts --help for usage.")
		return 2
	}
	flags := flag.NewFlagSet("check", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	var repo, rev, path, file, claimFile, batchFile, format string
	provided := registerOptions(flags, stringOption{"repo", &repo, "."}, stringOption{"rev", &rev, ""},
		stringOption{"path", &path, ""}, stringOption{"quote-file", &file, ""}, stringOption{"claim-file", &claimFile, ""},
		stringOption{"batch-file", &batchFile, ""}, stringOption{"format", &format, "text"})
	if err := flags.Parse(args[1:]); err != nil || flags.NArg() != 0 || repo == "" || (format != "text" && format != "json" && format != "markdown") {
		fmt.Fprintln(stderr, "Invalid check arguments. Run receipts check --help.")
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
			fmt.Fprintln(stderr, "Invalid check arguments. Run receipts check --help.")
			return 2
		}
		err = check.Validate(rev, path)
		if err == nil {
			quote, err = readInput(ctx, stdin, file, 2*check.MaxQuote, "quote")
			if errors.Is(err, errInputRead) {
				err = errors.New("cannot read quote within the 64 KiB normalized limit")
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
		return deliverJSON(stdout, stderr, receipt)
	}
	output := receipt.Text()
	if format == "markdown" {
		output = "    " + strings.ReplaceAll(strings.TrimSuffix(output, "\n"), "\n", "\n    ") + "\n"
	}
	return deliver(stdout, stderr, output)
}
func deliverJSON(stdout, stderr io.Writer, value any) int {
	data, err := json.Marshal(value)
	if err != nil {
		fmt.Fprintln(stderr, "Cannot encode receipt.")
		return 1
	}
	return deliver(stdout, stderr, string(data)+"\n")
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "review" {
		// Report a downstream pipe closing through the review output error contract.
		signal.Ignore(syscall.SIGPIPE)
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	code := execute(ctx, os.Args[1:], os.Stdin, os.Stdout, os.Stderr)
	cancel()
	os.Exit(code)
}
