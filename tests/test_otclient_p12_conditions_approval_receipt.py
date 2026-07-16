from __future__ import annotations

from scripts.ops import otclient_p12_conditions_execute_once_plan as plans
from scripts.ops import otclient_p12_conditions_execute_once_receipt as receipts
from scripts.ops import otclient_p12_conditions_execution_approval as executions
from scripts.ops import otclient_p12_conditions_session_approval as approvals


def _plan() -> dict:
    return {
        "schema_version": plans.SCHEMA,
        "status": "ready_for_sandbox_session_approval",
        "blockers": [],
        "plan_sha256": "a" * 64,
        "p9_receipt_sha256": "b" * 64,
        "required_session_confirmation": "approve session",
        **{flag: False for flag in plans.FALSE_FLAGS},
    }


def test_session_approval_never_grants_execution() -> None:
    approval = approvals.build_approval(_plan(), "approve session", now_ms=1)
    assert approval["status"] == "approved"
    assert approval["session_approved"] is True
    assert approval["execution_approved"] is False
    assert approval["attempt_count"] == 0
    assert approval["final_state"] == "disarmed"
    assert approval["intrusive_actions_performed"] == []


def test_session_approval_rejects_wrong_phrase() -> None:
    approval = approvals.build_approval(_plan(), "wrong", now_ms=1)
    assert approval["status"] == "rejected"
    assert approval["session_approved"] is False
    assert "operator_confirmation_mismatch" in approval["blockers"]


def test_execution_approval_is_separate_and_still_does_not_dispatch() -> None:
    plan = _plan()
    plan["required_execute_confirmation"] = "approve execution"
    session = approvals.build_approval(plan, "approve session", now_ms=1)
    rejected = executions.build_execution_approval(plan, session, "wrong", now_ms=2)
    assert rejected["execution_approved"] is False
    accepted = executions.build_execution_approval(plan, session, "approve execution", now_ms=2)
    assert accepted["execution_approved"] is True
    assert accepted["dispatch_allowed"] is False
    assert accepted["runtime_actions"] is False
    assert accepted["execute_once_allowed"] is False
    assert accepted["attempt_count"] == 0


def test_receipt_requires_execution_confirmation_and_terminal_disarm() -> None:
    plan = _plan()
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    trace = {
        "schema_version": "ctoa.p12-conditions-execute-once-trace.v1",
        "status": "executed", "result": "success",
        "action": "cast_exura_ico", "spell": "exura ico",
        "attempt_count": 1, "retry_budget": 0,
        "executor_called": True, "retry_scheduled": False,
        "final_state": "killed_and_disarmed", "live_promotion": False,
        "plan_sha256": "a" * 64, "p9_receipt_sha256": "b" * 64,
        "terminal_snapshot": {"armed": False, "killed": True, "consumed": True, "attempt_count": 1},
    }
    rejected = receipts.build_receipt(plan, approval, trace, now_ms=2)
    assert rejected["status"] == "rejected"
    assert "execution_confirmation_missing" in rejected["blockers"]
    approval["execution_approved"] = True
    accepted = receipts.build_receipt(plan, approval, trace, now_ms=2)
    assert accepted["status"] == "accepted"
    assert accepted["final_state"] == "killed_and_disarmed"
    assert accepted["retry_scheduled"] is False
    assert accepted["downstream_authority_granted"] is False
    assert accepted["intrusive_actions_performed"] == ["cast_exura_ico"]


def test_receipt_rejects_retry_or_nonterminal_state() -> None:
    plan = _plan()
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    approval["execution_approved"] = True
    trace = {
        "schema_version": "ctoa.p12-conditions-execute-once-trace.v1",
        "status": "executed", "result": "success",
        "action": "cast_exura_ico", "spell": "exura ico",
        "attempt_count": 1, "retry_budget": 0,
        "executor_called": True, "retry_scheduled": True,
        "final_state": "armed", "live_promotion": False,
        "plan_sha256": "a" * 64, "p9_receipt_sha256": "b" * 64,
        "terminal_snapshot": {"armed": True, "killed": False, "consumed": False, "attempt_count": 1},
    }
    receipt = receipts.build_receipt(plan, approval, trace, now_ms=2)
    assert receipt["status"] == "rejected"
    assert "trace_retry_scheduled_invalid" in receipt["blockers"]
    assert "terminal_disarm_not_proven" in receipt["blockers"]
