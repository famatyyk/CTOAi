from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
OBSERVER = LUA_DIR / "ctoa_helper_recovery_observer.lua"
CORE = LUA_DIR / "ctoa_helper_runtime_core.lua"
LOADER = LUA_DIR / "ctoa_otclient_loader.lua"
REGISTRY = LUA_DIR / "ctoa_helper_modules.lua"


def test_recovery_observer_is_loader_wired_and_passive():
    source = OBSERVER.read_text(encoding="utf-8")
    loader = LOADER.read_text(encoding="utf-8") + "\n" + REGISTRY.read_text(encoding="utf-8")

    assert '{name = "ctoa_helper_recovery_observer", file = "ctoa_helper_recovery_observer.lua"' in loader
    assert "function RecoveryObserver.normalizeObservation" in source
    assert "function RecoveryObserver.observe" in source
    assert "function RecoveryObserver.attach" in source
    assert 'schema_version = "ctoa.recovery-observation.v1"' in source
    assert 'EVENT_NAME = "recovery.observed"' in source
    assert "enabled = false" in source
    assert "runtime_actions = false" in source

    for forbidden in ["g_game.", "g_map.", "autoWalk(", "cast(", "useWith(", "pressKey("]:
        assert forbidden not in source


def test_recovery_observer_normalizes_vitals_and_stays_disabled_with_real_lua(tmp_path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for recovery-observer validation"
    probe = tmp_path / "recovery_observer_probe.lua"
    probe.write_text(
        """
local core = dofile(arg[1])
local observer = dofile(arg[2])
local received
assert(core.subscribe("recovery.observed", function(payload) received = payload end, "test") == true)
local result = observer.observe({
    observed_at_ms = 80,
    online = true,
    hp = 499,
    max_hp = 1000,
    hp_percent = 99,
    mana = 75,
    max_mana = 300,
    mana_percent = 99,
    states = 32,
}, core)
assert(result.published.delivered == 1)
assert(received.hp_percent == 50)
assert(received.mana_percent == 25)
assert(received.states == 32)
assert(received.runtime_actions == false)

local attached, state = observer.attach(core, function(ctx)
    return {observed_at_ms = ctx.now_ms, online = true}
end)
assert(attached == true and state.enabled == false)
local tasks = core.taskSnapshot()
assert(#tasks == 1)
assert(tasks[1].id == "recovery_observer.sample")
assert(tasks[1].enabled == false)
local tick = core.runDue(1000, {budget_ms = 100, max_tasks = 10, now_fn = function() return 0 end})
assert(#tick.ran == 0)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(CORE), str(OBSERVER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
