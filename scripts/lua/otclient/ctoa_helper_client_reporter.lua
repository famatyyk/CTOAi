-- ctoa_helper_client_reporter.lua [CTOA OTClient Native]
-- Passive heartbeat and capability reporter. It never dispatches game actions.

local Reporter = rawget(_G, "CTOA_HELPER_CLIENT_REPORTER") or {}

local SCHEMA_VERSION = "ctoa-client-capabilities-v1"
local PROFILE_SCHEMA = "ctoa-helper-profile-v1"
local HEARTBEAT_INTERVAL_MS = 5000

local CONDITIONS_OBSERVATION_SCHEMA = "ctoa.conditions-observation.v1"
local EQUIPMENT_SHADOW_OBSERVATION_SCHEMA = "ctoa.equipment-shadow-observation.v1"
local HEAL_FRIEND_SCAN_SCHEMA = "ctoa.heal-friend-scan.v1"
local CONDITIONS_OBSERVATION_FIELDS = {
    "schema_version", "observed_at_unix_ms", "observation_id", "online", "alive",
    "protection_zone", "protection_zone_source", "condition_id", "condition_state",
    "cooldown", "cooldown_source", "producer_source", "dispatch_allowed",
    "runtime_actions", "executes_plan", "execute_once_allowed", "promotion_allowed",
}
local CONDITIONS_OBSERVATION_FIELD_SET = {}
for _, field in ipairs(CONDITIONS_OBSERVATION_FIELDS) do
    CONDITIONS_OBSERVATION_FIELD_SET[field] = true
end
local EQUIPMENT_SHADOW_OBSERVATION_FIELDS = {
    "schema_version", "observed_at_unix_ms", "observation_id", "online", "alive",
    "protection_zone", "protection_zone_source", "inventory_api_available",
    "containers_complete", "ring", "candidates", "cooldown", "cooldown_source",
    "producer_source", "dispatch_allowed", "runtime_actions", "executes_plan",
    "execute_once_allowed", "promotion_allowed",
}
local EQUIPMENT_SHADOW_OBSERVATION_FIELD_SET = {}
for _, field in ipairs(EQUIPMENT_SHADOW_OBSERVATION_FIELDS) do
    EQUIPMENT_SHADOW_OBSERVATION_FIELD_SET[field] = true
end
local HEAL_FRIEND_SCAN_FIELDS = {
    "schema_version", "observed_at_unix_ms", "party_observed_at_unix_ms",
    "observation_id", "online", "alive", "protection_zone",
    "protection_zone_source", "self_id", "scan_complete", "candidates",
    "cooldown", "cooldown_source", "producer_source", "dispatch_allowed",
    "runtime_actions", "executes_plan", "execute_once_allowed",
    "promotion_allowed", "casts", "talks",
}
local HEAL_FRIEND_SCAN_FIELD_SET = {}
for _, field in ipairs(HEAL_FRIEND_SCAN_FIELDS) do HEAL_FRIEND_SCAN_FIELD_SET[field] = true end

local function oneOf(value, allowed)
    if type(value) ~= "string" then
        return false
    end
    for _, candidate in ipairs(allowed or {}) do
        if value == candidate then
            return true
        end
    end
    return false
end

local function validObservationId(value)
    return type(value) == "string" and #value >= 1 and #value <= 64 and
        string.match(value, "^[a-z0-9][a-z0-9_%-]*$") ~= nil
end

local function finiteInteger(value, minimum, maximum)
    return type(value) == "number" and value == value and value > -math.huge and
        value < math.huge and value % 1 == 0 and value >= minimum and value <= maximum
end

local function sanitizeConditionsObservation(observation, observedAtUnixMs)
    if type(observation) ~= "table" then
        return nil
    end
    local fieldCount = 0
    for key in next, observation do
        if type(key) ~= "string" or CONDITIONS_OBSERVATION_FIELD_SET[key] ~= true then
            return nil
        end
        fieldCount = fieldCount + 1
    end
    if fieldCount ~= #CONDITIONS_OBSERVATION_FIELDS then
        return nil
    end
    for _, field in ipairs(CONDITIONS_OBSERVATION_FIELDS) do
        if rawget(observation, field) == nil then
            return nil
        end
    end

    local observedAt = rawget(observation, "observed_at_unix_ms")
    if type(observedAt) ~= "number" or observedAt % 1 ~= 0 or observedAt < 1 or
        observedAt > 9999999999999 or observedAt ~= observedAtUnixMs then
        return nil
    end
    if rawget(observation, "schema_version") ~= CONDITIONS_OBSERVATION_SCHEMA or
        not validObservationId(rawget(observation, "observation_id")) or
        not oneOf(rawget(observation, "online"), {"online", "offline", "unknown"}) or
        not oneOf(rawget(observation, "alive"), {"alive", "dead", "unknown"}) or
        not oneOf(rawget(observation, "protection_zone"), {"outside", "inside", "unknown"}) or
        not oneOf(rawget(observation, "protection_zone_source"), {"player_method", "player_states", "unavailable"}) or
        rawget(observation, "condition_id") ~= "paralyze" or
        not oneOf(rawget(observation, "condition_state"), {"present", "absent", "unknown"}) or
        not oneOf(rawget(observation, "cooldown"), {"ready", "active", "unknown"}) or
        not oneOf(rawget(observation, "cooldown_source"), {"game_cooldown_group", "unavailable"}) or
        rawget(observation, "producer_source") ~= "otclient_guarded_adapter" then
        return nil
    end
    for _, field in ipairs({
        "dispatch_allowed", "runtime_actions", "executes_plan",
        "execute_once_allowed", "promotion_allowed",
    }) do
        if rawget(observation, field) ~= false then
            return nil
        end
    end

    return {
        schema_version = CONDITIONS_OBSERVATION_SCHEMA,
        observed_at_unix_ms = observedAt,
        observation_id = rawget(observation, "observation_id"),
        online = rawget(observation, "online"),
        alive = rawget(observation, "alive"),
        protection_zone = rawget(observation, "protection_zone"),
        protection_zone_source = rawget(observation, "protection_zone_source"),
        condition_id = "paralyze",
        condition_state = rawget(observation, "condition_state"),
        cooldown = rawget(observation, "cooldown"),
        cooldown_source = rawget(observation, "cooldown_source"),
        producer_source = "otclient_guarded_adapter",
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
        execute_once_allowed = false,
        promotion_allowed = false,
    }
end

local function optionalConditionsObservation(context, observedAtUnixMs)
    local data = context or {}
    local adapter = data.observation_adapter or
        rawget(_G, "CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER")
    if type(adapter) ~= "table" or type(adapter.conditionsSnapshot) ~= "function" then
        return nil
    end
    local ok, observation = pcall(adapter.conditionsSnapshot, {
        game = data.game,
        modules = data.modules,
        observed_at_unix_ms = observedAtUnixMs,
    })
    if not ok or type(observation) ~= "table" then
        return nil
    end
    local sanitizedOk, sanitized = pcall(
        sanitizeConditionsObservation, observation, observedAtUnixMs
    )
    return sanitizedOk and sanitized or nil
end

local function sanitizeEquipmentShadowObservation(observation, observedAtUnixMs)
    if type(observation) ~= "table" then return nil end
    local fieldCount = 0
    for key in next, observation do
        if type(key) ~= "string" or EQUIPMENT_SHADOW_OBSERVATION_FIELD_SET[key] ~= true then return nil end
        fieldCount = fieldCount + 1
    end
    if fieldCount ~= #EQUIPMENT_SHADOW_OBSERVATION_FIELDS then return nil end
    for _, field in ipairs(EQUIPMENT_SHADOW_OBSERVATION_FIELDS) do
        if rawget(observation, field) == nil then return nil end
    end
    if rawget(observation, "schema_version") ~= EQUIPMENT_SHADOW_OBSERVATION_SCHEMA or
        rawget(observation, "observed_at_unix_ms") ~= observedAtUnixMs or
        not validObservationId(rawget(observation, "observation_id")) or
        not oneOf(rawget(observation, "online"), {"online", "offline", "unknown"}) or
        not oneOf(rawget(observation, "alive"), {"alive", "dead", "unknown"}) or
        not oneOf(rawget(observation, "protection_zone"), {"outside", "inside", "unknown"}) or
        not oneOf(rawget(observation, "protection_zone_source"), {"player_method", "player_states", "unavailable"}) or
        type(rawget(observation, "inventory_api_available")) ~= "boolean" or
        type(rawget(observation, "containers_complete")) ~= "boolean" or
        not oneOf(rawget(observation, "cooldown"), {"ready", "active", "unknown"}) or
        not oneOf(rawget(observation, "cooldown_source"), {"game_cooldown_group", "unavailable"}) or
        rawget(observation, "producer_source") ~= "otclient_guarded_adapter" then return nil end
    for _, field in ipairs({"dispatch_allowed", "runtime_actions", "executes_plan", "execute_once_allowed", "promotion_allowed"}) do
        if rawget(observation, field) ~= false then return nil end
    end
    local ring = rawget(observation, "ring")
    if type(ring) ~= "table" or type(ring.present) ~= "boolean" or
        not finiteInteger(ring.item_id, 0, 65535) or not finiteInteger(ring.count, 0, 65535) then return nil end
    local candidates = rawget(observation, "candidates")
    if type(candidates) ~= "table" or #candidates > 256 then return nil end
    local candidateKeyCount = 0
    for key in next, candidates do
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 then return nil end
        candidateKeyCount = candidateKeyCount + 1
    end
    if candidateKeyCount ~= #candidates then return nil end
    local cleanCandidates = {}
    for index, item in ipairs(candidates) do
        if type(item) ~= "table" or next(item) == nil or
            not finiteInteger(item.container_id, 0, 65535) or
            not finiteInteger(item.slot_index, 1, 65535) or
            not finiteInteger(item.item_id, 1, 65535) or
            not finiteInteger(item.count, 1, 65535) then return nil end
        local keyCount = 0
        for key in next, item do
            if key ~= "container_id" and key ~= "slot_index" and key ~= "item_id" and key ~= "count" then return nil end
            keyCount = keyCount + 1
        end
        if keyCount ~= 4 then return nil end
        cleanCandidates[index] = {container_id = item.container_id, slot_index = item.slot_index,
            item_id = item.item_id, count = item.count}
    end
    return {
        schema_version = EQUIPMENT_SHADOW_OBSERVATION_SCHEMA,
        observed_at_unix_ms = observedAtUnixMs,
        observation_id = rawget(observation, "observation_id"),
        online = rawget(observation, "online"), alive = rawget(observation, "alive"),
        protection_zone = rawget(observation, "protection_zone"),
        protection_zone_source = rawget(observation, "protection_zone_source"),
        inventory_api_available = rawget(observation, "inventory_api_available"),
        containers_complete = rawget(observation, "containers_complete"),
        ring = {present = ring.present, item_id = ring.item_id, count = ring.count},
        candidates = cleanCandidates, cooldown = rawget(observation, "cooldown"),
        cooldown_source = rawget(observation, "cooldown_source"),
        producer_source = "otclient_guarded_adapter", dispatch_allowed = false,
        runtime_actions = false, executes_plan = false, execute_once_allowed = false,
        promotion_allowed = false,
    }
end

local function optionalEquipmentShadowObservation(context, observedAtUnixMs)
    local data = context or {}
    local adapter = data.observation_adapter or rawget(_G, "CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER")
    if type(adapter) ~= "table" or type(adapter.equipmentShadowObservation) ~= "function" then return nil end
    local ok, observation = pcall(adapter.equipmentShadowObservation, {
        game = data.game, modules = data.modules, observed_at_unix_ms = observedAtUnixMs,
    })
    if not ok or type(observation) ~= "table" then return nil end
    local sanitizedOk, sanitized = pcall(sanitizeEquipmentShadowObservation, observation, observedAtUnixMs)
    return sanitizedOk and sanitized or nil
end

local function canonicalCreatureName(value)
    return type(value) == "string" and #value >= 1 and #value <= 64 and
        value == string.lower(value) and string.match(value, "^[a-z][a-z0-9 ]*$") ~= nil and
        string.match(value, "^%s") == nil and string.match(value, "%s$") == nil and
        string.match(value, "%s%s") == nil
end

local function sanitizeHealFriendScan(scan, observedAtUnixMs)
    if type(scan) ~= "table" then return nil end
    local fieldCount = 0
    for key in next, scan do
        if type(key) ~= "string" or HEAL_FRIEND_SCAN_FIELD_SET[key] ~= true then return nil end
        fieldCount = fieldCount + 1
    end
    if fieldCount ~= #HEAL_FRIEND_SCAN_FIELDS then return nil end
    for _, field in ipairs(HEAL_FRIEND_SCAN_FIELDS) do
        if rawget(scan, field) == nil then return nil end
    end
    if rawget(scan, "schema_version") ~= HEAL_FRIEND_SCAN_SCHEMA or
        rawget(scan, "observed_at_unix_ms") ~= observedAtUnixMs or
        rawget(scan, "party_observed_at_unix_ms") ~= observedAtUnixMs or
        not validObservationId(rawget(scan, "observation_id")) or
        not oneOf(rawget(scan, "online"), {"online", "offline", "unknown"}) or
        not oneOf(rawget(scan, "alive"), {"alive", "dead", "unknown"}) or
        not oneOf(rawget(scan, "protection_zone"), {"outside", "inside", "unknown"}) or
        not oneOf(rawget(scan, "protection_zone_source"), {"player_method", "player_states", "unavailable"}) or
        not finiteInteger(rawget(scan, "self_id"), 0, 2147483647) or
        type(rawget(scan, "scan_complete")) ~= "boolean" or
        not oneOf(rawget(scan, "cooldown"), {"ready", "active", "unknown"}) or
        not oneOf(rawget(scan, "cooldown_source"), {"game_cooldown_group", "unavailable"}) or
        rawget(scan, "producer_source") ~= "otclient_guarded_adapter" then return nil end
    for _, field in ipairs({"dispatch_allowed", "runtime_actions", "executes_plan",
        "execute_once_allowed", "promotion_allowed", "casts", "talks"}) do
        if rawget(scan, field) ~= false then return nil end
    end
    local candidates = rawget(scan, "candidates")
    if type(candidates) ~= "table" or #candidates > 64 then return nil end
    local clean, previousId, previousName = {}, -1, ""
    for index, candidate in ipairs(candidates) do
        if type(candidate) ~= "table" then return nil end
        local count = 0
        for key in next, candidate do
            if key ~= "target_id" and key ~= "target_name" and key ~= "hp_percent" and
                key ~= "distance" and key ~= "target_is_player" and key ~= "target_is_self" and
                key ~= "target_party_member" and key ~= "target_visible" and
                key ~= "target_same_floor" then return nil end
            count = count + 1
        end
        if count ~= 9 or not finiteInteger(candidate.target_id, 1, 2147483647) or
            not canonicalCreatureName(candidate.target_name) or
            not finiteInteger(candidate.hp_percent, 0, 100) or
            not finiteInteger(candidate.distance, 0, 255) then return nil end
        for _, field in ipairs({"target_is_player", "target_is_self", "target_party_member",
            "target_visible", "target_same_floor"}) do
            if type(candidate[field]) ~= "boolean" then return nil end
        end
        if candidate.target_id < previousId or
            (candidate.target_id == previousId and candidate.target_name < previousName) then return nil end
        previousId, previousName = candidate.target_id, candidate.target_name
        clean[index] = {
            target_id = candidate.target_id, target_name = candidate.target_name,
            hp_percent = candidate.hp_percent, distance = candidate.distance,
            target_is_player = candidate.target_is_player,
            target_is_self = candidate.target_is_self,
            target_party_member = candidate.target_party_member,
            target_visible = candidate.target_visible,
            target_same_floor = candidate.target_same_floor,
        }
    end
    return {
        schema_version = HEAL_FRIEND_SCAN_SCHEMA,
        observed_at_unix_ms = observedAtUnixMs,
        party_observed_at_unix_ms = observedAtUnixMs,
        observation_id = rawget(scan, "observation_id"),
        online = rawget(scan, "online"), alive = rawget(scan, "alive"),
        protection_zone = rawget(scan, "protection_zone"),
        protection_zone_source = rawget(scan, "protection_zone_source"),
        self_id = rawget(scan, "self_id"), scan_complete = rawget(scan, "scan_complete"),
        candidates = clean, cooldown = rawget(scan, "cooldown"),
        cooldown_source = rawget(scan, "cooldown_source"),
        producer_source = "otclient_guarded_adapter", dispatch_allowed = false,
        runtime_actions = false, executes_plan = false, execute_once_allowed = false,
        promotion_allowed = false, casts = false, talks = false,
    }
end

local function optionalHealFriendScan(context, observedAtUnixMs)
    local data = context or {}
    local adapter = data.observation_adapter or rawget(_G, "CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER")
    if type(adapter) ~= "table" or type(adapter.healFriendScan) ~= "function" then return nil end
    local ok, scan = pcall(adapter.healFriendScan, {
        game = data.game, map = data.map, modules = data.modules,
        observed_at_unix_ms = observedAtUnixMs,
    })
    if not ok or type(scan) ~= "table" then return nil end
    local sanitizedOk, sanitized = pcall(sanitizeHealFriendScan, scan, observedAtUnixMs)
    return sanitizedOk and sanitized or nil
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
        runtime_session_armed = data.runtime_session_armed == true,
        runtime_state = data.runtime_session_armed == true and "armed" or "disarmed",
        runtime_enabled = data.runtime_enabled == true,
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
    snapshot.conditions_observation = optionalConditionsObservation(
        data, snapshot.observed_at_unix_ms
    )
    snapshot.equipment_shadow_observation = optionalEquipmentShadowObservation(
        data, snapshot.observed_at_unix_ms
    )
    snapshot.heal_friend_scan = optionalHealFriendScan(data, snapshot.observed_at_unix_ms)
    return snapshot
end

local function resourceDir(resources, methodName)
    if not resources or type(resources[methodName]) ~= "function" then
        return ""
    end
    local ok, value = pcall(function()
        return resources[methodName]()
    end)
    if not ok or type(value) ~= "string" or value == "" then
        return ""
    end
    local last = string.sub(value, -1)
    if last ~= "/" and last ~= "\\" then
        return value .. "/"
    end
    return value
end

function Reporter.resolvePath(uiPath, resources)
    local workDir = resourceDir(resources, "getWorkDir")
    if type(uiPath) == "string" and uiPath ~= "" then
        local resolved = string.gsub(uiPath, "ctoa_ui_prefs%.lua$", "ctoa_client_capabilities.json")
        if resolved ~= uiPath then
            if workDir ~= "" and string.sub(resolved, 1, 9) == "user_dir/" then
                return workDir .. "mods/ctoa_otclient/ctoa_client_capabilities.json"
            end
            if workDir ~= "" and string.sub(resolved, 1, 14) == "ctoa_otclient/" then
                return workDir .. "mods/" .. resolved
            end
            if workDir ~= "" and string.sub(resolved, 1, 1) == "/" and
                not string.match(resolved, "^/[A-Za-z]:") then
                return workDir .. "mods/ctoa_otclient/ctoa_client_capabilities.json"
            end
            return resolved
        end
    end
    if workDir ~= "" then
        return workDir .. "mods/ctoa_otclient/ctoa_client_capabilities.json"
    end
    local userDir = resourceDir(resources, "getUserDir")
    if userDir ~= "" then
        return userDir .. "ctoa_client_capabilities.json"
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

function Reporter.report(helper, config, helperVersion, runtimeCore, observationAdapter, now, force, active)
    local state = type(helper) == "table" and helper or nil
    local settings = type(config) == "table" and config or {}
    local timestamp = tonumber(now) or 0
    if not state then return false end
    if force ~= true and timestamp - (tonumber(state.last_client_report_ms) or 0) < HEARTBEAT_INTERVAL_MS then
        return false
    end
    local game = rawget(_G, "g_game")
    local online = false
    if game and type(game.isOnline) == "function" then
        local ok, value = pcall(game.isOnline)
        online = ok and value == true
    end
    local snapshot = Reporter.snapshot({
        app = rawget(_G, "g_app"), game = game, map = rawget(_G, "g_map"),
        loader_state = rawget(_G, "CTOA_OTCLIENT"), helper_version = helperVersion,
        vocation = state.vocation_id, profile_name = state.profile_name,
        online = online, active = active ~= false, protocol_ready = false,
        runtime_session_armed = state.runtime_session_armed == true,
        runtime_enabled = settings.enabled == true, runtime_core = runtimeCore,
        observation_adapter = observationAdapter, modules = rawget(_G, "modules"),
    })
    local path = Reporter.resolvePath(state.ui_path, rawget(_G, "g_resources"))
    if type(path) ~= "string" or path == "" then return false end
    local written = Reporter.writeSnapshot(path, snapshot, io, os)
    if written == true then
        state.last_client_report_ms = timestamp
        state.client_report_path = path
        return true
    end
    return false
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
        owns_report_lifecycle = true,
        reports_runtime_core = true,
        reports_optional_conditions_observation = true,
        sanitizes_conditions_observation = true,
        reports_optional_equipment_shadow_observation = true,
        sanitizes_equipment_shadow_observation = true,
        reports_optional_heal_friend_scan = true,
        sanitizes_heal_friend_scan = true,
        deterministic_work_dir_path = true,
        no_screen_safe = true,
    }
end

_G.CTOA_HELPER_CLIENT_REPORTER = Reporter
return Reporter
