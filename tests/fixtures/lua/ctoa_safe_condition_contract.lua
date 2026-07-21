-- ctoa_safe_condition_contract.lua [CTOA Safe parity fixture]
-- Pure condition semantics for parity validation. This file never dispatches or mutates runtime state.

local Contract = rawget(_G, "CTOA_SAFE_CONDITION_CONTRACT") or {}

local SCHEMA_VERSION = "ctoa-safe-condition-contract-v1"
local MAX_CONDITIONS = 4
local MAX_RANDOMIZATION = 20
local METRICS = {hp = true, mana = true, monsters = true}
local OPERATORS = { ["<"] = true, ["<="] = true, ["="] = true, ["!="] = true, [">="] = true, [">"] = true }

local function clamp(value, minimum, maximum, fallback)
    local number = tonumber(value)
    if number == nil then number = fallback end
    return math.max(minimum, math.min(maximum, number))
end

local function compare(actual, operator, expected)
    if operator == "<" then return actual < expected end
    if operator == "<=" then return actual <= expected end
    if operator == "=" then return actual == expected end
    if operator == "!=" then return actual ~= expected end
    if operator == ">=" then return actual >= expected end
    if operator == ">" then return actual > expected end
    return false
end

function Contract.sanitizeCondition(condition)
    local source = type(condition) == "table" and condition or {}
    local metric = tostring(source.metric or "")
    if not METRICS[metric] then return nil, "unsupported_metric" end
    local operator = tostring(source.operator or "")
    if not OPERATORS[operator] then return nil, "unsupported_operator" end
    return {
        metric = metric,
        operator = operator,
        value = clamp(source.value, 0, 1000, 0),
        randomization = clamp(source.randomization, 0, MAX_RANDOMIZATION, 0),
    }, nil
end

function Contract.evaluate(rule, context, randomInteger)
    local source = type(rule) == "table" and rule or {}
    local conditions = type(source.conditions) == "table" and source.conditions or {}
    if #conditions == 0 then
        return {matched = false, reason = "conditions_required", runtime_actions = false, dispatch_allowed = false}
    end
    if #conditions > MAX_CONDITIONS then
        return {matched = false, reason = "too_many_conditions", runtime_actions = false, dispatch_allowed = false}
    end
    local combinator = string.upper(tostring(source.combinator or source.condition_logic or "AND"))
    if combinator ~= "OR" then combinator = "AND" end
    local matched = combinator == "AND"
    local results = {}
    for index, condition in ipairs(conditions) do
        local clean, reason = Contract.sanitizeCondition(condition)
        if not clean then
            return {matched = false, reason = reason, failed_condition = index, runtime_actions = false, dispatch_allowed = false}
        end
        local actual = tonumber((context or {})[clean.metric])
        local conditionMatched = false
        local expected = clean.value
        if actual ~= nil then
            local spread = math.floor(clean.randomization)
            local offset = 0
            if spread > 0 and type(randomInteger) == "function" then
                offset = clamp(randomInteger(-spread, spread), -spread, spread, 0)
            end
            expected = expected + offset
            conditionMatched = compare(actual, clean.operator, expected)
        end
        results[index] = {metric = clean.metric, actual = actual, expected = expected, matched = conditionMatched}
        if combinator == "AND" and not conditionMatched then
            matched = false
            break
        elseif combinator == "OR" and conditionMatched then
            matched = true
            break
        end
    end
    return {
        matched = matched,
        reason = matched and "conditions_matched" or "conditions_not_matched",
        results = results,
        runtime_actions = false,
        dispatch_allowed = false,
        executes_action = false,
    }
end

function Contract.contract()
    return {
        module = "ctoa_safe_condition_contract",
        schema_version = SCHEMA_VERSION,
        metrics = {"hp", "mana", "monsters"},
        canonical_metric_map = {hp = "hp_percent", mana = "mana_percent", monsters = "monster_count"},
        operators = {"<", "<=", "=", "!=", ">=", ">"},
        combinators = {"AND", "OR"},
        max_conditions = MAX_CONDITIONS,
        max_randomization = MAX_RANDOMIZATION,
        pure = true,
        runtime_actions = false,
        dispatch_allowed = false,
        executes_actions = false,
    }
end

_G.CTOA_SAFE_CONDITION_CONTRACT = Contract
return Contract
