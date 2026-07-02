# CTOAi Command Risk Model

This document defines how Control Center should treat operational commands before any write action is exposed in the UI.

The goal is simple: make dangerous actions visible, understandable and gated before they become clickable.

## Core rule

No write action enters Control Center without a risk class, owner intent and confirmation model.

## Risk classes

| Risk class | Meaning | Examples | UI behavior |
| --- | --- | --- | --- |
| `read_only` | Reads state, logs, metrics or metadata. | `df -h /`, `docker ps`, `gh run list`, `/api/logs` | Can auto-refresh. |
| `safe_write` | Changes local/UI preferences or low-risk state. | save endpoint profile, save dashboard preference | Needs clear label. |
| `guarded_write` | Changes runtime state but is expected operational behavior. | restart bot, trigger controlled rebuild, enqueue known agent action | Needs confirmation and audit note. |
| `dangerous` | Can delete data, disrupt production or rewrite history. | Docker prune, delete artifacts, user deletion, deploy rollback | Requires owner role, typed confirmation and audit note. |
| `forbidden_ui` | Should not be exposed in Control Center. | arbitrary shell, secrets dump, destructive DB command | UI must not render button. |

## Current migration decisions

| Capability | Legacy source | Risk class | Control Center decision |
| --- | --- | --- | --- |
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
| `target` | VPS, Docker service, GitHub repo, user, etc. |
| `reason` | Human-entered reason or selected maintenance reason. |
| `result` | Success/failure and short output. |

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

