from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.ops import otclient_headless_evidence as evidence
from scripts.ops import otclient_headless_status as status


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"
CLI = ROOT / "ctoa.ps1"
REPORTER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_client_reporter.lua"
CONDITIONS_OBSERVATION_SCHEMA_FILE = (
    ROOT / "schemas" / "conditions-observation.schema.json"
)
SANDBOX_SMOKE = (
    ROOT / "scripts" / "ops" / "otclient_runtime_module_gates_sandbox_smoke.py"
)
NOW = datetime(2026, 7, 11, 16, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1_000)


@pytest.mark.parametrize(
    "relative",
    [
        "ctoa_project_loader.lua",
        "mods/ctoa_chooser/ctoa_chooser.otmod",
        "mods/ctoa_otclient/ctoa_native_helper.lua",
        "mods/ctoa_safe/ctoa_safe_helper.lua",
    ],
)
def test_live_manifest_accepts_only_fixed_project_package_paths(relative: str):
    assert status._manifest_relative_path(relative) == Path(relative)


@pytest.mark.parametrize(
    "relative",
    [
        "mods/arbitrary/injected.lua",
        "mods/ctoa_safe/nested/injected.lua",
        "../ctoa_project_loader.lua",
    ],
)
def test_live_manifest_rejects_paths_outside_fixed_project_package(relative: str):
    assert status._manifest_relative_path(relative) is None


def _conditions_observation(observed_at_ms: int = NOW_MS - 1_000) -> dict[str, object]:
    return {
        "schema_version": evidence.CONDITIONS_OBSERVATION_SCHEMA,
        "observed_at_unix_ms": observed_at_ms,
        "observation_id": f"conditions-{observed_at_ms}",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_method",
        "condition_id": "paralyze",
        "condition_state": "present",
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "fixture",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
    }


def _equipment_observation(observed_at_ms: int = NOW_MS - 1_000) -> dict[str, object]:
    return {
        "schema_version": evidence.EQUIPMENT_SHADOW_OBSERVATION_SCHEMA,
        "observed_at_unix_ms": observed_at_ms,
        "observation_id": f"equipment-{observed_at_ms}",
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
        "producer_source": "fixture",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _resign_promotion(dev: Path, client: Path) -> None:
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _write_json(
        dev / "live_promotion.json",
        {
            "name": "solteria-helper-live-promotion",
            "created_at": manifest.get("generated_at_utc"),
            "approval_switch": "ApproveLiveDeploy",
            "verification": "stage_live_sha256_match",
            "helper_version": manifest.get("helper_version"),
            "verified_file_count": len(manifest.get("files", [])),
            "live_manifest": str(manifest_path.resolve()),
            "live_manifest_sha256": _sha256(manifest_path),
            "live_client": str(client.resolve()),
        },
    )


def _fixture(
    tmp_path: Path,
    *,
    observed_at_ms: int = NOW_MS - 1_000,
) -> tuple[Path, Path, Path]:
    local_app_data = tmp_path / "LocalAppData"
    client = local_app_data / "Solteria" / "client"
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    target = client / "mods" / "ctoa_otclient" / "sample.lua"
    target.parent.mkdir(parents=True)
    target.write_text("return true\n", encoding="utf-8")
    dev.mkdir(parents=True)

    _write_json(
        dev / "live_manifest.json",
        {
            "schema_version": status.LIVE_MANIFEST_SCHEMA,
            "origin": status.LIVE_MANIFEST_ORIGIN,
            "generated_at_utc": "2026-07-11T15:55:00+00:00",
            "helper_version": "v2.2.1",
            "files": [
                {
                    "path": "mods/ctoa_otclient/sample.lua",
                    "sha256": _sha256(target),
                    "bytes": target.stat().st_size,
                }
            ],
        },
    )
    _resign_promotion(dev, client)

    capability = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    _write_json(
        capability,
        {
            "schema_version": evidence.CAPABILITY_SCHEMA,
            "observed_at_unix_ms": observed_at_ms,
            "heartbeat_interval_ms": evidence.EXPECTED_HEARTBEAT_INTERVAL_MS,
            "heartbeat_status": "online",
            "online": True,
            "helper_version": "v2.2.1",
            "protocol_status": "pending_protocol_source",
            "safe_fallback": True,
            "runtime_actions": False,
            "runtime_session_armed": False,
            "runtime_state": "disarmed",
            "runtime_enabled": False,
            "supported_modules": ["client_reporter"],
            "runtime_core": {
                "status": "available",
                "mode": "passive",
                "runtime_actions": False,
            },
        },
    )
    (client / "ctoa_local.log").write_text(
        "\n".join(
            [
                "old Lua exception",
                "Initialized successfully v2.2.1",
                "[CTOA-OTC-HELPER] Runtime disarmed",
                "[CTOA-OTC-HELPER] API probe (manual): core[online=yes localPlayer=yes] player[hp=100/100 pz=no]",
            ]
        ),
        encoding="utf-8",
    )
    return local_app_data, client, dev


def _build(
    client: Path,
    dev: Path,
    *,
    process_count: int = 1,
    process_start_unix_ms: int = NOW_MS - 10_000,
    explicit_report: Path | None = None,
) -> dict[str, object]:
    return status.build_status(
        client_root=client,
        live_manifest_path=dev / "live_manifest.json",
        live_promotion_path=dev / "live_promotion.json",
        process_count=process_count,
        process_start_unix_ms=process_start_unix_ms,
        explicit_report=explicit_report,
        now=NOW,
    )


def _mutate_capability(client: Path, mutation: str) -> None:
    path = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "heartbeat_offline":
        payload["heartbeat_status"] = "offline"
    elif mutation == "game_offline":
        payload["online"] = False
    elif mutation == "missing_runtime_actions":
        payload.pop("runtime_actions")
    elif mutation == "missing_runtime_core_actions":
        payload["runtime_core"].pop("runtime_actions")
    elif mutation == "wrong_interval":
        payload["heartbeat_interval_ms"] = 60_000
    elif mutation == "version_mismatch":
        payload["helper_version"] = "v9.9.9"
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    _write_json(path, payload)


def _set_conditions_observation(client: Path, value: object) -> None:
    path = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["conditions_observation"] = value
    _write_json(path, payload)


def _set_equipment_observation(client: Path, value: object) -> None:
    path = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["equipment_shadow_observation"] = value
    _write_json(path, payload)


def test_bounded_tail_and_session_parser_ignore_old_errors(tmp_path: Path):
    log = tmp_path / "client.log"
    log.write_text(
        "X" * 1_000
        + "\nInitialized successfully v2.2.1\n"
        + "[CTOA-OTC-HELPER] Runtime armed\n"
        + "[CTOA-OTC-HELPER] Runtime disarmed\n",
        encoding="utf-8",
    )

    tail = evidence.bounded_tail_text(log, 256)
    session = evidence.current_session(tail)

    assert len(tail.encode("utf-8")) <= 256
    assert evidence.latest_runtime_state(session) == "disarmed"
    assert evidence.summarize_log(log)["lua_exception_count"] == 0


def test_background_status_is_ready_only_from_trusted_live_evidence(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)

    report = _build(client, dev)

    assert report["status"] == "ready"
    assert report["mode"] == "background_no_screen"
    assert report["advisory_only"] is True
    assert report["safe_to_run_while_playing"] is True
    assert report["promotion_allowed"] is False
    assert report["dispatch_allowed"] is False
    assert report["runtime_actions"] is False
    assert report["process_count"] == 1
    assert report["integrity"]["pin_status"] == "trusted"
    assert report["integrity"]["pin_remediation"] == {
        "classification": "trusted",
        "required_action": "none",
        "observer_can_write_trust_anchor": False,
        "historical_rebinding_allowed": False,
        "requires_current_release_gate": False,
        "requires_explicit_live_approval": False,
    }
    assert report["integrity"]["matched_file_count"] == 1
    assert report["integrity"]["baseline_recorded"] is False
    assert report["capability"]["fresh"] is True
    assert report["capability"]["version_match"] is True
    assert report["capability"]["heartbeat_after_process_start"] is True
    assert report["capability"]["conditions_observation"]["status"] == "missing"
    assert (
        report["capability"]["conditions_observation"]["p9_blocker"]
        == "conditions_observation_missing"
    )
    assert report["intrusive_actions_performed"] == []
    assert report["blockers"] == []


def test_valid_conditions_observation_is_strictly_normalized_without_changing_p8(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)
    _set_conditions_observation(client, _conditions_observation())

    report = _build(client, dev)
    observation = report["capability"]["conditions_observation"]

    assert report["status"] == "ready"
    assert report["blockers"] == []
    assert observation == {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": evidence.CONDITIONS_OBSERVATION_SCHEMA,
        "observed_at_unix_ms": NOW_MS - 1_000,
        "observation_id": f"conditions-{NOW_MS - 1_000}",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_method",
        "condition_id": "paralyze",
        "condition_state": "present",
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "fixture",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "validation_errors": [],
        "p9_blocker": None,
    }


def test_valid_equipment_observation_is_bounded_and_does_not_authorize_p10(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    _set_equipment_observation(client, _equipment_observation())

    report = _build(client, dev)
    observation = report["capability"]["equipment_shadow_observation"]

    assert report["status"] == "ready"
    assert observation["status"] == "valid"
    assert observation["valid"] is True
    assert observation["ring"] == {"present": True, "item_id": 3051, "count": 1}
    assert observation["candidates"] == [
        {"container_id": 2, "slot_index": 1, "item_id": 3048, "count": 1}
    ]
    assert observation["p10_blocker"] is None
    assert all(observation[key] is False for key in evidence.CONDITIONS_ACTION_FLAGS)


def test_equipment_observation_unknown_fields_duplicates_and_unsafe_flags_fail_closed(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    value = _equipment_observation()
    assert isinstance(value["candidates"], list)
    value["candidates"].append(
        {"container_id": 2, "slot_index": 1, "item_id": 9999, "count": 1}
    )
    _set_equipment_observation(client, value)
    report = _build(client, dev)
    observation = report["capability"]["equipment_shadow_observation"]
    assert report["status"] == "ready"
    assert observation["status"] == "invalid"
    assert "candidate_order_or_duplicate" in observation["validation_errors"]

    value = _equipment_observation()
    value["runtime_actions"] = True
    _set_equipment_observation(client, value)
    report = _build(client, dev)
    assert report["status"] == "blocked"
    assert report["capability"]["status"] == "unsafe_runtime_claim"


@pytest.mark.parametrize(
    ("mutation", "expected_error", "p8_unsafe"),
    [
        ("explicit_null", "object_type", False),
        ("wrong_schema", "schema_version", False),
        ("extra_field", "fields_extra", False),
        ("missing_field", "fields_missing", False),
        ("wrong_enum_type", "online_enum", False),
        ("nested_enum", "condition_state_enum", False),
        ("timestamp_mismatch", "observed_at_mismatch", False),
        ("unsafe_dispatch_allowed", "dispatch_allowed_unsafe", True),
        ("unsafe_runtime_actions", "runtime_actions_unsafe", True),
        ("unsafe_executes_plan", "executes_plan_unsafe", True),
        ("unsafe_execute_once_allowed", "execute_once_allowed_unsafe", True),
        ("unsafe_promotion_allowed", "promotion_allowed_unsafe", True),
        ("oversize", "oversize", False),
    ],
)
def test_conditions_observation_mutations_are_classified_by_p8_safety(
    tmp_path: Path, mutation: str, expected_error: str, p8_unsafe: bool
):
    _, client, dev = _fixture(tmp_path)
    value: object = _conditions_observation()
    if mutation == "explicit_null":
        value = None
    else:
        assert isinstance(value, dict)
        if mutation == "wrong_schema":
            value["schema_version"] = "ctoa.conditions-observation.v999"
        elif mutation == "extra_field":
            value["local_path"] = "C:/private/client.log"
        elif mutation == "missing_field":
            value.pop("cooldown")
        elif mutation == "wrong_enum_type":
            value["online"] = True
        elif mutation == "nested_enum":
            value["condition_state"] = {"raw_bitmask": 32}
        elif mutation == "timestamp_mismatch":
            value["observed_at_unix_ms"] = NOW_MS - 2_000
        elif mutation.startswith("unsafe_"):
            value[mutation.removeprefix("unsafe_")] = True
        elif mutation == "oversize":
            value["observation_id"] = "a" * (
                evidence.MAX_CONDITIONS_OBSERVATION_BYTES + 1
            )
    _set_conditions_observation(client, value)

    report = _build(client, dev)
    observation = report["capability"]["conditions_observation"]

    if p8_unsafe:
        assert report["status"] == "blocked"
        assert report["capability"]["status"] == "unsafe_runtime_claim"
        assert report["capability"]["contract_valid"] is False
        assert report["capability"]["fresh"] is False
        assert "capability_unsafe_runtime_claim" in report["blockers"]
    else:
        assert report["status"] == "ready"
        assert report["blockers"] == []
    assert observation["status"] == "invalid"
    assert observation["valid"] is False
    assert observation["p9_blocker"] == "conditions_observation_invalid"
    assert expected_error in observation["validation_errors"]
    assert observation["runtime_actions"] is False
    assert "private" not in json.dumps(observation)


@pytest.mark.parametrize(
    ("timestamp", "expected_status"),
    [
        (0, "invalid"),
        (1, "valid"),
        (9_999_999_999_999, "valid"),
        (10_000_000_000_000, "invalid"),
    ],
)
def test_conditions_observation_timestamp_bounds(timestamp: int, expected_status: str):
    observation = _conditions_observation(timestamp)

    normalized = evidence.summarize_conditions_observation(
        observation,
        expected_observed_at_unix_ms=timestamp,
        require_timestamp_binding=True,
    )

    assert normalized["status"] == expected_status


def test_conditions_observation_id_rejects_dot():
    observation = _conditions_observation()
    observation["observation_id"] = "conditions.with-dot"

    normalized = evidence.summarize_conditions_observation(observation)

    assert normalized["status"] == "invalid"
    assert "observation_id" in normalized["validation_errors"]


def test_conditions_observation_accepts_proven_player_states_source():
    observation = _conditions_observation()
    observation["protection_zone"] = "inside"
    observation["protection_zone_source"] = "player_states"

    normalized = evidence.summarize_conditions_observation(observation)

    assert normalized["status"] == "valid"
    assert normalized["valid"] is True
    assert normalized["protection_zone_source"] == "player_states"


def test_conditions_observation_json_schema_matches_sanitizer_bounds():
    schema = json.loads(CONDITIONS_OBSERVATION_SCHEMA_FILE.read_text(encoding="utf-8"))
    timestamp = schema["properties"]["observed_at_unix_ms"]
    observation_id = schema["properties"]["observation_id"]

    assert timestamp["minimum"] == 1
    assert timestamp["maximum"] == 9_999_999_999_999
    assert observation_id["minLength"] == 1
    assert observation_id["maxLength"] == 64
    assert observation_id["pattern"] == "^[a-z0-9][a-z0-9_-]{0,63}$"


def test_present_observation_is_unbound_when_parent_timestamp_is_invalid(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)
    _set_conditions_observation(client, _conditions_observation())
    capability_path = (
        client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    )
    payload = json.loads(capability_path.read_text(encoding="utf-8"))
    payload["observed_at_unix_ms"] = "invalid"
    _write_json(capability_path, payload)

    report = _build(client, dev)
    observation = report["capability"]["conditions_observation"]

    assert report["status"] == "blocked"
    assert report["capability"]["status"] == "invalid_heartbeat"
    assert observation["status"] == "invalid"
    assert "parent_observed_at_unbound" in observation["validation_errors"]


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_top_flag",
        "duplicate_nested_flag",
        "nan",
        "infinity",
        "overflow",
        "bounded_depth",
        "deep_nesting",
    ],
)
def test_bounded_json_rejects_duplicate_keys_and_non_finite_numbers(
    tmp_path: Path, mutation: str
):
    _, client, dev = _fixture(tmp_path)
    if mutation == "duplicate_nested_flag":
        _set_conditions_observation(client, _conditions_observation())
    capability_path = (
        client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    )
    raw = capability_path.read_text(encoding="utf-8")
    if mutation == "duplicate_top_flag":
        raw = raw.replace(
            '"runtime_actions": false',
            '"runtime_actions": false, "runtime_actions": true',
            1,
        )
    elif mutation == "duplicate_nested_flag":
        nested_start = raw.index('"conditions_observation"')
        flag_start = raw.index('"runtime_actions": false', nested_start)
        flag_end = flag_start + len('"runtime_actions": false')
        raw = raw[:flag_end] + ', "runtime_actions": true' + raw[flag_end:]
    elif mutation == "nan":
        raw = raw.replace(
            f'"observed_at_unix_ms": {NOW_MS - 1_000}',
            '"observed_at_unix_ms": NaN',
            1,
        )
    elif mutation == "infinity":
        raw = raw.replace(
            f'"observed_at_unix_ms": {NOW_MS - 1_000}',
            '"observed_at_unix_ms": Infinity',
            1,
        )
    elif mutation == "overflow":
        raw = raw.replace(
            f'"observed_at_unix_ms": {NOW_MS - 1_000}',
            '"observed_at_unix_ms": 1e999',
            1,
        )
    elif mutation == "bounded_depth":
        raw = '{"deep":' + "[" * 80 + "0" + "]" * 80 + "}"
    elif mutation == "deep_nesting":
        raw = "[" * 1100 + "0" + "]" * 1100
    capability_path.write_text(raw, encoding="utf-8")

    assert evidence.load_json_bounded(capability_path)[1] == "malformed"
    report = _build(client, dev)
    assert report["status"] == "blocked"
    assert report["capability"]["status"] == "malformed"
    assert "capability_malformed" in report["blockers"]


@pytest.mark.parametrize(
    ("mutation", "expected_status"),
    [
        ("heartbeat_offline", "heartbeat_offline"),
        ("game_offline", "game_offline"),
        ("missing_runtime_actions", "invalid_contract"),
        ("missing_runtime_core_actions", "invalid_contract"),
        ("wrong_interval", "invalid_heartbeat"),
        ("version_mismatch", "version_mismatch"),
    ],
)
def test_heartbeat_contract_fails_closed(
    tmp_path: Path, mutation: str, expected_status: str
):
    _, client, dev = _fixture(tmp_path)
    _mutate_capability(client, mutation)

    report = _build(client, dev)

    assert report["status"] != "ready"
    assert report["capability"]["status"] == expected_status
    assert report["dispatch_allowed"] is False


def test_heartbeat_must_be_newer_than_process_and_no_more_than_15_seconds_old(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path, observed_at_ms=NOW_MS - 15_001)
    stale = _build(
        client,
        dev,
        process_start_unix_ms=NOW_MS - 30_000,
    )

    _, client2, dev2 = _fixture(tmp_path / "second", observed_at_ms=NOW_MS - 1_000)
    before_process = _build(
        client2,
        dev2,
        process_start_unix_ms=NOW_MS - 1_000,
    )

    assert stale["status"] != "ready"
    assert stale["capability"]["status"] == "stale"
    assert before_process["status"] == "blocked"
    assert before_process["capability"]["status"] == "heartbeat_before_process"


@pytest.mark.parametrize(
    ("process_count", "process_start_unix_ms"),
    [(0, NOW_MS - 10_000), (2, NOW_MS - 10_000), (1, 0)],
)
def test_ready_requires_one_active_process_with_positive_start_time(
    tmp_path: Path,
    process_count: int,
    process_start_unix_ms: int,
):
    _, client, dev = _fixture(tmp_path)

    report = _build(
        client,
        dev,
        process_count=process_count,
        process_start_unix_ms=process_start_unix_ms,
    )

    assert report["status"] != "ready"
    assert report["checks"]["exact_active_client_process"] is (process_count == 1)
    assert report["dispatch_allowed"] is False


def test_missing_or_untrusted_pin_blocks_and_observer_never_creates_one(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)
    live_manifest = dev / "live_manifest.json"
    live_manifest.unlink()
    _write_json(dev / "manifest.json", {"files": []})

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert "live_manifest_pin_untrusted" in report["blockers"]
    assert report["integrity"]["baseline"] == "live_manifest"
    assert report["integrity"]["baseline_recorded"] is False
    assert (
        report["integrity"]["pin_remediation"]["classification"]
        == "missing_or_unreadable_attestation"
    )
    assert report["integrity"]["pin_remediation"]["historical_rebinding_allowed"] is False
    assert not live_manifest.exists()


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("name", "wrong", "live_promotion_name_invalid"),
        ("created_at", "wrong", "live_promotion_timestamp_mismatch"),
        ("approval_switch", "no", "live_promotion_approval_invalid"),
        ("verification", "unchecked", "live_promotion_verification_invalid"),
        ("helper_version", "v0", "live_promotion_helper_version_mismatch"),
        ("verified_file_count", 99, "live_promotion_file_count_mismatch"),
        ("live_manifest", "wrong.json", "live_promotion_manifest_path_mismatch"),
        (
            "live_manifest_sha256",
            "0" * 64,
            "live_promotion_manifest_sha256_mismatch",
        ),
    ],
)
def test_live_promotion_cross_check_is_strict(
    tmp_path: Path, field: str, value: object, expected_error: str
):
    _, client, dev = _fixture(tmp_path)
    promotion_path = dev / "live_promotion.json"
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    promotion[field] = value
    _write_json(promotion_path, promotion)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert expected_error in report["integrity"]["pin_errors"]
    assert report["integrity"]["pin_trusted"] is False


def test_live_manifest_requires_official_origin_and_schema(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["origin"] = "background_verified_current_live"
    manifest["schema_version"] = "legacy"
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert "live_manifest_origin_invalid" in report["integrity"]["pin_errors"]
    assert "live_manifest_schema_invalid" in report["integrity"]["pin_errors"]


def test_legacy_unbound_promotion_is_diagnosed_without_rebinding(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["origin"] = "background_verified_current_live"
    _write_json(manifest_path, manifest)
    promotion_path = dev / "live_promotion.json"
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    promotion.pop("live_manifest")
    promotion.pop("live_manifest_sha256")
    promotion["created_at"] = "2026-07-11T15:54:00+00:00"
    _write_json(promotion_path, promotion)

    report = _build(client, dev)
    remediation = report["integrity"]["pin_remediation"]

    assert report["status"] == "blocked"
    assert remediation["classification"] == "legacy_or_unbound_attestation"
    assert remediation["required_action"] == (
        "refresh_official_live_promotion_after_current_gates"
    )
    assert remediation["observer_can_write_trust_anchor"] is False
    assert remediation["historical_rebinding_allowed"] is False
    assert remediation["requires_current_release_gate"] is True
    assert remediation["requires_explicit_live_approval"] is True
    assert "do not synthesize or rebind a trust anchor" in report["next_action"]
    assert report["integrity"]["matched_file_count"] == 0
    assert report["integrity"]["diagnostic_parity"] == {
        "attempted": True,
        "status": "passed",
        "manifest_file_count": 1,
        "matched_file_count": 1,
        "mismatch_count": 0,
        "mutable_drift_count": 0,
        "profile_drift_count": 0,
        "missing_count": 0,
        "invalid_path_count": 0,
        "oversize_count": 0,
        "actual_total_bytes": (
            client / "mods" / "ctoa_otclient" / "sample.lua"
        ).stat().st_size,
        "stable_during_observation": True,
        "acceptance_allowed": False,
    }


@pytest.mark.parametrize("mutation", ["duplicate", "nonfinite", "deep"])
def test_live_manifest_strict_parser_fails_closed(mutation: str, tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    raw = manifest_path.read_text(encoding="utf-8")
    if mutation == "duplicate":
        raw = raw.replace(
            '"origin": "official_live_promotion"',
            '"origin": "official_live_promotion", "origin": "background_verified_current_live"',
            1,
        )
    elif mutation == "nonfinite":
        raw = raw[:-1] + ', "poison": NaN}'
    else:
        raw = raw[:-1] + ', "poison": ' + "[" * 80 + "0" + "]" * 80 + "}"
    manifest_path.write_text(raw, encoding="utf-8")

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert "live_manifest_malformed" in report["integrity"]["pin_errors"]
    assert (
        report["integrity"]["pin_remediation"]["classification"]
        == "missing_or_unreadable_attestation"
    )


def test_untrusted_diagnostic_parity_exposes_profile_drift_without_acceptance(
    tmp_path: Path,
):
    _, client, dev = _fixture(tmp_path)
    profile = client / "mods" / "ctoa_otclient" / "ctoa_ek_profile.lua"
    profile.write_text("return true\n", encoding="utf-8")
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["origin"] = "background_verified_current_live"
    manifest["files"] = [
        {
            "path": "mods/ctoa_otclient/ctoa_ek_profile.lua",
            "sha256": _sha256(profile),
            "bytes": profile.stat().st_size,
        }
    ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)
    profile.write_text("return false\n", encoding="utf-8")

    report = _build(client, dev)
    diagnostic = report["integrity"]["diagnostic_parity"]

    assert report["status"] == "blocked"
    assert report["integrity"]["status"] == "untrusted_pin"
    assert report["integrity"]["profile_drift_count"] == 0
    assert diagnostic["attempted"] is True
    assert diagnostic["status"] == "failed"
    assert diagnostic["profile_drift_count"] == 1
    assert diagnostic["mutable_drift_count"] == 1
    assert diagnostic["stable_during_observation"] is True
    assert diagnostic["acceptance_allowed"] is False


@pytest.mark.parametrize(
    "invalid_kind", ["nested", "entry_limit", "file_size", "total_size"]
)
def test_manifest_scope_and_size_limits_fail_before_live_reads(
    tmp_path: Path, invalid_kind: str
):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if invalid_kind == "nested":
        manifest["files"][0]["path"] = "mods/ctoa_otclient/nested/sample.lua"
    elif invalid_kind == "entry_limit":
        manifest["files"] = [
            {
                "path": f"mods/ctoa_otclient/file_{index}.lua",
                "sha256": "0" * 64,
                "bytes": 1,
            }
            for index in range(status.MAX_MANIFEST_ENTRIES + 1)
        ]
    elif invalid_kind == "file_size":
        manifest["files"][0]["bytes"] = status.MAX_LIVE_FILE_BYTES + 1
    elif invalid_kind == "total_size":
        manifest["files"] = [
            {
                "path": f"mods/ctoa_otclient/file_{index}.lua",
                "sha256": "0" * 64,
                "bytes": status.MAX_LIVE_FILE_BYTES,
            }
            for index in range(9)
        ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["pin_trusted"] is False
    assert report["integrity"]["actual_total_bytes"] == 0


def test_live_file_hashing_stops_at_two_mib(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    target = client / "mods" / "ctoa_otclient" / "sample.lua"
    target.write_bytes(b"x" * (status.MAX_LIVE_FILE_BYTES + 1))

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["oversize_count"] == 1
    assert report["integrity"]["actual_total_bytes"] == 0


def test_case_insensitive_manifest_alias_is_rejected(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    alias = dict(manifest["files"][0])
    alias["path"] = "mods/ctoa_otclient/SAMPLE.lua"
    manifest["files"].append(alias)
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["pin_trusted"] is False
    assert "manifest_entry_1_duplicate" in report["integrity"]["pin_errors"]


def test_executable_profile_drift_never_passes_parity(tmp_path: Path):
    _, client, dev = _fixture(tmp_path)
    profile = client / "mods" / "ctoa_otclient" / "ctoa_ek_profile.lua"
    profile.write_text("return true\n", encoding="utf-8")
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        {
            "path": "mods/ctoa_otclient/ctoa_ek_profile.lua",
            "sha256": _sha256(profile),
            "bytes": profile.stat().st_size,
        }
    ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)
    profile.write_text("return false\n", encoding="utf-8")

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["status"] == "failed"
    assert report["integrity"]["profile_drift_count"] == 1
    assert report["integrity"]["mutable_drift_count"] == 1
    assert "live_manifest_parity_failed" in report["blockers"]


def test_actual_hashing_stops_at_remaining_aggregate_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, client, dev = _fixture(tmp_path)
    first = client / "mods" / "ctoa_otclient" / "first.lua"
    second = client / "mods" / "ctoa_otclient" / "second.lua"
    first.write_bytes(b"a" * 10)
    second.write_bytes(b"b" * 10)
    manifest_path = dev / "live_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        {
            "path": "mods/ctoa_otclient/first.lua",
            "sha256": _sha256(first),
            "bytes": 8,
        },
        {
            "path": "mods/ctoa_otclient/second.lua",
            "sha256": _sha256(second),
            "bytes": 8,
        },
    ]
    _write_json(manifest_path, manifest)
    _resign_promotion(dev, client)
    monkeypatch.setattr(status, "MAX_LIVE_TOTAL_BYTES", 16)

    report = _build(client, dev)

    assert report["status"] == "blocked"
    assert report["integrity"]["actual_total_bytes"] == 10
    assert report["integrity"]["oversize_count"] == 1
    assert report["integrity"]["matched_file_count"] == 0
    first_fingerprint, first_status = status._file_fingerprint(first)
    second_fingerprint, second_status = status._file_fingerprint(second)
    assert first_status == second_status == "loaded"
    assert first_fingerprint is not None and second_fingerprint is not None
    assert not status._fingerprints_unchanged(
        {
            "mods/ctoa_otclient/first.lua": first_fingerprint,
            "mods/ctoa_otclient/second.lua": second_fingerprint,
        },
        client,
    )


def test_only_deterministic_capability_path_is_accepted(tmp_path: Path):
    local_app_data, client, dev = _fixture(tmp_path)
    alternate = (
        local_app_data
        / "ctoa_helper_client_ui_preview"
        / "ctoa_client_capabilities.json"
    )
    alternate.parent.mkdir(parents=True)
    deterministic = client / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    alternate.write_bytes(deterministic.read_bytes())

    report = _build(client, dev, explicit_report=alternate)

    assert report["status"] == "blocked"
    assert report["capability"]["status"] == "explicit_path_mismatch"
    assert "capability_explicit_path_mismatch" in report["blockers"]


def test_bounded_json_reader_rejects_oversize_and_symlink(tmp_path: Path):
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * evidence.MAX_CAPABILITY_BYTES)
    assert evidence.load_json_bounded(oversized)[1] == "oversize"

    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    linked = tmp_path / "linked.json"
    try:
        os.symlink(target, linked)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    assert evidence.load_json_bounded(linked)[1] == "symlink_rejected"


def test_main_no_write_does_not_create_a_missing_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    local_app_data = tmp_path / "LocalAppData"
    client = local_app_data / "Solteria" / "client"
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    client.mkdir(parents=True)
    dev.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(status, "RUNTIME_ROOT", tmp_path / "runtime")

    result = status.main(
        [
            "--client-root",
            str(client),
            "--dev-dir",
            str(dev),
            "--json-out",
            str(dev / "background_status.json"),
            "--process-count",
            "1",
            "--process-start-unix-ms",
            str(NOW_MS - 10_000),
            "--no-write",
        ]
    )

    assert result == 1
    assert not (dev / "live_manifest.json").exists()
    assert not (dev / "background_status.json").exists()
    assert "live_manifest_pin_untrusted" in capsys.readouterr().out


def test_main_rejects_a_non_live_localappdata_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    local_app_data = tmp_path / "LocalAppData"
    wrong_client = local_app_data / "OtherApp"
    dev = tmp_path / "runtime" / "solteria_helper_dev"
    wrong_client.mkdir(parents=True)
    dev.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(status, "RUNTIME_ROOT", tmp_path / "runtime")

    result = status.main(
        [
            "--client-root",
            str(wrong_client),
            "--dev-dir",
            str(dev),
            "--json-out",
            str(dev / "background_status.json"),
            "--process-count",
            "1",
            "--process-start-unix-ms",
            str(NOW_MS - 10_000),
            "--no-write",
        ]
    )

    assert result == 2
    assert not (dev / "background_status.json").exists()


@pytest.mark.parametrize("invalid_target", ["dev_dir", "json_out"])
def test_main_requires_exact_repo_runtime_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_target: str,
):
    local_app_data = tmp_path / "LocalAppData"
    client = local_app_data / "Solteria" / "client"
    runtime_root = tmp_path / "runtime"
    exact_dev = runtime_root / "solteria_helper_dev"
    client.mkdir(parents=True)
    exact_dev.mkdir(parents=True)
    dev = runtime_root / "other" if invalid_target == "dev_dir" else exact_dev
    output = (
        exact_dev / "other.json"
        if invalid_target == "json_out"
        else dev / "background_status.json"
    )
    dev.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(status, "RUNTIME_ROOT", runtime_root)

    result = status.main(
        [
            "--client-root",
            str(client),
            "--dev-dir",
            str(dev),
            "--json-out",
            str(output),
            "--process-count",
            "1",
            "--process-start-unix-ms",
            str(NOW_MS - 10_000),
            "--no-write",
        ]
    )

    assert result == 2
    assert not output.exists()


def test_background_wrapper_has_positive_allowlist_and_guarded_primitives():
    wrapper = WRAPPER.read_text(encoding="utf-8")
    cli = CLI.read_text(encoding="utf-8")
    reporter = REPORTER.read_text(encoding="utf-8")
    smoke = SANDBOX_SMOKE.read_text(encoding="utf-8")

    allowlist = wrapper[
        wrapper.index("function Get-BackgroundAllowedActions") : wrapper.index(
            "function Assert-InteractiveOperatorMode"
        )
    ]
    background = wrapper[
        wrapper.index("function Invoke-BackgroundStatus") : wrapper.index(
            "Assert-OperatorModeAction\n\nswitch"
        )
    ]
    assert 'return @("BackgroundStatus")' in allowlist
    assert "CTOA_OPERATOR_MODE=background_no_screen cannot be downgraded" in wrapper
    assert "BackgroundNoScreen rejects live approval" in wrapper
    assert '"BackgroundStatus" {' in wrapper
    assert '"otbg" { Invoke-OtBackgroundStatus; break }' in cli
    assert '"-OperatorMode"' in cli and '"BackgroundNoScreen"' in cli
    assert '"--process-count"' in background
    assert '"--process-start-unix-ms"' in background
    for forbidden in (
        "Start-Process",
        "Stop-Process",
        "Capture-Screenshot",
        "SetForegroundWindow",
        "SendKeys",
        "mouse_event",
        "Copy-Item",
        "PromoteLiveCtoa",
    ):
        assert forbidden not in background
    for function_name in (
        "Write-SmokeCommand",
        "Sync-CtoaRuntimeFiles",
        "Start-LiveClientAfterPromotion",
        "Initialize-Sandbox",
        "Start-SandboxClient",
        "Stop-SandboxClient",
        "Set-LiveCtoaEnabled",
        "Set-LiveCtoaUiOnly",
        "New-LiveCtoaBackup",
        "Invoke-LivePromotion",
        "Invoke-LiveEmergencyRepair",
        "Capture-Screenshot",
    ):
        start = wrapper.index(f"function {function_name}")
        next_function = wrapper.find("\nfunction ", start + len("function "))
        function_body = wrapper[start : next_function if next_function >= 0 else None]
        assert "Assert-InteractiveOperatorMode" in function_body
    assert "deterministic_work_dir_path = true" in reporter
    assert "no_screen_safe = true" in reporter
    assert "bounded_tail_text(log_path)" in smoke
    assert "function Write-LiveManifestSnapshot" in wrapper
    assert 'schema_version = "ctoa.solteria-live-manifest.v1"' in wrapper
    assert "live_manifest_sha256 = $liveManifestSha256" in wrapper
    live_snapshot = wrapper[
        wrapper.index("function Write-LiveManifestSnapshot") : wrapper.index(
            "function Invoke-LivePromotion"
        )
    ]
    assert 'Join-Path $OutRoot "manifest.json"' not in live_snapshot
    assert "Get-Content" not in live_snapshot
    assert "$VerifiedEntries" in live_snapshot
    assert "$HelperVersion" in live_snapshot


def test_background_wrapper_publishes_only_after_external_invariants():
    wrapper = WRAPPER.read_text(encoding="utf-8")
    background = wrapper[
        wrapper.index("function Invoke-BackgroundStatus") : wrapper.index(
            "Assert-OperatorModeAction\n\nswitch"
        )
    ]

    assert "Assert-ExactLiveClientPath -Path $SourceClient" in background
    assert "BackgroundNoScreen requires the trusted repo interpreter" in background
    assert "Get-Command python" not in background
    assert '"--no-write"' in background
    assert background.index("$rawPayload = @(& $python @arguments)") < background.index(
        "$afterProcesses = Get-BackgroundProcessSample"
    )
    assert background.index(
        "$afterProcesses = Get-BackgroundProcessSample"
    ) < background.index("Write-JsonAtomic -InputObject $payload")
    assert "client_process_changed_during_observation" in background
    assert "screenshot_count_changed_during_observation" in background
    assert "stored a blocked sample" in background
    assert background.count("Assert-ExactBackgroundOutputPath") >= 2
    assert "publication escaped the exact runtime output path" in background
    output_guard = wrapper[
        wrapper.index("function Assert-ExactBackgroundOutputPath") : wrapper.index(
            "function Assert-SandboxClientPath"
        )
    ]
    assert "ReparsePoint" in output_guard
    assert 'Join-Path $runtimeRoot "solteria_helper_dev"' in output_guard
