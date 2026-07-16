from __future__ import annotations

import copy
from pathlib import Path

from scripts.ops import otclient_conditions_recovery_proof as producer
from scripts.ops import otclient_conditions_shadow_replay as replay


NOW_MS = 1783800000000


def _observation() -> dict:
    payload = dict(
        replay.read_document(
            replay.FIXTURE_DIR / "positive-observation.json"
        ).payload
        or {}
    )
    payload["observed_at_unix_ms"] = NOW_MS - 1000
    payload["observation_id"] = "operational-positive-paralyze"
    payload["producer_source"] = "otclient_guarded_adapter"
    return payload


def _background() -> dict:
    observation = _observation()
    envelope = {
        **observation,
        "status": "valid",
        "present": True,
        "valid": True,
        "validation_errors": [],
        "p9_blocker": None,
    }
    return {
        "schema_version": replay.P8_BACKGROUND_SCHEMA,
        "generated_at_utc": "2026-07-11T19:59:59+00:00",
        "status": "ready",
        "mode": "background_no_screen",
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "promotion_allowed": False,
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
        "integrity": {
            "manifest_sha256": "a" * 64,
            "helper_version": "v2.3.5",
        },
        "capability": {
            "conditions_observation": envelope,
            "runtime_actions": False,
            "runtime_core_actions": False,
        },
    }


def _build(background: dict | None = None):
    return producer.build_evidence(
        background=replay.document_from_payload(background or _background()),
        profile=replay.read_document(producer.DEFAULT_PROFILE),
        generated_at_unix_ms=NOW_MS,
    )


def test_ready_background_produces_hash_bound_no_action_recovery_evidence():
    trace, proof = _build()

    assert trace["status"] == proof["status"] == "ready"
    assert trace["decision"] == "plan_heal"
    assert trace["action"] == "exura"
    assert trace["blockers"] == []
    assert proof["recovery_trace_sha256"] == replay.canonical_sha256(trace)
    assert replay._recovery_trace_structurally_valid(trace)
    assert replay._recovery_proof_structurally_valid(proof)
    tampered_trace = dict(trace)
    tampered_trace["trace_id"] = "recovery-shadow-0000000000000000"
    assert not replay._recovery_trace_structurally_valid(tampered_trace)
    tampered_proof = dict(proof)
    tampered_proof["proof_id"] = "conditions-recovery-0000000000000000"
    assert not replay._recovery_proof_structurally_valid(tampered_proof)
    for payload in (trace, proof):
        assert all(payload[key] is False for key in producer.FALSE_FLAGS)
        assert payload["intrusive_actions_performed"] == []


def test_blocked_p8_and_unknown_observation_emit_blocked_not_missing_evidence():
    background = copy.deepcopy(_background())
    background["status"] = "blocked"
    background["checks"]["fresh_online_heartbeat"] = False
    observation = background["capability"]["conditions_observation"]
    observation["online"] = "offline"
    observation["condition_state"] = "unknown"

    trace, proof = _build(background)

    assert trace["status"] == proof["status"] == "blocked"
    assert trace["decision"] == "hold"
    assert "player_offline" in trace["blockers"]
    assert "condition_unknown" in trace["blockers"]
    assert "p8_operational_acceptance_blocked" in trace["blockers"]
    assert replay._recovery_trace_structurally_valid(trace)
    assert replay._recovery_proof_structurally_valid(proof)


def test_output_boundary_rejects_noncanonical_path(tmp_path: Path):
    try:
        producer._validate_output(tmp_path / "trace.json", producer.DEFAULT_TRACE)
    except ValueError as exc:
        assert "output must equal" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("noncanonical output was accepted")
