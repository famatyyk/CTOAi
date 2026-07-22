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


def load_helper_readiness_module():
    if str(PLUGIN_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PLUGIN_SCRIPTS))
    path = PLUGIN_SCRIPTS / "ctoai_helper_readiness.py"
    spec = importlib.util.spec_from_file_location(
        "ctoai_helper_readiness_for_tests", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ready_local_helper(**overrides):
    helper = {
        "status": "ready",
        "local_readiness": "ready",
        "validation_status": "passed",
        "module_contract": {"status": "passed", "forbidden_count": 0},
        "module_audit": {"status": "ready", "helper_budget_status": "within_budget"},
        "blockers": [],
        "runtime_state": "not_running",
    }
    helper.update(overrides)
    return helper


def p14_foundation() -> dict[str, object]:
    return {
        "status": "foundation_ready",
        "contract_version": "ctoa.p14-runner-request.v1",
        "required_file_count": 1,
        "implementation_file_count": 1,
        "runtime_authority_granted": False,
        "live_authority_granted": False,
        "promotion_approved": False,
        "mcp_write_tool_enabled": False,
        "blockers": [],
        "operational_runner_result": "missing",
        "operational_ready": False,
        "acceptance": {
            "status": "missing",
            "proven_capability_count": 0,
            "required_capability_count": 4,
            "complete": False,
            "capabilities": {
                "visual_regression": False,
                "in_world_regression": False,
                "canary_rehearsal": False,
                "rollback_rehearsal": False,
            },
        },
    }


def test_manifest_mismatch_becomes_an_adaptive_recovery_chain():
    readiness = load_helper_readiness_module()
    result = readiness.build_helper_readiness(
        ready_local_helper(
            blockers=["manifest_current: Manifest SHA256 does not match"]
        )
    )

    assert result["cause"] == "manifest_evidence_mismatch"
    assert result["recommended_action"] == "refresh_local_gates"
    assert result["interaction"] == "none"


def test_unknown_blocker_fails_closed_without_inventing_a_command():
    readiness = load_helper_readiness_module()
    result = readiness.build_helper_readiness(
        ready_local_helper(blockers=["UnrecognizedFutureGate"])
    )

    assert result["current_phase"] == "review_required"
    assert result["recommended_action"] == "review_helper_readiness"
    assert result["interaction"] == "operator_review"


def test_promoted_helper_has_no_remaining_recovery_phase():
    readiness = load_helper_readiness_module()
    result = readiness.build_helper_readiness(
        ready_local_helper(status="promoted", live_promotion_status="promoted")
    )

    assert result["status"] == "ready"
    assert result["current_phase"] == "ready"
    assert result["remaining_phase_count"] == 0


def test_p14_foundation_prefers_external_runner_without_granting_authority():
    readiness = load_helper_readiness_module()
    result = readiness.build_helper_readiness(
        ready_local_helper(blockers=["module_attach_smoke"], runner=p14_foundation())
    )

    assert result["recommended_action"] == "prepare_independent_runner_request"
    assert result["interaction"] == "external_runner"
    assert result["runner"]["authority_safe"] is True
    assert all(option["grants_authority"] is False for option in result["action_options"])


def test_p14_authority_drift_disables_external_runner_preference():
    readiness = load_helper_readiness_module()
    runner = p14_foundation()
    runner["live_authority_granted"] = True
    result = readiness.build_helper_readiness(
        ready_local_helper(blockers=["module_attach_smoke"], runner=runner)
    )

    assert result["runner"]["authority_safe"] is False
    assert result["recommended_action"] == "refresh_sandbox_evidence"
    assert result["interaction"] == "sandbox_in_world"


def test_legacy_and_camel_case_blockers_normalize_to_one_stable_code():
    readiness = load_helper_readiness_module()
    assert readiness.blocker_codes(["ModuleAttachSmoke", "module_attach_smoke"]) == [
        "module_attach_smoke"
    ]
