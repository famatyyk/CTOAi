-- ctoa_helper_planner.lua [CTOA OTClient Native]
-- Passive planner coordinator. It ranks module plans and never executes them.

local Planner = rawget(_G, "CTOA_HELPER_PLANNER") or {}
local externalDomainContract = rawget(_G, "CTOA_HELPER_DOMAIN_CONTRACT")

local ACTION_WEIGHT = {
    hold = 0,
    policy_review = 1,
    audit_only = 1,
    plan_sio = 2,
    plan_paralyze_recovery = 2,
    plan_poison_recovery = 2,
    plan_burn_recovery = 2,
    plan_energy_recovery = 2,
    plan_bleed_recovery = 2,
    plan_ring_swap = 2,
    plan_amulet_swap = 2,
    plan_attack = 3,
    plan_spell = 3,
    plan_rune = 3,
    plan_walk = 3,
    plan_loot = 3,
    plan_timer = 3
}

local function weightFor(plan)
    if type(plan) ~= "table" then
        return 0
    end
    return ACTION_WEIGHT[tostring(plan.next_action or "hold")] or 0
end

local function domainValue(functionName, ...)
    if type(externalDomainContract) ~= "table" or type(externalDomainContract[functionName]) ~= "function" then
        return nil
    end
    local ok, result = pcall(externalDomainContract[functionName], ...)
    if ok then
        return result
    end
    return nil
end

local function normalizedPlan(moduleId, plan, observation, context)
    local result = {}
    if type(plan) == "table" then
        for key, value in pairs(plan) do
            result[key] = value
        end
    end
    result.module_id = tostring(moduleId or result.module_id or "unknown")
    result.next_action = tostring(result.next_action or "hold")
    result.reason = tostring(result.reason or "no_reason")
    result.runtime_actions = false
    result.weight = weightFor(result)
    local enveloped = domainValue("planEnvelope", result.module_id, result)
    if type(enveloped) == "table" then
        result = enveloped
        result.weight = weightFor(result)
    end
    local ctx = context or {}
    local observationEnvelope = domainValue(
        "observationEnvelope",
        result.module_id,
        observation or {},
        ctx.now or ctx.observed_at or 0
    )
    if type(observationEnvelope) == "table" then
        result.observation_envelope = observationEnvelope
    end
    return result
end

function Planner.collect(entries, context)
    local plans = {}
    local ctx = context or {}
    for _, entry in ipairs(entries or {}) do
        local module = entry.module
        if module and type(module.plan) == "function" then
            local ok, plan = pcall(module.plan, entry.config or {}, entry.observation or {}, entry.context or ctx)
            if ok then
                plans[#plans + 1] = normalizedPlan(entry.id, plan, entry.observation, entry.context or ctx)
            else
                plans[#plans + 1] = normalizedPlan(entry.id, {
                    next_action = "hold",
                    reason = "planner_error"
                }, entry.observation, entry.context or ctx)
            end
        else
            plans[#plans + 1] = normalizedPlan(entry.id, {
                next_action = "hold",
                reason = "missing_plan"
            }, entry.observation, entry.context or ctx)
        end
    end
    table.sort(plans, function(left, right)
        if left.weight == right.weight then
            return tostring(left.module_id) < tostring(right.module_id)
        end
        return left.weight > right.weight
    end)
    return plans
end

function Planner.best(plans)
    for _, plan in ipairs(plans or {}) do
        if plan.next_action ~= "hold" then
            return plan
        end
    end
    return (plans or {})[1] or normalizedPlan("none", {
        next_action = "hold",
        reason = "no_plans"
    }, {}, {})
end

function Planner.summary(plans)
    local list = plans or {}
    local best = Planner.best(list)
    return "Plans " .. tostring(#list) ..
        " | Next " .. tostring(best.next_action or "hold") ..
        " | Module " .. tostring(best.module_id or "none") ..
        " | Reason " .. tostring(best.reason or "no_reason")
end

function Planner.summaryEnvelope(plans)
    local list = plans or {}
    local best = Planner.best(list)
    local state = best.next_action == "hold" and "idle" or "planned"
    local envelope = domainValue("summaryEnvelope", best.module_id, state, Planner.summary(list))
    if type(envelope) == "table" then
        return envelope
    end
    return {
        kind = "summary",
        lane = tostring(best.module_id or "unknown"),
        state = state,
        text = Planner.summary(list),
        runtime_actions = false,
    }
end

function Planner.contract()
    return {
        mode = "passive",
        domain_contract_version = "ctoa-helper-domain-v1",
        owns_domain_plan_normalization = true,
        owns_observation_envelope_handoff = true,
        owns_summary_envelope = true,
        runtime_actions = false,
        executes_plans = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        requires_sandbox_attach = true
    }
end

_G.CTOA_HELPER_PLANNER = Planner
return Planner
