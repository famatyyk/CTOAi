-- ctoa_helper_equipment_observer.lua [CTOA OTClient Native]
-- Passive equipment-slot observation domain for CTOAi Runtime 2.

local Observer = rawget(_G, "CTOA_HELPER_EQUIPMENT_OBSERVER") or {}
local MODULE_ID, TASK_ID, EVENT_NAME = "equipment_observer", "equipment_observer.sample", "equipment.observed"

local function numberValue(value, fallback, minimum)
    local parsed = tonumber(value) or fallback
    if minimum and parsed < minimum then parsed = minimum end
    return parsed
end

local function slot(source, name)
    local item = type(source[name]) == "table" and source[name] or {}
    return {present = item.present == true, item_id = numberValue(item.item_id, 0, 0), count = numberValue(item.count, 0, 0)}
end

function Observer.normalizeObservation(snapshot)
    local source = type(snapshot) == "table" and snapshot or {}
    local slots = type(source.slots) == "table" and source.slots or {}
    return {
        schema_version = "ctoa.equipment-observation.v1",
        observed_at_ms = numberValue(source.observed_at_ms, 0, 0),
        online = source.online == true,
        inventory_api_available = source.inventory_api_available == true,
        slots = {ring = slot(slots, "ring"), amulet = slot(slots, "amulet"),
            left = slot(slots, "left"), right = slot(slots, "right")},
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
        metadata = {event = EVENT_NAME, schema_version = "ctoa.equipment-observation.v1"}})
    if not moduleOk and moduleReason ~= "module_already_registered" then return false, moduleReason end
    local taskOk, taskReason = core.registerTask({id = TASK_ID, owner = MODULE_ID, interval_ms = 1500,
        enabled = false, observer_only = true,
        run = function(context) Observer.observe(provider(context), core) end})
    if not taskOk and taskReason ~= "task_already_registered" then return false, taskReason end
    return true, {module_id = MODULE_ID, task_id = TASK_ID, enabled = false}
end

function Observer.contract()
    return {mode = "passive_observer", schema_version = "ctoa.equipment-observation.v1", event_name = EVENT_NAME,
        task_enabled_by_default = false, runtime_actions = false, swaps_items = false, moves_items = false,
        uses_items = false, executes_plans = false}
end

_G.CTOA_HELPER_EQUIPMENT_OBSERVER = Observer
return Observer
