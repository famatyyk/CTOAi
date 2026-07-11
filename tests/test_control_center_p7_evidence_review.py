import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "control_center_p7_evidence_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("control_center_p7_evidence_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_ready_fixture(root: Path):
    generated = root / "AI" / "generated"
    runtime = root / "runtime" / "control-center"
    write_json(
        generated / "P7_OPERATOR_BRIEF.json",
        {
            "generated_at": "2026-07-07T23:53:39+00:00",
            "status": "ready",
            "decision": "ready_for_p7_operator_workflow",
            "hard_blockers": [],
            "next_safe_command": "Review confirmed evidence-pack-refresh audit evidence in runtime/control-center/action-audit.jsonl and runtime/evidence/latest.json; design the next P7 plugin action only after risk model coverage, audit logging, Control Center gates, and targeted MCP tests exist.",
        },
    )
    write_json(
        root / "runtime" / "evidence" / "latest.json",
        {
            "generated_at_utc": "2026-07-07T23:58:51+00:00",
            "p7_operator_brief": {
                "generated_at": "2026-07-07T23:53:39+00:00",
                "status": "ready",
                "decision": "ready_for_p7_operator_workflow",
                "hard_blocker_count": 0,
            },
            "control_center_audit": {"status": "ready", "record_count": 116},
        },
    )
    audit_path = runtime / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "at": "2026-07-07T23:58:50.995917Z",
                        "audit_id": "audit-dry-run",
                        "action": "evidence-pack-refresh",
                        "risk_class": "safe_write",
                        "dry_run": True,
                        "authorized": True,
                        "ok": True,
                    }
                ),
                json.dumps(
                    {
                        "at": "2026-07-07T23:58:51.115292Z",
                        "audit_id": "audit-confirmed",
                        "action": "evidence-pack-refresh",
                        "risk_class": "safe_write",
                        "dry_run": False,
                        "authorized": True,
                        "ok": True,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        runtime / "p7-cockpit-smoke.json",
        {
            "generated_at": "2026-07-07T23:59:06+00:00",
            "status": "ready",
            "summary": {
                "checks": 14,
                "passed": 14,
                "blocked": 0,
            },
            "safe_write_audits": [
                {
                    "action_id": "evidence-pack-refresh",
                    "mcp_tool": "ctoai_evidence_pack_refresh",
                    "ready": True,
                    "authorized": True,
                    "ok": True,
                    "dry_run": False,
                    "risk_class": "safe_write",
                    "at": "2026-07-07T23:58:51.115292Z",
                    "audit_id": "audit-confirmed",
                }
            ],
        },
    )
    write_json(
        runtime / "p7-safe-write-dry-run-smoke.json",
        {
            "status": "ready",
            "summary": {
                "checks": 12,
                "passed": 12,
                "blocked": 0,
                "safe_write_tool_count": 5,
                "dry_run_ready_count": 5,
                "preflight_ready_count": 5,
                "bootstrap_allowed_count": 0,
            },
        },
    )
    write_json(
        runtime / "p6-plugin-handoff-smoke.json",
        {
            "status": "ready",
            "summary": {
                "checks": 17,
                "passed": 17,
                "blocked": 0,
            },
        },
    )


def test_p7_evidence_review_reports_ready(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)

    report = module.build_report(tmp_path)

    assert report["status"] == "ready"
    assert report["outcome"] == "ready_to_design_next_p7_plugin_action"
    assert report["hard_blockers"] == []
    assert report["summary"]["confirmed_audit_id"] == "audit-confirmed"
    assert report["summary"]["passed"] == report["summary"]["checks"]
    assert "risk model coverage" in report["next_action"]


def test_p7_evidence_review_blocks_without_confirmed_audit(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)
    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for record in records:
        record["dry_run"] = True
    audit_path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    report = module.build_report(tmp_path)

    assert report["status"] == "blocked"
    assert "missing_confirmed_evidence_pack_audit" in report["hard_blockers"]


def test_p7_evidence_review_accepts_design_next_operator_brief(tmp_path: Path):
    module = load_module()
    write_ready_fixture(tmp_path)
    brief_path = tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["next_safe_command"] = (
        "Design the next P7 plugin action only after risk model coverage, "
        "audit logging, Control Center gates, and targeted MCP tests exist; "
        "keep deploy/live actions outside the plugin surface."
    )
    brief_path.write_text(json.dumps(brief), encoding="utf-8")

    report = module.build_report(tmp_path)

    assert report["status"] == "ready"
    assert {check["name"]: check["status"] for check in report["checks"]}[
        "operator_brief_review_or_design_ready"
    ] == "passed"
