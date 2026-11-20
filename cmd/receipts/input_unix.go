//go:build unix

package main

import (
	"os"
	"syscall"
)

func openInput(path string) (*os.File, error) {
	// The path could become a FIFO between the preliminary stat and open.
	return os.OpenFile(path, os.O_RDONLY|syscall.O_NONBLOCK, 0)
}
