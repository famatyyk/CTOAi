param(
  [string]$Entry = "scripts/ops/ctoa_loader.py",
  [string]$Name = "ctoa-loader",
  [string]$Dist = "dist/loader"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Entry)) {
  throw "Entry script not found: $Entry"
}

$python = ".venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -m pip install --upgrade pip pyinstaller | Out-Host

& $python -m PyInstaller `
  --onefile `
  --name $Name `
  --distpath $Dist `
  --clean `
  $Entry | Out-Host

Write-Host "Loader EXE build complete: $Dist/$Name.exe"
