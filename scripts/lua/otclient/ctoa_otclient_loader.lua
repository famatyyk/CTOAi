-- ctoa_otclient_loader.lua  [CTOA OTClient Native]
-- Main loader for all CTOA OTClient native modules

local CTOA_OTCLIENT = {
    version = "1.0.0",
    modules = {},
    loaded = false
}

local function log(msg)
    print("[CTOA-OTC] " .. msg)
    modules.game_console.addText('[CTOA-OTC] ' .. msg, MessageModes.ModeStatus)
end

local function loadModule(moduleName, filePath)
    local success, err = pcall(function()
        dofile(filePath)
        CTOA_OTCLIENT.modules[moduleName] = true
        log("Loaded: " .. moduleName)
    end)
    
    if not success then
        log("FAILED to load " .. moduleName .. ": " .. tostring(err))
        CTOA_OTCLIENT.modules[moduleName] = false
    end
end

local function initializeCTOA()
    if CTOA_OTCLIENT.loaded then
        return
    end
    
    log("Initializing CTOA OTClient Native v" .. CTOA_OTCLIENT.version)
    
    -- Try to load core modules
    local moduleDir = "user_dir/ctoa_otclient/"
    local coreModules = {
        "ctoa_native_heal.lua",
        "ctoa_native_combat.lua", 
        "ctoa_native_loot.lua"
    }
    
    for _, module in ipairs(coreModules) do
        local moduleName = module:gsub("%.lua$", "")
        loadModule(moduleName, moduleDir .. module)
    end
    
    CTOA_OTCLIENT.loaded = true
    
    local successCount = 0
    for _, loaded in pairs(CTOA_OTCLIENT.modules) do
        if loaded then successCount = successCount + 1 end
    end
    
    log("Initialization complete: " .. successCount .. "/" .. #coreModules .. " modules loaded")
end

-- Auto-initialize on game start
local function onGameStart()
    initializeCTOA()
end

connect(g_game, { onGameStart = onGameStart })

-- Manual initialize if already in game
if g_game.isOnline() then
    initializeCTOA()
end

-- Export for manual control
_G.CTOA_OTCLIENT = CTOA_OTCLIENT