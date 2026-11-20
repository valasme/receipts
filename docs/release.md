# Release and recovery

Source checks run on six native OS/architecture pairs. A manual Release workflow builds a snapshot and tests the exact archived binaries on all six. Versions for publication use a v-prefixed semantic tag on a commit reachable from main. The release workflow rebuilds that revision, verifies the checksums, runs installation tests, produces GitHub attestations and stages a draft. Only tag a reviewed revision. For limited previews disclose missing platform signatures and the tested install channels.

Download an archive and its checksums from the named release. Verify its listed SHA-256, then verify GitHub provenance independently:

    gh attestation verify ARCHIVE --repo valasme/receipts --signer-workflow valasme/receipts/.github/workflows/release.yml

On Linux, sha256sum can compute the archive digest. On macOS, use shasum -a 256. PowerShell provides Get-FileHash -Algorithm SHA256. Check that the provenance identifies the expected repository and release workflow. Keep the previous executable until the new one passes help, version and a known fixture.

The candidate contains tar.gz archives for Linux and macOS, Windows zip files, Linux deb/rpm packages and a preview installer manifest bundle. The manifest bundle contains a Homebrew formula, a Scoop bucket entry and a WinGet multi-file manifest with the release URLs and hashes. These are candidate manifests; inclusion does not register them in a public tap, bucket or package index. Development snapshots exercise the format but their URLs are placeholders until a matching release exists. Apple signing/notarization and Windows Authenticode need external credentials. These native signatures are independent of GitHub provenance.

For a failed job, inspect the first failing native run, build or install step. Correct the cause and rerun the exact candidate if its inputs are unchanged. A new commit gets a new version. Before making a draft public, confirm its tag, commit, native install runs, checksums, attestation, prerelease flag and release notes. For an incorrect published binary or verdict, identify affected versions in an advisory, disable any live publisher, issue a superseding version and ask affected users to replay their original claims. Keep the old release identity intact.

For a toolchain-only rebuild of an existing source tag, run the Release workflow on main with candidate_tag set to that tag. The package job checks out the unchanged tag, records the compiler and source commit, and scans all six built binaries. A patched compiler can build an older supported language version. For source installation, use a supported Go toolchain with current security patches. The build record and checksum manifest are both attested by the release workflow. The signed build-record.json distinguishes the tagged application source from the workflow revision that produced its assets.

## Install the unsigned limited preview

Download the archive matching your OS and processor. Each archive contains the executable, a README and the Apache-2.0 license. [v0.0.1-pre.1 assets](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.1)

| Operating system | Intel or AMD 64-bit | ARM64 |
| --- | --- | --- |
| Linux | `receipts_0.0.1-pre.1_linux_amd64.tar.gz` | `receipts_0.0.1-pre.1_linux_arm64.tar.gz` |
| macOS | `receipts_0.0.1-pre.1_darwin_amd64.tar.gz` | `receipts_0.0.1-pre.1_darwin_arm64.tar.gz` (Apple Silicon) |
| Windows | `receipts_0.0.1-pre.1_windows_amd64.zip` | `receipts_0.0.1-pre.1_windows_arm64.zip` |

Verify the downloaded archive with the provenance command above. A matching SHA-256 establishes that its bytes match the entry in the manifest. The GitHub attestation identifies the workflow that produced it. Extract it into a directory you own, then run `./receipts --help` on Linux or macOS, or `.\receipts.exe --help` in PowerShell. To uninstall, delete that extracted directory. Apple notarization and Windows Authenticode are pending. Use the install methods your organization and OS permit.

With Go and its binary directory on PATH, you can install the pinned source module instead:

    go install github.com/valasme/receipts/cmd/receipts@v0.0.1-pre.1
    receipts --version

The Go install reports `receipts v0.0.1-pre.1`. Release archives report `receipts 0.0.1-pre.1`.

Linux deb and rpm packages are available on the same release. The optional `preview-installers.zip` contains `Formula/receipts.rb`, `bucket/receipts.json` and the multi-file `winget/` manifest. These work with a local Homebrew tap, a local Scoop manifest and WinGet's local-manifest feature. Their URLs point to the public release. Stable package-index registration remains outside this preview. The [consumer workflow](../.github/workflows/consumer.yml) gives the commands tested on each platform.
