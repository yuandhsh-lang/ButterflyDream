$ErrorActionPreference = 'Stop'
$root = 'E:\紫萱2版'
$reportPath = Join-Path $root 'Evidence\setup\epic-install-path-repair-result.json'
$report = [ordered]@{ startedAt = (Get-Date).ToString('o'); completed = $false }
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        $quotedScript = '"' + $PSCommandPath + '"'
        $process = Start-Process -FilePath "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $quotedScript) -Verb RunAs -Wait -PassThru
        exit $process.ExitCode
    } catch {
        $report.error = $_.Exception.Message
        $report.finishedAt = (Get-Date).ToString('o')
        $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
        exit 1
    }
}
try {
    $legacyKey = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{D80555F6-E78B-43D0-86F4-C4B3C1E0EDA5}'
    $legacy = Get-ItemProperty -LiteralPath $legacyKey
    $oldLocation = $legacy.InstallLocation
    if ($oldLocation -notin @('G:\KK\jkvfhfxfx\Epic Games\', 'E:\Epic Games\')) { throw "Unexpected legacy install location: $oldLocation" }
    if ([IO.Directory]::Exists('G:\')) { throw 'G drive is present; preserve it for review' }
    $backup = Join-Path $root 'Evidence\setup\legacy-epic-uninstall-before-path-repair.reg'
    & reg.exe export 'HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{D80555F6-E78B-43D0-86F4-C4B3C1E0EDA5}' $backup /y | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $backup)) { throw 'Failed to back up the legacy uninstall key' }
    Set-ItemProperty -LiteralPath $legacyKey -Name InstallLocation -Value 'E:\Epic Games\'
    $report.registryRepair = @{ key = $legacyKey; old = $oldLocation; new = 'E:\Epic Games\'; backup = $backup }
    $msi = Join-Path $root 'Downloads\Epic\EpicInstaller-20.3.3.msi'
    if ((Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash -ne 'D55D79710EDFEAA107A62F2EA007BEC1EEEAC8B715A43C2BA3858EEC7BC60337') { throw 'Installer SHA256 mismatch' }
    if ((Get-AuthenticodeSignature -LiteralPath $msi).Status -ne 'Valid') { throw 'Installer signature is not valid' }
    $arguments = '/i "' + $msi + '" /qn /norestart INSTALLDIR="E:\Epic Games" SELECTEDINSTALLFOLDER="E:\" USER_CHOSE_INSTALLDIR=1 EPICAPPDATA="E:\EpicData\ProgramData" ShouldLaunchOnFinish=0 /L*v "' + $root + '\Evidence\setup\EpicInstaller-path-repair.log"'
    $process = Start-Process -FilePath "$env:WINDIR\System32\msiexec.exe" -ArgumentList $arguments -Wait -PassThru
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
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
if (-not $report.completed) { exit 1 }
