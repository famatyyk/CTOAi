-- ctoa_helper_conditions_execute_once.lua [CTOA OTClient Native]
-- P12 Conditions: one explicitly approved sandbox attempt, then mandatory KILL/disarm.

local Bridge = rawget(_G, "CTOA_HELPER_CONDITIONS_EXECUTE_ONCE") or {}

local state = Bridge.state or {
    armed = false, killed = false, consumed = false, session_id = nil,
    plan_sha256 = nil, p9_receipt_sha256 = nil, attempt_count = 0,
    kill_reason = nil,
}
local controller = Bridge.controller or {}

local function text(value)
    if value == nil then return "" end
    return tostring(value)
end
local function number(value) return tonumber(value) end
local function add(values, value) values[#values + 1] = value end
local function sha(value) return text(value):match("^[0-9a-f]+$") and #text(value) == 64 end
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

function Bridge.configure(dependencies)
    controller = type(dependencies) == "table" and dependencies or {}
    Bridge.controller = controller
    return true
end

local function terminate(reason)
    state.armed = false
    state.killed = true
    state.consumed = true
    state.session_id = nil
    state.kill_reason = text(reason or "execute_once_complete")
end

function Bridge.reset()
    state.armed = false
    state.killed = false
    state.consumed = false
    state.session_id = nil
    state.plan_sha256 = nil
    state.p9_receipt_sha256 = nil
    state.attempt_count = 0
    state.kill_reason = nil
    return {status = "disarmed", runtime_actions = false}
end

function Bridge.kill(reason)
    terminate(reason or "operator_kill")
    return {status = "killed_and_disarmed", reason = state.kill_reason,
        runtime_actions = false}
end

function Bridge.arm(input)
    local data = input or {}
    if state.armed then return false, "already_armed" end
    if state.consumed then return false, "bridge_consumed" end
    if data.sandbox ~= true then return false, "sandbox_required" end
    if data.operator_confirmed ~= true then return false, "operator_confirmation_required" end
    if data.runtime_disarmed ~= true then return false, "runtime_must_be_disarmed" end
    if data.live_promotion ~= false then return false, "live_promotion_must_be_false" end
    if text(data.lane) ~= "conditions" then return false, "conditions_lane_required" end
    if text(data.action) ~= "cast_exura_ico" or text(data.spell):lower() ~= "exura ico" then
        return false, "allowlisted_action_required"
    end
    if number(data.retry_budget) ~= 0 then return false, "retry_budget_must_be_zero" end
    if data.p9_acceptance_granted ~= true or not sha(data.p9_receipt_sha256) then
        return false, "p9_acceptance_binding_required"
    end
    if not sha(data.plan_sha256) then return false, "plan_sha256_required" end
    if text(data.session_id) == "" then return false, "session_id_required" end
    state.armed = true
    state.killed = false
    state.session_id = text(data.session_id)
    state.plan_sha256 = text(data.plan_sha256)
    state.p9_receipt_sha256 = text(data.p9_receipt_sha256)
    return true, {status = "armed", lane = "conditions", action = "cast_exura_ico",
        session_id = state.session_id, retry_budget = 0, runtime_actions = false}
end

function Bridge.preview(observation, context)
    local item = observation or {}
    local ctx = context or {}
    local blockers = {}
    if not state.armed then add(blockers, "bridge_disarmed") end
    if state.killed then add(blockers, "kill_switch_active") end
    if state.consumed then add(blockers, "bridge_consumed") end
    if ctx.sandbox ~= true then add(blockers, "sandbox_required") end
    if text(ctx.session_id) == "" or text(ctx.session_id) ~= text(state.session_id) then
        add(blockers, "session_binding_mismatch")
    end
    if text(ctx.plan_sha256) ~= text(state.plan_sha256) then add(blockers, "plan_binding_mismatch") end
    if text(ctx.p9_receipt_sha256) ~= text(state.p9_receipt_sha256) then
        add(blockers, "p9_receipt_binding_mismatch")
    end
    if text(ctx.spell):lower() ~= "exura ico" then add(blockers, "spell_not_allowlisted") end
    if number(ctx.retry_budget) ~= 0 then add(blockers, "retry_budget_nonzero") end
    if ctx.live_promotion ~= false then add(blockers, "live_promotion_must_be_false") end
    if item.online ~= "online" then add(blockers, "player_offline") end
    if item.alive ~= "alive" then add(blockers, "player_not_alive") end
    if item.protection_zone ~= "outside" then add(blockers, "protection_zone") end
    if item.condition_id ~= "paralyze" or item.condition_state ~= "present" then
        add(blockers, "paralyze_not_present")
    end
    if item.cooldown ~= "ready" then add(blockers, "cooldown_not_ready") end
    local observed = number(item.observed_at_unix_ms)
    local now = number(ctx.now_unix_ms)
    if not observed or not now or now < observed or now - observed > 1000 then
        add(blockers, "observation_not_fresh")
    end
    return {
        schema_version = "ctoa.p12-conditions-execute-once-trace.v1",
        status = #blockers == 0 and "ready" or "blocked",
        decision = #blockers == 0 and "execute_once_exura_ico" or "hold",
        blockers = blockers, action = "cast_exura_ico", spell = "exura ico",
        attempt_count = state.attempt_count, retry_budget = 0,
        dispatch_allowed = false, runtime_actions = false,
        execute_once_allowed = #blockers == 0, live_promotion = false,
        final_state = state.armed and "armed" or "disarmed",
    }
end

function Bridge.executeOnce(observation, context, executor)
    local alreadyConsumed = state.consumed
    local trace = Bridge.preview(observation, context)
    local called = false
    local ok, result = false, false
    if trace.status == "ready" and type(executor) == "function" and not alreadyConsumed then
        state.attempt_count = state.attempt_count + 1
        trace.attempt_count = state.attempt_count
        called = true
        ok, result = pcall(executor, {action = "cast_exura_ico", spell = "exura ico",
            session_id = text(state.session_id), attempt = state.attempt_count})
        trace.dispatch_allowed = true
        trace.runtime_actions = true
        trace.status = ok and result ~= false and "executed" or "failed"
        trace.result = ok and result ~= false and "success" or "executor_failed"
    elseif trace.status == "ready" then
        add(trace.blockers, "executor_required")
        trace.status = "blocked"
        trace.decision = "hold"
        trace.result = "not_called"
    else
        trace.result = "not_called"
    end
    terminate("execute_once_attempt_complete")
    trace.executor_called = called
    trace.plan_sha256 = text((context or {}).plan_sha256)
    trace.p9_receipt_sha256 = text((context or {}).p9_receipt_sha256)
    trace.live_promotion = false
    trace.execute_once_allowed = false
    trace.final_state = "killed_and_disarmed"
    trace.retry_scheduled = false
    trace.terminal_snapshot = Bridge.snapshot()
    return trace
end

function Bridge.snapshot()
    return {armed = state.armed, killed = state.killed, consumed = state.consumed,
        session_id = state.session_id, plan_sha256 = state.plan_sha256,
        p9_receipt_sha256 = state.p9_receipt_sha256,
        attempt_count = state.attempt_count, kill_reason = state.kill_reason}
end

function Bridge.controlExecuteOnce(command)
    local data = command or {}
    if not sandboxWorkDir() then call("status", "P12 Conditions blocked: sandbox required"); return false end
    if data.confirm ~= true or data.session_approved ~= true or data.execution_approved ~= true then
        call("status", "P12 Conditions blocked: separate approvals required")
        return false
    end
    local retryBudget = number(data.retry_budget)
    local planSha = text(data.plan_sha256)
    local receiptSha = text(data.p9_receipt_sha256)
    local sessionId = text(data.session_id)
    if retryBudget ~= 0 or not sha(planSha) or not sha(receiptSha) or sessionId == "" then
        call("status", "P12 Conditions blocked: command binding invalid")
        return false
    end
    local armed, reason = Bridge.arm({
        sandbox = true, operator_confirmed = true, runtime_disarmed = true,
        live_promotion = false, lane = "conditions", action = "cast_exura_ico",
        spell = "exura ico", retry_budget = 0, p9_acceptance_granted = true,
        p9_receipt_sha256 = receiptSha, plan_sha256 = planSha, session_id = sessionId,
    })
    if not armed then
        Bridge.kill("arm_failed")
        call("status", "P12 Conditions blocked: " .. text(reason))
        return false
    end
    local now = number(call("now_ms")) or 0
    local observation = call("observe", now) or {}
    local trace = Bridge.executeOnce(observation, {
        sandbox = true, session_id = sessionId, plan_sha256 = planSha,
        p9_receipt_sha256 = receiptSha, spell = "exura ico", retry_budget = 0,
        live_promotion = false, now_unix_ms = now,
    }, function(payload)
        return call("cast", payload.spell) == true
    end)
    local blockers = type(trace.blockers) == "table" and table.concat(trace.blockers, ",") or ""
    call("status", "P12 Conditions execute-once: status=" .. text(trace.status) ..
        " result=" .. text(trace.result) .. " attempt=" .. text(trace.attempt_count) ..
        " final=" .. text(trace.final_state) .. " retry=" .. text(trace.retry_scheduled) ..
        " armed=" .. text(trace.terminal_snapshot and trace.terminal_snapshot.armed) ..
        " killed=" .. text(trace.terminal_snapshot and trace.terminal_snapshot.killed) ..
        " consumed=" .. text(trace.terminal_snapshot and trace.terminal_snapshot.consumed) ..
        " plan=" .. planSha .. " p9=" .. receiptSha ..
        (blockers ~= "" and (" blockers=" .. blockers) or ""))
    return trace.status == "executed"
end

function Bridge.contract()
    return {module = "ctoa_helper_conditions_execute_once", phase = "p12_conditions",
        mode = "sandbox_execute_once", default_armed = false,
        exact_action = "cast_exura_ico", exact_spell = "exura ico", retry_budget = 0,
        exact_vocation = "ek", spell_source = "ctoa_ek_profile.healing.spell",
        requires_p9_receipt_binding = true, requires_plan_binding = true,
        requires_fresh_paralyze_observation = true,
        mandatory_kill_and_disarm_after_attempt = true,
        schedules_retry = false, live_promotion = false}
end

Bridge.state = state
Bridge.controller = controller
_G.CTOA_HELPER_CONDITIONS_EXECUTE_ONCE = Bridge
return Bridge
