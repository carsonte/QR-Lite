param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Resolve-PythonExe {
    param(
        [string]$RequestedPath
    )

    if ($RequestedPath) {
        return $RequestedPath
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $candidate = & $pyCommand.Source -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            return $candidate.Trim()
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    return ""
}

function Remove-PackagingBloat {
    param(
        [string]$DistDir
    )

    $cv2Dir = Join-Path $DistDir "_internal\\cv2"
    if (Test-Path $cv2Dir) {
        Get-ChildItem $cv2Dir -Recurse -File -Include *.pyi, py.typed -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            } catch {
            }
        }

        Get-ChildItem $cv2Dir -File -Filter "opencv_videoio_ffmpeg*.dll" -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            } catch {
            }
        }
    }

    @(
        (Join-Path $DistDir "_internal\\cv2\\data"),
        (Join-Path $DistDir "_internal\\watchfiles"),
        (Join-Path $DistDir "_internal\\websockets")
    ) | ForEach-Object {
        if (Test-Path $_) {
            try {
                Remove-Item $_ -Recurse -Force -ErrorAction SilentlyContinue
            } catch {
            }
        }
    }
}

$PythonExe = Resolve-PythonExe $PythonExe

if (-not (Test-Path $PythonExe)) {
    throw "Python not found: $PythonExe"
}

$AppName = "QRLite"
$existingDir = Join-Path $PSScriptRoot ("dist\\{0}" -f $AppName)
$existingExe = Join-Path $existingDir ("{0}.exe" -f $AppName)
$specPath = Join-Path $PSScriptRoot "QRLite.spec"

Write-Host "Ensuring PyInstaller is installed ..."
& $PythonExe -m pip install pyinstaller
& $PythonExe "build_brand_assets.py"

Get-Process -Name $AppName -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        if ($_.Path -eq $existingExe) {
            Stop-Process -Id $_.Id -Force
        }
    } catch {
    }
}

Start-Sleep -Milliseconds 500
if (Test-Path $existingDir) {
    Remove-Item $existingDir -Recurse -Force -ErrorAction SilentlyContinue
}

$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    $specPath
)

Write-Host ("Building {0} (onedir) ..." -f $AppName)
& $PythonExe @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Host "Removing unused packaged files ..."
Remove-PackagingBloat -DistDir $existingDir

$finalSizeMb = ((Get-ChildItem $existingDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB)
Write-Host ("Final size: {0:N2} MB" -f $finalSizeMb)
Write-Host ("Build complete: dist\\{0}\\{0}.exe" -f $AppName)
