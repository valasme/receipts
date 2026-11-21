# Release and recovery

Source checks run on six native OS and architecture pairs. A manual Release workflow with an empty tag builds a snapshot. A tagged run resolves the fully qualified tag to one commit on main and uses that SHA for source checks, packaging and archived-executable tests. The build record identifies the source commit, workflow commit and compiler. Each archived executable matches the corresponding binary sent to the vulnerability scanner.

A successful six-target candidate install stages a prerelease draft and reports the draft ID and the SHA-256 of `checksums.txt` in the run summary. Review the draft notes, source and native qualification results. To approve that candidate, dispatch Release on main with `candidate_tag`, `draft_id` and `candidate_checksum` from the reviewed run. Promotion verifies the current tag, attested manifest and build record, and every asset on that same draft. The Release workflow then runs the public consumer matrix on the published tag. Public install also accepts manual dispatch for rechecks.

### Verify and install a pinned release

Run these commands from a checkout of Receipts with Python 3.11 or newer and an authenticated GitHub CLI. This Linux amd64 example pins the published tag, the source and workflow commits, and the manifest SHA-256 for v0.0.1-pre.2. The verifier fetches the exact asset set, checks the attested manifest and build record against the release workflow, and compares every file with its authenticated hash. Choose the archive filename from the target table below for your platform.

```sh
tag=v0.0.1-pre.2
source=57f6601e0c52aaf835f8930ebc2ff81a603f8ffd
workflow=57f6601e0c52aaf835f8930ebc2ff81a603f8ffd
manifest=e6364759df3af594cf05638ac87dfe96cde3a5298180d663c8c12afd15ebb49e
work=$(mktemp -d)
python packaging/stage.py public "$tag" "$work/bundle" \
  --commit "$source" --workflow "$workflow" --checksum "$manifest" &&
  mkdir "$work/install" &&
  tar -xzf "$work/bundle/receipts_0.0.1-pre.2_linux_amd64.tar.gz" -C "$work/install" &&
  "$work/install/receipts" --version
```

Expect `receipts 0.0.1-pre.2`. Keep the previous executable until the new one passes help, version and a known fixture.

The candidate contains tar.gz archives for Linux and macOS, Windows zip files, Linux deb/rpm packages and a preview installer manifest bundle. The manifest bundle contains a Homebrew formula, a Scoop bucket entry and a WinGet multi-file manifest with the release URLs and hashes. These are candidate manifests; inclusion does not register them in a public tap, bucket or package index. Development snapshots exercise the format but their URLs are placeholders until a matching release exists. The owner will provide Apple and Windows signing access once they judge the product ready for v1. These native signatures are independent of GitHub provenance. [Signing decision](adr/0002-defer-native-signing-until-v1.md)

For a failed job, inspect the first failing native run, build or install step. Correct the cause and rerun the exact candidate if its inputs are unchanged. A new commit gets a new version. Before approving a draft, confirm its tag, commit, native install runs, checksums, attestation, prerelease flag and release notes. For an incorrect published binary or verdict, identify affected versions in an advisory, disable any live publisher, issue a superseding version and ask affected users to replay their original claims. Keep the old release identity intact.

For a toolchain-only rebuild of an existing source tag, run the Release workflow on main with `candidate_tag` set to that tag. The package job checks out the resolved commit, checks compiler and revision metadata from the six executables, and scans each one. A patched compiler can build an older supported language version. For source installation, use a supported Go toolchain with current security patches. The public Go checks compare the default-proxy and direct module origin hashes with the authenticated source commit before installing. The build record and checksum manifest are both attested by the release workflow. The signed build-record.json distinguishes the tagged application source from the workflow revision that produced its assets.

## Recover an interrupted or superseded preview

1. Find the failed release run and confirm the tag resolves to its original source commit. Recover the candidate by rerunning the failed staging job on that run. Keep the candidate artifact and its attestations together. If the original qualification inputs are unavailable, qualify a fresh version separately before staging again.
2. Check that the draft assets have the same names and hashes as the candidate. The packaging configuration uses the source commit time for binary, archive, and package metadata so repeat builds with the same inputs can match. Staging resumes missing uploads and stops on a different or unexpected asset. The workflow serializes staging and promotion for the tag. Keep the tag and draft assets unchanged during those jobs. A published immutable release retains its original identity.
3. GitHub can leave a zero-byte asset in the `starter` state after an upload returns HTTP 502. Match the draft ID, tag, asset ID and expected name in the staging diagnostic against the draft and its asset list. Confirm the release is still a draft and the asset still has state `starter` and size zero. Remove that asset from the draft, then rerun the staging job for the same candidate. Preserve uploaded assets and resolve any digest mismatch before retrying. [GitHub release assets API](https://docs.github.com/en/rest/releases/assets#list-release-assets)
4. For an incorrect published artifact, pause installation instructions that point to the affected version. Hold any GitHub publisher and identify affected versions, the symptom, the impact and the verified replacement in the advisory. If no verified replacement is available, ask users to stop using the affected version. For an incorrect receipt, ask readers to replay the original claim with the replacement and review any decision that relied on the old receipt.
5. Verify the replacement's signed checksum manifest and the downloaded file's digest, install in a clean directory and check the version, help and a known fixture. Update the public install guidance and provide a direct archive link if a package index lags. Accept ordinary support requests with synthetic fixtures and route sensitive reports to private reporting. [Issue tracker](https://github.com/valasme/receipts/issues) · [Private security report](https://github.com/valasme/receipts/security/advisories/new)

## Install the unsigned limited preview

Download the archive matching your OS and processor. Each archive contains the executable, a README, the Apache-2.0 license and third-party notices. [v0.0.1-pre.2 assets](https://github.com/valasme/receipts/releases/tag/v0.0.1-pre.2)

| Operating system | Intel or AMD 64-bit | ARM64 |
| --- | --- | --- |
| Linux | `receipts_0.0.1-pre.2_linux_amd64.tar.gz` | `receipts_0.0.1-pre.2_linux_arm64.tar.gz` |
| macOS | `receipts_0.0.1-pre.2_darwin_amd64.tar.gz` | `receipts_0.0.1-pre.2_darwin_arm64.tar.gz` (Apple Silicon) |
| Windows | `receipts_0.0.1-pre.2_windows_amd64.zip` | `receipts_0.0.1-pre.2_windows_arm64.zip` |

Verify the downloaded archive using the pinned steps above. A matching SHA-256 establishes that its bytes match the entry in the manifest. The GitHub attestation identifies the workflow that produced it. Extract it into a directory you own, then run `./receipts --help` on Linux or macOS, or `.\receipts.exe --help` in PowerShell. To uninstall, delete that extracted directory. Apple notarization and Windows Authenticode are pending. Use the install methods your organization and OS permit.

With Go and its binary directory on PATH, you can install the pinned source module instead:

    go install github.com/valasme/receipts/cmd/receipts@v0.0.1-pre.2
    receipts --version

The Go install reports `receipts v0.0.1-pre.2`. Release archives report `receipts 0.0.1-pre.2`.

Linux deb and rpm packages are available on the same release. The optional `preview-installers.zip` contains `Formula/receipts.rb`, `bucket/receipts.json` and the multi-file `winget/` manifest. These work with a local Homebrew tap, a local Scoop manifest and WinGet's local-manifest feature. Their URLs point to the public release. Stable package-index registration remains outside this preview. The [consumer workflow](../.github/workflows/consumer.yml) gives the commands tested on each platform.

## License notices in candidates after v0.0.1-pre.1

Run `receipts --licenses` to read the Apache-2.0 license and the bundled third-party notices offline, including from a standalone executable or a Go installation. Archives contain both documents beside the binary. Debian installs them in `/usr/share/doc/receipts/` (the project license is named `copyright`). RPM uses `/usr/share/licenses/receipts/`. Homebrew uses the formula's `share/receipts/` directory. The first public preview predates this change.

The candidate workflow checks each package-installed executable against the native archive and replays a frozen receipt with networking disabled and Git off PATH. It checks package-owned notice files where the installer ships them. Homebrew, WinGet and Scoop receive the staged archive in their download caches so their manifest hash checks work before a public URL exists. The public-install workflow exercises downloads again after publication, including separate Go installs using the default proxy configuration and direct mode. Each route has its own binary directory and module cache. The transition exercise validates an older and newer prerelease in install, update, restore and removal order. The Windows-only dispatch filter applies to fresh installs. When upgrading Go or adding a dependency, review the notices for every release target against the new sources. The notice file cites the upstream texts.
