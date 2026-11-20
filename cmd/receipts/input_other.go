//go:build !unix

package main

import "os"

func openInput(path string) (*os.File, error) {
	return os.Open(path)
}
