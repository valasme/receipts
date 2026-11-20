// Package check verifies claims against immutable local Git objects.
package check

import (
	"bufio"
	"bytes"
	"compress/zlib"
	"context"
	"crypto/sha1"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"sort"
	"strconv"
	"strings"
)

const maxBlob = 8 << 20

var errLimit = errors.New("resource_limit")
var errObject = errors.New("object_unavailable")
var errStorage = errors.New("unsupported_storage")
var errNotCommit = errors.New("revision must identify a commit object." + resolveCommitHint)
var errCommitTree = errors.New("invalid commit tree reference")

type object struct {
	kind string
	data []byte
}
type store struct {
	root      *os.Root
	ctx       context.Context
	remaining int64
}

func (s *store) commitTree(rev string) (string, error) {
	commit, err := s.read(rev)
	if err != nil {
		return "", err
	}
	if commit.kind != "commit" {
		return "", errNotCommit
	}
	header, _, ok := bytes.Cut(commit.data, []byte("\n"))
	if !ok || len(header) != 45 || !bytes.HasPrefix(header, []byte("tree ")) {
		return "", errCommitTree
	}
	treeID := string(header[5:])
	if _, err := hex.DecodeString(treeID); err != nil {
		return "", errCommitTree
	}
	return treeID, nil
}

type pathEntry struct {
	tree, mode, id, component string
	blocked                   bool
}

func (s *store) findPath(treeID, path string) (pathEntry, error) {
	for {
		component, rest, hasRest := strings.Cut(path, "/")
		tree, err := s.read(treeID)
		if err != nil {
			return pathEntry{}, err
		}
		if tree.kind != "tree" {
			return pathEntry{}, errObject
		}
		mode, id, err := lookup(tree.data, component)
		if err != nil {
			return pathEntry{}, err
		}
		if hasRest && mode == "40000" {
			treeID, path = id, rest
			continue
		}
		return pathEntry{
			tree:      treeID,
			mode:      mode,
			id:        id,
			component: component,
			blocked:   hasRest && id != "",
		}, nil
	}
}

func (s *store) readBlob(id string) ([]byte, error) {
	blob, err := s.read(id)
	if err != nil {
		return nil, err
	}
	if blob.kind != "blob" {
		return nil, errObject
	}
	return blob.data, nil
}

func openStore(ctx context.Context, path string) (*store, error) {
	root, err := os.OpenRoot(path)
	if err != nil {
		return nil, err
	}
	if _, err := root.Lstat(".git"); err == nil {
		child, err := root.OpenRoot(".git")
		root.Close()
		if err != nil {
			return nil, errStorage
		}
		root = child
	}
	info, err := root.Stat("objects")
	if err != nil || !info.IsDir() {
		root.Close()
		return nil, errObject
	}
	return &store{root, ctx, 32 << 20}, nil
}

// Git metadata is data only. Restrict opens to ordinary files beneath the root.
func (s *store) file(name string) (*os.File, error) {
	info, err := s.root.Lstat(name)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() {
		return nil, errStorage
	}
	return s.root.Open(name)
}

func (s *store) inflate(r io.Reader, limit int64) ([]byte, error) {
	if err := s.ctx.Err(); err != nil {
		return nil, errLimit
	}
	limit = min(limit, s.remaining)
	z, err := zlib.NewReader(r)
	if err != nil {
		return nil, errObject
	}
	defer z.Close()
	data, err := io.ReadAll(io.LimitReader(z, limit+1))
	s.remaining -= int64(len(data))
	if int64(len(data)) > limit || s.ctx.Err() != nil {
		return nil, errLimit
	}
	if err != nil {
		return nil, errObject
	}
	return data, nil
}

func (s *store) read(id string) (object, error) {
	if s.ctx.Err() != nil {
		return object{}, errLimit
	}
	f, err := s.file("objects/" + id[:2] + "/" + id[2:])
	var obj object
	if errors.Is(err, fs.ErrNotExist) {
		obj, err = s.packed(id)
	} else if err == nil {
		defer f.Close()
		var data []byte
		data, err = s.inflate(f, maxBlob+64)
		if err == nil {
			header, body, ok := bytes.Cut(data, []byte{0})
			kind, size, split := strings.Cut(string(header), " ")
			if !ok || !split || size != strconv.Itoa(len(body)) {
				return object{}, errObject
			}
			if len(body) > maxBlob {
				return object{}, errLimit
			}
			obj = object{kind, body}
		}
	}
	if err != nil {
		return object{}, err
	}
	hash := sha1.New()
	fmt.Fprintf(hash, "%s %d\x00", obj.kind, len(obj.data))
	hash.Write(obj.data)
	if hex.EncodeToString(hash.Sum(nil)) != id {
		return object{}, errObject
	}
	return obj, nil
}

// Read bounded v2 indexes. Always verify the reconstructed object's identity.
func (s *store) packed(id string) (object, error) {
	info, err := s.root.Stat("objects/pack")
	if err != nil || !info.IsDir() {
		return object{}, errObject
	}
	dir, err := s.root.Open("objects/pack")
	if err != nil {
		return object{}, errObject
	}
	defer dir.Close()
	entries, err := dir.ReadDir(257)
	if err != nil && err != io.EOF {
		return object{}, errObject
	}
	if len(entries) > 256 {
		return object{}, errLimit
	}
	key, _ := hex.DecodeString(id)
	for _, entry := range entries {
		name := entry.Name()
		if !strings.HasPrefix(name, "pack-") || !strings.HasSuffix(name, ".idx") {
			continue
		}
		index, err := s.file("objects/pack/" + name)
		if err != nil {
			return object{}, errObject
		}
		limit := min(s.remaining, int64(4<<20))
		data, err := io.ReadAll(io.LimitReader(index, limit+1))
		index.Close()
		s.remaining -= int64(len(data))
		if int64(len(data)) > limit || s.ctx.Err() != nil {
			return object{}, errLimit
		}
		if err != nil || len(data) < 1032 || !bytes.Equal(data[:8], []byte{255, 't', 'O', 'c', 0, 0, 0, 2}) {
			return object{}, errStorage
		}
		count64 := uint64(binary.BigEndian.Uint32(data[1028:]))
		if count64 > uint64((len(data)-1032)/28) {
			return object{}, errObject
		}
		count := int(count64)
		names := data[1032 : 1032+20*count]
		i := sort.Search(count, func(i int) bool { return bytes.Compare(names[20*i:20*i+20], key) >= 0 })
		if i == count || !bytes.Equal(names[20*i:20*i+20], key) {
			continue
		}
		offsets := data[1032+24*count:]
		off := uint64(binary.BigEndian.Uint32(offsets[4*i:]))
		if off >= 1<<31 {
			pos := uint64(4*count) + (off-(1<<31))*8
			if pos+8 > uint64(len(offsets)) {
				return object{}, errObject
			}
			off = binary.BigEndian.Uint64(offsets[pos:])
		}
		f, err := s.file("objects/pack/" + strings.TrimSuffix(name, ".idx") + ".pack")
		if err != nil {
			return object{}, errObject
		}
		defer f.Close()
		return s.packEntry(f, int64(off), 0)
	}
	return object{}, errObject
}

func (s *store) packEntry(f *os.File, offset int64, depth int) (object, error) {
	if offset < 12 {
		return object{}, errObject
	}
	if depth > 16 || s.ctx.Err() != nil {
		return object{}, errLimit
	}
	r := bufio.NewReader(io.NewSectionReader(f, offset, 2*maxBlob+1024))
	first, err := r.ReadByte()
	if err != nil {
		return object{}, errObject
	}
	typ := (first >> 4) & 7
	size := int64(first & 15)
	for b, shift := first, uint(4); b&128 != 0; shift += 7 {
		b, err = r.ReadByte()
		if err != nil {
			return object{}, errObject
		}
		if shift > 25 {
			return object{}, errLimit
		}
		size |= int64(b&127) << shift
	}
	if size > maxBlob {
		return object{}, errLimit
	}
	var baseOffset int64
	if typ == 6 {
		b, err := r.ReadByte()
		if err != nil {
			return object{}, errObject
		}
		distance := int64(b & 127)
		for b&128 != 0 {
			if distance > offset>>7 {
				return object{}, errObject
			}
			b, err = r.ReadByte()
			if err != nil {
				return object{}, errObject
			}
			distance = (distance+1)*128 + int64(b&127)
		}
		if distance <= 0 || distance > offset-12 {
			return object{}, errObject
		}
		baseOffset = offset - distance
	} else if typ < 1 || typ > 4 {
		return object{}, errStorage
	}
	data, err := s.inflate(r, size)
	if err != nil {
		return object{}, err
	}
	if int64(len(data)) != size {
		return object{}, errObject
	}
	if typ != 6 {
		return object{[]string{"", "commit", "tree", "blob", "tag"}[typ], data}, nil
	}
	base, err := s.packEntry(f, baseOffset, depth+1)
	if err != nil {
		return object{}, err
	}
	result, err := s.applyDelta(base.data, data)
	return object{base.kind, result}, err
}

func (s *store) applyDelta(base, delta []byte) ([]byte, error) {
	size, n := binary.Uvarint(delta)
	if n <= 0 || size != uint64(len(base)) {
		return nil, errObject
	}
	delta = delta[n:]
	target, n := binary.Uvarint(delta)
	if n <= 0 {
		return nil, errObject
	}
	if target > maxBlob || int64(target) > s.remaining {
		return nil, errLimit
	}
	s.remaining -= int64(target)
	delta = delta[n:]
	out := make([]byte, 0, int(target))
	for len(delta) > 0 {
		op := delta[0]
		delta = delta[1:]
		if op == 0 {
			return nil, errObject
		}
		if op&128 == 0 {
			count := int(op)
			if count > len(delta) || count > cap(out)-len(out) {
				return nil, errObject
			}
			out = append(out, delta[:count]...)
			delta = delta[count:]
			continue
		}
		var fields [7]uint32
		for i := range fields {
			if op&(1<<i) != 0 {
				if len(delta) == 0 {
					return nil, errObject
				}
				fields[i] = uint32(delta[0])
				delta = delta[1:]
			}
		}
		start := uint64(fields[0] | fields[1]<<8 | fields[2]<<16 | fields[3]<<24)
		length := uint64(fields[4] | fields[5]<<8 | fields[6]<<16)
		if length == 0 {
			length = 65536
		}
		if start+length > uint64(len(base)) || length > uint64(cap(out)-len(out)) {
			return nil, errObject
		}
		out = append(out, base[start:start+length]...)
	}
	if len(out) != cap(out) {
		return nil, errObject
	}
	return out, nil
}
