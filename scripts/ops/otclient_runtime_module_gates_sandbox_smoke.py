#!/usr/bin/env python3
"""Verify sequenced runtime-module gates fail closed against fresh sandbox evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .otclient_headless_evidence import (
        bounded_tail_text,
        current_session,
        latest_api_probe,
        latest_runtime_state,
    )
else:
    from otclient_headless_evidence import (
        bounded_tail_text,
        current_session,
        latest_api_probe,
        latest_runtime_state,
    )


ROOT = Path(__file__).resolve().parents[2]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
DEV = ROOT / "runtime" / "solteria_helper_dev"
PREVIEW = ROOT / "runtime" / "otclient_ui_preview"
SANDBOX = Path(os.environ.get("LOCALAPPDATA", "")) / "SolteriaCodexTest" / "client"
OUTPUT = DEV / "runtime_module_gates_sandbox_smoke.json"

GATE_FILES = {
    "conditions": "ctoa_helper_conditions_runtime_gate.lua",
    "equipment": "ctoa_helper_equipment_runtime_gate.lua",
    "heal_friend": "ctoa_helper_heal_friend_runtime_gate.lua",
}
STATIC_REPORTS = {
    "conditions": "conditions_runtime_gate_static_smoke.json",
    "equipment": "equipment_runtime_gate_static_smoke.json",
    "heal_friend": "heal_friend_runtime_gate_static_smoke.json",
}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_binding_matches(report: dict, manifest_sha256: str) -> bool:
    binding = report.get("manifest") if isinstance(report, dict) else None
    return (
        isinstance(binding, dict)
        and str(binding.get("sha256") or "").lower() == manifest_sha256.lower()
        and len(manifest_sha256) == 64
    )


def latest_smoke_all() -> Path | None:
    reports = list(PREVIEW.glob("solteria-helper-smokeall-inworld-*.json"))
    return max(reports, key=lambda path: path.stat().st_mtime) if reports else None


def run_lua_fail_closed(
    online: bool, alive: bool, client_ready: bool, outside_pz: bool
) -> tuple[dict[str, bool], str]:
    lua = shutil.which("lua")
    if not lua:
        return {
            "synthetic_action_bound_acceptance": False,
            "outside_pz_fail_closed_enforced": False,
            "actual_environment_gate_behavior": False,
            "high_risk_and_out_of_scope_deferred": False,
        }, "lua_interpreter_missing"
    probe = r"""
local engine = dofile(arg[1])
local conditions = dofile(arg[2])
local equipment = dofile(arg[3])
local healFriend = dofile(arg[4])
local policy = dofile(arg[5])
local function yes(value) return value == "true" end
local function has(values, needle)
  for _, value in ipairs(values or {}) do if value == needle then return true end end
  return false
end
local synthetic = {
  manifest_current = true, module_static_gates = true,
  module_attach_smoke = true, smoke_attach_all = true,
  sandbox = true, operator_confirmed = true, runtime_disarmed = true,
  dry_run = true, online = true, player_alive = true, client_ready = true,
  outside_protection_zone = true, protection_zone = false, live_promotion = false,
  runtime_lane_states = {combat = "disabled", cavebot = "disabled"},
}
local function with(base, extra)
  local result = {}
  for key, value in pairs(base or {}) do result[key] = value end
  for key, value in pairs(extra or {}) do result[key] = value end
  return result
end
local recoveryTrace = {
  schema_version = "ctoa.recovery-bridge-trace.v1", status = "ready",
  guard = "passed", decision = "plan_heal", dry_run = true,
  dispatch_allowed = false, runtime_actions = false,
}
local function conditionInput(base)
  return with(base, {
    next_action = "plan_paralyze_recovery", evidence_id = "sandbox-conditions-e1",
    recovery_bridge_trace = recoveryTrace, conditions_observer_smoke = true,
    conditions_observation_current = true, observation_id = "sandbox-conditions-o1",
    condition_confirmed = true, condition = "paralyze", spell = "exura",
    observed_at_ms = 1000, evaluated_at_ms = 1100,
    cooldown_ms = 1000, cooldown_elapsed_ms = 1000, retry_budget = 1,
  })
end
local function equipmentInput(base, conditionTrace)
  return with(base, {
    next_action = "plan_ring_swap", conditions_gate_trace = conditionTrace,
    evidence_id = "sandbox-equipment-e1", observation_id = "sandbox-equipment-o1",
    equipment_observer_smoke = true, equipment_observation_current = true,
    inventory_unambiguous = true, free_slot_confirmed = true, rollback_supported = true,
    equipped_item_id = 3051, candidate_item_id = 3048, rollback_item_id = 3051,
    slot_name = "ring", rollback_slot_name = "ring",
    candidate_source_container_id = 2, rollback_destination_container_id = 2,
    inventory_revision = "sandbox-inventory-r1", rollback_inventory_revision = "sandbox-inventory-r1",
    observed_at_ms = 2000, evaluated_at_ms = 2100,
    cooldown_ms = 1500, cooldown_elapsed_ms = 1500, retry_budget = 0,
  })
end
local function healInput(base, conditionTrace, equipmentTrace)
  return with(base, {
    next_action = "plan_sio", conditions_gate_trace = conditionTrace,
    equipment_gate_trace = equipmentTrace, heal_friend_no_target_smoke = true,
    evidence_id = "sandbox-heal-e1", whitelist_persistence_verified = true,
    require_whitelist = true, target_is_player = true, target_visible = true,
    target_same_floor = true, target_in_range = true, target_is_self = false,
    self_id = 1, target_id = 77, observed_target_id = 77, current_target_id = 77,
    target_name = "friend", observed_target_name = "Friend", current_target_name = "friend",
    whitelist_revision = "sandbox-whitelist-r1", persisted_whitelist_revision = "sandbox-whitelist-r1",
    persisted_whitelist_names = {"Friend"}, party_member_ids = {77},
    observed_target_hp_percent = 56, current_target_hp_percent = 55,
    hp_threshold = 70, spell = "exura sio", observed_at_ms = 3000,
    party_observed_at_ms = 3000, evaluated_at_ms = 3100,
    cooldown_ms = 1200, cooldown_elapsed_ms = 1200, retry_budget = 1,
  })
end

local c = conditions.evaluate(conditionInput(synthetic))
assert(c.accepted == true and c.dispatch_allowed == false and c.live_promotion == false)
local e = equipment.evaluate(equipmentInput(synthetic, c))
assert(e.accepted == true and e.dispatch_allowed == false and e.live_promotion == false)
local h = healFriend.evaluate(healInput(synthetic, c, e))
assert(h.accepted == true and h.dispatch_allowed == false and h.live_promotion == false)
print("synthetic_action_bound_acceptance=passed")

local pz = with(synthetic, {outside_protection_zone = false, protection_zone = true})
local pzTrace = conditions.evaluate(conditionInput(pz))
assert(pzTrace.status == "blocked" and has(pzTrace.blockers, "outside_protection_zone_required"))
assert(has(pzTrace.blockers, "protection_zone_false_required"))
print("outside_pz_fail_closed_enforced=passed")

local actual = with(synthetic, {
  online = yes(arg[6]), player_alive = yes(arg[7]), client_ready = yes(arg[8]),
  outside_protection_zone = yes(arg[9]), protection_zone = not yes(arg[9]),
})
local actualReady = yes(arg[6]) and yes(arg[7]) and yes(arg[8]) and yes(arg[9])
local actualC = conditions.evaluate(conditionInput(actual))
assert(actualC.accepted == actualReady)
local actualE = equipment.evaluate(equipmentInput(actual, actualC))
assert(actualE.accepted == actualReady)
local actualH = healFriend.evaluate(healInput(actual, actualC, actualE))
assert(actualH.accepted == actualReady)
print("actual_environment_gate_behavior=passed")

local generic = {
  manifest_current = true, module_static_gates = true, module_attach_smoke = true,
  smoke_attach_all = true, live_approval = true, combat_runtime_gate = true,
  cavebot_runtime_gate = true, conditions_runtime_gate = c, equipment_runtime_gate = e,
}
local combat = policy.decision({next_action = "plan_attack", runtime_action = false}, generic)
local cavebot = policy.decision({next_action = "plan_walk", runtime_action = false}, generic)
assert(combat.status == "blocked" and combat.reasons[#combat.reasons] == "high_risk_deferred")
assert(cavebot.status == "blocked" and cavebot.reasons[#cavebot.reasons] == "high_risk_deferred")
local poison = policy.decision({next_action = "plan_poison_recovery", runtime_action = false}, generic)
local amulet = policy.decision({next_action = "plan_amulet_swap", runtime_action = false}, generic)
assert(poison.status == "blocked" and has(poison.reasons, "action_not_approved_v1"))
assert(amulet.status == "blocked" and has(amulet.reasons, "action_not_approved_v1"))
print("high_risk_and_out_of_scope_deferred=passed")
"""
    with tempfile.TemporaryDirectory(prefix="ctoa-runtime-gates-") as temp_dir:
        probe_path = Path(temp_dir) / "probe.lua"
        probe_path.write_text(probe, encoding="utf-8")
        completed = subprocess.run(
            [
                lua,
                str(probe_path),
                str(LUA_DIR / "ctoa_helper_runtime_module_gate.lua"),
                str(LUA_DIR / GATE_FILES["conditions"]),
                str(LUA_DIR / GATE_FILES["equipment"]),
                str(LUA_DIR / GATE_FILES["heal_friend"]),
                str(LUA_DIR / "ctoa_helper_runtime_policy.lua"),
                str(online).lower(),
                str(alive).lower(),
                str(client_ready).lower(),
                str(outside_pz).lower(),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    detail = (completed.stdout + completed.stderr).strip()
    marker_names = [
        "synthetic_action_bound_acceptance",
        "outside_pz_fail_closed_enforced",
        "actual_environment_gate_behavior",
        "high_risk_and_out_of_scope_deferred",
    ]
    checks = {
        name: completed.returncode == 0 and f"{name}=passed" in completed.stdout
        for name in marker_names
    }
    return checks, detail


def main() -> int:
    manifest_path = DEV / "manifest.json"
    manifest = load_json(manifest_path)
    manifest_sha256 = sha256(manifest_path) if manifest_path.is_file() else ""
    helper_version = str(manifest.get("helper_version") or "unknown")
    initialized_marker = f"Initialized successfully {helper_version}"
    manifest_mtime = manifest_path.stat().st_mtime if manifest_path.is_file() else 0
    manifest_files = {
        item.get("path"): item
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    }
    module_attach_path = DEV / "module_attach_smoke.json"
    module_attach = load_json(module_attach_path)
    smoke_all_path = latest_smoke_all()
    smoke_all = load_json(smoke_all_path) if smoke_all_path else {}
    log_path = SANDBOX / "ctoa_local.log"
    boot_path = SANDBOX / "ctoa_boot.log"
    log_text = bounded_tail_text(log_path)
    boot_text = bounded_tail_text(boot_path)

    current_session_text = current_session(log_text)
    api_line = latest_api_probe(current_session_text)
    hp_match = re.search(r"hp=(\d+)/(\d+)", api_line)
    online = "core[online=yes" in api_line
    client_ready = "localPlayer=yes" in api_line
    alive = bool(hp_match and int(hp_match.group(1)) > 0)
    pz_match = re.search(r"\bpz=(yes|no)\b", api_line)
    outside_pz = bool(pz_match and pz_match.group(1) == "no")

    runtime_state = latest_runtime_state(current_session_text)
    checks: dict[str, bool] = {
        "manifest_present": bool(manifest.get("files")),
        "sandbox_workdir_log": log_path.is_file() and initialized_marker in log_text,
        "sandbox_online": online and client_ready and alive,
        "runtime_disarmed": runtime_state == "disarmed",
        "module_attach_sequence": module_attach.get("status") == "passed"
        and module_attach.get("required_sequence")
        == ["conditions", "equipment", "heal_friend"],
        "module_attach_current": module_attach_path.is_file()
        and manifest_binding_matches(module_attach, manifest_sha256),
        "smoke_attach_all_16": smoke_all.get("covered_count")
        == smoke_all.get("expected_count")
        == 16
        and not smoke_all.get("missing"),
        "smoke_attach_all_current": bool(
            smoke_all_path
            and manifest_binding_matches(smoke_all, manifest_sha256)
        ),
        "gate_modules_loaded": all(
            f"Loaded: ctoa_helper_{lane}_runtime_gate" in boot_text
            for lane in GATE_FILES
        ),
    }

    for lane, report_name in STATIC_REPORTS.items():
        report_path = DEV / report_name
        checks[f"{lane}_static_gate_current"] = (
            load_json(report_path).get("status") == "passed"
            and report_path.is_file()
            and report_path.stat().st_mtime >= manifest_mtime
        )
        source_path = LUA_DIR / GATE_FILES[lane]
        manifest_key = f"mods/ctoa_otclient/{GATE_FILES[lane]}"
        checks[f"{lane}_source_manifest_parity"] = (
            source_path.is_file()
            and manifest_files.get(manifest_key, {}).get("sha256")
            == sha256(source_path)
        )

    lua_checks, lua_detail = run_lua_fail_closed(
        online, alive, client_ready, outside_pz
    )
    checks.update(lua_checks)
    passed_count = sum(checks.values())
    status = "passed" if passed_count == len(checks) else "failed"
    payload = {
        "schema_version": "ctoa.runtime-module-gates-sandbox-smoke.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manifest": {
            "path": str(manifest_path.resolve()),
            "created_at": manifest.get("created_at"),
            "sha256": manifest_sha256,
        },
        "status": status,
        "mode": "in_world_fail_closed_dry_run",
        "sequence": ["conditions", "equipment", "heal_friend"],
        "check_count": len(checks),
        "passed_count": passed_count,
        "failed": [name for name, passed in checks.items() if not passed],
        "checks": checks,
        "observed": {
            "online": online,
            "player_alive": alive,
            "client_ready": client_ready,
            "outside_protection_zone_confirmed": outside_pz,
            "runtime_state": runtime_state,
            "acceptance_ready": False,
            "acceptance_blockers": [
                "real_domain_observation_required",
                "operator_confirmation_required",
                *([] if outside_pz else ["outside_protection_zone_not_confirmed"]),
            ],
        },
        "lane_results": {
            "conditions": "blocked_fail_closed",
            "equipment": "blocked_fail_closed",
            "heal_friend": "blocked_fail_closed",
            "combat": "deferred_high_risk",
            "cavebot": "deferred_high_risk",
        },
        "lua_detail": lua_detail,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "live_promotion": False,
        "next_action": (
            "Gather a real, current Conditions observation before any execute-once bridge design."
            if status == "passed"
            else "Repair stale or failed gate evidence and rerun the sandbox smoke."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)
    print(f"[runtime-module-gates-sandbox-smoke] JSON: {OUTPUT}")
    print(
        f"[runtime-module-gates-sandbox-smoke] Status: {status} ({passed_count}/{len(checks)})"
    )
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
