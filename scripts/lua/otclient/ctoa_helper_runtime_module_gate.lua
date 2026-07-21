-- ctoa_helper_runtime_module_gate.lua [CTOA OTClient Native]
-- Shared, passive evaluator for action-specific runtime safety gates.

local RuntimeModuleGate = rawget(_G, "CTOA_HELPER_RUNTIME_MODULE_GATE") or {}

local function appendUnique(values, value)
    local item = tostring(value or "unknown")
    for _, existing in ipairs(values) do
        if existing == item then return end
    end
    values[#values + 1] = item
end

local function contains(values, expected)
    local needle = tostring(expected or "")
    for _, value in ipairs(values or {}) do
        if tostring(value) == needle then return true end
    end
    return false
end

function RuntimeModuleGate.evaluate(spec, input)
    local gate = spec or {}
    local data = input or {}
    local blockers = {}
    local action = tostring(data.next_action or "hold")

    if not contains(gate.allowed_actions, action) then
        appendUnique(blockers, "unsupported_action")
    end
    for _, name in ipairs(gate.required_true or {}) do
        if data[name] ~= true then appendUnique(blockers, tostring(name) .. "_required") end
    end
    for _, name in ipairs(gate.required_false or {}) do
        if data[name] ~= false then appendUnique(blockers, tostring(name) .. "_false_required") end
    end
    for _, name in ipairs(gate.forbidden_true or {}) do
        if data[name] == true then appendUnique(blockers, tostring(name) .. "_forbidden") end
    end

    return {
        schema_version = tostring(gate.schema_version or "ctoa.runtime-module-safety-gate.v1"),
        gate_id = tostring(gate.gate_id or "unknown"),
        phase = tostring(gate.phase or "unknown"),
        domain = tostring(gate.domain or "unknown"),
        next_action = action,
        status = #blockers == 0 and "accepted" or "blocked",
        accepted = #blockers == 0,
        blockers = blockers,
        decision = action,
        guard = #blockers == 0 and "passed" or "blocked",
        result = "dry_run_gate",
        dry_run = data.dry_run == true,
        evidence_id = tostring(data.evidence_id or ""),
        dispatch_allowed = false,
        executes_plan = false,
        runtime_actions = false,
        live_promotion = false,
    }
end

function RuntimeModuleGate.acceptedTrace(trace, gateId, action, schemaVersion)
    local item = trace or {}
    return type(trace) == "table" and
        (tostring(schemaVersion or "") == "" or tostring(item.schema_version or "") == tostring(schemaVersion)) and
        tostring(item.gate_id or "") == tostring(gateId or "") and
        tostring(item.next_action or "") == tostring(action or "") and
        tostring(item.evidence_id or "") ~= "" and
        item.status == "accepted" and
        item.accepted == true and
        item.guard == "passed" and
        item.dry_run == true and
        item.dispatch_allowed == false and
        item.runtime_actions == false and
        item.live_promotion == false
end

function RuntimeModuleGate.block(trace, reason)
    local result = trace or {blockers = {}}
    result.blockers = result.blockers or {}
    appendUnique(result.blockers, reason)
    result.status = "blocked"
    result.accepted = false
    result.guard = "blocked"
    return result
end

function RuntimeModuleGate.finish(trace)
    local result = trace or {blockers = {"missing_trace"}}
    result.blockers = result.blockers or {}
    result.accepted = #result.blockers == 0
    result.status = result.accepted and "accepted" or "blocked"
    result.guard = result.accepted and "passed" or "blocked"
    return result
end

function RuntimeModuleGate.contract()
    return {
        module = "ctoa_helper_runtime_module_gate",
        mode = "passive",
        evaluates_action_specific_gates = true,
        validates_bound_predecessor_traces = true,
        default_closed = true,
        dry_run_only = true,
        dispatch_allowed = false,
        executes_plans = false,
        runtime_actions = false,
        live_promotion = false,
        touches_otclient_globals = false,
    }
end

_G.CTOA_HELPER_RUNTIME_MODULE_GATE = RuntimeModuleGate
return RuntimeModuleGate
