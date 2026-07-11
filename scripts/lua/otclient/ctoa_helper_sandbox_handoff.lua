-- ctoa_helper_sandbox_handoff.lua [CTOA OTClient Native]
-- Passive sandbox handoff checklist for runtime smoke. It never launches, attaches, promotes, or executes actions.

local SandboxHandoff = rawget(_G, "CTOA_HELPER_SANDBOX_HANDOFF") or {}

local STEPS = {
    {
        step_id = "launch_sandbox",
        gate = "sandbox_client_running",
        command = "solteria_helper_test_env.ps1 -Action Launch",
        required = true,
    },
    {
        step_id = "ready_check",
        gate = "character_in_world",
        command = "solteria_helper_test_env.ps1 -Action ReadyCheck",
        required = true,
    },
    {
        step_id = "module_attach_group",
        gate = "module_attach_smoke",
        command = "solteria_helper_test_env.ps1 -Action SmokeAttachModules",
        required = true,
    },
    {
        step_id = "smoke_attach_all",
        gate = "smoke_attach_all",
        command = "solteria_helper_test_env.ps1 -Action SmokeAttachAll",
        required = true,
    },
    {
        step_id = "promote_live_approval",
        gate = "live_approval",
        command = "solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy",
        required = false,
    },
}

local function copyStep(step)
    local item = step or {}
    return {
        step_id = tostring(item.step_id or "unknown"),
        gate = tostring(item.gate or "unknown"),
        command = tostring(item.command or ""),
        required = item.required == true,
        runtime_actions = false,
        executes_plan = false,
        dispatch_allowed = false,
    }
end

local function gateReady(gates, gate)
    local value = (gates or {})[gate]
    return value == true or value == "passed" or value == "ready" or value == "approved"
end

function SandboxHandoff.steps()
    local result = {}
    for index, step in ipairs(STEPS) do
        result[index] = copyStep(step)
    end
    return result
end

function SandboxHandoff.snapshot(gates)
    local rows = {}
    local missing = {}
    for index, step in ipairs(STEPS) do
        local row = copyStep(step)
        row.status = gateReady(gates, row.gate) and "passed" or "required"
        rows[index] = row
        if row.status ~= "passed" and row.required then
            missing[#missing + 1] = row.gate
        end
    end
    return {
        status = #missing == 0 and "ready_for_smoke_attach_all" or "waiting_for_operator",
        steps = rows,
        missing = missing,
        runtime_actions = false,
        executes_plan = false,
    }
end

function SandboxHandoff.next(snapshot)
    local item = snapshot or {}
    for _, step in ipairs(item.steps or {}) do
        if step.status ~= "passed" and step.required then
            return copyStep(step)
        end
    end
    for _, step in ipairs(item.steps or {}) do
        if step.status ~= "passed" then
            return copyStep(step)
        end
    end
    return {
        step_id = "complete",
        gate = "complete",
        command = "hold",
        required = false,
        runtime_actions = false,
        executes_plan = false,
        dispatch_allowed = false,
    }
end

function SandboxHandoff.summary(snapshot)
    local item = snapshot or {}
    local missing = item.missing or {}
    local nextStep = SandboxHandoff.next(item)
    return "Sandbox handoff " .. tostring(item.status or "waiting_for_operator") ..
        " | Next " .. tostring(nextStep.step_id or "unknown") ..
        " | Missing " .. tostring(#missing)
end

function SandboxHandoff.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
        launches_client = false,
        attaches_client = false,
        promotes_live = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
        requires_ready_check = true,
        requires_module_attach_smoke = true,
        requires_smoke_attach_all = true,
        requires_live_approval = true,
    }
end

_G.CTOA_HELPER_SANDBOX_HANDOFF = SandboxHandoff
return SandboxHandoff
