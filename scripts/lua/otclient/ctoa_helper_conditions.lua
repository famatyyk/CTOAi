-- ctoa_helper_conditions.lua [CTOA OTClient Native]
-- Read-only condition observer domain. It never casts, talks, or uses items.

local Conditions = rawget(_G, "CTOA_HELPER_CONDITIONS") or {}

local function boolText(value)
    return value and "yes" or "no"
end

local function hasBitFlag(value, flag)
    if type(value) ~= "number" or type(flag) ~= "number" then
        return false
    end
    if bit32 and bit32.band then
        return bit32.band(value, flag) ~= 0
    end
    if bit and bit.band then
        return bit.band(value, flag) ~= 0
    end
    return value % (flag * 2) >= flag
end

local function collectNumericFlags(candidates)
    local flags = {}
    for _, candidate in ipairs(candidates or {}) do
        if type(candidate) == "number" then
            flags[#flags + 1] = candidate
        end
    end
    return flags
end

function Conditions.flagText(player, label, enabled, candidates, ctx)
    ctx = ctx or {}
    if not enabled then
        return label .. ":off"
    end
    if not player then
        return label .. ":?"
    end
    if ctx.hasAnyState and ctx.hasAnyState(player, "hasState", candidates or {}) then
        return label .. ":yes"
    end
    local states = ctx.pcallNumber and ctx.pcallNumber(player, "getStates") or nil
    for _, flag in ipairs(collectNumericFlags(candidates or {})) do
        if hasBitFlag(states, flag) then
            return label .. ":yes"
        end
    end
    return label .. ":no"
end

function Conditions.snapshot(config, ctx)
    ctx = ctx or {}
    local conditions = config or {}
    local player = ctx.getLocalPlayer and ctx.getLocalPlayer() or nil
    local parts = {
        Conditions.flagText(player, "shield", conditions.mana_shield, {
            _G.CreatureStateManaShield,
            _G.CreatureStateMagicShield,
            "ManaShield",
            "MagicShield"
        }, ctx),
        Conditions.flagText(player, "para", conditions.paralyze, {
            _G.CreatureStateParalyze,
            _G.CreatureStateSlowed,
            "Paralyze",
            "Slowed"
        }, ctx),
        Conditions.flagText(player, "poison", conditions.poison, {
            _G.CreatureStatePoison,
            "Poison"
        }, ctx),
        Conditions.flagText(player, "burn", conditions.burn, {
            _G.CreatureStateBurn,
            _G.CreatureStateFire,
            "Burn",
            "Fire"
        }, ctx),
        Conditions.flagText(player, "shock", conditions.electric, {
            _G.CreatureStateEnergy,
            _G.CreatureStateElectric,
            "Energy",
            "Electric"
        }, ctx),
        Conditions.flagText(player, "bleed", conditions.bleeding, {
            _G.CreatureStateBleeding,
            "Bleeding"
        }, ctx)
    }
    return table.concat(parts, " | ")
end

function Conditions.apiProbe(config, ctx)
    ctx = ctx or {}
    local conditions = config or {}
    if conditions.api_probe_enabled == false then
        conditions.api_probe_status = "api probe off"
        return conditions.api_probe_status
    end
    conditions.api_probe_count = (conditions.api_probe_count or 0) + 1
    local player = ctx.getLocalPlayer and ctx.getLocalPlayer() or nil
    local states = ctx.pcallNumber and ctx.pcallNumber(player, "getStates") or nil
    local parts = {
        "player.hasState=" .. boolText(player and player.hasState),
        "player.getStates=" .. boolText(player and player.getStates),
        "states=" .. tostring(states or "?"),
        "state.manaShield=" .. boolText(_G.CreatureStateManaShield or _G.CreatureStateMagicShield),
        "state.paralyze=" .. boolText(_G.CreatureStateParalyze or _G.CreatureStateSlowed),
        "state.poison=" .. boolText(_G.CreatureStatePoison),
        "state.burn=" .. boolText(_G.CreatureStateBurn or _G.CreatureStateFire),
        "state.energy=" .. boolText(_G.CreatureStateEnergy or _G.CreatureStateElectric),
        "state.bleeding=" .. boolText(_G.CreatureStateBleeding)
    }
    conditions.api_probe_status = table.concat(parts, " ")
    return conditions.api_probe_status
end

function Conditions.observe(config, now, ctx)
    ctx = ctx or {}
    local conditions = config or {}
    if not conditions.enabled or not conditions.observe_states then
        return false
    end
    if now - (conditions.last_sample_ms or 0) < (conditions.sample_interval_ms or 1000) then
        return false
    end
    conditions.last_sample_ms = now
    conditions.last_status = Conditions.snapshot(conditions, ctx) .. " | " .. Conditions.apiProbe(conditions, ctx)
    return true
end

function Conditions.plan(config, observation, context)
    local conditions = config or {}
    local observed = observation or {}
    local ctx = context or {}
    local plan = {
        next_action = "hold",
        reason = "planner_disabled",
        runtime_actions = false
    }
    if not conditions.enabled then
        return plan
    end
    if conditions.runtime_enabled ~= true or ctx.runtime_allowed ~= true then
        plan.reason = "runtime_gated"
        return plan
    end
    if ctx.in_protection_zone == true then
        plan.reason = "protection_zone"
        return plan
    end
    local cures = {
        {key = "paralyze", observed = "paralyzed", action = "plan_paralyze_recovery"},
        {key = "poison", observed = "poisoned", action = "plan_poison_recovery"},
        {key = "burn", observed = "burning", action = "plan_burn_recovery"},
        {key = "electric", observed = "shocked", action = "plan_energy_recovery"},
        {key = "bleeding", observed = "bleeding", action = "plan_bleed_recovery"}
    }
    for _, cure in ipairs(cures) do
        if conditions[cure.key] == true and observed[cure.observed] == true then
            plan.next_action = cure.action
            plan.reason = "condition_detected"
            plan.condition = cure.key
            return plan
        end
    end
    plan.reason = "no_recovery_condition"
    return plan
end

function Conditions.summary(config, helpers)
    helpers = helpers or {}
    local conditions = config or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local runtimeText = conditions.runtime_enabled and "runtime ON" or "read-only"
    local planText = conditions.runtime_enabled and "planner gated" or "planner passive"
    return "Observer " .. onOffText(conditions.enabled == true) ..
        " | States " .. onOffText(conditions.observe_states == true) ..
        " | API " .. onOffText(conditions.api_probe_enabled ~= false) ..
        " | " .. runtimeText ..
        " | " .. planText ..
        " | " .. tostring(conditions.last_status or "pending")
end

function Conditions.contract()
    return {
        mode = "passive",
        owns_flag_text = true,
        owns_snapshot = true,
        owns_api_probe = true,
        owns_observer = true,
        owns_summary_text = true,
        runtime_actions = false,
        casts = false,
        uses_items = false,
        talks = false,
        requires_runtime_gate = true,
        requires_sandbox_attach = true
    }
end

_G.CTOA_HELPER_CONDITIONS = Conditions
return Conditions
