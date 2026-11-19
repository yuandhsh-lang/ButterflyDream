$ErrorActionPreference = 'Stop'
$root = 'E:\紫萱2版'
$source = 'C:\ProgramData\Epic\EpicGamesLauncher'
$target = 'E:\EpicData\ProgramData\EpicGamesLauncher'
$reportPath = Join-Path $root 'Evidence\setup\epic-data-link-result.json'
$report = [ordered]@{ startedAt = (Get-Date).ToString('o'); completed = $false }
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        $quotedScript = '"' + $PSCommandPath + '"'
        $process = Start-Process -FilePath "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $quotedScript) -Verb RunAs -Wait -PassThru
        exit $process.ExitCode
    } catch {
        $report.error = $_.Exception.Message
        $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
        exit 1
    }
}
try {
    $process = Get-Process -Name EpicGamesLauncher -ErrorAction SilentlyContinue
    if ($process) {
        $process.CloseMainWindow() | Out-Null
        Start-Sleep -Seconds 5
        if (Get-Process -Name EpicGamesLauncher -ErrorAction SilentlyContinue) { throw 'Epic Launcher is still running; not forcing it closed' }
    }
    $item = Get-Item -LiteralPath $source -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Source is already a reparse point; preserve it for review' }
    if (-not (Test-Path -LiteralPath $target)) { throw 'E-drive Epic data target is missing' }
    foreach ($name in @('ue.v5product', 'ue.v6product', 'ue.v7product', 'ue.v8product', 'ue.v9product')) {
        if (-not (Test-Path -LiteralPath (Join-Path $target "Data\EMS\EpicGamesLauncher\$name"))) { throw "Missing $name in E-drive Epic data" }
    }
    $backup = 'C:\ProgramData\Epic\EpicGamesLauncher.pre-recovery-' + (Get-Date).ToString('yyyyMMdd-HHmmss')
    Move-Item -LiteralPath $source -Destination $backup
    New-Item -ItemType Junction -Path $source -Target $target | Out-Null
    $linked = Get-Item -LiteralPath $source -Force
    $report.source = $source
    $report.target = $target
    $report.backup = $backup
    $report.linked = [bool]($linked.Attributes -band [IO.FileAttributes]::ReparsePoint)
    $report.note = 'No source files deleted. Remove this junction before any future MSI operation that checks reparse points.'
    $report.completed = $true
} catch {
    $report.error = $_.Exception.Message
} finally {
    $report.finishedAt = (Get-Date).ToString('o')
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
if (-not $report.completed) { exit 1 }
