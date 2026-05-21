# CTOA Desktop Console

Windows desktop client for CTOAi operations without using a browser.

## Features
- Login screen with username and password
- Account creation screen (self-register)
- Live dashboard after authentication
- Admin console available only for owner role

## Backend requirements
The backend API comes from mobile console service:
- endpoint base example: http://127.0.0.1:8787
- login: POST /api/auth/login
- self-register: POST /api/auth/register
- dashboard data: GET /api/status
- owner console commands: POST /api/command

Optional environment variables on backend:
- CTOA_SELF_REGISTER_ENABLED=true
- CTOA_SELF_REGISTER_CODE=<optional invite code>

## Run from source
1. Install dependencies:
   - pip install -r requirements.txt
2. Start GUI:
   - python desktop_console/app.py

## Build EXE
Use the helper script:
- powershell -ExecutionPolicy Bypass -File scripts/windows/build-ctoa-desktop-exe.ps1

Build output:
- dist/CTOA-Desktop.exe
