from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
ADAPTER = LUA_DIR / "ctoa_helper_otclient_observation_adapter.lua"
CORE = LUA_DIR / "ctoa_helper_runtime_core.lua"
OBSERVER = LUA_DIR / "ctoa_helper_combat_observer.lua"
RECOVERY_OBSERVER = LUA_DIR / "ctoa_helper_recovery_observer.lua"
LOADER = LUA_DIR / "ctoa_otclient_loader.lua"
REGISTRY = LUA_DIR / "ctoa_helper_modules.lua"


def test_otclient_observation_adapter_is_read_only_and_loader_wired():
    source = ADAPTER.read_text(encoding="utf-8")
    loader = LOADER.read_text(encoding="utf-8") + "\n" + REGISTRY.read_text(encoding="utf-8")

    assert '{name = "ctoa_helper_otclient_observation_adapter", file = "ctoa_helper_otclient_observation_adapter.lua"' in loader
    assert "function Adapter.combatSnapshot" in source
    assert "function Adapter.attach" in source
    assert 'mode = "read_only_adapter"' in source
    assert 'guarded_globals = {"g_game", "g_map", "g_clock"}' in source
    assert "Adapter.attachAll()" in source

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


def test_otclient_adapter_reads_mocked_state_and_attaches_disabled_task(tmp_path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for OTClient adapter behavior validation"
    probe = tmp_path / "otclient_adapter_probe.lua"
    probe.write_text(
        """
local target = {
    getName = function() return "Dragon Lord" end,
    getHealthPercent = function() return 73 end,
    getPosition = function() return {x = 103, y = 100, z = 7} end,
    canShoot = function() return true end,
    isMonster = function() return true end,
    isPlayer = function() return false end,
}
local player = {
    getPosition = function() return {x = 100, y = 100, z = 7} end,
    isInPz = function() return false end,
    getHealth = function() return 720 end,
    getMaxHealth = function() return 1000 end,
    getHealthPercent = function() return 72 end,
    getMana = function() return 350 end,
    getMaxMana = function() return 500 end,
    getManaPercent = function() return 70 end,
    getStates = function() return 16 end,
}
local party = {
    isMonster = function() return false end,
    isPlayer = function() return true end,
    isPartyMember = function() return true end,
}
g_game = {
    isOnline = function() return true end,
    getLocalPlayer = function() return player end,
    getAttackingCreature = function() return target end,
    getPing = function() return 88 end,
}
g_map = {
    getSpectators = function() return {target, party} end,
}
g_clock = {millis = function() return 1234 end}
getDistanceBetween = function(left, right) return math.abs(left.x - right.x) end
modules = {game_cooldown = {isGroupCooldownIconActive = function(group) return group == 1 end}}

local core = dofile(arg[1])
local observer = dofile(arg[2])
local recoveryObserver = dofile(arg[3])
local adapter = dofile(arg[4])
local snapshot = adapter.combatSnapshot({now_ms = 5000})
assert(snapshot.online == true)
assert(snapshot.observed_at_ms == 5000)
assert(snapshot.latency_ms == 88)
assert(snapshot.attack_cooldown == true)
assert(snapshot.spell_cooldown == false)
assert(snapshot.target.name == "Dragon Lord")
assert(snapshot.target.distance == 3)
assert(snapshot.spectators.monsters == 1)
assert(snapshot.spectators.players == 1)
assert(snapshot.spectators.party_members == 1)
local recovery = adapter.recoverySnapshot({now_ms = 5000})
assert(recovery.hp == 720 and recovery.max_hp == 1000)
assert(recovery.mana == 350 and recovery.max_mana == 500)
assert(recovery.states == 16)

local tasks = core.taskSnapshot()
assert(#tasks == 2)
assert(tasks[1].id == "combat_observer.sample")
assert(tasks[1].enabled == false)
assert(tasks[2].id == "recovery_observer.sample")
assert(tasks[2].enabled == false)
local contract = adapter.contract()
assert(contract.runtime_actions == false and contract.attacks == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(CORE), str(OBSERVER), str(RECOVERY_OBSERVER), str(ADAPTER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
