# Defer native code signing until the owner approves v1

Pre-v1 releases may ship as explicitly unsigned previews with native install checks, checksums and GitHub build attestations. The owner will provide signing access once they judge Receipts ready for v1. That decision starts Apple Developer ID signing and notarization, Windows Authenticode verification, and signing-provider recovery. [V1 signing ticket](https://github.com/valasme/receipts/issues/15)
