#!/usr/bin/env python3
"""Create a canonical P10 snapshot from passive BackgroundNoScreen evidence.

The producer never reads an OTClient installation directly and never moves or
uses an item. It consumes the sanitized equipment observation already embedded
in the canonical background report and fails closed until an operator persists
exact ring, candidate, and container identifiers.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as p9_replay
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as p9_replay


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_BACKGROUND = DEV_DIR / "background_status.json"
DEFAULT_CAPTURE_PROFILE = (
    ROOT / "config" / "otclient" / "equipment-shadow-capture-profile.template.json"
)
DEFAULT_LOCAL_CAPTURE_PROFILE = (
    ROOT / ".ctoa-local" / "otclient" / "equipment-shadow-capture-profile.json"
)
DEFAULT_SNAPSHOT = DEV_DIR / "equipment_shadow_snapshot.json"
DEFAULT_REPORT = DEV_DIR / "equipment_shadow_snapshot_ingest.json"

CAPTURE_SCHEMA = "ctoa.equipment-shadow-capture-profile.v1"
OBSERVATION_SCHEMA = "ctoa.equipment-shadow-observation.v1"
SNAPSHOT_SCHEMA = "ctoa.equipment-shadow-snapshot.v1"
REPORT_SCHEMA = "ctoa.equipment-shadow-snapshot-ingest.v1"
BACKGROUND_SCHEMA = "ctoa.otclient-headless-status.v1"
MAX_AGE_MS = 6000
CAPTURE_TRANSPORT_ALLOWANCE_MS = 1000
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)
BACKGROUND_INTERACTION_CONTRACT = {
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
BACKGROUND_WRAPPER_INVARIANTS = {
    "client_process_stable": True,
    "screenshot_count_stable": True,
}
BLOCKER_ORDER = (
    "background_missing",
    "background_invalid",
    "background_not_ready",
    "background_contract_invalid",
    "capture_profile_missing",
    "capture_profile_invalid",
    "capture_profile_not_configured",
    "equipment_observation_missing",
    "equipment_observation_invalid",
    "equipment_observation_future",
    "equipment_observation_stale",
    "player_offline",
    "player_dead",
    "protection_zone_inside",
    "protection_zone_unknown",
    "protection_zone_source_untrusted",
    "inventory_api_unavailable",
    "containers_incomplete",
    "ring_missing",
    "equipped_item_mismatch",
    "candidate_matches_equipped",
    "candidate_not_unique",
    "candidate_container_mismatch",
    "candidate_slot_mismatch",
    "cooldown_active",
    "cooldown_unknown",
    "cooldown_source_untrusted",
    "unsafe_contract",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}


def resolve_capture_profile(explicit: Path | None = None) -> tuple[Path, str]:
    """Select only the tracked template or the fixed ignored local override."""

    allowed = {
        os.path.normcase(str(DEFAULT_CAPTURE_PROFILE.resolve(strict=False))): (
            DEFAULT_CAPTURE_PROFILE,
            "tracked_safe_template",
        ),
        os.path.normcase(str(DEFAULT_LOCAL_CAPTURE_PROFILE.resolve(strict=False))): (
            DEFAULT_LOCAL_CAPTURE_PROFILE,
            "local_operator_override",
        ),
    }
    if explicit is not None:
        selected = allowed.get(os.path.normcase(str(explicit.resolve(strict=False))))
        if selected is None:
            raise ValueError(
                "capture profile must be the tracked safe template or fixed .ctoa-local override"
            )
        return selected
    if (
        DEFAULT_LOCAL_CAPTURE_PROFILE.exists()
        or DEFAULT_LOCAL_CAPTURE_PROFILE.is_symlink()
    ):
        return DEFAULT_LOCAL_CAPTURE_PROFILE, "local_operator_override"
    return DEFAULT_CAPTURE_PROFILE, "tracked_safe_template"


def load_capture_profile(path: Path, source: str) -> p9_replay.InputDocument:
    if source == "local_operator_override":
        current = ROOT.resolve(strict=False)
        try:
            relative = Path(os.path.abspath(path)).relative_to(
                Path(os.path.abspath(ROOT))
            )
        except ValueError:
            return p9_replay.InputDocument(None, "unreadable", p9_replay.ZERO_SHA256)
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        for part in relative.parts:
            current /= part
            try:
                metadata = current.lstat()
            except FileNotFoundError:
                break
            if (
                stat.S_ISLNK(metadata.st_mode)
                or int(getattr(metadata, "st_file_attributes", 0)) & reparse
            ):
                return p9_replay.InputDocument(
                    None, "symlink_rejected", p9_replay.ZERO_SHA256
                )
    document = p9_replay.read_document(path)
    if (
        source == "tracked_safe_template"
        and isinstance(document.payload, dict)
        and document.payload.get("configured_by_operator") is True
    ):
        return p9_replay.InputDocument(None, "unreadable", document.sha256)
    return document


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _false_flags(value: dict[str, Any]) -> bool:
    return all(value.get(key) is False for key in FALSE_FLAGS)


def _ordered(values: Iterable[str]) -> list[str]:
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)


def _capture_profile_valid(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload)
        == {
            "schema_version",
            "configured_by_operator",
            "slot",
            "equipped_item_id",
            "candidate_item_id",
            "candidate_source_container_id",
            "candidate_source_slot_index",
            "max_observation_age_ms",
            "retry_budget",
            *FALSE_FLAGS,
        }
        and payload.get("schema_version") == CAPTURE_SCHEMA
        and isinstance(payload.get("configured_by_operator"), bool)
        and payload.get("slot") == "ring"
        and all(
            _is_int(payload.get(key)) and 0 <= payload[key] <= 65535
            for key in (
                "equipped_item_id",
                "candidate_item_id",
                "candidate_source_container_id",
                "candidate_source_slot_index",
            )
        )
        and payload.get("max_observation_age_ms") == MAX_AGE_MS
        and payload.get("retry_budget") == 0
        and _false_flags(payload)
    )


def _observation_from_background(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    capability = payload.get("capability")
    if not isinstance(capability, dict):
        return None
    observation = capability.get("equipment_shadow_observation")
    return observation if isinstance(observation, dict) else None


def _observation_valid(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    required = {
        "status",
        "present",
        "valid",
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
        *FALSE_FLAGS,
        "validation_errors",
        "p10_blocker",
    }
    ring = payload.get("ring")
    candidates = payload.get("candidates")
    ring_valid = (
        isinstance(ring, dict)
        and set(ring) == {"present", "item_id", "count"}
        and isinstance(ring.get("present"), bool)
        and _is_int(ring.get("item_id"))
        and 0 <= ring["item_id"] <= 65535
        and _is_int(ring.get("count"))
        and 0 <= ring["count"] <= 65535
    )
    candidates_valid = isinstance(candidates, list) and len(candidates) <= 256
    identities: set[tuple[int, int]] = set()
    if candidates_valid:
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
                candidates_valid = False
                break
            identity = (item["container_id"], item["slot_index"])
            if identity in identities:
                candidates_valid = False
                break
            identities.add(identity)
    return (
        set(payload) == required
        and payload.get("status") == "valid"
        and payload.get("present") is True
        and payload.get("valid") is True
        and payload.get("schema_version") == OBSERVATION_SCHEMA
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload["observed_at_unix_ms"] > 0
        and isinstance(payload.get("observation_id"), str)
        and 1 <= len(payload["observation_id"]) <= 128
        and payload.get("producer_source") == "otclient_guarded_adapter"
        and payload.get("online") in {"online", "offline", "unknown"}
        and payload.get("alive") in {"alive", "dead", "unknown"}
        and payload.get("protection_zone") in {"outside", "inside", "unknown"}
        and payload.get("protection_zone_source")
        in {"player_method", "player_states", "unavailable"}
        and isinstance(payload.get("inventory_api_available"), bool)
        and isinstance(payload.get("containers_complete"), bool)
        and ring_valid
        and candidates_valid
        and payload.get("cooldown") in {"ready", "active", "unknown"}
        and payload.get("cooldown_source") in {"game_cooldown_group", "unavailable"}
        and payload.get("validation_errors") == []
        and payload.get("p10_blocker") is None
        and _false_flags(payload)
    )


def _background_contract_valid(payload: Any) -> bool:
    capability = payload.get("capability") if isinstance(payload, dict) else None
    return (
        isinstance(payload, dict)
        and payload.get("schema_version") == BACKGROUND_SCHEMA
        and payload.get("mode") == "background_no_screen"
        and payload.get("status") == "ready"
        and payload.get("advisory_only") is True
        and payload.get("safe_to_run_while_playing") is True
        and payload.get("dispatch_allowed") is False
        and payload.get("runtime_actions") is False
        and payload.get("promotion_allowed") is False
        and payload.get("intrusive_actions_performed") == []
        and payload.get("interaction_contract") == BACKGROUND_INTERACTION_CONTRACT
        and payload.get("wrapper_invariants") == BACKGROUND_WRAPPER_INVARIANTS
        and isinstance(capability, dict)
        and capability.get("fresh") is True
        and capability.get("contract_valid") is True
        and capability.get("version_match") is True
        and capability.get("runtime_actions") is False
        and capability.get("runtime_core_actions") is False
    )


def build_ingest(
    *,
    background: p9_replay.InputDocument,
    capture_profile: p9_replay.InputDocument,
    generated_at_unix_ms: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    blockers: set[str] = set()
    background_payload = background.payload
    profile_payload = capture_profile.payload
    if background.status != "loaded":
        blockers.add(
            "background_missing"
            if background.status == "missing"
            else "background_invalid"
        )
    elif (
        not isinstance(background_payload, dict)
        or background_payload.get("schema_version") != BACKGROUND_SCHEMA
    ):
        blockers.add("background_invalid")
    elif background_payload.get("status") != "ready":
        blockers.add("background_not_ready")
    if isinstance(background_payload, dict) and not _background_contract_valid(
        background_payload
    ):
        blockers.add("background_contract_invalid")
    if capture_profile.status != "loaded":
        blockers.add(
            "capture_profile_missing"
            if capture_profile.status == "missing"
            else "capture_profile_invalid"
        )
    elif not _capture_profile_valid(profile_payload):
        blockers.add("capture_profile_invalid")
    elif profile_payload.get("configured_by_operator") is not True:
        blockers.add("capture_profile_not_configured")

    observation = _observation_from_background(background_payload)
    if observation is None:
        blockers.add("equipment_observation_missing")
    elif not _observation_valid(observation):
        blockers.add("equipment_observation_invalid")

    observation_age: int | None = None
    if _observation_valid(observation):
        observation_age = generated_at_unix_ms - observation["observed_at_unix_ms"]
        if observation_age < 0:
            blockers.add("equipment_observation_future")
        elif observation_age > MAX_AGE_MS + CAPTURE_TRANSPORT_ALLOWANCE_MS:
            blockers.add("equipment_observation_stale")
        if observation["online"] != "online":
            blockers.add("player_offline")
        if observation["alive"] != "alive":
            blockers.add("player_dead")
        if observation["protection_zone"] == "inside":
            blockers.add("protection_zone_inside")
        elif observation["protection_zone"] != "outside":
            blockers.add("protection_zone_unknown")
        elif observation["protection_zone_source"] not in {
            "player_method",
            "player_states",
        }:
            blockers.add("protection_zone_source_untrusted")
        if observation["inventory_api_available"] is not True:
            blockers.add("inventory_api_unavailable")
        if observation["containers_complete"] is not True:
            blockers.add("containers_incomplete")
        if observation["ring"].get("present") is not True:
            blockers.add("ring_missing")
        if observation["cooldown"] == "active":
            blockers.add("cooldown_active")
        elif observation["cooldown"] != "ready":
            blockers.add("cooldown_unknown")
        elif observation["cooldown_source"] != "game_cooldown_group":
            blockers.add("cooldown_source_untrusted")
    if (
        _capture_profile_valid(profile_payload)
        and profile_payload.get("configured_by_operator") is True
        and _observation_valid(observation)
    ):
        equipped = profile_payload["equipped_item_id"]
        candidate = profile_payload["candidate_item_id"]
        container_id = profile_payload["candidate_source_container_id"]
        if equipped <= 0 or observation["ring"].get("item_id") != equipped:
            blockers.add("equipped_item_mismatch")
        if candidate <= 0 or candidate == equipped:
            blockers.add("candidate_matches_equipped")
        matches = [
            item
            for item in observation["candidates"]
            if item.get("item_id") == candidate
        ]
        if len(matches) != 1:
            blockers.add("candidate_not_unique")
        elif matches[0].get("container_id") != container_id:
            blockers.add("candidate_container_mismatch")
        elif (
            matches[0].get("slot_index")
            != profile_payload["candidate_source_slot_index"]
        ):
            blockers.add("candidate_slot_mismatch")
    unsafe = any(
        isinstance(value, dict) and not _false_flags(value)
        for value in (profile_payload, observation)
    )
    if unsafe:
        blockers.add("unsafe_contract")

    ordered = _ordered(blockers)
    observation_hash = p9_replay.canonical_sha256(observation or {"status": "missing"})
    snapshot: dict[str, Any] | None = None
    if (
        not ordered
        and isinstance(observation, dict)
        and isinstance(profile_payload, dict)
    ):
        revision = p9_replay.canonical_sha256(
            {"ring": observation["ring"], "candidates": observation["candidates"]}
        )
        snapshot = {
            "schema_version": SNAPSHOT_SCHEMA,
            "observed_at_unix_ms": observation["observed_at_unix_ms"],
            "observation_id": observation["observation_id"],
            "producer_source": "otclient_guarded_adapter",
            "source_report_sha256": background.sha256,
            "online": True,
            "alive": True,
            "protection_zone": observation["protection_zone"],
            "protection_zone_source": observation["protection_zone_source"],
            "inventory_revision": revision,
            "inventory_unambiguous": True,
            "slot_name": "ring",
            "rollback_slot_name": "ring",
            "equipped_item_id": profile_payload["equipped_item_id"],
            "candidate_item_id": profile_payload["candidate_item_id"],
            "rollback_item_id": profile_payload["equipped_item_id"],
            "rollback_inventory_revision": revision,
            "candidate_source_container_id": profile_payload[
                "candidate_source_container_id"
            ],
            "candidate_source_slot_index": profile_payload[
                "candidate_source_slot_index"
            ],
            "rollback_destination_container_id": profile_payload[
                "candidate_source_container_id"
            ],
            "rollback_destination_slot_index": profile_payload[
                "candidate_source_slot_index"
            ],
            "cooldown": observation["cooldown"],
            "cooldown_source": observation["cooldown_source"],
            **{key: False for key in FALSE_FLAGS},
            "intrusive_actions_performed": [],
        }
    report = {
        "schema_version": REPORT_SCHEMA,
        "generated_at_unix_ms": generated_at_unix_ms,
        "status": "snapshot_ready" if snapshot is not None else "blocked",
        "blockers": ordered,
        "source_sha256": {
            "background_status": background.sha256,
            "capture_profile": capture_profile.sha256,
            "equipment_observation": observation_hash,
        },
        "snapshot_sha256": p9_replay.canonical_sha256(snapshot) if snapshot else None,
        "snapshot_written": False,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    return report, snapshot


def _validate_output(path: Path, expected: Path) -> Path:
    if os.path.normcase(str(path.resolve(strict=False))) != os.path.normcase(
        str(expected.resolve(strict=False))
    ):
        raise ValueError(f"output must equal {expected}")
    boundary = RUNTIME_ROOT.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(boundary):
        raise ValueError(f"output must stay under {boundary}")
    current = boundary
    for part in (
        Path(os.path.abspath(path.parent))
        .relative_to(Path(os.path.abspath(boundary)))
        .parts
    ):
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & reparse
        ):
            raise ValueError(
                "output parent must not contain a symlink or reparse point"
            )
    return path


def _write_atomic(path: Path, expected: Path, payload: dict[str, Any]) -> None:
    _validate_output(path, expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
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
        _validate_output(path, expected)
        temporary.replace(path)
        persisted = p9_replay.read_document(path)
        if (
            persisted.status != "loaded"
            or persisted.sha256 != p9_replay.canonical_sha256(payload)
        ):
            raise ValueError("persisted output verification failed")
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-profile", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return success after producing a structurally blocked no-action report",
    )
    parser.add_argument("--generated-at-unix-ms", type=int, default=None)
    args = parser.parse_args(argv)
    generated_at = args.generated_at_unix_ms or int(time.time() * 1000)
    try:
        capture_profile_path, capture_profile_source = resolve_capture_profile(
            args.capture_profile
        )
    except ValueError:
        print(
            "P10 capture profile rejected; use the tracked template or fixed local override.",
            file=sys.stderr,
        )
        return 2
    background = p9_replay.read_document(DEFAULT_BACKGROUND)
    profile = load_capture_profile(capture_profile_path, capture_profile_source)
    report, snapshot = build_ingest(
        background=background,
        capture_profile=profile,
        generated_at_unix_ms=generated_at,
    )
    if not args.no_write:
        if snapshot is None:
            snapshot = {
                "schema_version": "ctoa.equipment-shadow-snapshot.blocked.v1",
                "generated_at_unix_ms": generated_at,
                "blockers": report["blockers"],
                **{key: False for key in FALSE_FLAGS},
                "intrusive_actions_performed": [],
            }
        _write_atomic(DEFAULT_SNAPSHOT, DEFAULT_SNAPSHOT, snapshot)
        report["snapshot_written"] = report["status"] == "snapshot_ready"
        _write_atomic(DEFAULT_REPORT, DEFAULT_REPORT, report)
    print(f"P10 capture profile: {capture_profile_source}", file=sys.stderr)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "snapshot_ready" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
