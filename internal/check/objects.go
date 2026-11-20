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
	"math"
	"os"
	"strconv"
	"strings"
)

var errObject = errors.New("object_unavailable")
var errStorage = errors.New("unsupported_storage")
var errNotCommit = errors.New("revision must identify a commit object." + resolveCommitHint)
var errCommitTree = errors.New("invalid commit tree reference")

type object struct {
	kind string
	data []byte
}
type store struct {
	root *os.Root
	ctx  context.Context
	budget
	packsLoaded bool
	packs       []packCandidate
	packFailure error
}

func (s *store) commitTree(rev string) (string, error) {
	commit, err := s.read(rev)
	if err != nil {
		return "", err
	}
	if commit.kind != "commit" {
		return "", errNotCommit
	}
	return parseCommit(commit.data)
}

// Read the required headers in their canonical order. Parent IDs describe
// history and do not need to be available to prove a claim about this commit.
func parseCommit(data []byte) (string, error) {
	header, rest, ok := bytes.Cut(data, []byte("\n"))
	if !ok || !bytes.HasPrefix(header, []byte("tree ")) || !canonicalOID(header[5:]) {
		return "", errCommitTree
	}
	treeID := string(header[5:])
	for bytes.HasPrefix(rest, []byte("parent ")) {
		header, rest, ok = bytes.Cut(rest, []byte("\n"))
		if !ok || !canonicalOID(header[7:]) {
			return "", errCommitTree
		}
	}
	for _, prefix := range []string{"author ", "committer "} {
		header, rest, ok = bytes.Cut(rest, []byte("\n"))
		if !ok || !bytes.HasPrefix(header, []byte(prefix)) || !validIdentity(header[len(prefix):]) {
			return "", errCommitTree
		}
	}

	optional := false
	for {
		header, rest, ok = bytes.Cut(rest, []byte("\n"))
		if !ok || bytes.IndexByte(header, 0) >= 0 {
			return "", errCommitTree
		}
		if len(header) == 0 {
			return treeID, nil
		}
		if header[0] == ' ' && optional {
			continue
		}
		key, _, found := bytes.Cut(header, []byte(" "))
		if !found || len(key) == 0 {
			return "", errCommitTree
		}
		for _, c := range key {
			if c <= ' ' || c >= 127 {
				return "", errCommitTree
			}
		}
		switch string(key) {
		case "tree", "parent", "author", "committer":
			return "", errCommitTree
		}
		optional = true
	}
}

func canonicalOID(id []byte) bool {
	if len(id) != 40 {
		return false
	}
	for _, c := range id {
		if (c < '0' || c > '9') && (c < 'a' || c > 'f') {
			return false
		}
	}
	return true
}

func validIdentity(data []byte) bool {
	name, rest, ok := bytes.Cut(data, []byte("<"))
	if !ok || len(name) == 0 || name[len(name)-1] != ' ' || bytes.ContainsAny(name, ">\x00\r") {
		return false
	}
	email, rest, ok := bytes.Cut(rest, []byte("> "))
	if !ok || bytes.ContainsAny(email, "<>\x00\r") {
		return false
	}
	timestamp, zone, ok := bytes.Cut(rest, []byte(" "))
	if !ok || len(timestamp) == 0 || len(zone) != 5 || (zone[0] != '+' && zone[0] != '-') {
		return false
	}
	if _, err := strconv.ParseUint(string(timestamp), 10, 64); err != nil {
		return false
	}
	for _, c := range zone[1:] {
		if c < '0' || c > '9' {
			return false
		}
	}
	return true
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
		mode, id, err := lookup(tree.data, component, &s.treeWork)
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

// Git metadata is data only. Restrict opens to ordinary files beneath the root.
func (s *store) file(name string) (*os.File, error) {
	if err := s.filesystemOp(); err != nil {
		return nil, err
	}
	info, err := s.root.Lstat(name)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() {
		return nil, errStorage
	}
	if err := s.filesystemOp(); err != nil {
		return nil, err
	}
	f, err := s.root.OpenFile(name, os.O_RDONLY|objectOpenFlags, 0)
	if err != nil {
		return nil, err
	}
	info, err = f.Stat()
	if err != nil || !info.Mode().IsRegular() {
		f.Close()
		if err != nil {
			return nil, err
		}
		return nil, errStorage
	}
	return f, nil
}

func (s *store) inflate(r io.Reader, limit int64, limitErr limitError) ([]byte, error) {
	if s.remaining == 0 {
		return nil, objectBytesLimit
	}
	z, err := zlib.NewReader(r)
	if err != nil {
		return nil, packReadError(err)
	}
	defer z.Close()
	return s.readBounded(z, limit, limitErr)
}

func (s *store) read(id string) (object, error) {
	if s.ctx.Err() != nil {
		return object{}, timeLimit
	}
	f, err := s.file("objects/" + id[:2] + "/" + id[2:])
	if errors.Is(err, fs.ErrNotExist) {
		obj, err := s.packed(id)
		if err == errObject {
			if err := s.filesystemOp(); err != nil {
				return object{}, err
			}
			if info, err := s.root.Lstat("objects/info/alternates"); err == nil && info.Size() != 0 {
				return object{}, errAlternates
			}
		}
		return obj, err
	}
	if err != nil {
		return object{}, err
	}
	defer f.Close()
	data, err := s.inflate(s.reader(f), maxBlob+64, objectSizeLimit)
	if err != nil {
		return object{}, err
	}
	obj, err := parseLoose(data)
	if err != nil {
		return object{}, err
	}
	return verifyIdentity(obj, id)
}

func parseLoose(data []byte) (object, error) {
	header, body, ok := bytes.Cut(data, []byte{0})
	kind, size, split := strings.Cut(string(header), " ")
	if !ok || !split || size != strconv.Itoa(len(body)) {
		return object{}, errObject
	}
	if len(body) > maxBlob {
		return object{}, objectSizeLimit
	}
	switch kind {
	case "commit", "tree", "blob", "tag":
		return object{kind, body}, nil
	}
	return object{}, errObject
}

func verifyIdentity(obj object, id string) (object, error) {
	hash := sha1.New()
	fmt.Fprintf(hash, "%s %d\x00", obj.kind, len(obj.data))
	hash.Write(obj.data)
	if hex.EncodeToString(hash.Sum(nil)) != id {
		return object{}, errObject
	}
	return obj, nil
}

func (s *store) packEntry(f *os.File, offset int64, depth int) (object, error) {
	if offset < 12 || offset > math.MaxInt64-(2*maxBlob+1024) {
		return object{}, errObject
	}
	if depth > maxDeltaDepth {
		return object{}, deltaDepthLimit
	}
	if err := s.filesystemOp(); err != nil {
		return object{}, err
	}
	r := bufio.NewReader(s.reader(io.NewSectionReader(f, offset, 2*maxBlob+1024)))
	first, err := r.ReadByte()
	if err != nil {
		return object{}, packReadError(err)
	}
	typ := (first >> 4) & 7
	size := int64(first & 15)
	for b, shift := first, uint(4); b&128 != 0; shift += 7 {
		b, err = r.ReadByte()
		if err != nil {
			return object{}, packReadError(err)
		}
		if shift > 25 {
			return object{}, objectSizeLimit
		}
		size |= int64(b&127) << shift
	}
	if size > maxBlob {
		return object{}, objectSizeLimit
	}
	var baseOffset int64
	if typ == 6 {
		b, err := r.ReadByte()
		if err != nil {
			return object{}, packReadError(err)
		}
		distance := int64(b & 127)
		for b&128 != 0 {
			if distance > offset>>7 {
				return object{}, errObject
			}
			b, err = r.ReadByte()
			if err != nil {
				return object{}, packReadError(err)
			}
			distance = (distance+1)*128 + int64(b&127)
		}
		if distance <= 0 || distance > offset-12 {
			return object{}, errObject
		}
		baseOffset = offset - distance
	} else if typ == 7 {
		return object{}, fmt.Errorf("%w: reference delta", errStorage)
	} else if typ < 1 || typ > 4 {
		return object{}, errObject
	}
	data, err := s.inflate(r, size, objectSizeLimit)
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
	if target > maxBlob {
		return nil, objectSizeLimit
	}
	if int64(target) > s.remaining {
		return nil, objectBytesLimit
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
