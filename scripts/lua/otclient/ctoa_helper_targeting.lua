-- ctoa_helper_targeting.lua [CTOA OTClient Native]
-- Passive target scoring helpers. This module never attacks or casts.

local Targeting = rawget(_G, "CTOA_HELPER_TARGETING") or {}

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

function Targeting.hasBlockingNpcIcon(creature, tools)
    local cfg = tools or {}
    if cfg.block_npc_icons == false then
        return false
    end
    if creature and creature.getIcon then
        local ok, icon = pcall(function()
            return creature:getIcon()
        end)
        return ok and icon ~= nil and icon ~= false and icon ~= 0 and icon ~= ""
    end
    return false
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
        }
    end
    if Targeting.isIgnoredName(name, cfg.ignored_names or {}) then
        return {
            eligible = false,
            reason = "ignored_name",
            name = name,
            score = 99999999,
            summary = "ignored " .. name,
        }
    end
    if Targeting.isFriendlySummonCandidate(candidate, cfg) then
        return {
            eligible = false,
            reason = "friendly_summon",
            name = name,
            score = 99999999,
            summary = "friendly summon/familiar " .. name,
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
    return {
        eligible = true,
        reason = "scored",
        name = name,
        rank = rank,
        score = score,
        summary = Targeting.summary(scored, cfg),
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
        owns_npc_icon_guard = true,
        owns_friendly_summon_guard = true,
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
