# P7 Operator Workflow

Generated at: `2026-07-11T03:56:45+00:00`
Status: `safe_write_ready`
Decision: `allow_bounded_safe_write_tools`

P7 operator workflow allows five audited safe_write evidence/context refresh tools. Deploy/live actions stay blocked.

Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Next safe command: Use ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true before any confirmed refresh.

## Allowed MCP Tools

| Tool | Risk | Purpose |
|---|---|---|
| `ctoai_engine_brain_status` | `read_only` | Summarize generated Engine Brain, validation, doctor, and pack status. |
| `ctoai_engine_brain_self_check` | `read_only` | Verify plugin install state and generated workspace evidence. |
| `ctoai_engine_brain_brief` | `read_only` | Return the generated P7 operator decision and next safe command. |
| `ctoai_control_center_cockpit` | `read_only` | Return read-only Control Center runtime evidence, P7 cockpit, and action-audit status. |
| `ctoai_repo_hygiene_refresh` | `safe_write` | Dry-run-first refresh of repo hygiene evidence with Control Center-compatible audit logging. |
| `ctoai_api_cost_refresh` | `safe_write` | Dry-run-first refresh of API cost evidence with Control Center-compatible audit logging. |
| `ctoai_evidence_pack_refresh` | `safe_write` | Dry-run-first refresh of release evidence with Control Center-compatible audit logging. |
| `ctoai_engine_brain_refresh` | `safe_write` | Dry-run-first refresh of Engine Brain generated context with Control Center-compatible audit logging. |
| `ctoai_p7_cockpit_smoke_refresh` | `safe_write` | Dry-run-first refresh of P7 cockpit smoke evidence with Control Center-compatible audit logging. |

## Blocked Action Classes

| Risk class | Blocked until |
|---|---|
| `guarded_write` | Risk metadata, confirmation modal, operator/owner role gate, and audit evidence exist. |
| `dangerous` | Owner-only typed confirmation, dry-run path, rollback evidence, and audit review exist. |
| `forbidden_ui` | Never expose through plugin or Control Center UI. |

## Gates Before Actions

- Every plugin tool must have a stable risk class from docs/CTOAI_COMMAND_RISK_MODEL.md.
- Every write-capable tool must be represented in Control Center action audit before enablement.
- Only ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh may be exposed as safe_write in this wave.
- Every safe-write MCP tool must default to dry-run and append runtime/control-center/action-audit.jsonl.
- No tool may bypass PromoteLiveCtoa -ApproveLiveDeploy for Solteria Helper live promotion.
- No tool may read .env, logs, databases, runtime client state, or private Solteria client data into generated context.
- P6 readiness, P7 operator brief, release evidence pack, doc sync, and secret guardrail must all be current.
