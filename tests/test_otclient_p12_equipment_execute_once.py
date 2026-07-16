from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_equipment_execute_once.lua"
REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
DIAGNOSTICS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_diagnostics.lua"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_equipment_bridge_static_contract_and_transport() -> None:
    source = MODULE.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert 'mode="sandbox_execute_once"' in source
    assert 'exact_action="move_ring_candidate_to_equipment_slot"' in source
    assert "before_item_id=3096" in source
    assert "candidate_item_id=3097" in source
    assert "requires_post_action_receipt=true" in source
    assert "ctoa_helper_equipment_execute_once.lua" in registry
    assert 'p12_equipment_execute_once = true' in helper
    assert 'moduleValue(externalEquipmentExecuteOnce, "controlExecuteOnce", command)' in helper
    assert 'moduleValue(externalEquipmentExecuteOnce, "kill", "helper_terminate")' in helper
    assert '"p10_receipt_sha256"' in diagnostics
    assert '"source_container_id"' in diagnostics
    assert "function Invoke-P12EquipmentExecuteOnce" in wrapper
    assert '"P12EquipmentExecuteOnce"' in wrapper
    assert '-CommandAction "p12_equipment_execute_once"' in wrapper
    assert "P10ReceiptSha256" in wrapper
    assert "no retry was attempted" in wrapper
    equipment_wrapper = wrapper.split("function Invoke-P12EquipmentExecuteOnce", 1)[1].split(
        "function Invoke-HealingVitalsSmoke", 1
    )[0]
    assert "otclient_p12_equipment_execute_once_plan.py" not in equipment_wrapper
    assert "otclient_p12_equipment_execution_preflight.py" in equipment_wrapper


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_equipment_bridge_one_request_then_terminal_disarm(tmp_path: Path) -> None:
    probe = tmp_path / "equipment.lua"
    probe.write_text(
        r'''
local bridge=dofile(arg[1]); bridge.reset(); local calls=0
local sha,receipt=string.rep("a",64),string.rep("b",64)
bridge.configure({work_dir=function() return "C:/x/SolteriaCodexTest/client" end})
assert(bridge.arm({sandbox=true,operator_confirmed=true,session_approved=true,execution_approved=true,
 runtime_disarmed=true,live_promotion=false,retry_budget=0,action="move_ring_candidate_to_equipment_slot",
 before_item_id=3096,candidate_item_id=3097,plan_sha256=sha,p10_receipt_sha256=receipt,session_id="s"})==true)
local observation={online="online",alive="alive",protection_zone="outside",inventory_api_available=true,
 containers_complete=true,ring={present=true,item_id=3096,count=1},
 candidates={{container_id=3,slot_index=1,item_id=3097,count=1}},observed_at_unix_ms=1000}
local context={session_id="s",plan_sha256=sha,p10_receipt_sha256=receipt,source_container_id=3,source_slot_index=1,now_unix_ms=1100}
local trace=bridge.executeOnce(observation,context,function(payload) calls=calls+1; return payload.item_id==3097 end)
assert(trace.status=="dispatched" and trace.result=="requested" and calls==1 and trace.attempt_count==1)
assert(trace.final_state=="killed_and_disarmed" and trace.retry_scheduled==false)
local state=bridge.snapshot(); assert(state.armed==false and state.killed==true and state.consumed==true and state.attempt_count==1)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)], check=False,
        capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_equipment_bridge_guard_rejection_does_not_consume_attempt(tmp_path: Path) -> None:
    probe = tmp_path / "blocked.lua"
    probe.write_text(
        r'''
local bridge=dofile(arg[1]); bridge.reset(); local calls=0
local sha,receipt=string.rep("a",64),string.rep("b",64)
bridge.configure({work_dir=function() return "C:/x/SolteriaCodexTest/client" end})
assert(bridge.arm({sandbox=true,operator_confirmed=true,session_approved=true,execution_approved=true,
 runtime_disarmed=true,live_promotion=false,retry_budget=0,action="move_ring_candidate_to_equipment_slot",
 before_item_id=3096,candidate_item_id=3097,plan_sha256=sha,p10_receipt_sha256=receipt,session_id="s"})==true)
local trace=bridge.executeOnce({online="online",alive="alive",protection_zone="inside",
 inventory_api_available=true,containers_complete=true,ring={present=true,item_id=3096,count=1},
 candidates={{container_id=3,slot_index=1,item_id=3097,count=1}},observed_at_unix_ms=1000},
 {session_id="s",plan_sha256=sha,p10_receipt_sha256=receipt,source_container_id=3,source_slot_index=1,now_unix_ms=1100},
 function() calls=calls+1 return true end)
assert(trace.status=="blocked" and calls==0 and trace.attempt_count==0)
assert(trace.final_state=="killed_and_disarmed" and bridge.snapshot().attempt_count==0)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)], check=False,
        capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
