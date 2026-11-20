//go:build !unix

package check

// Windows rooted opens resolve relative to a directory handle, outside
// the named pipe namespace. The caller checks the type on the returned handle.
const objectOpenFlags = 0
