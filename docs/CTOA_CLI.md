# CTOAi CLI (MVP)

Single entrypoint for day-to-day operations using short commands.

## Entry point

Run from repository root:

```powershell
.\ctoa.ps1 help
```

## Command legend

- `menu` (`m`) - interactive command picker for the most common workflows
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

## Practical examples

```powershell
# Interactive start
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
- Use `dev` when you are building locally.
- Use `ops` when you want a quick operational snapshot.
- Use `prod` before release-facing work.
