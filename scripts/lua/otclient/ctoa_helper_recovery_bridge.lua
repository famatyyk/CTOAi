-- ctoa_helper_recovery_bridge.lua [CTOA OTClient Native]
-- Bounded Recovery Runtime Bridge v1. Execution requires an explicitly armed
-- sandbox session and an injected executor; safe boot remains disarmed.

local RecoveryBridge = rawget(_G, "CTOA_HELPER_RECOVERY_BRIDGE") or {}

local state = RecoveryBridge.state or {
    armed = false,
    killed = false,
    session_id = nil,
    last_action_ms = 0,
    consecutive_failures = 0,
    kill_reason = nil,
}

local function text(value)
    return tostring(value or "")
end

local function number(value, fallback)
    return tonumber(value) or fallback
end

local function add(list, value)
    list[#list + 1] = value
end

function RecoveryBridge.disarm(reason)
    state.armed = false
    state.session_id = nil
    return {status = "disarmed", reason = text(reason or "operator_disarm")}
end

function RecoveryBridge.kill(reason)
    state.armed = false
    state.killed = true
    state.session_id = nil
    state.kill_reason = text(reason or "operator_kill")
    return {status = "killed", reason = state.kill_reason}
end

function RecoveryBridge.resetKillSwitch()
    state.killed = false
    state.kill_reason = nil
    state.consecutive_failures = 0
    return {status = "disarmed", killed = false}
end

function RecoveryBridge.arm(context)
    local ctx = context or {}
    local sessionId = text(ctx.session_id)
    if state.killed then return false, "kill_switch_active" end
    if ctx.sandbox ~= true then return false, "sandbox_required" end
    if ctx.operator_confirmed ~= true then return false, "operator_confirmation_required" end
    if ctx.runtime_enabled ~= true then return false, "runtime_disabled" end
    if sessionId == "" then return false, "session_id_required" end
    state.armed = true
    state.session_id = sessionId
    state.consecutive_failures = 0
    return true, {status = "armed", session_id = sessionId, sandbox = true}
end

function RecoveryBridge.preview(plan, observation, context)
    local actionPlan = plan or {}
    local observed = observation or {}
    local ctx = context or {}
    local blockers = {}
    local nowMs = number(ctx.now_ms, 0)
    local cooldownMs = math.max(250, number(ctx.cooldown_ms, 1000))

    if text(actionPlan.next_action) ~= "plan_heal" then add(blockers, "unsupported_action") end
    if text(actionPlan.spell) == "" then add(blockers, "spell_required") end
    if observed.online ~= true then add(blockers, "client_offline") end
    if number(observed.hp, 0) <= 0 then add(blockers, "player_dead") end
    if observed.protection_zone == true then add(blockers, "protection_zone") end
    if ctx.client_ready ~= true then add(blockers, "client_not_ready") end
    if ctx.sandbox ~= true then add(blockers, "sandbox_required") end
    if nowMs < state.last_action_ms + cooldownMs then add(blockers, "cooldown_active") end

    return {
        schema_version = "ctoa.recovery-bridge-trace.v1",
        status = #blockers == 0 and "ready" or "blocked",
        decision = text(actionPlan.next_action or "hold"),
        guard = #blockers == 0 and "passed" or "blocked",
        action = text(actionPlan.spell),
        result = "dry_run",
        blockers = blockers,
        dispatch_allowed = false,
        dry_run = true,
        runtime_actions = false,
    }
end

function RecoveryBridge.dispatch(plan, observation, context, executor)
    local ctx = context or {}
    local trace = RecoveryBridge.preview(plan, observation, ctx)
    if trace.status ~= "ready" then return trace end
    if ctx.dry_run ~= false then return trace end
    if state.killed then add(trace.blockers, "kill_switch_active") end
    if not state.armed then add(trace.blockers, "session_disarmed") end
    if text(ctx.session_id) == "" or text(ctx.session_id) ~= text(state.session_id) then
        add(trace.blockers, "armed_session_mismatch")
    end
    if type(executor) ~= "function" then add(trace.blockers, "executor_required") end
    if #trace.blockers > 0 then
        trace.status = "blocked"
        trace.guard = "blocked"
        return trace
    end

    local ok, result = pcall(executor, {
        action = "cast_heal",
        spell = text(plan and plan.spell),
        session_id = text(state.session_id),
    })
    trace.dry_run = false
    trace.dispatch_allowed = true
    trace.runtime_actions = true
    if ok and result ~= false then
        state.last_action_ms = number(ctx.now_ms, 0)
        state.consecutive_failures = 0
        trace.status = "executed"
        trace.result = "success"
        return trace
    end

    state.consecutive_failures = state.consecutive_failures + 1
    trace.status = "failed"
    trace.result = "executor_failed"
    trace.error = ok and "executor_rejected" or text(result)
    if state.consecutive_failures >= math.max(1, number(ctx.retry_budget, 2)) then
        RecoveryBridge.kill("retry_budget_exhausted")
        trace.kill_switch = "activated"
    end
    return trace
end

function RecoveryBridge.snapshot()
    return {
        armed = state.armed,
        killed = state.killed,
        session_id = state.session_id,
        last_action_ms = state.last_action_ms,
        consecutive_failures = state.consecutive_failures,
        kill_reason = state.kill_reason,
    }
end

function RecoveryBridge.contract()
    return {
        module = "ctoa_helper_recovery_bridge",
        version = "v1",
        mode = "sandbox_only",
        default_armed = false,
        default_dry_run = true,
        requires_session_arming = true,
        owns_kill_switch = true,
        owns_cooldown = true,
        owns_retry_budget = true,
        owns_decision_guard_action_result_trace = true,
        direct_otclient_calls = false,
        injected_executor_required = true,
        live_promotion = false,
    }
end

RecoveryBridge.state = state
_G.CTOA_HELPER_RECOVERY_BRIDGE = RecoveryBridge
return RecoveryBridge
