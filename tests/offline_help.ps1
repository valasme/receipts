param([Parameter(Mandatory)][string]$Binary)
$ErrorActionPreference = 'Stop'
$name = "Receipts offline help $([guid]::NewGuid())"
try {
    New-NetFirewallRule -DisplayName $name -Direction Outbound -Action Block -Program $Binary -Profile Any | Out-Null
    $active = Get-NetFirewallRule -PolicyStore ActiveStore -DisplayName $name
    if ($active.Enabled -ne 'True' -or $active.Action -ne 'Block') {
        throw 'The outbound block is absent from active policy'
    }
    if (Get-NetFirewallProfile -PolicyStore ActiveStore | Where-Object Enabled -ne 'True') {
        throw 'A Windows Firewall profile is disabled'
    }
    & $Binary --help
    exit $LASTEXITCODE
} finally {
    Remove-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
}
