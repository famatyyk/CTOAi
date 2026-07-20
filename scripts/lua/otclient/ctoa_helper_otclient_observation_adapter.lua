-- ctoa_helper_otclient_observation_adapter.lua [CTOA OTClient Native]
-- Guarded, read-only OTClient snapshot provider for CTOAi Runtime 2 observers.

local Adapter = rawget(_G, "CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER") or {}

local CONDITIONS_OBSERVATION_SCHEMA = "ctoa.conditions-observation.v1"
local EQUIPMENT_SHADOW_OBSERVATION_SCHEMA = "ctoa.equipment-shadow-observation.v1"
local HEAL_FRIEND_SCAN_SCHEMA = "ctoa.heal-friend-scan.v1"

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

function Adapter.isGameOnline(game)
    return call(game or rawget(_G, "g_game"), "isOnline", false) == true
end

function Adapter.localPlayer(game)
    return call(game or rawget(_G, "g_game"), "getLocalPlayer", nil)
end

function Adapter.position(thing)
    return call(thing, "getPosition", nil)
end

function Adapter.creatureId(creature)
    return tonumber(call(creature, "getId", 0)) or 0
end

function Adapter.healthPercent(creature)
    local value = call(creature, "getHealthPercent", 100)
    return type(value) == "number" and value or 100
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
        local ok, result = pcall(map.getSpectators, position, false)
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

local function normalizedName(value)
    return string.lower(tostring(value or "")):gsub("^%s+", ""):gsub("%s+$", ""):gsub("%s+", " ")
end

local function boundedPartyCandidates(map, player)
    local playerPosition = call(player, "getPosition", nil)
    local selfId = tonumber(call(player, "getId", 0)) or 0
    local spectators, complete = {}, playerPosition ~= nil and map ~= nil
    if complete and type(map.getSpectators) == "function" then
        local ok, result = pcall(map.getSpectators, playerPosition, false)
        if ok and type(result) == "table" then spectators = result else complete = false end
    else
        complete = false
    end
    local candidates = {}
    for _, creature in pairs(spectators) do
        if #candidates >= 64 then complete = false break end
        if call(creature, "isPlayer", false) == true then
            local creatureId = tonumber(call(creature, "getId", 0)) or 0
            local creaturePosition = call(creature, "getPosition", nil)
            local hp = tonumber(call(creature, "getHealthPercent", 0)) or 0
            candidates[#candidates + 1] = {
                target_id = math.max(0, math.floor(creatureId)),
                target_name = normalizedName(call(creature, "getName", "")),
                hp_percent = math.max(0, math.min(100, math.floor(hp))),
                distance = math.max(0, math.floor(distanceBetween(playerPosition, creaturePosition))),
                target_is_player = true,
                target_is_self = creatureId > 0 and creatureId == selfId,
                target_party_member = call(creature, "isPartyMember", false) == true,
                target_visible = call(creature, "canShoot", false) == true,
                target_same_floor = playerPosition ~= nil and creaturePosition ~= nil and
                    playerPosition.z == creaturePosition.z,
            }
        end
    end
    table.sort(candidates, function(left, right)
        if left.target_id ~= right.target_id then return left.target_id < right.target_id end
        return left.target_name < right.target_name
    end)
    return candidates, complete, math.max(0, math.floor(selfId))
end

local function cooldownActive(group)
    local cooldowns = modules and modules.game_cooldown or nil
    if not cooldowns or type(cooldowns.isGroupCooldownIconActive) ~= "function" then
        return false
    end
    local ok, active = pcall(cooldowns.isGroupCooldownIconActive, group)
    return ok and active == true
end

local function triStateBooleanCall(owner, methodNames, whenTrue, whenFalse)
    if type(owner) ~= "table" and type(owner) ~= "userdata" then
        return "unknown", "unavailable"
    end
    local observedFalse = false
    for _, methodName in ipairs(methodNames or {}) do
        local method = owner[methodName]
        if type(method) == "function" then
            local ok, value = pcall(method, owner)
            if ok and type(value) == "boolean" then
                if value then
                    return whenTrue, "player_method"
                end
                observedFalse = true
            end
        end
    end
    if observedFalse then
        return whenFalse, "player_method"
    end
    return "unknown", "unavailable"
end

local function playerAliveState(player)
    if type(player) ~= "table" and type(player) ~= "userdata" then
        return "unknown"
    end
    local dead, _ = triStateBooleanCall(player, {"isDead"}, "dead", "alive")
    if dead ~= "unknown" then
        return dead
    end
    for _, methodName in ipairs({"getHealthPercent", "getHealth"}) do
        local method = player[methodName]
        if type(method) == "function" then
            local ok, value = pcall(method, player)
            if ok and type(value) == "number" and value == value and
                value > -math.huge and value < math.huge then
                return value > 0 and "alive" or "dead"
            end
        end
    end
    return "unknown"
end

local function hasBitFlag(value, flag)
    if type(value) ~= "number" or type(flag) ~= "number" or flag <= 0 then return false end
    if bit32 and bit32.band then return bit32.band(value, flag) == flag end
    if bit and bit.band then return bit.band(value, flag) == flag end
    return value % (flag * 2) >= flag
end

local function playerStates(player)
    if (type(player) ~= "table" and type(player) ~= "userdata") or
        type(player.getStates) ~= "function" then return nil end
    local ok, value = pcall(player.getStates, player)
    if ok and type(value) == "number" and value == value and value >= 0 and
        value < math.huge and value % 1 == 0 then return value end
    return nil
end

local function stateFlags(globals, fallbacks)
    local result, seen = {}, {}
    for _, name in ipairs(globals or {}) do
        local value = rawget(_G, name)
        if type(value) == "number" and value > 0 and value % 1 == 0 and not seen[value] then
            result[#result + 1], seen[value] = value, true
        end
    end
    for _, value in ipairs(fallbacks or {}) do
        if type(value) == "number" and value > 0 and not seen[value] then
            result[#result + 1], seen[value] = value, true
        end
    end
    return result
end

local function speedSlowedState(player)
    local speed = call(player, "getSpeed", nil)
    local baseSpeed = call(player, "getBaseSpeed", nil)
    if type(speed) ~= "number" or type(baseSpeed) ~= "number" or
        speed ~= speed or baseSpeed ~= baseSpeed or baseSpeed <= 0 or
        speed <= -math.huge or speed >= math.huge or
        baseSpeed <= -math.huge or baseSpeed >= math.huge then
        return nil
    end
    return speed < baseSpeed
end

local function protectionZoneState(player)
    local state, source = triStateBooleanCall(player, {
        "isInPz", "isInProtectionZone", "isInSafeZone", "isProtected"
    }, "inside", "outside")
    if state ~= "unknown" then return state, source end
    local states = playerStates(player)
    if states == nil then return "unknown", "unavailable" end
    for _, flag in ipairs(stateFlags({
        "CreatureStateProtectionZone", "CreatureStatePz", "CreatureStateSafeZone"
    }, {16384})) do
        if hasBitFlag(states, flag) then return "inside", "player_states" end
    end
    return "outside", "player_states"
end

local function paralyzeState(player)
    if type(player) ~= "table" and type(player) ~= "userdata" then return "unknown" end
    local candidates = stateFlags({"CreatureStateParalyze", "CreatureStateSlowed"}, {32})
    local observed = false
    if type(player.hasState) == "function" then
        for _, candidate in ipairs(candidates) do
            local ok, active = pcall(player.hasState, player, candidate)
            if ok and type(active) == "boolean" then
                observed = true
                if active then return "present" end
            end
        end
    end
    local states = playerStates(player)
    if states ~= nil then
        for _, candidate in ipairs(candidates) do
            if hasBitFlag(states, candidate) then return "present" end
        end
    end
    local slowed = speedSlowedState(player)
    if slowed ~= nil then return slowed and "present" or "absent" end
    if states ~= nil then return "absent" end
    return observed and "absent" or "unknown"
end

local function spellCooldownState(context)
    local sourceModules = type(context) == "table" and context.modules or nil
    local cooldowns = sourceModules and sourceModules.game_cooldown or
        (modules and modules.game_cooldown or nil)
    if not cooldowns or type(cooldowns.isGroupCooldownIconActive) ~= "function" then
        return "unknown", "unavailable"
    end
    local ok, active = pcall(cooldowns.isGroupCooldownIconActive, 2)
    if not ok or type(active) ~= "boolean" then
        return "unknown", "unavailable"
    end
    return active and "active" or "ready", "game_cooldown_group"
end

function Adapter.conditionsSnapshot(context)
    local ctx = context or {}
    local game = ctx.game or rawget(_G, "g_game")
    local online, _ = triStateBooleanCall(game, {"isOnline"}, "online", "offline")
    local player = online == "online" and call(game, "getLocalPlayer", nil) or nil
    local protectionZone, protectionZoneSource = protectionZoneState(player)
    local cooldown, cooldownSource = "unknown", "unavailable"
    if online == "online" then
        cooldown, cooldownSource = spellCooldownState(ctx)
    end
    local observedAt = tonumber(ctx.observed_at_unix_ms) or 0
    observedAt = math.max(0, math.floor(observedAt))
    return {
        schema_version = CONDITIONS_OBSERVATION_SCHEMA,
        observed_at_unix_ms = observedAt,
        observation_id = "conditions-" .. tostring(observedAt),
        online = online,
        alive = playerAliveState(player),
        protection_zone = protectionZone,
        protection_zone_source = protectionZoneSource,
        condition_id = "paralyze",
        condition_state = paralyzeState(player),
        cooldown = cooldown,
        cooldown_source = cooldownSource,
        producer_source = "otclient_guarded_adapter",
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
        execute_once_allowed = false,
        promotion_allowed = false,
    }
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

local function inventorySlot(player, ...)
    if not player or type(player.getInventoryItem) ~= "function" then return {present = false} end
    for index = 1, select("#", ...) do
        local slotId = select(index, ...)
        if slotId ~= nil then
            local item = call(player, "getInventoryItem", nil, slotId)
            if item then
                return {present = true, item_id = call(item, "getId", 0), count = call(item, "getCount", 1)}
            end
        end
    end
    return {present = false}
end

local function boundedContainerItems(game)
    local containers = call(game, "getContainers", {})
    local result, containerCount, itemCount = {}, 0, 0
    local complete = type(containers) == "table"
    if type(containers) ~= "table" then return result, false end
    for key, container in pairs(containers) do
        containerCount = containerCount + 1
        if containerCount > 32 then complete = false break end
        local containerId = tonumber(call(container, "getId", nil)) or tonumber(key)
        local items = call(container, "getItems", {})
        if not containerId or containerId < 0 or containerId % 1 ~= 0 or type(items) ~= "table" then
            complete = false
        else
            local slotIndex = 0
            for _, item in pairs(items) do
                slotIndex = slotIndex + 1
                itemCount = itemCount + 1
                if itemCount > 256 then complete = false break end
                local itemId = tonumber(call(item, "getId", 0)) or 0
                local count = tonumber(call(item, "getCount", 1)) or 1
                result[#result + 1] = {
                    container_id = math.floor(containerId), slot_index = slotIndex,
                    item_id = math.max(0, math.floor(itemId)), count = math.max(0, math.floor(count)),
                }
            end
            if itemCount > 256 then break end
        end
    end
    table.sort(result, function(left, right)
        if left.container_id ~= right.container_id then return left.container_id < right.container_id end
        if left.slot_index ~= right.slot_index then return left.slot_index < right.slot_index end
        return left.item_id < right.item_id
    end)
    return result, complete
end

function Adapter.equipmentShadowObservation(context)
    local ctx = context or {}
    local game = ctx.game or rawget(_G, "g_game")
    local online, _ = triStateBooleanCall(game, {"isOnline"}, "online", "offline")
    local player = online == "online" and call(game, "getLocalPlayer", nil) or nil
    local protectionZone, protectionZoneSource = protectionZoneState(player)
    local cooldown, cooldownSource = "unknown", "unavailable"
    if online == "online" then cooldown, cooldownSource = spellCooldownState(ctx) end
    local observedAt = math.max(0, math.floor(tonumber(ctx.observed_at_unix_ms) or 0))
    local candidates, containersComplete = boundedContainerItems(game)
    local ring = inventorySlot(player, _G.InventorySlotFinger, _G.InventorySlotRing)
    return {
        schema_version = EQUIPMENT_SHADOW_OBSERVATION_SCHEMA,
        observed_at_unix_ms = observedAt,
        observation_id = "equipment-" .. tostring(observedAt),
        online = online,
        alive = playerAliveState(player),
        protection_zone = protectionZone,
        protection_zone_source = protectionZoneSource,
        inventory_api_available = hasMethod(player, "getInventoryItem"),
        containers_complete = containersComplete,
        ring = {present = ring.present == true, item_id = tonumber(ring.item_id) or 0,
            count = tonumber(ring.count) or 0},
        candidates = candidates,
        cooldown = cooldown,
        cooldown_source = cooldownSource,
        producer_source = "otclient_guarded_adapter",
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
        execute_once_allowed = false,
        promotion_allowed = false,
    }
end

function Adapter.healFriendScan(context)
    local ctx = context or {}
    local game = ctx.game or rawget(_G, "g_game")
    local map = ctx.map or rawget(_G, "g_map")
    local online, _ = triStateBooleanCall(game, {"isOnline"}, "online", "offline")
    local player = online == "online" and call(game, "getLocalPlayer", nil) or nil
    local protectionZone, protectionZoneSource = protectionZoneState(player)
    local cooldown, cooldownSource = "unknown", "unavailable"
    if online == "online" then cooldown, cooldownSource = spellCooldownState(ctx) end
    local observedAt = math.max(0, math.floor(tonumber(ctx.observed_at_unix_ms) or 0))
    local candidates, scanComplete, selfId = boundedPartyCandidates(map, player)
    return {
        schema_version = HEAL_FRIEND_SCAN_SCHEMA,
        observed_at_unix_ms = observedAt,
        party_observed_at_unix_ms = observedAt,
        observation_id = "heal-friend-" .. tostring(observedAt),
        online = online,
        alive = playerAliveState(player),
        protection_zone = protectionZone,
        protection_zone_source = protectionZoneSource,
        self_id = selfId,
        scan_complete = scanComplete,
        candidates = candidates,
        cooldown = cooldown,
        cooldown_source = cooldownSource,
        producer_source = "otclient_guarded_adapter",
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
        execute_once_allowed = false,
        promotion_allowed = false,
        casts = false,
        talks = false,
    }
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
            ring = inventorySlot(player, _G.InventorySlotFinger, _G.InventorySlotRing),
            amulet = inventorySlot(player, _G.InventorySlotNecklace, _G.InventorySlotAmulet),
            left = inventorySlot(player, _G.InventorySlotLeft, _G.InventorySlotLeftHand),
            right = inventorySlot(player, _G.InventorySlotRight, _G.InventorySlotRightHand),
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
        conditions_observation_schema = CONDITIONS_OBSERVATION_SCHEMA,
        owns_conditions_observation = true,
        equipment_shadow_observation_schema = EQUIPMENT_SHADOW_OBSERVATION_SCHEMA,
        owns_equipment_shadow_observation = true,
        heal_friend_scan_schema = HEAL_FRIEND_SCAN_SCHEMA,
        owns_heal_friend_scan = true,
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
