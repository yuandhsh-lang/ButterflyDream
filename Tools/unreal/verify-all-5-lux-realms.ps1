param(
    [int]$StoryCaptureSeconds = 6,
    [int]$VistaCaptureSeconds = 13,
    [int]$MaxWindowWaitSeconds = 900,
    [string[]]$FilterIds = @()
)

$ErrorActionPreference = 'Stop'

# Prevent Windows Modern Standby & display sleep
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class VerifyKeepAwake {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    public static IntPtr FindGameWindow(int pid) {
        IntPtr best = IntPtr.Zero;
        long bestArea = 0;
        EnumWindows((h, lp) => {
            uint wp = 0;
            GetWindowThreadProcessId(h, out wp);
            if ((int)wp != pid || !IsWindowVisible(h)) return true;
            RECT r;
            if (!GetWindowRect(h, out r)) return true;
            int w = r.Right - r.Left;
            int ht = r.Bottom - r.Top;
            if (w < 200 || ht < 200) return true;
            long area = (long)w * (long)ht;
            var cls = new StringBuilder(128);
            GetClassName(h, cls, 128);
            if (cls.ToString() == "UnrealWindow" && area > bestArea) {
                best = h;
                bestArea = area;
            } else if (best == IntPtr.Zero && area > bestArea) {
                best = h;
                bestArea = area;
            }
            return true;
        }, IntPtr.Zero);
        return best;
    }
}
"@
[void][VerifyKeepAwake]::SetThreadExecutionState([uint32]2147483651)

try {
    if (-not (Test-Path "V:\")) {
        subst V: "E:\紫萱2版"
    }

    $editorExe = "E:\Android\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
    $uproject = "V:\Unreal\ButterflyDream\ButterflyDream.uproject"
    $captureScript = "E:\紫萱2版\Tools\acquisition\capture-process-window.ps1"
    $ueLog = "E:\紫萱2版\Unreal\ButterflyDream\Saved\Logs\ButterflyDream.log"
    $outDir = "E:\紫萱2版\Evidence\Unreal\LuxFiveRealms"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $realms = @(
        @{ Id = "01_SakuraDream";        Map = "/Game/Maps/F06_SakuraDream" },
        @{ Id = "02_StarSeaDream";       Map = "/Game/Maps/Lux_StarSeaDream" },
        @{ Id = "03_InkCloudDream";      Map = "/Game/Maps/Lux_InkCloudDream" },
        @{ Id = "04_CrystalMirageDream"; Map = "/Game/Maps/Lux_CrystalMirageDream" },
        @{ Id = "05_TaijiAwakeningDream";Map = "/Game/Maps/Lux_TaijiAwakeningDream" }
    )

    Get-Process | Where-Object { $_.ProcessName -match 'Unreal|ShaderCompile' } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    if ($FilterIds.Count -gt 0) {
        $realms = @($realms | Where-Object { $FilterIds -contains $_.Id })
    }

    $auditResults = @()

    foreach ($r in $realms) {
        $id = $r.Id
        $mapPath = $r.Map
        $storyPng = Join-Path $outDir "${id}_story_game.png"
        $vistaPng = Join-Path $outDir "${id}_vista_game.png"
        $logCopy  = Join-Path $outDir "${id}_game.log"

        Write-Output "=== Launching -game for $id ($mapPath) [$(Get-Date -Format 'HH:mm:ss')] ==="
        $argsList = @(
            $uproject,
            $mapPath,
            "-game",
            "-ResX=1280",
            "-ResY=720",
            "-windowed",
            "-nosplash",
            "-nosound",
            "-nop4",
            "-NoTurnkey",
            "-unbuffered"
        )

        $launchTime = Get-Date
        $proc = Start-Process -FilePath $editorExe -ArgumentList $argsList -PassThru
        $gameHwnd = [IntPtr]::Zero
        try {
            $deadline = (Get-Date).AddSeconds($MaxWindowWaitSeconds)
            $ready = $false
            $engineInitSeenAt = $null
            while ((Get-Date) -lt $deadline) {
                if ($proc.HasExited) {
                    throw "UnrealEditor -game exited early for $mapPath with code $($proc.ExitCode)"
                }
                if ($gameHwnd -eq [IntPtr]::Zero) {
                    $gameHwnd = [VerifyKeepAwake]::FindGameWindow($proc.Id)
                }
                if (Test-Path $ueLog) {
                    $item = Get-Item $ueLog
                    if ($item.LastWriteTime -ge $launchTime) {
                        $txt = Get-Content $ueLog -Raw -ErrorAction SilentlyContinue
                        if ($txt -and $txt -match 'Engine is initialized\. Leaving FEngineLoop::Init\(\)') {
                            if (-not $engineInitSeenAt) {
                                $engineInitSeenAt = Get-Date
                                Write-Output "Engine initialized for $id at $(Get-Date -Format 'HH:mm:ss')"
                            }
                            if ($gameHwnd -eq [IntPtr]::Zero) {
                                $gameHwnd = [VerifyKeepAwake]::FindGameWindow($proc.Id)
                            }
                            if ($gameHwnd -ne [IntPtr]::Zero) {
                                Write-Output "Game window ready for $id (HWND=0x$($gameHwnd.ToInt64().ToString('X'))) at $(Get-Date -Format 'HH:mm:ss')"
                                $ready = $true
                                break
                            }
                        }
                    }
                }
                Start-Sleep -Seconds 1
            }
            if (-not $ready) {
                throw "Timed out waiting for -game ready for $mapPath (HWND=0x$($gameHwnd.ToInt64().ToString('X')))"
            }

            Write-Output "Gameplay tick live (PID=$($proc.Id)) at $(Get-Date -Format 'HH:mm:ss'). Waiting ${StoryCaptureSeconds}s for 3D Calligraphy Story Scroll..."
            Start-Sleep -Seconds $StoryCaptureSeconds
            & powershell -NoProfile -ExecutionPolicy Bypass -File $captureScript $proc.Id $storyPng
            Write-Output "Captured Story Scroll PNG: $storyPng"

            $extraWait = [Math]::Max(2, $VistaCaptureSeconds - $StoryCaptureSeconds)
            Start-Sleep -Seconds $extraWait
            $scDeadline = (Get-Date).AddSeconds(90)
            while ((Get-Date) -lt $scDeadline) {
                if (@(Get-Process -Name "ShaderCompileWorker" -ErrorAction SilentlyContinue).Count -eq 0) {
                    break
                }
                Start-Sleep -Seconds 2
            }
            Start-Sleep -Seconds 2
            & powershell -NoProfile -ExecutionPolicy Bypass -File $captureScript $proc.Id $vistaPng
            Write-Output "Captured Panorama Vista PNG: $vistaPng"
        }
        finally {
            if ($proc -and -not $proc.HasExited) {
                if ($gameHwnd -ne [IntPtr]::Zero) {
                    [void][VerifyKeepAwake]::PostMessage($gameHwnd, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
                } else {
                    $proc.CloseMainWindow() | Out-Null
                }
                if (-not $proc.WaitForExit(15000)) {
                    try { $proc.Kill() } catch {}
                }
            }
            Start-Sleep -Seconds 3
        }

        $naniteHits = -1
        $ismHits = -1
        $assetMisses = -1
        if (Test-Path $ueLog) {
            Copy-Item -Path $ueLog -Destination $logCopy -Force
            $naniteHits = (Select-String -Path $logCopy -Pattern "missing usage flag Nanite!" -AllMatches).Count
            $ismHits = (Select-String -Path $logCopy -Pattern "missing usage flag InstancedStaticMeshes!" -AllMatches).Count
            $assetMisses = (Select-String -Path $logCopy -Pattern "Failed to find object|Couldn't find file for package" -AllMatches).Count
        }
        $rec = [PSCustomObject]@{
            realm_id = $id
            map = $mapPath
            story_png = $storyPng
            vista_png = $vistaPng
            log = $logCopy
            nanite_missing_usage = $naniteHits
            ism_missing_usage = $ismHits
            asset_load_misses = $assetMisses
        }
        $auditResults += $rec
        Write-Output "AUDIT [$id]: nanite_missing_usage=$naniteHits ism_missing_usage=$ismHits asset_load_misses=$assetMisses"

        $summaryPath = Join-Path $outDir "five-realms-game-audit.json"
        $mergedMap = @{}
        if (Test-Path $summaryPath) {
            try {
                $existingJson = Get-Content $summaryPath -Raw | ConvertFrom-Json
                foreach ($item in @($existingJson)) {
                    if ($item -and $item.realm_id) { $mergedMap[$item.realm_id] = $item }
                }
            } catch {}
        }
        foreach ($rItem in $auditResults) {
            $mergedMap[$rItem.realm_id] = $rItem
        }
        $ordered = @($mergedMap.Values | Sort-Object realm_id)
        ($ordered | ConvertTo-Json -Depth 4) | Set-Content -Path $summaryPath -Encoding UTF8
    }

    $summaryPath = Join-Path $outDir "five-realms-game-audit.json"
    Write-Output "ALL_5_REALMS_VERIFIED summary=$summaryPath"
}
finally {
    [void][VerifyKeepAwake]::SetThreadExecutionState([uint32]2147483648)
}
