-- ctoa_helper_domain_contract.lua [CTOA OTClient Native]
-- Canonical passive envelopes for domain observations, plans, and summaries.

local DomainContract = rawget(_G, "CTOA_HELPER_DOMAIN_CONTRACT") or {}

local SCHEMA_VERSION = "ctoa-helper-domain-v1"

local LANES = {
    {id = "healing", observation = "recovery_observer", planner = "guarded_helper_shell", summary = "operator_summary", execution = "guarded_shell"},
    {id = "combat", observation = "combat_observer", planner = "combat_runtime", summary = "combat_runtime", execution = "guarded_adapter"},
    {id = "cavebot", observation = "cavebot_observer", planner = "cavebot_runtime", summary = "cavebot_runtime", execution = "guarded_adapter"},
    {id = "loot", observation = "loot_observer", planner = "loot_runtime", summary = "loot_runtime", execution = "guarded_adapter"},
    {id = "timer", observation = "context", planner = "timer_runtime", summary = "timer_runtime", execution = "guarded_adapter"},
    {id = "heal_friend", observation = "heal_friend", planner = "heal_friend", summary = "heal_friend", execution = "blocked_prototype"},
    {id = "conditions", observation = "conditions", planner = "conditions", summary = "conditions", execution = "blocked_prototype"},
    {id = "equipment", observation = "equipment", planner = "equipment", summary = "equipment", execution = "blocked_prototype"},
    {id = "scripting", observation = "request", planner = "scripting", summary = "scripting", execution = "deny_all"},
}

local function copyTable(source)
    local result = {}
    for key, value in pairs(source or {}) do
        result[key] = value
    end
    return result
end

local function descriptorCopy(descriptor)
    return {
        id = descriptor.id,
        observation = descriptor.observation,
        planner = descriptor.planner,
        summary = descriptor.summary,
        execution = descriptor.execution,
    }
end

function DomainContract.schemaVersion()
    return SCHEMA_VERSION
end

function DomainContract.lanes()
    local result = {}
    for index, descriptor in ipairs(LANES) do
        result[index] = descriptorCopy(descriptor)
    end
    return result
end

function DomainContract.lane(laneId)
    local id = tostring(laneId or "")
    for _, descriptor in ipairs(LANES) do
        if descriptor.id == id then
            return descriptorCopy(descriptor)
        end
    end
    return nil
end

function DomainContract.observationEnvelope(laneId, payload, observedAt)
    local descriptor = DomainContract.lane(laneId)
    return {
        schema_version = SCHEMA_VERSION,
        kind = "observation",
        lane = descriptor and descriptor.id or tostring(laneId or "unknown"),
        observed_at = tonumber(observedAt) or 0,
        payload = copyTable(payload),
        valid_lane = descriptor ~= nil,
        runtime_actions = false,
    }
end

function DomainContract.planEnvelope(laneId, plan)
    local descriptor = DomainContract.lane(laneId)
    local source = copyTable(plan)
    source.schema_version = SCHEMA_VERSION
    source.kind = "plan"
    source.lane = descriptor and descriptor.id or tostring(laneId or "unknown")
    source.module_id = tostring(source.module_id or source.lane)
    source.next_action = tostring(source.next_action or "hold")
    source.reason = tostring(source.reason or "no_reason")
    source.weight = tonumber(source.weight) or 0
    source.valid_lane = descriptor ~= nil
    source.dispatch_allowed = false
    source.executes_plan = false
    return source
end

function DomainContract.summaryEnvelope(laneId, state, text)
    local descriptor = DomainContract.lane(laneId)
    return {
        schema_version = SCHEMA_VERSION,
        kind = "summary",
        lane = descriptor and descriptor.id or tostring(laneId or "unknown"),
        state = tostring(state or "unknown"),
        text = tostring(text or ""),
        valid_lane = descriptor ~= nil,
        runtime_actions = false,
    }
end

function DomainContract.validateEnvelope(envelope, expectedKind)
    local item = type(envelope) == "table" and envelope or {}
    local errors = {}
    if item.schema_version ~= SCHEMA_VERSION then
        errors[#errors + 1] = "schema_version"
    end
    if tostring(item.kind or "") ~= tostring(expectedKind or item.kind or "") then
        errors[#errors + 1] = "kind"
    end
    if DomainContract.lane(item.lane) == nil then
        errors[#errors + 1] = "lane"
    end
    if item.kind == "plan" and (item.dispatch_allowed ~= false or item.executes_plan ~= false) then
        errors[#errors + 1] = "passive_plan"
    end
    return #errors == 0, errors
end

function DomainContract.contract()
    return {
        module = "ctoa_helper_domain_contract",
        mode = "passive",
        schema_version = SCHEMA_VERSION,
        owns_domain_catalog = true,
        owns_observation_envelope = true,
        owns_plan_envelope = true,
        owns_summary_envelope = true,
        validates_envelopes = true,
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
    }
end

_G.CTOA_HELPER_DOMAIN_CONTRACT = DomainContract
return DomainContract
