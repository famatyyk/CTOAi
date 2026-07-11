-- ctoa_helper_dispatch_guard.lua [CTOA OTClient Native]
-- Passive dispatch guard. It validates ranked plans against runtime policy without executing them.

local DispatchGuard = rawget(_G, "CTOA_HELPER_DISPATCH_GUARD") or {}

local ACTION_DOMAIN = {
    plan_heal = "recovery",
    plan_attack = "combat",
    plan_spell = "combat",
    plan_rune = "combat",
    plan_walk = "cavebot",
    plan_loot = "loot",
    plan_timer = "timer",
    plan_sio = "heal_friend",
    plan_paralyze_recovery = "conditions",
    plan_poison_recovery = "conditions",
    plan_burn_recovery = "conditions",
    plan_energy_recovery = "conditions",
    plan_bleed_recovery = "conditions",
    plan_ring_swap = "equipment",
    plan_amulet_swap = "equipment",
    audit_only = "scripting",
    policy_review = "scripting",
}

local function append(list, value)
    list[#list + 1] = value
end

local function isRuntimeAction(action)
    local name = tostring(action or "hold")
    return name ~= "hold" and name ~= "audit_only" and name ~= "policy_review"
end

local function policyStatus(policy)
    if type(policy) ~= "table" then
        return "missing_policy"
    end
    return tostring(policy.status or "blocked")
end

local function hasPolicyReady(policy)
    return policyStatus(policy) == "ready"
end

local function planModule(plan)
    if type(plan) ~= "table" then
        return "unknown"
    end
    return tostring(plan.module_id or ACTION_DOMAIN[tostring(plan.next_action or "hold")] or "unknown")
end

function DispatchGuard.classify(plan)
    local item = plan or {}
    local action = tostring(item.next_action or "hold")
    return {
        module_id = planModule(item),
        next_action = action,
        domain = ACTION_DOMAIN[action] or planModule(item),
        runtime_action = isRuntimeAction(action),
        weight = tonumber(item.weight) or 0,
        reason = tostring(item.reason or "no_reason")
    }
end

function DispatchGuard.decision(plan, policy, context)
    local classified = DispatchGuard.classify(plan)
    local ctx = context or {}
    local reasons = {}
    if classified.next_action == "hold" then
        append(reasons, "hold_action")
    end
    if ctx.runtime_enabled ~= true then
        append(reasons, "runtime_disabled")
    end
    if classified.runtime_action and not hasPolicyReady(policy) then
        append(reasons, "policy_not_ready")
    end
    if policyStatus(policy) == "deferred" then
        append(reasons, "policy_deferred")
    end
    if classified.runtime_action and ctx.sandbox_attach_ready ~= true then
        append(reasons, "sandbox_attach_required")
    end
    local status = "blocked"
    if classified.next_action == "hold" then
        status = "deferred"
    elseif not classified.runtime_action and #reasons == 0 then
        status = "observe"
    elseif #reasons == 0 then
        status = "ready"
    end
    return {
        status = status,
        module_id = classified.module_id,
        domain = classified.domain,
        next_action = classified.next_action,
        runtime_action = classified.runtime_action,
        dispatch_allowed = false,
        executes_plan = false,
        reasons = reasons
    }
end

function DispatchGuard.summary(decision)
    local item = decision or {}
    local reasons = item.reasons or {}
    return "Dispatch guard " .. tostring(item.status or "blocked") ..
        " | Action " .. tostring(item.next_action or "hold") ..
        " | Domain " .. tostring(item.domain or "unknown") ..
        " | Reasons " .. tostring(#reasons)
end

function DispatchGuard.contract()
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
        requires_runtime_policy = true,
        requires_sandbox_attach = true,
        requires_live_approval = true
    }
end

_G.CTOA_HELPER_DISPATCH_GUARD = DispatchGuard
return DispatchGuard
