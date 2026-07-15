#!/usr/bin/env python3
"""Generate the bounded P13 roadmap ledger and read-only roadmap state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = Path("schemas/ctoa-roadmap-schema-registry.v1.json")
REGISTRY_SCHEMA_PATH = Path("schemas/ctoa-roadmap-schema-registry.schema.json")
STATE_SCHEMA_PATH = Path("schemas/ctoa-roadmap-state.schema.json")
OUTPUT_JSON_PATH = Path("AI/generated/ROADMAP_STATE.json")
OUTPUT_MD_PATH = Path("AI/generated/ROADMAP_STATE.md")
AUDIT_PATH = Path("runtime/control-center/action-audit.jsonl")
CONFIRMATION = "refresh roadmap state"
ACTION_ID = "roadmap-state-refresh"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_TEXT_BYTES = 256 * 1024
MAX_SOURCE_AGE_SECONDS = 24 * 60 * 60
REGISTRY_V1_SHA256 = "c3dd65689219229de0a5d5bcda50f7b60779ad8cc6ea0262dc73386c7ae17fb2"
REGISTRY_SCHEMA_SHA256 = "e63f70b0443c5327a9bf2e597a30e6f49748ae5dee86c7e305ea3b4d28102dd6"
STATE_SCHEMA_SHA256 = "3f2afa6a4a49407ecce6f8bcc71cf4d131c2e98507b6b1b4977f08c8f5067854"

FIXED_ENTRY_PATHS = {
    "p8-background-acceptance": "runtime/solteria_helper_dev/background_status.json",
    "p9-conditions-shadow-acceptance": "runtime/solteria_helper_dev/conditions_shadow_acceptance.json",
    "p10-equipment-shadow-acceptance": "runtime/solteria_helper_dev/equipment_shadow_acceptance.json",
    "p11-heal-friend-shadow-acceptance": "runtime/solteria_helper_dev/heal_friend_shadow_acceptance.json",
    "p12-conditions-execute-once": "runtime/solteria_helper_dev/p12_conditions_execute_once_receipt.json",
    "p12-equipment-execute-once": "runtime/solteria_helper_dev/p12_equipment_execute_once_receipt.json",
    "p12-heal-friend-no-compatible-vocation": "runtime/solteria_helper_dev/p12_heal_friend_no_compatible_vocation_closure.json",
}
FIXED_BINDING_PATHS = {
    "runtime/solteria_helper_dev/conditions_shadow_replay.json",
    "runtime/solteria_helper_dev/equipment_shadow_replay.json",
    "runtime/solteria_helper_dev/heal_friend_shadow_replay.json",
    "runtime/solteria_helper_dev/p12_conditions_execute_once_plan.json",
    "runtime/solteria_helper_dev/p12_conditions_session_approval.json",
    "runtime/solteria_helper_dev/p12_conditions_execute_once_trace.json",
    "runtime/solteria_helper_dev/p12_equipment_execute_once_plan.json",
    "runtime/solteria_helper_dev/p12_equipment_session_approval.json",
    "runtime/solteria_helper_dev/p12_equipment_execute_once_trace.json",
    "runtime/solteria_helper_dev/p12_heal_friend_execute_once_plan.json",
    "runtime/solteria_helper_dev/p12_heal_friend_session_approval.json",
    "runtime/solteria_helper_dev/p12_heal_friend_execution_preflight.json",
}
SOURCE_HEALTH_PATHS = {
    "feature_roadmap": "AI/FEATURE_ROADMAP.md",
    "engine_brain_manifest": "AI/generated/manifest.json",
    "operator_brief": "AI/generated/P7_OPERATOR_BRIEF.json",
    "helper_manifest": "runtime/solteria_helper_dev/manifest.json",
    "runtime_module_gates": "runtime/solteria_helper_dev/runtime_module_gates_sandbox_smoke.json",
}
ALLOWED_OUTPUT_PATHS = [
    OUTPUT_JSON_PATH.as_posix(),
    OUTPUT_MD_PATH.as_posix(),
    AUDIT_PATH.as_posix(),
]


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains a duplicate key."""


@dataclass(frozen=True)
class LoadedJson:
    status: str
    payload: dict[str, Any] | None
    raw: bytes | None
    sha256: str | None
    mtime_ns: int | None


@dataclass(frozen=True)
class LoadedText:
    status: str
    text: str | None
    raw: bytes | None
    sha256: str | None
    mtime_ns: int | None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fixed_path(root: Path, relative: str | Path) -> tuple[Path | None, str | None]:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None, "outside_root"
    resolved_root = root.resolve(strict=False)
    if root.is_symlink():
        return None, "symlink_rejected"
    candidate = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            return None, "symlink_rejected"
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None, "outside_root"
    return candidate, None


def _read_stable_bytes(root: Path, relative: str | Path, max_bytes: int) -> tuple[str, bytes | None, int | None]:
    path, error = _fixed_path(root, relative)
    if error or path is None:
        return error or "outside_root", None, None
    try:
        before = path.stat()
    except FileNotFoundError:
        return "missing", None, None
    except OSError:
        return "malformed", None, None
    if not path.is_file():
        return "missing", None, None
    if before.st_size > max_bytes:
        return "oversize", None, before.st_mtime_ns
    try:
        raw = path.read_bytes()
        after = path.stat()
    except OSError:
        return "malformed", None, before.st_mtime_ns
    if (
        before.st_mtime_ns != after.st_mtime_ns
        or before.st_size != after.st_size
        or len(raw) != after.st_size
    ):
        return "changed_during_read", None, after.st_mtime_ns
    return "loaded", raw, after.st_mtime_ns


def _load_json(root: Path, relative: str | Path) -> LoadedJson:
    status, raw, mtime_ns = _read_stable_bytes(root, relative, MAX_JSON_BYTES)
    if status != "loaded" or raw is None:
        return LoadedJson(status, None, None, None, mtime_ns)
    try:
        payload = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except DuplicateKeyError:
        return LoadedJson("duplicate_keys", None, raw, _raw_sha256(raw), mtime_ns)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return LoadedJson("malformed", None, raw, _raw_sha256(raw), mtime_ns)
    if not isinstance(payload, dict):
        return LoadedJson("not_object", None, raw, _raw_sha256(raw), mtime_ns)
    return LoadedJson("loaded", payload, raw, _raw_sha256(raw), mtime_ns)


def _load_text(root: Path, relative: str | Path) -> LoadedText:
    status, raw, mtime_ns = _read_stable_bytes(root, relative, MAX_TEXT_BYTES)
    if status != "loaded" or raw is None:
        return LoadedText(status, None, None, None, mtime_ns)
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        return LoadedText("malformed", None, raw, _raw_sha256(raw), mtime_ns)
    return LoadedText("loaded", value, raw, _raw_sha256(raw), mtime_ns)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _artifact_datetime(payload: dict[str, Any], mtime_ns: int | None) -> datetime | None:
    for field in ("created_at_unix_ms", "generated_at_utc", "generated_at", "created_at"):
        parsed = _parse_datetime(payload.get(field))
        if parsed is not None:
            return parsed
    if mtime_ns is None:
        return None
    return datetime.fromtimestamp(mtime_ns / 1_000_000_000, tz=timezone.utc)


def _age_seconds(value: datetime | None, now: datetime) -> int | None:
    if value is None:
        return None
    return max(0, int((now - value).total_seconds()))


def _schema_errors(schema: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    try:
        Draft202012Validator.check_schema(schema)
        errors = Draft202012Validator(schema).iter_errors(payload)
    except jsonschema_exceptions.SchemaError as exc:
        return [f"schema_invalid:{exc.message[:120]}"]
    return [
        f"{'.'.join(str(item) for item in error.absolute_path) or '$'}:{error.message[:120]}"
        for error in sorted(errors, key=lambda item: list(item.absolute_path))
    ]


def _source_health(root: Path, now: datetime, cache: dict[str, LoadedJson]) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    feature = _load_text(root, SOURCE_HEALTH_PATHS["feature_roadmap"])
    feature_ok = bool(
        feature.status == "loaded"
        and feature.text
        and "P12 Heal Friend is `closed_blocked_no_compatible_vocation`" in feature.text
        and any(
            marker in feature.text
            for marker in (
                "P13 is `ready_to_start`",
                "P13 is `implementation_ready_for_confirmed_refresh`",
                "P13 is `runtime_evidence_ready`",
            )
        )
    )
    checks.append(
        {
            "name": "feature_roadmap",
            "path": SOURCE_HEALTH_PATHS["feature_roadmap"],
            "load_status": feature.status,
            "sha256": feature.sha256,
            "freshness_status": "timeless" if feature.status == "loaded" else "blocked",
            "age_seconds": None,
            "contract_status": "passed" if feature_ok else "blocked",
        }
    )
    if not feature_ok:
        blockers.append("feature_roadmap_contract")

    for name in ("engine_brain_manifest", "operator_brief", "helper_manifest", "runtime_module_gates"):
        relative = SOURCE_HEALTH_PATHS[name]
        loaded = cache.setdefault(relative, _load_json(root, relative))
        payload = loaded.payload or {}
        created = _artifact_datetime(payload, loaded.mtime_ns)
        age = _age_seconds(created, now)
        freshness = "current" if age is not None and age <= MAX_SOURCE_AGE_SECONDS else "stale"
        contract_ok = loaded.status == "loaded"
        if name == "engine_brain_manifest":
            contract_ok = contract_ok and payload.get("doc_sync_status") == "passed" and payload.get("secret_guardrail_status") == "passed"
        elif name == "operator_brief":
            roadmap = payload.get("roadmap_generation") if isinstance(payload.get("roadmap_generation"), dict) else {}
            handoff = payload.get("cockpit_handoff") if isinstance(payload.get("cockpit_handoff"), dict) else {}
            contract_ok = contract_ok and payload.get("status") == "ready" and payload.get("hard_blockers") == [] and roadmap.get("status") == "ready" and handoff.get("status") == "ready"
        elif name == "helper_manifest":
            contract_ok = contract_ok and payload.get("helper_version") == "v2.4.1" and isinstance(payload.get("files"), list)
        else:
            manifest = cache.setdefault(SOURCE_HEALTH_PATHS["helper_manifest"], _load_json(root, SOURCE_HEALTH_PATHS["helper_manifest"]))
            gate_manifest = payload.get("manifest") if isinstance(payload.get("manifest"), dict) else {}
            contract_ok = contract_ok and payload.get("status") == "passed" and payload.get("failed") == [] and payload.get("observed", {}).get("runtime_state") == "disarmed" and gate_manifest.get("sha256") == manifest.sha256
        if freshness == "stale":
            contract_ok = False
        checks.append(
            {
                "name": name,
                "path": relative,
                "load_status": loaded.status,
                "sha256": loaded.sha256,
                "freshness_status": freshness if loaded.status == "loaded" else "blocked",
                "age_seconds": age,
                "contract_status": "passed" if contract_ok else "blocked",
            }
        )
        if not contract_ok:
            blockers.append(f"{name}_contract")
    return checks, blockers


def _control_center_preflight(operator_brief: LoadedJson) -> dict[str, Any]:
    payload = operator_brief.payload or {}
    roadmap = payload.get("roadmap_generation") if isinstance(payload.get("roadmap_generation"), dict) else {}
    handoff = payload.get("cockpit_handoff") if isinstance(payload.get("cockpit_handoff"), dict) else {}
    hard_blockers = [str(item)[:200] for item in payload.get("hard_blockers", []) if str(item).strip()] if isinstance(payload.get("hard_blockers"), list) else ["operator_brief_hard_blockers_invalid"]
    if operator_brief.status != "loaded":
        hard_blockers.append(f"operator_brief_{operator_brief.status}")
    if payload.get("status") != "ready":
        hard_blockers.append("operator_brief_not_ready")
    if roadmap.get("status") != "ready":
        hard_blockers.append("roadmap_generation_not_ready")
    if handoff.get("status") != "ready":
        hard_blockers.append("cockpit_handoff_not_ready")
    unique = list(dict.fromkeys(hard_blockers))
    return {
        "status": "ready" if not unique else "blocked",
        "ready": not unique,
        "operator_brief_status": str(payload.get("status") or operator_brief.status),
        "roadmap_generation_status": str(roadmap.get("status") or "missing"),
        "cockpit_handoff_status": str(handoff.get("status") or "missing"),
        "hard_blockers": unique,
    }


def _binding_result(root: Path, primary: dict[str, Any], binding: dict[str, Any], cache: dict[str, LoadedJson]) -> tuple[dict[str, Any], str | None]:
    relative = str(binding["path"])
    loaded = cache.setdefault(relative, _load_json(root, relative))
    expected_value = primary.get(str(binding["target_field"]))
    actual_value: Any = None
    if loaded.status == "loaded" and loaded.payload is not None:
        if binding["mode"] == "raw_sha256":
            actual_value = loaded.sha256
        elif binding["mode"] == "canonical_json_sha256":
            actual_value = _canonical_sha256(loaded.payload)
        else:
            actual_value = loaded.payload.get(str(binding.get("source_field") or ""))
    passed = loaded.status == "loaded" and isinstance(expected_value, str) and expected_value == actual_value
    result = {
        "role": str(binding["role"]),
        "path": relative,
        "mode": str(binding["mode"]),
        "status": "passed" if passed else "blocked",
        "expected_sha256": str(expected_value) if isinstance(expected_value, str) else None,
        "actual_sha256": str(actual_value) if isinstance(actual_value, str) else None,
    }
    return result, None if passed else f"binding_{binding['role']}_{loaded.status}"


def _entry_created_at(payload: dict[str, Any], mtime_ns: int | None) -> tuple[str | None, datetime | None]:
    parsed = _artifact_datetime(payload, mtime_ns)
    return (parsed.isoformat().replace("+00:00", "Z") if parsed else None, parsed)


def _build_ledger_entry(
    root: Path,
    config: dict[str, Any],
    now: datetime,
    cache: dict[str, LoadedJson],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    relative = str(config["path"])
    loaded = cache.setdefault(relative, _load_json(root, relative))
    payload = loaded.payload or {}
    blockers: list[str] = []
    if loaded.status != "loaded":
        blockers.append(f"evidence_{loaded.status}")
    if payload.get("schema_version") != config["expected_schema_version"]:
        blockers.append("schema_version_mismatch")
    if payload.get("status") != config["expected_status"]:
        blockers.append("status_mismatch")
    source_blockers = payload.get(str(config["blocker_field"]))
    if source_blockers != []:
        blockers.append("source_blockers_present")
    for flag in config["required_false_flags"]:
        if payload.get(flag) is not False:
            blockers.append(f"unsafe_{flag}")
    for flag in config["required_true_flags"]:
        if payload.get(flag) is not True:
            blockers.append(f"required_{flag}_missing")
    if config["expected_attempt_count"] is not None and payload.get("attempt_count") != config["expected_attempt_count"]:
        blockers.append("attempt_count_mismatch")
    if config["expected_retry_scheduled"] is not None and payload.get("retry_scheduled") is not config["expected_retry_scheduled"]:
        blockers.append("retry_state_mismatch")
    if config["expected_final_state"] is not None and payload.get("final_state") != config["expected_final_state"]:
        blockers.append("final_state_mismatch")
    intrusive = payload.get("intrusive_actions_performed")
    if not isinstance(intrusive, list) or len(intrusive) != config["expected_intrusive_action_count"]:
        blockers.append("intrusive_action_count_mismatch")
    if config["decision_id"] == "p8-background-acceptance":
        interaction = payload.get("interaction_contract") if isinstance(payload.get("interaction_contract"), dict) else {}
        integrity = payload.get("integrity") if isinstance(payload.get("integrity"), dict) else {}
        capability = payload.get("capability") if isinstance(payload.get("capability"), dict) else {}
        if interaction.get("passive_reads_only") is not True or interaction.get("live_file_writes") is not False or interaction.get("gui_automation") is not False:
            blockers.append("p8_interaction_contract_unsafe")
        if integrity.get("status") != "passed" or capability.get("runtime_state") != "disarmed":
            blockers.append("p8_integrity_or_runtime_state")
    if config["decision_id"] == "p12-heal-friend-no-compatible-vocation":
        if payload.get("closure_reason") != "no_compatible_sandbox_vocation" or payload.get("required_vocation") != "ed":
            blockers.append("heal_friend_closure_reason_mismatch")

    binding_results: list[dict[str, Any]] = []
    for binding in config["bindings"]:
        result, blocker = _binding_result(root, payload, binding, cache)
        binding_results.append(result)
        if blocker:
            blockers.append(blocker)

    previous_sha = None
    if isinstance(previous, dict):
        candidate = previous.get("evidence_sha256")
        previous_sha = candidate if isinstance(candidate, str) else None
    tampered = bool(previous_sha and loaded.sha256 and previous_sha != loaded.sha256)
    if tampered:
        blockers.append("terminal_evidence_changed_since_previous_state")
    created_at, created_dt = _entry_created_at(payload, loaded.mtime_ns)
    unique = list(dict.fromkeys(blockers))
    integrity_status = "tampered" if tampered else ("passed" if not unique else "blocked")
    return {
        "decision_id": str(config["decision_id"]),
        "ordinal": int(config["ordinal"]),
        "phase": str(config["phase"]),
        "lane": str(config["lane"]),
        "decision_status": str(config["decision_status"]),
        "result_status": str(config["result_status"]),
        "evidence_path": relative,
        "evidence_schema_version": payload.get("schema_version") if isinstance(payload.get("schema_version"), str) else None,
        "evidence_sha256": loaded.sha256,
        "previous_evidence_sha256": previous_sha,
        "evidence_status": payload.get("status") if isinstance(payload.get("status"), str) else None,
        "integrity_status": integrity_status,
        "freshness_status": "immutable_terminal" if loaded.status == "loaded" else "blocked",
        "created_at": created_at,
        "age_seconds": _age_seconds(created_dt, now),
        "terminal": True,
        "attempt_count": payload.get("attempt_count") if isinstance(payload.get("attempt_count"), int) else None,
        "retry_scheduled": payload.get("retry_scheduled") if isinstance(payload.get("retry_scheduled"), bool) else None,
        "final_state": payload.get("final_state") if isinstance(payload.get("final_state"), str) else None,
        "downstream_authority_granted": False,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "execute_once_allowed": False,
        "live_promotion": False,
        "intrusive_action_count": len(intrusive) if isinstance(intrusive, list) else 0,
        "predecessor_ids": list(config["predecessor_ids"]),
        "bindings": binding_results,
        "blockers": unique,
    }


def build_state(root: Path = ROOT, *, now: datetime | None = None) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cache: dict[str, LoadedJson] = {}
    blockers: list[str] = []

    registry_schema = _load_json(root, REGISTRY_SCHEMA_PATH)
    registry = _load_json(root, REGISTRY_PATH)
    state_schema = _load_json(root, STATE_SCHEMA_PATH)
    if registry_schema.status != "loaded" or registry_schema.payload is None:
        blockers.append(f"registry_schema_{registry_schema.status}")
    if registry.status != "loaded" or registry.payload is None:
        blockers.append(f"registry_{registry.status}")
    if state_schema.status != "loaded" or state_schema.payload is None:
        blockers.append(f"state_schema_{state_schema.status}")
    registry_pin_mismatch = bool(
        registry.sha256 != REGISTRY_V1_SHA256
        or registry_schema.sha256 != REGISTRY_SCHEMA_SHA256
    )
    if registry.sha256 != REGISTRY_V1_SHA256:
        blockers.append("schema_registry_v1_pin_mismatch")
    if registry_schema.sha256 != REGISTRY_SCHEMA_SHA256:
        blockers.append("schema_registry_contract_pin_mismatch")
    if state_schema.sha256 != STATE_SCHEMA_SHA256:
        blockers.append("roadmap_state_schema_pin_mismatch")
    registry_errors = (
        _schema_errors(registry_schema.payload, registry.payload)
        if registry_schema.payload and registry.payload
        else []
    )
    blockers.extend(f"registry_validation:{item}" for item in registry_errors)
    entries = registry.payload.get("entries", []) if registry.payload else []
    if not isinstance(entries, list):
        entries = []

    observed_entry_paths = {
        str(item.get("decision_id")): str(item.get("path"))
        for item in entries
        if isinstance(item, dict)
    }
    if observed_entry_paths != FIXED_ENTRY_PATHS:
        blockers.append("registry_entry_allowlist_mismatch")
    observed_binding_paths = {
        str(binding.get("path"))
        for item in entries
        if isinstance(item, dict)
        for binding in item.get("bindings", [])
        if isinstance(binding, dict)
    }
    if observed_binding_paths != FIXED_BINDING_PATHS:
        blockers.append("registry_binding_allowlist_mismatch")

    previous_loaded = _load_json(root, OUTPUT_JSON_PATH)
    previous_payload = previous_loaded.payload if previous_loaded.status == "loaded" else None
    if previous_loaded.status not in {"loaded", "missing"}:
        blockers.append(f"previous_state_{previous_loaded.status}")
    previous_ledger = {
        str(item.get("decision_id")): item
        for item in (previous_payload or {}).get("ledger", [])
        if isinstance(item, dict)
    }
    previous_registry = (previous_payload or {}).get("schema_registry")
    previous_registry_sha = (
        previous_registry.get("sha256")
        if isinstance(previous_registry, dict) and isinstance(previous_registry.get("sha256"), str)
        else None
    )
    registry_tampered = bool(
        registry_pin_mismatch
        or (
            previous_registry_sha
            and registry.sha256
            and previous_registry_sha != registry.sha256
        )
    )
    if registry_tampered:
        blockers.append("schema_registry_changed_without_version")

    ledger = [
        _build_ledger_entry(
            root,
            item,
            current,
            cache,
            previous_ledger.get(str(item.get("decision_id"))),
        )
        for item in entries
        if isinstance(item, dict)
    ]
    if len(ledger) != 7:
        blockers.append("ledger_count_mismatch")
    for item in ledger:
        blockers.extend(f"{item['decision_id']}:{blocker}" for blocker in item["blockers"])

    source_health, source_blockers = _source_health(root, current, cache)
    blockers.extend(source_blockers)
    operator_brief = cache.setdefault(
        SOURCE_HEALTH_PATHS["operator_brief"],
        _load_json(root, SOURCE_HEALTH_PATHS["operator_brief"]),
    )
    preflight = _control_center_preflight(operator_brief)
    blockers.extend(f"control_center_preflight:{item}" for item in preflight["hard_blockers"])
    unique_blockers = list(dict.fromkeys(blockers))
    tampered_count = sum(1 for item in ledger if item["integrity_status"] == "tampered")
    blocked_count = sum(1 for item in ledger if item["blockers"])
    stale = any(item["freshness_status"] == "stale" for item in source_health)
    ready = not unique_blockers and preflight["ready"]

    basis: dict[str, Any] = {
        "schema_version": "ctoa.roadmap-state.v1",
        "generated_at": current.isoformat().replace("+00:00", "Z"),
        "status": "ready" if ready else "blocked",
        "phase": "P13",
        "phase_status": "runtime_evidence_ready" if ready else "blocked",
        "next_phase": "P14",
        "previous_state_sha256": previous_loaded.sha256,
        "control_center_preflight": preflight,
        "schema_registry": {
            "status": "tampered" if registry_tampered else ("passed" if not registry_errors and registry.status == "loaded" else "blocked"),
            "path": REGISTRY_PATH.as_posix(),
            "schema_path": REGISTRY_SCHEMA_PATH.as_posix(),
            "schema_version": registry.payload.get("schema_version") if registry.payload else None,
            "entry_count": len(entries),
            "sha256": registry.sha256,
            "schema_sha256": registry_schema.sha256,
            "previous_sha256": previous_registry_sha,
        },
        "source_health": source_health,
        "ledger": ledger,
        "summary": {
            "ledger_count": len(ledger),
            "accepted_count": sum(1 for item in ledger if item["decision_status"] == "accepted" and not item["blockers"]),
            "closed_no_action_count": sum(1 for item in ledger if item["decision_status"] == "closed_no_action" and not item["blockers"]),
            "blocked_count": blocked_count,
            "tampered_count": tampered_count,
            "total_attempt_count": sum(item["attempt_count"] or 0 for item in ledger),
            "runtime_authority_count": 0,
            "live_authority_count": 0,
        },
        "freshness_status": "blocked" if not ready and not stale else ("stale" if stale else "current"),
        "tamper_status": "tampered" if registry_tampered or tampered_count else ("passed" if ready else "blocked"),
        "authority": {
            "control_center_mode": "read_only",
            "runtime_executor_added": False,
            "runtime_actions": False,
            "live_authority": False,
            "p12_heal_friend_reopened": False,
            "mcp_write_tool_enabled": False,
            "allowed_output_paths": ALLOWED_OUTPUT_PATHS,
        },
        "blockers": unique_blockers,
        "next_action": (
            "Consume this P13 state read-only in Control Center; keep runtime, live authority, MCP writes, and the closed P12 Heal Friend lane unchanged."
            if ready
            else "Repair the listed P13 evidence, freshness, schema, binding, or preflight blockers before writing a new roadmap state."
        ),
    }
    payload = {**basis, "state_sha256": _canonical_sha256(basis)}
    state_errors = _schema_errors(state_schema.payload, payload) if state_schema.payload else ["state_schema_missing"]
    if state_errors:
        merged = list(dict.fromkeys([*payload["blockers"], *(f"state_validation:{item}" for item in state_errors)]))
        payload["blockers"] = merged
        payload["status"] = "blocked"
        payload["phase_status"] = "blocked"
        payload["freshness_status"] = "blocked"
        payload["tamper_status"] = "blocked" if payload["tamper_status"] == "passed" else payload["tamper_status"]
        payload["state_sha256"] = _canonical_sha256({key: value for key, value in payload.items() if key != "state_sha256"})
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# CTOAi P13 Roadmap State",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"State SHA-256: `{payload['state_sha256']}`",
        f"Status: `{payload['status']}`",
        f"Phase: `{payload['phase']}` / `{payload['phase_status']}`; next `{payload['next_phase']}`.",
        f"Freshness: `{payload['freshness_status']}`; tamper: `{payload['tamper_status']}`.",
        "",
        "## Authority Boundary",
        "",
        "- Control Center is read-only.",
        "- No runtime executor, runtime action, MCP write tool, or live authority is introduced.",
        "- P12 Heal Friend remains closed and is not reopened.",
        "",
        "## Decision / Result Ledger",
        "",
        "| Order | Decision | Phase | Lane | Decision | Result | Integrity | Freshness | Attempts | Final state |",
        "|---:|---|---|---|---|---|---|---|---:|---|",
    ]
    for item in payload["ledger"]:
        lines.append(
            f"| {item['ordinal']} | `{item['decision_id']}` | `{item['phase']}` | `{item['lane']}` | `{item['decision_status']}` | `{item['result_status']}` | `{item['integrity_status']}` | `{item['freshness_status']}` | {item['attempt_count'] if item['attempt_count'] is not None else '-'} | `{item['final_state'] or '-'}` |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Ledger entries: `{summary['ledger_count']}`; accepted: `{summary['accepted_count']}`; closed without action: `{summary['closed_no_action_count']}`.",
            f"- Blocked: `{summary['blocked_count']}`; tampered: `{summary['tampered_count']}`; total bounded attempts: `{summary['total_attempt_count']}`.",
            f"- Runtime authority: `{summary['runtime_authority_count']}`; live authority: `{summary['live_authority_count']}`.",
            "",
            "## Source Health",
            "",
        ]
    )
    for item in payload["source_health"]:
        lines.append(
            f"- `{item['name']}`: contract `{item['contract_status']}`, freshness `{item['freshness_status']}`, source `{item['path']}`."
        )
    if payload["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- `{item}`" for item in payload["blockers"])
    lines.extend(["", "## Next Action", "", payload["next_action"], ""])
    return "\n".join(lines)


def _sanitize_audit_text(value: Any, max_length: int = 500) -> str:
    text = str(value or "")
    text = re.sub(r"(?i)(token|password|secret|authorization)(\s*[:=]\s*)([^\s,;]+)", r"\1\2[redacted]", text)
    text = re.sub(r"(?i)\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]+", "[redacted]", text)
    text = text.replace("\r", " ").replace("\n", " ").strip()
    return text if len(text) <= max_length else f"{text[: max_length - 12].rstrip()} [truncated]"


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _audit_id(at: str) -> str:
    return f"{re.sub(r'[^0-9]', '', at)}-{ACTION_ID}"


def _ensure_write_target(root: Path, relative: Path) -> Path:
    path, error = _fixed_path(root, relative)
    if error or path is None:
        raise ValueError(f"{relative.as_posix()}:{error or 'outside_root'}")
    parent = path.parent
    parent_rel = parent.relative_to(root)
    parent_path, parent_error = _fixed_path(root, parent_rel)
    if parent_error or parent_path is None:
        raise ValueError(f"{relative.as_posix()}:{parent_error or 'outside_root'}")
    parent_path.mkdir(parents=True, exist_ok=True)
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise ValueError(f"{relative.as_posix()}:symlink_or_non_file_rejected")
    return path


def _atomic_write(path: Path, raw: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _append_audit(
    root: Path,
    *,
    dry_run: bool,
    authorized: bool,
    ok: bool,
    reason: str,
    output_hashes: dict[str, str],
    written_paths: list[str],
) -> tuple[str, str]:
    at = _timestamp_utc()
    identifier = _audit_id(at)
    audit_path = _ensure_write_target(root, AUDIT_PATH)
    record = {
        "at": at,
        "audit_id": identifier,
        "actor": "codex-cli",
        "actor_role": "operator",
        "action": ACTION_ID,
        "target": "local",
        "risk_class": "safe_write",
        "minimum_role": "operator",
        "dry_run": dry_run,
        "authorized": authorized,
        "ok": ok,
        "reason": _sanitize_audit_text(reason),
        "output_preview": _sanitize_audit_text(
            f"status={'completed' if ok else 'blocked'}; outputs={','.join(written_paths) or 'none'}"
        ),
        "output_hashes": output_hashes,
        "written_paths": written_paths,
    }
    with audit_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return identifier, AUDIT_PATH.as_posix()


def execute(
    root: Path = ROOT,
    *,
    dry_run: bool = True,
    confirmation: str = "",
    reason: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    payload = build_state(root, now=now)
    json_raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    markdown_raw = render_markdown(payload).encode()
    output_hashes = {
        OUTPUT_JSON_PATH.as_posix(): _raw_sha256(json_raw),
        OUTPUT_MD_PATH.as_posix(): _raw_sha256(markdown_raw),
    }
    authorized = dry_run or confirmation == CONFIRMATION
    ok = payload["status"] == "ready" and authorized
    written_paths: list[str] = []
    failure_reason = reason
    if not authorized:
        failure_reason = f"Confirmed execution requires confirmation={CONFIRMATION!r}."
    elif payload["status"] != "ready":
        failure_reason = f"P13 state is blocked: {', '.join(payload['blockers'][:8]) or 'unknown blocker'}"
    elif not dry_run:
        try:
            json_path = _ensure_write_target(root, OUTPUT_JSON_PATH)
            markdown_path = _ensure_write_target(root, OUTPUT_MD_PATH)
            _atomic_write(json_path, json_raw)
            _atomic_write(markdown_path, markdown_raw)
            written_paths = [OUTPUT_JSON_PATH.as_posix(), OUTPUT_MD_PATH.as_posix()]
        except (OSError, ValueError) as exc:
            ok = False
            failure_reason = f"Roadmap output write failed: {exc}"
    audit_identifier, audit_path = _append_audit(
        root,
        dry_run=dry_run,
        authorized=authorized,
        ok=ok,
        reason=failure_reason or ("P13 roadmap-state dry run" if dry_run else "P13 roadmap-state confirmed refresh"),
        output_hashes=output_hashes if ok else {},
        written_paths=written_paths,
    )
    return {
        "schema_version": 1,
        "status": "dry_run" if ok and dry_run else ("completed" if ok else "blocked"),
        "action": ACTION_ID,
        "risk_class": "safe_write",
        "dry_run": dry_run,
        "authorized": authorized,
        "ok": ok,
        "audit_id": audit_identifier,
        "audit_path": audit_path,
        "state_status": payload["status"],
        "state_sha256": payload["state_sha256"],
        "output_hashes": output_hashes if ok else {},
        "written_paths": written_paths,
        "blockers": payload["blockers"],
        "authority": payload["authority"],
    }


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", type=_parse_bool, default=True)
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)
    result = execute(
        ROOT,
        dry_run=args.dry_run,
        confirmation=args.confirmation,
        reason=args.reason,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
