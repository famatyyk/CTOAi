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
- `otprofile "<opis profilu EK>"` - generate and deploy an OTClient EK profile
- `otpreview` - render and open the helper UI preview
- `otmockup` - render and open the helper UI mockup
- `otdeploy approve-live` - promote the staged Helper through the official wrapper after all release gates pass
- `otest` - run `ValidateDev` through the official wrapper and open the local preview; never touches live
- `otbg` - collect bounded passive `BackgroundNoScreen` evidence against an official promotion pin; never launches, stops, focuses, captures, sends input to, or writes inside a client
- `otp9` - refresh bounded `otbg` evidence and run the strict data-only Conditions shadow replay; writes only repo-local evidence and never dispatches, executes once, or promotes
- `otp10preview` - render a bounded, sanitized ring/container/slot observation preview from canonical `BackgroundNoScreen` evidence; never reads or controls an OTClient process
- `otp10catalog` - classify exact ring/container/slot candidates from the fixed preview without selecting or recommending an item
- `otp10plan [equipped candidate container slot "plan P10 capture profile change"]` - fail closed without arguments or generate a hash-bound repo-runtime profile plan/diff; never reads or writes `.ctoa-local` and grants no acceptance or readiness
- `otp10autoplan equipped candidate "plan P10 capture profile change"` - refresh canonical `BackgroundNoScreen` evidence, rebuild the fixed passive preview, and resolve the session-scoped candidate container/slot from exactly one fresh operational item-ID match in one command; missing and duplicate matches fail closed, and the command still writes only a reviewable no-action plan
- `otp10apply planSha "zatwierdzam zastosowanie planu P10 <planSha>"` - apply only the reviewed hash-bound plan to the fixed ignored local capture profile after verifying the current-profile SHA; retains `.bak`, writes a no-action receipt, and never reads or controls OTClient
- `otp10preflight` - validate the fixed repo-only P8/P9 report and receipt, capture doctor, and Equipment observation preview chain; writes one blocked/passed report without changing eligibility or performing runtime/live actions
- `otp10ready` - consolidate doctor, preview, dependency, catalog, and change-plan blockers into ordered human-safe next commands; missing inputs remain blocked and eligibility is unchanged
- `otp10refresh` - refresh the complete fixed repo-only P10 operator chain through strict consumer parity; accepts no paths, IDs, confirmation, acceptance, replay, client-control, or local-profile-write inputs
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
.\ctoa.ps1 otprofile "EK monk, bez aoe na 1, exeta od 2 visible, potion F1 heal 80"
.\ctoa.ps1 otest
.\ctoa.ps1 otbg
.\ctoa.ps1 otp9
.\ctoa.ps1 otp10preview
.\ctoa.ps1 otp10catalog
.\ctoa.ps1 otp10plan 3051 3048 2 1 "plan P10 capture profile change"
.\ctoa.ps1 otp10autoplan 3051 3048 "plan P10 capture profile change"
.\ctoa.ps1 otp10apply <planSha> "zatwierdzam zastosowanie planu P10 <planSha>"
.\ctoa.ps1 otp10preflight
.\ctoa.ps1 otp10ready
.\ctoa.ps1 otp10refresh
.\ctoa.ps1 otdeploy approve-live
.\ctoa.ps1 brain refresh
.\ctoa.ps1 brain doctor
.\ctoa.ps1 brain pack
.\ctoa.ps1 brain pack helper
```

## Fixed P10 operator refresh

`otp10refresh` runs exactly this sequence: capture-profile doctor, passive
observation preview, dependency preflight, candidate catalog, change plan with
no explicit identifiers, operator readiness, then consumer parity. Producer
stages use `--allow-blocked`, so a coherent data-only blocker is preserved and
the sequence can continue. Consumer parity runs without that override and must
finish `passed`; otherwise the command exits non-zero.

The orchestrator's own `status=passed` means that every artifact was refreshed
and consumer parity passed. It does not mean `operator_inputs_ready`: the
no-ID change-plan stage is normally blocked and readiness remains separately
visible in the summary.

The command writes the seven fixed stage files plus the strict anti-mix,
anti-replay receipt
`runtime/solteria_helper_dev/equipment_operator_refresh_run.json`. The receipt
binds one UUIDv4, ordered stage receipts, exact canonical artifact hashes,
freshness/skew checks, and the final consumer-parity hash. Failed runs clean up
only their matching pending UUID and preserve the last good completed envelope.
It does not run
`otp10`, either acceptance command, the client, or the local-profile initializer,
and it never accepts an item ID or operator confirmation. See
`docs/otclient/P10_EQUIPMENT_OPERATOR_REFRESH_RUN.md` for the fixed finalizer
contract.

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
