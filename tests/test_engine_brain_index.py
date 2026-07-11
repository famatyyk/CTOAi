from __future__ import annotations

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


def test_roadmap_generation_blocks_p8_contract_marker_drift(tmp_path, monkeypatch):
    _write_roadmap_generation_docs(tmp_path)
    monkeypatch.setattr(engine_brain_index, "ROOT", tmp_path)
    roadmap_path = tmp_path / "AI" / "P8_P16_EXECUTION_ROADMAP.md"
    required_marker = (
        "the `v2.3.0` staged-source lane and does not auto-promote that version."
    )
    roadmap_path.write_text(
        roadmap_path.read_text(encoding="utf-8").replace(
            required_marker, "the staged-source lane remains under review."
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
    p6_payload = json.loads(p6_readiness_json.read_text(encoding="utf-8"))
    p6_check_names = {check["name"] for check in p6_payload["checks"]}
    assert {
        "control_center_p7_operator_brief_config",
        "control_center_p7_operator_brief_payload",
        "control_center_p7_operator_brief_ops",
        "control_center_p7_operator_brief_ui",
        "control_center_p7_operator_brief_detail_ui",
        "control_center_p7_cockpit_smoke_script",
        "control_center_p7_cockpit_smoke_tests",
        "control_center_p7_safe_write_dry_run_smoke_script",
        "control_center_p7_safe_write_dry_run_smoke_tests",
        "control_center_p7_evidence_review_script",
        "control_center_p7_evidence_review_tests",
        "control_center_safe_write_action_catalog",
        "ctoai_plugin_control_center_cockpit_mcp_contract",
        "ctoai_plugin_control_center_cockpit_drilldown_contract",
        "ctoai_plugin_control_center_cockpit_self_check_contract",
        "ctoai_plugin_control_center_cockpit_script",
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
        "release_evidence_p7_operator_brief",
    }.issubset(p6_check_names)
    workflow_payload = json.loads(p7_operator_workflow_json.read_text(encoding="utf-8"))
    assert workflow_payload["status"] in {"safe_write_ready", "blocked"}
    assert workflow_payload["decision"] in {
        "allow_bounded_safe_write_tools",
        "fix_p6_before_operator_workflow",
    }
    assert "five audited safe_write" in workflow_payload["policy"]
    assert [tool["name"] for tool in workflow_payload["allowed_mcp_tools"]] == [
        "ctoai_engine_brain_status",
        "ctoai_engine_brain_self_check",
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
        "ctoai_repo_hygiene_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
    ]
    assert (
        "repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke"
        in p6_payload["policy"]
    )
    if "Fix blocked readiness checks" in p6_payload["recommended_next"]:
        assert "Fix blocked readiness checks" in p6_payload["recommended_next"]
    else:
        assert (
            "repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke"
            in p6_payload["recommended_next"]
        )
    assert [tool["risk_class"] for tool in workflow_payload["allowed_mcp_tools"]] == [
        "read_only",
        "read_only",
        "read_only",
        "read_only",
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
    assert action_readiness_payload["candidate_count"] == 5
    assert action_readiness_payload["mcp_write_tool_count"] in {0, 1, 2, 3, 4, 5}
    assert [
        candidate["id"]
        for candidate in action_readiness_payload["safe_write_candidates"]
    ] == [
        "repo-hygiene-refresh",
        "api-cost-refresh",
        "evidence-pack-refresh",
        "engine-brain-refresh",
        "p7-cockpit-smoke-refresh",
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
        "repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke"
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
    assert brief_payload["operator_workflow"]["status"] == workflow_payload["status"]
    assert brief_payload["operator_workflow"]["allowed_tool_count"] == 9
    assert brief_payload["operator_workflow"]["safe_write_tool_count"] == 5
    assert (
        brief_payload["action_readiness"]["status"]
        == action_readiness_payload["status"]
    )
    assert brief_payload["action_readiness"]["candidate_count"] == 5
    assert brief_payload["action_readiness"]["mcp_write_tool_count"] in {
        0,
        1,
        2,
        3,
        4,
        5,
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
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "ctoai_evidence_pack_refresh dry_run=true",
        ],
        [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "ctoai_evidence_pack_refresh dry_run=false confirm='refresh evidence pack'",
        ],
        [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "review confirmed evidence-pack-refresh audit",
        ],
        [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "design next P7 plugin action",
        ],
        [
            "ctoai_engine_brain_self_check",
            "ctoai_control_center_cockpit",
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
        "scripts/ctoai_engine_brain_brief.py",
        "scripts/ctoai_control_center_cockpit.py",
        "scripts/ctoai_engine_brain_mcp.py",
        "scripts/ctoai_engine_brain_status.py",
        "scripts/ctoai_engine_brain_self_check.py",
    ]:
        path = cache_manifest.parents[1] / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(engine_brain_index.Path, "home", lambda: tmp_path)

    check = engine_brain_index._installed_plugin_cache_check()

    assert check["status"] == "passed"
    assert "0.1.0+codex.test" in check["evidence"]


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
    assert payload["p7_operator_workflow"]["allowed_tool_count"] == 9
    assert payload["p7_action_readiness"]["status"] == "safe_write_tools_enabled"
    assert payload["p7_action_readiness"]["candidate_count"] == 5
    assert payload["p7_action_readiness"]["mcp_write_tool_count"] == 5
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
    assert checks["mcp_config"] == "passed"
    assert checks["mcp_server_script"] == "passed"
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
    assert p7_cockpit_smoke["ready_safe_write_audit_count"] == 5
    assert p7_cockpit_smoke["expected_safe_write_audit_count"] == 5
    assert p7_cockpit_smoke["action_audit_line_count"] >= 5
    dry_run_smoke = payload["workspace_status"]["p7_safe_write_dry_run_smoke"]
    assert dry_run_smoke["status"] == "ready"
    assert dry_run_smoke["check_count"] == 12
    assert dry_run_smoke["passed_count"] == 12
    assert dry_run_smoke["blocked_count"] == 0
    assert dry_run_smoke["safe_write_tool_count"] == 5
    assert dry_run_smoke["dry_run_ready_count"] == 5


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
    assert payload["operator_workflow"]["allowed_tool_count"] == 9
    assert "dangerous" in payload["operator_workflow"]["blocked_action_classes"]
    assert "safe_write" not in payload["operator_workflow"]["blocked_action_classes"]
    assert payload["action_readiness"]["status"] == "safe_write_tools_enabled"
    assert payload["action_readiness"]["candidate_count"] == 5
    assert payload["action_readiness"]["mcp_write_tool_count"] == 5
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
    assert payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["passed"] == 12
    assert payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["checks"] == 12
    assert (
        payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"]
        == 5
    )
    assert (
        payload["cockpit_handoff"]["p7_safe_write_dry_run_smoke"][
            "preflight_ready_count"
        ]
        == 5
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
    assert payload["cockpit_handoff"]["action_audit"]["status"] == "ready"
    assert payload["cockpit_handoff"]["action_audit"]["record_count"] >= 3
    assert "safe_write" in payload["cockpit_handoff"]["action_audit"]["risk_counts"]
    assert payload["cockpit_handoff"]["recommended_tool_order"] in [
        [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "review confirmed evidence-pack-refresh audit",
        ],
        [
            "ctoai_engine_brain_brief",
            "ctoai_control_center_cockpit",
            "design next P7 plugin action",
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
    completed = subprocess.run(
        [sys.executable, str(script), "--workspace", str(workspace)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


@requires_engine_brain_plugin
def test_p6_plugin_cockpit_blocks_p8_contract_marker_drift(tmp_path):
    _write_plugin_roadmap_workspace(tmp_path)
    roadmap_path = tmp_path / "AI" / "P8_P16_EXECUTION_ROADMAP.md"
    required_marker = (
        "the `v2.3.0` staged-source lane and does not auto-promote that version."
    )
    roadmap_path.write_text(
        roadmap_path.read_text(encoding="utf-8").replace(
            required_marker, "the staged-source lane remains under review."
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

    completed = subprocess.run(
        [sys.executable, str(script), "--workspace", str(engine_brain_index.ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "ready"
    assert payload["hard_blockers"] == []
    assert payload["p7_cockpit"]["status"] == "ready"
    assert payload["p7_cockpit"]["enabled_safe_write_tool_count"] == 5
    assert payload["p7_cockpit"]["ready_audit_count"] == 5
    assert payload["p7_cockpit"]["audit_count"] == 5
    assert payload["p7_cockpit"]["mcp_write_tool_count"] == 5
    assert payload["operator_next"]["status"] == "ready"
    assert payload["operator_next"]["lane"] == "p7-safe-write"
    assert payload["operator_next"]["risk_class"] == "safe_write"
    assert (
        payload["operator_next"]["source_path"] == "AI/generated/P7_OPERATOR_BRIEF.json"
    )
    assert payload["operator_next"]["title"] in {
        "Review confirmed P7 evidence",
        "Design next P7 plugin action",
    }
    assert (
        "Review confirmed evidence-pack-refresh audit"
        in payload["operator_next"]["command"]
        or "Design the next P7 plugin action" in payload["operator_next"]["command"]
    )
    assert "PromoteLiveCtoa" not in payload["operator_next"]["command"]
    assert "ApproveLiveDeploy" not in payload["operator_next"]["command"]
    assert payload["p7_cockpit_smoke"]["status"] == "ready"
    assert payload["p7_cockpit_smoke"]["check_count"] == 14
    assert payload["p7_cockpit_smoke"]["passed_count"] == 14
    assert payload["p7_cockpit_smoke"]["blocked_count"] == 0
    assert payload["p7_cockpit_smoke"]["ready_safe_write_audit_count"] == 5
    assert payload["p7_cockpit_smoke"]["expected_safe_write_audit_count"] == 5
    assert (
        payload["source_paths"]["p7_cockpit_smoke"]
        == "runtime/control-center/p7-cockpit-smoke.json"
    )
    assert payload["p7_safe_write_dry_run_smoke"]["status"] == "ready"
    assert payload["p7_safe_write_dry_run_smoke"]["check_count"] == 12
    assert payload["p7_safe_write_dry_run_smoke"]["passed_count"] == 12
    assert payload["p7_safe_write_dry_run_smoke"]["blocked_count"] == 0
    assert payload["p7_safe_write_dry_run_smoke"]["safe_write_tool_count"] == 5
    assert payload["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"] == 5
    assert payload["p7_safe_write_dry_run_smoke"]["preflight_ready_count"] == 5
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


def write_cockpit_preflight_fixture(root):
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
                    "candidate_count": 5,
                    "audited_candidate_count": 5,
                    "mcp_write_tool_count": 5,
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
    evidence_path.write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-07-07T06:30:00+00:00",
                "release_evidence_file_count": 1,
                "latest_release_evidence": {"path": "releases/evidence/CTOA-test.md"},
                "repo_hygiene": {"status": "PASS", "finding_count": 0},
                "api_cost_report": {"status": "ready", "records_seen": 0},
                "control_center_audit": {"status": "ready", "record_count": 5},
                "otclient_helper": {
                    "status": "blocked",
                    "release_gate_status": "blocked",
                    "next_action": "Run SmokeAttachModules after sandbox character is in-world.",
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
        ),
        encoding="utf-8",
    )

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
                    "allowed_tool_count": 9,
                    "read_only_tool_count": 4,
                    "safe_write_tool_count": 5,
                    "installed_cache_version": "0.1.0+codex.test",
                    "plugin_manifest_version": "0.1.0+codex.test",
                    "fresh_thread_required": True,
                    "current_thread_tool_discovery_status": "requires_fresh_thread",
                },
                "fresh_thread_verification": {
                    "status": "pending_fresh_thread",
                    "recommended_tool_order": [
                        "ctoai_engine_brain_brief",
                        "ctoai_control_center_cockpit",
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
                    "allowed_mcp_tool_count": 9,
                    "enabled_safe_write_tool_count": 5,
                    "ready_safe_write_audit_count": 5,
                    "expected_safe_write_audit_count": 5,
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
                    "safe_write_tool_count": 5,
                    "dry_run_ready_count": 5,
                    "preflight_ready_count": 5,
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
    dry_run_smoke["summary"]["preflight_ready_count"] = 4
    dry_run_smoke["summary"]["bootstrap_allowed_count"] = 1
    dry_run_smoke["safe_write_results"][0]["preflight_ok"] = False
    dry_run_smoke["safe_write_results"][0]["preflight_bootstrap_allowed"] = True
    dry_run_smoke_path.write_text(json.dumps(dry_run_smoke), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(script), "--workspace", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "needs_attention"
    assert "p7_safe_write_dry_run_smoke_not_ready" in payload["hard_blockers"]
    assert payload["operator_next"]["status"] == "blocked"
    assert payload["operator_next"]["lane"] == "p7-safe-write-dry-run-smoke"
    assert payload["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"] == 5
    assert payload["p7_safe_write_dry_run_smoke"]["preflight_ready_count"] == 4
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
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('release evidence refreshed')\n", encoding="utf-8")
    api_cost_script_path.write_text("print('api cost refreshed')\n", encoding="utf-8")
    repo_hygiene_script_path.write_text(
        "print('repo hygiene refreshed')\n",
        encoding="utf-8",
    )
    engine_brain_script_path.write_text(
        "print('engine brain refreshed')\n",
        encoding="utf-8",
    )
    p7_cockpit_smoke_script_path.write_text(
        "print('p7 cockpit smoke refreshed')\n",
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

    assert responses[0]["result"]["serverInfo"]["name"] == "ctoai-engine-brain"
    assert tools == {
        "ctoai_engine_brain_status",
        "ctoai_engine_brain_self_check",
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
        "ctoai_repo_hygiene_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
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
    for tool_name in [
        "ctoai_repo_hygiene_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
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
    assert payload["operator_workflow"]["status"] == "safe_write_ready"
    assert payload["action_readiness"]["status"] == "safe_write_tools_enabled"
    assert payload["safe_write_tool_design"]["status"] == "implemented"
    assert cockpit_payload["status"] == "ready"
    assert cockpit_payload["p7_cockpit"]["enabled_safe_write_tool_count"] == 5
    assert cockpit_payload["p7_cockpit"]["ready_audit_count"] == 5
    assert cockpit_payload["operator_next"]["status"] == "ready"
    assert cockpit_payload["operator_next"]["lane"] == "p7-safe-write"
    assert cockpit_payload["operator_next"]["risk_class"] == "safe_write"
    assert (
        cockpit_payload["operator_next"]["source_path"]
        == "AI/generated/P7_OPERATOR_BRIEF.json"
    )
    assert cockpit_payload["operator_next"]["title"] in {
        "Review confirmed P7 evidence",
        "Design next P7 plugin action",
    }
    assert (
        "Review confirmed evidence-pack-refresh audit"
        in cockpit_payload["operator_next"]["command"]
        or "Design the next P7 plugin action"
        in cockpit_payload["operator_next"]["command"]
    )
    assert "PromoteLiveCtoa" not in cockpit_payload["operator_next"]["command"]
    assert "ApproveLiveDeploy" not in cockpit_payload["operator_next"]["command"]
    assert cockpit_payload["p7_cockpit_smoke"]["status"] == "ready"
    assert cockpit_payload["p7_cockpit_smoke"]["passed_count"] == 14
    assert cockpit_payload["p7_cockpit_smoke"]["blocked_count"] == 0
    assert cockpit_payload["p7_safe_write_dry_run_smoke"]["status"] == "ready"
    assert cockpit_payload["p7_safe_write_dry_run_smoke"]["passed_count"] == 12
    assert cockpit_payload["p7_safe_write_dry_run_smoke"]["blocked_count"] == 0
    assert cockpit_payload["p7_safe_write_dry_run_smoke"]["dry_run_ready_count"] == 5
    assert cockpit_payload["p7_safe_write_dry_run_smoke"]["preflight_ready_count"] == 5
    assert (
        cockpit_payload["p7_safe_write_dry_run_smoke"]["bootstrap_allowed_count"] == 0
    )
    assert (
        cockpit_payload["source_paths"]["p7_cockpit_smoke"]
        == "runtime/control-center/p7-cockpit-smoke.json"
    )
    assert (
        cockpit_payload["source_paths"]["p7_safe_write_dry_run_smoke"]
        == "runtime/control-center/p7-safe-write-dry-run-smoke.json"
    )
    assert cockpit_payload["release_evidence"]["status"] == "ready"
    assert cockpit_payload["release_evidence"]["drilldown"]["file_count"] > 0
    assert cockpit_payload["release_evidence"]["drilldown"]["sprint_count"] > 0
    assert cockpit_payload["release_evidence"]["drilldown"]["recent_files"]
    assert cockpit_payload["roadmap_generation"]["status"] == "ready"
    assert cockpit_payload["roadmap_generation"]["doc_sync_status"] == "passed"
    assert (
        cockpit_payload["roadmap_generation"]["doc_sync_roadmap_plan3_status"]
        == "passed"
    )
    assert (
        cockpit_payload["roadmap_generation"]["doc_sync_roadmap_p8_p16_status"]
        == "passed"
    )
    assert cockpit_payload["roadmap_generation"]["ready_doc_count"] == 4
    assert cockpit_payload["roadmap_generation"]["doc_count"] == 4
    assert cockpit_payload["action_audit_drilldown"]["status"] == "ready"
    assert cockpit_payload["action_audit_drilldown"]["record_count"] >= 5
    assert cockpit_payload["action_audit_drilldown"]["truncated"] is False
    assert (
        cockpit_payload["action_audit_drilldown"]["action_counts"][
            "evidence-pack-refresh"
        ]
        >= 1
    )
    assert cockpit_payload["action_audit_drilldown"]["risk_counts"]["safe_write"] >= 5
    assert "recent_records" in cockpit_payload["action_audit_drilldown"]
    assert cockpit_payload["policy"].startswith("Read-only Control Center cockpit")
    assert hygiene_refresh_payload["status"] == "dry_run"
    assert hygiene_refresh_payload["action"] == "repo-hygiene-refresh"
    assert hygiene_refresh_payload["tool"] == "ctoai_repo_hygiene_refresh"
    assert hygiene_refresh_payload["risk_class"] == "safe_write"
    assert hygiene_refresh_payload["dry_run"] is True
    assert hygiene_refresh_payload["ok"] is True
    assert hygiene_refresh_payload["preflight"]["ok"] is True
    assert (
        hygiene_refresh_payload["preflight"]["p7_cockpit"][
            "enabled_safe_write_tool_count"
        ]
        == 5
    )
    assert hygiene_refresh_payload["preflight"]["p7_cockpit"]["ready_audit_count"] == 5
    assert hygiene_refresh_payload["preflight"]["operator_next"]["status"] == "ready"
    assert (
        hygiene_refresh_payload["preflight"]["operator_next"]["lane"] == "p7-safe-write"
    )
    assert (
        hygiene_refresh_payload["preflight"]["operator_next"]["risk_class"]
        == "safe_write"
    )
    assert (
        "ctoai_evidence_pack_refresh"
        in hygiene_refresh_payload["preflight"]["operator_next"]["command"]
    )
    assert hygiene_refresh_payload["preflight"]["p7_cockpit_smoke"] == {
        "status": "ready",
        "check_count": 14,
        "passed_count": 14,
        "blocked_count": 0,
        "ready_safe_write_audit_count": 5,
        "expected_safe_write_audit_count": 5,
    }
    assert hygiene_refresh_payload["preflight"]["p7_safe_write_dry_run_smoke"] == {
        "status": "ready",
        "check_count": 12,
        "passed_count": 12,
        "blocked_count": 0,
        "safe_write_tool_count": 5,
        "dry_run_ready_count": 5,
        "preflight_ready_count": 5,
        "bootstrap_allowed_count": 0,
    }
    assert "DRY RUN ONLY" in hygiene_refresh_payload["output"]
    assert hygiene_confirmed_payload["status"] == "completed"
    assert hygiene_confirmed_payload["action"] == "repo-hygiene-refresh"
    assert hygiene_confirmed_payload["dry_run"] is False
    assert hygiene_confirmed_payload["ok"] is True
    assert hygiene_confirmed_payload["preflight"]["ok"] is True
    assert hygiene_confirmed_payload["audit_id"] != hygiene_refresh_payload["audit_id"]
    assert hygiene_blocked_payload["status"] == "blocked"
    assert hygiene_blocked_payload["action"] == "repo-hygiene-refresh"
    assert hygiene_blocked_payload["dry_run"] is False
    assert hygiene_blocked_payload["ok"] is False
    assert hygiene_blocked_payload["preflight"]["ok"] is True
    assert (
        "confirm='refresh repo hygiene snapshot'" in hygiene_blocked_payload["output"]
    )
    assert refresh_payload["status"] == "dry_run"
    assert refresh_payload["action"] == "evidence-pack-refresh"
    assert refresh_payload["tool"] == "ctoai_evidence_pack_refresh"
    assert refresh_payload["risk_class"] == "safe_write"
    assert refresh_payload["dry_run"] is True
    assert refresh_payload["ok"] is True
    assert refresh_payload["preflight"]["ok"] is True
    assert "DRY RUN ONLY" in refresh_payload["output"]
    assert confirmed_payload["status"] == "completed"
    assert confirmed_payload["action"] == "evidence-pack-refresh"
    assert confirmed_payload["dry_run"] is False
    assert confirmed_payload["ok"] is True
    assert confirmed_payload["preflight"]["ok"] is True
    assert confirmed_payload["preflight"]["p7_cockpit_smoke"]["status"] == "ready"
    assert (
        confirmed_payload["preflight"]["p7_safe_write_dry_run_smoke"]["status"]
        == "ready"
    )
    assert confirmed_payload["audit_id"] != refresh_payload["audit_id"]
    assert api_refresh_payload["status"] == "dry_run"
    assert api_refresh_payload["action"] == "api-cost-refresh"
    assert api_refresh_payload["tool"] == "ctoai_api_cost_refresh"
    assert api_refresh_payload["risk_class"] == "safe_write"
    assert api_refresh_payload["dry_run"] is True
    assert api_refresh_payload["ok"] is True
    assert api_refresh_payload["preflight"]["ok"] is True
    assert "DRY RUN ONLY" in api_refresh_payload["output"]
    assert api_confirmed_payload["status"] == "completed"
    assert api_confirmed_payload["action"] == "api-cost-refresh"
    assert api_confirmed_payload["dry_run"] is False
    assert api_confirmed_payload["ok"] is True
    assert api_confirmed_payload["preflight"]["ok"] is True
    assert api_confirmed_payload["preflight"]["p7_cockpit_smoke"]["status"] == "ready"
    assert (
        api_confirmed_payload["preflight"]["p7_safe_write_dry_run_smoke"]["status"]
        == "ready"
    )
    assert api_confirmed_payload["audit_id"] != api_refresh_payload["audit_id"]
    assert brain_refresh_payload["status"] == "dry_run"
    assert brain_refresh_payload["action"] == "engine-brain-refresh"
    assert brain_refresh_payload["tool"] == "ctoai_engine_brain_refresh"
    assert brain_refresh_payload["risk_class"] == "safe_write"
    assert brain_refresh_payload["dry_run"] is True
    assert brain_refresh_payload["ok"] is True
    assert brain_refresh_payload["preflight"]["ok"] is True
    assert "DRY RUN ONLY" in brain_refresh_payload["output"]
    assert brain_confirmed_payload["status"] == "completed"
    assert brain_confirmed_payload["action"] == "engine-brain-refresh"
    assert brain_confirmed_payload["dry_run"] is False
    assert brain_confirmed_payload["ok"] is True
    assert brain_confirmed_payload["preflight"]["ok"] is True
    assert brain_confirmed_payload["preflight"]["p7_cockpit_smoke"]["status"] == "ready"
    assert (
        brain_confirmed_payload["preflight"]["p7_safe_write_dry_run_smoke"]["status"]
        == "ready"
    )
    assert brain_confirmed_payload["audit_id"] != brain_refresh_payload["audit_id"]
    assert p7_cockpit_smoke_refresh_payload["status"] == "dry_run"
    assert p7_cockpit_smoke_refresh_payload["action"] == "p7-cockpit-smoke-refresh"
    assert p7_cockpit_smoke_refresh_payload["tool"] == "ctoai_p7_cockpit_smoke_refresh"
    assert p7_cockpit_smoke_refresh_payload["risk_class"] == "safe_write"
    assert p7_cockpit_smoke_refresh_payload["dry_run"] is True
    assert p7_cockpit_smoke_refresh_payload["ok"] is True
    assert p7_cockpit_smoke_refresh_payload["preflight"]["ok"] is True
    assert "DRY RUN ONLY" in p7_cockpit_smoke_refresh_payload["output"]
    assert p7_cockpit_smoke_confirmed_payload["status"] == "completed"
    assert p7_cockpit_smoke_confirmed_payload["action"] == "p7-cockpit-smoke-refresh"
    assert p7_cockpit_smoke_confirmed_payload["dry_run"] is False
    assert p7_cockpit_smoke_confirmed_payload["ok"] is True
    assert p7_cockpit_smoke_confirmed_payload["preflight"]["ok"] is True
    assert (
        p7_cockpit_smoke_confirmed_payload["audit_id"]
        != p7_cockpit_smoke_refresh_payload["audit_id"]
    )
    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_records = [
        json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len({record["audit_id"] for record in audit_records}) == len(audit_records)
    assert [record["action"] for record in audit_records[-11:]] == [
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
    ]
    assert [record["dry_run"] for record in audit_records[-11:]] == [
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
    ]
    assert [record["authorized"] for record in audit_records[-11:]] == [
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
    ]
    assert [record["ok"] for record in audit_records[-11:]] == [
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
    ]
    assert all(record["risk_class"] == "safe_write" for record in audit_records[-11:])
    assert "secret-value" not in json.dumps(audit_records)
    assert all(
        "[redacted]" in record["reason"]
        for record in audit_records[-11:]
        if record["authorized"]
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
    assert payload["action"] == "repo-hygiene-refresh"
    assert payload["dry_run"] is True
    assert payload["ok"] is False
    assert payload["preflight"]["ok"] is False
    assert "missing_p7_operator_brief" in payload["preflight"]["hard_blockers"]
    assert "missing_p7_cockpit_smoke" in payload["preflight"]["warnings"]
    assert "missing_p7_safe_write_dry_run_smoke" in payload["preflight"]["warnings"]
    assert payload["preflight"]["p7_cockpit_smoke"]["status"] == "missing"
    assert payload["preflight"]["p7_safe_write_dry_run_smoke"]["status"] == "missing"
    assert "cockpit preflight failed" in payload["output"]
    assert "secret-value" not in json.dumps(payload)

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
