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

type repositoryLayout uint8

const (
	noRepository repositoryLayout = iota
	cloneRoot
	standaloneRoot
)

var (
	errRepository    = errors.New("repository_unavailable")
	errCloneMetadata = fmt.Errorf("%w: Use the clone root or a bare repository.", errRepository)
	errMetadata      = fmt.Errorf("%w: Git metadata is inaccessible. Check directory permissions.", errRepository)
	errObjectDir     = fmt.Errorf("%w: The Git object directory is missing or inaccessible. Use a complete clone.", errRepository)
	errIndirection   = fmt.Errorf("%w: Git directory indirection. Use a regular clone or bare repository.", errStorage)
	errAlternates    = fmt.Errorf("%w: alternate object database. Use a self-contained clone.", errStorage)
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
		layout, err := s.selectRoot(path)
		if err != nil {
			return nil, err
		}
		if layout != noRepository {
			err := s.validateRoot(layout)
			if err == nil {
				return s, nil
			}
			s.root.Close()
			s.root = nil
			if !discover || !errors.Is(err, errCloneMetadata) {
				return nil, err
			}
		}
		parent := filepath.Dir(path)
		if !discover || parent == path {
			return nil, errRepository
		}
		path = parent
	}
}

func (s *store) selectRoot(path string) (repositoryLayout, error) {
	if err := s.filesystemOp(); err != nil {
		return noRepository, err
	}
	root, err := os.OpenRoot(path)
	if errors.Is(err, fs.ErrNotExist) {
		return noRepository, nil
	}
	if err != nil {
		return noRepository, errMetadata
	}
	defer func() {
		if s.root != root {
			root.Close()
		}
	}()
	if err := s.filesystemOp(); err != nil {
		return noRepository, err
	}
	git, err := root.Lstat(".git")
	switch {
	case err == nil:
		if !git.IsDir() {
			return noRepository, errIndirection
		}
		if err := s.filesystemOp(); err != nil {
			return noRepository, err
		}
		metadata, err := root.OpenRoot(".git")
		if err != nil {
			return noRepository, errMetadata
		}
		s.root = metadata
		return cloneRoot, nil
	case !errors.Is(err, fs.ErrNotExist):
		return noRepository, errMetadata
	}
	if err := s.filesystemOp(); err != nil {
		return noRepository, err
	}
	head, err := root.Lstat("HEAD")
	if errors.Is(err, fs.ErrNotExist) {
		return noRepository, nil
	}
	if err != nil {
		return noRepository, errMetadata
	}
	if !head.Mode().IsRegular() && head.Mode()&os.ModeSymlink == 0 {
		return noRepository, nil
	}
	// Ordinary directories can contain HEAD and config files. Require a
	// Git storage directory or recorded directory indirection as well.
	for _, name := range []string{"objects", "refs", "commondir"} {
		if err := s.filesystemOp(); err != nil {
			return noRepository, err
		}
		info, err := root.Lstat(name)
		if err == nil && (info.IsDir() || name == "commondir") {
			s.root = root
			return standaloneRoot, nil
		}
		if err != nil && !errors.Is(err, fs.ErrNotExist) {
			return noRepository, errMetadata
		}
	}
	return noRepository, nil
}

func (s *store) validateRoot(layout repositoryLayout) error {
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
	return checkRepositoryConfig(data, layout)
}

// Git's repository format is recorded in the local config. Treat values as
// inert data. Includes and configuration from the surrounding environment
// do not define the on-disk object format.
func checkRepositoryConfig(data []byte, layout repositoryLayout) error {
	data = bytes.TrimPrefix(data, []byte{0xef, 0xbb, 0xbf})
	var section string
	nonbare := false
	for line := range strings.SplitSeq(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || line[0] == '#' || line[0] == ';' {
			continue
		}
		if line[0] == '[' {
			name, rest, ok := strings.Cut(line[1:], "]")
			section = ""
			if ok {
				section = strings.ToLower(name)
			}
			line = strings.TrimSpace(rest)
		}
		key, value, _ := strings.Cut(line, "=")
		key = strings.ToLower(strings.TrimSpace(key))
		if index := strings.IndexAny(value, "#;"); index >= 0 {
			value = value[:index]
		}
		value = strings.ToLower(strings.Trim(strings.TrimSpace(value), "\""))
		if section == "core" && key == "bare" {
			nonbare = value == "false" || value == "no" || value == "off" || value == "0"
		}
		if section != "extensions" || key != "objectformat" {
			continue
		}
		switch value {
		case "sha1":
		case "sha256":
			return fmt.Errorf("%w: SHA-256 object format. Use a SHA-1 repository.", errStorage)
		default:
			return fmt.Errorf("%w: unrecognized Git object format", errStorage)
		}
	}
	if layout == standaloneRoot && nonbare {
		return errCloneMetadata
	}
	return nil
}
