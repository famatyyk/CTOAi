-- ctoa_helper_runtime_policy.lua [CTOA OTClient Native]
-- Passive runtime policy. It gates future dispatchers and never executes plans.

local RuntimePolicy = rawget(_G, "CTOA_HELPER_RUNTIME_POLICY") or {}

local REQUIRED_GATES = {
    "manifest_current",
    "module_static_gates",
    "module_attach_smoke",
    "smoke_attach_all",
    "live_approval"
}

local PROTECTION_ZONE_POLICY = {
    player_methods = {"isInPz", "isInProtectionZone", "isInSafeZone", "isProtected", "isPzLocked"},
    player_states = {
        globals = {"CreatureStateProtectionZone", "CreatureStatePz", "CreatureStateSafeZone"},
        literals = {"ProtectionZone", "Pz", "SafeZone"}
    },
    state_flags = {
        globals = {"CreatureStateProtectionZone", "CreatureStatePz", "CreatureStateSafeZone"},
        fallbacks = {16384}
    },
    tile_methods = {"isPz", "isProtectionZone", "isSafeZone"},
    tile_flags = {
        globals = {"TILESTATE_PROTECTIONZONE", "TileStateProtectionZone", "TileStatePz"},
        fallbacks = {1}
    },
    tile_has_flags = {
        globals = {"TILESTATE_PROTECTIONZONE", "TileStateProtectionZone", "TileStatePz"},
        literals = {"TILESTATE_PROTECTIONZONE", "TileStateProtectionZone", "ProtectionZone", "Pz"}
    }
}

local function boolValue(value)
    return value == true or value == "passed" or value == "ready" or value == "approved"
end

local function copyTable(value)
    if type(value) ~= "table" then
        return value
    end
    local result = {}
    for key, item in pairs(value) do
        result[key] = copyTable(item)
    end
    return result
end

local function globalValues(names)
    local values = {}
    for _, name in ipairs(names or {}) do
        values[#values + 1] = _G[name]
    end
    return values
end

local function policyStateValues(spec)
    local values = globalValues(spec and spec.globals or {})
    for _, value in ipairs(spec and spec.literals or {}) do
        values[#values + 1] = value
    end
    return values
end

local function collectNumericFlags(values, fallbacks)
    local flags = {}
    local seen = {}
    for _, value in ipairs(values or {}) do
        if type(value) == "number" and value > 0 and not seen[value] then
            flags[#flags + 1] = value
            seen[value] = true
        end
    end
    for _, value in ipairs(fallbacks or {}) do
        if type(value) == "number" and value > 0 and not seen[value] then
            flags[#flags + 1] = value
            seen[value] = true
        end
    end
    return flags
end

local function hasBitFlag(value, flag)
    if type(value) ~= "number" or type(flag) ~= "number" or flag <= 0 then
        return false
    end
    if bit32 and bit32.band then
        return bit32.band(value, flag) == flag
    end
    if bit and bit.band then
        return bit.band(value, flag) == flag
    end
    return value % (flag * 2) >= flag
end

local function gateValue(gates, name)
    if type(gates) ~= "table" then
        return false
    end
    return boolValue(gates[name])
end

local function append(list, value)
    list[#list + 1] = value
end

function RuntimePolicy.requiredGates()
    local result = {}
    for index, gate in ipairs(REQUIRED_GATES) do
        result[index] = gate
    end
    return result
end

function RuntimePolicy.protectionZonePolicy()
    return copyTable(PROTECTION_ZONE_POLICY)
end

function RuntimePolicy.resolvedProtectionZonePolicy()
    local policy = RuntimePolicy.protectionZonePolicy()
    policy.player_state_values = policyStateValues(policy.player_states)
    policy.state_flag_values = globalValues(policy.state_flags and policy.state_flags.globals or {})
    policy.state_flag_fallbacks = policy.state_flags and copyTable(policy.state_flags.fallbacks) or {}
    policy.tile_flag_values = globalValues(policy.tile_flags and policy.tile_flags.globals or {})
    policy.tile_flag_fallbacks = policy.tile_flags and copyTable(policy.tile_flags.fallbacks) or {}
    policy.tile_has_flag_values = policyStateValues(policy.tile_has_flags)
    return policy
end

function RuntimePolicy.protectionZoneDecision(observation)
    local data = observation or {}
    if data.player_method_hit == true or data.player_state_hit == true then
        return true
    end
    for _, flag in ipairs(collectNumericFlags(data.state_flag_values, data.state_flag_fallbacks)) do
        if hasBitFlag(data.player_states, flag) then
            return true
        end
    end
    if data.tile_method_hit == true or data.tile_has_flag_hit == true then
        return true
    end
    for _, flag in ipairs(collectNumericFlags(data.tile_flag_values, data.tile_flag_fallbacks)) do
        if hasBitFlag(data.tile_flags, flag) then
            return true
        end
    end
    return false
end

function RuntimePolicy.snapshot(gates)
    local result = {
        manifest_current = gateValue(gates, "manifest_current"),
        module_static_gates = gateValue(gates, "module_static_gates"),
        module_attach_smoke = gateValue(gates, "module_attach_smoke"),
        smoke_attach_all = gateValue(gates, "smoke_attach_all"),
        live_approval = gateValue(gates, "live_approval")
    }
    result.ready = (
        result.manifest_current and
        result.module_static_gates and
        result.module_attach_smoke and
        result.smoke_attach_all and
        result.live_approval
    )
    return result
end

function RuntimePolicy.decision(plan, gates)
    local actionPlan = plan or {}
    local snapshot = RuntimePolicy.snapshot(gates)
    local reasons = {}
    local runtimeAction = actionPlan.runtime_action == true
    if not snapshot.manifest_current then
        append(reasons, "manifest_not_current")
    end
    if not snapshot.module_static_gates then
        append(reasons, "module_static_gates_missing")
    end
    if not snapshot.module_attach_smoke then
        append(reasons, "module_attach_smoke_missing")
    end
    if not snapshot.smoke_attach_all then
        append(reasons, "smoke_attach_all_missing")
    end
    if not snapshot.live_approval then
        append(reasons, "live_approval_missing")
    end
    local status = "blocked"
    if actionPlan.next_action == "hold" or actionPlan.next_action == nil then
        status = "deferred"
    elseif #reasons == 0 and snapshot.ready then
        status = "ready"
    end
    return {
        status = status,
        next_action = tostring(actionPlan.next_action or "hold"),
        module_id = tostring(actionPlan.module_id or "unknown"),
        runtime_action = runtimeAction,
        planner_is_passive = actionPlan.runtime_actions ~= true,
        reasons = reasons,
        runtime_actions = false,
        executes_plan = false,
        gates = snapshot
    }
end

function RuntimePolicy.summary(decision)
    local item = decision or {}
    local reasons = item.reasons or {}
    return "Runtime policy " .. tostring(item.status or "blocked") ..
        " | Action " .. tostring(item.next_action or "hold") ..
        " | Reasons " .. tostring(#reasons)
end

function RuntimePolicy.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        executes_plans = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        owns_protection_zone_policy = true,
        owns_resolved_protection_zone_policy = true,
        owns_protection_zone_decision = true,
        requires_manifest_current = true,
        requires_module_static_gates = true,
        requires_module_attach_smoke = true,
        requires_smoke_attach_all = true,
        requires_live_approval = true
    }
end

_G.CTOA_HELPER_RUNTIME_POLICY = RuntimePolicy
return RuntimePolicy
