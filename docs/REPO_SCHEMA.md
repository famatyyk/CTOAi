# CTOAi Repo Schema

Status: refreshed on 2026-06-29.

This document is the current repository map and foundation contract for CTOAi. It replaces the older schema that treated `mobile_console` and `desktop_console` as the main execution surfaces. The current direction is simpler:

```text
One job, one canonical surface.
```

## What CTOAi is

CTOAi is an AI operations platform. Its current product body has several planes:

| Plane | Meaning |
| --- | --- |
| Control Center | Main operator cockpit and visual command surface. |
| Runtime Plane | Bot runtime, agents, scheduler, input backend and execution state. |
| Ops Plane | VPS, Docker, deploys, rebuilds, disk, logs and service health. |
| Governance Plane | Approvals, CI gates, evidence, policy and release decisions. |
| Telemetry Plane | Metrics, monitoring, reports, alerts and runtime visibility. |
| Interfaces | Web cockpit, Windows launcher, chat surface and API clients. |

## Canonical surfaces

| Job | Canonical surface | Notes |
| --- | --- | --- |
| Main operator cockpit | `web/src/app/control-center` | Daily work starts here. |
| Chat engine | `web/src/components/ChatWindow.tsx` | Reused by standalone chat and Control Center. |
| Control Center chat wrapper | `web/src/components/ControlCenterChatPanel.tsx` | Wrapper, not a separate chat product. |
| Ops status API | `web/src/app/api/control-center/*` | Read-only VPS/Docker/Bot/GitHub visibility. |
| Windows entry point | `desktop_console` | Launcher/profile/update shell, not the main cockpit. |
| Backend/API compatibility | `mobile_console/app.py` | Backend and legacy API provider. |
| Operator commands | `ctoa.ps1` and guarded scripts | Command engine under UI/API wrappers. |
| Production runtime | VPS Docker stack | Live runtime target. |

## Layered architecture

```mermaid
flowchart TD
    U[Operator] --> CC[Control Center\nweb/src/app/control-center]
    CC --> CHAT[Chat Engine\nChatWindow + /api/chat]
    CC --> OPSAPI[Control Center Ops API\n/api/control-center/*]
    CC --> DOCS[Docs Map\nfoundation cleanup + repo schema]
    DESK[Desktop EXE\ndesktop_console] --> CC
    OPSAPI --> VPS[VPS\n116.202.96.250:2222]
    OPSAPI --> GH[GitHub\nCI, PRs, workflow runs]
    VPS --> DOCKER[Docker Stack\ninfra-bot, dashboard, api, postgres]
    DOCKER --> BOT[Bot Runtime\ninfra-bot]
    MOB[mobile_console/app.py] --> API[Legacy/API compatibility]
    RUN[runner + agents + prompts] --> GOV[Governance + sprint flow]
    CI[.github/workflows] --> GOV
```

## Top-level ownership map

| Path | Owner role | Current decision |
| --- | --- | --- |
| `web/` | Main web UI, chat, Control Center and web API routes | Canonical cockpit |
| `desktop_console/` | Windows desktop app, updater, endpoint profiles | Wrapper/launcher |
| `mobile_console/` | FastAPI backend and legacy static console routes | Backend-only plus legacy UI |
| `api/` | API entry points and chat/system integration | Active backend surface |
| `bot/` | Bot runtime, dashboard reference and bot-specific services | Runtime Plane |
| `deploy/` | VPS/systemd/Docker deployment definitions | Ops Plane |
| `scripts/` | Local and VPS automation, validators and helpers | Command engine |
| `ctoa.ps1` | Windows operator command surface | Command engine |
| `runner/` | Agent/sprint orchestration runtime | Governance/runtime |
| `agents/` | Agent definitions and role specs | Governance/runtime |
| `prompts/` | BRAVE(R) templates and prompt packs | Prompt engine |
| `scoring/` | Tool advisor and scoring logic | Governance/runtime |
| `workflows/` | Sprint and delivery flow contracts | Governance Plane |
| `policies/` | CI/security/governance policy contracts | Governance Plane |
| `.github/workflows/` | GitHub Actions gates and automation | CI/Governance |
| `tests/` | Python, JS and integration coverage | Validation |
| `runtime/` | Generated runtime state and CI artifacts | Evidence/runtime state |
| `docs/` | Architecture, runbooks, evidence and cleanup maps | Documentation |
| `docs/site/live-dashboard.html` | Old static live dashboard | Legacy/reference |
| `bot/dashboard/app.py` | Bot-specific status dashboard | Legacy/reference until absorbed |

## Responsibility tree

```text
CTOAi/
|- web/                         canonical Control Center, chat and web API routes
|  |- src/app/control-center/    main operator cockpit
|  |- src/app/api/control-center/ops/  read-only ops status endpoint
|  |- src/components/ChatWindow.tsx    canonical chat UI engine
|  |- src/components/ControlCenterShell.tsx
|  |- src/components/ControlCenterChatPanel.tsx
|  |- src/components/ControlCenterOpsGrid.tsx
|  |- src/components/ControlCenterDetailPanels.tsx
|- desktop_console/             Windows launcher/profile/updater shell
|- mobile_console/              backend API and legacy UI compatibility
|- api/                         API integration surface
|- bot/                         bot runtime and reference bot dashboard
|- deploy/                      VPS, Docker and service deployment definitions
|- scripts/                     ops automation, validators and helper scripts
|- ctoa.ps1                     Windows command engine
|- runner/                      orchestration runtime
|- agents/                      agent definitions
|- prompts/                     BRAVE(R) prompt templates
|- scoring/                     tool scoring and advisor logic
|- workflows/                   sprint flow contracts
|- policies/                    governance policy contracts
|- .github/workflows/           CI and automation gates
|- tests/                       validation suite
|- runtime/                     generated evidence and runtime state
|- docs/                        architecture, runbooks and cleanup decisions
```

## Interface consolidation map

| Surface | Old role | New role |
| --- | --- | --- |
| `web/src/app/control-center` | New cockpit | Main cockpit |
| `web/src/app/page.tsx` | Standalone chat/login | Transitional surface until Control Center owns login/session flow |
| `desktop_console/app.py` | Full desktop console | Windows launcher/wrapper |
| `mobile_console/static/index.html` | Operational console UI | Legacy UI until parity in Control Center |
| `docs/site/live-dashboard.html` | Static live dashboard | Legacy reference until absorbed |
| `bot/dashboard/app.py` | Bot status dashboard | Dev/runtime reference until absorbed |
| `scripts/windows/open-control-center.ps1` | New helper | Lightweight Control Center opener |

## Current Control Center endpoints

| Endpoint | Purpose | Risk class |
| --- | --- | --- |
| `GET /api/control-center` | Minimal backend reachability and aggregated runtime counts | Read-only, operator |
| `GET /api/control-center/ops?view=summary` | Capability manifest and minimized status tiles | Read-only, operator |
| `GET /api/control-center/ops?view=detail&capability=<id>` | One role-scoped capability projection loaded on demand | Read-only, operator |
| `GET /api/control-center/evidence` | Deprecated compatibility contract; points callers to scoped capability projections and returns no evidence payload | Read-only, operator |
| `GET /api/control-center/legacy` | Retired compatibility contract (`410`); performs no backend probes and returns no paths, logs, or raw payloads | Read-only, operator |
| `POST /api/chat` | Chat completion route used by `ChatWindow` | User-initiated chat |

The `/control-center` page verifies the operator session before rendering the
cockpit. An unauthenticated request renders only the identity gateway and does
not load operational components or metadata.

## Control Center capability model

| Capability | Default projection |
| --- | --- |
| `operator-next` | Evidence-backed decision without shell command or source path |
| `repo-hygiene` | Finding and classification counts |
| `release-evidence` | Sprint/file freshness without filesystem paths |
| `engine-brain` | P6/P7, pack, smoke and guardrail aggregates |
| `api-cost` | Token, cost, anomaly and dataset counts |
| `control-center-audit` | Aggregate outcomes and minimized recent records without actor or audit IDs |

The capability registry is the UI and API discovery contract. Summary responses
never include the full `details` object or source paths. Detail responses expose
only one registered capability and omit raw commands, audit actors, audit IDs,
reasons and output previews. Client polling is centralized, pauses while the page
is hidden and applies bounded backoff after failures. Runtime failures are typed
as `auth_required`, `forbidden`, `service_unavailable`, `timeout`,
`invalid_response` or `request_failed` instead of being labeled generically as
an ops probe failure.

Server-side collection is scoped as well as projection. A detail request passes
exactly one capability ID to `controlCenterCapabilityRuntime.ts`, which requests
only that typed evidence slice. Summary collection requests the six registered
slices once and shares memoized repo, cost, audit, Engine Brain and operator-next
dependencies within the request. The legacy `collectControlCenterEvidence()` and
`collectControlCenterOps()` aggregates remain compatibility internals but are not
on the canonical `/api/control-center/ops` request path. Collector failures return
a generic typed `503 service_unavailable` response without filesystem paths or
upstream error text.

Evidence ingestion has two explicit boundaries. `controlCenterEvidenceIo.ts` is
the only bounded JSON and audit-log reader: it rejects symlinks, oversized files,
duplicate JSON keys, short reads and files changed while being read.
`controlCenterEvidenceAdapters.ts` converts trusted internal evidence into the
smallest capability-specific shape before it reaches the route. These adapters
remove filesystem paths, identities, audit IDs, reasons, command output and prompt
names. Release evidence is collected in one traversal capped at 64 sprint folders
and 256 Markdown files; capability responses retain only six recent records. The
six-tile summary has a tested 10 KB serialized response budget.

The Engine Brain plugin follows the same boundary. Its public cockpit is an
allowlisted schema-v2 projection; commands, paths, identities, audit IDs,
reasons, output previews and row-level evidence never enter the MCP response.
Workspace audit status consumes the compact
`runtime/audits/ctoai-full-workspace-audit-summary.json` artifact instead of the
full file inventory. Plugin-management marks an installation ready only when
required source and installed-cache files have matching SHA-256 digests.

Confirmed `evidence-pack-refresh` actions preallocate their audit identifier and
pass it into `release_evidence_pack.py`. The generated JSON self-hashes its
canonical payload, while the action-audit record stores SHA-256 digests for the
declared JSON and Markdown outputs. Control Central reports only the verification
state and fails its evidence-integrity gate when the self-hash, audit binding, or
artifact digest does not match; identifiers and digests remain local.

Freshness is evaluated independently from integrity. The bounded workspace
policy in `AI/control-central-freshness-policy.json` defines per-artifact age
windows, while severity and hard maximums remain enforced by the plugin. Brain
and cockpit collectors share the same parser, clock-skew guard and aging
threshold. Missing, naive, far-future or expired timestamps cannot remain
silently green. Public responses contain only policy revision, status and
counts; raw timestamps stay in local drilldown evidence.

All Control Center reads remain read-only. Write operations such as restart,
rebuild, cleanup or deploy require separate guarded actions and explicit audit
contracts before they can appear in the UI.

## Delivery and governance flow

```mermaid
sequenceDiagram
    participant OP as Operator
    participant CC as Control Center
    participant GH as GitHub
    participant CI as GitHub Actions
    participant OPS as Ops Scripts
    participant RUN as Runner
    participant VPS as VPS Docker Stack

    OP->>CC: inspect status, chat, docs and ops panels
    CC->>VPS: read-only health probes
    CC->>GH: read-only CI/run probes
    OP->>GH: open PR or issue
    GH->>CI: run gates
    CI->>OPS: validators and policy checks
    OPS->>RUN: sprint/governance validation
    RUN->>GH: publish evidence and status
    GH->>OP: merge/release decision
```

## Governance status mapping

Canonical sprint/task flow:

```text
NEW -> IN_PROGRESS -> IN_QA -> IN_CI_GATE -> WAITING_APPROVAL -> RELEASED | BLOCKED
```

| Status | Operational meaning | Primary ownership |
| --- | --- | --- |
| `NEW` | Task exists but is not scheduled yet. | `runner/`, `workflows/` |
| `IN_PROGRESS` | Work is actively scheduled/executed. | `runner/` |
| `IN_QA` | Implementation is ready for regression checks. | `tests/`, `scripts/ops/` |
| `IN_CI_GATE` | CI/security/policy gates are running or blocked. | `.github/workflows/`, `policies/` |
| `WAITING_APPROVAL` | Automated wave passed; manual sign-off needed. | `workflows/`, sprint docs |
| `RELEASED` | Accepted and recorded as released. | sprint release pack |
| `BLOCKED` | Held by a policy, test, infra or approval blocker. | runner reports and gate evidence |

## Validation chain

| Scope | Command/source |
| --- | --- |
| Frontend web tests | `npm test` in `web/` |
| Python tests | `python -m pytest` |
| Sprint validators | `scripts/ops/sprint0xx_validate.py` |
| Repo hygiene | `scripts/ops/repo_hygiene_audit.py` |
| CI gates | `.github/workflows/` |
| VPS status | Control Center ops endpoint and VPS runbooks |

## Cleanup references

| Document | Purpose |
| --- | --- |
| `docs/CTOAI_FOUNDATION_CLEANUP.md` | Active cleanup decision table |
| `docs/CTOAI_LEGACY_FEATURE_INVENTORY.md` | Migration inventory for legacy UI capabilities |
| `docs/CTOAI_COMMAND_RISK_MODEL.md` | Risk classes and confirmation model for operational commands |
| `docs/CTOAI_SURFACE_CONSOLIDATION.md` | Rule for one canonical surface per job |
| `docs/CTOAI_CONTROL_CENTER_PHASE1.md` | Control Center implementation history |
| `docs/ARCHITECTURE.md` | Older high-level architecture, still useful but not the current interface map |
| `docs/MOBILE_CONSOLE.md` | Mobile console/service runbook |

## Deprecated assumptions

The old assumption below is no longer current:

```text
mobile_console and desktop_console are the main execution surfaces.
```

The current assumption is:

```text
Control Center is the main operator cockpit.
desktop_console is a Windows launcher/wrapper.
mobile_console is backend/API compatibility plus legacy UI until parity.
```

## Quick navigation

| Need | Start here |
| --- | --- |
| Daily operator cockpit | `web/src/app/control-center` |
| Chat implementation | `web/src/components/ChatWindow.tsx` |
| Control Center shell | `web/src/components/ControlCenterShell.tsx` |
| Ops endpoint | `web/src/app/api/control-center/ops/route.ts` |
| Windows launcher | `desktop_console/` and `scripts/windows/open-control-center.ps1` |
| VPS/mobile service runbook | `docs/MOBILE_CONSOLE.md` |
| Foundation cleanup | `docs/CTOAI_FOUNDATION_CLEANUP.md` |
