-- ctoa_helper_timer_runtime.lua [CTOA OTClient Native]
-- Passive timer runtime adapter planner. This module never talks, casts, or evaluates code.

local TimerRuntime = rawget(_G, "CTOA_HELPER_TIMER_RUNTIME") or {}

local function boolValue(value)
    return value == true
end

local function numberValue(value, fallback)
    local parsed = tonumber(value)
    if parsed == nil then
        return fallback
    end
    return parsed
end

local function runtimeBlockedReason(tools, context)
    local cfg = tools or {}
    local env = context or {}
    if not boolValue(cfg.timer_enabled) then
        return "timer_disabled"
    end
    if boolValue(cfg.pause_in_pz) and boolValue(env.in_protection_zone) then
        return "protection_zone"
    end
    if env.online == false then
        return "offline"
    end
    if tostring(cfg.timer_message or "") == "" then
        return "missing_message"
    end
    if boolValue(cfg.block_timer_casts) then
        return "cast_bridge_blocked"
    end
    return nil
end

function TimerRuntime.plan(tools, context)
    local blocked = runtimeBlockedReason(tools, context)
    local cfg = tools or {}
    local now = numberValue((context or {}).now_ms, 0)
    local interval = math.max(1000, numberValue(cfg.timer_interval_ms, 60000))
    local last = numberValue(cfg.last_timer_ms, 0)
    local dueAt = last + interval
    if blocked then
        return {
            allowed = false,
            reason = blocked,
            next_action = "hold",
            due_in_ms = math.max(0, dueAt - now),
        }
    end
    if now > 0 and now < dueAt then
        return {
            allowed = false,
            reason = "interval_wait",
            next_action = "hold",
            due_in_ms = dueAt - now,
        }
    end
    return {
        allowed = true,
        reason = "planned",
        next_action = "plan_timer",
        interval_ms = interval,
        due_in_ms = 0,
        message_preview = tostring(cfg.timer_message or ""):sub(1, 32),
    }
end

function TimerRuntime.summary(plan)
    if type(plan) ~= "table" then
        return "timer adapter idle"
    end
    return tostring(plan.next_action or "hold") ..
        " | " .. tostring(plan.reason or "unknown") ..
        " | due " .. tostring(plan.due_in_ms or 0) .. "ms"
end

function TimerRuntime.dispatch(plan, tools, helpers)
    local cfg = tools or {}
    local runtimePlan = plan or {}
    local adapterText = ""
    if helpers and type(helpers.summary) == "function" then
        adapterText = tostring(helpers.summary(runtimePlan) or "")
    end
    if adapterText == "" then
        adapterText = tostring(runtimePlan.next_action or "hold") .. " | " .. tostring(runtimePlan.reason or "unknown")
    end
    if runtimePlan.allowed ~= true then
        return {
            allowed = false,
            reason = tostring(runtimePlan.reason or "hold"),
            adapter_text = adapterText,
            status_text = "Timer adapter: " .. adapterText,
        }
    end
    local message = tostring(cfg.timer_message or "")
    if message == "" then
        return {
            allowed = false,
            reason = "missing_message",
            adapter_text = adapterText,
            status_text = "Timer adapter: missing_message",
        }
    end
    local preview = message:sub(1, 32)
    return {
        allowed = true,
        reason = "dispatch_ready",
        message = message,
        adapter_text = adapterText,
        status_text = "Timer: " .. preview .. (adapterText ~= "" and (" | adapter " .. adapterText) or ""),
    }
end

function TimerRuntime.contract()
    return {
        module = "ctoa_helper_timer_runtime",
        mode = "passive",
        owns_runtime_plan = true,
        owns_dispatch_decision = true,
        runtime_actions = false,
        talks = false,
        casts = false,
        evaluates = false,
        loads_files = false,
        requires_no_eval_gate = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_TIMER_RUNTIME = TimerRuntime

return TimerRuntime
