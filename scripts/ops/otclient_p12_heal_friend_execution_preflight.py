#!/usr/bin/env python3
"""Preflight P12 Heal Friend against fresh exact-target sandbox evidence."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_p12_heal_friend_execute_once_plan as plans
else:  # pragma: no cover
    import otclient_p12_heal_friend_execute_once_plan as plans

APPROVAL = plans.DEV / "p12_heal_friend_session_approval.json"
CAPABILITY = (
    Path.home()
    / "AppData/Local/SolteriaCodexTest/client/mods/ctoa_otclient/ctoa_client_capabilities.json"
)
OUTPUT = plans.DEV / "p12_heal_friend_execution_preflight.json"
SCHEMA = "ctoa.p12-heal-friend-execution-preflight.v1"
MAX_HEARTBEAT_AGE_MS = 15_000
WAITING_BLOCKERS = {"exact_target_not_observed", "target_hp_above_threshold"}


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
        "runtime_gates": plans.RUNTIME_GATES,
        "capability": CAPABILITY,
        "manifest": plans.MANIFEST,
        "p11_receipt": plans.P11_RECEIPT,
        "p11_report": plans.P11_REPORT,
        "p12_equipment_receipt": plans.P12_EQUIPMENT_RECEIPT,
        "source": plans.SOURCE,
    }
    current_ms = int(time.time() * 1000) if now_ms is None else now_ms
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name, path in selected.items():
        if name == "source":
            try:
                raw = path.read_bytes()
                docs[name] = {}
                hashes[name] = hashlib.sha256(raw).hexdigest()
            except OSError:
                docs[name], hashes[name] = {}, "0" * 64
                blockers.append("source_missing_or_invalid")
            continue
        try:
            docs[name], hashes[name] = _load(path)
        except (OSError, ValueError, json.JSONDecodeError):
            blockers.append(f"{name}_missing_or_invalid")
            docs[name], hashes[name] = {}, "0" * 64

    plan = docs["plan"]
    approval = docs["approval"]
    gates = docs["runtime_gates"]
    capability = docs["capability"]
    if (
        plan.get("schema_version") != plans.SCHEMA
        or plan.get("status") != "ready_for_sandbox_session_approval"
        or plan.get("blockers") != []
    ):
        blockers.append("plan_not_ready")
    if not (
        approval.get("status") == "approved"
        and approval.get("session_approved") is True
        and isinstance(approval.get("execution_approved"), bool)
        and approval.get("plan_sha256") == plan.get("plan_sha256")
        and approval.get("p11_receipt_sha256")
        == plan.get("p11_receipt_sha256")
        and approval.get("p12_equipment_receipt_sha256")
        == plan.get("p12_equipment_receipt_sha256")
    ):
        blockers.append("session_approval_invalid")
    if hashes["p11_receipt"] != plan.get("p11_receipt_sha256"):
        blockers.append("p11_receipt_drift")
    report_sha = (
        plans._canonical_sha(docs["p11_report"])  # noqa: SLF001
        if docs["p11_report"]
        else "0" * 64
    )
    if report_sha != plan.get("p11_report_sha256"):
        blockers.append("p11_report_drift")
    if hashes["p12_equipment_receipt"] != plan.get(
        "p12_equipment_receipt_sha256"
    ):
        blockers.append("p12_equipment_receipt_drift")
    if hashes["source"] != plan.get("source_sha256"):
        blockers.append("source_drift")
    gate_manifest = gates.get("manifest")
    if not (
        gates.get("status") == "passed"
        and gates.get("failed") == []
        and isinstance(gate_manifest, dict)
        and gate_manifest.get("sha256") == hashes["manifest"]
        and hashes["manifest"] == plan.get("manifest_sha256")
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
        and capability.get("runtime_state") == "disarmed"
        and capability.get("runtime_enabled") is False
    ):
        blockers.append("capability_state_unsafe")
    if capability.get("vocation") != plans.EXACT_VOCATION:
        blockers.append("vocation_must_be_ed")

    scan = capability.get("heal_friend_scan")
    if not isinstance(scan, dict):
        blockers.append("heal_friend_scan_missing")
        scan = {}
    expected = {
        "schema_version": "ctoa.heal-friend-scan.v1",
        "observed_at_unix_ms": observed_at,
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "cooldown": "ready",
        "scan_complete": True,
        "producer_source": "otclient_guarded_adapter",
    }
    for field, value in expected.items():
        if scan.get(field) != value:
            if field == "cooldown":
                blockers.append("cooldown_not_ready")
            elif field == "protection_zone":
                blockers.append("protection_zone_not_ready")
            else:
                blockers.append(f"scan_{field}_not_ready")
    for flag in (
        "dispatch_allowed",
        "runtime_actions",
        "executes_plan",
        "execute_once_allowed",
        "promotion_allowed",
        "casts",
        "talks",
    ):
        if scan.get(flag) is not False:
            blockers.append(f"scan_{flag}_unsafe")

    candidates = scan.get("candidates") if isinstance(scan.get("candidates"), list) else []
    matches = [
        item
        for item in candidates
        if isinstance(item, dict)
        and item.get("target_id") == plan.get("target_id")
        and str(item.get("target_name", "")).strip().lower()
        == plan.get("target_name")
    ]
    if len(matches) != 1:
        blockers.append("exact_target_not_observed")
        candidate: dict[str, Any] = {}
    else:
        candidate = matches[0]
        if candidate.get("target_is_player") is not True:
            blockers.append("target_not_player")
        if candidate.get("target_is_self") is not False or scan.get(
            "self_id"
        ) == plan.get("target_id"):
            blockers.append("target_is_self")
        if candidate.get("target_party_member") is not True:
            blockers.append("target_not_party_member")
        if candidate.get("target_same_floor") is not True:
            blockers.append("target_different_floor")
        if candidate.get("target_visible") is not True:
            blockers.append("target_not_visible")
        distance = candidate.get("distance")
        if (
            not isinstance(distance, (int, float))
            or distance < 0
            or distance > plan.get("max_range", plans.MAX_RANGE)
        ):
            blockers.append("target_out_of_range")
        hp_percent = candidate.get("hp_percent")
        if not isinstance(hp_percent, (int, float)) or not 1 <= hp_percent <= 100:
            blockers.append("target_hp_invalid")
        elif hp_percent > plan.get("hp_threshold", plans.HP_THRESHOLD):
            blockers.append("target_hp_above_threshold")

    unique_blockers = list(dict.fromkeys(blockers))
    if not unique_blockers:
        status = "ready_for_execution_approval"
    elif set(unique_blockers).issubset(WAITING_BLOCKERS):
        status = "waiting_for_exact_target_window"
    else:
        status = "blocked"
    return {
        "schema_version": SCHEMA,
        "created_at_unix_ms": current_ms,
        "status": status,
        "plan_sha256": plan.get("plan_sha256"),
        "approval_id": approval.get("approval_id"),
        "p11_receipt_sha256": plan.get("p11_receipt_sha256"),
        "p12_equipment_receipt_sha256": plan.get(
            "p12_equipment_receipt_sha256"
        ),
        "manifest_sha256": hashes["manifest"],
        "runtime_gates_sha256": hashes["runtime_gates"],
        "capability_sha256": hashes["capability"],
        "capability_age_ms": age_ms,
        "vocation": capability.get("vocation"),
        "target_id": plan.get("target_id"),
        "target_name_sha256": plan.get("target_name_sha256"),
        "target_observation": candidate,
        "blockers": unique_blockers,
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
