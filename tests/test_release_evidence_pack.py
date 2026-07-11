import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "release_evidence_pack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_evidence_pack", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_evidence_pack_handles_missing_artifacts(tmp_path: Path):
    module = _load_module()

    pack = module.build_evidence_pack(
        tmp_path / "releases" / "evidence",
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        tmp_path / "runtime" / "solteria_helper_dev",
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )

    assert pack["release_evidence_file_count"] == 0
    assert pack["repo_hygiene"]["status"] == "missing"
    assert pack["api_cost_report"]["status"] == "missing"
    assert pack["control_center_audit"]["record_count"] == 0
    assert pack["otclient_helper"]["status"] == "missing"
    assert pack["p7_operator_brief"]["status"] == "missing"
    assert pack["p7_operator_brief"]["roadmap_generation"]["status"] == "missing"
    assert (
        "missing_p7_operator_brief"
        in pack["p7_operator_brief"]["roadmap_generation"]["hard_blockers"]
    )
    assert any("repo hygiene" in item.lower() for item in pack["recommendations"])
    assert any("api_cost_report" in item for item in pack["recommendations"])


def test_build_evidence_pack_reads_current_artifacts(tmp_path: Path):
    module = _load_module()

    releases_dir = tmp_path / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-056"
    sprint_dir.mkdir(parents=True)
    evidence_file = sprint_dir / "CTOA-300.md"
    evidence_file.write_text("# Evidence\n", encoding="utf-8")

    quality_path = tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        """
{
  "status": "PASS",
  "finding_count": 0,
  "summary": {
    "private_count": 0,
    "public_count": 0,
    "review_count": 0
  }
}
""".strip(),
        encoding="utf-8",
    )

    cost_path = tmp_path / "runtime" / "api-cost" / "latest.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(
        """
{
  "records_seen": 3,
  "total_tokens": 1234,
  "total_cost_usd": 1.25,
  "anomalies": [{"component": "prompt-forge"}]
}
""".strip(),
        encoding="utf-8",
    )

    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"ok": true}\n{"ok": false}\n', encoding="utf-8")

    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps(
            {"helper_version": "v1.1b", "files": [{"path": "ctoa_otclient_loader.lua"}]}
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "validation.json").write_text(
        json.dumps({"status": "passed"}), encoding="utf-8"
    )
    (helper_dev_dir / "release_readiness.json").write_text(
        json.dumps(
            {
                "status": "static-passed",
                "zip": {"path": "ctoa_otclient_v1.1b.zip", "sha256": "abc123"},
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "release_gate.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "releasable_to_live": False,
                "next_action": "Run SmokeAttachAll after sandbox character is in-world.",
                "next_command": "launch",
                "gates": [
                    {
                        "name": "SmokeAttachAll",
                        "status": "pending",
                        "reason": "Run SmokeAttachAll after sandbox character is in-world.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "smoke_preflight.json").write_text(
        json.dumps({"status": "passed"}), encoding="utf-8"
    )
    (helper_dev_dir / "module_contract.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "passed_count": 16,
                "check_count": 16,
                "forbidden_count": 0,
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "module_audit.json").write_text(
        json.dumps(
            {
                "status": "needs_modularization",
                "helper_budget_status": "over_budget",
                "helper_line_count": 5100,
                "helper_line_budget": 4500,
                "next_supplemental_id": "",
                "next_module_id": "heal_friend",
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "smoke_status.json").write_text(
        json.dumps({"status": "not_running"}), encoding="utf-8"
    )
    (helper_dev_dir / "goal_status.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "next_action": "Run SmokeAttachModules after sandbox character is in-world.",
                "next_command": "launch",
                "blockers": [
                    "ModuleAttachSmoke: Run SmokeAttachModules after sandbox character is in-world."
                ],
                "sandbox_smoke_queue": {
                    "status": "ready_for_operator",
                    "path": str(helper_dev_dir / "sandbox_smoke_queue.json"),
                    "runtime_status": "not_running",
                    "release_gate_status": "blocked",
                    "next_action": "Launch sandbox client and enter test character",
                    "required_count": 5,
                    "queued_count": 4,
                    "next_steps": [
                        {
                            "order": 2,
                            "step_id": "launch_sandbox",
                            "status": "required",
                            "command": "powershell -Action Launch",
                        },
                        {
                            "order": 4,
                            "step_id": "module_attach_group",
                            "status": "required",
                            "command": "powershell -Action SmokeAttachModules",
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    operator_brief_path = tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    operator_brief_path.parent.mkdir(parents=True)
    operator_brief_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-07T04:28:38+00:00",
                "decision": "ready_for_p7_operator_workflow",
                "status": "ready",
                "hard_blockers": [],
                "warnings": ["brain_doctor", "diff_check"],
                "next_safe_command": "Start a fresh Codex thread and use the ctoai_engine_brain_brief MCP tool.",
                "policy": "Read-only generated operator brief. Do not run deploy/live actions from this artifact.",
                "action_readiness": {
                    "status": "safe_write_tools_enabled",
                    "decision": "monitor_enabled_safe_write_tools",
                    "candidate_count": 5,
                    "audited_candidate_count": 5,
                    "mcp_write_tool_count": 5,
                    "enabled_safe_write_tools": [
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
                    ],
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
                    "next_safe_command": "Run ctoai_evidence_pack_refresh with dry_run=true.",
                },
                "roadmap_generation": {
                    "status": "ready",
                    "doc_sync_status": "passed",
                    "doc_count": 3,
                    "ready_doc_count": 3,
                    "hard_blockers": [],
                    "next_action": "Keep roadmap generation read-only in Control Center Evidence.",
                    "blocked_until": "risk model coverage, audit replay evidence, Control Center gates, and tests exist before adding any new MCP write tool.",
                },
            }
        ),
        encoding="utf-8",
    )

    pack = module.build_evidence_pack(
        releases_dir,
        quality_path,
        cost_path,
        audit_path,
        helper_dev_dir,
        operator_brief_path,
    )

    assert pack["release_evidence_file_count"] == 1
    assert pack["repo_hygiene"]["status"] == "PASS"
    assert pack["api_cost_report"]["status"] == "ready"
    assert pack["api_cost_report"]["records_seen"] == 3
    assert pack["api_cost_report"]["anomaly_count"] == 1
    assert pack["control_center_audit"]["record_count"] == 2
    assert pack["otclient_helper"]["status"] == "blocked"
    assert pack["otclient_helper"]["helper_version"] == "v1.1b"
    assert pack["otclient_helper"]["release_gate_status"] == "blocked"
    assert pack["otclient_helper"]["smoke_preflight_status"] == "passed"
    assert pack["otclient_helper"]["module_contract"]["status"] == "passed"
    assert pack["otclient_helper"]["module_contract"]["passed_count"] == 16
    assert pack["otclient_helper"]["module_contract"]["check_count"] == 16
    assert pack["otclient_helper"]["module_contract"]["forbidden_count"] == 0
    assert pack["otclient_helper"]["module_audit"]["status"] == "needs_modularization"
    assert pack["otclient_helper"]["module_audit"]["helper_budget_status"] == "over_budget"
    assert pack["otclient_helper"]["module_audit"]["helper_line_count"] == 5100
    assert pack["otclient_helper"]["module_audit"]["helper_line_budget"] == 4500
    assert pack["otclient_helper"]["module_audit"]["next_supplemental_id"] == ""
    assert pack["otclient_helper"]["module_audit"]["next_module_id"] == "heal_friend"
    assert pack["otclient_helper"]["package_sha256"] == "abc123"
    assert pack["otclient_helper"]["sandbox_smoke_queue"]["status"] == "ready_for_operator"
    assert pack["otclient_helper"]["sandbox_smoke_queue"]["required_count"] == 5
    assert pack["otclient_helper"]["sandbox_smoke_queue"]["queued_count"] == 4
    assert pack["otclient_helper"]["sandbox_smoke_queue"]["next_steps"][0]["step_id"] == "launch_sandbox"
    assert pack["p7_operator_brief"]["status"] == "ready"
    assert pack["p7_operator_brief"]["decision"] == "ready_for_p7_operator_workflow"
    assert pack["p7_operator_brief"]["warning_count"] == 2
    assert (
        pack["p7_operator_brief"]["action_readiness"]["status"]
        == "safe_write_tools_enabled"
    )
    assert pack["p7_operator_brief"]["action_readiness"][
        "enabled_safe_write_tools"
    ] == [
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
    assert (
        pack["p7_operator_brief"]["safe_write_tool_design"]["status"] == "implemented"
    )
    assert (
        pack["p7_operator_brief"]["safe_write_tool_design"]["proposed_mcp_tool"]
        == "ctoai_evidence_pack_refresh"
    )
    assert pack["p7_operator_brief"]["safe_write_tool_design"]["mcp_enabled"] is True
    assert pack["p7_operator_brief"]["roadmap_generation"]["status"] == "ready"
    assert (
        pack["p7_operator_brief"]["roadmap_generation"]["doc_sync_status"]
        == "passed"
    )
    assert pack["p7_operator_brief"]["roadmap_generation"]["ready_doc_count"] == 3
    assert pack["p7_operator_brief"]["roadmap_generation"]["doc_count"] == 3
    assert pack["p7_operator_brief"]["roadmap_generation"]["hard_blockers"] == []
    assert pack["latest_release_evidence"]["path"].endswith("CTOA-300.md")
    assert pack["release_sprints"][0]["sprint"] == "sprint-056"

    markdown = module.render_markdown(pack)
    assert "- P7 roadmap generation: `ready`" in markdown
    assert "- Roadmap docs ready: `3/3`" in markdown
    assert "- Sandbox smoke queue: `ready_for_operator`" in markdown
    assert "- ModuleContract: `passed` (16/16)" in markdown
    assert "### Sandbox Smoke Queue" in markdown
    assert "`launch_sandbox` `required`" in markdown


def test_build_evidence_pack_uses_configured_defaults(tmp_path: Path, monkeypatch):
    releases_dir = tmp_path / "configured" / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-099"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "CTOA-999.md").write_text("# Evidence\n", encoding="utf-8")

    quality_path = (
        tmp_path / "configured" / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    )
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        json.dumps({"status": "PASS", "finding_count": 0, "summary": {}}),
        encoding="utf-8",
    )

    cost_path = tmp_path / "configured" / "runtime" / "api-cost" / "latest.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(
        json.dumps({"records_seen": 1, "total_tokens": 10, "total_cost_usd": 0.1}),
        encoding="utf-8",
    )

    audit_path = (
        tmp_path / "configured" / "runtime" / "control-center" / "action-audit.jsonl"
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"ok": true}\n', encoding="utf-8")

    helper_dev_dir = tmp_path / "configured" / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps({"helper_version": "v1.1b", "files": []}), encoding="utf-8"
    )
    operator_brief_path = (
        tmp_path / "configured" / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    )
    operator_brief_path.parent.mkdir(parents=True)
    operator_brief_path.write_text(
        json.dumps({"status": "ready", "decision": "ready_for_p7_operator_workflow"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("CTOA_RELEASES_DIR", str(releases_dir))
    monkeypatch.setenv("CTOA_REPO_HYGIENE_PATH", str(quality_path))
    monkeypatch.setenv("CTOA_API_COST_REPORT_PATH", str(cost_path))
    monkeypatch.setenv("CTOA_ACTION_AUDIT_PATH", str(audit_path))
    monkeypatch.setenv("CTOA_HELPER_DEV_DIR", str(helper_dev_dir))
    monkeypatch.setenv(
        "CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH", str(operator_brief_path)
    )

    module = _load_module()
    pack = module.build_evidence_pack()

    assert pack["releases_dir"] == str(releases_dir).replace("\\", "/")
    assert pack["quality_path"] == str(quality_path).replace("\\", "/")
    assert pack["cost_report_path"] == str(cost_path).replace("\\", "/")
    assert pack["action_audit_path"] == str(audit_path).replace("\\", "/")
    assert pack["helper_dev_dir"] == str(helper_dev_dir).replace("\\", "/")
    assert pack["engine_brain_operator_brief_path"] == str(operator_brief_path).replace(
        "\\", "/"
    )
    assert pack["otclient_helper"]["helper_version"] == "v1.1b"
    assert pack["p7_operator_brief"]["decision"] == "ready_for_p7_operator_workflow"
    assert pack["latest_release_evidence"]["path"].endswith("CTOA-999.md")


def test_build_evidence_pack_rejects_symlinked_configured_json_and_audit(
    tmp_path: Path,
):
    module = _load_module()
    releases_dir = tmp_path / "releases" / "evidence"
    releases_dir.mkdir(parents=True)
    quality_path = tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    quality_path.parent.mkdir(parents=True)
    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True)
    outside_quality = tmp_path / "outside-quality.json"
    outside_audit = tmp_path / "outside-audit.jsonl"
    outside_quality.write_text(
        json.dumps({"status": "PASS", "finding_count": 0}), encoding="utf-8"
    )
    outside_audit.write_text(
        '{"ok": true, "token": "audit-secret-token"}\n', encoding="utf-8"
    )

    try:
        quality_path.symlink_to(outside_quality)
        audit_path.symlink_to(outside_audit)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    pack = module.build_evidence_pack(
        releases_dir,
        quality_path,
        tmp_path / "runtime" / "api-cost" / "latest.json",
        audit_path,
        tmp_path / "runtime" / "solteria_helper_dev",
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )
    serialized = json.dumps(pack)

    assert pack["repo_hygiene"]["status"] == "missing"
    assert pack["control_center_audit"]["record_count"] == 0
    assert "audit-secret-token" not in serialized
    assert "outside-quality.json" not in serialized
    assert "outside-audit.jsonl" not in serialized


def test_build_evidence_pack_ignores_symlinked_release_markdown(tmp_path: Path):
    module = _load_module()
    releases_dir = tmp_path / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-777"
    sprint_dir.mkdir(parents=True)
    outside_markdown = tmp_path / "outside-evidence.md"
    linked_markdown = sprint_dir / "CTOA-777.md"
    outside_markdown.write_text(
        "# External evidence\nsecret=outside-markdown-secret\n", encoding="utf-8"
    )

    try:
        linked_markdown.symlink_to(outside_markdown)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    pack = module.build_evidence_pack(
        releases_dir,
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        tmp_path / "runtime" / "solteria_helper_dev",
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )
    serialized = json.dumps(pack)

    assert pack["release_evidence_file_count"] == 0
    assert pack["latest_release_evidence"] is None
    assert pack["release_sprints"][0]["file_count"] == 0
    assert "outside-markdown-secret" not in serialized
    assert "outside-evidence.md" not in serialized


def test_build_evidence_pack_rejects_symlinked_p7_operator_brief(tmp_path: Path):
    module = _load_module()
    releases_dir = tmp_path / "releases" / "evidence"
    releases_dir.mkdir(parents=True)
    operator_brief_path = tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json"
    operator_brief_path.parent.mkdir(parents=True)
    outside_brief = tmp_path / "outside-p7-brief.json"
    outside_brief.write_text(
        json.dumps(
            {
                "status": "ready",
                "decision": "secret decision token=operator-secret-token",
                "next_safe_command": "leak password=operator-secret-password",
            }
        ),
        encoding="utf-8",
    )

    try:
        operator_brief_path.symlink_to(outside_brief)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    pack = module.build_evidence_pack(
        releases_dir,
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        tmp_path / "runtime" / "solteria_helper_dev",
        operator_brief_path,
    )
    serialized = json.dumps(pack)

    assert pack["p7_operator_brief"]["status"] == "missing"
    assert pack["p7_operator_brief"]["decision"] == "missing"
    assert "operator-secret-token" not in serialized
    assert "operator-secret-password" not in serialized
    assert "outside-p7-brief.json" not in serialized


def test_helper_status_rejects_symlinked_helper_dev_dir(tmp_path: Path):
    module = _load_module()
    outside_helper = tmp_path / "outside-helper"
    outside_helper.mkdir()
    (outside_helper / "manifest.json").write_text(
        json.dumps({"helper_version": "v9-unsafe", "files": []}),
        encoding="utf-8",
    )
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.parent.mkdir(parents=True)

    try:
        helper_dev_dir.symlink_to(outside_helper, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are not available: {exc}")

    status = module._helper_status(helper_dev_dir)

    assert status["status"] == "missing"
    assert status["helper_version"] == "unknown"


def test_helper_status_blocks_inconsistent_releasable_gate_with_pending_blocker(
    tmp_path: Path,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps({"helper_version": "v1.1b", "files": []}), encoding="utf-8"
    )
    (helper_dev_dir / "release_gate.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "releasable_to_live": True,
                "gates": [
                    {
                        "name": "live_approval",
                        "status": "pending",
                        "reason": "Live deployment requires explicit user approval.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = module._helper_status(helper_dev_dir)

    assert status["release_gate_releasable_to_live"] is True
    assert status["releasable_to_live"] is False
    assert status["status"] == "blocked"
    assert status["blockers"] == [
        "live_approval: Live deployment requires explicit user approval."
    ]


def test_helper_status_promoted_requires_durable_live_promotion_evidence(
    tmp_path: Path,
):
    module = _load_module()
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "manifest.json").write_text(
        json.dumps(
            {"helper_version": "v1.1b", "files": [{"path": "ctoa_native_helper.lua"}]}
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "release_readiness.json").write_text(
        json.dumps(
            {
                "status": "static-passed",
                "zip": {"path": "ctoa_otclient_v1.1b.zip", "sha256": "abc123"},
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "release_gate.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "releasable_to_live": True,
                "next_action": "Release gate passed.",
                "next_command": "",
                "gates": [
                    {"name": "PrepareDev", "status": "passed"},
                    {"name": "ValidateDev", "status": "passed"},
                    {
                        "name": "live_approval",
                        "status": "passed",
                        "evidence": "runtime/solteria_helper_dev/live_promotion.json",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "goal_status.json").write_text(
        json.dumps(
            {"next_command": "stale command that must not leak into promoted evidence"}
        ),
        encoding="utf-8",
    )
    (helper_dev_dir / "live_promotion.json").write_text(
        json.dumps(
            {
                "created_at": "2026-07-06T11:06:46",
                "approval_switch": "ApproveLiveDeploy",
                "live_client": "C:/Users/zycie/AppData/Local/Solteria/client",
                "backup": "runtime/solteria_helper_dev/live_backup_20260706-110646",
            }
        ),
        encoding="utf-8",
    )

    status = module._helper_status(helper_dev_dir)

    assert status["status"] == "promoted"
    assert status["releasable_to_live"] is True
    assert status["live_promoted"] is True
    assert status["live_promotion_status"] == "promoted"
    assert status["live_promotion_created_at"] == "2026-07-06T11:06:46"
    assert status["next_command"] == ""
    assert status["paths"]["live_promotion"].endswith("live_promotion.json")
