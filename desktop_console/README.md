# CTOA Desktop Console

Windows desktop client for CTOAi operations without using a browser.

## Features
- Login screen with API connectivity check and clearer error hints
- Endpoint profile switch with local/stage/prod configuration screen
- Account creation screen (self-register)
- Production-style live dashboard with summary metrics, auto-refresh, and raw diagnostics
- Agent operations panel in dashboard
- Admin console available only for owner role
- Update checker against latest GitHub release with guarded update package download
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
- Owner password: `CTOA_OWNER_PASSWORD` (required in production; no hardcoded default)
- Optional operator username: `CTOA_OPERATOR_USER` (default: `ctoa-bot`)
- Optional operator password: `CTOA_OPERATOR_PASSWORD` (empty by default, account disabled until set)

Self-register (`/api/auth/register`) creates `member` accounts in DB.
In production, self-register is disabled by default. If explicitly enabled, set
`CTOA_SELF_REGISTER_CODE` to a non-empty invite code.

## API Base URL (local vs VPS)
- Local backend example: `http://127.0.0.1:8787`
- VPS/backend-over-network example: `https://<vps-domain>`

If you use `127.0.0.1` from your Windows desktop, desktop app expects backend to run on that same machine.
Remote API URLs must use HTTPS and must not include embedded credentials,
query strings, or fragments.

## Update Safety
- Update repository identifiers must stay in `owner/repo` form.
- Windows update assets must be plain `.exe` filenames without path separators.
- Download URLs and final redirects must stay on trusted GitHub HTTPS hosts.
- The desktop app downloads the update package only; it does not auto-run the
  downloaded executable.
- Update downloads use a bounded maximum size, write to a temporary
  `.download` file, clean up partial files on failure, and replace the final
  executable only after a complete stream.

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

Owner agent launch and one-click execution are guarded writes. The desktop UI
prompts for confirmation and an audit reason, then sends `confirm=true` plus
`reason` before the backend touches DB, orchestrator, or client sync.

Optional backend env variables:
- `CTOA_SELF_REGISTER_ENABLED=false`
- `CTOA_SELF_REGISTER_CODE=<required invite code when self-register is enabled>`

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
