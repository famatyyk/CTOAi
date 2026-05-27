param(
    [string]$PythonPath = ".\\.venv\\Scripts\\python.exe",
    [string]$AppName = "CTOA-Desktop",
    [switch]$OneDir,
    [switch]$KeepSpec
)

$entryPoint = "desktop_console/app.py"
if (-not (Test-Path $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}
if (-not (Test-Path $entryPoint)) {
    throw "Entry point not found: $entryPoint"
}

$packMode = "--onefile"
if ($OneDir) {
    $packMode = "--onedir"
}

& $PythonPath -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

& $PythonPath -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pyinstaller install failed" }

& $PythonPath -m PyInstaller --noconfirm --clean $packMode --windowed --name $AppName $entryPoint
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

$specFile = "$AppName.spec"
if ((-not $KeepSpec) -and (Test-Path $specFile)) {
    Remove-Item $specFile -Force
}

if ($OneDir) {
    Write-Output "Desktop executable built successfully."
    Write-Output "Output location: dist/$AppName/"
}
else {
    Write-Output "Desktop executable built successfully."
    Write-Output "Output location: dist/$AppName.exe"
}
