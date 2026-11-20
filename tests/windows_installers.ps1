param([Parameter(Mandatory)][ValidateSet('winget','scoop')][string]$Channel)
$ErrorActionPreference = 'Stop'
if ($Channel -eq 'scoop') {
    $env:SCOOP = Join-Path $env:RUNNER_TEMP 'receipts-scoop'
    & ./scoop-bootstrap/install.ps1 -ScoopDir $env:SCOOP -RunAsAdmin
    if (!(Test-Path "$env:SCOOP/shims/scoop.ps1")) { throw 'Scoop installation failed' }
    "SCOOP=$env:SCOOP" >> $env:GITHUB_ENV
    exit
}
$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    $path = $winget.Source
} else {
    gh release download v1.29.380 --repo microsoft/winget-cli --dir winget-bootstrap -p DesktopAppInstaller_Dependencies.zip -p Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    Expand-Archive winget-bootstrap/DesktopAppInstaller_Dependencies.zip -DestinationPath winget-bootstrap/deps
    $arch = if ($env:RUNNER_ARCH -eq 'ARM64') { 'arm64' } else { 'x64' }
    $deps = @(Get-ChildItem -Recurse winget-bootstrap/deps -Include *.appx,*.msix | Where-Object { $_.FullName -match "[\\/]$arch[\\/]" } | ForEach-Object { $_.FullName })
    Add-AppxPackage -Path winget-bootstrap/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle -DependencyPath $deps -ForceApplicationShutdown
    $path = Join-Path (Get-AppxPackage Microsoft.DesktopAppInstaller).InstallLocation 'winget.exe'
}
& $path settings --enable LocalManifestFiles
if ($LASTEXITCODE) { exit $LASTEXITCODE }
"RECEIPTS_WINGET=$path" >> $env:GITHUB_ENV
