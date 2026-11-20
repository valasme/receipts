package main

import (
	"fmt"
	"io"
	"os"
)

var version = "dev"

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 1 && args[0] == "--version" {
		if _, err := fmt.Fprintln(stdout, "receipts", version); err != nil {
			fmt.Fprintln(stderr, "Could not write output.")
			return 1
		}
		return 0
	}
	if len(args) == 0 || (len(args) == 1 && (args[0] == "--help" || args[0] == "-h")) {
		if _, err := fmt.Fprintln(stdout, "Usage: receipts [--help | --version]"); err != nil {
			fmt.Fprintln(stderr, "Could not write output.")
			return 1
		}
		return 0
	}
	fmt.Fprintln(stderr, "Unknown arguments. Run receipts --help for usage.")
	return 2
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}
