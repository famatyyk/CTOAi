-- ctoa_helper_combat_runtime.lua [CTOA OTClient Native]
-- Passive combat runtime adapter planner. This module never scans, attacks, or casts.

local CombatRuntime = rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME") or {}

local MAX_ROTATION_RULES = 16
local MAX_COMBAT_ACTION_RULES = 16
local MAX_SPELL_WORDS = 64

local function explanation(lane, reason, status, values, rows, selectedIndex, state)
    local owner = rawget(_G, "CTOA_HELPER_RULE_EXPLANATIONS")
    if type(owner) ~= "table" or type(owner.trace) ~= "function" then return nil end
    local env = type(state) == "table" and state or {}
    return owner.trace(lane, reason, {
        status = status,
        selected_index = selectedIndex,
        observation_status = env.observation_status or "current",
        observed_at_ms = env.observed_at_ms,
        now_ms = env.now_ms,
        values = values,
        rules = rows,
    })
end

local function boolValue(value)
    return value == true
end

local function clampInteger(value, minimum, maximum, fallback)
    local number = math.floor(tonumber(value) or fallback or minimum)
    return math.max(minimum, math.min(maximum, number))
end

local function cleanWords(value)
    local text = tostring(value or "")
    text = string.gsub(text, "[%c]", " ")
    text = string.gsub(text, "%s+", " ")
    text = string.gsub(string.gsub(text, "^%s+", ""), "%s+$", "")
    return string.sub(text, 1, MAX_SPELL_WORDS)
end

local function cleanStateId(value)
    local text = string.lower(cleanWords(value))
    text = string.gsub(text, "[^a-z0-9_%-]", "_")
    return string.sub(text, 1, 48)
end

function CombatRuntime.sanitizeRotationRule(rule)
    local source = type(rule) == "table" and rule or {}
    local useMobCount = source.use_mob_count ~= false
    local minimum = useMobCount and clampInteger(source.min_nearby, 1, 20, 1) or 0
    local maximum = clampInteger(source.max_nearby, minimum, 99, 99)
    local words = cleanWords(source.words)
    return {
        enabled = source.enabled ~= false and words ~= "",
        words = words,
        use_mob_count = useMobCount,
        min_nearby = minimum,
        max_nearby = maximum,
        scan_range = clampInteger(source.scan_range, 1, 10, 1),
        cooldown_ms = clampInteger(source.cooldown_ms, 250, 60000, 2000),
        directional = source.directional == true,
    }
end

function CombatRuntime.sanitizeRotationRules(rules)
    local result = {}
    for _, rule in ipairs(type(rules) == "table" and rules or {}) do
        if #result >= MAX_ROTATION_RULES then
            break
        end
        result[#result + 1] = CombatRuntime.sanitizeRotationRule(rule)
    end
    return result
end


local function editorDecision(allowed, reason, index, count)
    return {
        allowed = allowed == true,
        reason = reason,
        index = index,
        count = count,
        runtime_actions = false,
        dispatch_allowed = false,
    }
end

function CombatRuntime.rotationRuleState(tools, requestedIndex)
    local cfg = type(tools) == "table" and tools or {}
    local rules = CombatRuntime.sanitizeRotationRules(cfg.rotation_spells)
    local count = #rules
    local index = count > 0 and clampInteger(requestedIndex, 1, count, 1) or 0
    local rule = index > 0 and rules[index] or nil
    return {
        index = index,
        count = count,
        rule = rule,
        summary = count > 0 and (tostring(index) .. "/" .. tostring(count) .. " " .. tostring(rule.words ~= "" and rule.words or "new spell")) or "0/0 no spell rules",
    }
end

function CombatRuntime.replaceRotationRules(tools, rules)
    if type(tools) ~= "table" then
        return nil, editorDecision(false, "tools_required", 0, 0)
    end
    tools.rotation_spells = CombatRuntime.sanitizeRotationRules(rules)
    tools.rotation_preset = "custom"
    return tools.rotation_spells, editorDecision(true, "rotation_rules_replaced", #tools.rotation_spells > 0 and 1 or 0, #tools.rotation_spells)
end

function CombatRuntime.addRotationRule(tools, draft)
    if type(tools) ~= "table" then
        return nil, editorDecision(false, "tools_required", 0, 0)
    end
    local rules = CombatRuntime.sanitizeRotationRules(tools.rotation_spells)
    if #rules >= MAX_ROTATION_RULES then
        return nil, editorDecision(false, "rotation_rule_limit", #rules, #rules)
    end
    local rule = CombatRuntime.sanitizeRotationRule(draft or {
        enabled = false,
        words = "",
        use_mob_count = true,
        min_nearby = 1,
        max_nearby = 99,
        scan_range = 1,
        cooldown_ms = 2000,
    })
    rules[#rules + 1] = rule
    tools.rotation_spells = rules
    tools.rotation_preset = "custom"
    return #rules, editorDecision(true, "rotation_rule_added", #rules, #rules)
end

function CombatRuntime.updateRotationRule(tools, requestedIndex, patch)
    if type(tools) ~= "table" or type(patch) ~= "table" then
        return nil, editorDecision(false, "rule_patch_required", 0, 0)
    end
    local rules = CombatRuntime.sanitizeRotationRules(tools.rotation_spells)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    local current = rules[index]
    if not current then
        return nil, editorDecision(false, "rotation_rule_missing", index, #rules)
    end
    local editable = {"enabled", "words", "use_mob_count", "min_nearby", "max_nearby", "scan_range", "cooldown_ms", "directional"}
    for _, key in ipairs(editable) do
        if patch[key] ~= nil then
            current[key] = patch[key]
        end
    end
    rules[index] = CombatRuntime.sanitizeRotationRule(current)
    tools.rotation_spells = rules
    tools.rotation_preset = "custom"
    return rules[index], editorDecision(true, "rotation_rule_updated", index, #rules)
end

function CombatRuntime.removeRotationRule(tools, requestedIndex)
    if type(tools) ~= "table" then
        return nil, editorDecision(false, "tools_required", 0, 0)
    end
    local rules = CombatRuntime.sanitizeRotationRules(tools.rotation_spells)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    if not rules[index] then
        return nil, editorDecision(false, "rotation_rule_missing", index, #rules)
    end
    table.remove(rules, index)
    tools.rotation_spells = rules
    tools.rotation_preset = "custom"
    local nextIndex = #rules > 0 and math.min(index, #rules) or 0
    return nextIndex, editorDecision(true, "rotation_rule_removed", nextIndex, #rules)
end

function CombatRuntime.moveRotationRule(tools, requestedIndex, delta)
    if type(tools) ~= "table" then
        return nil, editorDecision(false, "tools_required", 0, 0)
    end
    local rules = CombatRuntime.sanitizeRotationRules(tools.rotation_spells)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    local target = index + (tonumber(delta) and (tonumber(delta) < 0 and -1 or 1) or 0)
    if not rules[index] or target < 1 or target > #rules or target == index then
        return nil, editorDecision(false, "rotation_rule_move_blocked", index, #rules)
    end
    rules[index], rules[target] = rules[target], rules[index]
    tools.rotation_spells = rules
    tools.rotation_preset = "custom"
    return target, editorDecision(true, "rotation_rule_moved", target, #rules)
end

function CombatRuntime.sanitizeCombatActionRule(rule)
    local source = type(rule) == "table" and rule or {}
    local kind = tostring(source.kind or "rune")
    if kind ~= "stance" then kind = "rune" end
    local minCount = clampInteger(source.min_count, 0, 20, kind == "stance" and 1 or 0)
    local stanceMode = tostring(source.stance_mode or "offensive")
    if stanceMode ~= "defensive" then stanceMode = "offensive" end
    return {
        enabled = source.enabled == true,
        kind = kind,
        action_text = cleanWords(source.action_text or source.rune_name or source.spell),
        hotkey = string.sub(cleanWords(source.hotkey or source.actionbar_slot), 1, 16),
        min_count = minCount,
        max_count = clampInteger(source.max_count, minCount, 99, 99),
        cooldown_ms = clampInteger(source.cooldown_ms, 250, 60000, kind == "stance" and 10000 or 1000),
        stance_mode = stanceMode,
        state_id = cleanStateId(source.state_id),
        require_target = source.require_target ~= false,
        pvp_safe = source.pvp_safe ~= false,
    }
end

function CombatRuntime.sanitizeCombatActionRules(rules)
    local result = {}
    for _, rule in ipairs(type(rules) == "table" and rules or {}) do
        if #result >= MAX_COMBAT_ACTION_RULES then break end
        result[#result + 1] = CombatRuntime.sanitizeCombatActionRule(rule)
    end
    return result
end


function CombatRuntime.combatActionRuleState(tools, requestedIndex)
    local cfg = type(tools) == "table" and tools or {}
    local rules = CombatRuntime.sanitizeCombatActionRules(cfg.combat_action_rules)
    local count = #rules
    local index = count > 0 and clampInteger(requestedIndex, 1, count, 1) or 0
    local rule = index > 0 and rules[index] or nil
    local label = rule and (rule.action_text ~= "" and rule.action_text or ("new " .. rule.kind)) or "no action rules"
    return {index = index, count = count, rule = rule, summary = tostring(index) .. "/" .. tostring(count) .. " " .. label}
end

function CombatRuntime.replaceCombatActionRules(tools, rules)
    if type(tools) ~= "table" then return nil, editorDecision(false, "tools_required", 0, 0) end
    tools.combat_action_rules = CombatRuntime.sanitizeCombatActionRules(rules)
    return tools.combat_action_rules, editorDecision(true, "combat_action_rules_replaced", #tools.combat_action_rules > 0 and 1 or 0, #tools.combat_action_rules)
end

function CombatRuntime.addCombatActionRule(tools, draft)
    if type(tools) ~= "table" then return nil, editorDecision(false, "tools_required", 0, 0) end
    local rules = CombatRuntime.sanitizeCombatActionRules(tools.combat_action_rules)
    if #rules >= MAX_COMBAT_ACTION_RULES then return nil, editorDecision(false, "combat_action_rule_limit", #rules, #rules) end
    rules[#rules + 1] = CombatRuntime.sanitizeCombatActionRule(draft or {enabled = false, kind = "rune"})
    tools.combat_action_rules = rules
    return #rules, editorDecision(true, "combat_action_rule_added", #rules, #rules)
end

function CombatRuntime.updateCombatActionRule(tools, requestedIndex, patch)
    if type(tools) ~= "table" or type(patch) ~= "table" then return nil, editorDecision(false, "rule_patch_required", 0, 0) end
    local rules = CombatRuntime.sanitizeCombatActionRules(tools.combat_action_rules)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    if not rules[index] then return nil, editorDecision(false, "combat_action_rule_missing", index, #rules) end
    for _, key in ipairs({"enabled", "kind", "action_text", "hotkey", "min_count", "max_count", "cooldown_ms", "stance_mode", "state_id", "require_target", "pvp_safe"}) do
        if patch[key] ~= nil then rules[index][key] = patch[key] end
    end
    rules[index] = CombatRuntime.sanitizeCombatActionRule(rules[index])
    tools.combat_action_rules = rules
    return rules[index], editorDecision(true, "combat_action_rule_updated", index, #rules)
end

function CombatRuntime.removeCombatActionRule(tools, requestedIndex)
    if type(tools) ~= "table" then return nil, editorDecision(false, "tools_required", 0, 0) end
    local rules = CombatRuntime.sanitizeCombatActionRules(tools.combat_action_rules)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    if not rules[index] then return nil, editorDecision(false, "combat_action_rule_missing", index, #rules) end
    table.remove(rules, index)
    tools.combat_action_rules = rules
    local nextIndex = #rules > 0 and math.min(index, #rules) or 0
    return nextIndex, editorDecision(true, "combat_action_rule_removed", nextIndex, #rules)
end

function CombatRuntime.moveCombatActionRule(tools, requestedIndex, delta)
    if type(tools) ~= "table" then return nil, editorDecision(false, "tools_required", 0, 0) end
    local rules = CombatRuntime.sanitizeCombatActionRules(tools.combat_action_rules)
    local index = clampInteger(requestedIndex, 1, math.max(1, #rules), 1)
    local target = index + ((tonumber(delta) or 0) < 0 and -1 or 1)
    if not rules[index] or target < 1 or target > #rules then return nil, editorDecision(false, "combat_action_rule_move_blocked", index, #rules) end
    rules[index], rules[target] = rules[target], rules[index]
    tools.combat_action_rules = rules
    return target, editorDecision(true, "combat_action_rule_moved", target, #rules)
end

local function runtimeBlockedReason(tools, context)
    local cfg = tools or {}
    local env = context or {}
    if not boolValue(cfg.auto_attack) and not boolValue(cfg.spell_rotation) and not boolValue(cfg.rune_enabled) then
        return "runtime_disabled"
    end
    if boolValue(cfg.pause_in_pz) and boolValue(env.in_protection_zone) then
        return "protection_zone"
    end
    if env.online == false then
        return "offline"
    end
    if env.has_safe_target == false and boolValue(cfg.rune_requires_target) then
        return "target_required"
    end
    return nil
end

function CombatRuntime.plan(tools, context, target_decision)
    local blocked = runtimeBlockedReason(tools, context)
    if blocked then
        return {
            allowed = false,
            reason = blocked,
            target = "none",
            next_action = "hold",
        }
    end
    local decision = target_decision or {}
    if decision.eligible == false then
        return {
            allowed = false,
            reason = decision.reason or "target_not_eligible",
            target = decision.name or "none",
            next_action = "hold",
        }
    end
    local cfg = tools or {}
    local action = "target"
    if boolValue(cfg.spell_rotation) then
        action = "plan_spell"
    elseif boolValue(cfg.rune_enabled) then
        action = "plan_rune"
    end
    return {
        allowed = true,
        reason = "planned",
        target = decision.name or "selected",
        score = decision.score or 0,
        next_action = action,
    }
end

function CombatRuntime.summary(plan)
    if type(plan) ~= "table" then
        return "combat adapter idle"
    end
    return tostring(plan.next_action or "hold") ..
        " | " .. tostring(plan.reason or "unknown") ..
        " | " .. tostring(plan.target or "none")
end

function CombatRuntime.adapterSummary(tools, context, target_decision)
    local plan = CombatRuntime.plan(tools, context, target_decision)
    local text = CombatRuntime.summary(plan)
    if text == "" then
        text = tostring(plan.next_action or "hold") .. " | " .. tostring(plan.reason or "unknown")
    end
    return text, plan
end

function CombatRuntime.magicSummary(tools, helpers)
    local cfg = tools or {}
    helpers = helpers or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local actionbarSlotText = helpers.actionbarSlotText or tostring
    local resolveActionbarSlot = helpers.resolveActionbarSlot or function(slot, hotkey)
        return slot or hotkey
    end
    local runeSlot = actionbarSlotText(resolveActionbarSlot(cfg.rune_actionbar_slot, cfg.rune_hotkey))
    return "Rotation " .. onOffText(cfg.spell_rotation == true) ..
        " | Preset " .. tostring(cfg.rotation_preset or "custom") ..
        " | Rules " .. tostring(#CombatRuntime.sanitizeRotationRules(cfg.rotation_spells)) ..
        " | Rune " .. onOffText(cfg.rune_enabled == true) .. " " .. runeSlot ..
        " | Exeta " .. onOffText(cfg.auto_exeta == true)
end

function CombatRuntime.msLeftText(untilMs, now)
    local left = math.max(0, (untilMs or 0) - (now or 0))
    if left <= 0 then
        return "0.0s"
    end
    return string.format("%.1fs", left / 1000)
end

local function runeBlockedReason(tools, state, actionRule)
    local cfg = tools or {}
    local env = state or {}
    local rule = type(actionRule) == "table" and actionRule or nil
    if not boolValue(cfg.rune_enabled) then
        return "runtime_disabled"
    end
    local requiresTarget = boolValue(cfg.rune_requires_target)
    if rule then requiresTarget = rule.require_target == true end
    if requiresTarget and not boolValue(env.target_present) then
        return "target_required"
    end
    local visible = tonumber(env.visible) or 0
    if rule and visible < rule.min_count then
        return "count_below_min"
    end
    if rule and visible > rule.max_count then
        return "count_above_max"
    end
    if not rule and visible < (tonumber(cfg.rune_min_visible) or 1) then
        return "count_below_min"
    end
    local now = tonumber(env.now_ms) or 0
    if now < (tonumber(cfg.attack_action_lock_until_ms) or 0) then
        return "action_lock"
    end
    if now - (tonumber(cfg.last_rune_ms) or 0) < (tonumber(rule and rule.cooldown_ms or cfg.rune_cooldown_ms) or 1000) then
        return "cooldown"
    end
    return nil
end

function CombatRuntime.runeReady(tools, state, actionRule)
    return runeBlockedReason(tools, state, actionRule) == nil
end

local function monsterCountForRange(scan, range)
    local snapshot = scan or {}
    local value = tonumber(range) or 1
    if value <= 1 then
        return tonumber(snapshot.adjacent) or 0
    end
    if value == 2 then
        return tonumber(snapshot.close) or 0
    end
    return tonumber((snapshot.by_range or {})[value]) or 0
end

local function directionalSpell(words, spell)
    if spell and spell.directional == true then return true end
    return string.lower(tostring(words or "")) == "exori min"
end

function CombatRuntime.bestDirectionalFacing(scan)
    local snapshot = scan or {}
    local hits = snapshot.directional_hits or {}
    local current = tonumber(snapshot.facing_direction)
    local bestDirection = current or 0
    local bestCount = tonumber(hits[bestDirection]) or 0
    for direction = 0, 3 do
        local count = tonumber(hits[direction]) or 0
        if count > bestCount then
            bestDirection = direction
            bestCount = count
        end
    end
    return bestDirection, bestCount
end

function CombatRuntime.recordDirectionalHit(scan, dx, dy)
    local hits = (scan or {}).directional_hits
    if type(hits) ~= "table" then return scan end
    if dy == -1 then hits[0] = (tonumber(hits[0]) or 0) + 1 end
    if dx == 1 then hits[1] = (tonumber(hits[1]) or 0) + 1 end
    if dy == 1 then hits[2] = (tonumber(hits[2]) or 0) + 1 end
    if dx == -1 then hits[3] = (tonumber(hits[3]) or 0) + 1 end
    return scan
end

function CombatRuntime.rotationSpellRows(spells, state)
    local rows = {}
    local env = state or {}
    local scan = env.scan or {}
    local lastCasts = env.last_spell_casts or {}
    for _, spell in ipairs(CombatRuntime.sanitizeRotationRules(spells)) do
        local range = spell.scan_range or env.rotation_scan_range or 1
        local mobCount = monsterCountForRange(scan, range)
        local turnDirection = nil
        if directionalSpell(spell.words, spell) then
            turnDirection, mobCount = CombatRuntime.bestDirectionalFacing(scan)
        end
        rows[#rows + 1] = {
            words = spell.words,
            mob_count = mobCount,
            min_nearby = tonumber(spell.min_nearby) or 1,
            max_nearby = tonumber(spell.max_nearby) or 99,
            last_cast_ms = tonumber(lastCasts[spell.words]) or 0,
            cooldown_ms = spell.cooldown_ms,
            enabled = spell.enabled ~= false,
            use_mob_count = spell.use_mob_count ~= false,
            directional = directionalSpell(spell.words, spell),
            turn_direction = turnDirection,
        }
    end
    return rows
end

function CombatRuntime.spellReadiness(spells, state)
    local rows = {}
    local now = tonumber((state or {}).now_ms) or 0
    local defaultCooldown = tonumber((state or {}).default_cooldown_ms) or 1050
    for _, spell in ipairs(spells or {}) do
        local last = tonumber(spell.last_cast_ms) or 0
        local cd = tonumber(spell.cooldown_ms) or defaultCooldown
        rows[#rows + 1] = {
            words = spell.words,
            mob_count = tonumber(spell.mob_count) or 0,
            min_nearby = tonumber(spell.min_nearby) or 1,
            max_nearby = tonumber(spell.max_nearby) or 99,
            ready = now - last >= cd,
            cooldown_until_ms = last + cd,
            enabled = spell.enabled ~= false,
            directional = spell.directional == true,
            turn_direction = spell.turn_direction,
        }
    end
    return rows
end

function CombatRuntime.rotationSpell(spells, state)
    local env = state or {}
    local now = tonumber(env.now_ms) or 0
    if now < (tonumber(env.action_lock_until_ms) or 0) then
        return nil, explanation("spell", "action_lock", "blocked", {now_ms = now}, {}, nil, env)
    end
    if now - (tonumber(env.last_attack_spell_ms) or 0) < (tonumber(env.rotation_interval_ms) or 1050) then
        return nil, explanation("spell", "rotation_interval", "blocked", {now_ms = now}, {}, nil, env)
    end
    local rows = CombatRuntime.spellReadiness(spells, {
        now_ms = now,
        default_cooldown_ms = env.rotation_interval_ms or 1050,
    })
    local selected = nil
    local selectedIndex = nil
    local ruleRows = {}
    for index, spell in ipairs(rows) do
        local mobCount = tonumber(spell.mob_count) or 0
        local minNearby = tonumber(spell.min_nearby) or 1
        local maxNearby = tonumber(spell.max_nearby) or 99
        local reason = nil
        if spell.enabled == false then reason = "disabled"
        elseif tostring(spell.words or "") == "" then reason = "missing_words"
        elseif mobCount < minNearby then reason = "count_below_min"
        elseif mobCount > maxNearby then reason = "count_above_max"
        elseif spell.ready ~= true then reason = "cooldown" end
        ruleRows[index] = {index = index, matched = reason == nil, reason_code = reason or "matched", values = {mob_count = mobCount}}
        if reason == nil then
            if not selected then
                selected = spell
                selectedIndex = index
            elseif spell.directional == true and string.lower(tostring(selected.words or "")) == "exori" then
                ruleRows[selectedIndex].reason_code = "matched_not_selected"
                ruleRows[selectedIndex].matched = false
                selected = spell
                selectedIndex = index
            end
        end
    end
    if selectedIndex then
        ruleRows[selectedIndex].reason_code = "selected"
        return selected, explanation("spell", "rule_selected", "matched", {now_ms = now}, ruleRows, selectedIndex, env)
    end
    return nil, explanation("spell", #rows > 0 and "no_spell_rule" or "no_rules", "blocked", {now_ms = now}, ruleRows, nil, env)
end

function CombatRuntime.selectRotationSpell(tools, scan, now)
    local cfg = type(tools) == "table" and tools or {}
    local spells = CombatRuntime.rotationSpellRows(cfg.rotation_spells or {}, {
        scan = scan or {},
        rotation_scan_range = cfg.rotation_scan_range,
        last_spell_casts = cfg.last_spell_casts or {},
    })
    return CombatRuntime.rotationSpell(spells, {
        now_ms = now,
        action_lock_until_ms = cfg.attack_action_lock_until_ms,
        last_attack_spell_ms = cfg.last_attack_spell_ms,
        rotation_interval_ms = cfg.rotation_interval_ms,
    })
end

function CombatRuntime.stanceAction(tools, state)
    local cfg = tools or {}
    local env = state or {}
    if cfg.auto_stance ~= true then return nil, explanation("combat_action", "stance_runtime_disabled", "blocked", {}, {}, nil, env) end
    if env.target_present ~= true then return nil, explanation("combat_action", "target_required", "blocked", {}, {}, nil, env) end
    local now = tonumber(env.now_ms) or 0
    local monsters = tonumber(env.nearby) or 0
    local actionRules = CombatRuntime.sanitizeCombatActionRules(cfg.combat_action_rules)
    local stateDecisions = type(env.spell_state_decisions) == "table" and env.spell_state_decisions or {}
    if #actionRules > 0 then
        local rows = {}
        for index, rule in ipairs(actionRules) do
            local stateAllowed = rule.state_id == "" or (type(stateDecisions[rule.state_id]) == "table" and stateDecisions[rule.state_id].allowed == true)
            local reason = nil
            if not rule.enabled then reason = "disabled"
            elseif rule.kind ~= "stance" then reason = "kind_mismatch"
            elseif rule.action_text == "" then reason = "missing_action"
            elseif not stateAllowed then reason = "state_blocked"
            elseif monsters < rule.min_count then reason = "count_below_min"
            elseif monsters > rule.max_count then reason = "count_above_max"
            elseif now - (tonumber(cfg.last_stance_ms) or 0) < rule.cooldown_ms then reason = "cooldown" end
            rows[index] = {index = index, matched = reason == nil, reason_code = reason or "selected", values = {monster_count = monsters}}
            if reason == nil then
                return {kind = "stance", stance = rule.stance_mode, fight_mode = rule.stance_mode, spell = rule.action_text, action_index = index, state_id = rule.state_id},
                    explanation("combat_action", "rule_selected", "matched", {monster_count = monsters, kind = "stance"}, rows, index, env)
            end
        end
        return nil, explanation("combat_action", "no_stance_rule", "blocked", {monster_count = monsters, kind = "stance"}, rows, nil, env)
    end
    return nil, explanation("combat_action", "no_rules", "blocked", {kind = "stance"}, {}, nil, env)
end

function CombatRuntime.runeAction(tools, state)
    local cfg = tools or {}
    local env = state or {}
    local rows = {}
    for index, rule in ipairs(CombatRuntime.sanitizeCombatActionRules(cfg.combat_action_rules)) do
        local reason = nil
        if not rule.enabled then reason = "disabled"
        elseif rule.kind ~= "rune" then reason = "kind_mismatch"
        elseif rule.action_text == "" then reason = "missing_action"
        else reason = runeBlockedReason(cfg, env, rule) end
        if reason == nil and rule.pvp_safe ~= false and env.rune_target_safe == false then reason = "pvp_unsafe" end
        rows[index] = {index = index, matched = reason == nil, reason_code = reason or "selected", values = {monster_count = tonumber(env.visible) or 0}}
        if reason == nil then
            return {kind = "rune", rune_name = rule.action_text, hotkey = rule.hotkey, actionbar_slot = rule.hotkey, action_index = index},
                explanation("combat_action", "rule_selected", "matched", {monster_count = tonumber(env.visible) or 0, kind = "rune"}, rows, index, env)
        end
    end
    if type(cfg.combat_action_rules) == "table" and #cfg.combat_action_rules > 0 then
        return nil, explanation("combat_action", "no_rune_rule", "blocked", {kind = "rune"}, rows, nil, env)
    end
    local fallbackReason = runeBlockedReason(cfg, env)
    if fallbackReason == nil and env.rune_target_safe == false then fallbackReason = "pvp_unsafe" end
    if fallbackReason == nil then return {kind = "rune"}, explanation("combat_action", "legacy_rune_selected", "matched", {kind = "rune"}, {}, nil, env) end
    return nil, explanation("combat_action", fallbackReason, "blocked", {kind = "rune"}, {}, nil, env)
end

function CombatRuntime.offensiveAction(tools, state)
    local cfg = tools or {}
    local env = state or {}
    local targetPresent = boolValue(env.target_present)
    local now = tonumber(env.now_ms) or 0
    if env.blocked_reason then
        return nil
    end
    if targetPresent and env.target_in_range == false then
        return nil
    end
    if now < (tonumber(cfg.attack_action_lock_until_ms) or 0) then
        return nil
    end
    if boolValue(env.recovery_gap_active) then
        return nil
    end

    local stance, stanceTrace = CombatRuntime.stanceAction(cfg, env)
    if stance then return stance, stanceTrace end

    local visible = tonumber(env.visible) or 0
    if boolValue(cfg.auto_exeta) and targetPresent and visible >= (tonumber(cfg.exeta_min_visible) or 1) and now - (tonumber(cfg.last_exeta_ms) or 0) >= (tonumber(cfg.exeta_interval_ms) or 5000) then
        return {
            kind = "exeta",
            spell = (cfg.exeta_spells or {})[tonumber(cfg.exeta_index) or 1],
        }
    end

    local rotationSpell = env.rotation_spell
    local runeAction, runeTrace = CombatRuntime.runeAction(cfg, env)
    if cfg.magic_priority == "rune" and runeAction then
        return runeAction, runeTrace
    end
    if rotationSpell then
        return {
            kind = "rotation",
            spell = rotationSpell,
        }
    end
    if runeAction then
        return runeAction, runeTrace
    end
    return nil, runeTrace or stanceTrace
end

function CombatRuntime.dispatchDescriptor(action, tools)
    local item = type(action) == "table" and action or {}
    local cfg = type(tools) == "table" and tools or {}
    if item.kind == "stance" or item.kind == "exeta" then
        return {kind = "spell", words = tostring(item.spell or ""), fight_mode = item.fight_mode}
    end
    if item.kind == "rotation" and type(item.spell) == "table" then
        return {kind = "spell", words = tostring(item.spell.words or ""), turn_direction = item.spell.turn_direction}
    end
    if item.kind == "rune" then
        return {kind = "actionbar", slot = item.actionbar_slot or cfg.rune_actionbar_slot, hotkey = item.hotkey or cfg.rune_hotkey}
    end
    return {kind = "none"}
end

function CombatRuntime.recordActionSuccess(tools, action, now)
    local cfg = type(tools) == "table" and tools or {}
    local item = type(action) == "table" and action or {}
    local current = tonumber(now) or 0
    if item.kind == "stance" then
        cfg.last_stance_ms = current
        cfg.active_stance = item.stance or "neutral"
        cfg.last_spell_state_casts = type(cfg.last_spell_state_casts) == "table" and cfg.last_spell_state_casts or {}
        if tostring(item.state_id or "") ~= "" then cfg.last_spell_state_casts[item.state_id] = current end
    elseif item.kind == "exeta" then
        cfg.last_exeta_ms = current
        local count = type(cfg.exeta_spells) == "table" and #cfg.exeta_spells or 0
        if count > 0 then cfg.exeta_index = ((tonumber(cfg.exeta_index) or 1) % count) + 1 end
    elseif item.kind == "rotation" and type(item.spell) == "table" then
        cfg.last_rotation_ms = current
        cfg.last_spell_casts = type(cfg.last_spell_casts) == "table" and cfg.last_spell_casts or {}
        cfg.last_spell_casts[tostring(item.spell.words or "")] = current
    elseif item.kind == "rune" then
        cfg.last_rune_ms = current
    end
    return cfg
end

function CombatRuntime.actionStatusText(action, state)
    local item = action or {}
    local env = state or {}
    local kind = item.kind or env.kind
    if kind == "blocked" then
        return "Offensive action blocked: " .. tostring(env.reason or item.reason or "unknown")
    end
    if kind == "action_lock" then
        return "Offensive action blocked: action lock"
    end
    if kind == "recovery_gap" then
        return "Offensive action blocked: recovery gap"
    end
    if kind == "exeta" then
        return "Auto exeta: " .. tostring(item.spell or env.spell or "?") ..
            " (" .. tostring(env.visible or 0) .. " visible)"
    end
    if kind == "stance" then
        return "EK stance: " .. tostring(item.stance or env.stance or "neutral") ..
            " | " .. tostring(item.spell or env.spell or "?")
    end
    if kind == "rotation" then
        local spell = item.spell or {}
        return "Rotation: " .. tostring(spell.words or env.words or "?") ..
            " (" .. tostring(env.nearby or 0) .. " nearby)"
    end
    if kind == "rune" then
        return "Rune: " .. tostring(env.rune_name or item.rune_name or "rune") ..
            " via " .. tostring(env.slot_text or item.slot_text or "?")
    end
    return "Combat action: " .. tostring(kind or "unknown")
end

function CombatRuntime.targetingStatusText(event, data)
    local kind = tostring(event or "idle")
    local item = data or {}
    if kind == "blocked" then
        return "Targeting blocked: " .. tostring(item.reason or "unknown")
    end
    if kind == "no_valid_target" then
        return "Targeting: no valid monster"
    end
    if kind == "friendly_summon" then
        return "Targeting blocked: friendly summon/familiar"
    end
    if kind == "auto_target" then
        return "Auto target: " .. tostring(item.name or "monster")
    end
    if kind == "target_cleared" then
        return "Target cleared: " .. tostring(item.reason or "unknown")
    end
    return tostring(item.fallback or kind)
end

function CombatRuntime.nextActionText(action, fallback)
    local item = action or {}
    if item.kind == "exeta" then
        return "Next: " .. tostring(item.spell or "?")
    end
    if item.kind == "rune" then
        return "Next: rune/AoE"
    end
    if item.kind == "rotation" then
        local spell = item.spell or {}
        return "Next: " .. tostring(spell.words or "?")
    end
    if item.kind == "stance" then
        return "Next: " .. tostring(item.spell or item.stance or "stance")
    end
    return fallback
end

function CombatRuntime.waitReason(state)
    state = state or {}
    if state.blocked_reason then
        return "Blocked: " .. tostring(state.blocked_reason)
    end
    if state.recovery_gap_until_ms then
        return "Wait: recovery gap " .. CombatRuntime.msLeftText(state.recovery_gap_until_ms, state.now_ms)
    end
    if state.auto_attack and not state.target_present then
        return "Next: retarget monster"
    end
    if not state.target_present then
        return "No target"
    end
    if state.action_lock_until_ms and (state.now_ms or 0) < state.action_lock_until_ms then
        return "Wait: action lock " .. CombatRuntime.msLeftText(state.action_lock_until_ms, state.now_ms)
    end
    if not state.spell_rotation then
        if state.rune_enabled then
            return "Rotation OFF / rune ready check"
        end
        return "Rotation OFF"
    end
    if state.rotation_interval_wait then
        return "Wait: rotation interval"
    end

    local bestBlocked = nil
    for _, spell in ipairs(state.spells or {}) do
        local mobCount = tonumber(spell.mob_count) or 0
        local minNearby = tonumber(spell.min_nearby) or 1
        local maxNearby = tonumber(spell.max_nearby) or 99
        if spell.enabled ~= false and mobCount >= minNearby and mobCount <= maxNearby then
            if spell.ready == true then
                return "Next: " .. tostring(spell.words or "?") .. " (" .. tostring(mobCount) .. " mobs)"
            end
            bestBlocked = "Wait: " .. tostring(spell.words or "?") .. " CD " .. CombatRuntime.msLeftText(spell.cooldown_until_ms, state.now_ms)
        end
    end
    if bestBlocked then
        return bestBlocked
    end
    return "Wait: mobs " .. tostring(state.nearby or 0) .. "/" .. tostring(state.visible or 0) .. " below spell rules"
end

function CombatRuntime.decisionState(state)
    state = state or {}
    local targetText = state.target_present and "target=monster" or "target=none"
    local runeState = "off"
    if state.rune_enabled then
        runeState = state.rune_ready and "ready" or CombatRuntime.msLeftText(state.rune_until_ms, state.now_ms)
    end
    local exetaState = state.auto_exeta and CombatRuntime.msLeftText(state.exeta_until_ms, state.now_ms) or "off"
    local adapterSuffix = ""
    if type(state.adapter_text) == "string" and state.adapter_text ~= "" then
        adapterSuffix = " | adapter " .. state.adapter_text
    end
    return tostring(state.next_action or "idle") ..
        " | " .. targetText ..
        " | lock " .. CombatRuntime.msLeftText(state.action_lock_until_ms or 0, state.now_ms) ..
        " | exeta " .. exetaState ..
        " | rune " .. runeState ..
        adapterSuffix
end

function CombatRuntime.decisionStateSummary(tools, state, target_decision)
    state = state or {}
    local adapterText = CombatRuntime.adapterSummary(tools, {
        online = state.online,
        in_protection_zone = state.in_protection_zone,
        has_safe_target = state.target_present,
    }, target_decision or {
        eligible = state.target_present,
        reason = state.target_present and "selected" or "no_target",
        name = state.target_present and "monster" or "none",
        score = 0,
    })
    if type(adapterText) ~= "string" then
        adapterText = ""
    end
    state.adapter_text = adapterText
    return CombatRuntime.decisionState(state)
end

function CombatRuntime.contract()
    return {
        module = "ctoa_helper_combat_runtime",
        mode = "passive",
        owns_runtime_plan = true,
        owns_adapter_summary = true,
        owns_magic_summary = true,
        owns_magic_summary_text = true,
        owns_rotation_rule_editor = true,
        owns_rotation_rule_sanitization = true,
        rotation_rule_limit = MAX_ROTATION_RULES,
        owns_combat_action_rule_editor = true,
        owns_combat_action_rule_sanitization = true,
        combat_action_rule_limit = MAX_COMBAT_ACTION_RULES,
        owns_cooldown_text = true,
        owns_rune_ready = true,
        owns_rune_action_selection = true,
        owns_rotation_spell_rows = true,
        owns_spell_readiness = true,
        owns_rotation_spell_selection = true,
        owns_select_rotation_spell = true,
        owns_stance_selection = true,
        owns_offensive_action_selection = true,
        owns_action_status_text = true,
        owns_targeting_status_text = true,
        owns_next_action_text = true,
        owns_wait_reason_text = true,
        owns_decision_state_text = true,
        owns_decision_state_summary = true,
        runtime_actions = false,
        scans_creatures = false,
        attacks = false,
        casts = false,
        uses_items = false,
        requires_target_scorer = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_COMBAT_RUNTIME = CombatRuntime

return CombatRuntime
