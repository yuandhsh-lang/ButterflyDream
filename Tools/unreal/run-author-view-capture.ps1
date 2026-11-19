param(
    [Parameter(Mandatory=$true)][ValidateSet("F09","F06")][string]$SceneId,
    [int]$TimeoutSeconds = 900,
    [switch]$AutoCompleteAfterVerify = $true
)
$ErrorActionPreference = 'Stop'

# Prevent Modern Standby & display sleep for the lifetime of this runner process (ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class PowerKeepAwake {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
[void][PowerKeepAwake]::SetThreadExecutionState([uint32]2147483651)

try {
    $mapArg = if ($SceneId -eq "F09") { "/Game/Maps/F09_Unawakened" } else { "/Game/Maps/F06_SakuraDream" }
    $evidenceDir = "E:\紫萱2版\Evidence\Unreal\$SceneId"
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

    $readyFile = Join-Path $evidenceDir "author-view-ready.json"
    $errorFile = Join-Path $evidenceDir "author-view-error.txt"
    $completeFile = Join-Path $evidenceDir "capture-complete.json"
    $winPng = Join-Path $evidenceDir "author-ue-window.png"
    $vpPng = Join-Path $evidenceDir "author-ue.png"
    foreach ($f in @($readyFile, $errorFile, $completeFile, $winPng, $vpPng)) {
        if (Test-Path $f) { Remove-Item $f -Force }
    }

    $env:BUTTERFLY_SCENE_ID = $SceneId
    $env:BUTTERFLY_AUTO_AUTHOR_VIEW = "1"

    $ueExe = "E:\Android\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
    $uproject = "E:\紫萱2版\Unreal\ButterflyDream\ButterflyDream.uproject"
    $proc = Start-Process -FilePath $ueExe -ArgumentList @($uproject, $mapArg, "-NoSplash", "-nop4", "-unattended", "-nosound") -PassThru
    Write-Output ("LAUNCHED UE PID={0} Scene={1} Map={2}" -f $proc.Id, $SceneId, $mapArg)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $captured = $false

    while (-not $proc.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-Path $errorFile) {
            Write-Output "AUTHOR_VIEW_ERROR_DETECTED"
            Get-Content $errorFile | Write-Output
            break
        }
        if (-not $captured -and (Test-Path $readyFile)) {
            $scwWaitDeadline = (Get-Date).AddSeconds(90)
            while ((Get-Date) -lt $scwWaitDeadline) {
                $scw = @(Get-Process -Name ShaderCompileWorker -ErrorAction SilentlyContinue)
                if ($scw.Count -eq 0) { break }
                Start-Sleep -Seconds 2
            }
            Start-Sleep -Seconds 2

            for ($i = 0; $i -lt 5; $i++) {
                $proc.Refresh()
                if ($proc.MainWindowHandle -ne 0) { break }
                Start-Sleep -Seconds 1
            }
            Write-Output ("READY_DETECTED PID={0} MainWindowHandle={1} Title='{2}'" -f $proc.Id, $proc.MainWindowHandle, $proc.MainWindowTitle)
            if ($proc.MainWindowHandle -ne 0) {
                try {
                    & "E:\紫萱2版\Tools\acquisition\capture-process-window.ps1" $proc.Id $winPng
                    if ((Test-Path $winPng) -and ((Get-Item $winPng).Length -le 1024)) {
                        Remove-Item $winPng -Force
                    }
                } catch {
                    Write-Output ("CAPTURE_WINDOW_FAILED: " + $_.Exception.Message)
                }
            }
            $captured = $true
            if ($AutoCompleteAfterVerify -and (Test-Path $vpPng) -and ((Get-Item $vpPng).Length -gt 50000)) {
                Add-Type -AssemblyName System.Drawing
                $bmp = [System.Drawing.Bitmap]::FromFile($vpPng)
                $w = $bmp.Width; $h = $bmp.Height
                $nonBlack = 0
                foreach ($pt in @(@(0.25,0.25), @(0.5,0.3), @(0.5,0.5), @(0.5,0.7), @(0.75,0.5))) {
                    $c = $bmp.GetPixel([int]($w * $pt[0]), [int]($h * $pt[1]))
                    if (($c.R + $c.G + $c.B) -gt 15) { $nonBlack++ }
                }
                $bmp.Dispose()
                if ($nonBlack -ge 3) {
                    $compObj = @{
                        scene_id = $SceneId
                        verified_png = $vpPng
                        width = $w
                        height = $h
                        non_black_samples = $nonBlack
                        timestamp = (Get-Date).ToString("o")
                    } | ConvertTo-Json
                    Set-Content -Path $completeFile -Value $compObj -Encoding UTF8
                    Write-Output ("VERIFIED_PNG_AND_WROTE_COMPLETE ({0}x{1}, nonBlack={2}/5)" -f $w, $h, $nonBlack)
                } else {
                    Write-Output "PNG_FAILED_NONBLACK_CHECK waiting for manual inspection"
                }
            } else {
                Write-Output "WAITING_FOR_CAPTURE_COMPLETE_JSON"
            }
        }
        if ($captured -and (Test-Path $completeFile)) {
            Write-Output "CAPTURE_COMPLETE_DETECTED waiting clean exit..."
            break
        }
    }

    if (-not $captured) {
        Write-Output "ERROR: Capture did not complete within $TimeoutSeconds seconds; force closing UE."
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            $proc.WaitForExit()
        }
        throw "Author view capture timed out after ${TimeoutSeconds}s"
    }

    $exitDeadline = (Get-Date).AddSeconds(180)
    while (-not $proc.HasExited -and (Get-Date) -lt $exitDeadline) {
        Start-Sleep -Seconds 2
    }
    if (-not $proc.HasExited) {
        Write-Output "WARNING: UE did not exit cleanly after 180s; force closing."
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    $proc.WaitForExit()
    Write-Output ("UE_EXITED Code={0}" -f $proc.ExitCode)
} finally {
    [void][PowerKeepAwake]::SetThreadExecutionState([uint32]2147483648)
}
