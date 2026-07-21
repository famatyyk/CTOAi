#!/usr/bin/env python3
"""Render a bounded, sanitized equipment preview from BackgroundNoScreen.

This command is deliberately a data-only boundary.  It reads only the fixed
canonical ``runtime/solteria_helper_dev/background_status.json`` artifact,
projects the ring/container/slot fields needed for manual P10 configuration,
and optionally writes a repo-local preview artifact.  It never reads an
OTClient installation, launches or controls a client, or performs an item
action.  A preview can be useful while blocked (for example, when the
operator profile is still unconfigured), but a blocked preview never grants
P10 readiness or dispatch permission.
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
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_shadow_snapshot as snapshot
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_shadow_snapshot as snapshot


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_BACKGROUND = DEV_DIR / "background_status.json"
DEFAULT_OUTPUT = DEV_DIR / "equipment_observation_preview.json"

SCHEMA = "ctoa.equipment-observation-preview.v1"
BACKGROUND_SCHEMA = snapshot.BACKGROUND_SCHEMA
OBSERVATION_SCHEMA = snapshot.OBSERVATION_SCHEMA
MAX_BACKGROUND_BYTES = 64 * 1024
# Planning is passive and runs after the official BackgroundNoScreen wrapper.
# Keep a small transport allowance without relaxing the 6s operational
# snapshot/replay boundary in ``otclient_equipment_shadow_snapshot``.
MAX_AGE_MS = 10_000

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
    "live_file_writes": False,
    "passive_reads_only": True,
    "evidence_write_scope": "runtime/solteria_helper_dev",
}

BLOCKER_ORDER = (
    "background_missing",
    "background_invalid",
    "background_not_ready",
    "background_contract_invalid",
    "equipment_observation_missing",
    "equipment_observation_invalid",
    "equipment_observation_future",
    "equipment_observation_stale",
    "equipment_observation_provenance_untrusted",
    "player_offline",
    "player_dead",
    "protection_zone_inside",
    "protection_zone_unknown",
    "protection_zone_source_untrusted",
    "inventory_api_unavailable",
    "containers_incomplete",
    "ring_missing",
    "cooldown_active",
    "cooldown_unknown",
    "cooldown_source_untrusted",
    "unsafe_contract",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}


def _ordered(values: Iterable[str]) -> list[str]:
    unknown = set(values) - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown equipment preview blockers: {sorted(unknown)}")
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)


def _fixed_path(path: Path, expected: Path) -> bool:
    return os.path.normcase(str(path.resolve(strict=False))) == os.path.normcase(
        str(expected.resolve(strict=False))
    )


def _read_background() -> documents.InputDocument:
    """Read only the fixed canonical artifact and reject reparse ancestors."""

    root = ROOT.resolve(strict=False)
    try:
        relative = Path(os.path.abspath(DEFAULT_BACKGROUND)).relative_to(
            Path(os.path.abspath(root))
        )
    except ValueError:
        return documents.InputDocument(
            None,
            "unreadable",
            documents.canonical_sha256({"load_status": "unreadable"}),
        )
    current = root
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
            return documents.InputDocument(
                None,
                "symlink_rejected",
                documents.canonical_sha256({"load_status": "symlink_rejected"}),
            )
    return documents.read_document(DEFAULT_BACKGROUND, MAX_BACKGROUND_BYTES)


def _observation_projection(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields required to identify ring/container/slot candidates."""

    return {
        "schema_version": payload["schema_version"],
        "observation_id": payload["observation_id"],
        "observed_at_unix_ms": payload["observed_at_unix_ms"],
        "online": payload["online"],
        "alive": payload["alive"],
        "protection_zone": payload["protection_zone"],
        "protection_zone_source": payload["protection_zone_source"],
        "inventory_api_available": payload["inventory_api_available"],
        "containers_complete": payload["containers_complete"],
        "ring": {
            "present": payload["ring"]["present"],
            "item_id": payload["ring"]["item_id"],
            "count": payload["ring"]["count"],
        },
        "candidates": [
            {
                "container_id": item["container_id"],
                "slot_index": item["slot_index"],
                "item_id": item["item_id"],
                "count": item["count"],
            }
            for item in payload["candidates"]
        ],
        "cooldown": payload["cooldown"],
        "cooldown_source": payload["cooldown_source"],
        "producer_source": payload["producer_source"],
    }


def _observation_hash(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return documents.canonical_sha256(_observation_projection(payload))


def _observation_shape_valid(payload: Any) -> bool:
    """Validate the bounded envelope while keeping fixture provenance visible."""

    if snapshot._observation_valid(payload):  # noqa: SLF001
        return True
    if not isinstance(payload, dict) or payload.get("producer_source") != "fixture":
        return False
    # The shared snapshot validator intentionally accepts operational adapter
    # data only.  For this preview boundary, a fixture-shaped envelope is
    # still safe to render, but it must become an explicit provenance blocker.
    candidate = dict(payload)
    candidate["producer_source"] = "otclient_guarded_adapter"
    return snapshot._observation_valid(candidate)  # noqa: SLF001


def _write_atomic(path: Path, expected: Path, payload: dict[str, Any]) -> None:
    if not _fixed_path(path, expected):
        raise ValueError(f"output must equal {expected}")
    boundary = RUNTIME_ROOT.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(boundary):
        raise ValueError(f"output must stay under {boundary}")
    current = boundary
    try:
        relative_parent = Path(os.path.abspath(path.parent)).relative_to(
            Path(os.path.abspath(boundary))
        )
    except ValueError as exc:  # pragma: no cover - guarded by resolved check
        raise ValueError("output parent escaped runtime root") from exc
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    for part in relative_parent.parts:
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
                handle.write(documents.canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        metadata = temporary.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ValueError("temporary output identity invalid")
        _fixed_path(path, expected)
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build_preview(
    *, background: documents.InputDocument, generated_at_unix_ms: int
) -> dict[str, Any]:
    blockers: set[str] = set()
    payload = background.payload
    if background.status != "loaded":
        blockers.add(
            "background_missing"
            if background.status == "missing"
            else "background_invalid"
        )
    elif (
        not isinstance(payload, dict)
        or payload.get("schema_version") != BACKGROUND_SCHEMA
    ):
        blockers.add("background_invalid")
    elif payload.get("status") != "ready":
        blockers.add("background_not_ready")
    if isinstance(payload, dict) and not snapshot._background_contract_valid(payload):  # noqa: SLF001
        blockers.add("background_contract_invalid")

    raw_observation = snapshot._observation_from_background(payload)  # noqa: SLF001
    observation: dict[str, Any] | None = None
    if raw_observation is None:
        blockers.add("equipment_observation_missing")
    elif not _observation_shape_valid(raw_observation):
        blockers.add("equipment_observation_invalid")
    else:
        observation = _observation_projection(raw_observation)
        observed_at = raw_observation["observed_at_unix_ms"]
        age_ms = generated_at_unix_ms - observed_at
        if age_ms < 0:
            blockers.add("equipment_observation_future")
        elif age_ms > MAX_AGE_MS:
            blockers.add("equipment_observation_stale")
        if raw_observation["producer_source"] != "otclient_guarded_adapter":
            blockers.add("equipment_observation_provenance_untrusted")
        if raw_observation["online"] != "online":
            blockers.add("player_offline")
        if raw_observation["alive"] != "alive":
            blockers.add("player_dead")
        if raw_observation["protection_zone"] == "inside":
            blockers.add("protection_zone_inside")
        elif raw_observation["protection_zone"] != "outside":
            blockers.add("protection_zone_unknown")
        elif raw_observation["protection_zone_source"] not in {
            "player_method",
            "player_states",
        }:
            blockers.add("protection_zone_source_untrusted")
        if raw_observation["inventory_api_available"] is not True:
            blockers.add("inventory_api_unavailable")
        if raw_observation["containers_complete"] is not True:
            blockers.add("containers_incomplete")
        if raw_observation["ring"]["present"] is not True:
            blockers.add("ring_missing")
        if raw_observation["cooldown"] == "active":
            blockers.add("cooldown_active")
        elif raw_observation["cooldown"] != "ready":
            blockers.add("cooldown_unknown")
        elif raw_observation["cooldown_source"] != "game_cooldown_group":
            blockers.add("cooldown_source_untrusted")
        if any(raw_observation.get(key) is not False for key in FALSE_FLAGS):
            blockers.add("unsafe_contract")
    if isinstance(payload, dict) and any(
        payload.get(key) is not False
        for key in ("dispatch_allowed", "runtime_actions", "promotion_allowed")
    ):
        blockers.add("unsafe_contract")

    ordered = _ordered(blockers)
    age_ms: int | None = None
    fresh = False
    if observation is not None:
        age_ms = generated_at_unix_ms - observation["observed_at_unix_ms"]
        fresh = 0 <= age_ms <= MAX_AGE_MS
    capability = payload.get("capability") if isinstance(payload, dict) else None
    provenance = {
        "producer_source": observation.get("producer_source") if observation else None,
        "background_status_sha256": background.sha256,
        "background_schema_version": payload.get("schema_version")
        if isinstance(payload, dict)
        else None,
        "background_capability_fresh": capability.get("fresh") is True
        if isinstance(capability, dict)
        else False,
        "background_contract_valid": snapshot._background_contract_valid(payload),  # noqa: SLF001
        "version_match": capability.get("version_match") is True
        if isinstance(capability, dict)
        else False,
    }
    report = {
        "schema_version": SCHEMA,
        "generated_at_unix_ms": generated_at_unix_ms,
        "status": "preview_ready" if not ordered else "blocked",
        "source": "background_status",
        "source_sha256": background.sha256,
        "observation_sha256": _observation_hash(raw_observation)
        if observation
        else None,
        "observation": observation,
        "freshness": {
            "observed_at_unix_ms": observation["observed_at_unix_ms"]
            if observation
            else None,
            "age_ms": age_ms,
            "max_age_ms": MAX_AGE_MS,
            "fresh": fresh,
        },
        "provenance": provenance,
        "blockers": ordered,
        "interaction_contract": dict(INTERACTION_CONTRACT),
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return success after printing a structurally blocked preview",
    )
    args = parser.parse_args(argv)
    generated_at = int(time.time() * 1000)
    report = build_preview(
        background=_read_background(), generated_at_unix_ms=generated_at
    )
    if not args.no_write:
        _write_atomic(DEFAULT_OUTPUT, DEFAULT_OUTPUT, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "preview_ready" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
