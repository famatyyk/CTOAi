-- ctoa_helper_targeting.lua [CTOA OTClient Native]
-- Passive target scoring helpers. This module never attacks or casts.

local Targeting = rawget(_G, "CTOA_HELPER_TARGETING") or {}

local MAX_NAME_POLICY_ENTRIES = 32
local MAX_NAME_POLICY_LENGTH = 64
local MAX_TARGET_RULES = 16
local MAX_TARGET_RULE_NAME_LENGTH = 64
local EDITABLE_NAME_POLICY_KEYS = {
    ignored_names = true,
    priority_names = true,
}

local function explanation(reason, status, values, rows, selectedIndex)
    local owner = rawget(_G, "CTOA_HELPER_RULE_EXPLANATIONS")
    if type(owner) ~= "table" or type(owner.trace) ~= "function" then return nil end
    return owner.trace("target", reason, {
        status = status,
        selected_index = selectedIndex,
        observation_status = "current",
        values = values,
        rules = rows,
    })
end

local DEFAULT_FRIENDLY_SUMMON_NAME_FRAGMENTS = {
    " familiar ",
    " summon ",
    " summoned ",
    "familiar",
    "summon",
}

local function lowered(value)
    if value == nil then
        return ""
    end
    return string.lower(tostring(value))
end

local function trimmed(value)
    local text = tostring(value or "")
    text = string.gsub(text, "[%c]", " ")
    text = string.gsub(text, "%s+", " ")
    return string.gsub(string.gsub(text, "^%s+", ""), "%s+$", "")
end

local function clampInteger(value, minimum, maximum, fallback)
    local number = math.floor(tonumber(value) or fallback or minimum)
    return math.max(minimum, math.min(maximum, number))
end

local function targetEditorDecision(allowed, reason, index, count)
    return {
        allowed = allowed == true,
        reason = reason,
        index = index,
        count = count,
        runtime_actions = false,
        dispatch_allowed = false,
    }
end

function Targeting.sanitizeTargetRule(rule)
    local source = type(rule) == "table" and rule or {}
    local minHp = clampInteger(source.min_hp, 0, 100, 0)
    local minDistance = clampInteger(source.min_distance, 0, 10, 0)
    local minCount = clampInteger(source.min_count, 0, 99, 0)
    local chase = tostring(source.chase_policy or "inherit")
    if chase ~= "follow" and chase ~= "stand" then chase = "inherit" end
    return {
        enabled = source.enabled ~= false,
        name_pattern = string.sub(lowered(trimmed(source.name_pattern)), 1, MAX_TARGET_RULE_NAME_LENGTH),
        min_hp = minHp,
        max_hp = clampInteger(source.max_hp, minHp, 100, 100),
        min_distance = minDistance,
        max_distance = clampInteger(source.max_distance, minDistance, 10, 7),
        min_count = minCount,
        max_count = clampInteger(source.max_count, minCount, 99, 99),
        priority = clampInteger(source.priority, 1, 100, 50),
        chase_policy = chase,
    }
end

function Targeting.sanitizeTargetRules(rules)
    local result = {}
    for _, rule in ipairs(type(rules) == "table" and rules or {}) do
        if #result >= MAX_TARGET_RULES then break end
        result[#result + 1] = Targeting.sanitizeTargetRule(rule)
    end
    return result
end

function Targeting.targetRuleState(tools, requestedIndex)
    local cfg = type(tools) == "table" and tools or {}
    local rules = Targeting.sanitizeTargetRules(cfg.target_rules)
    local count = #rules
    local index = count > 0 and clampInteger(requestedIndex, 1, count, 1) or 0
    local rule = index > 0 and rules[index] or nil
    local label = rule and (rule.name_pattern ~= "" and rule.name_pattern or "any monster") or "no target rules"
    return {index = index, count = count, rule = rule, summary = tostring(index) .. "/" .. tostring(count) .. " " .. label}
end

function Targeting.replaceTargetRules(tools, rules)
    if type(tools) ~= "table" then return nil, targetEditorDecision(false, "tools_required", 0, 0) end
    tools.target_rules = Targeting.sanitizeTargetRules(rules)
    return tools.target_rules, targetEditorDecision(true, "target_rules_replaced", #tools.target_rules > 0 and 1 or 0, #tools.target_rules)
end


function Targeting.addTargetRule(tools, draft)
    if type(tools) ~= "table" then return nil, targetEditorDecision(false, "tools_required", 0, 0) end
    local rules = Targeting.sanitizeTargetRules(tools.target_rules)
    if #rules >= MAX_TARGET_RULES then return nil, targetEditorDecision(false, "target_rule_limit", #rules, #rules) end
    rules[#rules + 1] = Targeting.sanitizeTargetRule(draft or {enabled = false, name_pattern = ""})
    tools.target_rules = rules
    return #rules, targetEditorDecision(true, "target_rule_added", #rules, #rules)
end

function Targeting.updateTargetRule(tools, requestedIndex, patch)
    if type(tools) ~= "table" or type(patch) ~= "table" then return nil, targetEditorDecision(false, "rule_patch_required", 0, 0) end
    local rules = Targeting.sanitizeTargetRules(tools.target_rules)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    if not rules[index] then return nil, targetEditorDecision(false, "target_rule_missing", index, #rules) end
    for _, key in ipairs({"enabled", "name_pattern", "min_hp", "max_hp", "min_distance", "max_distance", "min_count", "max_count", "priority", "chase_policy"}) do
        if patch[key] ~= nil then rules[index][key] = patch[key] end
    end
    rules[index] = Targeting.sanitizeTargetRule(rules[index])
    tools.target_rules = rules
    return rules[index], targetEditorDecision(true, "target_rule_updated", index, #rules)
end

function Targeting.removeTargetRule(tools, requestedIndex)
    if type(tools) ~= "table" then return nil, targetEditorDecision(false, "tools_required", 0, 0) end
    local rules = Targeting.sanitizeTargetRules(tools.target_rules)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    if not rules[index] then return nil, targetEditorDecision(false, "target_rule_missing", index, #rules) end
    table.remove(rules, index)
    tools.target_rules = rules
    local nextIndex = #rules > 0 and math.min(index, #rules) or 0
    return nextIndex, targetEditorDecision(true, "target_rule_removed", nextIndex, #rules)
end

function Targeting.moveTargetRule(tools, requestedIndex, delta)
    if type(tools) ~= "table" then return nil, targetEditorDecision(false, "tools_required", 0, 0) end
    local rules = Targeting.sanitizeTargetRules(tools.target_rules)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    local target = index + ((tonumber(delta) or 0) < 0 and -1 or 1)
    if not rules[index] or target < 1 or target > #rules then return nil, targetEditorDecision(false, "target_rule_move_blocked", index, #rules) end
    rules[index], rules[target] = rules[target], rules[index]
    tools.target_rules = rules
    return target, targetEditorDecision(true, "target_rule_moved", target, #rules)
end

local function targetRuleReason(rule, candidate)
    if rule.enabled == false then return "disabled" end
    local name = Targeting.normalizedName(candidate.name or candidate)
    if rule.name_pattern ~= "" and not string.find(name, rule.name_pattern, 1, true) then return "name_mismatch" end
    local hp = tonumber(candidate.hp) or 100
    local distance = tonumber(candidate.distance) or 99
    local count = tonumber(candidate.monster_count) or 0
    if hp < rule.min_hp then return "hp_below_min" end
    if hp > rule.max_hp then return "hp_above_max" end
    if distance < rule.min_distance then return "distance_below_min" end
    if distance > rule.max_distance then return "distance_above_max" end
    if count < rule.min_count then return "count_below_min" end
    if count > rule.max_count then return "count_above_max" end
    return nil
end

function Targeting.matchTargetRule(candidate, rules)
    local sanitized = Targeting.sanitizeTargetRules(rules)
    local enabledCount = 0
    local rows = {}
    for index, rule in ipairs(sanitized) do
        if rule.enabled ~= false then
            enabledCount = enabledCount + 1
        end
        local reason = targetRuleReason(rule, candidate or {})
        rows[index] = {index = index, matched = reason == nil, reason_code = reason or "matched"}
        if reason == nil then return rule, index, enabledCount, rows end
    end
    return nil, nil, enabledCount, rows
end

local function appendPolicyName(result, seen, value)
    if #result >= MAX_NAME_POLICY_ENTRIES then
        return
    end
    local name = lowered(trimmed(value))
    if name == "" then
        return
    end
    name = string.sub(name, 1, MAX_NAME_POLICY_LENGTH)
    if seen[name] then
        return
    end
    seen[name] = true
    result[#result + 1] = name
end

function Targeting.sanitizeNameList(values)
    local result = {}
    local seen = {}
    if type(values) == "string" then
        for value in string.gmatch(values, "[^,;\r\n]+") do
            appendPolicyName(result, seen, value)
        end
    elseif type(values) == "table" then
        for _, value in ipairs(values) do
            appendPolicyName(result, seen, value)
        end
    end
    return result
end

function Targeting.parseNameList(text)
    return Targeting.sanitizeNameList(text)
end

function Targeting.formatNameList(values)
    return table.concat(Targeting.sanitizeNameList(values), ", ")
end

function Targeting.updateNameList(tools, key, text)
    if type(tools) ~= "table" or EDITABLE_NAME_POLICY_KEYS[key] ~= true then
        return nil, {allowed = false, reason = "invalid_name_policy_key"}
    end
    local names = Targeting.parseNameList(text)
    tools[key] = names
    return names, {
        allowed = true,
        reason = "name_policy_updated",
        key = key,
        count = #names,
        runtime_actions = false,
    }
end

function Targeting.normalizedName(value)
    if type(value) == "string" then
        return lowered(value)
    end
    if type(value) == "table" and value.getName then
        local ok, name = pcall(function()
            return value:getName()
        end)
        if ok and name then
            return lowered(name)
        end
    end
    return ""
end

function Targeting.isIgnoredName(name, ignoredNames)
    local normalized = Targeting.normalizedName(name)
    if normalized == "" then
        return false
    end
    for _, ignored in ipairs(ignoredNames or {}) do
        local needle = lowered(ignored)
        if needle ~= "" and string.find(normalized, needle, 1, true) then
            return true
        end
    end
    return false
end

function Targeting.creatureHasBlockingNpcIcon(icon, tools)
    local cfg = tools or {}
    if cfg.block_npc_icons == false then
        return false
    end
    return icon ~= nil and icon ~= false and icon ~= 0 and icon ~= ""
end

function Targeting.hasBlockingNpcIcon(icon, tools)
    return Targeting.creatureHasBlockingNpcIcon(icon, tools)
end

local function friendlySummonFragments(tools)
    local cfg = tools or {}
    if type(cfg.friendly_summon_name_fragments) == "table" and #cfg.friendly_summon_name_fragments > 0 then
        return cfg.friendly_summon_name_fragments
    end
    return DEFAULT_FRIENDLY_SUMMON_NAME_FRAGMENTS
end

function Targeting.isFriendlySummonName(name, tools)
    local cfg = tools or {}
    if cfg.block_friendly_summons == false then
        return false
    end
    local normalized = " " .. Targeting.normalizedName(name) .. " "
    if normalized == "  " then
        return false
    end
    for _, fragment in ipairs(friendlySummonFragments(cfg)) do
        local needle = lowered(fragment)
        if needle ~= "" and string.find(normalized, needle, 1, true) then
            return true
        end
    end
    return false
end

function Targeting.isFriendlySummonCandidate(candidate, tools)
    local cfg = tools or {}
    if cfg.block_friendly_summons == false then
        return false
    end
    if type(candidate) ~= "table" then
        return Targeting.isFriendlySummonName(candidate, cfg)
    end
    if candidate.is_friendly_summon == true or candidate.is_summon == true or candidate.is_familiar == true then
        return true
    end
    return Targeting.isFriendlySummonName(candidate.name or candidate, cfg)
end

function Targeting.priorityRank(name, priorityNames)
    local normalized = Targeting.normalizedName(name)
    for index, needle in ipairs(priorityNames or {}) do
        local candidate = lowered(needle)
        if candidate ~= "" and string.find(normalized, candidate, 1, true) then
            return index
        end
    end
    return 999
end

function Targeting.scoreCandidate(candidate, tools)
    local data = candidate or {}
    local cfg = tools or {}
    local rank = tonumber(data.rank)
    if not rank then
        rank = Targeting.priorityRank(data.name or "", cfg.priority_names or {})
    end
    local distance = tonumber(data.distance) or 99
    local hp = tonumber(data.hp) or 100
    if cfg.prefer_low_hp then
        return rank * 10000 + hp * 100 + distance
    end
    return rank * 10000 + distance * 100 + hp
end

function Targeting.targetCandidateScore(candidate, tools)
    local score = Targeting.scoreCandidate(candidate, tools)
    if tonumber(score) then
        return tonumber(score)
    end
    return 99999999
end

function Targeting.bestCandidate(candidates, tools)
    local best = nil
    local bestDecision = nil
    for _, candidate in ipairs(candidates or {}) do
        local decision = Targeting.decision(candidate, tools)
        if decision.eligible and (not bestDecision or decision.score < bestDecision.score) then
            best = candidate
            bestDecision = decision
        end
    end
    return best, bestDecision
end

function Targeting.creatureTypeDecision(probe)
    local data = probe or {}
    if data.missing == true or data.is_local_player == true then
        return false
    end
    if data.ignored_name == true or data.blocking_npc_icon == true or data.friendly_summon == true then
        return false
    end
    if data.is_npc == true or data.is_player == true then
        return false
    end
    if data.attackable == false or data.can_be_attacked == false or data.targetable == false then
        return false
    end
    if data.is_monster ~= nil then
        return data.is_monster == true
    end
    return false
end

function Targeting.decision(candidate, tools)
    if type(candidate) ~= "table" then
        return {
            eligible = false,
            reason = "no_candidate",
            score = 99999999,
            summary = "target scorer idle",
            rule_explanation = explanation("no_candidate", "blocked"),
        }
    end
    local cfg = tools or {}
    local name = Targeting.normalizedName(candidate.name or candidate)
    if name == "" then
        return {
            eligible = false,
            reason = "missing_name",
            score = 99999999,
            summary = "target missing name",
            rule_explanation = explanation("missing_name", "blocked"),
        }
    end
    if Targeting.isIgnoredName(name, cfg.ignored_names or {}) then
        return {
            eligible = false,
            reason = "ignored_name",
            name = name,
            score = 99999999,
            summary = "ignored " .. name,
            rule_explanation = explanation("ignored_name", "blocked", {name = name}),
        }
    end
    if Targeting.isFriendlySummonCandidate(candidate, cfg) then
        return {
            eligible = false,
            reason = "friendly_summon",
            name = name,
            score = 99999999,
            summary = "friendly summon/familiar " .. name,
            rule_explanation = explanation("friendly_summon", "blocked", {name = name}),
        }
    end
    if cfg.require_reachable_target == true and candidate.reachable == false then
        return {
            eligible = false,
            reason = "unreachable",
            name = name,
            score = 99999999,
            summary = "unreachable " .. name,
            rule_explanation = explanation("unreachable", "blocked", {name = name}),
        }
    end
    local targetRule, targetRuleIndex, enabledRuleCount, ruleRows = Targeting.matchTargetRule(candidate, cfg.target_rules)
    local traceValues = {
        name = name,
        hp = tonumber(candidate.hp) or 100,
        distance = tonumber(candidate.distance) or 99,
        monster_count = tonumber(candidate.monster_count) or 0,
    }
    if enabledRuleCount > 0 and not targetRule then
        return {
            eligible = false,
            reason = "no_target_rule",
            name = name,
            score = 99999999,
            summary = "no target rule for " .. name,
            rule_explanation = explanation("no_target_rule", "blocked", traceValues, ruleRows),
        }
    end
    local rank = candidate.rank or Targeting.priorityRank(name, cfg.priority_names or {})
    local scored = {
        name = name,
        rank = rank,
        distance = candidate.distance,
        hp = candidate.hp,
    }
    local score = Targeting.scoreCandidate(scored, cfg)
    if targetRule then
        score = targetRule.priority * 1000000000 + targetRuleIndex * 10000000 + math.min(score, 9999999)
    end
    return {
        eligible = true,
        reason = "scored",
        name = name,
        rank = rank,
        score = score,
        target_rule_index = targetRuleIndex,
        target_rule_priority = targetRule and targetRule.priority or nil,
        chase_policy = targetRule and targetRule.chase_policy or "inherit",
        summary = Targeting.summary(scored, cfg),
        rule_explanation = explanation(targetRule and "rule_matched" or "scored_without_rules", "matched", traceValues, ruleRows, targetRuleIndex),
    }
end

function Targeting.summary(candidate, tools)
    if type(candidate) ~= "table" then
        return "target scorer idle"
    end
    local rank = candidate.rank or Targeting.priorityRank(candidate.name or "", (tools or {}).priority_names or {})
    return "rank " .. tostring(rank) ..
        " dist " .. tostring(candidate.distance or "?") ..
        " hp " .. tostring(candidate.hp or "?")
end

function Targeting.configSummary(tools, helpers)
    local cfg = tools or {}
    helpers = helpers or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    return "Targeting " .. onOffText(cfg.auto_attack == true) ..
        " | Chase " .. onOffText(cfg.chase == true) ..
        " | Range " .. tostring(cfg.attack_range or "?") ..
        " | Rules " .. tostring(#Targeting.sanitizeTargetRules(cfg.target_rules)) ..
        " | Ignore " .. tostring(#Targeting.sanitizeNameList(cfg.ignored_names)) ..
        " | Priority " .. tostring(#Targeting.sanitizeNameList(cfg.priority_names)) ..
        " | PZ guard " .. onOffText(cfg.pause_in_pz == true)
end

function Targeting.contract()
    return {
        module = "ctoa_helper_targeting",
        mode = "passive",
        owns_target_score = true,
        owns_best_candidate = true,
        owns_creature_type_decision = true,
        owns_ignored_names = true,
        owns_editable_name_policy = true,
        owns_target_rule_editor = true,
        owns_target_rule_matching = true,
        target_rule_limit = MAX_TARGET_RULES,
        target_rule_name_limit = MAX_TARGET_RULE_NAME_LENGTH,
        name_policy_max_entries = MAX_NAME_POLICY_ENTRIES,
        name_policy_max_length = MAX_NAME_POLICY_LENGTH,
        owns_npc_icon_guard = true,
        owns_blocking_npc_icon_value = true,
        owns_friendly_summon_guard = true,
        owns_friendly_summon_name = true,
        owns_target_candidate_score = true,
        owns_config_summary = true,
        owns_targeting_summary_text = true,
        runtime_actions = false,
        attacks = false,
        casts = false,
        creature_scan = false,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_TARGETING = Targeting

return Targeting
