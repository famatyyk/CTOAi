# P6 Codex Integration Readiness

Generated at: `2026-07-21T08:27:41+00:00`
Status: `ready_for_plugin_design`

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
| `ctoai_plugin_installed_cache` | `passed` | installed personal cache version 0.1.0+codex.20260717215814 |
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
