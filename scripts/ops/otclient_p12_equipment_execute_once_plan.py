#!/usr/bin/env python3
"""Capture the hash-bound P12 Equipment bridge plan; never move an item."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "runtime" / "solteria_helper_dev"
MANIFEST = DEV / "manifest.json"
RUNTIME_GATES = DEV / "runtime_module_gates_sandbox_smoke.json"
P10_RECEIPT = DEV / "equipment_shadow_acceptance.json"
CAPABILITY = (
    Path.home()
    / "AppData/Local/SolteriaCodexTest/client/mods/ctoa_otclient/ctoa_client_capabilities.json"
)
FAMILY_SELECTION_PROFILE = (
    Path.home() / "AppData/Local/SolteriaCodexTest/client/ctoa_user_ek_profile.lua"
)
SOURCE = (
    ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_equipment_execute_once.lua"
)
REGISTRY_SOURCE = (
    ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_equipment_family_registry.lua"
)
OUTPUT = DEV / "p12_equipment_execute_once_plan.json"
MODULE_PATH = "mods/ctoa_otclient/ctoa_helper_equipment_execute_once.lua"
REGISTRY_MODULE_PATH = "mods/ctoa_otclient/ctoa_helper_equipment_family_registry.lua"
SCHEMA = "ctoa.p12-equipment-execute-once-plan.v1"
MAX_HEARTBEAT_AGE_MS = 15_000
ACTIVE_RING_ID = 3096
CANDIDATE_RING_ID = 3097
EQUIPPED_CANDIDATE_RING_ID = 3099
ROLLBACK_BACKPACK_RING_ID = 3093
BEFORE_FAMILY_KEY = "ring_primary"
CANDIDATE_FAMILY_KEY = "ring_secondary"
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "execute_once_allowed",
    "live_promotion",
)


def _load(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value, hashlib.sha256(raw).hexdigest()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def build_plan(
    paths: dict[str, Path] | None = None, *, now_ms: int | None = None
) -> dict[str, Any]:
    selected = paths or {
        "manifest": MANIFEST,
        "runtime_gates": RUNTIME_GATES,
        "p10_receipt": P10_RECEIPT,
        "capability": CAPABILITY,
        "source": SOURCE,
        "registry_source": REGISTRY_SOURCE,
        "family_selection_profile": FAMILY_SELECTION_PROFILE,
    }
    current_ms = int(time.time() * 1000) if now_ms is None else now_ms
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name, path in selected.items():
        if name in {"source", "registry_source", "family_selection_profile"}:
            continue
        try:
            docs[name], hashes[name] = _load(path)
        except (OSError, ValueError, json.JSONDecodeError):
            docs[name], hashes[name] = {}, "0" * 64
            blockers.append(f"{name}_missing_or_invalid")

    manifest = docs["manifest"]
    gates = docs["runtime_gates"]
    receipt = docs["p10_receipt"]
    capability = docs["capability"]
    try:
        source_sha = hashlib.sha256(selected["source"].read_bytes()).hexdigest()
    except OSError:
        source_sha = "0" * 64
        blockers.append("source_missing")
    try:
        registry_raw = selected["registry_source"].read_bytes()
        registry_text = registry_raw.decode("utf-8")
        registry_sha = hashlib.sha256(registry_raw).hexdigest()
    except (OSError, UnicodeDecodeError):
        registry_text = ""
        registry_sha = "0" * 64
        blockers.append("family_registry_missing_or_invalid")
    registry_contract = (
        'key = "ring_primary"' in registry_text
        and "inventory_ids = {3093}" in registry_text
        and "equipped_ids = {3096}" in registry_text
        and 'key = "ring_secondary"' in registry_text
        and "inventory_ids = {3097}" in registry_text
        and "equipped_ids = {3099}" in registry_text
        and "default_enabled = false" in registry_text
    )
    if not registry_contract:
        blockers.append("family_registry_contract_mismatch")
    try:
        profile_raw = selected["family_selection_profile"].read_bytes()
        profile_text = profile_raw.decode("utf-8")
        profile_sha = hashlib.sha256(profile_raw).hexdigest()
    except (OSError, UnicodeDecodeError):
        profile_text = ""
        profile_sha = "0" * 64
        blockers.append("family_selection_profile_missing_or_invalid")
    primary_values = re.findall(r"\bring_primary\s*=\s*(true|false)\s*,", profile_text)
    secondary_values = re.findall(
        r"\bring_secondary\s*=\s*(true|false)\s*,", profile_text
    )
    if primary_values != ["false"] or secondary_values != ["true"]:
        blockers.append("family_selection_invalid")
    entries = [
        item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and item.get("path") == MODULE_PATH
    ]
    if len(entries) != 1 or entries[0].get("sha256") != source_sha:
        blockers.append("source_manifest_parity_failed")
    registry_entries = [
        item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and item.get("path") == REGISTRY_MODULE_PATH
    ]
    if len(registry_entries) != 1 or registry_entries[0].get("sha256") != registry_sha:
        blockers.append("family_registry_manifest_parity_failed")
    gate_manifest = gates.get("manifest")
    if not (
        gates.get("status") == "passed"
        and gates.get("failed") == []
        and gates.get("check_count") == 19
        and gates.get("passed_count") == 19
        and isinstance(gate_manifest, dict)
        and gate_manifest.get("sha256") == hashes["manifest"]
        and gates.get("observed", {}).get("runtime_state") == "disarmed"
    ):
        blockers.append("runtime_gates_not_current")
    if manifest.get("helper_version") != "v2.4.1":
        blockers.append("helper_version_mismatch")
    if not (
        receipt.get("schema_version") == "ctoa.equipment-shadow-acceptance.v1"
        and receipt.get("status") == "accepted"
        and receipt.get("acceptance_granted") is True
        and receipt.get("action") == "plan_ring_swap"
        and receipt.get("blockers") == []
        and all(
            receipt.get(flag) is False
            for flag in (
                "dispatch_allowed",
                "runtime_actions",
                "execute_once_allowed",
                "promotion_allowed",
            )
        )
    ):
        blockers.append("p10_acceptance_invalid")

    observed_at = capability.get("observed_at_unix_ms")
    age_ms = current_ms - observed_at if isinstance(observed_at, int) else None
    if not isinstance(age_ms, int) or age_ms < 0 or age_ms > MAX_HEARTBEAT_AGE_MS:
        blockers.append("capability_heartbeat_stale")
    if not (
        capability.get("heartbeat_status") == "online"
        and capability.get("online") is True
        and capability.get("vocation") == "ek"
        and capability.get("runtime_state") == "disarmed"
        and capability.get("runtime_enabled") is False
    ):
        blockers.append("capability_state_unsafe")

    observation = capability.get("equipment_shadow_observation")
    if not isinstance(observation, dict):
        blockers.append("equipment_observation_missing")
        observation = {}
    expected = {
        "schema_version": "ctoa.equipment-shadow-observation.v1",
        "observed_at_unix_ms": observed_at,
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_states",
        "inventory_api_available": True,
        "containers_complete": True,
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
    }
    for field, value in expected.items():
        if observation.get(field) != value:
            blockers.append(f"observation_{field}_not_ready")
    for flag in (
        "dispatch_allowed",
        "runtime_actions",
        "executes_plan",
        "execute_once_allowed",
        "promotion_allowed",
    ):
        if observation.get(flag) is not False:
            blockers.append(f"observation_{flag}_unsafe")
    ring = observation.get("ring") if isinstance(observation.get("ring"), dict) else {}
    if not (
        ring.get("present") is True
        and ring.get("item_id") == ACTIVE_RING_ID
        and ring.get("count") == 1
    ):
        blockers.append("equipped_ring_mismatch")
    candidates = (
        observation.get("candidates")
        if isinstance(observation.get("candidates"), list)
        else []
    )
    matches = [
        item
        for item in candidates
        if isinstance(item, dict) and item.get("item_id") == CANDIDATE_RING_ID
    ]
    if len(matches) != 1:
        blockers.append("candidate_ring_not_unique")
        candidate = {}
    else:
        candidate = matches[0]
        if not (
            isinstance(candidate.get("container_id"), int)
            and candidate.get("container_id") >= 0
            and isinstance(candidate.get("slot_index"), int)
            and candidate.get("slot_index") >= 1
            and candidate.get("count") == 1
        ):
            blockers.append("candidate_location_invalid")

    basis = {
        "schema_version": SCHEMA,
        "lane": "equipment",
        "action": "move_ring_candidate_to_equipment_slot",
        "slot": "ring",
        "before_item_id": ACTIVE_RING_ID,
        "before_family_key": BEFORE_FAMILY_KEY,
        "candidate_item_id": CANDIDATE_RING_ID,
        "candidate_family_key": CANDIDATE_FAMILY_KEY,
        "source_container_id": candidate.get("container_id"),
        "source_slot_index": candidate.get("slot_index"),
        "rollback_item_id": ROLLBACK_BACKPACK_RING_ID,
        "retry_budget": 0,
        "mandatory_kill_and_disarm": True,
        "requires_post_action_ring_id": EQUIPPED_CANDIDATE_RING_ID,
        "observation_id": observation.get("observation_id"),
        "capability_sha256": hashes["capability"],
        "manifest_sha256": hashes["manifest"],
        "runtime_gates_sha256": hashes["runtime_gates"],
        "p10_receipt_sha256": hashes["p10_receipt"],
        "source_sha256": source_sha,
        "family_registry_sha256": registry_sha,
        "family_selection_profile_sha256": profile_sha,
    }
    plan_sha = hashlib.sha256(
        json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        **basis,
        "plan_sha256": plan_sha,
        "status": "ready_for_sandbox_session_approval" if not blockers else "blocked",
        "blockers": blockers,
        "bridge_implemented": True,
        "required_session_confirmation": f"zatwierdzam sesję sandbox P12 Equipment {plan_sha}",
        "required_execute_confirmation": f"zatwierdzam wykonanie P12 Equipment {plan_sha}",
        "session_approved": False,
        "execution_approved": False,
        "attempt_count": 0,
        "retry_scheduled": False,
        "final_state": "disarmed",
        "capability_age_ms": age_ms,
        **{flag: False for flag in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main() -> int:
    plan = build_plan()
    _atomic_write(OUTPUT, plan)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0 if plan["status"] == "ready_for_sandbox_session_approval" else 1


if __name__ == "__main__":
    sys.exit(main())
