#!/usr/bin/env python3
"""Add the separate P12 Conditions execution approval; never execute the action."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from typing import Any

if __package__:
    from . import otclient_p12_conditions_execute_once_plan as plans
    from . import otclient_p12_conditions_session_approval as sessions
else:  # pragma: no cover
    import otclient_p12_conditions_execute_once_plan as plans
    import otclient_p12_conditions_session_approval as sessions


def build_execution_approval(plan: dict[str, Any], approval: dict[str, Any], confirmation: str, *, now_ms: int) -> dict[str, Any]:
    blockers: list[str] = []
    if approval.get("schema_version") != sessions.SCHEMA or approval.get("status") != "approved" or approval.get("session_approved") is not True:
        blockers.append("session_approval_invalid")
    if approval.get("plan_sha256") != plan.get("plan_sha256"):
        blockers.append("plan_binding_mismatch")
    if confirmation != plan.get("required_execute_confirmation"):
        blockers.append("operator_confirmation_mismatch")
    result = dict(approval)
    result.update({
        "status": "approved" if not blockers else "rejected",
        "execution_approved": not blockers,
        "execution_approved_at_unix_ms": now_ms if not blockers else None,
        "execution_confirmation_sha256": hashlib.sha256(confirmation.encode()).hexdigest(),
        "blockers": blockers,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "execute_once_allowed": False,
        "attempt_count": 0,
        "final_state": "disarmed",
        "intrusive_actions_performed": [],
    })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmation", required=True)
    args = parser.parse_args(argv)
    try:
        plan = json.loads(plans.OUTPUT.read_text(encoding="utf-8"))
        approval = json.loads(sessions.OUTPUT.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Invalid approval input: {error}", file=sys.stderr)
        return 1
    result = build_execution_approval(plan, approval, args.confirmation, now_ms=int(time.time() * 1000))
    if result["status"] != "approved":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    plans._atomic_write(sessions.OUTPUT, result)  # noqa: SLF001
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
