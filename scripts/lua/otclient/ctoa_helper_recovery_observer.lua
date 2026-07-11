-- ctoa_helper_recovery_observer.lua [CTOA OTClient Native]
-- Passive recovery/healing observation domain for CTOAi Runtime 2.

local RecoveryObserver = rawget(_G, "CTOA_HELPER_RECOVERY_OBSERVER") or {}

local MODULE_ID = "recovery_observer"
local TASK_ID = "recovery_observer.sample"
local EVENT_NAME = "recovery.observed"

local function numberValue(value, fallback, minimum, maximum)
    local parsed = tonumber(value)
    if not parsed then parsed = fallback end
    if minimum and parsed < minimum then parsed = minimum end
    if maximum and parsed > maximum then parsed = maximum end
    return parsed
end

local function percentage(value, maximum, fallback)
    local current = numberValue(value, 0, 0)
    local total = numberValue(maximum, 0, 0)
    if total > 0 then
        return math.max(0, math.min(100, math.floor((current / total) * 100 + 0.5)))
    end
    return numberValue(fallback, 0, 0, 100)
end

function RecoveryObserver.normalizeObservation(snapshot)
    local source = type(snapshot) == "table" and snapshot or {}
    local hp = numberValue(source.hp, 0, 0)
    local maxHp = numberValue(source.max_hp, 0, 0)
    local mana = numberValue(source.mana, 0, 0)
    local maxMana = numberValue(source.max_mana, 0, 0)
    return {
        schema_version = "ctoa.recovery-observation.v1",
        observed_at_ms = numberValue(source.observed_at_ms, 0, 0),
        online = source.online == true,
        protection_zone = source.protection_zone == true,
        hp = hp,
        max_hp = maxHp,
        hp_percent = percentage(hp, maxHp, source.hp_percent),
        mana = mana,
        max_mana = maxMana,
        mana_percent = percentage(mana, maxMana, source.mana_percent),
        states = numberValue(source.states, 0, 0),
        source = tostring(source.source or "adapter"),
        runtime_actions = false,
    }
end

function RecoveryObserver.observe(snapshot, runtimeCore)
    local observation = RecoveryObserver.normalizeObservation(snapshot)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    local published = {event = EVENT_NAME, delivered = 0, failures = {}}
    if core and type(core.publish) == "function" then
        published = core.publish(EVENT_NAME, observation)
    end
    return {observation = observation, published = published}
end

function RecoveryObserver.attach(runtimeCore, provider)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    if type(core) ~= "table" or type(core.registerModule) ~= "function" or type(core.registerTask) ~= "function" then
        return false, "runtime_core_required"
    end
    if type(provider) ~= "function" then
        return false, "observation_provider_required"
    end
    local moduleOk, moduleResult = core.registerModule({
        id = MODULE_ID,
        mode = "observer",
        enabled = false,
        dependencies = {"runtime_policy", "dispatch_guard"},
        healthcheck = function()
            return {status = "ready", mode = "observer", runtime_actions = false}
        end,
        metadata = {event = EVENT_NAME, schema_version = "ctoa.recovery-observation.v1"},
    })
    if not moduleOk and moduleResult ~= "module_already_registered" then
        return false, moduleResult
    end
    local taskOk, taskResult = core.registerTask({
        id = TASK_ID,
        owner = MODULE_ID,
        interval_ms = 250,
        enabled = false,
        observer_only = true,
        run = function(context)
            RecoveryObserver.observe(provider(context), core)
        end,
    })
    if not taskOk and taskResult ~= "task_already_registered" then
        return false, taskResult
    end
    return true, {module_id = MODULE_ID, task_id = TASK_ID, enabled = false}
end

function RecoveryObserver.contract()
    return {
        mode = "passive_observer",
        schema_version = "ctoa.recovery-observation.v1",
        event_name = EVENT_NAME,
        task_id = TASK_ID,
        task_enabled_by_default = false,
        runtime_actions = false,
        executes_plans = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
    }
end

_G.CTOA_HELPER_RECOVERY_OBSERVER = RecoveryObserver
return RecoveryObserver
