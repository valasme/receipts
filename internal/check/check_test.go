package check

import (
	"bytes"
	"context"
	"crypto/sha1"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"strings"
	"testing"
	"time"
)

func FuzzLookup(f *testing.F) {
	f.Add([]byte("100644 a\x00"+strings.Repeat("x", 20)), "a")
	f.Add([]byte("40000 bad"), "x")
	f.Fuzz(func(t *testing.T, data []byte, path string) {
		remaining := maxTreeWork
		mode, id, err := lookup(data, path, &remaining)
		if err == nil && id != "" && (len(id) != 40 || mode == "") {
			t.Fatal("invalid tree witness")
		}
		// Use arbitrary bytes to generate independent object IDs for a complete,
		// ordered tree. Include the ordering distinction for a directory.
		dirID := sha1.Sum(data)
		fileID := sha1.Sum([]byte(path))
		tree := append([]byte("100644 dir.txt\x00"), fileID[:]...)
		tree = append(tree, []byte("40000 dir\x00")...)
		tree = append(tree, dirID[:]...)
		for _, wanted := range []struct {
			path, mode, id string
		}{
			{"dir", "40000", hex.EncodeToString(dirID[:])},
			{"dir.txt", "100644", hex.EncodeToString(fileID[:])},
			{"absent", "", ""},
		} {
			remaining := maxTreeWork
			mode, id, err := lookup(tree, wanted.path, &remaining)
			if err != nil || mode != wanted.mode || id != wanted.id {
				t.Fatalf("%q: got %q %q, %v", wanted.path, mode, id, err)
			}
			remaining = maxTreeWork
			if _, _, err := lookup(tree[:len(tree)-1], wanted.path, &remaining); err == nil {
				t.Fatalf("%q: accepted a truncated suffix", wanted.path)
			}
		}
	})
}
func FuzzDelta(f *testing.F) {
	f.Add([]byte("abc"), []byte{3, 3, 0x90, 3})
	f.Add([]byte("abc"), []byte{3, 2, 2, 'x', 'y'})
	f.Add([]byte{}, []byte{0, 0})
	f.Add([]byte("before"), []byte{6, 5, 0x91, 2, 3, 2, 's', 't'})
	f.Fuzz(func(t *testing.T, base, delta []byte) {
		s := store{ctx: context.Background(), budget: budget{remaining: 65536}}
		out, err := s.applyDelta(base, delta)
		if err == nil && len(out) > 65536 {
			t.Fatal("output exceeds budget")
		}
		// Generate a copy/insert/copy program and obtain the expected bytes
		// through ordinary slices, independently of the wire decoder.
		base = base[:min(len(base), 126)]
		insert := delta[:min(len(delta), 127)]
		split := len(base) / 2
		program := []byte{byte(len(base))}
		program = binary.AppendUvarint(program, uint64(len(base)+len(insert)))
		if split > 0 {
			program = append(program, 0x91, byte(split), byte(split))
		}
		if len(insert) > 0 {
			program = append(program, byte(len(insert)))
			program = append(program, insert...)
		}
		if split > 0 {
			program = append(program, 0x90, byte(split))
		}
		if len(base)%2 != 0 {
			program = append(program, 0x91, byte(2*split), 1)
		}
		expected := bytes.Join([][]byte{base[split : 2*split], insert, base[:split], base[2*split:]}, nil)
		s.budget = newBudget()
		out, err = s.applyDelta(base, program)
		if err != nil || !bytes.Equal(out, expected) {
			t.Fatalf("got %x, %v; want %x", out, err, expected)
		}
		s.budget = newBudget()
		if _, err := s.applyDelta(base, append(program, 0)); err == nil {
			t.Fatal("accepted an invalid trailing instruction")
		}
	})
}
func TestDeltaCopyAndInsert(t *testing.T) {
	s := store{budget: budget{remaining: 1024}}
	got, err := s.applyDelta([]byte("before"), []byte{6, 5, 0x91, 2, 3, 2, 's', 't'})
	if err != nil || string(got) != "forst" {
		t.Fatalf("%q %v", got, err)
	}
}
func TestMalformedTrees(t *testing.T) {
	item := []byte("100644 a\x00" + strings.Repeat("x", 20))
	for _, data := range [][]byte{append(bytes.Clone(item), item...), item[:len(item)-1], append(bytes.Clone(item), 0)} {
		remaining := maxTreeWork
		if _, _, err := lookup(data, "a", &remaining); err == nil {
			t.Fatal("accepted incomplete or duplicate tree")
		}
	}
}
func TestExpiredBudget(t *testing.T) {
	ctx, cancel := context.WithDeadline(context.Background(), time.Now().Add(-time.Second))
	defer cancel()
	pin := strings.Repeat("0", 40)
	r, err := Verify(ctx, t.TempDir(), pin, "item", []byte("sample"), "test")
	if err != nil || r.Verdict != "cant_check" || r.Reason != "resource_limit" || !strings.Contains(r.Detail, "deadline") {
		t.Fatalf("receipt %+v, error %v", r, err)
	}
	rChange, err := VerifyFileChange(ctx, t.TempDir(), pin, pin, "item")
	if err != nil || !strings.Contains(rChange.Text(), "object access and comparison deadline") {
		t.Fatalf("receipt %s, error %v", rChange.Text(), err)
	}
}

func FuzzCommit(f *testing.F) {
	const identity = "Fixture <test@example.invalid> 1735689600 +0000"
	const tree = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	const required = "author " + identity + "\ncommitter " + identity + "\n"
	f.Add([]byte("tree " + tree + "\n" + required + "\n"))
	f.Add([]byte("tree " + tree + "\nauthor bad\n"))
	f.Add([]byte("tree " + strings.ToUpper(tree) + "\n" + required + "\n"))
	f.Fuzz(func(t *testing.T, data []byte) {
		got, err := parseCommit(data)
		if err == nil {
			decoded, decodeErr := hex.DecodeString(got)
			if decodeErr != nil || len(decoded) != 20 ||
				!bytes.HasPrefix(data, []byte("tree "+hex.EncodeToString(decoded)+"\n")) {
				t.Fatalf("invalid tree reference %q", got)
			}
		}

		parent := sha1.Sum(data)
		valid := fmt.Sprintf("tree %s\nparent %x\n%sgpgsig example\n continuation\n\n", tree, parent, required)
		commit := append([]byte(valid), data...)
		if got, err := parseCommit(commit); got != tree || err != nil {
			t.Fatalf("rejected canonical header: %q, %v", got, err)
		}
		if _, err := parseCommit([]byte(strings.Replace(valid, "committer ", "editor ", 1))); err == nil {
			t.Fatal("accepted missing committer")
		}
	})
}

func FuzzLoose(f *testing.F) {
	f.Add([]byte("blob 5\x00hello"))
	f.Add([]byte("blob 6\x00hello"))
	f.Add([]byte("tree 00\x00"))
	f.Fuzz(func(t *testing.T, data []byte) {
		obj, err := parseLoose(data)
		if err == nil {
			want := []byte(fmt.Sprintf("%s %d\x00", obj.kind, len(obj.data)))
			if !bytes.Equal(data, append(want, obj.data...)) {
				t.Fatal("loose framing does not round trip")
			}
		}
		if len(data) > maxBlob {
			return
		}
		complete := append([]byte(fmt.Sprintf("blob %d\x00", len(data))), data...)
		obj, err = parseLoose(complete)
		if err != nil || obj.kind != "blob" || !bytes.Equal(obj.data, data) {
			t.Fatalf("rejected generated blob: %v", err)
		}
	})
}

func FuzzPackIndex(f *testing.F) {
	f.Add([]byte{255, 't', 'O', 'c', 0, 0, 0, 2}, uint32(12))
	f.Add([]byte("irrelevant contents"), uint32(1<<31))
	f.Fuzz(func(t *testing.T, data []byte, offset uint32) {
		key := sha1.Sum(data)
		if idx, err := parsePackIndex(data); err == nil {
			// Lookup also exercises offset table bounds on arbitrary input.
			_, _, _ = idx.offset(key[:])
		}
		valid := []byte{255, 't', 'O', 'c', 0, 0, 0, 2}
		for i := range 256 {
			var count uint32
			if i >= int(key[0]) {
				count = 1
			}
			valid = binary.BigEndian.AppendUint32(valid, count)
		}
		valid = append(valid, key[:]...)
		valid = append(valid, 0, 0, 0, 0) // CRC table
		if offset < 1<<31 {
			valid = binary.BigEndian.AppendUint32(valid, offset)
		} else {
			valid = binary.BigEndian.AppendUint32(valid, 1<<31)
			valid = binary.BigEndian.AppendUint64(valid, uint64(offset))
		}
		valid = append(valid, make([]byte, sha1.Size)...)
		sum := sha1.Sum(valid)
		valid = append(valid, sum[:]...)
		idx, err := parsePackIndex(valid)
		if err != nil {
			t.Fatal(err)
		}
		got, found, err := idx.offset(key[:])
		if !found || err != nil || got != int64(offset) {
			t.Fatalf("got offset %d, found %t, %v; want %d", got, found, err, offset)
		}
		if _, err := parsePackIndex(valid[:len(valid)-1]); err == nil {
			t.Fatal("accepted a truncated index")
		}
	})
}
