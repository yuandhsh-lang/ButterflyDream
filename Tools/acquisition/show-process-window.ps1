param([Parameter(Mandatory = $true)][int]$ProcessId)
$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ButterflyWindowShow {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr handle, int command);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
}
'@
$process = Get-Process -Id $ProcessId
if ($process.MainWindowHandle -eq 0) { throw 'Process has no main window' }
$shown = [ButterflyWindowShow]::ShowWindow($process.MainWindowHandle, 9)
$foreground = [ButterflyWindowShow]::SetForegroundWindow($process.MainWindowHandle)
[pscustomobject]@{ processId = $ProcessId; showWindowResult = $shown; setForegroundResult = $foreground; title = $process.MainWindowTitle } | ConvertTo-Json
