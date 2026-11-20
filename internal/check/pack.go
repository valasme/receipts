package check

import (
	"bytes"
	"crypto/sha1"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"slices"
	"sort"
	"strings"
)

type packCandidate struct {
	path   string
	loaded bool
	index  packIndex
	err    error
}

type packIndex struct {
	names   []byte
	offsets []byte
	large   []byte
}

func parsePackIndex(data []byte) (packIndex, error) {
	const fanoutEnd = 8 + 256*4
	const trailer = 2 * sha1.Size
	if !bytes.HasPrefix(data, []byte{255, 't', 'O', 'c'}) {
		const fanoutV1 = 256 * 4
		if len(data) >= fanoutV1+trailer &&
			uint64(binary.BigEndian.Uint32(data[fanoutV1-4:]))*24 == uint64(len(data)-fanoutV1-trailer) &&
			validIndexChecksum(data) {
			return packIndex{}, fmt.Errorf("%w: version 1 pack index", errStorage)
		}
		return packIndex{}, errObject
	}
	if len(data) < fanoutEnd+trailer {
		return packIndex{}, errObject
	}
	if binary.BigEndian.Uint32(data[4:]) != 2 {
		return packIndex{}, fmt.Errorf("%w: unsupported pack index version", errStorage)
	}
	count64 := uint64(binary.BigEndian.Uint32(data[fanoutEnd-4:]))
	tables := data[fanoutEnd : len(data)-trailer]
	if count64 > uint64(len(tables)/28) {
		return packIndex{}, errObject
	}
	count := int(count64)
	large := tables[28*count:]
	if len(large)%8 != 0 || len(large)/8 > count {
		return packIndex{}, errObject
	}
	if !validIndexChecksum(data) {
		return packIndex{}, errObject
	}
	return packIndex{names: tables[:20*count], offsets: tables[24*count : 28*count], large: large}, nil
}

func validIndexChecksum(data []byte) bool {
	digest := sha1.Sum(data[:len(data)-sha1.Size])
	return bytes.Equal(digest[:], data[len(data)-sha1.Size:])
}

func (idx packIndex) offset(key []byte) (int64, bool, error) {
	count := len(idx.names) / sha1.Size
	i := sort.Search(count, func(i int) bool {
		return bytes.Compare(idx.names[sha1.Size*i:sha1.Size*(i+1)], key) >= 0
	})
	if i == count || !bytes.Equal(idx.names[sha1.Size*i:sha1.Size*(i+1)], key) {
		return 0, false, nil
	}
	off := uint64(binary.BigEndian.Uint32(idx.offsets[4*i:]))
	if off >= 1<<31 {
		pos := (off - (1 << 31)) * 8
		if pos+8 > uint64(len(idx.large)) {
			return 0, true, errObject
		}
		off = binary.BigEndian.Uint64(idx.large[pos:])
	}
	return int64(off), true, nil
}

// Look up candidates in stable order. Only an independently verified object
// establishes evidence. Each index is read and charged once per store.
func (s *store) packed(id string) (object, error) {
	if !s.packsLoaded {
		if err := s.loadPacks(); err != nil {
			s.packFailure = err
		}
		s.packsLoaded = true
	}
	key, _ := hex.DecodeString(id)
	failure := s.packFailure
	if failure == nil {
		failure = errObject
	}
	for i := range s.packs {
		candidate := &s.packs[i]
		if !candidate.loaded {
			candidate.index, candidate.err = s.readIndex(candidate.path)
			candidate.loaded = true
		}
		if candidate.err != nil {
			failure = preferPackFailure(failure, candidate.err)
			continue
		}
		off, found, err := candidate.index.offset(key)
		if !found {
			continue
		}
		if err == nil {
			var obj object
			obj, err = s.readPack(strings.TrimSuffix(candidate.path, ".idx")+".pack", off, id)
			if err == nil {
				return obj, nil
			}
		}
		failure = preferPackFailure(failure, err)
	}
	return object{}, failure
}

func preferPackFailure(known, candidate error) error {
	switch {
	case errors.Is(known, errLimit):
		return known
	case errors.Is(candidate, errLimit):
		return candidate
	case errors.Is(known, errStorage):
		return known
	case errors.Is(candidate, errStorage):
		return candidate
	case known == nil:
		return errObject
	default:
		return known
	}
}

func (s *store) loadPacks() error {
	if err := s.filesystemOp(); err != nil {
		return err
	}
	dir, err := s.root.OpenRoot("objects/pack")
	if errors.Is(err, fs.ErrNotExist) {
		return nil
	}
	if err != nil {
		return errObject
	}
	defer dir.Close()
	if err := s.filesystemOp(); err != nil {
		return err
	}
	f, err := dir.Open(".")
	if err != nil {
		return errObject
	}
	defer f.Close()
	if err := s.filesystemOp(); err != nil {
		return err
	}
	entries, err := f.ReadDir(maxPackEntries + 1)
	if err != nil && err != io.EOF {
		return errObject
	}
	if len(entries) > maxPackEntries {
		return packListingLimit
	}
	var names []string
	for _, entry := range entries {
		name := entry.Name()
		if strings.HasPrefix(name, "pack-") && strings.HasSuffix(name, ".idx") {
			names = append(names, name)
		}
	}
	if len(names) > maxPackIndexes {
		return packCandidateLimit
	}
	slices.Sort(names)
	for _, name := range names {
		s.packs = append(s.packs, packCandidate{path: "objects/pack/" + name})
	}
	return nil
}

func (s *store) readIndex(path string) (packIndex, error) {
	f, err := s.file(path)
	if err != nil {
		return packIndex{}, err
	}
	defer f.Close()
	data, err := s.readBounded(s.reader(f), maxIndexBytes, indexSizeLimit)
	if err != nil {
		return packIndex{}, err
	}
	return parsePackIndex(data)
}

func (s *store) readPack(path string, off int64, id string) (object, error) {
	f, err := s.file(path)
	if err != nil {
		return object{}, err
	}
	defer f.Close()
	var header [12]byte
	if _, err := io.ReadFull(s.reader(f), header[:]); err != nil {
		return object{}, packReadError(err)
	}
	if string(header[:4]) != "PACK" {
		return object{}, errObject
	}
	if version := binary.BigEndian.Uint32(header[4:]); version != 2 && version != 3 {
		return object{}, fmt.Errorf("%w: unsupported pack version", errStorage)
	}
	obj, err := s.packEntry(f, off, 0)
	if err != nil {
		return object{}, err
	}
	return verifyIdentity(obj, id)
}

func packReadError(err error) error {
	if errors.Is(err, errLimit) {
		return err
	}
	return errObject
}
