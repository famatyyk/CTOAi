-- ctoa_otclient_loader.lua  [CTOA OTClient Native]
-- Safe loader for CTOA OTClient helper UI.

local CTOA_OTCLIENT = rawget(_G, "CTOA_OTCLIENT") or {
    version = "2.1.1a",
    mode = "helper-ui-only",
    modules = {},
    loaded = false,
    loading = false,
}

local LOAD_DELAY_MS = 1500
local HELPER_MODULE = "ctoa_native_helper.lua"
local BOOTSTRAP_MODULE = {name = "ctoa_helper_modules", file = "ctoa_helper_modules.lua"}

local function bootLog(msg)
    if not g_resources or not g_resources.getWorkDir then
        return
    end
    local ok, workDir = pcall(function()
        return g_resources.getWorkDir()
    end)
    if not ok or not workDir or workDir == "" then
        return
    end
    local file = io.open(workDir .. "ctoa_boot.log", "a")
    if file then
        file:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-LOADER] " .. tostring(msg) .. "\n")
        file:close()
    end
end

local function log(msg)
    print("[CTOA-OTC] " .. msg)
    bootLog(msg)
    if modules and modules.game_console and modules.game_console.addText then
        pcall(function()
            modules.game_console.addText("[CTOA-OTC] " .. msg, MessageModes.ModeStatus)
        end)
    end
end

local function fileExists(path)
    if g_resources and g_resources.fileExists then
        local ok, exists = pcall(function()
            return g_resources.fileExists(path)
        end)
        if ok and exists then
            return true
        end
    end
    return false
end

local function resolveModuleDir(anchorFile)
    local candidates = {
        "ctoa_otclient/",
    }
    for _, dir in ipairs(candidates) do
        if fileExists(dir .. anchorFile) then
            return dir
        end
    end
    return nil
end

local function isOnline()
    return g_game and g_game.isOnline and g_game.isOnline()
end

local function loadModule(moduleName, filePath)
    local success, err = pcall(function()
        dofile(filePath)
    end)

    CTOA_OTCLIENT.modules[moduleName] = success
    if success then
        log("Loaded: " .. moduleName)
    else
        log("FAILED to load " .. moduleName .. ": " .. tostring(err))
    end
    return success
end

local function loadHelperFromFilesystem(moduleName)
    if not g_resources or not g_resources.getWorkDir then
        return false
    end
    local candidates = {
        g_resources.getWorkDir() .. "mods/ctoa_otclient/" .. HELPER_MODULE,
    }
    for _, path in ipairs(candidates) do
        local file = io.open(path, "r")
        if file then
            file:close()
            log("Trying filesystem helper: " .. path)
            return loadModule(moduleName, path)
        end
    end
    log("No filesystem helper candidate found")
    return false
end

local function supportManifest()
    local registry = rawget(_G, "CTOA_HELPER_MODULES")
    if type(registry) ~= "table" or type(registry.getSupportModules) ~= "function" then
        log("FAILED: helper boot manifest unavailable")
        return nil
    end
    local modules = registry.getSupportModules()
    if type(registry.validateSupportModules) == "function" then
        local valid, errors = registry.validateSupportModules(modules)
        if not valid then
            log("FAILED: invalid helper boot manifest: " .. table.concat(errors or {}, "; "))
            return nil
        end
    end
    return modules
end

local function loadSupportModules(moduleDir)
    if not moduleDir then
        return false
    end
    if not CTOA_OTCLIENT.modules[BOOTSTRAP_MODULE.name] then
        if not fileExists(moduleDir .. BOOTSTRAP_MODULE.file) or not loadModule(BOOTSTRAP_MODULE.name, moduleDir .. BOOTSTRAP_MODULE.file) then
            return false
        end
    end
    local modules = supportManifest()
    if not modules then
        return false
    end
    for _, module in ipairs(modules) do
        if not CTOA_OTCLIENT.modules[module.name] and fileExists(moduleDir .. module.file) then
            loadModule(module.name, moduleDir .. module.file)
        end
        if not CTOA_OTCLIENT.modules[module.name] then
            log("FAILED: required support module unavailable: " .. tostring(module.name))
            return false
        end
    end
    return true
end

local function loadSupportModulesFromFilesystem()
    if not g_resources or not g_resources.getWorkDir then
        return false
    end
    local baseDirs = {
        g_resources.getWorkDir() .. "mods/ctoa_otclient/",
    }
    if not CTOA_OTCLIENT.modules[BOOTSTRAP_MODULE.name] then
        local bootstrapPath = baseDirs[1] .. BOOTSTRAP_MODULE.file
        local bootstrapFile = io.open(bootstrapPath, "r")
        if bootstrapFile then
            bootstrapFile:close()
            loadModule(BOOTSTRAP_MODULE.name, bootstrapPath)
        end
    end
    local modules = supportManifest()
    if not modules then
        return false
    end
    for _, module in ipairs(modules) do
        if not CTOA_OTCLIENT.modules[module.name] then
            for _, dir in ipairs(baseDirs) do
                local path = dir .. module.file
                local file = io.open(path, "r")
                if file then
                    file:close()
                    loadModule(module.name, path)
                    break
                end
            end
        end
        if not CTOA_OTCLIENT.modules[module.name] then
            log("FAILED: required filesystem support module unavailable: " .. tostring(module.name))
            return false
        end
    end
    return true
end

local function loadHelperOnly()
    if CTOA_OTCLIENT.loaded or CTOA_OTCLIENT.loading then
        return
    end

    CTOA_OTCLIENT.loading = true
    log("Initializing CTOA OTClient Native v" .. tostring(CTOA_OTCLIENT.version) .. " (" .. CTOA_OTCLIENT.mode .. ")")

    local moduleDir = resolveModuleDir(HELPER_MODULE)
    local ok = false
    if moduleDir then
        local supportReady = loadSupportModules(moduleDir)
        if supportReady then
            ok = loadModule("ctoa_native_helper", moduleDir .. HELPER_MODULE)
        end
    else
        log("Resource helper path not resolved; trying filesystem fallback")
    end

    if not ok then
        local supportReady = loadSupportModulesFromFilesystem()
        if supportReady then
            ok = loadHelperFromFilesystem("ctoa_native_helper")
        end
    end
    CTOA_OTCLIENT.loaded = ok
    CTOA_OTCLIENT.loading = false

    if ok then
        log("Initialization complete: helper UI loaded; runtime modules skipped")
    end
end

local function scheduleHelperLoad()
    if CTOA_OTCLIENT.loaded or CTOA_OTCLIENT.loading then
        return
    end
    if scheduleEvent then
        scheduleEvent(loadHelperOnly, LOAD_DELAY_MS)
    elseif addEvent then
        addEvent(loadHelperOnly)
    else
        loadHelperOnly()
    end
end

local function onGameStart()
    if CTOA_OTCLIENT.loaded then
        local helper = rawget(_G, "CTOA_Helper")
        if type(helper) == "table" and type(helper.handleGameStart) == "function" then
            pcall(helper.handleGameStart)
        end
        log("Game started; reused existing helper singleton")
        return
    end
    scheduleHelperLoad()
end

local function onGameEnd()
    CTOA_OTCLIENT.loading = false
    log("Game ended; helper singleton retained for next login")
end

if g_game and connect then
    connect(g_game, {
        onGameStart = onGameStart,
        onGameEnd = onGameEnd,
    })
end

scheduleHelperLoad()

CTOA_OTCLIENT.loadHelperOnly = loadHelperOnly
_G.CTOA_OTCLIENT = CTOA_OTCLIENT
