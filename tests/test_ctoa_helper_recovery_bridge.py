from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
BRIDGE = LUA_DIR / "ctoa_helper_recovery_bridge.lua"


def test_recovery_bridge_is_packaged_and_safe_by_default():
    source = BRIDGE.read_text(encoding="utf-8")
    registry = (LUA_DIR / "ctoa_helper_modules.lua").read_text(encoding="utf-8")
    wrapper = (ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1").read_text(
        encoding="utf-8"
    )
    helper = (LUA_DIR / "ctoa_native_helper.lua").read_text(encoding="utf-8")
    ui = (LUA_DIR / "ctoa_helper_ui.lua").read_text(encoding="utf-8")
    modal = (LUA_DIR / "ctoa_helper_modal.lua").read_text(encoding="utf-8")

    assert 'name = "ctoa_helper_recovery_bridge"' in registry
    assert "ctoa_helper_recovery_bridge.lua" in wrapper
    assert '"RecoveryBridgeStaticSmoke"' in wrapper
    assert 'module = "recovery_bridge"; action = "RecoveryBridgeStaticSmoke"' in wrapper
    assert "default_armed = false" in source
    assert "default_dry_run = true" in source
    assert 'mode = "sandbox_only"' in source
    assert "injected_executor_required = true" in source
    assert 'normalized:find("/solteriacodextest/client/", 1, true)' in helper
    assert "Helper.recoveryBridgeArm" in helper
    assert "Helper.recoveryBridgeDryRun" in helper
    assert "Helper.recoveryBridgeKill" in helper
    assert 'moduleValue(externalRecoveryBridge, "dispatch"' in helper
    assert 'bridgeTrace.status == "executed"' in helper
    assert "protection_zone = isLocalPlayerInProtectionZone()" in helper
    assert '"ctoaRecoveryBridgeArm"' in ui
    assert '"ctoaRecoveryBridgeDryRun"' in ui
    assert '"ctoaRecoveryBridgeKill"' in ui
    assert "create_widget = createWidget" in helper
    assert "add_to_section = addToSection" in helper
    assert "recovery_bridge_arm = true" in modal
    for forbidden in ["g_game.", "g_map.", "castSpell(", "sendActionbarSlot(", "useWith("]:
        assert forbidden not in source


def test_recovery_bridge_dry_run_arming_execution_and_kill_switch(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for recovery-bridge validation"
    probe = tmp_path / "recovery_bridge_probe.lua"
    probe.write_text(
        """
local bridge = dofile(arg[1])
local plan = {next_action = "plan_heal", spell = "exura gran"}
local observation = {online = true, hp = 400, protection_zone = false}
local context = {now_ms = 2000, cooldown_ms = 500, client_ready = true, sandbox = true}

local preview = bridge.dispatch(plan, observation, context, function() error("must not execute") end)
assert(preview.status == "ready" and preview.result == "dry_run")
assert(preview.dispatch_allowed == false and preview.runtime_actions == false)

local armed, armedState = bridge.arm({
  session_id = "sandbox-1", sandbox = true, operator_confirmed = true, runtime_enabled = true,
})
assert(armed == true and armedState.status == "armed")
context.dry_run = false
context.session_id = "sandbox-1"
local calls = 0
local executed = bridge.dispatch(plan, observation, context, function(payload)
  calls = calls + 1
  assert(payload.action == "cast_heal" and payload.spell == "exura gran")
  return true
end)
assert(executed.status == "executed" and executed.result == "success" and calls == 1)

context.now_ms = 2100
local cooldown = bridge.dispatch(plan, observation, context, function() return true end)
assert(cooldown.status == "blocked" and cooldown.blockers[1] == "cooldown_active")

context.now_ms = 3000
context.retry_budget = 2
local firstFailure = bridge.dispatch(plan, observation, context, function() return false end)
assert(firstFailure.status == "failed")
local secondFailure = bridge.dispatch(plan, observation, context, function() return false end)
assert(secondFailure.status == "failed" and secondFailure.kill_switch == "activated")
assert(bridge.snapshot().killed == true and bridge.snapshot().armed == false)

local reset = bridge.resetKillSwitch()
assert(reset.killed == false)
local wrongSession = bridge.dispatch(plan, observation, context, function() return true end)
assert(wrongSession.status == "blocked")

observation.protection_zone = true
context.dry_run = true
local pz = bridge.dispatch(plan, observation, context, function() return true end)
assert(pz.status == "blocked")
assert(bridge.contract().live_promotion == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(BRIDGE)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_plan_heal_is_classified_and_guarded_by_runtime_policy(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for recovery-bridge validation"
    policy = LUA_DIR / "ctoa_helper_runtime_policy.lua"
    guard = LUA_DIR / "ctoa_helper_dispatch_guard.lua"
    catalog = LUA_DIR / "ctoa_helper_action_catalog.lua"
    probe = tmp_path / "recovery_bridge_policy_probe.lua"
    probe.write_text(
        """
local policy = dofile(arg[1])
local guard = dofile(arg[2])
local catalog = dofile(arg[3])
local plan = {module_id = "recovery", next_action = "plan_heal", spell = "exura"}
local classified = catalog.classify(plan)
assert(classified.domain == "recovery")
assert(classified.risk == "runtime_recovery")
assert(classified.runtime_action == true)
local gates = {
  manifest_current = true,
  module_static_gates = true,
  module_attach_smoke = true,
  smoke_attach_all = true,
  live_approval = true,
}
local policyDecision = policy.decision({
  module_id = "recovery", next_action = "plan_heal", runtime_action = true,
}, gates)
local ready = guard.decision(plan, policyDecision, {
  runtime_enabled = true, sandbox_attach_ready = true,
})
assert(policyDecision.status == "ready")
assert(ready.status == "ready" and ready.domain == "recovery")
assert(ready.dispatch_allowed == false and ready.executes_plan == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(policy), str(guard), str(catalog)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
