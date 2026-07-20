from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_capture_profile_change_plan as change_plan
from scripts.ops import otclient_equipment_observation_preview as preview


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "equipment-capture-profile-change-plan.schema.json"
NOW_MS = 1_783_800_000_000


def _observation() -> dict:
    return {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": preview.OBSERVATION_SCHEMA,
        "observed_at_unix_ms": NOW_MS - 1_000,
        "observation_id": "equipment-change-plan-1",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_method",
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


def _background() -> dict:
    return {
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
            "equipment_shadow_observation": _observation(),
        },
    }


def _doctor() -> dict:
    return {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": "blocked",
        "source": "local_operator_override",
        "path": str(change_plan.DEFAULT_LOCAL_CAPTURE_PROFILE),
        "sha256": "c" * 64,
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


def _inputs(*, doctor: dict | None = None, observation_preview: dict | None = None):
    rendered_preview = observation_preview or preview.build_preview(
        background=documents.document_from_payload(_background()),
        generated_at_unix_ms=NOW_MS,
    )
    assert rendered_preview["status"] == "preview_ready"
    return change_plan.CanonicalInputs(
        capture_doctor=documents.document_from_payload(doctor or _doctor()),
        observation_preview=documents.document_from_payload(rendered_preview),
    )


def _evaluate(inputs=None, **overrides) -> dict:
    values = {
        "equipped_item_id": 3051,
        "candidate_item_id": 3048,
        "candidate_source_container_id": 2,
        "candidate_source_slot_index": 1,
        "confirmation": change_plan.EXACT_CONFIRMATION,
        "generated_at_unix_ms": NOW_MS,
    }
    values.update(overrides)
    return change_plan.evaluate_change_plan(inputs or _inputs(), **values)


def _validate(report: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)


def test_strict_schema_and_blocker_contract_are_closed():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["blockers"]["items"]["enum"]) == set(
        change_plan.BLOCKER_ORDER
    )


def test_no_arguments_fail_closed_and_explain_without_a_plan():
    report = change_plan.evaluate_change_plan(_inputs(), generated_at_unix_ms=NOW_MS)

    _validate(report)
    assert report["status"] == "blocked"
    assert report["plan"] is None
    assert report["plan_sha256"] is None
    assert "explicit_identifiers_missing" in report["blockers"]
    assert "operator_confirmation_missing" in report["blockers"]
    assert "provide exact item IDs" in report["explanation"]
    assert report["acceptance_granted"] is False
    assert report["runtime_readiness_claimed"] is False
    assert report["profile_write_performed"] is False


def test_exact_preview_match_generates_only_hash_bound_plan_and_diff():
    report = _evaluate()

    _validate(report)
    assert report["status"] == "plan_generated"
    assert report["blockers"] == []
    assert report["operator_confirmation"] == {
        "required": True,
        "provided": True,
        "matched": True,
        "confirmation_sha256": change_plan.hashlib.sha256(
            change_plan.EXACT_CONFIRMATION.encode("utf-8")
        ).hexdigest(),
    }
    assert report["checks"]["capture_doctor_profile_valid"] is True
    assert report["checks"]["equipped_item_exact_match_in_preview"] is True
    assert report["checks"]["candidate_exact_match_in_preview"] is True
    plan = report["plan"]
    assert plan["expected_current_profile_sha256"] == "c" * 64
    assert plan["input_binding_sha256"] == report["input_binding_sha256"]
    assert plan["diff"]["from_sha256"] == "c" * 64
    assert plan["diff"]["to_sha256"] == plan["proposed_profile_sha256"]
    assert plan["diff"]["set"]["configured_by_operator"] is True
    assert plan["diff"]["set"]["equipped_item_id"] == 3051
    assert plan["diff"]["set"]["candidate_item_id"] == 3048
    assert plan["diff"]["set"]["candidate_source_container_id"] == 2
    assert plan["diff"]["set"]["candidate_source_slot_index"] == 1
    assert all(plan["diff"]["set"][key] is False for key in change_plan.FALSE_FLAGS)
    assert report["plan_sha256"] == documents.canonical_sha256(plan)
    assert report["interaction_contract"]["local_profile_read"] is False
    assert report["interaction_contract"]["local_profile_write"] is False
    assert all(report[key] is False for key in change_plan.FALSE_FLAGS)


def test_unique_candidate_item_id_auto_resolves_session_container_and_slot():
    report = _evaluate(
        candidate_source_container_id=None,
        candidate_source_slot_index=None,
    )

    _validate(report)
    assert report["status"] == "plan_generated"
    assert report["blockers"] == []
    assert report["requested_identifiers"] == {
        "equipped_item_id": 3051,
        "candidate_item_id": 3048,
        "candidate_source_container_id": 2,
        "candidate_source_slot_index": 1,
    }
    assert report["plan"]["diff"]["set"]["candidate_source_container_id"] == 2
    assert report["plan"]["diff"]["set"]["candidate_source_slot_index"] == 1


def test_auto_location_rejects_ambiguous_candidate_item_id():
    background = _background()
    background["capability"]["equipment_shadow_observation"]["candidates"].append(
        {"container_id": 3, "slot_index": 2, "item_id": 3048, "count": 1}
    )
    rendered_preview = preview.build_preview(
        background=documents.document_from_payload(background),
        generated_at_unix_ms=NOW_MS,
    )
    assert rendered_preview["status"] == "preview_ready"

    report = _evaluate(
        inputs=_inputs(observation_preview=rendered_preview),
        candidate_source_container_id=None,
        candidate_source_slot_index=None,
    )

    _validate(report)
    assert report["status"] == "blocked"
    assert report["plan"] is None
    assert "candidate_exact_match_ambiguous" in report["blockers"]


@pytest.mark.parametrize(
    ("overrides", "expected_blocker"),
    [
        ({"equipped_item_id": 0}, "explicit_identifiers_invalid"),
        ({"candidate_item_id": 3051}, "item_ids_not_distinct"),
        ({"equipped_item_id": 3052}, "equipped_item_preview_mismatch"),
        ({"candidate_item_id": 3049}, "candidate_exact_match_missing"),
        ({"candidate_source_container_id": 3}, "candidate_exact_match_missing"),
        ({"candidate_source_slot_index": 2}, "candidate_exact_match_missing"),
        ({"confirmation": "wrong"}, "operator_confirmation_mismatch"),
    ],
)
def test_invalid_ids_distinctness_exact_match_and_confirmation_fail_closed(
    overrides, expected_blocker
):
    report = _evaluate(**overrides)

    _validate(report)
    assert report["status"] == "blocked"
    assert report["plan"] is None
    assert expected_blocker in report["blockers"]


def test_partial_arguments_are_explicitly_incomplete():
    report = change_plan.evaluate_change_plan(
        _inputs(),
        equipped_item_id=3051,
        confirmation=change_plan.EXACT_CONFIRMATION,
        generated_at_unix_ms=NOW_MS,
    )

    _validate(report)
    assert "explicit_identifiers_incomplete" in report["blockers"]
    assert report["checks"]["identifiers_complete"] is False


def test_stale_preview_and_strict_input_tamper_fail_closed():
    stale = _evaluate(generated_at_unix_ms=NOW_MS + preview.MAX_AGE_MS + 1)
    assert stale["status"] == "blocked"
    assert "observation_preview_stale" in stale["blockers"]

    tampered_preview = copy.deepcopy(_inputs().observation_preview.payload)
    tampered_preview["unexpected"] = True
    tampered = _evaluate(inputs=_inputs(observation_preview=tampered_preview))
    assert tampered["status"] == "blocked"
    assert "observation_preview_schema_invalid" in tampered["blockers"]

    invalid_doctor = _doctor()
    invalid_doctor["runtime_readiness_claimed"] = True
    unsafe = _evaluate(inputs=_inputs(doctor=invalid_doctor))
    assert unsafe["status"] == "blocked"
    assert "capture_doctor_schema_invalid" in unsafe["blockers"]


def test_semantically_tampered_ready_preview_is_independently_rejected():
    tampered_preview = copy.deepcopy(_inputs().observation_preview.payload)
    tampered_preview["observation"]["online"] = "offline"
    tampered_preview["observation_sha256"] = documents.canonical_sha256(
        tampered_preview["observation"]
    )

    report = _evaluate(inputs=_inputs(observation_preview=tampered_preview))

    _validate(report)
    assert report["status"] == "blocked"
    assert "observation_preview_not_ready" in report["blockers"]
    assert report["checks"]["observation_preview_ready"] is False


def test_input_hashes_and_plan_hash_change_with_current_doctor_document():
    first = _evaluate()
    changed_doctor = _doctor()
    changed_doctor["next_action"] = "A separately reviewed wording change."
    second = _evaluate(inputs=_inputs(doctor=changed_doctor))

    assert first["status"] == second["status"] == "plan_generated"
    assert (
        first["input_sha256"]["capture_profile"]
        == second["input_sha256"]["capture_profile"]
    )
    assert (
        first["input_sha256"]["capture_doctor"]
        != second["input_sha256"]["capture_doctor"]
    )
    assert first["input_binding_sha256"] != second["input_binding_sha256"]
    assert first["plan_sha256"] != second["plan_sha256"]


def test_cli_default_is_blocked_and_allow_blocked_is_explanatory(monkeypatch, capsys):
    monkeypatch.setattr(change_plan, "read_canonical_inputs", _inputs)

    assert change_plan.main(["--no-write"]) == 1
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["status"] == "blocked"
    assert change_plan.main(["--no-write", "--allow-blocked"]) == 0


def test_cli_exact_args_generate_plan_but_reject_input_path_overrides(
    monkeypatch, capsys
):
    monkeypatch.setattr(change_plan, "read_canonical_inputs", _inputs)
    monkeypatch.setattr(change_plan.time, "time", lambda: NOW_MS / 1000)
    args = [
        "--equipped-item-id",
        "3051",
        "--candidate-item-id",
        "3048",
        "--candidate-container-id",
        "2",
        "--candidate-slot-index",
        "1",
        "--confirm",
        change_plan.EXACT_CONFIRMATION,
        "--no-write",
    ]

    assert change_plan.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "plan_generated"
    with pytest.raises(SystemExit) as exc:
        change_plan.main(["--capture-doctor", "escape.json", "--no-write"])
    assert exc.value.code == 2


def test_cli_refresh_preview_builds_and_consumes_one_fresh_snapshot(
    monkeypatch, capsys
):
    monkeypatch.setattr(change_plan, "read_canonical_inputs", _inputs)
    monkeypatch.setattr(
        change_plan.preview,
        "_read_background",
        lambda: documents.document_from_payload(_background()),
    )
    monkeypatch.setattr(change_plan.time, "time", lambda: NOW_MS / 1000)

    assert (
        change_plan.main(
            [
                "--equipped-item-id",
                "3051",
                "--candidate-item-id",
                "3048",
                "--confirm",
                change_plan.EXACT_CONFIRMATION,
                "--refresh-preview",
                "--no-write",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "plan_generated"
    assert report["requested_identifiers"]["candidate_source_container_id"] == 2
    assert report["requested_identifiers"]["candidate_source_slot_index"] == 1


def test_writer_is_confined_to_runtime_and_preserves_local_profile(
    monkeypatch, tmp_path: Path
):
    runtime_root = tmp_path / "runtime"
    output = runtime_root / "solteria_helper_dev" / change_plan.DEFAULT_OUTPUT.name
    local_profile = tmp_path / ".ctoa-local" / "otclient" / "profile.json"
    local_profile.parent.mkdir(parents=True)
    local_profile.write_text("preserve", encoding="utf-8")
    report = change_plan.evaluate_change_plan(_inputs(), generated_at_unix_ms=NOW_MS)
    monkeypatch.setattr(change_plan, "RUNTIME_ROOT", runtime_root)
    monkeypatch.setattr(change_plan, "DEFAULT_OUTPUT", output)

    change_plan.write_report(report)

    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "blocked"
    assert local_profile.read_text(encoding="utf-8") == "preserve"
