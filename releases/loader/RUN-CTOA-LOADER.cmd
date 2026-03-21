@echo off
setlocal
set "BASE=%~dp0"
pushd "%BASE%"
set EXE=ctoa-loader-v20260321.exe
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
