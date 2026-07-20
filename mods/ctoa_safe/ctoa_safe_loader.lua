-- ctoa_safe_loader.lua [CTOA Safe]
-- Explicit project lifecycle. This file never schedules or autostarts itself.

local LOADER_VERSION = "3.3.0"
local HELPER_FILE = "ctoa_safe_helper.lua"
local Loader = rawget(_G, "CTOA_SAFE_LOADER") or {}
_G.CTOA_SAFE_LOADER = Loader

Loader.version = LOADER_VERSION
Loader.initialized = false

local function log(message)
    local text = "[CTOA-SAFE-LOADER] " .. tostring(message)
    print(text)
    if g_resources and type(g_resources.getWorkDir) == "function" then
        local ok, workDir = pcall(function() return g_resources.getWorkDir() end)
        if ok and workDir and workDir ~= "" then
            local file = io.open(workDir .. "ctoa_safe.log", "a")
            if file then file:write(os.date("%Y-%m-%d %H:%M:%S") .. " " .. text .. "\n"); file:close() end
        end
    end
end

local function selectionAuthorized()
    local projectLoader = rawget(_G, "CTOA_PROJECT_LOADER")
    return type(projectLoader) == "table"
        and type(projectLoader.isSelected) == "function"
        and projectLoader.isSelected("safe") == true
end

local function fileExists(path)
    if g_resources and type(g_resources.fileExists) == "function" then
        local ok, exists = pcall(function() return g_resources.fileExists(path) end)
        if ok and exists then return true end
    end
    local file = io.open(path, "r")
    if file then file:close(); return true end
    return false
end

local function resolveHelperPath()
    local candidates = {"/mods/ctoa_safe/" .. HELPER_FILE, "mods/ctoa_safe/" .. HELPER_FILE, "ctoa_safe/" .. HELPER_FILE}
    for _, path in ipairs(candidates) do if fileExists(path) then return path end end
    return nil
end

function Loader.init()
    if Loader.initialized then return true end
    if not selectionAuthorized() then log("Initialization rejected: neutral loader did not select Safe"); return false end
    local helper = rawget(_G, "CTOA_Helper")
    if type(helper) == "table" and helper.think_event then log("Initialization rejected: Helper runtime is still active"); return false end

    local path = resolveHelperPath()
    if not path then log("Safe project file not found"); return false end
    local ok, result = pcall(function() return dofile(path) end)
    if not ok then log("Safe project load failed: " .. tostring(result)); return false end
    local safe = rawget(_G, "CTOA_SAFE")
    if type(safe) ~= "table" or type(safe.init) ~= "function" then log("Safe project API missing"); return false end
    local initOk, initResult = pcall(safe.init)
    if not initOk or initResult == false then log("Safe project init failed: " .. tostring(initResult)); return false end
    Loader.initialized = true
    log("Safe project initialized exclusively")
    return true
end

function Loader.terminate(reason)
    local safe = rawget(_G, "CTOA_SAFE")
    if type(safe) == "table" and type(safe.terminate) == "function" then pcall(safe.terminate, reason or "loader_terminate") end
    Loader.initialized = false
    log("Safe project terminated")
    return true
end

return Loader
