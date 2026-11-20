//go:build unix

package check

import "syscall"

// A name that changes to a FIFO between metadata lookup and open must
// not wait for a writer. The caller checks the type on the returned handle.
const objectOpenFlags = syscall.O_NONBLOCK
