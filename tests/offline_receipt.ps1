param(
    [Parameter(Mandatory)][string]$Binary,
    [Parameter(Mandatory)][string]$Repo,
    [Parameter(Mandatory)][string]$Revision,
    [Parameter(Mandatory)][string]$Quote,
    [Parameter(Mandatory)][string]$EmptyPath,
    [Parameter(Mandatory)][string]$ReceiptOutput
)
$ErrorActionPreference = 'Stop'
$name = "Receipts offline qualification $([guid]::NewGuid())"
$code = 1
try {
    New-NetFirewallRule -DisplayName $name -Direction Outbound -Action Block -Program $Binary -Profile Any | Out-Null
    $active = Get-NetFirewallRule -PolicyStore ActiveStore -DisplayName $name
    if ($active.Enabled -ne 'True' -or $active.Action -ne 'Block') {
        throw 'The outbound block is absent from active policy'
    }
    if (Get-NetFirewallProfile -PolicyStore ActiveStore | Where-Object Enabled -ne 'True') {
        throw 'A Windows Firewall profile is disabled'
    }
    $start = [Diagnostics.ProcessStartInfo]::new($Binary)
    $start.Environment['PATH'] = $EmptyPath
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    foreach ($arg in @('check', '--repo', $Repo, '--rev', $Revision, '--path', 'sample.txt', '--quote-file', $Quote, '--format', 'json')) {
        $start.ArgumentList.Add($arg)
    }
    $child = [Diagnostics.Process]::Start($start)
    $receipt = [IO.File]::Create($ReceiptOutput)
    try {
        $copy = $child.StandardOutput.BaseStream.CopyToAsync($receipt)
        if (!$child.WaitForExit(15000)) {
            $child.Kill($true)
            throw 'The offline receipt check timed out'
        }
        $copy.GetAwaiter().GetResult()
        $code = $child.ExitCode
    } finally {
        $receipt.Dispose()
        $child.Dispose()
    }
} finally {
    Remove-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
}
exit $code
