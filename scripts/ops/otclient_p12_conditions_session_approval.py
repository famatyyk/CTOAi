#!/usr/bin/env python3
"""Persist a hash-bound P12 Conditions sandbox-session approval; never execute."""

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

OUTPUT = plans.DEV / "p12_conditions_session_approval.json"
SCHEMA = "ctoa.p12-conditions-session-approval.v1"


def build_approval(plan: dict[str, Any], confirmation: str, *, now_ms: int) -> dict[str, Any]:
    expected = plan.get("required_session_confirmation")
    blockers: list[str] = []
    if plan.get("schema_version") != plans.SCHEMA or plan.get("status") != "ready_for_sandbox_session_approval" or plan.get("blockers") != []:
        blockers.append("plan_not_ready")
    if confirmation != expected:
        blockers.append("operator_confirmation_mismatch")
    if any(plan.get(flag) is not False for flag in plans.FALSE_FLAGS):
        blockers.append("plan_unsafe")
    return {
        "schema_version": SCHEMA,
        "approval_id": f"p12-conditions-session-{uuid.uuid4().hex[:16]}",
        "created_at_unix_ms": now_ms,
        "status": "approved" if not blockers else "rejected",
        "session_approved": not blockers,
        "execution_approved": False,
        "plan_sha256": plan.get("plan_sha256"),
        "p9_receipt_sha256": plan.get("p9_receipt_sha256"),
        "confirmation_sha256": hashlib.sha256(confirmation.encode()).hexdigest(),
        "blockers": blockers,
        "lane": "conditions",
        "vocation": "ek",
        "action": "cast_exura_ico",
        "spell": "exura ico",
        "retry_budget": 0,
        "attempt_count": 0,
        "final_state": "disarmed",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "execute_once_allowed": False,
        "live_promotion": False,
        "intrusive_actions_performed": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args(argv)
    current = plans.build_plan()
    persisted = json.loads(plans.OUTPUT.read_text(encoding="utf-8")) if plans.OUTPUT.exists() else {}
    if persisted.get("plan_sha256") != current.get("plan_sha256"):
        print("Refusing approval: persisted and recomputed plan differ.", file=sys.stderr)
        return 1
    approval = build_approval(current, args.confirmation, now_ms=int(time.time() * 1000))
    if approval["status"] != "approved":
        print(json.dumps(approval, indent=2, sort_keys=True))
        return 1
    plans._atomic_write(OUTPUT, approval)  # noqa: SLF001
    print(json.dumps(approval, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
