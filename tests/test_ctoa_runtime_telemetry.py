from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
CORE = LUA_DIR / "ctoa_helper_runtime_core.lua"
DIAGNOSTICS = LUA_DIR / "ctoa_helper_diagnostics.lua"
REPORTER = LUA_DIR / "ctoa_helper_client_reporter.lua"
HELPER = LUA_DIR / "ctoa_native_helper.lua"


def test_runtime_core_telemetry_is_wired_to_diagnostics_and_reporter():
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    reporter = REPORTER.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")

    assert "function Diagnostics.runtimeCoreSnapshot" in diagnostics
    assert "function Diagnostics.runtimeCoreText" in diagnostics
    assert "runtime_core = Diagnostics.runtimeCoreSnapshot(data.runtime_core)" in diagnostics
    assert "runtime_core = snapshot.runtime_core" in diagnostics
    assert "owns_runtime_core_snapshot = true" in diagnostics
    assert "owns_runtime_core_text = true" in diagnostics
    assert "local function runtimeCoreSnapshot" in reporter
    assert "runtime_core = runtimeCoreSnapshot(data.runtime_core)" in reporter
    assert "reports_runtime_core = true" in reporter
    assert 'local externalRuntimeCore = rawget(_G, "CTOA_HELPER_RUNTIME_CORE")' in helper
    assert "runtime_core = externalRuntimeCore" in helper


def test_runtime_telemetry_reports_disabled_deferred_and_failed_states_with_real_lua(tmp_path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for runtime telemetry validation"
    probe = tmp_path / "runtime_telemetry_probe.lua"
    probe.write_text(
        """
local core = dofile(arg[1])
local diagnostics = dofile(arg[2])
local reporter = dofile(arg[3])

assert(core.registerModule({id = "observer", mode = "observer"}) == true)
assert(core.registerTask({id = "disabled", enabled = false, run = function() end}) == true)
assert(core.registerTask({id = "healthy", enabled = true, run = function() end}) == true)
assert(core.registerTask({id = "failed", enabled = true, run = function() error("boom") end}) == true)
assert(core.registerTask({id = "deferred", enabled = true, run = function() end}) == true)

local tick = core.runDue(100, {budget_ms = 100, max_tasks = 2, now_fn = function() return 0 end})
assert(#tick.ran == 2)
assert(#tick.deferred == 1)
assert(#tick.failures == 1)

local runtime = diagnostics.runtimeCoreSnapshot(core)
assert(runtime.status == "available")
assert(runtime.registered_modules == 1)
assert(runtime.registered_tasks == 4)
assert(runtime.enabled_tasks == 3)
assert(runtime.disabled_tasks == 1)
assert(runtime.failed_tasks == 1)
assert(runtime.tasks_deferred == 1)
assert(runtime.task_failures == 1)
assert(runtime.runtime_actions == false)
local text = diagnostics.runtimeCoreText(runtime)
assert(string.find(text, "tasks=3/4", 1, true))
assert(string.find(text, "deferred=1", 1, true))
assert(string.find(text, "failed=1", 1, true))

local api = diagnostics.apiProbeSnapshot({runtime_core = core})
assert(api.runtime_core.registered_tasks == 4)
local buffer, recorded = diagnostics.recordSnapshot({}, {
    snapshot = api,
    version = "test",
    reason = "runtime-core",
    captured_ms = 100,
    limit = 2,
})
assert(recorded == true)
assert(buffer[1].runtime_core.registered_tasks == 4)

local snapshot = reporter.snapshot({
    helper_version = "test",
    runtime_core = core,
    active = true,
    online = false,
})
assert(snapshot.schema_version == "ctoa-client-capabilities-v1")
assert(snapshot.runtime_core.schema_version == "ctoa.runtime-core.v1")
assert(snapshot.runtime_core.registered_tasks == 4)
assert(snapshot.runtime_core.enabled_tasks == 3)
assert(snapshot.runtime_core.disabled_tasks == 1)
assert(snapshot.runtime_core.failed_tasks == 1)
assert(snapshot.runtime_core.tasks_deferred == 1)
assert(snapshot.runtime_core.runtime_actions == false)

local unavailable = diagnostics.runtimeCoreSnapshot({statusSnapshot = function() error("broken") end})
assert(unavailable.status == "unavailable")
assert(unavailable.runtime_actions == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(CORE), str(DIAGNOSTICS), str(REPORTER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_runtime_telemetry_remains_read_only():
    combined = DIAGNOSTICS.read_text(encoding="utf-8") + REPORTER.read_text(encoding="utf-8")
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
        assert forbidden not in combined
