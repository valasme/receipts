package check

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

const maxConfigBytes = 256 << 10
const configSizeLimit = limitError("256 KiB Git config size")

var (
	errRepository  = errors.New("repository_unavailable")
	errMetadata    = fmt.Errorf("%w: Git metadata is inaccessible. Check directory permissions.", errRepository)
	errObjectDir   = fmt.Errorf("%w: The Git object directory is missing or inaccessible. Use a complete clone.", errRepository)
	errIndirection = fmt.Errorf("%w: Git directory indirection. Use a regular clone or bare repository.", errStorage)
	errAlternates  = fmt.Errorf("%w: alternate object database. Use a self-contained clone.", errStorage)
)

func openStore(ctx context.Context, path string) (*store, error) {
	s := &store{ctx: ctx, budget: newBudget()}
	discover := path == ""
	if discover {
		var err error
		path, err = os.Getwd()
		if err != nil {
			return nil, errMetadata
		}
	}
	for {
		found, err := s.selectRoot(path)
		if err != nil {
			return nil, err
		}
		if found {
			if err := s.validateRoot(); err != nil {
				s.root.Close()
				return nil, err
			}
			return s, nil
		}
		parent := filepath.Dir(path)
		if !discover || parent == path {
			return nil, errRepository
		}
		path = parent
	}
}

func (s *store) selectRoot(path string) (found bool, err error) {
	if err := s.filesystemOp(); err != nil {
		return false, err
	}
	root, err := os.OpenRoot(path)
	if errors.Is(err, fs.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, errMetadata
	}
	defer func() {
		if s.root != root {
			root.Close()
		}
	}()
	if err := s.filesystemOp(); err != nil {
		return false, err
	}
	git, err := root.Lstat(".git")
	switch {
	case err == nil:
		if !git.IsDir() {
			return false, errIndirection
		}
		if err := s.filesystemOp(); err != nil {
			return false, err
		}
		s.root, err = root.OpenRoot(".git")
		if err != nil {
			return false, errMetadata
		}
		return true, nil
	case !errors.Is(err, fs.ErrNotExist):
		return false, errMetadata
	}
	if err := s.filesystemOp(); err != nil {
		return false, err
	}
	head, err := root.Lstat("HEAD")
	if errors.Is(err, fs.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, errMetadata
	}
	if !head.Mode().IsRegular() && head.Mode()&os.ModeSymlink == 0 {
		return false, nil
	}
	// A bare or explicitly selected Git directory has both HEAD and
	// repository metadata. Avoid treating a lone file named HEAD as a repo.
	for _, name := range []string{"objects", "config", "commondir"} {
		if err := s.filesystemOp(); err != nil {
			return false, err
		}
		if _, err := root.Lstat(name); err == nil {
			s.root = root
			return true, nil
		} else if !errors.Is(err, fs.ErrNotExist) {
			return false, errMetadata
		}
	}
	return false, nil
}

func (s *store) validateRoot() error {
	if err := s.filesystemOp(); err != nil {
		return err
	}
	if _, err := s.root.Lstat("commondir"); err == nil {
		return errIndirection
	} else if !errors.Is(err, fs.ErrNotExist) {
		return errMetadata
	}
	if err := s.filesystemOp(); err != nil {
		return err
	}
	objects, err := s.root.Stat("objects")
	if err != nil || !objects.IsDir() {
		return errObjectDir
	}
	file, err := s.file("config")
	switch {
	case errors.Is(err, fs.ErrNotExist):
		return nil
	case errors.Is(err, errLimit):
		return err
	case err != nil:
		return errMetadata
	}
	defer file.Close()
	data, err := s.readBounded(s.reader(file), maxConfigBytes, configSizeLimit)
	if errors.Is(err, errLimit) {
		return err
	}
	if err != nil {
		return errMetadata
	}
	return checkObjectFormat(data)
}

// Git's repository format is recorded in the local config. Treat values as
// inert data. Includes and configuration from the surrounding environment
// do not define the on-disk object format.
func checkObjectFormat(data []byte) error {
	data = bytes.TrimPrefix(data, []byte{0xef, 0xbb, 0xbf})
	extensions := false
	for line := range strings.SplitSeq(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || line[0] == '#' || line[0] == ';' {
			continue
		}
		if line[0] == '[' {
			section, rest, ok := strings.Cut(line[1:], "]")
			extensions = ok && strings.EqualFold(section, "extensions")
			line = strings.TrimSpace(rest)
		}
		if !extensions {
			continue
		}
		key, value, _ := strings.Cut(line, "=")
		if !strings.EqualFold(strings.TrimSpace(key), "objectformat") {
			continue
		}
		if index := strings.IndexAny(value, "#;"); index >= 0 {
			value = value[:index]
		}
		switch strings.ToLower(strings.TrimSpace(value)) {
		case "sha1", "\"sha1\"":
		case "sha256", "\"sha256\"":
			return fmt.Errorf("%w: SHA-256 object format. Use a SHA-1 repository.", errStorage)
		default:
			return fmt.Errorf("%w: unrecognized Git object format", errStorage)
		}
	}
	return nil
}
