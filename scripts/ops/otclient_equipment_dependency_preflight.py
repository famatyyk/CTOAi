#!/usr/bin/env python3
"""Evaluate the canonical no-action P9 -> P10 dependency chain.

The preflight reads only fixed repo-local evidence.  It never refreshes P8/P9,
creates a P10 snapshot, accepts a receipt, reads an OTClient installation, or
performs a runtime/live action.  A passing report means only that the inputs are
internally consistent at evaluation time; it does not change eligibility or
authorize replay, execute-once, dispatch, inventory movement, or promotion.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_acceptance as p9_acceptance
    from . import otclient_conditions_shadow_replay as p9_replay
    from . import otclient_equipment_observation_preview as observation_preview
    from . import otclient_equipment_shadow_replay as p10_replay
else:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_acceptance as p9_acceptance
    import otclient_conditions_shadow_replay as p9_replay
    import otclient_equipment_observation_preview as observation_preview
    import otclient_equipment_shadow_replay as p10_replay


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"

DEFAULT_P8_REPORT = DEV_DIR / "background_status.json"
DEFAULT_P9_REPORT = DEV_DIR / "conditions_shadow_replay.json"
DEFAULT_P9_RECEIPT = DEV_DIR / "conditions_shadow_acceptance.json"
DEFAULT_CAPTURE_DOCTOR = DEV_DIR / "equipment_capture_profile_doctor.json"
DEFAULT_OBSERVATION_PREVIEW = DEV_DIR / "equipment_observation_preview.json"
DEFAULT_OUTPUT = DEV_DIR / "equipment_dependency_preflight.json"
DEFAULT_LOCAL_CAPTURE_PROFILE = (
    ROOT / ".ctoa-local" / "otclient" / "equipment-shadow-capture-profile.json"
)

SCHEMA = "ctoa.equipment-dependency-preflight.v1"
MODE = "repo_only_dependency_preflight"
MAX_INPUT_BYTES = 512 * 1024
MAX_P8_AGE_MS = p9_replay.MAX_P8_AGE_MS
MAX_PREVIEW_AGE_MS = observation_preview.MAX_AGE_MS
ZERO_SHA256 = p9_replay.ZERO_SHA256

FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)

INPUT_NAMES = (
    "p8_report",
    "p9_report",
    "p9_receipt",
    "capture_doctor",
    "observation_preview",
)

LOAD_FAILURE_STATUSES = (
    "missing",
    "malformed",
    "duplicate_keys",
    "oversize",
    "symlink_rejected",
    "not_regular",
    "unreadable",
    "not_object",
)

BLOCKER_ORDER = (
    *(f"p8_report_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "p8_report_schema_invalid",
    "p8_report_unsafe_contract",
    "p8_report_not_ready",
    "p8_report_future",
    "p8_report_stale",
    "p8_report_fixture_not_operational",
    *(f"p9_report_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "p9_report_schema_invalid",
    "p9_report_unsafe_contract",
    "p9_report_not_ready",
    "p9_report_has_blockers",
    "p9_report_fixture_not_operational",
    *(f"p9_receipt_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "p9_receipt_schema_invalid",
    "p9_receipt_unsafe_contract",
    "p9_receipt_not_accepted",
    "p9_receipt_fixture_not_operational",
    "p9_receipt_report_mismatch",
    "p9_receipt_trace_mismatch",
    "p9_p8_binding_mismatch",
    *(f"capture_doctor_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "capture_doctor_schema_invalid",
    "capture_doctor_unsafe_contract",
    "capture_doctor_blocked",
    "capture_doctor_not_operator_override",
    *(f"observation_preview_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "observation_preview_schema_invalid",
    "observation_preview_unsafe_contract",
    "observation_preview_blocked",
    "observation_preview_not_ready",
    "observation_preview_future",
    "observation_preview_stale",
    "observation_preview_fixture_not_operational",
    "observation_preview_background_mismatch",
    "unsafe_contract",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}

DOCTOR_KEYS = {
    "schema_version",
    "status",
    "source",
    "path",
    "sha256",
    "configured_by_operator",
    "slot",
    "identifiers_present",
    "candidate_slot_index_valid",
    "no_action_contract",
    "blockers",
    "next_action",
    "runtime_actions",
    "live_file_writes",
    "runtime_readiness_claimed",
}

PREVIEW_KEYS = {
    "schema_version",
    "generated_at_unix_ms",
    "status",
    "source",
    "source_sha256",
    "observation_sha256",
    "observation",
    "freshness",
    "provenance",
    "blockers",
    "interaction_contract",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}

PREVIEW_OBSERVATION_KEYS = {
    "schema_version",
    "observation_id",
    "observed_at_unix_ms",
    "online",
    "alive",
    "protection_zone",
    "protection_zone_source",
    "inventory_api_available",
    "containers_complete",
    "ring",
    "candidates",
    "cooldown",
    "cooldown_source",
    "producer_source",
}


@dataclass(frozen=True)
class EvidenceBundle:
    p8_report: p9_replay.InputDocument
    p9_report: p9_replay.InputDocument
    p9_receipt: p9_replay.InputDocument
    capture_doctor: p9_replay.InputDocument
    observation_preview: p9_replay.InputDocument


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: Any, *, allow_zero: bool = False) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
        and (allow_zero or value != ZERO_SHA256)
    )


def _false_flags(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in FALSE_FLAGS)


def _empty_ledger(payload: dict[str, Any]) -> bool:
    return payload.get("intrusive_actions_performed") == []


def _ordered(values: Iterable[str]) -> list[str]:
    unique = set(values)
    unknown = unique - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown dependency blockers: {sorted(unknown)}")
    return sorted(unique, key=BLOCKER_RANK.__getitem__)


def _load_blocker(prefix: str, document: p9_replay.InputDocument) -> str | None:
    if document.status == "loaded" and document.payload is not None:
        return None
    suffix = (
        document.status if document.status in LOAD_FAILURE_STATUSES else "unreadable"
    )
    return f"{prefix}_{suffix}"


def _read(path: Path) -> p9_replay.InputDocument:
    return p9_replay.read_document(path, MAX_INPUT_BYTES)


def read_canonical_evidence() -> EvidenceBundle:
    return EvidenceBundle(
        p8_report=_read(DEFAULT_P8_REPORT),
        p9_report=_read(DEFAULT_P9_REPORT),
        p9_receipt=_read(DEFAULT_P9_RECEIPT),
        capture_doctor=_read(DEFAULT_CAPTURE_DOCTOR),
        observation_preview=_read(DEFAULT_OBSERVATION_PREVIEW),
    )


def _doctor_contract_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != DOCTOR_KEYS:
        return False
    blockers = payload.get("blockers")
    return bool(
        payload.get("schema_version") == "ctoa.equipment-capture-profile-doctor.v1"
        and payload.get("status") in {"ready", "blocked"}
        and payload.get("source")
        in {"tracked_safe_template", "local_operator_override"}
        and isinstance(payload.get("path"), str)
        and bool(payload["path"])
        and _is_sha256(payload.get("sha256"), allow_zero=True)
        and isinstance(payload.get("configured_by_operator"), bool)
        and payload.get("slot") in {"ring", None}
        and isinstance(payload.get("identifiers_present"), bool)
        and isinstance(payload.get("candidate_slot_index_valid"), bool)
        and payload.get("no_action_contract") is True
        and isinstance(blockers, list)
        and len(blockers) == len(set(blockers))
        and all(
            item
            in {
                "local_operator_override_missing",
                "capture_profile_invalid",
                "operator_confirmation_missing",
                "exact_ids_missing",
                "candidate_matches_equipped",
            }
            for item in blockers
        )
        and isinstance(payload.get("next_action"), str)
        and bool(payload["next_action"])
        and payload.get("runtime_actions") is False
        and payload.get("live_file_writes") is False
        and payload.get("runtime_readiness_claimed") is False
        and (
            (payload["status"] == "ready" and blockers == [])
            or (payload["status"] == "blocked" and len(blockers) > 0)
        )
    )


def _preview_observation_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != PREVIEW_OBSERVATION_KEYS:
        return False
    ring = payload.get("ring")
    candidates = payload.get("candidates")
    if not (
        isinstance(ring, dict)
        and set(ring) == {"present", "item_id", "count"}
        and isinstance(ring.get("present"), bool)
        and _is_int(ring.get("item_id"))
        and 0 <= ring["item_id"] <= 65535
        and _is_int(ring.get("count"))
        and 0 <= ring["count"] <= 65535
        and isinstance(candidates, list)
        and len(candidates) <= 256
    ):
        return False
    identities: set[tuple[int, int]] = set()
    for item in candidates:
        if not (
            isinstance(item, dict)
            and set(item) == {"container_id", "slot_index", "item_id", "count"}
            and all(_is_int(item.get(key)) for key in item)
            and 0 <= item["container_id"] <= 65535
            and 1 <= item["slot_index"] <= 65535
            and 1 <= item["item_id"] <= 65535
            and 1 <= item["count"] <= 65535
        ):
            return False
        identity = (item["container_id"], item["slot_index"])
        if identity in identities:
            return False
        identities.add(identity)
    return bool(
        payload.get("schema_version") == observation_preview.OBSERVATION_SCHEMA
        and isinstance(payload.get("observation_id"), str)
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", payload["observation_id"])
        is not None
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload["observed_at_unix_ms"] > 0
        and payload.get("online") in {"online", "offline", "unknown"}
        and payload.get("alive") in {"alive", "dead", "unknown"}
        and payload.get("protection_zone") in {"outside", "inside", "unknown"}
        and payload.get("protection_zone_source")
        in {"player_method", "player_states", "unavailable"}
        and isinstance(payload.get("inventory_api_available"), bool)
        and isinstance(payload.get("containers_complete"), bool)
        and payload.get("cooldown") in {"ready", "active", "unknown"}
        and payload.get("cooldown_source") in {"game_cooldown_group", "unavailable"}
        and payload.get("producer_source") in {"otclient_guarded_adapter", "fixture"}
    )


def _preview_contract_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != PREVIEW_KEYS:
        return False
    blockers = payload.get("blockers")
    freshness = payload.get("freshness")
    provenance = payload.get("provenance")
    observation = payload.get("observation")
    if not (
        isinstance(blockers, list)
        and blockers == observation_preview._ordered(blockers)  # noqa: SLF001
        and isinstance(freshness, dict)
        and set(freshness) == {"observed_at_unix_ms", "age_ms", "max_age_ms", "fresh"}
        and (
            freshness.get("observed_at_unix_ms") is None
            or (
                _is_int(freshness["observed_at_unix_ms"])
                and freshness["observed_at_unix_ms"] > 0
            )
        )
        and (freshness.get("age_ms") is None or _is_int(freshness["age_ms"]))
        and freshness.get("max_age_ms") == MAX_PREVIEW_AGE_MS
        and isinstance(freshness.get("fresh"), bool)
        and isinstance(provenance, dict)
        and set(provenance)
        == {
            "producer_source",
            "background_status_sha256",
            "background_schema_version",
            "background_capability_fresh",
            "background_contract_valid",
            "version_match",
        }
        and (
            provenance.get("producer_source") is None
            or isinstance(provenance["producer_source"], str)
        )
        and _is_sha256(provenance.get("background_status_sha256"), allow_zero=True)
        and (
            provenance.get("background_schema_version") is None
            or isinstance(provenance["background_schema_version"], str)
        )
        and all(
            isinstance(provenance.get(key), bool)
            for key in (
                "background_capability_fresh",
                "background_contract_valid",
                "version_match",
            )
        )
    ):
        return False
    observation_valid = observation is None or _preview_observation_valid(observation)
    observation_hash_valid = (
        payload.get("observation_sha256") is None
        if observation is None
        else payload.get("observation_sha256")
        == p9_replay.canonical_sha256(observation)
    )
    ready = payload.get("status") == "preview_ready"
    generated_at = payload.get("generated_at_unix_ms")
    temporal_contract_valid = True
    if isinstance(observation, dict):
        expected_age = (
            generated_at - observation["observed_at_unix_ms"]
            if _is_int(generated_at)
            else None
        )
        temporal_contract_valid = bool(
            freshness.get("observed_at_unix_ms") == observation["observed_at_unix_ms"]
            and freshness.get("age_ms") == expected_age
            and freshness.get("fresh")
            is (expected_age is not None and 0 <= expected_age <= MAX_PREVIEW_AGE_MS)
            and provenance.get("producer_source") == observation.get("producer_source")
        )
    elif (
        any(freshness.get(key) is not None for key in ("observed_at_unix_ms", "age_ms"))
        or freshness.get("fresh") is not False
    ):
        temporal_contract_valid = False
    return bool(
        payload.get("schema_version") == observation_preview.SCHEMA
        and _is_int(payload.get("generated_at_unix_ms"))
        and payload["generated_at_unix_ms"] > 0
        and payload.get("status") in {"preview_ready", "blocked"}
        and payload.get("source") == "background_status"
        and _is_sha256(payload.get("source_sha256"), allow_zero=True)
        and observation_hash_valid
        and observation_valid
        and temporal_contract_valid
        and provenance.get("background_status_sha256") == payload.get("source_sha256")
        and provenance.get("background_schema_version")
        in {observation_preview.BACKGROUND_SCHEMA, None}
        and payload.get("interaction_contract")
        == observation_preview.INTERACTION_CONTRACT
        and _false_flags(payload)
        and _empty_ledger(payload)
        and (
            (
                ready
                and blockers == []
                and isinstance(observation, dict)
                and freshness.get("fresh") is True
            )
            or (not ready and len(blockers) > 0)
        )
    )


def _summary(
    *,
    name: str,
    document: p9_replay.InputDocument,
    valid: bool,
    ready: bool,
    operational: bool,
    fixture: bool,
    age_ms: int | None,
) -> dict[str, Any]:
    paths = {
        "p8_report": DEFAULT_P8_REPORT,
        "p9_report": DEFAULT_P9_REPORT,
        "p9_receipt": DEFAULT_P9_RECEIPT,
        "capture_doctor": DEFAULT_CAPTURE_DOCTOR,
        "observation_preview": DEFAULT_OBSERVATION_PREVIEW,
    }
    payload = document.payload
    schema_version = (
        payload.get("schema_version") if isinstance(payload, dict) else None
    )
    return {
        "path": paths[name].relative_to(ROOT).as_posix(),
        "load_status": document.status,
        "schema_version": schema_version if isinstance(schema_version, str) else None,
        "sha256": document.sha256,
        "valid": valid,
        "ready": ready,
        "operational": operational,
        "fixture": fixture,
        "age_ms": age_ms,
    }


def evaluate_preflight(
    evidence: EvidenceBundle, *, evaluated_at_unix_ms: int
) -> dict[str, Any]:
    if not _is_int(evaluated_at_unix_ms) or evaluated_at_unix_ms <= 0:
        raise ValueError("evaluated_at_unix_ms must be a positive integer")

    blockers: set[str] = set()
    upstream_blockers: dict[str, list[str]] = {name: [] for name in INPUT_NAMES}

    documents = {
        "p8_report": evidence.p8_report,
        "p9_report": evidence.p9_report,
        "p9_receipt": evidence.p9_receipt,
        "capture_doctor": evidence.capture_doctor,
        "observation_preview": evidence.observation_preview,
    }
    for name, document in documents.items():
        blocker = _load_blocker(name, document)
        if blocker:
            blockers.add(blocker)

    # P8: normalize the current raw BackgroundNoScreen report exactly as P9 does.
    p8_valid = p8_ready = p8_operational = False
    p8_safe = True
    p8_fixture = False
    p8_age_ms: int | None = None
    p8_proof = p9_replay.document_from_payload(None, "missing")
    p8_payload = evidence.p8_report.payload
    if evidence.p8_report.status == "loaded" and isinstance(p8_payload, dict):
        raw_safe = p9_replay._raw_p8_no_action_contract(p8_payload)  # noqa: SLF001
        p8_safe = raw_safe
        observation = p9_replay.extract_embedded_observation(evidence.p8_report)
        p8_proof = p9_replay.normalize_p8_proof(evidence.p8_report, observation)
        proof_payload = p8_proof.payload
        p8_shape_valid = bool(
            p8_payload.get("schema_version") == p9_replay.P8_BACKGROUND_SCHEMA
            and isinstance(proof_payload, dict)
            and p9_replay._p8_structurally_valid(proof_payload)  # noqa: SLF001
        )
        if not p8_shape_valid:
            blockers.add("p8_report_schema_invalid")
        if not raw_safe:
            blockers.add("p8_report_unsafe_contract")
        p8_valid = p8_shape_valid and raw_safe
        if isinstance(proof_payload, dict):
            observed_at = proof_payload.get("observed_at_unix_ms")
            if _is_int(observed_at) and observed_at > 0:
                p8_age_ms = evaluated_at_unix_ms - observed_at
                if p8_age_ms < 0:
                    blockers.add("p8_report_future")
                elif p8_age_ms > MAX_P8_AGE_MS:
                    blockers.add("p8_report_stale")
            else:
                blockers.add("p8_report_schema_invalid")
            p8_operational = proof_payload.get("source") == "background_no_screen"
            p8_fixture = not p8_operational
            if p8_fixture:
                blockers.add("p8_report_fixture_not_operational")
            p8_ready = bool(
                p8_valid
                and p8_operational
                and p8_age_ms is not None
                and 0 <= p8_age_ms <= MAX_P8_AGE_MS
                and p9_replay._p8_acceptance_ready(proof_payload)  # noqa: SLF001
            )
            if isinstance(p8_payload.get("blockers"), list):
                upstream_blockers["p8_report"] = [
                    str(item) for item in p8_payload["blockers"]
                ]
        if not p8_ready:
            blockers.add("p8_report_not_ready")

    # P9 report: full canonical report, never a fixture-only direct trace.
    p9_report_valid = p9_report_ready = p9_report_operational = False
    p9_report_safe = True
    p9_report_fixture = False
    p9_payload = evidence.p9_report.payload
    p9_trace: dict[str, Any] | None = None
    if evidence.p9_report.status == "loaded" and isinstance(p9_payload, dict):
        top_shape_valid = bool(
            set(p9_payload) == p9_acceptance.REPORT_KEYS
            and p9_payload.get("schema_version") == p9_replay.REPORT_SCHEMA
        )
        safe = p9_acceptance._report_no_action_contract(p9_payload)  # noqa: SLF001
        p9_report_safe = safe
        if not top_shape_valid:
            blockers.add("p9_report_schema_invalid")
        elif not safe:
            blockers.add("p9_report_unsafe_contract")
        candidate_trace = p9_payload.get("operational_trace")
        trace_shape_valid = bool(
            isinstance(candidate_trace, dict)
            and set(candidate_trace) == p10_replay.P9_TRACE_KEYS
            and candidate_trace.get("schema_version") == p9_replay.TRACE_SCHEMA
        )
        if not trace_shape_valid:
            blockers.add("p9_report_schema_invalid")
        else:
            p9_trace = candidate_trace
            trace_blockers = candidate_trace.get("blockers")
            if isinstance(trace_blockers, list):
                upstream_blockers["p9_report"] = [str(item) for item in trace_blockers]
                if trace_blockers:
                    blockers.add("p9_report_has_blockers")
            p9_report_operational = candidate_trace.get("source") == "operational"
            p9_report_fixture = not p9_report_operational or any(
                str(item).startswith("fixture_")
                for item in upstream_blockers["p9_report"]
            )
            if p9_report_fixture:
                blockers.add("p9_report_fixture_not_operational")
        p9_report_valid = bool(top_shape_valid and safe and trace_shape_valid)
        p9_report_ready = bool(
            p9_report_valid
            and p9_report_operational
            and p9_payload.get("operational_acceptance_status")
            == "shadow_plan_ready_for_operator_review"
            and isinstance(p9_trace, dict)
            and p10_replay._p9_trace_valid(p9_trace)  # noqa: SLF001
        )
        if not p9_report_ready:
            blockers.add("p9_report_not_ready")

    # P9 receipt: accepted, non-fixture, persisted, and bound to the full report.
    p9_receipt_valid = p9_receipt_ready = p9_receipt_operational = False
    p9_receipt_safe = True
    p9_receipt_fixture = False
    p9_receipt_payload = evidence.p9_receipt.payload
    receipt_report_bound = receipt_trace_bound = p9_p8_bound = False
    if evidence.p9_receipt.status == "loaded" and isinstance(p9_receipt_payload, dict):
        receipt_shape_valid = bool(
            set(p9_receipt_payload) == p9_acceptance.RECEIPT_KEYS
            and p9_receipt_payload.get("schema_version") == p9_acceptance.SCHEMA_VERSION
        )
        receipt_safe = bool(
            _false_flags(p9_receipt_payload)
            and _empty_ledger(p9_receipt_payload)
            and p9_receipt_payload.get("runtime_readiness_claimed") is False
        )
        p9_receipt_safe = receipt_safe
        if not receipt_shape_valid:
            blockers.add("p9_receipt_schema_invalid")
        elif not receipt_safe:
            blockers.add("p9_receipt_unsafe_contract")
        p9_receipt_valid = bool(
            receipt_shape_valid
            and receipt_safe
            and p9_acceptance._receipt_contract_valid(p9_receipt_payload)  # noqa: SLF001
        )
        if receipt_shape_valid and not p9_receipt_valid and receipt_safe:
            blockers.add("p9_receipt_schema_invalid")
        p9_receipt_operational = bool(
            p9_receipt_payload.get("operational_inputs_fixture") is False
            and p9_receipt_payload.get("canonical_operational_paths") is True
        )
        p9_receipt_fixture = not p9_receipt_operational
        if p9_receipt_fixture:
            blockers.add("p9_receipt_fixture_not_operational")
        p9_receipt_ready = bool(
            p9_receipt_valid
            and p9_receipt_operational
            and p9_receipt_payload.get("status") == "accepted"
            and p9_receipt_payload.get("acceptance_granted") is True
            and p9_receipt_payload.get("operator_review_completed") is True
            and p9_receipt_payload.get("receipt_persisted") is True
        )
        if not p9_receipt_ready:
            blockers.add("p9_receipt_not_accepted")
        receipt_report_bound = bool(
            p9_report_valid
            and p9_receipt_payload.get("report_sha256") == evidence.p9_report.sha256
            and p9_receipt_payload.get("recomputed_report_sha256")
            == evidence.p9_report.sha256
        )
        if not receipt_report_bound:
            blockers.add("p9_receipt_report_mismatch")
        receipt_trace_bound = bool(
            isinstance(p9_trace, dict)
            and p9_receipt_payload.get("decision_sha256")
            == p9_trace.get("decision_sha256")
            and p9_receipt_payload.get("canonical_input_sha256")
            == p9_trace.get("canonical_input_sha256")
            and p9_receipt_payload.get("input_sha256") == p9_trace.get("input_sha256")
        )
        if not receipt_trace_bound:
            blockers.add("p9_receipt_trace_mismatch")
        # P9 is a durable accepted predecessor.  Its receipt must preserve the
        # P8 proof hash recorded by the accepted P9 report, but it must not be
        # rebound to today's ephemeral BackgroundNoScreen document.  Current
        # P8 is independently required below for the current P10 preview.
        trace_hashes = (
            p9_trace.get("input_sha256") if isinstance(p9_trace, dict) else None
        )
        p9_p8_bound = bool(
            isinstance(trace_hashes, dict)
            and _is_sha256(trace_hashes.get("p8_proof"))
            and isinstance(p9_receipt_payload.get("input_sha256"), dict)
            and p9_receipt_payload["input_sha256"].get("p8_proof")
            == trace_hashes.get("p8_proof")
        )
        if not p9_p8_bound:
            blockers.add("p9_p8_binding_mismatch")
        if isinstance(p9_receipt_payload.get("blockers"), list):
            upstream_blockers["p9_receipt"] = [
                str(item) for item in p9_receipt_payload["blockers"]
            ]

    # Capture doctor: ready only for the fixed ignored operator override.
    doctor_valid = doctor_ready = doctor_operational = False
    doctor_safe = True
    doctor_fixture = False
    doctor_payload = evidence.capture_doctor.payload
    if evidence.capture_doctor.status == "loaded" and isinstance(doctor_payload, dict):
        doctor_valid = _doctor_contract_valid(doctor_payload)
        doctor_safe = bool(
            doctor_payload.get("no_action_contract") is True
            and doctor_payload.get("runtime_actions") is False
            and doctor_payload.get("live_file_writes") is False
        )
        if not doctor_valid:
            blockers.add("capture_doctor_schema_invalid")
        if not doctor_safe:
            blockers.add("capture_doctor_unsafe_contract")
        doctor_path = doctor_payload.get("path")
        doctor_operational = bool(
            doctor_payload.get("source") == "local_operator_override"
            and isinstance(doctor_path, str)
            and _same_path(Path(doctor_path), DEFAULT_LOCAL_CAPTURE_PROFILE)
        )
        doctor_fixture = not doctor_operational
        if doctor_fixture:
            blockers.add("capture_doctor_not_operator_override")
        if isinstance(doctor_payload.get("blockers"), list):
            upstream_blockers["capture_doctor"] = [
                str(item) for item in doctor_payload["blockers"]
            ]
        doctor_ready = bool(
            doctor_valid
            and doctor_safe
            and doctor_operational
            and doctor_payload.get("status") == "ready"
            and doctor_payload.get("configured_by_operator") is True
            and doctor_payload.get("identifiers_present") is True
            and doctor_payload.get("candidate_slot_index_valid") is True
            and doctor_payload.get("slot") == "ring"
            and doctor_payload.get("blockers") == []
        )
        if not doctor_ready:
            blockers.add("capture_doctor_blocked")

    # Observation preview: ready, fresh, operational, and bound to current P8.
    preview_valid = preview_ready = preview_operational = False
    preview_safe = True
    preview_fixture = False
    preview_age_ms: int | None = None
    preview_background_bound = False
    preview_payload = evidence.observation_preview.payload
    if evidence.observation_preview.status == "loaded" and isinstance(
        preview_payload, dict
    ):
        try:
            preview_valid = _preview_contract_valid(preview_payload)
        except ValueError:
            preview_valid = False
        preview_safe = bool(
            _false_flags(preview_payload) and _empty_ledger(preview_payload)
        )
        if not preview_valid:
            blockers.add("observation_preview_schema_invalid")
        if not preview_safe:
            blockers.add("observation_preview_unsafe_contract")
        freshness = preview_payload.get("freshness")
        if isinstance(freshness, dict) and _is_int(
            freshness.get("observed_at_unix_ms")
        ):
            preview_age_ms = evaluated_at_unix_ms - freshness["observed_at_unix_ms"]
            if preview_age_ms < 0:
                blockers.add("observation_preview_future")
            elif preview_age_ms > MAX_PREVIEW_AGE_MS:
                blockers.add("observation_preview_stale")
        else:
            blockers.add("observation_preview_not_ready")
        provenance = preview_payload.get("provenance")
        observation = preview_payload.get("observation")
        preview_operational = bool(
            isinstance(provenance, dict)
            and provenance.get("producer_source") == "otclient_guarded_adapter"
            and isinstance(observation, dict)
            and observation.get("producer_source") == "otclient_guarded_adapter"
        )
        preview_fixture = not preview_operational
        if preview_fixture:
            blockers.add("observation_preview_fixture_not_operational")
        preview_background_bound = bool(
            p8_valid
            and preview_payload.get("source_sha256") == evidence.p8_report.sha256
            and isinstance(provenance, dict)
            and provenance.get("background_status_sha256") == evidence.p8_report.sha256
        )
        if not preview_background_bound:
            blockers.add("observation_preview_background_mismatch")
        if isinstance(preview_payload.get("blockers"), list):
            upstream_blockers["observation_preview"] = [
                str(item) for item in preview_payload["blockers"]
            ]
        preview_ready = bool(
            preview_valid
            and preview_safe
            and preview_operational
            and preview_background_bound
            and preview_payload.get("status") == "preview_ready"
            and preview_payload.get("blockers") == []
            and isinstance(freshness, dict)
            and freshness.get("fresh") is True
            and preview_age_ms is not None
            and 0 <= preview_age_ms <= MAX_PREVIEW_AGE_MS
            and isinstance(provenance, dict)
            and provenance.get("background_capability_fresh") is True
            and provenance.get("background_contract_valid") is True
            and provenance.get("version_match") is True
        )
        if preview_payload.get("status") == "blocked":
            blockers.add("observation_preview_blocked")
        if not preview_ready:
            blockers.add("observation_preview_not_ready")

    no_action_chain = bool(
        p8_safe and p9_report_safe and p9_receipt_safe and doctor_safe and preview_safe
    )
    if not no_action_chain:
        blockers.add("unsafe_contract")
    non_fixture_chain = bool(
        p8_operational
        and p9_report_operational
        and p9_receipt_operational
        and doctor_operational
        and preview_operational
        and not any(
            (
                p8_fixture,
                p9_report_fixture,
                p9_receipt_fixture,
                doctor_fixture,
                preview_fixture,
            )
        )
    )

    checks = {
        "p8_background_valid": p8_valid,
        "p8_background_fresh": p8_ready,
        "p9_report_ready": p9_report_ready,
        "p9_receipt_accepted": p9_receipt_ready,
        "p9_receipt_report_bound": receipt_report_bound,
        "p9_receipt_trace_bound": receipt_trace_bound,
        "p9_bound_to_current_p8": p9_p8_bound,
        "capture_doctor_ready": doctor_ready,
        "observation_preview_ready": preview_ready,
        "observation_preview_bound_to_current_p8": preview_background_bound,
        "non_fixture_chain": non_fixture_chain,
        "no_action_chain": no_action_chain,
    }

    ordered = _ordered(blockers)
    dependencies_satisfied = not ordered and all(checks.values())
    if not dependencies_satisfied and not ordered:
        raise AssertionError("blocked dependency state requires an exact blocker")

    inputs = {
        "p8_report": _summary(
            name="p8_report",
            document=evidence.p8_report,
            valid=p8_valid,
            ready=p8_ready,
            operational=p8_operational,
            fixture=p8_fixture,
            age_ms=p8_age_ms,
        ),
        "p9_report": _summary(
            name="p9_report",
            document=evidence.p9_report,
            valid=p9_report_valid,
            ready=p9_report_ready,
            operational=p9_report_operational,
            fixture=p9_report_fixture,
            age_ms=None,
        ),
        "p9_receipt": _summary(
            name="p9_receipt",
            document=evidence.p9_receipt,
            valid=p9_receipt_valid,
            ready=p9_receipt_ready,
            operational=p9_receipt_operational,
            fixture=p9_receipt_fixture,
            age_ms=None,
        ),
        "capture_doctor": _summary(
            name="capture_doctor",
            document=evidence.capture_doctor,
            valid=doctor_valid,
            ready=doctor_ready,
            operational=doctor_operational,
            fixture=doctor_fixture,
            age_ms=None,
        ),
        "observation_preview": _summary(
            name="observation_preview",
            document=evidence.observation_preview,
            valid=preview_valid,
            ready=preview_ready,
            operational=preview_operational,
            fixture=preview_fixture,
            age_ms=preview_age_ms,
        ),
    }
    input_sha256 = {name: documents[name].sha256 for name in INPUT_NAMES}
    canonical_input_sha256 = p9_replay.canonical_sha256(
        {
            "schema_version": "ctoa.equipment-dependency-input.v1",
            "evaluated_at_unix_ms": evaluated_at_unix_ms,
            "input_sha256": input_sha256,
        }
    )
    basis = {
        "schema_version": SCHEMA,
        "status": "passed" if dependencies_satisfied else "blocked",
        "dependencies_satisfied": dependencies_satisfied,
        "checks": checks,
        "blockers": ordered,
        "input_sha256": input_sha256,
        "canonical_input_sha256": canonical_input_sha256,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    decision_sha256 = p9_replay.canonical_sha256(basis)
    return {
        "schema_version": SCHEMA,
        "mode": MODE,
        "evaluated_at_unix_ms": evaluated_at_unix_ms,
        "status": basis["status"],
        "dependencies_satisfied": dependencies_satisfied,
        "inputs": inputs,
        "input_sha256": input_sha256,
        "canonical_input_sha256": canonical_input_sha256,
        "checks": checks,
        "upstream_blockers": upstream_blockers,
        "blockers": ordered,
        "decision_sha256": decision_sha256,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        "operator_review_required": True,
        "repo_report_write_only": True,
        "live_file_writes": False,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _validate_output(path: Path) -> Path:
    if not _same_path(path, DEFAULT_OUTPUT):
        raise ValueError(f"output must equal {DEFAULT_OUTPUT}")
    boundary = RUNTIME_ROOT.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(boundary):
        raise ValueError(f"output must stay under {boundary}")
    current = boundary
    relative = Path(os.path.abspath(path.parent)).relative_to(
        Path(os.path.abspath(boundary))
    )
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & reparse
        ):
            raise ValueError(
                "output parent must not contain a symlink or reparse point"
            )
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return resolved
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("output must be a regular non-link file")
    return resolved


def write_report(payload: dict[str, Any]) -> None:
    output = _validate_output(DEFAULT_OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | int(getattr(os, "O_BINARY", 0))
            | int(getattr(os, "O_NOFOLLOW", 0))
        )
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(p9_replay.canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        metadata = temporary.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("temporary output identity invalid")
        temporary.replace(output)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return success after emitting a structurally blocked report",
    )
    args = parser.parse_args(argv)
    report = evaluate_preflight(
        read_canonical_evidence(), evaluated_at_unix_ms=int(time.time() * 1000)
    )
    if not args.no_write:
        write_report(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"P10 dependency preflight: {report['status']}", file=sys.stderr)
    return 0 if report["status"] == "passed" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
