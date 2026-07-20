from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys

import pytest

from scripts.ops import engine_brain_index
from scripts.ops.engine_brain_index import build_indexes


PLUGIN_ROOT = engine_brain_index.Path.home() / "plugins" / "ctoai-engine-brain"
requires_engine_brain_plugin = pytest.mark.skipif(
    not PLUGIN_ROOT.exists(), reason="Engine Brain operator plugin is not installed"
)


def _load_plugin_module(name, path):
    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ADAPTIVE_OPERATOR_EXPECTATIONS = {
    "harden_p14_environment": {
        "status": "awaiting_external",
        "availability": "awaiting_external",
        "lane": "p14-environment-approval",
        "risk_class": "guarded_write",
        "interaction": "external_config",
        "title": "Configure P14 environment approval",
    },
    "refresh_p14_independent_runner_evidence": {
        "status": "awaiting_external",
        "availability": "awaiting_external",
        "lane": "p14-independent-runner",
        "risk_class": "safe_write",
        "interaction": "external_runner",
        "title": "Refresh independent P14 runner evidence",
    },
    "prepare_independent_runner_request": {
        "status": "awaiting_external",
        "availability": "awaiting_external",
        "lane": "p14-independent-runner",
        "risk_class": "safe_write",
        "interaction": "external_runner",
        "title": "Prepare independent P14 runner request",
    },
    "verify_independent_runner_result": {
        "status": "awaiting_external",
        "availability": "awaiting_external",
        "lane": "p14-independent-runner",
        "risk_class": "read_only",
        "interaction": "external_runner",
        "title": "Verify independent P14 runner result",
    },
    "refresh_local_gates": {
        "status": "action_required",
        "availability": "available",
        "lane": "helper-local-validation",
        "risk_class": "safe_write",
        "interaction": "none",
        "title": "Refresh Helper local gates",
    },
}


def _assert_adaptive_operator(operator, *, public):
    action = operator["action_id"]
    assert action in ADAPTIVE_OPERATOR_EXPECTATIONS
    expected = ADAPTIVE_OPERATOR_EXPECTATIONS[action]
    for field, value in expected.items():
        assert operator[field] == value
    assert operator["decision_policy"] == "evidence-priority-v1"
    assert operator["auto_executable"] is False
    assert operator["mutates_live"] is False
    assert operator["grants_authority"] is False
    alternatives = [item["action_id"] for item in operator["alternatives"]]
    assert len(alternatives) == len(set(alternatives))
    assert 1 <= len(alternatives) <= 3
    assert set(alternatives).issubset(
        {
            "design_roadmap_state_refresh_contract",
            "refresh_local_gates",
            "refresh_sandbox_evidence",
            "refresh_runtime_gate",
            "continue_static_work",
            "monitor_adaptive_roadmap_state",
            "review_external_evidence",
            "review_helper_readiness",
            "review_release_evidence",
        }
    )
    assert not any("live" in item or "promote" in item for item in alternatives)
    if public:
        assert "command" not in operator
        assert "source_path" not in operator
    else:
        assert operator["command"] == ""
        assert operator["source_path"] == "runtime/evidence/latest.json"


def _write_roadmap_generation_docs(root):
    for config in engine_brain_index.ROADMAP_GENERATION_DOCS.values():
        path = root / str(config["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(config["needles"]) + "\n", encoding="utf-8")


def _roadmap_doc_sync_payload(
    *, overall_status="passed", plan3_status="passed", p8_p16_status="passed"
):
    return {
        "status": overall_status,
        "checks": [
            {"name": "roadmap_plan3", "status": plan3_status},
            {"name": "roadmap_p8_p16", "status": p8_p16_status},
        ],
    }


@pytest.mark.parametrize(
    ("overall_status", "plan3_status", "p8_p16_status", "expected_blocker"),
    [
        ("blocked", "passed", "passed", "doc_sync_status"),
        ("passed", "blocked", "passed", "doc_sync:roadmap_plan3"),
        ("passed", "passed", "blocked", "doc_sync:roadmap_p8_p16"),
    ],
)
def test_roadmap_generation_requires_all_doc_sync_gates(
    tmp_path,
    monkeypatch,
    overall_status,
    plan3_status,
    p8_p16_status,
    expected_blocker,
):
    _write_roadmap_generation_docs(tmp_path)
    monkeypatch.setattr(engine_brain_index, "ROOT", tmp_path)

    payload = engine_brain_index.build_roadmap_generation_payload(
        "2099-01-01T00:00:00+00:00",
        _roadmap_doc_sync_payload(
            overall_status=overall_status,
            plan3_status=plan3_status,
            p8_p16_status=p8_p16_status,
        ),
    )

    assert payload["status"] == "blocked"
    assert expected_blocker in payload["hard_blockers"]
    assert payload["doc_sync_status"] == overall_status
    assert payload["doc_sync_roadmap_plan3_status"] == plan3_status
    assert payload["doc_sync_roadmap_p8_p16_status"] == p8_p16_status


def test_roadmap_generation_blocks_current_phase_marker_drift(tmp_path, monkeypatch):
    _write_roadmap_generation_docs(tmp_path)
    monkeypatch.setattr(engine_brain_index, "ROOT", tmp_path)
    roadmap_path = tmp_path / "AI" / "P8_P16_EXECUTION_ROADMAP.md"
    required_marker = (
        "Conditions and Equipment lanes are `operational_acceptance_complete`"
    )
    roadmap_path.write_text(
        roadmap_path.read_text(encoding="utf-8").replace(
            required_marker, "Conditions and Equipment lanes remain under review"
        ),
        encoding="utf-8",
    )

    payload = engine_brain_index.build_roadmap_generation_payload(
        "2099-01-01T00:00:00+00:00", _roadmap_doc_sync_payload()
    )

    assert payload["status"] == "blocked"
    assert (
        f"missing_marker:AI/P8_P16_EXECUTION_ROADMAP.md:{required_marker}"
        in payload["hard_blockers"]
    )
    p8_doc = next(
        item for item in payload["docs"] if item["name"] == "p8_p16_execution_roadmap"
    )
    assert p8_doc["status"] == "blocked"
    assert required_marker in p8_doc["missing_markers"]


def test_roadmap_generation_accepts_markdown_line_wrapping(tmp_path, monkeypatch):
    _write_roadmap_generation_docs(tmp_path)
    monkeypatch.setattr(engine_brain_index, "ROOT", tmp_path)

    status_path = tmp_path / "AI" / "ENGINE_BRAIN_STATUS.md"
    status_path.write_text(
        status_path.read_text(encoding="utf-8").replace(
            "session and execution approvals remain false",
            "session and execution\napprovals remain false",
        ),
        encoding="utf-8",
    )
    roadmap_path = tmp_path / "AI" / "P8_P16_EXECUTION_ROADMAP.md"
    roadmap_path.write_text(
        roadmap_path.read_text(encoding="utf-8").replace(
            "no sandbox client process is running",
            "no sandbox client process\nis running",
        ),
        encoding="utf-8",
    )

    payload = engine_brain_index.build_roadmap_generation_payload(
        "2099-01-01T00:00:00+00:00", _roadmap_doc_sync_payload()
    )

    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert payload["ready_doc_count"] == payload["doc_count"]


def test_release_evidence_summary_exposes_helper_sandbox_queue(tmp_path):
    release_root = tmp_path / "releases" / "evidence"
    sprint_dir = release_root / "sprint-999"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "CTOA-999.md").write_text("# Evidence\n", encoding="utf-8")
    latest_path = tmp_path / "runtime" / "evidence" / "latest.json"
    latest_path.parent.mkdir(parents=True)
    latest_path.write_text(
        json.dumps(
            {
                "generated_at_utc": "2099-01-01T00:00:00+00:00",
                "otclient_helper": {
                    "status": "blocked",
                    "release_gate_status": "blocked",
                    "next_action": "Run SmokeAttachModules after sandbox character is in-world.",
                    "module_contract": {
                        "status": "passed",
                        "passed_count": 16,
                        "check_count": 16,
                        "forbidden_count": 0,
                    },
                    "conditions_shadow": {
                        "status": "operational_acceptance_blocked",
                        "contract_valid": True,
                        "fresh": True,
                        "fixture_validation_status": "passed",
                        "fixture_only_validation_passed": True,
                        "runtime_readiness_claimed": False,
                    },
                    "equipment_shadow": {
                        "status": "operational_acceptance_blocked",
                        "contract_valid": True,
                        "fresh": True,
                        "fixture_validation_status": "passed",
                        "rollback_simulation": "blocked",
                        "runtime_readiness_claimed": False,
                    },
                    "equipment_shadow_acceptance": {
                        "status": "blocked",
                        "contract_valid": True,
                        "fresh": True,
                        "report_hash_match": True,
                        "acceptance_granted": False,
                        "p11_predecessor_eligible": False,
                        "runtime_readiness_claimed": False,
                    },
                    "roadmap_phase_state": {
                        "status": "p12_in_progress",
                        "aligned_with_current_roadmap": True,
                        "p8": "operational_acceptance_complete",
                        "p9": "operational_acceptance_complete",
                        "p10": "operational_acceptance_complete",
                        "p11": "operational_acceptance_complete",
                        "p12": {
                            "status": "in_progress",
                            "conditions": {"status": "operational_acceptance_complete"},
                            "equipment": {
                                "status": "operational_acceptance_blocked",
                                "current_plan_status": "blocked",
                                "attempt_count": 0,
                            },
                            "heal_friend": {"status": "not_started"},
                        },
                    },
                    "sandbox_smoke_queue": {
                        "status": "ready_for_operator",
                        "runtime_status": "not_running",
                        "next_action": "Launch sandbox client and enter test character",
                        "required_count": 5,
                        "queued_count": 4,
                        "next_steps": [{"step_id": "launch_sandbox"}],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    summary = engine_brain_index.read_release_evidence_summary(
        release_root, latest_path
    )

    assert summary["status"] == "ready"
    assert summary["file_count"] == 1
    assert summary["otclient_helper_status"] == "blocked"
    assert summary["otclient_helper_release_gate_status"] == "blocked"
    assert summary["otclient_helper_module_contract"]["status"] == "passed"
    assert summary["otclient_helper_module_contract"]["passed_count"] == 16
    assert summary["otclient_helper_module_contract"]["check_count"] == 16
    assert summary["otclient_helper_module_contract"]["forbidden_count"] == 0
    assert summary["otclient_helper_conditions_shadow"] == {
        "status": "operational_acceptance_blocked",
        "contract_valid": True,
        "fresh": True,
        "fixture_validation_status": "passed",
        "fixture_only_validation_passed": True,
        "runtime_readiness_claimed": False,
    }
    assert summary["otclient_helper_equipment_shadow"] == {
        "status": "operational_acceptance_blocked",
        "contract_valid": True,
        "fresh": True,
        "fixture_validation_status": "passed",
        "rollback_simulation": "blocked",
        "runtime_readiness_claimed": False,
    }
    assert summary["otclient_helper_equipment_acceptance"] == {
        "status": "blocked",
        "contract_valid": True,
        "fresh": True,
        "report_hash_match": True,
        "acceptance_granted": False,
        "p11_predecessor_eligible": False,
        "runtime_readiness_claimed": False,
    }
    assert summary["otclient_helper_roadmap_phase_state"]["status"] == (
        "p12_in_progress"
    )
    assert (
        summary["otclient_helper_roadmap_phase_state"]["aligned_with_current_roadmap"]
        is True
    )
    assert summary["otclient_helper_roadmap_phase_state"]["p12"]["equipment"] == {
        "status": "operational_acceptance_blocked",
        "current_plan_status": "blocked",
        "attempt_count": 0,
    }
    assert summary["sandbox_smoke_queue"]["status"] == "ready_for_operator"
    assert summary["sandbox_smoke_queue"]["first_step"] == "launch_sandbox"


def test_engine_brain_index_writes_secret_safe_outputs(tmp_path):
    payload = build_indexes(tmp_path)

    file_tree = tmp_path / "FILE_TREE.md"
    symbol_map = tmp_path / "SYMBOL_MAP.md"
    ownership_map = tmp_path / "OWNERSHIP_MAP.md"
    doc_sync = tmp_path / "DOC_SYNC.md"
    secret_guardrail = tmp_path / "SECRET_GUARDRAIL.md"
    p6_readiness = tmp_path / "P6_CODEX_INTEGRATION_READINESS.md"
    p6_readiness_json = tmp_path / "P6_CODEX_INTEGRATION_READINESS.json"
    p7_operator_workflow = tmp_path / "P7_OPERATOR_WORKFLOW.md"
    p7_operator_workflow_json = tmp_path / "P7_OPERATOR_WORKFLOW.json"
    p7_action_readiness = tmp_path / "P7_ACTION_READINESS.md"
    p7_action_readiness_json = tmp_path / "P7_ACTION_READINESS.json"
    p7_safe_write_tool_design = tmp_path / "P7_SAFE_WRITE_TOOL_DESIGN.md"
    p7_safe_write_tool_design_json = tmp_path / "P7_SAFE_WRITE_TOOL_DESIGN.json"
    p7_operator_brief = tmp_path / "P7_OPERATOR_BRIEF.md"
    p7_operator_brief_json = tmp_path / "P7_OPERATOR_BRIEF.json"
    manifest = tmp_path / "manifest.json"

    assert file_tree.exists()
    assert symbol_map.exists()
    assert ownership_map.exists()
    assert doc_sync.exists()
    assert secret_guardrail.exists()
    assert p6_readiness.exists()
    assert p6_readiness_json.exists()
    assert p7_operator_workflow.exists()
    assert p7_operator_workflow_json.exists()
    assert p7_action_readiness.exists()
    assert p7_action_readiness_json.exists()
    assert p7_safe_write_tool_design.exists()
    assert p7_safe_write_tool_design_json.exists()
    assert p7_operator_brief.exists()
    assert p7_operator_brief_json.exists()
    assert manifest.exists()
    brief_text = p7_operator_brief.read_text(encoding="utf-8")
    assert "- OTClient helper:" in brief_text
    assert "module contract" in brief_text
    assert "sandbox queue" in brief_text
    assert "first step" in brief_text
    assert payload["file_count"] > 0
    assert payload["doc_sync_status"] == "passed"
    assert payload["secret_guardrail_status"] == "passed"

    tree_text = file_tree.read_text(encoding="utf-8")
    assert ".env`" not in tree_text
    assert "node_modules" in tree_text
    assert "scripts/ops/engine_brain_index.py" in tree_text

    symbols_text = symbol_map.read_text(encoding="utf-8")
    assert "build_indexes" in symbols_text
    assert "Engine Brain Ownership Map" in ownership_map.read_text(encoding="utf-8")
    assert "Engine Brain Doc Sync" in doc_sync.read_text(encoding="utf-8")
    assert "Engine Brain Secret Guardrail" in secret_guardrail.read_text(
        encoding="utf-8"
    )
    assert "P6 Codex Integration Readiness" in p6_readiness.read_text(encoding="utf-8")
    assert "P7 Operator Workflow" in p7_operator_workflow.read_text(encoding="utf-8")
    assert "P7 Action Readiness" in p7_action_readiness.read_text(encoding="utf-8")
    assert "P7 Safe Write Tool Design" in p7_safe_write_tool_design.read_text(
        encoding="utf-8"
    )
    assert "P7 Operator Brief" in p7_operator_brief.read_text(encoding="utf-8")
    assert "P10 Equipment shadow" in p7_operator_brief.read_text(encoding="utf-8")
    assert "P10 Equipment acceptance" in p7_operator_brief.read_text(encoding="utf-8")
    p6_payload = json.loads(p6_readiness_json.read_text(encoding="utf-8"))
    p6_check_names = {check["name"] for check in p6_payload["checks"]}
    assert {
        "control_center_p7_operator_brief_config",
        "control_center_p7_operator_brief_payload",
        "control_center_p7_operator_brief_ops",
        "control_center_p7_operator_brief_ui",
        "control_center_p7_operator_brief_detail_ui",
        "control_center_scoped_capability_runtime",
        "control_center_scoped_evidence_slices",
        "control_center_evidence_bounded_io",
        "control_center_evidence_domain_adapters",
        "control_center_capability_adapter_tests",
        "control_center_engine_brain_evidence_adapter",
        "control_center_evidence_adapter_tests",
        "control_center_p7_cockpit_smoke_script",
        "control_center_p7_cockpit_smoke_tests",
        "control_center_p7_safe_write_dry_run_smoke_script",
        "control_center_p7_safe_write_dry_run_smoke_tests",
        "control_center_p7_evidence_review_script",
        "control_center_p7_evidence_review_tests",
        "control_center_safe_write_action_catalog",
        "control_center_dry_run_first_action_engine",
        "control_center_action_capability_api",
        "control_center_action_capability_ui",
        "control_center_action_capability_tests",
        "ctoai_plugin_control_center_cockpit_mcp_contract",
        "ctoai_plugin_public_cockpit_projection",
        "ctoai_plugin_public_cockpit_tests",
        "ctoai_plugin_public_projection_contract",
        "control_center_evidence_provenance_contract",
        "ctoai_plugin_evidence_artifact_hash_contract",
        "ctoai_plugin_evidence_integrity_gate",
        "control_center_evidence_integrity_tests",
        "control_central_freshness_policy",
        "ctoai_plugin_freshness",
        "ctoai_plugin_freshness_contract",
        "ctoai_plugin_freshness_status_gate",
        "ctoai_plugin_freshness_cockpit_gate",
        "control_central_freshness_tests",
        "ctoai_plugin_helper_readiness",
        "ctoai_plugin_helper_readiness_contract",
        "ctoai_plugin_helper_recovery_projection",
        "control_central_helper_readiness_tests",
        "ctoai_plugin_operator_decision",
        "ctoai_plugin_operator_decision_contract",
        "control_central_operator_decision_tests",
        "ctoai_plugin_control_center_cockpit_drilldown_contract",
        "ctoai_plugin_control_center_cockpit_self_check_contract",
        "ctoai_plugin_control_center_cockpit_script",
        "ctoai_plugin_evidence_io",
        "ctoai_plugin_bounded_evidence_io_contract",
        "ctoai_plugin_bounded_evidence_io_tests",
        "ctoai_plugin_cache_hash_parity",
        "ctoai_plugin_compact_audit_status",
        "full_workspace_audit_compact_summary",
        "ctoai_plugin_control_central_contract",
        "ctoai_plugin_control_central_mcp_contract",
        "ctoai_plugin_control_central_script",
        "ctoai_plugin_control_central_fault_isolation_tests",
        "ctoai_plugin_mcp_absolute_script",
        "ctoai_plugin_operator_brief_cockpit_handoff_contract",
        "ctoai_plugin_p7_cockpit_smoke_contract_tests",
        "ctoai_plugin_p7_action_readiness_status_contract",
        "ctoai_plugin_p7_action_readiness_brief_contract",
        "ctoai_plugin_p7_safe_write_design_status_contract",
        "ctoai_plugin_p7_safe_write_design_brief_contract",
        "ctoai_plugin_p7_workflow_status_contract",
        "ctoai_plugin_p7_workflow_brief_contract",
        "ctoai_plugin_engine_brain_refresh_mcp_contract",
        "ctoai_plugin_p7_cockpit_smoke_refresh_mcp_contract",
        "ctoai_plugin_roadmap_state_refresh_mcp_contract",
        "release_evidence_p7_operator_brief",
    }.issubset(p6_check_names)
    workflow_payload = json.loads(p7_operator_workflow_json.read_text(encoding="utf-8"))
    assert workflow_payload["status"] in {"safe_write_ready", "blocked"}
    assert workflow_payload["decision"] in {
        "allow_bounded_safe_write_tools",
        "fix_p6_before_operator_workflow",
    }
    assert "six audited safe_write" in workflow_payload["policy"]
    assert [tool["name"] for tool in workflow_payload["allowed_mcp_tools"]] == [
        "ctoai_control_central",
        "ctoai_engine_brain_status",
        "ctoai_engine_brain_self_check",
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
        "ctoai_repo_hygiene_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
        "ctoai_roadmap_state_refresh",
    ]
    assert (
        "repo-hygiene, API-cost, evidence-pack, Engine Brain, P7 cockpit-smoke, and adaptive roadmap-state"
        in p6_payload["policy"]
    )
    if "Fix blocked readiness checks" in p6_payload["recommended_next"]:
        assert "Fix blocked readiness checks" in p6_payload["recommended_next"]
    else:
        assert (
            "repo-hygiene, API-cost, evidence-pack, Engine Brain, P7 cockpit-smoke, and adaptive roadmap-state"
            in p6_payload["recommended_next"]
        )
    assert [tool["risk_class"] for tool in workflow_payload["allowed_mcp_tools"]] == [
        "read_only",
        "read_only",
        "read_only",
        "read_only",
        "read_only",
        "safe_write",
        "safe_write",
        "safe_write",
        "safe_write",
        "safe_write",
        "safe_write",
    ]
    assert {
        item["risk_class"] for item in workflow_payload["blocked_action_classes"]
    } == {
        "guarded_write",
        "dangerous",
        "forbidden_ui",
    }
    action_readiness_payload = json.loads(
        p7_action_readiness_json.read_text(encoding="utf-8")
    )
    assert action_readiness_payload["status"] in {
        "write_tools_blocked",
        "first_safe_write_enabled",
        "safe_write_tools_enabled",
        "unsafe_write_tools_present",
    }
    assert action_readiness_payload["decision"] in {
        "collect_control_center_action_audit_evidence",
        "ready_to_design_first_safe_write_tool",
        "monitor_first_safe_write_tool",
        "monitor_enabled_safe_write_tools",
        "remove_unexpected_mcp_write_tools",
    }
    assert action_readiness_payload["candidate_count"] == 6
    assert action_readiness_payload["mcp_write_tool_count"] in {0, 1, 2, 3, 4, 5, 6}
    assert [
        candidate["id"]
        for candidate in action_readiness_payload["safe_write_candidates"]
    ] == [
        "repo-hygiene-refresh",
        "api-cost-refresh",
        "evidence-pack-refresh",
        "engine-brain-refresh",
        "p7-cockpit-smoke-refresh",
        "roadmap-state-refresh",
    ]
    allowed_candidates = [
        candidate["id"]
        for candidate in action_readiness_payload["safe_write_candidates"]
        if candidate["plugin_mcp_allowed"]
    ]
    assert tuple(allowed_candidates) in {
        (),
        ("evidence-pack-refresh",),
        ("api-cost-refresh", "evidence-pack-refresh"),
        ("repo-hygiene-refresh", "api-cost-refresh", "evidence-pack-refresh"),
        (
            "repo-hygiene-refresh",
            "api-cost-refresh",
            "evidence-pack-refresh",
            "engine-brain-refresh",
        ),
        (
            "repo-hygiene-refresh",
            "api-cost-refresh",
            "evidence-pack-refresh",
            "engine-brain-refresh",
            "p7-cockpit-smoke-refresh",
            "roadmap-state-refresh",
        ),
    }
    safe_write_design_payload = json.loads(
        p7_safe_write_tool_design_json.read_text(encoding="utf-8")
    )
    assert safe_write_design_payload["status"] in {
        "design_ready",
        "implemented",
        "blocked",
    }
    assert safe_write_design_payload["mode"] in {"design_only", "dry_run_first"}
    assert isinstance(safe_write_design_payload["mcp_enabled"], bool)
    assert safe_write_design_payload["selected_action_id"] == "evidence-pack-refresh"
    assert (
        safe_write_design_payload["proposed_mcp_tool"] == "ctoai_evidence_pack_refresh"
    )
    assert safe_write_design_payload["risk_class"] == "safe_write"
    assert (
        "append a sanitized action audit record"
        in " ".join(safe_write_design_payload["implementation_contract"]).lower()
    )
    brief_payload = json.loads(p7_operator_brief_json.read_text(encoding="utf-8"))
    assert (
        "repo-hygiene, API-cost, evidence-pack, Engine Brain, P7 cockpit-smoke, and roadmap-state"
        in brief_payload["policy"]
    )
    next_safe_mode = brief_payload["action_readiness"].get("next_safe_mode")
    if next_safe_mode == "review_confirmed_safe_write_evidence":
        assert (
            "Review confirmed evidence-pack-refresh audit"
            in brief_payload["next_safe_command"]
        )
        assert "runtime/evidence/latest.json" in brief_payload["next_safe_command"]
    elif next_safe_mode == "design_next_p7_plugin_action":
        assert "Design the next P7 plugin action" in brief_payload["next_safe_command"]
        assert "risk model coverage" in brief_payload["next_safe_command"]
    elif next_safe_mode in {
        "dry_run_roadmap_state_refresh",
        "confirmed_roadmap_state_refresh",
        "monitor_adaptive_roadmap_state",
    }:
        if brief_payload["hard_blockers"]:
            assert "hard_blockers" in brief_payload["next_safe_command"]
        else:
            assert "roadmap" in brief_payload["next_safe_command"].lower()
    elif next_safe_mode == "confirmed_selected_safe_write":
        assert "ctoai_evidence_pack_refresh" in brief_payload["next_safe_command"]
        assert "dry_run=false" in brief_payload["next_safe_command"]
        assert "refresh evidence pack" in brief_payload["next_safe_command"]
    elif brief_payload["next_safe_command"].startswith("Fix hard_blockers"):
        assert workflow_payload["status"] == "blocked"
    else:
        assert "ctoai_evidence_pack_refresh" in brief_payload["next_safe_command"]
        assert "ctoai_repo_hygiene_refresh" in brief_payload["next_safe_command"]
        assert "ctoai_api_cost_refresh" in brief_payload["next_safe_command"]
        assert "ctoai_engine_brain_refresh" in brief_payload["next_safe_command"]
        assert "ctoai_p7_cockpit_smoke_refresh" in brief_payload["next_safe_command"]
        assert "ctoai_roadmap_state_refresh" in brief_payload["next_safe_command"]
    assert brief_payload["operator_workflow"]["status"] == workflow_payload["status"]
    assert brief_payload["operator_workflow"]["allowed_tool_count"] == 11
    assert brief_payload["operator_workflow"]["safe_write_tool_count"] == 6
    assert (
        brief_payload["action_readiness"]["status"]
        == action_readiness_payload["status"]
    )
    assert brief_payload["action_readiness"]["candidate_count"] == 6
    assert brief_payload["action_readiness"]["mcp_write_tool_count"] in {
        0,
        1,
        2,
        3,
        4,
        5,
        6,
    }
    assert (
        brief_payload["safe_write_tool_design"]["status"]
        == safe_write_design_payload["status"]
    )
    assert (
        brief_payload["safe_write_tool_design"]["proposed_mcp_tool"]
        == "ctoai_evidence_pack_refresh"
    )
    assert isinstance(brief_payload["safe_write_tool_design"]["mcp_enabled"], bool)
    assert brief_payload["cockpit_handoff"]["status"] in {
        "ready",
        "needs_attention",
    }
    assert isinstance(brief_payload["cockpit_handoff"]["ready"], bool)
    assert "p7_cockpit_smoke" in brief_payload["cockpit_handoff"]
    assert "release_evidence" in brief_payload["cockpit_handoff"]
    assert "action_audit" in brief_payload["cockpit_handoff"]
    assert brief_payload["cockpit_handoff"]["recommended_tool_order"] in [
        [
            "ctoai_control_central",
            "ctoai_evidence_pack_refresh dry_run=true",
        ],
        [
            "ctoai_control_central",
            "ctoai_evidence_pack_refresh dry_run=false confirm='refresh evidence pack'",
        ],
        [
            "ctoai_control_central",
            "review confirmed evidence-pack-refresh audit",
        ],
        [
            "ctoai_control_central",
            "design next P7 plugin action",
        ],
        [
            "ctoai_control_central",
            "ctoai_engine_brain_self_check",
        ],
    ]
    assert brief_payload["roadmap_generation"]["status"] == "ready"
    assert brief_payload["roadmap_generation"]["doc_sync_status"] == "passed"
    assert (
        brief_payload["roadmap_generation"]["doc_sync_roadmap_plan3_status"] == "passed"
    )
    assert (
        brief_payload["roadmap_generation"]["doc_sync_roadmap_p8_p16_status"]
        == "passed"
    )
    assert brief_payload["roadmap_generation"]["ready_doc_count"] == 4
    assert brief_payload["roadmap_generation"]["doc_count"] == 4
    assert brief_payload["roadmap_generation"]["hard_blockers"] == []
    assert "risk model coverage" in brief_payload["roadmap_generation"]["blocked_until"]

    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["schema_version"] == 1
    assert "ownership_map" in manifest_payload["outputs"]
    assert "p6_readiness" in manifest_payload["outputs"]
    assert "p7_operator_workflow" in manifest_payload["outputs"]
    assert "p7_action_readiness" in manifest_payload["outputs"]
    assert "p7_safe_write_tool_design" in manifest_payload["outputs"]
    assert "p7_operator_brief" in manifest_payload["outputs"]
    assert manifest_payload["p6_readiness_status"] in {
        "ready_for_plugin_design",
        "blocked",
    }
    assert manifest_payload["p7_operator_workflow_status"] in {
        "safe_write_ready",
        "blocked",
    }
    assert manifest_payload["p7_action_readiness_status"] in {
        "write_tools_blocked",
        "first_safe_write_enabled",
        "safe_write_tools_enabled",
        "unsafe_write_tools_present",
    }
    assert manifest_payload["p7_safe_write_tool_design_status"] in {
        "design_ready",
        "implemented",
        "blocked",
    }
    assert manifest_payload["p7_operator_brief_status"] in {"ready", "needs_attention"}


def test_source_needles_check_blocks_missing_contract_markers(tmp_path, monkeypatch):
    source = tmp_path / "web" / "src" / "lib" / "controlCenterEvidence.ts"
    source.parent.mkdir(parents=True)
    source.write_text("const marker = 'p7OperatorBriefStatus'\n", encoding="utf-8")
    monkeypatch.setattr(engine_brain_index, "ROOT", tmp_path)

    check = engine_brain_index._source_needles_check(
        "p7_contract",
        "web/src/lib/controlCenterEvidence.ts",
        ["p7OperatorBriefStatus", "p7NextSafeCommand"],
    )

    assert check["status"] == "blocked"
    assert check["missing"] == ["p7NextSafeCommand"]


def test_p6_installed_plugin_cache_check_matches_local_manifest(tmp_path, monkeypatch):
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    source_manifest = plugin_root / ".codex-plugin" / "plugin.json"
    cache_manifest = (
        tmp_path
        / ".codex"
        / "plugins"
        / "cache"
        / "personal"
        / "ctoai-engine-brain"
        / "0.1.0+codex.test"
        / ".codex-plugin"
        / "plugin.json"
    )
    source_manifest.parent.mkdir(parents=True)
    cache_manifest.parent.mkdir(parents=True)
    manifest = {
        "name": "ctoai-engine-brain",
        "version": "0.1.0+codex.test",
    }
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    cache_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    for relative in [
        ".mcp.json",
        "skills/ctoai-engine-brain-operator/SKILL.md",
        "scripts/ctoai_collection_policy.py",
        "scripts/ctoai_control_central.py",
        "scripts/ctoai_engine_brain_brief.py",
        "scripts/ctoai_control_center_cockpit.py",
        "scripts/ctoai_evidence_io.py",
        "scripts/ctoai_freshness.py",
        "scripts/ctoai_helper_readiness.py",
        "scripts/ctoai_operator_decision.py",
        "scripts/ctoai_public_projection.py",
        "scripts/ctoai_engine_brain_mcp.py",
        "scripts/ctoai_engine_brain_status.py",
        "scripts/ctoai_engine_brain_self_check.py",
    ]:
        source_path = plugin_root / relative
        cache_path = cache_manifest.parents[1] / relative
        source_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("{}", encoding="utf-8")
        cache_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(engine_brain_index.Path, "home", lambda: tmp_path)

    check = engine_brain_index._installed_plugin_cache_check()

    assert check["status"] == "passed"
    assert "0.1.0+codex.test" in check["evidence"]
    assert "hash parity" in check["evidence"]

    (cache_manifest.parents[1] / "scripts/ctoai_control_central.py").write_text(
        "changed", encoding="utf-8"
    )
    mismatch = engine_brain_index._installed_plugin_cache_check()

    assert mismatch["status"] == "blocked"
    assert "hash_mismatch=1" in mismatch["evidence"]


def test_p6_plugin_mcp_absolute_script_check_requires_runnable_absolute_arg(
    tmp_path, monkeypatch
):
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    mcp_script = plugin_root / "scripts" / "ctoai_engine_brain_mcp.py"
    mcp_script.parent.mkdir(parents=True, exist_ok=True)
    mcp_script.write_text("# fixture\n", encoding="utf-8")
    mcp_path = plugin_root / ".mcp.json"
    mcp_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "ctoai-engine-brain": {
                        "type": "stdio",
                        "command": "python",
                        "args": [str(mcp_script)],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(engine_brain_index.Path, "home", lambda: tmp_path)

    check = engine_brain_index._plugin_mcp_absolute_script_check()

    assert check["status"] == "passed"

    mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
    mcp["mcpServers"]["ctoai-engine-brain"]["args"] = [
        "./scripts/ctoai_engine_brain_mcp.py"
    ]
    mcp_path.write_text(json.dumps(mcp), encoding="utf-8")

    check = engine_brain_index._plugin_mcp_absolute_script_check()

    assert check["status"] == "blocked"


@requires_engine_brain_plugin
def test_p6_plugin_status_script_reports_ready_for_current_workspace():
    script = (
        engine_brain_index.Path.home()
        / "plugins"
        / "ctoai-engine-brain"
        / "scripts"
        / "ctoai_engine_brain_status.py"
    )
    if not script.exists():
        raise AssertionError(f"Missing plugin status script: {script}")

    completed = subprocess.run(
        [sys.executable, str(script), "--workspace", str(engine_brain_index.ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert payload["manifest"]["doc_sync_status"] == "passed"
    assert payload["manifest"]["secret_guardrail_status"] == "passed"
    assert payload["p6"]["status"] == "ready_for_plugin_design"
    assert payload["p7_operator_workflow"]["status"] == "safe_write_ready"
    assert payload["p7_operator_workflow"]["allowed_tool_count"] == 11
    assert payload["p7_action_readiness"]["status"] == "safe_write_tools_enabled"
    assert payload["p7_action_readiness"]["candidate_count"] == 6
    assert payload["p7_action_readiness"]["mcp_write_tool_count"] == 6
    assert payload["p7_safe_write_tool_design"]["status"] == "implemented"
    assert (
        payload["p7_safe_write_tool_design"]["selected_action_id"]
        == "evidence-pack-refresh"
    )
    assert (
        payload["p7_safe_write_tool_design"]["proposed_mcp_tool"]
        == "ctoai_evidence_pack_refresh"
    )
    assert payload["p7_safe_write_tool_design"]["mcp_enabled"] is True


@requires_engine_brain_plugin
def test_p6_plugin_self_check_reports_ready_for_current_workspace():
    script = (
        engine_brain_index.Path.home()
        / "plugins"
        / "ctoai-engine-brain"
        / "scripts"
        / "ctoai_engine_brain_self_check.py"
    )
    if not script.exists():
        raise AssertionError(f"Missing plugin self-check script: {script}")

    completed = subprocess.run(
        [sys.executable, str(script), "--workspace", str(engine_brain_index.ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    checks = {item["name"]: item["status"] for item in payload["checks"]}

    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert checks["plugin_manifest"] == "passed"
    assert checks["bounded_write_policy"] == "passed"
    assert checks["brief_script"] == "passed"
    assert checks["control_center_cockpit_script"] == "passed"
    assert checks["operator_decision_script"] == "passed"
    assert checks["mcp_config"] == "passed"
    assert checks["mcp_server_script"] == "passed"
    assert checks["dashboard_skill"] == "passed"
    assert checks["collection_policy_script"] == "passed"
    assert checks["collection_policy"] == "passed"
    assert checks["installed_cache"] == "passed"
    assert checks["workspace_evidence_status"] == "passed"
    assert checks["p7_cockpit_smoke"] == "passed"
    assert checks["p7_safe_write_dry_run_smoke"] == "passed"
    assert (
        payload["workspace_status"]["p7_operator_workflow"]["status"]
        == "safe_write_ready"
    )
    assert (
        payload["workspace_status"]["p7_action_readiness"]["status"]
        == "safe_write_tools_enabled"
    )
    assert (
        payload["workspace_status"]["p7_safe_write_tool_design"]["status"]
        == "implemented"
    )
    p7_cockpit_smoke = payload["workspace_status"]["p7_cockpit_smoke"]
    assert p7_cockpit_smoke["status"] == "ready"
    assert p7_cockpit_smoke["check_count"] == 14
    assert p7_cockpit_smoke["passed_count"] == 14
    assert p7_cockpit_smoke["blocked_count"] == 0
    assert p7_cockpit_smoke["ready_safe_write_audit_count"] == 6
    assert p7_cockpit_smoke["expected_safe_write_audit_count"] == 6
    assert p7_cockpit_smoke["action_audit_line_count"] >= 6
    dry_run_smoke = payload["workspace_status"]["p7_safe_write_dry_run_smoke"]
    assert dry_run_smoke["status"] == "ready"
    assert dry_run_smoke["check_count"] == 14
    assert dry_run_smoke["passed_count"] == 14
    assert dry_run_smoke["blocked_count"] == 0
    assert dry_run_smoke["safe_write_tool_count"] == 6
    assert dry_run_smoke["dry_run_ready_count"] == 6


@requires_engine_brain_plugin
def test_p7_operator_brief_reports_next_safe_step():
    script = (
        engine_brain_index.Path.home()
        / "plugins"
        / "ctoai-engine-brain"
        / "scripts"
        / "ctoai_engine_brain_brief.py"
    )
    if not script.exists():
        raise AssertionError(f"Missing operator brief script: {script}")

    completed = subprocess.run(
        [sys.executable, str(script), "--workspace", str(engine_brain_index.ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["decision"] == "ready_for_p7_operator_workflow"
    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert payload["p6_readiness"]["status"] == "ready_for_plugin_design"
    assert payload["operator_workflow"]["status"] == "safe_write_ready"
    assert payload["operator_workflow"]["allowed_tool_count"] == 11
    assert "dangerous" in payload["operator_workflow"]["blocked_action_classes"]
    assert "safe_write" not in payload["operator_workflow"]["blocked_action_classes"]
    assert payload["action_readiness"]["status"] == "safe_write_tools_enabled"
    assert payload["action_readiness"]["candidate_count"] == 6
    assert payload["action_readiness"]["mcp_write_tool_count"] == 6
    assert payload["action_readiness"]["enabled_safe_write_tools"] == [
        {
            "action_id": "repo-hygiene-refresh",
            "mcp_tool": "ctoai_repo_hygiene_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "api-cost-refresh",
            "mcp_tool": "ctoai_api_cost_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "evidence-pack-refresh",
            "mcp_tool": "ctoai_evidence_pack_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "engine-brain-refresh",
            "mcp_tool": "ctoai_engine_brain_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "p7-cockpit-smoke-refresh",
            "mcp_tool": "ctoai_p7_cockpit_smoke_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "roadmap-state-refresh",
            "mcp_tool": "ctoai_roadmap_state_refresh",
            "risk_class": "safe_write",
        },
    ]
    assert payload["safe_write_tool_design"]["status"] == "implemented"
    assert (
        payload["safe_write_tool_design"]["proposed_mcp_tool"]
        == "ctoai_evidence_pack_refresh"
    )
    assert payload["safe_write_tool_design"]["mcp_enabled"] is True
    assert payload["cockpit_handoff"]["status"] == "ready"
    assert payload["cockpit_handoff"]["ready"] is True
    assert payload["cockpit_handoff"]["p7_cockpit_smoke"]["status"] == "ready"
    assert payload["cockpit_handoff"]["p7_cockpit_smoke"]["passed"] == 14
    assert payload["cockpit_handoff"]["p7_cockpit_smoke"]["checks"] == 14
    assert (
        payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["status"] == "ready"
    )
    assert payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["passed"] == 14
    assert payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["checks"] == 14
    assert (
        payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"]
        == 6
    )
    assert (
        payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"][
            "preflight_ready_count"
        ]
        == 6
    )
    assert (
        payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"][
            "bootstrap_allowed_count"
        ]
        == 0
    )
    assert payload["cockpit_handoff"]["release_evidence"]["status"] == "ready"
    assert payload["cockpit_handoff"]["release_evidence"]["file_count"] > 0
    assert payload["cockpit_handoff"]["release_evidence"]["sprint_count"] > 0
    phase_state = payload["cockpit_handoff"]["release_evidence"][
        "otclient_helper_roadmap_phase_state"
    ]
    assert phase_state["status"] == "p14_foundation_ready"
    assert phase_state["aligned_with_current_roadmap"] is True
    assert phase_state["p12"]["status"] == "complete"
    assert (
        phase_state["p12"]["equipment_current_plan_status"]
        == "ready_for_sandbox_session_approval"
    )
    assert payload["cockpit_handoff"]["action_audit"]["status"] == "ready"
    assert payload["cockpit_handoff"]["action_audit"]["record_count"] >= 3
    assert "safe_write" in payload["cockpit_handoff"]["action_audit"]["risk_counts"]
    assert payload["cockpit_handoff"]["recommended_tool_order"] in [
        [
            "ctoai_control_central",
            "review confirmed evidence-pack-refresh audit",
        ],
        [
            "ctoai_control_central",
            "design next P7 plugin action",
        ],
        [
            "ctoai_control_central",
            "ctoai_roadmap_state_refresh dry_run=true",
        ],
        [
            "ctoai_control_central",
            "ctoai_roadmap_state_refresh dry_run=false confirm='refresh roadmap state'",
        ],
        [
            "ctoai_control_central",
            "monitor adaptive ROADMAP_STATE",
        ],
    ]
    assert payload["roadmap_generation"]["status"] == "ready"
    assert payload["roadmap_generation"]["doc_sync_status"] == "passed"
    assert payload["roadmap_generation"]["ready_doc_count"] == 4
    assert payload["roadmap_generation"]["doc_count"] == 4
    assert "risk model coverage" in payload["roadmap_generation"]["blocked_until"]
    assert (
        "Review confirmed evidence-pack-refresh audit" in payload["next_safe_command"]
        or "Design the next P7 plugin action" in payload["next_safe_command"]
        or "Monitor the adaptive ROADMAP_STATE" in payload["next_safe_command"]
    )
    assert "deploy/live actions" in payload["policy"]


def _write_plugin_roadmap_workspace(root, *, p8_p16_status="passed"):
    roadmap_paths = [
        "AI/FEATURE_ROADMAP.md",
        "AI/ENGINE_BRAIN_STATUS.md",
        "AI/P8_P16_EXECUTION_ROADMAP.md",
        "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
    ]
    for rel_path in roadmap_paths:
        source = engine_brain_index.ROOT / rel_path
        destination = root / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    doc_sync_path = root / "AI" / "generated" / "DOC_SYNC.json"
    doc_sync_path.parent.mkdir(parents=True, exist_ok=True)
    doc_sync_path.write_text(
        json.dumps(_roadmap_doc_sync_payload(p8_p16_status=p8_p16_status)),
        encoding="utf-8",
    )


def _run_plugin_cockpit(workspace):
    script = PLUGIN_ROOT / "scripts" / "ctoai_control_center_cockpit.py"
    module = _load_plugin_module("ctoai_control_center_cockpit_internal", script)
    return module.build_cockpit(workspace)


@requires_engine_brain_plugin
def test_p6_plugin_cockpit_blocks_current_phase_marker_drift(tmp_path):
    _write_plugin_roadmap_workspace(tmp_path)
    roadmap_path = tmp_path / "AI" / "P8_P16_EXECUTION_ROADMAP.md"
    required_marker = (
        "Conditions and Equipment lanes are `operational_acceptance_complete`"
    )
    roadmap_path.write_text(
        roadmap_path.read_text(encoding="utf-8").replace(
            required_marker, "Conditions and Equipment lanes remain under review"
        ),
        encoding="utf-8",
    )

    payload = _run_plugin_cockpit(tmp_path)["roadmap_generation"]

    assert payload["status"] == "needs_attention"
    assert "p8_p16_execution_roadmap_not_ready" in payload["hard_blockers"]
    assert payload["doc_sync_status"] == "passed"
    assert payload["doc_sync_roadmap_plan3_status"] == "passed"
    assert payload["doc_sync_roadmap_p8_p16_status"] == "passed"
    p8_doc = next(
        item for item in payload["docs"] if item["name"] == "p8_p16_execution_roadmap"
    )
    assert required_marker in p8_doc["missing_markers"]


@requires_engine_brain_plugin
def test_p6_plugin_cockpit_requires_p8_doc_sync_status(tmp_path):
    _write_plugin_roadmap_workspace(tmp_path, p8_p16_status="blocked")

    payload = _run_plugin_cockpit(tmp_path)["roadmap_generation"]

    assert payload["status"] == "needs_attention"
    assert "doc_sync:roadmap_p8_p16" in payload["hard_blockers"]
    assert payload["doc_sync_status"] == "passed"
    assert payload["doc_sync_roadmap_plan3_status"] == "passed"
    assert payload["doc_sync_roadmap_p8_p16_status"] == "blocked"


@requires_engine_brain_plugin
def test_p6_control_center_cockpit_script_reports_read_only_status():
    script = (
        engine_brain_index.Path.home()
        / "plugins"
        / "ctoai-engine-brain"
        / "scripts"
        / "ctoai_control_center_cockpit.py"
    )
    if not script.exists():
        raise AssertionError(f"Missing Control Center cockpit script: {script}")

    module = _load_plugin_module("ctoai_control_center_cockpit_internal", script)
    payload = module.build_cockpit(engine_brain_index.ROOT)

    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert payload["p7_cockpit"]["status"] == "ready"
    assert payload["p7_cockpit"]["enabled_safe_write_tool_count"] == 6
    assert payload["p7_cockpit"]["ready_audit_count"] == 6
    assert payload["p7_cockpit"]["audit_count"] == 6
    assert payload["p7_cockpit"]["mcp_write_tool_count"] == 6
    _assert_adaptive_operator(payload["operator_next"], public=False)
    helper = payload["otclient_helper"]
    assert len(helper["blockers"]) == min(helper["blocker_count"], 8)
    phase_state = payload["otclient_helper"]["roadmap_phase_state"]
    assert phase_state["status"] == "p14_foundation_ready"
    assert phase_state["aligned_with_current_roadmap"] is True
    assert phase_state["p12"] == {
        "status": "complete",
        "conditions_status": "operational_acceptance_complete",
        "equipment_status": "operational_acceptance_complete",
        "equipment_receipt_status": "accepted",
        "equipment_consumed_attempt": True,
        "equipment_current_plan_status": "ready_for_sandbox_session_approval",
        "equipment_current_plan_safe": True,
        "equipment_attempt_count": 1,
        "equipment_session_approved": True,
        "equipment_execution_approved": True,
        "heal_friend_status": "closed_blocked_no_compatible_vocation",
    }
    assert "PromoteLiveCtoa" not in payload["operator_next"]["command"]
    assert "ApproveLiveDeploy" not in payload["operator_next"]["command"]
    assert payload["p7_cockpit_smoke"]["status"] == "ready"
    assert payload["p7_cockpit_smoke"]["check_count"] == 14
    assert payload["p7_cockpit_smoke"]["passed_count"] == 14
    assert payload["p7_cockpit_smoke"]["blocked_count"] == 0
    assert payload["p7_cockpit_smoke"]["ready_safe_write_audit_count"] == 6
    assert payload["p7_cockpit_smoke"]["expected_safe_write_audit_count"] == 6
    assert (
        payload["source_paths"]["p7_cockpit_smoke"]
        == "runtime/control-center/p7-cockpit-smoke.json"
    )
    assert payload["p7_safe_write_dry_run_smoke"]["status"] == "ready"
    assert payload["p7_safe_write_dry_run_smoke"]["check_count"] == 14
    assert payload["p7_safe_write_dry_run_smoke"]["passed_count"] == 14
    assert payload["p7_safe_write_dry_run_smoke"]["blocked_count"] == 0
    assert payload["p7_safe_write_dry_run_smoke"]["safe_write_tool_count"] == 6
    assert payload["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"] == 6
    assert payload["p7_safe_write_dry_run_smoke"]["preflight_ready_count"] == 6
    assert payload["p7_safe_write_dry_run_smoke"]["bootstrap_allowed_count"] == 0
    assert (
        payload["source_paths"]["p7_safe_write_dry_run_smoke"]
        == "runtime/control-center/p7-safe-write-dry-run-smoke.json"
    )
    assert payload["release_evidence"]["status"] == "ready"
    assert payload["release_evidence"]["drilldown"]["file_count"] > 0
    assert payload["release_evidence"]["drilldown"]["recent_files"]
    assert payload["roadmap_generation"]["status"] == "ready"
    assert payload["roadmap_generation"]["doc_sync_status"] == "passed"
    assert payload["roadmap_generation"]["doc_sync_roadmap_plan3_status"] == "passed"
    assert payload["roadmap_generation"]["doc_sync_roadmap_p8_p16_status"] == "passed"
    assert payload["roadmap_generation"]["ready_doc_count"] == 4
    assert payload["roadmap_generation"]["doc_count"] == 4
    assert payload["roadmap_generation"]["hard_blockers"] == []
    assert "risk model coverage" in payload["roadmap_generation"]["blocked_until"]
    assert payload["action_audit_drilldown"]["status"] == "ready"
    assert payload["action_audit_drilldown"]["record_count"] >= 3
    assert (
        payload["action_audit_drilldown"]["source_bytes"]
        >= payload["action_audit_drilldown"]["sampled_bytes"]
    )
    assert "safe_write" in payload["action_audit_drilldown"]["risk_counts"]
    assert "deploy" in payload["policy"]
    assert "live-client" in payload["policy"]


@requires_engine_brain_plugin
def test_p6_control_center_cockpit_cli_returns_public_projection():
    script = PLUGIN_ROOT / "scripts" / "ctoai_control_center_cockpit.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--workspace",
            str(engine_brain_index.ROOT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["schema_version"] == 2
    assert payload["status"] == "ready"
    assert len(serialized) < 6000
    for private_key in (
        '"command"',
        '"source_path"',
        '"source_paths"',
        '"audit_id"',
        '"actor"',
        '"actor_role"',
        '"reason"',
        '"output_preview"',
        '"recent_records"',
        '"recent_files"',
    ):
        assert private_key not in serialized

    internal_attempt = subprocess.run(
        [
            sys.executable,
            str(script),
            "--workspace",
            str(engine_brain_index.ROOT),
            "--detail",
            "internal",
        ],
        capture_output=True,
        text=True,
    )
    assert internal_attempt.returncode != 0


def write_cockpit_preflight_fixture(root):
    fresh_now = engine_brain_index.datetime.now(
        engine_brain_index.timezone.utc
    ).isoformat()
    release_dir = root / "releases" / "evidence" / "sprint-999"
    release_dir.mkdir(parents=True, exist_ok=True)
    (release_dir / "CTOA-test.md").write_text(
        "# P6 Plugin Cockpit Drilldown\n\nRead-only release evidence fixture.\n",
        encoding="utf-8",
    )

    operator_brief_path = root / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    operator_brief_path.parent.mkdir(parents=True, exist_ok=True)
    enabled_tools = [
        {
            "action_id": "repo-hygiene-refresh",
            "mcp_tool": "ctoai_repo_hygiene_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "api-cost-refresh",
            "mcp_tool": "ctoai_api_cost_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "evidence-pack-refresh",
            "mcp_tool": "ctoai_evidence_pack_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "engine-brain-refresh",
            "mcp_tool": "ctoai_engine_brain_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "p7-cockpit-smoke-refresh",
            "mcp_tool": "ctoai_p7_cockpit_smoke_refresh",
            "risk_class": "safe_write",
        },
        {
            "action_id": "roadmap-state-refresh",
            "mcp_tool": "ctoai_roadmap_state_refresh",
            "risk_class": "safe_write",
        },
    ]
    operator_brief_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-07T06:30:00+00:00",
                "decision": "ready_for_p7_operator_workflow",
                "status": "ready",
                "hard_blockers": [],
                "warnings": [],
                "next_safe_command": "Run ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true.",
                "action_readiness": {
                    "status": "safe_write_tools_enabled",
                    "decision": "monitor_enabled_safe_write_tools",
                    "candidate_count": 6,
                    "audited_candidate_count": 6,
                    "mcp_write_tool_count": 6,
                    "enabled_safe_write_tools": enabled_tools,
                    "next_safe_command": "Run ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true.",
                },
                "safe_write_tool_design": {
                    "status": "implemented",
                    "decision": "ready_for_dry_run_operation",
                    "selected_action_id": "evidence-pack-refresh",
                    "proposed_mcp_tool": "ctoai_evidence_pack_refresh",
                    "risk_class": "safe_write",
                    "mode": "dry_run_first",
                    "mcp_enabled": True,
                },
            }
        ),
        encoding="utf-8",
    )

    evidence_path = root / "runtime" / "evidence" / "latest.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_payload = {
        "generated_at_utc": fresh_now,
        "release_evidence_file_count": 1,
        "latest_release_evidence": {"path": "releases/evidence/CTOA-test.md"},
        "repo_hygiene": {"status": "PASS", "finding_count": 0},
        "api_cost_report": {"status": "ready", "records_seen": 0},
        "control_center_audit": {"status": "ready", "record_count": 5},
        "otclient_helper": {
            "status": "blocked",
            "release_gate_status": "blocked",
            "next_action": "Run SmokeAttachModules after sandbox character is in-world.",
            "roadmap_phase_state": {
                "status": "p12_in_progress",
                "aligned_with_current_roadmap": True,
                "p8": "operational_acceptance_complete",
                "p9": "operational_acceptance_complete",
                "p10": "operational_acceptance_complete",
                "p11": "operational_acceptance_complete",
                "p12": {
                    "status": "in_progress",
                    "conditions": {"status": "operational_acceptance_complete"},
                    "equipment": {
                        "status": "operational_acceptance_blocked",
                        "receipt_status": "rejected",
                        "consumed_attempt": True,
                        "current_plan_status": "blocked",
                        "current_plan_safe": True,
                        "attempt_count": 0,
                        "session_approved": False,
                        "execution_approved": False,
                    },
                    "heal_friend": {"status": "not_started"},
                },
            },
            "sandbox_smoke_queue": {
                "status": "ready_for_operator",
                "runtime_status": "not_running",
                "next_action": "Launch sandbox client and enter test character",
                "required_count": 5,
                "queued_count": 4,
                "next_steps": [
                    {"step_id": "launch_sandbox"},
                    {"step_id": "module_attach_group"},
                ],
            },
        },
    }
    source_audit_id = "20260707063000000000-evidence-pack-refresh"
    evidence_payload["schema_version"] = "ctoa.control-center.evidence.v2"
    evidence_payload["provenance"] = {
        "source_action": "evidence-pack-refresh",
        "source_audit_id": source_audit_id,
        "binding_status": "bound",
    }
    evidence_payload["provenance"]["content_sha256"] = hashlib.sha256(
        json.dumps(
            evidence_payload,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    evidence_text = json.dumps(evidence_payload)
    evidence_path.write_text(evidence_text, encoding="utf-8")

    audit_path = root / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "at": f"2026-07-07T06:30:0{index}Z",
            "audit_id": f"preflight-{tool['action_id']}",
            "actor": "pytest",
            "actor_role": "operator",
            "action": tool["action_id"],
            "target": "local",
            "risk_class": "safe_write",
            "minimum_role": "operator",
            "dry_run": True,
            "authorized": True,
            "ok": True,
            "reason": "pytest preflight fixture",
            "output_preview": "ready",
        }
        for index, tool in enumerate(enabled_tools, start=1)
    ]
    records.append(
        {
            "at": "2026-07-07T06:30:06Z",
            "audit_id": source_audit_id,
            "actor": "pytest",
            "actor_role": "operator",
            "action": "evidence-pack-refresh",
            "target": "local",
            "risk_class": "safe_write",
            "minimum_role": "operator",
            "dry_run": False,
            "authorized": True,
            "ok": True,
            "reason": "pytest integrity fixture",
            "output_preview": "ready",
            "output_hashes": {
                "runtime/evidence/latest.json": hashlib.sha256(
                    evidence_text.encode("utf-8")
                ).hexdigest()
            },
        }
    )
    audit_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    p6_smoke_path = root / "runtime" / "control-center" / "p6-plugin-handoff-smoke.json"
    p6_smoke_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-07-07T06:29:00+00:00",
                "status": "ready",
                "hard_blockers": [],
                "warnings": [],
                "summary": {
                    "checks": 15,
                    "passed": 15,
                    "blocked": 0,
                    "p6_check_count": 48,
                    "p6_passed_count": 48,
                    "mcp_contract_count": 6,
                    "passed_mcp_contract_count": 6,
                    "allowed_tool_count": 11,
                    "read_only_tool_count": 5,
                    "safe_write_tool_count": 6,
                    "installed_cache_version": "0.1.0+codex.test",
                    "plugin_manifest_version": "0.1.0+codex.test",
                    "fresh_thread_required": True,
                    "current_thread_tool_discovery_status": "requires_fresh_thread",
                },
                "fresh_thread_verification": {
                    "status": "pending_fresh_thread",
                    "recommended_tool_order": [
                        "ctoai_control_central",
                        "ctoai_engine_brain_self_check",
                    ],
                    "next_action": "Open a fresh Codex thread and verify plugin tools.",
                },
            }
        ),
        encoding="utf-8",
    )
    smoke_path = root / "runtime" / "control-center" / "p7-cockpit-smoke.json"
    smoke_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-07-07T06:30:00+00:00",
                "status": "ready",
                "hard_blockers": [],
                "warnings": [],
                "summary": {
                    "checks": 14,
                    "passed": 14,
                    "blocked": 0,
                    "allowed_mcp_tool_count": 11,
                    "enabled_safe_write_tool_count": 6,
                    "ready_safe_write_audit_count": 6,
                    "expected_safe_write_audit_count": 6,
                    "action_audit_line_count": len(records),
                },
            }
        ),
        encoding="utf-8",
    )
    dry_run_smoke_path = (
        root / "runtime" / "control-center" / "p7-safe-write-dry-run-smoke.json"
    )
    dry_run_smoke_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-07-07T06:31:00+00:00",
                "status": "ready",
                "hard_blockers": [],
                "warnings": [],
                "summary": {
                    "checks": 12,
                    "passed": 12,
                    "blocked": 0,
                    "safe_write_tool_count": 6,
                    "dry_run_ready_count": 6,
                    "preflight_ready_count": 6,
                    "bootstrap_allowed_count": 0,
                },
                "safe_write_results": [
                    {
                        "action_id": tool["action_id"],
                        "mcp_tool": tool["mcp_tool"],
                        "status": "dry_run",
                        "audit_record_ready": True,
                        "preflight_ok": True,
                        "preflight_bootstrap_allowed": False,
                    }
                    for tool in enabled_tools
                ],
            }
        ),
        encoding="utf-8",
    )


@requires_engine_brain_plugin
def test_p6_plugin_cockpit_blocks_bootstrap_only_dry_run_smoke(tmp_path):
    plugin_root = engine_brain_index.Path.home() / "plugins" / "ctoai-engine-brain"
    script = plugin_root / "scripts" / "ctoai_control_center_cockpit.py"
    if not script.exists():
        raise AssertionError(f"Missing Control Center cockpit script: {script}")

    write_cockpit_preflight_fixture(tmp_path)
    dry_run_smoke_path = (
        tmp_path / "runtime" / "control-center" / "p7-safe-write-dry-run-smoke.json"
    )
    dry_run_smoke = json.loads(dry_run_smoke_path.read_text(encoding="utf-8"))
    dry_run_smoke["summary"]["preflight_ready_count"] = 5
    dry_run_smoke["summary"]["bootstrap_allowed_count"] = 1
    dry_run_smoke["safe_write_results"][0]["preflight_ok"] = False
    dry_run_smoke["safe_write_results"][0]["preflight_bootstrap_allowed"] = True
    dry_run_smoke_path.write_text(json.dumps(dry_run_smoke), encoding="utf-8")

    module = _load_plugin_module("ctoai_control_center_cockpit_bootstrap", script)
    payload = module.build_cockpit(tmp_path)

    assert payload["status"] == "needs_attention"
    assert "p7_safe_write_dry_run_smoke_not_ready" in payload["hard_blockers"]
    assert payload["operator_next"]["status"] == "blocked"
    assert payload["operator_next"]["lane"] == "p7-safe-write-dry-run-smoke"
    assert payload["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"] == 6
    assert payload["p7_safe_write_dry_run_smoke"]["preflight_ready_count"] == 5
    assert payload["p7_safe_write_dry_run_smoke"]["bootstrap_allowed_count"] == 1


@requires_engine_brain_plugin
def test_p6_plugin_mcp_server_exposes_expected_tools_and_audited_safe_write(tmp_path):
    plugin_root = engine_brain_index.Path.home() / "plugins" / "ctoai-engine-brain"
    config_path = plugin_root / ".mcp.json"
    if not config_path.exists():
        raise AssertionError(f"Missing plugin MCP config: {config_path}")

    script_path = tmp_path / "scripts" / "ops" / "release_evidence_pack.py"
    api_cost_script_path = tmp_path / "scripts" / "ops" / "api_cost_report.py"
    repo_hygiene_script_path = tmp_path / "scripts" / "ops" / "repo_hygiene_audit.py"
    engine_brain_script_path = tmp_path / "scripts" / "ops" / "engine_brain_index.py"
    p7_cockpit_smoke_script_path = (
        tmp_path / "scripts" / "ops" / "control_center_p7_cockpit_smoke.py"
    )
    roadmap_state_script_path = (
        tmp_path / "scripts" / "ops" / "ctoai_roadmap_state.py"
    )
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        """import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--json-out', type=Path, required=True)
parser.add_argument('--md-out', type=Path, required=True)
parser.add_argument('--source-audit-id', required=True)
args = parser.parse_args()
payload = {'schema_version': 'ctoa.control-center.evidence.v2', 'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'provenance': {'source_action': 'evidence-pack-refresh', 'source_audit_id': args.source_audit_id, 'binding_status': 'bound'}}
payload['provenance']['content_sha256'] = hashlib.sha256(json.dumps(payload, allow_nan=False, ensure_ascii=True, separators=(',', ':'), sort_keys=True).encode('utf-8')).hexdigest()
args.json_out.parent.mkdir(parents=True, exist_ok=True)
args.json_out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
args.md_out.write_text('# refreshed\\n', encoding='utf-8')
print('release evidence refreshed')
""",
        encoding="utf-8",
    )
    api_cost_script_path.write_text(
        """import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--json-out', type=Path, required=True)
parser.add_argument('--md-out', type=Path, required=True)
args = parser.parse_args()
args.json_out.parent.mkdir(parents=True, exist_ok=True)
args.json_out.write_text(json.dumps({'status': 'ready'}), encoding='utf-8')
args.md_out.write_text('# ready\\n', encoding='utf-8')
print('api cost refreshed')
""",
        encoding="utf-8",
    )
    repo_hygiene_script_path.write_text(
        """import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--json-out', type=Path, required=True)
args = parser.parse_args()
args.json_out.parent.mkdir(parents=True, exist_ok=True)
args.json_out.write_text(json.dumps({'status': 'PASS'}), encoding='utf-8')
print('repo hygiene refreshed')
""",
        encoding="utf-8",
    )
    engine_brain_script_path.write_text(
        """import json
from pathlib import Path
path = Path('AI/generated/manifest.json')
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({'status': 'ready'}), encoding='utf-8')
print('engine brain refreshed')
""",
        encoding="utf-8",
    )
    p7_cockpit_smoke_script_path.write_text(
        """import json
from pathlib import Path
for suffix in ('json', 'md'):
    path = Path(f'runtime/control-center/p7-cockpit-smoke.{suffix}')
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'status': 'ready', 'hard_blockers': [], 'warnings': [], 'summary': {'checks': 14, 'passed': 14, 'blocked': 0, 'allowed_mcp_tool_count': 11, 'enabled_safe_write_tool_count': 6, 'ready_safe_write_audit_count': 6, 'expected_safe_write_audit_count': 6}}
    path.write_text(json.dumps(payload) if suffix == 'json' else '# ready\\n', encoding='utf-8')
print('p7 cockpit smoke refreshed')
""",
        encoding="utf-8",
    )
    roadmap_state_script_path.write_text(
        """import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', choices=('true', 'false'), required=True)
parser.add_argument('--confirmation')
parser.add_argument('--reason', required=True)
args = parser.parse_args()
if args.dry_run == 'false':
    if args.confirmation != 'refresh roadmap state':
        raise SystemExit('invalid confirmation')
    json_out = Path('AI/generated/ROADMAP_STATE.json')
    md_out = Path('AI/generated/ROADMAP_STATE.md')
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps({'schema_version': 'ctoa.roadmap-state.v2', 'status': 'ready', 'readiness_status': 'awaiting_external'}), encoding='utf-8')
    md_out.write_text('# Adaptive roadmap state\\n', encoding='utf-8')
print(json.dumps({'status': 'dry_run' if args.dry_run == 'true' else 'completed', 'ok': True}))
""",
        encoding="utf-8",
    )
    write_cockpit_preflight_fixture(tmp_path)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["ctoai-engine-brain"]
    assert server["type"] == "stdio"
    assert server["command"] == "python"
    args = server["args"]

    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "ctoai_engine_brain_brief",
                "arguments": {"workspace": str(engine_brain_index.ROOT)},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "ctoai_control_center_cockpit",
                "arguments": {"workspace": str(engine_brain_index.ROOT)},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "ctoai_repo_hygiene_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest hygiene token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "ctoai_repo_hygiene_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "confirm": "refresh repo hygiene snapshot",
                    "reason": "pytest hygiene confirmed token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "ctoai_repo_hygiene_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "reason": "pytest hygiene missing confirm token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "ctoai_evidence_pack_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "ctoai_evidence_pack_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "confirm": "refresh evidence pack",
                    "reason": "pytest confirmed token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "ctoai_api_cost_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest api token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "ctoai_api_cost_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "confirm": "refresh api cost report",
                    "reason": "pytest api confirmed token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "ctoai_engine_brain_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest brain token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "ctoai_engine_brain_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "confirm": "refresh engine brain context",
                    "reason": "pytest brain confirmed token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "ctoai_p7_cockpit_smoke_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest p7 cockpit smoke token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "ctoai_p7_cockpit_smoke_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "confirm": "refresh p7 cockpit smoke",
                    "reason": "pytest p7 cockpit smoke confirmed token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 16,
            "method": "tools/call",
            "params": {
                "name": "ctoai_roadmap_state_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest roadmap token=secret-value",
                },
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 17,
            "method": "tools/call",
            "params": {
                "name": "ctoai_roadmap_state_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": False,
                    "confirm": "refresh roadmap state",
                    "reason": "pytest roadmap confirmed token=secret-value",
                },
            },
        },
    ]
    completed = subprocess.run(
        [sys.executable, *args],
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        check=True,
        capture_output=True,
        text=True,
        cwd=plugin_root,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    tools_by_name = {tool["name"]: tool for tool in responses[1]["result"]["tools"]}
    tools = set(tools_by_name)
    payload = json.loads(responses[2]["result"]["content"][0]["text"])
    cockpit_payload = json.loads(responses[3]["result"]["content"][0]["text"])
    hygiene_refresh_payload = json.loads(responses[4]["result"]["content"][0]["text"])
    hygiene_confirmed_payload = json.loads(responses[5]["result"]["content"][0]["text"])
    hygiene_blocked_payload = json.loads(responses[6]["result"]["content"][0]["text"])
    refresh_payload = json.loads(responses[7]["result"]["content"][0]["text"])
    confirmed_payload = json.loads(responses[8]["result"]["content"][0]["text"])
    api_refresh_payload = json.loads(responses[9]["result"]["content"][0]["text"])
    api_confirmed_payload = json.loads(responses[10]["result"]["content"][0]["text"])
    brain_refresh_payload = json.loads(responses[11]["result"]["content"][0]["text"])
    brain_confirmed_payload = json.loads(responses[12]["result"]["content"][0]["text"])
    p7_cockpit_smoke_refresh_payload = json.loads(
        responses[13]["result"]["content"][0]["text"]
    )
    p7_cockpit_smoke_confirmed_payload = json.loads(
        responses[14]["result"]["content"][0]["text"]
    )
    roadmap_state_refresh_payload = json.loads(
        responses[15]["result"]["content"][0]["text"]
    )
    roadmap_state_confirmed_payload = json.loads(
        responses[16]["result"]["content"][0]["text"]
    )

    assert responses[0]["result"]["serverInfo"]["name"] == "ctoai-engine-brain"
    assert tools == {
        "ctoai_control_central",
        "ctoai_engine_brain_status",
        "ctoai_engine_brain_self_check",
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
        "ctoai_repo_hygiene_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
        "ctoai_roadmap_state_refresh",
    }
    assert not any(
        fragment in tool_name.lower()
        for tool_name in tools
        for fragment in ("deploy", "live", "promote", "solteria")
    )
    for tool_name in [
        "ctoai_engine_brain_status",
        "ctoai_engine_brain_self_check",
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
    ]:
        schema = tools_by_name[tool_name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == {"workspace"}
    central_schema = tools_by_name["ctoai_control_central"]["inputSchema"]
    assert central_schema["additionalProperties"] is False
    assert set(central_schema["properties"]) == {"workspace", "profile", "detail"}
    assert "plugin-management" in central_schema["properties"]["profile"]["enum"]
    assert central_schema["properties"]["detail"]["enum"] == [
        "summary",
        "compact",
        "full",
    ]
    assert central_schema["properties"]["detail"]["default"] == "summary"
    detail_description = central_schema["properties"]["detail"]["description"]
    assert "bounded allowlisted" in detail_description
    assert "never raw evidence" in detail_description
    for tool_name in [
        "ctoai_repo_hygiene_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
        "ctoai_roadmap_state_refresh",
    ]:
        schema = tools_by_name[tool_name]["inputSchema"]
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == {
            "workspace",
            "dry_run",
            "confirm",
            "reason",
        }
        assert schema["properties"]["dry_run"]["type"] == "boolean"
    assert payload["decision"] == "ready_for_p7_operator_workflow"
    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert payload["schema_version"] == 2
    assert payload["p7"]["workflow"] == "safe_write_ready"
    assert payload["p7"]["readiness"] == "safe_write_tools_enabled"
    assert payload["p7"]["design"]["status"] == "implemented"
    brief_text = json.dumps(payload, sort_keys=True)
    for private_key in (
        '"workspace"',
        '"path"',
        '"command"',
        '"next_safe_command"',
        '"evidence"',
        '"audit_id"',
        '"actor"',
        '"reason"',
        '"output"',
    ):
        assert private_key not in brief_text
    assert len(brief_text) < 4000
    assert cockpit_payload["schema_version"] == 2
    assert cockpit_payload["status"] == "ready"
    assert cockpit_payload["p7_cockpit"]["enabled_tools"] == 6
    assert cockpit_payload["p7_cockpit"]["ready_audits"] == 6
    _assert_adaptive_operator(cockpit_payload["operator_next"], public=True)
    assert cockpit_payload["smoke"]["p7_cockpit"] == {
        "status": "ready",
        "checks": 14,
        "passed": 14,
        "blocked": 0,
    }
    assert cockpit_payload["smoke"]["p7_dry_run"] == {
        "status": "ready",
        "checks": 14,
        "passed": 14,
        "blocked": 0,
    }
    assert cockpit_payload["release_evidence"]["status"] == "ready"
    assert cockpit_payload["release_evidence"]["files"] > 0
    assert cockpit_payload["release_evidence"]["sprints"] > 0
    assert cockpit_payload["roadmap"]["status"] == "ready"
    assert cockpit_payload["roadmap"]["ready_docs"] == 4
    assert cockpit_payload["roadmap"]["docs"] == 4
    assert cockpit_payload["action_audit"]["status"] == "ready"
    assert cockpit_payload["action_audit"]["records"] >= 5
    cockpit_text = json.dumps(cockpit_payload, sort_keys=True)
    for private_key in (
        '"command"',
        '"source_path"',
        '"source_paths"',
        '"audit_id"',
        '"actor"',
        '"actor_role"',
        '"reason"',
        '"output_preview"',
        '"recent_records"',
        '"recent_files"',
    ):
        assert private_key not in cockpit_text
    assert cockpit_payload["policy"].startswith("Read-only minimized cockpit")
    safe_write_pairs = [
        (
            hygiene_refresh_payload,
            hygiene_confirmed_payload,
            "repo-hygiene-refresh",
            "ctoai_repo_hygiene_refresh",
            1,
        ),
        (
            refresh_payload,
            confirmed_payload,
            "evidence-pack-refresh",
            "ctoai_evidence_pack_refresh",
            2,
        ),
        (
            api_refresh_payload,
            api_confirmed_payload,
            "api-cost-refresh",
            "ctoai_api_cost_refresh",
            2,
        ),
        (
            brain_refresh_payload,
            brain_confirmed_payload,
            "engine-brain-refresh",
            "ctoai_engine_brain_refresh",
            1,
        ),
        (
            p7_cockpit_smoke_refresh_payload,
            p7_cockpit_smoke_confirmed_payload,
            "p7-cockpit-smoke-refresh",
            "ctoai_p7_cockpit_smoke_refresh",
            2,
        ),
        (
            roadmap_state_refresh_payload,
            roadmap_state_confirmed_payload,
            "roadmap-state-refresh",
            "ctoai_roadmap_state_refresh",
            2,
        ),
    ]
    private_safe_write_keys = (
        '"audit_id"',
        '"audit_path"',
        '"command"',
        '"command_summary"',
        '"json_out"',
        '"md_out"',
        '"operator_next"',
        '"output"',
        '"reason"',
        '"source_path"',
        '"source_paths"',
        '"output_hashes"',
    )
    for dry_payload, confirmed, action, tool, artifact_count in safe_write_pairs:
        for current in (dry_payload, confirmed):
            public_text = json.dumps(current, sort_keys=True)
            assert current["schema_version"] == 2
            assert current["action"] == action
            assert current["tool"] == tool
            assert current["risk_class"] == "safe_write"
            assert current["ok"] is True, (action, current)
            assert current["audit_recorded"] is True
            assert current["artifact_count"] == artifact_count
            assert current["preflight"]["ok"] is True
            assert current["preflight"]["p7_cockpit"] == {
                "status": "ready",
                "enabled_tools": 6,
                "ready_audits": 6,
            }
            assert current["preflight"]["p7_smoke"] == {
                "status": "ready",
                "passed": 14,
                "checks": 14,
            }
            assert current["preflight"]["p7_dry_run"] == {
                "status": "ready",
                "ready_tools": 6,
                "tools": 6,
            }
            assert len(public_text) < 2500
            assert "secret-value" not in public_text
            assert str(tmp_path) not in public_text
            for private_key in private_safe_write_keys:
                assert private_key not in public_text
        assert dry_payload["status"] == "dry_run"
        assert dry_payload["dry_run"] is True
        assert dry_payload["result_code"] == "plan_recorded"
        assert dry_payload["artifact_integrity"] == {
            "status": "not_applicable",
            "verified": 0,
            "expected": artifact_count,
        }
        assert confirmed["status"] == "completed"
        assert confirmed["dry_run"] is False
        assert confirmed["result_code"] == "action_completed"
        assert confirmed["artifact_integrity"] == {
            "status": "verified",
            "verified": artifact_count,
            "expected": artifact_count,
        }

    assert hygiene_blocked_payload["status"] == "blocked"
    assert hygiene_blocked_payload["action"] == "repo-hygiene-refresh"
    assert hygiene_blocked_payload["dry_run"] is False
    assert hygiene_blocked_payload["ok"] is False
    assert hygiene_blocked_payload["result_code"] == "action_blocked"
    assert hygiene_blocked_payload["audit_recorded"] is True
    assert hygiene_blocked_payload["artifact_count"] == 0
    assert hygiene_blocked_payload["preflight"]["ok"] is True
    blocked_text = json.dumps(hygiene_blocked_payload, sort_keys=True)
    assert str(tmp_path) not in blocked_text
    for private_key in private_safe_write_keys:
        assert private_key not in blocked_text
    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_records = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len({record["audit_id"] for record in audit_records}) == len(audit_records)
    confirmed_records = [
        record
        for record in audit_records
        if record.get("authorized") is True
        and record.get("ok") is True
        and record.get("dry_run") is False
    ]
    assert confirmed_records
    assert all(record.get("output_hashes") for record in confirmed_records)
    evidence_record = next(
        record
        for record in reversed(confirmed_records)
        if record["action"] == "evidence-pack-refresh"
    )
    generated_evidence = json.loads(
        (tmp_path / "runtime" / "evidence" / "latest.json").read_text(encoding="utf-8")
    )
    assert (
        generated_evidence["provenance"]["source_audit_id"]
        == evidence_record["audit_id"]
    )
    assert [record["action"] for record in audit_records[-13:]] == [
        "repo-hygiene-refresh",
        "repo-hygiene-refresh",
        "repo-hygiene-refresh",
        "evidence-pack-refresh",
        "evidence-pack-refresh",
        "api-cost-refresh",
        "api-cost-refresh",
        "engine-brain-refresh",
        "engine-brain-refresh",
        "p7-cockpit-smoke-refresh",
        "p7-cockpit-smoke-refresh",
        "roadmap-state-refresh",
        "roadmap-state-refresh",
    ]
    assert [record["dry_run"] for record in audit_records[-13:]] == [
        True,
        False,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    ]
    assert [record["authorized"] for record in audit_records[-13:]] == [
        True,
        True,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    assert [record["ok"] for record in audit_records[-13:]] == [
        True,
        True,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]
    assert all(record["risk_class"] == "safe_write" for record in audit_records[-13:])
    assert "secret-value" not in json.dumps(audit_records)
    assert all(
        "[redacted]" in record["reason"]
        for record in audit_records[-13:]
        if record["authorized"]
    )


@requires_engine_brain_plugin
def test_p6_plugin_dry_run_bootstrap_breaks_only_known_evidence_cycles():
    script = PLUGIN_ROOT / "scripts" / "ctoai_engine_brain_mcp.py"
    module = _load_plugin_module("ctoai_engine_brain_mcp_bootstrap", script)

    assert module.dry_run_preflight_bootstrap_allowed(
        {
            "hard_blockers": [
                "p6_plugin_handoff_smoke_not_ready",
                "p7_safe_write_dry_run_smoke_not_ready",
            ]
        }
    )
    assert not module.dry_run_preflight_bootstrap_allowed(
        {
            "hard_blockers": [
                "p6_plugin_handoff_smoke_not_ready",
                "untrusted_runtime_authority",
            ]
        }
    )


@requires_engine_brain_plugin
def test_p6_plugin_safe_write_blocks_without_cockpit_preflight(tmp_path):
    plugin_root = engine_brain_index.Path.home() / "plugins" / "ctoai-engine-brain"
    config_path = plugin_root / ".mcp.json"
    if not config_path.exists():
        raise AssertionError(f"Missing plugin MCP config: {config_path}")

    repo_hygiene_script_path = tmp_path / "scripts" / "ops" / "repo_hygiene_audit.py"
    repo_hygiene_script_path.parent.mkdir(parents=True)
    repo_hygiene_script_path.write_text(
        "print('repo hygiene should not run')\n",
        encoding="utf-8",
    )

    config = json.loads(config_path.read_text(encoding="utf-8"))
    args = config["mcpServers"]["ctoai-engine-brain"]["args"]
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ctoai_repo_hygiene_refresh",
                "arguments": {
                    "workspace": str(tmp_path),
                    "dry_run": True,
                    "reason": "pytest missing cockpit token=secret-value",
                },
            },
        },
    ]
    completed = subprocess.run(
        [sys.executable, *args],
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        check=True,
        capture_output=True,
        text=True,
        cwd=plugin_root,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    payload = json.loads(responses[1]["result"]["content"][0]["text"])

    assert payload["status"] == "blocked"
    assert payload["schema_version"] == 2
    assert payload["action"] == "repo-hygiene-refresh"
    assert payload["dry_run"] is True
    assert payload["ok"] is False
    assert payload["result_code"] == "action_blocked"
    assert payload["audit_recorded"] is True
    assert payload["preflight"]["ok"] is False
    assert "missing_p7_operator_brief" in payload["preflight"]["hard_blockers"]
    assert "missing_p7_cockpit_smoke" in payload["preflight"]["warnings"]
    assert "missing_p7_safe_write_dry_run_smoke" in payload["preflight"]["warnings"]
    assert payload["preflight"]["p7_smoke"]["status"] == "missing"
    assert payload["preflight"]["p7_dry_run"]["status"] == "missing"
    public_text = json.dumps(payload, sort_keys=True)
    assert "secret-value" not in public_text
    assert str(tmp_path) not in public_text
    for private_key in (
        '"audit_id"',
        '"audit_path"',
        '"command"',
        '"output"',
        '"reason"',
        '"source_path"',
        '"source_paths"',
    ):
        assert private_key not in public_text

    audit_records = [
        json.loads(line)
        for line in (tmp_path / "runtime" / "control-center" / "action-audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert audit_records[-1]["action"] == "repo-hygiene-refresh"
    assert audit_records[-1]["authorized"] is False
    assert audit_records[-1]["ok"] is False
    assert "missing_p7_operator_brief" in audit_records[-1]["reason"]
    assert "secret-value" not in json.dumps(audit_records)
