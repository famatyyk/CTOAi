# CTOAi Operations Audit

Snapshot date: 2026-07-06 Europe/Warsaw

This file records current operational evidence gathered for Engine Brain
planning. Refresh it before release, deploy, or infrastructure work.

## Local Git

- Repo root: `C:/Users/zycie/CTOAi`
- Branch: `codex/control-center-guarded-actions`
- HEAD: `43b76958e4efa1d59f974f1ae1effb482160b964`
- Plain `git` is available through PATH in this PowerShell session and resolves
  to Git for Windows at `C:\Program Files\Git\cmd\git.exe`.
- Worktree is dirty and includes pre-existing OTClient/local changes plus
  `AI/`.
- Remote `origin`: `https://github.com/famatyyk/CTOAi.git`
- Remote `upstream`: `git@github.com:famatyyk/CTOAi.git`

Rule: if plain `git` disappears from PATH again, use the explicit Git for
Windows path, and do not package unrelated dirty work without a scope decision.

## GitHub

- Auth: `gh` is logged in as `famatyyk`.
- Repo: `famatyyk/CTOAi`
- Visibility: public.
- Default branch: `main`.
- Repo URL: `https://github.com/famatyyk/CTOAi`
- Open PRs found: 6.
- High-attention PRs:
  - `#184` `[WIP] Fix CTOA VPS Global Save Cycle failure`, merge state `DIRTY`.
  - `#183` `[WIP] Fix CTOA VPS Global Save Cycle failure`, merge state `DIRTY`.
  - `#160`, `#157`, `#153`, `#152` are older Copilot/review lanes.
- Last 15 listed workflow runs were completed successfully.

Rule: use `gh` with Git on PATH or pass explicit `--repo` values to avoid base
repo detection failures.

## Docker

- Docker client/server: `29.4.1`.
- Docker Desktop: `4.71.0`.
- Docker context: `desktop-linux`.
- Compose: `v5.1.3`.
- Running CTOAi-related containers include `ctoa-api` and `ctoa-postgres`.
- `docker compose up -d --remove-orphans api postgres` recreated the active
  root compose runtime and removed stale orphan containers that had kept broad
  host bindings.
- `ctoa-api` is bound to loopback at `127.0.0.1:8001->8000/tcp`.
- `ctoa-postgres` is reachable only inside Docker networking (`5432/tcp`).
- Current root `docker-compose.yml` config resolves API to
  `127.0.0.1:8001:8000` by default through `CTOA_BIND_HOST`.
- Current `bot/infra/docker-compose.yml` config resolves dashboard and
  Prometheus to `127.0.0.1` by default through
  `CTOA_BOT_DASHBOARD_BIND_HOST` and `CTOA_MONITOR_BIND_HOST`.
- The obsolete `version` field was removed from `bot/infra/docker-compose.yml`.
- Engine Brain doctor reports `running_broad=0` and `configured_broad=0`.

Rule: local development services should bind to loopback unless LAN/VPN access
is explicitly required.

## VPN

- Cloudflare WARP adapter is present and up.
- `warp-cli` path: `C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe`.
- `warp-cli status`: connected, network healthy.
- Wi-Fi and WSL virtual adapter are also up.
- No Windows built-in VPN profile was listed by `Get-VpnConnection`.

Rule: WARP is active network context; keep Docker services on loopback unless
LAN/VPN exposure is explicitly required and reviewed.

## Vercel

- Vercel CLI: `54.10.3`.
- Logged-in account shown by CLI: `famatyyk-5221`.
- Linked project: `ctoa-web`.
- Project framework: `nextjs`.
- Project node version: `24.x`.
- `web/package.json` uses Next `^16.2.9`, React `^19.0.0`, TypeScript `^5`,
  and Vitest `^4.1.9`.

Rule: list Vercel project metadata and env names only; do not print env values.

## VS Code And Codex Extension

- Active extension list includes `openai.chatgpt@26.623.101652`.
- Older OpenAI extension directories still exist:
  - `openai.chatgpt-26.623.70822-win32-x64`
  - `openai.chatgpt-26.623.81905-win32-x64`
  - `openai.chatgpt-26.623.101652-win32-x64`
- Installed relevant extensions include GitHub PRs, GitHub Actions, Docker,
  Remote SSH/Containers/WSL, Python, Pylance, Python envs, Codex stats, and
  ChatGPT/Codex.
- Workspace Python interpreter is pinned to
  `C:\Users\zycie\CTOAi\.venv\Scripts\python.exe`.
- `.vscode/extensions.json` recommends PowerShell, OTC doc hub, and OTUI
  highlights extensions.

Rule: if Codex extension commands disappear again, inspect stale extension dirs
and workspace storage before blaming repo code.

## Local CTOAi Gate

Evidence command:

```powershell
.\.venv\Scripts\python.exe scripts\ops\ctoa_update_gate.py
```

Current result:

- `ok: true`
- `status: launch_allowed`
- Product: `CTOA Toolkit`
- Version: `1.1.1`
- Channel: `stable`
- Package tier: `studio`

Drift:

- Historical memory referenced `scripts/ops/ctoa_env_doctor.py`, but that file
  is absent in the current worktree.
- Current preflight-like scripts include `scripts/ops/ctoa_update_gate.py` and
  `scripts/ops/run_validator_with_preflight.py`.

## Engine Brain Doctor

Evidence command:

```powershell
.\ctoa.ps1 brain doctor
```

Current result:

- Output JSON: `AI/generated/ENV_DOCTOR.json`
- Output Markdown: `AI/generated/ENV_DOCTOR.md`
- Overall status: `warn`
- Failed checks: `0`
- Docker check: `ok`, with `running_broad=0` and `configured_broad=0`.
- Warnings are currently limited to GitHub PRs with `DIRTY` merge states.

Rule:

- Use `.\ctoa.ps1 brain doctor` as the current replacement for the removed
  historical `scripts/ops/ctoa_env_doctor.py`.
