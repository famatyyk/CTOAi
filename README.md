# CTOA AI Toolkit

CTOAi is one AI operations platform. The current product direction is the
Control Center: one operator cockpit for local status, evidence, actions, chat,
docs, and VPS/runtime visibility.

## Start Here

Run from the repository root:

```powershell
.\ctoa.ps1 next
```

Use the visual cockpit:

```powershell
.\ctoa.ps1 cc
```

If Control Center is not already running, `cc` starts the web dev server and
opens:

```text
http://127.0.0.1:3000/control-center
```

## Current Lane

Keep current work focused on:

```text
Control Center + evidence/reporting + VPS parity
```

Do not start a new lane until the current docs/env parity work is packaged into
one reviewable change set.

## Canonical Docs

- [Documentation Index](docs/INDEX.md): routing map for canonical, active, historical, and evidence docs.
- [Repo Schema](docs/REPO_SCHEMA.md): current repository map and ownership contract.
- [Foundation Cleanup](docs/CTOAI_FOUNDATION_CLEANUP.md): surface cleanup plan.
- [Product Portfolio](docs/PRODUCT_PORTFOLIO.md): product ownership and product-ready definition.
- [Infrastructure Canonical](docs/INFRASTRUCTURE_CANONICAL.md): VPS/deploy/production source of truth.
- [Sprint Governance](docs/SPRINT_GOVERNANCE.md): sprint gates and release process.

## Main Commands

```powershell
.\ctoa.ps1 next       # one recommended next step
.\ctoa.ps1 cc         # open Control Center
.\ctoa.ps1 status     # local + VPS + dashboard snapshot
.\ctoa.ps1 test       # pytest suite without e2e
.\ctoa.ps1 help       # command reference
```

## Repository Shape

| Area | Path | Role |
| --- | --- | --- |
| Control Center | `web/src/app/control-center` | Main operator cockpit |
| Command surface | `ctoa.ps1` | One Windows operator entry point |
| Runtime/API | `runner/`, `api/`, `mobile_console/` | Execution and compatibility surfaces |
| Agents/prompts/scoring | `agents/`, `prompts/`, `scoring/` | Agent execution quality loop |
| Ops/deploy | `scripts/`, `deploy/` | Local and VPS automation |
| Governance | `workflows/`, `policies/`, `docs/history/sprints/` | Sprint and release records |
| Evidence | `releases/evidence/`, `runtime/evidence/` | Release proof and generated state |

## History

- [CHANGELOG](CHANGELOG.md) is release history only.
- `docs/history/`, `docs/evidence/`, `docs/experiments/`, and `releases/evidence/`
  are retained for traceability. They should not drive new implementation unless
  a canonical doc links to them as current.

## Rule

One repo, one project, one current operator path:

```powershell
.\ctoa.ps1 next
.\ctoa.ps1 cc
```

## License

MIT
