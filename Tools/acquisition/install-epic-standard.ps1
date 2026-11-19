$ErrorActionPreference = 'Stop'
$root = 'E:\紫萱2版'
$msi = Join-Path $root 'Downloads\Epic\EpicInstaller-20.3.3.msi'
$reportPath = Join-Path $root 'Evidence\setup\epic-install-standard-result.json'
$report = [ordered]@{ startedAt = (Get-Date).ToString('o'); completed = $false; method = 'standard MSI install only; no registry edits or legacy uninstall' }
try {
    if ((Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash -ne 'D55D79710EDFEAA107A62F2EA007BEC1EEEAC8B715A43C2BA3858EEC7BC60337') { throw 'Installer SHA256 mismatch' }
    $signature = Get-AuthenticodeSignature -LiteralPath $msi
    if ($signature.Status -ne 'Valid') { throw 'Installer signature is not valid' }
    if (Get-Process -Name EpicGamesLauncher, EpicWebHelper -ErrorAction SilentlyContinue) { throw 'Close Epic Launcher before installation' }
    $arguments = '/i "' + $msi + '" /qn /norestart INSTALLDIR="E:\Epic Games" EPICAPPDATA="E:\EpicData\ProgramData" ShouldLaunchOnFinish=0 /L*v "' + $root + '\Evidence\setup\EpicInstaller-standard.log"'
    $process = Start-Process -FilePath "$env:WINDIR\System32\msiexec.exe" -ArgumentList $arguments -Verb RunAs -PassThru -Wait
    $report.exitCode = $process.ExitCode
    if ($process.ExitCode -notin @(0, 3010)) { throw "Epic installer returned $($process.ExitCode)" }
    $launcher = 'E:\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe'
    if (-not (Test-Path -LiteralPath $launcher)) { $launcher = 'E:\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe' }
    if (-not (Test-Path -LiteralPath $launcher)) { throw 'Launcher executable was not found at the requested E drive destination' }
    $report.launcher = $launcher
    $report.completed = $true
} catch {
    $report.error = $_.Exception.Message
} finally {
    $report.finishedAt = (Get-Date).ToString('o')
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
if (-not $report.completed) { exit 1 }
