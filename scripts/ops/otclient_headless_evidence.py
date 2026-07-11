#!/usr/bin/env python3
"""Shared, bounded readers for passive OTClient evidence.

This module never launches, stops, focuses, captures, or writes to a client.
It only parses already-existing capability and log evidence.
"""

from __future__ import annotations

import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_CAPABILITY_BYTES = 64 * 1024
MAX_LOG_TAIL_BYTES = 256 * 1024
CAPABILITY_SCHEMA = "ctoa-client-capabilities-v1"
EXPECTED_HEARTBEAT_INTERVAL_MS = 5_000
MAX_HEARTBEAT_AGE_MS = 15_000
INITIALIZED_PATTERN = re.compile(r"Initialized successfully v[0-9][^\s]*")
API_PROBE_PATTERN = re.compile(r"\[CTOA-OTC-HELPER\] API probe \((startup|manual)\):")
RUNTIME_PATTERN = re.compile(r"\[CTOA-OTC-HELPER\] Runtime (armed|disarmed)(?::|\b)")
LOG_TIMESTAMP_PATTERN = re.compile(
    r"^\[?(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)"
)


def _regular_file_lstat(path: Path) -> tuple[os.stat_result | None, str]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "unreadable"
    if stat.S_ISLNK(metadata.st_mode):
        return None, "symlink_rejected"
    if not stat.S_ISREG(metadata.st_mode):
        return None, "not_regular"
    return metadata, "regular"


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def read_bytes_bounded(path: Path, max_bytes: int) -> tuple[bytes | None, str]:
    """Open one regular file and read at most ``max_bytes + 1`` bytes."""

    if max_bytes <= 0:
        return None, "invalid_limit"
    before, status = _regular_file_lstat(path)
    if before is None:
        return None, status
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or not _same_file_identity(
                before, opened
            ):
                return None, "changed_during_open"
            payload = handle.read(max_bytes + 1)
    except FileNotFoundError:
        return None, "changed_during_open"
    except OSError:
        return None, "unreadable"
    if len(payload) > max_bytes:
        return None, "oversize"
    return payload, "loaded"


def bounded_tail_text(path: Path, max_bytes: int = MAX_LOG_TAIL_BYTES) -> str:
    """Read at most ``max_bytes`` from the end of a regular non-link file."""

    if max_bytes <= 0:
        return ""
    before, status = _regular_file_lstat(path)
    if before is None or status != "regular":
        return ""
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or not _same_file_identity(
                before, opened
            ):
                return ""
            size = opened.st_size
            if size > max_bytes:
                handle.seek(size - max_bytes)
            payload = handle.read(max_bytes)
    except OSError:
        return ""
    if size > max_bytes and payload:
        newline = payload.find(b"\n")
        payload = payload[newline + 1 :] if newline >= 0 else b""
    return payload.decode("utf-8", errors="replace")


def load_json_bounded(
    path: Path, max_bytes: int = MAX_CAPABILITY_BYTES
) -> tuple[dict[str, Any] | None, str]:
    """Return a bounded JSON object plus a fail-closed status."""

    raw, load_status = read_bytes_bounded(path, max_bytes)
    if raw is None:
        return None, load_status
    try:
        if not raw:
            return None, "empty"
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return None, "malformed"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, "loaded"


def current_session(log_text: str) -> str:
    """Return only the latest helper session from a bounded log tail."""

    matches = list(INITIALIZED_PATTERN.finditer(log_text or ""))
    return (log_text or "")[matches[-1].start() :] if matches else ""


def latest_api_probe(session_text: str) -> str:
    lines = [
        line
        for line in (session_text or "").splitlines()
        if API_PROBE_PATTERN.search(line)
    ]
    return lines[-1] if lines else ""


def latest_runtime_state(session_text: str) -> str:
    markers = RUNTIME_PATTERN.findall(session_text or "")
    return markers[-1] if markers else "unknown"


def _line_age_ms(line: str, now: datetime) -> int | None:
    match = LOG_TIMESTAMP_PATTERN.search(line or "")
    if not match:
        return None
    try:
        parsed = datetime.fromisoformat(match.group(1).replace(" ", "T"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=now.astimezone().tzinfo)
    age = int(
        (now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        * 1_000
    )
    return age if 0 <= age <= 24 * 60 * 60 * 1_000 else None


def parse_api_probe(line: str, now: datetime | None = None) -> dict[str, Any]:
    hp_match = re.search(r"\bhp=(\d+)/(\d+)\b", line or "")
    pz_match = re.search(
        r"\bpz=(yes|no|true|false|inside|outside|nil|unknown)\b",
        line or "",
    )
    online = "core[online=yes" in (line or "")
    client_ready = "localPlayer=yes" in (line or "")
    alive = bool(hp_match and int(hp_match.group(1)) > 0)
    outside_pz: bool | None = None
    if pz_match and pz_match.group(1) in {"no", "false", "outside"}:
        outside_pz = True
    elif pz_match and pz_match.group(1) in {"yes", "true", "inside"}:
        outside_pz = False
    observed_now = now or datetime.now(timezone.utc)
    age_ms = _line_age_ms(line, observed_now)
    return {
        "present": bool(line),
        "fresh": age_ms is not None and age_ms <= 15_000,
        "age_ms": age_ms,
        "online": online,
        "client_ready": client_ready,
        "player_alive": alive,
        "outside_protection_zone": outside_pz,
    }


def summarize_log(path: Path, now: datetime | None = None) -> dict[str, Any]:
    observed_now = now or datetime.now(timezone.utc)
    text = bounded_tail_text(path)
    session = current_session(text)
    api_probe = latest_api_probe(session)
    version_match = INITIALIZED_PATTERN.search(session)
    return {
        "status": "current_session" if session else "no_current_session",
        "tail_bytes_limit": MAX_LOG_TAIL_BYTES,
        "session_version_marker": version_match.group(0) if version_match else "",
        "runtime_state": latest_runtime_state(session),
        "api_probe": parse_api_probe(api_probe, observed_now),
        "lua_exception_count": len(re.findall(r"Lua exception", session)),
        "combat_runtime_nil_count": len(
            re.findall(r"combatRuntimeText.*nil value", session)
        ),
    }


def summarize_capability(
    payload: dict[str, Any] | None,
    load_status: str,
    now_unix_ms: int,
    *,
    process_start_unix_ms: int | None = None,
    expected_helper_version: str | None = None,
) -> dict[str, Any]:
    """Sanitize a capability heartbeat and classify freshness fail-closed."""

    if payload is None:
        return {
            "status": load_status,
            "fresh": False,
            "schema_valid": False,
            "age_ms": None,
            "runtime_actions": False,
            "runtime_core_actions": False,
            "contract_valid": False,
            "version_match": False,
            "heartbeat_after_process_start": False,
        }

    schema_valid = payload.get("schema_version") == CAPABILITY_SCHEMA
    observed = payload.get("observed_at_unix_ms")
    interval = payload.get("heartbeat_interval_ms")
    observed_valid = (
        isinstance(observed, int) and not isinstance(observed, bool) and observed >= 0
    )
    interval_valid = (
        isinstance(interval, int)
        and not isinstance(interval, bool)
        and interval == EXPECTED_HEARTBEAT_INTERVAL_MS
    )
    age_ms = now_unix_ms - observed if observed_valid else None
    age_valid = isinstance(age_ms, int) and 0 <= age_ms <= 24 * 60 * 60 * 1000
    fresh_age = bool(age_valid and age_ms <= MAX_HEARTBEAT_AGE_MS)
    process_start_valid = (
        isinstance(process_start_unix_ms, int)
        and not isinstance(process_start_unix_ms, bool)
        and process_start_unix_ms > 0
        and process_start_unix_ms <= now_unix_ms
    )
    heartbeat_after_process_start = bool(
        observed_valid and process_start_valid and observed > process_start_unix_ms
    )

    runtime_actions_value = payload.get("runtime_actions")
    runtime_actions = runtime_actions_value is True
    runtime_actions_explicit_safe = runtime_actions_value is False
    core_present = isinstance(payload.get("runtime_core"), dict)
    core = payload.get("runtime_core") if core_present else {}
    runtime_core_actions_value = core.get("runtime_actions")
    runtime_core_actions = runtime_core_actions_value is True
    runtime_core_actions_explicit_safe = (
        core_present and runtime_core_actions_value is False
    )
    unsafe = runtime_actions or runtime_core_actions
    heartbeat_online = payload.get("heartbeat_status") == "online"
    game_online = payload.get("online") is True
    helper_version_value = payload.get("helper_version")
    helper_version_valid = (
        isinstance(helper_version_value, str) and 0 < len(helper_version_value) <= 32
    )
    version_match = bool(
        helper_version_valid
        and expected_helper_version
        and helper_version_value == expected_helper_version
    )
    contract_valid = bool(
        runtime_actions_explicit_safe
        and runtime_core_actions_explicit_safe
        and heartbeat_online
        and game_online
        and helper_version_valid
    )
    fresh = bool(
        schema_valid
        and observed_valid
        and interval_valid
        and fresh_age
        and heartbeat_after_process_start
        and contract_valid
        and version_match
    )
    if unsafe:
        status = "unsafe_runtime_claim"
    elif not schema_valid:
        status = "schema_mismatch"
    elif (
        not helper_version_valid
        or not runtime_actions_explicit_safe
        or not runtime_core_actions_explicit_safe
    ):
        status = "invalid_contract"
    elif expected_helper_version and not version_match:
        status = "version_mismatch"
    elif not observed_valid or not interval_valid or not age_valid:
        status = "invalid_heartbeat"
    elif not process_start_valid or not heartbeat_after_process_start:
        status = "heartbeat_before_process"
    elif not heartbeat_online:
        status = "heartbeat_offline"
    elif not game_online:
        status = "game_offline"
    elif fresh:
        status = "fresh"
    else:
        status = "stale"

    supported_modules = payload.get("supported_modules")
    module_count = len(supported_modules) if isinstance(supported_modules, list) else 0
    return {
        "status": status,
        "fresh": fresh,
        "schema_valid": schema_valid,
        "age_ms": age_ms if isinstance(age_ms, int) else None,
        "freshness_limit_ms": MAX_HEARTBEAT_AGE_MS,
        "heartbeat_status": str(payload.get("heartbeat_status") or "unknown"),
        "online": game_online,
        "helper_version": str(payload.get("helper_version") or "unknown")[:32],
        "protocol_status": str(payload.get("protocol_status") or "unknown")[:64],
        "safe_fallback": payload.get("safe_fallback") is True,
        "runtime_actions": runtime_actions,
        "runtime_session_armed": payload.get("runtime_session_armed") is True,
        "runtime_state": str(payload.get("runtime_state") or "unknown")[:32],
        "runtime_enabled": payload.get("runtime_enabled") is True,
        "runtime_core_actions": runtime_core_actions,
        "runtime_core_status": str(core.get("status") or "unknown")[:32],
        "runtime_core_mode": str(core.get("mode") or "unknown")[:32],
        "supported_module_count": module_count,
        "contract_valid": contract_valid,
        "version_match": version_match,
        "heartbeat_after_process_start": heartbeat_after_process_start,
    }
