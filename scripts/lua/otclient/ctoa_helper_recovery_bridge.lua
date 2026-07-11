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
local controller = RecoveryBridge.controller or {}

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

local function call(name, ...)
    local fn = controller[name]
    if type(fn) ~= "function" then return nil end
    return fn(...)
end

local function sandboxWorkDir()
    local normalized = text(call("work_dir")):lower():gsub("\\", "/")
    local marker = "/solteriacodextest/client"
    local start = normalized:find(marker, 1, true)
    if not start then return false end
    local suffix = normalized:sub(start + #marker, start + #marker)
    return suffix == "" or suffix == "/"
end

function RecoveryBridge.configure(dependencies)
    controller = type(dependencies) == "table" and dependencies or {}
    RecoveryBridge.controller = controller
    return true
end

function RecoveryBridge.dispatchHealing(spell, vitals, nowMs, dryRun)
    local data = type(vitals) == "table" and vitals or {}
    local snapshot = RecoveryBridge.snapshot()
    return RecoveryBridge.dispatch({next_action = "plan_heal", spell = spell}, {
        online = call("online") == true,
        hp = number(data.hp, 0),
        protection_zone = call("in_protection_zone") == true,
    }, {
        now_ms = number(nowMs, 0),
        cooldown_ms = number(call("cooldown_ms"), 1000),
        client_ready = call("player_ready") == true,
        sandbox = sandboxWorkDir(),
        dry_run = dryRun ~= false,
        session_id = snapshot.session_id,
        retry_budget = 2,
    }, function(payload)
        if type(payload) ~= "table" or payload.action ~= "cast_heal" then return false end
        return call("cast", payload.spell) == true
    end)
end

function RecoveryBridge.controlStatus()
    if state.killed then return "KILLED" end
    if state.armed then return "ARMED" end
    return "DRY-RUN / DISARMED"
end

function RecoveryBridge.controlArm()
    if not sandboxWorkDir() then call("status", "Recovery bridge blocked: sandbox required"); return false end
    local now = number(call("now_ms"), 0)
    local requested = number(state.arm_requested_at_ms, 0)
    if requested == 0 or now > requested + 6000 then
        state.arm_requested_at_ms = now
        call("status", "Recovery bridge: click ARM again to confirm sandbox session")
        return false
    end
    if now - requested < 500 then return false end
    state.arm_requested_at_ms = 0
    RecoveryBridge.resetKillSwitch()
    call("request_runtime_arm", "recovery bridge sandbox confirmation")
    local armed, result = RecoveryBridge.arm({
        session_id = "sandbox-" .. tostring(now), sandbox = true,
        operator_confirmed = true, runtime_enabled = true,
    })
    if not armed then call("status", "Recovery bridge arm blocked: " .. tostring(result)); return false end
    call("enable_healing")
    if call("arm_runtime", "recovery bridge sandbox") ~= true then
        RecoveryBridge.disarm("runtime_arm_failed")
        return false
    end
    call("status", "Recovery bridge armed: sandbox Healing session")
    return true
end

function RecoveryBridge.controlKill()
    RecoveryBridge.kill("operator_kill_switch")
    call("kill_runtime")
    call("status", "Recovery bridge KILL: runtime disarmed")
    return true
end

local function controlDispatch(dryRun, label)
    local now = number(call("now_ms"), 0)
    local vitals = call("read_vitals") or {}
    local spell = call("select_spell", vitals.hp_percent, now)
    local trace = RecoveryBridge.dispatchHealing(spell, vitals, now, dryRun)
    local blockers = type(trace.blockers) == "table" and table.concat(trace.blockers, ",") or ""
    call("status", label .. ": " .. tostring(trace.status) .. " / " .. tostring(trace.result) .. (blockers ~= "" and (" / " .. blockers) or ""))
    return trace
end

function RecoveryBridge.controlDryRun()
    return controlDispatch(true, "Recovery bridge dry-run")
end

function RecoveryBridge.controlExecuteOnce()
    return controlDispatch(false, "Recovery bridge execute-once").status == "executed"
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
RecoveryBridge.controller = controller
_G.CTOA_HELPER_RECOVERY_BRIDGE = RecoveryBridge
return RecoveryBridge
