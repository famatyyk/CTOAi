import json
from pathlib import Path

from scripts.ops import solteria_helper_sandbox_smoke_queue as queue


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def seed_dev_dir(tmp_path: Path) -> Path:
    dev = tmp_path / "dev"
    write_json(dev / "manifest.json", {"helper_version": "v1.1b", "created_at": "2099-01-01T00:00:00"})
    write_json(
        dev / "release_gate.json",
        {
            "status": "blocked",
            "gates": [
                {"name": "SmokePreflight", "status": "passed", "evidence": "smoke_preflight.json", "reason": ""},
                {"name": "ModuleStaticGates", "status": "passed", "evidence": "module_static_gates.json", "reason": ""},
                {
                    "name": "ModuleAttachSmoke",
                    "status": "pending",
                    "evidence": "module_attach_smoke.json",
                    "reason": "Run SmokeAttachModules after sandbox character is in-world.",
                },
                {
                    "name": "SmokeAttachAll",
                    "status": "blocked",
                    "evidence": "old-smokeall.json",
                    "reason": "SmokeAttachAll is stale for the current dev manifest.",
                },
                {"name": "live_approval", "status": "blocked", "evidence": "live_promotion.json", "reason": "approval stale"},
            ],
        },
    )
    write_json(
        dev / "smoke_status.json",
        {
            "status": "not_running",
            "next_action": "Launch the sandbox client, enter test character, then run SmokeAttachModules.",
        },
    )
    write_json(
        dev / "goal_status.json",
        {
            "status": "blocked",
            "module_audit": {
                "static_gate_summary": [
                    {
                        "module": "heal_friend",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend",
                    },
                    {
                        "module": "conditions",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions",
                    },
                    {
                        "module": "planner",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "planner_static_smoke.json",
                    },
                    {
                        "module": "runtime_policy",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "runtime_policy_static_smoke.json",
                    },
                    {
                        "module": "dispatch_guard",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "dispatch_guard_static_smoke.json",
                    },
                    {
                        "module": "plan_queue",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "plan_queue_static_smoke.json",
                    },
                    {
                        "module": "runtime_readiness",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "runtime_readiness_static_smoke.json",
                    },
                    {
                        "module": "module_status",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "module_status_static_smoke.json",
                    },
                    {
                        "module": "action_catalog",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "action_catalog_static_smoke.json",
                    },
                    {
                        "module": "decision_trace",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "decision_trace_static_smoke.json",
                    },
                    {
                        "module": "sandbox_handoff",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "sandbox_handoff_static_smoke.json",
                    },
                    {
                        "module": "feature_flags",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "feature_flags_static_smoke.json",
                    },
                    {
                        "module": "hud",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_hud",
                        "report_path": "hud_static_smoke.json",
                    },
                    {
                        "module": "hotkeys",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "hotkeys_static_smoke.json",
                    },
                    {
                        "module": "modal",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "modal_static_smoke.json",
                    },
                    {
                        "module": "route",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot",
                        "report_path": "route_static_smoke.json",
                    },
                    {
                        "module": "targeting",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting",
                        "report_path": "targeting_static_smoke.json",
                    },
                    {
                        "module": "combat_runtime",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic",
                        "report_path": "combat_runtime_static_smoke.json",
                    },
                    {
                        "module": "cavebot_runtime",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot",
                        "report_path": "cavebot_runtime_static_smoke.json",
                    },
                    {
                        "module": "loot_runtime",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag",
                        "report_path": "loot_runtime_static_smoke.json",
                    },
                    {
                        "module": "timer_runtime",
                        "status": "passed",
                        "attach_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer",
                        "report_path": "timer_runtime_static_smoke.json",
                    },
                    {
                        "module": "profile_schema",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "profile_schema_static_smoke.json",
                    },
                    {
                        "module": "external_bot_import_gate",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "external_bot_import_gate_static_smoke.json",
                    },
                    {
                        "module": "helper_shell_budget",
                        "status": "passed",
                        "attach_command": "",
                        "report_path": "helper_shell_budget_static_smoke.json",
                    },
                ]
            },
        },
    )
    return dev


def test_smoke_queue_routes_current_blockers(tmp_path: Path):
    dev = seed_dev_dir(tmp_path)

    report = queue.build_queue(dev)

    assert report["status"] == "ready_for_operator"
    assert report["runtime_status"] == "not_running"
    assert report["module_attach_status"] == "pending"
    assert report["smoke_attach_all_status"] == "blocked"
    assert report["next_action"] == "Launch sandbox client and enter test character"
    assert [step["step_id"] for step in report["steps"]] == [
        "local_ready",
        "launch_sandbox",
        "ready_check",
        "module_attach_group",
        "attach_heal_friend",
        "attach_conditions",
        "attach_hud",
        "attach_route",
        "attach_targeting",
        "attach_combat_runtime",
        "attach_cavebot_runtime",
        "attach_loot_runtime",
        "attach_timer_runtime",
        "smoke_attach_all",
        "promote_live_approval",
    ]
    assert report["steps"][0]["status"] == "passed"
    assert report["steps"][1]["command"].endswith("-Action Launch")
    assert report["steps"][-1]["command"].endswith("-ApproveLiveDeploy -SmokeReport <fresh-smokeattachall-json>")
    assert [item["module"] for item in report["static_only_modules"]] == [
        "planner",
        "runtime_policy",
        "dispatch_guard",
        "plan_queue",
        "runtime_readiness",
        "module_status",
        "action_catalog",
        "decision_trace",
        "sandbox_handoff",
        "feature_flags",
        "hotkeys",
        "modal",
        "profile_schema",
        "external_bot_import_gate",
        "helper_shell_budget",
    ]
    assert all("-Tab planner" not in step["command"] for step in report["steps"])
    assert all("-Tab runtime_policy" not in step["command"] for step in report["steps"])
    assert all("-Tab dispatch_guard" not in step["command"] for step in report["steps"])
    assert all("-Tab plan_queue" not in step["command"] for step in report["steps"])
    assert all("-Tab runtime_readiness" not in step["command"] for step in report["steps"])
    assert all("-Tab module_status" not in step["command"] for step in report["steps"])
    assert all("-Tab action_catalog" not in step["command"] for step in report["steps"])
    assert all("-Tab decision_trace" not in step["command"] for step in report["steps"])
    assert all("-Tab sandbox_handoff" not in step["command"] for step in report["steps"])
    assert all("-Tab feature_flags" not in step["command"] for step in report["steps"])
    assert all("-Tab hotkeys" not in step["command"] for step in report["steps"])
    assert all("-Tab modal" not in step["command"] for step in report["steps"])
    assert all("-Tab profile_schema" not in step["command"] for step in report["steps"])
    assert all("-Tab external_bot_import_gate" not in step["command"] for step in report["steps"])
    assert all("-Tab helper_shell_budget" not in step["command"] for step in report["steps"])
    assert any(step["command"].endswith("-Action SmokeAttach -Tab tools_hud") for step in report["steps"])
    assert any(step["command"].endswith("-Action SmokeAttach -Tab cavebot") for step in report["steps"])
    assert any(step["command"].endswith("-Action SmokeAttach -Tab hunting") for step in report["steps"])
    assert any(step["command"].endswith("-Action SmokeAttach -Tab hunting_magic") for step in report["steps"])
    assert any(step["command"].endswith("-Action SmokeAttach -Tab tools_diag") for step in report["steps"])
    assert any(step["command"].endswith("-Action SmokeAttach -Tab tools_timer") for step in report["steps"])


def test_smoke_queue_requires_static_refresh_when_preflight_missing(tmp_path: Path):
    dev = tmp_path / "dev"
    write_json(dev / "release_gate.json", {"status": "missing", "gates": []})
    write_json(dev / "smoke_status.json", {"status": "missing"})
    write_json(dev / "goal_status.json", {})

    report = queue.build_queue(dev)

    assert report["status"] == "refresh_required"
    assert report["preflight_status"] == "missing"
    assert report["steps"][0]["status"] == "required"


def test_smoke_queue_rejects_invalid_attach_tabs(tmp_path: Path):
    dev = seed_dev_dir(tmp_path)
    goal_status = json.loads((dev / "goal_status.json").read_text(encoding="utf-8"))
    goal_status["module_audit"]["static_gate_summary"][2]["attach_command"] = (
        "powershell -NoProfile -ExecutionPolicy Bypass -File "
        "scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab planner"
    )
    write_json(dev / "goal_status.json", goal_status)

    report = queue.build_queue(dev)

    commands = [step["command"] for step in report["steps"]]
    assert all("-Tab planner" not in command for command in commands)
    planner = next(item for item in report["static_only_modules"] if item["module"] == "planner")
    assert "Invalid attach tab `planner`" in planner["reason"]


def test_render_markdown_includes_live_safety_and_queue(tmp_path: Path):
    report = queue.build_queue(seed_dev_dir(tmp_path))

    markdown = queue.render_markdown(report)

    assert "# Solteria Helper Sandbox Smoke Queue" in markdown
    assert "Live safety: read-only plan" in markdown
    assert "`module_attach_group`" in markdown
    assert "## Static-Only Modules" in markdown
    assert "`planner`" in markdown
    assert "`runtime_policy`" in markdown
    assert "`dispatch_guard`" in markdown
    assert "`plan_queue`" in markdown
    assert "`runtime_readiness`" in markdown
    assert "`module_status`" in markdown
    assert "`action_catalog`" in markdown
    assert "`decision_trace`" in markdown
    assert "`sandbox_handoff`" in markdown
    assert "`feature_flags`" in markdown
    assert "`hotkeys`" in markdown
    assert "`modal`" in markdown
    assert "`external_bot_import_gate`" in markdown
    assert "`helper_shell_budget`" in markdown
    assert "SmokeAttachAll is stale" in markdown
    assert "ApproveLiveDeploy" in markdown


def test_write_text_atomic_outputs_queue_files(tmp_path: Path):
    report = queue.build_queue(seed_dev_dir(tmp_path))
    json_out = tmp_path / "queue.json"
    plan_out = tmp_path / "queue.md"

    queue.write_text_atomic(json_out, json.dumps(report, indent=2))
    queue.write_text_atomic(plan_out, queue.render_markdown(report))

    assert json.loads(json_out.read_text(encoding="utf-8"))["status"] == "ready_for_operator"
    assert "Sandbox Smoke Queue" in plan_out.read_text(encoding="utf-8")
    assert list(tmp_path.glob(".*.tmp")) == []
