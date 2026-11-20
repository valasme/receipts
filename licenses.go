// Package receipts provides the license notices accompanying the Receipts CLI.
package receipts

import _ "embed"

//go:embed LICENSE
var projectLicense string

//go:embed THIRD-PARTY-NOTICES.txt
var thirdPartyNotices string

// LicenseText returns the project license followed by its binary distribution notices.
func LicenseText() string {
	return projectLicense + "\n" + thirdPartyNotices
}
