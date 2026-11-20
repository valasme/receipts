package check

import (
	"context"
	"errors"
	"strings"
)

// Inspection shares one offline observation budget across an admitted command.
// Its methods are synchronous to the caller. Close releases its repository root
// once any operation still returning from the filesystem has completed.
type Inspection struct {
	ctx     context.Context
	repo    string
	version string
	state   chan inspectionState
}

type inspectionState struct {
	opened bool
	store  *store
	err    error
}

func NewInspection(ctx context.Context, repo, version string) *Inspection {
	state := make(chan inspectionState, 1)
	state <- inspectionState{}
	return &Inspection{ctx: ctx, repo: repo, version: version, state: state}
}

func (i *Inspection) Close() {
	closeRoot := func(state inspectionState) {
		if state.store != nil {
			state.store.root.Close()
		}
	}
	select {
	case state := <-i.state:
		closeRoot(state)
	default:
		go func() { closeRoot(<-i.state) }()
	}
}

func observe[T any](i *Inspection, timeout T, run func(*store, error) (T, error)) (T, error) {
	if i.ctx.Err() != nil {
		return timeout, nil
	}
	var state inspectionState
	select {
	case state = <-i.state:
	case <-i.ctx.Done():
		return timeout, nil
	}
	type result struct {
		value T
		err   error
	}
	done := make(chan result, 1)
	go func() {
		if !state.opened {
			state.store, state.err = openStore(i.ctx, i.repo)
			state.opened = true
		}
		value, err := run(state.store, state.err)
		i.state <- state
		done <- result{value, err}
	}()
	select {
	case completed := <-done:
		if i.ctx.Err() == nil {
			return completed.value, completed.err
		}
	case <-i.ctx.Done():
	}
	return timeout, nil
}

// ValidateSharedRevision rejects a known non-commit at the envelope boundary.
// Unavailable evidence is carried by each subsequent claim receipt.
func (i *Inspection) ValidateSharedRevision(rev string) error {
	if err := ValidateRevision(rev); err != nil {
		return err
	}
	_, err := observe(i, struct{}{}, func(s *store, opening error) (struct{}, error) {
		if opening == nil {
			if _, err := s.commitTree(strings.ToLower(rev)); errors.Is(err, errNotCommit) {
				return struct{}{}, err
			}
		}
		return struct{}{}, nil
	})
	return err
}
