# CTOAi Foundation Cleanup

This document is the cleanup map for the platform foundation. It intentionally avoids adding new features. Its job is to reduce chaos by deciding which existing surfaces are canonical, which ones become wrappers, and which ones should eventually be archived or deleted.

## Core rule

One job, one canonical surface.

If an old surface still has useful behavior, migrate that behavior into the canonical surface before deleting anything.

## Canonical foundation

| Area | Canonical target | Reason |
| --- | --- | --- |
| Operator cockpit | `web/src/app/control-center` | Single place for VPS, Docker, bot runtime, GitHub CI, docs map and chat. |
| Chat engine | `web/src/components/ChatWindow.tsx` | Already used by the main web chat and now embedded in Control Center. |
| Control Center chat wrapper | `web/src/components/ControlCenterChatPanel.tsx` | Wrapper around the canonical chat engine, not a separate chat product. |
| Ops data API | `web/src/app/api/control-center/*` | One read-only status layer for Control Center. |
| Windows entry point | `desktop_console` | Should become launcher/profile/update shell, not a second cockpit. |
| Command engine | `ctoa.ps1` plus guarded wrappers | Existing operator command surface; UI should call fixed wrappers, not ad-hoc commands. |
| Runtime backend | `mobile_console/app.py` and service modules | Backend API remains useful, but the old UI surface should not be the main cockpit. |
| Runtime target | VPS Docker stack | Production runtime and live ops target. |

## Surface inventory

| Surface | Current role | Decision | Next cleanup action |
| --- | --- | --- | --- |
| `web/src/app/control-center` | New operator cockpit | Canonical | Keep expanding only by absorbing existing capabilities. |
| `web/src/app/page.tsx` | Existing standalone chat/login app | Transitional | Keep until Control Center owns login/session flow; then redirect or slim down. |
| `web/src/components/ChatWindow.tsx` | Chat UI and `/api/chat` client | Canonical | Reuse everywhere; do not create another chat component. |
| `web/src/components/LoginPanel.tsx` | Web auth screen | Candidate canonical auth UI | Keep for now; later embed or route through Control Center. |
| `desktop_console/app.py` | Windows GUI with login, dashboard, admin console, updater | Wrapper | Keep EXE, but make it launch/open Control Center and only keep unique Windows/update/profile behavior. |
| `mobile_console/app.py` | FastAPI API plus legacy UI routes | Backend-only plus legacy UI | Keep API; mark `/console` and `/live-dashboard` as legacy after parity. |
| `mobile_console/static/index.html` | Legacy console UI | Legacy | Replace with link/redirect once Control Center has missing dashboard/admin parity. |
| `docs/site/live-dashboard.html` | Static live dashboard | Legacy | Preserve as reference until Control Center has equivalent status panels. |
| `bot/dashboard/app.py` | Bot-specific FastAPI dashboard | Legacy/reference | Move useful bot metrics into Control Center; keep as dev-only until then. |
| `ctoa.ps1` | Windows operator CLI | Command engine | Keep; expose selected read-only actions in Control Center. |
| `scripts/ops/ctoa_loader.py` | Packagable loader | Review | Decide whether it overlaps with desktop launcher. |
| `scripts/windows/open-control-center.ps1` | Opens Control Center | Wrapper | Keep as lightweight entry helper. |
| `docs/REPO_SCHEMA.md` | Current repo map | Canonical docs map | Keep refreshed as module boundaries change. |
| `docs/CTOAI_CONTROL_CENTER_PHASE1.md` | Control Center phase record | Current | Keep as implementation history. |
| `docs/CTOAI_SURFACE_CONSOLIDATION.md` | Surface consolidation policy | Current | Keep as policy companion to this cleanup map. |

## Login consolidation

Current issue: login exists across web, desktop and mobile surfaces.

Target:

| Layer | Target role |
| --- | --- |
| Web login | Canonical visual auth flow. |
| Desktop login | Transitional or profile/auth helper only. |
| Mobile console auth | API contract and backend enforcement. |

Rule: do not add another login screen.

## Chat consolidation

Current issue: main web chat and Control Center chat could become separate products.

Target:

| Piece | Target role |
| --- | --- |
| `ChatWindow.tsx` | Canonical chat engine. |
| `ControlCenterChatPanel.tsx` | Wrapper embedded inside Control Center. |
| `/api/chat` | Canonical chat API route. |

Rule: if another surface needs chat, it imports/wraps `ChatWindow`.

## Console consolidation

Current issue: desktop console, mobile console, web Control Center, static live dashboard, bot dashboard and CLI all compete for "main console" status.

Target:

| Surface | Target role |
| --- | --- |
| Control Center | Main operator cockpit. |
| Desktop console | Windows launcher, updater and profile shell. |
| Mobile console | Backend API and legacy compatibility. |
| Static live dashboard | Reference/legacy until absorbed. |
| Bot dashboard | Dev/runtime reference until absorbed. |
| `ctoa.ps1` | Command engine. |

Rule: operator starts in Control Center.

## Cleanup sequence

1. Mark canonical surfaces in docs and UI.
2. Inventory duplicate features before deleting anything.
3. Move missing unique behavior into Control Center.
4. Replace old UI entry points with links to Control Center.
5. Archive stale docs and old dashboards.
6. Delete only after parity is visible and documented.

## Near-term non-feature work

| Task | Why it matters |
| --- | --- |
| Add "Foundation Cleanup" section in Control Center Docs Map | Makes cleanup visible during daily work. |
| Keep `REPO_SCHEMA.md` aligned with Control Center decisions | Prevents old architecture from returning. |
| Inventory desktop console unique capabilities | So we know what must move before slimming it. |
| Inventory mobile console API vs UI | So backend stays while duplicate UI gets retired. |
| Define auth contract once | Prevents another login fork. |
| Define command risk classes once | Prevents unsafe deploy/restart buttons. |

## Legacy entrypoint markers

First cleanup pass marks old UI entrypoints without deleting them:

| Entrypoint | Marker |
| --- | --- |
| `/console` from `mobile_console/app.py` | `X-CTOAi-UI-Status: legacy; canonical=control-center` header and visible banner |
| `/live-dashboard` from `mobile_console/app.py` | `X-CTOAi-UI-Status: legacy; canonical=control-center` header and visible banner |
| `bot/dashboard/app.py` root page | Visible legacy/dev dashboard notice |

The marker points operators to:

```text
http://127.0.0.1:3000/control-center
```

No automatic redirect is used yet. This preserves old tests, old operator flows and missing unique features while making the canonical destination obvious.

## Legacy feature inventory

The migration inventory lives in:

```text
docs/CTOAI_LEGACY_FEATURE_INVENTORY.md
```

This is the checklist for what must be migrated, wrapped or intentionally dropped before old UI surfaces are removed.

First read-only parity pack:

```text
GET /api/control-center/legacy
```

This brings logs, dashboard summary, agent status, release evidence and command dictionary into Control Center without enabling writes.

Command risk model:

```text
docs/CTOAI_COMMAND_RISK_MODEL.md
```

This defines `read_only`, `safe_write`, `guarded_write`, `dangerous` and `forbidden_ui` before legacy write actions move into Control Center.

## Definition of cleaner foundation

The foundation is cleaner when:

| Signal | Target |
| --- | --- |
| Main cockpit count | 1 |
| Chat engine count | 1 |
| Login contract count | 1 |
| Windows launcher count | 1 |
| Ops status endpoint family | 1 |
| Stale architecture docs | Marked, refreshed or archived |
| Legacy dashboards | Linked, wrapped or retired |
