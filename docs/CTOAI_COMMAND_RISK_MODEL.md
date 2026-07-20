# CTOAi Command Risk Model

This document defines how Control Center should treat operational commands before any write action is exposed in the UI.

The goal is simple: make dangerous actions visible, understandable and gated before they become clickable.

## Core rule

No write action enters Control Center without a risk class, owner intent and confirmation model.

Production startup must also fail closed: API CORS must use explicit trusted
origins, JWT secrets must be non-default, default auth-account seeding must not
run in production, and mobile-console self-registration must stay disabled
unless a registration code is configured.
API public member self-registration must also stay disabled in production unless
`CTOA_API_SELF_REGISTER_ENABLED=true` and `CTOA_API_SELF_REGISTER_CODE` are both
configured. `/api/auth/register` must never create `owner` or `operator`
accounts without an authenticated owner token, even when the auth store is
empty.

Default auth-account seeding is disabled unless `CTOA_ALLOW_SEED_ACCOUNTS=true`
is explicitly set. Control Center local seed-login must stay development-only,
localhost-only, and backed by `CTOA_SEED_*_PASSWORD` env vars outside the repo.
Production Intel launch targets must reject local/private/internal URLs unless
`CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true` is explicitly set for a trusted private
target.
Mobile-console self-registration must create only `member` accounts, and
operator endpoints must require `operator` or `owner`, not just any
authenticated session.

## Risk classes

| Risk class | Meaning | Examples | UI behavior |
| --- | --- | --- | --- |
| `read_only` | Reads state, logs, metrics or metadata. | local JSON reports, evidence packs, audit JSONL, `/api/logs` | Can auto-refresh. |
| `safe_write` | Performs a fixed, low-risk local evidence/context refresh. | repo hygiene, API cost, evidence pack, Engine Brain and P7 smoke refresh | Operator-only, audited and dry-run-first. |
| `guarded_write` | Changes runtime state but is expected operational behavior. | restart bot, trigger controlled rebuild, enqueue known agent action | Needs confirmation and audit note. |
| `dangerous` | Can delete data, disrupt production or rewrite history. | Docker prune, delete artifacts, user deletion, deploy rollback | Requires owner role, typed confirmation and audit note. |
| `forbidden_ui` | Should not be exposed in Control Center. | arbitrary shell, secrets dump, destructive DB command | UI must not render button. |

## Current migration decisions

| Capability | Legacy source | Risk class | Control Center decision |
| --- | --- | --- | --- |
| Repo hygiene refresh | `scripts/ops/repo_hygiene_audit.py` | `safe_write` | Implemented as dry-run-first capability `repo-hygiene-refresh`. |
| API cost refresh | `scripts/ops/api_cost_report.py` | `safe_write` | Implemented as dry-run-first capability `api-cost-refresh`. |
| Evidence pack refresh | `scripts/ops/release_evidence_pack.py` | `safe_write` | Implemented as dry-run-first capability `evidence-pack-refresh`. |
| Engine Brain refresh | `scripts/ops/engine_brain_index.py` | `safe_write` | Implemented as dry-run-first capability `engine-brain-refresh`. |
| P7 cockpit smoke refresh | `scripts/ops/control_center_p7_cockpit_smoke.py` | `safe_write` | Implemented as dry-run-first capability `p7-cockpit-smoke-refresh`. |
| Roadmap state refresh | `scripts/ops/ctoai_roadmap_state.py` | `safe_write` | Enabled as native dry-run-first capability `roadmap-state-refresh`; fixed inputs/outputs, exact confirmation, hash-bound audit, and no runtime/live authority. |
| Logs preview | `/api/logs` | `read_only` | Migrated. |
| Dashboard summary | `/api/dashboard` | `read_only` | Migrated. |
| Agent status | `/api/agents/status` | `read_only` | Migrated. |
| Release evidence | `/api/dashboard/release-evidence` | `read_only` | Migrated. |
| Command dictionary | `/api/commands/dictionary` | `read_only` | Migrated as preview only. |
| Command execution | `/api/command` | `dangerous` by default | Do not expose until allowlist/risk metadata is enforced. |
| One-click agent execution | `/api/agents/execution/run` | `guarded_write` | Owner-only; requires `confirm=true` and audit `reason` before runtime side effects. |
| Intel mission launch | `/api/agents/intel/launch` | `guarded_write` | Owner-only; requires `confirm=true`, audit `reason`, visible input payload, and production private-target guardrails. |
| Intel client sync | `CTOA_CLIENT_SYNC_ENABLED` via `/api/agents/intel/run` | `guarded_write` | Must keep target, autoloader, and init-file writes inside `CTOA_CLIENT_SCRIPTS_DIR`. |
| User role/password/delete | `/api/users/*` | `dangerous` | Owner-only admin panel with typed confirmation. |
| Docker cleanup | VPS Docker commands | `dangerous` | Owner-only, typed confirmation, dry-run first. |
| Bot restart | Docker/service restart | `guarded_write` | Confirmation and live status check before/after. |

## Confirmation model

| Risk class | Confirmation |
| --- | --- |
| `read_only` | None. |
| `safe_write` | Operator role, current P7 registration, trusted runtime, successful actor-bound dry-run no older than 15 minutes, exact typed confirmation and an audit reason of at least 8 characters. The execution attempt consumes the dry-run proof. |
| `guarded_write` | Modal confirmation with target, command summary and expected effect. |
| `dangerous` | Owner role, typed confirmation, audit reason and dry-run when possible. |
| `forbidden_ui` | No UI rendering. |

## Audit model

Every `safe_write`, `guarded_write` and `dangerous` attempt records:

| Field | Meaning |
| --- | --- |
| `at` | UTC timestamp. |
| `actor` | Authenticated username. |
| `actor_role` | Actor role. |
| `risk_class` | Risk class at execution time. |
| `action` | Stable action id. |
| `target` | Local status area, report, or audited surface. |
| `reason` | Human-entered reason or selected maintenance reason. |
| `dry_run` | Whether the request validated only or attempted execution. |
| `authorized` | Whether role policy allowed the attempt. |
| `ok` | Success/failure. |
| `output_preview` | Bounded, redacted result summary. |

Implemented audit sink:
- `runtime/control-center/action-audit.jsonl`
- records dry-runs, denied requests, failed confirmation/preflight gates and execution attempts with unique audit ids.
- redacts common secret forms from `reason` and `output_preview` before the
  JSONL record is written; evidence drilldowns must remain sanitized as a
  second read-side guard.
- local Python-backed actions resolve executables through
  `CTOA_PYTHON_BIN` as an absolute existing path or the repo-local `.venv`
  Python. There is no PATH-only `python`/`python3` fallback; missing trusted
  Python blocks preflight and writes a redacted failed audit record instead of
  launching an ambiguous executable.
- the browser capability projection contains effect/evidence metadata and
  preflight checks only. It does not contain command strings, executable paths,
  script paths, usernames or display names.

## Evidence flow

The evidence/reporting lane is part of the same control model:

1. Generate `runtime/api-cost/latest.json` from eval artifacts with `scripts/ops/api_cost_report.py`.
2. Generate `runtime/evidence/latest.json` and `runtime/evidence/latest.md` with `scripts/ops/release_evidence_pack.py`.
3. Record Control Center action history in `runtime/control-center/action-audit.jsonl`.
4. Surface only the bounded summary from `GET /api/control-center/ops?view=summary`; request one allowlisted detail with `GET /api/control-center/ops?view=detail&capability=<id>`.

These paths are configurable through `CTOA_*` env vars in the scripts, API routes and Control Center evidence reader, so self-hosted or VPS deployments can move the runtime/evidence locations without breaking the cockpit.
The scoped Control Center ops endpoint provides read-only drilldowns for
tracked release-evidence metadata and sanitized action-audit JSONL metadata.
Its evidence boundary is physical, not only a response filter: bounded file I/O,
release/audit/API/repo adapters and Engine Brain collection live in separate
modules. Scoped slice types do not carry filesystem paths, audit identifiers,
operator identity or role, maintenance reasons, raw output, prompt names or
command strings, so those fields cannot be reintroduced by a later projector.
The local `ctoai_control_central` plugin uses the same rule in schema v2:
`detail=full` requires one selected lane, is capped at 6000 compact JSON
characters, and returns an allowlisted projection rather than the source
payload. `profile=all&detail=full` is rejected. Each lane is collected through
an isolated failure boundary, so one broken probe becomes a stable lane error
code instead of hanging or failing the whole Control Central response; bounded
timings identify slow lanes without exposing exception text.
Helper warnings use stable blocker codes and a semantic next-step enum. Raw
client paths, runtime blocker prose and launch commands remain outside the
Control Central contract.
The top-level operator recommendation uses `evidence-priority-v1`. It ranks a
bounded set of semantic candidates instead of returning the first hard-coded
lane. A time-limited confirmed P7 proof may outrank ordinary maintenance; a
verified P14 runner handoff outranks design-only P7 work; and up to three safe
alternatives remain visible. Live mutation, authority grants and automatic
execution are never selectable by this decision model. Unknown actions or
authority drift fail closed to read-only review.
The retired `/api/control-center/evidence` route returns migration metadata and
never a full evidence export. The action-audit drilldown intentionally avoids raw command output
previews so the cockpit can review action shape, risk, authorization and result
without copying command logs into the UI payload. Oversized action-audit JSONL
is read as a bounded, redacted tail sample and reported as `warn` with sample
metadata, rather than loading the whole runtime log into memory.
`GET /api/control-center/ops` mirrors those drilldowns into the Overview and
Local Status detail panels. Its legacy `recentActions` fallback must also
redact common token forms before returning action metadata.
It also compares the current runtime evidence pack with the latest tracked
release-evidence markdown so stale sign-off state is visible without adding a
write action.
The Helper evidence surface includes `CTOA_HELPER_LIVE_PROMOTION_PATH`, which
is read-only and points to `runtime/solteria_helper_dev/live_promotion.json`
by default. Control Center may display that live-promotion evidence, but it
must not run live deploy shortcuts or bypass `PromoteLiveCtoa -ApproveLiveDeploy`.
`CTOA_HELPER_BACKGROUND_STATUS_PATH` points to the advisory-only
`runtime/solteria_helper_dev/background_status.json`. Its producer runs only as
`BackgroundStatus -OperatorMode BackgroundNoScreen`: a positive allowlist blocks
every other wrapper action, child processes cannot downgrade the mode, and the
result always keeps `promotion_allowed=false` and `dispatch_allowed=false`.
The action may read bounded heartbeat/log/process/hash state and write the
repo-local report. Hash reads are restricted to bounded Helper paths from an
officially promoted manifest. Readiness requires one canonical live process,
an explicit online post-start heartbeat, explicit false runtime-action claims,
and a promotion record whose manifest SHA256 matches. The observer cannot
create that trust anchor. It may not send input, focus/capture a window,
start/stop a client, write a smoke command, or change live files. Drift in a
vocation profile remains blocking while that profile is executable Lua.
`CTOA_HELPER_CONDITIONS_SHADOW_REPLAY_PATH` points to the read-only Control
Center input `runtime/solteria_helper_dev/conditions_shadow_replay.json`. Only
`ctoa.ps1 otp9` may refresh it, after collecting bounded `BackgroundNoScreen`
evidence. The replay is data-only: fixture success is reported separately from
operational acceptance, every action/dispatch/execute/promotion flag remains
false, and malformed, stale, untrusted, or hash-inconsistent inputs fail closed.

This keeps evidence visible in the cockpit before any release or guarded action is treated as complete.

Legacy mobile-console `/api/command` remains outside the Control Center write
surface. Its command audit records must redact common secret forms before
writing `logs/mobile-console-audit.log`, but this is a leak-reduction guard, not
permission to expose arbitrary shell execution in Control Center.
Those records should include actor, role, auth mode and auth transport, while
never persisting session tokens or CSRF tokens.
Safe-mode mobile-console presets execute through backend-owned `argv/cwd/env`
specifications instead of raw shell snippets. This keeps allowlisted legacy
commands deterministic. `CTOA_MOBILE_FULL_ACCESS=true` must not re-enable
arbitrary command text execution through the HTTP endpoint; non-preset command
text stays blocked.
Health/auto-check payloads should report `command_mode=presets`, and legacy
mobile or desktop UIs should not render arbitrary full-command entry points.
Legacy mobile and desktop Intel guarded writes now require explicit confirmation
and a non-empty audit reason before database writes, orchestrator triggers, or
client sync can run. Denied attempts are audited as missing confirmation.

## UI staging status

The six selected `safe_write` capabilities are complete as a capability engine:

1. Server-side role filtering and schema-v2 minimal projection.
2. Current P7 readiness plus trusted-runtime preflight.
3. Dry-run-first, actor-bound and time-limited execution gate.
4. Exact confirmation, maintenance reason and one-attempt proof consumption.
5. Redacted audit trail for allowed, denied and failed attempts.
6. No command text, executable path, script path or operator identity in the browser payload.

`guarded_write` and `dangerous` actions remain outside this surface. They are
enabled one by one only after their own rollback, target-state and audit
contracts exist.

## Do not expose yet

These stay blocked until this model is implemented in code:

| Action | Reason |
| --- | --- |
| Arbitrary `/api/command` text box | Too broad and too easy to misuse. |
| Docker prune/cleanup | Can remove useful images/volumes. |
| User delete/role change | Security-sensitive. |
| One-click execution in Control Center | Changes runtime state; Control Center write UI is still disabled until its guarded-action modal/audit lane is enabled. |
| Intel launch in Control Center | External side effects and runtime load; Control Center write UI is still disabled until its guarded-action modal/audit lane is enabled. |
