from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


PLUGIN_SCRIPTS = Path.home() / "plugins" / "ctoai-engine-brain" / "scripts"
pytestmark = pytest.mark.skipif(
    not PLUGIN_SCRIPTS.is_dir(),
    reason="Engine Brain operator plugin is not installed",
)


def load_operator_decision_module():
    if str(PLUGIN_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PLUGIN_SCRIPTS))
    path = PLUGIN_SCRIPTS / "ctoai_operator_decision.py"
    spec = importlib.util.spec_from_file_location(
        "ctoai_operator_decision_for_tests", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runner_recovery(*, authority_safe: bool = True, action: str = "restore_p14_runner_capacity"):
    interaction, risk_class = {
        "restore_p14_runner_capacity": ("external_config", "guarded_write"),
        "prepare_independent_runner_request": ("external_runner", "safe_write"),
    }.get(action, ("explicit_approval", "guarded_write"))
    return {
        "status": "needs_action",
        "recommended_action": action,
        "action_options": [
            {
                "action_id": action,
                "status": "ready",
                "interaction": interaction,
                "risk_class": risk_class,
                "mutates_live": False,
                "grants_authority": False,
            }
        ],
        "runner": {"foundation_ready": True, "authority_safe": authority_safe},
    }


def enabled_p7(mode: str) -> dict[str, object]:
    return {"status": "safe_write_tools_enabled", "next_safe_mode": mode}


def test_p14_runner_outranks_design_only_p7_without_authority_or_live_mutation():
    decisions = load_operator_decision_module()
    result = decisions.build_operator_decision(
        runner_recovery(), enabled_p7("design_next_p7_plugin_action")
    )

    assert result["selected"]["action_id"] == "restore_p14_runner_capacity"
    assert result["selected"]["mutates_live"] is False
    assert result["selected"]["grants_authority"] is False


def test_time_limited_confirmed_p7_proof_outranks_runner_preparation():
    decisions = load_operator_decision_module()
    result = decisions.build_operator_decision(
        runner_recovery(action="prepare_independent_runner_request"),
        enabled_p7("confirmed_selected_safe_write"),
    )

    assert result["selected"]["action_id"] == "run_confirmed_selected_safe_write"
    assert result["selected"]["interaction"] == "exact_confirmation"
    assert result["selected"]["auto_executable"] is False


def test_runner_authority_drift_fails_closed_to_review():
    decisions = load_operator_decision_module()
    result = decisions.build_operator_decision(
        runner_recovery(
            authority_safe=False, action="prepare_independent_runner_request"
        ),
        {},
    )

    assert result["selected"]["action_id"] == "review_helper_readiness"
    assert "external_runner_failed_closed" in result["exclusions"]


def test_live_promotion_is_never_selected_or_returned_as_an_alternative():
    decisions = load_operator_decision_module()
    recovery = runner_recovery(action="promote_live")
    recovery["alternatives"] = ["promote_live", "review_release_evidence"]
    result = decisions.build_operator_decision(recovery, {})

    actions = [result["selected"]["action_id"], *[item["action_id"] for item in result["alternatives"]]]
    assert "promote_live" not in actions
    assert all("live" not in action for action in actions)


def test_unknown_actions_and_modes_return_only_bounded_semantic_metadata():
    decisions = load_operator_decision_module()
    result = decisions.build_operator_decision(
        {"status": "needs_action", "recommended_action": "unknown_action"},
        enabled_p7("unknown-mode"),
    )

    assert result["selected"]["action_id"] == "review_helper_readiness"
    assert result["selected"]["detail_code"] == "unclassified_recovery_action"
    assert "command" not in result["selected"]
    assert "source_path" not in result["selected"]
