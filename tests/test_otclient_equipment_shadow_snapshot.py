from __future__ import annotations

import json
from pathlib import Path

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_shadow_snapshot as producer


ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1783800000000


def _observation() -> dict:
    return {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": producer.OBSERVATION_SCHEMA,
        "observed_at_unix_ms": NOW_MS - 1000,
        "observation_id": "equipment-operational-1",
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
        "schema_version": producer.BACKGROUND_SCHEMA,
        "mode": "background_no_screen",
        "status": "ready",
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "promotion_allowed": False,
        "intrusive_actions_performed": [],
        "interaction_contract": dict(producer.BACKGROUND_INTERACTION_CONTRACT),
        "wrapper_invariants": dict(producer.BACKGROUND_WRAPPER_INVARIANTS),
        "capability": {
            "fresh": True,
            "contract_valid": True,
            "version_match": True,
            "runtime_actions": False,
            "runtime_core_actions": False,
            "equipment_shadow_observation": _observation(),
        },
    }


def _profile() -> dict:
    return {
        "schema_version": producer.CAPTURE_SCHEMA,
        "configured_by_operator": True,
        "slot": "ring",
        "equipped_item_id": 3051,
        "candidate_item_id": 3048,
        "candidate_source_container_id": 2,
        "candidate_source_slot_index": 1,
        "max_observation_age_ms": 6000,
        "retry_budget": 0,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
    }


def _build(background: dict | None = None, profile: dict | None = None):
    return producer.build_ingest(
        background=documents.document_from_payload(background or _background()),
        capture_profile=documents.document_from_payload(profile or _profile()),
        generated_at_unix_ms=NOW_MS,
    )


def test_passive_background_observation_produces_hash_bound_snapshot():
    report, snapshot = _build()
    assert report["status"] == "snapshot_ready"
    assert report["blockers"] == []
    assert report["snapshot_written"] is False
    assert snapshot is not None
    assert snapshot["producer_source"] == "otclient_guarded_adapter"
    assert snapshot["rollback_item_id"] == snapshot["equipped_item_id"] == 3051
    assert snapshot["candidate_item_id"] == 3048
    assert snapshot["inventory_revision"] == snapshot["rollback_inventory_revision"]
    assert len(snapshot["source_report_sha256"]) == 64
    assert all(snapshot[key] is False for key in producer.FALSE_FLAGS)
    assert snapshot["intrusive_actions_performed"] == []


def test_unconfigured_profile_and_ambiguous_candidate_fail_closed():
    profile = _profile()
    profile["configured_by_operator"] = False
    report, snapshot = _build(profile=profile)
    assert snapshot is None
    assert "capture_profile_not_configured" in report["blockers"]

    background = _background()
    background["capability"]["equipment_shadow_observation"]["candidates"].append(
        {"container_id": 3, "slot_index": 1, "item_id": 3048, "count": 1}
    )
    report, snapshot = _build(background=background)
    assert snapshot is None
    assert "candidate_not_unique" in report["blockers"]

    profile = _profile()
    profile["candidate_source_slot_index"] = 2
    report, snapshot = _build(profile=profile)
    assert snapshot is None
    assert "candidate_slot_mismatch" in report["blockers"]


def test_stale_unsafe_or_nonready_background_never_produces_snapshot():
    within_transport = _background()
    within_transport["capability"]["equipment_shadow_observation"][
        "observed_at_unix_ms"
    ] = NOW_MS - producer.MAX_AGE_MS - producer.CAPTURE_TRANSPORT_ALLOWANCE_MS
    within_report, within_snapshot = _build(background=within_transport)
    assert within_report["status"] == "snapshot_ready"
    assert within_snapshot is not None

    background = _background()
    background["capability"]["equipment_shadow_observation"][
        "observed_at_unix_ms"
    ] = (
        NOW_MS
        - producer.MAX_AGE_MS
        - producer.CAPTURE_TRANSPORT_ALLOWANCE_MS
        - 1
    )
    report, snapshot = _build(background=background)
    assert snapshot is None
    assert "equipment_observation_stale" in report["blockers"]

    background = _background()
    background["capability"]["equipment_shadow_observation"]["runtime_actions"] = True
    report, snapshot = _build(background=background)
    assert snapshot is None
    assert "equipment_observation_invalid" in report["blockers"]
    assert "unsafe_contract" in report["blockers"]

    background = _background()
    background["status"] = "blocked"
    report, snapshot = _build(background=background)
    assert snapshot is None
    assert "background_not_ready" in report["blockers"]


def test_malformed_or_duplicate_nested_inventory_fails_closed_without_exception():
    for candidates in (
        ["not-an-item"],
        [{"container_id": 2, "slot_index": 1, "item_id": "3048", "count": 1}],
        [
            {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1},
            {"container_id": 2, "slot_index": 1, "item_id": 3049, "count": 1},
        ],
    ):
        background = _background()
        background["capability"]["equipment_shadow_observation"]["candidates"] = candidates
        report, snapshot = _build(background=background)
        assert snapshot is None
        assert "equipment_observation_invalid" in report["blockers"]


def test_capture_and_ingest_schemas_are_closed():
    for name in (
        "equipment-shadow-observation.schema.json",
        "equipment-shadow-capture-profile.schema.json",
        "equipment-shadow-snapshot-ingest.schema.json",
    ):
        schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False


def test_default_capture_profile_is_explicitly_unconfigured():
    profile = json.loads(producer.DEFAULT_CAPTURE_PROFILE.read_text(encoding="utf-8"))
    assert profile["configured_by_operator"] is False
    assert profile["equipped_item_id"] == profile["candidate_item_id"] == 0


def test_capture_profile_resolution_prefers_only_fixed_ignored_local_override(
    monkeypatch, tmp_path: Path
):
    tracked = tmp_path / "config" / "equipment.json"
    local = tmp_path / ".ctoa-local" / "otclient" / "equipment.json"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(producer, "DEFAULT_CAPTURE_PROFILE", tracked)
    monkeypatch.setattr(producer, "DEFAULT_LOCAL_CAPTURE_PROFILE", local)

    assert producer.resolve_capture_profile() == (tracked, "tracked_safe_template")
    local.parent.mkdir(parents=True)
    local.write_text("{}", encoding="utf-8")
    assert producer.resolve_capture_profile() == (local, "local_operator_override")

    other = tmp_path / "other.json"
    other.write_text("{}", encoding="utf-8")
    try:
        producer.resolve_capture_profile(other)
    except ValueError as exc:
        assert "fixed .ctoa-local override" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("arbitrary capture profile path was accepted")


def test_tracked_template_cannot_be_turned_into_configured_operator_state(
    tmp_path: Path,
):
    path = tmp_path / "template.json"
    profile = _profile()
    profile["configured_by_operator"] = True
    path.write_text(json.dumps(profile), encoding="utf-8")

    document = producer.load_capture_profile(path, "tracked_safe_template")

    assert document.status != "loaded"
    assert document.payload is None
