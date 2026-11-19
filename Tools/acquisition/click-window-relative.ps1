$ErrorActionPreference = 'Stop'
$processId = [int]$args[0]
$xRatio = [double]$args[1]
$yRatio = [double]$args[2]
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ButterflyWindowClick {
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect { public int Left; public int Top; public int Right; public int Bottom; }
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr handle, out Rect rect);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
}
'@
[ButterflyWindowClick]::SetProcessDpiAwarenessContext([IntPtr]::new(-4)) | Out-Null
$process = Get-Process -Id $processId
$handle = $process.MainWindowHandle
if ($handle -eq 0) { throw 'Process has no main window' }
[ButterflyWindowClick]::SetForegroundWindow($handle) | Out-Null
Start-Sleep -Milliseconds 500
if ([ButterflyWindowClick]::GetForegroundWindow() -ne $handle) { throw 'Target window is not foreground; no click sent' }
$rect = New-Object ButterflyWindowClick+Rect
if (-not [ButterflyWindowClick]::GetWindowRect($handle, [ref]$rect)) { throw 'GetWindowRect failed' }
$x = $rect.Left + [int](($rect.Right - $rect.Left) * $xRatio)
$y = $rect.Top + [int](($rect.Bottom - $rect.Top) * $yRatio)
[ButterflyWindowClick]::SetCursorPos($x, $y) | Out-Null
[ButterflyWindowClick]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
[ButterflyWindowClick]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
[pscustomobject]@{processId=$processId;x=$x;y=$y;clicked=$true;title=$process.MainWindowTitle} | ConvertTo-Json
