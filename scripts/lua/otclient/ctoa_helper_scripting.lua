-- ctoa_helper_scripting.lua [CTOA OTClient Native]
-- Policy-only scripting shell. It records status and never executes snippets.

local Scripting = rawget(_G, "CTOA_HELPER_SCRIPTING") or {}

function Scripting.policySnapshot(config)
    local scripting = config or {}
    if scripting.allow_runtime_eval == true or scripting.allow_user_snippets == true then
        scripting.last_status = "blocked: unsafe scripting flag"
        return scripting.last_status
    end
    if scripting.runtime_enabled == true then
        scripting.last_status = "blocked: runtime scripting disabled"
        return scripting.last_status
    end
    scripting.last_status = "policy " .. tostring(scripting.policy_mode or "deny_all") .. " / command " .. tostring(scripting.command_model or "none")
    return scripting.last_status
end

function Scripting.plan(config, request, context)
    local scripting = config or {}
    local command = request or {}
    local ctx = context or {}
    local plan = {
        next_action = "hold",
        reason = "policy_disabled",
        runtime_actions = false
    }
    if scripting.enabled ~= true then
        return plan
    end
    if scripting.allow_runtime_eval == true or scripting.allow_user_snippets == true then
        plan.reason = "unsafe_scripting_flag"
        return plan
    end
    if scripting.runtime_enabled == true or ctx.runtime_allowed == true then
        plan.reason = "runtime_scripting_blocked"
        return plan
    end
    if command.text and tostring(command.text) ~= "" then
        plan.next_action = "audit_only"
        plan.reason = "snippet_execution_blocked"
        plan.max_snippet_chars = tonumber(scripting.max_snippet_chars or 0) or 0
        return plan
    end
    plan.next_action = "policy_review"
    plan.reason = "deny_all"
    plan.policy_mode = tostring(scripting.policy_mode or "deny_all")
    plan.command_model = tostring(scripting.command_model or "none")
    return plan
end

function Scripting.summary(config, helpers)
    helpers = helpers or {}
    local scripting = config or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local runtimeText = scripting.runtime_enabled and "runtime ON" or "runtime gated"
    return "Policy " .. tostring(scripting.policy_mode or "deny_all") ..
        " | Snippets " .. onOffText(scripting.allow_user_snippets == true) ..
        " | Eval " .. onOffText(scripting.allow_runtime_eval == true) ..
        " | " .. runtimeText
end

function Scripting.contract()
    return {
        mode = "passive",
        owns_policy_snapshot = true,
        owns_summary_text = true,
        runtime_actions = false,
        executes_snippets = false,
        loads_files = false,
        talks = false,
        casts = false,
        requires_security_review = true,
        requires_sandbox_attach = true
    }
end

_G.CTOA_HELPER_SCRIPTING = Scripting
return Scripting
