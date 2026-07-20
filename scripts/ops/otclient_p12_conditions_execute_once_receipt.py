#!/usr/bin/env python3
"""Validate one P12 Conditions result trace and persist its terminal receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_p12_conditions_execute_once_plan as plans
else:  # pragma: no cover
    import otclient_p12_conditions_execute_once_plan as plans

APPROVAL = plans.DEV / "p12_conditions_session_approval.json"
TRACE = plans.DEV / "p12_conditions_execute_once_trace.json"
OUTPUT = plans.DEV / "p12_conditions_execute_once_receipt.json"
SCHEMA = "ctoa.p12-conditions-execute-once-receipt.v1"


def _sha(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_receipt(plan: dict[str, Any], approval: dict[str, Any], trace: dict[str, Any], *, now_ms: int) -> dict[str, Any]:
    blockers: list[str] = []
    if approval.get("schema_version") != "ctoa.p12-conditions-session-approval.v1" or approval.get("status") != "approved" or approval.get("session_approved") is not True:
        blockers.append("session_approval_invalid")
    if approval.get("execution_approved") is not True:
        blockers.append("execution_confirmation_missing")
    if approval.get("plan_sha256") != plan.get("plan_sha256") or trace.get("plan_sha256") != plan.get("plan_sha256"):
        blockers.append("plan_binding_mismatch")
    if trace.get("p9_receipt_sha256") != plan.get("p9_receipt_sha256"):
        blockers.append("p9_receipt_binding_mismatch")
    expected = {
        "schema_version": "ctoa.p12-conditions-execute-once-trace.v1",
        "status": "executed",
        "result": "success",
        "action": "cast_exura_ico",
        "spell": "exura ico",
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
        "p9_receipt_sha256": plan.get("p9_receipt_sha256"),
    }
    return {
        "schema_version": SCHEMA,
        "receipt_id": f"p12-conditions-{uuid.uuid4().hex[:16]}",
        "created_at_unix_ms": now_ms,
        "status": "accepted" if accepted else "rejected",
        "acceptance_granted": accepted,
        **basis,
        "acceptance_basis_sha256": _sha(basis),
        "lane": "conditions",
        "vocation": "ek",
        "action": "cast_exura_ico",
        "spell": "exura ico",
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
        "intrusive_actions_performed": ["cast_exura_ico"] if accepted else [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=TRACE)
    args = parser.parse_args(argv)
    try:
        plan = json.loads(plans.OUTPUT.read_text(encoding="utf-8"))
        approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
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
