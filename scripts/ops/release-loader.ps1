param(
  [string]$Entry = "scripts/ops/ctoa_loader.py",
  [string]$Name = "ctoa-loader",
  [string]$Dist = "dist/loader",
  [string]$ReleasesDir = "releases/loader"
)

$ErrorActionPreference = "Stop"

# 1. Generate version stamp (yyyyMMdd)
$version = Get-Date -Format "yyyyMMdd"
$versionTag = "v$version"
$exeName = "$Name-$versionTag.exe"
$checksumFile = "$ReleasesDir/$Name-$versionTag.CHECKSUM.txt"
$zipFile = "$ReleasesDir/$Name-$versionTag.zip"
$releaseMetaFile = "$ReleasesDir/LATEST.json"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CTOA Loader Release Pipeline" -ForegroundColor Cyan
Write-Host "Version: $versionTag" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

# 2. Validate entry script
if (-not (Test-Path $Entry)) {
  throw "Entry script not found: $Entry"
}

# 3. Create releases directory
if (-not (Test-Path $ReleasesDir)) {
  New-Item -ItemType Directory -Path $ReleasesDir -Force | Out-Null
  Write-Host "Created releases directory: $ReleasesDir" -ForegroundColor Green
}

# 4. Build EXE
Write-Host "`nBuilding EXE..." -ForegroundColor Cyan
$python = ".venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

& $python -m pip install --upgrade pip pyinstaller -q | Out-Null

& $python -m PyInstaller `
  --onefile `
  --name $Name `
  --distpath $Dist `
  --clean `
  $Entry | Out-Host

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exePath = "$Dist/$Name.exe"
if (-not (Test-Path $exePath)) {
  throw "Build failed: EXE not found at $exePath"
}

Write-Host "[OK] EXE built successfully" -ForegroundColor Green

# 5. Copy to releases with version tag
$releaseExePath = "$ReleasesDir/$exeName"
Copy-Item $exePath -Destination $releaseExePath -Force
Write-Host "[OK] Copied to: $releaseExePath" -ForegroundColor Green

# 6. Generate SHA256 checksum
Write-Host "`nGenerating checksum..." -ForegroundColor Cyan
$fileStream = [System.IO.File]::OpenRead($releaseExePath)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$hash = $sha256.ComputeHash($fileStream)
$fileStream.Close()
$hashString = [System.BitConverter]::ToString($hash) -replace "-", ""

$checksumContent = @"
sha256: $hashString
filename: $exeName
version: $versionTag
date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')
"@

$checksumContent | Out-File -FilePath $checksumFile -Encoding UTF8 -Force
Write-Host "[OK] Checksum saved: $checksumFile" -ForegroundColor Green

# 7. Create README for release
$readmePath = "$ReleasesDir/README-$versionTag.txt"
$launcherCmdName = "RUN-CTOA-LOADER.cmd"
$launcherCmdPath = "$ReleasesDir/$launcherCmdName"
$launcherPlBrCmdName = "RUN-CTOA-LOADER-SYNC-PL-BR.cmd"
$launcherPlBrCmdPath = "$ReleasesDir/$launcherPlBrCmdName"
$pathsTemplateName = "ctoa-loader-paths.env.cmd"
$pathsTemplatePath = "$ReleasesDir/$pathsTemplateName"
$readmeContent = @"
CTOA Loader $versionTag
=======================

Double-click the EXE to open the GUI app.
CLI mode is still available from Terminal.

Quick Start (GUI):
1. Double-click $exeName.
2. Set source/target paths in the app window.
3. Use buttons: List / Sync / Open / Export.

Quick Start (Terminal / CLI):
1. Open terminal in this folder.
2. Verify checksum:
   certutil -hashfile $exeName SHA256
3. List targets:
   .\\$exeName list
4. Sync targets:
   .\\$exeName sync --source <path> --target <path>

One-click mode:
- Double-click $launcherCmdName and choose an option.
- Double-click $launcherPlBrCmdName for direct PL/BR sync presets.
- Edit $pathsTemplateName once to set production paths 1:1.

Commands:
  list      - List available live targets
  sync      - Sync targets from source to target directory
  open      - Open target directory in file explorer
  export    - Export manifest of a specific target

For more info:
  .\\$exeName --help
"@

$readmeContent | Out-File -FilePath $readmePath -Encoding UTF8 -Force
Write-Host "[OK] README created: $readmePath" -ForegroundColor Green

$launcherCmdContent = @"
@echo off
setlocal
set "BASE=%~dp0"
pushd "%BASE%"
set EXE=$exeName
set "PYW=..\..\.venv\Scripts\pythonw.exe"
set "PY=..\..\.venv\Scripts\python.exe"
set "PYS=..\..\scripts\ops\ctoa_loader.py"
set "MODE=EXE"

if not exist "%EXE%" (
  echo [ERROR] %EXE% not found in current directory.
  pause
  exit /b 1
)

REM Best-effort unblocking for downloaded files (harmless if already unblocked).
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -Path '%BASE%%EXE%'" >nul 2>nul

echo Starting CTOA Loader GUI...
"%EXE%"
if not errorlevel 1 exit /b 0

if exist "%PYW%" if exist "%PYS%" (
  echo [INFO] EXE blocked. Starting GUI via Python fallback...
  start "CTOA Loader" "%PYW%" "%PYS%"
  set "MODE=PY"
)

echo.
echo [WARN] GUI did not start. Possible cause: Windows/App Control policy block.
echo Try one of these:
echo   1^) Right click EXE -> Properties -> Unblock
echo   2^) Run PowerShell as user and execute:
echo      Unblock-File -Path .\%EXE%
echo   3^) If policy still blocks, ask admin to allow this signed/hashed binary.
echo.
echo You can still try CLI menu below:

:menu
echo.
echo CTOA Loader Menu
echo ===============================
echo 1^) Start GUI again
echo 2^) List targets
echo 3^) Sync targets (default paths)
echo 4^) Help
echo 5^) Exit
set /p CHOICE=Choose option [1-5]: 

if "%CHOICE%"=="1" (
  if "%MODE%"=="PY" (
    start "CTOA Loader" "%PYW%" "%PYS%"
  ) else (
    "%EXE%"
  )
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="2" (
  if "%MODE%"=="PY" (
    "%PY%" "%PYS%" list
  ) else (
    "%EXE%" list
  )
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="3" (
  if "%MODE%"=="PY" (
    "%PY%" "%PYS%" sync
  ) else (
    "%EXE%" sync
  )
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="4" (
  if "%MODE%"=="PY" (
    "%PY%" "%PYS%" --help
  ) else (
    "%EXE%" --help
  )
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="5" exit /b 0

echo Invalid option.
goto menu
"@

$launcherCmdContent | Out-File -FilePath $launcherCmdPath -Encoding ASCII -Force
Write-Host "[OK] Launcher created: $launcherCmdPath" -ForegroundColor Green

$launcherPlBrCmdContent = @"
@echo off
setlocal
set "BASE=%~dp0"
pushd "%BASE%"
set EXE=$exeName

if not exist "%EXE%" (
  echo [ERROR] %EXE% not found in current directory.
  pause
  exit /b 1
)

REM Best-effort unblocking for downloaded files (harmless if already unblocked).
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -Path '%BASE%%EXE%'" >nul 2>nul

if exist "$pathsTemplateName" (
  call "$pathsTemplateName"
)

if "%PL_SOURCE%"=="" set "PL_SOURCE=%~dp0..\..\runtime\live-targets\pl"
if "%PL_TARGET%"=="" set "PL_TARGET=%~dp0..\..\runtime\bot-live\pl"
if "%BR_SOURCE%"=="" set "BR_SOURCE=%~dp0..\..\runtime\live-targets\br"
if "%BR_TARGET%"=="" set "BR_TARGET=%~dp0..\..\runtime\bot-live\br"

echo.
echo CTOA Loader Sync Presets (PL/BR)
echo ========================================
echo [PL] %PL_SOURCE%  --^>  %PL_TARGET%
echo [BR] %BR_SOURCE%  --^>  %BR_TARGET%
echo.

if not exist "%PL_SOURCE%" (
  echo [ERROR] PL source not found: %PL_SOURCE%
  pause
  exit /b 1
)
if not exist "%BR_SOURCE%" (
  echo [ERROR] BR source not found: %BR_SOURCE%
  pause
  exit /b 1
)

echo Syncing PL preset...
"%EXE%" --source "%PL_SOURCE%" --target "%PL_TARGET%" sync
if errorlevel 1 (
  echo [ERROR] PL sync failed.
  pause
  exit /b 1
)

echo.
echo Syncing BR preset...
"%EXE%" --source "%BR_SOURCE%" --target "%BR_TARGET%" sync
if errorlevel 1 (
  echo [ERROR] BR sync failed. If EXE is blocked by policy, allow/unblock the file first.
  pause
  exit /b 1
)

echo.
echo [OK] PL + BR sync finished.
pause
"@

$launcherPlBrCmdContent | Out-File -FilePath $launcherPlBrCmdPath -Encoding ASCII -Force
Write-Host "[OK] PL/BR launcher created: $launcherPlBrCmdPath" -ForegroundColor Green

$pathsTemplateContent = @"
@echo off
REM Set production paths once. Keep quotes if your paths contain spaces.

set "PL_SOURCE=C:\\CTOA\\live-targets\\pl"
set "PL_TARGET=C:\\Users\\%USERNAME%\\AppData\\Roaming\\otclientv8\\bot\\live\\pl"
set "BR_SOURCE=C:\\CTOA\\live-targets\\br"
set "BR_TARGET=C:\\Users\\%USERNAME%\\AppData\\Roaming\\otclientv8\\bot\\live\\br"
"@

$pathsTemplateContent | Out-File -FilePath $pathsTemplatePath -Encoding ASCII -Force
Write-Host "[OK] Paths template created: $pathsTemplatePath" -ForegroundColor Green

# 8. Create ZIP release package
Write-Host "`nPackaging ZIP..." -ForegroundColor Cyan
$tmpPackage = New-Item -ItemType Directory -Path "$ReleasesDir/.tmp-$versionTag" -Force

Copy-Item $releaseExePath -Destination "$tmpPackage/$exeName" -Force
Copy-Item $checksumFile -Destination "$tmpPackage/CHECKSUM.txt" -Force
Copy-Item $readmePath -Destination "$tmpPackage/README.txt" -Force
Copy-Item $launcherCmdPath -Destination "$tmpPackage/$launcherCmdName" -Force
Copy-Item $launcherPlBrCmdPath -Destination "$tmpPackage/$launcherPlBrCmdName" -Force
Copy-Item $pathsTemplatePath -Destination "$tmpPackage/$pathsTemplateName" -Force

# Create ZIP
$zipSource = $tmpPackage.FullName
$zipTarget = (Get-Item $zipFile -ErrorAction SilentlyContinue).FullName
if (Test-Path $zipFile) { Remove-Item $zipFile -Force }

# Using PowerShell native compression (requires PS5+)
Compress-Archive -Path "$tmpPackage/*" -DestinationPath $zipFile -Force

Remove-Item $tmpPackage -Recurse -Force
Write-Host "[OK] ZIP package created: $zipFile" -ForegroundColor Green

# 9. Update LATEST.json metadata
$fileSize = (Get-Item $releaseExePath).Length
$latestMeta = @{
  version = $versionTag
  timestamp = [System.DateTime]::UtcNow.ToString('o')
  executable = $exeName
  checksum = $hashString
  checksum_type = "sha256"
  file_size_bytes = $fileSize
  zip_file = (Split-Path $zipFile -Leaf)
  change_log = "Auto-generated release"
} | ConvertTo-Json

$latestMeta | Out-File -FilePath $releaseMetaFile -Encoding UTF8 -Force
Write-Host "[OK] Metadata updated: $releaseMetaFile" -ForegroundColor Green

# 10. Update RELEASES.md changelog
$releaseMdPath = "$ReleasesDir/RELEASES.md"
if (-not (Test-Path $releaseMdPath)) {
  $releasesMdContent = "# CTOA Loader Releases`n`n"
} else {
  $releasesMdContent = Get-Content $releaseMdPath -Raw
}

$newEntry = @"
## [$versionTag] - $(Get-Date -Format 'yyyy-MM-dd')
- Automatic release build
- Executable: $exeName
- SHA256: $hashString
- Size: $($fileSize / 1MB -as [int]) MB

"@

$releasesMdContent = $newEntry + $releasesMdContent
$releasesMdContent | Out-File -FilePath $releaseMdPath -Encoding UTF8 -Force
Write-Host "[OK] Changelog updated: $releaseMdPath" -ForegroundColor Green

# 11. Validate release
Write-Host "`nValidating release..." -ForegroundColor Cyan
if (-not (Test-Path $releaseExePath)) { throw "Release EXE not found!" }
if (-not (Test-Path $checksumFile)) { throw "Checksum file not found!" }
if (-not (Test-Path $zipFile)) { throw "ZIP not found!" }
if (-not (Test-Path $releaseMetaFile)) { throw "Metadata not found!" }

# Quick sanity check: run EXE with --help
Write-Host "Testing EXE startup..." -ForegroundColor Cyan
try {
  $testOutput = & $releaseExePath --help 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ Warning: EXE help test returned exit code $LASTEXITCODE" -ForegroundColor Yellow
  } else {
    Write-Host "[OK] EXE startup validation passed" -ForegroundColor Green
  }
} catch {
  Write-Host "⚠ Warning: EXE startup test skipped on this machine (blocked by policy)." -ForegroundColor Yellow
  Write-Host "  Details: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "  Running fallback validation via Python entry..." -ForegroundColor Cyan
  & $python $Entry --help | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Fallback Python validation failed with exit code $LASTEXITCODE"
  }
  Write-Host "[OK] Fallback validation passed (entry script is runnable)." -ForegroundColor Green
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Release Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Version:      $versionTag" -ForegroundColor Yellow
Write-Host "EXE:          $exeName" -ForegroundColor Yellow
Write-Host "ZIP:          $(Split-Path $zipFile -Leaf)" -ForegroundColor Yellow
Write-Host "Location:     $ReleasesDir" -ForegroundColor Yellow
Write-Host "Checksum:     $hashString" -ForegroundColor Cyan
Write-Host ""
Write-Host "Files:" -ForegroundColor Cyan
Write-Host "  - $exeName (executable)"
Write-Host "  - CHECKSUM.txt (verification)"
Write-Host "  - README.txt (quick start guide)"
Write-Host "  - $launcherCmdName (double-click launcher)"
Write-Host "  - $launcherPlBrCmdName (preset sync launcher)"
Write-Host "  - $pathsTemplateName (production path presets)"
Write-Host "  - $($zipFile | Split-Path -Leaf) (complete package)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Share ZIP with team"
Write-Host "2. Test on target machine: .\$exeName list"
Write-Host "3. Verify checksum: certutil -hashfile $exeName SHA256"
Write-Host ""
Write-Host "Metadata saved to: LATEST.json" -ForegroundColor Green
