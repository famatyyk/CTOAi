#!/usr/bin/env python3
"""Preflight P12 Equipment execution approval from current passive evidence."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_p12_equipment_execute_once_plan as plans
else:  # pragma: no cover
    import otclient_p12_equipment_execute_once_plan as plans

APPROVAL = plans.DEV / "p12_equipment_session_approval.json"
RUNTIME_GATES = plans.DEV / "runtime_module_gates_sandbox_smoke.json"
CAPABILITY = plans.CAPABILITY
OUTPUT = plans.DEV / "p12_equipment_execution_preflight.json"
SCHEMA = "ctoa.p12-equipment-execution-preflight.v1"
MAX_HEARTBEAT_AGE_MS = 15_000


def _load(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value, hashlib.sha256(raw).hexdigest()


def build_preflight(
    paths: dict[str, Path] | None = None, *, now_ms: int | None = None
) -> dict[str, Any]:
    selected = paths or {
        "plan": plans.OUTPUT,
        "approval": APPROVAL,
        "runtime_gates": RUNTIME_GATES,
        "capability": CAPABILITY,
        "manifest": plans.MANIFEST,
        "family_selection_profile": plans.FAMILY_SELECTION_PROFILE,
        "registry_source": plans.REGISTRY_SOURCE,
    }
    current_ms = int(time.time() * 1000) if now_ms is None else now_ms
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name, path in selected.items():
        try:
            if name in {"family_selection_profile", "registry_source"}:
                raw = path.read_bytes()
                docs[name] = {"text": raw.decode("utf-8")}
                hashes[name] = hashlib.sha256(raw).hexdigest()
            else:
                docs[name], hashes[name] = _load(path)
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            blockers.append(f"{name}_missing_or_invalid")
            docs[name], hashes[name] = {}, "0" * 64

    plan = docs["plan"]
    approval = docs["approval"]
    gates = docs["runtime_gates"]
    capability = docs["capability"]
    family_selection_profile = docs["family_selection_profile"].get("text", "")
    if (
        plan.get("status") != "ready_for_sandbox_session_approval"
        or plan.get("blockers") != []
    ):
        blockers.append("plan_not_ready")
    if not (
        approval.get("status") == "approved"
        and approval.get("session_approved") is True
        and isinstance(approval.get("execution_approved"), bool)
        and approval.get("plan_sha256") == plan.get("plan_sha256")
        and approval.get("p10_receipt_sha256") == plan.get("p10_receipt_sha256")
    ):
        blockers.append("session_approval_invalid")
    family_selection_matches = {
        family: re.findall(
            rf"\b{family}\s*=\s*(true|false)\b", family_selection_profile
        )
        for family in ("ring_primary", "ring_secondary")
    }
    if not (
        hashes["family_selection_profile"]
        == plan.get("family_selection_profile_sha256")
        and family_selection_matches["ring_primary"] == ["false"]
        and family_selection_matches["ring_secondary"] == ["true"]
    ):
        blockers.append("family_selection_drift")
    if hashes["registry_source"] != plan.get("family_registry_sha256"):
        blockers.append("family_registry_drift")
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
        blockers.append("sandbox_gates_not_current")
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
    else:
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
        ring = (
            observation.get("ring") if isinstance(observation.get("ring"), dict) else {}
        )
        if not (
            ring.get("present") is True
            and ring.get("item_id") == plan.get("before_item_id")
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
            if isinstance(item, dict)
            and item.get("item_id") == plan.get("candidate_item_id")
        ]
        if len(matches) != 1 or not (
            matches[0].get("container_id") == plan.get("source_container_id")
            and matches[0].get("slot_index") == plan.get("source_slot_index")
            and matches[0].get("count") == 1
        ):
            blockers.append("candidate_location_mismatch")
        for flag in (
            "dispatch_allowed",
            "runtime_actions",
            "executes_plan",
            "execute_once_allowed",
            "promotion_allowed",
        ):
            if observation.get(flag) is not False:
                blockers.append(f"observation_{flag}_unsafe")

    return {
        "schema_version": SCHEMA,
        "created_at_unix_ms": current_ms,
        "status": "ready_for_execution_approval" if not blockers else "blocked",
        "plan_sha256": plan.get("plan_sha256"),
        "approval_id": approval.get("approval_id"),
        "p10_receipt_sha256": plan.get("p10_receipt_sha256"),
        "manifest_sha256": hashes["manifest"],
        "runtime_gates_sha256": hashes["runtime_gates"],
        "capability_sha256": hashes["capability"],
        "family_selection_profile_sha256": hashes["family_selection_profile"],
        "family_registry_sha256": hashes["registry_source"],
        "capability_age_ms": age_ms,
        "observation": observation,
        "blockers": blockers,
        "required_execute_confirmation": plan.get("required_execute_confirmation"),
        "session_approved": approval.get("session_approved") is True,
        "execution_approved": approval.get("execution_approved") is True,
        "attempt_count": 0,
        "retry_budget": 0,
        "final_state": "disarmed",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "execute_once_allowed": False,
        "live_promotion": False,
        "intrusive_actions_performed": [],
    }


def main() -> int:
    report = build_preflight()
    plans._atomic_write(OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready_for_execution_approval" else 1


if __name__ == "__main__":
    sys.exit(main())
