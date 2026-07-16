from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_dependency_preflight as dependency
from scripts.ops import otclient_equipment_observation_preview as preview
from scripts.ops import otclient_equipment_operator_readiness as readiness


ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1_783_800_000_000
SHA = "a" * 64


def _doctor() -> dict:
    return {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": "ready",
        "source": "local_operator_override",
        "path": str(ROOT / ".ctoa-local/otclient/equipment-shadow-capture-profile.json"),
        "sha256": SHA,
        "configured_by_operator": True,
        "slot": "ring",
        "identifiers_present": True,
        "candidate_slot_index_valid": True,
        "no_action_contract": True,
        "blockers": [],
        "next_action": "Run the separate dependency preflight.",
        "runtime_actions": False,
        "live_file_writes": False,
        "runtime_readiness_claimed": False,
    }


def _preview() -> dict:
    observation = {
        "schema_version": "ctoa.equipment-shadow-observation.v1",
        "observation_id": "equipment-operational-1",
        "observed_at_unix_ms": NOW_MS - 1_000,
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
    }
    return {
        "schema_version": preview.SCHEMA,
        "generated_at_unix_ms": NOW_MS,
        "status": "preview_ready",
        "source": "background_status",
        "source_sha256": SHA,
        "observation_sha256": documents.canonical_sha256(observation),
        "observation": observation,
        "freshness": {
            "observed_at_unix_ms": NOW_MS - 1_000,
            "age_ms": 1_000,
            "max_age_ms": 6_000,
            "fresh": True,
        },
        "provenance": {
            "producer_source": "otclient_guarded_adapter",
            "background_status_sha256": SHA,
            "background_schema_version": "ctoa.otclient-headless-status.v1",
            "background_capability_fresh": True,
            "background_contract_valid": True,
            "version_match": True,
        },
        "blockers": [],
        "interaction_contract": dict(preview.INTERACTION_CONTRACT),
        **{key: False for key in readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _dependency() -> dict:
    checks = {
        "p8_background_valid": True,
        "p8_background_fresh": True,
        "p9_report_ready": True,
        "p9_receipt_accepted": True,
        "p9_receipt_report_bound": True,
        "p9_receipt_trace_bound": True,
        "p9_bound_to_current_p8": True,
        "capture_doctor_ready": True,
        "observation_preview_ready": True,
        "observation_preview_bound_to_current_p8": True,
        "non_fixture_chain": True,
        "no_action_chain": True,
    }
    hashes = {name: SHA for name in dependency.INPUT_NAMES}
    basis = {
        "schema_version": dependency.SCHEMA,
        "status": "passed",
        "dependencies_satisfied": True,
        "checks": checks,
        "blockers": [],
        "input_sha256": hashes,
        "canonical_input_sha256": SHA,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        **{key: False for key in readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    return {
        "schema_version": dependency.SCHEMA,
        "mode": dependency.MODE,
        "evaluated_at_unix_ms": NOW_MS,
        "status": "passed",
        "dependencies_satisfied": True,
        "inputs": {},
        "input_sha256": hashes,
        "canonical_input_sha256": SHA,
        "checks": checks,
        "upstream_blockers": {name: [] for name in dependency.INPUT_NAMES},
        "blockers": [],
        "decision_sha256": documents.canonical_sha256(basis),
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        "operator_review_required": True,
        "repo_report_write_only": True,
        "live_file_writes": False,
        **{key: False for key in readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _catalog(preview_sha: str) -> dict:
    return {
        "schema_version": "ctoa.equipment-candidate-catalog.v1",
        "generated_at_unix_ms": NOW_MS,
        "status": "catalog_ready",
        "source": "equipment_observation_preview",
        "preview_sha256": preview_sha,
        "preview_status": "preview_ready",
        "preview_blockers": [],
        "selection_policy": "none",
        "recommendation": None,
        "ring": {"present": True, "item_id": 3051, "count": 1},
        "groups": [
            {
                "item_id": 3048,
                "container_id": 2,
                "slot_index": 1,
                "count": 1,
                "occurrences": 1,
                "flags": [],
            }
        ],
        "summary": {
            "candidate_count": 1,
            "exact_group_count": 1,
            "duplicate_group_count": 0,
            "unique_item_id_count": 1,
            "ambiguous_item_id_count": 0,
            "position_conflict_count": 0,
            "zero_id_count": 0,
        },
        "blockers": [],
        **{key: False for key in readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _change_plan() -> dict:
    plan = {
        "plan_id": "equipment-capture-profile-plan-aaaaaaaaaaaaaaaa",
        "target_profile": ".ctoa-local/otclient/equipment-shadow-capture-profile.json",
        "input_binding_sha256": SHA,
        "expected_current_profile_sha256": SHA,
        "proposed_profile_sha256": "b" * 64,
        "diff": {"operation": "replace_document_after_separate_operator_review"},
    }
    return {
        "schema_version": readiness.CHANGE_PLAN_SCHEMA,
        "generated_at_unix_ms": NOW_MS,
        "status": "plan_generated",
        "mode": readiness.change_plan.MODE,
        "sources": {},
        "input_status": {},
        "input_sha256": {},
        "input_binding_sha256": SHA,
        "requested_identifiers": {},
        "operator_confirmation": {},
        "checks": {},
        "observation_age_ms": 1_000,
        "blockers": [],
        "plan": plan,
        "plan_sha256": documents.canonical_sha256(plan),
        "explanation": "Data-only plan generated.",
        "operator_review_required": True,
        "acceptance_granted": False,
        "eligibility_changed": False,
        "runtime_readiness_claimed": False,
        "profile_write_performed": False,
        "repo_report_write_only": True,
        "live_file_writes": False,
        "interaction_contract": dict(readiness.change_plan.INTERACTION_CONTRACT),
        **{key: False for key in readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _ready_artifacts() -> dict[str, documents.InputDocument]:
    preview_document = documents.document_from_payload(_preview())
    return {
        "capture_doctor": documents.document_from_payload(_doctor()),
        "observation_preview": preview_document,
        "dependency_preflight": documents.document_from_payload(_dependency()),
        "candidate_catalog": documents.document_from_payload(
            _catalog(preview_document.sha256)
        ),
        "change_plan": documents.document_from_payload(_change_plan()),
    }


def _schema() -> dict:
    return json.loads(
        (ROOT / "schemas/equipment-operator-readiness.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_schema_is_closed_and_blocker_categories_are_exact() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["$defs"]["blockerCode"]["enum"]) == set(
        readiness.BLOCKER_ORDER
    )


def test_all_fixed_inputs_ready_only_explains_and_never_changes_eligibility() -> None:
    report = readiness.evaluate_readiness(
        _ready_artifacts(), generated_at_unix_ms=NOW_MS
    )
    Draft202012Validator(_schema()).validate(report)
    assert report["status"] == "operator_inputs_ready"
    assert report["operator_inputs_ready"] is True
    assert report["blockers"] == []
    assert report["next_actions"] == []
    assert report["eligibility_changed"] is False
    assert report["operational_readiness_claimed"] is False
    assert all(report[key] is False for key in readiness.FALSE_FLAGS)
    assert report["intrusive_actions_performed"] == []


def test_missing_new_artifacts_fail_closed_with_ordered_safe_commands() -> None:
    artifacts = _ready_artifacts()
    artifacts["candidate_catalog"] = documents.document_from_payload(None, "missing")
    artifacts["change_plan"] = documents.document_from_payload(None, "missing")
    report = readiness.evaluate_readiness(artifacts, generated_at_unix_ms=NOW_MS)

    assert report["status"] == "blocked"
    assert report["blockers"] == [
        "candidate_catalog_missing",
        "change_plan_missing",
    ]
    assert [action["command"] for action in report["next_actions"]] == [
        ".\\ctoa.ps1 otp10catalog",
        ".\\ctoa.ps1 otp10plan",
    ]
    assert all(action["changes_eligibility"] is False for action in report["next_actions"])


def test_missing_invalid_stale_and_upstream_are_distinct() -> None:
    artifacts = _ready_artifacts()
    artifacts["capture_doctor"] = documents.document_from_payload(None, "missing")
    invalid_preview = _preview()
    invalid_preview["runtime_actions"] = True
    artifacts["observation_preview"] = documents.document_from_payload(invalid_preview)
    stale_dependency = _dependency()
    stale_dependency["evaluated_at_unix_ms"] = NOW_MS - 6_001
    artifacts["dependency_preflight"] = documents.document_from_payload(stale_dependency)
    blocked_catalog = _catalog(artifacts["observation_preview"].sha256)
    blocked_catalog["status"] = "blocked"
    blocked_catalog["blockers"] = ["candidates_empty"]
    artifacts["candidate_catalog"] = documents.document_from_payload(blocked_catalog)

    report = readiness.evaluate_readiness(artifacts, generated_at_unix_ms=NOW_MS)

    assert "capture_doctor_missing" in report["blockers"]
    assert "observation_preview_invalid" in report["blockers"]
    assert "dependency_preflight_stale" in report["blockers"]
    assert "candidate_catalog_upstream" in report["blockers"]
    assert report["blocker_counts"] == {
        "missing": 1,
        "invalid": 1,
        "stale": 1,
        "upstream": 1,
        "total": 4,
    }


def test_dependency_upstream_maps_p9_actions_before_preflight_regeneration() -> None:
    artifacts = _ready_artifacts()
    blocked = _dependency()
    blocked["status"] = "blocked"
    blocked["dependencies_satisfied"] = False
    blocked["checks"]["p9_receipt_accepted"] = False
    blocked["blockers"] = ["p9_receipt_missing"]
    blocked["upstream_blockers"]["p9_receipt"] = ["p9_receipt_missing"]
    basis = {
        "schema_version": blocked["schema_version"],
        "status": blocked["status"],
        "dependencies_satisfied": blocked["dependencies_satisfied"],
        "checks": blocked["checks"],
        "blockers": blocked["blockers"],
        "input_sha256": blocked["input_sha256"],
        "canonical_input_sha256": blocked["canonical_input_sha256"],
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        **{key: False for key in readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    blocked["decision_sha256"] = documents.canonical_sha256(basis)
    artifacts["dependency_preflight"] = documents.document_from_payload(blocked)

    report = readiness.evaluate_readiness(artifacts, generated_at_unix_ms=NOW_MS)

    assert "dependency_preflight_upstream" in report["blockers"]
    commands = [action["command"] for action in report["next_actions"]]
    assert commands[:2] == [
        '.\\ctoa.ps1 otp9accept "accept P9 conditions shadow"',
        ".\\ctoa.ps1 otp10preflight",
    ]
