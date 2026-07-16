-- ctoa_native_loot.lua  [CTOA OTClient Native]
-- LOCAL SOURCE ONLY: legacy standalone reference; not loaded or shipped by CTOAi Helper.
-- Passive looting scanner with profile-fed rules and guarded OTClient calls.

local LOOT_CONFIG = {
    enabled = false,
    auto_open_corpses = false,
    auto_loot_containers = false,
    loot_range = 2,
    capacity_threshold = 50,
    value_threshold = 100,
    scan_interval_ms = 1000,
    max_items_per_scan = 8,
    move_cooldown_ms = 250,
}

local VALUABLE_LOOT = {
    [3031] = {tier = 1, name = "gold coin"},
    [3035] = {tier = 2, name = "platinum coin"},
    [3043] = {tier = 3, name = "crystal coin"},
    [3029] = {tier = 2, name = "small sapphire"},
    [3030] = {tier = 2, name = "small ruby"},
    [3032] = {tier = 2, name = "small emerald"},
    [3155] = {tier = 3, name = "sudden death rune"},
    [3147] = {tier = 2, name = "heavy magic missile"},
    [3370] = {tier = 3, name = "knight armor"},
    [3383] = {tier = 4, name = "robe of the underworld"},
}

local Loot = {
    think_event = nil,
    last_scan_ms = 0,
    last_move_ms = 0,
    last_status_ms = 0,
}

local function appendLog(msg)
    local paths = {"ctoa_local.log", "user_dir/ctoa_local.log"}
    if g_resources and g_resources.getUserDir then
        local ok, userDir = pcall(function()
            return g_resources.getUserDir()
        end)
        if ok and userDir then
            paths[#paths + 1] = userDir .. "/ctoa_local.log"
        end
    end
    for _, path in ipairs(paths) do
        local f = io.open(path, "a")
        if f then
            f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-OTC-LOOT] " .. msg .. "\n")
            f:close()
            return
        end
    end
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

local function helperLootConfig()
    local config = {}
    for key, value in pairs(LOOT_CONFIG) do
        config[key] = value
    end
    local helper = rawget(_G, "CTOA_Helper")
    if helper and helper.config and helper.config.tools then
        local tools = helper.config.tools
        local flags = tools.feature_flags or {}
        config.enabled = helper.config.enabled == true and flags.experimental_loot == true
        config.loot_range = tools.loot_range or config.loot_range
        config.auto_open_corpses = tools.auto_open_corpses == true
        config.auto_loot_containers = tools.auto_loot_containers == true
        config.capacity_threshold = tools.loot_capacity_threshold or config.capacity_threshold
        config.max_items_per_scan = tools.loot_max_items_per_scan or config.max_items_per_scan
    end
    return config
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

local function itemId(item)
    if item and item.getId then
        local ok, id = pcall(function()
            return item:getId()
        end)
        if ok then
            return id
        end
    end
    return nil
end

local function itemCount(item)
    if item and item.getCount then
        local ok, count = pcall(function()
            return item:getCount()
        end)
        if ok and type(count) == "number" then
            return math.max(1, count)
        end
    end
    return 1
end

local function itemName(item)
    local id = itemId(item)
    if id and VALUABLE_LOOT[id] and VALUABLE_LOOT[id].name then
        return VALUABLE_LOOT[id].name
    end
    if ItemsDatabase and id and ItemsDatabase.getItemName then
        local ok, name = pcall(function()
            return ItemsDatabase:getItemName(id)
        end)
        if ok and name then
            return name
        end
    end
    return "item " .. tostring(id or "?")
end

local function lootRule(item)
    local id = itemId(item)
    return id and VALUABLE_LOOT[id] or nil
end

local function isValuableLoot(item)
    return lootRule(item) ~= nil
end

local function freeCapacity(player)
    if player and player.getFreeCapacity then
        local ok, capacity = pcall(function()
            return player:getFreeCapacity()
        end)
        if ok and type(capacity) == "number" then
            return capacity
        end
    end
    return nil
end

local function hasCapacityForItem(item, config)
    local capacity = freeCapacity(localPlayer())
    if not capacity then
        return true
    end
    return capacity > (config.capacity_threshold or LOOT_CONFIG.capacity_threshold)
end

local function isCorpseContainer(container)
    if not container or not container.getContainerItem then
        return false
    end
    local ok, containerItem = pcall(function()
        return container:getContainerItem()
    end)
    if not ok or not containerItem then
        return false
    end
    if containerItem.isCorpse then
        local corpseOk, corpse = pcall(function()
            return containerItem:isCorpse()
        end)
        return corpseOk and corpse == true
    end
    return false
end

local function getContainerItems(container)
    if not container or not container.getItems then
        return {}
    end
    local ok, items = pcall(function()
        return container:getItems()
    end)
    if ok and type(items) == "table" then
        return items
    end
    return {}
end

local function getOpenContainers()
    if g_game and g_game.getContainers then
        local ok, containers = pcall(function()
            return g_game.getContainers()
        end)
        if ok and type(containers) == "table" then
            return containers
        end
    end
    return {}
end

local function destinationForLoot()
    local player = localPlayer()
    if player and player.getInventoryItem and InventorySlotBackpack then
        local ok, backpack = pcall(function()
            return player:getInventoryItem(InventorySlotBackpack)
        end)
        if ok and backpack then
            if backpack.getPosition then
                local posOk, pos = pcall(function()
                    return backpack:getPosition()
                end)
                if posOk and pos then
                    return pos
                end
            end
            return backpack
        end
    end
    return nil
end

local function lootScore(item)
    local rule = lootRule(item)
    if not rule then
        return 0
    end
    return (rule.tier or 1) * 1000 + itemCount(item)
end

local function moveItem(item, config)
    if not item or not isValuableLoot(item) then
        return false
    end
    if not hasCapacityForItem(item, config) then
        appendLog("Skip " .. itemName(item) .. ": low capacity")
        return false
    end
    local now = nowMs()
    if now - Loot.last_move_ms < (config.move_cooldown_ms or LOOT_CONFIG.move_cooldown_ms) then
        return false
    end
    local destination = destinationForLoot()
    if not destination then
        appendLog("Skip " .. itemName(item) .. ": no backpack destination")
        return false
    end
    if not g_game or not g_game.move then
        appendLog("Skip " .. itemName(item) .. ": g_game.move unavailable")
        return false
    end
    local ok, err = pcall(function()
        g_game.move(item, destination, itemCount(item))
    end)
    if not ok then
        appendLog("Loot move failed for " .. itemName(item) .. ": " .. tostring(err))
        return false
    end
    Loot.last_move_ms = now
    appendLog("Looted " .. itemName(item) .. " x" .. tostring(itemCount(item)))
    return true
end

local function sortedValuableItems(container)
    local items = {}
    for _, item in pairs(getContainerItems(container)) do
        if isValuableLoot(item) then
            items[#items + 1] = item
        end
    end
    table.sort(items, function(left, right)
        return lootScore(left) > lootScore(right)
    end)
    return items
end

local function scanContainer(container, config)
    if not config.enabled then
        return 0
    end
    if not config.auto_loot_containers and not isCorpseContainer(container) then
        return 0
    end
    local moved = 0
    for _, item in ipairs(sortedValuableItems(container)) do
        if moved >= (config.max_items_per_scan or LOOT_CONFIG.max_items_per_scan) then
            break
        end
        if moveItem(item, config) then
            moved = moved + 1
        end
    end
    return moved
end

local function onContainerOpen(container, previousContainer)
    local config = helperLootConfig()
    if not config.enabled or not config.auto_open_corpses then
        return
    end
    local moved = scanContainer(container, config)
    if moved > 0 then
        appendLog("Container scan moved " .. tostring(moved) .. " items")
    end
end

local function distance(a, b)
    if not a or not b or a.z ~= b.z then
        return nil
    end
    return math.max(math.abs((a.x or 0) - (b.x or 0)), math.abs((a.y or 0) - (b.y or 0)))
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

local function onItemAppear(item, oldPos)
    local config = helperLootConfig()
    if not config.enabled or not isValuableLoot(item) then
        return
    end
    local player = localPlayer()
    local playerPos = getPosition(player)
    local itemPos = getPosition(item)
    local range = distance(playerPos, itemPos)
    if range and range <= (config.loot_range or LOOT_CONFIG.loot_range) then
        appendLog("Nearby valuable loot: " .. itemName(item) .. " range=" .. tostring(range))
    end
end

local function scanOpenContainers()
    local config = helperLootConfig()
    if not config.enabled then
        return 0
    end
    local moved = 0
    for _, container in pairs(getOpenContainers()) do
        moved = moved + scanContainer(container, config)
        if moved >= (config.max_items_per_scan or LOOT_CONFIG.max_items_per_scan) then
            break
        end
    end
    return moved
end

local function onThink()
    local config = helperLootConfig()
    if not config.enabled then
        return
    end
    local now = nowMs()
    if now - Loot.last_scan_ms < (config.scan_interval_ms or LOOT_CONFIG.scan_interval_ms) then
        return
    end
    Loot.last_scan_ms = now
    local moved = scanOpenContainers()
    if moved > 0 then
        appendLog("Open container scan moved " .. tostring(moved) .. " items")
    end
end

local function init()
    if connect then
        if Container then
            pcall(function()
                connect(Container, {onOpen = onContainerOpen})
            end)
        end
        if Map then
            pcall(function()
                connect(Map, {onItemAppear = onItemAppear})
            end)
        end
    end
    if cycleEvent and not Loot.think_event then
        Loot.think_event = cycleEvent(onThink, 500)
    end
    appendLog("CTOA Native Loot module loaded in passive profile-fed mode")
end

Loot.scanOpenContainers = scanOpenContainers
Loot.setEnabled = function(enabled)
    LOOT_CONFIG.enabled = enabled == true
    appendLog("Standalone loot " .. (LOOT_CONFIG.enabled and "enabled" or "disabled"))
end
Loot.addValuableLoot = function(itemId, tier, name)
    VALUABLE_LOOT[itemId] = {tier = tier or 1, name = name}
end
_G.CTOA_NativeLoot = Loot

init()
