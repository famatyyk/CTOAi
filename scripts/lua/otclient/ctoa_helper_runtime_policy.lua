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

local ACTION_SAFETY_GATES = {
    plan_paralyze_recovery = "conditions_runtime_gate",
    plan_ring_swap = "equipment_runtime_gate",
    plan_sio = "heal_friend_runtime_gate",
}

local ACTION_SAFETY_GATE_SCHEMAS = {
    plan_paralyze_recovery = "ctoa.conditions-runtime-safety-gate.v1",
    plan_ring_swap = "ctoa.equipment-runtime-safety-gate.v1",
    plan_sio = "ctoa.heal-friend-runtime-safety-gate.v1",
}

local DEFERRED_MODULE_SCOPE_ACTIONS = {
    plan_poison_recovery = true,
    plan_burn_recovery = true,
    plan_energy_recovery = true,
    plan_bleed_recovery = true,
    plan_amulet_swap = true,
}

local DEFERRED_HIGH_RISK_ACTIONS = {
    plan_attack = true,
    plan_spell = true,
    plan_rune = true,
    plan_walk = true,
}

local PASSIVE_ACTIONS = {
    hold = true,
    audit_only = true,
    policy_review = true,
}

local KNOWN_RUNTIME_ACTIONS = {
    plan_heal = true,
    plan_loot = true,
    plan_timer = true,
    plan_paralyze_recovery = true,
    plan_poison_recovery = true,
    plan_burn_recovery = true,
    plan_energy_recovery = true,
    plan_bleed_recovery = true,
    plan_ring_swap = true,
    plan_amulet_swap = true,
    plan_sio = true,
    plan_attack = true,
    plan_spell = true,
    plan_rune = true,
    plan_walk = true,
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
    return value == true or value == "passed" or value == "ready" or value == "approved" or value == "accepted"
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

local function actionGateAccepted(gates, name, action, schemaVersion)
    if type(gates) ~= "table" then return false end
    local trace = gates[name]
    return type(trace) == "table" and
        tostring(trace.schema_version or "") == tostring(schemaVersion or "") and
        tostring(trace.gate_id or "") == tostring(name or "") and
        tostring(trace.next_action or "") == tostring(action or "") and
        tostring(trace.evidence_id or "") ~= "" and
        trace.status == "accepted" and
        trace.accepted == true and
        trace.guard == "passed" and
        trace.dry_run == true and
        trace.dispatch_allowed == false and
        trace.runtime_actions == false and
        trace.live_promotion == false
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
    local action = tostring(actionPlan.next_action or "hold")
    local runtimeAction = not PASSIVE_ACTIONS[action]
    local knownAction = PASSIVE_ACTIONS[action] == true or KNOWN_RUNTIME_ACTIONS[action] == true
    local moduleSafetyGate = ACTION_SAFETY_GATES[action]
    local moduleSafetySchema = ACTION_SAFETY_GATE_SCHEMAS[action]
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
    if moduleSafetyGate and not actionGateAccepted(gates, moduleSafetyGate, action, moduleSafetySchema) then
        append(reasons, moduleSafetyGate .. "_missing")
    end
    if DEFERRED_MODULE_SCOPE_ACTIONS[action] then
        append(reasons, "action_not_approved_v1")
    end
    if DEFERRED_HIGH_RISK_ACTIONS[action] then
        append(reasons, "high_risk_deferred")
    end
    if not knownAction then
        append(reasons, "unknown_action")
    end
    local status = "blocked"
    if action == "hold" then
        status = "deferred"
    elseif #reasons == 0 and snapshot.ready then
        status = "ready"
    end
    return {
        status = status,
        next_action = action,
        module_id = tostring(actionPlan.module_id or "unknown"),
        module_safety_gate = moduleSafetyGate or "none",
        phase = DEFERRED_HIGH_RISK_ACTIONS[action] and "deferred_high_risk" or
            (DEFERRED_MODULE_SCOPE_ACTIONS[action] and "deferred_module_scope" or
            (moduleSafetyGate and "sequenced_runtime_gate" or (knownAction and "current" or "unknown_blocked"))),
        runtime_action = runtimeAction,
        runtime_action_classified_by_policy = true,
        caller_runtime_action = actionPlan.runtime_action == true,
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
        owns_action_specific_safety_gates = true,
        binds_gate_acceptance_to_action_trace = true,
        classifies_runtime_actions_internally = true,
        unknown_actions_default_to_blocked_runtime = true,
        defers_out_of_scope_module_actions = true,
        defers_combat_and_cavebot = true,
        requires_manifest_current = true,
        requires_module_static_gates = true,
        requires_module_attach_smoke = true,
        requires_smoke_attach_all = true,
        requires_live_approval = true
    }
end

_G.CTOA_HELPER_RUNTIME_POLICY = RuntimePolicy
return RuntimePolicy
