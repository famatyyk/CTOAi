import importlib.util
import json
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "control_center_p7_safe_write_dry_run_smoke.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "control_center_p7_safe_write_dry_run_smoke", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_fake_plugin(
    plugin_root: Path,
    *,
    forbidden_tool: bool = False,
    omit_full_validation_tool: bool = False,
    finalizable_bootstrap_preflight: bool = False,
    projected_schema_v2: bool = False,
) -> None:
    script_path = plugin_root / "scripts" / "fake_mcp.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        textwrap.dedent(
            f"""
            import json
            import sys
            from pathlib import Path

            TOOLS = {{
                "ctoai_repo_hygiene_refresh": "repo-hygiene-refresh",
                "ctoai_api_cost_refresh": "api-cost-refresh",
                "ctoai_evidence_pack_refresh": "evidence-pack-refresh",
                "ctoai_engine_brain_refresh": "engine-brain-refresh",
                "ctoai_p7_cockpit_smoke_refresh": "p7-cockpit-smoke-refresh",
                "ctoai_roadmap_state_refresh": "roadmap-state-refresh",
                "ctoai_full_workspace_validation_refresh": "full-workspace-validation-refresh",
            }}
            TOOL_LIST = [
                "ctoai_control_central",
                "ctoai_engine_brain_status",
                "ctoai_engine_brain_self_check",
                "ctoai_engine_brain_brief",
                "ctoai_control_center_cockpit",
                *TOOLS.keys(),
            ]
            if {str(omit_full_validation_tool)}:
                TOOLS.pop("ctoai_full_workspace_validation_refresh", None)
                TOOL_LIST.remove("ctoai_full_workspace_validation_refresh")
            if {str(forbidden_tool)}:
                TOOL_LIST.append("ctoai_live_deploy")

            def send(payload):
                print(json.dumps(payload), flush=True)

            for line in sys.stdin:
                message = json.loads(line)
                message_id = message.get("id")
                method = message.get("method")
                if method == "initialize":
                    send({{"jsonrpc": "2.0", "id": message_id, "result": {{"serverInfo": {{"name": "fake"}}}}}})
                elif method == "tools/list":
                    send({{"jsonrpc": "2.0", "id": message_id, "result": {{"tools": [{{"name": name}} for name in TOOL_LIST]}}}})
                elif method == "tools/call":
                    params = message.get("params") or {{}}
                    name = params.get("name")
                    arguments = params.get("arguments") or {{}}
                    action = TOOLS[name]
                    root = Path(arguments["workspace"])
                    audit_id = f"fake-{{action}}"
                    audit_path = root / "runtime" / "control-center" / "action-audit.jsonl"
                    audit_path.parent.mkdir(parents=True, exist_ok=True)
                    audit_path.write_text(
                        audit_path.read_text(encoding="utf-8") if audit_path.exists() else "",
                        encoding="utf-8",
                    )
                    with audit_path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps({{
                            "at": "2026-07-07T08:00:00Z",
                            "audit_id": audit_id,
                            "action": action,
                            "risk_class": "safe_write",
                            "dry_run": True,
                            "authorized": True,
                            "ok": True,
                        }}) + "\\n")
                    preflight = (
                        {{
                            "status": "needs_attention",
                            "ok": False,
                            "dry_run_bootstrap_allowed": True,
                            "hard_blockers": [
                                "p7_safe_write_audit_not_ready",
                                "p7_safe_write_dry_run_smoke_not_ready",
                            ],
                        }}
                        if {str(finalizable_bootstrap_preflight)}
                        else {{"status": "ready", "ok": True}}
                    )
                    payload = {{
                        "schema_version": 2 if {str(projected_schema_v2)} else 1,
                        "status": "dry_run",
                        "action": action,
                        "tool": name,
                        "risk_class": "safe_write",
                        "dry_run": True,
                        "ok": True,
                        "audit_recorded": True,
                        "result_code": "plan_recorded",
                        "preflight": preflight,
                    }}
                    if not {str(projected_schema_v2)}:
                        payload["audit_id"] = audit_id
                        payload["output"] = "DRY RUN ONLY\\nfixed command"
                    else:
                        payload["preflight"] = {{
                            "status": "needs_attention",
                            "ok": False,
                            "bootstrap_allowed": True,
                            "hard_blockers": [
                                "freshness:evidence:stale",
                                "p7_operator_brief_not_ready",
                                "p7_safe_write_dry_run_smoke_not_ready",
                            ],
                        }}
                    send({{"jsonrpc": "2.0", "id": message_id, "result": {{"content": [{{"type": "text", "text": json.dumps(payload)}}], "isError": False}}}})
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (plugin_root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "ctoai-engine-brain": {
                        "type": "stdio",
                        "command": "python",
                        "args": ["./scripts/fake_mcp.py"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def test_safe_write_dry_run_smoke_reports_ready(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugin"
    write_fake_plugin(plugin_root)

    report = module.build_report(tmp_path, plugin_root)

    assert report["status"] == "ready"
    assert report["hard_blockers"] == []
    assert report["summary"]["passed"] == report["summary"]["checks"]
    assert report["summary"]["dry_run_ready_count"] == 7
    assert report["summary"]["preflight_ready_count"] == 7
    assert report["summary"]["bootstrap_allowed_count"] == 0
    assert [item["status"] for item in report["safe_write_results"]] == [
        "dry_run",
        "dry_run",
        "dry_run",
        "dry_run",
        "dry_run",
        "dry_run",
        "dry_run",
    ]
    assert all(item["audit_record_ready"] for item in report["safe_write_results"])
    assert all(item["preflight_ok"] for item in report["safe_write_results"])
    assert not any(
        item["preflight_bootstrap_allowed"] for item in report["safe_write_results"]
    )


def test_safe_write_dry_run_smoke_finalizes_self_bootstrap_preflight(
    tmp_path: Path,
):
    module = load_module()
    plugin_root = tmp_path / "plugin"
    write_fake_plugin(plugin_root, finalizable_bootstrap_preflight=True)

    report = module.build_report(tmp_path, plugin_root)

    assert report["status"] == "ready"
    assert report["hard_blockers"] == []
    assert report["summary"]["dry_run_ready_count"] == 7
    assert report["summary"]["preflight_ready_count"] == 7
    assert report["summary"]["bootstrap_allowed_count"] == 0
    assert all(item["preflight_ok"] for item in report["safe_write_results"])
    assert all(
        item["preflight_bootstrap_used"] for item in report["safe_write_results"]
    )
    assert not any(
        item["preflight_bootstrap_allowed"] for item in report["safe_write_results"]
    )


def test_safe_write_dry_run_smoke_accepts_minimized_schema_v2(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugin"
    write_fake_plugin(plugin_root, projected_schema_v2=True)

    report = module.build_report(tmp_path, plugin_root)

    assert report["status"] == "ready"
    assert report["hard_blockers"] == []
    assert report["summary"]["dry_run_ready_count"] == 7
    assert report["summary"]["preflight_ready_count"] == 7
    assert report["summary"]["bootstrap_allowed_count"] == 0
    assert all(item["audit_record_ready"] for item in report["safe_write_results"])
    assert all(item["preflight_bootstrap_used"] for item in report["safe_write_results"])
    assert all("audit_id" not in item for item in report["safe_write_results"])


def test_safe_write_dry_run_smoke_blocks_forbidden_tool(tmp_path: Path):
    module = load_module()
    plugin_root = tmp_path / "plugin"
    write_fake_plugin(plugin_root, forbidden_tool=True)

    report = module.build_report(tmp_path, plugin_root)

    assert report["status"] == "blocked"
    assert "mcp_tool_policy_mismatch" in report["hard_blockers"]


def test_safe_write_dry_run_smoke_requires_full_workspace_validation_tool(
    tmp_path: Path,
):
    module = load_module()
    plugin_root = tmp_path / "plugin"
    write_fake_plugin(plugin_root, omit_full_validation_tool=True)

    report = module.build_report(tmp_path, plugin_root)

    assert report["status"] == "blocked"
    assert "mcp_tool_policy_mismatch" in report["hard_blockers"]
