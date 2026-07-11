from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
PIPELINE = LUA_DIR / "ctoa_helper_decision_pipeline.lua"
REGISTRY = LUA_DIR / "ctoa_helper_modules.lua"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_decision_pipeline_is_packaged_dependency_ordered_and_passive():
    source = PIPELINE.read_text(encoding="utf-8")
    registry = REGISTRY.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    for function_name in ["components", "evaluate", "summary", "blockers", "contract"]:
        assert f"function DecisionPipeline.{function_name}" in source
    for dependency in [
        "CTOA_HELPER_PLANNER",
        "CTOA_HELPER_RUNTIME_POLICY",
        "CTOA_HELPER_DISPATCH_GUARD",
        "CTOA_HELPER_PLAN_QUEUE",
        "CTOA_HELPER_RUNTIME_READINESS",
        "CTOA_HELPER_ACTION_CATALOG",
        "CTOA_HELPER_DECISION_TRACE",
    ]:
        assert dependency in source
    assert 'name = "ctoa_helper_decision_pipeline"' in registry
    assert 'file = "ctoa_helper_decision_pipeline.lua"' in registry
    assert "ctoa_helper_decision_pipeline.lua" in wrapper
    assert "invokes_adapters = false" in source
    assert "owns_operator_blockers = true" in source
    assert "dispatch_allowed = false" in source
    assert "executes_plan = false" in source
    assert "runtime_actions = false" in source
    for forbidden in ["g_game", "g_map", "autoWalk", "castSpell", "sendActionbarSlot", "useInventoryItem"]:
        assert forbidden not in source

    helper = (LUA_DIR / "ctoa_native_helper.lua").read_text(encoding="utf-8")
    assert 'rawget(_G, "CTOA_HELPER_DECISION_PIPELINE")' in helper
    assert "Helper.evaluateDecisionPipeline = function(entries, state)" in helper
    assert 'moduleValue(externalDecisionPipeline, "evaluate", entries or {}, pipelineState)' in helper
    assert "Helper.decision_pipeline_queue = result.queue" in helper
    assert "evaluateDecisionPipeline = function(entries, state)" in helper


def test_full_decision_pipeline_with_real_lua(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for decision-pipeline validation"
    ordered_modules = [
        "ctoa_helper_domain_contract.lua",
        "ctoa_helper_planner.lua",
        "ctoa_helper_runtime_policy.lua",
        "ctoa_helper_dispatch_guard.lua",
        "ctoa_helper_plan_queue.lua",
        "ctoa_helper_runtime_readiness.lua",
        "ctoa_helper_action_catalog.lua",
        "ctoa_helper_decision_trace.lua",
        "ctoa_helper_decision_pipeline.lua",
    ]
    probe = tmp_path / "decision_pipeline_probe.lua"
    probe.write_text(
        """
for index = 1, 9 do dofile(arg[index]) end
local pipeline = CTOA_HELPER_DECISION_PIPELINE
local conditionsModule = {
  plan = function(config, observation, context)
    assert(config.enabled == true)
    assert(observation.paralyzed == true)
    return {next_action = "plan_paralyze_recovery", reason = "condition_detected"}
  end,
}
local gates = {
  manifest_current = true,
  module_static_gates = true,
  module_attach_smoke = true,
  smoke_attach_all = true,
  live_approval = true,
  conditions_runtime_gate = {
    schema_version = "ctoa.conditions-runtime-safety-gate.v1",
    evidence_id = "conditions-e1",
    gate_id = "conditions_runtime_gate",
    next_action = "plan_paralyze_recovery",
    status = "accepted",
    accepted = true,
    guard = "passed",
    dry_run = true,
    dispatch_allowed = false,
    runtime_actions = false,
    live_promotion = false,
  },
}
local result = pipeline.evaluate({{
  id = "conditions",
  module = conditionsModule,
  config = {enabled = true},
  observation = {paralyzed = true},
}}, {
  gates = gates,
  runtime_enabled = true,
  sandbox_attach_ready = true,
  context = {now = 42},
  queue_limit = 4,
})

assert(result.status == "review_ready")
assert(result.selected.next_action == "plan_paralyze_recovery")
assert(result.catalog.domain == "conditions")
assert(result.catalog.runtime_action == true)
assert(result.catalog.module_safety_gate == "conditions_runtime_gate")
assert(result.policy.status == "ready")
assert(result.policy.planner_is_passive == true)
assert(result.guard.status == "ready")
assert(#result.queue == 1)
assert(result.readiness.status == "review_ready")
assert(result.trace.risk == "runtime_recovery")
assert(result.adapter_handoff.adapter_id == "conditions_runtime")
assert(result.adapter_handoff.status == "review_ready")
assert(result.adapter_handoff.dispatch_allowed == false)
assert(result.dispatch_allowed == false)
assert(result.executes_plan == false)

local attackModule = {
  plan = function()
    return {next_action = "plan_attack", reason = "target_selected"}
  end,
}
local highRisk = pipeline.evaluate({{
  id = "combat",
  module = attackModule,
  config = {enabled = true},
  observation = {target = "Dragon"},
}}, {
  gates = gates,
  runtime_enabled = true,
  sandbox_attach_ready = true,
})
assert(highRisk.status == "blocked")
assert(highRisk.policy.status == "blocked")
assert(highRisk.policy.reasons[#highRisk.policy.reasons] == "high_risk_deferred")

gates.live_approval = false
local blocked = pipeline.evaluate({{
  id = "conditions",
  module = conditionsModule,
  config = {enabled = true},
  observation = {paralyzed = true},
}}, {
  gates = gates,
  runtime_enabled = true,
  sandbox_attach_ready = true,
})
assert(blocked.status == "blocked")
assert(blocked.policy.status == "blocked")
assert(blocked.guard.status == "blocked")
assert(blocked.adapter_handoff.dispatch_allowed == false)
assert(blocked.dispatch_allowed == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), *[str(LUA_DIR / name) for name in ordered_modules]],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_boot_phase_and_dependency_status_with_real_lua(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for boot-status validation"
    probe = tmp_path / "boot_status_probe.lua"
    probe.write_text(
        """
local registry = dofile(arg[1])
local loaded = {}
for _, module in ipairs(registry.getSupportModules()) do loaded[module.name] = true end
local ready = registry.bootSnapshot(loaded)
assert(ready.status == "ready")
assert(ready.loaded == ready.total)
assert(ready.phase_count >= 6)
assert(#ready.missing == 0)
assert(#ready.dependency_blockers == 0)
assert(string.find(registry.bootSummary(ready), "deps 0", 1, true) ~= nil)

loaded.ctoa_helper_runtime_policy = false
local blocked = registry.bootSnapshot(loaded)
assert(blocked.status == "blocked")
assert(#blocked.missing == 1)
assert(#blocked.dependency_blockers > 0)
assert(blocked.missing[1] == "ctoa_helper_runtime_policy")
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(REGISTRY)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_engine_panel_exposes_boot_pipeline_and_blocker_status():
    ui = (LUA_DIR / "ctoa_helper_ui.lua").read_text(encoding="utf-8")
    helper = (LUA_DIR / "ctoa_native_helper.lua").read_text(encoding="utf-8")

    assert 'ctx.widgets.ui_boot_status = ctx.add_footer_strip' in ui
    assert 'ctx.widgets.ui_pipeline_status = ctx.add_footer_strip' in ui
    assert 'tostring(data.boot_status or "Boot status unavailable")' in ui
    assert 'tostring(data.pipeline_status or "Decision pipeline idle")' in ui
    assert "owns_engine_status_rows = true" in ui
    assert 'moduleValue(externalModules, "bootSnapshot", loaderState.modules or {})' in helper
    assert 'moduleValue(externalModules, "bootSummary", bootSnapshot or {})' in helper
    assert 'moduleValue(externalDecisionPipeline, "summary", Helper.decision_pipeline_result or {})' in helper
