param(
    [int]$CaptureWarmupSeconds = 20,
    [int]$MaxWindowWaitSeconds = 1800,
    [string[]]$FilterIds = @()
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$editorExe = 'E:\Android\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$uproject = Join-Path $root 'Unreal\ButterflyDream\ButterflyDream.uproject'
$captureScript = Join-Path $root 'Tools\acquisition\capture-process-window.ps1'
$ueLog = Join-Path $root 'Unreal\ButterflyDream\Saved\Logs\ButterflyDream.log'
$outDir = Join-Path $root ('Evidence\Unreal\FourRealms_20261119\Runtime_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class FourRealmCapture {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
    public static IntPtr FindGameWindow(int pid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h, lp) => {
            uint windowPid = 0;
            GetWindowThreadProcessId(h, out windowPid);
            if ((int)windowPid != pid || !IsWindowVisible(h)) return true;
            var cls = new StringBuilder(128);
            GetClassName(h, cls, 128);
            if (cls.ToString() != "UnrealWindow") return true;
            RECT rect;
            if (!GetWindowRect(h, out rect)) return true;
            if (rect.Right - rect.Left >= 800 && rect.Bottom - rect.Top >= 500) {
                found = h;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
"@
[void][FourRealmCapture]::SetThreadExecutionState([uint32]2147483651)

$realms = @(
    @{ Id = '01_StarSeaDream'; Map = '/Game/Maps/Lux_StarSeaDream'; Spawn = 'Lux_StarSeaDream' },
    @{ Id = '02_InkCloudDream'; Map = '/Game/Maps/Lux_InkCloudDream'; Spawn = 'Lux_InkCloudDream' },
    @{ Id = '03_CrystalMirageDream'; Map = '/Game/Maps/Lux_CrystalMirageDream'; Spawn = 'Lux_CrystalMirageDream' },
    @{ Id = '04_TaijiAwakeningDream'; Map = '/Game/Maps/Lux_TaijiAwakeningDream'; Spawn = 'Lux_TaijiAwakeningDream' }
)
if ($FilterIds.Count -gt 0) {
    $realms = @($realms | Where-Object { $FilterIds -contains $_.Id })
}
if ($realms.Count -eq 0) {
    throw 'No valid realm IDs were requested.'
}
if (-not (Test-Path $uproject)) {
    throw "Project not found: $uproject"
}
if (-not (Test-Path $editorExe)) {
    throw "UE5.8 is required but was not found: $editorExe"
}

$results = @()
try {
    foreach ($realm in $realms) {
        $existing = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*ButterflyDream.uproject*'
        })
        if ($existing.Count -gt 0) {
            throw 'A ButterflyDream UE process is already running. Close it before capture; this script never kills unrelated UE processes.'
        }

        $id = $realm.Id
        $map = $realm.Map
        $spawn = $realm.Spawn
        $storyPng = Join-Path $outDir "${id}_story.png"
        $vistaPng = Join-Path $outDir "${id}_vista.png"
        $logCopy = Join-Path $outDir "${id}.log"
        Write-Output "=== Launching $id ($map) ==="
        $argsList = @(
            $uproject,
            $map,
            '-game',
            '-ResX=1280',
            '-ResY=720',
            '-windowed',
            '-nosplash',
            '-nosound',
            '-nop4'
        )
        $launchTime = Get-Date
        $proc = Start-Process -FilePath $editorExe -ArgumentList $argsList -PassThru
        $gameHwnd = [IntPtr]::Zero
        $engineInitSeconds = $null
        $mapLoadSeconds = $null
        $record = $null
        try {
            $deadline = $launchTime.AddSeconds($MaxWindowWaitSeconds)
            $ready = $false
            while ((Get-Date) -lt $deadline) {
                if ($proc.HasExited) {
                    throw "UE exited early for $map with code $($proc.ExitCode)"
                }
                if ($gameHwnd -eq [IntPtr]::Zero) {
                    $gameHwnd = [FourRealmCapture]::FindGameWindow($proc.Id)
                }
                if ($gameHwnd -ne [IntPtr]::Zero -and (Test-Path $ueLog)) {
                    $logItem = Get-Item $ueLog
                    if ($logItem.LastWriteTime -gt $launchTime) {
                        $text = Get-Content $ueLog -Raw -ErrorAction SilentlyContinue
                        if ($text -and $text.Contains("LUX_SPAWN Map=$spawn") -and $text.Contains('Engine is initialized. Leaving FEngineLoop::Init()')) {
                            $ready = $true
                            break
                        }
                    }
                }
                Start-Sleep -Seconds 2
            }
            if (-not $ready) {
                throw "Timed out waiting for actual gameplay readiness: $map"
            }

            Start-Sleep -Seconds $CaptureWarmupSeconds
            $shaderDeadline = (Get-Date).AddSeconds(120)
            while ((Get-Date) -lt $shaderDeadline -and @(Get-Process -Name 'ShaderCompileWorker' -ErrorAction SilentlyContinue).Count -gt 0) {
                Start-Sleep -Seconds 2
            }
            & powershell -NoProfile -ExecutionPolicy Bypass -File $captureScript $proc.Id $storyPng
            Start-Sleep -Seconds 5
            & powershell -NoProfile -ExecutionPolicy Bypass -File $captureScript $proc.Id $vistaPng

            $proc.Refresh()
            $processRamBytes = $proc.WorkingSet64
            $vramParts = @()
            try { $vramParts = @((& nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits) -split ',') } catch { $vramParts = @() }
            $text = Get-Content $ueLog -Raw
            $engineMatch = [regex]::Match($text, 'Engine Initialization\) Total time: ([0-9.]+) seconds')
            if ($engineMatch.Success) { $engineInitSeconds = [double]$engineMatch.Groups[1].Value }
            $loadMatches = [regex]::Matches($text, 'LogLoad: Took ([0-9.]+) seconds to LoadMap')
            if ($loadMatches.Count -gt 0) { $mapLoadSeconds = [double]$loadMatches[$loadMatches.Count - 1].Groups[1].Value }
        }
        finally {
            if ($proc -and -not $proc.HasExited) {
                if ($gameHwnd -ne [IntPtr]::Zero) {
                    [void][FourRealmCapture]::PostMessage($gameHwnd, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
                } else {
                    $proc.CloseMainWindow() | Out-Null
                }
                if (-not $proc.WaitForExit(20000)) {
                    $proc.Kill()
                }
            }
            Start-Sleep -Seconds 2
        }

        if (Test-Path $ueLog) {
            Copy-Item $ueLog $logCopy -Force
        }
        $logText = if (Test-Path $logCopy) { Get-Content $logCopy -Raw } else { '' }
        $record = [PSCustomObject]@{
            status = 'CAPTURED_NOT_VERIFIED'
            realm_id = $id
            map = $map
            captured_at = (Get-Date).ToString('o')
            story_png = $storyPng
            vista_png = $vistaPng
            log = $logCopy
            engine_init_seconds = $engineInitSeconds
            map_load_seconds = $mapLoadSeconds
            process_ram_working_set_bytes = $processRamBytes
            system_vram_used_mib = if ($vramParts.Count -ge 2) { [double]$vramParts[0] } else { $null }
            system_vram_total_mib = if ($vramParts.Count -ge 2) { [double]$vramParts[1] } else { $null }
            memory_scope = 'Snapshot after warmup; VRAM is whole GPU, not per-process. No frame-time claim.'
            nanite_missing_usage = [regex]::Matches($logText, 'missing usage flag Nanite!').Count
            ism_missing_usage = [regex]::Matches($logText, 'missing usage flag InstancedStaticMeshes!').Count
            asset_load_misses = [regex]::Matches($logText, 'Failed to find object|Couldn''t find file for package').Count
            fatal_errors = [regex]::Matches($logText, 'Fatal error|Assertion failed').Count
            sky_capture_errors = [regex]::Matches($logText, 'SkyLight.*(red|capture)|capture.*SkyLight|SkyLight.*not marked|No sky light').Count
            missing_niagara = [regex]::Matches($logText, '/Game/FX/[^ ''\r\n]+.*(Failed|not found)|Failed.*Niagara').Count
            visual_review = 'NOT_TESTED'
            input_review = 'NOT_TESTED'
            performance_review = 'NOT_TESTED'
        }
        $results += $record
        $results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $outDir 'capture-audit.json') -Encoding UTF8
        Write-Output "CAPTURED_NOT_VERIFIED $id"
    }
}
finally {
    [void][FourRealmCapture]::SetThreadExecutionState([uint32]2147483648)
}
Write-Output "Capture complete; visual, input, and performance reviews remain separate: $outDir"
