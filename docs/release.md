# Release and recovery

Source checks run on six native OS/architecture pairs. A manual Release workflow builds a snapshot and tests the exact archived binaries on all six. Versions for publication use a v-prefixed semantic tag on a commit reachable from main. The release workflow rebuilds that revision, verifies the checksums, runs installation tests, produces GitHub attestations and stages a draft. Only tag a reviewed revision. For limited previews disclose missing platform signatures and the tested install channels.

Download an archive and its checksums from the named release. Verify its listed SHA-256, then verify GitHub provenance independently:

    gh attestation verify ARCHIVE --repo valasme/receipts

On Linux, sha256sum can compute the archive digest. On macOS, use shasum -a 256. PowerShell provides Get-FileHash -Algorithm SHA256. Check that the provenance identifies the expected repository and release workflow. Keep the previous executable until the new one passes help, version and a known fixture.

The candidate contains tar.gz archives for Linux and macOS, Windows zip files, Linux deb/rpm packages and a preview installer manifest bundle. The manifest bundle contains a Homebrew formula, a Scoop bucket entry and a WinGet singleton manifest with the release URLs and hashes. These are candidate manifests; inclusion does not register them in a public tap, bucket or package index. Development snapshots exercise the format but their URLs are placeholders until a matching release exists. Apple signing/notarization and Windows Authenticode need external credentials. These native signatures are independent of GitHub provenance.

For a failed job, inspect the first failing native run, build or install step. Correct the cause and rerun the exact candidate if its inputs are unchanged. A new commit gets a new version. Before making a draft public, confirm its tag, commit, native install runs, checksums, attestation, prerelease flag and release notes. For an incorrect published binary or verdict, identify affected versions in an advisory, disable any live publisher, issue a superseding version and ask affected users to replay their original claims. Keep the old release identity intact.
