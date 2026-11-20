package check

import (
	"bytes"
	"context"
	"strings"
	"testing"
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
	})
}
func FuzzDelta(f *testing.F) {
	f.Add([]byte("abc"), []byte{3, 3, 0x90, 3})
	f.Fuzz(func(t *testing.T, base, delta []byte) {
		s := store{ctx: context.Background(), budget: budget{remaining: 65536}}
		out, err := s.applyDelta(base, delta)
		if err == nil && len(out) > 65536 {
			t.Fatal("output exceeds budget")
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
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	s := store{ctx: ctx}
	if _, err := s.read(strings.Repeat("0", 40)); err != timeLimit {
		t.Fatal(err)
	}
}
