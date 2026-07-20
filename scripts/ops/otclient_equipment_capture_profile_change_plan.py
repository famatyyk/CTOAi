#!/usr/bin/env python3
"""Generate a hash-bound, data-only P10 capture-profile change plan.

The generator reads only the fixed capture-profile doctor and equipment
observation preview under ``runtime/solteria_helper_dev``. It never reads or
writes ``.ctoa-local``, never controls OTClient, and never grants acceptance or
runtime readiness. Without all exact identifiers and the exact confirmation it
emits an explanatory blocked report.
"""

from __future__ import annotations

import argparse
import hashlib
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
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_observation_preview as preview
    from . import otclient_equipment_shadow_snapshot as snapshot
else:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_observation_preview as preview
    import otclient_equipment_shadow_snapshot as snapshot


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_CAPTURE_DOCTOR = DEV_DIR / "equipment_capture_profile_doctor.json"
DEFAULT_OBSERVATION_PREVIEW = DEV_DIR / "equipment_observation_preview.json"
DEFAULT_OUTPUT = DEV_DIR / "equipment_capture_profile_change_plan.json"
DEFAULT_LOCAL_CAPTURE_PROFILE = (
    ROOT / ".ctoa-local" / "otclient" / "equipment-shadow-capture-profile.json"
)

SCHEMA = "ctoa.equipment-capture-profile-change-plan.v1"
MODE = "repo_runtime_profile_change_plan"
EXACT_CONFIRMATION = "plan P10 capture profile change"
MAX_INPUT_BYTES = 256 * 1024
ZERO_SHA256 = documents.ZERO_SHA256
TARGET_PROFILE_RELPATH = ".ctoa-local/otclient/equipment-shadow-capture-profile.json"

FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)

INTERACTION_CONTRACT = {
    "gui_automation": False,
    "mouse_keyboard_input": False,
    "window_focus": False,
    "screenshot_capture": False,
    "client_launch": False,
    "client_stop": False,
    "local_profile_read": False,
    "local_profile_write": False,
    "live_file_writes": False,
    "repo_runtime_reads_only": True,
    "evidence_write_scope": "runtime/solteria_helper_dev",
}

LOAD_FAILURE_STATUSES = (
    "missing",
    "malformed",
    "duplicate_keys",
    "oversize",
    "symlink_rejected",
    "not_regular",
    "changed_during_open",
    "unreadable",
    "not_object",
)

BLOCKER_ORDER = (
    *(f"capture_doctor_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "capture_doctor_schema_invalid",
    "capture_doctor_unsafe_contract",
    "capture_doctor_profile_invalid",
    "capture_doctor_not_local_override",
    *(f"observation_preview_{suffix}" for suffix in LOAD_FAILURE_STATUSES),
    "observation_preview_schema_invalid",
    "observation_preview_unsafe_contract",
    "observation_preview_not_ready",
    "observation_preview_future",
    "observation_preview_stale",
    "observation_preview_fixture_not_operational",
    "explicit_identifiers_missing",
    "explicit_identifiers_incomplete",
    "explicit_identifiers_invalid",
    "item_ids_not_distinct",
    "equipped_item_preview_mismatch",
    "candidate_exact_match_missing",
    "candidate_exact_match_ambiguous",
    "operator_confirmation_missing",
    "operator_confirmation_mismatch",
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

OBSERVATION_KEYS = {
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
class CanonicalInputs:
    capture_doctor: documents.InputDocument
    observation_preview: documents.InputDocument


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: Any, *, allow_zero: bool = False) -> bool:
    return bool(
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value)
        and (allow_zero or value != ZERO_SHA256)
    )


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _status_document(status: str) -> documents.InputDocument:
    return documents.InputDocument(
        None, status, documents.canonical_sha256({"load_status": status})
    )


def _read_fixed_runtime_document(path: Path) -> documents.InputDocument:
    """Read one fixed runtime artifact after rejecting reparse ancestors."""

    root = Path(os.path.abspath(RUNTIME_ROOT))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return _status_document("unreadable")

    current = root
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError:
            return _status_document("unreadable")
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & reparse
        ):
            return _status_document("symlink_rejected")
    return documents.read_document(path, MAX_INPUT_BYTES)


def read_canonical_inputs() -> CanonicalInputs:
    return CanonicalInputs(
        capture_doctor=_read_fixed_runtime_document(DEFAULT_CAPTURE_DOCTOR),
        observation_preview=_read_fixed_runtime_document(DEFAULT_OBSERVATION_PREVIEW),
    )


def _ordered(values: Iterable[str]) -> list[str]:
    unique = set(values)
    unknown = unique - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown profile change-plan blockers: {sorted(unknown)}")
    return sorted(unique, key=BLOCKER_RANK.__getitem__)


def _load_blocker(prefix: str, document: documents.InputDocument) -> str | None:
    if document.status == "loaded" and document.payload is not None:
        return None
    suffix = (
        document.status if document.status in LOAD_FAILURE_STATUSES else "unreadable"
    )
    return f"{prefix}_{suffix}"


def _doctor_contract_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != DOCTOR_KEYS:
        return False
    blockers = payload.get("blockers")
    allowed_blockers = {
        "local_operator_override_missing",
        "capture_profile_invalid",
        "operator_confirmation_missing",
        "exact_ids_missing",
        "candidate_matches_equipped",
    }
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
        and all(item in allowed_blockers for item in blockers)
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


def _observation_contract_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != OBSERVATION_KEYS:
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
        payload.get("schema_version") == snapshot.OBSERVATION_SCHEMA
        and isinstance(payload.get("observation_id"), str)
        and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", payload["observation_id"])
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
    try:
        blockers_valid = isinstance(blockers, list) and blockers == preview._ordered(
            blockers
        )
    except ValueError:
        blockers_valid = False
    if not (
        payload.get("schema_version") == preview.SCHEMA
        and _is_int(payload.get("generated_at_unix_ms"))
        and payload["generated_at_unix_ms"] > 0
        and payload.get("status") in {"preview_ready", "blocked"}
        and payload.get("source") == "background_status"
        and _is_sha256(payload.get("source_sha256"), allow_zero=True)
        and blockers_valid
        and isinstance(freshness, dict)
        and set(freshness) == {"observed_at_unix_ms", "age_ms", "max_age_ms", "fresh"}
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
        and payload.get("interaction_contract") == preview.INTERACTION_CONTRACT
        and all(payload.get(key) is False for key in FALSE_FLAGS)
        and payload.get("intrusive_actions_performed") == []
    ):
        return False
    if not (
        freshness.get("observed_at_unix_ms") is None
        or (
            _is_int(freshness["observed_at_unix_ms"])
            and freshness["observed_at_unix_ms"] > 0
        )
    ):
        return False
    if not (freshness.get("age_ms") is None or _is_int(freshness.get("age_ms"))):
        return False
    if (
        freshness.get("max_age_ms") != preview.MAX_AGE_MS
        or not isinstance(freshness.get("fresh"), bool)
        or not _is_sha256(provenance.get("background_status_sha256"), allow_zero=True)
        or provenance.get("background_status_sha256") != payload.get("source_sha256")
        or not all(
            isinstance(provenance.get(key), bool)
            for key in (
                "background_capability_fresh",
                "background_contract_valid",
                "version_match",
            )
        )
    ):
        return False
    if observation is None:
        observation_valid = payload.get("observation_sha256") is None
    else:
        observation_valid = bool(
            _observation_contract_valid(observation)
            and payload.get("observation_sha256")
            == documents.canonical_sha256(observation)
            and freshness.get("observed_at_unix_ms")
            == observation.get("observed_at_unix_ms")
            and freshness.get("age_ms")
            == payload["generated_at_unix_ms"] - observation["observed_at_unix_ms"]
            and freshness.get("fresh")
            == (
                0
                <= payload["generated_at_unix_ms"] - observation["observed_at_unix_ms"]
                <= preview.MAX_AGE_MS
            )
        )
    return bool(
        observation_valid
        and (
            (payload["status"] == "preview_ready" and blockers == [] and observation)
            or (payload["status"] == "blocked" and blockers)
        )
    )


def _parse_identifier(value: Any) -> tuple[int | None, bool]:
    if value is None:
        return None, False
    if _is_int(value):
        parsed = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,5}", value):
        parsed = int(value)
    else:
        return None, False
    return (parsed, True) if 1 <= parsed <= 65535 else (None, False)


def _proposed_profile(identifiers: dict[str, int]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": snapshot.CAPTURE_SCHEMA,
        "configured_by_operator": True,
        "slot": "ring",
        **identifiers,
        "max_observation_age_ms": snapshot.MAX_AGE_MS,
        "retry_budget": 0,
        **{key: False for key in snapshot.FALSE_FLAGS},
    }
    if not snapshot._capture_profile_valid(payload):  # pragma: no cover - invariant
        raise RuntimeError("generated capture profile is invalid")
    return payload


def evaluate_change_plan(
    inputs: CanonicalInputs,
    *,
    equipped_item_id: Any = None,
    candidate_item_id: Any = None,
    candidate_source_container_id: Any = None,
    candidate_source_slot_index: Any = None,
    confirmation: str | None = None,
    generated_at_unix_ms: int,
) -> dict[str, Any]:
    blockers: set[str] = set()
    for prefix, document in (
        ("capture_doctor", inputs.capture_doctor),
        ("observation_preview", inputs.observation_preview),
    ):
        blocker = _load_blocker(prefix, document)
        if blocker:
            blockers.add(blocker)

    doctor_payload = inputs.capture_doctor.payload
    doctor_valid = bool(
        inputs.capture_doctor.status == "loaded"
        and _doctor_contract_valid(doctor_payload)
    )
    doctor_safe = bool(
        doctor_valid
        and isinstance(doctor_payload, dict)
        and doctor_payload.get("no_action_contract") is True
        and doctor_payload.get("runtime_actions") is False
        and doctor_payload.get("live_file_writes") is False
        and doctor_payload.get("runtime_readiness_claimed") is False
    )
    doctor_local = bool(
        doctor_valid
        and isinstance(doctor_payload, dict)
        and doctor_payload.get("source") == "local_operator_override"
        and isinstance(doctor_payload.get("path"), str)
        and _same_path(Path(doctor_payload["path"]), DEFAULT_LOCAL_CAPTURE_PROFILE)
    )
    doctor_profile_valid = bool(
        doctor_valid
        and isinstance(doctor_payload, dict)
        and _is_sha256(doctor_payload.get("sha256"))
        and "capture_profile_invalid" not in doctor_payload.get("blockers", [])
    )
    if inputs.capture_doctor.status == "loaded" and not doctor_valid:
        blockers.add("capture_doctor_schema_invalid")
    elif doctor_valid and not doctor_safe:
        blockers.add("capture_doctor_unsafe_contract")
    if doctor_valid and not doctor_profile_valid:
        blockers.add("capture_doctor_profile_invalid")
    if doctor_valid and not doctor_local:
        blockers.add("capture_doctor_not_local_override")

    preview_payload = inputs.observation_preview.payload
    preview_valid = bool(
        inputs.observation_preview.status == "loaded"
        and _preview_contract_valid(preview_payload)
    )
    preview_safe = bool(
        preview_valid
        and isinstance(preview_payload, dict)
        and all(preview_payload.get(key) is False for key in FALSE_FLAGS)
        and preview_payload.get("intrusive_actions_performed") == []
    )
    observation = (
        preview_payload.get("observation")
        if preview_valid and isinstance(preview_payload, dict)
        else None
    )
    preview_freshness = (
        preview_payload.get("freshness")
        if preview_valid and isinstance(preview_payload, dict)
        else None
    )
    preview_provenance = (
        preview_payload.get("provenance")
        if preview_valid and isinstance(preview_payload, dict)
        else None
    )
    preview_ring = observation.get("ring") if isinstance(observation, dict) else None
    preview_ready = bool(
        preview_valid
        and isinstance(preview_payload, dict)
        and preview_payload.get("status") == "preview_ready"
        and preview_payload.get("blockers") == []
        and isinstance(observation, dict)
        and observation.get("online") == "online"
        and observation.get("alive") == "alive"
        and observation.get("protection_zone") == "outside"
        and observation.get("protection_zone_source")
        in {"player_method", "player_states"}
        and observation.get("inventory_api_available") is True
        and observation.get("containers_complete") is True
        and isinstance(preview_ring, dict)
        and preview_ring.get("present") is True
        and observation.get("cooldown") == "ready"
        and observation.get("cooldown_source") == "game_cooldown_group"
        and isinstance(preview_freshness, dict)
        and preview_freshness.get("fresh") is True
        and isinstance(preview_provenance, dict)
        and preview_provenance.get("background_capability_fresh") is True
        and preview_provenance.get("background_contract_valid") is True
        and preview_provenance.get("version_match") is True
    )
    observation_operational = bool(
        preview_ready
        and observation.get("producer_source") == "otclient_guarded_adapter"
        and isinstance(preview_provenance, dict)
        and preview_provenance.get("producer_source") == "otclient_guarded_adapter"
    )
    observation_age_ms: int | None = None
    preview_fresh = False
    if isinstance(observation, dict) and _is_int(
        observation.get("observed_at_unix_ms")
    ):
        observation_age_ms = generated_at_unix_ms - observation["observed_at_unix_ms"]
        preview_fresh = 0 <= observation_age_ms <= preview.MAX_AGE_MS
        if observation_age_ms < 0:
            blockers.add("observation_preview_future")
        elif observation_age_ms > preview.MAX_AGE_MS:
            blockers.add("observation_preview_stale")
    if inputs.observation_preview.status == "loaded" and not preview_valid:
        blockers.add("observation_preview_schema_invalid")
    elif preview_valid and not preview_safe:
        blockers.add("observation_preview_unsafe_contract")
    if preview_valid and not preview_ready:
        blockers.add("observation_preview_not_ready")
    if preview_valid and not observation_operational:
        blockers.add("observation_preview_fixture_not_operational")

    auto_location_requested = (
        candidate_source_container_id is None
        and candidate_source_slot_index is None
        and candidate_item_id is not None
    )
    if (
        auto_location_requested
        and preview_valid
        and preview_safe
        and preview_ready
        and preview_fresh
        and observation_operational
        and isinstance(observation, dict)
    ):
        parsed_candidate, candidate_valid = _parse_identifier(candidate_item_id)
        candidates = observation.get("candidates")
        matches = (
            [
                item
                for item in candidates
                if isinstance(item, dict)
                and candidate_valid
                and item.get("item_id") == parsed_candidate
            ]
            if isinstance(candidates, list)
            else []
        )
        if len(matches) == 1:
            candidate_source_container_id = matches[0].get("container_id")
            candidate_source_slot_index = matches[0].get("slot_index")
        elif len(matches) == 0:
            blockers.add("candidate_exact_match_missing")
        else:
            blockers.add("candidate_exact_match_ambiguous")

    raw_identifiers = {
        "equipped_item_id": equipped_item_id,
        "candidate_item_id": candidate_item_id,
        "candidate_source_container_id": candidate_source_container_id,
        "candidate_source_slot_index": candidate_source_slot_index,
    }
    provided = {key: value is not None for key, value in raw_identifiers.items()}
    parsed_pairs = {
        key: _parse_identifier(value) for key, value in raw_identifiers.items()
    }
    identifiers_complete = all(provided.values())
    identifiers_valid = bool(
        identifiers_complete and all(valid for _, valid in parsed_pairs.values())
    )
    parsed_identifiers = {key: parsed for key, (parsed, _) in parsed_pairs.items()}
    if not any(provided.values()):
        blockers.add("explicit_identifiers_missing")
    elif not identifiers_complete:
        blockers.add("explicit_identifiers_incomplete")
    if any(provided.values()) and not all(
        valid for key, (_, valid) in parsed_pairs.items() if provided[key]
    ):
        blockers.add("explicit_identifiers_invalid")

    item_ids_distinct = bool(
        identifiers_valid
        and parsed_identifiers["equipped_item_id"]
        != parsed_identifiers["candidate_item_id"]
    )
    if identifiers_valid and not item_ids_distinct:
        blockers.add("item_ids_not_distinct")

    equipped_item_matches = False
    candidate_match_count = 0
    if identifiers_valid and isinstance(observation, dict):
        ring = observation.get("ring")
        equipped_item_matches = bool(
            isinstance(ring, dict)
            and ring.get("present") is True
            and ring.get("item_id") == parsed_identifiers["equipped_item_id"]
        )
        candidates = observation.get("candidates")
        if isinstance(candidates, list):
            candidate_match_count = sum(
                1
                for item in candidates
                if isinstance(item, dict)
                and item.get("item_id") == parsed_identifiers["candidate_item_id"]
                and item.get("container_id")
                == parsed_identifiers["candidate_source_container_id"]
                and item.get("slot_index")
                == parsed_identifiers["candidate_source_slot_index"]
            )
        if not equipped_item_matches:
            blockers.add("equipped_item_preview_mismatch")
        if candidate_match_count == 0:
            blockers.add("candidate_exact_match_missing")
        elif candidate_match_count > 1:
            blockers.add("candidate_exact_match_ambiguous")

    confirmation_provided = confirmation is not None
    confirmation_matched = confirmation == EXACT_CONFIRMATION
    if not confirmation_provided:
        blockers.add("operator_confirmation_missing")
    elif not confirmation_matched:
        blockers.add("operator_confirmation_mismatch")
    confirmation_sha256 = (
        hashlib.sha256(EXACT_CONFIRMATION.encode("utf-8")).hexdigest()
        if confirmation_matched
        else None
    )

    doctor_profile_sha256 = (
        doctor_payload.get("sha256")
        if doctor_valid and isinstance(doctor_payload, dict)
        else None
    )
    observation_sha256 = (
        preview_payload.get("observation_sha256")
        if preview_valid and isinstance(preview_payload, dict)
        else None
    )
    requested_for_report = {
        key: value if valid else None for key, (value, valid) in parsed_pairs.items()
    }
    input_binding = {
        "capture_doctor": inputs.capture_doctor.sha256,
        "capture_profile": doctor_profile_sha256,
        "observation_preview": inputs.observation_preview.sha256,
        "observation": observation_sha256,
        "requested_identifiers": requested_for_report,
        "operator_confirmation_sha256": confirmation_sha256,
    }
    input_binding_sha256 = documents.canonical_sha256(input_binding)

    ordered = _ordered(blockers)
    plan: dict[str, Any] | None = None
    plan_sha256: str | None = None
    if not ordered:
        exact_identifiers = {
            key: value for key, value in parsed_identifiers.items() if value is not None
        }
        proposed_profile = _proposed_profile(exact_identifiers)
        proposed_sha256 = documents.canonical_sha256(proposed_profile)
        plan = {
            "plan_id": f"equipment-capture-profile-plan-{input_binding_sha256[:16]}",
            "target_profile": TARGET_PROFILE_RELPATH,
            "input_binding_sha256": input_binding_sha256,
            "expected_current_profile_sha256": doctor_profile_sha256,
            "proposed_profile_sha256": proposed_sha256,
            "diff": {
                "operation": "replace_document_after_separate_operator_review",
                "from_sha256": doctor_profile_sha256,
                "to_sha256": proposed_sha256,
                "set": proposed_profile,
            },
        }
        plan_sha256 = documents.canonical_sha256(plan)

    status = "plan_generated" if plan is not None else "blocked"
    return {
        "schema_version": SCHEMA,
        "generated_at_unix_ms": generated_at_unix_ms,
        "status": status,
        "mode": MODE,
        "sources": {
            "capture_doctor": "runtime/solteria_helper_dev/equipment_capture_profile_doctor.json",
            "observation_preview": "runtime/solteria_helper_dev/equipment_observation_preview.json",
            "target_profile": TARGET_PROFILE_RELPATH,
        },
        "input_status": {
            "capture_doctor": {
                "load_status": inputs.capture_doctor.status,
                "schema_valid": doctor_valid,
                "safe_contract": doctor_safe,
            },
            "observation_preview": {
                "load_status": inputs.observation_preview.status,
                "schema_valid": preview_valid,
                "safe_contract": preview_safe,
            },
        },
        "input_sha256": {
            "capture_doctor": inputs.capture_doctor.sha256,
            "capture_profile": doctor_profile_sha256,
            "observation_preview": inputs.observation_preview.sha256,
            "observation": observation_sha256,
        },
        "input_binding_sha256": input_binding_sha256,
        "requested_identifiers": requested_for_report,
        "operator_confirmation": {
            "required": True,
            "provided": confirmation_provided,
            "matched": confirmation_matched,
            "confirmation_sha256": confirmation_sha256,
        },
        "checks": {
            "inputs_loaded": all(
                document.status == "loaded"
                for document in (
                    inputs.capture_doctor,
                    inputs.observation_preview,
                )
            ),
            "capture_doctor_schema_valid": doctor_valid,
            "capture_doctor_no_action": doctor_safe,
            "capture_doctor_profile_valid": doctor_profile_valid,
            "capture_doctor_local_override": doctor_local,
            "observation_preview_schema_valid": preview_valid,
            "observation_preview_no_action": preview_safe,
            "observation_preview_ready": preview_ready,
            "observation_preview_fresh": preview_fresh,
            "observation_operational": observation_operational,
            "identifiers_complete": identifiers_complete,
            "identifiers_valid": identifiers_valid,
            "item_ids_distinct": item_ids_distinct,
            "equipped_item_exact_match_in_preview": equipped_item_matches,
            "candidate_exact_match_in_preview": candidate_match_count == 1,
            "operator_confirmation_matched": confirmation_matched,
        },
        "observation_age_ms": observation_age_ms,
        "blockers": ordered,
        "plan": plan,
        "plan_sha256": plan_sha256,
        "explanation": (
            "Data-only profile change plan generated for separate operator review; nothing was applied."
            if plan is not None
            else "No profile change plan was generated; inspect blockers and provide exact item IDs plus the exact confirmation. Candidate container and slot are auto-resolved only from one fresh operational match."
        ),
        "operator_review_required": True,
        "acceptance_granted": False,
        "runtime_readiness_claimed": False,
        "eligibility_changed": False,
        "profile_write_performed": False,
        "repo_report_write_only": True,
        "live_file_writes": False,
        "interaction_contract": dict(INTERACTION_CONTRACT),
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


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
                handle.write(documents.canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        metadata = temporary.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("temporary output identity invalid")
        _validate_output(DEFAULT_OUTPUT)
        temporary.replace(output)
        persisted = documents.read_document(output, MAX_INPUT_BYTES)
        if (
            persisted.status != "loaded"
            or persisted.sha256 != documents.canonical_sha256(payload)
        ):
            raise ValueError("persisted profile change plan verification failed")
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipped-item-id")
    parser.add_argument("--candidate-item-id")
    parser.add_argument("--candidate-container-id")
    parser.add_argument("--candidate-slot-index")
    parser.add_argument("--confirm")
    parser.add_argument(
        "--refresh-preview",
        action="store_true",
        help=(
            "rebuild the fixed passive Equipment preview from canonical "
            "BackgroundNoScreen evidence in the same process before planning"
        ),
    )
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return success after emitting an explanatory blocked report",
    )
    args = parser.parse_args(argv)
    generated_at_unix_ms = int(time.time() * 1000)
    inputs = read_canonical_inputs()
    if args.refresh_preview:
        refreshed_preview = preview.build_preview(
            background=preview._read_background(),
            generated_at_unix_ms=generated_at_unix_ms,
        )
        if not args.no_write:
            preview._write_atomic(
                preview.DEFAULT_OUTPUT,
                preview.DEFAULT_OUTPUT,
                refreshed_preview,
            )
        inputs = CanonicalInputs(
            capture_doctor=inputs.capture_doctor,
            observation_preview=documents.document_from_payload(refreshed_preview),
        )
    report = evaluate_change_plan(
        inputs,
        equipped_item_id=args.equipped_item_id,
        candidate_item_id=args.candidate_item_id,
        candidate_source_container_id=args.candidate_container_id,
        candidate_source_slot_index=args.candidate_slot_index,
        confirmation=args.confirm,
        generated_at_unix_ms=generated_at_unix_ms,
    )
    if not args.no_write:
        write_report(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"P10 capture-profile change plan: {report['status']}", file=sys.stderr)
    return 0 if report["status"] == "plan_generated" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
