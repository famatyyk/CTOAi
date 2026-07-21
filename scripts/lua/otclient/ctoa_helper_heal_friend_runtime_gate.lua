-- ctoa_helper_heal_friend_runtime_gate.lua [CTOA OTClient Native]
-- Heal Friend v1 safety gate. It remains dry-run and follows Conditions/Equipment.

local HealFriendRuntimeGate = rawget(_G, "CTOA_HELPER_HEAL_FRIEND_RUNTIME_GATE") or {}
local Gate = rawget(_G, "CTOA_HELPER_RUNTIME_MODULE_GATE")

local REQUIRED_TRUE = {
    "manifest_current",
    "module_static_gates",
    "module_attach_smoke",
    "smoke_attach_all",
    "heal_friend_no_target_smoke",
    "whitelist_persistence_verified",
    "sandbox",
    "operator_confirmed",
    "runtime_disarmed",
    "dry_run",
    "online",
    "player_alive",
    "client_ready",
    "outside_protection_zone",
    "require_whitelist",
    "target_is_player",
    "target_visible",
    "target_same_floor",
    "target_in_range",
}

local function finiteNumber(value)
    local result = tonumber(value)
    if not result or result ~= result or result == math.huge or result == -math.huge then return nil end
    return result
end

local function integer(value)
    local result = finiteNumber(value)
    if not result or result % 1 ~= 0 then return nil end
    return result
end

local function normalizedName(value)
    return tostring(value or ""):match("^%s*(.-)%s*$"):lower()
end

local function containsName(values, expected)
    local needle = normalizedName(expected)
    if needle == "" or type(values) ~= "table" then return false end
    for _, value in ipairs(values) do
        if normalizedName(value) == needle then return true end
    end
    return false
end

local function containsId(values, expected)
    if type(values) ~= "table" then return false end
    for _, value in ipairs(values) do
        if integer(value) == expected then return true end
    end
    return false
end

local function runtimeLanesDisabled(value)
    return type(value) == "table" and value.combat == "disabled" and value.cavebot == "disabled"
end

function HealFriendRuntimeGate.evaluate(input)
    local data = input or {}
    if type(Gate) ~= "table" or type(Gate.evaluate) ~= "function" then
        return {status = "blocked", accepted = false, blockers = {"gate_engine_missing"}}
    end
    local trace = Gate.evaluate({
        schema_version = "ctoa.heal-friend-runtime-safety-gate.v1",
        gate_id = "heal_friend_runtime_gate",
        phase = "heal_friend_after_equipment_conditions",
        domain = "heal_friend",
        allowed_actions = {"plan_sio"},
        required_true = REQUIRED_TRUE,
        required_false = {"protection_zone", "target_is_self", "live_promotion"},
    }, data)
    if type(Gate.acceptedTrace) ~= "function" or not Gate.acceptedTrace(data.conditions_gate_trace, "conditions_runtime_gate", "plan_paralyze_recovery", "ctoa.conditions-runtime-safety-gate.v1") then
        Gate.block(trace, "conditions_gate_trace_required")
    end
    if type(Gate.acceptedTrace) ~= "function" or not Gate.acceptedTrace(data.equipment_gate_trace, "equipment_runtime_gate", "plan_ring_swap", "ctoa.equipment-runtime-safety-gate.v1") then
        Gate.block(trace, "equipment_gate_trace_required")
    end
    if not runtimeLanesDisabled(data.runtime_lane_states) then Gate.block(trace, "high_risk_lanes_must_be_disabled") end
    if tostring(data.evidence_id or "") == "" then Gate.block(trace, "evidence_id_required") end

    local targetId = integer(data.target_id)
    local observedTargetId = integer(data.observed_target_id)
    local currentTargetId = integer(data.current_target_id)
    local selfId = integer(data.self_id)
    local targetName = normalizedName(data.target_name)
    local observedName = normalizedName(data.observed_target_name)
    local currentName = normalizedName(data.current_target_name)
    if not targetId or targetId <= 0 then Gate.block(trace, "target_id_invalid") end
    if not selfId or selfId <= 0 or selfId == targetId then Gate.block(trace, "self_identity_invalid") end
    if targetName == "" then Gate.block(trace, "target_name_required") end
    if observedTargetId ~= targetId or currentTargetId ~= targetId or observedName ~= targetName or currentName ~= targetName then
        Gate.block(trace, "target_identity_mismatch")
    end

    local whitelistRevision = tostring(data.whitelist_revision or "")
    if whitelistRevision == "" or tostring(data.persisted_whitelist_revision or "") ~= whitelistRevision then
        Gate.block(trace, "persisted_whitelist_revision_mismatch")
    end
    if not containsName(data.persisted_whitelist_names, targetName) then Gate.block(trace, "persisted_whitelist_identity_missing") end
    if not targetId or not containsId(data.party_member_ids, targetId) then Gate.block(trace, "party_membership_missing") end

    local hp = finiteNumber(data.current_target_hp_percent)
    local observedHp = finiteNumber(data.observed_target_hp_percent)
    local threshold = finiteNumber(data.hp_threshold)
    if not hp or hp <= 0 or hp > 100 or not observedHp or observedHp <= 0 or observedHp > 100 then Gate.block(trace, "target_hp_invalid") end
    if not threshold or threshold < 1 or threshold > 100 then Gate.block(trace, "hp_threshold_invalid") end
    if hp and threshold and hp > threshold then Gate.block(trace, "target_above_threshold") end
    if tostring(data.spell or ""):lower() ~= "exura sio" then Gate.block(trace, "sio_spell_required") end

    local observedAt = integer(data.observed_at_ms)
    local partyObservedAt = integer(data.party_observed_at_ms)
    local evaluatedAt = integer(data.evaluated_at_ms)
    if not observedAt or observedAt < 0 or not partyObservedAt or partyObservedAt < 0 or not evaluatedAt or evaluatedAt < observedAt or evaluatedAt < partyObservedAt then
        Gate.block(trace, "observation_timestamp_invalid")
    elseif evaluatedAt - observedAt > 750 or evaluatedAt - partyObservedAt > 750 then
        Gate.block(trace, "observation_stale")
    else
        trace.observation_age_ms = evaluatedAt - observedAt
        trace.party_observation_age_ms = evaluatedAt - partyObservedAt
    end
    local cooldown = integer(data.cooldown_ms)
    local elapsed = integer(data.cooldown_elapsed_ms)
    if not cooldown or cooldown < 1000 or cooldown > 60000 then Gate.block(trace, "cooldown_invalid") end
    if not elapsed or elapsed < 0 then
        Gate.block(trace, "cooldown_elapsed_invalid")
    elseif cooldown and elapsed < cooldown then
        Gate.block(trace, "cooldown_active")
    end
    local retries = integer(data.retry_budget)
    if retries == nil or retries < 0 or retries > 1 then Gate.block(trace, "retry_budget_invalid") end
    return Gate.finish(trace)
end

function HealFriendRuntimeGate.contract()
    return {
        module = "ctoa_helper_heal_friend_runtime_gate",
        mode = "sandbox_dry_run_gate",
        phase = "heal_friend_after_equipment_conditions",
        allowed_action = "plan_sio",
        default_closed = true,
        requires_conditions_gate = true,
        requires_equipment_gate = true,
        requires_bound_predecessor_traces = true,
        requires_exact_whitelist_identity = true,
        requires_persisted_whitelist_revision = true,
        requires_stable_target_identity = true,
        requires_fresh_target_observation = true,
        derives_observation_age_from_timestamps = true,
        requires_party_membership = true,
        requires_cooldown_elapsed = true,
        requires_operator_confirmation = true,
        blocks_protection_zone = true,
        combat_deferred = true,
        cavebot_deferred = true,
        dispatch_allowed = false,
        runtime_actions = false,
        live_promotion = false,
    }
end

_G.CTOA_HELPER_HEAL_FRIEND_RUNTIME_GATE = HealFriendRuntimeGate
return HealFriendRuntimeGate
