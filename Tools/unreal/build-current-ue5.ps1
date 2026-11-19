param(
    [string]$EngineRoot = 'E:\Android\UE_5.8',
    [string]$BuildRoot = 'E:\ButterflyDream_Build',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BuildArgs = @()
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectDir = (Resolve-Path (Join-Path $root 'Unreal\ButterflyDream')).Path
$project = Join-Path $projectDir 'ButterflyDream.uproject'
$buildBat = Join-Path $EngineRoot 'Engine\Build\BatchFiles\Build.bat'
if (-not (Test-Path $project -PathType Leaf)) { throw "Project not found: $project" }
if (-not (Test-Path $buildBat -PathType Leaf)) { throw "UE5.8 build tools not found: $buildBat" }
if ($BuildRoot -match '[^\x20-\x7E]') { throw "BuildRoot must contain only ASCII characters: $BuildRoot" }
if (-not (Test-Path $BuildRoot)) { New-Item -ItemType Directory -Path $BuildRoot | Out-Null }

$linkPath = Join-Path $BuildRoot 'CurrentProject'
if (Test-Path $linkPath) {
    $link = Get-Item $linkPath -Force
    if ($link.LinkType -ne 'Junction') { throw "Refusing to replace a real directory or file: $linkPath" }
    $target = [IO.Path]::GetFullPath([string]@($link.Target)[0]).TrimEnd('\')
    if ($target -ine $projectDir.TrimEnd('\')) { throw "Junction points elsewhere: $target" }
} else {
    New-Item -ItemType Junction -Path $linkPath -Target $projectDir | Out-Null
}

$aliasProject = Join-Path $linkPath 'ButterflyDream.uproject'
Write-Host "Building the current project with UE5: $project"
Write-Host "ASCII compiler path: $aliasProject"
& $buildBat ButterflyDreamEditor Win64 Development "-Project=$aliasProject" -WaitMutex -NoHotReloadFromIDE @BuildArgs
exit $LASTEXITCODE
