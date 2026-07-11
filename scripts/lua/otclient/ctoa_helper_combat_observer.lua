-- ctoa_helper_combat_observer.lua [CTOA OTClient Native]
-- Passive combat/targeting observation domain for CTOAi Runtime 2.

local CombatObserver = rawget(_G, "CTOA_HELPER_COMBAT_OBSERVER") or {}

local MODULE_ID = "combat_observer"
local TASK_ID = "combat_observer.sample"
local EVENT_NAME = "combat.observed"

local function numberValue(value, fallback, minimum, maximum)
    local parsed = tonumber(value)
    if not parsed then
        parsed = fallback
    end
    if minimum and parsed < minimum then
        parsed = minimum
    end
    if maximum and parsed > maximum then
        parsed = maximum
    end
    return parsed
end

local function textValue(value, fallback, maximumLength)
    local text = tostring(value or fallback or "")
    if maximumLength and #text > maximumLength then
        return text:sub(1, maximumLength)
    end
    return text
end

local function normalizeTarget(target)
    local item = type(target) == "table" and target or {}
    return {
        present = item.present == true,
        name = textValue(item.name, "", 80),
        health_percent = numberValue(item.health_percent, 0, 0, 100),
        distance = numberValue(item.distance, 0, 0, 64),
        shootable = item.shootable == true,
        monster = item.monster == true,
        player = item.player == true,
    }
end

local function normalizeSpectators(spectators)
    local source = type(spectators) == "table" and spectators or {}
    return {
        monsters = numberValue(source.monsters, 0, 0, 512),
        players = numberValue(source.players, 0, 0, 512),
        party_members = numberValue(source.party_members, 0, 0, 512),
        visible = numberValue(source.visible, 0, 0, 1024),
    }
end

function CombatObserver.normalizeObservation(snapshot)
    local source = type(snapshot) == "table" and snapshot or {}
    local target = normalizeTarget(source.target)
    if not target.present then
        target.name = ""
        target.health_percent = 0
        target.distance = 0
        target.shootable = false
        target.monster = false
        target.player = false
    end
    return {
        schema_version = "ctoa.combat-observation.v1",
        observed_at_ms = numberValue(source.observed_at_ms, 0, 0),
        online = source.online == true,
        protection_zone = source.protection_zone == true,
        latency_ms = numberValue(source.latency_ms, 0, 0, 60000),
        action_lock_ms = numberValue(source.action_lock_ms, 0, 0, 60000),
        attack_cooldown = source.attack_cooldown == true,
        spell_cooldown = source.spell_cooldown == true,
        target = target,
        spectators = normalizeSpectators(source.spectators),
        source = textValue(source.source, "adapter", 40),
        runtime_actions = false,
    }
end

function CombatObserver.observe(snapshot, runtimeCore)
    local observation = CombatObserver.normalizeObservation(snapshot)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    local published = {event = EVENT_NAME, delivered = 0, failures = {}}
    if core and type(core.publish) == "function" then
        published = core.publish(EVENT_NAME, observation)
    end
    return {observation = observation, published = published}
end

function CombatObserver.attach(runtimeCore, provider)
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
        metadata = {event = EVENT_NAME, schema_version = "ctoa.combat-observation.v1"},
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
            local snapshot = provider(context)
            CombatObserver.observe(snapshot, core)
        end,
    })
    if not taskOk and taskResult ~= "task_already_registered" then
        return false, taskResult
    end
    return true, {module_id = MODULE_ID, task_id = TASK_ID, enabled = false}
end

function CombatObserver.contract()
    return {
        mode = "passive_observer",
        schema_version = "ctoa.combat-observation.v1",
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

_G.CTOA_HELPER_COMBAT_OBSERVER = CombatObserver
return CombatObserver
