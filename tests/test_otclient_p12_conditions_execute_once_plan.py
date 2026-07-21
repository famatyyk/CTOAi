from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.ops import otclient_p12_conditions_execute_once_plan as plan


def _write(path: Path, value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path) -> dict[str, Path]:
    source = tmp_path / "bridge.lua"
    source.write_text("return {}\n", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    ek_profile = tmp_path / "ctoa_ek_profile.lua"
    ek_profile.write_text('return { healing = { spell = "exura ico" } }\n', encoding="utf-8")
    ek_profile_sha = hashlib.sha256(ek_profile.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest_sha = _write(manifest, {"helper_version": "v2.4.1", "created_at": "2026-07-15T10:00:00", "files": [{"path": plan.MODULE_PATH, "sha256": source_sha}, {"path": plan.EK_PROFILE_PATH, "sha256": ek_profile_sha}]})
    validation = tmp_path / "validation.json"
    _write(validation, {"status": "passed", "created_at": "2026-07-15T10:00:01"})
    preflight = tmp_path / "preflight.json"
    _write(preflight, {"status": "passed", "manifest": {"sha256": manifest_sha}})
    gates = tmp_path / "gates.json"
    _write(gates, {"status": "passed", "failed_count": 0, "created_at": "2026-07-15T10:00:02"})
    contract = tmp_path / "contract.json"
    _write(contract, {"status": "passed", "failed_count": 0, "created_at": "2026-07-15T10:00:03"})
    receipt = tmp_path / "receipt.json"
    _write(receipt, {"schema_version": "ctoa.conditions-shadow-acceptance.v1", "status": "accepted", "acceptance_granted": True, "receipt_persisted": True, "action": "plan_paralyze_recovery", "condition": "paralyze", "spell": "exura", "blockers": [], "dispatch_allowed": False, "runtime_actions": False, "execute_once_allowed": False, "promotion_allowed": False})
    return {"manifest": manifest, "validation": validation, "preflight": preflight, "static_gates": gates, "module_contract": contract, "p9_receipt": receipt, "source": source, "ek_profile": ek_profile}


def test_plan_is_ready_but_never_armed_or_executed(tmp_path: Path) -> None:
    report = plan.build_plan(_fixture(tmp_path))
    assert report["status"] == "ready_for_sandbox_session_approval"
    assert report["blockers"] == []
    assert report["retry_budget"] == 0
    assert report["vocation"] == "ek"
    assert report["action"] == "cast_exura_ico"
    assert report["spell"] == "exura ico"
    assert report["mandatory_kill_and_disarm"] is True
    assert report["session_approved"] is False
    assert report["execution_approved"] is False
    assert report["attempt_count"] == 0
    assert report["final_state"] == "disarmed"
    assert report["intrusive_actions_performed"] == []
    assert all(report[key] is False for key in plan.FALSE_FLAGS)


def test_plan_fails_closed_on_manifest_drift(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    paths["source"].write_text("return {changed=true}\n", encoding="utf-8")
    report = plan.build_plan(paths)
    assert report["status"] == "blocked"
    assert "source_manifest_parity_failed" in report["blockers"]
    assert report["execute_once_allowed"] is False
