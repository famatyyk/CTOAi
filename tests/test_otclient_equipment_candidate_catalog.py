from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_candidate_catalog as catalog
from scripts.ops import otclient_equipment_observation_preview as preview


ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1783800000000
SCHEMA_PATH = ROOT / "schemas" / "equipment-candidate-catalog.schema.json"


def _observation(candidates: list[dict] | None = None) -> dict:
    return {
        "schema_version": preview.OBSERVATION_SCHEMA,
        "observation_id": "equipment-catalog-1",
        "observed_at_unix_ms": NOW_MS - 1000,
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_method",
        "inventory_api_available": True,
        "containers_complete": True,
        "ring": {"present": True, "item_id": 3051, "count": 1},
        "candidates": (
            candidates
            if candidates is not None
            else [{"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1}]
        ),
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
    }


def _preview(
    candidates: list[dict] | None = None,
    *,
    status: str = "preview_ready",
    blockers: list[str] | None = None,
) -> dict:
    observation = _observation(candidates)
    observation_hash = documents.canonical_sha256(observation)
    return {
        "schema_version": catalog.PREVIEW_SCHEMA,
        "generated_at_unix_ms": NOW_MS,
        "status": status,
        "source": "background_status",
        "source_sha256": "a" * 64,
        "observation_sha256": observation_hash,
        "observation": observation,
        "freshness": {
            "observed_at_unix_ms": NOW_MS - 1000,
            "age_ms": 1000,
            "max_age_ms": 10000,
            "fresh": True,
        },
        "provenance": {
            "producer_source": "otclient_guarded_adapter",
            "background_status_sha256": "a" * 64,
            "background_schema_version": "ctoa.otclient-headless-status.v1",
            "background_capability_fresh": True,
            "background_contract_valid": True,
            "version_match": True,
        },
        "blockers": blockers or [],
        "interaction_contract": dict(catalog.INTERACTION_CONTRACT),
        **{key: False for key in catalog.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _build(payload: dict | None = None) -> dict:
    return catalog.build_catalog(
        preview_document=documents.document_from_payload(payload or _preview()),
        generated_at_unix_ms=NOW_MS,
    )


def _validate(report: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return list(Draft202012Validator(schema).iter_errors(report))


def test_unique_catalog_is_deterministic_and_never_recommends():
    report = _build()
    assert report["status"] == "catalog_ready"
    assert report["blockers"] == []
    assert report["selection_policy"] == "none"
    assert report["recommendation"] is None
    assert report["groups"] == [
        {
            "item_id": 3048,
            "container_id": 2,
            "slot_index": 1,
            "count": 1,
            "occurrences": 1,
            "flags": [],
        }
    ]
    assert report["summary"]["candidate_count"] == 1
    assert all(report[key] is False for key in catalog.FALSE_FLAGS)
    assert report["intrusive_actions_performed"] == []
    assert _validate(report) == []
    assert report == _build(copy.deepcopy(_preview()))


def test_exact_duplicates_and_ambiguous_positions_and_items_are_grouped_not_selected():
    report = _build(
        _preview(
            [
                {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1},
                {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1},
                {"container_id": 2, "slot_index": 1, "item_id": 3049, "count": 1},
                {"container_id": 3, "slot_index": 1, "item_id": 3048, "count": 1},
            ]
        )
    )
    assert report["status"] == "blocked"
    assert {
        "candidate_exact_duplicate",
        "candidate_position_ambiguous",
        "candidate_item_ambiguous",
    } <= set(report["blockers"])
    assert len(report["groups"]) == 3
    assert report["recommendation"] is None
    assert all("recommended" not in group for group in report["groups"])
    assert _validate(report) == []


def test_zero_ids_and_empty_candidates_fail_closed():
    zero = _build(
        _preview(
            [
                {"container_id": 0, "slot_index": 1, "item_id": 3048, "count": 1},
                {"container_id": 2, "slot_index": 0, "item_id": 0, "count": 1},
            ]
        )
    )
    assert zero["status"] == "blocked"
    assert "candidate_zero_id" in zero["blockers"]
    assert zero["summary"]["zero_id_count"] == 2

    empty = _build(_preview([]))
    assert empty["status"] == "blocked"
    assert "candidates_empty" in empty["blockers"]
    assert empty["groups"] == []


def test_blocked_preview_is_bound_and_invalid_hash_is_reported():
    blocked = _preview(status="blocked", blockers=["equipment_observation_stale"])
    report = _build(blocked)
    assert report["status"] == "blocked"
    assert "preview_not_ready" in report["blockers"]
    assert report["preview_blockers"] == ["equipment_observation_stale"]
    assert report["groups"]
    assert _validate(report) == []

    tampered = _preview()
    tampered["observation"]["candidates"][0]["item_id"] = 9999
    report = _build(tampered)
    assert "preview_contract_invalid" in report["blockers"]
    assert "preview_observation_hash_mismatch" in report["blockers"]


def test_catalog_rejects_unknown_preview_fields_and_cli_path_overrides():
    tampered = _preview()
    tampered["unexpected"] = "do-not-copy"
    report = _build(tampered)
    assert report["status"] == "blocked"
    assert "preview_contract_invalid" in report["blockers"]
    assert "do-not-copy" not in json.dumps(report)

    command = [
        sys.executable,
        str(ROOT / "scripts" / "ops" / "otclient_equipment_candidate_catalog.py"),
    ]
    override = subprocess.run(
        [*command, "--no-write", "--preview", "other.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert override.returncode == 2
    completed = subprocess.run(
        [*command, "--no-write", "--allow-blocked"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "blocked"
