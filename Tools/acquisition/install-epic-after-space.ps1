$ErrorActionPreference = 'Stop'
$root = 'E:\紫萱2版'
$source = 'C:\ProgramData\Epic\EpicGamesLauncher'
$target = 'E:\EpicData\ProgramData\EpicGamesLauncher'
$backup = 'C:\ProgramData\Epic\EpicGamesLauncher.pre-recovery-20261111-190707'
$reportPath = Join-Path $root 'Evidence\setup\epic-install-after-space-result.json'
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
    if ((Get-PSDrive -Name C).Free -lt 1 * 1024 * 1024 * 1024) { throw 'Insufficient C drive working space' }
    $process = Get-Process -Name EpicGamesLauncher -ErrorAction SilentlyContinue
    if ($process) {
        $process.CloseMainWindow() | Out-Null
        Start-Sleep -Seconds 5
        if (Get-Process -Name EpicGamesLauncher -ErrorAction SilentlyContinue) { throw 'Epic Launcher is still running; not forcing it closed' }
    }
    $item = Get-Item -LiteralPath $source -Force
    if (-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Expected Epic data junction is missing' }
    if ($item.Target -ne $target) { throw 'Epic data junction points to an unexpected target' }
    if (-not (Test-Path -LiteralPath $target)) { throw 'E-drive Epic data target is missing' }
    if (-not (Test-Path -LiteralPath $backup)) { throw 'Preserved C-drive Epic directory is missing' }
    [IO.Directory]::Delete($source)
    Move-Item -LiteralPath $backup -Destination $source
    $report.junctionRemovedOnly = $true
    $report.preservedDirectoryRestored = $source
    $msi = Join-Path $root 'Downloads\Epic\EpicInstaller-20.3.3.msi'
    if ((Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash -ne 'D55D79710EDFEAA107A62F2EA007BEC1EEEAC8B715A43C2BA3858EEC7BC60337') { throw 'Installer SHA256 mismatch' }
    if ((Get-AuthenticodeSignature -LiteralPath $msi).Status -ne 'Valid') { throw 'Installer signature is not valid' }
    $arguments = '/i "' + $msi + '" /qn /norestart INSTALLDIR="E:\Epic Games" SELECTEDINSTALLFOLDER="E:\" USER_CHOSE_INSTALLDIR=1 EPICAPPDATA="E:\EpicData\ProgramData" ShouldLaunchOnFinish=0 /L*v "' + $root + '\Evidence\setup\EpicInstaller-after-space.log"'
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
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
if (-not $report.completed) { exit 1 }
