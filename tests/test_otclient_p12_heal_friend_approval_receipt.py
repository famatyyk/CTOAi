from __future__ import annotations

import hashlib

from scripts.ops import otclient_p12_heal_friend_execute_once_plan as plans
from scripts.ops import otclient_p12_heal_friend_execute_once_receipt as receipts
from scripts.ops import otclient_p12_heal_friend_execution_approval as executions
from scripts.ops import otclient_p12_heal_friend_session_approval as approvals


def _plan() -> dict:
    return {
        "schema_version": plans.SCHEMA,
        "status": "ready_for_sandbox_session_approval",
        "blockers": [],
        "plan_sha256": "a" * 64,
        "p11_receipt_sha256": "b" * 64,
        "p12_equipment_receipt_sha256": "c" * 64,
        "target_id": 1234,
        "target_name": "trusted friend",
        "target_name_sha256": hashlib.sha256(b"trusted friend").hexdigest(),
        "whitelist_revision": "d" * 64,
        "required_session_confirmation": "approve session",
        "required_execute_confirmation": "approve execution",
        **{flag: False for flag in plans.FALSE_FLAGS},
    }


def _trace() -> dict:
    return {
        "schema_version": "ctoa.p12-heal-friend-execute-once-trace.v1",
        "status": "executed",
        "result": "success",
        "action": "cast_exura_sio_exact_target",
        "spell": "exura sio",
        "vocation": "ed",
        "target_id": 1234,
        "target_name_sha256": hashlib.sha256(b"trusted friend").hexdigest(),
        "whitelist_revision": "d" * 64,
        "attempt_count": 1,
        "retry_budget": 0,
        "executor_called": True,
        "retry_scheduled": False,
        "final_state": "killed_and_disarmed",
        "live_promotion": False,
        "plan_sha256": "a" * 64,
        "p11_receipt_sha256": "b" * 64,
        "p12_equipment_receipt_sha256": "c" * 64,
        "terminal_snapshot": {
            "armed": False,
            "killed": True,
            "consumed": True,
            "attempt_count": 1,
        },
    }


def test_two_separate_approvals_never_dispatch() -> None:
    plan = _plan()
    session = approvals.build_approval(plan, "approve session", now_ms=1)
    assert session["session_approved"] is True
    assert session["execution_approved"] is False
    accepted = executions.build_execution_approval(
        plan, session, "approve execution", now_ms=2
    )
    assert accepted["execution_approved"] is True
    assert accepted["dispatch_allowed"] is False
    assert accepted["runtime_actions"] is False
    assert accepted["attempt_count"] == 0


def test_receipt_requires_exact_target_and_terminal_disarm() -> None:
    plan = _plan()
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    approval = executions.build_execution_approval(
        plan, approval, "approve execution", now_ms=2
    )
    accepted = receipts.build_receipt(plan, approval, _trace(), now_ms=3)
    assert accepted["status"] == "accepted"
    assert accepted["downstream_authority_granted"] is False
    assert accepted["intrusive_actions_performed"] == [
        "cast_exura_sio_exact_target"
    ]

    trace = _trace()
    trace["target_id"] = 9999
    rejected = receipts.build_receipt(plan, approval, trace, now_ms=3)
    assert "trace_target_id_invalid" in rejected["blockers"]


def test_receipt_rejects_missing_execution_confirmation() -> None:
    plan = _plan()
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    rejected = receipts.build_receipt(plan, approval, _trace(), now_ms=3)
    assert rejected["status"] == "rejected"
    assert "execution_confirmation_missing" in rejected["blockers"]


def test_reconcile_captures_one_hash_bound_terminal_attempt() -> None:
    plan = _plan()
    line = (
        "P12 Heal Friend execute-once: status=executed result=success attempt=1 "
        "final=killed_and_disarmed retry=false armed=false killed=true "
        f"consumed=true target=1234 plan={'a' * 64} p11={'b' * 64} "
        f"p12e={'c' * 64}"
    )
    trace = receipts.build_reconciled_trace(plan, line, now_ms=4)
    assert trace["attempt_count"] == 1
    assert trace["target_id"] == 1234
    assert trace["final_state"] == "killed_and_disarmed"
    assert "target_name" not in trace
