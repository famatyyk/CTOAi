-- ctoa_helper_modules.lua [CTOA OTClient Native]
-- Passive module registry domain for the helper UI and audits.

local Registry = rawget(_G, "CTOA_HELPER_MODULES") or {}

-- Single ordered source of truth for helper boot. The loader bootstraps this
-- registry first and then consumes a defensive copy of this manifest.
local SUPPORT_MODULES = {
    {name = "ctoa_helper_runtime_core", file = "ctoa_helper_runtime_core.lua", phase = "core", depends_on = {}},
    {name = "ctoa_helper_domain_contract", file = "ctoa_helper_domain_contract.lua", phase = "core", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_combat_observer", file = "ctoa_helper_combat_observer.lua", phase = "observe", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_recovery_observer", file = "ctoa_helper_recovery_observer.lua", phase = "observe", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_cavebot_observer", file = "ctoa_helper_cavebot_observer.lua", phase = "observe", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_loot_observer", file = "ctoa_helper_loot_observer.lua", phase = "observe", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_equipment_observer", file = "ctoa_helper_equipment_observer.lua", phase = "observe", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_otclient_observation_adapter", file = "ctoa_helper_otclient_observation_adapter.lua", phase = "observe", depends_on = {"ctoa_helper_combat_observer", "ctoa_helper_recovery_observer"}},
    {name = "ctoa_helper_ui", file = "ctoa_helper_ui.lua", phase = "present", depends_on = {}},
    {name = "ctoa_helper_client_reporter", file = "ctoa_helper_client_reporter.lua", phase = "present", depends_on = {}},
    {name = "ctoa_helper_diagnostics", file = "ctoa_helper_diagnostics.lua", phase = "present", depends_on = {}},
    {name = "ctoa_helper_hotkeys", file = "ctoa_helper_hotkeys.lua", phase = "present", depends_on = {}},
    {name = "ctoa_helper_modal", file = "ctoa_helper_modal.lua", phase = "present", depends_on = {}},
    {name = "ctoa_helper_route", file = "ctoa_helper_route.lua", phase = "domain", depends_on = {}},
    {name = "ctoa_helper_targeting", file = "ctoa_helper_targeting.lua", phase = "domain", depends_on = {}},
    {name = "ctoa_helper_combat_runtime", file = "ctoa_helper_combat_runtime.lua", phase = "domain", depends_on = {"ctoa_helper_targeting"}},
    {name = "ctoa_helper_cavebot_runtime", file = "ctoa_helper_cavebot_runtime.lua", phase = "domain", depends_on = {"ctoa_helper_route"}},
    {name = "ctoa_helper_loot_runtime", file = "ctoa_helper_loot_runtime.lua", phase = "domain", depends_on = {"ctoa_helper_loot_observer"}},
    {name = "ctoa_helper_timer_runtime", file = "ctoa_helper_timer_runtime.lua", phase = "domain", depends_on = {"ctoa_helper_runtime_core"}},
    {name = "ctoa_helper_recovery_runtime", file = "ctoa_helper_recovery_runtime.lua", phase = "domain", depends_on = {"ctoa_helper_recovery_observer"}},
    {name = "ctoa_helper_profile_schema", file = "ctoa_helper_profile_schema.lua", phase = "profile", depends_on = {}},
    {name = "ctoa_helper_profile_persistence", file = "ctoa_helper_profile_persistence.lua", phase = "profile", depends_on = {"ctoa_helper_profile_schema"}},
    {name = "ctoa_helper_operator_summary", file = "ctoa_helper_operator_summary.lua", phase = "coordinate", depends_on = {"ctoa_helper_profile_schema"}},
    {name = "ctoa_helper_planner", file = "ctoa_helper_planner.lua", phase = "coordinate", depends_on = {}},
    {name = "ctoa_helper_runtime_policy", file = "ctoa_helper_runtime_policy.lua", phase = "guard", depends_on = {}},
    {name = "ctoa_helper_dispatch_guard", file = "ctoa_helper_dispatch_guard.lua", phase = "guard", depends_on = {"ctoa_helper_runtime_policy"}},
    {name = "ctoa_helper_plan_queue", file = "ctoa_helper_plan_queue.lua", phase = "guard", depends_on = {"ctoa_helper_dispatch_guard"}},
    {name = "ctoa_helper_runtime_readiness", file = "ctoa_helper_runtime_readiness.lua", phase = "evidence", depends_on = {"ctoa_helper_plan_queue"}},
    {name = "ctoa_helper_module_status", file = "ctoa_helper_module_status.lua", phase = "evidence", depends_on = {"ctoa_helper_runtime_readiness"}},
    {name = "ctoa_helper_action_catalog", file = "ctoa_helper_action_catalog.lua", phase = "evidence", depends_on = {"ctoa_helper_runtime_policy"}},
    {name = "ctoa_helper_decision_trace", file = "ctoa_helper_decision_trace.lua", phase = "evidence", depends_on = {"ctoa_helper_dispatch_guard", "ctoa_helper_plan_queue"}},
    {name = "ctoa_helper_decision_pipeline", file = "ctoa_helper_decision_pipeline.lua", phase = "coordinate", depends_on = {"ctoa_helper_planner", "ctoa_helper_runtime_policy", "ctoa_helper_dispatch_guard", "ctoa_helper_plan_queue", "ctoa_helper_runtime_readiness", "ctoa_helper_action_catalog", "ctoa_helper_decision_trace"}},
    {name = "ctoa_helper_sandbox_handoff", file = "ctoa_helper_sandbox_handoff.lua", phase = "evidence", depends_on = {"ctoa_helper_runtime_readiness"}},
    {name = "ctoa_helper_feature_flags", file = "ctoa_helper_feature_flags.lua", phase = "guard", depends_on = {"ctoa_helper_runtime_policy"}},
    {name = "ctoa_helper_hud", file = "ctoa_helper_hud.lua", phase = "feature", depends_on = {"ctoa_helper_ui"}},
    {name = "ctoa_helper_conditions", file = "ctoa_helper_conditions.lua", phase = "feature", depends_on = {"ctoa_helper_recovery_observer"}},
    {name = "ctoa_helper_equipment", file = "ctoa_helper_equipment.lua", phase = "feature", depends_on = {"ctoa_helper_equipment_observer"}},
    {name = "ctoa_helper_scripting", file = "ctoa_helper_scripting.lua", phase = "feature", depends_on = {"ctoa_helper_runtime_policy"}},
    {name = "ctoa_helper_heal_friend", file = "ctoa_helper_heal_friend.lua", phase = "feature", depends_on = {"ctoa_helper_recovery_observer"}},
}

local MODULE_LANES = {
    {
        id = "healing",
        label = "Healing",
        profile_key = "healing",
        stage = "implemented",
        mode = "runtime",
        gate = "ValidateDev plus in-world HP/MP sandbox log evidence"
    },
    {
        id = "combat",
        label = "Combat",
        profile_key = "tools",
        stage = "implemented",
        mode = "runtime",
        gate = "PZ/NPC regression log plus SmokeAttachAll hunting views"
    },
    {
        id = "cavebot",
        label = "CaveBot",
        profile_key = "tools",
        stage = "implemented",
        mode = "runtime",
        gate = "Route editor tests plus sandbox autoWalk retry evidence"
    },
    {
        id = "loot",
        label = "Loot",
        profile_key = "tools",
        stage = "implemented",
        mode = "experimental",
        gate = "Bounded ctoa_local.log loot scan evidence in sandbox"
    },
    {
        id = "timer",
        label = "Timer",
        profile_key = "tools",
        stage = "implemented",
        mode = "bounded_action",
        gate = "Static contract plus sandbox log evidence for one timer tick"
    },
    {
        id = "heal_friend",
        label = "Heal Friend",
        profile_key = "heal_friend",
        stage = "prototype",
        mode = "planner",
        gate = "No runtime sio cast until whitelist sandbox smoke passes"
    },
    {
        id = "conditions",
        label = "Conditions",
        profile_key = "conditions",
        stage = "prototype",
        mode = "read_only_observer",
        gate = "No recovery action until condition observer sandbox smoke passes"
    },
    {
        id = "equipment",
        label = "Equipment",
        profile_key = "equipment",
        stage = "prototype",
        mode = "read_only_observer",
        gate = "No runtime swap until inventory API probe and sandbox smoke pass"
    },
    {
        id = "scripting",
        label = "Scripting",
        profile_key = "scripting",
        stage = "prototype",
        mode = "policy_shell",
        gate = "No user snippet execution until security review and sandbox smoke pass"
    }
}

local MODULE_SHORT_LABELS = {
    healing = "Heal",
    combat = "Combat",
    cavebot = "Cave",
    loot = "Loot",
    timer = "Timer",
    heal_friend = "Friend",
    conditions = "Cond",
    equipment = "Equip",
    scripting = "Script"
}

local function copyList(values)
    local copied = {}
    for index, value in ipairs(values or {}) do
        copied[index] = value
    end
    return copied
end

function Registry.getSupportModules()
    local modules = {}
    for index, module in ipairs(SUPPORT_MODULES) do
        modules[index] = {
            name = module.name,
            file = module.file,
            phase = module.phase,
            depends_on = copyList(module.depends_on),
        }
    end
    return modules
end

function Registry.validateSupportModules(modules)
    local seen = {ctoa_helper_modules = true}
    local errors = {}
    for index, module in ipairs(modules or {}) do
        local name = type(module) == "table" and tostring(module.name or "") or ""
        local file = type(module) == "table" and tostring(module.file or "") or ""
        if name == "" or file == "" then
            errors[#errors + 1] = "invalid module descriptor at " .. tostring(index)
        elseif seen[name] then
            errors[#errors + 1] = "duplicate module " .. name
        else
            for _, dependency in ipairs(module.depends_on or {}) do
                if not seen[dependency] then
                    errors[#errors + 1] = name .. " depends on unavailable " .. tostring(dependency)
                end
            end
            seen[name] = true
        end
    end
    return #errors == 0, errors
end

function Registry.bootSnapshot(loadedModules)
    local loaded = loadedModules or {}
    local phases = {}
    local phaseOrder = {}
    local missing = {}
    local dependencyBlockers = {}
    local loadedCount = 0
    for _, module in ipairs(SUPPORT_MODULES) do
        local phase = tostring(module.phase or "unknown")
        if not phases[phase] then
            phases[phase] = {phase = phase, total = 0, loaded = 0, missing = 0}
            phaseOrder[#phaseOrder + 1] = phase
        end
        local row = phases[phase]
        row.total = row.total + 1
        local isLoaded = loaded[module.name] == true
        if isLoaded then
            row.loaded = row.loaded + 1
            loadedCount = loadedCount + 1
        else
            row.missing = row.missing + 1
            missing[#missing + 1] = module.name
        end
        for _, dependency in ipairs(module.depends_on or {}) do
            if loaded[dependency] ~= true and dependency ~= "ctoa_helper_modules" then
                dependencyBlockers[#dependencyBlockers + 1] = module.name .. "<-" .. dependency
            end
        end
    end
    local phaseRows = {}
    for _, phase in ipairs(phaseOrder) do
        phaseRows[#phaseRows + 1] = phases[phase]
    end
    return {
        status = #missing == 0 and #dependencyBlockers == 0 and "ready" or "blocked",
        total = #SUPPORT_MODULES,
        loaded = loadedCount,
        phase_count = #phaseRows,
        phases = phaseRows,
        missing = missing,
        dependency_blockers = dependencyBlockers,
        runtime_actions = false,
    }
end

function Registry.bootSummary(snapshot)
    local item = snapshot or {}
    return "Boot " .. tostring(item.status or "unknown") ..
        " | phases " .. tostring(item.phase_count or 0) ..
        " | modules " .. tostring(item.loaded or 0) .. "/" .. tostring(item.total or 0) ..
        " | missing " .. tostring(#(item.missing or {})) ..
        " | deps " .. tostring(#(item.dependency_blockers or {}))
end

function Registry.getModuleLanes()
    return MODULE_LANES
end

function Registry.getShortLabels()
    return MODULE_SHORT_LABELS
end

function Registry.laneEnabled(lane, config)
    if not lane then
        return false
    end
    local cfg = config or {}
    local healing = cfg.healing or {}
    local tools = cfg.tools or {}
    if lane.id == "healing" then
        return healing.spell_enabled == true or healing.potion_enabled == true or healing.mana_potion_enabled == true
    end
    if lane.id == "combat" then
        return tools.auto_attack == true or tools.spell_rotation == true or tools.rune_enabled == true
    end
    if lane.id == "cavebot" then
        return tools.cavebot_enabled == true or tools.cavebot_movement_enabled == true
    end
    if lane.id == "loot" then
        return tools.experimental_loot == true
    end
    if lane.id == "timer" then
        return tools.timer_enabled == true
    end
    local domain = cfg[lane.profile_key]
    return type(domain) == "table" and domain.enabled == true
end

function Registry.laneRuntimeText(lane, config)
    if not lane then
        return "unknown"
    end
    if lane.stage == "prototype" then
        local cfg = config or {}
        local domain = cfg[lane.profile_key]
        if type(domain) == "table" and domain.runtime_enabled == true then
            return "prototype runtime"
        end
        return "prototype gated"
    end
    if Registry.laneEnabled(lane, config) then
        return tostring(lane.mode or "runtime") .. " armed"
    end
    return tostring(lane.mode or "runtime") .. " idle"
end

function Registry.registrySummary(lanes, config)
    local implemented = 0
    local prototypes = 0
    local armed = 0
    for _, lane in ipairs(lanes or MODULE_LANES) do
        if lane.stage == "implemented" then
            implemented = implemented + 1
        elseif lane.stage == "prototype" then
            prototypes = prototypes + 1
        end
        if Registry.laneEnabled(lane, config) then
            armed = armed + 1
        end
    end
    return tostring(implemented) .. " impl / " .. tostring(prototypes) .. " proto / " .. tostring(armed) .. " armed"
end

function Registry.readinessTag(lane, config)
    if not lane then
        return "UNKNOWN"
    end
    local enabled = Registry.laneEnabled(lane, config)
    if lane.stage == "prototype" then
        if enabled then
            return "OBSERVE"
        end
        return "GATED"
    end
    if lane.mode == "experimental" and not enabled then
        return "FLAG"
    end
    if enabled then
        return "ARMED"
    end
    return "IDLE"
end

function Registry.readinessRow(stage, lanes, config, labels)
    local parts = {}
    local shortLabels = labels or MODULE_SHORT_LABELS
    for _, lane in ipairs(lanes or MODULE_LANES) do
        if lane.stage == stage then
            local label = shortLabels[lane.id] or lane.label or lane.id
            parts[#parts + 1] = tostring(label) .. ":" .. Registry.readinessTag(lane, config)
        end
    end
    if #parts == 0 then
        return tostring(stage or "modules") .. ": none"
    end
    return table.concat(parts, "  ")
end

function Registry.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        owns_boot_manifest = true,
        validates_boot_dependencies = true,
        owns_boot_status = true,
        owns_lane_readiness = true,
        owns_lane_enabled = true,
        owns_lane_runtime_text = true,
        owns_registry_summary = true,
        owns_readiness_row = true,
        gate = "Registry parity test plus Overview readiness smoke."
    }
end

_G.CTOA_HELPER_MODULES = Registry
return Registry
