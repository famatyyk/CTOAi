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
        result[#result + 1] = "user_dir/ctoa_otclient/" .. character .. "_" .. file
    end
    result[#result + 1] = "user_dir/ctoa_otclient/" .. file
    result[#result + 1] = "mods/ctoa_otclient/" .. file
    result[#result + 1] = "/mods/ctoa_otclient/" .. file
    result[#result + 1] = "ctoa_otclient/" .. file
    result[#result + 1] = "/" .. file
    return result
end

function VocationProfiles.contract()
    return {
        module = "ctoa_helper_vocation_profiles",
        mode = "passive",
        supported = {"ek", "ms", "ed", "rp"},
        auto_detect = true,
        runtime_actions = false,
        writes_files = false,
    }
end

_G.CTOA_HELPER_VOCATION_PROFILES = VocationProfiles
return VocationProfiles
