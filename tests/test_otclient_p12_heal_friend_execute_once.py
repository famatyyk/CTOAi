from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/lua/otclient/ctoa_helper_heal_friend_execute_once.lua"
FEATURE = ROOT / "scripts/lua/otclient/ctoa_helper_heal_friend.lua"
REGISTRY = ROOT / "scripts/lua/otclient/ctoa_helper_modules.lua"
HELPER = ROOT / "scripts/lua/otclient/ctoa_native_helper.lua"
DIAGNOSTICS = ROOT / "scripts/lua/otclient/ctoa_helper_diagnostics.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def test_heal_friend_bridge_static_contract_and_transport() -> None:
    source = MODULE.read_text(encoding="utf-8")
    feature = FEATURE.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert 'mode="sandbox_execute_once"' in source
    assert 'exact_action="cast_exura_sio_exact_target"' in source
    assert 'exact_vocation="ed"' in source
    assert 'exact_spell="exura sio"' in source
    assert "mandatory_kill_and_disarm_after_attempt=true" in source
    assert "function HealFriend.executeOnceObservation" in feature
    assert "ctoa_helper_heal_friend_execute_once.lua" in registry
    assert 'p12_heal_friend_execute_once = true' in helper
    assert (
        'moduleValue(externalHealFriendExecuteOnce, "controlExecuteOnce", command)'
        in helper
    )
    assert (
        'moduleValue(externalHealFriendExecuteOnce, "kill", "helper_terminate")'
        in helper
    )
    assert '"p11_receipt_sha256"' in diagnostics
    assert '"p12_equipment_receipt_sha256"' in diagnostics
    assert '"target_name"' in diagnostics
    assert "function Invoke-P12HealFriendExecuteOnce" in wrapper
    assert '"P12HealFriendExecuteOnce"' in wrapper
    assert '-CommandAction "p12_heal_friend_execute_once"' in wrapper
    assert "P11ReceiptSha256" in wrapper
    assert "P12EquipmentReceiptSha256" in wrapper
    assert "no retry was attempted" in wrapper


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_heal_friend_bridge_one_exact_cast_then_terminal_disarm(
    tmp_path: Path,
) -> None:
    probe = tmp_path / "heal_friend.lua"
    probe.write_text(
        r'''
local bridge=dofile(arg[1]); bridge.reset(); local calls=0
local sha,p11,equipment,whitelist=string.rep("a",64),string.rep("b",64),string.rep("c",64),string.rep("d",64)
bridge.configure({work_dir=function() return "C:/x/SolteriaCodexTest/client" end})
assert(bridge.arm({sandbox=true,operator_confirmed=true,session_approved=true,execution_approved=true,
 runtime_disarmed=true,live_promotion=false,retry_budget=0,action="cast_exura_sio_exact_target",spell="exura sio",
 vocation="ed",target_id=1234,target_name="trusted friend",hp_threshold=70,max_range=7,
 whitelist_revision=whitelist,plan_sha256=sha,p11_receipt_sha256=p11,
 p12_equipment_receipt_sha256=equipment,session_id="s"})==true)
local observation={schema_version="ctoa.p12-heal-friend-execute-once-observation.v1",observed_at_unix_ms=1000,
 online="online",alive="alive",protection_zone="outside",cooldown="ready",scan_complete=true,self_id=999,
 dispatch_allowed=false,runtime_actions=false,executes_plan=false,execute_once_allowed=false,promotion_allowed=false,casts=false,talks=false,
 exact_target={status="observed",match_count=1,target_id=1234,target_name="trusted friend",target_is_player=true,
 target_is_self=false,target_party_member=true,target_same_floor=true,target_visible=true,distance=2,hp_percent=53}}
local context={session_id="s",plan_sha256=sha,p11_receipt_sha256=p11,p12_equipment_receipt_sha256=equipment,
 vocation="ed",now_unix_ms=1100}
local trace=bridge.executeOnce(observation,context,function(phrase) calls=calls+1; return phrase=='exura sio "trusted friend' end)
assert(trace.status=="executed" and trace.result=="success" and calls==1 and trace.attempt_count==1)
assert(trace.final_state=="killed_and_disarmed" and trace.retry_scheduled==false)
local state=bridge.snapshot(); assert(state.armed==false and state.killed==true and state.consumed==true and state.attempt_count==1)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_heal_friend_bridge_blocks_wrong_vocation_without_cast(tmp_path: Path) -> None:
    probe = tmp_path / "blocked.lua"
    probe.write_text(
        r'''
local bridge=dofile(arg[1]); bridge.reset()
local sha,p11,equipment,whitelist=string.rep("a",64),string.rep("b",64),string.rep("c",64),string.rep("d",64)
bridge.configure({work_dir=function() return "C:/x/SolteriaCodexTest/client" end})
local armed,reason=bridge.arm({sandbox=true,operator_confirmed=true,session_approved=true,execution_approved=true,
 runtime_disarmed=true,live_promotion=false,retry_budget=0,action="cast_exura_sio_exact_target",spell="exura sio",
 vocation="ek",target_id=1234,target_name="trusted friend",hp_threshold=70,max_range=7,
 whitelist_revision=whitelist,plan_sha256=sha,p11_receipt_sha256=p11,p12_equipment_receipt_sha256=equipment,session_id="s"})
assert(armed==false and string.find(reason,"vocation_must_be_ed",1,true)~=nil)
assert(bridge.snapshot().attempt_count==0)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
