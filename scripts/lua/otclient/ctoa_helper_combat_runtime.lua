-- ctoa_helper_combat_runtime.lua [CTOA OTClient Native]
-- Passive combat runtime adapter planner. This module never scans, attacks, or casts.

local CombatRuntime = rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME") or {}

local function boolValue(value)
    return value == true
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

function CombatRuntime.runeReady(tools, state)
    local cfg = tools or {}
    local env = state or {}
    if not boolValue(cfg.rune_enabled) then
        return false
    end
    if boolValue(cfg.rune_requires_target) and not boolValue(env.target_present) then
        return false
    end
    if (tonumber(env.visible) or 0) < (tonumber(cfg.rune_min_visible) or 1) then
        return false
    end
    local now = tonumber(env.now_ms) or 0
    if now < (tonumber(cfg.attack_action_lock_until_ms) or 0) then
        return false
    end
    return now - (tonumber(cfg.last_rune_ms) or 0) >= (tonumber(cfg.rune_cooldown_ms) or 1000)
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
    for _, spell in ipairs(spells or {}) do
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
        return nil
    end
    if now - (tonumber(env.last_attack_spell_ms) or 0) < (tonumber(env.rotation_interval_ms) or 1050) then
        return nil
    end
    local rows = CombatRuntime.spellReadiness(spells, {
        now_ms = now,
        default_cooldown_ms = env.rotation_interval_ms or 1050,
    })
    local selected = nil
    for _, spell in ipairs(rows) do
        local mobCount = tonumber(spell.mob_count) or 0
        local minNearby = tonumber(spell.min_nearby) or 1
        local maxNearby = tonumber(spell.max_nearby) or 99
        if mobCount >= minNearby and mobCount <= maxNearby and spell.ready == true then
            if not selected then
                selected = spell
            elseif spell.directional == true and string.lower(tostring(selected.words or "")) == "exori" then
                selected = spell
            end
        end
    end
    return selected
end

function CombatRuntime.stanceAction(tools, state)
    local cfg = tools or {}
    local env = state or {}
    if cfg.auto_stance ~= true or env.target_present ~= true then return nil end
    local now = tonumber(env.now_ms) or 0
    if now - (tonumber(cfg.last_stance_ms) or 0) < (tonumber(cfg.stance_cooldown_ms) or 10000) then
        return nil
    end
    local monsters = tonumber(env.nearby) or 0
    if monsters >= (tonumber(cfg.defensive_min_monsters) or 4) then
        return {kind="stance", stance="defensive", fight_mode="defensive", spell=cfg.defensive_buff_spell or "utamo tempo"}
    end
    if monsters >= 1 and monsters <= (tonumber(cfg.offensive_max_monsters) or 2) then
        return {kind="stance", stance="offensive", fight_mode="offensive", spell=cfg.offensive_buff_spell or "utito tempo"}
    end
    return nil
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

    local stance = CombatRuntime.stanceAction(cfg, env)
    if stance then return stance end

    local visible = tonumber(env.visible) or 0
    if boolValue(cfg.auto_exeta) and targetPresent and visible >= (tonumber(cfg.exeta_min_visible) or 1) and now - (tonumber(cfg.last_exeta_ms) or 0) >= (tonumber(cfg.exeta_interval_ms) or 5000) then
        return {
            kind = "exeta",
            spell = (cfg.exeta_spells or {})[tonumber(cfg.exeta_index) or 1],
        }
    end

    local rotationSpell = env.rotation_spell
    local runeIsReady = CombatRuntime.runeReady(cfg, env) and env.rune_target_safe ~= false
    if cfg.magic_priority == "rune" and runeIsReady then
        return {kind = "rune"}
    end
    if rotationSpell then
        return {
            kind = "rotation",
            spell = rotationSpell,
        }
    end
    if runeIsReady then
        return {kind = "rune"}
    end
    return nil
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
        if mobCount >= minNearby and mobCount <= maxNearby then
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
        owns_cooldown_text = true,
        owns_rune_ready = true,
        owns_rotation_spell_rows = true,
        owns_spell_readiness = true,
        owns_rotation_spell_selection = true,
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
