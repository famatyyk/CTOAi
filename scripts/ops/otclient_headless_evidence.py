#!/usr/bin/env python3
"""Shared, bounded readers for passive OTClient evidence.

This module never launches, stops, focuses, captures, or writes to a client.
It only parses already-existing capability and log evidence.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_CAPABILITY_BYTES = 64 * 1024
MAX_CONDITIONS_OBSERVATION_BYTES = 4 * 1024
MAX_EQUIPMENT_SHADOW_OBSERVATION_BYTES = 24 * 1024
MAX_HEAL_FRIEND_SCAN_BYTES = 24 * 1024
MAX_LOG_TAIL_BYTES = 256 * 1024
CAPABILITY_SCHEMA = "ctoa-client-capabilities-v1"
CONDITIONS_OBSERVATION_SCHEMA = "ctoa.conditions-observation.v1"
EQUIPMENT_SHADOW_OBSERVATION_SCHEMA = "ctoa.equipment-shadow-observation.v1"
HEAL_FRIEND_SCAN_SCHEMA = "ctoa.heal-friend-scan.v1"
EXPECTED_HEARTBEAT_INTERVAL_MS = 5_000
MAX_HEARTBEAT_AGE_MS = 15_000
INITIALIZED_PATTERN = re.compile(r"Initialized successfully v[0-9][^\s]*")
API_PROBE_PATTERN = re.compile(r"\[CTOA-OTC-HELPER\] API probe \((startup|manual)\):")
RUNTIME_PATTERN = re.compile(r"\[CTOA-OTC-HELPER\] Runtime (armed|disarmed)(?::|\b)")
LOG_TIMESTAMP_PATTERN = re.compile(
    r"^\[?(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)"
)
CONDITIONS_OBSERVATION_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
CONDITIONS_OBSERVATION_FIELDS = frozenset(
    {
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
        "dispatch_allowed",
        "runtime_actions",
        "executes_plan",
        "execute_once_allowed",
        "promotion_allowed",
    }
)
CONDITIONS_ACTION_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)
EQUIPMENT_SHADOW_OBSERVATION_FIELDS = frozenset(
    {
        "schema_version",
        "observed_at_unix_ms",
        "observation_id",
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
        *CONDITIONS_ACTION_FLAGS,
    }
)
HEAL_FRIEND_SCAN_ACTION_FLAGS = (*CONDITIONS_ACTION_FLAGS, "casts", "talks")
HEAL_FRIEND_SCAN_FIELDS = frozenset(
    {
        "schema_version", "observed_at_unix_ms", "party_observed_at_unix_ms",
        "observation_id", "online", "alive", "protection_zone",
        "protection_zone_source", "self_id", "scan_complete", "candidates",
        "cooldown", "cooldown_source", "producer_source",
        *HEAL_FRIEND_SCAN_ACTION_FLAGS,
    }
)
_MISSING = object()


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
    return parse_json_object_bytes(raw)


def parse_json_object_bytes(raw: bytes) -> tuple[dict[str, Any] | None, str]:
    """Strictly decode one already-bounded JSON object without rereading it."""

    try:
        if not raw:
            return None, "empty"
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_json_object_without_duplicates,
            parse_constant=_reject_json_non_finite,
            parse_float=_json_finite_float,
        )
    except (UnicodeError, ValueError, RecursionError):
        return None, "malformed"
    if not _json_shape_within_bounds(payload):
        return None, "malformed"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, "loaded"


def _json_object_without_duplicates(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_non_finite(value: str) -> Any:
    raise ValueError(f"non-finite JSON number: {value}")


def _json_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number")
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


def _normalized_conditions_observation(
    status: str, errors: list[str]
) -> dict[str, Any]:
    return {
        "status": status,
        "present": status != "missing",
        "valid": False,
        "schema_version": "unknown",
        "observed_at_unix_ms": None,
        "observation_id": "",
        "online": "unknown",
        "alive": "unknown",
        "protection_zone": "unknown",
        "protection_zone_source": "unavailable",
        "condition_id": "paralyze",
        "condition_state": "unknown",
        "cooldown": "unknown",
        "cooldown_source": "unavailable",
        "producer_source": "unknown",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "validation_errors": errors,
        "p9_blocker": (
            "conditions_observation_missing"
            if status == "missing"
            else "conditions_observation_invalid"
        ),
    }


def summarize_conditions_observation(
    value: Any = _MISSING,
    *,
    expected_observed_at_unix_ms: int | None = None,
    require_timestamp_binding: bool = False,
) -> dict[str, Any]:
    """Strictly validate and normalize the optional passive P9 observation.

    Missing data is intentionally distinct from malformed data so a v2.2.1
    heartbeat remains valid P8 evidence while both states stay blocked for P9.
    No unvalidated strings or nested values are copied to the result.
    """

    if value is _MISSING:
        return _normalized_conditions_observation("missing", [])
    if not isinstance(value, dict):
        return _normalized_conditions_observation("invalid", ["object_type"])

    errors: list[str] = []
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        encoded = b""
        errors.append("encoding")
    if len(encoded) > MAX_CONDITIONS_OBSERVATION_BYTES:
        errors.append("oversize")

    keys = frozenset(value)
    if CONDITIONS_OBSERVATION_FIELDS - keys:
        errors.append("fields_missing")
    if keys - CONDITIONS_OBSERVATION_FIELDS:
        errors.append("fields_extra")
    if value.get("schema_version") != CONDITIONS_OBSERVATION_SCHEMA:
        errors.append("schema_version")

    observed_at = value.get("observed_at_unix_ms")
    observed_at_valid = (
        isinstance(observed_at, int)
        and not isinstance(observed_at, bool)
        and 1 <= observed_at <= 9_999_999_999_999
    )
    if not observed_at_valid:
        errors.append("observed_at_unix_ms")
    elif (
        isinstance(expected_observed_at_unix_ms, int)
        and not isinstance(expected_observed_at_unix_ms, bool)
        and observed_at != expected_observed_at_unix_ms
    ):
        errors.append("observed_at_mismatch")
    elif require_timestamp_binding and not (
        isinstance(expected_observed_at_unix_ms, int)
        and not isinstance(expected_observed_at_unix_ms, bool)
    ):
        errors.append("parent_observed_at_unbound")

    observation_id = value.get("observation_id")
    if not (
        isinstance(observation_id, str)
        and CONDITIONS_OBSERVATION_ID_PATTERN.fullmatch(observation_id)
    ):
        errors.append("observation_id")

    enum_fields = {
        "online": {"online", "offline", "unknown"},
        "alive": {"alive", "dead", "unknown"},
        "protection_zone": {"outside", "inside", "unknown"},
        "protection_zone_source": {
            "player_method",
            "player_states",
            "unavailable",
        },
        "condition_id": {"paralyze"},
        "condition_state": {"present", "absent", "unknown"},
        "cooldown": {"ready", "active", "unknown"},
        "cooldown_source": {"game_cooldown_group", "unavailable"},
        "producer_source": {"otclient_guarded_adapter", "fixture"},
    }
    for field, allowed in enum_fields.items():
        enum_value = value.get(field)
        if not isinstance(enum_value, str) or enum_value not in allowed:
            errors.append(f"{field}_enum")
    for field in CONDITIONS_ACTION_FLAGS:
        if value.get(field) is not False:
            errors.append(f"{field}_unsafe")

    if errors:
        return _normalized_conditions_observation("invalid", errors)

    return {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": CONDITIONS_OBSERVATION_SCHEMA,
        "observed_at_unix_ms": observed_at,
        "observation_id": observation_id,
        "online": value["online"],
        "alive": value["alive"],
        "protection_zone": value["protection_zone"],
        "protection_zone_source": value["protection_zone_source"],
        "condition_id": "paralyze",
        "condition_state": value["condition_state"],
        "cooldown": value["cooldown"],
        "cooldown_source": value["cooldown_source"],
        "producer_source": value["producer_source"],
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "validation_errors": [],
        "p9_blocker": None,
    }


def _normalized_equipment_shadow_observation(
    status: str, errors: list[str]
) -> dict[str, Any]:
    return {
        "status": status,
        "present": status != "missing",
        "valid": False,
        "schema_version": "unknown",
        "observed_at_unix_ms": None,
        "observation_id": "",
        "online": "unknown",
        "alive": "unknown",
        "protection_zone": "unknown",
        "protection_zone_source": "unavailable",
        "inventory_api_available": False,
        "containers_complete": False,
        "ring": {"present": False, "item_id": 0, "count": 0},
        "candidates": [],
        "cooldown": "unknown",
        "cooldown_source": "unavailable",
        "producer_source": "unknown",
        **{field: False for field in CONDITIONS_ACTION_FLAGS},
        "validation_errors": errors,
        "p10_blocker": (
            "equipment_observation_missing"
            if status == "missing"
            else "equipment_observation_invalid"
        ),
    }


def _bounded_int(value: Any, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def summarize_equipment_shadow_observation(
    value: Any = _MISSING,
    *,
    expected_observed_at_unix_ms: int | None = None,
    require_timestamp_binding: bool = False,
) -> dict[str, Any]:
    if value is _MISSING:
        return _normalized_equipment_shadow_observation("missing", [])
    if not isinstance(value, dict):
        return _normalized_equipment_shadow_observation("invalid", ["object_type"])
    errors: list[str] = []
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError):
        encoded = b""
        errors.append("encoding")
    if len(encoded) > MAX_EQUIPMENT_SHADOW_OBSERVATION_BYTES:
        errors.append("oversize")
    keys = frozenset(value)
    if EQUIPMENT_SHADOW_OBSERVATION_FIELDS - keys:
        errors.append("fields_missing")
    if keys - EQUIPMENT_SHADOW_OBSERVATION_FIELDS:
        errors.append("fields_extra")
    if value.get("schema_version") != EQUIPMENT_SHADOW_OBSERVATION_SCHEMA:
        errors.append("schema_version")
    observed_at = value.get("observed_at_unix_ms")
    if not _bounded_int(observed_at, 1, 9_999_999_999_999):
        errors.append("observed_at_unix_ms")
    elif isinstance(expected_observed_at_unix_ms, int) and observed_at != expected_observed_at_unix_ms:
        errors.append("observed_at_mismatch")
    elif require_timestamp_binding and not isinstance(expected_observed_at_unix_ms, int):
        errors.append("parent_observed_at_unbound")
    observation_id = value.get("observation_id")
    if not (
        isinstance(observation_id, str)
        and CONDITIONS_OBSERVATION_ID_PATTERN.fullmatch(observation_id)
    ):
        errors.append("observation_id")
    enum_fields = {
        "online": {"online", "offline", "unknown"},
        "alive": {"alive", "dead", "unknown"},
        "protection_zone": {"outside", "inside", "unknown"},
        "protection_zone_source": {
            "player_method",
            "player_states",
            "unavailable",
        },
        "cooldown": {"ready", "active", "unknown"},
        "cooldown_source": {"game_cooldown_group", "unavailable"},
        "producer_source": {"otclient_guarded_adapter", "fixture"},
    }
    for field, allowed in enum_fields.items():
        if value.get(field) not in allowed:
            errors.append(f"{field}_enum")
    for field in ("inventory_api_available", "containers_complete"):
        if not isinstance(value.get(field), bool):
            errors.append(field)
    for field in CONDITIONS_ACTION_FLAGS:
        if value.get(field) is not False:
            errors.append(f"{field}_unsafe")
    ring = value.get("ring")
    if not (
        isinstance(ring, dict)
        and set(ring) == {"present", "item_id", "count"}
        and isinstance(ring.get("present"), bool)
        and _bounded_int(ring.get("item_id"), 0, 65535)
        and _bounded_int(ring.get("count"), 0, 65535)
    ):
        errors.append("ring")
    candidates = value.get("candidates")
    clean_candidates: list[dict[str, int]] = []
    if not isinstance(candidates, list) or len(candidates) > 256:
        errors.append("candidates")
    else:
        seen_positions: set[tuple[int, int]] = set()
        previous: tuple[int, int, int] | None = None
        for item in candidates:
            valid = (
                isinstance(item, dict)
                and set(item) == {"container_id", "slot_index", "item_id", "count"}
                and _bounded_int(item.get("container_id"), 0, 65535)
                and _bounded_int(item.get("slot_index"), 1, 65535)
                and _bounded_int(item.get("item_id"), 1, 65535)
                and _bounded_int(item.get("count"), 1, 65535)
            )
            if not valid:
                errors.append("candidate_entry")
                break
            position = (item["container_id"], item["slot_index"])
            ordering = (*position, item["item_id"])
            if position in seen_positions or (previous is not None and ordering < previous):
                errors.append("candidate_order_or_duplicate")
                break
            seen_positions.add(position)
            previous = ordering
            clean_candidates.append(dict(item))
    if errors:
        return _normalized_equipment_shadow_observation("invalid", errors)
    assert isinstance(ring, dict)
    return {
        "status": "valid",
        "present": True,
        "valid": True,
        "schema_version": EQUIPMENT_SHADOW_OBSERVATION_SCHEMA,
        "observed_at_unix_ms": observed_at,
        "observation_id": observation_id,
        "online": value["online"],
        "alive": value["alive"],
        "protection_zone": value["protection_zone"],
        "protection_zone_source": value["protection_zone_source"],
        "inventory_api_available": value["inventory_api_available"],
        "containers_complete": value["containers_complete"],
        "ring": {"present": ring["present"], "item_id": ring["item_id"], "count": ring["count"]},
        "candidates": clean_candidates,
        "cooldown": value["cooldown"],
        "cooldown_source": value["cooldown_source"],
        "producer_source": value["producer_source"],
        **{field: False for field in CONDITIONS_ACTION_FLAGS},
        "validation_errors": [],
        "p10_blocker": None,
    }


def _normalized_heal_friend_scan(status: str, errors: list[str]) -> dict[str, Any]:
    return {
        "status": status, "present": status != "missing", "valid": False,
        "schema_version": "unknown", "observed_at_unix_ms": None,
        "party_observed_at_unix_ms": None, "observation_id": "",
        "online": "unknown", "alive": "unknown", "protection_zone": "unknown",
        "protection_zone_source": "unavailable", "self_id": 0,
        "scan_complete": False, "candidates": [], "cooldown": "unknown",
        "cooldown_source": "unavailable", "producer_source": "unknown",
        **{field: False for field in HEAL_FRIEND_SCAN_ACTION_FLAGS},
        "validation_errors": errors,
        "p11_blocker": "heal_friend_scan_missing" if status == "missing" else "heal_friend_scan_invalid",
    }


def summarize_heal_friend_scan(
    value: Any = _MISSING,
    *,
    expected_observed_at_unix_ms: int | None = None,
    require_timestamp_binding: bool = False,
) -> dict[str, Any]:
    if value is _MISSING:
        return _normalized_heal_friend_scan("missing", [])
    if not isinstance(value, dict):
        return _normalized_heal_friend_scan("invalid", ["object_type"])
    errors: list[str] = []
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    except (TypeError, ValueError):
        encoded = b""
        errors.append("encoding")
    if len(encoded) > MAX_HEAL_FRIEND_SCAN_BYTES:
        errors.append("oversize")
    keys = frozenset(value)
    if HEAL_FRIEND_SCAN_FIELDS - keys:
        errors.append("fields_missing")
    if keys - HEAL_FRIEND_SCAN_FIELDS:
        errors.append("fields_extra")
    if value.get("schema_version") != HEAL_FRIEND_SCAN_SCHEMA:
        errors.append("schema_version")
    observed_at = value.get("observed_at_unix_ms")
    party_at = value.get("party_observed_at_unix_ms")
    if not _bounded_int(observed_at, 1, 9_999_999_999_999):
        errors.append("observed_at_unix_ms")
    elif isinstance(expected_observed_at_unix_ms, int) and observed_at != expected_observed_at_unix_ms:
        errors.append("observed_at_mismatch")
    elif require_timestamp_binding and not isinstance(expected_observed_at_unix_ms, int):
        errors.append("parent_observed_at_unbound")
    if not _bounded_int(party_at, 1, 9_999_999_999_999) or party_at != observed_at:
        errors.append("party_observed_at_unix_ms")
    observation_id = value.get("observation_id")
    if not isinstance(observation_id, str) or not CONDITIONS_OBSERVATION_ID_PATTERN.fullmatch(observation_id):
        errors.append("observation_id")
    enum_fields = {
        "online": {"online", "offline", "unknown"}, "alive": {"alive", "dead", "unknown"},
        "protection_zone": {"outside", "inside", "unknown"},
        "protection_zone_source": {"player_method", "player_states", "unavailable"},
        "cooldown": {"ready", "active", "unknown"},
        "cooldown_source": {"game_cooldown_group", "unavailable"},
        "producer_source": {"otclient_guarded_adapter"},
    }
    for field, allowed in enum_fields.items():
        if value.get(field) not in allowed:
            errors.append(f"{field}_enum")
    if not _bounded_int(value.get("self_id"), 0, 2_147_483_647):
        errors.append("self_id")
    if not isinstance(value.get("scan_complete"), bool):
        errors.append("scan_complete")
    for field in HEAL_FRIEND_SCAN_ACTION_FLAGS:
        if value.get(field) is not False:
            errors.append(f"{field}_unsafe")
    candidates = value.get("candidates")
    clean: list[dict[str, Any]] = []
    previous: tuple[int, str] | None = None
    candidate_fields = {"target_id", "target_name", "hp_percent", "distance", "target_is_player", "target_is_self", "target_party_member", "target_visible", "target_same_floor"}
    if not isinstance(candidates, list) or len(candidates) > 64:
        errors.append("candidates")
    else:
        for candidate in candidates:
            valid = (
                isinstance(candidate, dict) and set(candidate) == candidate_fields
                and _bounded_int(candidate.get("target_id"), 1, 2_147_483_647)
                and isinstance(candidate.get("target_name"), str)
                and re.fullmatch(r"[a-z][a-z0-9 ]{0,63}", candidate["target_name"]) is not None
                and candidate["target_name"] == " ".join(candidate["target_name"].split())
                and _bounded_int(candidate.get("hp_percent"), 0, 100)
                and _bounded_int(candidate.get("distance"), 0, 255)
                and all(isinstance(candidate.get(field), bool) for field in candidate_fields if field.startswith("target_") and field not in {"target_id", "target_name"})
            )
            if not valid:
                errors.append("candidate_entry")
                break
            ordering = (candidate["target_id"], candidate["target_name"])
            if previous is not None and ordering < previous:
                errors.append("candidate_order")
                break
            previous = ordering
            clean.append(dict(candidate))
    if errors:
        return _normalized_heal_friend_scan("invalid", errors)
    return {
        "status": "valid", "present": True, "valid": True,
        "schema_version": HEAL_FRIEND_SCAN_SCHEMA, "observed_at_unix_ms": observed_at,
        "party_observed_at_unix_ms": party_at, "observation_id": observation_id,
        "online": value["online"], "alive": value["alive"],
        "protection_zone": value["protection_zone"],
        "protection_zone_source": value["protection_zone_source"],
        "self_id": value["self_id"], "scan_complete": value["scan_complete"],
        "candidates": clean, "cooldown": value["cooldown"],
        "cooldown_source": value["cooldown_source"], "producer_source": value["producer_source"],
        **{field: False for field in HEAL_FRIEND_SCAN_ACTION_FLAGS},
        "validation_errors": [], "p11_blocker": None,
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
            "conditions_observation": summarize_conditions_observation(),
            "equipment_shadow_observation": summarize_equipment_shadow_observation(),
            "heal_friend_scan": summarize_heal_friend_scan(),
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

    conditions_value = (
        payload["conditions_observation"]
        if "conditions_observation" in payload
        else _MISSING
    )
    conditions_observation = summarize_conditions_observation(
        conditions_value,
        expected_observed_at_unix_ms=observed if observed_valid else None,
        require_timestamp_binding=True,
    )
    equipment_value = (
        payload["equipment_shadow_observation"]
        if "equipment_shadow_observation" in payload
        else _MISSING
    )
    equipment_shadow_observation = summarize_equipment_shadow_observation(
        equipment_value,
        expected_observed_at_unix_ms=observed if observed_valid else None,
        require_timestamp_binding=True,
    )
    heal_friend_value = payload["heal_friend_scan"] if "heal_friend_scan" in payload else _MISSING
    heal_friend_scan = summarize_heal_friend_scan(
        heal_friend_value,
        expected_observed_at_unix_ms=observed if observed_valid else None,
        require_timestamp_binding=True,
    )
    nested_conditions_actions = bool(
        isinstance(conditions_value, dict)
        and any(
            conditions_value.get(field) is True for field in CONDITIONS_ACTION_FLAGS
        )
    )
    nested_equipment_actions = bool(
        isinstance(equipment_value, dict)
        and any(equipment_value.get(field) is True for field in CONDITIONS_ACTION_FLAGS)
    )
    nested_heal_friend_actions = bool(
        isinstance(heal_friend_value, dict)
        and any(heal_friend_value.get(field) is True for field in HEAL_FRIEND_SCAN_ACTION_FLAGS)
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
    unsafe = runtime_actions or runtime_core_actions or nested_conditions_actions or nested_equipment_actions or nested_heal_friend_actions
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
        and not nested_conditions_actions
        and not nested_equipment_actions
        and not nested_heal_friend_actions
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
        "conditions_observation": conditions_observation,
        "equipment_shadow_observation": equipment_shadow_observation,
        "heal_friend_scan": heal_friend_scan,
    }
