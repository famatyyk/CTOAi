-- ctoa_helper_vocation_profiles.lua [CTOA OTClient Native]
-- Passive vocation detection and profile routing. Never performs game actions.

local VocationProfiles = rawget(_G, "CTOA_HELPER_VOCATION_PROFILES") or {}

-- Solteria exposes a base vocation enum, not classic Tibia vocation ids.
local BY_ID = {
    [1] = "ek", [2] = "rp", [3] = "ms", [4] = "ed",
    -- Keep promoted classic ids for compatible OTClient forks.
    [5] = "ms", [6] = "ed", [7] = "rp", [8] = "ek",
}

local NAME_RULES = {
    {needle = "sorcerer", id = "ms"},
    {needle = "druid", id = "ed"},
    {needle = "paladin", id = "rp"},
    {needle = "knight", id = "ek"},
}

local LABELS = {
    ek = "Elite Knight",
    ms = "Master Sorcerer",
    ed = "Elder Druid",
    rp = "Royal Paladin",
}

local PROFILE_SCHEMA = "ctoa-helper-profile-v1"
local MAX_PACK_DEPTH = 12
local MAX_PACK_NODES = 4096
local SAFE_FALSE_PATHS = {
    "enabled",
    "tools.auto_attack",
    "tools.auto_exeta",
    "tools.auto_haste",
    "tools.spell_rotation",
    "tools.rune_enabled",
    "tools.cavebot_enabled",
    "tools.cavebot_movement_enabled",
    "tools.timer_enabled",
    "tools.feature_flags.experimental_cavebot",
    "tools.feature_flags.experimental_loot",
    "tools.feature_flags.experimental_combat",
}

local function safeCall(value, method)
    if value and type(value[method]) == "function" then
        local ok, result = pcall(function() return value[method](value) end)
        if ok then return result end
    end
    return nil
end

local function slug(value)
    local text = string.lower(tostring(value or ""))
    text = string.gsub(text, "[^%w]+", "_")
    text = string.gsub(text, "^_+", "")
    text = string.gsub(text, "_+$", "")
    return text
end

local function pathValue(root, path)
    local current = root
    for part in string.gmatch(path, "[^%.]+") do
        if type(current) ~= "table" then return nil end
        current = current[part]
    end
    return current
end

local function validateData(value, path, depth, state)
    local kind = type(value)
    if kind == "nil" or kind == "boolean" or kind == "number" or kind == "string" then
        state.nodes = state.nodes + 1
        return state.nodes <= MAX_PACK_NODES
    end
    if kind ~= "table" then
        state.errors[#state.errors + 1] = tostring(path) .. ":non_data_" .. kind
        return false
    end
    if depth > MAX_PACK_DEPTH then
        state.errors[#state.errors + 1] = tostring(path) .. ":max_depth"
        return false
    end
    if state.seen[value] then
        state.errors[#state.errors + 1] = tostring(path) .. ":cycle"
        return false
    end
    state.seen[value] = true
    state.nodes = state.nodes + 1
    if state.nodes > MAX_PACK_NODES then
        state.errors[#state.errors + 1] = tostring(path) .. ":max_nodes"
        state.seen[value] = nil
        return false
    end
    for key, item in pairs(value) do
        local keyKind = type(key)
        if keyKind ~= "string" and keyKind ~= "number" then
            state.errors[#state.errors + 1] = tostring(path) .. ":invalid_key_" .. keyKind
        else
            validateData(item, tostring(path) .. "." .. tostring(key), depth + 1, state)
        end
    end
    state.seen[value] = nil
    return #state.errors == 0
end

function VocationProfiles.normalize(value)
    local numeric = tonumber(value)
    if numeric and BY_ID[numeric] then return BY_ID[numeric] end
    local text = string.lower(tostring(value or ""))
    for _, rule in ipairs(NAME_RULES) do
        if string.find(text, rule.needle, 1, true) then return rule.id end
    end
    if LABELS[text] then return text end
    return nil
end

function VocationProfiles.detect(player)
    if not player then return nil, "player_unavailable" end
    local directId = safeCall(player, "getVocationId")
    local profileId = VocationProfiles.normalize(directId)
    if profileId then return profileId, "getVocationId", directId end

    local vocation = safeCall(player, "getVocation")
    profileId = VocationProfiles.normalize(vocation)
    if profileId then return profileId, "getVocation", vocation end
    if type(vocation) == "table" then
        for _, method in ipairs({"getId", "getClientId", "getName", "getDescription"}) do
            local raw = safeCall(vocation, method)
            profileId = VocationProfiles.normalize(raw)
            if profileId then return profileId, "getVocation." .. method, raw end
        end
    end
    return nil, "vocation_unknown", vocation or directId
end

function VocationProfiles.fileName(profileId)
    local id = VocationProfiles.normalize(profileId) or "ek"
    return "ctoa_" .. id .. "_profile.lua"
end

function VocationProfiles.label(profileId)
    local id = VocationProfiles.normalize(profileId)
    return id and LABELS[id] or "Unknown vocation"
end

function VocationProfiles.characterName(player)
    return slug(safeCall(player, "getName"))
end

function VocationProfiles.candidates(profileId, player)
    local id = VocationProfiles.normalize(profileId) or "ek"
    local file = VocationProfiles.fileName(id)
    local character = VocationProfiles.characterName(player)
    local result = {}
    if character ~= "" then
        result[#result + 1] = "/ctoa_user_" .. character .. "_" .. file
    end
    result[#result + 1] = "/ctoa_user_" .. file:gsub("^ctoa_", "")
    if character ~= "" then
        result[#result + 1] = "user_dir/ctoa_otclient/" .. character .. "_" .. file
    end
    result[#result + 1] = "user_dir/ctoa_otclient/" .. file
    result[#result + 1] = "mods/ctoa_otclient/" .. file
    result[#result + 1] = "/mods/ctoa_otclient/" .. file
    result[#result + 1] = "ctoa_otclient/" .. file
    result[#result + 1] = "/" .. file
    return result
end

function VocationProfiles.validatePack(profile, expectedVocation)
    local errors = {}
    local cfg = type(profile) == "table" and profile or nil
    if not cfg then
        return {allowed = false, reason = "pack_not_table", errors = {"profile:not_table"}, runtime_actions = false}
    end
    if cfg.schema_version ~= PROFILE_SCHEMA then
        errors[#errors + 1] = "schema_version:invalid"
    end
    local vocation = VocationProfiles.normalize(cfg.vocation)
    local expected = VocationProfiles.normalize(expectedVocation)
    if not vocation then
        errors[#errors + 1] = "vocation:invalid"
    elseif expected and vocation ~= expected then
        errors[#errors + 1] = "vocation:mismatch"
    end
    if cfg.safe_boot_runtime_disabled ~= true then
        errors[#errors + 1] = "safe_boot_runtime_disabled:required"
    end
    for _, path in ipairs(SAFE_FALSE_PATHS) do
        if pathValue(cfg, path) == true then
            errors[#errors + 1] = path .. ":must_default_false"
        end
    end
    local state = {errors = errors, seen = {}, nodes = 0}
    validateData(cfg, "profile", 0, state)
    return {
        allowed = #errors == 0,
        reason = #errors == 0 and "pack_ready" or "pack_invalid",
        errors = errors,
        vocation = vocation,
        expected_vocation = expected,
        schema_version = cfg.schema_version,
        data_only = #errors == 0,
        node_count = state.nodes,
        max_nodes = MAX_PACK_NODES,
        max_depth = MAX_PACK_DEPTH,
        runtime_actions = false,
    }
end

function VocationProfiles.contract()
    return {
        module = "ctoa_helper_vocation_profiles",
        mode = "passive",
        supported = {"ek", "ms", "ed", "rp"},
        auto_detect = true,
        owns_data_only_pack_validation = true,
        profile_schema = PROFILE_SCHEMA,
        max_pack_depth = MAX_PACK_DEPTH,
        max_pack_nodes = MAX_PACK_NODES,
        runtime_actions = false,
        writes_files = false,
    }
end

_G.CTOA_HELPER_VOCATION_PROFILES = VocationProfiles
return VocationProfiles
