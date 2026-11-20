//go:build linux || darwin

package check

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"syscall"
	"testing"
	"time"
)

type replacedObjectRoot struct {
	*os.Root
}

func (r replacedObjectRoot) OpenFile(name string, flags int, mode os.FileMode) (*os.File, error) {
	// Replace the regular file after Lstat has succeeded. Perform the open
	// through the real rooted filesystem with the checker's original flags.
	if err := r.Remove(name); err != nil {
		return nil, err
	}
	if err := r.Rename("pipe", name); err != nil {
		return nil, err
	}
	return r.Root.OpenFile(name, flags, mode)
}

func TestObjectReplacedByPipeBeforeOpen(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "object"), []byte("original"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := syscall.Mkfifo(filepath.Join(dir, "pipe"), 0o600); err != nil {
		t.Fatal(err)
	}
	root, err := os.OpenRoot(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer root.Close()
	s := store{ctx: context.Background(), budget: newBudget()}
	done := make(chan error, 1)
	go func() {
		file, err := s.openObjectFile(replacedObjectRoot{root}, "object")
		if file != nil {
			file.Close()
		}
		done <- err
	}()
	select {
	case err := <-done:
		if !errors.Is(err, errStorage) {
			t.Fatalf("opening the substituted pipe returned %v", err)
		}
	case <-time.After(2 * time.Second):
		// Release an open that mistakenly waited for a writer.
		fd, err := syscall.Open(filepath.Join(dir, "object"), syscall.O_WRONLY|syscall.O_NONBLOCK, 0)
		if err == nil {
			syscall.Close(fd)
		}
		t.Fatal("opening the substituted pipe waited for a writer")
	}
}
