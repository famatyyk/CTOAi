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
| `safe_write` | Performs a fixed, low-risk local evidence/context refresh. | repo hygiene, API cost, evidence pack, Engine Brain, P7 smoke, roadmap state and full-workspace validation | Operator-only, audited and dry-run-first; fails closed until current preflight and audit evidence pass. |
| `guarded_write` | Changes runtime state but is expected operational behavior. | restart bot, trigger controlled rebuild, enqueue known agent action | Needs confirmation and audit note. |
| `dangerous` | Can delete data, disrupt production or rewrite history. | Docker prune, delete artifacts, user deletion, deploy rollback | Requires owner role, typed confirmation and audit note. |
| `forbidden_ui` | Should not be exposed in Control Center. | arbitrary shell, secrets dump, destructive DB command | UI must not render button. |

## Current migration decisions

| Capability | Legacy source | Risk class | Control Center decision |
| --- | --- | --- | --- |
| Repo hygiene refresh | `scripts/ops/repo_hygiene_audit.py` | `safe_write` | Registered dry-run-first capability `repo-hygiene-refresh`; current preflight and audit evidence are still required. |
| API cost refresh | `scripts/ops/api_cost_report.py` | `safe_write` | Registered dry-run-first capability `api-cost-refresh`; current preflight and audit evidence are still required. |
| Evidence pack refresh | `scripts/ops/release_evidence_pack.py` | `safe_write` | Registered dry-run-first capability `evidence-pack-refresh`; current preflight and audit evidence are still required. |
| Engine Brain refresh | `scripts/ops/engine_brain_index.py` | `safe_write` | Registered dry-run-first capability `engine-brain-refresh`; current preflight and audit evidence are still required. |
| P7 cockpit smoke refresh | `scripts/ops/control_center_p7_cockpit_smoke.py` | `safe_write` | Registered dry-run-first capability `p7-cockpit-smoke-refresh`; current preflight and audit evidence are still required. |
| Roadmap state refresh | `scripts/ops/ctoai_roadmap_state.py` | `safe_write` | Registered native dry-run-first candidate `roadmap-state-refresh`; fixed inputs/outputs and hash-bound audit, with no runtime/live authority. It fails closed until current P13 source, plugin, preflight, and audit evidence validate. |
| Full workspace validation refresh | `scripts/ops/ctoa_full_workspace_validation.py` | `safe_write` | Registered native dry-run-first candidate `full-workspace-validation-refresh`; fixed registry, bounded evidence, and no deploy/live/client/promotion authority. It fails closed until current plugin, preflight, and audit evidence validate. |
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
| `safe_write` | Button label must describe the exact change. |
| `guarded_write` | Modal confirmation with target, command summary and expected effect. |
| `dangerous` | Owner role, typed confirmation, audit reason and dry-run when possible. |
| `forbidden_ui` | No UI rendering. |

## Audit model

Every `guarded_write` and `dangerous` action should record:

| Field | Meaning |
| --- | --- |
| `at` | UTC timestamp. |
| `actor` | Authenticated username. |
| `role` | Actor role. |
| `risk_class` | Risk class at execution time. |
| `action` | Stable action id. |
| `target` | Local status area, report, or audited surface. |
| `reason` | Human-entered reason or selected maintenance reason. |
| `result` | Success/failure and short output. |

Implemented audit sink:
- `runtime/control-center/action-audit.jsonl`
- includes read-only action runs too, and now also records actor role plus authorization outcome for gated actions.
- redacts common secret forms from `reason` and `output_preview` before the
  JSONL record is written; evidence drilldowns must remain sanitized as a
  second read-side guard.
- local Python-backed actions resolve executables through
  `CTOA_PYTHON_BIN` as an absolute existing path or the repo-local `.venv`
  Python. There is no PATH-only `python`/`python3` fallback; missing trusted
  Python returns an audited failed action instead of launching an ambiguous
  executable.

## Evidence flow

The evidence/reporting lane is part of the same control model:

1. Generate `runtime/api-cost/latest.json` from eval artifacts with `scripts/ops/api_cost_report.py`.
2. Generate `runtime/evidence/latest.json` and `runtime/evidence/latest.md` with `scripts/ops/release_evidence_pack.py`.
3. Record Control Center action history in `runtime/control-center/action-audit.jsonl`.
4. Surface the current state in `GET /api/control-center/evidence` and the `Evidence` tab in Control Center.

These paths are configurable through `CTOA_*` env vars in the scripts, API routes and Control Center evidence reader, so self-hosted or VPS deployments can move the runtime/evidence locations without breaking the cockpit.
The Control Center evidence endpoint also provides read-only drilldowns for
tracked release-evidence markdown files and sanitized action-audit JSONL
metadata. The action-audit drilldown intentionally avoids raw command output
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

## UI staging plan

The seven registered `safe_write` candidates share a capability engine.
Registration never marks a candidate operator-ready: current P6/P7 source,
plugin support, cockpit preflight, and audited evidence must pass independently.
1. Server-side role filtering and schema-v2 minimal projection.
2. Current P7 readiness plus trusted-runtime preflight.
3. Dry-run-first, actor-bound and time-limited execution gate.
4. Exact confirmation, maintenance reason and one-attempt proof consumption.
5. Redacted audit trail for allowed, denied and failed attempts.
6. No command text, executable path, script path or operator identity in the browser payload.
7. Missing, mismatched, stale, or failed evidence blocks the candidate without fallback.
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
