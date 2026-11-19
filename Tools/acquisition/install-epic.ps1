$ErrorActionPreference = 'Stop'
$taskSetupRoot = 'E:\紫萱2版\Evidence\setup'
$taskMsiPath = 'E:\紫萱2版\Downloads\Epic\EpicInstaller-20.3.3.msi'
$taskExpectedHash = 'D55D79710EDFEAA107A62F2EA007BEC1EEEAC8B715A43C2BA3858EEC7BC60337'
New-Item -ItemType Directory -Force -Path $taskSetupRoot, 'E:\EpicData\Temp' | Out-Null
$env:TEMP = 'E:\EpicData\Temp'
$env:TMP = 'E:\EpicData\Temp'
$taskReport = [ordered]@{ startedAt = (Get-Date).ToString('o'); installDir = 'E:\Epic Games'; dataDir = 'E:\EpicData'; completed = $false; relocations = @() }
$taskCreatedLegacyMapping = $false

try {
    if ((Get-FileHash -LiteralPath $taskMsiPath -Algorithm SHA256).Hash -ne $taskExpectedHash) { throw 'Installer SHA256 mismatch' }
    $taskSig = Get-AuthenticodeSignature -LiteralPath $taskMsiPath
    if ($taskSig.Status -ne 'Valid') { throw 'Installer signature is not valid' }
    $taskReport.signer = $taskSig.SignerCertificate.Subject
    if (Get-Process -Name EpicGamesLauncher, EpicWebHelper -ErrorAction SilentlyContinue) { throw 'Epic Launcher is running; cache relocation must wait until it is closed' }

    $taskMappings = @(
        @('C:\Users\LENOVO\AppData\Local\EpicGamesLauncher', 'E:\EpicData\LocalAppData\EpicGamesLauncher'),
        @('C:\ProgramData\Epic\UnrealEngineLauncher', 'E:\EpicData\ProgramData\UnrealEngineLauncher')
    )
    foreach ($taskMapping in $taskMappings) {
        $taskSource = [IO.Path]::GetFullPath($taskMapping[0])
        $taskDestination = [IO.Path]::GetFullPath($taskMapping[1])
        # These exact paths are the only directories this installer may move.
        if ($taskSource -ne $taskMapping[0] -or -not $taskDestination.StartsWith('E:\EpicData\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected relocation path' }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $taskDestination) | Out-Null
        if (Test-Path -LiteralPath $taskSource) {
            $taskSourceItem = Get-Item -LiteralPath $taskSource -Force
            if ($taskSourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                if ($taskSourceItem.Target -ne $taskDestination) { throw 'Existing data link points to another location' }
            } else {
                if (Test-Path -LiteralPath $taskDestination) { throw 'Destination already exists; preserve both directories for review' }
                $taskResolvedSource = (Resolve-Path -LiteralPath $taskSource).ProviderPath
                if ($taskResolvedSource -ne $taskSource) { throw 'Resolved source differs from approved relocation path' }
                Move-Item -LiteralPath $taskResolvedSource -Destination $taskDestination
                New-Item -ItemType Junction -Path $taskSource -Target $taskDestination | Out-Null
            }
        } else {
            New-Item -ItemType Directory -Force -Path $taskDestination, (Split-Path -Parent $taskSource) | Out-Null
            New-Item -ItemType Junction -Path $taskSource -Target $taskDestination | Out-Null
        }
        $taskReport.relocations += @{ source = $taskSource; target = $taskDestination; linked = $true }
    }

    # Epic's MSI explicitly checks this legacy folder for reparse points.
    # Retain its data on E: and remove only our junction, never its target.
    # The new MSI writes its AppDataPath directly to E: through EPICAPPDATA.
    $taskProgramDataPath = 'C:\ProgramData\Epic\EpicGamesLauncher'
    if (Test-Path -LiteralPath $taskProgramDataPath) {
        $taskProgramDataItem = Get-Item -LiteralPath $taskProgramDataPath -Force
        if ($taskProgramDataItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            if ($taskProgramDataItem.Target -ne 'E:\EpicData\ProgramData\EpicGamesLauncher') { throw 'Unexpected ProgramData link target' }
            if ($taskProgramDataItem.FullName -ne $taskProgramDataPath) { throw 'Unexpected ProgramData link path' }
            [IO.Directory]::Delete($taskProgramDataPath)
        }
    }
    New-Item -ItemType Directory -Force -Path $taskProgramDataPath, 'E:\EpicData\ProgramData\EpicGamesLauncher' | Out-Null
    $taskReport.relocations += @{ source = $taskProgramDataPath; target = 'E:\EpicData\ProgramData\EpicGamesLauncher'; method = 'native EPICAPPDATA installer directory property' }

    $taskPreviousCache = [Environment]::GetEnvironmentVariable('UE-LocalDataCachePath', 'User')
    $taskReport.previousUnrealCache = $taskPreviousCache
    New-Item -ItemType Directory -Force -Path 'E:\EpicData\DerivedDataCache' | Out-Null
    [Environment]::SetEnvironmentVariable('UE-LocalDataCachePath', 'E:\EpicData\DerivedDataCache', 'User')

    # Repair only the obsolete launcher's registered location before invoking
    # its normal MSI uninstaller. Its G: files no longer exist. Keep a backup
    # and use an isolated E: directory rather than a substituted drive.
    $taskLegacyKey = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{D80555F6-E78B-43D0-86F4-C4B3C1E0EDA5}'
    if (Test-Path -LiteralPath $taskLegacyKey) {
        $taskLegacy = Get-ItemProperty -LiteralPath $taskLegacyKey
        if ($taskLegacy.InstallLocation -ne 'G:\KK\jkvfhfxfx\Epic Games\') { throw 'Legacy launcher path changed; preserve current installation' }
        if ([IO.Directory]::Exists('G:\')) { throw 'G drive is present; preserve the existing installation for review' }
        & reg.exe export 'HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{D80555F6-E78B-43D0-86F4-C4B3C1E0EDA5}' 'E:\紫萱2版\Evidence\setup\legacy-epic-uninstall.reg' /y | Out-Null
        $taskLegacyPropertiesKey = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\S-1-5-18\Products\6F55508DB87E0D34684F4C3B1C0EDE5A\InstallProperties'
        & reg.exe export 'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\UserData\S-1-5-18\Products\6F55508DB87E0D34684F4C3B1C0EDE5A\InstallProperties' 'E:\紫萱2版\Evidence\setup\legacy-epic-install-properties.reg' /y | Out-Null
        $taskLegacyRecovery = 'E:\EpicData\LegacyLauncherRecovery\Epic Games\'
        New-Item -ItemType Directory -Force -Path $taskLegacyRecovery | Out-Null
        Set-ItemProperty -LiteralPath $taskLegacyKey -Name InstallLocation -Value $taskLegacyRecovery
        Set-ItemProperty -LiteralPath $taskLegacyPropertiesKey -Name InstallLocation -Value $taskLegacyRecovery
        $taskReport.legacyLocationRepair = @{ old = 'G:\KK\jkvfhfxfx\Epic Games\'; temporary = $taskLegacyRecovery; backup = 'Evidence/setup/legacy-epic-uninstall.reg' }
        $taskLegacyArgs = '/x {D80555F6-E78B-43D0-86F4-C4B3C1E0EDA5} /qn /norestart /L*v "E:\紫萱2版\Evidence\setup\EpicLegacyRemove-native.log"'
        $taskRemoval = Start-Process -FilePath "$env:WINDIR\System32\msiexec.exe" -ArgumentList $taskLegacyArgs -WindowStyle Hidden -PassThru -Wait
        $taskReport.legacyRemovalExitCode = $taskRemoval.ExitCode
        if ($taskRemoval.ExitCode -notin @(0, 1605, 3010)) { throw "Legacy launcher uninstall returned $($taskRemoval.ExitCode)" }
    }

    $taskArguments = '/i "E:\紫萱2版\Downloads\Epic\EpicInstaller-20.3.3.msi" /qn /norestart INSTALLDIR="E:\Epic Games" SELECTEDINSTALLFOLDER="E:\" USER_CHOSE_INSTALLDIR=1 EPICAPPDATA="E:\EpicData\ProgramData" APPDATA="E:\EpicData\ProgramData\EpicGamesLauncher\Data" ShouldLaunchOnFinish=0 /L*v "E:\紫萱2版\Evidence\setup\EpicInstaller-native.log"'
    $taskInstall = Start-Process -FilePath "$env:WINDIR\System32\msiexec.exe" -ArgumentList $taskArguments -WindowStyle Hidden -PassThru -Wait
    $taskReport.exitCode = $taskInstall.ExitCode
    if ($taskInstall.ExitCode -notin @(0, 3010)) { throw "Epic installer returned $($taskInstall.ExitCode)" }
    $taskLauncher = 'E:\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe'
    if (-not (Test-Path -LiteralPath $taskLauncher)) { $taskLauncher = 'E:\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe' }
    if (-not (Test-Path -LiteralPath $taskLauncher)) { throw 'Launcher executable was not found at the requested E drive destination' }
    $taskReport.launcher = $taskLauncher
    $taskReport.completed = $true
} catch {
    $taskReport.error = $_.Exception.Message
} finally {
    if ($taskCreatedLegacyMapping) { & "$env:WINDIR\System32\subst.exe" G: /d }
    $taskReport.finishedAt = (Get-Date).ToString('o')
    $taskReport | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskSetupRoot 'epic-install-result.json') -Encoding UTF8
}

if (-not $taskReport.completed) { exit 1 }
