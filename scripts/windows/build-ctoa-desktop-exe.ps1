param(
    [string]$PythonPath = ".\\.venv\\Scripts\\python.exe",
    [string]$AppName = "CTOA-Desktop",
    [switch]$OneDir
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

& $PythonPath -m PyInstaller --noconfirm $packMode --windowed --name $AppName $entryPoint
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Output "Desktop executable built successfully."
Write-Output "Output location: dist/$AppName"
