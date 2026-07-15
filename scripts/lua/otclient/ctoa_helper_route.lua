-- ctoa_helper_route.lua [CTOA OTClient Native]
-- Passive cavebot route helpers. This module never walks or touches OTClient globals.

local Route = rawget(_G, "CTOA_HELPER_ROUTE") or {}

local function clampIndex(index, count)
    if count <= 0 then
        return 1
    end
    local value = tonumber(index) or 1
    if value < 1 then
        return 1
    end
    if value > count then
        return count
    end
    return math.floor(value)
end

function Route.distanceChebyshev(from_pos, to_pos)
    if type(from_pos) ~= "table" or type(to_pos) ~= "table" then
        return nil
    end
    if from_pos.z ~= to_pos.z then
        return nil
    end
    local dx = math.abs((tonumber(from_pos.x) or 0) - (tonumber(to_pos.x) or 0))
    local dy = math.abs((tonumber(from_pos.y) or 0) - (tonumber(to_pos.y) or 0))
    return math.max(dx, dy)
end

local function advanceIndex(index, count)
    if count <= 0 then
        return 1
    end
    return (clampIndex(index, count) % count) + 1
end

function Route.position(waypoint)
    if type(waypoint) ~= "table" then
        return nil
    end
    local x = tonumber(waypoint.x)
    local y = tonumber(waypoint.y)
    local z = tonumber(waypoint.z)
    if not x or not y or not z then
        return nil
    end
    return {x = x, y = y, z = z}
end

function Route.label(waypoint, index)
    if waypoint and waypoint.label and waypoint.label ~= "" then
        return waypoint.label
    end
    local pos = Route.position(waypoint)
    if not pos then
        return "#" .. tostring(index or "?")
    end
    return "#" .. tostring(index or "?") .. " " .. pos.x .. "," .. pos.y .. "," .. pos.z
end

function Route.posKey(pos)
    if type(pos) ~= "table" then
        return nil
    end
    return tostring(pos.x) .. ":" .. tostring(pos.y) .. ":" .. tostring(pos.z)
end

function Route.positionText(pos, fallback)
    local value = Route.position(pos)
    if not value then
        return tostring(fallback or "nil")
    end
    return tostring(value.x) .. "," .. tostring(value.y) .. "," .. tostring(value.z)
end

function Route.probeTarget(tools)
    local waypoints = type(tools) == "table" and type(tools.cavebot_waypoints) == "table" and tools.cavebot_waypoints or {}
    local count = #waypoints
    local index = clampIndex(type(tools) == "table" and tools.cavebot_index or 1, count)
    local waypoint = count > 0 and waypoints[index] or nil
    local target = Route.position(waypoint)
    return {
        waypoint_count = count,
        selected_index = index,
        has_waypoint = waypoint ~= nil,
        target_valid = target ~= nil,
        waypoint = waypoint,
        target = target,
        label = waypoint and Route.label(waypoint, index) or "no waypoint",
        target_text = Route.positionText(target),
        runtime_actions = false,
        route_mutated = false,
    }
end

function Route.probeMetadata(tools, current)
    local selected = Route.probeTarget(tools)
    local currentPosition = Route.position(current)
    local target = selected.target
    local sameFloor = currentPosition ~= nil and target ~= nil and currentPosition.z == target.z
    return {
        schema_version = "ctoa.route-probe-metadata.v1",
        mode = "passive",
        waypoint_count = selected.waypoint_count,
        selected_index = selected.selected_index,
        has_waypoint = selected.has_waypoint,
        target_valid = selected.target_valid,
        route_empty = selected.waypoint_count == 0,
        label = selected.label,
        current = currentPosition,
        current_text = Route.positionText(currentPosition),
        target = target,
        target_text = selected.target_text,
        same_floor = sameFloor,
        distance = sameFloor and Route.distanceChebyshev(currentPosition, target) or nil,
        runtime_actions = false,
        movement_executed = false,
        route_mutated = false,
        arming_changed = false,
    }
end

function Route.add(tools, pos)
    if type(tools) ~= "table" or type(pos) ~= "table" then
        return false, "no player position"
    end
    tools.cavebot_waypoints = tools.cavebot_waypoints or {}
    local index = #tools.cavebot_waypoints + 1
    tools.cavebot_waypoints[index] = {
        x = pos.x,
        y = pos.y,
        z = pos.z,
        label = "wp" .. tostring(index),
    }
    tools.cavebot_index = index
    return true, "added " .. Route.label(tools.cavebot_waypoints[index], index)
end

function Route.clear(tools)
    if type(tools) ~= "table" then
        return false, "route unavailable"
    end
    tools.cavebot_waypoints = {}
    tools.cavebot_index = 1
    return true, "route cleared"
end

function Route.select(tools, delta)
    if type(tools) ~= "table" then
        return false, "route unavailable"
    end
    local waypoints = tools.cavebot_waypoints or {}
    if #waypoints == 0 then
        tools.cavebot_index = 1
        return false, "no waypoints"
    end
    local current = clampIndex(tools.cavebot_index, #waypoints)
    tools.cavebot_index = ((current - 1 + (tonumber(delta) or 0)) % #waypoints) + 1
    return true, "selected " .. Route.label(waypoints[tools.cavebot_index], tools.cavebot_index)
end

function Route.delete(tools)
    if type(tools) ~= "table" then
        return false, "route unavailable"
    end
    local waypoints = tools.cavebot_waypoints or {}
    if #waypoints == 0 then
        tools.cavebot_index = 1
        return false, "delete: no waypoint"
    end
    local index = clampIndex(tools.cavebot_index, #waypoints)
    local removed = waypoints[index]
    table.remove(waypoints, index)
    tools.cavebot_index = clampIndex(index, #waypoints)
    return true, "deleted " .. Route.label(removed, index)
end

function Route.move(tools, delta)
    if type(tools) ~= "table" then
        return false, "route unavailable"
    end
    local waypoints = tools.cavebot_waypoints or {}
    if #waypoints < 2 then
        return false, "move: need 2 waypoints"
    end
    local index = clampIndex(tools.cavebot_index, #waypoints)
    local target = clampIndex(index + (tonumber(delta) or 0), #waypoints)
    if target == index then
        return false, "move: edge"
    end
    waypoints[index], waypoints[target] = waypoints[target], waypoints[index]
    tools.cavebot_index = target
    return true, "moved " .. Route.label(waypoints[target], target)
end

function Route.editorAction(tools, action, options)
    options = options or {}
    local ok, message = false, "route unavailable"
    local dirtyReason = nil
    if action == "add" then
        ok, message = Route.add(tools, options.pos)
        dirtyReason = "cavebot_waypoint"
    elseif action == "clear" then
        ok, message = Route.clear(tools)
        dirtyReason = "cavebot_clear"
    elseif action == "select" then
        ok, message = Route.select(tools, options.delta)
    elseif action == "delete" then
        ok, message = Route.delete(tools)
        dirtyReason = "cavebot_delete"
    elseif action == "move" then
        ok, message = Route.move(tools, options.delta)
        dirtyReason = "cavebot_reorder"
    else
        message = "route action unavailable"
    end
    return {
        ok = ok == true,
        message = message,
        dirty_reason = ok and dirtyReason or nil,
    }
end

function Route.retryStatus(tools)
    if type(tools) ~= "table" then
        return "retry unavailable"
    end
    return "retry " .. tostring(tools.cavebot_retry_attempts or 0) .. "/" .. tostring(tools.cavebot_retry_limit or 3)
end

function Route.retryBlocked(tools)
    if type(tools) ~= "table" then
        return false
    end
    local limit = math.max(1, tonumber(tools.cavebot_retry_limit) or 3)
    return (tonumber(tools.cavebot_retry_attempts) or 0) >= limit
end

function Route.progress(tools, currentKey, targetKey, now)
    if type(tools) ~= "table" then
        return false
    end
    if tools.cavebot_last_target_key ~= targetKey then
        tools.cavebot_last_target_key = targetKey
        tools.cavebot_last_position_key = currentKey
        tools.cavebot_retry_attempts = 0
        tools.cavebot_stuck_ticks = 0
        tools.cavebot_last_stuck_ms = now
        return false
    end
    if tools.cavebot_last_position_key ~= currentKey then
        tools.cavebot_last_position_key = currentKey
        tools.cavebot_retry_attempts = 0
        tools.cavebot_stuck_ticks = 0
        tools.cavebot_last_stuck_ms = now
        return false
    end
    tools.cavebot_stuck_ticks = (tools.cavebot_stuck_ticks or 0) + 1
    tools.cavebot_retry_attempts = (tools.cavebot_retry_attempts or 0) + 1
    tools.cavebot_last_stuck_ms = now
    return true
end

function Route.activeTarget(tools, current, reach_distance)
    if type(tools) ~= "table" then
        return {ok = false, status_event = "no_waypoints"}
    end
    local waypoints = tools.cavebot_waypoints or {}
    if #waypoints == 0 then
        tools.cavebot_index = 1
        return {ok = false, status_event = "no_waypoints"}
    end

    tools.cavebot_index = clampIndex(tools.cavebot_index, #waypoints)
    local waypoint = waypoints[tools.cavebot_index]
    local target = Route.position(waypoint)
    if not target then
        tools.cavebot_index = advanceIndex(tools.cavebot_index, #waypoints)
        return {ok = false, status_event = "skip_invalid_waypoint"}
    end

    local distance = Route.distanceChebyshev(current, target)
    local reach = tonumber(reach_distance) or 1
    local reached = distance == 0 or (distance and distance <= reach)
    if reached then
        tools.cavebot_index = advanceIndex(tools.cavebot_index, #waypoints)
        waypoint = waypoints[tools.cavebot_index]
        target = Route.position(waypoint)
        distance = Route.distanceChebyshev(current, target)
        if distance == 0 and #waypoints > 1 then
            tools.cavebot_index = advanceIndex(tools.cavebot_index, #waypoints)
            waypoint = waypoints[tools.cavebot_index]
            target = Route.position(waypoint)
            distance = Route.distanceChebyshev(current, target)
        end
    end

    if not target then
        return {ok = false, status_event = "skip_invalid_waypoint", reached = reached}
    end
    return {
        ok = true,
        target = target,
        waypoint = waypoint,
        index = tools.cavebot_index,
        distance = distance,
        reached = reached,
    }
end

function Route.stats(tools)
    local waypoints = {}
    local retry_attempts = 0
    local retry_limit = 3
    local selected_index = 1
    if type(tools) == "table" then
        waypoints = tools.cavebot_waypoints or {}
        retry_attempts = tonumber(tools.cavebot_retry_attempts) or 0
        retry_limit = tonumber(tools.cavebot_retry_limit) or 3
        selected_index = clampIndex(tools.cavebot_index, #waypoints)
    end
    local valid = 0
    local invalid = 0
    for _, waypoint in ipairs(waypoints) do
        if Route.position(waypoint) then
            valid = valid + 1
        else
            invalid = invalid + 1
        end
    end
    return {
        total = #waypoints,
        valid = valid,
        invalid = invalid,
        selected_index = selected_index,
        empty = #waypoints == 0,
        retry_attempts = retry_attempts,
        retry_limit = retry_limit,
        retry_blocked = retry_attempts >= retry_limit,
    }
end

function Route.selectedSummary(tools)
    if type(tools) ~= "table" then
        return "route unavailable"
    end
    local waypoints = tools.cavebot_waypoints or {}
    if #waypoints == 0 then
        return "route empty"
    end
    local index = clampIndex(tools.cavebot_index, #waypoints)
    return Route.label(waypoints[index], index) .. " | " .. Route.retryStatus(tools)
end

function Route.uiState(tools)
    local waypoints = {}
    local index = 1
    if type(tools) == "table" then
        waypoints = tools.cavebot_waypoints or {}
        index = clampIndex(tools.cavebot_index, #waypoints)
    end
    return {
        waypoint_count = #waypoints,
        current_index = index,
    }
end

function Route.deleteRequest(tools)
    local state = Route.uiState(tools)
    local waypoints = type(tools) == "table" and tools.cavebot_waypoints or {}
    local label = state.waypoint_count > 0 and Route.label(waypoints[state.current_index], state.current_index) or "no waypoint"
    return {
        label = label,
        timeout_ms = 4500,
    }
end

function Route.contract()
    return {
        module = "ctoa_helper_route",
        mode = "passive",
        owns_waypoint_mutation = true,
        owns_editor_state = true,
        owns_editor_action = true,
        owns_distance_chebyshev = true,
        owns_position_key = true,
        owns_position_text = true,
        owns_probe_target = true,
        owns_probe_metadata = true,
        owns_retry_status = true,
        owns_progress_state = true,
        owns_target_selection = true,
        runtime_actions = false,
        movement_enabled = false,
        probe_mutates_route = false,
        probe_changes_arming = false,
        ui_widgets = false,
        pathfinding = false,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_ROUTE = Route

return Route
