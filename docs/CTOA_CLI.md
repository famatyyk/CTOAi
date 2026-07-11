# CTOAi CLI (MVP)

Single entrypoint for day-to-day operations using short commands.

## Entry point

Run from repository root:

```powershell
.\ctoa.ps1 help
```

## Command legend

- `menu` (`m`) - interactive command picker for the most common workflows
- `next` (`nx`) - show the recommended next step and current review lane
- `cc` (`control-center`) - open the visual Control Center and start web dev if needed
- `dev` - developer profile; starts mobile console in dev mode
- `ops` - operator profile; runs core/risk/sprint health checks
- `prod` - production profile; runs update gate and sprint-029 validation
- `status` (`s`) - combined snapshot: local guards + VPS services + dashboard health
- `up` - start mobile console in dev mode (`uvicorn` on port `8787`)
- `test` (`t`) - run local test suite (excludes `tests/e2e`)
- `val <sprint>` (`v`) - run sprint validator and write CI artifact JSON
- `nightly [sprint]` (`n`) - run nightly stability batch for sprint (default `029`)
- `doctor` (`d`) - run core guard + runtime freeze guard + sprint-029 validator
- `vps <action>` - run VPS operation via `scripts/ops/ctoa-vps.ps1 -Action <action>`
- `runner <status|restart|logs>` - runner service shortcuts
- `report <status|restart|now|logs>` - report service shortcuts
- `mobile <status|restart|logs>` - mobile service shortcuts
- `logs <runner|health|agents|report|mobile>` - logs shortcuts
- `dash snap` - VPS dashboard snapshot
- `report now` - publish report via service environment
- `brain refresh` - regenerate secret-safe Engine Brain file tree and symbol map
- `brain doctor` - run secret-safe Engine Brain environment audit
- `brain pack [all|helper|control-center|infra|security]` - build a portable secret-safe Engine Brain markdown pack

## Practical examples

```powershell
# Interactive start
.\ctoa.ps1 next
.\ctoa.ps1 cc
.\ctoa.ps1 menu

# Profiles
.\ctoa.ps1 dev
.\ctoa.ps1 ops
.\ctoa.ps1 prod

# Unified status snapshot
.\ctoa.ps1 status

# Quick startup
.\ctoa.ps1 up

# Fast validation loop
.\ctoa.ps1 t
.\ctoa.ps1 v 029

# Daily health check
.\ctoa.ps1 d

# VPS operations
.\ctoa.ps1 runner status
.\ctoa.ps1 report restart
.\ctoa.ps1 mobile logs
.\ctoa.ps1 logs health
.\ctoa.ps1 vps ValidateServices
.\ctoa.ps1 dash snap
.\ctoa.ps1 report now
.\ctoa.ps1 brain refresh
.\ctoa.ps1 brain doctor
.\ctoa.ps1 brain pack
.\ctoa.ps1 brain pack helper
```

## Rule for adding aliases

If you run any command manually more than 2 times, add a dedicated alias to `ctoa.ps1`.

This keeps operations centralized and reduces context switching across scripts/tasks/web UIs.

## Shared command vocabulary (CLI + Web)

Command dictionary source:

- `schemas/ctoa-command-dictionary.json`

Web/API exposure:

- `GET /api/commands/dictionary`

This keeps dashboard/web and CLI aligned to the same command names and meanings.

## Suggested daily usage

- Start with `menu` if you do not remember the command.
- Start with `next` if you are overloaded and need one concrete recommendation.
- Use `cc` when you need the visual cockpit instead of reading code or scripts; it starts web dev if port 3000 is not responding.
- Use `dev` when you are building locally.
- Use `ops` when you want a quick operational snapshot.
- Use `prod` before release-facing work.
