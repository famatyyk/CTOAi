#!/usr/bin/env python3
"""Close the ED-only P12 Heal Friend session without performing an action."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_p12_heal_friend_execute_once_plan as plans
    from . import otclient_p12_heal_friend_execution_preflight as preflights
    from . import otclient_p12_heal_friend_session_approval as approvals
else:  # pragma: no cover
    import otclient_p12_heal_friend_execute_once_plan as plans
    import otclient_p12_heal_friend_execution_preflight as preflights
    import otclient_p12_heal_friend_session_approval as approvals

PREFLIGHT = plans.DEV / "p12_heal_friend_execution_preflight.json"
OUTPUT = plans.DEV / "p12_heal_friend_no_compatible_vocation_closure.json"
SCHEMA = "ctoa.p12-heal-friend-no-compatible-vocation-closure.v1"
EXPECTED_CONFIRMATION = "nie mam zadnego ed ... mam tylko sorcera i knighta"
AVAILABLE_VOCATIONS = ("sorcerer", "knight")
REQUIRED_PREFLIGHT_BLOCKERS = ["vocation_must_be_ed"]
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


def build_closure(
    paths: dict[str, Path], confirmation: str, *, now_ms: int
) -> dict[str, Any]:
    blockers: list[str] = []
    documents: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        try:
            documents[name], hashes[name] = _load(path)
        except (OSError, ValueError, json.JSONDecodeError):
            documents[name], hashes[name] = {}, "0" * 64
            blockers.append(f"{name}_missing_or_invalid")

    plan = documents.get("plan", {})
    approval = documents.get("approval", {})
    preflight = documents.get("preflight", {})
    plan_hash = plan.get("plan_sha256")
    approval_id = approval.get("approval_id")

    if not (
        plan.get("schema_version") == plans.SCHEMA
        and plan.get("status") == "ready_for_sandbox_session_approval"
        and plan.get("blockers") == []
        and plan.get("exact_vocation") == plans.EXACT_VOCATION
        and plan.get("action") == "cast_exura_sio_exact_target"
        and plan.get("spell") == plans.SPELL
        and plan.get("attempt_count") == 0
        and plan.get("retry_budget") == 0
        and plan.get("retry_scheduled") is False
        and plan.get("final_state") == "disarmed"
        and plan.get("intrusive_actions_performed") == []
        and all(plan.get(flag) is False for flag in plans.FALSE_FLAGS)
    ):
        blockers.append("plan_not_safe_to_close")

    if not (
        approval.get("schema_version") == approvals.SCHEMA
        and approval.get("status") == "approved"
        and approval.get("session_approved") is True
        and approval.get("execution_approved") is False
        and approval.get("plan_sha256") == plan_hash
        and approval.get("exact_vocation") == plans.EXACT_VOCATION
        and approval.get("attempt_count") == 0
        and approval.get("retry_budget") == 0
        and approval.get("final_state") == "disarmed"
        and approval.get("intrusive_actions_performed") == []
        and all(approval.get(flag) is False for flag in FALSE_FLAGS)
    ):
        blockers.append("session_approval_not_safe_to_close")

    if not (
        preflight.get("schema_version") == preflights.SCHEMA
        and preflight.get("status") == "blocked"
        and preflight.get("blockers") == REQUIRED_PREFLIGHT_BLOCKERS
        and preflight.get("plan_sha256") == plan_hash
        and preflight.get("approval_id") == approval_id
        and preflight.get("session_approved") is True
        and preflight.get("execution_approved") is False
        and preflight.get("attempt_count") == 0
        and preflight.get("retry_budget") == 0
        and preflight.get("final_state") == "disarmed"
        and preflight.get("intrusive_actions_performed") == []
        and all(preflight.get(flag) is False for flag in FALSE_FLAGS)
    ):
        blockers.append("preflight_not_ed_only_blocked_and_disarmed")

    if confirmation != EXPECTED_CONFIRMATION:
        blockers.append("operator_confirmation_mismatch")

    unique_blockers = list(dict.fromkeys(blockers))
    granted = not unique_blockers
    return {
        "schema_version": SCHEMA,
        "created_at_unix_ms": now_ms,
        "status": (
            "closed_blocked_no_compatible_vocation" if granted else "rejected"
        ),
        "closure_granted": granted,
        "closure_reason": "no_compatible_sandbox_vocation",
        "validation_blockers": unique_blockers,
        "plan_sha256": plan_hash,
        "plan_file_sha256": hashes.get("plan"),
        "approval_id": approval_id,
        "approval_file_sha256": hashes.get("approval"),
        "preflight_file_sha256": hashes.get("preflight"),
        "confirmation_sha256": hashlib.sha256(confirmation.encode()).hexdigest(),
        "lane": "heal_friend",
        "required_vocation": plans.EXACT_VOCATION,
        "operator_declared_available_vocations": list(AVAILABLE_VOCATIONS),
        "session_approval_expired": granted,
        "session_approval_reusable": False,
        "execution_approval_permitted": False,
        "attempt_count": 0,
        "retry_budget": 0,
        "retry_scheduled": False,
        "final_state": "disarmed",
        "cast_performed": False,
        "talk_performed": False,
        "downstream_authority_granted": False,
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
    closure = build_closure(
        {
            "plan": plans.OUTPUT,
            "approval": approvals.OUTPUT,
            "preflight": PREFLIGHT,
        },
        args.confirmation,
        now_ms=int(time.time() * 1000),
    )
    if closure["status"] != "closed_blocked_no_compatible_vocation":
        print(json.dumps(closure, indent=2, sort_keys=True))
        return 1
    plans._atomic_write(OUTPUT, closure)  # noqa: SLF001
    print(json.dumps(closure, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
