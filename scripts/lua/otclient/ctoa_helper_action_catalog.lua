-- ctoa_helper_action_catalog.lua [CTOA OTClient Native]
-- Passive action capability catalog. It classifies future runtime actions and never executes them.

local ActionCatalog = rawget(_G, "CTOA_HELPER_ACTION_CATALOG") or {}

local REQUIRED_RUNTIME_GATES = {
    "manifest_current",
    "module_static_gates",
    "module_attach_smoke",
    "smoke_attach_all",
    "live_approval",
}

local ACTIONS = {
    {
        action = "plan_heal",
        domain = "recovery",
        risk = "runtime_recovery",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_attack",
        domain = "combat",
        risk = "runtime_combat",
        requires_target = true,
        runtime_action = true,
    },
    {
        action = "plan_spell",
        domain = "combat",
        risk = "runtime_cast",
        requires_target = true,
        runtime_action = true,
    },
    {
        action = "plan_rune",
        domain = "combat",
        risk = "runtime_item_use",
        requires_target = true,
        runtime_action = true,
    },
    {
        action = "plan_walk",
        domain = "cavebot",
        risk = "runtime_movement",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_loot",
        domain = "loot",
        risk = "runtime_item_move",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_timer",
        domain = "timer",
        risk = "runtime_talk_or_cast",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_sio",
        domain = "heal_friend",
        risk = "runtime_cast",
        requires_target = true,
        runtime_action = true,
    },
    {
        action = "plan_paralyze_recovery",
        domain = "conditions",
        risk = "runtime_recovery",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_poison_recovery",
        domain = "conditions",
        risk = "runtime_recovery",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_burn_recovery",
        domain = "conditions",
        risk = "runtime_recovery",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_energy_recovery",
        domain = "conditions",
        risk = "runtime_recovery",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_bleed_recovery",
        domain = "conditions",
        risk = "runtime_recovery",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_ring_swap",
        domain = "equipment",
        risk = "runtime_equipment",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "plan_amulet_swap",
        domain = "equipment",
        risk = "runtime_equipment",
        requires_target = false,
        runtime_action = true,
    },
    {
        action = "audit_only",
        domain = "scripting",
        risk = "passive_audit",
        requires_target = false,
        runtime_action = false,
    },
    {
        action = "policy_review",
        domain = "scripting",
        risk = "passive_policy",
        requires_target = false,
        runtime_action = false,
    },
    {
        action = "hold",
        domain = "system",
        risk = "passive_hold",
        requires_target = false,
        runtime_action = false,
    },
}

local function copyList(source)
    local result = {}
    for index, value in ipairs(source or {}) do
        result[index] = tostring(value)
    end
    return result
end

local function copyAction(action)
    local item = action or {}
    return {
        action = tostring(item.action or "hold"),
        domain = tostring(item.domain or "unknown"),
        risk = tostring(item.risk or "unknown"),
        requires_target = item.requires_target == true,
        runtime_action = item.runtime_action == true,
        required_gates = copyList(REQUIRED_RUNTIME_GATES),
        dispatch_allowed = false,
        executes_plan = false,
    }
end

function ActionCatalog.requiredGates()
    return copyList(REQUIRED_RUNTIME_GATES)
end

function ActionCatalog.all()
    local result = {}
    for index, action in ipairs(ACTIONS) do
        result[index] = copyAction(action)
    end
    return result
end

function ActionCatalog.domains()
    local result = {}
    local seen = {}
    for _, action in ipairs(ACTIONS) do
        if not seen[action.domain] then
            result[#result + 1] = action.domain
            seen[action.domain] = true
        end
    end
    return result
end

function ActionCatalog.byAction(actionName)
    local name = tostring(actionName or "hold")
    for _, action in ipairs(ACTIONS) do
        if action.action == name then
            return copyAction(action)
        end
    end
    return {
        action = name,
        domain = "unknown",
        risk = "unknown",
        requires_target = false,
        runtime_action = false,
        required_gates = copyList(REQUIRED_RUNTIME_GATES),
        dispatch_allowed = false,
        executes_plan = false,
    }
end

function ActionCatalog.classify(plan)
    local item = plan or {}
    local catalog = ActionCatalog.byAction(item.next_action or "hold")
    catalog.module_id = tostring(item.module_id or catalog.domain)
    catalog.weight = tonumber(item.weight) or 0
    catalog.reason = tostring(item.reason or "no_reason")
    return catalog
end

function ActionCatalog.summary(classified)
    local item = classified or {}
    return "Action catalog " .. tostring(item.action or "hold") ..
        " | Domain " .. tostring(item.domain or "unknown") ..
        " | Risk " .. tostring(item.risk or "unknown")
end

function ActionCatalog.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
        catalogs_action_risk = true,
        requires_manifest_current = true,
        requires_module_static_gates = true,
        requires_module_attach_smoke = true,
        requires_smoke_attach_all = true,
        requires_live_approval = true,
    }
end

_G.CTOA_HELPER_ACTION_CATALOG = ActionCatalog
return ActionCatalog
