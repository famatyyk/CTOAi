from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.ops import otclient_conditions_shadow_replay as replay
from scripts.ops import otclient_headless_evidence as headless_evidence


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "otclient_conditions_shadow_replay"
NOW_MS = 1783800000000
SCHEMAS = (
    "conditions-shadow-profile.schema.json",
    "conditions-observation.schema.json",
    "conditions-p8-proof.schema.json",
    "conditions-recovery-trace.schema.json",
    "conditions-recovery-proof.schema.json",
    "conditions-shadow-trace.schema.json",
    "conditions-shadow-scenario-pack.schema.json",
    "conditions-shadow-replay-report.schema.json",
)


def _documents():
    return replay._fixture_documents()


def _evaluate(documents=None, *, source="fixture"):
    inputs = documents or _documents()
    return replay.evaluate_shadow(
        profile_document=inputs[0],
        observation_document=inputs[1],
        p8_document=inputs[2],
        recovery_trace_document=inputs[3],
        recovery_proof_document=inputs[4],
        evaluated_at_unix_ms=NOW_MS,
        source=source,
    )


def _assert_no_action(payload: dict[str, object]) -> None:
    for key in replay.FALSE_FLAGS:
        assert payload[key] is False
    assert payload["intrusive_actions_performed"] == []


def _assert_objects_closed(value: object) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object" or "properties" in value:
            assert value.get("additionalProperties") is False
        for nested in value.values():
            _assert_objects_closed(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_objects_closed(nested)


def test_data_only_profile_is_the_exact_safe_p9_contract():
    document = replay.read_document(replay.DEFAULT_PROFILE)

    assert document.status == "loaded"
    assert document.payload == {
        "schema_version": replay.PROFILE_SCHEMA,
        "mode": "shadow_only",
        "action": replay.ACTION,
        "condition": replay.CONDITION,
        "spell": replay.SPELL,
        "max_observation_age_ms": 6000,
        "cooldown_required": "ready",
        "retry_budget": 0,
        "requires_p8_ready": True,
        "requires_recovery_trace": True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
    }
    assert replay._profile_structurally_valid(document.payload)


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_all_p9_json_schemas_are_closed_draft_2020_12(schema_name: str):
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    _assert_objects_closed(schema)


def test_flat_observation_fixture_matches_the_producer_contract_exactly():
    observation = replay.read_document(FIXTURES / "positive-observation.json")

    assert observation.status == "loaded"
    assert observation.payload is not None
    assert set(observation.payload) == replay.OBSERVATION_KEYS
    assert observation.payload["protection_zone"] == "outside"
    assert observation.payload["protection_zone_source"] == "player_method"
    assert observation.payload["cooldown"] == "ready"
    assert observation.payload["cooldown_source"] == "game_cooldown_group"
    assert replay._observation_structurally_valid(observation.payload)


def test_observation_id_with_dot_is_rejected_like_the_passive_producer():
    documents = list(_documents())
    assert documents[1].payload is not None
    payload = dict(documents[1].payload)
    payload["observation_id"] = "observation.with-dot"
    documents[1] = replay.document_from_payload(payload)

    trace = _evaluate(tuple(documents))

    assert trace["status"] == "operational_acceptance_blocked"
    assert "observation_schema_invalid" in trace["blockers"]


def test_positive_fixture_is_deterministic_but_never_executes():
    first = _evaluate()
    second = _evaluate()

    assert first == second
    assert first["status"] == "shadow_plan_ready"
    assert first["decision"] == "would_plan_paralyze_recovery"
    assert first["blockers"] == []
    assert first["operator_review_required"] is True
    assert first["trace_id"].endswith(first["decision_sha256"][:16])
    _assert_no_action(first)


def test_scenario_pack_covers_required_fail_closed_matrix_and_passes_twice():
    document = replay.read_document(
        replay.DEFAULT_SCENARIO_PACK, replay.MAX_SCENARIO_BYTES
    )
    report = replay.run_scenario_pack(document)
    names = {case["name"] for case in report["cases"]}

    assert report["status"] == "passed"
    assert report["total_count"] == report["passed_count"] == 44
    assert report["failed_count"] == 0
    assert {
        "positive_shadow_plan",
        "profile_wrong_action",
        "profile_wrong_spell",
        "profile_retry_nonzero",
        "profile_malformed",
        "profile_future_version",
        "profile_oversized",
        "profile_symlinked",
        "profile_non_regular",
        "profile_extra_field",
        "observation_stale",
        "observation_future",
        "player_offline",
        "player_online_unknown",
        "player_dead",
        "player_life_unknown",
        "protection_zone_inside",
        "protection_zone_unknown",
        "condition_absent",
        "condition_unknown",
        "condition_wrong",
        "cooldown_active",
        "cooldown_unknown",
        "p8_missing",
        "p8_blocked",
        "p8_stale",
        "p8_future",
        "recovery_missing",
        "recovery_malformed",
        "recovery_hash_mismatch",
        "recovery_wrong_spell",
    } <= names
    _assert_no_action(report)
    for case in report["cases"]:
        assert case["deterministic"] is True
        assert case["passed"] is True
        _assert_no_action(case)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("expected_blockers", ["unknown_blocker"]),
        ("expected_blockers", {"unexpected": "shape"}),
        ("mutation", {"unexpected": "shape"}),
        ("expected_status", ["shadow_plan_ready"]),
    ],
)
def test_scenario_pack_rejects_invalid_nested_shapes_without_exception(
    field: str, invalid_value: object
):
    document = replay.read_document(
        replay.DEFAULT_SCENARIO_PACK, replay.MAX_SCENARIO_BYTES
    )
    assert document.payload is not None
    payload = copy.deepcopy(document.payload)
    payload["scenarios"][0][field] = invalid_value
    invalid_document = replay.document_from_payload(payload)

    report = replay.run_scenario_pack(invalid_document)

    assert report["status"] == "failed"
    assert report["total_count"] == report["passed_count"] == 0
    assert report["failed_count"] == 1
    _assert_no_action(report)


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        ('{"a":1,"a":2}', "duplicate_keys"),
        ('{"a":NaN}', "malformed"),
        ('{"a":Infinity}', "malformed"),
        ('{"a":1e999}', "malformed"),
        ('{"a":' + "[" * 80 + "0" + "]" * 80 + "}", "malformed"),
        ("[" * 1100 + "0" + "]" * 1100, "malformed"),
        ("[]", "not_object"),
    ],
)
def test_strict_loader_rejects_duplicate_nonfinite_and_nonobject_json(
    tmp_path: Path, contents: str, expected: str
):
    path = tmp_path / "input.json"
    path.write_text(contents, encoding="utf-8")

    assert replay.read_document(path).status == expected


def test_bounded_loader_rejects_oversize_symlink_and_non_regular(tmp_path: Path):
    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"{" + b" " * replay.MAX_INPUT_BYTES)
    assert replay.read_document(oversized).status == "oversize"

    directory = tmp_path / "directory.json"
    directory.mkdir()
    assert replay.read_document(directory).status == "not_regular"

    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    linked = tmp_path / "linked.json"
    try:
        os.symlink(target, linked)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert replay.read_document(linked).status == "symlink_rejected"


@pytest.mark.parametrize(
    ("index", "prefix"),
    [
        (0, "profile"),
        (1, "observation"),
        (2, "p8"),
        (3, "recovery_trace"),
        (4, "recovery"),
    ],
)
@pytest.mark.parametrize(
    "load_status",
    ["duplicate_keys", "oversize", "symlink_rejected", "not_regular"],
)
def test_each_input_surface_maps_unsafe_file_status_to_a_stable_blocker(
    index: int, prefix: str, load_status: str
):
    documents = list(_documents())
    documents[index] = replay.document_from_payload(None, load_status)

    trace = _evaluate(tuple(documents))

    assert f"{prefix}_{load_status}" in trace["blockers"]
    assert trace["status"] == "operational_acceptance_blocked"
    _assert_no_action(trace)


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, "profile_schema_invalid"),
        (1, "observation_schema_invalid"),
        (2, "p8_schema_invalid"),
        (3, "recovery_trace_schema_invalid"),
        (4, "recovery_schema_invalid"),
    ],
)
def test_extra_fields_fail_closed_for_every_strict_input(index: int, expected: str):
    documents = list(_documents())
    assert documents[index].payload is not None
    payload = dict(documents[index].payload)
    payload["unexpected"] = True
    documents[index] = replay.document_from_payload(payload)

    trace = _evaluate(tuple(documents))

    assert expected in trace["blockers"]
    assert trace["status"] == "operational_acceptance_blocked"
    _assert_no_action(trace)


@pytest.mark.parametrize(
    "field",
    [
        "background_status_sha256",
        "live_manifest_sha256",
        "conditions_observation_sha256",
    ],
)
def test_p8_zero_hash_sentinels_are_structural_but_never_accepted(field: str):
    documents = list(_documents())
    assert documents[2].payload is not None
    payload = copy.deepcopy(documents[2].payload)
    payload[field] = replay.ZERO_SHA256
    documents[2] = replay.document_from_payload(payload)

    trace = _evaluate(tuple(documents))

    assert "p8_schema_invalid" not in trace["blockers"]
    assert "p8_operational_acceptance_blocked" in trace["blockers"]
    assert trace["status"] == "operational_acceptance_blocked"
    _assert_no_action(trace)


@pytest.mark.parametrize(
    ("index", "field", "invalid_value", "expected_blocker"),
    [
        (1, "online", {}, "observation_schema_invalid"),
        (2, "status", [], "p8_schema_invalid"),
        (3, "source", {}, "recovery_trace_schema_invalid"),
        (4, "status", [], "recovery_schema_invalid"),
    ],
)
def test_untrusted_enum_shapes_fail_closed_without_type_errors(
    index: int, field: str, invalid_value: object, expected_blocker: str
):
    documents = list(_documents())
    assert documents[index].payload is not None
    payload = copy.deepcopy(documents[index].payload)
    payload[field] = invalid_value
    documents[index] = replay.document_from_payload(payload)

    trace = _evaluate(tuple(documents))

    assert expected_blocker in trace["blockers"]
    assert trace["status"] == "operational_acceptance_blocked"
    _assert_no_action(trace)


def _valid_envelope() -> dict[str, object]:
    observation = json.loads(
        (FIXTURES / "positive-observation.json").read_text(encoding="utf-8")
    )
    return {
        **observation,
        "status": "valid",
        "present": True,
        "valid": True,
        "validation_errors": [],
        "p9_blocker": None,
    }


def test_embedded_sanitizer_envelope_is_strictly_projected_before_hashing():
    envelope = _valid_envelope()
    raw = replay.document_from_payload(
        {
            "schema_version": replay.P8_BACKGROUND_SCHEMA,
            "capability": {"conditions_observation": envelope},
        }
    )

    projected = replay.extract_embedded_observation(raw)

    assert projected.status == "loaded"
    assert projected.payload is not None
    assert set(projected.payload) == replay.OBSERVATION_KEYS
    assert "status" not in projected.payload
    assert projected.sha256 == replay.canonical_sha256(projected.payload)


def test_raw_background_status_ignores_external_observation_override():
    envelope = _valid_envelope()
    raw = replay.document_from_payload(
        {
            "schema_version": replay.P8_BACKGROUND_SCHEMA,
            "capability": {"conditions_observation": envelope},
        }
    )
    crafted_payload = copy.deepcopy(_documents()[1].payload)
    assert crafted_payload is not None
    crafted_payload["condition_state"] = "absent"
    crafted = replay.document_from_payload(crafted_payload)

    selected = replay._select_observation_document(raw, crafted)

    assert selected.payload is not None
    assert selected.payload["condition_state"] == "present"
    assert selected.sha256 != crafted.sha256


def test_external_observation_without_strict_p8_proof_fails_closed():
    crafted = _documents()[1]
    unknown_p8 = replay.document_from_payload({"schema_version": "unknown"})

    selected = replay._select_observation_document(unknown_p8, crafted)

    assert selected.status == "missing"
    assert selected.payload is None


def test_replay_accepts_the_real_headless_sanitizer_envelope_contract():
    raw_observation = json.loads(
        (FIXTURES / "positive-observation.json").read_text(encoding="utf-8")
    )
    envelope = headless_evidence.summarize_conditions_observation(
        raw_observation,
        expected_observed_at_unix_ms=raw_observation["observed_at_unix_ms"],
        require_timestamp_binding=True,
    )
    raw = replay.document_from_payload(
        {
            "schema_version": replay.P8_BACKGROUND_SCHEMA,
            "capability": {"conditions_observation": envelope},
        }
    )

    projected = replay.extract_embedded_observation(raw)

    assert envelope["status"] == "valid"
    assert projected.status == "loaded"
    assert projected.payload == raw_observation


@pytest.mark.parametrize(
    "kind", ["missing", "invalid", "extra", "ambiguous", "invalid_shape"]
)
def test_embedded_sanitizer_envelope_fails_closed(kind: str):
    envelope = _valid_envelope()
    payload: dict[str, object] = {
        "schema_version": replay.P8_BACKGROUND_SCHEMA,
        "capability": {"conditions_observation": envelope},
    }
    if kind == "missing":
        envelope["status"] = "missing"
        envelope["present"] = False
        envelope["valid"] = False
        envelope["p9_blocker"] = "conditions_observation_missing"
    elif kind == "invalid":
        envelope["status"] = "invalid"
        envelope["valid"] = False
        envelope["validation_errors"] = ["condition_state_invalid"]
        envelope["p9_blocker"] = "conditions_observation_invalid"
    elif kind == "extra":
        envelope["unexpected"] = True
    elif kind == "ambiguous":
        payload["conditions_observation"] = dict(envelope)
    else:
        envelope["status"] = {"unexpected": "shape"}

    projected = replay.extract_embedded_observation(
        replay.document_from_payload(payload)
    )

    assert projected.status == ("missing" if kind == "missing" else "invalid_envelope")


def test_raw_p8_status_shape_normalizes_to_unknown_without_type_error():
    raw = replay.document_from_payload(
        {
            "schema_version": replay.P8_BACKGROUND_SCHEMA,
            "generated_at_utc": "2026-07-11T19:59:59+00:00",
            "status": {"unexpected": "shape"},
        }
    )
    observation = replay.document_from_payload(None, "missing")

    normalized = replay.normalize_p8_proof(raw, observation)

    assert normalized.payload is not None
    assert normalized.payload["status"] == "unknown"
    assert normalized.payload["dispatch_allowed"] is False


def test_operational_mode_rejects_all_fixture_sources():
    trace = _evaluate(source="operational")

    assert trace["blockers"][-4:] == [
        "fixture_observation_not_operational",
        "fixture_p8_proof_not_operational",
        "fixture_recovery_trace_not_operational",
        "fixture_recovery_proof_not_operational",
    ]
    assert trace["status"] == "operational_acceptance_blocked"


def test_pz_and_cooldown_sources_must_prove_positive_states():
    documents = list(_documents())
    assert documents[1].payload is not None
    observation = dict(documents[1].payload)
    observation["protection_zone_source"] = "unavailable"
    observation["cooldown_source"] = "unavailable"
    documents[1] = replay.document_from_payload(observation)

    trace = _evaluate(tuple(documents))

    assert "protection_zone_source_untrusted" in trace["blockers"]
    assert "cooldown_source_untrusted" in trace["blockers"]


def test_raw_p8_adapter_rejects_optional_execute_once_claim():
    payload = {
        "schema_version": replay.P8_BACKGROUND_SCHEMA,
        "mode": "background_no_screen",
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "promotion_allowed": False,
        "execute_once_allowed": True,
        "intrusive_actions_performed": [],
        "interaction_contract": {
            "gui_automation": False,
            "mouse_keyboard_input": False,
            "window_focus": False,
            "screenshot_capture": False,
            "client_launch": False,
            "client_stop": False,
            "live_file_writes": False,
            "passive_reads_only": True,
            "evidence_write_scope": "runtime/solteria_helper_dev",
        },
        "wrapper_invariants": {
            "client_process_stable": True,
            "screenshot_count_stable": True,
        },
        "checks": {
            "no_screen_contract": True,
            "client_process_stable_during_wrapper": True,
            "screenshot_count_stable_during_wrapper": True,
        },
        "capability": {"runtime_actions": False, "runtime_core_actions": False},
    }

    assert replay._raw_p8_no_action_contract(payload) is False


@pytest.mark.parametrize("flag", replay.FALSE_FLAGS)
@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, "profile_unsafe_contract"),
        (1, "observation_unsafe_contract"),
        (2, "p8_unsafe_contract"),
        (3, "recovery_trace_unsafe_contract"),
        (4, "recovery_unsafe_contract"),
    ],
)
def test_every_true_action_flag_fails_closed(flag: str, index: int, expected: str):
    documents = list(_documents())
    assert documents[index].payload is not None
    payload = dict(documents[index].payload)
    payload[flag] = True
    documents[index] = replay.document_from_payload(payload)

    trace = _evaluate(tuple(documents))

    assert expected in trace["blockers"]
    _assert_no_action(trace)


def test_all_recovery_hash_bindings_are_independently_enforced():
    documents = list(_documents())
    assert documents[4].payload is not None
    recovery = dict(documents[4].payload)
    for key in (
        "recovery_trace_sha256",
        "profile_sha256",
        "observation_sha256",
        "p8_proof_sha256",
    ):
        recovery[key] = replay.ZERO_SHA256
    documents[4] = replay.document_from_payload(recovery)

    trace = _evaluate(tuple(documents))

    assert [blocker for blocker in trace["blockers"] if "hash_mismatch" in blocker] == [
        "recovery_trace_hash_mismatch",
        "recovery_profile_hash_mismatch",
        "recovery_observation_hash_mismatch",
        "recovery_p8_hash_mismatch",
    ]


def test_blocker_order_is_canonical_and_independent_of_input_key_order():
    documents = replay._scenario_documents("p8_unsafe_contract", NOW_MS)
    first = _evaluate(documents)
    reordered = list(documents)
    assert reordered[2].payload is not None
    reordered[2] = replay.document_from_payload(
        dict(reversed(list(reordered[2].payload.items())))
    )
    assert reordered[4].payload is not None
    recovery = dict(reordered[4].payload)
    recovery["p8_proof_sha256"] = reordered[2].sha256
    reordered[4] = replay.document_from_payload(recovery)
    second = _evaluate(tuple(reordered))

    assert first["blockers"] == second["blockers"]
    assert first["canonical_input_sha256"] == second["canonical_input_sha256"]
    assert first["decision_sha256"] == second["decision_sha256"]
    assert first["blockers"] == replay._sort_blockers(first["blockers"])


def test_current_real_p8_evidence_is_reported_as_operationally_blocked():
    if not replay.DEFAULT_P8_PROOF.exists():
        pytest.skip("current local P8 evidence is not present")
    report = replay.build_report(
        profile_document=replay.read_document(replay.DEFAULT_PROFILE),
        raw_p8_document=replay.read_document(replay.DEFAULT_P8_PROOF),
        recovery_trace_document=replay.read_document(replay.DEFAULT_RECOVERY_TRACE),
        recovery_proof_document=replay.read_document(replay.DEFAULT_RECOVERY_PROOF),
        scenario_document=replay.read_document(
            replay.DEFAULT_SCENARIO_PACK, replay.MAX_SCENARIO_BYTES
        ),
        evaluated_at_unix_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
    )

    assert report["operational_acceptance_status"] == ("operational_acceptance_blocked")
    assert report["scenario_pack_status"] == "passed"
    assert report["runtime_readiness_claimed"] is False
    _assert_no_action(report)


def test_raw_background_status_blocked_is_not_promoted_by_a_passing_pack():
    profile, observation, _, recovery_trace, recovery = _documents()
    assert observation.payload is not None
    raw_observation = dict(observation.payload)
    raw_observation["producer_source"] = "otclient_guarded_adapter"
    envelope = headless_evidence.summarize_conditions_observation(
        raw_observation,
        expected_observed_at_unix_ms=raw_observation["observed_at_unix_ms"],
        require_timestamp_binding=True,
    )
    raw_p8 = replay.document_from_payload(
        {
            "schema_version": replay.P8_BACKGROUND_SCHEMA,
            "generated_at_utc": "2026-07-11T19:59:59+00:00",
            "status": "blocked",
            "mode": "background_no_screen",
            "advisory_only": True,
            "safe_to_run_while_playing": True,
            "promotion_allowed": False,
            "dispatch_allowed": False,
            "runtime_actions": False,
            "process_state": "running",
            "process_count": 1,
            "interaction_contract": {
                "gui_automation": False,
                "mouse_keyboard_input": False,
                "window_focus": False,
                "screenshot_capture": False,
                "client_launch": False,
                "client_stop": False,
                "live_file_writes": False,
                "passive_reads_only": True,
                "evidence_write_scope": "runtime/solteria_helper_dev",
            },
            "wrapper_invariants": {
                "client_process_stable": True,
                "screenshot_count_stable": True,
            },
            "checks": {
                "no_screen_contract": True,
                "trusted_live_manifest_pin": False,
                "live_manifest_parity": False,
                "live_files_unchanged": True,
                "exact_active_client_process": True,
                "fresh_online_heartbeat": True,
                "helper_version_match": True,
                "capability_fail_closed": True,
                "client_process_stable_during_wrapper": True,
                "screenshot_count_stable_during_wrapper": True,
            },
            "integrity": {
                "manifest_sha256": "a" * 64,
                "helper_version": "v2.3.0",
            },
            "capability": {
                "helper_version": "v2.3.0",
                "runtime_actions": False,
                "runtime_core_actions": False,
                "conditions_observation": envelope,
            },
            "intrusive_actions_performed": [],
        }
    )
    projected_observation = replay.extract_embedded_observation(raw_p8)
    normalized_p8 = replay.normalize_p8_proof(raw_p8, projected_observation)

    assert recovery_trace.payload is not None
    trace_payload = dict(recovery_trace.payload)
    trace_payload["source"] = "recovery_shadow"
    operational_recovery_trace = replay.document_from_payload(trace_payload)

    assert recovery.payload is not None
    recovery_payload = dict(recovery.payload)
    recovery_payload["source"] = "recovery_shadow"
    recovery_payload["profile_sha256"] = profile.sha256
    recovery_payload["observation_sha256"] = projected_observation.sha256
    recovery_payload["p8_proof_sha256"] = normalized_p8.sha256
    recovery_payload["recovery_trace_sha256"] = operational_recovery_trace.sha256
    operational_recovery = replay.document_from_payload(recovery_payload)

    report = replay.build_report(
        profile_document=profile,
        raw_p8_document=raw_p8,
        recovery_trace_document=operational_recovery_trace,
        recovery_proof_document=operational_recovery,
        scenario_document=replay.read_document(
            replay.DEFAULT_SCENARIO_PACK, replay.MAX_SCENARIO_BYTES
        ),
        evaluated_at_unix_ms=NOW_MS,
    )

    assert report["operational_trace"]["blockers"] == [
        "p8_operational_acceptance_blocked"
    ]
    assert report["scenario_pack_status"] == "passed"
    assert report["operational_acceptance_status"] == ("operational_acceptance_blocked")
    _assert_no_action(report)


def test_atomic_writer_is_confined_to_exact_runtime_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output = (
        tmp_path / "runtime" / "solteria_helper_dev" / "conditions_shadow_replay.json"
    )
    monkeypatch.setattr(replay, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(replay, "RUNTIME_ROOT", tmp_path / "runtime")
    payload = {"schema_version": "test"}

    replay.write_json_atomic(output, payload)

    assert json.loads(output.read_text(encoding="utf-8")) == payload
    assert list(output.parent.glob(".*.tmp")) == []
    with pytest.raises(ValueError):
        replay.write_json_atomic(tmp_path / "escaped.json", payload)


def test_cli_no_write_does_not_create_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    output = (
        tmp_path / "runtime" / "solteria_helper_dev" / "conditions_shadow_replay.json"
    )
    monkeypatch.setattr(replay, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(replay, "RUNTIME_ROOT", tmp_path / "runtime")

    result = replay.main(
        [
            "--profile",
            str(replay.DEFAULT_PROFILE),
            "--p8-proof",
            str(replay.DEFAULT_P8_PROOF),
            "--recovery-trace",
            str(replay.DEFAULT_RECOVERY_TRACE),
            "--recovery-proof",
            str(replay.DEFAULT_RECOVERY_PROOF),
            "--scenario-pack",
            str(replay.DEFAULT_SCENARIO_PACK),
            "--json-out",
            str(output),
            "--evaluated-at-unix-ms",
            str(NOW_MS),
            "--no-write",
        ]
    )

    assert result == 0
    assert not output.exists()
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["operational_acceptance_status"] == (
        "operational_acceptance_blocked"
    )
    assert rendered["scenario_pack_status"] == "passed"


def test_failed_scenario_pack_blocks_an_otherwise_ready_operational_trace():
    profile, observation, p8, recovery_trace, recovery = _documents()
    assert observation.payload is not None
    operational_observation_payload = dict(observation.payload)
    operational_observation_payload["producer_source"] = "otclient_guarded_adapter"
    operational_observation = replay.document_from_payload(
        operational_observation_payload
    )

    assert p8.payload is not None
    operational_p8_payload = dict(p8.payload)
    operational_p8_payload["source"] = "background_no_screen"
    operational_p8_payload["conditions_observation_sha256"] = (
        operational_observation.sha256
    )
    operational_p8 = replay.document_from_payload(operational_p8_payload)

    assert recovery_trace.payload is not None
    operational_trace_payload = dict(recovery_trace.payload)
    operational_trace_payload["source"] = "recovery_shadow"
    operational_recovery_trace = replay.document_from_payload(operational_trace_payload)

    assert recovery.payload is not None
    operational_recovery_payload = dict(recovery.payload)
    operational_recovery_payload["source"] = "recovery_shadow"
    operational_recovery_payload["profile_sha256"] = profile.sha256
    operational_recovery_payload["observation_sha256"] = operational_observation.sha256
    operational_recovery_payload["p8_proof_sha256"] = operational_p8.sha256
    operational_recovery_payload["recovery_trace_sha256"] = (
        operational_recovery_trace.sha256
    )
    operational_recovery = replay.document_from_payload(operational_recovery_payload)

    report = replay.build_report(
        profile_document=profile,
        raw_p8_document=operational_p8,
        recovery_trace_document=operational_recovery_trace,
        recovery_proof_document=operational_recovery,
        scenario_document=replay.document_from_payload({"invalid": True}),
        evaluated_at_unix_ms=NOW_MS,
        explicit_observation_document=operational_observation,
    )

    assert report["operational_trace"]["status"] == "shadow_plan_ready"
    assert report["scenario_pack_status"] == "failed"
    assert report["operational_acceptance_status"] == ("operational_acceptance_blocked")
    _assert_no_action(report)


def test_default_source_has_no_client_or_process_interaction_primitives():
    source = Path(replay.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "subprocess",
        "Start-Process",
        "Stop-Process",
        "SetForegroundWindow",
        "SendKeys",
        "mouse_event",
        "pyautogui",
        "ctypes.windll",
        "win32gui",
    ):
        assert forbidden not in source
