from __future__ import annotations

import json
from pathlib import Path

from scripts.ops import (
    otclient_p12_heal_friend_execute_once_plan as plans,
)
from scripts.ops import (
    otclient_p12_heal_friend_execution_preflight as preflights,
)
from scripts.ops import (
    otclient_p12_heal_friend_no_compatible_vocation_closure as closures,
)
from scripts.ops import (
    otclient_p12_heal_friend_session_approval as approvals,
)


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _paths(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "plan": tmp_path / "plan.json",
        "approval": tmp_path / "approval.json",
        "preflight": tmp_path / "preflight.json",
    }
    safe_flags = {flag: False for flag in plans.FALSE_FLAGS}
    plan = {
        "schema_version": plans.SCHEMA,
        "status": "ready_for_sandbox_session_approval",
        "blockers": [],
        "plan_sha256": "a" * 64,
        "exact_vocation": "ed",
        "action": "cast_exura_sio_exact_target",
        "spell": "exura sio",
        "attempt_count": 0,
        "retry_budget": 0,
        "retry_scheduled": False,
        "final_state": "disarmed",
        "intrusive_actions_performed": [],
        **safe_flags,
    }
    approval = {
        "schema_version": approvals.SCHEMA,
        "status": "approved",
        "approval_id": "p12-heal-friend-session-test",
        "session_approved": True,
        "execution_approved": False,
        "plan_sha256": plan["plan_sha256"],
        "exact_vocation": "ed",
        "attempt_count": 0,
        "retry_budget": 0,
        "final_state": "disarmed",
        "intrusive_actions_performed": [],
        **safe_flags,
    }
    preflight = {
        "schema_version": preflights.SCHEMA,
        "status": "blocked",
        "blockers": ["vocation_must_be_ed"],
        "plan_sha256": plan["plan_sha256"],
        "approval_id": approval["approval_id"],
        "session_approved": True,
        "execution_approved": False,
        "attempt_count": 0,
        "retry_budget": 0,
        "final_state": "disarmed",
        "intrusive_actions_performed": [],
        **safe_flags,
    }
    _write(paths["plan"], plan)
    _write(paths["approval"], approval)
    _write(paths["preflight"], preflight)
    return paths


def test_closes_ed_only_session_without_action(tmp_path: Path) -> None:
    closure = closures.build_closure(
        _paths(tmp_path), closures.EXPECTED_CONFIRMATION, now_ms=1234
    )

    assert closure["status"] == "closed_blocked_no_compatible_vocation"
    assert closure["closure_granted"] is True
    assert closure["validation_blockers"] == []
    assert closure["operator_declared_available_vocations"] == [
        "sorcerer",
        "knight",
    ]
    assert closure["required_vocation"] == "ed"
    assert closure["session_approval_expired"] is True
    assert closure["execution_approval_permitted"] is False
    assert closure["attempt_count"] == 0
    assert closure["retry_scheduled"] is False
    assert closure["final_state"] == "disarmed"
    assert closure["cast_performed"] is False
    assert closure["downstream_authority_granted"] is False
    assert closure["intrusive_actions_performed"] == []


def test_rejects_closure_after_execution_or_attempt(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    approval = json.loads(paths["approval"].read_text(encoding="utf-8"))
    approval["execution_approved"] = True
    _write(paths["approval"], approval)
    preflight = json.loads(paths["preflight"].read_text(encoding="utf-8"))
    preflight["attempt_count"] = 1
    _write(paths["preflight"], preflight)

    closure = closures.build_closure(
        paths, closures.EXPECTED_CONFIRMATION, now_ms=1234
    )

    assert closure["status"] == "rejected"
    assert closure["closure_granted"] is False
    assert closure["session_approval_expired"] is False
    assert "session_approval_not_safe_to_close" in closure["validation_blockers"]
    assert (
        "preflight_not_ed_only_blocked_and_disarmed"
        in closure["validation_blockers"]
    )


def test_rejects_mismatched_confirmation_or_preflight_reason(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    preflight = json.loads(paths["preflight"].read_text(encoding="utf-8"))
    preflight["blockers"] = ["exact_target_not_observed"]
    _write(paths["preflight"], preflight)

    closure = closures.build_closure(paths, "different statement", now_ms=1234)

    assert closure["status"] == "rejected"
    assert "operator_confirmation_mismatch" in closure["validation_blockers"]
    assert (
        "preflight_not_ed_only_blocked_and_disarmed"
        in closure["validation_blockers"]
    )
