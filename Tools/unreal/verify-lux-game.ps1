param(
    [Parameter(Mandatory = $true)]
    [string]$MapPath,
    [Parameter(Mandatory = $true)]
    [string]$OutPng,
    [Parameter(Mandatory = $true)]
    [string]$OutLogCopy,
    [int]$WarmupAfterWindowSeconds = 8,
    [int]$MaxWindowWaitSeconds = 60
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path "V:\")) {
    subst V: "E:\紫萱2版"
}

$editorExe = "E:\Android\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "V:\Unreal\ButterflyDream\ButterflyDream.uproject"
$captureScript = "E:\紫萱2版\Tools\acquisition\capture-process-window.ps1"
$ueLog = "E:\紫萱2版\Unreal\ButterflyDream\Saved\Logs\ButterflyDream.log"

$outDir = Split-Path -Parent $OutPng
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$logDir = Split-Path -Parent $OutLogCopy
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$argsList = @(
    "`"$uproject`"",
    $MapPath,
    "-game",
    "-ResX=1280",
    "-ResY=720",
    "-windowed",
    "-nosplash",
    "-nosound"
)

Write-Output "Launching UE -game for $MapPath..."
$proc = Start-Process -FilePath $editorExe -ArgumentList ($argsList -join " ") -PassThru

try {
    $deadline = (Get-Date).AddSeconds($MaxWindowWaitSeconds)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) {
            throw "UnrealEditor -game exited early with code $($proc.ExitCode)"
        }
        $proc.Refresh()
        if ($proc.MainWindowHandle -ne 0 -and $proc.MainWindowTitle -ne "") {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) {
        throw "Timed out waiting for UnrealEditor -game window for $MapPath"
    }

    Write-Output "Window ready (PID=$($proc.Id), Title=$($proc.MainWindowTitle)). Waiting ${WarmupAfterWindowSeconds}s for render warmup..."
    Start-Sleep -Seconds $WarmupAfterWindowSeconds

    & powershell -NoProfile -ExecutionPolicy Bypass -File $captureScript $proc.Id $OutPng
    Write-Output "Captured screenshot: $OutPng"
}
finally {
    if ($proc -and -not $proc.HasExited) {
        $proc.CloseMainWindow() | Out-Null
        if (-not $proc.WaitForExit(5000)) {
            Stop-Process -Id $proc.Id -Force
        }
    }
    Start-Sleep -Seconds 1
}

if (Test-Path $ueLog) {
    Copy-Item -Path $ueLog -Destination $OutLogCopy -Force
    $naniteHits = (Select-String -Path $OutLogCopy -Pattern "missing usage flag Nanite!" -AllMatches).Count
    $ctorFails = (Select-String -Path $OutLogCopy -Pattern "Failed to find object|Couldn't find file for package" -AllMatches).Count
    Write-Output "LOG_AUDIT nanite_missing_usage=$naniteHits asset_load_misses=$ctorFails log=$OutLogCopy"
}
