-- ctoa_helper_feature_flags.lua [CTOA OTClient Native]
-- Passive feature flag matrix for safe defaults. It never toggles runtime settings.

local FeatureFlags = rawget(_G, "CTOA_HELPER_FEATURE_FLAGS") or {}

local FLAGS = {
    {
        key = "enabled",
        domain = "global",
        default = false,
        mode = "runtime_master",
        gate = "operator_arm",
    },
    {
        key = "tools.auto_haste",
        domain = "tools",
        default = false,
        mode = "runtime_spell",
        gate = "SmokeAttachAll",
    },
    {
        key = "tools.auto_exeta",
        domain = "tools",
        default = false,
        mode = "runtime_spell",
        gate = "SmokeAttachAll",
    },
    {
        key = "tools.rune_enabled",
        domain = "combat",
        default = false,
        mode = "runtime_item_use",
        gate = "SmokeAttachAll",
    },
    {
        key = "tools.cavebot_enabled",
        domain = "cavebot",
        default = false,
        mode = "runtime_planner",
        gate = "SmokeAttachAll",
    },
    {
        key = "tools.cavebot_movement_enabled",
        domain = "cavebot",
        default = false,
        mode = "runtime_movement",
        gate = "SmokeAttachAll",
    },
    {
        key = "tools.timer_enabled",
        domain = "timer",
        default = false,
        mode = "bounded_runtime_action",
        gate = "SmokeAttachAll",
    },
    {
        key = "tools.feature_flags.experimental_loot",
        domain = "loot",
        default = false,
        mode = "experimental_runtime",
        gate = "sandbox_loot_log",
    },
    {
        key = "conditions.runtime_enabled",
        domain = "conditions",
        default = false,
        mode = "runtime_recovery",
        gate = "ConditionsRuntimeGate",
    },
    {
        key = "equipment.runtime_enabled",
        domain = "equipment",
        default = false,
        mode = "runtime_equipment",
        gate = "EquipmentRuntimeGate",
    },
    {
        key = "heal_friend.runtime_enabled",
        domain = "heal_friend",
        default = false,
        mode = "runtime_cast",
        gate = "HealFriendRuntimeGate",
    },
    {
        key = "scripting.runtime_enabled",
        domain = "scripting",
        default = false,
        mode = "blocked_runtime_eval",
        gate = "security_review",
    },
    {
        key = "scripting.allow_user_snippets",
        domain = "scripting",
        default = false,
        mode = "blocked_snippets",
        gate = "security_review",
    },
    {
        key = "scripting.allow_runtime_eval",
        domain = "scripting",
        default = false,
        mode = "blocked_eval",
        gate = "security_review",
    },
}

local function copyFlag(flag)
    local item = flag or {}
    return {
        key = tostring(item.key or ""),
        domain = tostring(item.domain or "unknown"),
        default = item.default == true,
        mode = tostring(item.mode or "unknown"),
        gate = tostring(item.gate or "unknown"),
        runtime_actions = false,
        executes_plan = false,
        dispatch_allowed = false,
    }
end

local function valueAtPath(source, key)
    local current = source or {}
    local path = tostring(key or "")
    if current[path] ~= nil then
        return current[path]
    end
    for part in string.gmatch(path, "[^.]+") do
        if type(current) ~= "table" then
            return nil
        end
        current = current[part]
        if current == nil then
            return nil
        end
    end
    return current
end

function FeatureFlags.all()
    local result = {}
    for index, flag in ipairs(FLAGS) do
        result[index] = copyFlag(flag)
    end
    return result
end

function FeatureFlags.safeFalseKeys()
    local result = {}
    for index, flag in ipairs(FLAGS) do
        if flag.default ~= true then
            result[index] = flag.key
        end
    end
    return result
end

function FeatureFlags.byKey(key)
    local name = tostring(key or "")
    for _, flag in ipairs(FLAGS) do
        if flag.key == name then
            return copyFlag(flag)
        end
    end
    return {
        key = name,
        domain = "unknown",
        default = false,
        mode = "unknown",
        gate = "unknown",
        runtime_actions = false,
        executes_plan = false,
        dispatch_allowed = false,
    }
end

function FeatureFlags.audit(profile)
    local cfg = profile or {}
    local unsafe = {}
    for _, flag in ipairs(FLAGS) do
        local value = valueAtPath(cfg, flag.key)
        if value == true and flag.default ~= true then
            unsafe[#unsafe + 1] = flag.key
        end
    end
    return {
        status = #unsafe == 0 and "safe_defaults" or "unsafe_runtime_flags",
        unsafe = unsafe,
        checked_count = #FLAGS,
        runtime_actions = false,
        executes_plan = false,
    }
end

function FeatureFlags.summary(audit)
    local item = audit or {}
    local unsafe = item.unsafe or {}
    return "Feature flags " .. tostring(item.status or "unknown") ..
        " | Checked " .. tostring(item.checked_count or 0) ..
        " | Unsafe " .. tostring(#unsafe)
end

function FeatureFlags.toolsSummary(config, helpers)
    helpers = helpers or {}
    local cfg = config or {}
    local tools = cfg.tools or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local audit = helpers.audit
    local featureFlagText = ""
    if type(audit) == "table" then
        local summary = FeatureFlags.summary(audit)
        if type(summary) == "string" and summary ~= "" then
            featureFlagText = " | " .. summary
        else
            featureFlagText = " | Flags " .. tostring(audit.status or "unknown")
        end
    end
    return "Haste " .. onOffText(tools.auto_haste == true) ..
        " | Exeta " .. onOffText(tools.auto_exeta == true) .. " >= " .. tostring(tools.exeta_min_visible or "?") ..
        " | Timer " .. onOffText(tools.timer_enabled == true) ..
        " | Diagnostics " .. onOffText(tools.feature_flags and tools.feature_flags.diagnostics == true) ..
        featureFlagText
end

function FeatureFlags.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
        toggles_flags = false,
        writes_profile = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
        owns_safe_defaults = true,
        owns_tools_summary = true,
        requires_profile_audit = true,
        requires_module_static_gates = true,
        requires_smoke_attach_all = true,
    }
end

_G.CTOA_HELPER_FEATURE_FLAGS = FeatureFlags
return FeatureFlags
