from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "AI" / "P24_REPLAY_CANARY_MATRIX.json"


def _matrix() -> dict[str, object]:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_p24_matrix_keeps_static_replay_below_runtime_and_live_authority() -> None:
    matrix = _matrix()
    policy = matrix["execution_policy"]

    assert matrix["schema_version"] == "ctoa.helper-replay-canary-matrix.v1"
    assert matrix["status"] == "p24_1_matrix_complete"
    assert policy["sandbox_first"] is True
    assert policy["static_replay_grants_runtime_authority"] is False
    assert policy["fixture_evidence_satisfies_operational_acceptance"] is False
    assert policy["canary_execution_authorized"] is False
    assert policy["live_authorized"] is False
    assert policy["live_requires_separate_explicit_approval"] is True
    validation = matrix["validation"]
    assert validation["engine_brain_doc_sync"] == "passed"
    assert validation["engine_brain_secret_guardrail"] == "passed"
    assert validation["engine_brain_doctor"] == "warn"
    assert validation["engine_brain_doctor_failures"] == 0


def test_every_completed_refactor_phase_has_bounded_replay_evidence() -> None:
    matrix = _matrix()
    lanes = matrix["replay_lanes"]

    assert [lane["phase"] for lane in lanes] == ["P18", "P19", "P20", "P21", "P22", "P23"]
    for lane in lanes:
        assert lane["evidence_level"] in {"static_contract", "deterministic_lua_replay"}
        assert lane["tests"]
        assert lane["proves"]
        assert lane["does_not_prove"]
        for relative in lane["tests"]:
            assert (ROOT / relative).is_file(), relative


def test_external_runner_snapshot_is_explicitly_stale_and_non_accepting() -> None:
    snapshot = _matrix()["external_runner_snapshot"]

    assert snapshot["source_required_for_static_validation"] is False
    assert snapshot["status"] == "needs_attention"
    assert snapshot["operational_result"] == "externally_verified_stale"
    assert snapshot["runner_online"] is True
    assert snapshot["self_hosted_run_success"] is True
    assert snapshot["source_revision_match"] is False
    assert snapshot["acceptance_complete"] is False
    assert set(snapshot["hard_blockers"]) == {
        "p14_environment_required_reviewer_missing",
        "p14_environment_admin_bypass_enabled",
        "p14_self_hosted_result_revision_mismatch",
        "p14_visual_regression_not_proven",
        "p14_in_world_regression_not_proven",
        "p14_canary_rehearsal_not_proven",
        "p14_rollback_rehearsal_not_proven",
    }

    stage = _matrix()["local_stage_snapshot"]
    assert stage["status"] == "stale"
    assert stage["tracked_source_manifest_match"] is False
    assert stage["first_mismatch"]["path"] == "mods/ctoa_otclient/ctoa_helper_hud.lua"
    assert stage["promotion_allowed"] is False


def test_canaries_are_sandbox_bounded_abortable_and_rollback_defined() -> None:
    canaries = _matrix()["sandbox_canaries"]

    assert len(canaries) == 4
    assert sum(canary["max_dispatches"] for canary in canaries) == 1
    for canary in canaries:
        assert canary["status"] == "specified_not_executed"
        assert canary["preconditions"]
        assert canary["operator_actions"]
        assert canary["observations"]
        assert canary["abort_conditions"]
        assert canary["rollback"]
        serialized = json.dumps(canary).lower()
        assert "live promotion" not in serialized

    spell = next(item for item in canaries if item["id"] == "spell-state-pz-and-anti-spam")
    assert spell["requires_explicit_session_approval"] is True
    assert spell["max_dispatches"] == 1
    assert "any cast in PZ" in spell["abort_conditions"]
