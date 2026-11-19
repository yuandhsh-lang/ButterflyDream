$ErrorActionPreference = 'Stop'
$root = 'E:\紫萱2版'
$msi = Join-Path $root 'Downloads\Epic\EpicInstaller-20.3.3.msi'
$target = 'E:\EpicPortable'
$reportPath = Join-Path $root 'Evidence\setup\epic-admin-extract-result.json'
$report = [ordered]@{ startedAt = (Get-Date).ToString('o'); target = $target; completed = $false; method = 'msiexec /a extraction to E; no registry edits or legacy uninstall' }
try {
    if (Test-Path -LiteralPath $target) { throw 'Extraction target already exists; preserve it for review' }
    if ((Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash -ne 'D55D79710EDFEAA107A62F2EA007BEC1EEEAC8B715A43C2BA3858EEC7BC60337') { throw 'Installer SHA256 mismatch' }
    if ((Get-AuthenticodeSignature -LiteralPath $msi).Status -ne 'Valid') { throw 'Installer signature is not valid' }
    $arguments = '/a "' + $msi + '" /qn /norestart TARGETDIR="' + $target + '" /L*v "' + $root + '\Evidence\setup\EpicInstaller-admin-extract.log"'
    $process = Start-Process -FilePath "$env:WINDIR\System32\msiexec.exe" -ArgumentList $arguments -Wait -PassThru
    $report.exitCode = $process.ExitCode
    if ($process.ExitCode -notin @(0, 3010)) { throw "Epic administrative extraction returned $($process.ExitCode)" }
    $report.completed = $true
} catch {
    $report.error = $_.Exception.Message
} finally {
    $report.finishedAt = (Get-Date).ToString('o')
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
if (-not $report.completed) { exit 1 }
