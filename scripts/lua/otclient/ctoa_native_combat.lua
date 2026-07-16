-- ctoa_native_combat.lua  [CTOA OTClient Native]
-- Auto-targeting layer fed by helper config; priorities inspired by ZeroBot/Validus target logic.
-- LOCAL SOURCE ONLY: legacy standalone reference; not loaded or shipped by CTOAi Helper.

local DEFAULT_COMBAT_CONFIG = {
    auto_attack = false,
    auto_follow = false,
    pause_in_pz = true,
    hold_target = false,
    attack_range = 7,
    target_timeout_ms = 15000,
    retarget_delay_ms = 200,
    log_retarget_ms = 3000,
    block_log_ms = 3000,
    probe_log_ms = 5000,
    clear_target_in_pz = true,
    prefer_low_hp = false,
    ignored_names = {
        "elara goldwarden",
        "goldwarden",
        "aldren",
        "postman",
        "taskmaster",
        "liora",
        "npc"
    },
    priority_names = {
        "demon",
        "dragon lord",
        "dragon",
        "cyclops",
        "dwarf"
    }
}

local Combat = {
    think_event = nil,
    current_target_id = 0,
    target_start_ms = 0,
    last_retarget_ms = 0,
    last_logged_target_id = 0,
    last_logged_target_name = "",
    last_log_ms = 0,
    last_block_log_ms = 0,
    last_block_reason = "",
    probe_log = {}
}

local function appendLog(msg)
    local f = io.open("ctoa_local.log", "a")
    if not f then
        f = io.open("user_dir/ctoa_local.log", "a")
    end
    if f then
        f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-OTC-COMBAT] " .. msg .. "\n")
        f:close()
    end
end

local function helperConfig()
    local config = {}
    for key, value in pairs(DEFAULT_COMBAT_CONFIG) do
        config[key] = value
    end
    local helper = _G.CTOA_Helper
    if helper and helper.config and helper.config.tools then
        for key, value in pairs(helper.config.tools) do
            config[key] = value
        end
    end
    return config
end

local function nowMs()
    if g_clock and g_clock.millis then
        local ok, value = pcall(function()
            return g_clock.millis()
        end)
        if ok and type(value) == "number" then
            return value
        end
    end
    return math.floor(os.clock() * 1000)
end

local function localPlayer()
    if g_game and g_game.getLocalPlayer then
        local ok, player = pcall(function()
            return g_game.getLocalPlayer()
        end)
        if ok then
            return player
        end
    end
    return nil
end

local function getPosition(thing)
    if thing and thing.getPosition then
        local ok, pos = pcall(function()
            return thing:getPosition()
        end)
        if ok then
            return pos
        end
    end
    return nil
end

local function pcallBool(obj, methodName)
    if obj and obj[methodName] then
        local ok, result = pcall(function()
            return obj[methodName](obj)
        end)
        if ok then
            return result == true
        end
    end
    return false
end

local function pcallOptionalBool(obj, methodName)
    if obj and obj[methodName] then
        local ok, result = pcall(function()
            return obj[methodName](obj)
        end)
        if ok then
            return result == true
        end
        return false
    end
    return nil
end

local function pcallWithArg(obj, methodName, arg)
    if obj and obj[methodName] then
        local ok, result = pcall(function()
            return obj[methodName](obj, arg)
        end)
        if ok then
            return result == true
        end
    end
    return false
end

local function pcallNumber(obj, methodName)
    if obj and obj[methodName] then
        local ok, result = pcall(function()
            return obj[methodName](obj)
        end)
        if ok and type(result) == "number" then
            return result
        end
    end
    return nil
end

local function hasAnyState(obj, methodName, states)
    if not obj or not obj[methodName] then
        return false
    end
    for _, state in ipairs(states) do
        if state ~= nil and pcallWithArg(obj, methodName, state) then
            return true
        end
    end
    return false
end

local function hasBitFlag(value, flag)
    if type(value) ~= "number" or type(flag) ~= "number" or flag <= 0 then
        return false
    end
    if bit32 and bit32.band then
        return bit32.band(value, flag) == flag
    end
    if bit and bit.band then
        return bit.band(value, flag) == flag
    end
    return value % (flag * 2) >= flag
end

local function collectNumericFlags(values, fallbacks)
    local flags = {}
    local seen = {}
    for _, value in ipairs(values or {}) do
        if type(value) == "number" and value > 0 and not seen[value] then
            flags[#flags + 1] = value
            seen[value] = true
        end
    end
    for _, value in ipairs(fallbacks or {}) do
        if type(value) == "number" and value > 0 and not seen[value] then
            flags[#flags + 1] = value
            seen[value] = true
        end
    end
    return flags
end

local function isInProtectionZone(player)
    if not player then
        return false
    end

    local methods = {
        "isInPz",
        "isInProtectionZone",
        "isInSafeZone",
        "isProtected",
        "isPzLocked"
    }
    for _, methodName in ipairs(methods) do
        if pcallBool(player, methodName) then
            return true
        end
    end
    if hasAnyState(player, "hasState", {
        _G.CreatureStateProtectionZone,
        _G.CreatureStatePz,
        _G.CreatureStateSafeZone,
        "ProtectionZone",
        "Pz",
        "SafeZone"
    }) then
        return true
    end
    local stateFlags = collectNumericFlags({
        _G.CreatureStateProtectionZone,
        _G.CreatureStatePz,
        _G.CreatureStateSafeZone
    }, {16384})
    local states = pcallNumber(player, "getStates")
    for _, flag in ipairs(stateFlags) do
        if hasBitFlag(states, flag) then
            return true
        end
    end

    local pos = getPosition(player)
    if pos and g_map and g_map.getTile then
        local ok, tile = pcall(function()
            return g_map.getTile(pos)
        end)
        if ok and tile then
            for _, methodName in ipairs({"isPz", "isProtectionZone", "isSafeZone"}) do
                if pcallBool(tile, methodName) then
                    return true
                end
            end
            local tileFlags = pcallNumber(tile, "getFlags")
            for _, flag in ipairs(collectNumericFlags({
                _G.TILESTATE_PROTECTIONZONE,
                _G.TileStateProtectionZone,
                _G.TileStatePz
            }, {1})) do
                if hasBitFlag(tileFlags, flag) then
                    return true
                end
            end
            if tile.hasFlag then
                local flags = {
                    _G.TILESTATE_PROTECTIONZONE,
                    _G.TileStateProtectionZone,
                    _G.TileStatePz,
                    "TILESTATE_PROTECTIONZONE",
                    "TileStateProtectionZone",
                    "ProtectionZone",
                    "Pz"
                }
                if hasAnyState(tile, "hasFlag", flags) then
                    return true
                end
            end
        end
    end

    return false
end

local function safeGameCall(methodName, arg)
    if g_game and g_game[methodName] then
        pcall(function()
            if arg == nil then
                g_game[methodName]()
            else
                g_game[methodName](arg)
            end
        end)
    end
end

local function clearCombatState(now, reason, config)
    Combat.current_target_id = 0
    Combat.target_start_ms = 0
    if config.clear_target_in_pz ~= false then
        safeGameCall("cancelAttack")
        safeGameCall("stopAttack")
        safeGameCall("attack", nil)
        safeGameCall("follow", nil)
    end
    if reason and now and (Combat.last_block_reason ~= reason or now - Combat.last_block_log_ms >= (config.block_log_ms or DEFAULT_COMBAT_CONFIG.block_log_ms)) then
        Combat.last_block_reason = reason
        Combat.last_block_log_ms = now
        appendLog("Combat paused: " .. reason)
    end
end

local function chebyshevDistance(a, b)
    if not a or not b or a.z ~= b.z then
        return nil
    end
    return math.max(math.abs((a.x or 0) - (b.x or 0)), math.abs((a.y or 0) - (b.y or 0)))
end

local function normalizedName(creature)
    if creature and creature.getName then
        local ok, name = pcall(function()
            return creature:getName()
        end)
        if ok and name then
            return string.lower(name)
        end
    end
    return ""
end

local function appendIgnoredNames(target, names)
    for _, ignored in ipairs(names or {}) do
        if ignored and ignored ~= "" then
            target[#target + 1] = ignored
        end
    end
end

local function mergedIgnoredNames(config)
    local names = {}
    appendIgnoredNames(names, DEFAULT_COMBAT_CONFIG.ignored_names)
    appendIgnoredNames(names, config and config.ignored_names)
    return names
end

local function isIgnoredName(creature, config)
    local name = normalizedName(creature)
    if name == "" then
        return false
    end
    for _, ignored in ipairs(mergedIgnoredNames(config)) do
        local needle = string.lower(ignored or "")
        if needle ~= "" and string.find(name, needle, 1, true) then
            return true
        end
    end
    return false
end

local function isMonsterCreature(creature, player)
    if not creature or creature == player then
        return false
    end
    if creature.isNpc then
        local ok, result = pcall(function()
            return creature:isNpc()
        end)
        if ok and result then
            return false
        end
    end
    if creature.isPlayer then
        local ok, result = pcall(function()
            return creature:isPlayer()
        end)
        if ok and result then
            return false
        end
    end
    for _, methodName in ipairs({"isAttackable", "canBeAttacked", "isTargetable"}) do
        local result = pcallOptionalBool(creature, methodName)
        if result == false then
            return false
        end
    end
    if creature.isMonster then
        local ok, result = pcall(function()
            return creature:isMonster()
        end)
        if ok then
            return result == true
        end
    end
    -- Targeting must be opt-in: unknown creature types are treated as non-monsters.
    return false
end

local function isValidTarget(creature, player, maxRange)
    if not creature or creature == player then
        return false
    end
    if isIgnoredName(creature, helperConfig()) then
        return false
    end
    if creature.getHealthPercent and creature:getHealthPercent() <= 0 then
        return false
    end
    if not isMonsterCreature(creature, player) then
        return false
    end

    local playerPos = getPosition(player)
    local targetPos = getPosition(creature)
    local distance = chebyshevDistance(playerPos, targetPos)
    if not distance or distance > maxRange then
        return false
    end
    return true
end

local function getPriorityNameRank(creature, config)
    local priorityNames = config.priority_names or DEFAULT_COMBAT_CONFIG.priority_names
    local name = normalizedName(creature)
    for index, needle in ipairs(priorityNames) do
        if string.find(name, string.lower(needle), 1, true) then
            return index
        end
    end
    return 999
end

local function candidateScore(creature, player, config)
    local playerPos = getPosition(player)
    local creaturePos = getPosition(creature)
    local distance = chebyshevDistance(playerPos, creaturePos) or 99
    local hp = creature.getHealthPercent and creature:getHealthPercent() or 100
    local nameRank = getPriorityNameRank(creature, config)
    if config.prefer_low_hp then
        return nameRank * 10000 + hp * 100 + distance
    end
    return nameRank * 10000 + distance * 100 + hp
end

local function getSpectators(playerPos, range)
    if g_map and g_map.getSpectatorsInRange then
        local ok, spectators = pcall(function()
            return g_map.getSpectatorsInRange(playerPos, false, range, range)
        end)
        if ok and spectators then
            return spectators
        end
    end
    if g_map and g_map.getCreaturesInRange then
        local ok, spectators = pcall(function()
            return g_map.getCreaturesInRange(playerPos, range)
        end)
        if ok and spectators then
            return spectators
        end
    end
    return {}
end

local function findBestTarget(config)
    local player = localPlayer()
    if not player then
        return nil
    end
    local playerPos = getPosition(player)
    if not playerPos then
        return nil
    end

    local bestTarget = nil
    local bestScore = nil
    for _, creature in ipairs(getSpectators(playerPos, config.attack_range or DEFAULT_COMBAT_CONFIG.attack_range)) do
        if isValidTarget(creature, player, config.attack_range or DEFAULT_COMBAT_CONFIG.attack_range) then
            local score = candidateScore(creature, player, config)
            if not bestScore or score < bestScore then
                bestTarget = creature
                bestScore = score
            end
        end
    end
    return bestTarget
end

local function currentAttackTarget()
    if g_game and g_game.getAttackingCreature then
        local ok, creature = pcall(function()
            return g_game.getAttackingCreature()
        end)
        if ok then
            return creature
        end
    end
    return nil
end

local function currentTargetId(creature)
    if creature and creature.getId then
        local ok, id = pcall(function()
            return creature:getId()
        end)
        if ok then
            return id or 0
        end
    end
    return 0
end

local function probeValue(creature, methodName)
    if not creature or not creature[methodName] then
        return "n/a"
    end
    local ok, result = pcall(function()
        return creature[methodName](creature)
    end)
    if not ok then
        return "err"
    end
    return tostring(result)
end

local function logCreatureProbe(creature, reason, config, now)
    if not creature or not now then
        return
    end
    local id = currentTargetId(creature)
    local name = creature.getName and creature:getName() or "?"
    local key = tostring(id) .. ":" .. tostring(reason)
    local last = Combat.probe_log[key] or 0
    if now - last < (config.probe_log_ms or DEFAULT_COMBAT_CONFIG.probe_log_ms) then
        return
    end
    Combat.probe_log[key] = now
    appendLog(
        "Target probe: "
            .. tostring(name)
            .. " id="
            .. tostring(id)
            .. " reason="
            .. tostring(reason)
            .. " isNpc="
            .. probeValue(creature, "isNpc")
            .. " isMonster="
            .. probeValue(creature, "isMonster")
            .. " isPlayer="
            .. probeValue(creature, "isPlayer")
            .. " isAttackable="
            .. probeValue(creature, "isAttackable")
            .. " canBeAttacked="
            .. probeValue(creature, "canBeAttacked")
            .. " isTargetable="
            .. probeValue(creature, "isTargetable")
    )
end

local function retargetNow(now, config)
    if now - Combat.last_retarget_ms < (config.retarget_delay_ms or DEFAULT_COMBAT_CONFIG.retarget_delay_ms) then
        return
    end

    local target = findBestTarget(config)
    if not target then
        clearCombatState(now, "no valid monster target", config)
        return
    end
    logCreatureProbe(target, "selected", config, now)

    if g_game and g_game.attack then
        g_game.attack(target)
    end
    if config.auto_follow and g_game and g_game.follow then
        g_game.follow(target)
    end

    Combat.current_target_id = currentTargetId(target)
    Combat.target_start_ms = now
    Combat.last_retarget_ms = now
    local targetName = target.getName and target:getName() or "?"
    if now - Combat.last_log_ms >= (config.log_retarget_ms or DEFAULT_COMBAT_CONFIG.log_retarget_ms) then
        Combat.last_logged_target_id = Combat.current_target_id
        Combat.last_logged_target_name = targetName
        Combat.last_log_ms = now
        appendLog("Auto target: " .. targetName)
    end
end

local function onThink()
    if not g_game or not g_game.isOnline or not g_game.isOnline() then
        return
    end

    local config = helperConfig()
    local now = nowMs()
    if not config.auto_attack then
        clearCombatState(now, "targeting disabled", config)
        return
    end

    local player = localPlayer()
    if not player then
        return
    end
    if config.pause_in_pz ~= false and isInProtectionZone(player) then
        clearCombatState(now, "protection zone", config)
        return
    end

    local target = currentAttackTarget()
    local maxRange = config.attack_range or DEFAULT_COMBAT_CONFIG.attack_range

    if target and isValidTarget(target, player, maxRange) then
        local targetId = currentTargetId(target)
        if Combat.current_target_id ~= targetId then
            Combat.current_target_id = targetId
            Combat.target_start_ms = now
        end
        if config.hold_target then
            return
        end
        if now - Combat.target_start_ms < (config.target_timeout_ms or DEFAULT_COMBAT_CONFIG.target_timeout_ms) then
            return
        end
    elseif target then
        logCreatureProbe(target, "invalid current target", config, now)
        clearCombatState(now, "invalid current target", config)
    end

    retargetNow(now, config)
end

local function onCreatureDeath(creature, corpse)
    if currentTargetId(creature) == Combat.current_target_id then
        Combat.current_target_id = 0
        Combat.target_start_ms = 0
    end
end

local function init()
    if Combat.think_event then
        return
    end
    Combat.think_event = cycleEvent(onThink, 100)
    connect(Creature, { onDeath = onCreatureDeath })
    appendLog("CTOA Native Combat module loaded")
end

init()
