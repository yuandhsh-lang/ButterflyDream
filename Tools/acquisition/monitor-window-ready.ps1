param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$Report
)
$ErrorActionPreference = 'Stop'
while ($true) {
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) { throw "Process $ProcessId exited before creating a window" }
    if ($process.MainWindowHandle -ne 0 -and $process.MainWindowTitle) { break }
    Start-Sleep -Seconds 10
}
[pscustomobject]@{
    detectedAt = (Get-Date).ToString('o')
    processId = $ProcessId
    windowTitle = $process.MainWindowTitle
    responding = $process.Responding
    status = 'UNREAL_EDITOR_WINDOW_READY'
} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
