-- ctoa_helper_runtime_readiness.lua [CTOA OTClient Native]
-- Passive readiness summary for future runtime bridges. It never executes plans.

local RuntimeReadiness = rawget(_G, "CTOA_HELPER_RUNTIME_READINESS") or {}

local REQUIRED_COMPONENTS = {
    "planner",
    "runtime_policy",
    "dispatch_guard",
    "plan_queue",
}

local REQUIRED_GATES = {
    "manifest_current",
    "module_static_gates",
    "module_attach_smoke",
    "smoke_attach_all",
    "live_approval",
}

local function append(list, value)
    list[#list + 1] = value
end

local function truthy(value)
    return value == true or value == "passed" or value == "ready" or value == "approved"
end

local function componentReady(components, name)
    if type(components) ~= "table" then
        return false
    end
    return truthy(components[name])
end

local function gateReady(gates, name)
    if type(gates) ~= "table" then
        return false
    end
    return truthy(gates[name])
end

function RuntimeReadiness.requiredComponents()
    local result = {}
    for index, name in ipairs(REQUIRED_COMPONENTS) do
        result[index] = name
    end
    return result
end

function RuntimeReadiness.requiredGates()
    local result = {}
    for index, name in ipairs(REQUIRED_GATES) do
        result[index] = name
    end
    return result
end

function RuntimeReadiness.snapshot(components, gates)
    local missing = {}
    local readyComponents = {}
    local readyGates = {}
    for _, name in ipairs(REQUIRED_COMPONENTS) do
        local ready = componentReady(components, name)
        readyComponents[name] = ready
        if not ready then
            append(missing, "component_" .. name)
        end
    end
    for _, name in ipairs(REQUIRED_GATES) do
        local ready = gateReady(gates, name)
        readyGates[name] = ready
        if not ready then
            append(missing, "gate_" .. name)
        end
    end
    return {
        status = #missing == 0 and "ready" or "blocked",
        components = readyComponents,
        gates = readyGates,
        missing = missing,
        runtime_actions = false,
        executes_plan = false,
    }
end

function RuntimeReadiness.decision(snapshot, queue)
    local item = snapshot or {}
    local queued = queue or {}
    local latest = queued[#queued] or {}
    local missing = item.missing or {}
    local status = "blocked"
    if item.status == "ready" and latest.next_action ~= nil and latest.next_action ~= "hold" then
        status = "review_ready"
    elseif item.status == "ready" then
        status = "idle_ready"
    end
    return {
        status = status,
        latest_action = tostring(latest.next_action or "hold"),
        latest_module = tostring(latest.module_id or "unknown"),
        missing = missing,
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
    }
end

function RuntimeReadiness.summary(decision)
    local item = decision or {}
    local missing = item.missing or {}
    return "Runtime readiness " .. tostring(item.status or "blocked") ..
        " | Latest " .. tostring(item.latest_action or "hold") ..
        " | Missing " .. tostring(#missing)
end

function RuntimeReadiness.contract()
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
        requires_planner = true,
        requires_runtime_policy = true,
        requires_dispatch_guard = true,
        requires_plan_queue = true,
        requires_module_attach_smoke = true,
        requires_smoke_attach_all = true,
        requires_live_approval = true,
    }
end

_G.CTOA_HELPER_RUNTIME_READINESS = RuntimeReadiness
return RuntimeReadiness
