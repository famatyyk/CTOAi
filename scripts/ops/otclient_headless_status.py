#!/usr/bin/env python3
"""Collect passive OTClient status without interacting with the user's screen.

The command is advisory-only. It never starts, stops, focuses, captures, sends
input to, or writes inside an OTClient/Solteria installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from .otclient_headless_evidence import (
        load_json_bounded,
        parse_json_object_bytes,
        read_bytes_bounded,
        summarize_capability,
        summarize_log,
    )
else:
    from otclient_headless_evidence import (
        load_json_bounded,
        parse_json_object_bytes,
        read_bytes_bounded,
        summarize_capability,
        summarize_log,
    )


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEFAULT_DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_OUTPUT = DEFAULT_DEV_DIR / "background_status.json"
SCHEMA_VERSION = "ctoa.otclient-headless-status.v1"
LIVE_MANIFEST_SCHEMA = "ctoa.solteria-live-manifest.v1"
LIVE_MANIFEST_ORIGIN = "official_live_promotion"
MAX_MANIFEST_JSON_BYTES = 2 * 1024 * 1024
MAX_PROMOTION_JSON_BYTES = 64 * 1024
MAX_MANIFEST_ENTRIES = 128
MAX_LIVE_FILE_BYTES = 2 * 1024 * 1024
MAX_LIVE_TOTAL_BYTES = 16 * 1024 * 1024
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PIN_LOAD_STATUSES = {
    "missing",
    "empty",
    "malformed",
    "oversize",
    "symlink_rejected",
    "not_regular",
    "not_object",
    "changed_during_open",
    "unreadable",
}
ROOT_MANIFEST_FILES = {
    "ctoa_otclient_loader.lua",
    "ctoa_ek_profile.lua",
    "ctoa_ms_profile.lua",
    "ctoa_ed_profile.lua",
    "ctoa_rp_profile.lua",
}
PROFILE_RUNTIME_PATHS = {
    "mods/ctoa_otclient/ctoa_ek_profile.lua",
    "mods/ctoa_otclient/ctoa_ms_profile.lua",
    "mods/ctoa_otclient/ctoa_ed_profile.lua",
    "mods/ctoa_otclient/ctoa_rp_profile.lua",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_text(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _same_canonical_path(left: Path, right: Path) -> bool:
    return _canonical_text(left) == _canonical_text(right)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (OSError, ValueError):
        return False


def _require_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve(strict=False)
    if not _is_within(resolved, root):
        raise ValueError(f"{label} must stay under {root}")
    return resolved


def _require_exact(path: Path, expected: Path, label: str) -> Path:
    resolved = path.resolve(strict=False)
    if not _same_canonical_path(resolved, expected):
        raise ValueError(f"{label} must equal {expected.resolve(strict=False)}")
    return resolved


def _manifest_relative_path(value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    text = value.replace("\\", "/")
    pure = PurePosixPath(text)
    if (
        not text
        or "\x00" in text
        or pure.is_absolute()
        or ".." in pure.parts
        or "." in pure.parts
    ):
        return None
    if len(pure.parts) == 1 and pure.name in ROOT_MANIFEST_FILES:
        return Path(pure.name)
    if (
        len(pure.parts) == 3
        and pure.parts[0] == "mods"
        and pure.parts[1] == "ctoa_otclient"
        and pure.parts[2]
    ):
        return Path(*pure.parts)
    return None


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _file_fingerprint(
    path: Path,
    max_bytes: int = MAX_LIVE_FILE_BYTES,
) -> tuple[tuple[str, int, int] | None, str]:
    if max_bytes <= 0:
        return None, "aggregate_budget_exceeded"
    bounded_max_bytes = min(max_bytes, MAX_LIVE_FILE_BYTES)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "unreadable"
    if stat.S_ISLNK(before.st_mode):
        return None, "symlink_rejected"
    if not stat.S_ISREG(before.st_mode):
        return None, "not_regular"

    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or not _same_file_identity(
                before, opened
            ):
                return None, "changed_during_open"
            if opened.st_size > MAX_LIVE_FILE_BYTES:
                return None, "file_oversize"
            if opened.st_size > bounded_max_bytes:
                return None, "aggregate_budget_exceeded"
            while True:
                remaining = bounded_max_bytes + 1 - total
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                total += len(chunk)
                if total > bounded_max_bytes:
                    return None, "aggregate_budget_exceeded"
                digest.update(chunk)
    except OSError:
        return None, "unreadable"
    return (digest.hexdigest(), total, opened.st_mtime_ns), "loaded"


def _validated_manifest_entries(
    manifest: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], int]:
    errors: list[str] = []
    entries = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        return [], ["manifest_files_missing"], 0
    if len(entries) > MAX_MANIFEST_ENTRIES:
        return [], ["manifest_entry_limit_exceeded"], 0

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    declared_total = 0
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            errors.append(f"manifest_entry_{index}_invalid")
            continue
        relative = _manifest_relative_path(item.get("path"))
        if relative is None:
            errors.append(f"manifest_entry_{index}_path_invalid")
            continue
        key = relative.as_posix()
        folded_key = key.casefold()
        if folded_key in seen:
            errors.append(f"manifest_entry_{index}_duplicate")
            continue
        seen.add(folded_key)

        expected_hash = item.get("sha256")
        expected_bytes = item.get("bytes")
        if not isinstance(expected_hash, str) or not SHA256_PATTERN.fullmatch(
            expected_hash
        ):
            errors.append(f"manifest_entry_{index}_sha256_invalid")
            continue
        if (
            not isinstance(expected_bytes, int)
            or isinstance(expected_bytes, bool)
            or expected_bytes < 0
            or expected_bytes > MAX_LIVE_FILE_BYTES
        ):
            errors.append(f"manifest_entry_{index}_bytes_invalid")
            continue
        declared_total += expected_bytes
        if declared_total > MAX_LIVE_TOTAL_BYTES:
            errors.append("manifest_total_bytes_exceeded")
            break
        normalized.append(
            {
                "relative": relative,
                "path": key,
                "sha256": expected_hash,
                "bytes": expected_bytes,
            }
        )
    return normalized, errors, declared_total


def validate_live_pin(
    live_manifest_path: Path,
    live_promotion_path: Path,
    client_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_raw, manifest_load_status = read_bytes_bounded(
        live_manifest_path, MAX_MANIFEST_JSON_BYTES
    )
    manifest: dict[str, Any] | None = None
    if manifest_raw is not None and manifest_load_status == "loaded":
        manifest, manifest_load_status = parse_json_object_bytes(manifest_raw)
    promotion, promotion_load_status = load_json_bounded(
        live_promotion_path, MAX_PROMOTION_JSON_BYTES
    )
    manifest_sha256 = (
        hashlib.sha256(manifest_raw).hexdigest()
        if manifest_raw is not None and manifest_load_status == "loaded"
        else ""
    )

    errors: list[str] = []
    if manifest_load_status != "loaded":
        errors.append(f"live_manifest_{manifest_load_status}")
    if promotion_load_status != "loaded":
        errors.append(f"live_promotion_{promotion_load_status}")

    helper_version = ""
    entries: list[dict[str, Any]] = []
    entry_errors: list[str] = []
    declared_total = 0
    if isinstance(manifest, dict):
        if manifest.get("schema_version") != LIVE_MANIFEST_SCHEMA:
            errors.append("live_manifest_schema_invalid")
        if manifest.get("origin") != LIVE_MANIFEST_ORIGIN:
            errors.append("live_manifest_origin_invalid")
        generated_at = manifest.get("generated_at_utc")
        if not isinstance(generated_at, str) or not 0 < len(generated_at) <= 64:
            errors.append("live_manifest_timestamp_invalid")
        helper_value = manifest.get("helper_version")
        if not isinstance(helper_value, str) or not 0 < len(helper_value) <= 32:
            errors.append("live_manifest_helper_version_invalid")
        else:
            helper_version = helper_value
        entries, entry_errors, declared_total = _validated_manifest_entries(manifest)
        errors.extend(entry_errors)

    if isinstance(promotion, dict):
        if promotion.get("name") != "solteria-helper-live-promotion":
            errors.append("live_promotion_name_invalid")
        if promotion.get("approval_switch") != "ApproveLiveDeploy":
            errors.append("live_promotion_approval_invalid")
        if promotion.get("verification") != "stage_live_sha256_match":
            errors.append("live_promotion_verification_invalid")
        if promotion.get("helper_version") != helper_version:
            errors.append("live_promotion_helper_version_mismatch")
        verified_file_count = promotion.get("verified_file_count")
        if (
            not isinstance(verified_file_count, int)
            or isinstance(verified_file_count, bool)
            or verified_file_count != len(entries)
        ):
            errors.append("live_promotion_file_count_mismatch")

        recorded_manifest = promotion.get("live_manifest")
        if (
            not isinstance(recorded_manifest, str)
            or not Path(recorded_manifest).is_absolute()
            or not _same_canonical_path(Path(recorded_manifest), live_manifest_path)
        ):
            errors.append("live_promotion_manifest_path_mismatch")
        recorded_sha256 = promotion.get("live_manifest_sha256")
        if (
            not isinstance(recorded_sha256, str)
            or not SHA256_PATTERN.fullmatch(recorded_sha256)
            or recorded_sha256 != manifest_sha256
        ):
            errors.append("live_promotion_manifest_sha256_mismatch")
        recorded_client = promotion.get("live_client")
        if (
            not isinstance(recorded_client, str)
            or not Path(recorded_client).is_absolute()
            or not _same_canonical_path(Path(recorded_client), client_root)
        ):
            errors.append("live_promotion_client_path_mismatch")
        if promotion.get("created_at") != (manifest or {}).get("generated_at_utc"):
            errors.append("live_promotion_timestamp_mismatch")

    manifest_safe_for_diagnostics = bool(
        isinstance(manifest, dict)
        and manifest_load_status == "loaded"
        and manifest.get("schema_version") == LIVE_MANIFEST_SCHEMA
        and isinstance(manifest.get("generated_at_utc"), str)
        and 0 < len(manifest["generated_at_utc"]) <= 64
        and isinstance(manifest.get("helper_version"), str)
        and 0 < len(manifest["helper_version"]) <= 32
        and entries
        and not entry_errors
    )
    trusted = not errors
    remediation = _pin_remediation(errors)
    summary = {
        "status": "trusted" if trusted else "untrusted",
        "trusted": trusted,
        "errors": errors,
        "manifest_load_status": manifest_load_status,
        "promotion_load_status": promotion_load_status,
        "manifest_sha256": manifest_sha256,
        "helper_version": helper_version or "unknown",
        "manifest_file_count": len(entries),
        "declared_total_bytes": declared_total,
        "manifest_safe_for_diagnostics": manifest_safe_for_diagnostics,
        "remediation": remediation,
    }
    return (entries if trusted or manifest_safe_for_diagnostics else []), summary


def _pin_remediation(errors: list[str]) -> dict[str, Any]:
    error_set = set(errors)
    if not error_set:
        classification = "trusted"
        required_action = "none"
    elif any(
        error == f"{prefix}_{status}"
        for prefix in ("live_manifest", "live_promotion")
        for status in PIN_LOAD_STATUSES
        for error in error_set
    ):
        classification = "missing_or_unreadable_attestation"
        required_action = "refresh_official_live_promotion_after_current_gates"
    elif "live_manifest_origin_invalid" in error_set and error_set.intersection(
        {
            "live_promotion_manifest_path_mismatch",
            "live_promotion_manifest_sha256_mismatch",
            "live_promotion_timestamp_mismatch",
        }
    ):
        classification = "legacy_or_unbound_attestation"
        required_action = "refresh_official_live_promotion_after_current_gates"
    else:
        classification = "invalid_or_mismatched_attestation"
        required_action = "refresh_official_live_promotion_after_current_gates"
    blocked = classification != "trusted"
    return {
        "classification": classification,
        "required_action": required_action,
        "observer_can_write_trust_anchor": False,
        "historical_rebinding_allowed": False,
        "requires_current_release_gate": blocked,
        "requires_explicit_live_approval": blocked,
    }


def inspect_live_manifest(
    entries: list[dict[str, Any]],
    pin: dict[str, Any],
    client_root: Path,
) -> tuple[dict[str, Any], dict[str, tuple[str, int, int]]]:
    base = {
        "pin_status": pin.get("status", "untrusted"),
        "pin_trusted": pin.get("trusted") is True,
        "pin_errors": list(pin.get("errors") or []),
        "manifest_sha256": str(pin.get("manifest_sha256") or ""),
        "helper_version": str(pin.get("helper_version") or "unknown"),
        "manifest_file_count": int(pin.get("manifest_file_count") or 0),
        "declared_total_bytes": int(pin.get("declared_total_bytes") or 0),
        "pin_remediation": dict(pin.get("remediation") or {}),
        "diagnostic_parity": {
            "attempted": False,
            "status": "not_required" if pin.get("trusted") is True else "unavailable",
            "manifest_file_count": int(pin.get("manifest_file_count") or 0),
            "matched_file_count": 0,
            "mismatch_count": 0,
            "mutable_drift_count": 0,
            "profile_drift_count": 0,
            "missing_count": 0,
            "invalid_path_count": 0,
            "oversize_count": 0,
            "actual_total_bytes": 0,
            "stable_during_observation": False,
            "acceptance_allowed": False,
        },
        "matched_file_count": 0,
        "mismatch_count": 0,
        "mutable_drift_count": 0,
        "profile_drift_count": 0,
        "missing_count": 0,
        "invalid_path_count": 0,
        "oversize_count": 0,
        "actual_total_bytes": 0,
    }
    details, fingerprints = _inspect_manifest_entries(entries, client_root)
    if pin.get("trusted") is not True:
        diagnostic_attempted = bool(
            pin.get("manifest_safe_for_diagnostics") is True and entries
        )
        diagnostic = {
            **base["diagnostic_parity"],
            **(details if diagnostic_attempted else {}),
            "attempted": diagnostic_attempted,
            "status": details["status"] if diagnostic_attempted else "unavailable",
            "acceptance_allowed": False,
        }
        return {
            **base,
            "status": "untrusted_pin",
            "diagnostic_parity": diagnostic,
        }, (fingerprints if diagnostic_attempted else {})
    return {**base, **details}, fingerprints


def _inspect_manifest_entries(
    entries: list[dict[str, Any]], client_root: Path
) -> tuple[dict[str, Any], dict[str, tuple[str, int, int]]]:
    matched = 0
    mismatch = 0
    profile_drift = 0
    missing = 0
    invalid = 0
    oversize = 0
    actual_total = 0
    fingerprints: dict[str, tuple[str, int, int]] = {}
    for item in entries:
        relative = item["relative"]
        target = client_root / relative
        if not _is_within(target, client_root):
            invalid += 1
            continue
        remaining_budget = MAX_LIVE_TOTAL_BYTES - actual_total
        fingerprint, fingerprint_status = _file_fingerprint(target, remaining_budget)
        if fingerprint is None:
            if fingerprint_status == "missing":
                missing += 1
            elif fingerprint_status in {
                "file_oversize",
                "aggregate_budget_exceeded",
            }:
                oversize += 1
                if fingerprint_status == "aggregate_budget_exceeded":
                    break
            else:
                invalid += 1
            continue
        key = item["path"]
        fingerprints[key] = fingerprint
        actual_total += fingerprint[1]
        exact = fingerprint[0] == item["sha256"] and fingerprint[1] == item["bytes"]
        if exact:
            matched += 1
        elif key in PROFILE_RUNTIME_PATHS:
            profile_drift += 1
        else:
            mismatch += 1

    total = len(entries)
    passed = (
        matched == total
        and not mismatch
        and not profile_drift
        and not missing
        and not invalid
        and not oversize
        and actual_total <= MAX_LIVE_TOTAL_BYTES
    )
    return {
        "status": "passed" if passed else "failed",
        "manifest_file_count": total,
        "matched_file_count": matched,
        "mismatch_count": mismatch,
        "mutable_drift_count": profile_drift,
        "profile_drift_count": profile_drift,
        "missing_count": missing,
        "invalid_path_count": invalid,
        "oversize_count": oversize,
        "actual_total_bytes": actual_total,
    }, fingerprints


def _deterministic_capability_report(
    client_root: Path, explicit: Path | None
) -> tuple[str, Path | None]:
    expected = (
        client_root / "mods" / "ctoa_otclient" / "ctoa_client_capabilities.json"
    ).resolve(strict=False)
    if explicit is not None and not _same_canonical_path(explicit, expected):
        return "explicit_path_mismatch", None
    return "live_client/mods/ctoa_otclient/ctoa_client_capabilities.json", expected


def _select_log(client_root: Path) -> tuple[str, Path]:
    candidates = [
        ("live_client/ctoa_local.log", client_root / "ctoa_local.log"),
        ("live_client/otclient.log", client_root / "otclient.log"),
    ]
    existing: list[tuple[int, str, Path]] = []
    for label, path in candidates:
        try:
            metadata = path.lstat()
            if stat.S_ISREG(metadata.st_mode):
                existing.append((metadata.st_mtime_ns, label, path))
        except OSError:
            continue
    if not existing:
        return "missing", client_root / "ctoa_local.log"
    _, label, path = max(existing, key=lambda item: item[0])
    return label, path


def _fingerprints_unchanged(
    before: dict[str, tuple[str, int, int]],
    client_root: Path,
) -> bool:
    if not before:
        return False
    total_read = 0
    for relative, fingerprint in before.items():
        remaining_budget = MAX_LIVE_TOTAL_BYTES - total_read
        current, status = _file_fingerprint(
            client_root / Path(*PurePosixPath(relative).parts),
            remaining_budget,
        )
        if status != "loaded" or current != fingerprint:
            return False
        total_read += current[1]
    return True


def build_status(
    *,
    client_root: Path,
    live_manifest_path: Path,
    live_promotion_path: Path,
    process_count: int,
    process_start_unix_ms: int | None,
    explicit_report: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed_at = now or _utc_now()
    now_ms = int(observed_at.timestamp() * 1000)
    entries, pin = validate_live_pin(
        live_manifest_path, live_promotion_path, client_root
    )
    integrity, fingerprints = inspect_live_manifest(entries, pin, client_root)

    report_label, report_path = _deterministic_capability_report(
        client_root, explicit_report
    )
    capability_payload: dict[str, Any] | None = None
    capability_load_status = (
        "explicit_path_mismatch" if report_path is None else "missing"
    )
    if report_path is not None:
        capability_payload, capability_load_status = load_json_bounded(report_path)
    capability = summarize_capability(
        capability_payload,
        capability_load_status,
        now_ms,
        process_start_unix_ms=process_start_unix_ms,
        expected_helper_version=(
            str(pin.get("helper_version")) if pin.get("trusted") is True else None
        ),
    )
    capability["source"] = report_label

    log_label, log_path = _select_log(client_root)
    log_summary = summarize_log(log_path, observed_at)
    log_summary["source"] = log_label
    unchanged = _fingerprints_unchanged(fingerprints, client_root)
    if pin.get("trusted") is True:
        integrity["live_files_unchanged_during_observation"] = unchanged
    else:
        integrity["live_files_unchanged_during_observation"] = False
        diagnostic_parity = integrity.get("diagnostic_parity")
        if isinstance(diagnostic_parity, dict):
            diagnostic_parity["stable_during_observation"] = unchanged
    integrity["baseline"] = "live_manifest"
    integrity["baseline_recorded"] = False

    process_count_valid = (
        isinstance(process_count, int)
        and not isinstance(process_count, bool)
        and process_count >= 0
    )
    exact_process = process_count_valid and process_count == 1
    process_start_valid = (
        isinstance(process_start_unix_ms, int)
        and not isinstance(process_start_unix_ms, bool)
        and 0 < process_start_unix_ms <= now_ms
    )
    process_state = (
        "running"
        if exact_process
        else "not_running"
        if process_count_valid and process_count == 0
        else "ambiguous"
    )

    blockers: list[str] = []
    if pin.get("trusted") is not True:
        blockers.append("live_manifest_pin_untrusted")
    elif integrity.get("status") != "passed":
        blockers.append("live_manifest_parity_failed")
    if pin.get("trusted") is True and not unchanged:
        blockers.append("live_files_changed_or_unverifiable")
    if not process_count_valid or process_count > 1:
        blockers.append("active_client_process_count_invalid")
    if exact_process and not process_start_valid:
        blockers.append("active_client_process_start_invalid")

    hard_capability_failures = {
        "unsafe_runtime_claim",
        "schema_mismatch",
        "invalid_contract",
        "version_mismatch",
        "invalid_heartbeat",
        "heartbeat_before_process",
        "malformed",
        "oversize",
        "symlink_rejected",
        "not_regular",
        "not_object",
        "changed_during_open",
        "unreadable",
        "explicit_path_mismatch",
    }
    if capability.get("status") in hard_capability_failures:
        blockers.append(f"capability_{capability['status']}")
    if exact_process and log_summary.get("lua_exception_count", 0) > 0:
        blockers.append("current_session_lua_exception")

    ready = bool(
        not blockers
        and exact_process
        and process_start_valid
        and pin.get("trusted") is True
        and integrity.get("status") == "passed"
        and unchanged
        and capability.get("fresh") is True
        and capability.get("contract_valid") is True
        and capability.get("version_match") is True
        and capability.get("heartbeat_after_process_start") is True
    )
    if blockers:
        status_value = "blocked"
    elif ready:
        status_value = "ready"
    elif process_count_valid and process_count == 0:
        status_value = "idle"
    elif exact_process:
        status_value = "waiting_for_passive_heartbeat"
    else:
        status_value = "observation_pending"

    checks = {
        "no_screen_contract": True,
        "trusted_live_manifest_pin": pin.get("trusted") is True,
        "live_manifest_parity": integrity.get("status") == "passed",
        "live_files_unchanged": unchanged,
        "exact_active_client_process": exact_process,
        "active_client_process_start_valid": process_start_valid,
        "fresh_online_heartbeat": capability.get("fresh") is True,
        "helper_version_match": capability.get("version_match") is True,
        "capability_fail_closed": capability.get("contract_valid") is True,
        "current_session_lua_clean": log_summary.get("lua_exception_count", 0) == 0,
    }
    next_action = {
        "ready": "Continue passive observation; no GUI action is required.",
        "idle": "Wait for the user to start the client, then collect background status again.",
        "waiting_for_passive_heartbeat": "Keep the client untouched; wait for a fresh deterministic capability heartbeat.",
        "observation_pending": "Collect another passive sample without launching or focusing a client.",
        "blocked": (
            "Keep the evidence blocked and do not synthesize or rebind a trust anchor. "
            "A new pin requires current sandbox/release gates plus explicit operator approval "
            "for the official live-promotion path."
            if pin.get("trusted") is not True
            else "Fix the reported evidence blocker offline; do not interact with the user's client."
        ),
    }[status_value]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": observed_at.isoformat(timespec="seconds"),
        "status": status_value,
        "mode": "background_no_screen",
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "promotion_allowed": False,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "process_state": process_state,
        "process_count": process_count,
        "process_start_unix_ms": process_start_unix_ms,
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
        "checks": checks,
        "passed_check_count": sum(checks.values()),
        "check_count": len(checks),
        "integrity": integrity,
        "capability": capability,
        "log": log_summary,
        "blockers": blockers,
        "next_action": next_action,
        "intrusive_actions_performed": [],
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-root",
        type=Path,
        default=Path(os.environ.get("LOCALAPPDATA", "")) / "Solteria" / "client",
    )
    parser.add_argument("--dev-dir", type=Path, default=DEFAULT_DEV_DIR)
    parser.add_argument(
        "--capability-report",
        type=Path,
        default=(
            Path(os.environ["CTOA_HELPER_CLIENT_STATE_PATH"])
            if os.environ.get("CTOA_HELPER_CLIENT_STATE_PATH")
            else None
        ),
    )
    parser.add_argument("--process-count", type=int, required=True)
    parser.add_argument("--process-start-unix-ms", type=int, required=True)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print JSON only; do not write a runtime evidence artifact.",
    )
    parser.add_argument(
        "--require-fresh",
        action="store_true",
        help="Return non-zero unless a fresh passive heartbeat is ready.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    local_app_data_text = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data_text:
        print("LOCALAPPDATA is required", file=sys.stderr)
        return 2
    local_app_data = Path(local_app_data_text).resolve(strict=False)
    expected_client_root = local_app_data / "Solteria" / "client"
    try:
        client_root = _require_exact(
            args.client_root, expected_client_root, "client root"
        )
        client_root = _require_within(client_root, local_app_data, "client root")
        expected_dev_dir = RUNTIME_ROOT / "solteria_helper_dev"
        dev_dir = _require_exact(args.dev_dir, expected_dev_dir, "dev dir")
        dev_dir = _require_within(dev_dir, RUNTIME_ROOT, "dev dir")
        output = _require_exact(
            args.json_out,
            dev_dir / "background_status.json",
            "JSON output",
        )
        live_manifest_path = _require_within(
            dev_dir / "live_manifest.json", dev_dir, "live manifest"
        )
        live_promotion_path = _require_within(
            dev_dir / "live_promotion.json", dev_dir, "live promotion"
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = build_status(
        client_root=client_root,
        live_manifest_path=live_manifest_path,
        live_promotion_path=live_promotion_path,
        process_count=args.process_count,
        process_start_unix_ms=args.process_start_unix_ms,
        explicit_report=args.capability_report,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.no_write:
        print(rendered)
    else:
        write_json_atomic(output, payload)
        print(f"[otclient-headless-status] JSON: {output}")
        print(f"[otclient-headless-status] Status: {payload['status']}")
        print(f"[otclient-headless-status] Next: {payload['next_action']}")

    if payload["status"] == "blocked":
        return 1
    if args.require_fresh and payload["status"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
