@echo off
setlocal
set "BASE=%~dp0"
pushd "%BASE%"
set EXE=ctoa-loader-v20260321.exe

if not exist "%EXE%" (
  echo [ERROR] %EXE% not found in current directory.
  pause
  exit /b 1
)

REM Best-effort unblocking for downloaded files (harmless if already unblocked).
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -Path '%BASE%%EXE%'" >nul 2>nul

if exist "ctoa-loader-paths.env.cmd" (
  call "ctoa-loader-paths.env.cmd"
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
