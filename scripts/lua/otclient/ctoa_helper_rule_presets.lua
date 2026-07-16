-- ctoa_helper_rule_presets.lua [CTOA OTClient Native]
-- Strict data-only import/export boundary for portable Helper rule presets.

local RulePresets = rawget(_G, "CTOA_HELPER_RULE_PRESETS") or {}

local SCHEMA_VERSION = "ctoa-helper-rule-preset-v1"
local MAX_RULES = 16
local MAX_NAME_LENGTH = 64

local TOP_LEVEL_KEYS = {
    schema_version = "string",
    name = "string",
    target_rules = "table",
    spell_rules = "table",
    combat_action_rules = "table",
}

local TARGET_RULE_KEYS = {
    enabled = "boolean",
    name_pattern = "string",
    min_hp = "number",
    max_hp = "number",
    min_distance = "number",
    max_distance = "number",
    min_count = "number",
    max_count = "number",
    priority = "number",
    chase_policy = "string",
}

local SPELL_RULE_KEYS = {
    enabled = "boolean",
    words = "string",
    use_mob_count = "boolean",
    min_nearby = "number",
    max_nearby = "number",
    scan_range = "number",
    cooldown_ms = "number",
    directional = "boolean",
}

local COMBAT_ACTION_RULE_KEYS = {
    enabled = "boolean",
    kind = "string",
    action_text = "string",
    hotkey = "string",
    min_count = "number",
    max_count = "number",
    cooldown_ms = "number",
    stance_mode = "string",
    state_id = "string",
    require_target = "boolean",
    pvp_safe = "boolean",
}

local function decision(allowed, reason, details)
    return {
        allowed = allowed == true,
        reason = tostring(reason or "unknown"),
        details = details,
        runtime_actions = false,
        dispatch_allowed = false,
        runtime_armed = false,
    }
end

local function copyValue(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for key, item in pairs(value) do result[key] = copyValue(item) end
    return result
end

local function sameValue(left, right)
    if type(left) ~= type(right) then return false end
    if type(left) ~= "table" then return left == right end
    for key, value in pairs(left) do
        if not sameValue(value, right[key]) then return false end
    end
    for key in pairs(right) do
        if left[key] == nil then return false end
    end
    return true
end

local function cleanName(value)
    local text = tostring(value or "")
    text = string.gsub(text, "[%c]", " ")
    text = string.gsub(text, "%s+", " ")
    text = string.gsub(string.gsub(text, "^%s+", ""), "%s+$", "")
    return string.sub(text, 1, MAX_NAME_LENGTH)
end

local function validateObject(source, fields, path)
    if type(source) ~= "table" or getmetatable(source) ~= nil then
        return false, path .. ":object_required"
    end
    for key, value in pairs(source) do
        if type(key) ~= "string" or fields[key] == nil then
            return false, path .. ":unknown_field:" .. tostring(key)
        end
        if type(value) ~= fields[key] then
            return false, path .. ":invalid_type:" .. key
        end
        if type(value) == "number" and (value ~= value or value == math.huge or value == -math.huge or value ~= math.floor(value)) then
            return false, path .. ":invalid_integer:" .. key
        end
    end
    for key in pairs(fields) do
        if source[key] == nil then return false, path .. ":missing_field:" .. key end
    end
    return true
end

local function validateRuleList(source, fields, sanitizer, path)
    if type(source) ~= "table" or getmetatable(source) ~= nil then
        return nil, path .. ":array_required"
    end
    local count = 0
    for key in pairs(source) do
        if type(key) ~= "number" or key < 1 or key > MAX_RULES or key ~= math.floor(key) then
            return nil, path .. ":invalid_index:" .. tostring(key)
        end
        count = count + 1
    end
    if count ~= #source then return nil, path .. ":sparse_array" end
    local result = {}
    for index, rule in ipairs(source) do
        local valid, reason = validateObject(rule, fields, path .. "[" .. tostring(index) .. "]")
        if not valid then return nil, reason end
        local sanitized = sanitizer({rule})
        if type(sanitized) ~= "table" or #sanitized ~= 1 or not sameValue(rule, sanitized[1]) then
            return nil, path .. "[" .. tostring(index) .. "]:non_canonical_value"
        end
        result[index] = copyValue(sanitized[1])
    end
    return result, nil
end

local function dependencies()
    local targeting = rawget(_G, "CTOA_HELPER_TARGETING")
    local combat = rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME")
    if type(targeting) ~= "table" or type(targeting.sanitizeTargetRules) ~= "function" then
        return nil, nil, "targeting_sanitizer_unavailable"
    end
    if type(combat) ~= "table" or type(combat.sanitizeRotationRules) ~= "function" or type(combat.sanitizeCombatActionRules) ~= "function" then
        return nil, nil, "combat_sanitizer_unavailable"
    end
    return targeting, combat, nil
end

function RulePresets.schemaVersion()
    return SCHEMA_VERSION
end

function RulePresets.validate(payload)
    local valid, reason = validateObject(payload, TOP_LEVEL_KEYS, "preset")
    if not valid then return nil, decision(false, reason) end
    if payload.schema_version ~= SCHEMA_VERSION then
        local versionReason = string.match(payload.schema_version, "^ctoa%-helper%-rule%-preset%-v%d+$") and "future_schema_version" or "invalid_schema_version"
        return nil, decision(false, versionReason)
    end
    if payload.name ~= cleanName(payload.name) or payload.name == "" then
        return nil, decision(false, "invalid_preset_name")
    end

    local targeting, combat, dependencyReason = dependencies()
    if dependencyReason then return nil, decision(false, dependencyReason) end
    local targetRules, targetReason = validateRuleList(payload.target_rules, TARGET_RULE_KEYS, targeting.sanitizeTargetRules, "target_rules")
    if not targetRules then return nil, decision(false, targetReason) end
    local spellRules, spellReason = validateRuleList(payload.spell_rules, SPELL_RULE_KEYS, combat.sanitizeRotationRules, "spell_rules")
    if not spellRules then return nil, decision(false, spellReason) end
    local actionRules, actionReason = validateRuleList(payload.combat_action_rules, COMBAT_ACTION_RULE_KEYS, combat.sanitizeCombatActionRules, "combat_action_rules")
    if not actionRules then return nil, decision(false, actionReason) end

    return {
        schema_version = SCHEMA_VERSION,
        name = payload.name,
        target_rules = targetRules,
        spell_rules = spellRules,
        combat_action_rules = actionRules,
    }, decision(true, "preset_valid", {
        target_rules = #targetRules,
        spell_rules = #spellRules,
        combat_action_rules = #actionRules,
    })
end

function RulePresets.exportPreset(tools, presetName)
    local targeting, combat, dependencyReason = dependencies()
    if dependencyReason then return nil, decision(false, dependencyReason) end
    if type(tools) ~= "table" then return nil, decision(false, "tools_required") end
    local payload = {
        schema_version = SCHEMA_VERSION,
        name = cleanName(presetName),
        target_rules = targeting.sanitizeTargetRules(tools.target_rules),
        spell_rules = combat.sanitizeRotationRules(tools.rotation_spells),
        combat_action_rules = combat.sanitizeCombatActionRules(tools.combat_action_rules),
    }
    if payload.name == "" then return nil, decision(false, "invalid_preset_name") end
    return RulePresets.validate(payload)
end

function RulePresets.importPreset(tools, payload)
    if type(tools) ~= "table" then return nil, decision(false, "tools_required") end
    local canonical, validation = RulePresets.validate(payload)
    if not canonical then return nil, validation end
    tools.target_rules = copyValue(canonical.target_rules)
    tools.rotation_spells = copyValue(canonical.spell_rules)
    tools.combat_action_rules = copyValue(canonical.combat_action_rules)
    return canonical, decision(true, "preset_imported", validation.details)
end

function RulePresets.contract()
    return {
        module = "ctoa_helper_rule_presets",
        mode = "passive_data_boundary",
        schema_version = SCHEMA_VERSION,
        maximum_rules_per_lane = MAX_RULES,
        owns_rule_preset_validation = true,
        owns_rule_preset_import_export = true,
        rejects_unknown_fields = true,
        rejects_executable_values = true,
        rejects_future_versions = true,
        preserves_safe_boot = true,
        mutates_only_rule_lists_on_import = true,
        runtime_actions = false,
        dispatch_allowed = false,
        arms_runtime = false,
        loads_files = false,
        saves_files = false,
        casts = false,
        attacks = false,
        walks = false,
        uses_items = false,
    }
end

_G.CTOA_HELPER_RULE_PRESETS = RulePresets
return RulePresets
