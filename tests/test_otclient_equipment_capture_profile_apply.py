from __future__ import annotations

import json
from pathlib import Path

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_capture_profile_apply as apply_tool
from scripts.ops import otclient_equipment_capture_profile_change_plan as change_plan
from scripts.ops import otclient_equipment_capture_profile_doctor as doctor
from scripts.ops import otclient_equipment_observation_preview as preview


NOW_MS = 1_783_800_000_000


def _plan_payload() -> tuple[dict, dict]:
    current = doctor.zero_id_skeleton()
    current_sha = documents.canonical_sha256(current)
    doctor_payload = {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": "blocked",
        "source": "local_operator_override",
        "path": str(change_plan.DEFAULT_LOCAL_CAPTURE_PROFILE),
        "sha256": current_sha,
        "configured_by_operator": False,
        "slot": "ring",
        "identifiers_present": False,
        "candidate_slot_index_valid": True,
        "no_action_contract": True,
        "blockers": ["operator_confirmation_missing", "exact_ids_missing"],
        "next_action": "Set exact identifiers after data-only review.",
        "runtime_actions": False,
        "live_file_writes": False,
        "runtime_readiness_claimed": False,
    }
    observation = {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": preview.OBSERVATION_SCHEMA,
        "observed_at_unix_ms": NOW_MS - 1000,
        "observation_id": "equipment-apply-1",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_states",
        "inventory_api_available": True,
        "containers_complete": True,
        "ring": {"present": True, "item_id": 3051, "count": 1},
        "candidates": [
            {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1}
        ],
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "validation_errors": [],
        "p10_blocker": None,
    }
    background = {
        "schema_version": preview.BACKGROUND_SCHEMA,
        "mode": "background_no_screen",
        "status": "ready",
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "promotion_allowed": False,
        "intrusive_actions_performed": [],
        "interaction_contract": dict(preview.INTERACTION_CONTRACT),
        "wrapper_invariants": {
            "client_process_stable": True,
            "screenshot_count_stable": True,
        },
        "capability": {
            "fresh": True,
            "contract_valid": True,
            "version_match": True,
            "runtime_actions": False,
            "runtime_core_actions": False,
            "equipment_shadow_observation": observation,
        },
    }
    rendered_preview = preview.build_preview(
        background=documents.document_from_payload(background),
        generated_at_unix_ms=NOW_MS,
    )
    inputs = change_plan.CanonicalInputs(
        capture_doctor=documents.document_from_payload(doctor_payload),
        observation_preview=documents.document_from_payload(rendered_preview),
    )
    plan = change_plan.evaluate_change_plan(
        inputs,
        equipped_item_id=3051,
        candidate_item_id=3048,
        candidate_source_container_id=2,
        candidate_source_slot_index=1,
        confirmation=change_plan.EXACT_CONFIRMATION,
        generated_at_unix_ms=NOW_MS,
    )
    assert plan["status"] == "plan_generated"
    return plan, current


def _configure_paths(monkeypatch, tmp_path: Path, plan: dict, current: dict) -> None:
    runtime = tmp_path / "runtime"
    local = tmp_path / ".ctoa-local" / "otclient"
    runtime.mkdir(parents=True)
    local.mkdir(parents=True)
    plan_path = runtime / "equipment_capture_profile_change_plan.json"
    profile_path = local / "equipment-shadow-capture-profile.json"
    plan_path.write_bytes(documents.canonical_bytes(plan) + b"\n")
    profile_path.write_bytes(documents.canonical_bytes(current) + b"\n")
    monkeypatch.setattr(apply_tool, "ROOT", tmp_path)
    monkeypatch.setattr(apply_tool, "PLAN_PATH", plan_path)
    monkeypatch.setattr(apply_tool, "PROFILE_PATH", profile_path)
    monkeypatch.setattr(
        apply_tool, "BACKUP_PATH", profile_path.with_suffix(".json.bak")
    )
    monkeypatch.setattr(apply_tool, "RECEIPT_PATH", runtime / "apply_receipt.json")
    monkeypatch.setattr(apply_tool.snapshot, "RUNTIME_ROOT", runtime)


def test_apply_requires_plan_hash_bound_confirmation(monkeypatch, tmp_path: Path):
    plan, current = _plan_payload()
    _configure_paths(monkeypatch, tmp_path, plan, current)

    report = apply_tool.apply_plan(plan_sha256=plan["plan_sha256"], confirmation=None)

    assert report["status"] == "blocked"
    assert report["blockers"] == ["operator_confirmation_mismatch"]
    assert report["profile_write_performed"] is False
    assert json.loads(apply_tool.PROFILE_PATH.read_text()) == current


def test_apply_writes_only_local_profile_backup_and_no_action_receipt(
    monkeypatch, tmp_path: Path
):
    plan, current = _plan_payload()
    _configure_paths(monkeypatch, tmp_path, plan, current)
    confirmation = apply_tool.exact_confirmation(plan["plan_sha256"])

    report = apply_tool.apply_plan(
        plan_sha256=plan["plan_sha256"], confirmation=confirmation
    )

    proposed = plan["plan"]["diff"]["set"]
    assert report["status"] == "applied"
    assert report["profile_write_performed"] is True
    assert json.loads(apply_tool.PROFILE_PATH.read_text()) == proposed
    assert json.loads(apply_tool.BACKUP_PATH.read_text()) == current
    assert (
        json.loads(apply_tool.RECEIPT_PATH.read_text())["acceptance_granted"] is False
    )
    assert report["runtime_actions"] is False
    assert report["dispatch_allowed"] is False
    assert report["item_movement_performed"] is False
