# CTOAi Legacy Feature Inventory

This document lists unique capabilities that still live in legacy surfaces. Nothing should be deleted or heavily slimmed until the relevant unique capability is either migrated into Control Center, intentionally dropped, or kept as backend-only.

## Migration status legend

| Status | Meaning |
| --- | --- |
| Keep | Keep as-is because it is backend, CLI, or platform infrastructure. |
| Migrate | Move UX/capability into Control Center before retiring legacy UI. |
| Wrap | Keep legacy code, but expose it through Control Center or launcher. |
| Drop later | Candidate for deletion after parity and explicit approval. |
| Review | Needs a decision before migration/deletion. |

## Mobile console capabilities

Source surfaces:

```text
mobile_console/app.py
mobile_console/static/index.html
mobile_console/static/app.js
docs/site/live-dashboard.html
```

| Capability | Current endpoint/UI | Current surface | Decision | Control Center target |
| --- | --- | --- | --- | --- |
| Login/logout/session | `/api/auth/login`, `/api/auth/me`, `/api/auth/logout` | mobile console + web | Keep | One auth contract, then Control Center session shell |
| Self-register | `/api/auth/register`, `/api/users/register` | mobile console/live dashboard | Review | Owner/admin panel if still needed |
| User list/admin | `/api/users`, role/password/delete endpoints | live dashboard | Migrate | Control Center `Admin` panel, owner-only |
| Health/status | `/api/health`, `/api/status` | mobile console | Keep | Already partially represented by `/api/control-center` |
| Presets | `/api/presets` | mobile console/desktop | Migrate | Command palette/read-only command browser |
| Command execution | `/api/command` | mobile console terminal/admin console | Wrap with guardrails | Guarded command runner with risk classes |
| Logs | `/api/logs?target=...` | mobile console logs tab | Migrate | Control Center logs panel |
| Server registration | `/api/server/register` | mobile console agents tab | Review | Runtime/agent onboarding panel if still active |
| Intel mission launch | `/api/agents/intel/launch` | mobile console/desktop | Migrate guarded | Control Center `Agents` or `Intel` panel |
| Intel report | `/api/agents/intel/report` | mobile console/desktop | Migrate | Control Center reports panel |
| Auto-trainer latest | `/api/agents/auto-trainer/latest` | mobile console | Migrate if active | Control Center reports/training panel |
| One-click execution | `/api/agents/execution/run` | mobile console/desktop | Migrate guarded | Control Center guarded action |
| Execution metrics/trend | `/api/agents/execution/metrics`, `/trend` | mobile console | Migrate | Control Center telemetry panel |
| Generated latest | `/api/agents/generated/latest` | live dashboard | Migrate | Control Center generated artifacts panel |
| Dashboard summary | `/api/dashboard` | mobile console/live dashboard/desktop | Migrate | Control Center summary/status panels |
| Agent status | `/api/agents/status` | mobile console/desktop | Migrate | Control Center agents panel |
| Commands dictionary | `/api/commands/dictionary` | mobile console | Migrate | Command palette |
| Release evidence | `/api/dashboard/release-evidence` | mobile console | Migrate | Governance/evidence panel |
| Live dashboard profile | `/api/live-dashboard/profile` | live dashboard/desktop | Review | Possibly absorbed into Control Center preferences |
| Admin settings | `/api/admin/settings` | backend/admin | Review | Admin settings panel if still used |
| Ideas | `/api/ideas` | backend | Review | Product backlog or drop later |
| Metrics endpoint | `/metrics` | backend | Keep | Observability backend |

## Desktop console capabilities

Source surfaces:

```text
desktop_console/app.py
desktop_console/api_client.py
desktop_console/update_client.py
scripts/windows/build-ctoa-desktop-exe.ps1
scripts/windows/open-control-center.ps1
```

| Capability | Current implementation | Decision | Control Center / launcher target |
| --- | --- | --- | --- |
| Windows EXE packaging | `scripts/windows/build-ctoa-desktop-exe.ps1` | Keep | Keep as official Windows entry point |
| Control Center opener | `Ctrl+Shift+C`, `open-control-center.ps1` | Keep | Launcher canonical behavior |
| Endpoint profiles local/stage/prod | `EndpointConfigFrame`, desktop settings | Keep/wrap | Keep in launcher; later expose in Control Center settings |
| Theme selection | desktop settings | Review | Probably launcher-only or drop later |
| Login/register | `LoginFrame`, `RegisterFrame` | Transitional | Replace with Control Center/auth contract eventually |
| Guided onboarding | `OnboardingFrame` | Review | Migrate useful instructions into Control Center docs/onboarding |
| API ping/auto-check | login utilities | Migrate | Control Center backend probe already covers part |
| Update checker | `GitHubReleaseUpdater` | Keep | Unique Windows capability |
| Dashboard summary | `DashboardFrame` | Migrate/drop UI | Control Center owns dashboard |
| Agent operations | one-click run, intel launch/report | Migrate guarded | Control Center guarded actions |
| Admin console command runner | `AdminConsoleFrame` + `/api/command` | Wrap with guardrails | Control Center command runner only after risk model |
| Live profile editor | `/api/live-dashboard/profile` | Review | Replace with Control Center preferences or drop |
| Logout/session | desktop API client | Transitional | Keep until desktop is launcher-only |

## Static live dashboard capabilities

Source:

```text
docs/site/live-dashboard.html
```

| Capability | Decision | Control Center target |
| --- | --- | --- |
| Pipeline progress | Migrate | Governance/Telemetry panel |
| Server count/state | Migrate if still relevant | Runtime/agents panel |
| Latest generated modules | Migrate | Generated artifacts panel |
| Status context panel | Migrate | Health/status panel |
| Account management | Migrate guarded | Admin panel |
| Live dashboard profile | Review | Preferences or drop |

## Bot dashboard capabilities

Source:

```text
bot/dashboard/app.py
```

| Capability | Decision | Control Center target |
| --- | --- | --- |
| `/health` uptime | Keep/migrate | Bot Runtime panel |
| `/scheduler` state | Migrate | Bot Runtime scheduler card |
| `/stats` gold/hr exp/hr kills session hours | Migrate if bot product remains active | Bot Runtime metrics panel |
| `/metrics` Prometheus | Keep | Observability backend |
| HTML dashboard | Drop later | Control Center absorbs UI |

## Migration order

Recommended sequence before slimming legacy:

1. Logs panel from `/api/logs`.
2. Dashboard summary from `/api/dashboard`.
3. Agent status from `/api/agents/status`.
4. GitHub/release evidence from `/api/dashboard/release-evidence`.
5. Command dictionary from `/api/commands/dictionary`.
6. Guarded command/action model for `/api/command`.
7. Admin users panel from `/api/users`.
8. Desktop endpoint profiles and update checker stay in launcher.
9. Bot dashboard scheduler/stats into Bot Runtime tab.
10. Only then consider redirects or deletion of legacy UI.

## First migrated read-only parity pack

Control Center now reads the first legacy capabilities through:

```text
GET /api/control-center/legacy
```

UI component:

```text
web/src/components/ControlCenterLegacyPanels.tsx
```

Migrated read-only visibility:

| Capability | Legacy source | Control Center status |
| --- | --- | --- |
| Logs preview | `/api/logs?target=runner&lines=80` | Read-only panel |
| Dashboard summary | `/api/dashboard` | Read-only panel |
| Agent status | `/api/agents/status` | Read-only panel |
| Release evidence | `/api/dashboard/release-evidence` | Read-only panel |
| Command dictionary | `/api/commands/dictionary` | Read-only panel |

This does not migrate write actions yet. `/api/command`, one-click execution, intel launch and user admin remain legacy/guarded until a command risk model exists.

The command risk model now lives in:

```text
docs/CTOAI_COMMAND_RISK_MODEL.md
```

Until that model is implemented in code, write actions remain blocked from Control Center.

## Do not delete yet

Do not delete these until parity is complete:

| Surface | Why |
| --- | --- |
| `mobile_console/static/index.html` | Still has agent, logs, command and dashboard UX not fully migrated. |
| `docs/site/live-dashboard.html` | Still has account management and generated/latest dashboard UX. |
| `desktop_console/app.py` | Still has Windows update/profile behavior and operational UX. |
| `bot/dashboard/app.py` | Still has bot scheduler/stats endpoints and dev dashboard. |
