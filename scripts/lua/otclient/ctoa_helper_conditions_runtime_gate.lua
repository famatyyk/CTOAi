-- ctoa_helper_conditions_runtime_gate.lua [CTOA OTClient Native]
-- Conditions v1 safety gate. It approves only a dry-run paralyze recovery plan.

local ConditionsRuntimeGate = rawget(_G, "CTOA_HELPER_CONDITIONS_RUNTIME_GATE") or {}
local Gate = rawget(_G, "CTOA_HELPER_RUNTIME_MODULE_GATE")

local REQUIRED_TRUE = {
    "manifest_current",
    "module_static_gates",
    "module_attach_smoke",
    "smoke_attach_all",
    "conditions_observer_smoke",
    "conditions_observation_current",
    "sandbox",
    "operator_confirmed",
    "runtime_disarmed",
    "dry_run",
    "online",
    "player_alive",
    "client_ready",
    "outside_protection_zone",
    "condition_confirmed",
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

local function recoveryTraceAccepted(trace)
    local item = trace or {}
    return type(trace) == "table" and
        item.schema_version == "ctoa.recovery-bridge-trace.v1" and
        item.status == "ready" and
        item.guard == "passed" and
        item.decision == "plan_heal" and
        item.dry_run == true and
        item.dispatch_allowed == false and
        item.runtime_actions == false
end

local function runtimeLanesDisabled(value)
    return type(value) == "table" and value.combat == "disabled" and value.cavebot == "disabled"
end

function ConditionsRuntimeGate.evaluate(input)
    local data = input or {}
    if type(Gate) ~= "table" or type(Gate.evaluate) ~= "function" then
        return {status = "blocked", accepted = false, blockers = {"gate_engine_missing"}}
    end
    local trace = Gate.evaluate({
        schema_version = "ctoa.conditions-runtime-safety-gate.v1",
        gate_id = "conditions_runtime_gate",
        phase = "conditions_first",
        domain = "conditions",
        allowed_actions = {"plan_paralyze_recovery"},
        required_true = REQUIRED_TRUE,
        required_false = {"protection_zone", "live_promotion"},
    }, data)
    if not recoveryTraceAccepted(data.recovery_bridge_trace) then Gate.block(trace, "recovery_bridge_trace_required") end
    if not runtimeLanesDisabled(data.runtime_lane_states) then Gate.block(trace, "high_risk_lanes_must_be_disabled") end
    if tostring(data.evidence_id or "") == "" then Gate.block(trace, "evidence_id_required") end
    if tostring(data.observation_id or "") == "" then Gate.block(trace, "observation_id_required") end
    if tostring(data.condition or ""):lower() ~= "paralyze" then Gate.block(trace, "paralyze_condition_required") end
    if tostring(data.spell or ""):lower() ~= "exura" then Gate.block(trace, "allowlisted_recovery_spell_required") end

    local observedAt = integer(data.observed_at_ms)
    local evaluatedAt = integer(data.evaluated_at_ms)
    if not observedAt or observedAt < 0 or not evaluatedAt or evaluatedAt < observedAt then
        Gate.block(trace, "observation_timestamp_invalid")
    elseif evaluatedAt - observedAt > 1000 then
        Gate.block(trace, "observation_stale")
    else
        trace.observation_age_ms = evaluatedAt - observedAt
    end

    local cooldown = integer(data.cooldown_ms)
    local elapsed = integer(data.cooldown_elapsed_ms)
    if not cooldown or cooldown < 500 or cooldown > 60000 then Gate.block(trace, "cooldown_invalid") end
    if not elapsed or elapsed < 0 then
        Gate.block(trace, "cooldown_elapsed_invalid")
    elseif cooldown and elapsed < cooldown then
        Gate.block(trace, "cooldown_active")
    end
    local retries = integer(data.retry_budget)
    if retries == nil or retries < 0 or retries > 1 then Gate.block(trace, "retry_budget_invalid") end
    return Gate.finish(trace)
end

function ConditionsRuntimeGate.contract()
    return {
        module = "ctoa_helper_conditions_runtime_gate",
        mode = "sandbox_dry_run_gate",
        phase = "conditions_first",
        allowed_action = "plan_paralyze_recovery",
        default_closed = true,
        requires_recovery_acceptance = true,
        requires_bound_recovery_trace = true,
        allowed_spell = "exura",
        requires_fresh_condition_observation = true,
        derives_observation_age_from_timestamps = true,
        requires_cooldown_elapsed = true,
        requires_operator_confirmation = true,
        requires_runtime_disarmed = true,
        blocks_protection_zone = true,
        combat_deferred = true,
        cavebot_deferred = true,
        dispatch_allowed = false,
        runtime_actions = false,
        live_promotion = false,
    }
end

_G.CTOA_HELPER_CONDITIONS_RUNTIME_GATE = ConditionsRuntimeGate
return ConditionsRuntimeGate
