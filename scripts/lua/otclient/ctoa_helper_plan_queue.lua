-- ctoa_helper_plan_queue.lua [CTOA OTClient Native]
-- Passive plan queue. It stages guarded decisions for review and never dispatches them.

local PlanQueue = rawget(_G, "CTOA_HELPER_PLAN_QUEUE") or {}

local DEFAULT_LIMIT = 12

local function copyDecision(decision)
    local source = decision or {}
    local reasons = {}
    for index, reason in ipairs(source.reasons or {}) do
        reasons[index] = tostring(reason)
    end
    return {
        module_id = tostring(source.module_id or "unknown"),
        domain = tostring(source.domain or source.module_id or "unknown"),
        next_action = tostring(source.next_action or "hold"),
        status = tostring(source.status or "blocked"),
        reason = tostring(source.reason or "no_reason"),
        runtime_action = source.runtime_action == true,
        dispatch_allowed = false,
        executes_plan = false,
        reasons = reasons
    }
end

local function boundedLimit(limit)
    local value = tonumber(limit) or DEFAULT_LIMIT
    if value < 1 then
        return 1
    end
    if value > 50 then
        return 50
    end
    return math.floor(value)
end

function PlanQueue.normalize(decision)
    return copyDecision(decision)
end

function PlanQueue.enqueue(queue, decision, limit)
    local result = {}
    for _, item in ipairs(queue or {}) do
        result[#result + 1] = copyDecision(item)
    end
    result[#result + 1] = copyDecision(decision)
    local maxItems = boundedLimit(limit)
    while #result > maxItems do
        table.remove(result, 1)
    end
    return result
end

function PlanQueue.trim(queue, limit)
    local result = {}
    local maxItems = boundedLimit(limit)
    for _, item in ipairs(queue or {}) do
        result[#result + 1] = copyDecision(item)
        while #result > maxItems do
            table.remove(result, 1)
        end
    end
    return result
end

function PlanQueue.summary(queue)
    local list = queue or {}
    local latest = list[#list] or {}
    return "Plan queue " .. tostring(#list) ..
        " | Latest " .. tostring(latest.next_action or "hold") ..
        " | Status " .. tostring(latest.status or "none")
end

function PlanQueue.contract()
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
        stores_decisions_only = true,
        bounded_queue = true,
        requires_planner = true,
        requires_dispatch_guard = true,
        requires_sandbox_attach = true
    }
end

_G.CTOA_HELPER_PLAN_QUEUE = PlanQueue
return PlanQueue
