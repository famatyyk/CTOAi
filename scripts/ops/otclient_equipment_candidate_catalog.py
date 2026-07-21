#!/usr/bin/env python3
"""Classify passive equipment candidates without selecting or recommending one.

The catalog consumes only the fixed, bounded
``equipment_observation_preview.json`` artifact.  It groups exact
``item_id/container_id/slot_index/count`` tuples, records duplicate and
ambiguous identities, and leaves all candidates for explicit human
configuration.  It never reads an OTClient installation or dispatches an
item action.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_observation_preview as preview
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_observation_preview as preview


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_PREVIEW = DEV_DIR / "equipment_observation_preview.json"
DEFAULT_OUTPUT = DEV_DIR / "equipment_candidate_catalog.json"

SCHEMA = "ctoa.equipment-candidate-catalog.v1"
PREVIEW_SCHEMA = "ctoa.equipment-observation-preview.v1"
MAX_PREVIEW_BYTES = 64 * 1024

FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)

INTERACTION_CONTRACT = dict(preview.INTERACTION_CONTRACT)

BLOCKER_ORDER = (
    "preview_missing",
    "preview_invalid",
    "preview_not_ready",
    "preview_contract_invalid",
    "preview_observation_missing",
    "preview_observation_hash_mismatch",
    "candidates_empty",
    "candidate_zero_id",
    "candidate_exact_duplicate",
    "candidate_position_ambiguous",
    "candidate_item_ambiguous",
    "ring_zero_id",
    "unsafe_contract",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}

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


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _ordered(values: Iterable[str]) -> list[str]:
    unknown = set(values) - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown equipment catalog blockers: {sorted(unknown)}")
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)


def _read_preview() -> documents.InputDocument:
    """Read only the fixed preview path, bounded and reparse-safe."""

    root = ROOT.resolve(strict=False)
    try:
        relative = Path(os.path.abspath(DEFAULT_PREVIEW)).relative_to(
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
    return documents.read_document(DEFAULT_PREVIEW, MAX_PREVIEW_BYTES)


def _observation_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != OBSERVATION_KEYS:
        return False
    ring = payload.get("ring")
    candidates = payload.get("candidates")
    if not (
        payload.get("schema_version") == preview.OBSERVATION_SCHEMA
        and _is_int(payload.get("observed_at_unix_ms"))
        and payload["observed_at_unix_ms"] > 0
        and isinstance(payload.get("observation_id"), str)
        and 1 <= len(payload["observation_id"]) <= 64
        and payload.get("online") in {"online", "offline", "unknown"}
        and payload.get("alive") in {"alive", "dead", "unknown"}
        and payload.get("protection_zone") in {"outside", "inside", "unknown"}
        and payload.get("protection_zone_source")
        in {"player_method", "player_states", "unavailable"}
        and isinstance(payload.get("inventory_api_available"), bool)
        and isinstance(payload.get("containers_complete"), bool)
        and isinstance(ring, dict)
        and set(ring) == {"present", "item_id", "count"}
        and isinstance(ring.get("present"), bool)
        and _is_int(ring.get("item_id"))
        and 0 <= ring["item_id"] <= 65535
        and _is_int(ring.get("count"))
        and 0 <= ring["count"] <= 65535
        and isinstance(candidates, list)
        and len(candidates) <= 256
        and payload.get("cooldown") in {"ready", "active", "unknown"}
        and payload.get("cooldown_source") in {"game_cooldown_group", "unavailable"}
        and payload.get("producer_source") in {"otclient_guarded_adapter", "fixture"}
    ):
        return False
    for item in candidates:
        if not (
            isinstance(item, dict)
            and set(item) == {"container_id", "slot_index", "item_id", "count"}
            and all(_is_int(item.get(key)) for key in item)
            and 0 <= item["container_id"] <= 65535
            and 0 <= item["slot_index"] <= 65535
            and 0 <= item["item_id"] <= 65535
            and 0 <= item["count"] <= 65535
        ):
            return False
    return True


def _preview_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != PREVIEW_KEYS:
        return False
    if payload.get("schema_version") != PREVIEW_SCHEMA:
        return False
    if payload.get("status") not in {"preview_ready", "blocked"}:
        return False
    if payload.get("source") != "background_status" or not _is_sha(
        payload.get("source_sha256")
    ):
        return False
    observation = payload.get("observation")
    if observation is not None and not _observation_valid(observation):
        return False
    expected_observation_hash = (
        preview._observation_hash(observation) if observation is not None else None  # noqa: SLF001
    )
    if payload.get("observation_sha256") != expected_observation_hash:
        return False
    freshness = payload.get("freshness")
    if not (
        isinstance(freshness, dict)
        and set(freshness) == {"observed_at_unix_ms", "age_ms", "max_age_ms", "fresh"}
        and freshness["max_age_ms"] == preview.MAX_AGE_MS
        and isinstance(freshness["fresh"], bool)
        and (
            freshness["observed_at_unix_ms"] is None
            or _is_int(freshness["observed_at_unix_ms"])
        )
        and (freshness["age_ms"] is None or _is_int(freshness["age_ms"]))
    ):
        return False
    provenance = payload.get("provenance")
    if not (
        isinstance(provenance, dict)
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
            provenance["producer_source"] is None
            or isinstance(provenance["producer_source"], str)
        )
        and _is_sha(provenance["background_status_sha256"])
        and (
            provenance["background_schema_version"] is None
            or isinstance(provenance["background_schema_version"], str)
        )
        and isinstance(provenance["background_capability_fresh"], bool)
        and isinstance(provenance["background_contract_valid"], bool)
        and isinstance(provenance["version_match"], bool)
    ):
        return False
    if provenance["background_status_sha256"] != payload["source_sha256"]:
        return False
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or any(
        not isinstance(item, str) or item not in preview.BLOCKER_RANK
        for item in blockers
    ):
        return False
    if blockers != preview._ordered(blockers):  # noqa: SLF001
        return False
    if payload["status"] == "preview_ready" and blockers:
        return False
    if payload["status"] == "blocked" and not blockers:
        return False
    if payload.get("interaction_contract") != INTERACTION_CONTRACT:
        return False
    return (
        _is_int(payload.get("generated_at_unix_ms"))
        and payload["generated_at_unix_ms"] > 0
        and all(payload.get(key) is False for key in FALSE_FLAGS)
        and payload.get("intrusive_actions_performed") == []
    )


def _classify_groups(
    candidates: list[dict[str, int]],
) -> tuple[list[dict[str, Any]], dict[str, int], set[str]]:
    grouped: Counter[tuple[int, int, int, int]] = Counter(
        (
            item["item_id"],
            item["container_id"],
            item["slot_index"],
            item["count"],
        )
        for item in candidates
    )
    by_item: defaultdict[int, set[tuple[int, int, int]]] = defaultdict(set)
    by_position: defaultdict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for item_id, container_id, slot_index, count in grouped:
        by_item[item_id].add((container_id, slot_index, count))
        by_position[(container_id, slot_index)].add((item_id, count))

    groups: list[dict[str, Any]] = []
    blocker_set: set[str] = set()
    for item_id, container_id, slot_index, count in sorted(grouped):
        flags: list[str] = []
        if grouped[(item_id, container_id, slot_index, count)] > 1:
            flags.append("exact_duplicate")
            blocker_set.add("candidate_exact_duplicate")
        if len(by_item[item_id]) > 1:
            flags.append("item_ambiguous")
            blocker_set.add("candidate_item_ambiguous")
        if len(by_position[(container_id, slot_index)]) > 1:
            flags.append("position_ambiguous")
            blocker_set.add("candidate_position_ambiguous")
        if item_id <= 0 or container_id <= 0 or slot_index <= 0:
            flags.append("zero_id")
            blocker_set.add("candidate_zero_id")
        groups.append(
            {
                "item_id": item_id,
                "container_id": container_id,
                "slot_index": slot_index,
                "count": count,
                "occurrences": grouped[(item_id, container_id, slot_index, count)],
                "flags": sorted(flags),
            }
        )
    summary = {
        "candidate_count": len(candidates),
        "exact_group_count": len(groups),
        "duplicate_group_count": sum(
            "exact_duplicate" in group["flags"] for group in groups
        ),
        "unique_item_id_count": len(by_item),
        "ambiguous_item_id_count": sum(len(values) > 1 for values in by_item.values()),
        "position_conflict_count": sum(
            len(values) > 1 for values in by_position.values()
        ),
        "zero_id_count": sum(
            group["item_id"] <= 0
            or group["container_id"] <= 0
            or group["slot_index"] <= 0
            for group in groups
        ),
    }
    return groups, summary, blocker_set


def build_catalog(
    *, preview_document: documents.InputDocument, generated_at_unix_ms: int
) -> dict[str, Any]:
    blockers: set[str] = set()
    payload = preview_document.payload
    if preview_document.status != "loaded":
        blockers.add(
            "preview_missing"
            if preview_document.status == "missing"
            else "preview_invalid"
        )
    elif not _preview_valid(payload):
        blockers.add("preview_contract_invalid")
    observation = payload.get("observation") if isinstance(payload, dict) else None
    if isinstance(payload, dict) and payload.get("status") != "preview_ready":
        blockers.add("preview_not_ready")
    if observation is None:
        blockers.add("preview_observation_missing")
    groups: list[dict[str, Any]] = []
    summary = {
        "candidate_count": 0,
        "exact_group_count": 0,
        "duplicate_group_count": 0,
        "unique_item_id_count": 0,
        "ambiguous_item_id_count": 0,
        "position_conflict_count": 0,
        "zero_id_count": 0,
    }
    ring = None
    if isinstance(observation, dict) and _observation_valid(observation):
        if payload.get("observation_sha256") != preview._observation_hash(observation):  # noqa: SLF001
            blockers.add("preview_observation_hash_mismatch")
        ring = observation["ring"]
        candidates = observation["candidates"]
        if not candidates:
            blockers.add("candidates_empty")
        groups, summary, candidate_blockers = _classify_groups(candidates)
        blockers.update(candidate_blockers)
        if ring["present"] and ring["item_id"] <= 0:
            blockers.add("ring_zero_id")
    if isinstance(payload, dict) and any(
        payload.get(key) is not False for key in FALSE_FLAGS
    ):
        blockers.add("unsafe_contract")
    ordered = _ordered(blockers)
    status = "catalog_ready" if not ordered else "blocked"
    preview_status = (
        payload.get("status")
        if isinstance(payload, dict)
        and payload.get("status") in {"preview_ready", "blocked"}
        else None
    )
    preview_blockers = (
        [
            item
            for item in payload.get("blockers", [])
            if isinstance(item, str) and item in preview.BLOCKER_RANK
        ]
        if isinstance(payload, dict) and isinstance(payload.get("blockers"), list)
        else []
    )
    return {
        "schema_version": SCHEMA,
        "generated_at_unix_ms": generated_at_unix_ms,
        "status": status,
        "source": "equipment_observation_preview",
        "preview_sha256": preview_document.sha256,
        "preview_status": preview_status,
        "preview_blockers": preview_blockers,
        "selection_policy": "none",
        "recommendation": None,
        "ring": ring,
        "groups": groups,
        "summary": summary,
        "blockers": ordered,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return success after printing a blocked catalog",
    )
    args = parser.parse_args(argv)
    report = build_catalog(
        preview_document=_read_preview(), generated_at_unix_ms=int(time.time() * 1000)
    )
    if not args.no_write:
        preview._write_atomic(DEFAULT_OUTPUT, DEFAULT_OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "catalog_ready" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
