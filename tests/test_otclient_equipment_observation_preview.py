from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_equipment_observation_preview as preview


ROOT = Path(__file__).resolve().parents[1]
NOW_MS = 1783800000000
SCHEMA_PATH = ROOT / "schemas" / "equipment-observation-preview.schema.json"


def _observation(*, source: str = "otclient_guarded_adapter") -> dict:
    return {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": preview.OBSERVATION_SCHEMA,
        "observed_at_unix_ms": NOW_MS - 1000,
        "observation_id": "equipment-preview-1",
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
        "producer_source": source,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "validation_errors": [],
        "p10_blocker": None,
    }


def _background(observation: dict | None = None) -> dict:
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
            "equipment_shadow_observation": observation or _observation(),
        },
    }


def _build(payload: dict | None = None, now: int = NOW_MS) -> dict:
    return preview.build_preview(
        background=documents.document_from_payload(payload or _background()),
        generated_at_unix_ms=now,
    )


def _validate(report: dict) -> list:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return list(Draft202012Validator(schema).iter_errors(report))


def test_preview_is_profile_independent_and_projects_only_configuration_fields():
    report = _build()

    assert report["status"] == "preview_ready"
    assert report["blockers"] == []
    assert report["source"] == "background_status"
    assert report["observation"]["ring"] == {
        "present": True,
        "item_id": 3051,
        "count": 1,
    }
    assert report["observation"]["candidates"] == [
        {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1}
    ]
    assert "validation_errors" not in report["observation"]
    assert "p10_blocker" not in report["observation"]
    assert "configured_by_operator" not in report
    assert report["freshness"] == {
        "observed_at_unix_ms": NOW_MS - 1000,
        "age_ms": 1000,
        "max_age_ms": 10000,
        "fresh": True,
    }
    assert all(report[key] is False for key in preview.FALSE_FLAGS)
    assert report["intrusive_actions_performed"] == []


def test_schema_validates_ready_and_blocked_previews():
    ready = _build()
    assert _validate(ready) == []

    blocked_payload = _background()
    blocked_payload["capability"]["equipment_shadow_observation"][
        "observed_at_unix_ms"
    ] = NOW_MS - preview.MAX_AGE_MS - 1
    blocked = _build(blocked_payload)
    assert blocked["status"] == "blocked"
    assert "equipment_observation_stale" in blocked["blockers"]
    assert blocked["observation"] is not None
    assert _validate(blocked) == []


def test_stale_future_and_untrusted_provenance_are_explicit_blockers():
    stale = _build()
    stale_payload = _background()
    stale_payload["capability"]["equipment_shadow_observation"][
        "observed_at_unix_ms"
    ] = NOW_MS - preview.MAX_AGE_MS - 1
    stale = _build(stale_payload)
    assert stale["status"] == "blocked"
    assert stale["freshness"]["fresh"] is False
    assert "equipment_observation_stale" in stale["blockers"]

    future_payload = _background()
    future_payload["capability"]["equipment_shadow_observation"]["observed_at_unix_ms"] = NOW_MS + 1
    future = _build(future_payload)
    assert "equipment_observation_future" in future["blockers"]
    assert future["freshness"]["age_ms"] == -1

    fixture = _build(_background(_observation(source="fixture")))
    assert fixture["status"] == "blocked"
    assert fixture["observation"]["producer_source"] == "fixture"
    assert "equipment_observation_provenance_untrusted" in fixture["blockers"]


def test_invalid_background_and_observation_fail_closed_without_leaking_raw_fields():
    background = _background()
    background["capability"]["equipment_shadow_observation"]["unexpected"] = "redact-me"
    report = _build(background)
    assert report["status"] == "blocked"
    assert report["observation"] is None
    assert "equipment_observation_invalid" in report["blockers"]
    assert "redact-me" not in json.dumps(report)

    blocked = _background()
    blocked["status"] = "blocked"
    blocked["capability"]["contract_valid"] = False
    report = _build(blocked)
    assert report["status"] == "blocked"
    assert "background_not_ready" in report["blockers"]
    assert "background_contract_invalid" in report["blockers"]


def test_preview_does_not_accept_external_paths_or_write_in_no_write_mode(tmp_path: Path):
    command = [
        sys.executable,
        str(ROOT / "scripts" / "ops" / "otclient_equipment_observation_preview.py"),
    ]
    override = subprocess.run(
        [*command, "--no-write", "--json-out", str(tmp_path / "escape.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert override.returncode == 2
    before = preview.DEFAULT_OUTPUT.exists()
    completed = subprocess.run(
        [*command, "--no-write", "--allow-blocked"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    rendered = json.loads(completed.stdout)
    assert rendered["source"] == "background_status"
    assert rendered["status"] == "blocked"
    assert preview.DEFAULT_OUTPUT.exists() is before


def test_preview_report_is_deterministic_for_same_background_and_time():
    payload = _background()
    first = _build(payload)
    second = _build(copy.deepcopy(payload))
    assert first == second
    assert first["source_sha256"] == first["provenance"]["background_status_sha256"]
    assert first["observation_sha256"] is not None
