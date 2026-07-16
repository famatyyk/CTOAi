from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
CORE = LUA_DIR / "ctoa_helper_runtime_core.lua"
COMBAT = LUA_DIR / "ctoa_helper_combat_observer.lua"
RECOVERY = LUA_DIR / "ctoa_helper_recovery_observer.lua"
CAVEBOT = LUA_DIR / "ctoa_helper_cavebot_observer.lua"
LOOT = LUA_DIR / "ctoa_helper_loot_observer.lua"
EQUIPMENT = LUA_DIR / "ctoa_helper_equipment_observer.lua"
ADAPTER = LUA_DIR / "ctoa_helper_otclient_observation_adapter.lua"
LOADER = LUA_DIR / "ctoa_otclient_loader.lua"
REGISTRY = LUA_DIR / "ctoa_helper_modules.lua"
TEST_ENV = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_remaining_observers_are_loader_wired_passive_and_disabled():
    loader = LOADER.read_text(encoding="utf-8") + "\n" + REGISTRY.read_text(encoding="utf-8")
    test_env = TEST_ENV.read_text(encoding="utf-8")
    assert "function Get-DevModuleFileNames" in test_env
    assert "foreach ($relative in Get-DevPackageFiles)" in test_env
    specs = [
        (CAVEBOT, "ctoa_helper_cavebot_observer", "ctoa.cavebot-observation.v1"),
        (LOOT, "ctoa_helper_loot_observer", "ctoa.loot-observation.v1"),
        (EQUIPMENT, "ctoa_helper_equipment_observer", "ctoa.equipment-observation.v1"),
    ]
    for path, module_name, schema in specs:
        source = path.read_text(encoding="utf-8")
        assert f'{{name = "{module_name}", file = "{module_name}.lua"' in loader
        assert f'"mods/ctoa_otclient/{module_name}.lua"' in test_env
        assert schema in source
        assert "enabled = false" in source
        assert "observer_only = true" in source
        assert "runtime_actions = false" in source
        for forbidden in ["g_game.", "autoWalk(", "findPath(", "move(", "useWith(", "cast("]:
            assert forbidden not in source

    for module_name in [
        "ctoa_helper_runtime_core",
        "ctoa_helper_otclient_observation_adapter",
    ]:
        assert f'"mods/ctoa_otclient/{module_name}.lua"' in test_env


def test_all_five_observers_attach_disabled_and_read_mocked_state_with_real_lua(tmp_path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for remaining observer validation"
    probe = tmp_path / "remaining_observers_probe.lua"
    probe.write_text(
        """
InventorySlotFinger = 1
InventorySlotNecklace = 2
InventorySlotLeft = 3
InventorySlotRight = 4

local ring = {getId = function() return 3051 end, getCount = function() return 1 end}
local sword = {getId = function() return 7405 end, getCount = function() return 1 end}
local player = {
    getPosition = function() return {x = 101, y = 202, z = 7} end,
    isInPz = function() return false end,
    isAutoWalking = function() return true end,
    autoWalk = function() end,
    getHealth = function() return 800 end,
    getMaxHealth = function() return 1000 end,
    getMana = function() return 400 end,
    getMaxMana = function() return 500 end,
    getStates = function() return 8 end,
    getFreeCapacity = function() return 321.5 end,
    getInventoryItem = function(_, slot)
        if slot == 1 then return ring end
        if slot == 3 then return sword end
        return nil
    end,
}
local container = {getItems = function() return {{}, {}, {}} end}
g_game = {
    isOnline = function() return true end,
    getLocalPlayer = function() return player end,
    getAttackingCreature = function() return nil end,
    getContainers = function() return {container} end,
    getPing = function() return 44 end,
}
local tile = {isWalkable = function() return true end}
g_map = {
    getTile = function() return tile end,
    getSpectators = function() return {} end,
    findPath = function() return {} end,
}
g_clock = {millis = function() return 900 end}

local core = dofile(arg[1])
dofile(arg[2])
dofile(arg[3])
local cavebot = dofile(arg[4])
local loot = dofile(arg[5])
local equipment = dofile(arg[6])
local adapter = dofile(arg[7])

local cave = cavebot.normalizeObservation(adapter.cavebotSnapshot({now_ms = 1000}))
assert(cave.position.x == 101 and cave.position.y == 202 and cave.position.z == 7)
assert(cave.auto_walking == true and cave.can_walk == true)
assert(cave.tile_walkable == true and cave.path_api_available == true)
assert(cave.runtime_actions == false)

local lootState = loot.normalizeObservation(adapter.lootSnapshot({now_ms = 1000}))
assert(lootState.open_container_count == 1)
assert(lootState.visible_item_count == 3)
assert(lootState.free_capacity == 321.5)
assert(lootState.container_api_available == true)
assert(lootState.runtime_actions == false)

local equipmentState = equipment.normalizeObservation(adapter.equipmentSnapshot({now_ms = 1000}))
assert(equipmentState.inventory_api_available == true)
assert(equipmentState.slots.ring.present == true and equipmentState.slots.ring.item_id == 3051)
assert(equipmentState.slots.left.present == true and equipmentState.slots.left.item_id == 7405)
assert(equipmentState.slots.amulet.present == false)
assert(equipmentState.runtime_actions == false)

local status = core.statusSnapshot()
assert(status.registered_modules == 5)
assert(status.registered_tasks == 5)
assert(status.enabled_tasks == 0)
assert(status.disabled_tasks == 5)
for _, task in ipairs(status.tasks) do
    assert(task.enabled == false)
    assert(task.observer_only == true)
    assert(task.runtime_actions == false)
end
local tick = core.runDue(2000, {budget_ms = 100, max_tasks = 10, now_fn = function() return 0 end})
assert(#tick.ran == 0)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            lua,
            str(probe),
            str(CORE),
            str(COMBAT),
            str(RECOVERY),
            str(CAVEBOT),
            str(LOOT),
            str(EQUIPMENT),
            str(ADAPTER),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
