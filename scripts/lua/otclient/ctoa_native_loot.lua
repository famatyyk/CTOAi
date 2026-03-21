-- ctoa_native_loot.lua  [CTOA OTClient Native]
-- Intelligent looting using OTClient container and item API

local LOOT_CONFIG = {
    auto_open_corpses = true,
    loot_range = 2,  -- Maximum distance to loot
    capacity_threshold = 50,  -- Stop looting when capacity < this
    value_threshold = 100  -- Minimum item value to loot
}

local VALUABLE_LOOT = {
    -- Coins
    [3031] = true,  -- gold coin
    [3035] = true,  -- platinum coin  
    [3043] = true,  -- crystal coin
    -- Gems
    [3029] = true,  -- small sapphire
    [3030] = true,  -- small ruby
    [3032] = true,  -- small emerald
    -- Runes
    [3155] = true,  -- sudden death rune
    [3147] = true,  -- heavy magic missile
    -- Equipment
    [3370] = true,  -- knight armor
    [3383] = true,  -- robe of the underworld
}

local function appendLog(msg)
    local f = io.open("ctoa_local.log", "a")
    if not f then
        f = io.open("user_dir/ctoa_local.log", "a")
    end
    if f then
        f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-OTC-LOOT] " .. msg .. "\n")
        f:close()
    end
end

local function isValuableLoot(item)
    if not item then return false end
    local itemId = item:getId()
    return VALUABLE_LOOT[itemId] == true
end

local function hasCapacityForItem(item)
    local player = g_game.getLocalPlayer()
    if not player then return false end
    
    local freeCapacity = player:getFreeCapacity()
    local itemWeight = item:getCount() * (ItemsDatabase:getItemInfo(item:getId()).weight or 0)
    
    return freeCapacity > LOOT_CONFIG.capacity_threshold and freeCapacity >= itemWeight
end

local function lootItem(item, container)
    if not hasCapacityForItem(item) then
        appendLog("Skipping loot - low capacity")
        return false
    end
    
    local backpack = g_game.getLocalPlayer():getInventoryItem(InventorySlotBackpack)
    if not backpack then
        appendLog("No backpack found")
        return false
    end
    
    g_game.move(item, backpack, item:getCount())
    appendLog("Looted: " .. (ItemsDatabase:getItemName(item:getId()) or "Unknown") .. " x" .. item:getCount())
    return true
end

local function onContainerOpen(container, previousContainer)
    if not container or not LOOT_CONFIG.auto_open_corpses then return end
    
    -- Check if this looks like a corpse container
    local containerItem = container:getContainerItem()
    if containerItem and containerItem:isCorpse() then
        appendLog("Corpse opened, scanning for loot...")
        
        local items = container:getItems()
        local lootedCount = 0
        
        for _, item in pairs(items) do
            if isValuableLoot(item) then
                if lootItem(item, container) then
                    lootedCount = lootedCount + 1
                end
            end
        end
        
        if lootedCount > 0 then
            modules.game_console.addText('[CTOA] Looted ' .. lootedCount .. ' items', MessageModes.ModeStatus)
        end
    end
end

local function onItemAppear(item, oldPos)
    if not isValuableLoot(item) then return end
    
    local player = g_game.getLocalPlayer()
    if not player then return end
    
    local itemPos = item:getPosition()
    local playerPos = player:getPosition()
    
    -- Check if item is within loot range
    local distance = math.max(
        math.abs(playerPos.x - itemPos.x),
        math.abs(playerPos.y - itemPos.y)
    )
    
    if distance <= LOOT_CONFIG.loot_range then
        appendLog("Ground item found: " .. (ItemsDatabase:getItemName(item:getId()) or "Unknown"))
        lootItem(item, nil)
    end
end

-- Connect to OTClient events
connect(Container, { onOpen = onContainerOpen })
connect(Map, { onItemAppear = onItemAppear })

appendLog("CTOA Native Loot module loaded")