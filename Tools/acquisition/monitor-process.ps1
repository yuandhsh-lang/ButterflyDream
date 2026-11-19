param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$Report,
    [Parameter(Mandatory = $true)][string]$Status
)
$ErrorActionPreference = 'Stop'
$process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
if (-not $process) { throw "Process $ProcessId not found" }
while (-not $process.HasExited) {
    Start-Sleep -Seconds 10
    $process.Refresh()
}
[pscustomobject]@{
    finishedAt = (Get-Date).ToString('o')
    processId = $ProcessId
    status = $Status
} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
