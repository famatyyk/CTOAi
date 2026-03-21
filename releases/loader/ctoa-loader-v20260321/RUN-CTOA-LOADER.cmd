@echo off
setlocal
set EXE=ctoa-loader-v20260321.exe

if not exist "%EXE%" (
  echo [ERROR] %EXE% not found in current directory.
  pause
  exit /b 1
)

:menu
echo.
echo CTOA Loader Menu
echo ===============================
echo 1^) List targets
echo 2^) Sync targets (default paths)
echo 3^) Help
echo 4^) Exit
set /p CHOICE=Choose option [1-4]: 

if "%CHOICE%"=="1" (
  "%EXE%" list
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="2" (
  "%EXE%" sync
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="3" (
  "%EXE%" --help
  echo.
  pause
  goto menu
)
if "%CHOICE%"=="4" exit /b 0

echo Invalid option.
goto menu
