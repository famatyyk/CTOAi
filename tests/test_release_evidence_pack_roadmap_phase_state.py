from __future__ import annotations

from copy import deepcopy
import datetime as dt
import json

from scripts.ops import (
    otclient_p12_conditions_execute_once_receipt as conditions_receipt,
)
from scripts.ops import otclient_p12_equipment_execute_once_receipt as equipment_receipt
from scripts.ops import release_evidence_pack as evidence
from scripts.ops import otclient_p14_runner_preflight as preflight


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def _p14_foundation_ready() -> dict:
    return {
        "status": "foundation_ready",
        "contract_version": "ctoa.p14-runner-request.v1",
        "implementation_file_count": len(evidence.P14_FOUNDATION_PATHS),
        "required_file_count": len(evidence.P14_FOUNDATION_PATHS),
        "operational_runner_result": "missing",
        "operational_ready": False,
        "runtime_authority_granted": False,
        "live_authority_granted": False,
        "promotion_approved": False,
        "mcp_write_tool_enabled": False,
        "blockers": [],
    }


def _write_p14_preflight(tmp_path, *, result: str, ready: bool, blockers: list[str]):
    target = tmp_path / evidence.P14_RUNNER_PREFLIGHT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "schema_version": evidence.P14_RUNNER_PREFLIGHT_SCHEMA,
                "generated_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
                "status": "ready" if ready else "needs_attention",
                "operational_result": result,
                "operational_ready": ready,
                "hard_blockers": blockers,
                "warnings": [],
                "acceptance": {
                    "status": "passed",
                    "request_present": True,
                    "request_valid": True,
                    "result_present": True,
                    "result_valid": True,
                    "signature_verification_passed": True,
                    "source_current": True,
                    "proven_capability_count": 4,
                    "required_capability_count": 4,
                    "complete": True,
                    "authority_safe": True,
                    "capabilities": {
                        "visual_regression": True,
                        "in_world_regression": True,
                        "canary_rehearsal": True,
                        "rollback_rehearsal": True,
                    },
                },
                "remediation": preflight.build_remediation_plan(blockers),
                "workflow": {
                    "signature_verification_passed": True,
                    "acceptance_signature_verification_passed": True,
                },
                "runner": {"online": True},
                "authority": {
                    "runtime_actions": False,
                    "live_authority": False,
                    "promotion_approved": False,
                    "mcp_write_tool_enabled": False,
                },
            }
        ),
        encoding="utf-8",
    )


def test_p14_foundation_keeps_external_security_gaps_separate(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "P14_FOUNDATION_PATHS", ("p14-contract.txt",))
    (tmp_path / "p14-contract.txt").write_text("bounded", encoding="utf-8")
    blockers = [
        "p14_environment_required_reviewer_missing",
        "p14_environment_admin_bypass_enabled",
        "p14_self_hosted_result_revision_mismatch",
    ]
    _write_p14_preflight(
        tmp_path,
        result="externally_verified_stale",
        ready=False,
        blockers=blockers,
    )

    summary = evidence._p14_foundation_summary(tmp_path)

    assert summary["status"] == "foundation_ready"
    assert summary["blockers"] == []
    assert summary["operational_ready"] is False
    assert summary["operational_runner_result"] == "externally_verified_stale"
    assert summary["operational_blockers"] == blockers
    assert summary["runner_preflight"]["authority_safe"] is True
    assert summary["remediation_plan"]["next_action"] == "harden_p14_environment"
    assert summary["remediation_plan"]["action_count"] == 2
    assert summary["remediation_plan"]["actions"][1]["status"] == "blocked"


def test_p14_foundation_accepts_current_external_verification(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "P14_FOUNDATION_PATHS", ("p14-contract.txt",))
    (tmp_path / "p14-contract.txt").write_text("bounded", encoding="utf-8")
    _write_p14_preflight(
        tmp_path,
        result="externally_verified_current",
        ready=True,
        blockers=[],
    )

    summary = evidence._p14_foundation_summary(tmp_path)

    assert summary["status"] == "foundation_ready"
    assert summary["operational_ready"] is True
    assert summary["operational_runner_result"] == "externally_verified_current"
    assert summary["operational_blockers"] == []
    assert summary["remediation_plan"]["status"] == "complete"
    assert summary["remediation_plan"]["next_action"] == "none"


def test_p14_foundation_fails_closed_on_unbounded_remediation(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "P14_FOUNDATION_PATHS", ("p14-contract.txt",))
    (tmp_path / "p14-contract.txt").write_text("bounded", encoding="utf-8")
    _write_p14_preflight(
        tmp_path,
        result="externally_verified_stale",
        ready=False,
        blockers=["p14_self_hosted_result_revision_mismatch"],
    )
    path = tmp_path / evidence.P14_RUNNER_PREFLIGHT_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["remediation"]["actions"][0]["action_id"] = "run_arbitrary_command"
    path.write_text(json.dumps(payload), encoding="utf-8")

    summary = evidence._p14_foundation_summary(tmp_path)

    assert summary["runner_preflight"]["contract_valid"] is False
    assert summary["operational_blockers"] == ["p14_runner_preflight_invalid"]
    assert summary["remediation_plan"]["next_action"] == "review_p14_external_state"


def test_p14_foundation_rejects_action_contract_substitution(monkeypatch, tmp_path):
    monkeypatch.setattr(evidence, "P14_FOUNDATION_PATHS", ("p14-contract.txt",))
    (tmp_path / "p14-contract.txt").write_text("bounded", encoding="utf-8")
    _write_p14_preflight(
        tmp_path,
        result="externally_verified_stale",
        ready=False,
        blockers=["p14_environment_required_reviewer_missing"],
    )
    path = tmp_path / evidence.P14_RUNNER_PREFLIGHT_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["remediation"]["actions"][0]["capability"] = "signing_material"
    path.write_text(json.dumps(payload), encoding="utf-8")

    summary = evidence._p14_foundation_summary(tmp_path)

    assert summary["runner_preflight"]["contract_valid"] is False
    assert summary["operational_blockers"] == ["p14_runner_preflight_invalid"]
    assert summary["remediation_plan"]["next_action"] == "review_p14_external_state"


def _safe_plan(basis: dict, *, status: str, blockers: list[str]) -> dict:
    return {
        **basis,
        "plan_sha256": evidence._conditions_shadow_canonical_sha256(basis),
        "status": status,
        "blockers": blockers,
        "session_approved": False,
        "execution_approved": False,
        "attempt_count": 0,
        "final_state": "disarmed",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "execute_once_allowed": False,
        "live_promotion": False,
        "intrusive_actions_performed": [],
    }


def _conditions_summary() -> dict:
    basis = {
        "schema_version": conditions_receipt.plans.SCHEMA,
        "lane": "conditions",
        "vocation": "ek",
        "action": "cast_exura_ico",
        "spell": "exura ico",
        "spell_source": "ctoa_ek_profile.healing.spell",
        "predecessor_accepted_spell": "exura",
        "retry_budget": 0,
        "mandatory_kill_and_disarm": True,
        "requires_fresh_paralyze_observation_ms": 1000,
        "manifest_sha256": SHA_A,
        "source_sha256": SHA_B,
        "ek_profile_sha256": SHA_C,
        "p9_receipt_sha256": SHA_A,
        "validation_sha256": SHA_B,
        "smoke_preflight_sha256": SHA_C,
        "module_static_gates_sha256": SHA_A,
        "module_contract_sha256": SHA_B,
    }
    plan = _safe_plan(basis, status="ready_for_sandbox_session_approval", blockers=[])
    approval = {
        "schema_version": "ctoa.p12-conditions-session-approval.v1",
        "status": "approved",
        "session_approved": True,
        "execution_approved": True,
        "plan_sha256": plan["plan_sha256"],
    }
    trace = {
        "schema_version": "ctoa.p12-conditions-execute-once-trace.v1",
        "status": "executed",
        "result": "success",
        "action": "cast_exura_ico",
        "spell": "exura ico",
        "attempt_count": 1,
        "retry_budget": 0,
        "executor_called": True,
        "retry_scheduled": False,
        "final_state": "killed_and_disarmed",
        "live_promotion": False,
        "plan_sha256": plan["plan_sha256"],
        "p9_receipt_sha256": plan["p9_receipt_sha256"],
        "terminal_snapshot": {
            "armed": False,
            "killed": True,
            "consumed": True,
            "attempt_count": 1,
        },
    }
    receipt = conditions_receipt.build_receipt(
        plan, approval, trace, now_ms=2_000_000_000_000
    )
    return evidence._p12_conditions_summary(plan, approval, trace, receipt)


def _heal_friend_closure_summary() -> dict:
    return {
        "status": "closed_blocked_no_compatible_vocation",
        "contract_valid": True,
        "closure_granted": True,
        "closure_reason": "no_compatible_sandbox_vocation",
        "attempt_count": 0,
        "retry_scheduled": False,
        "final_state": "disarmed",
        "required_vocation": "ed",
        "available_vocations": ["sorcerer", "knight"],
        "downstream_authority_granted": False,
        "runtime_actions": False,
        "live_promotion": False,
        "binding_status": "passed",
        "blockers": [],
    }


def _equipment_documents() -> tuple[dict, dict, dict, dict]:
    current_basis = {
        "schema_version": equipment_receipt.plans.SCHEMA,
        "lane": "equipment",
        "action": "move_ring_candidate_to_equipment_slot",
        "slot": "ring",
        "before_item_id": 3096,
        "before_family_key": "ring_primary",
        "candidate_item_id": 3097,
        "candidate_family_key": "ring_secondary",
        "source_container_id": None,
        "source_slot_index": None,
        "rollback_item_id": 3093,
        "retry_budget": 0,
        "mandatory_kill_and_disarm": True,
        "requires_post_action_ring_id": 3099,
        "observation_id": None,
        "capability_sha256": SHA_A,
        "manifest_sha256": SHA_B,
        "runtime_gates_sha256": SHA_C,
        "p10_receipt_sha256": SHA_A,
        "source_sha256": SHA_B,
        "family_registry_sha256": SHA_C,
        "family_selection_profile_sha256": SHA_A,
    }
    current_plan = _safe_plan(
        current_basis,
        status="blocked",
        blockers=["runtime_gates_not_current"],
    )
    consumed_plan = {
        "plan_sha256": SHA_C,
        "p10_receipt_sha256": SHA_A,
        "before_item_id": 3096,
        "candidate_item_id": 3097,
        "source_container_id": 3,
        "source_slot_index": 1,
        "requires_post_action_ring_id": 3097,
        "rollback_item_id": 3096,
    }
    approval = {
        "schema_version": "ctoa.p12-equipment-session-approval.v1",
        "status": "approved",
        "session_approved": True,
        "execution_approved": True,
        "plan_sha256": consumed_plan["plan_sha256"],
    }
    trace = {
        "schema_version": "ctoa.p12-equipment-execute-once-trace.v1",
        "status": "dispatched",
        "result": "requested",
        "action": "move_ring_candidate_to_equipment_slot",
        "before_item_id": 3096,
        "candidate_item_id": 3097,
        "source_container_id": 3,
        "source_slot_index": 1,
        "attempt_count": 1,
        "retry_budget": 0,
        "executor_called": True,
        "retry_scheduled": False,
        "final_state": "killed_and_disarmed",
        "live_promotion": False,
        "plan_sha256": consumed_plan["plan_sha256"],
        "p10_receipt_sha256": consumed_plan["p10_receipt_sha256"],
        "post_action_observation": {
            "online": "offline",
            "alive": "unknown",
            "inventory_api_available": False,
            "containers_complete": False,
            "ring": {"present": False, "item_id": 0, "count": 0},
            "candidates": [
                {"item_id": 3093, "container_id": 3, "slot_index": 1, "count": 1}
            ],
        },
        "post_action_capability": {
            "online": False,
            "runtime_state": "disarmed",
            "runtime_enabled": False,
        },
        "terminal_snapshot": {
            "armed": False,
            "killed": True,
            "consumed": True,
            "attempt_count": 1,
        },
    }
    receipt = equipment_receipt.build_receipt(
        consumed_plan,
        approval,
        trace,
        now_ms=2_000_000_000_000,
    )
    return current_plan, approval, trace, receipt


def _accepted_equipment_documents() -> tuple[dict, dict, dict, dict]:
    blocked_plan, _, _, _ = _equipment_documents()
    basis = {key: blocked_plan[key] for key in evidence.P12_EQUIPMENT_PLAN_BASIS_KEYS}
    basis.update(
        {
            "source_container_id": 2,
            "source_slot_index": 1,
            "observation_id": "equipment-accepted",
        }
    )
    plan = _safe_plan(
        basis,
        status="ready_for_sandbox_session_approval",
        blockers=[],
    )
    approval = {
        "schema_version": "ctoa.p12-equipment-session-approval.v1",
        "status": "approved",
        "session_approved": True,
        "execution_approved": True,
        "plan_sha256": plan["plan_sha256"],
    }
    trace = {
        "schema_version": "ctoa.p12-equipment-execute-once-trace.v1",
        "status": "dispatched",
        "result": "requested",
        "action": "move_ring_candidate_to_equipment_slot",
        "before_item_id": 3096,
        "candidate_item_id": 3097,
        "source_container_id": 2,
        "source_slot_index": 1,
        "attempt_count": 1,
        "retry_budget": 0,
        "executor_called": True,
        "retry_scheduled": False,
        "final_state": "killed_and_disarmed",
        "live_promotion": False,
        "plan_sha256": plan["plan_sha256"],
        "p10_receipt_sha256": plan["p10_receipt_sha256"],
        "post_action_observation": {
            "online": "online",
            "alive": "alive",
            "inventory_api_available": True,
            "containers_complete": True,
            "ring": {"present": True, "item_id": 3099, "count": 1},
            "candidates": [
                {"item_id": 3093, "container_id": 2, "slot_index": 1, "count": 1}
            ],
        },
        "post_action_capability": {
            "online": True,
            "runtime_state": "disarmed",
            "runtime_enabled": False,
        },
        "terminal_snapshot": {
            "armed": False,
            "killed": True,
            "consumed": True,
            "attempt_count": 1,
        },
    }
    receipt = equipment_receipt.build_receipt(
        plan,
        approval,
        trace,
        now_ms=2_000_000_000_000,
    )
    return plan, approval, trace, receipt


def test_roadmap_phase_state_rejects_legacy_incomplete_p12_boundary(monkeypatch):
    monkeypatch.setattr(
        evidence.conditions_acceptance, "_receipt_contract_valid", lambda _value: True
    )
    monkeypatch.setattr(
        evidence.equipment_acceptance, "_receipt_contract", lambda _value: True
    )
    monkeypatch.setattr(
        evidence, "_heal_friend_acceptance_contract_valid", lambda _value: True
    )
    current_plan, approval, trace, receipt = _equipment_documents()
    equipment = evidence._p12_equipment_summary(current_plan, approval, trace, receipt)

    phase = evidence._roadmap_phase_state_summary(
        background={
            "contract_valid": True,
            "reported_status": "ready",
            "integrity_status": "passed",
            "capability_status": "fresh",
            "blockers": [],
        },
        p9_receipt={"status": "accepted", "acceptance_granted": True},
        p10_receipt={"status": "accepted", "acceptance_granted": True},
        p11_receipt={"status": "accepted", "acceptance_granted": True},
        p12_conditions=_conditions_summary(),
        p12_equipment=equipment,
        p12_heal_friend_artifact_present=False,
    )

    assert phase["status"] == "needs_attention"
    assert phase["aligned_with_current_roadmap"] is False
    assert [phase[key] for key in ("p8", "p9", "p10", "p11")] == [
        "operational_acceptance_complete"
    ] * 4
    assert phase["p12"]["conditions"]["status"] == "operational_acceptance_complete"
    assert phase["p12"]["equipment"]["status"] == "operational_acceptance_blocked"
    assert phase["p12"]["equipment"]["receipt_status"] == "rejected"
    assert phase["p12"]["equipment"]["receipt_contract_valid"] is True
    assert phase["p12"]["equipment"]["consumed_attempt"] is True
    assert phase["p12"]["equipment"]["replacement_plan_distinct"] is True
    assert phase["p12"]["equipment"]["current_plan_safe"] is True
    assert phase["p12"]["equipment"]["attempt_count"] == 0
    assert phase["p12"]["heal_friend"]["status"] == "not_started"
    assert phase["p12"]["status"] == "legacy_boundary_incomplete"
    assert phase["p13"]["status"] == "blocked"


def test_roadmap_phase_state_advances_accepted_p12_equipment(monkeypatch):
    monkeypatch.setattr(
        evidence.conditions_acceptance, "_receipt_contract_valid", lambda _value: True
    )
    monkeypatch.setattr(
        evidence.equipment_acceptance, "_receipt_contract", lambda _value: True
    )
    monkeypatch.setattr(
        evidence, "_heal_friend_acceptance_contract_valid", lambda _value: True
    )
    plan, approval, trace, receipt = _accepted_equipment_documents()
    equipment = evidence._p12_equipment_summary(plan, approval, trace, receipt)

    phase = evidence._roadmap_phase_state_summary(
        background={
            "contract_valid": True,
            "reported_status": "ready",
            "integrity_status": "passed",
            "capability_status": "fresh",
            "blockers": [],
        },
        p9_receipt={"status": "accepted", "acceptance_granted": True},
        p10_receipt={"status": "accepted", "acceptance_granted": True},
        p11_receipt={"status": "accepted", "acceptance_granted": True},
        p12_conditions=_conditions_summary(),
        p12_equipment=equipment,
        p12_heal_friend_artifact_present=False,
    )

    assert equipment == {
        **equipment,
        "status": "operational_acceptance_complete",
        "receipt_status": "accepted",
        "receipt_contract_valid": True,
        "acceptance_granted": True,
        "consumed_attempt": True,
        "current_plan_status": "ready_for_sandbox_session_approval",
        "current_plan_contract_valid": True,
        "current_plan_safe": True,
        "replacement_plan_distinct": False,
        "attempt_count": 1,
        "session_approved": True,
        "execution_approved": True,
        "final_state": "killed_and_disarmed",
        "downstream_authority_granted": False,
    }
    assert phase["status"] == "needs_attention"
    assert phase["aligned_with_current_roadmap"] is False
    assert phase["p12"]["equipment"]["status"] == ("operational_acceptance_complete")
    assert phase["p12"]["heal_friend"]["status"] == "not_started"


def test_roadmap_phase_state_closes_p12_and_tracks_p13_read_only(monkeypatch):
    monkeypatch.setattr(
        evidence.conditions_acceptance, "_receipt_contract_valid", lambda _value: True
    )
    monkeypatch.setattr(
        evidence.equipment_acceptance, "_receipt_contract", lambda _value: True
    )
    monkeypatch.setattr(
        evidence, "_heal_friend_acceptance_contract_valid", lambda _value: True
    )
    plan, approval, trace, receipt = _accepted_equipment_documents()
    equipment = evidence._p12_equipment_summary(plan, approval, trace, receipt)
    common = {
        "background": {
            "contract_valid": True,
            "reported_status": "ready",
            "integrity_status": "passed",
            "capability_status": "fresh",
            "blockers": [],
        },
        "p9_receipt": {"status": "accepted", "acceptance_granted": True},
        "p10_receipt": {"status": "accepted", "acceptance_granted": True},
        "p11_receipt": {"status": "accepted", "acceptance_granted": True},
        "p12_conditions": _conditions_summary(),
        "p12_equipment": equipment,
        "p12_heal_friend_artifact_present": True,
        "p12_heal_friend_closure": _heal_friend_closure_summary(),
    }

    active = evidence._roadmap_phase_state_summary(**common)

    assert active["status"] == "p13_in_progress"
    assert active["current_phase"] == "P13"
    assert active["next_phase"] == "P13"
    assert active["aligned_with_current_roadmap"] is True
    assert active["p12"]["status"] == "complete"
    assert active["p12"]["heal_friend"]["attempt_count"] == 0
    assert active["p13"] == {
        "status": "implementation_in_progress",
        "roadmap_state": {"status": "missing", "blockers": []},
        "control_center_mode": "read_only",
        "runtime_authority_granted": False,
        "live_authority_granted": False,
    }

    ready = evidence._roadmap_phase_state_summary(
        **common,
        roadmap_state={
            "status": "runtime_evidence_ready",
            "contract_valid": True,
            "freshness_status": "current",
            "tamper_status": "passed",
            "audit_binding_status": "passed",
            "control_center_mode": "read_only",
            "runtime_authority_count": 0,
            "live_authority_count": 0,
            "blockers": [],
        },
    )

    assert ready["status"] == "p13_runtime_evidence_ready"
    assert ready["next_phase"] == "P14"
    assert ready["p13"]["status"] == "runtime_evidence_ready"
    assert ready["p13"]["runtime_authority_granted"] is False
    assert ready["p13"]["live_authority_granted"] is False

    p14_active = evidence._roadmap_phase_state_summary(
        **common,
        roadmap_state=ready["p13"]["roadmap_state"],
        p14_foundation=_p14_foundation_ready(),
    )

    assert p14_active["status"] == "p14_foundation_ready"
    assert p14_active["current_phase"] == "P14"
    assert p14_active["next_phase"] == "P14"
    assert p14_active["aligned_with_current_roadmap"] is True
    assert p14_active["p14"]["operational_ready"] is False
    assert p14_active["p14"]["promotion_approved"] is False
    assert p14_active["p14"]["mcp_write_tool_enabled"] is False


def test_roadmap_phase_state_fails_closed_on_approved_replacement_plan(monkeypatch):
    monkeypatch.setattr(
        evidence.conditions_acceptance, "_receipt_contract_valid", lambda _value: True
    )
    monkeypatch.setattr(
        evidence.equipment_acceptance, "_receipt_contract", lambda _value: True
    )
    monkeypatch.setattr(
        evidence, "_heal_friend_acceptance_contract_valid", lambda _value: True
    )
    current_plan, approval, trace, receipt = _equipment_documents()
    unsafe_plan = deepcopy(current_plan)
    unsafe_plan["session_approved"] = True
    equipment = evidence._p12_equipment_summary(unsafe_plan, approval, trace, receipt)

    phase = evidence._roadmap_phase_state_summary(
        background={
            "contract_valid": True,
            "reported_status": "ready",
            "integrity_status": "passed",
            "capability_status": "fresh",
            "blockers": [],
        },
        p9_receipt={"status": "accepted", "acceptance_granted": True},
        p10_receipt={"status": "accepted", "acceptance_granted": True},
        p11_receipt={"status": "accepted", "acceptance_granted": True},
        p12_conditions=_conditions_summary(),
        p12_equipment=equipment,
        p12_heal_friend_artifact_present=False,
    )

    assert equipment["current_plan_contract_valid"] is False
    assert equipment["current_plan_safe"] is False
    assert phase["status"] == "needs_attention"
    assert phase["aligned_with_current_roadmap"] is False
