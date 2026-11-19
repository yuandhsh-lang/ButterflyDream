param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Report
)
$ErrorActionPreference = 'Stop'
$required = @(
    'Engine\Binaries\Win64\UnrealEditor.exe',
    'Engine\Plugins\EnhancedInput\EnhancedInput.uplugin',
    'Engine\Plugins\FX\Niagara\Niagara.uplugin',
    'Engine\Plugins\Interchange\Runtime\Interchange.uplugin'
)
while ($true) {
    $missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $Root $_)) })
    $pending = Test-Path -LiteralPath (Join-Path $Root '.egstore\Pending')
    if ($missing.Count -eq 0 -and -not $pending) { break }
    Start-Sleep -Seconds 30
}
[pscustomobject]@{
    detectedAt = (Get-Date).ToString('o')
    root = $Root
    requiredFiles = $required
    pendingDirectoryRemoved = $true
    status = 'UNREAL_INSTALLATION_FILES_READY'
} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
