from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CORE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_runtime_core.lua"
LOADER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_otclient_loader.lua"
REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"
PLAN = ROOT / "docs" / "otclient" / "ctoai_runtime_2_execution_plan.md"


def test_runtime_core_is_loader_wired_and_documented():
    loader = LOADER.read_text(encoding="utf-8") + "\n" + REGISTRY.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")

    assert '{name = "ctoa_helper_runtime_core", file = "ctoa_helper_runtime_core.lua"' in loader
    assert "## Execution Sequence" in plan
    assert "### P0 — Runtime Core" in plan
    assert "Runtime action enablement: prohibited" in plan


def test_runtime_core_exposes_registry_event_bus_and_budgeted_scheduler():
    source = RUNTIME_CORE.read_text(encoding="utf-8")

    for function_name in [
        "registerModule",
        "moduleSnapshot",
        "moduleHealth",
        "subscribe",
        "publish",
        "registerTask",
        "setTaskEnabled",
        "taskSnapshot",
        "runDue",
        "metricsSnapshot",
        "statusSnapshot",
        "contract",
    ]:
        assert f"function RuntimeCore.{function_name}" in source

    assert "DEFAULT_TICK_BUDGET_MS = 4" in source
    assert "DEFAULT_MAX_TASKS_PER_TICK = 8" in source
    assert "failure_backoff_ms" in source
    assert "tasks_deferred" in source
    assert "handler_failures" in source


def test_runtime_core_is_passive_and_safe_by_default():
    source = RUNTIME_CORE.read_text(encoding="utf-8")

    for forbidden in [
        "g_game.attack",
        "g_game.talk",
        "g_game.use",
        "g_game.move",
        "autoWalk(",
        "cast(",
        "useWith(",
        "pressKey(",
    ]:
        assert forbidden not in source

    assert "enabled = item.enabled == true" in source
    assert "observer_only = item.observer_only ~= false" in source
    assert "runtime_actions = false" in source
    assert 'mode = "passive"' in source
    assert "default_tasks_enabled = false" in source


def test_runtime_core_is_failure_isolated_and_budget_bounded():
    source = RUNTIME_CORE.read_text(encoding="utf-8")

    assert "pcall(subscriber.handler, payload, name)" in source
    assert "pcall(task.run" in source
    assert "#result.ran >= maxTasks or elapsed >= budgetMs" in source
    assert "task.next_run_ms = now + task.failure_backoff_ms" in source
    assert "result.deferred" in source
    assert "result.failures" in source


def test_runtime_core_behavior_with_real_lua(tmp_path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for runtime-core behavior validation"
    probe = tmp_path / "runtime_core_probe.lua"
    probe.write_text(
        """
local core = dofile(arg[1])

local moduleOk = core.registerModule({id = "combat_observer", dependencies = {"policy"}})
assert(moduleOk == true)
local duplicateOk, duplicateReason = core.registerModule({id = "combat_observer"})
assert(duplicateOk == false and duplicateReason == "module_already_registered")

local delivered = 0
assert(core.subscribe("combat.observed", function(payload)
    delivered = delivered + payload.count
end, "healthy") == true)
assert(core.subscribe("combat.observed", function()
    error("handler failure")
end, "broken") == true)
local eventResult = core.publish("combat.observed", {count = 2})
assert(delivered == 2)
assert(eventResult.delivered == 1)
assert(#eventResult.failures == 1)

local ran = {}
for _, id in ipairs({"one", "two", "three"}) do
    assert(core.registerTask({
        id = id,
        enabled = true,
        interval_ms = 100,
        run = function(ctx)
            assert(ctx.observer_only == true)
            ran[#ran + 1] = ctx.task_id
        end,
    }) == true)
end
local tick = core.runDue(0, {budget_ms = 100, max_tasks = 2, now_fn = function() return 0 end})
assert(#tick.ran == 2)
assert(#tick.deferred == 1 and tick.deferred[1] == "three")

assert(core.registerTask({
    id = "broken_task",
    enabled = true,
    interval_ms = 100,
    failure_backoff_ms = 750,
    run = function() error("task failure") end,
}) == true)
local failureTick = core.runDue(200, {budget_ms = 100, max_tasks = 10, now_fn = function() return 0 end})
assert(#failureTick.failures == 1)
local snapshots = core.taskSnapshot()
local broken
for _, item in ipairs(snapshots) do
    if item.id == "broken_task" then broken = item end
end
assert(broken and broken.next_run_ms == 950 and broken.failures == 1)

local metrics = core.metricsSnapshot()
assert(metrics.handler_failures == 1)
assert(metrics.task_failures == 1)
assert(metrics.tasks_deferred == 1)

local status = core.statusSnapshot()
assert(status.schema_version == "ctoa.runtime-core.v1")
assert(status.runtime_actions == false)
assert(status.registered_tasks == 4)
assert(status.enabled_tasks == 4)
assert(status.failed_tasks == 1)
assert(status.tasks_deferred == 1)
assert(#status.tasks == 4)

local contract = core.contract()
assert(contract.mode == "passive")
assert(contract.runtime_actions == false)
assert(contract.default_tasks_enabled == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(RUNTIME_CORE)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
