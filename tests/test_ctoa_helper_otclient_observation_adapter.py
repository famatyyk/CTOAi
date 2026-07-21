from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LUA_DIR = ROOT / "scripts" / "lua" / "otclient"
ADAPTER = LUA_DIR / "ctoa_helper_otclient_observation_adapter.lua"
REPORTER = LUA_DIR / "ctoa_helper_client_reporter.lua"
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
    assert "function Adapter.conditionsSnapshot" in source
    assert "function Adapter.attach" in source
    assert 'mode = "read_only_adapter"' in source
    assert 'guarded_globals = {"g_game", "g_map", "g_clock"}' in source
    assert "Adapter.attachAll()" in source


def test_spectator_reads_use_confirmed_mehah_global_function_signature():
    source = ADAPTER.read_text(encoding="utf-8")

    assert "pcall(map.getSpectators, position, false)" in source
    assert "pcall(map.getSpectators, playerPosition, false)" in source
    assert "pcall(map.getSpectators, map," not in source

    conditions_source = source[
        source.index("function Adapter.conditionsSnapshot") : source.index(
            "function Adapter.combatSnapshot"
        )
    ]
    for forbidden in [
        "getName",
        "getPosition",
        "getStates",
        "cycleEvent",
        "scheduleEvent",
        "addEvent",
    ]:
        assert forbidden not in conditions_source

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
    getId = function() return 111 end,
    getPosition = function() return {x = 100, y = 100, z = 7} end,
    isInPz = function() return false end,
    getHealth = function() return 720 end,
    getMaxHealth = function() return 1000 end,
    getHealthPercent = function() return 72 end,
    getMana = function() return 350 end,
    getMaxMana = function() return 500 end,
    getManaPercent = function() return 70 end,
    getStates = function() return 16 end,
    isDead = function() return false end,
    hasState = function(_, state) return state == 32 end,
    getInventoryItem = function(_, slot)
        if slot == 9 then return {getId = function() return 3051 end, getCount = function() return 1 end} end
        return nil
    end,
}
InventorySlotRing = 9
CreatureStateParalyze = 32
local party = {
    getId = function() return 424242 end,
    getName = function() return "Fixture Ally" end,
    getHealthPercent = function() return 42 end,
    getPosition = function() return {x = 102, y = 101, z = 7} end,
    canShoot = function() return true end,
    isMonster = function() return false end,
    isPlayer = function() return true end,
    isPartyMember = function() return true end,
}
g_game = {
    isOnline = function() return true end,
    getLocalPlayer = function() return player end,
    getAttackingCreature = function() return target end,
    getPing = function() return 88 end,
    getContainers = function()
        return {{getId = function() return 4 end, getItems = function()
            return {{getId = function() return 3088 end, getCount = function() return 1 end}}
        end}}
    end,
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
local reporter = dofile(arg[5])
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
local conditions = adapter.conditionsSnapshot({observed_at_unix_ms = 1752250000000})
assert(conditions.schema_version == "ctoa.conditions-observation.v1")
assert(conditions.observation_id == "conditions-1752250000000")
assert(conditions.online == "online")
assert(conditions.alive == "alive")
assert(conditions.protection_zone == "outside")
assert(conditions.protection_zone_source == "player_method")
assert(conditions.condition_id == "paralyze")
assert(conditions.condition_state == "present")
assert(conditions.cooldown == "ready")
assert(conditions.cooldown_source == "game_cooldown_group")
assert(conditions.producer_source == "otclient_guarded_adapter")
assert(conditions.dispatch_allowed == false and conditions.runtime_actions == false)
assert(conditions.executes_plan == false and conditions.execute_once_allowed == false)
assert(conditions.promotion_allowed == false)
local equipment = adapter.equipmentShadowObservation({observed_at_unix_ms = 1752250000000})
assert(equipment.schema_version == "ctoa.equipment-shadow-observation.v1")
assert(equipment.ring.present == true and equipment.ring.item_id == 3051)
assert(#equipment.candidates == 1 and equipment.candidates[1].item_id == 3088)
assert(equipment.producer_source == "otclient_guarded_adapter")
assert(equipment.dispatch_allowed == false and equipment.runtime_actions == false)
local healFriend = adapter.healFriendScan({observed_at_unix_ms = 1752250000000})
assert(healFriend.schema_version == "ctoa.heal-friend-scan.v1")
assert(healFriend.self_id == 111 and healFriend.scan_complete == true)
assert(#healFriend.candidates == 1)
assert(healFriend.candidates[1].target_id == 424242)
assert(healFriend.candidates[1].target_name == "fixture ally")
assert(healFriend.candidates[1].target_party_member == true)
assert(healFriend.candidates[1].target_visible == true)
assert(healFriend.casts == false and healFriend.talks == false)

local conflictingPlayer = {
    isDead = function() return false end,
    hasState = function() return false end,
    isInPz = function() return false end,
    isInProtectionZone = function() return true end,
}
local conflictingPz = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250001000,
    game = {
        isOnline = function() return true end,
        getLocalPlayer = function() return conflictingPlayer end,
    },
    modules = modules,
})
assert(conflictingPz.protection_zone == "inside")
assert(conflictingPz.protection_zone_source == "player_method")

local nonBooleanPzPlayer = {
    isDead = function() return false end,
    hasState = function() return false end,
    isInPz = function() return nil end,
    isInProtectionZone = function() return "yes" end,
}
local unknownPz = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250001500,
    game = {
        isOnline = function() return true end,
        getLocalPlayer = function() return nonBooleanPzPlayer end,
    },
    modules = modules,
})
assert(unknownPz.protection_zone == "unknown")
assert(unknownPz.protection_zone_source == "unavailable")

local stateOnlyPlayer = {
    isDead = function() return false end,
    getStates = function() return 0 end,
}
local stateOnlyOutside = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250001750,
    game = {
        isOnline = function() return true end,
        getLocalPlayer = function() return stateOnlyPlayer end,
    },
    modules = modules,
})
assert(stateOnlyOutside.protection_zone == "outside")
assert(stateOnlyOutside.protection_zone_source == "player_states")
assert(stateOnlyOutside.condition_state == "absent")

stateOnlyPlayer.getSpeed = function() return 140 end
stateOnlyPlayer.getBaseSpeed = function() return 220 end
local speedSlowedWithoutFlag = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250001775,
    game = {
        isOnline = function() return true end,
        getLocalPlayer = function() return stateOnlyPlayer end,
    },
    modules = modules,
})
assert(speedSlowedWithoutFlag.condition_state == "present")
stateOnlyPlayer.getSpeed = function() return 220 end

stateOnlyPlayer.getStates = function() return 32 + 16384 end
local stateOnlyInsideParalyzed = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250001800,
    game = {
        isOnline = function() return true end,
        getLocalPlayer = function() return stateOnlyPlayer end,
    },
    modules = modules,
})
assert(stateOnlyInsideParalyzed.protection_zone == "inside")
assert(stateOnlyInsideParalyzed.protection_zone_source == "player_states")
assert(stateOnlyInsideParalyzed.condition_state == "present")

CreatureStateParalyze = "Paralyze"
CreatureStateSlowed = "Slowed"
local noNumericPlayer = {
    isDead = function() return false end,
    isInPz = function() return false end,
    hasState = function() error("string state probes are forbidden") end,
}
local noNumericCondition = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250002000,
    game = {
        isOnline = function() return true end,
        getLocalPlayer = function() return noNumericPlayer end,
    },
    modules = modules,
})
assert(noNumericCondition.condition_state == "unknown")
CreatureStateParalyze = 32

local offline = adapter.conditionsSnapshot({
    observed_at_unix_ms = 1752250005000,
    game = {isOnline = function() return false end},
    modules = modules,
})
assert(offline.online == "offline")
assert(offline.alive == "unknown")
assert(offline.protection_zone == "unknown")
assert(offline.condition_state == "unknown")
assert(offline.cooldown == "unknown")
assert(offline.cooldown_source == "unavailable")

local heartbeat = reporter.snapshot({
    game = g_game,
    modules = modules,
    observation_adapter = adapter,
    active = true,
    online = true,
})
assert(heartbeat.conditions_observation.schema_version == "ctoa.conditions-observation.v1")
assert(heartbeat.conditions_observation.observed_at_unix_ms == heartbeat.observed_at_unix_ms)
assert(heartbeat.conditions_observation.runtime_actions == false)
assert(heartbeat.equipment_shadow_observation.schema_version == "ctoa.equipment-shadow-observation.v1")
assert(heartbeat.equipment_shadow_observation.ring.item_id == 3051)
assert(heartbeat.equipment_shadow_observation.candidates[1].container_id == 4)
assert(heartbeat.equipment_shadow_observation.runtime_actions == false)
assert(heartbeat.heal_friend_scan.schema_version == "ctoa.heal-friend-scan.v1")
assert(heartbeat.heal_friend_scan.candidates[1].target_id == 424242)
assert(heartbeat.heal_friend_scan.runtime_actions == false)
assert(heartbeat.heal_friend_scan.casts == false and heartbeat.heal_friend_scan.talks == false)

local tasks = core.taskSnapshot()
assert(#tasks == 2)
assert(tasks[1].id == "combat_observer.sample")
assert(tasks[1].enabled == false)
assert(tasks[2].id == "recovery_observer.sample")
assert(tasks[2].enabled == false)
local contract = adapter.contract()
assert(contract.runtime_actions == false and contract.attacks == false)
assert(contract.owns_equipment_shadow_observation == true)
assert(contract.owns_heal_friend_scan == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            lua,
            str(probe),
            str(CORE),
            str(OBSERVER),
            str(RECOVERY_OBSERVER),
            str(ADAPTER),
            str(REPORTER),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_reporter_rebuilds_allowlisted_observation_and_omits_poisoned_adapters(
    tmp_path,
):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for reporter boundary validation"
    probe = tmp_path / "reporter_boundary_probe.lua"
    probe.write_text(
        """
local reporter = dofile(arg[1])

local function validObservation(context)
    return {
        schema_version = "ctoa.conditions-observation.v1",
        observed_at_unix_ms = context.observed_at_unix_ms,
        observation_id = "conditions-" .. tostring(context.observed_at_unix_ms),
        online = "online",
        alive = "alive",
        protection_zone = "outside",
        protection_zone_source = "player_method",
        condition_id = "paralyze",
        condition_state = "present",
        cooldown = "ready",
        cooldown_source = "game_cooldown_group",
        producer_source = "otclient_guarded_adapter",
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
        execute_once_allowed = false,
        promotion_allowed = false,
    }
end

local function heartbeat(adapter)
    local ok, snapshot = pcall(reporter.snapshot, {
        game = {getClientVersion = function() return 1511 end},
        observation_adapter = adapter,
        helper_version = "test",
        active = true,
        online = true,
    })
    assert(ok == true)
    return snapshot
end

local clean = heartbeat({conditionsSnapshot = validObservation})
assert(type(clean.conditions_observation) == "table")
assert(clean.conditions_observation.condition_id == "paralyze")
assert(clean.conditions_observation.runtime_actions == false)
assert(clean.conditions_observation.secret_path == nil)

local poisoned = {
    {conditionsSnapshot = function(context)
        local value = validObservation(context)
        value.secret_path = "C:/private/client.log"
        return value
    end},
    {conditionsSnapshot = function(context)
        local value = validObservation(context)
        value.condition_state = value
        return value
    end},
    {conditionsSnapshot = function(context)
        local value = validObservation(context)
        value.runtime_actions = true
        return value
    end},
    {conditionsSnapshot = function(context)
        local value = validObservation(context)
        value.observed_at_unix_ms = context.observed_at_unix_ms - 1
        return value
    end},
    {conditionsSnapshot = function(context)
        local value = validObservation(context)
        value.producer_source = "fixture"
        return value
    end},
    {conditionsSnapshot = function() error("adapter failure") end},
}
for _, adapter in ipairs(poisoned) do
    local snapshot = heartbeat(adapter)
    assert(snapshot.conditions_observation == nil)
end
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(REPORTER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
