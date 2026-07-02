# CTOA Desktop Console

Windows desktop client for CTOAi operations without using a browser.

## Features
- Login screen with API connectivity check and clearer error hints
- Endpoint profile switch with local/stage/prod configuration screen
- Account creation screen (self-register)
- Production-style live dashboard with summary metrics, auto-refresh, and raw diagnostics
- Agent operations panel in dashboard
- Admin console available only for owner role
- Update checker against latest GitHub release with one-click update package download
- Control Center launcher shortcut for the modern web cockpit

## Control Center
The desktop app remains the Windows EXE entry point. The modern cockpit lives in the web app:

- Default URL: `http://127.0.0.1:3000/control-center`
- Desktop shortcut: `Ctrl+Shift+C`
- Settings key: `control_center_url`
- Windows helper: `scripts/windows/open-control-center.ps1`

This keeps the EXE useful as a launcher while the richer dashboard can evolve in `web`.

PowerShell helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/windows/open-control-center.ps1
```

## Credentials and roles
Desktop authentication uses backend accounts from `mobile_console/app.py`:
- Owner username: `CTOA_OWNER_USER` (default: `CTO`)
- Owner password: `CTOA_OWNER_PASSWORD` (default in code: `asdzxc12`)
- Optional operator username: `CTOA_OPERATOR_USER` (default: `ctoa-bot`)
- Optional operator password: `CTOA_OPERATOR_PASSWORD` (empty by default, account disabled until set)

Self-register (`/api/auth/register`) creates `operator` accounts in DB.

## API Base URL (local vs VPS)
- Local backend example: `http://127.0.0.1:8787`
- VPS backend example: `http://<vps-ip-or-domain>:8787` (or HTTPS behind reverse proxy)

If you use `127.0.0.1` from your Windows desktop, desktop app expects backend to run on that same machine.

## Endpoint profiles
Desktop stores profile URLs in local settings file and lets you switch active endpoint:
- local
- stage
- prod

Optional environment defaults:
- `CTOA_STAGE_API_BASE`
- `CTOA_PROD_API_BASE`

## Backend requirements
Desktop app uses mobile console API:
- login: `POST /api/auth/login`
- self-register: `POST /api/auth/register`
- status: `GET /api/status`
- dashboard: `GET /api/dashboard`
- agents status: `GET /api/agents/status`
- intel report: `GET /api/agents/intel/report`
- owner agent launch: `POST /api/agents/intel/launch`
- owner one-click execution: `POST /api/agents/execution/run`
- owner command execution: `POST /api/command`

Optional backend env variables:
- `CTOA_SELF_REGISTER_ENABLED=true`
- `CTOA_SELF_REGISTER_CODE=<optional invite code>`

## Run from source
1. Install dependencies:
   - `pip install -r requirements.txt`
2. Start GUI:
   - `python desktop_console/app.py`

## Build EXE
Use helper script:
- `powershell -ExecutionPolicy Bypass -File scripts/windows/build-ctoa-desktop-exe.ps1`

Build output:
- `dist/CTOA-Desktop.exe`
