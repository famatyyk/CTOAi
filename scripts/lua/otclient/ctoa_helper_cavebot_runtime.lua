-- ctoa_helper_cavebot_runtime.lua [CTOA OTClient Native]
-- Passive cavebot runtime adapter planner. This module never walks or pathfinds.

local CavebotRuntime = rawget(_G, "CTOA_HELPER_CAVEBOT_RUNTIME") or {}

local function boolValue(value)
    return value == true
end

local function numberValue(value, fallback)
    local parsed = tonumber(value)
    if parsed == nil then
        return fallback
    end
    return parsed
end

local function boolOrText(value)
    if value == true or value == "true" then
        return true
    end
    return false
end

local function textValue(value, fallback)
    if value == nil or value == "" then
        return tostring(fallback or "")
    end
    return tostring(value)
end

local function valueOr(value, fallback)
    if value == nil then
        return fallback
    end
    return value
end

local function runtimeBlockedReason(tools, context, route_stats)
    local cfg = tools or {}
    local env = context or {}
    local stats = route_stats or {}
    if not boolValue(cfg.cavebot_movement_enabled) then
        return "movement_disabled"
    end
    if boolValue(cfg.pause_in_pz) and boolValue(env.in_protection_zone) then
        return "protection_zone"
    end
    if env.online == false then
        return "offline"
    end
    if numberValue(stats.count, 0) <= 0 then
        return "empty_route"
    end
    if numberValue(cfg.retry_count, 0) >= numberValue(cfg.max_retries, 3) then
        return "retry_budget_exhausted"
    end
    return nil
end

function CavebotRuntime.plan(tools, context, route_stats)
    local blocked = runtimeBlockedReason(tools, context, route_stats)
    local cfg = tools or {}
    local stats = route_stats or {}
    local selected = numberValue(stats.selected_index, 0)
    local count = numberValue(stats.count, 0)
    if blocked then
        return {
            allowed = false,
            reason = blocked,
            next_action = "hold",
            waypoint_index = selected,
            waypoint_count = count,
        }
    end
    return {
        allowed = true,
        reason = "planned",
        next_action = "plan_walk",
        waypoint_index = selected > 0 and selected or 1,
        waypoint_count = count,
        retry_count = numberValue(cfg.retry_count, 0),
        retry_budget = numberValue(cfg.max_retries, 3),
    }
end

function CavebotRuntime.summary(plan)
    if type(plan) ~= "table" then
        return "cavebot adapter idle"
    end
    return tostring(plan.next_action or "hold") ..
        " | " .. tostring(plan.reason or "unknown") ..
        " | wp " .. tostring(plan.waypoint_index or 0) ..
        "/" .. tostring(plan.waypoint_count or 0)
end

function CavebotRuntime.decisionText(plan)
    if type(plan) ~= "table" then
        return "hold | adapter_idle | wp 0/0"
    end
    local retry = ""
    if plan.retry_count then
        retry = " | retry " .. tostring(plan.retry_count) .. "/" .. tostring(plan.retry_budget or "?")
    end
    return tostring(plan.next_action or "hold") ..
        " | " .. tostring(plan.reason or "unknown") ..
        " | wp " .. tostring(plan.waypoint_index or 0) ..
        "/" .. tostring(plan.waypoint_count or 0) ..
        retry
end

function CavebotRuntime.adapterSummary(tools, context, route_stats, helpers)
    local plan = CavebotRuntime.plan(tools, context, route_stats)
    local text = ""
    helpers = helpers or {}
    if type(helpers.decisionText) == "function" then
        text = tostring(helpers.decisionText(plan) or "")
    end
    if text == "" then
        text = CavebotRuntime.decisionText(plan)
    end
    if text == "" and type(helpers.summary) == "function" then
        text = tostring(helpers.summary(plan) or "")
    end
    if text == "" then
        text = CavebotRuntime.summary(plan)
    end
    return text, plan
end

function CavebotRuntime.adapterStatusText(summary)
    local text = tostring(summary or "")
    if text == "" then
        return ""
    end
    return "adapter " .. text
end

function CavebotRuntime.adapterStatusSummary(tools, context, route_stats)
    local summary = CavebotRuntime.adapterSummary(tools, context, route_stats)
    return CavebotRuntime.adapterStatusText(summary)
end

function CavebotRuntime.movementCapability(sample)
    local data = sample or {}
    if data.available == false then
        return {
            can_move = true,
            can_move_value = nil,
            text = "n/a",
        }
    end
    if data.ok ~= true then
        return {
            can_move = false,
            can_move_value = data.value,
            text = "error:" .. tostring(data.value),
        }
    end
    return {
        can_move = data.value == true,
        can_move_value = data.value,
        text = tostring(data.value),
    }
end

function CavebotRuntime.movementCapabilityForPlayer(player, safeCall)
    local available = player ~= nil and type(player.canWalk) == "function"
    local ok, value = false, nil
    if available and type(safeCall) == "function" then
        ok, value = safeCall(player, "canWalk", true)
    end
    return CavebotRuntime.movementCapability({
        available = available,
        ok = ok,
        value = value,
    })
end

function CavebotRuntime.resetMovementState(tools)
    if type(tools) ~= "table" then
        return false
    end
    tools.cavebot_retry_attempts = 0
    tools.cavebot_stuck_ticks = 0
    tools.cavebot_last_position_key = nil
    tools.cavebot_last_target_key = nil
    tools.cavebot_last_stuck_ms = 0
    return true
end

function CavebotRuntime.probeMetadata(snapshot)
    local data = type(snapshot) == "table" and snapshot or {}
    local api = type(data.api) == "table" and data.api or {}
    local route = type(data.route_metadata) == "table" and data.route_metadata or (type(data.route) == "table" and data.route or {})
    local canSample = type(data.player_can_sample) == "table" and data.player_can_sample or (type(data.can_walk) == "table" and data.can_walk or nil)
    local capability = nil
    if canSample then
        capability = CavebotRuntime.movementCapability(canSample)
    else
        capability = {
            can_move = data.player_can == true or data.player_can == "true",
            can_move_value = data.player_can,
            text = textValue(data.player_can, "n/a"),
        }
    end
    local pathSample = type(data.path_sample) == "table" and data.path_sample or (type(data.path) == "table" and data.path or nil)
    local pathText = pathSample and pathSample.text and textValue(pathSample.text, "n/a") or (pathSample and CavebotRuntime.pathText(pathSample) or textValue(data.path, "n/a"))
    local routeCount = numberValue(route.waypoint_count, 0)
    local routeIndex = numberValue(route.selected_index, routeCount > 0 and 1 or 0)
    return {
        schema_version = "ctoa.cavebot-probe-metadata.v1",
        mode = "passive_probe",
        reason = textValue(data.reason, "startup"),
        api = {
            game_walk = boolOrText(valueOr(api.game_walk, data.game_walk)),
            game_auto_walk = boolOrText(valueOr(api.game_auto_walk, data.game_auto)),
            game_force_walk = boolOrText(valueOr(api.game_force_walk, data.game_force)),
            player_auto_walk = boolOrText(valueOr(api.player_auto_walk, data.player_walk)),
            player_stop_auto_walk = boolOrText(valueOr(api.player_stop_auto_walk, data.player_stop)),
        },
        can_walk = {
            available = canSample ~= nil and canSample.available == true,
            ok = canSample ~= nil and canSample.ok == true,
            value = capability.can_move_value,
            can_move = capability.can_move == true,
            text = textValue(capability.text, "n/a"),
        },
        route = {
            waypoint_count = routeCount,
            selected_index = routeIndex,
            has_waypoint = route.has_waypoint == true,
            target_valid = route.target_valid == true,
            route_empty = routeCount == 0,
            label = textValue(route.label, routeCount > 0 and "waypoint" or "no waypoint"),
            current_text = textValue(route.current_text, data.current or "nil"),
            target_text = textValue(route.target_text, data.target or "nil"),
            same_floor = route.same_floor == true,
            distance = tonumber(route.distance),
        },
        path = {
            available = pathSample ~= nil and pathSample.available == true,
            ok = pathSample ~= nil and pathSample.ok == true,
            dirs_count = pathSample and tonumber(pathSample.dirs_count) or nil,
            result = pathSample and pathSample.result or nil,
            text = pathText,
        },
        runtime_actions = false,
        movement_executed = false,
        route_mutated = false,
        arming_changed = false,
        intrusive_actions_performed = {},
    }
end

function CavebotRuntime.probeSnapshot(snapshot)
    local data = CavebotRuntime.probeMetadata(snapshot)
    return {
        reason = data.reason or "startup",
        game_walk = tostring(data.api and data.api.game_walk == true),
        game_auto = tostring(data.api and data.api.game_auto_walk == true),
        game_force = tostring(data.api and data.api.game_force_walk == true),
        player_walk = tostring(data.api and data.api.player_auto_walk == true),
        player_stop = tostring(data.api and data.api.player_stop_auto_walk == true),
        player_can = data.can_walk and textValue(data.can_walk.text, "n/a") or "n/a",
        current = data.route and textValue(data.route.current_text, "nil") or "nil",
        target = data.route and textValue(data.route.target_text, "nil") or "nil",
        path = data.path and textValue(data.path.text, "n/a") or "n/a",
        waypoint_count = data.route and numberValue(data.route.waypoint_count, 0) or 0,
        selected_index = data.route and numberValue(data.route.selected_index, 0) or 0,
        waypoint_label = data.route and textValue(data.route.label, "no waypoint") or "no waypoint",
    }
end

function CavebotRuntime.probeSummary(snapshot)
    local data = CavebotRuntime.probeSnapshot(snapshot)
    return "Move API probe (" .. tostring(data.reason or "startup") .. "): " ..
        "game.walk=" .. tostring(data.game_walk or "false") ..
        " game.auto=" .. tostring(data.game_auto or "false") ..
        " game.force=" .. tostring(data.game_force or "false") ..
        " player.walk=" .. tostring(data.player_walk or "false") ..
        " player.stop=" .. tostring(data.player_stop or "false") ..
        " player.can=" .. tostring(data.player_can or "n/a") ..
        " current=" .. tostring(data.current or "nil") ..
        " target=" .. tostring(data.target or "nil") ..
        " route=" .. tostring(data.selected_index or 0) .. "/" .. tostring(data.waypoint_count or 0) ..
        " label=" .. tostring(data.waypoint_label or "no waypoint") ..
        " path=" .. tostring(data.path or "n/a")
end

function CavebotRuntime.probeReport(snapshot)
    local metadata = CavebotRuntime.probeMetadata(snapshot)
    local data = CavebotRuntime.probeSnapshot(metadata)
    return {
        schema_version = "ctoa.cavebot-probe-report.v1",
        mode = "passive_probe",
        metadata = metadata,
        snapshot = data,
        text = CavebotRuntime.probeSummary(metadata),
        runtime_actions = false,
        movement_executed = false,
        route_mutated = false,
        arming_changed = false,
        intrusive_actions_performed = {},
    }
end

function CavebotRuntime.pathText(snapshot)
    local data = snapshot or {}
    if data.available == false then
        return "n/a"
    end
    if data.ok ~= true then
        return "error:" .. tostring(data.error or data.value or "unknown")
    end
    if data.dirs_count ~= nil then
        return "dirs=" .. tostring(data.dirs_count) .. " result=" .. tostring(data.result)
    end
    return "non-table result=" .. tostring(data.value) .. " extra=" .. tostring(data.extra)
end

function CavebotRuntime.movementBlockedReason(context)
    local env = context or {}
    if env.online == false then
        return "offline"
    end
    if env.has_player == false then
        return "no player"
    end
    if env.has_position == false then
        return "no position"
    end
    if env.in_protection_zone == true then
        return "PZ guard"
    end
    return nil
end

function CavebotRuntime.walkPreflight(state)
    local data = state or {}
    if data.movement_enabled == false then
        return {allowed = false, status_event = "movement_disabled"}
    end
    if data.blocked_reason then
        return {allowed = false, status_event = "walk_blocked", status_data = {reason = data.blocked_reason}}
    end
    if data.same_floor == false then
        return {allowed = false, status_event = "floor_blocked"}
    end
    if data.api_available == false then
        return {allowed = false, status_event = "api_missing"}
    end
    if data.already_moving == true then
        return {allowed = true, already_moving = true, status_event = "already_walking"}
    end
    if data.can_move == false then
        return {allowed = false, status_event = "can_walk_false"}
    end
    return {allowed = true, status_event = "ready"}
end

function CavebotRuntime.testWalkPlan(state)
    local data = state or {}
    if data.has_player_position == false then
        return {allowed = false, status_event = "test_no_player_position", trace_event = "test_blocked", trace_data = {reason = "no player position"}}
    end
    if data.has_waypoint == false then
        return {allowed = false, status_event = "test_no_waypoint", trace_event = "test_blocked", trace_data = {reason = "no waypoint"}}
    end
    if data.has_target == false then
        return {allowed = false, status_event = "test_invalid_waypoint", trace_event = "test_blocked", trace_data = {reason = "invalid waypoint"}}
    end
    if data.same_floor == false then
        return {allowed = false, status_event = "test_different_floor", trace_event = "test_floor_blocked", trace_data = {current = data.current_text, target = data.target_text}}
    end
    if data.api_available == false then
        return {allowed = false, status_event = "test_api_missing", trace_event = "test_blocked", trace_data = {reason = "movement API unavailable"}}
    end
    if data.can_move == false then
        return {allowed = false, status_event = "test_can_walk_false", trace_event = "test_blocked", trace_data = {reason = "canWalk=" .. tostring(data.can_move_value)}}
    end
    return {allowed = true, status_event = "test_ready"}
end

function CavebotRuntime.walkingStatus(state)
    local data = state or {}
    local label = data.label or data.waypoint_label or "waypoint"
    local retry = data.retry_status
    if type(retry) ~= "string" or retry == "" then
        retry = "retry " .. tostring(data.retry_count or 0) .. "/" .. tostring(data.retry_limit or 3)
    end
    return {
        event = "walking",
        data = {
            label = label,
            retry_status = retry,
        },
        text = "walking " .. tostring(label) .. " " .. tostring(retry),
    }
end

function CavebotRuntime.retryDecision(state)
    local data = state or {}
    if data.stuck == true and data.retry_budget_exceeded == true then
        return {
            disable_movement = true,
            status_event = "retry_budget_reached",
            trace_event = "retry_budget_disabled",
            trace_data = {
                target = data.target,
                current = data.current,
                attempts = data.attempts,
            },
        }
    end
    if data.walk_failed == true and data.retry_budget_exceeded == true then
        return {
            disable_movement = true,
            status_event = "walk_failed",
            trace_event = "walk_failed_budget",
            trace_data = {
                target = data.target,
            },
        }
    end
    return {
        disable_movement = false,
        status_event = "walk_retry",
        status_data = {
            retry_count = data.retry_count or 0,
        },
    }
end

function CavebotRuntime.statusText(event, data)
    local kind = tostring(event or "idle")
    local item = data or {}
    if kind == "movement_disabled" then
        return "movement disabled"
    end
    if kind == "no_player_position" then
        return "no player position"
    end
    if kind == "no_waypoints" then
        return "no waypoints"
    end
    if kind == "walk_blocked" then
        return "walk blocked: " .. tostring(item.reason or "unknown")
    end
    if kind == "movement_blocked" then
        return "movement blocked: " .. tostring(item.reason or "unknown")
    end
    if kind == "floor_blocked" then
        return "walk blocked: floor"
    end
    if kind == "api_missing" then
        return "walk blocked: API missing"
    end
    if kind == "already_walking" then
        return "already walking"
    end
    if kind == "can_walk_false" then
        return "walk blocked: canWalk=false"
    end
    if kind == "skip_invalid_waypoint" then
        return "skip invalid waypoint"
    end
    if kind == "retry_budget_reached" then
        return "stuck: retry budget reached"
    end
    if kind == "walk_failed" then
        return "stuck: walk failed"
    end
    if kind == "walk_retry" then
        return "walk retry " .. tostring(item.retry_count or 0)
    end
    if kind == "walking" then
        local planned = CavebotRuntime.walkingStatus(item)
        return planned.text
    end
    if kind == "test_no_player_position" then
        return "test walk: no player position"
    end
    if kind == "test_no_waypoint" then
        return "test walk: add waypoint first"
    end
    if kind == "test_invalid_waypoint" then
        return "test walk: invalid waypoint"
    end
    if kind == "test_different_floor" then
        return "test walk: different floor"
    end
    if kind == "test_api_missing" then
        return "test walk: API missing"
    end
    if kind == "test_can_walk_false" then
        return "test walk: canWalk=false"
    end
    if kind == "test_sent" then
        return "test walk sent " .. tostring(item.label or "waypoint")
    end
    if kind == "test_failed" then
        return "test walk failed"
    end
    return tostring(item.fallback or kind)
end

function CavebotRuntime.traceText(event, data)
    local kind = tostring(event or "idle")
    local item = data or {}
    if kind == "movement_reset" then
        return "Cavebot movement state reset: " .. tostring(item.reason or "manual")
    end
    if kind == "movement_attempt" then
        return "Cavebot movement target=" .. tostring(item.target or "nil") ..
            " current=" .. tostring(item.current or "nil") ..
            " path=" .. tostring(item.path or "n/a") ..
            " retry=" .. tostring(item.retry or false) ..
            " ok=" .. tostring(item.ok) ..
            " result=" .. tostring(item.result)
    end
    if kind == "test_attempt" then
        return "Test walk target=" .. tostring(item.target or "nil") ..
            " current=" .. tostring(item.current or "nil") ..
            " path=" .. tostring(item.path or "n/a") ..
            " ok=" .. tostring(item.ok) ..
            " result=" .. tostring(item.result)
    end
    if kind == "test_blocked" then
        return "Test walk blocked: " .. tostring(item.reason or "unknown")
    end
    if kind == "test_floor_blocked" then
        return "Test walk blocked: different floor current=" .. tostring(item.current or "nil") ..
            " target=" .. tostring(item.target or "nil")
    end
    if kind == "retry_budget_disabled" then
        return "Cavebot movement disabled: retry budget reached target=" .. tostring(item.target or "nil") ..
            " current=" .. tostring(item.current or "nil") ..
            " attempts=" .. tostring(item.attempts or 0)
    end
    if kind == "walk_failed_budget" then
        return "Cavebot movement disabled: walk failed retry budget target=" .. tostring(item.target or "nil")
    end
    return tostring(item.fallback or kind)
end

function CavebotRuntime.cavebotRuntimeText(functionName, event, data, fallback)
    local formatter = nil
    if functionName == "statusText" then
        formatter = CavebotRuntime.statusText
    elseif functionName == "traceText" then
        formatter = CavebotRuntime.traceText
    end
    if formatter then
        local ok, text = pcall(formatter, event, data or {})
        if ok and type(text) == "string" and text ~= "" then
            return text
        end
    end
    return fallback or tostring(event or "idle")
end

function CavebotRuntime.cavebotRetryBudgetExceeded(tools)
    local cfg = type(tools) == "table" and tools or {}
    local attempts = tonumber(cfg.cavebot_retry_attempts) or 0
    local limit = math.max(1, tonumber(cfg.cavebot_retry_limit) or 3)
    return attempts >= limit
end

function CavebotRuntime.contract()
    return {
        module = "ctoa_helper_cavebot_runtime",
        mode = "passive",
        owns_runtime_plan = true,
        owns_decision_text = true,
        owns_adapter_summary = true,
        owns_adapter_status_text = true,
        owns_adapter_status_summary = true,
        owns_movement_capability = true,
        owns_player_movement_capability = true,
        owns_movement_state_reset = true,
        owns_probe_metadata = true,
        owns_probe_snapshot = true,
        owns_probe_summary_text = true,
        owns_probe_report = true,
        owns_path_text = true,
        owns_blocked_reason_text = true,
        owns_walk_preflight = true,
        owns_test_walk_plan = true,
        owns_walking_status = true,
        owns_retry_decision = true,
        owns_status_text = true,
        owns_trace_text = true,
        owns_runtime_text_bridge = true,
        owns_retry_budget = true,
        runtime_actions = false,
        movement_enabled = false,
        probe_executes_movement = false,
        probe_mutates_route = false,
        probe_changes_arming = false,
        pathfinding = false,
        uses_map = false,
        walks = false,
        requires_route_engine = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_CAVEBOT_RUNTIME = CavebotRuntime

return CavebotRuntime
