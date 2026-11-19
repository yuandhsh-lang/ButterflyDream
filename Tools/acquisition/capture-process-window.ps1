$ErrorActionPreference = 'Stop'
$processId = [int]$args[0]
$output = $args[1]
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class ButterflyWindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect { public int Left; public int Top; public int Right; public int Bottom; }
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr handle, out Rect rect);
    [DllImport("user32.dll")]
    public static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")]
    public static extern uint GetDpiForWindow(IntPtr handle);

    public static IntPtr FindBestWindowForPid(int targetPid) {
        IntPtr bestUnreal = IntPtr.Zero;
        long bestUnrealArea = 0;
        IntPtr bestAny = IntPtr.Zero;
        long bestAnyArea = 0;
        EnumWindows((h, lp) => {
            uint wp = 0;
            GetWindowThreadProcessId(h, out wp);
            if ((int)wp != targetPid || !IsWindowVisible(h)) return true;
            Rect r;
            if (!GetWindowRect(h, out r)) return true;
            int w = r.Right - r.Left;
            int ht = r.Bottom - r.Top;
            if (w < 200 || ht < 200) return true;
            long area = (long)w * (long)ht;
            var cls = new StringBuilder(128);
            GetClassName(h, cls, 128);
            string clsName = cls.ToString();
            if (clsName == "UnrealWindow" && area > bestUnrealArea) {
                bestUnreal = h;
                bestUnrealArea = area;
            }
            if (area > bestAnyArea) {
                bestAny = h;
                bestAnyArea = area;
            }
            return true;
        }, IntPtr.Zero);
        return bestUnreal != IntPtr.Zero ? bestUnreal : bestAny;
    }
}
'@
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ButterflyWindowFallback {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr handle, int command);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
[ButterflyWindowCapture]::SetProcessDpiAwarenessContext([IntPtr]::new(-4)) | Out-Null
$process = Get-Process -Id $processId
$targetHwnd = [ButterflyWindowCapture]::FindBestWindowForPid($processId)
if ($targetHwnd -eq [IntPtr]::Zero) { $targetHwnd = $process.MainWindowHandle }
if ($targetHwnd -eq [IntPtr]::Zero) { throw 'Process has no main window' }
$rect = New-Object ButterflyWindowCapture+Rect
if (-not [ButterflyWindowCapture]::GetWindowRect($targetHwnd, [ref]$rect)) { throw 'GetWindowRect failed' }
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { throw 'Window has invalid dimensions' }
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    [ButterflyWindowFallback]::ShowWindow($targetHwnd, 9) | Out-Null
    [ButterflyWindowFallback]::SetForegroundWindow($targetHwnd) | Out-Null
    Start-Sleep -Milliseconds 600
    if ([ButterflyWindowFallback]::GetForegroundWindow() -ne $targetHwnd) {
        throw 'Target window is not foreground for desktop capture'
    }
    $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
    $bitmap.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
Write-Output "WINDOW_CAPTURE_SAVED $output"
