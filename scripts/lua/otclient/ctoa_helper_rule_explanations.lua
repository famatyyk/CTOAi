-- ctoa_helper_rule_explanations.lua [CTOA OTClient Native]
-- Passive normalization and presentation for deterministic rule decision traces.

local RuleExplanations = rawget(_G, "CTOA_HELPER_RULE_EXPLANATIONS") or {}

local SCHEMA_VERSION = "ctoa-helper-rule-explanation-v1"
local LANE_LABELS = {
    target = "Target",
    spell = "Spell",
    combat_action = "Action",
}

local function cleanCode(value, fallback)
    local text = string.lower(tostring(value or fallback or "unknown"))
    text = string.gsub(text, "[^a-z0-9_%-]", "_")
    text = string.gsub(text, "_+", "_")
    return string.sub(text, 1, 64)
end

local function scalarCopy(source, limit)
    local result = {}
    local count = 0
    for key, value in pairs(type(source) == "table" and source or {}) do
        local valueType = type(value)
        if type(key) == "string" and (valueType == "string" or valueType == "number" or valueType == "boolean") then
            count = count + 1
            if count > (limit or 16) then break end
            result[cleanCode(key, "value")] = valueType == "string" and string.sub(value, 1, 96) or value
        end
    end
    return result
end

local function normalizeRows(rows)
    local result = {}
    for index, row in ipairs(type(rows) == "table" and rows or {}) do
        if index > 16 then break end
        local item = type(row) == "table" and row or {}
        result[index] = {
            index = tonumber(item.index) or index,
            matched = item.matched == true,
            reason_code = cleanCode(item.reason_code or item.reason, "unknown"),
            values = scalarCopy(item.values, 12),
        }
    end
    return result
end

function RuleExplanations.trace(lane, reasonCode, details)
    local data = type(details) == "table" and details or {}
    local observationStatus = cleanCode(data.observation_status, "current")
    local reason = cleanCode(reasonCode, "unknown")
    local status = data.status == "matched" and "matched" or "blocked"
    if observationStatus == "unknown" then
        status = "blocked"
        reason = "observation_unknown"
    elseif observationStatus == "stale" then
        status = "blocked"
        reason = "observation_stale"
    end
    return {
        schema_version = SCHEMA_VERSION,
        lane = LANE_LABELS[tostring(lane or "")] and tostring(lane) or "unknown",
        status = status,
        reason_code = reason,
        selected_index = tonumber(data.selected_index),
        observation_status = observationStatus,
        observed_at_ms = tonumber(data.observed_at_ms),
        now_ms = tonumber(data.now_ms),
        values = scalarCopy(data.values, 16),
        rules = normalizeRows(data.rules),
        runtime_actions = false,
        dispatch_allowed = false,
    }
end

function RuleExplanations.summary(trace)
    local item = type(trace) == "table" and trace or {}
    local label = LANE_LABELS[item.lane] or "Rule"
    local state = item.status == "matched" and "matched" or "blocked"
    local index = tonumber(item.selected_index)
    local ruleText = index and (" r" .. tostring(index)) or ""
    return label .. " " .. state .. ruleText .. ": " .. cleanCode(item.reason_code, "unknown")
end

function RuleExplanations.contract()
    return {
        module = "ctoa_helper_rule_explanations",
        mode = "passive_trace_presentation",
        schema_version = SCHEMA_VERSION,
        owns_rule_trace_envelope = true,
        owns_rule_trace_summary = true,
        accepts_normalized_observations_only = true,
        rescans_client = false,
        unknown_observations_fail_closed = true,
        stale_observations_fail_closed = true,
        runtime_actions = false,
        dispatch_allowed = false,
        casts = false,
        attacks = false,
        walks = false,
        uses_items = false,
    }
end

_G.CTOA_HELPER_RULE_EXPLANATIONS = RuleExplanations
return RuleExplanations
