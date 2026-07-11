# CTOAi Control Center: Phase 1 Blueprint

Phase 1 creates a single visible operator surface for the project. The goal is not to add another random app. The goal is to make the existing platform understandable, launchable and operable from one place.

## Source of truth

`docs/REPO_SCHEMA.md` has been refreshed and is now the current repository map. It should stay aligned with Control Center and the foundation cleanup map.

The Phase 1 source of truth is this boundary map:

| Name | Meaning |
| --- | --- |
| CTOAi Platform | The whole system: runtime, ops, governance, telemetry and interfaces. |
| Control Center | The user-facing cockpit and launcher for daily operation. |
| Runtime Plane | Bot runtime, agents, schedulers, input backend and execution state. |
| Status Plane | Local evidence, repo hygiene, release packs and audit traces. |
| Governance Plane | Approvals, security rules, evidence, CI gates and audit trail. |
| Telemetry Plane | Metrics, reports, monitoring, alerts and runtime visibility. |
| Interfaces | Web UI, Windows desktop launcher, mobile console and Codex/chat surface. |

## Product decision

Use a hybrid model:

| Surface | Role |
| --- | --- |
| `desktop_console` | Windows EXE entry point, profile selector and local launcher. |
| `web` | Primary modern cockpit UI. |
| `ctoa.ps1` | Local command engine for scripted actions. |
| Local runtime + evidence files | File-backed source of truth for the cockpit. |
| Codex/chat | Operator workspace for guided work and troubleshooting. |

This keeps the old launcher idea, but avoids trapping the whole product inside Tkinter. The desktop app should launch, configure and supervise. The web app should present the rich dashboard.

## First UI route

Phase 1 starts with:

```text
web/src/app/control-center/page.tsx
```

This route is a visual shell for the Control Center. It does not replace the current chat page. It gives us a clean place to design the future cockpit without breaking the existing interface.

## Navigation model

Initial left navigation:

| Section | Purpose |
| --- | --- |
| Overview | Global status and project health. |
| Codex Chat | Work conversation and guided actions. |
| Local Status | Repo hygiene, release evidence, cost report and audit trace. |
| Docs Map | Architecture, repo boundaries and foundation cleanup decisions. |

## Phase 1 data tiles

The first dashboard should expose:

| Tile | Initial source |
| --- | --- |
| Repo hygiene | Local JSON report under `runtime/repo-hygiene/local-pr-quality.json`. |
| Release evidence | Local evidence pack under `runtime/evidence/latest.json`. |
| API cost report | Local cost report under `runtime/api-cost/latest.json`. |
| Control Center audit | Local JSONL audit log under `runtime/control-center/action-audit.jsonl`. |
| Codex/chat state | Local session state first, direct integration later. |

## Command model

All destructive or high-risk commands should start as read-only buttons. Write actions can be added after we have confirmation gates.

Safe first commands:

```text
Refresh repo hygiene snapshot
Refresh API cost report
Rebuild evidence pack
```

Later write commands:

```text
Docker cleanup
Controlled rebuild
Bot restart
Deploy selected image
Archive old artifacts
```

## Phase plan

1. Create Control Center shell route in `web`.
2. Keep existing chat route untouched.
3. Connect the shell to static last-known health data.
4. Add backend endpoints for read-only status.
5. Wire desktop EXE launcher to open the Control Center.
6. Add local refresh actions after status is reliable.
7. Refresh repo schema after module names stabilize.

## Phase 2: launcher bridge

The Windows desktop console now has a direct launcher path to Control Center:

```text
Ctrl+Shift+C
```

Default target:

```text
http://127.0.0.1:3000/control-center
```

The target is stored as `control_center_url` in the desktop settings file. This makes the EXE a stable entry point while keeping the richer cockpit in the web app.

Windows helper:

```text
scripts/windows/open-control-center.ps1
```

## Phase 3: status layer

The first status endpoint is:

```text
GET /api/control-center
```

It currently returns a static, typed snapshot from:

```text
web/src/lib/controlCenterSnapshot.ts
```

This is intentional. Static first prevents the UI from being blocked by remote wiring or auth setup. The next step is replacing each field with local read-only sources.

## Phase 4: backend probe

The Control Center endpoint now probes the configured backend API:

```text
VPS_API_URL/api/status
```

When `VPS_API_URL` is not set, the web app falls back to:

```text
http://127.0.0.1:8001/api/status
```

The response is merged into:

```text
GET /api/control-center
```

This is read-only and safe. It gives the cockpit an early live signal without adding deploy/restart buttons yet.

The UI reads this endpoint through:

```text
web/src/components/ControlCenterLiveProbe.tsx
```

The probe refreshes every 30 seconds.

## Definition of done for Phase 1

Phase 1 is done when:

| Requirement | Status |
| --- | --- |
| A Control Center route exists | Started |
| Platform boundaries are named | Started |
| Desktop launcher role is clear | Wired through shortcut |
| Existing chat is not broken | Preserved |
| Local status tiles are visible | Started |
| Status endpoint exists | Started |
| Backend API probe exists | Started |
| Frontend live probe exists | Started |
| Live backend wiring is intentionally deferred | Planned |

## Phase 5: live ops tiles

The first real local status endpoint is:

```text
GET /api/control-center/ops
```

It collects local file-backed status from:

| Tile | Probe |
| --- | --- |
| Repo hygiene | `runtime/repo-hygiene/local-pr-quality.json` |
| Release evidence | `runtime/evidence/latest.json` |
| API cost report | `runtime/api-cost/latest.json` |
| Control Center audit | `runtime/control-center/action-audit.jsonl` |

The route uses only fixed local reads and timeouts. It is intentionally read-only, but it is not public: local evidence reads require operator-or-owner access before files are collected. Browser-visible paths are display-safe: repo-local paths are relative, and external absolute paths collapse to `[external]/name`. Release-evidence and API-cost markdown responses apply the same redaction and display-path rules before returning text to the browser. If local paths are unavailable, the tile reports `unknown` instead of breaking the page.

Configuration knobs:

| Env var | Default |
| --- | --- |
| `CTOA_RELEASES_DIR` | `releases/evidence` |
| `CTOA_REPO_HYGIENE_PATH` | `runtime/repo-hygiene/local-pr-quality.json` |
| `CTOA_API_COST_REPORT_PATH` | `runtime/api-cost/latest.json` |
| `CTOA_ACTION_AUDIT_PATH` | `runtime/control-center/action-audit.jsonl` |

UI component:

```text
web/src/components/ControlCenterOpsGrid.tsx
```

Refresh interval:

```text
45 seconds
```

## Phase 6: detail panels

The Control Center now has real detail panels layered on top of the status tiles:

| Panel | Data |
| --- | --- |
| Repo hygiene | Repo hygiene JSON snapshot |
| Release evidence | Evidence pack and sprint folder summary |
| API cost report | Cost report JSON and eval artifact summary |
| Control Center audit | JSONL audit trail with recent local actions |

UI component:

```text
web/src/components/ControlCenterDetailPanels.tsx
```

The detail panels remain read-only and operator-gated. They are visible in Overview and focused tabs:

| Tab | Details |
| --- | --- |
| Overview | All detail panels |
| Local Status | All local status panels |

The Release evidence panel now consumes the same drilldown payload as the
Evidence tab: latest tracked markdown files, runtime-vs-tracked comparison and
next review action. The Control Center audit panel now consumes sanitized JSONL
metadata from the action-audit drilldown, including risk/action counts,
dry-run, failed, denied and invalid-record counters. Raw command output previews
are not required for either panel.

## Phase 7: embedded chat and surface consolidation

The Codex Chat tab now embeds the existing chat engine instead of creating a separate third chat.

Canonical chat component:

```text
web/src/components/ChatWindow.tsx
```

Control Center wrapper:

```text
web/src/components/ControlCenterChatPanel.tsx
```

Storage key:

```text
ctoa_control_center_chat
```

The consolidation plan lives in:

```text
docs/CTOAI_SURFACE_CONSOLIDATION.md
```

Rule: no new surface unless it replaces or wraps an old one.

## Phase 8: foundation cleanup map

The cleanup map for duplicate consoles, chats, login screens, dashboards and stale docs now lives in:

```text
docs/CTOAI_FOUNDATION_CLEANUP.md
```

This phase is intentionally not a feature phase. It marks the foundation decisions:

| Area | Decision |
| --- | --- |
| Main cockpit | Control Center |
| Chat | One `ChatWindow` engine |
| Desktop | Launcher/wrapper |
| Mobile console | Backend/API plus legacy UI until parity |
| Static dashboards | Legacy/reference until absorbed |
| `REPO_SCHEMA.md` | Refreshed canonical repo map |
