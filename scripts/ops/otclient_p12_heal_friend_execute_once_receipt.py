#!/usr/bin/env python3
"""Validate one P12 Heal Friend trace and persist its terminal receipt."""

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
    from . import otclient_p12_heal_friend_execute_once_plan as plans
else:  # pragma: no cover
    import otclient_p12_heal_friend_execute_once_plan as plans

APPROVAL = plans.DEV / "p12_heal_friend_session_approval.json"
TRACE = plans.DEV / "p12_heal_friend_execute_once_trace.json"
OUTPUT = plans.DEV / "p12_heal_friend_execute_once_receipt.json"
SCHEMA = "ctoa.p12-heal-friend-execute-once-receipt.v1"
TERMINAL_PATTERN = re.compile(
    r"P12 Heal Friend execute-once: status=(\w+) result=(\w+) attempt=(\d+) "
    r"final=([\w_]+) retry=(true|false) armed=(true|false) killed=(true|false) "
    r"consumed=(true|false) target=(\d+) plan=([0-9a-f]{64}) "
    r"p11=([0-9a-f]{64}) p12e=([0-9a-f]{64})"
)


def _sha(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_reconciled_trace(
    plan: dict[str, Any], log_text: str, *, now_ms: int
) -> dict[str, Any]:
    matches = list(TERMINAL_PATTERN.finditer(log_text))
    bound = [match for match in matches if match.group(10) == plan.get("plan_sha256")]
    if len(bound) != 1:
        raise ValueError("exactly one plan-bound terminal log entry required")
    match = bound[0]
    return {
        "schema_version": "ctoa.p12-heal-friend-execute-once-trace.v1",
        "created_at_unix_ms": now_ms,
        "status": match.group(1),
        "result": match.group(2),
        "action": "cast_exura_sio_exact_target",
        "spell": plans.SPELL,
        "vocation": plans.EXACT_VOCATION,
        "target_id": int(match.group(9)),
        "target_name_sha256": plan.get("target_name_sha256"),
        "whitelist_revision": plan.get("whitelist_revision"),
        "attempt_count": int(match.group(3)),
        "retry_budget": 0,
        "executor_called": match.group(1) in {"executed", "failed"},
        "retry_scheduled": match.group(5) == "true",
        "final_state": match.group(4),
        "live_promotion": False,
        "plan_sha256": match.group(10),
        "p11_receipt_sha256": match.group(11),
        "p12_equipment_receipt_sha256": match.group(12),
        "terminal_snapshot": {
            "armed": match.group(6) == "true",
            "killed": match.group(7) == "true",
            "consumed": match.group(8) == "true",
            "attempt_count": int(match.group(3)),
        },
        "intrusive_actions_performed": ["cast_exura_sio_exact_target"],
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
        approval.get("schema_version")
        != "ctoa.p12-heal-friend-session-approval.v1"
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
    if trace.get("p11_receipt_sha256") != plan.get("p11_receipt_sha256"):
        blockers.append("p11_receipt_binding_mismatch")
    if trace.get("p12_equipment_receipt_sha256") != plan.get(
        "p12_equipment_receipt_sha256"
    ):
        blockers.append("p12_equipment_receipt_binding_mismatch")
    expected = {
        "schema_version": "ctoa.p12-heal-friend-execute-once-trace.v1",
        "status": "executed",
        "result": "success",
        "action": "cast_exura_sio_exact_target",
        "spell": plans.SPELL,
        "vocation": plans.EXACT_VOCATION,
        "target_id": plan.get("target_id"),
        "target_name_sha256": plan.get("target_name_sha256"),
        "whitelist_revision": plan.get("whitelist_revision"),
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

    accepted = not blockers
    basis = {
        "plan_sha256": plan.get("plan_sha256"),
        "approval_sha256": _sha(approval),
        "trace_sha256": _sha(trace),
        "p11_receipt_sha256": plan.get("p11_receipt_sha256"),
        "p12_equipment_receipt_sha256": plan.get(
            "p12_equipment_receipt_sha256"
        ),
    }
    return {
        "schema_version": SCHEMA,
        "receipt_id": f"p12-heal-friend-{uuid.uuid4().hex[:16]}",
        "created_at_unix_ms": now_ms,
        "status": "accepted" if accepted else "rejected",
        "acceptance_granted": accepted,
        **basis,
        "acceptance_basis_sha256": _sha(basis),
        "lane": "heal_friend",
        "vocation": plans.EXACT_VOCATION,
        "action": "cast_exura_sio_exact_target",
        "spell": plans.SPELL,
        "target_id": plan.get("target_id"),
        "target_name_sha256": plan.get("target_name_sha256"),
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
        "intrusive_actions_performed": ["cast_exura_sio_exact_target"]
        if accepted
        else [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=TRACE)
    parser.add_argument("--reconcile-log", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = json.loads(plans.OUTPUT.read_text(encoding="utf-8"))
        approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
        if args.reconcile_log:
            trace = build_reconciled_trace(
                plan,
                args.reconcile_log.read_text(encoding="utf-8", errors="replace"),
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
