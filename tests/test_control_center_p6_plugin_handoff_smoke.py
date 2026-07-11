import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "control_center_p6_plugin_handoff_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "control_center_p6_plugin_handoff_smoke", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_ready_fixture(root: Path, plugin_root: Path):
    generated = root / "AI" / "generated"
    runtime = root / "runtime" / "control-center"
    allowed_tools = [
        {"name": "ctoai_engine_brain_status", "risk_class": "read_only"},
        {"name": "ctoai_engine_brain_self_check", "risk_class": "read_only"},
        {"name": "ctoai_engine_brain_brief", "risk_class": "read_only"},
        {"name": "ctoai_control_center_cockpit", "risk_class": "read_only"},
        {"name": "ctoai_repo_hygiene_refresh", "risk_class": "safe_write"},
        {"name": "ctoai_api_cost_refresh", "risk_class": "safe_write"},
        {"name": "ctoai_evidence_pack_refresh", "risk_class": "safe_write"},
        {"name": "ctoai_engine_brain_refresh", "risk_class": "safe_write"},
        {"name": "ctoai_p7_cockpit_smoke_refresh", "risk_class": "safe_write"},
    ]
    write_json(
        generated / "P6_CODEX_INTEGRATION_READINESS.json",
        {
            "status": "ready_for_plugin_design",
            "policy": "P6 plugin handoff fixture.",
            "recommended_next": "Open a fresh Codex thread and verify plugin tools.",
            "checks": [
                {
                    "name": "ctoai_plugin_marketplace_entry",
                    "status": "passed",
                    "evidence": "personal marketplace entry",
                },
                {
                    "name": "ctoai_plugin_installed_cache",
                    "status": "passed",
                    "evidence": "installed personal cache version 0.1.0+codex.test",
                },
                {
                    "name": "ctoai_plugin_control_center_cockpit_mcp_contract",
                    "status": "passed",
                    "evidence": "home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py",
                },
                {
                    "name": "ctoai_plugin_p7_cockpit_smoke_refresh_mcp_contract",
                    "status": "passed",
                    "evidence": "home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py",
                },
            ],
        },
    )
    write_json(
        generated / "P7_OPERATOR_WORKFLOW.json",
        {
            "status": "safe_write_ready",
            "allowed_mcp_tools": allowed_tools,
            "blocked_action_classes": [
                {"risk_class": "guarded_write"},
                {"risk_class": "dangerous"},
                {"risk_class": "forbidden_ui"},
            ],
        },
    )
    write_json(
        generated / "P7_OPERATOR_BRIEF.json",
        {
            "status": "ready",
            "decision": "ready_for_p7_operator_workflow",
            "hard_blockers": [],
            "cockpit_handoff": {"status": "ready"},
        },
    )
    write_json(
        runtime / "p7-cockpit-smoke.json",
        {
            "status": "ready",
            "summary": {
                "checks": 14,
                "passed": 14,
                "blocked": 0,
                "enabled_safe_write_tool_count": 5,
            },
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
        plugin_root / ".codex-plugin" / "plugin.json",
        {
            "name": "ctoai-engine-brain",
            "version": "0.1.0+codex.test",
            "description": "test plugin",
        },
    )
    mcp_script = plugin_root / "scripts" / "ctoai_engine_brain_mcp.py"
    mcp_script.parent.mkdir(parents=True, exist_ok=True)
    mcp_script.write_text("# fixture\n", encoding="utf-8")
    write_json(
        plugin_root / ".mcp.json",
        {
            "mcpServers": {
                "ctoai-engine-brain": {
                    "type": "stdio",
                    "command": "python",
                    "args": [str(mcp_script)],
                }
            }
        },
    )


def test_p6_plugin_handoff_smoke_reports_ready(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    write_ready_fixture(tmp_path, plugin_root)

    report = module.build_report(tmp_path, plugin_root=plugin_root)

    assert report["status"] == "ready"
    assert report["hard_blockers"] == []
    assert report["summary"]["passed"] == report["summary"]["checks"]
    assert report["summary"]["p6_passed_count"] == report["summary"]["p6_check_count"]
    assert report["summary"]["mcp_contract_count"] == 2
    assert report["summary"]["passed_mcp_contract_count"] == 2
    assert report["summary"]["allowed_tool_count"] == 9
    assert report["summary"]["safe_write_tool_count"] == 5
    assert report["summary"]["installed_cache_version"] == "0.1.0+codex.test"
    assert report["summary"]["plugin_manifest_version"] == "0.1.0+codex.test"
    assert report["summary"]["fresh_thread_required"] is True
    assert report["summary"]["current_thread_tool_discovery_status"] == "requires_fresh_thread"
    assert report["fresh_thread_verification"]["status"] == "pending_fresh_thread"
    assert report["fresh_thread_verification"]["recommended_tool_order"] == [
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
        "ctoai_engine_brain_self_check",
    ]
    assert report["source_paths"]["plugin_manifest"].endswith(
        "ctoai-engine-brain/.codex-plugin/plugin.json"
    )
    assert report["source_paths"]["plugin_mcp_config"].endswith(
        "ctoai-engine-brain/.mcp.json"
    )


def test_p6_plugin_handoff_smoke_blocks_version_mismatch(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    write_ready_fixture(tmp_path, plugin_root)
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "0.1.0+codex.other"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = module.build_report(tmp_path, plugin_root=plugin_root)

    assert report["status"] == "blocked"
    assert "plugin_manifest_version_mismatch" in report["hard_blockers"]


def test_p6_plugin_handoff_smoke_blocks_missing_cache(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    write_ready_fixture(tmp_path, plugin_root)
    p6_path = tmp_path / "AI" / "generated" / "P6_CODEX_INTEGRATION_READINESS.json"
    p6 = json.loads(p6_path.read_text(encoding="utf-8"))
    p6["checks"] = [
        check
        for check in p6["checks"]
        if check["name"] != "ctoai_plugin_installed_cache"
    ]
    p6_path.write_text(json.dumps(p6), encoding="utf-8")

    report = module.build_report(tmp_path, plugin_root=plugin_root)

    assert report["status"] == "blocked"
    assert "p6_installed_cache_not_ready" in report["hard_blockers"]


def test_p6_plugin_handoff_smoke_blocks_relative_mcp_script_path(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    write_ready_fixture(tmp_path, plugin_root)
    mcp_path = plugin_root / ".mcp.json"
    mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
    mcp["mcpServers"]["ctoai-engine-brain"]["args"] = [
        "./scripts/ctoai_engine_brain_mcp.py"
    ]
    mcp_path.write_text(json.dumps(mcp), encoding="utf-8")

    report = module.build_report(tmp_path, plugin_root=plugin_root)

    assert report["status"] == "blocked"
    assert "plugin_mcp_start_path_not_runnable" in report["hard_blockers"]


def test_p6_plugin_handoff_smoke_rejects_symlinked_p6_readiness(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugins" / "ctoai-engine-brain"
    write_ready_fixture(tmp_path, plugin_root)
    p6_path = tmp_path / "AI" / "generated" / "P6_CODEX_INTEGRATION_READINESS.json"
    outside = tmp_path / "outside-p6.json"
    outside.write_text(json.dumps({"status": "ready_for_plugin_design"}), encoding="utf-8")
    p6_path.unlink()
    try:
        p6_path.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")

    report = module.build_report(tmp_path, plugin_root=plugin_root)

    assert report["status"] == "blocked"
    assert "missing_or_invalid_p6_readiness" in report["hard_blockers"]
