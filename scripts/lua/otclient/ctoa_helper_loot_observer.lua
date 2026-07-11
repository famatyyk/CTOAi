-- ctoa_helper_loot_observer.lua [CTOA OTClient Native]
-- Passive container/loot observation domain for CTOAi Runtime 2.

local Observer = rawget(_G, "CTOA_HELPER_LOOT_OBSERVER") or {}
local MODULE_ID, TASK_ID, EVENT_NAME = "loot_observer", "loot_observer.sample", "loot.observed"

local function numberValue(value, fallback, minimum)
    local parsed = tonumber(value) or fallback
    if minimum and parsed < minimum then parsed = minimum end
    return parsed
end

function Observer.normalizeObservation(snapshot)
    local source = type(snapshot) == "table" and snapshot or {}
    return {
        schema_version = "ctoa.loot-observation.v1",
        observed_at_ms = numberValue(source.observed_at_ms, 0, 0),
        online = source.online == true,
        open_container_count = numberValue(source.open_container_count, 0, 0),
        visible_item_count = numberValue(source.visible_item_count, 0, 0),
        free_capacity = numberValue(source.free_capacity, 0, 0),
        container_api_available = source.container_api_available == true,
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
        metadata = {event = EVENT_NAME, schema_version = "ctoa.loot-observation.v1"}})
    if not moduleOk and moduleReason ~= "module_already_registered" then return false, moduleReason end
    local taskOk, taskReason = core.registerTask({id = TASK_ID, owner = MODULE_ID, interval_ms = 750,
        enabled = false, observer_only = true,
        run = function(context) Observer.observe(provider(context), core) end})
    if not taskOk and taskReason ~= "task_already_registered" then return false, taskReason end
    return true, {module_id = MODULE_ID, task_id = TASK_ID, enabled = false}
end

function Observer.contract()
    return {mode = "passive_observer", schema_version = "ctoa.loot-observation.v1", event_name = EVENT_NAME,
        task_enabled_by_default = false, runtime_actions = false, scans_containers = false, opens_containers = false,
        moves_items = false, uses_items = false, executes_plans = false}
end

_G.CTOA_HELPER_LOOT_OBSERVER = Observer
return Observer
