-- ctoa_helper_client_reporter.lua [CTOA OTClient Native]
-- Passive heartbeat and capability reporter. It never dispatches game actions.

local Reporter = rawget(_G, "CTOA_HELPER_CLIENT_REPORTER") or {}

local SCHEMA_VERSION = "ctoa-client-capabilities-v1"
local PROFILE_SCHEMA = "ctoa-helper-profile-v1"
local HEARTBEAT_INTERVAL_MS = 5000
local P14_CAPTURE_FLAGS = {
    CTOA_P14_CAPTURE_HELPER_ACTIVATION = "helper-ui-only",
    CTOA_P14_ISOLATED_ENVIRONMENT = "true",
    CTOA_P14_CAPTURE_CONTEXT = "guest",
    CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = "false",
    CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = "false",
    CTOA_P14_NETWORK_DISPATCH_USED = "false",
    CTOA_P14_LIVE_CLIENT_ACCESSED = "false",
    CTOA_P14_PROMOTION_ATTEMPTED = "false",
}
local P14_CAPTURE_REPORT_ROOT = "C:\\P14Runner\\evidence\\"

local function p14CaptureRequested()
    if not os or type(os.getenv) ~= "function" then return false end
    for name, expected in pairs(P14_CAPTURE_FLAGS) do
        local ok, value = pcall(function() return os.getenv(name) end)
        if not ok or value ~= expected then return false end
    end
    return true
end

local function p14CaptureReportPath()
    if not p14CaptureRequested() then return nil end
    local ok, target = pcall(function()
        return os.getenv("CTOA_P14_CAPTURE_REPORT_PATH")
    end)
    if not ok or type(target) ~= "string" or target == "" then return nil end

    local normalized = string.gsub(target, "/", "\\")
    local root = string.lower(P14_CAPTURE_REPORT_ROOT)
    if string.lower(string.sub(normalized, 1, #root)) ~= root then return nil end
    local relative = string.sub(normalized, #root + 1)
    if relative == "" or string.find(relative, "\\", 1, true) or string.find(relative, "..", 1, true) or string.find(relative, ":", 1, true) then
        return nil
    end
    local filename = relative
    local revision, nonce = nil, nil
    if filename then
        revision, nonce = string.match(filename, "^p14%-helper%-runtime%-([a-f0-9]+)%-([a-f0-9]+)%.json$")
    end
    if not revision or #revision ~= 40 or not nonce or #nonce ~= 32 then return nil end
    return normalized
end

local function safeCall(target, methodName)
    if not target or type(target[methodName]) ~= "function" then
        return nil
    end
    local ok, value = pcall(function()
        return target[methodName](target)
    end)
    if ok and value ~= nil and tostring(value) ~= "" then
        return value
    end
    return nil
end

local function firstValue(target, methodNames)
    for _, methodName in ipairs(methodNames or {}) do
        local value = safeCall(target, methodName)
        if value ~= nil then
            return value
        end
    end
    return nil
end

local function normalizedId(value, fallback)
    local text = string.lower(tostring(value or fallback or "unknown"))
    text = string.gsub(text, "[^%w%._%-]+", "-")
    text = string.gsub(text, "%-+", "-")
    text = string.gsub(text, "^%-", "")
    text = string.gsub(text, "%-$", "")
    if text == "" then
        return fallback or "unknown"
    end
    return text
end

local function sortedLoadedModules(loaderState)
    local result = {}
    local modules = type(loaderState) == "table" and loaderState.modules or nil
    for moduleName, loaded in pairs(type(modules) == "table" and modules or {}) do
        if loaded == true then
            result[#result + 1] = tostring(moduleName)
        end
    end
    table.sort(result)
    return result
end

local function runtimeCoreSnapshot(runtimeCore)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    if type(core) == "table" and type(core.statusSnapshot) == "function" then
        local ok, snapshot = pcall(core.statusSnapshot)
        if ok and type(snapshot) == "table" then
            snapshot.status = "available"
            snapshot.runtime_actions = false
            return snapshot
        end
    end
    return {
        schema_version = "ctoa.runtime-core.v1",
        status = "unavailable",
        mode = "passive",
        runtime_actions = false,
        registered_modules = 0,
        registered_tasks = 0,
        enabled_tasks = 0,
        disabled_tasks = 0,
        failed_tasks = 0,
        tasks_deferred = 0,
        task_failures = 0,
        tasks = {},
    }
end

local function jsonEscape(value)
    local text = tostring(value or "")
    text = string.gsub(text, "\\", "\\\\")
    text = string.gsub(text, '"', '\\"')
    text = string.gsub(text, "\b", "\\b")
    text = string.gsub(text, "\f", "\\f")
    text = string.gsub(text, "\n", "\\n")
    text = string.gsub(text, "\r", "\\r")
    text = string.gsub(text, "\t", "\\t")
    return text
end

local function isArray(value)
    local count = 0
    for key in pairs(value) do
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 then
            return false, 0
        end
        count = math.max(count, key)
    end
    for index = 1, count do
        if value[index] == nil then
            return false, 0
        end
    end
    return true, count
end

local function encodeJson(value)
    local valueType = type(value)
    if value == nil then
        return "null"
    elseif valueType == "boolean" then
        return value and "true" or "false"
    elseif valueType == "number" then
        return tostring(value)
    elseif valueType == "string" then
        return '"' .. jsonEscape(value) .. '"'
    elseif valueType ~= "table" then
        return '"' .. jsonEscape(tostring(value)) .. '"'
    end

    local array, count = isArray(value)
    local parts = {}
    if array then
        for index = 1, count do
            parts[#parts + 1] = encodeJson(value[index])
        end
        return "[" .. table.concat(parts, ",") .. "]"
    end

    local keys = {}
    for key in pairs(value) do
        keys[#keys + 1] = tostring(key)
    end
    table.sort(keys)
    for _, key in ipairs(keys) do
        parts[#parts + 1] = '"' .. jsonEscape(key) .. '":' .. encodeJson(value[key])
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

function Reporter.detect(context)
    local data = context or {}
    local app = data.app
    local game = data.game
    local familyValue = firstValue(app, {"getName", "getApplicationName"}) or "otclient"
    local buildValue = firstValue(game, {"getClientVersion"}) or
        firstValue(app, {"getVersion", "getBuildVersion", "getBuildRevision"})
    local buildId = buildValue and normalizedId(buildValue, "unknown") or "unknown"
    local family = normalizedId(familyValue, "otclient")
    local knownBuild = buildId ~= "unknown"
    local protocolReady = data.protocol_ready == true and knownBuild
    local clientId = normalizedId(data.client_id, family .. "-local-default")

    return {
        schema_version = SCHEMA_VERSION,
        client_id = clientId,
        client_family = family,
        build_id = buildId,
        status = knownBuild and "known_build" or "unknown_build",
        helper_version = tostring(data.helper_version or "unknown"),
        vocation = tostring(data.vocation or "unknown"),
        profile_name = tostring(data.profile_name or "unknown"),
        supported_modules = sortedLoadedModules(data.loader_state),
        protocol_status = protocolReady and "ready" or "pending_protocol_source",
        profile_schema = PROFILE_SCHEMA,
        safe_fallback = not protocolReady,
        runtime_actions = false,
        runtime_core = runtimeCoreSnapshot(data.runtime_core),
    }
end

function Reporter.snapshot(context)
    local data = context or {}
    local snapshot = Reporter.detect(data)
    local unixSeconds = os.time and os.time() or 0
    snapshot.observed_at = os.date and os.date("!%Y-%m-%dT%H:%M:%SZ", unixSeconds) or nil
    snapshot.observed_at_unix_ms = unixSeconds * 1000
    snapshot.heartbeat_interval_ms = HEARTBEAT_INTERVAL_MS
    snapshot.heartbeat_status = data.active == false and "offline" or "online"
    snapshot.online = data.online == true
    return snapshot
end

function Reporter.resolvePath(uiPath, resources)
    local capturePath = p14CaptureReportPath()
    if capturePath then
        return capturePath
    end
    if type(uiPath) == "string" and uiPath ~= "" then
        local resolved = string.gsub(uiPath, "ctoa_ui_prefs%.lua$", "ctoa_client_capabilities.json")
        if resolved ~= uiPath then
            return resolved
        end
    end
    if resources and type(resources.getUserDir) == "function" then
        local ok, userDir = pcall(function()
            return resources.getUserDir()
        end)
        if ok and userDir and userDir ~= "" then
            return userDir .. "/ctoa_client_capabilities.json"
        end
    end
    return "ctoa_client_capabilities.json"
end

function Reporter.writeSnapshot(path, snapshot, ioLib, osLib)
    local fileApi = ioLib or io
    local systemApi = osLib or os
    if not fileApi or type(fileApi.open) ~= "function" then
        return false, "io_unavailable"
    end
    local target = tostring(path or "ctoa_client_capabilities.json")
    local temporary = target .. ".tmp"
    local file = fileApi.open(temporary, "w")
    if not file then
        return false, "report_open_failed"
    end
    file:write(encodeJson(snapshot or {}) .. "\n")
    file:close()

    if systemApi and type(systemApi.remove) == "function" then
        pcall(function()
            systemApi.remove(target)
        end)
    end
    if systemApi and type(systemApi.rename) == "function" then
        local ok, renamed = pcall(function()
            return systemApi.rename(temporary, target)
        end)
        if ok and renamed then
            return true
        end
    end
    return false, "report_rename_failed"
end

function Reporter.intervalMs()
    return HEARTBEAT_INTERVAL_MS
end

function Reporter.contract()
    return {
        mode = "passive",
        schema_version = SCHEMA_VERSION,
        runtime_actions = false,
        heartbeat_interval_ms = HEARTBEAT_INTERVAL_MS,
        detects_client_capabilities = true,
        unknown_build_safe_fallback = true,
        writes_atomic_json = true,
        reports_runtime_core = true,
    }
end

_G.CTOA_HELPER_CLIENT_REPORTER = Reporter
return Reporter
