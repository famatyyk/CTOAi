from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_acceptance as acceptance
from scripts.ops import otclient_conditions_shadow_replay as p9
from scripts.ops import otclient_equipment_dependency_preflight as preflight
from scripts.ops import otclient_equipment_observation_preview as preview


ROOT = Path(__file__).resolve().parents[1]
P9_FIXTURES = ROOT / "tests" / "fixtures" / "otclient_conditions_shadow_replay"
NOW_MS = 1_783_800_000_000


def _payload(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p9.canonical_bytes(payload) + b"\n")


def _equipment_observation() -> dict:
    return {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": "ctoa.equipment-shadow-observation.v1",
        "observed_at_unix_ms": NOW_MS - 1_000,
        "observation_id": "equipment-operational-1",
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


def _ready_workspace(tmp_path: Path) -> tuple[acceptance.EvidencePaths, p9.InputDocument]:
    profile_path = tmp_path / "profile.json"
    p8_path = tmp_path / "background.json"
    recovery_trace_path = tmp_path / "recovery-trace.json"
    recovery_proof_path = tmp_path / "recovery-proof.json"
    scenario_path = tmp_path / "scenarios.json"
    report_path = tmp_path / "report.json"

    profile = _payload(p9.DEFAULT_PROFILE)
    conditions = _payload(P9_FIXTURES / "positive-observation.json")
    conditions.update(
        observed_at_unix_ms=NOW_MS - 1_000,
        observation_id="operational-paralyze-observation",
        producer_source="otclient_guarded_adapter",
    )
    conditions_envelope = {
        **conditions,
        "status": "valid",
        "present": True,
        "valid": True,
        "validation_errors": [],
        "p9_blocker": None,
    }
    generated_at = datetime.fromtimestamp(
        (NOW_MS - 2_000) / 1000, tz=timezone.utc
    ).isoformat()
    background = {
        "schema_version": p9.P8_BACKGROUND_SCHEMA,
        "status": "ready",
        "mode": "background_no_screen",
        "generated_at_utc": generated_at,
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "promotion_allowed": False,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "process_state": "running",
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
        "checks": {
            "trusted_live_manifest_pin": True,
            "live_manifest_parity": True,
            "live_files_unchanged": True,
            "exact_active_client_process": True,
            "fresh_online_heartbeat": True,
            "helper_version_match": True,
            "capability_fail_closed": True,
            "no_screen_contract": True,
            "client_process_stable_during_wrapper": True,
            "screenshot_count_stable_during_wrapper": True,
        },
        "wrapper_invariants": {
            "client_process_stable": True,
            "screenshot_count_stable": True,
        },
        "intrusive_actions_performed": [],
        "integrity": {"manifest_sha256": "b" * 64, "helper_version": "v2.3.8"},
        "capability": {
            "fresh": True,
            "contract_valid": True,
            "version_match": True,
            "runtime_actions": False,
            "runtime_core_actions": False,
            "conditions_observation": conditions_envelope,
            "equipment_shadow_observation": _equipment_observation(),
        },
        "blockers": [],
    }

    recovery_trace = _payload(P9_FIXTURES / "positive-recovery-trace.json")
    recovery_trace.update(observed_at_unix_ms=NOW_MS - 2_000, source="recovery_shadow")
    recovery_trace["trace_id"] = ""
    recovery_trace["trace_id"] = "recovery-shadow-" + p9.canonical_sha256(
        {key: value for key, value in recovery_trace.items() if key != "trace_id"}
    )[:16]
    recovery_proof = _payload(P9_FIXTURES / "positive-recovery-proof.json")
    recovery_proof.update(observed_at_unix_ms=NOW_MS - 2_000, source="recovery_shadow")

    for path, value in (
        (profile_path, profile),
        (p8_path, background),
        (recovery_trace_path, recovery_trace),
        (scenario_path, _payload(p9.DEFAULT_SCENARIO_PACK)),
    ):
        _write(path, value)

    profile_document = p9.read_document(profile_path)
    raw_p8_document = p9.read_document(p8_path)
    observation_document = p9.extract_embedded_observation(raw_p8_document)
    p8_proof = p9.normalize_p8_proof(raw_p8_document, observation_document)
    recovery_trace_document = p9.read_document(recovery_trace_path)
    recovery_proof.update(
        recovery_trace_sha256=recovery_trace_document.sha256,
        profile_sha256=profile_document.sha256,
        observation_sha256=observation_document.sha256,
        p8_proof_sha256=p8_proof.sha256,
    )
    recovery_proof["proof_id"] = ""
    recovery_proof["proof_id"] = "conditions-recovery-" + p9.canonical_sha256(
        {key: value for key, value in recovery_proof.items() if key != "proof_id"}
    )[:16]
    _write(recovery_proof_path, recovery_proof)

    report = p9.build_report(
        profile_document=profile_document,
        raw_p8_document=raw_p8_document,
        recovery_trace_document=recovery_trace_document,
        recovery_proof_document=p9.read_document(recovery_proof_path),
        scenario_document=p9.read_document(scenario_path, p9.MAX_SCENARIO_BYTES),
        evaluated_at_unix_ms=NOW_MS,
        explicit_observation_document=None,
    )
    assert report["operational_acceptance_status"] == (
        "shadow_plan_ready_for_operator_review"
    )
    _write(report_path, report)
    return (
        acceptance.EvidencePaths(
            report=report_path,
            profile=profile_path,
            p8_proof=p8_path,
            recovery_trace=recovery_trace_path,
            recovery_proof=recovery_proof_path,
            scenario_pack=scenario_path,
            observation=None,
        ),
        raw_p8_document,
    )


def _ready_bundle(tmp_path: Path, monkeypatch) -> preflight.EvidenceBundle:
    paths, background = _ready_workspace(tmp_path)
    monkeypatch.setattr(acceptance, "_canonical_operational_paths", lambda _: True)
    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )
    assert receipt["status"] == "accepted"
    doctor = {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": "ready",
        "source": "local_operator_override",
        "path": str(ROOT / ".ctoa-local/otclient/equipment-shadow-capture-profile.json"),
        "sha256": "c" * 64,
        "configured_by_operator": True,
        "slot": "ring",
        "identifiers_present": True,
        "candidate_slot_index_valid": True,
        "no_action_contract": True,
        "blockers": [],
        "next_action": "Run the separate P10 replay after review.",
        "runtime_actions": False,
        "live_file_writes": False,
        "runtime_readiness_claimed": False,
    }
    observation = preview.build_preview(
        background=background, generated_at_unix_ms=NOW_MS
    )
    assert observation["status"] == "preview_ready"
    return preflight.EvidenceBundle(
        p8_report=background,
        p9_report=p9.read_document(paths.report),
        p9_receipt=p9.document_from_payload(receipt),
        capture_doctor=p9.document_from_payload(doctor),
        observation_preview=p9.document_from_payload(observation),
    )


def test_strict_schema_and_blocker_contract_are_closed() -> None:
    schema = _payload(ROOT / "schemas/equipment-dependency-preflight.schema.json")
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["blockers"]["items"]["enum"]) == set(
        preflight.BLOCKER_ORDER
    )


def test_complete_nonfixture_chain_passes_without_changing_eligibility(
    tmp_path: Path, monkeypatch
) -> None:
    report = preflight.evaluate_preflight(
        _ready_bundle(tmp_path, monkeypatch), evaluated_at_unix_ms=NOW_MS
    )
    schema = _payload(ROOT / "schemas/equipment-dependency-preflight.schema.json")
    Draft202012Validator(schema).validate(report)
    assert report["status"] == "passed"
    assert report["dependencies_satisfied"] is True
    assert report["blockers"] == []
    assert report["eligibility_changed"] is False
    assert report["eligibility_state"] == "unchanged"
    assert report["operational_readiness_claimed"] is False
    assert all(report[key] is False for key in preflight.FALSE_FLAGS)
    assert report["intrusive_actions_performed"] == []


def test_accepted_p9_keeps_its_original_p8_binding_while_current_p8_advances(
    tmp_path: Path, monkeypatch
) -> None:
    bundle = _ready_bundle(tmp_path, monkeypatch)
    current_p8 = copy.deepcopy(bundle.p8_report.payload)
    assert isinstance(current_p8, dict)
    current_p8["generated_at_utc"] = datetime.fromtimestamp(
        (NOW_MS - 500) / 1000, tz=timezone.utc
    ).isoformat()
    current_p8["capability"]["equipment_shadow_observation"][
        "observed_at_unix_ms"
    ] = NOW_MS - 500
    current_p8["capability"]["equipment_shadow_observation"][
        "observation_id"
    ] = "equipment-operational-current"
    current_document = p9.document_from_payload(current_p8)
    current_preview = preview.build_preview(
        background=current_document, generated_at_unix_ms=NOW_MS
    )
    assert current_preview["status"] == "preview_ready"
    advanced = preflight.EvidenceBundle(
        p8_report=current_document,
        p9_report=bundle.p9_report,
        p9_receipt=bundle.p9_receipt,
        capture_doctor=bundle.capture_doctor,
        observation_preview=p9.document_from_payload(current_preview),
    )

    report = preflight.evaluate_preflight(advanced, evaluated_at_unix_ms=NOW_MS)

    assert report["status"] == "passed"
    assert report["checks"]["p9_bound_to_current_p8"] is True
    assert report["checks"]["observation_preview_bound_to_current_p8"] is True


def test_fixture_receipt_and_preview_never_pass(tmp_path: Path, monkeypatch) -> None:
    bundle = _ready_bundle(tmp_path, monkeypatch)
    receipt = copy.deepcopy(bundle.p9_receipt.payload)
    observation = copy.deepcopy(bundle.observation_preview.payload)
    assert isinstance(receipt, dict) and isinstance(observation, dict)
    receipt["operational_inputs_fixture"] = True
    observation["observation"]["producer_source"] = "fixture"
    observation["provenance"]["producer_source"] = "fixture"
    observation["observation_sha256"] = p9.canonical_sha256(observation["observation"])
    mutated = preflight.EvidenceBundle(
        p8_report=bundle.p8_report,
        p9_report=bundle.p9_report,
        p9_receipt=p9.document_from_payload(receipt),
        capture_doctor=bundle.capture_doctor,
        observation_preview=p9.document_from_payload(observation),
    )

    report = preflight.evaluate_preflight(mutated, evaluated_at_unix_ms=NOW_MS)

    assert report["status"] == "blocked"
    assert "p9_receipt_fixture_not_operational" in report["blockers"]
    assert "observation_preview_fixture_not_operational" in report["blockers"]
    assert report["eligibility_changed"] is False


def test_hash_binding_tamper_fails_closed(tmp_path: Path, monkeypatch) -> None:
    bundle = _ready_bundle(tmp_path, monkeypatch)
    preview_payload = copy.deepcopy(bundle.observation_preview.payload)
    assert isinstance(preview_payload, dict)
    preview_payload["source_sha256"] = "d" * 64
    mutated = preflight.EvidenceBundle(
        p8_report=bundle.p8_report,
        p9_report=bundle.p9_report,
        p9_receipt=bundle.p9_receipt,
        capture_doctor=bundle.capture_doctor,
        observation_preview=p9.document_from_payload(preview_payload),
    )

    report = preflight.evaluate_preflight(mutated, evaluated_at_unix_ms=NOW_MS)

    assert report["status"] == "blocked"
    assert "observation_preview_background_mismatch" in report["blockers"]
    assert report["checks"]["observation_preview_bound_to_current_p8"] is False


def test_missing_preview_is_explicit_and_fail_closed(tmp_path: Path, monkeypatch) -> None:
    bundle = _ready_bundle(tmp_path, monkeypatch)
    missing = preflight.EvidenceBundle(
        p8_report=bundle.p8_report,
        p9_report=bundle.p9_report,
        p9_receipt=bundle.p9_receipt,
        capture_doctor=bundle.capture_doctor,
        observation_preview=p9.document_from_payload(None, "missing"),
    )

    report = preflight.evaluate_preflight(missing, evaluated_at_unix_ms=NOW_MS)

    assert report["status"] == "blocked"
    assert "observation_preview_missing" in report["blockers"]
    assert report["dependencies_satisfied"] is False
    assert report["eligibility_changed"] is False
