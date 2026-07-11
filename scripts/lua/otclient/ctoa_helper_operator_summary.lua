-- ctoa_helper_operator_summary.lua [CTOA OTClient Native]
-- Passive operator summary composer. It formats text only and never touches runtime APIs.

local OperatorSummary = rawget(_G, "CTOA_HELPER_OPERATOR_SUMMARY") or {}

local function callText(fn, fallback, ...)
    if type(fn) == "function" then
        local ok, text = pcall(fn, ...)
        if ok and type(text) == "string" and text ~= "" then
            return text
        end
    end
    return fallback
end

local function moduleSummary(module, functionName, fallback, ...)
    if module and type(module[functionName]) == "function" then
        local ok, text = pcall(module[functionName], ...)
        if ok and type(text) == "string" and text ~= "" then
            return text
        end
    end
    return fallback
end

function OperatorSummary.title(context)
    context = context or {}
    local helpers = context.helpers or {}
    local schema = context.profileSchema
    return moduleSummary(schema, "titleSummary", "profile summary unavailable", {
        version = tostring(context.version or ""),
        profile = callText(helpers.displayProfileName, "EK profile"),
        autosave = callText(helpers.autosaveText, "Autosave clean"),
        autosaveState = {
            profile_dirty = context.profile_dirty == true,
            ui_dirty = context.ui_dirty == true,
        },
    })
end

function OperatorSummary.healing(config, context)
    context = context or {}
    return moduleSummary(context.profileSchema, "healingSummary", "healing summary unavailable", config or {}, context.helpers or {})
end

function OperatorSummary.healFriend(config, context)
    context = context or {}
    return moduleSummary(context.healFriend, "summary", "Heal Friend module unavailable | runtime gated", config or {}, context.helpers or {})
end

function OperatorSummary.conditions(config, context)
    context = context or {}
    return moduleSummary(context.conditions, "summary", "Conditions module unavailable | read-only", config or {}, context.helpers or {})
end

function OperatorSummary.equipment(config, context)
    context = context or {}
    return moduleSummary(context.equipment, "summary", "Equipment module unavailable | read-only", config or {}, context.helpers or {})
end

function OperatorSummary.scripting(config, context)
    context = context or {}
    return moduleSummary(context.scripting, "summary", "Scripting module unavailable | runtime gated", config or {}, context.helpers or {})
end

function OperatorSummary.targeting(config, context)
    context = context or {}
    return moduleSummary(context.targeting, "configSummary", "targeting summary unavailable", config or {}, context.helpers or {})
end

function OperatorSummary.magic(config, context)
    context = context or {}
    return moduleSummary(context.combatRuntime, "magicSummary", "magic summary unavailable", config or {}, context.helpers or {})
end

function OperatorSummary.tools(config, context)
    context = context or {}
    local featureFlags = context.featureFlags
    local featureFlagAudit = context.featureFlagAudit
    if not featureFlagAudit and featureFlags and type(featureFlags.audit) == "function" then
        local ok, audit = pcall(featureFlags.audit, context.profile or {})
        if ok and type(audit) == "table" then
            featureFlagAudit = audit
        end
    end
    local helpers = context.helpers or {}
    helpers.audit = featureFlagAudit
    return moduleSummary(featureFlags, "toolsSummary", "tools summary unavailable", config or {}, helpers)
end

function OperatorSummary.profile(config, context)
    context = context or {}
    local schema = context.profileSchema
    local schemaText = moduleSummary(schema, "profileSchemaSuffix", "", context.profile or {})
    local helpers = context.helpers or {}
    helpers.schemaText = schemaText
    helpers.autosaveState = {
        profile_dirty = context.profile_dirty == true,
        ui_dirty = context.ui_dirty == true,
    }
    return moduleSummary(schema, "profileSummary", "profile summary unavailable", config or {}, helpers)
end

function OperatorSummary.ui(config, context)
    context = context or {}
    return moduleSummary(context.hud, "operatorSummary", "ui summary unavailable", config or {}, context.helpers or {})
end

function OperatorSummary.bridgeText(summaryName, bridges)
    local bridge = bridges and bridges[summaryName]
    if bridge and type(bridge.args) == "function" then
        local ok, first, second, third = pcall(bridge.args)
        if ok then
            return moduleSummary(OperatorSummary, summaryName, bridge.fallback or "summary unavailable", first, second, third)
        end
        return bridge.fallback or "summary unavailable"
    end
    return moduleSummary(OperatorSummary, summaryName, "summary unavailable")
end

function OperatorSummary.contract()
    return {
        module = "ctoa_helper_operator_summary",
        mode = "passive",
        owns_operator_summary_text = true,
        owns_profile_summary_bridge = true,
        owns_module_summary_bridge = true,
        owns_bridge_dispatch = true,
        creates_widgets = false,
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
        casts = false,
        talks = false,
        walks = false,
        uses_items = false,
        attacks = false,
        requires_module_static_gates = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_OPERATOR_SUMMARY = OperatorSummary
return OperatorSummary
