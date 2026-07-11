import json
from pathlib import Path

from scripts.ops import solteria_helper_goal_audit as audit


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_goal_audit_atomic_json_write_leaves_complete_artifact(tmp_path: Path):
    out = tmp_path / "goal_audit.json"

    audit.write_json_atomic(out, {"status": "blocked", "complete": False})

    assert json.loads(out.read_text(encoding="utf-8"))["complete"] is False
    assert list(tmp_path.glob(".*.tmp")) == []
    source = Path(audit.__file__).read_text(encoding="utf-8")
    assert ".{path.name}.{os.getpid()}.tmp" not in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source


def _write_base_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    plan = tmp_path / "plan.md"
    plan.write_text(
        "\n".join(
            [
                "### P0: Development Lane",
                "### P1: Runtime Observability",
                "### P2: Healing And Mana",
                "### P3: CaveBot",
                "### P4: Combat And Magic",
                "### P5: Packaging And Release",
            ]
        ),
        encoding="utf-8",
    )
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "manifest.json").write_text("{}", encoding="utf-8")
    (dev / "CHANGELOG.md").write_text("# changelog\n", encoding="utf-8")
    (dev / "ctoa_otclient_v1.1b.zip").write_bytes(b"zip")
    _write_json(dev / "validation.json", {"status": "passed"})
    _write_json(dev / "release_readiness.json", {"status": "static-passed"})
    _write_json(dev / "smoke_preflight.json", {"status": "passed"})
    _write_json(dev / "smoke_status.json", {"status": "not_running", "next_action": "Launch sandbox", "next_command": "launch"})
    _write_json(dev / "ready_check.json", {"status": "blocked_no_sandbox_window", "next_action": "Launch sandbox", "next_command": "launch"})
    _write_json(dev / "module_audit.json", {"status": "needs_modularization", "next_phase": "P6-module-lane"})
    _write_json(dev / "module_static_gates.json", {"status": "passed", "gate_count": 5, "passed_count": 5, "failed_count": 0})
    _write_json(dev / "module_attach_smoke.json", {"status": "passed", "module_count": 4, "passed_count": 4, "failed_count": 0})
    return plan, dev


def test_goal_audit_resolves_versioned_zip_from_manifest(tmp_path: Path):
    plan, dev = _write_base_artifacts(tmp_path)
    (dev / "ctoa_otclient_v1.1b.zip").rename(dev / "ctoa_otclient_v2.0.0.zip")
    _write_json(dev / "manifest.json", {"helper_version": "v2.0.0"})
    _write_json(
        dev / "release_gate.json",
        {"status": "blocked", "releasable_to_live": False, "gates": []},
    )

    result = audit.build_audit(plan, dev)

    items = {item.name: item for item in result.items}
    assert items["zip"].status == "passed"
    assert items["zip"].evidence.endswith("ctoa_otclient_v2.0.0.zip")


def test_goal_audit_reports_pending_smokeattachall(tmp_path: Path):
    plan, dev = _write_base_artifacts(tmp_path)
    _write_json(
        dev / "release_gate.json",
        {
            "status": "blocked",
            "releasable_to_live": False,
            "next_action": "Run SmokeAttachAll after sandbox character is in-world.",
            "next_command": "launch",
            "gates": [
                {"name": "SmokeAttachAll", "status": "pending", "reason": "Run SmokeAttachAll after sandbox character is in-world."},
                {"name": "live_approval", "status": "pending", "reason": "Live deployment requires explicit user approval."},
            ],
        },
    )

    result = audit.build_audit(plan, dev)

    assert result.complete is False
    assert result.status == "blocked"
    assert result.next_command == "launch"
    assert "SmokeAttachAll: Run SmokeAttachAll after sandbox character is in-world." in result.blockers
    items = {item.name: item for item in result.items}
    assert items["ready_check"].status == "blocked_no_sandbox_window"
    assert items["module_audit"].status == "needs_modularization"
    assert items["module_audit"].note == "P6-module-lane"
    assert items["module_static_gates"].status == "passed"
    assert items["module_static_gates"].note == "5/5 static gates passed"
    assert items["module_attach_smoke"].status == "passed"
    assert items["module_attach_smoke"].note == "4/4 module attach tabs passed"
    roadmap = {item.name: item.status for item in result.items if item.name.startswith("P")}
    assert roadmap["P0_development_lane"] == "passed"
    assert roadmap["P1_runtime_observability"] == "passed"
    assert roadmap["P2_healing_and_mana"] == "passed"
    assert roadmap["P3_cavebot"] == "passed"
    assert roadmap["P4_combat_and_magic"] == "passed"
    assert roadmap["P5_packaging_and_release"] == "blocked"


def test_goal_audit_can_report_complete_when_release_gate_is_releasable(tmp_path: Path):
    plan, dev = _write_base_artifacts(tmp_path)
    _write_json(
        dev / "release_gate.json",
        {
            "status": "passed",
            "releasable_to_live": True,
            "next_action": "Run PromoteLiveCtoa -ApproveLiveDeploy if the user still wants live promotion.",
            "next_command": "promote",
            "gates": [
                {"name": "SmokeAttachAll", "status": "passed", "reason": ""},
                {"name": "live_approval", "status": "passed", "reason": ""},
            ],
        },
    )

    result = audit.build_audit(plan, dev)

    assert result.complete is True
    assert result.status == "complete"
    assert result.blockers == []
    roadmap = {item.name: item.status for item in result.items if item.name.startswith("P")}
    assert roadmap["P5_packaging_and_release"] == "passed"


def test_goal_audit_keeps_empty_next_command_after_completed_live_promotion(tmp_path: Path):
    plan, dev = _write_base_artifacts(tmp_path)
    _write_json(
        dev / "release_gate.json",
        {
            "status": "passed",
            "releasable_to_live": True,
            "next_action": "Live promotion is complete for the current staged package.",
            "next_command": "",
            "gates": [
                {"name": "SmokeAttachAll", "status": "passed", "reason": ""},
                {"name": "live_approval", "status": "passed", "reason": ""},
            ],
        },
    )

    result = audit.build_audit(plan, dev)

    assert result.complete is True
    assert result.next_action == "Live promotion is complete for the current staged package."
    assert result.next_command == ""


def test_goal_audit_prefers_release_gate_promotion_command_when_only_approval_is_pending(tmp_path: Path):
    plan, dev = _write_base_artifacts(tmp_path)
    _write_json(
        dev / "release_gate.json",
        {
            "status": "blocked",
            "releasable_to_live": False,
            "next_action": "Live deployment requires explicit user approval.",
            "next_command": "promote-live",
            "gates": [
                {"name": "SmokeAttachAll", "status": "passed", "reason": ""},
                {"name": "live_approval", "status": "pending", "reason": "Live deployment requires explicit user approval."},
            ],
        },
    )

    result = audit.build_audit(plan, dev)

    assert result.complete is False
    assert result.status == "blocked"
    assert result.next_action == "Live deployment requires explicit user approval."
    assert result.next_command == "promote-live"


def test_goal_audit_renders_safe_operator_dashboard_and_terminal_summary(tmp_path: Path):
    plan, dev = _write_base_artifacts(tmp_path)
    _write_json(
        dev / "release_gate.json",
        {
            "status": "blocked",
            "releasable_to_live": False,
            "next_action": "Review <unsafe> evidence before the next smoke.",
            "next_command": "powershell -File smoke.ps1",
            "gates": [
                {"name": "SmokeAttachAll", "status": "pending", "reason": "Sandbox evidence is stale."},
            ],
        },
    )

    result = audit.build_audit(plan, dev)
    dashboard = audit.render_html(result)
    terminal = audit.render_terminal_dashboard(result)
    out = tmp_path / "goal_audit.html"
    audit.write_text_atomic(out, dashboard)

    assert "Solteria Helper Goal Audit" in dashboard
    assert "P0–P5 status" in dashboard
    assert "powershell -File smoke.ps1" in dashboard
    assert "Review &lt;unsafe&gt; evidence" in dashboard
    assert "<unsafe>" not in dashboard
    assert "<script" not in dashboard
    assert out.read_text(encoding="utf-8") == dashboard
    assert list(tmp_path.glob(".*.tmp")) == []
    assert "SOLTERIA HELPER  |  GOAL AUDIT" in terminal
    assert "COMMAND: powershell -File smoke.ps1" in terminal
