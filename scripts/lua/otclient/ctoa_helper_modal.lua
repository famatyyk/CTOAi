-- ctoa_helper_modal.lua [CTOA OTClient Native]
-- Passive confirmation lifecycle helpers. This module never creates widgets.

local Modal = rawget(_G, "CTOA_HELPER_MODAL") or {}

local DEFAULT_TTL_MS = 4500
local GUARDED_ACTIONS = {
    cavebot_delete = true,
    cavebot_clear = true,
    profile_reset = true,
    ui_reset = true,
    promote_live = true,
}

local function trim(value)
    if type(value) ~= "string" then
        return ""
    end
    return (value:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function actionText(action)
    local text = trim(action)
    if text == "" then
        return "action"
    end
    return text:gsub("_", " ")
end

function Modal.request(action, context, nowMs, ttlMs)
    local ttl = tonumber(ttlMs) or DEFAULT_TTL_MS
    local now = tonumber(nowMs) or 0
    local label = actionText(action)
    local detail = trim(context)
    local message = "Confirm " .. label
    if detail ~= "" then
        message = message .. ": " .. detail
    end
    return {
        action = trim(action),
        context = detail,
        requested_at_ms = now,
        expires_at_ms = now + ttl,
        message = message,
        confirm_label = "Confirm",
        cancel_label = "Cancel",
    }
end

function Modal.isPending(request, action, nowMs)
    if type(request) ~= "table" then
        return false
    end
    local now = tonumber(nowMs) or 0
    if now > (tonumber(request.expires_at_ms) or 0) then
        return false
    end
    local requestedAction = trim(request.action)
    return requestedAction ~= "" and requestedAction == trim(action)
end

function Modal.isExpired(request, nowMs)
    if type(request) ~= "table" then
        return false
    end
    local now = tonumber(nowMs) or 0
    return now > (tonumber(request.expires_at_ms) or 0)
end

function Modal.confirm(request, action, nowMs)
    if not Modal.isPending(request, action, nowMs) then
        return false, nil
    end
    return true, {
        action = trim(request.action),
        context = trim(request.context),
        confirmed_at_ms = tonumber(nowMs) or 0
    }
end

function Modal.cancel(request, nowMs)
    if type(request) ~= "table" then
        return false, nil
    end
    return true, {
        action = trim(request.action),
        context = trim(request.context),
        cancelled_at_ms = tonumber(nowMs) or 0
    }
end

function Modal.decision(request, action, command, nowMs)
    command = command or {}
    local normalizedAction = trim(action)
    if GUARDED_ACTIONS[normalizedAction] ~= true then
        return {
            allowed = true,
            reason = "unguarded_action",
            action = normalizedAction
        }
    end
    if command.confirm == true then
        local ok, payload = Modal.confirm(request, normalizedAction, nowMs)
        if ok then
            return {
                allowed = true,
                reason = "confirmed",
                action = payload.action,
                context = payload.context,
                confirmed_at_ms = payload.confirmed_at_ms
            }
        end
    end
    if Modal.isExpired(request, nowMs) then
        return {
            allowed = false,
            reason = "expired",
            action = normalizedAction
        }
    end
    return {
        allowed = false,
        reason = "confirmation_required",
        action = normalizedAction
    }
end

function Modal.decisionText(decision)
    if type(decision) ~= "table" then
        return "confirmation required"
    end
    if decision.allowed == true then
        if decision.reason == "confirmed" then
            return "confirmed: " .. actionText(decision.action)
        end
        return "allowed: " .. actionText(decision.action)
    end
    if decision.reason == "expired" then
        return "confirmation expired"
    end
    if decision.reason == "confirmation_required" then
        return "confirmation required: " .. actionText(decision.action)
    end
    return "blocked: " .. actionText(decision.reason)
end

function Modal.statusText(request)
    if type(request) ~= "table" then
        return "no confirmation pending"
    end
    local message = trim(request.message)
    if message == "" then
        return "confirmation pending"
    end
    return message
end

function Modal.buttonText(baseText, request, action, nowMs)
    if Modal.isPending(request, action, nowMs) then
        return trim(request.confirm_label) ~= "" and trim(request.confirm_label) or "Confirm"
    end
    local text = trim(baseText)
    if text == "" then
        return "Action"
    end
    return text
end

function Modal.contract()
    return {
        mode = "passive",
        creates_widgets = false,
        live_shortcuts = false,
        runtime_actions = false,
        owns_decision_text = true,
        default_ttl_ms = DEFAULT_TTL_MS,
        guarded_actions = {"cavebot_delete", "cavebot_clear", "profile_reset", "ui_reset", "promote_live"},
        gate = "Static lifecycle tests, UI preview, no live promotion bypass, and explicit approval path retained."
    }
end

_G.CTOA_HELPER_MODAL = Modal

return Modal
