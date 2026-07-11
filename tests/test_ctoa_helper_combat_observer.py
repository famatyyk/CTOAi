from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OBSERVER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_observer.lua"
RUNTIME_CORE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_runtime_core.lua"
LOADER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_otclient_loader.lua"
REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"


def test_combat_observer_is_loader_wired_and_passive():
    source = OBSERVER.read_text(encoding="utf-8")
    loader = LOADER.read_text(encoding="utf-8") + "\n" + REGISTRY.read_text(encoding="utf-8")

    assert '{name = "ctoa_helper_combat_observer", file = "ctoa_helper_combat_observer.lua"' in loader
    assert "function CombatObserver.normalizeObservation" in source
    assert "function CombatObserver.observe" in source
    assert "function CombatObserver.attach" in source
    assert 'schema_version = "ctoa.combat-observation.v1"' in source
    assert 'EVENT_NAME = "combat.observed"' in source
    assert "enabled = false" in source
    assert "runtime_actions = false" in source

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


def test_combat_observer_normalization_and_disabled_attach_with_real_lua(tmp_path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for combat-observer behavior validation"
    probe = tmp_path / "combat_observer_probe.lua"
    probe.write_text(
        """
local core = dofile(arg[1])
local observer = dofile(arg[2])

local received
assert(core.subscribe("combat.observed", function(payload) received = payload end, "test") == true)
local result = observer.observe({
    observed_at_ms = 42,
    online = true,
    protection_zone = true,
    latency_ms = -5,
    target = {
        present = true,
        name = "Dragon",
        health_percent = 130,
        distance = 3,
        shootable = true,
        monster = true,
    },
    spectators = {monsters = 4, players = 1, party_members = 1, visible = 6},
}, core)
assert(result.published.delivered == 1)
assert(received.schema_version == "ctoa.combat-observation.v1")
assert(received.latency_ms == 0)
assert(received.target.health_percent == 100)
assert(received.target.name == "Dragon")
assert(received.spectators.monsters == 4)
assert(received.runtime_actions == false)

local attached, attachState = observer.attach(core, function(ctx)
    return {observed_at_ms = ctx.now_ms, online = true}
end)
assert(attached == true)
assert(attachState.enabled == false)
local tasks = core.taskSnapshot()
assert(#tasks == 1)
assert(tasks[1].id == "combat_observer.sample")
assert(tasks[1].enabled == false)
assert(tasks[1].observer_only == true)
local tick = core.runDue(1000, {budget_ms = 100, max_tasks = 10, now_fn = function() return 0 end})
assert(#tick.ran == 0)

local contract = observer.contract()
assert(contract.mode == "passive_observer")
assert(contract.runtime_actions == false)
assert(contract.attacks == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(RUNTIME_CORE), str(OBSERVER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
