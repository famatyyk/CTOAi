-- ctoa_helper_decision_pipeline.lua [CTOA OTClient Native]
-- Passive end-to-end decision coordinator. It never invokes runtime adapters.

local DecisionPipeline = rawget(_G, "CTOA_HELPER_DECISION_PIPELINE") or {}

local Planner = rawget(_G, "CTOA_HELPER_PLANNER")
local RuntimePolicy = rawget(_G, "CTOA_HELPER_RUNTIME_POLICY")
local DispatchGuard = rawget(_G, "CTOA_HELPER_DISPATCH_GUARD")
local PlanQueue = rawget(_G, "CTOA_HELPER_PLAN_QUEUE")
local RuntimeReadiness = rawget(_G, "CTOA_HELPER_RUNTIME_READINESS")
local ActionCatalog = rawget(_G, "CTOA_HELPER_ACTION_CATALOG")
local DecisionTrace = rawget(_G, "CTOA_HELPER_DECISION_TRACE")

local REQUIRED_COMPONENTS = {
    planner = Planner,
    runtime_policy = RuntimePolicy,
    dispatch_guard = DispatchGuard,
    plan_queue = PlanQueue,
    runtime_readiness = RuntimeReadiness,
    action_catalog = ActionCatalog,
    decision_trace = DecisionTrace,
}

local function componentReady(module, functionName)
    return type(module) == "table" and type(module[functionName]) == "function"
end

local function copyTable(source)
    local result = {}
    for key, value in pairs(source or {}) do
        result[key] = value
    end
    return result
end

local function componentsSnapshot()
    return {
        planner = componentReady(Planner, "collect"),
        runtime_policy = componentReady(RuntimePolicy, "decision"),
        dispatch_guard = componentReady(DispatchGuard, "decision"),
        plan_queue = componentReady(PlanQueue, "enqueue"),
    }
end

local function missingComponents()
    local missing = {}
    for name, module in pairs(REQUIRED_COMPONENTS) do
        if type(module) ~= "table" then
            missing[#missing + 1] = name
        end
    end
    table.sort(missing)
    return missing
end

local function adapterHandoff(selected, catalog, guard)
    local classified = catalog or {}
    local decision = guard or {}
    local domain = tostring(classified.domain or selected.module_id or "unknown")
    return {
        adapter_id = domain .. "_runtime",
        domain = domain,
        action = tostring(classified.action or selected.next_action or "hold"),
        risk = tostring(classified.risk or "unknown"),
        status = decision.status == "ready" and "review_ready" or "blocked",
        guard_status = tostring(decision.status or "missing_guard"),
        dispatch_allowed = false,
        executes_plan = false,
        runtime_actions = false,
    }
end

function DecisionPipeline.components()
    return componentsSnapshot()
end

function DecisionPipeline.evaluate(entries, state)
    local ctx = state or {}
    local missing = missingComponents()
    if #missing > 0 then
        return {
            status = "missing_components",
            missing_components = missing,
            queue = copyTable(ctx.queue),
            dispatch_allowed = false,
            executes_plan = false,
            runtime_actions = false,
        }
    end

    local plans = Planner.collect(entries or {}, ctx.context or {})
    local selected = Planner.best(plans)
    local catalog = ActionCatalog.classify(selected)
    local policyInput = copyTable(selected)
    policyInput.runtime_action = catalog.runtime_action == true
    local policy = RuntimePolicy.decision(policyInput, ctx.gates or {})
    local guard = DispatchGuard.decision(selected, policy, {
        runtime_enabled = ctx.runtime_enabled == true,
        sandbox_attach_ready = ctx.sandbox_attach_ready == true,
    })
    local queue = PlanQueue.enqueue(ctx.queue or {}, guard, ctx.queue_limit)
    local readinessSnapshot = RuntimeReadiness.snapshot(componentsSnapshot(), ctx.gates or {})
    local readiness = RuntimeReadiness.decision(readinessSnapshot, queue)
    local trace = DecisionTrace.record(selected, policy, guard, catalog)
    local handoff = adapterHandoff(selected, catalog, guard)

    return {
        status = handoff.status,
        plans = plans,
        selected = selected,
        catalog = catalog,
        policy = policy,
        guard = guard,
        queue = queue,
        readiness = readiness,
        trace = trace,
        adapter_handoff = handoff,
        dispatch_allowed = false,
        executes_plan = false,
        runtime_actions = false,
    }
end

function DecisionPipeline.summary(result)
    local item = result or {}
    local handoff = item.adapter_handoff or {}
    local blockers = DecisionPipeline.blockers(item)
    local status = item.status or (item.adapter_handoff and "blocked" or "idle")
    return "Decision pipeline " .. tostring(status) ..
        " | Adapter " .. tostring(handoff.adapter_id or "none") ..
        " | Action " .. tostring(handoff.action or "hold") ..
        " | Guard " .. tostring(handoff.guard_status or "missing") ..
        " | Blockers " .. tostring(#blockers)
end

function DecisionPipeline.blockers(result)
    local item = result or {}
    local blockers = {}
    local seen = {}
    local function append(values)
        for _, value in ipairs(values or {}) do
            local text = tostring(value)
            if not seen[text] then
                blockers[#blockers + 1] = text
                seen[text] = true
            end
        end
    end
    append(item.missing_components)
    append(item.policy and item.policy.reasons)
    append(item.guard and item.guard.reasons)
    append(item.readiness and item.readiness.missing)
    return blockers
end

function DecisionPipeline.contract()
    return {
        module = "ctoa_helper_decision_pipeline",
        mode = "passive",
        owns_end_to_end_decision_flow = true,
        owns_adapter_handoff = true,
        owns_operator_blockers = true,
        requires_planner = true,
        requires_runtime_policy = true,
        requires_dispatch_guard = true,
        requires_plan_queue = true,
        requires_runtime_readiness = true,
        requires_action_catalog = true,
        requires_decision_trace = true,
        invokes_adapters = false,
        dispatch_allowed = false,
        executes_plan = false,
        runtime_actions = false,
    }
end

_G.CTOA_HELPER_DECISION_PIPELINE = DecisionPipeline
return DecisionPipeline
