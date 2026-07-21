#!/usr/bin/env python3
"""Validate one P12 Equipment result trace and persist its terminal receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_p12_equipment_execute_once_plan as plans
else:  # pragma: no cover
    import otclient_p12_equipment_execute_once_plan as plans

APPROVAL = plans.DEV / "p12_equipment_session_approval.json"
TRACE = plans.DEV / "p12_equipment_execute_once_trace.json"
OUTPUT = plans.DEV / "p12_equipment_execute_once_receipt.json"
SCHEMA = "ctoa.p12-equipment-execute-once-receipt.v1"
SANDBOX = Path.home() / "AppData/Local/SolteriaCodexTest/client"
CAPABILITY = SANDBOX / "mods/ctoa_otclient/ctoa_client_capabilities.json"
LOG = SANDBOX / "ctoa_local.log"
TERMINAL_PATTERN = re.compile(
    r"P12 Equipment execute-once: status=(\w+) result=(\w+) attempt=(\d+) "
    r"final=([\w_]+) retry=(true|false) armed=(true|false) killed=(true|false) "
    r"consumed=(true|false) plan=([0-9a-f]{64}) p10=([0-9a-f]{64})"
)


def _sha(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_reconciled_trace(
    plan: dict[str, Any], capability: dict[str, Any], log_text: str, *, now_ms: int
) -> dict[str, Any]:
    matches = list(TERMINAL_PATTERN.finditer(log_text))
    bound = [match for match in matches if match.group(9) == plan.get("plan_sha256")]
    if len(bound) != 1:
        raise ValueError("exactly one plan-bound terminal log entry required")
    match = bound[0]
    return {
        "schema_version": "ctoa.p12-equipment-execute-once-trace.v1",
        "created_at_unix_ms": now_ms,
        "status": match.group(1),
        "result": match.group(2),
        "action": "move_ring_candidate_to_equipment_slot",
        "before_item_id": plan.get("before_item_id"),
        "candidate_item_id": plan.get("candidate_item_id"),
        "source_container_id": plan.get("source_container_id"),
        "source_slot_index": plan.get("source_slot_index"),
        "attempt_count": int(match.group(3)),
        "retry_budget": 0,
        "executor_called": match.group(1) in {"dispatched", "failed"},
        "retry_scheduled": match.group(5) == "true",
        "final_state": match.group(4),
        "live_promotion": False,
        "plan_sha256": match.group(9),
        "p10_receipt_sha256": match.group(10),
        "post_action_observation": capability.get("equipment_shadow_observation"),
        "post_action_capability": {
            "observed_at_unix_ms": capability.get("observed_at_unix_ms"),
            "online": capability.get("online"),
            "runtime_state": capability.get("runtime_state"),
            "runtime_enabled": capability.get("runtime_enabled"),
        },
        "terminal_snapshot": {
            "armed": match.group(6) == "true",
            "killed": match.group(7) == "true",
            "consumed": match.group(8) == "true",
            "attempt_count": int(match.group(3)),
        },
        "reconciled_after_postcondition_timeout": True,
        "intrusive_actions_performed": ["move_ring_candidate_to_equipment_slot"],
    }


def build_receipt(
    plan: dict[str, Any],
    approval: dict[str, Any],
    trace: dict[str, Any],
    *,
    now_ms: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    if (
        approval.get("schema_version") != "ctoa.p12-equipment-session-approval.v1"
        or approval.get("status") != "approved"
        or approval.get("session_approved") is not True
    ):
        blockers.append("session_approval_invalid")
    if approval.get("execution_approved") is not True:
        blockers.append("execution_confirmation_missing")
    if approval.get("plan_sha256") != plan.get("plan_sha256") or trace.get(
        "plan_sha256"
    ) != plan.get("plan_sha256"):
        blockers.append("plan_binding_mismatch")
    if trace.get("p10_receipt_sha256") != plan.get("p10_receipt_sha256"):
        blockers.append("p10_receipt_binding_mismatch")
    expected = {
        "schema_version": "ctoa.p12-equipment-execute-once-trace.v1",
        "status": "dispatched",
        "result": "requested",
        "action": "move_ring_candidate_to_equipment_slot",
        "before_item_id": plan.get("before_item_id"),
        "candidate_item_id": plan.get("candidate_item_id"),
        "source_container_id": plan.get("source_container_id"),
        "source_slot_index": plan.get("source_slot_index"),
        "attempt_count": 1,
        "retry_budget": 0,
        "executor_called": True,
        "retry_scheduled": False,
        "final_state": "killed_and_disarmed",
        "live_promotion": False,
    }
    for field, value in expected.items():
        if trace.get(field) != value:
            blockers.append(f"trace_{field}_invalid")
    terminal = trace.get("terminal_snapshot")
    if not isinstance(terminal, dict) or not (
        terminal.get("armed") is False
        and terminal.get("killed") is True
        and terminal.get("consumed") is True
        and terminal.get("attempt_count") == 1
    ):
        blockers.append("terminal_disarm_not_proven")
    post = trace.get("post_action_observation")
    if not isinstance(post, dict):
        blockers.append("post_action_observation_missing")
        post = {}
    post_ring = post.get("ring") if isinstance(post.get("ring"), dict) else {}
    if not (
        post_ring.get("present") is True
        and post_ring.get("item_id") == plan.get("requires_post_action_ring_id")
        and post_ring.get("count") == 1
    ):
        blockers.append("post_action_ring_not_proven")
    if not (
        post.get("online") == "online"
        and post.get("alive") == "alive"
        and post.get("inventory_api_available") is True
        and post.get("containers_complete") is True
    ):
        blockers.append("post_action_observation_unsafe")
    rollback = (
        post.get("candidates") if isinstance(post.get("candidates"), list) else []
    )
    rollback_matches = [
        item
        for item in rollback
        if isinstance(item, dict)
        and item.get("item_id") == plan.get("rollback_item_id")
    ]
    if len(rollback_matches) != 1 or not (
        rollback_matches[0].get("container_id") == plan.get("source_container_id")
        and rollback_matches[0].get("slot_index") == plan.get("source_slot_index")
        and rollback_matches[0].get("count") == 1
    ):
        blockers.append("rollback_item_location_not_proven")
    capability = trace.get("post_action_capability")
    if not isinstance(capability, dict) or not (
        capability.get("runtime_state") == "disarmed"
        and capability.get("runtime_enabled") is False
        and capability.get("online") is True
    ):
        blockers.append("post_action_capability_unsafe")

    accepted = not blockers
    basis = {
        "plan_sha256": plan.get("plan_sha256"),
        "approval_sha256": _sha(approval),
        "trace_sha256": _sha(trace),
        "p10_receipt_sha256": plan.get("p10_receipt_sha256"),
    }
    return {
        "schema_version": SCHEMA,
        "receipt_id": f"p12-equipment-{uuid.uuid4().hex[:16]}",
        "created_at_unix_ms": now_ms,
        "status": "accepted" if accepted else "rejected",
        "acceptance_granted": accepted,
        **basis,
        "acceptance_basis_sha256": _sha(basis),
        "lane": "equipment",
        "action": "move_ring_candidate_to_equipment_slot",
        "before_item_id": plan.get("before_item_id"),
        "candidate_item_id": plan.get("candidate_item_id"),
        "attempt_count": trace.get("attempt_count", 0),
        "retry_budget": 0,
        "retry_scheduled": False,
        "final_state": trace.get("final_state", "unknown"),
        "blockers": blockers,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "execute_once_allowed": False,
        "live_promotion": False,
        "downstream_authority_granted": False,
        "intrusive_actions_performed": ["move_ring_candidate_to_equipment_slot"]
        if accepted
        else [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=TRACE)
    parser.add_argument("--reconcile-sandbox", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = json.loads(plans.OUTPUT.read_text(encoding="utf-8"))
        approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
        if args.reconcile_sandbox:
            capability = json.loads(CAPABILITY.read_text(encoding="utf-8"))
            trace = build_reconciled_trace(
                plan,
                capability,
                LOG.read_text(encoding="utf-8", errors="replace"),
                now_ms=int(time.time() * 1000),
            )
            plans._atomic_write(args.trace, trace)  # noqa: SLF001
        else:
            trace = json.loads(args.trace.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Invalid receipt input: {error}", file=sys.stderr)
        return 1
    receipt = build_receipt(plan, approval, trace, now_ms=int(time.time() * 1000))
    plans._atomic_write(OUTPUT, receipt)  # noqa: SLF001
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "accepted" else 1


if __name__ == "__main__":
    sys.exit(main())
