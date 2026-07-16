from __future__ import annotations

import json
from pathlib import Path

from scripts.ops import otclient_p12_conditions_execution_preflight as preflight


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _paths(tmp_path: Path, *, condition: str = "present") -> dict[str, Path]:
    paths = {name: tmp_path / f"{name}.json" for name in ("plan", "approval", "runtime_gates", "capability", "manifest")}
    _write(paths["manifest"], {"name": "manifest"})
    import hashlib
    manifest_sha = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    _write(paths["plan"], {"status": "ready_for_sandbox_session_approval", "blockers": [], "plan_sha256": "a" * 64, "p9_receipt_sha256": "b" * 64, "required_execute_confirmation": "confirm"})
    _write(paths["approval"], {"status": "approved", "session_approved": True, "execution_approved": False, "plan_sha256": "a" * 64, "p9_receipt_sha256": "b" * 64, "approval_id": "session"})
    _write(paths["runtime_gates"], {"status": "passed", "failed": [], "check_count": 19, "passed_count": 19, "manifest": {"sha256": manifest_sha}, "observed": {"runtime_state": "disarmed"}})
    _write(paths["capability"], {"observed_at_unix_ms": 1000, "heartbeat_status": "online", "online": True, "vocation": "ek", "runtime_state": "disarmed", "runtime_enabled": False, "conditions_observation": {"schema_version": "ctoa.conditions-observation.v1", "observed_at_unix_ms": 1000, "online": "online", "alive": "alive", "protection_zone": "outside", "protection_zone_source": "player_states", "condition_id": "paralyze", "condition_state": condition, "cooldown": "ready", "cooldown_source": "game_cooldown_group", "producer_source": "otclient_guarded_adapter", "dispatch_allowed": False, "runtime_actions": False, "executes_plan": False, "execute_once_allowed": False, "promotion_allowed": False}})
    return paths


def test_preflight_ready_only_with_current_present_condition(tmp_path: Path) -> None:
    report = preflight.build_preflight(_paths(tmp_path), now_ms=1100)
    assert report["status"] == "ready_for_execution_approval"
    assert report["blockers"] == []
    assert report["execution_approved"] is False
    assert report["attempt_count"] == 0
    assert report["final_state"] == "disarmed"
    assert report["intrusive_actions_performed"] == []


def test_preflight_waits_without_consuming_attempt_when_paralyze_absent(tmp_path: Path) -> None:
    report = preflight.build_preflight(_paths(tmp_path, condition="absent"), now_ms=1100)
    assert report["status"] == "waiting_for_paralyze"
    assert report["blockers"] == ["observation_condition_state_not_ready"]
    assert report["attempt_count"] == 0
    assert report["execute_once_allowed"] is False


def test_preflight_fails_closed_on_stale_heartbeat(tmp_path: Path) -> None:
    report = preflight.build_preflight(_paths(tmp_path), now_ms=20_000)
    assert report["status"] == "blocked"
    assert "capability_heartbeat_stale" in report["blockers"]


def test_preflight_rechecks_domain_after_execution_approval(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    approval = json.loads(paths["approval"].read_text(encoding="utf-8"))
    approval["execution_approved"] = True
    _write(paths["approval"], approval)
    report = preflight.build_preflight(paths, now_ms=1100)
    assert report["status"] == "ready_for_execution_approval"
    assert report["execution_approved"] is True
    assert report["attempt_count"] == 0
