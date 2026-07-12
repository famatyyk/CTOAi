-- ctoa_helper_recovery_runtime.lua [CTOA OTClient Native]
-- Passive recovery adapter. It normalizes vitals and chooses recovery labels only.

local RecoveryRuntime = rawget(_G, "CTOA_HELPER_RECOVERY_RUNTIME") or {}

local function numberValue(value)
    return tonumber(value)
end

local function percentValue(current, maximum)
    local value = numberValue(current)
    local maxValue = numberValue(maximum)
    if value and maxValue and maxValue > 0 then
        return math.floor((value / maxValue) * 100)
    end
    return nil
end

function RecoveryRuntime.normalizeVitals(snapshot)
    local raw = snapshot or {}
    local vitals = {
        source = "none",
        hp = numberValue(raw.hp),
        max_hp = numberValue(raw.max_hp),
        hp_percent = nil,
        mana = numberValue(raw.mana),
        max_mana = numberValue(raw.max_mana),
        mana_percent = nil,
    }

    vitals.hp_percent = percentValue(vitals.hp, vitals.max_hp)
    if vitals.hp_percent then
        vitals.source = "real"
    else
        vitals.hp_percent = numberValue(raw.hp_percent_api)
        if vitals.hp_percent then
            vitals.source = "percent_api"
        end
    end

    vitals.mana_percent = percentValue(vitals.mana, vitals.max_mana)
    if vitals.mana_percent then
        if vitals.source == "none" then
            vitals.source = "real"
        end
    else
        vitals.mana_percent = numberValue(raw.mana_percent_api)
        if vitals.mana_percent and vitals.source == "none" then
            vitals.source = "percent_api"
        end
    end
    return vitals
end

function RecoveryRuntime.readVitals(player)
    local snapshot = {}
    local reads = {
        {field = "hp", method = "getHealth"},
        {field = "max_hp", method = "getMaxHealth"},
        {field = "mana", method = "getMana"},
        {field = "max_mana", method = "getMaxMana"},
        {field = "hp_percent_api", method = "getHealthPercent"},
        {field = "mana_percent_api", method = "getManaPercent"},
    }
    for _, read in ipairs(reads) do
        local method = player and player[read.method]
        if type(method) == "function" then
            local ok, value = pcall(method, player)
            if ok then
                snapshot[read.field] = tonumber(value)
            end
        end
    end
    return RecoveryRuntime.normalizeVitals(snapshot)
end

function RecoveryRuntime.jitterThreshold(baseThreshold, jitterPercent, nonce)
    local base = numberValue(baseThreshold)
    if not base then
        return nil, 0
    end
    local span = math.max(0, math.min(5, math.floor(numberValue(jitterPercent) or 0)))
    if span == 0 then
        return math.max(1, math.min(100, base)), 0
    end
    local seed = math.abs(math.floor(numberValue(nonce) or 0))
    local offset = ((seed * 1103515245 + 12345) % (span * 2 + 1)) - span
    return math.max(1, math.min(100, base + offset)), offset
end

function RecoveryRuntime.selectHealingSpell(healing, hp, nonce)
    local cfg = healing or {}
    local percent = numberValue(hp)
    local selected = nil
    local selectedThreshold = nil
    for index, rule in ipairs(cfg.spell_rotation or {}) do
        local threshold = numberValue(rule and rule.threshold)
        threshold = RecoveryRuntime.jitterThreshold(threshold, cfg.threshold_jitter_percent, (nonce or 0) + index * 17)
        local spell = rule and rule.spell
        if percent and threshold and spell and spell ~= "" and percent <= threshold then
            if not selectedThreshold or threshold < selectedThreshold then
                selected = spell
                selectedThreshold = threshold
            end
        end
    end
    if selected then
        return selected
    end
    local criticalThreshold = RecoveryRuntime.jitterThreshold(30, cfg.threshold_jitter_percent, (nonce or 0) + 97)
    if percent and percent <= criticalThreshold and cfg.critical_spell and cfg.critical_spell ~= "" then
        return cfg.critical_spell
    end
    return cfg.spell
end

function RecoveryRuntime.potionStatusText(kind, potionName, slotText, percent)
    local label = tostring(kind or "Potion")
    return label .. " via " .. tostring(slotText or "?") .. " at " .. tostring(percent or "?") .. "%"
end

function RecoveryRuntime.spellStatusText(spell, percent)
    return "Spell heal: " .. tostring(spell or "?") .. " at " .. tostring(percent or "?") .. "%"
end

function RecoveryRuntime.actionGap(now, lastActionMs, gapMs)
    local current = numberValue(now) or 0
    local last = numberValue(lastActionMs) or 0
    local gap = numberValue(gapMs) or 250
    local untilMs = last + gap
    return {
        active = current < untilMs,
        until_ms = untilMs,
        remaining_ms = math.max(0, untilMs - current),
        gap_ms = gap,
    }
end

function RecoveryRuntime.summary(vitals)
    local data = vitals or {}
    return "Recovery vitals=" .. tostring(data.source or "none") ..
        " | hp=" .. tostring(data.hp_percent or "?") ..
        " | mana=" .. tostring(data.mana_percent or "?")
end

function RecoveryRuntime.contract()
    return {
        module = "ctoa_helper_recovery_runtime",
        mode = "passive",
        owns_vitals_normalization = true,
        owns_vitals_read = true,
        owns_healing_spell_selection = true,
        owns_threshold_jitter = true,
        owns_recovery_status_text = true,
        owns_recovery_action_gap = true,
        runtime_actions = false,
        casts = false,
        uses_items = false,
        talks = false,
        walks = false,
        reads_otclient = false,
        creates_widgets = false,
        requires_module_static_gates = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_RECOVERY_RUNTIME = RecoveryRuntime
return RecoveryRuntime
