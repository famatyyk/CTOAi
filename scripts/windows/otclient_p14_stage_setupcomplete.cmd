@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem Copy this file into the answer ISO as:
rem   $OEM$\$$\Setup\Scripts\SetupComplete.cmd
rem Copy otclient_p14_post_oobe_bootstrap.ps1 beside it with this exact target
rem name. It installs one LOCAL SYSTEM AtLogOn task; it does not directly run
rem Guest Additions or create the stage bootstrap task during SetupComplete.
set "P14_BOOTSTRAP=C:\Windows\Setup\Scripts\ctoa_p14_post_oobe_bootstrap.ps1"

if not exist "%P14_BOOTSTRAP%" exit /b 23

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%P14_BOOTSTRAP%" -Install
exit /b %ERRORLEVEL%
