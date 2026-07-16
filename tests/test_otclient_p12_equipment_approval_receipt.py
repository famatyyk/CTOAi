from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.ops import otclient_p12_equipment_execute_once_plan as plans
from scripts.ops import otclient_p12_equipment_execute_once_receipt as receipts
from scripts.ops import otclient_p12_equipment_execution_approval as executions
from scripts.ops import otclient_p12_equipment_execution_preflight as preflight
from scripts.ops import otclient_p12_equipment_session_approval as approvals


def _plan(
    *,
    family_selection_profile_sha256: str = "c" * 64,
    family_registry_sha256: str = "d" * 64,
) -> dict:
    return {
        "schema_version": plans.SCHEMA,
        "status": "ready_for_sandbox_session_approval",
        "blockers": [],
        "plan_sha256": "a" * 64,
        "p10_receipt_sha256": "b" * 64,
        "before_item_id": 3096,
        "candidate_item_id": 3097,
        "source_container_id": 3,
        "source_slot_index": 1,
        "rollback_item_id": 3093,
        "requires_post_action_ring_id": 3099,
        "family_selection_profile_sha256": family_selection_profile_sha256,
        "family_registry_sha256": family_registry_sha256,
        "required_session_confirmation": "approve session",
        "required_execute_confirmation": "approve execution",
        **{flag: False for flag in plans.FALSE_FLAGS},
    }


def _observation(ring_id: int = 3096) -> dict:
    return {
        "schema_version": "ctoa.equipment-shadow-observation.v1",
        "observed_at_unix_ms": 1000,
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_states",
        "inventory_api_available": True,
        "containers_complete": True,
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
        "ring": {"present": True, "item_id": ring_id, "count": 1},
        "candidates": [
            {
                "container_id": 3,
                "slot_index": 1,
                "item_id": 3097 if ring_id == 3096 else 3093,
                "count": 1,
            }
        ],
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
    }


def test_separate_approvals_never_dispatch() -> None:
    plan = _plan()
    session = approvals.build_approval(plan, "approve session", now_ms=1)
    assert session["session_approved"] is True
    assert session["execution_approved"] is False
    accepted = executions.build_execution_approval(
        plan, session, "approve execution", now_ms=2
    )
    assert accepted["execution_approved"] is True
    assert accepted["dispatch_allowed"] is False
    assert accepted["runtime_actions"] is False
    assert accepted["attempt_count"] == 0


def test_session_approval_binds_persisted_plan_not_rotating_heartbeat(
    tmp_path: Path, monkeypatch
) -> None:
    plan = _plan()
    output = tmp_path / "plan.json"
    approval_output = tmp_path / "approval.json"
    output.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(plans, "OUTPUT", output)
    monkeypatch.setattr(approvals, "OUTPUT", approval_output)
    monkeypatch.setattr(
        plans,
        "build_plan",
        lambda: {**plan, "plan_sha256": "c" * 64},
    )
    result = approvals.main(["--confirmation", "approve session"])
    assert result == 0
    persisted = json.loads(approval_output.read_text(encoding="utf-8"))
    assert persisted["plan_sha256"] == "a" * 64
    assert persisted["session_approved"] is True


def test_preflight_requires_exact_current_ring_and_candidate_location(
    tmp_path: Path,
) -> None:
    paths = {
        name: tmp_path / f"{name}.json"
        for name in ("plan", "approval", "runtime_gates", "capability", "manifest")
    }
    paths["family_selection_profile"] = tmp_path / "ctoa_user_ek_profile.lua"
    paths["registry_source"] = tmp_path / "equipment_family_registry.lua"
    paths["family_selection_profile"].write_text(
        "family_enabled = {\n  ring_primary = false,\n  ring_secondary = true,\n}\n",
        encoding="utf-8",
    )
    paths["registry_source"].write_text(
        "return { registry = true }\n", encoding="utf-8"
    )
    profile_sha = hashlib.sha256(
        paths["family_selection_profile"].read_bytes()
    ).hexdigest()
    registry_sha = hashlib.sha256(paths["registry_source"].read_bytes()).hexdigest()
    plan = _plan(
        family_selection_profile_sha256=profile_sha,
        family_registry_sha256=registry_sha,
    )
    paths["manifest"].write_text(json.dumps({"name": "manifest"}), encoding="utf-8")
    manifest_sha = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    paths["plan"].write_text(json.dumps(plan), encoding="utf-8")
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    paths["approval"].write_text(json.dumps(approval), encoding="utf-8")
    paths["runtime_gates"].write_text(
        json.dumps(
            {
                "status": "passed",
                "failed": [],
                "check_count": 19,
                "passed_count": 19,
                "manifest": {"sha256": manifest_sha},
                "observed": {"runtime_state": "disarmed"},
            }
        ),
        encoding="utf-8",
    )
    paths["capability"].write_text(
        json.dumps(
            {
                "observed_at_unix_ms": 1000,
                "heartbeat_status": "online",
                "online": True,
                "vocation": "ek",
                "runtime_state": "disarmed",
                "runtime_enabled": False,
                "equipment_shadow_observation": _observation(),
            }
        ),
        encoding="utf-8",
    )
    report = preflight.build_preflight(paths, now_ms=1100)
    assert report["status"] == "ready_for_execution_approval"
    assert report["blockers"] == []
    capability = json.loads(paths["capability"].read_text(encoding="utf-8"))
    capability["equipment_shadow_observation"]["candidates"][0]["slot_index"] = 2
    paths["capability"].write_text(json.dumps(capability), encoding="utf-8")
    blocked = preflight.build_preflight(paths, now_ms=1100)
    assert "candidate_location_mismatch" in blocked["blockers"]


def test_preflight_rejects_family_selection_or_registry_drift(tmp_path: Path) -> None:
    paths = {
        name: tmp_path / f"{name}.json"
        for name in ("plan", "approval", "runtime_gates", "capability", "manifest")
    }
    paths["family_selection_profile"] = tmp_path / "ctoa_user_ek_profile.lua"
    paths["registry_source"] = tmp_path / "equipment_family_registry.lua"
    profile = (
        "family_enabled = {\n  ring_primary = false,\n  ring_secondary = true,\n}\n"
    )
    paths["family_selection_profile"].write_text(profile, encoding="utf-8")
    paths["registry_source"].write_text(
        "return { registry = true }\n", encoding="utf-8"
    )
    plan = _plan(
        family_selection_profile_sha256=hashlib.sha256(
            paths["family_selection_profile"].read_bytes()
        ).hexdigest(),
        family_registry_sha256=hashlib.sha256(
            paths["registry_source"].read_bytes()
        ).hexdigest(),
    )
    paths["plan"].write_text(json.dumps(plan), encoding="utf-8")
    paths["approval"].write_text(
        json.dumps(approvals.build_approval(plan, "approve session", now_ms=1)),
        encoding="utf-8",
    )
    paths["manifest"].write_text(json.dumps({"name": "manifest"}), encoding="utf-8")
    manifest_sha = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    paths["runtime_gates"].write_text(
        json.dumps(
            {
                "status": "passed",
                "failed": [],
                "check_count": 19,
                "passed_count": 19,
                "manifest": {"sha256": manifest_sha},
                "observed": {"runtime_state": "disarmed"},
            }
        ),
        encoding="utf-8",
    )
    paths["capability"].write_text(
        json.dumps(
            {
                "observed_at_unix_ms": 1000,
                "heartbeat_status": "online",
                "online": True,
                "vocation": "ek",
                "runtime_state": "disarmed",
                "runtime_enabled": False,
                "equipment_shadow_observation": _observation(),
            }
        ),
        encoding="utf-8",
    )

    paths["family_selection_profile"].write_text(
        profile.replace("ring_primary = false", "ring_primary = true"),
        encoding="utf-8",
    )
    selection_drift = preflight.build_preflight(paths, now_ms=1100)
    assert "family_selection_drift" in selection_drift["blockers"]

    paths["family_selection_profile"].write_text(profile, encoding="utf-8")
    paths["registry_source"].write_text(
        "return { registry = false }\n", encoding="utf-8"
    )
    registry_drift = preflight.build_preflight(paths, now_ms=1100)
    assert "family_registry_drift" in registry_drift["blockers"]


def test_receipt_requires_terminal_disarm_post_ring_and_rollback_location() -> None:
    plan = _plan()
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    approval = executions.build_execution_approval(
        plan, approval, "approve execution", now_ms=2
    )
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
        "plan_sha256": "a" * 64,
        "p10_receipt_sha256": "b" * 64,
        "terminal_snapshot": {
            "armed": False,
            "killed": True,
            "consumed": True,
            "attempt_count": 1,
        },
        "post_action_observation": _observation(ring_id=3099),
        "post_action_capability": {
            "online": True,
            "runtime_state": "disarmed",
            "runtime_enabled": False,
        },
    }
    accepted = receipts.build_receipt(plan, approval, trace, now_ms=3)
    assert accepted["status"] == "accepted"
    assert accepted["intrusive_actions_performed"] == [
        "move_ring_candidate_to_equipment_slot"
    ]
    trace["post_action_observation"]["candidates"][0]["slot_index"] = 2
    rejected = receipts.build_receipt(plan, approval, trace, now_ms=3)
    assert "rollback_item_location_not_proven" in rejected["blockers"]


def test_reconcile_captures_one_terminal_attempt_without_retry() -> None:
    plan = _plan()
    line = (
        "P12 Equipment execute-once: status=dispatched result=requested attempt=1 "
        "final=killed_and_disarmed retry=false armed=false killed=true consumed=true "
        f"plan={'a' * 64} p10={'b' * 64}"
    )
    capability = {
        "observed_at_unix_ms": 4,
        "online": True,
        "runtime_state": "disarmed",
        "runtime_enabled": False,
        "equipment_shadow_observation": _observation(ring_id=3099),
    }
    trace = receipts.build_reconciled_trace(plan, capability, line, now_ms=5)
    assert trace["attempt_count"] == 1
    assert trace["retry_scheduled"] is False
    assert trace["final_state"] == "killed_and_disarmed"
    assert trace["reconciled_after_postcondition_timeout"] is True
