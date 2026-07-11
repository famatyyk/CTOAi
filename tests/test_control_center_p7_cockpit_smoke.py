import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "control_center_p7_cockpit_smoke.py"
ROADMAP_DOCS = [
    {
        "name": "feature_roadmap",
        "path": "AI/FEATURE_ROADMAP.md",
        "status": "passed",
        "missing_markers": [],
    },
    {
        "name": "engine_brain_status",
        "path": "AI/ENGINE_BRAIN_STATUS.md",
        "status": "passed",
        "missing_markers": [],
    },
    {
        "name": "p8_p16_execution_roadmap",
        "path": "AI/P8_P16_EXECUTION_ROADMAP.md",
        "status": "passed",
        "missing_markers": [],
    },
    {
        "name": "plan3_roadmap",
        "path": "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md",
        "status": "passed",
        "missing_markers": [],
    },
]


def load_module():
    spec = importlib.util.spec_from_file_location("control_center_p7_cockpit_smoke", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_ready_fixture(root: Path):
    generated = root / "AI" / "generated"
    runtime = root / "runtime"
    safe_tools = [
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
    write_json(
        generated / "manifest.json",
        {
            "doc_sync_status": "passed",
            "secret_guardrail_status": "passed",
            "p6_readiness_status": "ready_for_plugin_design",
            "p7_operator_workflow_status": "safe_write_ready",
            "p7_action_readiness_status": "safe_write_tools_enabled",
            "p7_safe_write_tool_design_status": "implemented",
            "p7_operator_brief_status": "ready",
        },
    )
    write_json(
        generated / "P7_OPERATOR_WORKFLOW.json",
        {
            "status": "safe_write_ready",
            "allowed_mcp_tools": [
                {"name": "ctoai_engine_brain_status", "risk_class": "read_only"},
                {"name": "ctoai_engine_brain_self_check", "risk_class": "read_only"},
                {"name": "ctoai_engine_brain_brief", "risk_class": "read_only"},
                {"name": "ctoai_control_center_cockpit", "risk_class": "read_only"},
                {"name": "ctoai_repo_hygiene_refresh", "risk_class": "safe_write"},
                {"name": "ctoai_api_cost_refresh", "risk_class": "safe_write"},
                {"name": "ctoai_evidence_pack_refresh", "risk_class": "safe_write"},
                {"name": "ctoai_engine_brain_refresh", "risk_class": "safe_write"},
                {"name": "ctoai_p7_cockpit_smoke_refresh", "risk_class": "safe_write"},
            ],
        },
    )
    write_json(
        generated / "P7_ACTION_READINESS.json",
        {
            "status": "safe_write_tools_enabled",
            "candidate_count": 5,
            "audited_candidate_count": 5,
            "unexpected_mcp_write_tools": [],
            "enabled_safe_write_tools": safe_tools,
        },
    )
    write_json(
        generated / "P7_SAFE_WRITE_TOOL_DESIGN.json",
        {
            "status": "implemented",
            "decision": "ready_for_dry_run_operation",
            "mode": "dry_run_first",
            "mcp_enabled": True,
            "risk_class": "safe_write",
            "proposed_mcp_tool": "ctoai_evidence_pack_refresh",
        },
    )
    write_json(
        generated / "P7_OPERATOR_BRIEF.json",
        {
            "generated_at": "2026-07-07T06:40:00+00:00",
            "status": "ready",
            "decision": "ready_for_p7_operator_workflow",
            "hard_blockers": [],
            "roadmap_generation": {
                "status": "ready",
                "doc_sync_status": "passed",
                "doc_count": len(ROADMAP_DOCS),
                "ready_doc_count": len(ROADMAP_DOCS),
                "hard_blockers": [],
                "docs": ROADMAP_DOCS,
            },
        },
    )
    write_json(
        runtime / "evidence" / "latest.json",
        {
            "p7_operator_brief": {
                "generated_at": "2026-07-07T06:40:00+00:00",
                "status": "ready",
                "decision": "ready_for_p7_operator_workflow",
                "hard_blocker_count": 0,
                "roadmap_generation": {
                    "status": "ready",
                    "doc_sync_status": "passed",
                    "doc_count": len(ROADMAP_DOCS),
                    "ready_doc_count": len(ROADMAP_DOCS),
                    "hard_blockers": [],
                },
            },
            "control_center_audit": {"status": "ready", "record_count": 5},
        },
    )
    audit_path = runtime / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "at": f"2026-07-07T06:4{index}:00Z",
                    "action": tool["action_id"],
                    "risk_class": "safe_write",
                    "authorized": True,
                    "ok": True,
                    "dry_run": index < 2,
                    "audit_id": f"audit-{index}",
                }
            )
            for index, tool in enumerate(safe_tools, start=1)
        )
        + "\n",
        encoding="utf-8",
    )


def test_p7_cockpit_smoke_reports_ready(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)

    report = module.build_report(tmp_path)

    assert report["status"] == "ready"
    assert report["hard_blockers"] == []
    assert report["summary"]["passed"] == report["summary"]["checks"]
    assert {check["name"]: check["status"] for check in report["checks"]}[
        "operator_brief_roadmap_generation"
    ] == "passed"
    assert report["summary"]["allowed_mcp_tool_count"] == 9
    assert report["summary"]["enabled_safe_write_tool_count"] == 5
    assert report["summary"]["ready_safe_write_audit_count"] == 5
    assert [audit["ready"] for audit in report["safe_write_audits"]] == [True, True, True, True, True]


def test_p7_cockpit_smoke_blocks_missing_safe_write_audit(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)
    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = [record for record in records if record["action"] != "api-cost-refresh"]
    audit_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    report = module.build_report(tmp_path)

    assert report["status"] == "blocked"
    assert "action_audit_missing_ready_safe_write_record" in report["hard_blockers"]
    api_audit = next(audit for audit in report["safe_write_audits"] if audit["action_id"] == "api-cost-refresh")
    assert api_audit["ready"] is False


def test_p7_cockpit_smoke_blocks_forbidden_plugin_tool(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)
    workflow_path = tmp_path / "AI" / "generated" / "P7_OPERATOR_WORKFLOW.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow["allowed_mcp_tools"][-1]["name"] = "ctoai_live_deploy"
    workflow_path.write_text(json.dumps(workflow), encoding="utf-8")

    report = module.build_report(tmp_path)

    assert report["status"] == "blocked"
    assert "workflow_tool_policy_mismatch" in report["hard_blockers"]


def test_p7_cockpit_smoke_rejects_legacy_three_of_three_roadmap(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)
    operator_brief_path = (
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    )
    operator_brief = json.loads(operator_brief_path.read_text(encoding="utf-8"))
    roadmap_generation = operator_brief["roadmap_generation"]
    roadmap_generation["docs"] = ROADMAP_DOCS[:-1]
    roadmap_generation["doc_count"] = len(ROADMAP_DOCS) - 1
    roadmap_generation["ready_doc_count"] = len(ROADMAP_DOCS) - 1
    operator_brief_path.write_text(json.dumps(operator_brief), encoding="utf-8")
    release_evidence_path = tmp_path / "runtime" / "evidence" / "latest.json"
    release_evidence = json.loads(release_evidence_path.read_text(encoding="utf-8"))
    release_roadmap = release_evidence["p7_operator_brief"]["roadmap_generation"]
    release_roadmap["doc_count"] = len(ROADMAP_DOCS) - 1
    release_roadmap["ready_doc_count"] = len(ROADMAP_DOCS) - 1
    release_evidence_path.write_text(json.dumps(release_evidence), encoding="utf-8")

    report = module.build_report(tmp_path)

    assert report["status"] == "blocked"
    assert (
        "operator_brief_roadmap_generation_not_ready" in report["hard_blockers"]
    )
    assert "release_evidence_not_p7_ready" in report["hard_blockers"]


def test_p7_cockpit_smoke_rejects_symlinked_operator_brief(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)
    operator_brief = tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    outside = tmp_path / "outside-brief.json"
    outside.write_text(json.dumps({"status": "ready"}), encoding="utf-8")
    operator_brief.unlink()
    try:
        operator_brief.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")

    report = module.build_report(tmp_path)

    assert report["status"] == "blocked"
    assert "missing_or_invalid_operator_brief" in report["hard_blockers"]
