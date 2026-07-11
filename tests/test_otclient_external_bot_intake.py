import json
import zipfile
from pathlib import Path

from scripts.ops import otclient_external_bot_intake as intake


def test_missing_source_reports_source_required():
    report = intake.build_report(Path("Z:/missing/vbot.zip"))

    assert report["status"] == "source_missing"
    assert report["secret_scan_status"] == "not_run"
    assert "source path does not exist" in report["blockers"]
    assert report["import_gate"]["decision"] == "source_required"
    assert report["import_gate"]["runtime_import_allowed"] is False
    assert report["import_gate"]["direct_copy_allowed"] is False


def test_directory_intake_indexes_capabilities_and_runtime_risks(tmp_path: Path):
    source = tmp_path / "vbot"
    source.mkdir()
    (source / "LICENSE").write_text("Allowed for local review.\n", encoding="utf-8")
    (source / "targeting.lua").write_text(
        "local monster = getTarget()\n"
        "g_game.attack(monster)\n"
        "say('exori')\n",
        encoding="utf-8",
    )
    (source / "cavebot.lua").write_text("autoWalk({x=1,y=2,z=7})\n", encoding="utf-8")

    report = intake.build_report(source, origin="local owner handoff")

    assert report["status"] == "ready_for_capability_mapping"
    assert report["secret_scan_status"] == "passed"
    assert report["source_sha256"]
    assert "targeting.lua" in report["capability_inventory"]["targeting"]
    assert "cavebot.lua" in report["capability_inventory"]["cavebot"]
    assert "targeting.lua" in report["runtime_action_inventory"]["attack"]
    assert "runtime action path detected: movement" in report["warnings"]
    gate = report["import_gate"]
    assert gate["decision"] == "capability_mapping_only"
    assert gate["runtime_import_allowed"] is False
    assert gate["direct_copy_allowed"] is False
    assert gate["capability_mapping"]["targeting"]["target_module"] == "ctoa_helper_targeting.lua"
    assert gate["capability_mapping"]["cavebot"]["target_module"] == "ctoa_helper_route.lua"
    assert gate["runtime_gate_mapping"]["attack"]["required_gate"] == "combat_runtime"
    assert gate["runtime_gate_mapping"]["movement"]["required_gate"] == "cavebot_runtime"
    assert "runtime actions detected" in gate["blockers"][0]


def test_secret_like_values_block_import(tmp_path: Path):
    source = tmp_path / "vbot"
    source.mkdir()
    (source / "LICENSE").write_text("review only\n", encoding="utf-8")
    (source / "config.lua").write_text("token = 'abcdef1234567890abcdef'\n", encoding="utf-8")

    report = intake.build_report(source, origin="local owner handoff")

    assert report["status"] == "review_required"
    assert report["secret_scan_status"] == "needs_review"
    assert "secret-like values require review" in report["blockers"]
    assert report["secret_files"] == ["config.lua"]
    assert report["import_gate"]["decision"] == "review_required"
    assert report["import_gate"]["runtime_import_allowed"] is False


def test_zip_intake_and_markdown_render(tmp_path: Path):
    source = tmp_path / "vbot.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("LICENSE.txt", "review allowed")
        archive.writestr("modules/hud.lua", "local hudLabel = 'HUD'\n")
        archive.writestr("modules/hotkeys.lua", "g_keyboard.bindKeyPress('Ctrl+H', cb)\n")

    report = intake.build_report(source, origin="fixture archive")
    markdown = intake.render_markdown(report)

    assert report["status"] == "ready_for_capability_mapping"
    assert "modules/hud.lua" in report["capability_inventory"]["hud"]
    assert "modules/hotkeys.lua" in report["runtime_action_inventory"]["keyboard_binding"]
    assert "# External Bot Intake Report" in markdown
    assert "Use this report as a capability checklist only" in markdown
    assert "## CTOAi Import Gate" in markdown
    assert "Decision: `capability_mapping_only`" in markdown
    assert "Runtime import allowed: `false`" in markdown
    assert "`keyboard_binding` -> `hotkeys`" in markdown


def test_write_text_atomic_outputs_json_and_markdown(tmp_path: Path):
    report = intake.build_report(tmp_path / "missing.zip")
    json_out = tmp_path / "intake.json"
    markdown_out = tmp_path / "intake.md"

    intake.write_text_atomic(json_out, json.dumps(report, indent=2))
    intake.write_text_atomic(markdown_out, intake.render_markdown(report))

    assert json.loads(json_out.read_text(encoding="utf-8"))["status"] == "source_missing"
    assert "External Bot Intake Report" in markdown_out.read_text(encoding="utf-8")
    assert list(tmp_path.glob(".*.tmp")) == []
