-- ctoa_helper_rule_engine.lua [CTOA OTClient Native]
-- Pure action/condition validation and passive evaluation. Never dispatches.

local RuleEngine = rawget(_G, "CTOA_HELPER_RULE_ENGINE") or {}

local SCHEMA_VERSION = "ctoa-helper-rule-v1"
local RULE_SET_SCHEMA_VERSION = "ctoa-helper-rule-set-v1"
local CURRENT_VERSION = 1
local MAX_CONDITIONS = 8
local MAX_RULES = 32
local MAX_COOLDOWN_MS = 600000
local MAX_HYSTERESIS = 100
local MAX_RANDOMIZATION = 20

local METRICS = {
    hp_percent = {kind = "number", minimum = 0, maximum = 100},
    mana_percent = {kind = "number", minimum = 0, maximum = 100},
    monster_count = {kind = "number", minimum = 0, maximum = 1000},
    distance = {kind = "number", minimum = 0, maximum = 100},
    pz = {kind = "boolean"},
    active_condition = {kind = "boolean", requires_key = true},
}

local OPERATORS = { ["<"] = true, ["<="] = true, ["="] = true, ["!="] = true, [">="] = true, [">"] = true }
local COMBINATORS = {AND = true, OR = true}
local ACTION_TYPES = {spell = true, rune = true, item = true, equipment = true, stance = true, target = true, hold = true}

local function copyScalarTable(source)
    local result = {}
    for key, value in pairs(type(source) == "table" and source or {}) do
        if type(value) == "string" or type(value) == "number" or type(value) == "boolean" then
            result[key] = value
        end
    end
    return result
end

local function clampNumber(value, minimum, maximum, fallback)
    local number = tonumber(value)
    if number == nil then
        number = fallback
    end
    number = math.max(minimum, math.min(maximum, number))
    return number
end

local function normalizedExpected(metric, value)
    local descriptor = METRICS[metric]
    if not descriptor then
        return nil
    end
    if descriptor.kind == "boolean" then
        return value == true
    end
    return clampNumber(value, descriptor.minimum, descriptor.maximum, descriptor.minimum)
end

function RuleEngine.sanitizeCondition(condition)
    local source = type(condition) == "table" and condition or {}
    local metric = tostring(source.metric or "")
    local descriptor = METRICS[metric]
    if not descriptor then
        return nil, "unsupported_metric"
    end
    local operator = tostring(source.operator or "")
    if not OPERATORS[operator] then
        return nil, "unsupported_operator"
    end
    if descriptor.kind == "boolean" and operator ~= "=" and operator ~= "!=" then
        return nil, "boolean_operator"
    end
    local key = tostring(source.key or "")
    if descriptor.requires_key and key == "" then
        return nil, "condition_key"
    end
    return {
        metric = metric,
        operator = operator,
        value = normalizedExpected(metric, source.value),
        key = key,
        hysteresis = clampNumber(source.hysteresis, 0, MAX_HYSTERESIS, 0),
        randomization = descriptor.kind == "number" and clampNumber(source.randomization, 0, MAX_RANDOMIZATION, 0) or 0,
    }, nil
end

local function sanitizeCurrentRule(rule)
    local source = type(rule) == "table" and rule or {}
    local actionSource = type(source.action) == "table" and source.action or {}
    local actionType = tostring(actionSource.type or "")
    if not ACTION_TYPES[actionType] then
        return nil, {"unsupported_action"}
    end
    local conditions = {}
    local errors = {}
    for index, condition in ipairs(type(source.conditions) == "table" and source.conditions or {}) do
        if index > MAX_CONDITIONS then
            errors[#errors + 1] = "too_many_conditions"
            break
        end
        local clean, err = RuleEngine.sanitizeCondition(condition)
        if clean then
            conditions[#conditions + 1] = clean
        else
            errors[#errors + 1] = "condition_" .. tostring(index) .. ":" .. tostring(err)
        end
    end
    if #conditions == 0 then
        errors[#errors + 1] = "conditions_required"
    end
    if #errors > 0 then
        return nil, errors
    end
    local combinator = string.upper(tostring(source.combinator or "AND"))
    if not COMBINATORS[combinator] then
        combinator = "AND"
    end
    return {
        schema_version = SCHEMA_VERSION,
        id = tostring(source.id or ""),
        enabled = source.enabled == true,
        priority = math.floor(clampNumber(source.priority, -1000, 1000, 0)),
        combinator = combinator,
        cooldown_ms = math.floor(clampNumber(source.cooldown_ms, 0, MAX_COOLDOWN_MS, 0)),
        action = {type = actionType, params = copyScalarTable(actionSource.params)},
        conditions = conditions,
        dispatch_allowed = false,
        executes_action = false,
    }, {}
end

local function namedVersion(value, prefix)
    if value == nil or value == "" then
        return 0, "unversioned"
    end
    if type(value) == "number" and value == math.floor(value) and value >= 0 then
        return value, "numeric"
    end
    local parsed = type(value) == "string" and string.match(value, "^" .. prefix .. "(%d+)$") or nil
    if parsed then
        return tonumber(parsed), "named"
    end
    return nil, "invalid"
end

function RuleEngine.migrationPlan(rule)
    local source = type(rule) == "table" and rule or {}
    local version, kind = namedVersion(source.schema_version, "ctoa%-helper%-rule%-v")
    local allowed = version ~= nil and version <= CURRENT_VERSION
    local reason = "schema_ready"
    if version == nil then
        reason = "invalid_schema_version"
    elseif version > CURRENT_VERSION then
        reason = "future_schema_version"
    elseif version < CURRENT_VERSION then
        reason = "migration_required"
    end
    return {
        allowed = allowed,
        reason = reason,
        source_version = version,
        source_version_kind = kind,
        target_version = CURRENT_VERSION,
        target_schema = SCHEMA_VERSION,
        safe_disabled = version ~= CURRENT_VERSION,
        preserves_order = true,
        runtime_actions = false,
    }
end

function RuleEngine.migrate(rule)
    local plan = RuleEngine.migrationPlan(rule)
    if plan.allowed ~= true then
        return nil, plan
    end
    local clean, errors = sanitizeCurrentRule(rule)
    if not clean then
        plan.allowed = false
        plan.reason = "invalid_rule"
        plan.validation_errors = errors
        return nil, plan
    end
    clean.schema_version = SCHEMA_VERSION
    if plan.safe_disabled then
        clean.enabled = false
    end
    plan.applied = plan.source_version ~= CURRENT_VERSION
    plan.result_schema = clean.schema_version
    return clean, plan
end

function RuleEngine.ruleSetMigrationPlan(ruleSet)
    local source = type(ruleSet) == "table" and ruleSet or {}
    local rawRules = source.rules
    local schema = source.schema_version
    if rawRules == nil and #source > 0 then
        rawRules = source
        schema = nil
    end
    local version, kind = namedVersion(schema, "ctoa%-helper%-rule%-set%-v")
    local count = type(rawRules) == "table" and #rawRules or 0
    local allowed = version ~= nil and version <= CURRENT_VERSION and count <= MAX_RULES
    local reason = "schema_ready"
    if version == nil then
        reason = "invalid_schema_version"
    elseif version > CURRENT_VERSION then
        reason = "future_schema_version"
    elseif count > MAX_RULES then
        reason = "too_many_rules"
    elseif version < CURRENT_VERSION then
        reason = "migration_required"
    end
    return {
        allowed = allowed,
        reason = reason,
        source_version = version,
        source_version_kind = kind,
        target_version = CURRENT_VERSION,
        target_schema = RULE_SET_SCHEMA_VERSION,
        rule_count = count,
        max_rules = MAX_RULES,
        safe_disabled = version ~= CURRENT_VERSION,
        preserves_order = true,
        runtime_actions = false,
    }, rawRules or {}
end

function RuleEngine.migrateRuleSet(ruleSet)
    local plan, rules = RuleEngine.ruleSetMigrationPlan(ruleSet)
    if plan.allowed ~= true then
        return nil, plan
    end
    local migrated = {schema_version = RULE_SET_SCHEMA_VERSION, rules = {}}
    for index, rule in ipairs(rules) do
        local candidate = rule
        if plan.safe_disabled and type(rule) == "table" and rule.schema_version == nil then
            candidate = {}
            for key, value in pairs(rule) do candidate[key] = value end
            candidate.schema_version = SCHEMA_VERSION
        end
        local clean, rulePlan = RuleEngine.migrate(candidate)
        if not clean then
            plan.allowed = false
            plan.reason = "rule_migration_failed"
            plan.failed_rule_index = index
            plan.rule_plan = rulePlan
            return nil, plan
        end
        if plan.safe_disabled then clean.enabled = false end
        migrated.rules[index] = clean
    end
    plan.applied = plan.source_version ~= CURRENT_VERSION
    plan.result_schema = migrated.schema_version
    return migrated, plan
end

function RuleEngine.sanitizeRule(rule)
    local clean, plan = RuleEngine.migrate(rule)
    if clean then
        return clean, {}
    end
    return nil, plan.validation_errors or {plan.reason}
end

local function actualValue(condition, context)
    if condition.metric == "active_condition" then
        local active = type(context.active_conditions) == "table" and context.active_conditions or {}
        return active[condition.key] == true
    end
    return context[condition.metric]
end

local function numericExpected(condition, previousMatch, randomOffset)
    local expected = tonumber(condition.value) or 0
    if previousMatch == true then
        if condition.operator == "<" or condition.operator == "<=" then
            expected = expected + condition.hysteresis
        elseif condition.operator == ">" or condition.operator == ">=" then
            expected = expected - condition.hysteresis
        end
    end
    return expected + randomOffset
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

function RuleEngine.evaluate(rule, context, state, randomInteger)
    local clean, errors = RuleEngine.sanitizeRule(rule)
    if not clean then
        return {matched = false, reason = "invalid_rule", errors = errors, dispatch_allowed = false, executes_action = false}
    end
    if not clean.enabled then
        return {matched = false, reason = "disabled", rule = clean, dispatch_allowed = false, executes_action = false}
    end
    local snapshot = type(context) == "table" and context or {}
    local previous = type(state) == "table" and state or {}
    local now = math.max(0, tonumber(snapshot.now_ms) or 0)
    local lastMatched = math.max(0, tonumber(previous.last_matched_ms) or 0)
    if clean.cooldown_ms > 0 and lastMatched > 0 and now - lastMatched < clean.cooldown_ms then
        return {matched = false, reason = "cooldown", rule = clean, dispatch_allowed = false, executes_action = false}
    end
    local results = {}
    local matched = clean.combinator == "AND"
    for index, condition in ipairs(clean.conditions) do
        local actual = actualValue(condition, snapshot)
        local descriptor = METRICS[condition.metric]
        local conditionMatched = false
        local expected = condition.value
        if descriptor.kind == "number" and tonumber(actual) ~= nil then
            local spread = math.floor(condition.randomization)
            local offset = 0
            if spread > 0 and type(randomInteger) == "function" then
                offset = clampNumber(randomInteger(-spread, spread), -spread, spread, 0)
            end
            expected = numericExpected(condition, previous.previous_match == true, offset)
            conditionMatched = compare(tonumber(actual), condition.operator, expected)
        elseif descriptor.kind == "boolean" and type(actual) == "boolean" then
            conditionMatched = compare(actual, condition.operator, expected)
        end
        results[index] = {metric = condition.metric, key = condition.key, actual = actual, expected = expected, matched = conditionMatched}
        if clean.combinator == "AND" and not conditionMatched then
            matched = false
            break
        elseif clean.combinator == "OR" and conditionMatched then
            matched = true
            break
        end
    end
    return {
        matched = matched,
        reason = matched and "conditions_matched" or "conditions_not_matched",
        rule = clean,
        results = results,
        next_state = {previous_match = matched, last_matched_ms = matched and now or lastMatched},
        dispatch_allowed = false,
        executes_action = false,
    }
end

function RuleEngine.contract()
    return {
        module = "ctoa_helper_rule_engine",
        schema_version = SCHEMA_VERSION,
        rule_set_schema_version = RULE_SET_SCHEMA_VERSION,
        metrics = {"hp_percent", "mana_percent", "monster_count", "distance", "pz", "active_condition"},
        operators = {"<", "<=", "=", "!=", ">=", ">"},
        combinators = {"AND", "OR"},
        max_conditions = MAX_CONDITIONS,
        max_rules = MAX_RULES,
        max_randomization = MAX_RANDOMIZATION,
        owns_versioned_rule_migration = true,
        owns_versioned_rule_set_migration = true,
        runtime_actions = false,
        dispatch_allowed = false,
        executes_actions = false,
    }
end

_G.CTOA_HELPER_RULE_ENGINE = RuleEngine
return RuleEngine
