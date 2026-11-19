param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Report,
    [Parameter(Mandatory = $true)][string]$Status
)
$ErrorActionPreference = 'Stop'
while (-not (Test-Path -LiteralPath $Path)) {
    Start-Sleep -Seconds 30
}
$item = Get-Item -LiteralPath $Path
[pscustomobject]@{
    detectedAt = (Get-Date).ToString('o')
    path = $Path
    bytes = $item.Length
    status = $Status
} | ConvertTo-Json | Set-Content -LiteralPath $Report -Encoding UTF8
