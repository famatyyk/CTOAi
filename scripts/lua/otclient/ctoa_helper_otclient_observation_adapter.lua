-- ctoa_helper_otclient_observation_adapter.lua [CTOA OTClient Native]
-- Guarded, read-only OTClient snapshot provider for CTOAi Runtime 2 observers.

local Adapter = rawget(_G, "CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER") or {}

local function call(owner, methodName, fallback, ...)
    if type(owner) ~= "table" and type(owner) ~= "userdata" then
        return fallback
    end
    local method = owner[methodName]
    if type(method) ~= "function" then
        return fallback
    end
    local ok, value = pcall(method, owner, ...)
    if not ok or value == nil then
        return fallback
    end
    return value
end

local function boolCall(owner, methods)
    for _, methodName in ipairs(methods or {}) do
        if call(owner, methodName, false) == true then
            return true
        end
    end
    return false
end

local function hasMethod(owner, methodName)
    return (type(owner) == "table" or type(owner) == "userdata") and type(owner[methodName]) == "function"
end

local function clockMillis()
    if g_clock and type(g_clock.millis) == "function" then
        local ok, value = pcall(g_clock.millis)
        if ok and tonumber(value) then
            return tonumber(value)
        end
    end
    return math.floor(os.clock() * 1000)
end

local function distanceBetween(left, right)
    if type(getDistanceBetween) == "function" and left and right then
        local ok, value = pcall(getDistanceBetween, left, right)
        if ok and tonumber(value) then
            return tonumber(value)
        end
    end
    return 0
end

local function targetSnapshot(game, player)
    local target = call(game, "getAttackingCreature", nil)
    if not target then
        return {present = false}
    end
    return {
        present = true,
        name = call(target, "getName", ""),
        health_percent = call(target, "getHealthPercent", 0),
        distance = distanceBetween(call(player, "getPosition", nil), call(target, "getPosition", nil)),
        shootable = call(target, "canShoot", false) == true,
        monster = call(target, "isMonster", false) == true,
        player = call(target, "isPlayer", false) == true,
    }
end

local function spectatorSnapshot(map, player)
    local position = call(player, "getPosition", nil)
    local spectators = {}
    if map and position and type(map.getSpectators) == "function" then
        local ok, result = pcall(map.getSpectators, map, position, false)
        if ok and type(result) == "table" then
            spectators = result
        end
    end
    local counts = {monsters = 0, players = 0, party_members = 0, visible = 0}
    for _, creature in pairs(spectators) do
        counts.visible = counts.visible + 1
        if call(creature, "isMonster", false) == true then
            counts.monsters = counts.monsters + 1
        elseif call(creature, "isPlayer", false) == true then
            counts.players = counts.players + 1
            if call(creature, "isPartyMember", false) == true then
                counts.party_members = counts.party_members + 1
            end
        end
    end
    return counts
end

local function cooldownActive(group)
    local cooldowns = modules and modules.game_cooldown or nil
    if not cooldowns or type(cooldowns.isGroupCooldownIconActive) ~= "function" then
        return false
    end
    local ok, active = pcall(cooldowns.isGroupCooldownIconActive, group)
    return ok and active == true
end

function Adapter.combatSnapshot(context)
    local game = rawget(_G, "g_game")
    local map = rawget(_G, "g_map")
    local online = game and call(game, "isOnline", false) == true or false
    local player = online and call(game, "getLocalPlayer", nil) or nil
    return {
        observed_at_ms = context and context.now_ms or clockMillis(),
        online = online,
        protection_zone = boolCall(player, {"isInPz", "isInProtectionZone", "isInSafeZone", "isProtected"}),
        latency_ms = game and call(game, "getPing", 0) or 0,
        action_lock_ms = 0,
        attack_cooldown = cooldownActive(1),
        spell_cooldown = cooldownActive(2),
        target = targetSnapshot(game, player),
        spectators = spectatorSnapshot(map, player),
        source = "otclient_guarded_adapter",
    }
end

function Adapter.recoverySnapshot(context)
    local game = rawget(_G, "g_game")
    local online = game and call(game, "isOnline", false) == true or false
    local player = online and call(game, "getLocalPlayer", nil) or nil
    return {
        observed_at_ms = context and context.now_ms or clockMillis(),
        online = online,
        protection_zone = boolCall(player, {"isInPz", "isInProtectionZone", "isInSafeZone", "isProtected"}),
        hp = call(player, "getHealth", 0),
        max_hp = call(player, "getMaxHealth", 0),
        hp_percent = call(player, "getHealthPercent", 0),
        mana = call(player, "getMana", 0),
        max_mana = call(player, "getMaxMana", 0),
        mana_percent = call(player, "getManaPercent", 0),
        states = call(player, "getStates", 0),
        source = "otclient_guarded_adapter",
    }
end

function Adapter.cavebotSnapshot(context)
    local game = rawget(_G, "g_game")
    local map = rawget(_G, "g_map")
    local online = game and call(game, "isOnline", false) == true or false
    local player = online and call(game, "getLocalPlayer", nil) or nil
    local position = call(player, "getPosition", nil) or {x = 0, y = 0, z = 0}
    local tile = map and call(map, "getTile", nil, position) or nil
    return {
        observed_at_ms = context and context.now_ms or clockMillis(),
        online = online,
        protection_zone = boolCall(player, {"isInPz", "isInProtectionZone", "isInSafeZone", "isProtected"}),
        position = position,
        auto_walking = call(player, "isAutoWalking", false) == true,
        can_walk = hasMethod(player, "autoWalk"),
        tile_walkable = call(tile, "isWalkable", false) == true,
        path_api_available = hasMethod(map, "findPath"),
        route_size = 0,
        route_index = 0,
        source = "otclient_guarded_adapter",
    }
end

function Adapter.lootSnapshot(context)
    local game = rawget(_G, "g_game")
    local online = game and call(game, "isOnline", false) == true or false
    local player = online and call(game, "getLocalPlayer", nil) or nil
    local containers = game and call(game, "getContainers", {}) or {}
    local containerCount, itemCount = 0, 0
    if type(containers) == "table" then
        for _, container in pairs(containers) do
            containerCount = containerCount + 1
            local items = call(container, "getItems", {})
            if type(items) == "table" then
                for _ in pairs(items) do itemCount = itemCount + 1 end
            end
        end
    end
    return {
        observed_at_ms = context and context.now_ms or clockMillis(),
        online = online,
        open_container_count = containerCount,
        visible_item_count = itemCount,
        free_capacity = call(player, "getFreeCapacity", 0),
        container_api_available = hasMethod(game, "getContainers"),
        source = "otclient_guarded_adapter",
    }
end

local function inventorySlot(player, candidates)
    if not player or type(player.getInventoryItem) ~= "function" then return {present = false} end
    for _, slotId in ipairs(candidates or {}) do
        if slotId ~= nil then
            local item = call(player, "getInventoryItem", nil, slotId)
            if item then
                return {present = true, item_id = call(item, "getId", 0), count = call(item, "getCount", 1)}
            end
        end
    end
    return {present = false}
end

function Adapter.equipmentSnapshot(context)
    local game = rawget(_G, "g_game")
    local online = game and call(game, "isOnline", false) == true or false
    local player = online and call(game, "getLocalPlayer", nil) or nil
    return {
        observed_at_ms = context and context.now_ms or clockMillis(),
        online = online,
        inventory_api_available = hasMethod(player, "getInventoryItem"),
        slots = {
            ring = inventorySlot(player, {_G.InventorySlotFinger, _G.InventorySlotRing}),
            amulet = inventorySlot(player, {_G.InventorySlotNecklace, _G.InventorySlotAmulet}),
            left = inventorySlot(player, {_G.InventorySlotLeft, _G.InventorySlotLeftHand}),
            right = inventorySlot(player, {_G.InventorySlotRight, _G.InventorySlotRightHand}),
        },
        source = "otclient_guarded_adapter",
    }
end

function Adapter.attach(runtimeCore, combatObserver)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    local observer = combatObserver or rawget(_G, "CTOA_HELPER_COMBAT_OBSERVER")
    if type(observer) ~= "table" or type(observer.attach) ~= "function" then
        return false, "combat_observer_required"
    end
    return observer.attach(core, Adapter.combatSnapshot)
end

function Adapter.attachAll(runtimeCore, combatObserver, recoveryObserver, cavebotObserver, lootObserver, equipmentObserver)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    local combat = combatObserver or rawget(_G, "CTOA_HELPER_COMBAT_OBSERVER")
    local recovery = recoveryObserver or rawget(_G, "CTOA_HELPER_RECOVERY_OBSERVER")
    local cavebot = cavebotObserver or rawget(_G, "CTOA_HELPER_CAVEBOT_OBSERVER")
    local loot = lootObserver or rawget(_G, "CTOA_HELPER_LOOT_OBSERVER")
    local equipment = equipmentObserver or rawget(_G, "CTOA_HELPER_EQUIPMENT_OBSERVER")
    local results = {}
    local combatOk, combatResult = Adapter.attach(core, combat)
    results.combat = {ok = combatOk, result = combatResult}
    if type(recovery) == "table" and type(recovery.attach) == "function" then
        local recoveryOk, recoveryResult = recovery.attach(core, Adapter.recoverySnapshot)
        results.recovery = {ok = recoveryOk, result = recoveryResult}
    else
        results.recovery = {ok = false, result = "recovery_observer_required"}
    end
    local observerSpecs = {
        {key = "cavebot", observer = cavebot, provider = Adapter.cavebotSnapshot},
        {key = "loot", observer = loot, provider = Adapter.lootSnapshot},
        {key = "equipment", observer = equipment, provider = Adapter.equipmentSnapshot},
    }
    for _, spec in ipairs(observerSpecs) do
        if type(spec.observer) == "table" and type(spec.observer.attach) == "function" then
            local ok, result = spec.observer.attach(core, spec.provider)
            results[spec.key] = {ok = ok, result = result}
        else
            results[spec.key] = {ok = false, result = spec.key .. "_observer_required"}
        end
    end
    local ready = combatOk == true and results.recovery.ok == true
    for _, key in ipairs({"cavebot", "loot", "equipment"}) do ready = ready and results[key].ok == true end
    return ready, results
end

function Adapter.contract()
    return {
        mode = "read_only_adapter",
        guarded_globals = {"g_game", "g_map", "g_clock"},
        runtime_actions = false,
        executes_plans = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
    }
end

_G.CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER = Adapter
Adapter.attachAll()
return Adapter
