$ErrorActionPreference = 'Stop'
$processId = [int]$args[0]
$buttonText = $args[1]
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ButterflyDialogButton {
    public delegate bool EnumWindowsProc(IntPtr handle, IntPtr parameter);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr parent, EnumWindowsProc callback, IntPtr parameter);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr handle, StringBuilder text, int length);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr handle, StringBuilder text, int length);
    [DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr handle, uint message, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
}
'@
$process = Get-Process -Id $processId
$parent = $process.MainWindowHandle
if ($parent -eq 0) { throw 'Process has no main window' }
$matches = @()
$callback = [ButterflyDialogButton+EnumWindowsProc]{
    param($handle, $parameter)
    $text = New-Object System.Text.StringBuilder 256
    $class = New-Object System.Text.StringBuilder 256
    [void][ButterflyDialogButton]::GetWindowText($handle, $text, $text.Capacity)
    [void][ButterflyDialogButton]::GetClassName($handle, $class, $class.Capacity)
    if ($text.ToString() -eq $buttonText -and $class.ToString() -eq 'Button') {
        $script:matches += $handle
    }
    return $true
}
[void][ButterflyDialogButton]::EnumChildWindows($parent, $callback, [IntPtr]::Zero)
if ($matches.Count -ne 1) { throw "Expected exactly one matching button, found $($matches.Count)" }
$result = [IntPtr]::Zero
$ok = [ButterflyDialogButton]::SendMessageTimeout($matches[0], 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero, 2, 5000, [ref]$result)
if (-not $ok) { throw 'Button message timed out or failed' }
[pscustomobject]@{processId=$processId;button=$buttonText;clicked=$true;parentTitle=$process.MainWindowTitle} | ConvertTo-Json
