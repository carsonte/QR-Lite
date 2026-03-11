param(
    [string]$Version = "v1.0.0",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..

$distDir = Join-Path $PSScriptRoot "..\\dist\\QRLite"
$exePath = Join-Path $distDir "QRLite.exe"
$releaseDir = Join-Path $PSScriptRoot "..\\output\\release"
$zipName = "QRLite-$Version-windows-x64.zip"
$zipPath = Join-Path $releaseDir $zipName

if (-not $SkipBuild -or -not (Test-Path $exePath)) {
    powershell -ExecutionPolicy Bypass -File ".\\build_exe.ps1"
}

if (-not (Test-Path $exePath)) {
    throw "Packaged app not found: $exePath"
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $zipPath -Force

$sizeMb = ((Get-Item $zipPath).Length / 1MB)
Write-Host ("Release zip created: {0}" -f $zipPath)
Write-Host ("Zip size: {0:N2} MB" -f $sizeMb)
