#!/usr/bin/env python3
"""Run the P9 Conditions decision lane entirely offline and fail closed.

The tool consumes bounded data-only evidence.  It never launches, focuses,
captures, configures, or writes to an OTClient installation, and every result
is an advisory shadow decision with all execution flags disabled.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from .otclient_headless_evidence import read_bytes_bounded
else:
    from otclient_headless_evidence import read_bytes_bounded


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEFAULT_DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_PROFILE = ROOT / "config" / "otclient" / "conditions-shadow-profile.json"
DEFAULT_P8_PROOF = DEFAULT_DEV_DIR / "background_status.json"
DEFAULT_RECOVERY_TRACE = DEFAULT_DEV_DIR / "recovery_bridge_trace.json"
DEFAULT_RECOVERY_PROOF = DEFAULT_DEV_DIR / "conditions_recovery_proof.json"
DEFAULT_SCENARIO_PACK = (
    ROOT / "tests" / "fixtures" / "otclient_conditions_shadow_replay" / "scenarios.json"
)
DEFAULT_OUTPUT = DEFAULT_DEV_DIR / "conditions_shadow_replay.json"
FIXTURE_DIR = DEFAULT_SCENARIO_PACK.parent

PROFILE_SCHEMA = "ctoa.conditions-shadow-profile.v1"
OBSERVATION_SCHEMA = "ctoa.conditions-observation.v1"
P8_PROOF_SCHEMA = "ctoa.p8-operational-proof.v1"
P8_BACKGROUND_SCHEMA = "ctoa.otclient-headless-status.v1"
RECOVERY_TRACE_SCHEMA = "ctoa.recovery-bridge-trace.v1"
RECOVERY_PROOF_SCHEMA = "ctoa.conditions-recovery-proof.v1"
TRACE_SCHEMA = "ctoa.conditions-shadow-trace.v1"
REPORT_SCHEMA = "ctoa.conditions-shadow-replay-report.v1"
SCENARIO_SCHEMA = "ctoa.conditions-shadow-scenario-pack.v1"
INPUT_SCHEMA = "ctoa.conditions-shadow-input.v1"

MAX_INPUT_BYTES = 64 * 1024
MAX_SCENARIO_BYTES = 256 * 1024
MAX_P8_AGE_MS = 30_000
MAX_RECOVERY_AGE_MS = 30_000
ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
OBSERVATION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

ACTION = "plan_paralyze_recovery"
CONDITION = "paralyze"
SPELL = "exura"
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)

PROFILE_KEYS = {
    "schema_version",
    "mode",
    "action",
    "condition",
    "spell",
    "max_observation_age_ms",
    "cooldown_required",
    "retry_budget",
    "requires_p8_ready",
    "requires_recovery_trace",
    *FALSE_FLAGS,
}
OBSERVATION_KEYS = {
    "schema_version",
    "observed_at_unix_ms",
    "observation_id",
    "online",
    "alive",
    "protection_zone",
    "protection_zone_source",
    "condition_id",
    "condition_state",
    "cooldown",
    "cooldown_source",
    "producer_source",
    *FALSE_FLAGS,
}
OBSERVATION_ENVELOPE_KEYS = {
    *OBSERVATION_KEYS,
    "status",
    "present",
    "valid",
    "validation_errors",
    "p9_blocker",
}
P8_PROOF_KEYS = {
    "schema_version",
    "proof_id",
    "observed_at_unix_ms",
    "status",
    "source",
    "background_status_sha256",
    "live_manifest_sha256",
    "helper_version",
    "conditions_observation_sha256",
    "contract_valid",
    "trusted_live_manifest_pin",
    "live_manifest_parity",
    "live_files_unchanged",
    "exact_active_client_process",
    "fresh_online_heartbeat",
    "helper_version_match",
    "capability_fail_closed",
    "client_process_stable",
    "screenshot_count_stable",
    "no_screen_contract",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}
RECOVERY_TRACE_KEYS = {
    "schema_version",
    "trace_id",
    "observed_at_unix_ms",
    "source",
    "status",
    "decision",
    "guard",
    "action",
    "result",
    "blockers",
    "dry_run",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}
RECOVERY_PROOF_KEYS = {
    "schema_version",
    "proof_id",
    "observed_at_unix_ms",
    "status",
    "source",
    "action",
    "condition",
    "spell",
    "recovery_trace_sha256",
    "profile_sha256",
    "observation_sha256",
    "p8_proof_sha256",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}

BLOCKER_ORDER = (
    "profile_missing",
    "profile_malformed",
    "profile_duplicate_keys",
    "profile_oversize",
    "profile_symlink_rejected",
    "profile_not_regular",
    "profile_unreadable",
    "profile_schema_invalid",
    "profile_action_mismatch",
    "profile_condition_mismatch",
    "profile_spell_mismatch",
    "profile_cooldown_policy_invalid",
    "profile_retry_budget_nonzero",
    "profile_p8_proof_not_required",
    "profile_recovery_proof_not_required",
    "profile_unsafe_contract",
    "observation_missing",
    "observation_malformed",
    "observation_duplicate_keys",
    "observation_oversize",
    "observation_symlink_rejected",
    "observation_not_regular",
    "observation_unreadable",
    "observation_envelope_invalid",
    "observation_schema_invalid",
    "observation_future",
    "observation_stale",
    "player_offline",
    "player_online_unknown",
    "player_dead",
    "player_life_unknown",
    "protection_zone_inside",
    "protection_zone_unknown",
    "protection_zone_source_untrusted",
    "condition_mismatch",
    "condition_absent",
    "condition_unknown",
    "cooldown_active",
    "cooldown_unknown",
    "cooldown_source_untrusted",
    "observation_unsafe_contract",
    "p8_missing",
    "p8_malformed",
    "p8_duplicate_keys",
    "p8_oversize",
    "p8_symlink_rejected",
    "p8_not_regular",
    "p8_unreadable",
    "p8_schema_invalid",
    "p8_future",
    "p8_stale",
    "p8_observation_hash_mismatch",
    "p8_operational_acceptance_blocked",
    "p8_unsafe_contract",
    "recovery_trace_missing",
    "recovery_trace_malformed",
    "recovery_trace_duplicate_keys",
    "recovery_trace_oversize",
    "recovery_trace_symlink_rejected",
    "recovery_trace_not_regular",
    "recovery_trace_unreadable",
    "recovery_trace_schema_invalid",
    "recovery_trace_future",
    "recovery_trace_stale",
    "recovery_trace_status_blocked",
    "recovery_trace_action_mismatch",
    "recovery_trace_unsafe_contract",
    "recovery_missing",
    "recovery_malformed",
    "recovery_duplicate_keys",
    "recovery_oversize",
    "recovery_symlink_rejected",
    "recovery_not_regular",
    "recovery_unreadable",
    "recovery_schema_invalid",
    "recovery_future",
    "recovery_stale",
    "recovery_status_blocked",
    "recovery_action_mismatch",
    "recovery_condition_mismatch",
    "recovery_spell_mismatch",
    "recovery_trace_hash_mismatch",
    "recovery_profile_hash_mismatch",
    "recovery_observation_hash_mismatch",
    "recovery_p8_hash_mismatch",
    "recovery_unsafe_contract",
    "fixture_observation_not_operational",
    "fixture_p8_proof_not_operational",
    "fixture_recovery_trace_not_operational",
    "fixture_recovery_proof_not_operational",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}


class DuplicateKeyError(ValueError):
    """Raised when strict JSON parsing sees a duplicate object key."""


@dataclass(frozen=True)
class InputDocument:
    payload: dict[str, Any] | None
    status: str
    sha256: str


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _invalid_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _json_shape_within_bounds(
    value: Any, *, max_depth: int = 64, max_nodes: int = 50_000
) -> bool:
    stack: list[tuple[Any, int]] = [(value, 0)]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if depth > max_depth or visited > max_nodes:
            return False
        if isinstance(current, dict):
            stack.extend((nested, depth + 1) for nested in current.values())
        elif isinstance(current, list):
            stack.extend((nested, depth + 1) for nested in current)
    return True


def read_document(path: Path, max_bytes: int = MAX_INPUT_BYTES) -> InputDocument:
    raw, status = read_bytes_bounded(path, max_bytes)
    if raw is None:
        return InputDocument(None, status, canonical_sha256({"load_status": status}))
    raw_hash = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_invalid_constant,
            parse_float=_parse_finite_float,
        )
    except DuplicateKeyError:
        return InputDocument(None, "duplicate_keys", raw_hash)
    except (UnicodeError, ValueError, RecursionError):
        return InputDocument(None, "malformed", raw_hash)
    if not isinstance(payload, dict):
        return InputDocument(None, "not_object", raw_hash)
    if not _json_shape_within_bounds(payload):
        return InputDocument(None, "malformed", raw_hash)
    return InputDocument(payload, "loaded", canonical_sha256(payload))


def document_from_payload(
    payload: dict[str, Any] | None,
    status: str = "loaded",
) -> InputDocument:
    if payload is None:
        return InputDocument(None, status, canonical_sha256({"load_status": status}))
    if not _json_shape_within_bounds(payload):
        return InputDocument(
            None, "malformed", canonical_sha256({"load_status": "malformed"})
        )
    return InputDocument(payload, status, canonical_sha256(payload))


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_allowed_string(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _exact_keys(payload: dict[str, Any], expected: set[str]) -> bool:
    return set(payload) == expected


def _false_flags(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in FALSE_FLAGS)


def _empty_ledger(payload: dict[str, Any]) -> bool:
    return payload.get("intrusive_actions_performed") == []


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and ID_RE.fullmatch(value) is not None


def _load_blocker(prefix: str, status: str) -> str | None:
    mapped = {
        "missing": "missing",
        "malformed": "malformed",
        "duplicate_keys": "duplicate_keys",
        "oversize": "oversize",
        "symlink_rejected": "symlink_rejected",
        "not_regular": "not_regular",
        "not_object": "schema_invalid",
        "empty": "malformed",
        "unreadable": "unreadable",
        "changed_during_open": "unreadable",
        "invalid_envelope": "envelope_invalid",
    }.get(status)
    return f"{prefix}_{mapped}" if mapped else None


def _profile_structurally_valid(payload: dict[str, Any]) -> bool:
    return bool(
        _exact_keys(payload, PROFILE_KEYS)
        and payload.get("schema_version") == PROFILE_SCHEMA
        and isinstance(payload.get("mode"), str)
        and isinstance(payload.get("action"), str)
        and isinstance(payload.get("condition"), str)
        and isinstance(payload.get("spell"), str)
        and _is_int(payload.get("max_observation_age_ms"))
        and _is_int(payload.get("retry_budget"))
        and isinstance(payload.get("cooldown_required"), str)
        and isinstance(payload.get("requires_p8_ready"), bool)
        and isinstance(payload.get("requires_recovery_trace"), bool)
        and all(isinstance(payload.get(key), bool) for key in FALSE_FLAGS)
    )


def _observation_structurally_valid(payload: dict[str, Any]) -> bool:
    return bool(
        _exact_keys(payload, OBSERVATION_KEYS)
        and payload.get("schema_version") == OBSERVATION_SCHEMA
        and _is_int(payload.get("observed_at_unix_ms"))
        and 1 <= payload["observed_at_unix_ms"] <= 9_999_999_999_999
        and isinstance(payload.get("observation_id"), str)
        and OBSERVATION_ID_RE.fullmatch(payload["observation_id"]) is not None
        and _is_allowed_string(payload.get("online"), {"online", "offline", "unknown"})
        and _is_allowed_string(payload.get("alive"), {"alive", "dead", "unknown"})
        and _is_allowed_string(
            payload.get("protection_zone"), {"outside", "inside", "unknown"}
        )
        and _is_allowed_string(
            payload.get("protection_zone_source"), {"player_method", "unavailable"}
        )
        and isinstance(payload.get("condition_id"), str)
        and _is_allowed_string(
            payload.get("condition_state"), {"present", "absent", "unknown"}
        )
        and _is_allowed_string(payload.get("cooldown"), {"ready", "active", "unknown"})
        and _is_allowed_string(
            payload.get("cooldown_source"),
            {"game_cooldown_group", "unavailable"},
        )
        and _is_allowed_string(
            payload.get("producer_source"),
            {"otclient_guarded_adapter", "fixture"},
        )
        and all(isinstance(payload.get(key), bool) for key in FALSE_FLAGS)
    )


def _p8_structurally_valid(payload: dict[str, Any]) -> bool:
    boolean_keys = P8_PROOF_KEYS - {
        "schema_version",
        "proof_id",
        "observed_at_unix_ms",
        "status",
        "source",
        "background_status_sha256",
        "live_manifest_sha256",
        "helper_version",
        "conditions_observation_sha256",
        "intrusive_actions_performed",
    }
    return bool(
        _exact_keys(payload, P8_PROOF_KEYS)
        and payload.get("schema_version") == P8_PROOF_SCHEMA
        and _valid_id(payload.get("proof_id"))
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload["observed_at_unix_ms"] > 0
        and _is_allowed_string(payload.get("status"), {"ready", "blocked", "unknown"})
        and _is_allowed_string(
            payload.get("source"), {"background_no_screen", "fixture"}
        )
        and _valid_sha(payload.get("background_status_sha256"))
        and _valid_sha(payload.get("live_manifest_sha256"))
        and isinstance(payload.get("helper_version"), str)
        and 0 < len(payload["helper_version"]) <= 32
        and _valid_sha(payload.get("conditions_observation_sha256"))
        and all(isinstance(payload.get(key), bool) for key in boolean_keys)
        and isinstance(payload.get("intrusive_actions_performed"), list)
    )


def _recovery_trace_structurally_valid(payload: dict[str, Any]) -> bool:
    blockers = payload.get("blockers")
    return bool(
        _exact_keys(payload, RECOVERY_TRACE_KEYS)
        and payload.get("schema_version") == RECOVERY_TRACE_SCHEMA
        and _valid_id(payload.get("trace_id"))
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload["observed_at_unix_ms"] > 0
        and _is_allowed_string(payload.get("source"), {"recovery_shadow", "fixture"})
        and _is_allowed_string(payload.get("status"), {"ready", "blocked", "unknown"})
        and _is_allowed_string(payload.get("decision"), {"plan_heal", "hold"})
        and _is_allowed_string(payload.get("guard"), {"passed", "blocked"})
        and _is_allowed_string(payload.get("action"), {"exura", "other"})
        and payload.get("result") == "dry_run"
        and isinstance(blockers, list)
        and len(blockers) <= 16
        and all(isinstance(item, str) and 0 < len(item) <= 64 for item in blockers)
        and payload.get("dry_run") is True
        and all(isinstance(payload.get(key), bool) for key in FALSE_FLAGS)
        and isinstance(payload.get("intrusive_actions_performed"), list)
    )


def _recovery_proof_structurally_valid(payload: dict[str, Any]) -> bool:
    return bool(
        _exact_keys(payload, RECOVERY_PROOF_KEYS)
        and payload.get("schema_version") == RECOVERY_PROOF_SCHEMA
        and _valid_id(payload.get("proof_id"))
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload["observed_at_unix_ms"] > 0
        and _is_allowed_string(payload.get("status"), {"ready", "blocked", "unknown"})
        and _is_allowed_string(payload.get("source"), {"recovery_shadow", "fixture"})
        and isinstance(payload.get("action"), str)
        and isinstance(payload.get("condition"), str)
        and isinstance(payload.get("spell"), str)
        and all(
            _valid_sha(payload.get(key))
            for key in (
                "recovery_trace_sha256",
                "profile_sha256",
                "observation_sha256",
                "p8_proof_sha256",
            )
        )
        and all(isinstance(payload.get(key), bool) for key in FALSE_FLAGS)
        and isinstance(payload.get("intrusive_actions_performed"), list)
    )


def _iso_to_unix_ms(value: Any) -> int:
    if not isinstance(value, str) or not value:
        return 0
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        return 0
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def extract_embedded_observation(p8_document: InputDocument) -> InputDocument:
    """Project the exact raw observation from the strict sanitizer envelope."""

    payload = p8_document.payload
    if not isinstance(payload, dict):
        return document_from_payload(None, "missing")
    capability = payload.get("capability")
    nested = (
        capability.get("conditions_observation")
        if isinstance(capability, dict)
        else None
    )
    top_level = payload.get("conditions_observation")
    if nested is not None and top_level is not None:
        return document_from_payload(None, "invalid_envelope")
    envelope = nested if nested is not None else top_level
    if envelope is None:
        return document_from_payload(None, "missing")
    if not isinstance(envelope, dict) or not _exact_keys(
        envelope, OBSERVATION_ENVELOPE_KEYS
    ):
        return document_from_payload(None, "invalid_envelope")

    status = envelope.get("status")
    present = envelope.get("present")
    valid = envelope.get("valid")
    errors = envelope.get("validation_errors")
    p9_blocker = envelope.get("p9_blocker")
    metadata_valid = bool(
        _is_allowed_string(status, {"valid", "missing", "invalid"})
        and isinstance(present, bool)
        and isinstance(valid, bool)
        and isinstance(errors, list)
        and len(errors) <= 32
        and all(isinstance(item, str) and 0 < len(item) <= 64 for item in errors)
        and (p9_blocker is None or isinstance(p9_blocker, str))
    )
    if not metadata_valid:
        return document_from_payload(None, "invalid_envelope")
    if status == "missing" and present is False and valid is False:
        return document_from_payload(None, "missing")
    if not (
        status == "valid"
        and present is True
        and valid is True
        and errors == []
        and p9_blocker is None
    ):
        return document_from_payload(None, "invalid_envelope")
    projected = {key: envelope[key] for key in OBSERVATION_KEYS}
    return document_from_payload(projected)


def _raw_p8_no_action_contract(payload: dict[str, Any]) -> bool:
    interaction = payload.get("interaction_contract")
    wrapper = payload.get("wrapper_invariants")
    checks = payload.get("checks")
    capability = payload.get("capability")
    expected_interaction = {
        "gui_automation": False,
        "mouse_keyboard_input": False,
        "window_focus": False,
        "screenshot_capture": False,
        "client_launch": False,
        "client_stop": False,
        "live_file_writes": False,
        "passive_reads_only": True,
        "evidence_write_scope": "runtime/solteria_helper_dev",
    }
    optional_action_flags_safe = all(
        key not in payload or payload.get(key) is False
        for key in ("executes_plan", "execute_once_allowed")
    )
    return bool(
        payload.get("mode") == "background_no_screen"
        and payload.get("advisory_only") is True
        and payload.get("safe_to_run_while_playing") is True
        and payload.get("dispatch_allowed") is False
        and payload.get("runtime_actions") is False
        and payload.get("promotion_allowed") is False
        and optional_action_flags_safe
        and payload.get("intrusive_actions_performed") == []
        and interaction == expected_interaction
        and isinstance(wrapper, dict)
        and set(wrapper) == {"client_process_stable", "screenshot_count_stable"}
        and wrapper.get("client_process_stable") is True
        and wrapper.get("screenshot_count_stable") is True
        and isinstance(checks, dict)
        and checks.get("no_screen_contract") is True
        and checks.get("client_process_stable_during_wrapper") is True
        and checks.get("screenshot_count_stable_during_wrapper") is True
        and isinstance(capability, dict)
        and capability.get("runtime_actions") is False
        and capability.get("runtime_core_actions") is False
    )


def normalize_p8_proof(
    raw_document: InputDocument,
    observation_document: InputDocument,
) -> InputDocument:
    """Normalize a raw P8 wrapper artifact into the strict hash-bound proof."""

    if raw_document.status != "loaded" or raw_document.payload is None:
        return raw_document
    raw = raw_document.payload
    if raw.get("schema_version") == P8_PROOF_SCHEMA:
        return raw_document
    if raw.get("schema_version") != P8_BACKGROUND_SCHEMA:
        return document_from_payload(raw, "loaded")

    checks = raw.get("checks") if isinstance(raw.get("checks"), dict) else {}
    integrity = raw.get("integrity") if isinstance(raw.get("integrity"), dict) else {}
    capability = (
        raw.get("capability") if isinstance(raw.get("capability"), dict) else {}
    )
    wrapper = (
        raw.get("wrapper_invariants")
        if isinstance(raw.get("wrapper_invariants"), dict)
        else {}
    )
    manifest_sha = integrity.get("manifest_sha256")
    if not _valid_sha(manifest_sha):
        manifest_sha = ZERO_SHA256
    helper_version = integrity.get("helper_version") or capability.get("helper_version")
    if not isinstance(helper_version, str) or not 0 < len(helper_version) <= 32:
        helper_version = "unknown"
    observation_sha = (
        observation_document.sha256
        if observation_document.status == "loaded"
        else ZERO_SHA256
    )
    normalized = {
        "schema_version": P8_PROOF_SCHEMA,
        "proof_id": "p8-background-status",
        "observed_at_unix_ms": _iso_to_unix_ms(raw.get("generated_at_utc")),
        "status": raw.get("status")
        if _is_allowed_string(raw.get("status"), {"ready", "blocked"})
        else "unknown",
        "source": "background_no_screen",
        "background_status_sha256": raw_document.sha256,
        "live_manifest_sha256": manifest_sha,
        "helper_version": helper_version,
        "conditions_observation_sha256": observation_sha,
        "contract_valid": _raw_p8_no_action_contract(raw),
        "trusted_live_manifest_pin": checks.get("trusted_live_manifest_pin") is True,
        "live_manifest_parity": checks.get("live_manifest_parity") is True,
        "live_files_unchanged": checks.get("live_files_unchanged") is True,
        "exact_active_client_process": checks.get("exact_active_client_process")
        is True,
        "fresh_online_heartbeat": checks.get("fresh_online_heartbeat") is True,
        "helper_version_match": checks.get("helper_version_match") is True,
        "capability_fail_closed": checks.get("capability_fail_closed") is True,
        "client_process_stable": wrapper.get("client_process_stable") is True,
        "screenshot_count_stable": wrapper.get("screenshot_count_stable") is True,
        "no_screen_contract": checks.get("no_screen_contract") is True,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "intrusive_actions_performed": [],
    }
    return document_from_payload(normalized)


def _age_ms(timestamp: Any, evaluated_at_unix_ms: int) -> int | None:
    if not _is_int(timestamp) or timestamp <= 0:
        return None
    return evaluated_at_unix_ms - timestamp


def _sort_blockers(blockers: Iterable[str]) -> list[str]:
    unique = set(blockers)
    unknown = unique - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown blockers: {sorted(unknown)}")
    return sorted(unique, key=BLOCKER_RANK.__getitem__)


def _add_document_load_blocker(
    blockers: set[str], prefix: str, document: InputDocument
) -> bool:
    if document.status == "loaded" and document.payload is not None:
        return True
    blocker = _load_blocker(prefix, document.status) or f"{prefix}_unreadable"
    blockers.add(blocker)
    return False


def _p8_acceptance_ready(payload: dict[str, Any]) -> bool:
    required_true = (
        "contract_valid",
        "trusted_live_manifest_pin",
        "live_manifest_parity",
        "live_files_unchanged",
        "exact_active_client_process",
        "fresh_online_heartbeat",
        "helper_version_match",
        "capability_fail_closed",
        "client_process_stable",
        "screenshot_count_stable",
        "no_screen_contract",
    )
    return bool(
        payload.get("status") == "ready"
        and all(payload.get(key) is True for key in required_true)
        and all(
            payload.get(key) != ZERO_SHA256
            for key in (
                "background_status_sha256",
                "live_manifest_sha256",
                "conditions_observation_sha256",
            )
        )
        and _false_flags(payload)
        and _empty_ledger(payload)
    )


def evaluate_shadow(
    *,
    profile_document: InputDocument,
    observation_document: InputDocument,
    p8_document: InputDocument,
    recovery_trace_document: InputDocument,
    recovery_proof_document: InputDocument,
    evaluated_at_unix_ms: int,
    source: str,
) -> dict[str, Any]:
    """Return one deterministic no-action trace from already bounded inputs."""

    if not _is_allowed_string(source, {"operational", "fixture"}):
        raise ValueError("source must be operational or fixture")
    if not _is_int(evaluated_at_unix_ms) or evaluated_at_unix_ms <= 0:
        raise ValueError("evaluated_at_unix_ms must be a positive integer")

    blockers: set[str] = set()
    profile = profile_document.payload
    observation = observation_document.payload
    p8 = p8_document.payload
    recovery_trace = recovery_trace_document.payload
    recovery = recovery_proof_document.payload

    profile_valid = _add_document_load_blocker(blockers, "profile", profile_document)
    if profile_valid and profile is not None:
        profile_valid = _profile_structurally_valid(profile)
        if not profile_valid:
            blockers.add("profile_schema_invalid")
        else:
            if profile.get("action") != ACTION:
                blockers.add("profile_action_mismatch")
            if profile.get("condition") != CONDITION:
                blockers.add("profile_condition_mismatch")
            if profile.get("spell") != SPELL:
                blockers.add("profile_spell_mismatch")
            if (
                profile.get("mode") != "shadow_only"
                or profile.get("max_observation_age_ms") != 6000
                or profile.get("cooldown_required") != "ready"
            ):
                blockers.add("profile_cooldown_policy_invalid")
            if profile.get("retry_budget") != 0:
                blockers.add("profile_retry_budget_nonzero")
            if profile.get("requires_p8_ready") is not True:
                blockers.add("profile_p8_proof_not_required")
            if profile.get("requires_recovery_trace") is not True:
                blockers.add("profile_recovery_proof_not_required")
            if not _false_flags(profile):
                blockers.add("profile_unsafe_contract")

    observation_valid = _add_document_load_blocker(
        blockers, "observation", observation_document
    )
    observation_age = None
    if observation_valid and observation is not None:
        observation_valid = _observation_structurally_valid(observation)
        if not observation_valid:
            blockers.add("observation_schema_invalid")
        else:
            observation_age = _age_ms(
                observation.get("observed_at_unix_ms"), evaluated_at_unix_ms
            )
            max_age = (
                profile.get("max_observation_age_ms", 6000)
                if profile_valid and profile is not None
                else 6000
            )
            if observation_age is not None and observation_age < 0:
                blockers.add("observation_future")
            elif observation_age is None or observation_age > max_age:
                blockers.add("observation_stale")
            if observation.get("online") == "offline":
                blockers.add("player_offline")
            elif observation.get("online") == "unknown":
                blockers.add("player_online_unknown")
            if observation.get("alive") == "dead":
                blockers.add("player_dead")
            elif observation.get("alive") == "unknown":
                blockers.add("player_life_unknown")
            if observation.get("protection_zone") == "inside":
                blockers.add("protection_zone_inside")
            elif observation.get("protection_zone") == "unknown":
                blockers.add("protection_zone_unknown")
            elif observation.get("protection_zone_source") != "player_method":
                blockers.add("protection_zone_source_untrusted")
            if observation.get("condition_id") != CONDITION:
                blockers.add("condition_mismatch")
            if observation.get("condition_state") == "absent":
                blockers.add("condition_absent")
            elif observation.get("condition_state") == "unknown":
                blockers.add("condition_unknown")
            if observation.get("cooldown") == "active":
                blockers.add("cooldown_active")
            elif observation.get("cooldown") == "unknown":
                blockers.add("cooldown_unknown")
            elif observation.get("cooldown_source") != "game_cooldown_group":
                blockers.add("cooldown_source_untrusted")
            if not _false_flags(observation):
                blockers.add("observation_unsafe_contract")
            if source == "operational" and observation.get("producer_source") != (
                "otclient_guarded_adapter"
            ):
                blockers.add("fixture_observation_not_operational")

    p8_valid = _add_document_load_blocker(blockers, "p8", p8_document)
    p8_age = None
    if p8_valid and p8 is not None:
        p8_valid = _p8_structurally_valid(p8)
        if not p8_valid:
            blockers.add("p8_schema_invalid")
        else:
            p8_age = _age_ms(p8.get("observed_at_unix_ms"), evaluated_at_unix_ms)
            if p8_age is not None and p8_age < 0:
                blockers.add("p8_future")
            elif p8_age is None or p8_age > MAX_P8_AGE_MS:
                blockers.add("p8_stale")
            if (
                observation_valid
                and p8.get("conditions_observation_sha256")
                != observation_document.sha256
            ):
                blockers.add("p8_observation_hash_mismatch")
            if not _p8_acceptance_ready(p8):
                blockers.add("p8_operational_acceptance_blocked")
            if not _false_flags(p8) or not _empty_ledger(p8):
                blockers.add("p8_unsafe_contract")
            if source == "operational" and p8.get("source") != ("background_no_screen"):
                blockers.add("fixture_p8_proof_not_operational")

    trace_valid = _add_document_load_blocker(
        blockers, "recovery_trace", recovery_trace_document
    )
    recovery_trace_age = None
    if trace_valid and recovery_trace is not None:
        trace_valid = _recovery_trace_structurally_valid(recovery_trace)
        if not trace_valid:
            blockers.add("recovery_trace_schema_invalid")
        else:
            recovery_trace_age = _age_ms(
                recovery_trace.get("observed_at_unix_ms"), evaluated_at_unix_ms
            )
            if recovery_trace_age is not None and recovery_trace_age < 0:
                blockers.add("recovery_trace_future")
            elif recovery_trace_age is None or recovery_trace_age > MAX_RECOVERY_AGE_MS:
                blockers.add("recovery_trace_stale")
            if (
                recovery_trace.get("status") != "ready"
                or recovery_trace.get("guard") != "passed"
                or recovery_trace.get("decision") != "plan_heal"
                or recovery_trace.get("blockers") != []
            ):
                blockers.add("recovery_trace_status_blocked")
            if recovery_trace.get("action") != SPELL:
                blockers.add("recovery_trace_action_mismatch")
            if (
                not _false_flags(recovery_trace)
                or not _empty_ledger(recovery_trace)
                or recovery_trace.get("dry_run") is not True
                or recovery_trace.get("result") != "dry_run"
            ):
                blockers.add("recovery_trace_unsafe_contract")
            if source == "operational" and recovery_trace.get("source") != (
                "recovery_shadow"
            ):
                blockers.add("fixture_recovery_trace_not_operational")

    recovery_valid = _add_document_load_blocker(
        blockers, "recovery", recovery_proof_document
    )
    recovery_age = None
    if recovery_valid and recovery is not None:
        recovery_valid = _recovery_proof_structurally_valid(recovery)
        if not recovery_valid:
            blockers.add("recovery_schema_invalid")
        else:
            recovery_age = _age_ms(
                recovery.get("observed_at_unix_ms"), evaluated_at_unix_ms
            )
            if recovery_age is not None and recovery_age < 0:
                blockers.add("recovery_future")
            elif recovery_age is None or recovery_age > MAX_RECOVERY_AGE_MS:
                blockers.add("recovery_stale")
            if recovery.get("status") != "ready":
                blockers.add("recovery_status_blocked")
            if recovery.get("action") != ACTION:
                blockers.add("recovery_action_mismatch")
            if recovery.get("condition") != CONDITION:
                blockers.add("recovery_condition_mismatch")
            if recovery.get("spell") != SPELL:
                blockers.add("recovery_spell_mismatch")
            if trace_valid and recovery.get("recovery_trace_sha256") != (
                recovery_trace_document.sha256
            ):
                blockers.add("recovery_trace_hash_mismatch")
            if profile_valid and recovery.get("profile_sha256") != (
                profile_document.sha256
            ):
                blockers.add("recovery_profile_hash_mismatch")
            if observation_valid and recovery.get("observation_sha256") != (
                observation_document.sha256
            ):
                blockers.add("recovery_observation_hash_mismatch")
            if p8_valid and recovery.get("p8_proof_sha256") != p8_document.sha256:
                blockers.add("recovery_p8_hash_mismatch")
            if not _false_flags(recovery) or not _empty_ledger(recovery):
                blockers.add("recovery_unsafe_contract")
            if source == "operational" and recovery.get("source") != (
                "recovery_shadow"
            ):
                blockers.add("fixture_recovery_proof_not_operational")

    ordered_blockers = _sort_blockers(blockers)
    status = (
        "shadow_plan_ready"
        if not ordered_blockers
        else "operational_acceptance_blocked"
    )
    input_hashes = {
        "profile": profile_document.sha256,
        "observation": observation_document.sha256,
        "p8_proof": p8_document.sha256,
        "recovery_trace": recovery_trace_document.sha256,
        "recovery_proof": recovery_proof_document.sha256,
    }
    canonical_input_sha = canonical_sha256(
        {
            "schema_version": INPUT_SCHEMA,
            "evaluated_at_unix_ms": evaluated_at_unix_ms,
            "input_sha256": input_hashes,
        }
    )
    decision_basis = {
        "schema_version": TRACE_SCHEMA,
        "canonical_input_sha256": canonical_input_sha,
        "status": status,
        "decision": "would_plan_paralyze_recovery" if not ordered_blockers else "hold",
        "action": ACTION,
        "condition": CONDITION,
        "spell": SPELL,
        "observation_age_ms": observation_age,
        "p8_age_ms": p8_age,
        "recovery_trace_age_ms": recovery_trace_age,
        "recovery_age_ms": recovery_age,
        "blockers": ordered_blockers,
        "operator_review_required": True,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    decision_sha = canonical_sha256(decision_basis)
    return {
        "schema_version": TRACE_SCHEMA,
        "trace_id": f"conditions-shadow-{decision_sha[:16]}",
        "source": source,
        "evaluated_at_unix_ms": evaluated_at_unix_ms,
        "mode": "shadow_only",
        "action": ACTION,
        "condition": CONDITION,
        "spell": SPELL,
        "input_sha256": input_hashes,
        "canonical_input_sha256": canonical_input_sha,
        "observation_age_ms": observation_age,
        "p8_age_ms": p8_age,
        "recovery_trace_age_ms": recovery_trace_age,
        "recovery_age_ms": recovery_age,
        "status": status,
        "decision": decision_basis["decision"],
        "blockers": ordered_blockers,
        "decision_sha256": decision_sha,
        "operator_review_required": True,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


SCENARIO_MUTATIONS = {
    "none",
    "profile_wrong_action",
    "profile_wrong_condition",
    "profile_wrong_spell",
    "profile_retry_nonzero",
    "profile_future_version",
    "profile_malformed",
    "profile_duplicate_keys",
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
    "observation_extra_field",
    "observation_unsafe_contract",
    "p8_missing",
    "p8_blocked",
    "p8_stale",
    "p8_future",
    "p8_unsafe_contract",
    "p8_extra_field",
    "recovery_missing",
    "recovery_malformed",
    "recovery_status_blocked",
    "recovery_future",
    "recovery_stale",
    "recovery_wrong_action",
    "recovery_wrong_condition",
    "recovery_wrong_spell",
    "recovery_hash_mismatch",
    "recovery_extra_field",
    "recovery_unsafe_contract",
}


def _scenario_expected_blockers_valid(value: Any) -> bool:
    return bool(
        isinstance(value, list)
        and len(value) <= len(BLOCKER_ORDER)
        and all(isinstance(item, str) and item in BLOCKER_RANK for item in value)
        and len(value) == len(set(value))
        and value == sorted(value, key=BLOCKER_RANK.__getitem__)
    )


def _scenario_pack_valid(payload: dict[str, Any]) -> bool:
    if set(payload) != {
        "schema_version",
        "fixture_only",
        "operational_readiness_claimed",
        "evaluated_at_unix_ms",
        "scenarios",
    }:
        return False
    scenarios = payload.get("scenarios")
    if not (
        payload.get("schema_version") == SCENARIO_SCHEMA
        and payload.get("fixture_only") is True
        and payload.get("operational_readiness_claimed") is False
        and _is_int(payload.get("evaluated_at_unix_ms"))
        and payload["evaluated_at_unix_ms"] > 0
        and isinstance(scenarios, list)
        and 1 <= len(scenarios) <= 128
    ):
        return False
    seen: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {
            "name",
            "mutation",
            "expected_status",
            "expected_blockers",
        }:
            return False
        name = scenario.get("name")
        blockers = scenario.get("expected_blockers")
        if not (
            _valid_id(name)
            and name not in seen
            and _is_allowed_string(scenario.get("mutation"), SCENARIO_MUTATIONS)
            and _is_allowed_string(
                scenario.get("expected_status"),
                {"shadow_plan_ready", "operational_acceptance_blocked"},
            )
            and _scenario_expected_blockers_valid(blockers)
        ):
            return False
        seen.add(name)
    return True


def _fixture_documents() -> tuple[
    InputDocument,
    InputDocument,
    InputDocument,
    InputDocument,
    InputDocument,
]:
    return (
        read_document(DEFAULT_PROFILE),
        read_document(FIXTURE_DIR / "positive-observation.json"),
        read_document(FIXTURE_DIR / "positive-p8-proof.json"),
        read_document(FIXTURE_DIR / "positive-recovery-trace.json"),
        read_document(FIXTURE_DIR / "positive-recovery-proof.json"),
    )


def _scenario_documents(
    mutation: str,
    evaluated_at_unix_ms: int,
) -> tuple[
    InputDocument,
    InputDocument,
    InputDocument,
    InputDocument,
    InputDocument,
]:
    base = _fixture_documents()
    if any(document.status != "loaded" for document in base):
        raise ValueError("positive fixture inputs must load")
    profile = copy.deepcopy(base[0].payload)
    observation = copy.deepcopy(base[1].payload)
    p8 = copy.deepcopy(base[2].payload)
    recovery_trace = copy.deepcopy(base[3].payload)
    recovery = copy.deepcopy(base[4].payload)
    assert profile is not None
    assert observation is not None
    assert p8 is not None
    assert recovery_trace is not None
    assert recovery is not None

    synthetic_status: dict[str, str] = {}
    if mutation == "profile_wrong_action":
        profile["action"] = "other"
    elif mutation == "profile_wrong_condition":
        profile["condition"] = "other"
    elif mutation == "profile_wrong_spell":
        profile["spell"] = "other"
    elif mutation == "profile_retry_nonzero":
        profile["retry_budget"] = 1
    elif mutation == "profile_future_version":
        profile["schema_version"] = "ctoa.conditions-shadow-profile.v2"
    elif mutation == "profile_malformed":
        synthetic_status["profile"] = "malformed"
    elif mutation == "profile_duplicate_keys":
        synthetic_status["profile"] = "duplicate_keys"
    elif mutation == "profile_oversized":
        synthetic_status["profile"] = "oversize"
    elif mutation == "profile_symlinked":
        synthetic_status["profile"] = "symlink_rejected"
    elif mutation == "profile_non_regular":
        synthetic_status["profile"] = "not_regular"
    elif mutation == "profile_extra_field":
        profile["unexpected"] = True
    elif mutation == "observation_stale":
        observation["observed_at_unix_ms"] = evaluated_at_unix_ms - 6001
    elif mutation == "observation_future":
        observation["observed_at_unix_ms"] = evaluated_at_unix_ms + 1
    elif mutation == "player_offline":
        observation["online"] = "offline"
    elif mutation == "player_online_unknown":
        observation["online"] = "unknown"
    elif mutation == "player_dead":
        observation["alive"] = "dead"
    elif mutation == "player_life_unknown":
        observation["alive"] = "unknown"
    elif mutation == "protection_zone_inside":
        observation["protection_zone"] = "inside"
    elif mutation == "protection_zone_unknown":
        observation["protection_zone"] = "unknown"
        observation["protection_zone_source"] = "unavailable"
    elif mutation == "condition_absent":
        observation["condition_state"] = "absent"
    elif mutation == "condition_unknown":
        observation["condition_state"] = "unknown"
    elif mutation == "condition_wrong":
        observation["condition_id"] = "other"
    elif mutation == "cooldown_active":
        observation["cooldown"] = "active"
    elif mutation == "cooldown_unknown":
        observation["cooldown"] = "unknown"
        observation["cooldown_source"] = "unavailable"
    elif mutation == "observation_extra_field":
        observation["unexpected"] = True
    elif mutation == "observation_unsafe_contract":
        observation["dispatch_allowed"] = True
    elif mutation == "p8_missing":
        synthetic_status["p8"] = "missing"
    elif mutation == "p8_blocked":
        p8["status"] = "blocked"
    elif mutation == "p8_stale":
        p8["observed_at_unix_ms"] = evaluated_at_unix_ms - MAX_P8_AGE_MS - 1
    elif mutation == "p8_future":
        p8["observed_at_unix_ms"] = evaluated_at_unix_ms + 1
    elif mutation == "p8_unsafe_contract":
        p8["dispatch_allowed"] = True
    elif mutation == "p8_extra_field":
        p8["unexpected"] = True
    elif mutation == "recovery_missing":
        synthetic_status["recovery"] = "missing"
    elif mutation == "recovery_malformed":
        synthetic_status["recovery"] = "malformed"
    elif mutation == "recovery_status_blocked":
        recovery["status"] = "blocked"
    elif mutation == "recovery_future":
        recovery["observed_at_unix_ms"] = evaluated_at_unix_ms + 1
    elif mutation == "recovery_stale":
        recovery["observed_at_unix_ms"] = evaluated_at_unix_ms - MAX_RECOVERY_AGE_MS - 1
    elif mutation == "recovery_wrong_action":
        recovery["action"] = "other"
    elif mutation == "recovery_wrong_condition":
        recovery["condition"] = "other"
    elif mutation == "recovery_wrong_spell":
        recovery["spell"] = "other"
    elif mutation == "recovery_extra_field":
        recovery["unexpected"] = True
    elif mutation == "recovery_unsafe_contract":
        recovery["runtime_actions"] = True
    elif mutation != "none" and mutation != "recovery_hash_mismatch":
        raise ValueError(f"unsupported scenario mutation: {mutation}")

    profile_doc = (
        document_from_payload(None, synthetic_status["profile"])
        if "profile" in synthetic_status
        else document_from_payload(profile)
    )
    observation_doc = document_from_payload(observation)
    p8_doc = (
        document_from_payload(None, synthetic_status["p8"])
        if "p8" in synthetic_status
        else document_from_payload(p8)
    )
    trace_doc = document_from_payload(recovery_trace)

    if p8_doc.payload is not None and observation_doc.status == "loaded":
        p8_doc.payload["conditions_observation_sha256"] = observation_doc.sha256
        p8_doc = document_from_payload(p8_doc.payload)
    if "recovery" not in synthetic_status:
        recovery["recovery_trace_sha256"] = trace_doc.sha256
        recovery["profile_sha256"] = profile_doc.sha256
        recovery["observation_sha256"] = observation_doc.sha256
        recovery["p8_proof_sha256"] = p8_doc.sha256
        if mutation == "recovery_hash_mismatch":
            recovery["observation_sha256"] = ZERO_SHA256
        recovery_doc = document_from_payload(recovery)
    else:
        recovery_doc = document_from_payload(None, synthetic_status["recovery"])
    return profile_doc, observation_doc, p8_doc, trace_doc, recovery_doc


def run_scenario_pack(scenario_document: InputDocument) -> dict[str, Any]:
    payload = scenario_document.payload
    if (
        scenario_document.status != "loaded"
        or payload is None
        or not _scenario_pack_valid(payload)
    ):
        return {
            "status": "failed",
            "fixture_only": True,
            "operational_readiness_claimed": False,
            "scenario_pack_sha256": scenario_document.sha256,
            "total_count": 0,
            "passed_count": 0,
            "failed_count": 1,
            "cases": [],
            **{key: False for key in FALSE_FLAGS},
            "intrusive_actions_performed": [],
        }

    evaluated_at = payload["evaluated_at_unix_ms"]
    cases: list[dict[str, Any]] = []
    for scenario in payload["scenarios"]:
        documents = _scenario_documents(scenario["mutation"], evaluated_at)
        first = evaluate_shadow(
            profile_document=documents[0],
            observation_document=documents[1],
            p8_document=documents[2],
            recovery_trace_document=documents[3],
            recovery_proof_document=documents[4],
            evaluated_at_unix_ms=evaluated_at,
            source="fixture",
        )
        second = evaluate_shadow(
            profile_document=documents[0],
            observation_document=documents[1],
            p8_document=documents[2],
            recovery_trace_document=documents[3],
            recovery_proof_document=documents[4],
            evaluated_at_unix_ms=evaluated_at,
            source="fixture",
        )
        deterministic = bool(
            first["blockers"] == second["blockers"]
            and first["canonical_input_sha256"] == second["canonical_input_sha256"]
            and first["decision_sha256"] == second["decision_sha256"]
        )
        passed = bool(
            deterministic
            and first["status"] == scenario["expected_status"]
            and first["blockers"] == scenario["expected_blockers"]
            and _false_flags(first)
            and _empty_ledger(first)
        )
        cases.append(
            {
                "name": scenario["name"],
                "mutation": scenario["mutation"],
                "expected_status": scenario["expected_status"],
                "actual_status": first["status"],
                "expected_blockers": scenario["expected_blockers"],
                "blockers": first["blockers"],
                "canonical_input_sha256": first["canonical_input_sha256"],
                "decision_sha256": first["decision_sha256"],
                "deterministic": deterministic,
                "passed": passed,
                **{key: False for key in FALSE_FLAGS},
                "intrusive_actions_performed": [],
            }
        )
    passed_count = sum(case["passed"] is True for case in cases)
    return {
        "status": "passed" if passed_count == len(cases) else "failed",
        "fixture_only": True,
        "operational_readiness_claimed": False,
        "scenario_pack_sha256": scenario_document.sha256,
        "total_count": len(cases),
        "passed_count": passed_count,
        "failed_count": len(cases) - passed_count,
        "cases": cases,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _select_observation_document(
    raw_p8_document: InputDocument,
    explicit_observation_document: InputDocument | None,
) -> InputDocument:
    payload = raw_p8_document.payload
    schema_version = (
        payload.get("schema_version") if isinstance(payload, dict) else None
    )
    if schema_version == P8_BACKGROUND_SCHEMA:
        return extract_embedded_observation(raw_p8_document)
    if schema_version == P8_PROOF_SCHEMA and explicit_observation_document is not None:
        return explicit_observation_document
    return document_from_payload(None, "missing")


def build_report(
    *,
    profile_document: InputDocument,
    raw_p8_document: InputDocument,
    recovery_trace_document: InputDocument,
    recovery_proof_document: InputDocument,
    scenario_document: InputDocument,
    evaluated_at_unix_ms: int,
    explicit_observation_document: InputDocument | None = None,
) -> dict[str, Any]:
    observation_document = _select_observation_document(
        raw_p8_document, explicit_observation_document
    )
    p8_document = normalize_p8_proof(raw_p8_document, observation_document)
    operational_trace = evaluate_shadow(
        profile_document=profile_document,
        observation_document=observation_document,
        p8_document=p8_document,
        recovery_trace_document=recovery_trace_document,
        recovery_proof_document=recovery_proof_document,
        evaluated_at_unix_ms=evaluated_at_unix_ms,
        source="operational",
    )
    scenario_pack = run_scenario_pack(scenario_document)
    operational_no_action = bool(
        _false_flags(operational_trace) and _empty_ledger(operational_trace)
    )
    operational_status = (
        "shadow_plan_ready_for_operator_review"
        if operational_trace["status"] == "shadow_plan_ready"
        and scenario_pack["status"] == "passed"
        and operational_no_action
        else "operational_acceptance_blocked"
    )
    return {
        "schema_version": REPORT_SCHEMA,
        "generated_at_unix_ms": evaluated_at_unix_ms,
        "mode": "offline_shadow_replay",
        "operational_acceptance_status": operational_status,
        "scenario_pack_status": scenario_pack["status"],
        "fixture_only_validation_passed": scenario_pack["status"] == "passed",
        "runtime_readiness_claimed": False,
        "operational_trace": operational_trace,
        "scenario_pack": scenario_pack,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (OSError, ValueError):
        return False


def _validate_output_path(path: Path) -> Path:
    if not _same_path(path, DEFAULT_OUTPUT):
        raise ValueError(f"JSON output must equal {DEFAULT_OUTPUT}")
    if not _is_within(path, RUNTIME_ROOT):
        raise ValueError(f"JSON output must stay under {RUNTIME_ROOT}")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return path.resolve(strict=False)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("JSON output must be a regular non-link file")
    return path.resolve(strict=False)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    output = _validate_output_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(canonical_bytes(payload) + b"\n")
        temporary.replace(output)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--p8-proof", type=Path, default=DEFAULT_P8_PROOF)
    parser.add_argument(
        "--observation",
        type=Path,
        help=(
            "Optional strict observation for an existing strict P8 proof only; "
            "raw BackgroundStatus always uses its embedded sanitizer envelope."
        ),
    )
    parser.add_argument("--recovery-trace", type=Path, default=DEFAULT_RECOVERY_TRACE)
    parser.add_argument("--recovery-proof", type=Path, default=DEFAULT_RECOVERY_PROOF)
    parser.add_argument("--scenario-pack", type=Path, default=DEFAULT_SCENARIO_PACK)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--evaluated-at-unix-ms", type=int)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--require-operational-acceptance", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evaluated_at = args.evaluated_at_unix_ms
    if evaluated_at is None:
        evaluated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
    if not _is_int(evaluated_at) or evaluated_at <= 0:
        print("evaluated-at-unix-ms must be positive", file=sys.stderr)
        return 2
    try:
        output = _validate_output_path(args.json_out)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report = build_report(
        profile_document=read_document(args.profile),
        raw_p8_document=read_document(args.p8_proof),
        recovery_trace_document=read_document(args.recovery_trace),
        recovery_proof_document=read_document(args.recovery_proof),
        scenario_document=read_document(args.scenario_pack, MAX_SCENARIO_BYTES),
        evaluated_at_unix_ms=evaluated_at,
        explicit_observation_document=(
            read_document(args.observation) if args.observation else None
        ),
    )
    if args.no_write:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        write_json_atomic(output, report)
        print(f"[conditions-shadow-replay] JSON: {output}")
        print(
            "[conditions-shadow-replay] Operational: "
            f"{report['operational_acceptance_status']}"
        )
        print(
            "[conditions-shadow-replay] Scenario pack: "
            f"{report['scenario_pack_status']}"
        )

    if report["scenario_pack_status"] != "passed":
        return 1
    if (
        args.require_operational_acceptance
        and report["operational_acceptance_status"]
        != "shadow_plan_ready_for_operator_review"
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
