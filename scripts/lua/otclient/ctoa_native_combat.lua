-- ctoa_native_combat.lua  [CTOA OTClient Native]
-- Advanced combat system using full creature API

local COMBAT_CONFIG = {
    attack_range = 8,
    prefer_low_hp = true,
    target_timeout = 30000,  -- 30 seconds
    auto_follow = true
}

local PRIORITY_TARGETS = {
    "demon",
    "dragon lord", 
    "dragon",
    "cyclops",
    "dwarf"
}

local currentTarget = nil
local targetStartTime = 0

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

local function getTargetPriority(creature)
    local name = string.lower(creature:getName())
    for i, target in ipairs(PRIORITY_TARGETS) do
        if string.find(name, target) then
            return i  -- Lower number = higher priority
        end
    end
    return 999  -- Low priority
end

local function isValidTarget(creature)
    if not creature or creature == g_game.getLocalPlayer() then
        return false
    end
    return creature:getHealthPercent() > 0
end

local function findBestTarget()
    local localPlayer = g_game.getLocalPlayer()
    if not localPlayer then return nil end
    
    local pos = localPlayer:getPosition()
    local creatures = g_map.getCreaturesInRange(pos, COMBAT_CONFIG.attack_range)
    
    local bestTarget = nil
    local bestPriority = 999
    local bestDistance = 999
    
    for _, creature in pairs(creatures) do
        if isValidTarget(creature) then
            local priority = getTargetPriority(creature)
            local creaturePos = creature:getPosition()
            local distance = math.abs(pos.x - creaturePos.x) + math.abs(pos.y - creaturePos.y)
            
            -- Prefer higher priority targets, then closer targets
            if priority < bestPriority or (priority == bestPriority and distance < bestDistance) then
                bestTarget = creature
                bestPriority = priority 
                bestDistance = distance
            end
        end
    end
    
    return bestTarget
end

local function onThink()
    local attackTarget = g_game.getAttackingCreature()
    local now = g_clock.millis()
    
    -- Check if current target is still valid
    if attackTarget and isValidTarget(attackTarget) then
        if attackTarget ~= currentTarget then
            currentTarget = attackTarget
            targetStartTime = now
            appendLog("Attacking: " .. attackTarget:getName())
        end
        
        -- Target timeout check
        if now - targetStartTime > COMBAT_CONFIG.target_timeout then
            appendLog("Target timeout, finding new target")
            currentTarget = nil
        end
    else
        -- Find new target
        local newTarget = findBestTarget()
        if newTarget and newTarget ~= currentTarget then
            g_game.attack(newTarget)
            currentTarget = newTarget
            targetStartTime = now
            appendLog("New target: " .. newTarget:getName() .. " (priority: " .. getTargetPriority(newTarget) .. ")")
            
            if COMBAT_CONFIG.auto_follow then
                g_game.follow(newTarget)
            end
        end
    end
end

local function onCreatureDeath(creature, corpse)
    if creature == currentTarget then
        currentTarget = nil
        appendLog("Target died: " .. creature:getName())
    end
end

-- Connect to OTClient events  
local thinkEvent = cycleEvent(onThink, 500)  -- Check every 500ms
connect(Creature, { onDeath = onCreatureDeath })

appendLog("CTOA Native Combat module loaded")