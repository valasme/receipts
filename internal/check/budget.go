package check

import (
	"context"
	"errors"
	"io"
)

const (
	maxBlob        = 8 << 20
	maxObjectBytes = 32 << 20
	maxReadBytes   = 64 << 20
	maxFileOps     = 4096
	maxTreeEntries = 32768
	maxTreeWork    = 131072
	maxIndexBytes  = 4 << 20
	maxPackIndexes = 256
	maxPackEntries = 4096
	maxDeltaDepth  = 16
)

var errLimit = errors.New("resource_limit")

type limitError string

func (e limitError) Error() string { return string(e) }
func (e limitError) Unwrap() error { return errLimit }

const (
	timeLimit          = limitError("object access and comparison deadline")
	objectSizeLimit    = limitError("8 MiB uncompressed object size")
	objectBytesLimit   = limitError("32 MiB cumulative object and index bytes")
	readBytesLimit     = limitError("64 MiB cumulative filesystem bytes")
	fileOpsLimit       = limitError("4096 filesystem operations")
	treeSizeLimit      = limitError("32768 entries in one tree")
	treeWorkLimit      = limitError("131072 cumulative tree entries")
	indexSizeLimit     = limitError("4 MiB pack index size")
	packCandidateLimit = limitError("256 pack index candidates")
	packListingLimit   = limitError("4096 pack directory entries")
	deltaDepthLimit    = limitError("16 pack delta levels")
)

type budget struct {
	remaining int64
	readBytes int64
	fileOps   int
	treeWork  int
}

func newBudget() budget {
	return budget{
		remaining: maxObjectBytes,
		readBytes: maxReadBytes,
		fileOps:   maxFileOps,
		treeWork:  maxTreeWork,
	}
}

func (s *store) filesystemOp() error {
	if s.ctx.Err() != nil {
		return timeLimit
	}
	if s.fileOps == 0 {
		return fileOpsLimit
	}
	s.fileOps--
	return nil
}

type budgetedReader struct {
	ctx       context.Context
	remaining *int64
	reader    io.Reader
}

func (r budgetedReader) Read(p []byte) (int, error) {
	if r.ctx.Err() != nil {
		return 0, timeLimit
	}
	if *r.remaining == 0 {
		return 0, readBytesLimit
	}
	n, err := r.reader.Read(p[:min(int64(len(p)), *r.remaining)])
	*r.remaining -= int64(n)
	return n, err
}

func (s *store) reader(r io.Reader) io.Reader {
	return budgetedReader{s.ctx, &s.readBytes, r}
}

func (s *store) readBounded(r io.Reader, limit int64, limitErr error) ([]byte, error) {
	if s.ctx.Err() != nil {
		return nil, timeLimit
	}
	if s.remaining == 0 {
		return nil, objectBytesLimit
	}
	total := min(limit, s.remaining)
	data, err := io.ReadAll(io.LimitReader(r, total+1))
	s.remaining -= min(int64(len(data)), total)
	if s.ctx.Err() != nil {
		return nil, timeLimit
	}
	if int64(len(data)) > total {
		if total < limit {
			return nil, objectBytesLimit
		}
		return nil, limitErr
	}
	if errors.Is(err, errLimit) {
		return nil, err
	}
	if err != nil {
		return nil, errObject
	}
	return data, nil
}
