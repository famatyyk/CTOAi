-- ctoa_helper_spell_state_registry.lua [CTOA OTClient Native]
-- Passive observed spell-state registry. It never casts, talks, or mutates runtime configuration.

local SpellStateRegistry = rawget(_G, "CTOA_HELPER_SPELL_STATE_REGISTRY") or {}

local MAX_FAMILIES = 16
local MAX_FLAGS = 4
local MAX_SPELLS = 16

local function clampInteger(value, minimum, maximum, fallback)
    local number = math.floor(tonumber(value) or fallback or minimum)
    return math.max(minimum, math.min(maximum, number))
end

local function cleanIdentifier(value)
    local text = string.lower(tostring(value or ""))
    text = string.gsub(text, "[^a-z0-9_%-]", "_")
    text = string.gsub(text, "_+", "_")
    text = string.gsub(string.gsub(text, "^_+", ""), "_+$", "")
    return string.sub(text, 1, 48)
end

local function cleanText(value, maximum)
    local text = tostring(value or "")
    text = string.gsub(text, "[%c]", " ")
    text = string.gsub(text, "%s+", " ")
    text = string.gsub(string.gsub(text, "^%s+", ""), "%s+$", "")
    return string.sub(text, 1, maximum or 64)
end

local function cleanList(values, maximum, cleaner)
    local result, seen = {}, {}
    for _, value in ipairs(type(values) == "table" and values or {}) do
        if #result >= maximum then break end
        local item = cleaner(value)
        local key = string.lower(item)
        if item ~= "" and not seen[key] then
            seen[key] = true
            result[#result + 1] = item
        end
    end
    return result
end

local function hasBitFlag(value, flag)
    if type(value) ~= "number" or type(flag) ~= "number" or flag <= 0 then return nil end
    if bit32 and bit32.band then return bit32.band(value, flag) ~= 0 end
    if bit and bit.band then return bit.band(value, flag) ~= 0 end
    return value % (flag * 2) >= flag
end

function SpellStateRegistry.hasteFlag(ctx)
    local env = ctx or {}
    if type(env.haste_flag) == "number" then return env.haste_flag, "injected" end
    local states = rawget(_G, "PlayerStates")
    if type(states) == "table" and type(states.Haste) == "number" then return states.Haste, "PlayerStates.Haste" end
    local legacy = rawget(_G, "CreatureStateHaste")
    if type(legacy) == "number" then return legacy, "CreatureStateHaste" end
    return nil, "unavailable"
end

function SpellStateRegistry.sanitizeFamily(family)
    local source = type(family) == "table" and family or {}
    local policy = tostring(source.unknown_policy or "block")
    if policy ~= "bounded_cooldown" then policy = "block" end
    return {
        id = cleanIdentifier(source.id),
        flag_names = cleanList(source.flag_names, MAX_FLAGS, function(value) return cleanText(value, 48) end),
        spells = cleanList(source.spells, MAX_SPELLS, function(value) return cleanText(value, 64) end),
        max_age_ms = clampInteger(source.max_age_ms, 250, 10000, 1500),
        unknown_policy = policy,
        fallback_cooldown_ms = clampInteger(source.fallback_cooldown_ms, 1000, 300000, 30000),
    }
end

function SpellStateRegistry.sanitizeFamilies(families)
    local result, seen = {}, {}
    for _, family in ipairs(type(families) == "table" and families or {}) do
        if #result >= MAX_FAMILIES then break end
        local clean = SpellStateRegistry.sanitizeFamily(family)
        if clean.id ~= "" and not seen[clean.id] then
            seen[clean.id] = true
            result[#result + 1] = clean
        end
    end
    return result
end

function SpellStateRegistry.familyById(families, familyId)
    local wanted = cleanIdentifier(familyId)
    for _, family in ipairs(SpellStateRegistry.sanitizeFamilies(families)) do
        if family.id == wanted then return family end
    end
    return nil
end

function SpellStateRegistry.resolveFlag(family, ctx)
    local clean = SpellStateRegistry.sanitizeFamily(family)
    local env = ctx or {}
    local flags = type(env.state_flags) == "table" and env.state_flags or rawget(_G, "PlayerStates")
    if type(flags) ~= "table" then return nil, "PlayerStates_unavailable" end
    for _, name in ipairs(clean.flag_names) do
        if type(flags[name]) == "number" then return flags[name], "PlayerStates." .. name end
    end
    return nil, clean.id .. "_flag_unavailable"
end

function SpellStateRegistry.observe(player, family, now, ctx)
    local clean = SpellStateRegistry.sanitizeFamily(family)
    local observedAt = tonumber(now) or 0
    local base = {id = clean.id, state = "unknown", observed_at_ms = observedAt, runtime_actions = false}
    if not player then base.reason = "no_player"; base.source = "none"; return base end
    local flag, source = SpellStateRegistry.resolveFlag(clean, ctx)
    if not flag then base.reason = clean.id .. "_flag_unavailable"; base.source = source; return base end
    local env = ctx or {}
    local states = nil
    if type(env.read_states) == "function" then
        local ok, value = pcall(env.read_states, player)
        if ok then states = value end
    elseif type(player.getStates) == "function" then
        local ok, value = pcall(function() return player:getStates() end)
        if ok then states = value end
    end
    local active = hasBitFlag(states, flag)
    if active == nil then base.reason = "states_unavailable"; base.source = source; return base end
    base.state = active and "active" or "inactive"
    base.reason = active and "observed_active" or "observed_inactive"
    base.source = source
    base.states = states
    base.flag = flag
    return base
end

function SpellStateRegistry.observeAll(player, families, now, ctx)
    local result = {}
    for _, family in ipairs(SpellStateRegistry.sanitizeFamilies(families)) do
        result[family.id] = SpellStateRegistry.observe(player, family, now, ctx)
    end
    return result
end

function SpellStateRegistry.familyDecision(family, evidence, now, lastCastMs)
    local clean = SpellStateRegistry.sanitizeFamily(family)
    local observed = type(evidence) == "table" and evidence or {}
    local current = tonumber(now) or 0
    local decision = {
        id = clean.id,
        allowed = false,
        reason = "state_unknown",
        state = tostring(observed.state or "unknown"),
        runtime_actions = false,
        dispatch_allowed = false,
    }
    if decision.state == "active" then decision.reason = "state_already_active"; return decision end
    local observedAt = tonumber(observed.observed_at_ms)
    local fresh = observedAt and current >= observedAt and current - observedAt <= clean.max_age_ms
    if decision.state == "inactive" and fresh then
        decision.allowed = true
        decision.reason = "fresh_inactive_state"
        return decision
    end
    if decision.state == "inactive" then decision.reason = "state_stale" end
    if clean.unknown_policy ~= "bounded_cooldown" then return decision end
    local lastCast = tonumber(lastCastMs)
    if lastCast and current - lastCast < clean.fallback_cooldown_ms then
        decision.reason = "bounded_fallback_cooldown"
        return decision
    end
    decision.allowed = true
    decision.reason = "bounded_unknown_fallback"
    decision.fallback = true
    return decision
end

function SpellStateRegistry.decisionMap(families, evidenceById, now, lastCasts)
    local decisions = {}
    local evidence = type(evidenceById) == "table" and evidenceById or {}
    local casts = type(lastCasts) == "table" and lastCasts or {}
    for _, family in ipairs(SpellStateRegistry.sanitizeFamilies(families)) do
        decisions[family.id] = SpellStateRegistry.familyDecision(family, evidence[family.id], now, casts[family.id])
    end
    return decisions
end

function SpellStateRegistry.observeHaste(player, now, ctx)
    local family = {id = "haste", flag_names = {"Haste"}, max_age_ms = 1500, unknown_policy = "block"}
    local generic = SpellStateRegistry.observe(player, family, now, ctx)
    if generic.reason ~= "haste_flag_unavailable" then return generic end
    local env = ctx or {}
    local observedAt = tonumber(now) or 0
    if not player then
        return {id = "haste", state = "unknown", reason = "no_player", observed_at_ms = observedAt, source = "none", runtime_actions = false}
    end
    local flag, source = SpellStateRegistry.hasteFlag(env)
    if not flag then
        return {id = "haste", state = "unknown", reason = "haste_flag_unavailable", observed_at_ms = observedAt, source = source, runtime_actions = false}
    end
    local states = nil
    if type(env.read_states) == "function" then
        local ok, value = pcall(env.read_states, player)
        if ok then states = value end
    elseif type(player.getStates) == "function" then
        local ok, value = pcall(function() return player:getStates() end)
        if ok then states = value end
    end
    local active = hasBitFlag(states, flag)
    if active == nil then
        return {id = "haste", state = "unknown", reason = "states_unavailable", observed_at_ms = observedAt, source = source, runtime_actions = false}
    end
    return {
        id = "haste",
        state = active and "active" or "inactive",
        reason = active and "observed_active" or "observed_inactive",
        observed_at_ms = observedAt,
        states = states,
        flag = flag,
        source = source,
        runtime_actions = false,
    }
end

function SpellStateRegistry.hasteDecision(tools, evidence, now)
    local cfg = type(tools) == "table" and tools or {}
    local observed = type(evidence) == "table" and evidence or {}
    local current = tonumber(now) or 0
    local decision = {allowed = false, reason = "disabled", state = tostring(observed.state or "unknown"), runtime_actions = false, dispatch_allowed = false}
    if cfg.auto_haste ~= true then return decision end
    local family = SpellStateRegistry.familyById(cfg.spell_state_families, "haste") or {
        id = "haste", flag_names = {"Haste"}, max_age_ms = cfg.spell_state_max_age_ms,
        unknown_policy = "block", fallback_cooldown_ms = cfg.haste_interval_ms,
    }
    local stateDecision = SpellStateRegistry.familyDecision(family, observed, current, cfg.last_haste_ms)
    if not stateDecision.allowed then
        local reasons = {state_already_active = "haste_already_active", state_unknown = "haste_state_unknown", state_stale = "haste_state_stale"}
        decision.reason = reasons[stateDecision.reason] or stateDecision.reason
        return decision
    end
    if current - (tonumber(cfg.last_haste_ms) or 0) < math.max(250, tonumber(cfg.haste_interval_ms) or 30000) then decision.reason = "haste_cooldown"; return decision end
    local words = tostring(cfg.haste_spell or "")
    if words == "" then decision.reason = "haste_spell_missing"; return decision end
    decision.allowed = true
    decision.reason = "fresh_inactive_haste"
    decision.spell = words
    return decision
end

function SpellStateRegistry.summary(evidence, decision)
    local observed = type(evidence) == "table" and evidence or {}
    local plan = type(decision) == "table" and decision or {}
    return "Haste " .. tostring(observed.state or "unknown") .. " | " .. tostring(plan.reason or observed.reason or "unknown")
end

function SpellStateRegistry.contract()
    return {
        module = "ctoa_helper_spell_state_registry",
        mode = "passive_observed_state",
        owns_haste_flag_resolution = true,
        owns_haste_observation = true,
        owns_haste_decision = true,
        owns_family_sanitization = true,
        owns_family_observation = true,
        owns_family_decisions = true,
        family_limit = MAX_FAMILIES,
        vocation_spell_families_are_data = true,
        bounded_unknown_fallback_is_explicit = true,
        unknown_fails_closed = true,
        stale_fails_closed = true,
        runtime_actions = false,
        dispatch_allowed = false,
        casts = false,
        talks = false,
        uses_items = false,
        scans_creatures = false,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_SPELL_STATE_REGISTRY = SpellStateRegistry
return SpellStateRegistry
