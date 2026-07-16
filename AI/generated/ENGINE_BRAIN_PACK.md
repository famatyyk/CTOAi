# CTOAi Engine Brain Pack

Generated at: `2026-07-16T18:27:20+00:00`
Repo root: `C:\Users\zycie\CTOAi`
Profile: `control-central`

This pack is curated and secret-safe. It excludes `.env*`, auth stores,
runtime data, logs, local databases, tokens, credentials, and generated
dependency folders. It is intended as a portable context artifact for
Codex or another code assistant.

## Included Sources


## `AI/README.md`

```markdown
# CTOAi Engine Brain

This folder is the Codex working context for the current CTOAi + OTClient lane.
It is intentionally split into small files so a model can load only the slice
needed for a task instead of relying on one long prompt.

## Load Order

1. `SYSTEM_PROMPT.md`
2. `PROJECT_CONTEXT.md`
3. `ENGINE_MEMORY.md`
4. `RULEBOOK.md`
5. The relevant index file for the task
6. The relevant persona from `SPECIALIZED_PROMPTS.md`
7. `TASK_TEMPLATE.md`

## Source Snapshot

- CTOAi repo root: `C:/Users/zycie/CTOAi`
- OTClient source tree: `scripts/lua/otclient/`
- Expanded inspection source used for this package: `.tmp/otclient_ai_source/otclient`
- Current limitation: no TFS fork source tree was included in the workspace, so
  TFS engine classes, packet handlers, and server-side protocol flow are marked
  as pending source rather than inferred.

## Files

- `SYSTEM_PROMPT.md`: primary Codex behavior for this project.
- `PROJECT_CONTEXT.md`: repo architecture and integration map.
- `ENGINE_MEMORY.md`: stable facts, decisions, and current state.
- `RULEBOOK.md`: project-specific engineering rules.
- `ARCHITECTURE_INDEX.md`: subsystem map and data flow.
- `API_INDEX.md`: CTOAi HTTP/API and local model surfaces.
- `LUA_INDEX.md`: Lua runtime modules and helper APIs.
- `OTCLIENT_INDEX.md`: OTClient native module map.
- `PACKET_INDEX.md`: protocol/packet status and known gaps.
- `CLASS_INDEX.md`: important Python/Lua classes and tables.
- `FEATURE_ROADMAP.md`: next implementation lanes.
- `P8_P16_EXECUTION_ROADMAP.md`: background-first post-P7 phase sequence and
  evidence gates through design-only Combat/CaveBot work.
- `P17_P24_HELPER_EVOLUTION_ROADMAP.md` and `.json`: post-P16 Helper
  simplification, typed rules, configurable combat surfaces, spell-state
  correctness, unified UX, shared pure contracts, and canary/rollback plan.
- `../docs/otclient/P9_CONDITIONS_SHADOW_REPLAY_DESIGN.md`: review-ready P9
  data-only observation/replay contract, still blocked by P8 operational acceptance.
- `../docs/otclient/P9_CONDITIONS_SHADOW_ACCEPTANCE.md`: strict current-evidence
  recomputation and explicit data-only operator receipt boundary; it does not
  unlock P10 or runtime actions.
- `KNOWN_BUGS.md`: known risks and suspected defects.
- `TECH_DEBT.md`: cleanup backlog.
- `SPECIALIZED_PROMPTS.md`: project-aware task personas.
- `TASK_TEMPLATE.md`: reusable task intake and delivery template.
- `OPERATIONS_AUDIT.md`: current Docker/VPN/Vercel/GitHub/extension/local gate evidence.
- `CODEX_CAPABILITY_MAP.md`: Codex surfaces and external context tools to use next.
- `ENGINE_BRAIN_STATUS.md`: completion status, risks, and remaining work.
- `generated/FILE_TREE.md`: generated secret-safe file inventory.
- `generated/SYMBOL_MAP.md`: generated lightweight symbol map.
- `generated/manifest.json`: generated index metadata.
- `generated/ENV_DOCTOR.md`: generated local operations audit summary.
- `generated/ENV_DOCTOR.json`: generated local operations audit data.
- `generated/ENGINE_BRAIN_PACK.md`: generated portable secret-safe context pack.
- `generated/ENGINE_BRAIN_PACK.json`: generated context pack manifest.
```


## `AI/generated/manifest.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-16T18:25:57+00:00",
  "root": "C:\\Users\\zycie\\CTOAi",
  "file_count": 1497,
  "outputs": {
    "file_tree": "AI\\generated\\FILE_TREE.md",
    "symbol_map": "AI\\generated\\SYMBOL_MAP.md",
    "ownership_map": "AI\\generated\\OWNERSHIP_MAP.md",
    "ownership_json": "AI\\generated\\OWNERSHIP_MAP.json",
    "doc_sync": "AI\\generated\\DOC_SYNC.md",
    "doc_sync_json": "AI\\generated\\DOC_SYNC.json",
    "secret_guardrail": "AI\\generated\\SECRET_GUARDRAIL.md",
    "secret_guardrail_json": "AI\\generated\\SECRET_GUARDRAIL.json",
    "p6_readiness": "AI\\generated\\P6_CODEX_INTEGRATION_READINESS.md",
    "p6_readiness_json": "AI\\generated\\P6_CODEX_INTEGRATION_READINESS.json",
    "p7_operator_workflow": "AI\\generated\\P7_OPERATOR_WORKFLOW.md",
    "p7_operator_workflow_json": "AI\\generated\\P7_OPERATOR_WORKFLOW.json",
    "p7_action_readiness": "AI\\generated\\P7_ACTION_READINESS.md",
    "p7_action_readiness_json": "AI\\generated\\P7_ACTION_READINESS.json",
    "p7_safe_write_tool_design": "AI\\generated\\P7_SAFE_WRITE_TOOL_DESIGN.md",
    "p7_safe_write_tool_design_json": "AI\\generated\\P7_SAFE_WRITE_TOOL_DESIGN.json",
    "p7_operator_brief": "AI\\generated\\P7_OPERATOR_BRIEF.md",
    "p7_operator_brief_json": "AI\\generated\\P7_OPERATOR_BRIEF.json"
  },
  "doc_sync_status": "passed",
  "secret_guardrail_status": "passed",
  "p6_readiness_status": "blocked",
  "p7_operator_workflow_status": "blocked",
  "p7_action_readiness_status": "safe_write_tools_enabled",
  "p7_safe_write_tool_design_status": "implemented",
  "p7_operator_brief_status": "needs_attention",
  "excluded_dirs": [
    ".git",
    ".hg",
    ".next",
    ".pytest_cache",
    ".svn",
    ".tmp",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "logs",
    "node_modules",
    "runtime"
  ],
  "excluded_file_patterns": [
    ".env-",
    ".env.",
    "credential",
    "password",
    "secret",
    "token"
  ]
}
```


## `AI/generated/ENV_DOCTOR.md`

```markdown
# Engine Brain Environment Doctor

Generated at: `2026-07-16T18:26:54+00:00`
Overall status: `warn`

| Check | Status | Key evidence |
|---|---|---|
| `git` | `ok` | branch=codex/p14-independent-runner; dirty=194; path=C:\Program Files\Git\cmd\git.EXE |
| `docker` | `ok` | containers=2; running_broad=0; configured_broad=0 |
| `vpn` | `warn` | warp_connected=False |
| `vercel` | `ok` | version=54.10.3; project=ctoa-web |
| `vscode` | `warn` | openai=['openai.chatgpt@26.707.91948']; old_dirs=2 |
| `github` | `warn` | open_prs=7; dirty_prs=5; failed_runs=0 |
| `update_gate` | `ok` | gate=ok; product=CTOA Toolkit; version=1.1.1 |

## GitHub Dirty PRs

- `#184` [WIP] Fix CTOA VPS Global Save Cycle failure - https://github.com/famatyyk/CTOAi/pull/184
- `#160` test(copilot-instructions): expand conformance coverage to all seven sections - https://github.com/famatyyk/CTOAi/pull/160
- `#157` feat: add /analyze-prompt Copilot slash command - https://github.com/famatyyk/CTOAi/pull/157
- `#153` docs: add alternative LLM model recommendations to copilot instructions and .env.example - https://github.com/famatyyk/CTOAi/pull/153
- `#152` Enable workspace-level Python trace logging in VS Code - https://github.com/famatyyk/CTOAi/pull/152
```


## `AI/generated/DOC_SYNC.md`

```markdown
# Engine Brain Doc Sync

Generated at: `2026-07-16T18:25:57+00:00`
Status: `passed`

| Check | Path | Status | Missing |
|---|---|---|---|
| `brain_cli_docs` | `docs/CTOA_CLI.md` | `passed` | - |
| `otclient_cli_docs` | `docs/CTOA_CLI.md` | `passed` | - |
| `command_dictionary_brain` | `schemas/ctoa-command-dictionary.json` | `passed` | - |
| `command_dictionary_otclient` | `schemas/ctoa-command-dictionary.json` | `passed` | - |
| `docs_index_plan3_artifacts` | `docs/INDEX.md` | `passed` | - |
| `roadmap_plan3` | `docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md` | `passed` | - |
| `roadmap_p8_p16` | `AI/P8_P16_EXECUTION_ROADMAP.md` | `passed` | - |
```


## `AI/generated/SECRET_GUARDRAIL.md`

```markdown
# Engine Brain Secret Guardrail

Generated at: `2026-07-16T18:25:57+00:00`
Status: `passed`
Sensitive/local env path count in audit: `8`

Generated Engine Brain context must not include exact local sensitive/env paths or secret contents.

| Generated path | Exact sensitive path hits |
|---|---:|
| `AI\generated\FILE_TREE.md` | 0 |
| `AI\generated\SYMBOL_MAP.md` | 0 |
| `AI\generated\OWNERSHIP_MAP.md` | 0 |
| `AI\generated\OWNERSHIP_MAP.json` | 0 |
| `AI\generated\DOC_SYNC.md` | 0 |
| `AI\generated\DOC_SYNC.json` | 0 |
```


## `AI/generated/P6_CODEX_INTEGRATION_READINESS.md`

```markdown
# P6 Codex Integration Readiness

Generated at: `2026-07-16T18:25:57+00:00`
Status: `blocked`

P6 allows only five read-only Control Central/status/cockpit tools plus audited repo-hygiene, API-cost, evidence-pack, Engine Brain, P7 cockpit-smoke, and adaptive roadmap-state safe-write refreshes. Do not add deploy/live shortcuts or bypass Control Center evidence gates.

Recommended next: Fix blocked readiness checks before creating a CTOAi plugin.

| Check | Status | Evidence |
|---|---|---|
| `ai_agents_instruction` | `passed` | AI/AGENTS.md |
| `control_central_freshness_policy` | `passed` | AI/control-central-freshness-policy.json |
| `lua_agents_instruction` | `passed` | scripts/lua/AGENTS.md |
| `engine_brain_skill_source` | `passed` | codex_home/skills/ctoa-engine-brain/SKILL.md |
| `ctoai_plugin_manifest` | `passed` | home/plugins/ctoai-engine-brain/.codex-plugin/plugin.json |
| `ctoai_plugin_brief_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_control_central_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_central.py |
| `ctoai_plugin_mcp_config` | `passed` | home/plugins/ctoai-engine-brain/.mcp.json |
| `ctoai_plugin_mcp_absolute_script` | `passed` | absolute MCP script path is runnable |
| `ctoai_plugin_mcp_server` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_operator_skill` | `passed` | home/plugins/ctoai-engine-brain/skills/ctoai-engine-brain-operator/SKILL.md |
| `ctoai_plugin_status_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_control_center_cockpit_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_evidence_io` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_evidence_io.py |
| `ctoai_plugin_freshness` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_freshness.py |
| `ctoai_plugin_helper_readiness` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_helper_readiness.py |
| `ctoai_plugin_operator_decision` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_operator_decision.py |
| `ctoai_plugin_self_check_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_p7_workflow_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p7_workflow_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_operator_brief_cockpit_handoff_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_control_center_cockpit_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_public_cockpit_projection` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `control_center_evidence_provenance_contract` | `passed` | scripts/ops/release_evidence_pack.py |
| `ctoai_plugin_evidence_artifact_hash_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_evidence_integrity_gate` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `control_center_evidence_integrity_tests` | `passed` | tests/test_ctoai_control_central.py |
| `ctoai_plugin_public_cockpit_tests` | `passed` | tests/test_ctoai_control_central.py |
| `ctoai_plugin_public_projection_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_public_projection.py |
| `ctoai_plugin_control_central_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_central.py |
| `ctoai_plugin_control_central_fault_isolation_tests` | `passed` | tests/test_ctoai_control_central.py |
| `ctoai_plugin_control_central_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_control_center_cockpit_drilldown_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_bounded_evidence_io_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_evidence_io.py |
| `ctoai_plugin_freshness_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_freshness.py |
| `ctoai_plugin_freshness_status_gate` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_freshness_cockpit_gate` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `control_central_freshness_tests` | `passed` | tests/test_ctoai_freshness.py |
| `ctoai_plugin_helper_readiness_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_helper_readiness.py |
| `ctoai_plugin_helper_recovery_projection` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_operator_decision_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_operator_decision.py |
| `control_central_helper_readiness_tests` | `passed` | tests/test_ctoai_helper_readiness.py |
| `control_central_operator_decision_tests` | `passed` | tests/test_ctoai_operator_decision.py |
| `ctoai_plugin_cache_hash_parity` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_compact_audit_status` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `full_workspace_audit_compact_summary` | `passed` | scripts/ops/ctoa_full_workspace_audit.py |
| `ctoai_plugin_bounded_evidence_io_tests` | `passed` | tests/test_ctoai_evidence_io.py |
| `ctoai_plugin_control_center_cockpit_self_check_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_p7_action_readiness_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p7_action_readiness_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_p7_safe_write_design_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p7_safe_write_design_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_repo_hygiene_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_evidence_pack_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_api_cost_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_engine_brain_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_p7_cockpit_smoke_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_roadmap_state_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_p6_handoff_smoke_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p6_handoff_smoke_cockpit_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_p6_handoff_smoke_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_p6_handoff_smoke_self_check_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_bounded_write_policy_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_p7_cockpit_smoke_contract_tests` | `passed` | tests/test_engine_brain_index.py |
| `ctoai_plugin_marketplace_entry` | `passed` | personal marketplace entry |
| `ctoai_plugin_installed_cache` | `blocked` | cache parity failed for 0.1.0+codex.20260716175808; missing=0; hash_mismatch=1 |
| `control_center_evidence_contract` | `passed` | web/src/lib/controlCenterEvidence.ts |
| `control_center_evidence_tests` | `passed` | web/src/lib/__tests__/controlCenterEvidence.test.ts |
| `control_center_p7_cockpit_smoke_script` | `passed` | scripts/ops/control_center_p7_cockpit_smoke.py |
| `control_center_p7_cockpit_smoke_tests` | `passed` | tests/test_control_center_p7_cockpit_smoke.py |
| `control_center_p7_safe_write_dry_run_smoke_script` | `passed` | scripts/ops/control_center_p7_safe_write_dry_run_smoke.py |
| `control_center_p7_safe_write_dry_run_smoke_tests` | `passed` | tests/test_control_center_p7_safe_write_dry_run_smoke.py |
| `control_center_p7_evidence_review_script` | `passed` | scripts/ops/control_center_p7_evidence_review.py |
| `control_center_p7_evidence_review_tests` | `passed` | tests/test_control_center_p7_evidence_review.py |
| `control_center_p6_plugin_handoff_smoke_script` | `passed` | scripts/ops/control_center_p6_plugin_handoff_smoke.py |
| `control_center_p6_plugin_handoff_smoke_tests` | `passed` | tests/test_control_center_p6_plugin_handoff_smoke.py |
| `control_center_safe_write_action_catalog` | `passed` | web/src/lib/controlCenterActions.ts |
| `control_center_dry_run_first_action_engine` | `passed` | web/src/lib/controlCenterActions.ts |
| `control_center_action_capability_api` | `passed` | web/src/app/api/control-center/actions/route.ts |
| `control_center_action_capability_ui` | `passed` | web/src/components/ControlCenterActionPanel.tsx |
| `control_center_action_capability_tests` | `passed` | web/src/lib/__tests__/controlCenterActions.test.ts |
| `control_center_p7_operator_brief_config` | `passed` | web/src/lib/controlCenterEvidenceConfig.ts |
| `control_center_p7_operator_brief_payload` | `passed` | web/src/lib/controlCenterEngineBrainEvidence.ts |
| `control_center_p7_operator_brief_ops` | `passed` | web/src/lib/controlCenterOps.ts |
| `control_center_p7_operator_brief_ui` | `passed` | web/src/lib/controlCenterCapabilities.ts |
| `control_center_p7_operator_brief_detail_ui` | `passed` | web/src/components/ControlCenterDetailPanels.tsx |
| `control_center_scoped_capability_runtime` | `passed` | web/src/lib/controlCenterCapabilityRuntime.ts |
| `control_center_scoped_evidence_slices` | `passed` | web/src/lib/controlCenterEvidence.ts |
| `control_center_evidence_bounded_io` | `passed` | web/src/lib/controlCenterEvidenceIo.ts |
| `control_center_evidence_domain_adapters` | `passed` | web/src/lib/controlCenterEvidenceAdapters.ts |
| `control_center_capability_adapter_tests` | `passed` | web/src/lib/__tests__/controlCenterEvidenceAdapters.test.ts |
| `control_center_engine_brain_evidence_adapter` | `passed` | web/src/lib/controlCenterEngineBrainEvidence.ts |
| `control_center_evidence_adapter_tests` | `passed` | web/src/lib/__tests__/controlCenterEngineBrainEvidence.test.ts |
| `release_evidence_pack` | `passed` | scripts/ops/release_evidence_pack.py |
| `release_evidence_p7_operator_brief` | `passed` | scripts/ops/release_evidence_pack.py |
| `full_workspace_validation_evidence` | `passed` | runtime\audits\ctoai-full-workspace-validation.json |
| `engine_brain_generated_context` | `passed` | doc_sync_status=passed; secret_guardrail_status=passed |
```


## `AI/generated/P7_OPERATOR_WORKFLOW.md`

```markdown
# P7 Operator Workflow

Generated at: `2026-07-16T18:25:57+00:00`
Status: `blocked`
Decision: `fix_p6_before_operator_workflow`

P7 operator workflow allows six audited safe_write evidence/context refresh tools. Deploy/live actions stay blocked.

Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Next safe command: Fix P6 readiness before exposing the P7 operator workflow.

## Allowed MCP Tools

| Tool | Risk | Purpose |
|---|---|---|
| `ctoai_control_central` | `read_only` | Return token-efficient brain, Control Center, plugin-management, and sites status with lane-specific drilldown. |
| `ctoai_engine_brain_status` | `read_only` | Summarize generated Engine Brain, validation, doctor, and pack status. |
| `ctoai_engine_brain_self_check` | `read_only` | Verify plugin install state and generated workspace evidence. |
| `ctoai_engine_brain_brief` | `read_only` | Return the generated P7 operator decision and next safe command. |
| `ctoai_control_center_cockpit` | `read_only` | Return read-only Control Center runtime evidence, P7 cockpit, and action-audit status. |
| `ctoai_repo_hygiene_refresh` | `safe_write` | Dry-run-first refresh of repo hygiene evidence with Control Center-compatible audit logging. |
| `ctoai_api_cost_refresh` | `safe_write` | Dry-run-first refresh of API cost evidence with Control Center-compatible audit logging. |
| `ctoai_evidence_pack_refresh` | `safe_write` | Dry-run-first refresh of release evidence with Control Center-compatible audit logging. |
| `ctoai_engine_brain_refresh` | `safe_write` | Dry-run-first refresh of Engine Brain generated context with Control Center-compatible audit logging. |
| `ctoai_p7_cockpit_smoke_refresh` | `safe_write` | Dry-run-first refresh of P7 cockpit smoke evidence with Control Center-compatible audit logging. |
| `ctoai_roadmap_state_refresh` | `safe_write` | Native dry-run-first refresh of the adaptive roadmap state with fixed inputs, fixed outputs, and hash-bound audit logging. |

## Blocked Action Classes

| Risk class | Blocked until |
|---|---|
| `guarded_write` | Risk metadata, confirmation modal, operator/owner role gate, and audit evidence exist. |
| `dangerous` | Owner-only typed confirmation, dry-run path, rollback evidence, and audit review exist. |
| `forbidden_ui` | Never expose through plugin or Control Center UI. |

## Gates Before Actions

- Every plugin tool must have a stable risk class from docs/CTOAI_COMMAND_RISK_MODEL.md.
- Every write-capable tool must be represented in Control Center action audit before enablement.
- Only ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, ctoai_p7_cockpit_smoke_refresh, and ctoai_roadmap_state_refresh may be exposed as safe_write in this wave.
- Every safe-write MCP tool must default to dry-run and append runtime/control-center/action-audit.jsonl.
- No tool may bypass PromoteLiveCtoa -ApproveLiveDeploy for Solteria Helper live promotion.
- No tool may read .env, logs, databases, runtime client state, or private Solteria client data into generated context.
- P6 readiness, P7 operator brief, release evidence pack, doc sync, and secret guardrail must all be current.
```


## `AI/generated/P7_ACTION_READINESS.md`

```markdown
# P7 Action Readiness

Generated at: `2026-07-16T18:25:57+00:00`
Status: `safe_write_tools_enabled`
Decision: `monitor_enabled_safe_write_tools`

P7 action readiness is evidence-only. MCP write tools stay disabled until every candidate has audit evidence and explicit enablement.

Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Action audit: `runtime\control-center\action-audit.jsonl` with `466` records.
MCP write tools: `6`
Next safe command: Monitor the adaptive ROADMAP_STATE and refresh it only when required P13 inputs change; pending P14 evidence must not degrade the platform.

## Safe Write Candidates

| Action | Source | Risk model | Audit | MCP allowed | Missing gates |
|---|---:|---:|---:|---:|---|
| `repo-hygiene-refresh` | `True` | `True` | `True` | `True` | `none` |
| `api-cost-refresh` | `True` | `True` | `True` | `True` | `none` |
| `evidence-pack-refresh` | `True` | `True` | `True` | `True` | `none` |
| `engine-brain-refresh` | `True` | `True` | `True` | `True` | `none` |
| `p7-cockpit-smoke-refresh` | `True` | `True` | `True` | `True` | `none` |
| `roadmap-state-refresh` | `True` | `True` | `True` | `True` | `none` |
```


## `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md`

```markdown
# P7 Safe Write Tool Design

Generated at: `2026-07-16T18:25:57+00:00`
Status: `implemented`
Decision: `ready_for_dry_run_operation`

Primary safe-write MCP design remains evidence-pack refresh; repo hygiene, API cost, and Engine Brain refreshes are allowed as additional bounded evidence/context tools. Deploy/live actions remain blocked.

Mode: `dry_run_first`
MCP enabled: `True`
Selected action: `evidence-pack-refresh`
Proposed MCP tool: `ctoai_evidence_pack_refresh`
Risk class: `safe_write`
Control Center source: `web/src/lib/controlCenterActions.ts`
Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Audit sink: `runtime/control-center/action-audit.jsonl`
Blocked reasons: `none`
Next safe command: Run ctoai_evidence_pack_refresh with dry_run=true and verify runtime/control-center/action-audit.jsonl before confirmed execution.

## Implementation Contract

- Reuse Control Center action semantics for evidence-pack-refresh or an equivalent audited runner.
- Default to dry-run before any write and expose the dry-run result in the MCP response.
- Append a sanitized action audit record before returning.
- Accept no arbitrary command, path, shell, live-deploy, or Solteria Helper promotion arguments.
- Do not read .env, logs, databases, runtime client state, or private client data into AI/generated context.
- Keep live, deploy, guarded_write, dangerous, and forbidden_ui actions out of this tool.
- Keep MCP tool listing read-only until implementation tests and audit parity pass in a later turn.

## Required Tests

- MCP tools/list still exposes only read-only tools while this design artifact is design-only.
- Dry-run call returns planned evidence-pack refresh output without mutating release artifacts.
- Real execution requires explicit safe_write intent and appends a sanitized action audit record.
- Denied or malformed arguments return blocked status without running a command.
- Release evidence and Control Center panels show the tool status without secret leakage.
```


## `AI/generated/P7_OPERATOR_BRIEF.md`

```markdown
# P7 Operator Brief

Generated at: `2026-07-16T18:25:57+00:00`
Decision: `needs_attention`
Status: `needs_attention`

Generated operator brief. Only audited repo-hygiene, API-cost, evidence-pack, Engine Brain, P7 cockpit-smoke, and roadmap-state safe_write tools are allowed; deploy/live actions remain blocked.

Next safe command: Fix hard_blockers before expanding P7 operator workflow.

## Evidence

- P6 readiness: `blocked` with `97` checks.
- P7 workflow: `blocked` with `11` MCP tools and `6` safe-write tools.
- P7 action readiness: `safe_write_tools_enabled` with `6/6` audited candidates and `6` MCP write tools.
- P7 safe-write design: `implemented` for `ctoai_evidence_pack_refresh` with MCP enabled `True`.
- P7 cockpit handoff: `ready`; smoke `14/14`; safe-write audits `6/6`; release files `35`; action audit records `466`.
- OTClient helper: `blocked`; release gate `blocked`; module contract `passed` (34/34); sandbox queue `ready_for_operator`; runtime `not_running`; first step `launch_sandbox`.
- BackgroundNoScreen: `stale`; integrity `passed`; capability `fresh`; runtime `disarmed`.
- Helper roadmap phase evidence: `p14_foundation_ready`; aligned `True`; P8/P9/P10/P11 `operational_acceptance_complete`/`operational_acceptance_complete`/`operational_acceptance_complete`/`operational_acceptance_complete`; P12 `complete`.
- P9 Conditions shadow: `stale`; contract `True`; fresh `False`; fixtures `passed`; runtime readiness `False`.
- P10 Equipment shadow: `stale`; contract `True`; fresh `False`; fixtures `passed`; rollback `ready`; runtime readiness `False`.
- P10 Equipment acceptance: `invalid`; contract `False`; fresh `False`; report bound `True`; accepted `False`; P11 eligible `False`.
- Roadmap generation: `ready`; docs `4/4`; doc sync `passed`; Plan 3 `passed`; P8-P16 `passed`.
- Validation evidence: `16` commands from `2026-07-11T19:04:23+00:00`.
- Hard blockers: `p6_readiness_status`, `p6:ctoai_plugin_installed_cache`, `p7_operator_workflow_status`.
- Warnings: `brain_doctor`, `diff_check`.
```
