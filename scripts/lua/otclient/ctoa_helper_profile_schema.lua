-- ctoa_helper_profile_schema.lua [CTOA OTClient Native]
-- Passive profile schema metadata. This module never loads, saves, or migrates profile files.

local ProfileSchema = rawget(_G, "CTOA_HELPER_PROFILE_SCHEMA") or {}

local CURRENT_PROFILE_VERSION = 1
local CURRENT_PROFILE_SCHEMA = "ctoa-helper-profile-v1"

local SECTION_ORDER = {
    "schema_version",
    "vocation",
    "name",
    "enabled",
    "safe_boot_runtime_disabled",
    "tick_ms",
    "hotkey",
    "auto_hide_ms",
    "modules",
    "healing",
    "heal_friend",
    "conditions",
    "equipment",
    "scripting",
    "tools",
    "hud",
}

local SAFE_FALSE_KEYS = {
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

local REQUIRED_SECTIONS = {
    "name",
    "enabled",
    "safe_boot_runtime_disabled",
    "tick_ms",
    "modules",
    "healing",
    "tools",
    "hud",
}

local OPTION_LISTS = {
    spell = {"exura ico", "exura med ico", "exura gran ico", "exura gran", "exura"},
    critical_spell = {"exura med ico", "exura gran ico", "exura gran", "exura"},
    potion_name = {"Health Potion", "Great Health Potion", "Ultimate Health Potion"},
    mana_potion_name = {"Mana Potion", "Strong Mana Potion", "Great Mana Potion", "Ultimate Mana Potion"},
    hotkey = {"F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"},
    rune_name = {"Sudden Death Rune", "Avalanche Rune", "Great Fireball Rune", "Stone Shower Rune", "Thunderstorm Rune"},
    sio_spell = {"exura sio", "exura gran sio"},
    heal_friend_priority = {"lowest_hp", "whitelist_order"},
    magic_priority = {"rotation", "rune"},
    ui_hotkey = {"Ctrl+J", "Ctrl+K", "Ctrl+L", "Ctrl+H", "F1", "F2", "F3", "F4", "F5", "F6"},
    theme_preset = {"classic", "graphite", "amber", "emerald"},
    tool_timeout_ms = {5000, 10000, 15000, 30000},
    timer_interval_ms = {30000, 60000, 120000, 300000},
    tool_range = {3, 5, 7, 8},
}

local ROTATION_PRESETS = {
    {
        id = "smart",
        label = "Smart EK",
        spells = {
            {words = "exori gran", min_nearby = 3, cooldown_ms = 6000},
            {words = "exori min", min_nearby = 2, cooldown_ms = 4000, directional = true},
            {words = "exori", min_nearby = 2, cooldown_ms = 4000},
            {words = "exori gran ico", min_nearby = 1, max_nearby = 2, cooldown_ms = 6000},
            {words = "exori ico", min_nearby = 1, max_nearby = 2, cooldown_ms = 2000},
            {words = "exori hur", min_nearby = 1, cooldown_ms = 2000, max_nearby = 1},
        },
    },
    {
        id = "safe",
        label = "Single safe",
        spells = {
            {words = "exori gran", min_nearby = 4, cooldown_ms = 6000},
            {words = "exori min", min_nearby = 3, cooldown_ms = 4000, directional = true},
            {words = "exori", min_nearby = 3, cooldown_ms = 4000},
            {words = "exori gran ico", min_nearby = 1, max_nearby = 2, cooldown_ms = 6000},
            {words = "exori ico", min_nearby = 1, max_nearby = 2, cooldown_ms = 2000},
            {words = "exori hur", min_nearby = 1, cooldown_ms = 2000, max_nearby = 1},
        },
    },
    {
        id = "aggressive",
        label = "Aggressive",
        spells = {
            {words = "exori gran", min_nearby = 2, cooldown_ms = 6000},
            {words = "exori min", min_nearby = 1, cooldown_ms = 4000, directional = true},
            {words = "exori", min_nearby = 2, cooldown_ms = 4000},
            {words = "exori gran ico", min_nearby = 1, max_nearby = 2, cooldown_ms = 6000},
            {words = "exori ico", min_nearby = 1, max_nearby = 2, cooldown_ms = 2000},
            {words = "exori hur", min_nearby = 1, cooldown_ms = 2000, max_nearby = 1},
        },
    },
}

local KEY_ORDERS = {
    profile = {"schema_version", "vocation", "name", "enabled", "safe_boot_runtime_disabled", "tick_ms", "modules", "healing", "heal_friend", "conditions", "equipment", "scripting", "tools"},
    ui_prefs = {"hotkey", "auto_hide_ms", "theme_preset", "compact_mode", "window_x", "window_y", "active_tab", "hud"},
    healing = {
        "spell_enabled",
        "potion_enabled",
        "spell_threshold",
        "potion_threshold",
        "threshold_jitter_percent",
        "spell",
        "critical_spell",
        "spell_rotation",
        "potion_name",
        "potion_mode",
        "potion_hotkey",
        "potion_actionbar_slot",
        "mana_potion_enabled",
        "mana_potion_threshold",
        "mana_potion_name",
        "mana_potion_hotkey",
        "mana_potion_actionbar_slot",
        "mana_potion_cooldown_ms",
        "cooldown_ms",
    },
    modules = {
        "overview",
        "healing",
        "heal_friend",
        "conditions",
        "targeting",
        "magic",
        "cavebot",
        "equipment",
        "helper",
        "scripting",
        "settings",
        "engine",
    },
    heal_friend = {
        "enabled",
        "observe_party",
        "sio_spell",
        "hp_threshold",
        "cooldown_ms",
        "action_lock_ms",
        "friend_whitelist",
        "priority",
        "require_whitelist",
        "pz_safe",
        "runtime_enabled",
        "friend_scan_range",
        "sample_interval_ms",
        "last_sample_ms",
        "last_status",
        "observed_count",
        "lowest_friend_hp",
        "last_cast_ms",
    },
    conditions = {
        "enabled",
        "observe_states",
        "mana_shield",
        "paralyze",
        "poison",
        "burn",
        "electric",
        "bleeding",
        "runtime_enabled",
        "sample_interval_ms",
        "api_probe_enabled",
        "api_probe_status",
        "api_probe_count",
        "last_sample_ms",
        "last_status",
    },
    equipment = {
        "enabled",
        "observe_slots",
        "ring_swap",
        "amulet_swap",
        "weapon_set",
        "pvp_gear_lock",
        "hp_threshold",
        "sample_interval_ms",
        "api_probe_enabled",
        "api_probe_status",
        "api_probe_count",
        "runtime_enabled",
        "last_sample_ms",
        "last_status",
    },
    scripting = {
        "enabled",
        "policy_mode",
        "allow_user_snippets",
        "allow_runtime_eval",
        "command_model",
        "audit_log",
        "sandbox_required",
        "max_snippet_chars",
        "runtime_enabled",
        "last_status",
    },
    tools = {
        "auto_attack",
        "chase",
        "auto_follow",
        "pause_in_pz",
        "hold_target",
        "require_reachable_target",
        "attack_range",
        "target_timeout_ms",
        "unreachable_timeout_ms",
        "retarget_delay_ms",
        "log_retarget_ms",
        "block_log_ms",
        "probe_log_ms",
        "clear_target_in_pz",
        "block_npc_icons",
        "block_friendly_summons",
        "friendly_summon_name_fragments",
        "ignored_names",
        "prefer_low_hp",
        "priority_names",
        "auto_haste",
        "haste_spell",
        "haste_interval_ms",
        "api_probe_enabled",
        "magic_api_probe_enabled",
        "spell_rotation",
        "magic_priority",
        "rotation_preset",
        "rotation_interval_ms",
        "rotation_scan_range",
        "recovery_action_gap_ms",
        "rotation_spells",
        "auto_exeta",
        "exeta_interval_ms",
        "exeta_min_visible",
        "exeta_spells",
        "auto_stance",
        "offensive_buff_spell",
        "defensive_buff_spell",
        "offensive_max_monsters",
        "defensive_min_monsters",
        "stance_cooldown_ms",
        "last_stance_ms",
        "active_stance",
        "rune_enabled",
        "rune_name",
        "rune_hotkey",
        "rune_actionbar_slot",
        "rune_min_visible",
        "rune_cooldown_ms",
        "rune_pvp_safe",
        "rune_requires_target",
        "timer_enabled",
        "timer_interval_ms",
        "timer_message",
        "last_timer_ms",
        "auto_open_corpses",
        "auto_loot_containers",
        "loot_range",
        "loot_capacity_threshold",
        "loot_max_items_per_scan",
        "cavebot_api_probe_enabled",
        "cavebot_enabled",
        "cavebot_movement_enabled",
        "cavebot_step_delay_ms",
        "cavebot_reach_distance",
        "cavebot_retry_limit",
        "cavebot_waypoints",
        "feature_flags",
        "diagnostics_export_limit",
        "diagnostics_sample_interval_ms",
    },
    hud = {"enabled", "x", "y"},
    rotation = {"words", "min_nearby", "cooldown_ms", "max_nearby", "scan_range"},
    heal_spell = {"threshold", "spell"},
    waypoint = {"x", "y", "z", "label"},
    feature_flags = {"diagnostics", "experimental_cavebot", "experimental_loot", "experimental_combat"},
}

local function copyList(values)
    local result = {}
    for index, value in ipairs(values or {}) do
        result[index] = value
    end
    return result
end

local function copyTable(value)
    if type(value) ~= "table" then
        return value
    end
    local result = {}
    for key, item in pairs(value) do
        result[key] = copyTable(item)
    end
    return result
end

local function isArrayTable(value)
    return type(value) == "table" and #value > 0
end

function ProfileSchema.mergeTable(base, override)
    if type(base) ~= "table" or type(override) ~= "table" then
        return base
    end
    for key, value in pairs(override) do
        if type(value) == "table" and type(base[key]) == "table" then
            if isArrayTable(value) or isArrayTable(base[key]) then
                base[key] = value
            else
                ProfileSchema.mergeTable(base[key], value)
            end
        else
            base[key] = value
        end
    end
    return base
end

local function luaQuote(value)
    return '"' .. tostring(value):gsub("\\", "\\\\"):gsub('"', '\\"') .. '"'
end

local function nestedOrderForKey(key)
    if key == "rotation_spells" then
        return "rotation"
    end
    if key == "spell_rotation" then
        return "heal_spell"
    end
    if key == "cavebot_waypoints" then
        return "waypoint"
    end
    return key
end

function ProfileSchema.serializeLua(value, rootKey, indent)
    indent = indent or 0
    local pad = string.rep(" ", indent)
    local child = string.rep(" ", indent + 4)
    local kind = type(value)

    if kind == "boolean" then
        return value and "true" or "false"
    end
    if kind == "number" then
        return tostring(value)
    end
    if kind == "string" then
        return luaQuote(value)
    end
    if kind ~= "table" then
        return "nil"
    end

    local lines = {"{"}
    if #value > 0 then
        for _, item in ipairs(value) do
            lines[#lines + 1] = child .. ProfileSchema.serializeLua(item, rootKey, indent + 4) .. ","
        end
    else
        local used = {}
        local keys = KEY_ORDERS[tostring(rootKey or "")] or {}
        for _, key in ipairs(keys) do
            if value[key] ~= nil then
                lines[#lines + 1] = child .. key .. " = " .. ProfileSchema.serializeLua(value[key], nestedOrderForKey(key), indent + 4) .. ","
                used[key] = true
            end
        end
        for key, item in pairs(value) do
            if not used[key] then
                lines[#lines + 1] = child .. tostring(key) .. " = " .. ProfileSchema.serializeLua(item, nestedOrderForKey(key), indent + 4) .. ","
            end
        end
    end
    lines[#lines + 1] = pad .. "}"
    return table.concat(lines, "\n")
end

local function shortValue(value, maxLen)
    local text = tostring(value or "")
    local limit = tonumber(maxLen) or 8
    if #text <= limit then
        return text
    end
    return string.sub(text, 1, math.max(1, limit - 1)) .. "~"
end

function ProfileSchema.requiredSections()
    return copyList(REQUIRED_SECTIONS)
end

function ProfileSchema.sectionOrder()
    return copyList(SECTION_ORDER)
end

function ProfileSchema.safeFalseKeys()
    return copyList(SAFE_FALSE_KEYS)
end

function ProfileSchema.optionList(key)
    return copyList(OPTION_LISTS[tostring(key or "")] or {})
end

function ProfileSchema.rotationPresets()
    return copyTable(ROTATION_PRESETS)
end

function ProfileSchema.keyOrder(key)
    return copyList(KEY_ORDERS[tostring(key or "")] or {})
end

function ProfileSchema.valueIndex(options, current)
    for index, value in ipairs(options or {}) do
        if value == current then
            return index
        end
    end
    return 1
end

function ProfileSchema.cycleValue(options, current, direction)
    options = options or {}
    if #options == 0 then
        return current
    end
    local index = ProfileSchema.valueIndex(options, current)
    index = ((index - 1 + (tonumber(direction) or 0)) % #options) + 1
    return options[index]
end

function ProfileSchema.fieldGeometry(x, width)
    local buttonWidth = 14
    local valueWidth = math.min(122, math.max(76, math.floor((tonumber(width) or 0) * 0.46)))
    local prevX = (tonumber(x) or 0) + (tonumber(width) or 0) - (buttonWidth * 2) - valueWidth - 10
    local valueX = prevX + buttonWidth + 3
    local nextX = valueX + valueWidth + 3
    local labelWidth = math.max(64, prevX - (tonumber(x) or 0) - 14)
    return {
        label_width = labelWidth,
        prev_x = prevX,
        value_x = valueX,
        next_x = nextX,
        button_width = buttonWidth,
        value_width = valueWidth,
    }
end

function ProfileSchema.stepValue(current, step, minValue, maxValue)
    local value = (tonumber(current) or 0) + (tonumber(step) or 0)
    if minValue ~= nil then
        value = math.max(tonumber(minValue) or value, value)
    end
    if maxValue ~= nil then
        value = math.min(tonumber(maxValue) or value, value)
    end
    return value
end

local function profileVersion(profile)
    local raw = type(profile) == "table" and profile.schema_version or nil
    if raw == nil or raw == "" then
        return 0, "unversioned"
    end
    if type(raw) == "number" and raw == math.floor(raw) and raw >= 0 then
        return raw, "numeric"
    end
    local parsed = type(raw) == "string" and string.match(raw, "^ctoa%-helper%-profile%-v(%d+)$") or nil
    if parsed then
        return tonumber(parsed), "named"
    end
    return nil, "invalid"
end

local function setPath(root, path, value)
    local current = root
    local parts = {}
    for part in string.gmatch(path, "[^%.]+") do
        parts[#parts + 1] = part
    end
    for index = 1, #parts - 1 do
        local key = parts[index]
        if type(current[key]) ~= "table" then
            current[key] = {}
        end
        current = current[key]
    end
    if #parts > 0 then
        current[parts[#parts]] = value
    end
end

function ProfileSchema.currentVersion()
    return CURRENT_PROFILE_VERSION
end

function ProfileSchema.currentSchema()
    return CURRENT_PROFILE_SCHEMA
end

function ProfileSchema.profileVersion(profile)
    return profileVersion(profile)
end

function ProfileSchema.migrationPlan(profile)
    local cfg = profile or {}
    local sourceVersion, versionKind = profileVersion(cfg)
    local missing = {}
    for _, section in ipairs(REQUIRED_SECTIONS) do
        if cfg[section] == nil then
            table.insert(missing, section)
        end
    end
    local steps = {}
    local allowed = sourceVersion ~= nil and sourceVersion <= CURRENT_PROFILE_VERSION
    if allowed and sourceVersion < CURRENT_PROFILE_VERSION then
        steps[#steps + 1] = "upgrade_to_v1"
    end
    if allowed and #missing > 0 then
        steps[#steps + 1] = "fill_required_sections"
    end
    if allowed then
        steps[#steps + 1] = "enforce_safe_defaults"
    end
    local reason = "schema_ready"
    if sourceVersion == nil then
        reason = "invalid_schema_version"
    elseif sourceVersion > CURRENT_PROFILE_VERSION then
        reason = "future_schema_version"
    elseif #steps > 1 or sourceVersion < CURRENT_PROFILE_VERSION then
        reason = "migration_required"
    end
    return {
        allowed = allowed,
        reason = reason,
        source_version = sourceVersion,
        source_version_kind = versionKind,
        target_version = CURRENT_PROFILE_VERSION,
        target_schema = CURRENT_PROFILE_SCHEMA,
        steps = steps,
        missing_sections = missing,
        enforces_safe_defaults = true,
        preserves_key_order = true,
        runtime_actions = false,
    }
end

function ProfileSchema.migrate(profile, defaults)
    local plan = ProfileSchema.migrationPlan(profile)
    if plan.allowed ~= true then
        return nil, plan
    end
    local migrated = copyTable(type(defaults) == "table" and defaults or {})
    ProfileSchema.mergeTable(migrated, copyTable(type(profile) == "table" and profile or {}))
    migrated.schema_version = CURRENT_PROFILE_SCHEMA
    migrated.safe_boot_runtime_disabled = true
    for _, path in ipairs(SAFE_FALSE_KEYS) do
        setPath(migrated, path, false)
    end
    for _, path in ipairs({
        "heal_friend.enabled",
        "heal_friend.runtime_enabled",
        "conditions.enabled",
        "conditions.runtime_enabled",
        "equipment.enabled",
        "equipment.runtime_enabled",
        "scripting.enabled",
        "scripting.runtime_enabled",
        "scripting.allow_user_snippets",
        "scripting.allow_runtime_eval",
    }) do
        setPath(migrated, path, false)
    end
    plan.applied = #plan.steps > 0
    plan.result_schema = migrated.schema_version
    return migrated, plan
end

function ProfileSchema.summary(plan)
    if type(plan) ~= "table" then
        return "profile schema idle"
    end
    return tostring(plan.reason or "unknown") ..
        " | v" .. tostring(plan.source_version or "?") .. "->" .. tostring(plan.target_version or "?") ..
        " | missing " .. tostring(#(plan.missing_sections or {}))
end

function ProfileSchema.profileSchemaSuffix(profile)
    local plan = ProfileSchema.migrationPlan(profile)
    if type(plan) ~= "table" then
        return ""
    end
    return " | Schema " .. ProfileSchema.summary(plan)
end

function ProfileSchema.autosaveLabel(state)
    state = state or {}
    if state.profile_dirty or state.ui_dirty then
        return "pending"
    end
    return "saved"
end

function ProfileSchema.titleSummary(options)
    options = options or {}
    local version = tostring(options.version or "?")
    local profile = tostring(options.profile or "profile")
    local autosave = ProfileSchema.autosaveLabel(options.autosaveState or {})
    if type(options.autosave) == "string" and options.autosave ~= "" then
        autosave = options.autosave
    end
    return version .. " | " .. profile .. " | " .. autosave
end

function ProfileSchema.healingSummary(config, helpers)
    config = config or {}
    helpers = helpers or {}
    local healing = config.healing or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local actionbarSlotText = helpers.actionbarSlotText or tostring
    local resolveActionbarSlot = helpers.resolveActionbarSlot or function(slot)
        return slot
    end
    local hpSlot = actionbarSlotText(resolveActionbarSlot(healing.potion_actionbar_slot, healing.potion_hotkey))
    local mpSlot = actionbarSlotText(resolveActionbarSlot(healing.mana_potion_actionbar_slot, healing.mana_potion_hotkey))
    return "Runtime " .. onOffText(config.enabled == true) ..
        " | HP spell " .. onOffText(healing.spell_enabled == true) .. " <= " .. tostring(healing.spell_threshold or "?") .. "%" ..
        " | HP pot " .. hpSlot .. " <= " .. tostring(healing.potion_threshold or "?") .. "%" ..
        " | MP " .. mpSlot .. " <= " .. tostring(healing.mana_potion_threshold or "?") .. "%"
end

function ProfileSchema.profileSummary(config, helpers)
    config = config or {}
    helpers = helpers or {}
    local healing = config.healing or {}
    local tools = config.tools or {}
    local displayProfileName = helpers.displayProfileName or function()
        return tostring(config.name or "profile")
    end
    local spellText = helpers.spellText or tostring
    local autosaveLabel = helpers.autosaveLabel or ProfileSchema.autosaveLabel
    local schemaText = tostring(helpers.schemaText or "")
    return displayProfileName() ..
        " | Spell " .. spellText(healing.spell or "?") .. " <= " .. tostring(healing.spell_threshold or "?") .. "%" ..
        " | Rotation " .. tostring(tools.rotation_preset or "custom") ..
        " | Autosave " .. autosaveLabel(helpers.autosaveState or {}) ..
        schemaText
end

function ProfileSchema.rotationPresetIds(presets)
    local result = {}
    for _, preset in ipairs(presets or {}) do
        if type(preset) == "table" and preset.id ~= nil then
            result[#result + 1] = tostring(preset.id)
        end
    end
    return result
end

function ProfileSchema.rotationPresetLabel(presets, presetId)
    local id = tostring(presetId or "")
    for _, preset in ipairs(presets or {}) do
        if type(preset) == "table" and tostring(preset.id or "") == id then
            return tostring(preset.label or preset.id)
        end
    end
    return id
end

function ProfileSchema.rotationSummary(spells, helpers)
    helpers = helpers or {}
    local spellText = helpers.spellText or tostring
    local shortText = helpers.shortText or function(text)
        return tostring(text)
    end
    local pieces = {}
    for index, spell in ipairs(spells or {}) do
        if index > 3 then
            pieces[#pieces + 1] = "..."
            break
        end
        if type(spell) == "table" then
            local words = spellText(spell.words or "?")
            local minNearby = spell.min_nearby or 1
            local maxNearby = spell.max_nearby
            if maxNearby and maxNearby ~= minNearby then
                pieces[#pieces + 1] = words .. " " .. tostring(minNearby) .. "-" .. tostring(maxNearby)
            else
                pieces[#pieces + 1] = words .. " " .. tostring(minNearby) .. "+"
            end
        end
    end
    if #pieces == 0 then
        return "Rotation: no spells"
    end
    return "Rotation: " .. shortText(table.concat(pieces, " | "), 52)
end

function ProfileSchema.spellLabel(value, helpers)
    helpers = helpers or {}
    local shortText = helpers.shortText or shortValue
    local map = {
        ["exura med ico"] = "med ico",
        ["exura gran ico"] = "gran ico",
        ["exura gran"] = "ex gran",
        ["exura ico"] = "ex ico",
        ["exura"] = "exura",
        ["exori gran ico"] = "gran ico",
        ["exori gran"] = "exori gr",
        ["exori min"] = "exori min",
        ["exori ico"] = "ex ico",
        ["exori hur"] = "ex hur",
    }
    return map[value] or shortText(tostring(value), 9)
end

function ProfileSchema.potionLabel(value, helpers)
    helpers = helpers or {}
    local shortText = helpers.shortText or shortValue
    local map = {
        ["Health Potion"] = "HP",
        ["Great Health Potion"] = "GHP",
        ["Ultimate Health Potion"] = "UHP",
        ["Supreme Health Potion"] = "SHP",
    }
    return map[value] or shortText(tostring(value), 8)
end

function ProfileSchema.runeLabel(value, helpers)
    helpers = helpers or {}
    local shortText = helpers.shortText or shortValue
    local map = {
        ["Sudden Death Rune"] = "SD",
        ["Avalanche Rune"] = "AVA",
        ["Great Fireball Rune"] = "GFB",
        ["Stone Shower Rune"] = "SS",
        ["Thunderstorm Rune"] = "TS",
    }
    return map[value] or shortText(tostring(value), 8)
end

function ProfileSchema.healFriendPriorityLabel(value)
    if value == "whitelist_order" then
        return "Whitelist"
    end
    return "Lowest HP"
end

function ProfileSchema.magicPriorityLabel(value)
    if value == "rune" then
        return "Rune"
    end
    return "Rotation"
end

function ProfileSchema.themePresetLabel(value)
    if value == "graphite" then
        return "Graphite"
    end
    if value == "amber" then
        return "Amber"
    end
    if value == "emerald" then
        return "Emerald"
    end
    return "Classic"
end

function ProfileSchema.onOffLabel(value)
    return value and "ON" or "OFF"
end

function ProfileSchema.contract()
    return {
        module = "ctoa_helper_profile_schema",
        mode = "passive",
        owns_schema_metadata = true,
        owns_versioned_migration_plan = true,
        owns_safe_profile_migration = true,
        owns_key_order_metadata = true,
        owns_merge_table = true,
        owns_lua_serializer = true,
        owns_rotation_metadata = true,
        owns_profile_labels = true,
        owns_profile_summaries = true,
        owns_title_summary = true,
        owns_healing_summary = true,
        owns_rotation_summary = true,
        runtime_actions = false,
        loads_files = false,
        saves_files = false,
        migrates_files = false,
        preserves_key_order = true,
        requires_profile_audit = true,
        requires_safe_boot_defaults = true,
    }
end

_G.CTOA_HELPER_PROFILE_SCHEMA = ProfileSchema

return ProfileSchema
