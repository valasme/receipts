package main

import (
	"errors"
	"io"
	"testing"
)

type failedOutput struct{}

func (failedOutput) Write([]byte) (int, error) { return 0, errors.New("sink unavailable") }
func TestFailedDelivery(t *testing.T) {
	if code := run([]string{"--version"}, failedOutput{}, io.Discard); code != 1 {
		t.Fatalf("exit %d, want operational failure", code)
	}
}
