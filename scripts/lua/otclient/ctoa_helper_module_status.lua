-- ctoa_helper_module_status.lua [CTOA OTClient Native]
-- Passive module status board. It summarizes helper module readiness and never executes actions.

local ModuleStatus = rawget(_G, "CTOA_HELPER_MODULE_STATUS") or {}

local DEFAULT_ORDER = {
    "modules",
    "diagnostics",
    "client_reporter",
    "hotkeys",
    "modal",
    "route",
    "targeting",
    "combat_runtime",
    "cavebot_runtime",
    "loot_runtime",
    "timer_runtime",
    "profile_schema",
    "planner",
    "runtime_policy",
    "dispatch_guard",
    "runtime_module_gate",
    "plan_queue",
    "runtime_readiness",
    "action_catalog",
    "decision_trace",
    "sandbox_handoff",
    "feature_flags",
    "hud",
    "conditions",
    "conditions_runtime_gate",
    "equipment",
    "equipment_runtime_gate",
    "heal_friend",
    "heal_friend_runtime_gate",
    "scripting",
}

local function copyList(source)
    local result = {}
    for index, value in ipairs(source or {}) do
        result[index] = tostring(value)
    end
    return result
end

local function truthy(value)
    return value == true or value == "passed" or value == "ready" or value == "extracted"
end

local function moduleStatus(module)
    local item = module or {}
    if truthy(item.ready) or truthy(item.status) then
        return "ready"
    end
    if item.status == "blocked" or item.blocked == true then
        return "blocked"
    end
    if item.status == "missing" or item.missing == true then
        return "missing"
    end
    return tostring(item.status or "unknown")
end

local function normalizeOne(moduleId, module)
    local item = module or {}
    local status = moduleStatus(item)
    return {
        module_id = tostring(item.module_id or item.id or moduleId or "unknown"),
        lane_id = tostring(item.lane_id or item.lane or item.domain or ""),
        status = status,
        gate = tostring(item.gate or item.required_gate or ""),
        evidence = tostring(item.evidence or item.report or ""),
        next_action = tostring(item.next_action or item.next_step or "hold"),
        ready = status == "ready",
        runtime_actions = false,
        executes_plan = false,
        dispatch_allowed = false,
    }
end

function ModuleStatus.defaultOrder()
    return copyList(DEFAULT_ORDER)
end

function ModuleStatus.normalize(modules, order)
    local result = {}
    local seen = {}
    local source = modules or {}
    local moduleOrder = order or DEFAULT_ORDER
    for _, moduleId in ipairs(moduleOrder) do
        local normalized = normalizeOne(moduleId, source[moduleId])
        result[#result + 1] = normalized
        seen[normalized.module_id] = true
    end
    for moduleId, module in pairs(source) do
        if not seen[tostring(moduleId)] then
            result[#result + 1] = normalizeOne(moduleId, module)
        end
    end
    return result
end

function ModuleStatus.snapshot(modules, order)
    local rows = ModuleStatus.normalize(modules, order)
    local counts = {
        total = #rows,
        ready = 0,
        blocked = 0,
        missing = 0,
        unknown = 0,
    }
    local blockers = {}
    for _, row in ipairs(rows) do
        if row.status == "ready" then
            counts.ready = counts.ready + 1
        elseif row.status == "blocked" then
            counts.blocked = counts.blocked + 1
            blockers[#blockers + 1] = row.module_id
        elseif row.status == "missing" then
            counts.missing = counts.missing + 1
            blockers[#blockers + 1] = row.module_id
        else
            counts.unknown = counts.unknown + 1
            blockers[#blockers + 1] = row.module_id
        end
    end
    return {
        status = #blockers == 0 and "ready" or "blocked",
        counts = counts,
        blockers = blockers,
        modules = rows,
        runtime_actions = false,
        executes_plan = false,
    }
end

function ModuleStatus.summary(snapshot)
    local item = snapshot or {}
    local counts = item.counts or {}
    return "Module status " .. tostring(item.status or "blocked") ..
        " | Ready " .. tostring(counts.ready or 0) .. "/" .. tostring(counts.total or 0) ..
        " | Blockers " .. tostring(#(item.blockers or {}))
end

function ModuleStatus.contract()
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
        normalizes_module_status = true,
        exposes_status_board = true,
        requires_module_contract = true,
        requires_module_static_gates = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_MODULE_STATUS = ModuleStatus
return ModuleStatus
