@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem This fixed helper is copied by the answer ISO to:
rem C:\Windows\Setup\Scripts\ctoa_p14_guest_additions_setup.cmd
rem It is invoked by specialize RunSynchronous as LOCAL SYSTEM.  It trusts
rem only the certificates on the mounted Guest Additions medium, then starts
rem its documented silent installer.  The caller controls any reboot.

if not "%~1"=="" exit /b 32

set "P14_EXPECTED_SCRIPT=%SystemRoot%\Setup\Scripts\ctoa_p14_guest_additions_setup.cmd"
for %%I in ("%~f0") do set "P14_SCRIPT_PATH=%%~fI"
if /I not "%P14_SCRIPT_PATH%"=="%P14_EXPECTED_SCRIPT%" exit /b 31

set "P14_CALLER_SID="
for /f "usebackq tokens=2 delims=," %%I in (`whoami /user /fo csv /nh`) do set "P14_CALLER_SID=%%~I"
if not "%P14_CALLER_SID%"=="S-1-5-18" exit /b 30

set "P14_GA_DRIVE="
for %%D in (D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if not defined P14_GA_DRIVE if exist "%%D:\VBoxWindowsAdditions.exe" set "P14_GA_DRIVE=%%D:"
)
if not defined P14_GA_DRIVE exit /b 40

set "P14_GA_INSTALLER=%P14_GA_DRIVE%\VBoxWindowsAdditions.exe"
set "P14_GA_CERT_TOOL=%P14_GA_DRIVE%\cert\VBoxCertUtil.exe"
set "P14_GA_CERT_DIR=%P14_GA_DRIVE%\cert"
if not exist "%P14_GA_CERT_TOOL%" exit /b 41

set "P14_CERT_FOUND="
for %%C in ("%P14_GA_CERT_DIR%\vbox*.cer") do (
    if exist "%%~fC" (
        set "P14_CERT_FOUND=1"
        "%P14_GA_CERT_TOOL%" add-trusted-publisher "%%~fC" --root "%%~fC"
        if errorlevel 1 exit /b 43
    )
)
if not defined P14_CERT_FOUND exit /b 42

"%P14_GA_INSTALLER%" /S
set "P14_INSTALL_EXIT=%ERRORLEVEL%"
if "%P14_INSTALL_EXIT%"=="0" exit /b 0
if "%P14_INSTALL_EXIT%"=="3010" exit /b 3010
if "%P14_INSTALL_EXIT%"=="1641" exit /b 1641
exit /b %P14_INSTALL_EXIT%
