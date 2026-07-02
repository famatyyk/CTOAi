# CTOAi Command Risk Model

This document defines how Control Center should treat operational commands before any write action is exposed in the UI.

The goal is simple: make dangerous actions visible, understandable and gated before they become clickable.

## Core rule

No write action enters Control Center without a risk class, owner intent and confirmation model.

## Risk classes

| Risk class | Meaning | Examples | UI behavior |
| --- | --- | --- | --- |
| `read_only` | Reads state, logs, metrics or metadata. | local JSON reports, evidence packs, audit JSONL, `/api/logs` | Can auto-refresh. |
| `safe_write` | Changes local/UI preferences or low-risk state. | save endpoint profile, save dashboard preference | Needs clear label. |
| `guarded_write` | Changes runtime state but is expected operational behavior. | restart bot, trigger controlled rebuild, enqueue known agent action | Needs confirmation and audit note. |
| `dangerous` | Can delete data, disrupt production or rewrite history. | Docker prune, delete artifacts, user deletion, deploy rollback | Requires owner role, typed confirmation and audit note. |
| `forbidden_ui` | Should not be exposed in Control Center. | arbitrary shell, secrets dump, destructive DB command | UI must not render button. |

## Current migration decisions

| Capability | Legacy source | Risk class | Control Center decision |
| --- | --- | --- | --- |
| Repo hygiene refresh | `scripts/ops/repo_hygiene_audit.py` | `safe_write` | Implemented as `repo-hygiene-refresh`. |
| API cost refresh | `scripts/ops/api_cost_report.py` | `safe_write` | Implemented as `api-cost-refresh`. |
| Evidence pack refresh | `scripts/ops/release_evidence_pack.py` | `safe_write` | Implemented as `evidence-pack-refresh`. |
| Logs preview | `/api/logs` | `read_only` | Migrated. |
| Dashboard summary | `/api/dashboard` | `read_only` | Migrated. |
| Agent status | `/api/agents/status` | `read_only` | Migrated. |
| Release evidence | `/api/dashboard/release-evidence` | `read_only` | Migrated. |
| Command dictionary | `/api/commands/dictionary` | `read_only` | Migrated as preview only. |
| Command execution | `/api/command` | `dangerous` by default | Do not expose until allowlist/risk metadata is enforced. |
| One-click agent execution | `/api/agents/execution/run` | `guarded_write` | Needs confirmation and audit note. |
| Intel mission launch | `/api/agents/intel/launch` | `guarded_write` | Needs confirmation and visible input payload. |
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

## Evidence flow

The evidence/reporting lane is part of the same control model:

1. Generate `runtime/api-cost/latest.json` from eval artifacts with `scripts/ops/api_cost_report.py`.
2. Generate `runtime/evidence/latest.json` and `runtime/evidence/latest.md` with `scripts/ops/release_evidence_pack.py`.
3. Record Control Center action history in `runtime/control-center/action-audit.jsonl`.
4. Surface the current state in `GET /api/control-center/evidence` and the `Evidence` tab in Control Center.

These paths are configurable through `CTOA_*` env vars in the scripts, API routes and Control Center evidence reader, so self-hosted or VPS deployments can move the runtime/evidence locations without breaking the cockpit.

This keeps evidence visible in the cockpit before any release or guarded action is treated as complete.

## UI staging plan

1. Show read-only command dictionary.
2. Add risk labels to command dictionary entries.
3. Hide commands without risk metadata.
4. Add disabled buttons for `guarded_write` actions with "requires guardrails" labels.
5. Implement confirmation modals.
6. Implement audit trail.
7. Enable selected guarded actions one by one.

## Do not expose yet

These stay blocked until this model is implemented in code:

| Action | Reason |
| --- | --- |
| Arbitrary `/api/command` text box | Too broad and too easy to misuse. |
| Docker prune/cleanup | Can remove useful images/volumes. |
| User delete/role change | Security-sensitive. |
| One-click execution | Changes runtime state. |
| Intel launch | External side effects and runtime load. |
