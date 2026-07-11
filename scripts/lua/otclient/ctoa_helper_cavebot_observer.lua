-- ctoa_helper_cavebot_observer.lua [CTOA OTClient Native]
-- Passive cavebot/pathing observation domain for CTOAi Runtime 2.

local Observer = rawget(_G, "CTOA_HELPER_CAVEBOT_OBSERVER") or {}
local MODULE_ID, TASK_ID, EVENT_NAME = "cavebot_observer", "cavebot_observer.sample", "cavebot.observed"

local function numberValue(value, fallback, minimum)
    local parsed = tonumber(value) or fallback
    if minimum and parsed < minimum then parsed = minimum end
    return parsed
end

function Observer.normalizeObservation(snapshot)
    local source = type(snapshot) == "table" and snapshot or {}
    local position = type(source.position) == "table" and source.position or {}
    return {
        schema_version = "ctoa.cavebot-observation.v1",
        observed_at_ms = numberValue(source.observed_at_ms, 0, 0),
        online = source.online == true,
        protection_zone = source.protection_zone == true,
        position = {x = numberValue(position.x, 0), y = numberValue(position.y, 0), z = numberValue(position.z, 0)},
        auto_walking = source.auto_walking == true,
        can_walk = source.can_walk == true,
        tile_walkable = source.tile_walkable == true,
        path_api_available = source.path_api_available == true,
        route_size = numberValue(source.route_size, 0, 0),
        route_index = numberValue(source.route_index, 0, 0),
        source = tostring(source.source or "adapter"),
        runtime_actions = false,
    }
end

function Observer.observe(snapshot, runtimeCore)
    local observation = Observer.normalizeObservation(snapshot)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    local published = {event = EVENT_NAME, delivered = 0, failures = {}}
    if core and type(core.publish) == "function" then published = core.publish(EVENT_NAME, observation) end
    return {observation = observation, published = published}
end

function Observer.attach(runtimeCore, provider)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    if type(core) ~= "table" or type(provider) ~= "function" then return false, "runtime_core_and_provider_required" end
    local moduleOk, moduleReason = core.registerModule({id = MODULE_ID, mode = "observer", enabled = false,
        dependencies = {"runtime_policy", "dispatch_guard"},
        healthcheck = function() return {status = "ready", mode = "observer", runtime_actions = false} end,
        metadata = {event = EVENT_NAME, schema_version = "ctoa.cavebot-observation.v1"}})
    if not moduleOk and moduleReason ~= "module_already_registered" then return false, moduleReason end
    local taskOk, taskReason = core.registerTask({id = TASK_ID, owner = MODULE_ID, interval_ms = 500,
        enabled = false, observer_only = true,
        run = function(context) Observer.observe(provider(context), core) end})
    if not taskOk and taskReason ~= "task_already_registered" then return false, taskReason end
    return true, {module_id = MODULE_ID, task_id = TASK_ID, enabled = false}
end

function Observer.contract()
    return {mode = "passive_observer", schema_version = "ctoa.cavebot-observation.v1", event_name = EVENT_NAME,
        task_enabled_by_default = false, runtime_actions = false, pathfinding = false, walks = false, executes_plans = false}
end

_G.CTOA_HELPER_CAVEBOT_OBSERVER = Observer
return Observer
