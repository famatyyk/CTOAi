import json
from dataclasses import asdict

from scripts.ops import otclient_input_contract_fixtures as fixtures


def test_input_contract_fixture_report_covers_hotkeys_and_modal_states():
    report = fixtures.build_report()

    assert report.name == "otclient-helper-input-contract-fixtures"
    assert report.status == "passed"
    assert report.check_count == 16
    assert report.passed_count == 16
    assert report.failed_count == 0
    assert len(report.hotkey_checks) == 9
    assert len(report.modal_checks) == 7

    hotkey_names = {item.name: item for item in report.hotkey_checks}
    assert hotkey_names["modifier_order_normalizes_ctrl_h"].expected == {
        "input": " ctrl + h ",
        "valid": True,
        "normalized": "Ctrl+H",
        "reason": "ok",
    }
    assert hotkey_names["binding_decision_reports_changed_allowed_choice"].expected["reason"] == "changed"
    assert hotkey_names["binding_decision_rejects_disallowed_choice"].expected["reason"] == "not_allowed"
    assert hotkey_names["reserved_keys_are_rejected"].expected["reason"] == "reserved_key"

    modal_names = {item.name: item for item in report.modal_checks}
    assert modal_names["request_builds_bounded_confirmation"].expected["expires_at_ms"] == 5500
    assert modal_names["guarded_action_requires_confirmation"].expected["reason"] == "confirmation_required"
    assert modal_names["confirmed_guarded_action_is_allowed"].expected["allowed"] is True
    assert modal_names["expired_guarded_action_is_blocked"].expected["decision_text"] == "confirmation expired"
    assert "does not launch" in report.live_safety


def test_input_contract_fixture_markdown_and_json_outputs(tmp_path):
    json_out = tmp_path / "input_contract_fixtures.json"
    plan_out = tmp_path / "solteria_helper_input_contracts.md"
    report = fixtures.build_report()

    fixtures.write_json_atomic(json_out, asdict(report))
    fixtures.write_text_atomic(plan_out, fixtures.render_markdown(report))

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = plan_out.read_text(encoding="utf-8")

    assert payload["status"] == "passed"
    assert payload["check_count"] == 16
    assert payload["hotkey_checks"][0]["name"] == "modifier_order_normalizes_ctrl_h"
    assert payload["modal_checks"][-1]["name"] == "decision_text_covers_allow_deny_states"
    assert "# Solteria Helper Input Contracts" in markdown
    assert "Hotkey Fixtures" in markdown
    assert "Modal Fixtures" in markdown
    assert "InputContractsStaticSmoke" in markdown
    assert "confirmation required: cavebot delete" in markdown
