-- ctoa_helper_heal_friend.lua [CTOA OTClient Native]
-- Read-only Heal Friend observer domain. It never casts or sends chat.

local HealFriend = rawget(_G, "CTOA_HELPER_HEAL_FRIEND") or {}

function HealFriend.whitelistContainsName(whitelist, normalizedName)
    if not normalizedName or normalizedName == "" then
        return false
    end
    for _, entry in ipairs(whitelist or {}) do
        local needle = string.lower(tostring(entry or ""))
        if needle ~= "" and normalizedName == needle then
            return true
        end
    end
    return false
end

function HealFriend.scan(config, ctx)
    ctx = ctx or {}
    local healFriend = config or {}
    local player = ctx.getLocalPlayer and ctx.getLocalPlayer() or nil
    local playerPos = ctx.getThingPosition and ctx.getThingPosition(player) or nil
    local scanRange = math.max(1, tonumber(healFriend.friend_scan_range) or 7)
    local result = {
        observed = 0,
        matched = 0,
        lowest_hp = 100,
        lowest_name = "none"
    }
    if not player or not playerPos or not healFriend.observe_party then
        return result
    end
    local spectators = {}
    if ctx.getSpectatorsInRange then
        spectators = ctx.getSpectatorsInRange(playerPos, scanRange) or {}
    end
    for _, creature in ipairs(spectators) do
        if ctx.isPlayerCreature and ctx.isPlayerCreature(creature, player) then
            local creaturePos = ctx.getThingPosition and ctx.getThingPosition(creature) or nil
            local distance = ctx.distanceChebyshev and ctx.distanceChebyshev(playerPos, creaturePos) or nil
            if distance and distance <= scanRange then
                result.observed = result.observed + 1
                local normalizedName = ctx.normalizedCreatureName and ctx.normalizedCreatureName(creature) or ""
                local whitelisted = HealFriend.whitelistContainsName(healFriend.friend_whitelist or {}, normalizedName)
                if whitelisted or healFriend.require_whitelist ~= true then
                    result.matched = result.matched + 1
                    local hp = ctx.getCreatureHealthPercent and ctx.getCreatureHealthPercent(creature) or 100
                    if hp <= result.lowest_hp then
                        result.lowest_hp = hp
                        result.lowest_name = normalizedName ~= "" and normalizedName or "friend"
                    end
                end
            end
        end
    end
    return result
end

function HealFriend.observe(config, now, ctx)
    ctx = ctx or {}
    local healFriend = config or {}
    if not healFriend.enabled or not healFriend.observe_party then
        return false, nil
    end
    if now - (healFriend.last_sample_ms or 0) < (healFriend.sample_interval_ms or 1000) then
        return false, nil
    end
    healFriend.last_sample_ms = now
    local result = HealFriend.scan(healFriend, ctx)
    healFriend.observed_count = result.observed
    healFriend.lowest_friend_hp = result.lowest_hp
    local shortText = ctx.shortText or function(text)
        return tostring(text or "")
    end
    if result.matched > 0 then
        healFriend.last_status = "matched " .. tostring(result.matched) .. "/" .. tostring(result.observed) .. " lowest " .. tostring(result.lowest_hp) .. "% " .. shortText(result.lowest_name, 12)
    else
        healFriend.last_status = "observed " .. tostring(result.observed) .. " / whitelist 0"
    end
    return true, result
end

function HealFriend.plan(config, observation, context)
    local healFriend = config or {}
    local result = observation or {}
    local env = context or {}
    if healFriend.enabled ~= true then
        return {
            allowed = false,
            reason = "planner_disabled",
            next_action = "hold",
            target = "none",
        }
    end
    if healFriend.runtime_enabled ~= true then
        return {
            allowed = false,
            reason = "runtime_gated",
            next_action = "hold",
            target = result.lowest_name or "none",
        }
    end
    if healFriend.pz_safe == true and env.in_protection_zone == true then
        return {
            allowed = false,
            reason = "protection_zone",
            next_action = "hold",
            target = result.lowest_name or "none",
        }
    end
    if tonumber(result.matched or 0) <= 0 then
        return {
            allowed = false,
            reason = "no_whitelisted_friend",
            next_action = "hold",
            target = "none",
        }
    end
    local hp = tonumber(result.lowest_hp) or 100
    local threshold = tonumber(healFriend.hp_threshold) or 70
    if hp > threshold then
        return {
            allowed = false,
            reason = "hp_above_threshold",
            next_action = "hold",
            target = result.lowest_name or "friend",
            hp = hp,
            threshold = threshold,
        }
    end
    return {
        allowed = true,
        reason = "planned",
        next_action = "plan_sio",
        target = result.lowest_name or "friend",
        hp = hp,
        threshold = threshold,
        spell = tostring(healFriend.sio_spell or "exura sio"),
    }
end

function HealFriend.statusText(config, observation)
    local healFriend = config or {}
    local result = observation or {}
    local status = healFriend.last_status
    if type(status) == "string" and status ~= "" then
        return status
    end
    if healFriend.enabled == true and healFriend.observe_party == true then
        return "observer ready; waiting for sandbox attach"
    end
    return "read-only pending; no sio cast until sandbox whitelist smoke passes"
end

function HealFriend.decisionText(plan)
    local decision = plan or {}
    local action = tostring(decision.next_action or "hold")
    local reason = tostring(decision.reason or "unknown")
    local target = tostring(decision.target or "none")
    if decision.hp then
        return action .. " | " .. reason .. " | " .. target .. " " .. tostring(decision.hp) .. "%"
    end
    return action .. " | " .. reason .. " | " .. target
end

function HealFriend.summary(config, helpers)
    helpers = helpers or {}
    local healFriend = config or {}
    local whitelist = healFriend.friend_whitelist or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local runtimeText = healFriend.runtime_enabled and "runtime ON" or "runtime gated"
    return "Planner " .. onOffText(healFriend.enabled == true) ..
        " | " .. tostring(healFriend.sio_spell or "exura sio") ..
        " <= " .. tostring(healFriend.hp_threshold or "?") .. "%" ..
        " | Friends " .. tostring(#whitelist) .. "/" .. tostring(healFriend.observed_count or 0) ..
        " | " .. runtimeText
end

function HealFriend.contract()
    return {
        module = "ctoa_helper_heal_friend",
        mode = "passive",
        owns_whitelist_matching = true,
        owns_scan = true,
        owns_observer = true,
        owns_runtime_plan = true,
        owns_status_text = true,
        owns_decision_text = true,
        owns_summary_text = true,
        runtime_actions = false,
        casts = false,
        talks = false,
        uses_items = false,
        scans_with_context_only = true,
        requires_whitelist = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_HEAL_FRIEND = HealFriend
return HealFriend
