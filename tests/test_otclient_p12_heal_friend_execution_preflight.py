from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.ops import otclient_p12_heal_friend_execute_once_plan as plans
from scripts.ops import otclient_p12_heal_friend_execution_preflight as preflight
from scripts.ops import otclient_p12_heal_friend_session_approval as approvals


def _write(path: Path, value: dict) -> str:
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _paths(tmp_path: Path, *, vocation: str = "ed", target_present: bool = True) -> dict[str, Path]:
    paths = {
        name: tmp_path / f"{name}.json"
        for name in (
            "plan",
            "approval",
            "runtime_gates",
            "capability",
            "manifest",
            "p11_receipt",
            "p11_report",
            "p12_equipment_receipt",
        )
    }
    paths["source"] = tmp_path / "bridge.lua"
    paths["source"].write_text("return {}\n", encoding="utf-8")
    source_sha = hashlib.sha256(paths["source"].read_bytes()).hexdigest()
    manifest_sha = _write(paths["manifest"], {"name": "manifest"})
    _write(paths["p11_receipt"], {"accepted": True})
    p11_receipt_sha = hashlib.sha256(paths["p11_receipt"].read_bytes()).hexdigest()
    p11_report = {"report": "accepted"}
    _write(paths["p11_report"], p11_report)
    _write(paths["p12_equipment_receipt"], {"accepted": True})
    equipment_sha = hashlib.sha256(
        paths["p12_equipment_receipt"].read_bytes()
    ).hexdigest()
    plan = {
        "schema_version": plans.SCHEMA,
        "status": "ready_for_sandbox_session_approval",
        "blockers": [],
        "plan_sha256": "a" * 64,
        "manifest_sha256": manifest_sha,
        "source_sha256": source_sha,
        "p11_receipt_sha256": p11_receipt_sha,
        "p11_report_sha256": plans._canonical_sha(p11_report),  # noqa: SLF001
        "p12_equipment_receipt_sha256": equipment_sha,
        "target_id": 1234,
        "target_name": "trusted friend",
        "target_name_sha256": hashlib.sha256(b"trusted friend").hexdigest(),
        "max_range": 7,
        "hp_threshold": 70,
        "required_session_confirmation": "approve session",
        "required_execute_confirmation": "approve execution",
        **{flag: False for flag in plans.FALSE_FLAGS},
    }
    _write(paths["plan"], plan)
    approval = approvals.build_approval(plan, "approve session", now_ms=1)
    _write(paths["approval"], approval)
    _write(
        paths["runtime_gates"],
        {
            "status": "passed",
            "failed": [],
            "manifest": {"sha256": manifest_sha},
            "observed": {"runtime_state": "disarmed"},
        },
    )
    candidates = (
        [
            {
                "target_id": 1234,
                "target_name": "trusted friend",
                "hp_percent": 53,
                "distance": 2,
                "target_is_player": True,
                "target_is_self": False,
                "target_party_member": True,
                "target_same_floor": True,
                "target_visible": True,
            }
        ]
        if target_present
        else []
    )
    _write(
        paths["capability"],
        {
            "observed_at_unix_ms": 1000,
            "heartbeat_status": "online",
            "online": True,
            "vocation": vocation,
            "runtime_state": "disarmed",
            "runtime_enabled": False,
            "heal_friend_scan": {
                "schema_version": "ctoa.heal-friend-scan.v1",
                "observed_at_unix_ms": 1000,
                "online": "online",
                "alive": "alive",
                "protection_zone": "outside",
                "cooldown": "ready",
                "scan_complete": True,
                "producer_source": "otclient_guarded_adapter",
                "self_id": 999,
                "candidates": candidates,
                "dispatch_allowed": False,
                "runtime_actions": False,
                "executes_plan": False,
                "execute_once_allowed": False,
                "promotion_allowed": False,
                "casts": False,
                "talks": False,
            },
        },
    )
    return paths


def test_preflight_ready_only_for_fresh_exact_ed_target(tmp_path: Path) -> None:
    report = preflight.build_preflight(_paths(tmp_path), now_ms=1100)
    assert report["status"] == "ready_for_execution_approval"
    assert report["blockers"] == []
    assert report["execution_approved"] is False
    assert report["attempt_count"] == 0


def test_preflight_hard_blocks_ek_even_when_target_matches(tmp_path: Path) -> None:
    report = preflight.build_preflight(_paths(tmp_path, vocation="ek"), now_ms=1100)
    assert report["status"] == "blocked"
    assert "vocation_must_be_ed" in report["blockers"]


def test_preflight_waits_without_attempt_when_exact_target_absent(tmp_path: Path) -> None:
    report = preflight.build_preflight(
        _paths(tmp_path, target_present=False), now_ms=1100
    )
    assert report["status"] == "waiting_for_exact_target_window"
    assert report["blockers"] == ["exact_target_not_observed"]
    assert report["attempt_count"] == 0
    assert report["execute_once_allowed"] is False


def test_preflight_blocks_non_party_target(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    capability = json.loads(paths["capability"].read_text())
    capability["heal_friend_scan"]["candidates"][0]["target_party_member"] = False
    _write(paths["capability"], capability)
    report = preflight.build_preflight(paths, now_ms=1100)
    assert report["status"] == "blocked"
    assert "target_not_party_member" in report["blockers"]
