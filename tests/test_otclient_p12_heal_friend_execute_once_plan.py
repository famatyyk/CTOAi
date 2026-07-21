from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.ops import otclient_p12_heal_friend_execute_once_plan as plan


def _write(path: Path, value: dict) -> str:
    raw = (json.dumps(value, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path) -> dict[str, Path]:
    source = tmp_path / "bridge.lua"
    source.write_text("return {}\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest_sha = _write(
        manifest,
        {
            "helper_version": "v2.4.1",
            "files": [{"path": plan.MODULE_PATH, "sha256": source_sha}],
        },
    )
    gates = tmp_path / "gates.json"
    _write(
        gates,
        {
            "status": "passed",
            "failed": [],
            "manifest": {"sha256": manifest_sha},
            "observed": {"runtime_state": "disarmed"},
        },
    )
    report_value = {
        "schema_version": "ctoa.heal-friend-shadow-replay-report.v1",
        "status": "passed",
        "source": "operational",
        "operational_trace": {
            "schema_version": "ctoa.heal-friend-shadow-trace.v1",
            "status": "shadow_plan_ready",
            "action": "plan_sio",
            "blockers": [],
            "plan": {
                "action": "plan_sio",
                "spell": "exura sio",
                "target_id": 1234,
                "target_name": "Trusted Friend",
                "whitelist_revision": "d" * 64,
                "hp_threshold": 70,
                "max_range": 7,
                "retry_budget": 0,
                "dispatch_allowed": False,
                "runtime_actions": False,
                "casts": False,
                "talks": False,
            },
        },
    }
    report = tmp_path / "p11-report.json"
    _write(report, report_value)
    report_sha = plan._canonical_sha(report_value)  # noqa: SLF001
    receipt = tmp_path / "p11-receipt.json"
    _write(
        receipt,
        {
            "schema_version": "ctoa.heal-friend-shadow-acceptance.v1",
            "status": "accepted",
            "acceptance_granted": True,
            "blockers": [],
            "report_sha256": report_sha,
            "recomputed_report_sha256": report_sha,
            "dispatch_allowed": False,
            "runtime_actions": False,
            "execute_once_allowed": False,
            "promotion_allowed": False,
            "casts": False,
            "talks": False,
        },
    )
    equipment = tmp_path / "equipment-receipt.json"
    _write(
        equipment,
        {
            "schema_version": "ctoa.p12-equipment-execute-once-receipt.v1",
            "status": "accepted",
            "acceptance_granted": True,
            "lane": "equipment",
            "attempt_count": 1,
            "retry_budget": 0,
            "retry_scheduled": False,
            "final_state": "killed_and_disarmed",
            "blockers": [],
            "downstream_authority_granted": False,
            "dispatch_allowed": False,
            "runtime_actions": False,
            "execute_once_allowed": False,
            "live_promotion": False,
        },
    )
    return {
        "manifest": manifest,
        "runtime_gates": gates,
        "p11_receipt": receipt,
        "p11_report": report,
        "p12_equipment_receipt": equipment,
        "source": source,
    }


def test_plan_binds_exact_p11_target_and_completed_equipment(tmp_path: Path) -> None:
    report = plan.build_plan(_fixture(tmp_path))
    assert report["status"] == "ready_for_sandbox_session_approval"
    assert report["blockers"] == []
    assert report["exact_vocation"] == "ed"
    assert report["action"] == "cast_exura_sio_exact_target"
    assert report["target_id"] == 1234
    assert report["target_name"] == "trusted friend"
    assert report["target_name_sha256"] == hashlib.sha256(
        b"trusted friend"
    ).hexdigest()
    assert report["hp_threshold"] == 70
    assert report["max_range"] == 7
    assert report["attempt_count"] == 0
    assert all(report[field] is False for field in plan.FALSE_FLAGS)


def test_plan_rejects_unaccepted_equipment_predecessor(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    receipt = json.loads(paths["p12_equipment_receipt"].read_text())
    receipt["status"] = "rejected"
    _write(paths["p12_equipment_receipt"], receipt)
    report = plan.build_plan(paths)
    assert report["status"] == "blocked"
    assert "p12_equipment_receipt_invalid" in report["blockers"]


def test_plan_rejects_p11_canonical_report_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    report = json.loads(paths["p11_report"].read_text())
    report["operational_trace"]["plan"]["hp_threshold"] = 60
    _write(paths["p11_report"], report)
    blocked = plan.build_plan(paths)
    assert "p11_acceptance_invalid" in blocked["blockers"]
    assert "p11_plan_contract_mismatch" in blocked["blockers"]
