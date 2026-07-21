from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_conditions_execute_once.lua"
REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
DIAGNOSTICS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_diagnostics.lua"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_p12_conditions_bridge_static_contract_and_registry():
    source = MODULE.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    assert 'mode = "sandbox_execute_once"' in source
    assert 'exact_action = "cast_exura_ico"' in source
    assert 'exact_spell = "exura ico"' in source
    assert 'exact_vocation = "ek"' in source
    assert "retry_budget = 0" in source
    assert "mandatory_kill_and_disarm_after_attempt = true" in source
    assert "schedules_retry = false" in source
    assert "live_promotion = false" in source
    assert "ctoa_helper_conditions_execute_once.lua" in registry
    assert "function Bridge.controlExecuteOnce" in source
    assert 'marker = "/solteriacodextest/client"' in source


def test_p12_conditions_transport_is_hash_bound_and_live_excluded():
    helper = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert 'p12_conditions_execute_once = true' in helper
    assert 'action ~= "p12_conditions_execute_once"' in helper
    assert 'moduleValue(externalConditionsExecuteOnce, "controlExecuteOnce", command)' in helper
    assert 'moduleValue(externalConditionsExecuteOnce, "kill", "helper_terminate")' in helper
    for key in ("session_id", "plan_sha256", "p9_receipt_sha256", "retry_budget", "session_approved", "execution_approved"):
        assert key in diagnostics
    assert 'function Invoke-P12ConditionsExecuteOnce' in wrapper
    assert 'exactly one running sandbox process' in wrapper
    assert 'sandbox/module hash parity failed' in wrapper
    assert 'requires the global runtime to be disarmed' in wrapper
    assert 'unexpectedly armed the global runtime' in wrapper
    assert 'Live client untouched' in wrapper


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_p12_conditions_bridge_executes_exactly_once_then_kills(tmp_path):
    probe = tmp_path / "probe.lua"
    probe.write_text(
        r'''
local bridge = dofile(arg[1])
local sha = string.rep("a", 64)
local receipt = string.rep("b", 64)
local calls = 0
bridge.reset()
local armed, arm = bridge.arm({sandbox=true, operator_confirmed=true,
  runtime_disarmed=true, live_promotion=false, lane="conditions",
  action="cast_exura_ico", spell="exura ico", retry_budget=0,
  p9_acceptance_granted=true, p9_receipt_sha256=receipt,
  plan_sha256=sha, session_id="sandbox-p12-conditions"})
assert(armed == true and arm.status == "armed")
local observation = {online="online", alive="alive", protection_zone="outside",
  condition_id="paralyze", condition_state="present", cooldown="ready",
  observed_at_unix_ms=1000}
local context = {sandbox=true, session_id="sandbox-p12-conditions",
  plan_sha256=sha, p9_receipt_sha256=receipt, spell="exura ico",
  retry_budget=0, live_promotion=false, now_unix_ms=1100}
local result = bridge.executeOnce(observation, context, function(payload)
  calls = calls + 1
  assert(payload.action == "cast_exura_ico" and payload.spell == "exura ico")
  return true
end)
assert(result.status == "executed" and result.result == "success")
assert(result.final_state == "killed_and_disarmed")
assert(result.retry_scheduled == false and calls == 1)
local state = bridge.snapshot()
assert(state.armed == false and state.killed == true and state.consumed == true)
local second = bridge.executeOnce(observation, context, function() calls = calls + 1 return true end)
assert(second.status == "blocked" and second.final_state == "killed_and_disarmed")
assert(calls == 1 and bridge.snapshot().attempt_count == 1)
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)],
        check=False, capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_p12_conditions_bridge_never_calls_executor_on_stale_or_absent_condition(tmp_path):
    probe = tmp_path / "blocked.lua"
    probe.write_text(
        r'''
local bridge = dofile(arg[1])
bridge.reset()
local sha, receipt = string.rep("a",64), string.rep("b",64)
assert(bridge.arm({sandbox=true, operator_confirmed=true, runtime_disarmed=true,
  live_promotion=false, lane="conditions", action="cast_exura_ico", spell="exura ico",
  retry_budget=0, p9_acceptance_granted=true, p9_receipt_sha256=receipt,
  plan_sha256=sha, session_id="s"}) == true)
local calls = 0
local result = bridge.executeOnce({online="online", alive="alive",
  protection_zone="outside", condition_id="paralyze", condition_state="absent",
  cooldown="ready", observed_at_unix_ms=1}, {sandbox=true, session_id="s",
  plan_sha256=sha, p9_receipt_sha256=receipt, spell="exura ico", retry_budget=0,
  live_promotion=false, now_unix_ms=5000}, function() calls=calls+1 return true end)
assert(result.status == "blocked" and result.executor_called == false and calls == 0)
assert(result.final_state == "killed_and_disarmed" and result.retry_scheduled == false)
assert(result.attempt_count == 0 and result.terminal_snapshot.attempt_count == 0)
''', encoding="utf-8")
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)],
        check=False, capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_p12_conditions_observation_detects_speed_slow_without_state_bit(tmp_path):
    probe = tmp_path / "speed_slow.lua"
    probe.write_text(
        r'''
local conditions = dofile(arg[1])
local player = {
  getStates=function() return 0 end,
  hasState=function() return false end,
  getSpeed=function() return 140 end,
  getBaseSpeed=function() return 220 end,
}
local function number(obj, method)
  local value = obj and obj[method] and obj[method](obj) or nil
  return type(value) == "number" and value or nil
end
local observed = conditions.executeOnceObservation({healing={cooldown_ms=1000,last_cast_ms=0}}, 5000, {
  getLocalPlayer=function() return player end,
  readVitals=function() return {hp=100} end,
  online=function() return true end,
  inProtectionZone=function() return false end,
  hasAnyState=function() return false end,
  pcallNumber=number,
})
assert(observed.condition_state == "present")
''',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            shutil.which("lua"),
            str(probe),
            str(ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_conditions.lua"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_p12_conditions_control_path_is_sandbox_only_and_single_use(tmp_path):
    probe = tmp_path / "control.lua"
    probe.write_text(
        r'''
local bridge = dofile(arg[1])
local plan, receipt = string.rep("a",64), string.rep("b",64)
local calls, status = 0, ""
local command = {confirm=true, session_approved=true, execution_approved=true,
  retry_budget="0", plan_sha256=plan, p9_receipt_sha256=receipt, session_id="approved-session"}
bridge.reset()
bridge.configure({work_dir=function() return "C:/Users/x/AppData/Local/Solteria/client" end,
  status=function(value) status=value end})
assert(bridge.controlExecuteOnce(command) == false)
assert(calls == 0 and status:find("sandbox required",1,true))
bridge.reset()
bridge.configure({
  work_dir=function() return "C:/Users/x/AppData/Local/SolteriaCodexTest/client/" end,
  now_ms=function() return 1100 end,
  observe=function() return {online="online",alive="alive",protection_zone="outside",
    condition_id="paralyze",condition_state="present",cooldown="ready",observed_at_unix_ms=1000} end,
  cast=function(spell) calls=calls+1; return spell == "exura ico" end,
  status=function(value) status=value end,
})
assert(bridge.controlExecuteOnce(command) == true)
assert(calls == 1 and status:find("status=executed",1,true))
local state = bridge.snapshot()
assert(state.armed == false and state.killed == true and state.consumed == true and state.attempt_count == 1)
assert(bridge.controlExecuteOnce(command) == false)
assert(calls == 1 and bridge.snapshot().attempt_count == 1)
''', encoding="utf-8")
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(MODULE)],
        check=False, capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
