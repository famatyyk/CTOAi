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

-- P11-compatible passive scan.  It refuses ranking and multi-target selection:
-- exactly one normalized whitelist name must be configured, and more than one
-- matching creature is treated as ambiguous.  No action API is called here.
function HealFriend.scanExactTarget(config, ctx)
    ctx = ctx or {}
    local healFriend = config or {}
    local whitelist = healFriend.friend_whitelist or {}
    local result = {
        status = "blocked",
        reason = "single_exact_target_required",
        match_count = 0,
        target_id = nil,
        target_name = "none",
        target_is_player = false,
        target_is_self = false,
        hp_percent = nil,
        distance = nil,
        target_party_member = false,
        target_visible = false,
        target_same_floor = false,
        ranking_applied = false,
        selection_policy = "single_exact_target",
        casts = false,
        talks = false,
        runtime_actions = false,
    }
    if type(whitelist) ~= "table" or #whitelist ~= 1 then
        return result
    end
    local expectedName = string.lower(tostring(whitelist[1] or "")):match("^%s*(.-)%s*$")
    if expectedName == "" then
        result.reason = "exact_target_name_required"
        return result
    end
    local expectedId = tonumber(healFriend.friend_target_id)
    if not expectedId or expectedId <= 0 or expectedId % 1 ~= 0 then
        result.reason = "stable_target_id_required"
        return result
    end
    local player = ctx.getLocalPlayer and ctx.getLocalPlayer() or nil
    local playerPos = ctx.getThingPosition and ctx.getThingPosition(player) or nil
    local selfId = player and ctx.getCreatureId and tonumber(ctx.getCreatureId(player)) or nil
    result.self_id = selfId
    if not player or not playerPos or healFriend.observe_party ~= true then
        result.reason = "observer_not_ready"
        return result
    end
    local scanRange = math.max(1, math.min(7, tonumber(healFriend.friend_scan_range) or 7))
    local spectators = ctx.getSpectatorsInRange and ctx.getSpectatorsInRange(playerPos, scanRange) or {}
    for _, creature in ipairs(spectators) do
        if ctx.isPlayerCreature and ctx.isPlayerCreature(creature, player) then
            local creaturePos = ctx.getThingPosition and ctx.getThingPosition(creature) or nil
            local distance = ctx.distanceChebyshev and ctx.distanceChebyshev(playerPos, creaturePos) or nil
            local name = ctx.normalizedCreatureName and ctx.normalizedCreatureName(creature) or ""
            local creatureId = ctx.getCreatureId and tonumber(ctx.getCreatureId(creature)) or nil
            if name == expectedName and creatureId == expectedId then
                result.match_count = result.match_count + 1
                if result.match_count == 1 then
                    result.target_id = creatureId
                    result.target_name = name
                    result.target_is_player = true
                    result.target_is_self = creature == player or creatureId == selfId
                    result.hp_percent = ctx.getCreatureHealthPercent and tonumber(ctx.getCreatureHealthPercent(creature)) or nil
                    result.distance = distance
                    result.target_party_member = ctx.isPartyMemberCreature and ctx.isPartyMemberCreature(creature) == true or false
                    result.target_visible = ctx.canShootCreature and ctx.canShootCreature(creature) == true or false
                    result.target_same_floor = playerPos and creaturePos and playerPos.z == creaturePos.z or false
                end
            end
        end
    end
    if result.match_count == 0 then
        result.reason = "exact_target_not_observed"
    elseif result.match_count > 1 then
        result.reason = "exact_target_ambiguous"
        result.target_id = nil
        result.target_name = "none"
        result.hp_percent = nil
        result.distance = nil
    elseif not result.target_id or result.target_id <= 0 then
        result.reason = "stable_target_id_required"
    elseif result.target_is_self == true then
        result.reason = "target_is_self"
    elseif result.target_party_member ~= true then
        result.reason = "target_not_party_member"
    elseif result.target_same_floor ~= true then
        result.reason = "target_different_floor"
    elseif result.target_visible ~= true then
        result.reason = "target_not_visible"
    elseif not result.distance or result.distance > scanRange then
        result.reason = "target_out_of_range"
    elseif not result.hp_percent or result.hp_percent < 1 or result.hp_percent > 100 then
        result.reason = "target_hp_invalid"
    else
        result.status = "observed"
        result.reason = "exact_target_observed"
    end
    return result
end

-- P12 bridge observation. This remains passive: it combines the guarded
-- adapter's environment snapshot with the exact P11 target scan and exposes no
-- talk/cast function.
function HealFriend.executeOnceObservation(config, now, ctx)
    ctx = ctx or {}
    local base = type(ctx.base_observation) == "table" and ctx.base_observation or {}
    local exact = HealFriend.scanExactTarget(config or {}, ctx)
    return {
        schema_version = "ctoa.p12-heal-friend-execute-once-observation.v1",
        observed_at_unix_ms = tonumber(now),
        online = base.online,
        alive = base.alive,
        protection_zone = base.protection_zone,
        protection_zone_source = base.protection_zone_source,
        cooldown = base.cooldown,
        cooldown_source = base.cooldown_source,
        scan_complete = base.scan_complete == true,
        producer_source = "otclient_guarded_adapter_exact_target",
        self_id = exact.self_id or base.self_id,
        exact_target = exact,
        dispatch_allowed = false,
        runtime_actions = false,
        executes_plan = false,
        execute_once_allowed = false,
        promotion_allowed = false,
        casts = false,
        talks = false,
    }
end

function HealFriend.scan(config, ctx)
    local exact = HealFriend.scanExactTarget(config, ctx)
    local result = {
        observed = exact.match_count or 0,
        matched = exact.status == "observed" and 1 or 0,
        lowest_hp = exact.status == "observed" and exact.hp_percent or 100,
        lowest_name = exact.status == "observed" and exact.target_name or "none",
        exact_target = exact,
    }
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
        owns_exact_single_target_scan = true,
        exact_scan_applies_ranking = false,
        exact_scan_supports_multi_target = false,
        owns_scan = true,
        owns_execute_once_observation = true,
        scan_policy = "single_exact_target_id_and_name",
        requires_party_membership = true,
        requires_visibility = true,
        requires_same_floor = true,
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
