-- ctoa_helper_decision_trace.lua [CTOA OTClient Native]
-- Passive decision trace formatter for plan/policy/guard/queue review. It never writes logs or executes actions.

local DecisionTrace = rawget(_G, "CTOA_HELPER_DECISION_TRACE") or {}

local function copyList(source)
    local result = {}
    for index, value in ipairs(source or {}) do
        result[index] = tostring(value)
    end
    return result
end

local function missingGates(gates)
    local result = {}
    for name, ready in pairs(gates or {}) do
        if ready ~= true and ready ~= "passed" and ready ~= "ready" and ready ~= "approved" then
            result[#result + 1] = tostring(name)
        end
    end
    table.sort(result)
    return result
end

function DecisionTrace.record(plan, policy, guard, catalog)
    local actionPlan = plan or {}
    local policyDecision = policy or {}
    local guardDecision = guard or {}
    local catalogDecision = catalog or {}
    return {
        module_id = tostring(actionPlan.module_id or guardDecision.module_id or catalogDecision.domain or "unknown"),
        action = tostring(actionPlan.next_action or guardDecision.next_action or catalogDecision.action or "hold"),
        domain = tostring(guardDecision.domain or catalogDecision.domain or actionPlan.module_id or "unknown"),
        risk = tostring(catalogDecision.risk or "unknown"),
        plan_reason = tostring(actionPlan.reason or "no_reason"),
        policy_status = tostring(policyDecision.status or "missing_policy"),
        guard_status = tostring(guardDecision.status or "missing_guard"),
        policy_reasons = copyList(policyDecision.reasons),
        guard_reasons = copyList(guardDecision.reasons),
        missing_gates = missingGates(policyDecision.gates),
        runtime_action = actionPlan.runtime_actions == true or catalogDecision.runtime_action == true,
        dispatch_allowed = false,
        executes_plan = false,
    }
end

function DecisionTrace.queue(queue, limit)
    local result = {}
    local maxItems = tonumber(limit) or 5
    if maxItems < 1 then
        maxItems = 1
    end
    if maxItems > 20 then
        maxItems = 20
    end
    local source = queue or {}
    local startIndex = #source - maxItems + 1
    if startIndex < 1 then
        startIndex = 1
    end
    for index = startIndex, #source do
        local item = source[index] or {}
        result[#result + 1] = {
            module_id = tostring(item.module_id or "unknown"),
            action = tostring(item.next_action or "hold"),
            status = tostring(item.status or "unknown"),
            reason = tostring(item.reason or "no_reason"),
            dispatch_allowed = false,
            executes_plan = false,
        }
    end
    return result
end

function DecisionTrace.summary(trace)
    local item = trace or {}
    local policyReasons = item.policy_reasons or {}
    local guardReasons = item.guard_reasons or {}
    local missing = item.missing_gates or {}
    return "Decision trace " .. tostring(item.action or "hold") ..
        " | Policy " .. tostring(item.policy_status or "missing_policy") ..
        " | Guard " .. tostring(item.guard_status or "missing_guard") ..
        " | Reasons " .. tostring(#policyReasons + #guardReasons) ..
        " | Missing gates " .. tostring(#missing)
end

function DecisionTrace.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
        writes_logs = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
        traces_policy_reasons = true,
        traces_guard_reasons = true,
        traces_missing_gates = true,
        requires_runtime_policy = true,
        requires_dispatch_guard = true,
        requires_action_catalog = true,
    }
end

_G.CTOA_HELPER_DECISION_TRACE = DecisionTrace
return DecisionTrace
