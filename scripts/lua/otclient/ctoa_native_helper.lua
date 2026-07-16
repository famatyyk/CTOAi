-- ctoa_native_helper.lua  [CTOA OTClient Native]
-- Compact in-client helper panel inspired by OTClient helper UIs.

local existingHelper = rawget(_G, "CTOA_Helper")
if type(existingHelper) == "table" and existingHelper.window then
    if type(existingHelper.handleGameStart) == "function" then
        pcall(existingHelper.handleGameStart)
    end
    return existingHelper
end

local HELPER_VERSION = "v2.4.1"
local externalProfileSchema = rawget(_G, "CTOA_HELPER_PROFILE_SCHEMA")
if type(externalProfileSchema) ~= "table" or type(externalProfileSchema.defaultProfile) ~= "function" then
    _G.CTOA_HELPER_BOOT_BLOCKER = "profile_schema_defaults_unavailable"
    return nil
end
local defaultProfileOk, HELPER_CONFIG = pcall(externalProfileSchema.defaultProfile)
if not defaultProfileOk or type(HELPER_CONFIG) ~= "table" then
    _G.CTOA_HELPER_BOOT_BLOCKER = "profile_schema_defaults_invalid"
    return nil
end
local externalModules = rawget(_G, "CTOA_HELPER_MODULES")
local externalUi = rawget(_G, "CTOA_HELPER_UI")
local externalClientReporter = rawget(_G, "CTOA_HELPER_CLIENT_REPORTER")
local externalObservationAdapter = rawget(_G, "CTOA_HELPER_OTCLIENT_OBSERVATION_ADAPTER")
local externalRuntimeCore = rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
local MODULE_LANES = {}
local MODULE_LANE_INDEX = {}

local function moduleCall(module, functionName, ...)
    if type(module) == "table" and type(module[functionName]) == "function" then
        local ok, value, extra, detail = pcall(module[functionName], ...)
        if ok then
            return true, value, extra, detail
        end
    end
    return false, nil
end

local function moduleValue(module, functionName, ...)
    local ok, value, extra, detail = moduleCall(module, functionName, ...)
    if ok then
        return value, extra, detail
    end
    return nil
end

local externalLanes = moduleValue(externalModules, "getModuleLanes")
if type(externalLanes) == "table" and #externalLanes > 0 then
    MODULE_LANES = externalLanes
    MODULE_LANE_INDEX = moduleValue(externalModules, "rebuildModuleLaneIndex", MODULE_LANES) or {}
end

local Helper = {
    config = HELPER_CONFIG,
    window = nil,
    think_event = nil,
    auto_hide_event = nil,
    ui_save_event = nil,
    profile_save_event = nil,
    profile_dirty = false,
    ui_dirty = false,
    status_label = nil,
    hud_label = nil,
    widgets = {},
    sections = {},
    active_tab = "overview",
    smoke_tab = nil,
    smoke_subtab = nil,
    active_hunting_tab = "targeting",
    magic_rule_index = 1,
    active_tools_tab = "helper",
    cavebot_editor_bindings = {},
    profile_name = "Built-in EK", vocation_id = "ek",
    vocation_source = "default", last_vocation_probe_ms = 0,
    profile_path = nil, ui_path = nil,
    bound_hotkey = nil, pending_confirm = nil,
    current_target_id = 0, target_start_ms = 0,
    last_retarget_ms = 0, last_target_log_ms = 0,
    last_runtime_block_reason = nil, last_runtime_block_ms = 0,
    last_client_report_ms = 0,
    client_report_path = nil
}

local delay
local flushProfileSave
local flushUiPrefsSave
local markUiPrefsDirty
local rebuildUi
local refreshOperatorSummaries
local switchTab
local switchHuntingSubtab
local switchToolsSubtab
local THEME_PRESETS

local UI_STYLE = moduleValue(externalUi, "newStyle") or {}

local UI_THEMES = moduleValue(externalUi, "themes") or {}

local UI_LAYOUT = moduleValue(externalUi, "newLayout") or {}

local shortText = externalUi and externalUi.shortText or tostring; local fitText = externalUi and externalUi.fitText or shortText

local externalDiagnostics = rawget(_G, "CTOA_HELPER_DIAGNOSTICS")
local hasApi = externalDiagnostics and externalDiagnostics.hasApi
local safeCall = externalDiagnostics and externalDiagnostics.safeCall
local safeGlobalCall = externalDiagnostics and externalDiagnostics.safeGlobalCall
local externalHealFriend = rawget(_G, "CTOA_HELPER_HEAL_FRIEND")
local externalConditions = rawget(_G, "CTOA_HELPER_CONDITIONS")
local externalEquipment = rawget(_G, "CTOA_HELPER_EQUIPMENT")
local externalEquipmentFamilyRegistry = rawget(_G, "CTOA_HELPER_EQUIPMENT_FAMILY_REGISTRY")
local externalScripting = rawget(_G, "CTOA_HELPER_SCRIPTING")
local externalHud = rawget(_G, "CTOA_HELPER_HUD")
local externalHotkeys = rawget(_G, "CTOA_HELPER_HOTKEYS")
local externalModal = rawget(_G, "CTOA_HELPER_MODAL")
local externalRoute = rawget(_G, "CTOA_HELPER_ROUTE")
local externalTargeting = rawget(_G, "CTOA_HELPER_TARGETING")
local externalCombatRuntime = rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME")
local externalSpellStateRegistry = rawget(_G, "CTOA_HELPER_SPELL_STATE_REGISTRY")
local externalCavebotRuntime = rawget(_G, "CTOA_HELPER_CAVEBOT_RUNTIME")
local externalLootRuntime = rawget(_G, "CTOA_HELPER_LOOT_RUNTIME")
local externalTimerRuntime = rawget(_G, "CTOA_HELPER_TIMER_RUNTIME")
local externalRecoveryRuntime = rawget(_G, "CTOA_HELPER_RECOVERY_RUNTIME")
local externalRecoveryBridge = rawget(_G, "CTOA_HELPER_RECOVERY_BRIDGE")
local externalConditionsExecuteOnce = rawget(_G, "CTOA_HELPER_CONDITIONS_EXECUTE_ONCE")
local externalEquipmentExecuteOnce = rawget(_G, "CTOA_HELPER_EQUIPMENT_EXECUTE_ONCE")
local externalHealFriendExecuteOnce = rawget(_G, "CTOA_HELPER_HEAL_FRIEND_EXECUTE_ONCE")
local externalRuleEngine = rawget(_G, "CTOA_HELPER_RULE_ENGINE")
local externalVocationProfiles = rawget(_G, "CTOA_HELPER_VOCATION_PROFILES")
local externalProfilePersistence = rawget(_G, "CTOA_HELPER_PROFILE_PERSISTENCE")
local externalOperatorSummary = rawget(_G, "CTOA_HELPER_OPERATOR_SUMMARY")
local externalRuntimePolicy = rawget(_G, "CTOA_HELPER_RUNTIME_POLICY")
local externalDecisionPipeline = rawget(_G, "CTOA_HELPER_DECISION_PIPELINE")
local externalFeatureFlags = rawget(_G, "CTOA_HELPER_FEATURE_FLAGS")

local isGameOnline = externalObservationAdapter and externalObservationAdapter.isGameOnline
local getLocalPlayer = externalObservationAdapter and externalObservationAdapter.localPlayer
local getThingPosition = externalObservationAdapter and externalObservationAdapter.position
local currentTargetId = externalObservationAdapter and externalObservationAdapter.creatureId
local getCreatureHealthPercent = externalObservationAdapter and externalObservationAdapter.healthPercent
local pcallBool = externalDiagnostics and externalDiagnostics.callBoolean
local pcallNumber = externalDiagnostics and externalDiagnostics.callNumber
local hasAnyState = externalDiagnostics and externalDiagnostics.hasAnyState
local anyPcallBool = externalDiagnostics and externalDiagnostics.anyBooleanMethod

local function helperNowMs()
    if g_clock and g_clock.millis then
        local ok, value = pcall(function()
            return g_clock.millis()
        end)
        if ok and tonumber(value) then
            return tonumber(value)
        end
    end
    return (os.time and os.time() or 0) * 1000
end

local function appendLog(msg)
    if moduleValue(externalDiagnostics, "appendLog", msg, "CTOA-OTC-HELPER") then
        return
    end
    local f = io.open("ctoa_local.log", "a")
    if not f and g_resources and g_resources.getUserDir then
        local ok, userDir = pcall(function()
            return g_resources.getUserDir()
        end)
        if ok and userDir and userDir ~= "" then
            f = io.open(userDir .. "/ctoa_local.log", "a")
        end
    end
    if f then
        f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-OTC-HELPER] " .. msg .. "\n")
        f:close()
    end
end

function status(msg)
    appendLog(msg)
    if modules and modules.game_console and modules.game_console.addText then
        pcall(function()
            local modes = rawget(_G, "MessageModes")
            local mode = type(modes) == "table" and (modes.Status or modes.ModeStatus) or nil
            if mode ~= nil then
                modules.game_console.addText("[CTOA-HELPER] " .. msg, mode)
            else
                modules.game_console.addText("[CTOA-HELPER] " .. msg)
            end
        end)
    end
    if Helper.status_label and Helper.status_label.setText then
        Helper.status_label:setText("Status: " .. shortText(msg, 13))
    end
end

local function loadDataOnlyLua(path)
    if type(loadfile) ~= "function" then
        return false, "loadfile unavailable"
    end

    -- Profiles and UI preferences are declarative `return { ... }` files.
    -- Execute them without OTClient globals so a modified data file cannot
    -- talk, move, cast, access the filesystem, or schedule runtime callbacks.
    local environment = {}
    local chunk, loadError
    if type(setfenv) == "function" then
        chunk, loadError = loadfile(path)
        if type(chunk) == "function" then
            setfenv(chunk, environment)
        end
    else
        local called, loaded, message = pcall(loadfile, path, "t", environment)
        if called then
            chunk, loadError = loaded, message
        else
            loadError = loaded
        end
    end
    if type(chunk) ~= "function" then
        return false, loadError or "profile chunk unavailable"
    end

    local executed, value = pcall(chunk)
    if not executed then
        return false, value
    end
    if type(value) ~= "table" then
        return false, "data file must return a table"
    end
    return true, value
end

local function loadProfile(requestedVocation)
    if type(externalVocationProfiles) ~= "table" or type(externalProfileSchema) ~= "table" or type(externalProfilePersistence) ~= "table" then
        status("Profile blocked: required profile owner unavailable")
        return false
    end
    local player = g_game and g_game.getLocalPlayer and g_game.getLocalPlayer() or nil
    local detected, source, raw = moduleValue(externalVocationProfiles, "detect", player)
    if type(detected) ~= "string" or detected == "" then
        detected = Helper.vocation_id or "ek"
        source = source or "fallback"
    end
    local vocationId = requestedVocation or detected or "ek"
    local routed = moduleValue(externalVocationProfiles, "candidates", vocationId, player)
    local candidates = type(routed) == "table" and routed or moduleValue(externalProfilePersistence, "profilePersistenceTable", "profileCandidates", {
        "user_dir/ctoa_otclient/ctoa_ek_profile.lua",
        "ctoa_otclient/ctoa_ek_profile.lua",
        "/ctoa_ek_profile.lua"
    })
    candidates = type(candidates) == "table" and candidates or {}
    for _, path in ipairs(candidates) do
        if g_resources and g_resources.fileExists and g_resources.fileExists(path) then
            local ok, profile = loadDataOnlyLua(path)
            if ok and type(profile) == "table" then
                local packDecision = moduleValue(externalVocationProfiles, "validatePack", profile, vocationId)
                if type(packDecision) ~= "table" or packDecision.allowed ~= true then
                    local reason = type(packDecision) == "table" and packDecision.reason or "pack_validation_unavailable"
                    status("Profile blocked: " .. tostring(reason))
                    return false
                end
                local migrated, migration = moduleValue(externalProfileSchema, "migrate", profile, HELPER_CONFIG, externalRuleEngine)
                if type(migrated) ~= "table" then
                    local reason = type(migration) == "table" and migration.reason or "migration_unavailable"
                    status("Profile blocked: " .. tostring(reason))
                    return false
                end
                moduleValue(externalProfileSchema, "mergeTable", HELPER_CONFIG, migrated)
                Helper.profile_migration = migration
                Helper.profile_name = profile.name or path
                Helper.profile_path = path
                Helper.vocation_id = profile.vocation or vocationId
                Helper.vocation_source = source
                HELPER_CONFIG.vocation = Helper.vocation_id
                local vocationProbeText = moduleValue(externalDiagnostics, "vocationProbeText", {
                    raw = raw,
                    resolved = vocationId,
                    source = source
                })
                status(type(vocationProbeText) == "string" and vocationProbeText ~= "" and vocationProbeText or "Vocation diagnostics unavailable")
                status(moduleValue(externalProfilePersistence, "profilePersistenceValue", "loadSuccessText", "Profile loaded: " .. Helper.profile_name, "profile", Helper.profile_name))
                return true
            end
            status(moduleValue(externalProfilePersistence, "profilePersistenceValue", "loadFailureText", "Profile load failed: " .. path .. " " .. tostring(profile), "profile", path, profile))
        end
    end
    status("Profile unavailable for vocation: " .. tostring(vocationId))
    return false
end

local function applySafeBootRuntimeGuard()
    -- Safe boot is a startup-only guard.  A later UI action may arm this
    -- process, but each helper load begins disarmed again.
    Helper.runtime_session_armed = false
    if HELPER_CONFIG.safe_boot_runtime_disabled == false then
        return
    end
    HELPER_CONFIG.enabled = false
    HELPER_CONFIG.healing.spell_enabled = false
    HELPER_CONFIG.healing.potion_enabled = false
    HELPER_CONFIG.heal_friend.enabled = false
    HELPER_CONFIG.heal_friend.runtime_enabled = false
    HELPER_CONFIG.conditions.enabled = false
    HELPER_CONFIG.conditions.runtime_enabled = false
    HELPER_CONFIG.equipment.enabled = false
    HELPER_CONFIG.equipment.runtime_enabled = false
    HELPER_CONFIG.scripting.enabled = false
    HELPER_CONFIG.scripting.runtime_enabled = false
    HELPER_CONFIG.scripting.allow_user_snippets = false
    HELPER_CONFIG.scripting.allow_runtime_eval = false
    HELPER_CONFIG.tools.auto_attack = false
    HELPER_CONFIG.tools.chase = false
    HELPER_CONFIG.tools.auto_follow = false
    HELPER_CONFIG.tools.auto_haste = false
    HELPER_CONFIG.tools.spell_rotation = false
    HELPER_CONFIG.tools.auto_exeta = false
    HELPER_CONFIG.tools.rune_enabled = false
    HELPER_CONFIG.tools.timer_enabled = false
    status("Safe boot: runtime automation disabled")
end

local function runtimeArmingBlockedReason()
    if HELPER_CONFIG.safe_boot_runtime_disabled ~= false and Helper.runtime_session_armed ~= true then
        return "safe boot runtime disabled"
    end
    return nil
end

local function requestRuntimeSessionArm(reason)
    if HELPER_CONFIG.safe_boot_runtime_disabled == false or Helper.runtime_session_armed == true then
        return true
    end
    Helper.runtime_session_armed = true
    status("Runtime session armed by operator: " .. tostring(reason or "UI action"))
    return true
end

local function loadUiPrefs()
    if type(externalProfilePersistence) ~= "table" then
        status("UI prefs blocked: persistence owner unavailable")
        return false
    end
    local candidates = moduleValue(externalProfilePersistence, "profilePersistenceTable", "uiPrefsCandidates", {
        "user_dir/ctoa_otclient/ctoa_ui_prefs.lua",
        "ctoa_otclient/ctoa_ui_prefs.lua",
        "/ctoa_ui_prefs.lua"
    })
    candidates = type(candidates) == "table" and candidates or {}
    for _, path in ipairs(candidates) do
        if g_resources and g_resources.fileExists and g_resources.fileExists(path) then
            local ok, prefs = loadDataOnlyLua(path)
            if ok and type(prefs) == "table" then
                local plan = moduleValue(externalProfilePersistence, "profilePersistenceTable", "uiPrefsPlan", {}, prefs, HELPER_CONFIG, {
                    normalize_hotkey = type(externalHotkeys) == "table" and type(externalHotkeys.normalizeHelperHotkey) == "function" and externalHotkeys.normalizeHelperHotkey or nil
                })
                if type(plan) ~= "table" then status("UI prefs blocked: invalid persistence plan"); return false end
                if type(plan.config_updates) == "table" then
                    for key, value in pairs(plan.config_updates) do
                        HELPER_CONFIG[key] = value
                    end
                end
                if type(plan.hud_updates) == "table" then
                    HELPER_CONFIG.hud = HELPER_CONFIG.hud or {}
                    for key, value in pairs(plan.hud_updates) do
                        HELPER_CONFIG.hud[key] = value
                    end
                end
                if type(plan.helper_updates) == "table" then
                    for key, value in pairs(plan.helper_updates) do
                        Helper[key] = value
                    end
                end
                Helper.ui_path = path
                status(moduleValue(externalProfilePersistence, "profilePersistenceValue", "loadSuccessText", "UI prefs loaded: " .. path, "ui_prefs", path))
                return true
            end
            status(moduleValue(externalProfilePersistence, "profilePersistenceValue", "loadFailureText", "UI prefs load failed: " .. path .. " " .. tostring(prefs), "ui_prefs", path, prefs))
        end
    end
    status(moduleValue(externalProfilePersistence, "profilePersistenceValue", "loadSuccessText", "UI prefs loaded: defaults", "ui_prefs", "defaults"))
    return false
end

local function applyThemePreset(presetId)
    local theme = UI_THEMES[presetId or "graphite"] or UI_THEMES.graphite
    for key, value in pairs(theme) do
        UI_STYLE[key] = value
    end
    -- Semantic depth tokens keep every panel consistent while preserving the
    -- existing four palette presets and older OTClient widget capabilities.
    UI_STYLE.surface_low = theme.sidebar_fill or theme.panel_surface
    UI_STYLE.surface_raised = theme.panel_raised or theme.row_fill_active
    UI_STYLE.surface_inset = theme.value_fill or theme.panel_dark
    UI_STYLE.edge_highlight = theme.border_active or theme.border
    UI_STYLE.edge_shadow = theme.divider or theme.border
    UI_STYLE.state_on = theme.good or theme.accent
    UI_STYLE.state_off = theme.off or theme.muted; UI_STYLE.state_blocked = theme.blocked or "#d9825b"; UI_STYLE.state_stale = theme.stale or theme.accent or "#f0c36a"
end

function applyWindowPlacement()
    if not Helper.window then
        return
    end
    local x = tonumber(HELPER_CONFIG.window_x) or 520
    local y = tonumber(HELPER_CONFIG.window_y) or 34
    if Helper.window.setPosition then
        pcall(function()
            Helper.window:setPosition({x = x, y = y})
        end)
    elseif Helper.window.move then
        pcall(function()
            Helper.window:move(x, y)
        end)
    end
end

local function applyUiPrefs()
    moduleValue(externalUi, "configureLayout", UI_LAYOUT, HELPER_CONFIG.compact_mode == true)
    applyThemePreset(HELPER_CONFIG.theme_preset)
    applyWindowPlacement()
end

function setThemePreset(presetId)
    HELPER_CONFIG.theme_preset = presetId or "graphite"
    markUiPrefsDirty("theme_preset")
    rebuildUi()
    return false
end

function setCompactMode(enabled)
    HELPER_CONFIG.compact_mode = enabled and true or false
    markUiPrefsDirty("compact_mode")
    rebuildUi()
    return false
end

flushProfileSave = function()
    if type(externalProfileSchema) ~= "table" or type(externalProfilePersistence) ~= "table" then
        status("Profile save blocked: required profile owner unavailable")
        return false
    end
    if Helper.profile_save_event then
        removeEvent(Helper.profile_save_event)
        Helper.profile_save_event = nil
    end
    local defaults = moduleValue(externalProfilePersistence, "profilePersistenceTable", "saveDefaults", {}, "profile")
    local path = moduleValue(externalProfilePersistence, "profilePersistenceValue", "resolveSavePath", Helper.profile_path or "ctoa_ek_profile.lua", "profile", Helper.profile_path, g_resources and g_resources.getWorkDir and g_resources.getWorkDir() or "")
    defaults = type(defaults) == "table" and defaults or {}
    if type(path) ~= "string" or path == "" then status("Profile save blocked: save path unavailable"); return false end
    local exportedProfile = moduleValue(externalProfilePersistence, "exportProfile", HELPER_CONFIG, Helper.profile_name or "Built-in EK")
    local serializedProfile = moduleValue(externalProfileSchema, "serializeLua", exportedProfile, "profile")
    if type(serializedProfile) ~= "string" then status("Profile save blocked: serialization unavailable"); return false end
    local profileSaveText = moduleValue(externalProfilePersistence, "profilePersistenceValue", "saveText", "return " .. serializedProfile .. "\n", "profile", serializedProfile)
    if type(profileSaveText) ~= "string" then status("Profile save blocked: save text unavailable"); return false end
    local file = io.open(path, "w")
    if not file and path ~= "ctoa_ek_profile.lua" then
        local fallbackPath = moduleValue(externalProfilePersistence, "profilePersistenceValue", "fallbackSavePath", "ctoa_ek_profile.lua", "profile", path)
        file = io.open(fallbackPath, "w")
        if file then
            path = fallbackPath
        end
    end
    if not file then
        status(tostring(defaults.save_failed_status or "Profile save failed"))
        return false
    end

    file:write(profileSaveText)
    file:close()
    Helper.profile_dirty = false
    if Helper.widgets.profile_status and Helper.widgets.profile_status.setText then
        Helper.widgets.profile_status:setText(tostring(defaults.clean_status or "Autosave: saved"))
    end
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
    status(tostring(defaults.saved_status or "Profile saved"))
    return true
end

local PRIVILEGED_SMOKE_ACTIONS = {
    cavebot_test_walk = true,
    recovery_bridge_arm = true,
    recovery_bridge_execute_once = true,
    p12_conditions_execute_once = true,
    p12_equipment_execute_once = true,
    p12_heal_friend_execute_once = true
}

local function applySmokeCommand(command)
    if type(command) ~= "table" then
        return false
    end
    local target = moduleValue(externalDiagnostics, "smokeCommandTarget", command)
    if type(target) ~= "table" then
        return false
    end
    local action = target.action
    local tab = target.tab
    local subtab = target.subtab
    local theme = target.theme
    if action == "theme_set" then
        local allowed = false
        for _, presetId in ipairs(THEME_PRESETS or {}) do
            if presetId == theme then
                allowed = true
                break
            end
        end
        if not allowed then
            status("Smoke theme rejected: " .. tostring(theme))
            return false
        end
        setThemePreset(theme)
        if type(tab) ~= "string" or tab == "" then
            tab = "ui"
        end
    end
    switchTab(tab)
    if tab == "hunting" and subtab == "magic" then
        switchHuntingSubtab("magic")
    elseif tab == "tools" and type(subtab) == "string" and subtab ~= "" then
        switchToolsSubtab(subtab)
    end
    if Helper.window and Helper.window.show then
        Helper.window:show()
        Helper.window:raise()
        Helper.window:focus()
    end
    local visibleText = moduleValue(externalDiagnostics, "smokeCommandStatusText", "tab_visible", {target = target})
    if action == "theme_set" then
        status("Smoke theme visible: " .. tostring(theme))
        status(type(visibleText) == "string" and visibleText ~= "" and visibleText or "Smoke tab visible: " .. tostring(tab))
    else
        status(type(visibleText) == "string" and visibleText ~= "" and visibleText or "Smoke tab visible: " .. tostring(tab))
    end
    local privilegedBlocked = nil
    if PRIVILEGED_SMOKE_ACTIONS[action] == true and action ~= "p12_conditions_execute_once" and action ~= "p12_equipment_execute_once" and action ~= "p12_heal_friend_execute_once" then
        if HELPER_CONFIG.enabled ~= true then privilegedBlocked = "runtime disabled" else privilegedBlocked = runtimeArmingBlockedReason() end
    end
    if privilegedBlocked then
        local blockedText = moduleValue(externalDiagnostics, "smokeCommandStatusText", "blocked", {reason = privilegedBlocked})
        status(type(blockedText) == "string" and blockedText ~= "" and blockedText or "smoke blocked")
        return false
    end
    if action == "cavebot_probe" and Helper.runMovementApiProbe then
        return Helper.runMovementApiProbe("manual")
    elseif action == "cavebot_test_walk" and testCavebotAutoWalk then
        local blocked = runtimeArmingBlockedReason()
        if blocked then
            local blockedText = moduleValue(externalDiagnostics, "smokeCommandStatusText", "blocked", {reason = blocked})
            status(type(blockedText) == "string" and blockedText ~= "" and blockedText or "smoke blocked")
            return false
        end
        return testCavebotAutoWalk()
    elseif action == "cavebot_prev" and type(Helper.cavebot_editor_bindings.select) == "function" then
        return Helper.cavebot_editor_bindings.select(-1)
    elseif action == "cavebot_next" and type(Helper.cavebot_editor_bindings.select) == "function" then
        return Helper.cavebot_editor_bindings.select(1)
    elseif action == "cavebot_delete" and deleteCurrentCavebotWaypoint then
        return deleteCurrentCavebotWaypoint(command.confirm == true)
    elseif action == "cavebot_move_up" and type(Helper.cavebot_editor_bindings.move) == "function" then
        return Helper.cavebot_editor_bindings.move(-1)
    elseif action == "cavebot_move_down" and type(Helper.cavebot_editor_bindings.move) == "function" then
        return Helper.cavebot_editor_bindings.move(1)
    elseif action == "magic_probe" and Helper.runMagicApiProbe then
        return Helper.runMagicApiProbe()
    elseif action == "api_probe" and Helper.runApiProbe then
        return Helper.runApiProbe("manual")
    elseif action == "recovery_bridge_dry_run" and Helper.recoveryBridgeDryRun then
        return Helper.recoveryBridgeDryRun()
    elseif action == "recovery_bridge_arm" and Helper.recoveryBridgeArm then
        return Helper.recoveryBridgeArm()
    elseif action == "recovery_bridge_execute_once" and Helper.recoveryBridgeExecuteOnce then
        if command.confirm ~= true then status("Recovery bridge execute-once blocked: confirm required"); return false end
        return Helper.recoveryBridgeExecuteOnce()
    elseif action == "recovery_bridge_kill" and Helper.recoveryBridgeKill then
        return Helper.recoveryBridgeKill()
    elseif action == "p12_conditions_execute_once" and Helper.conditionsExecuteOnce then
        if command.confirm ~= true then status("P12 Conditions blocked: confirm required"); return false end
        return Helper.conditionsExecuteOnce(command)
    elseif action == "p12_equipment_execute_once" and Helper.equipmentExecuteOnce then
        if command.confirm ~= true then status("P12 Equipment blocked: confirm required"); return false end
        return Helper.equipmentExecuteOnce(command)
    elseif action == "p12_heal_friend_execute_once" and Helper.healFriendExecuteOnce then
        if command.confirm ~= true then status("P12 Heal Friend blocked: confirm required"); return false end
        return Helper.healFriendExecuteOnce(command)
    elseif action == "timer_probe" then
        local plan = moduleValue(externalTimerRuntime, "plan", HELPER_CONFIG.tools or {}, {
            online = g_game and g_game.isOnline and g_game.isOnline() or false,
            in_protection_zone = false,
            now_ms = g_clock and g_clock.millis and g_clock.millis() or 0
        })
        local probeText = moduleValue(externalTimerRuntime, "probeSummary", plan)
        status(type(probeText) == "string" and probeText ~= "" and probeText or "Timer runtime adapter unavailable")
        return true
    elseif action == "diag_export" and Helper.exportDiagnostics then
        return Helper.exportDiagnostics()
    end
    return true
end

local function processSmokeCommand()
    local path = moduleValue(externalDiagnostics, "smokeCommandPath", Helper.ui_path, g_resources)
    if type(path) ~= "string" or path == "" then
        return false
    end
    if not moduleValue(externalDiagnostics, "smokeCommandExists", path, g_resources, io) then
        return false
    end
    local command = moduleValue(externalDiagnostics, "readSmokeCommand", path, io)
    moduleValue(externalDiagnostics, "removeSmokeCommand", path, os)
    if type(command) ~= "table" then
        local failedText = moduleValue(externalDiagnostics, "smokeCommandStatusText", "failed", {value = command})
        status(type(failedText) == "string" and failedText ~= "" and failedText or "smoke failed")
        return false
    end
    return applySmokeCommand(command)
end

flushUiPrefsSave = function()
    if type(externalProfileSchema) ~= "table" or type(externalProfilePersistence) ~= "table" then
        status("UI prefs save blocked: required profile owner unavailable")
        return false
    end
    if Helper.ui_save_event then
        removeEvent(Helper.ui_save_event)
        Helper.ui_save_event = nil
    end
    local defaults = moduleValue(externalProfilePersistence, "profilePersistenceTable", "saveDefaults", {}, "ui_prefs")
    local path = moduleValue(externalProfilePersistence, "profilePersistenceValue", "resolveSavePath", Helper.ui_path or "ctoa_ui_prefs.lua", "ui_prefs", Helper.ui_path, g_resources and g_resources.getWorkDir and g_resources.getWorkDir() or "")
    defaults = type(defaults) == "table" and defaults or {}
    if type(path) ~= "string" or path == "" then status("UI prefs save blocked: save path unavailable"); return false end
    local exportedPrefs = moduleValue(externalProfilePersistence, "exportUiPrefs", HELPER_CONFIG, Helper)
    local serializedPrefs = moduleValue(externalProfileSchema, "serializeLua", exportedPrefs, "ui_prefs")
    if type(serializedPrefs) ~= "string" then status("UI prefs save blocked: serialization unavailable"); return false end
    local uiPrefsSaveText = moduleValue(externalProfilePersistence, "profilePersistenceValue", "saveText", "return " .. serializedPrefs .. "\n", "ui_prefs", serializedPrefs)
    if type(uiPrefsSaveText) ~= "string" then status("UI prefs save blocked: save text unavailable"); return false end
    local file = io.open(path, "w")
    if not file and path ~= "ctoa_ui_prefs.lua" then
        local fallbackPath = moduleValue(externalProfilePersistence, "profilePersistenceValue", "fallbackSavePath", "ctoa_ui_prefs.lua", "ui_prefs", path)
        file = io.open(fallbackPath, "w")
        if file then
            path = fallbackPath
        end
    end
    if not file then
        status(tostring(defaults.save_failed_status or "UI prefs save failed"))
        return false
    end

    file:write(uiPrefsSaveText)
    file:close()
    Helper.ui_dirty = false
    if Helper.widgets.ui_status and Helper.widgets.ui_status.setText then
        Helper.widgets.ui_status:setText(tostring(defaults.clean_status or "Autosave: saved"))
    end
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
    status(tostring(defaults.saved_status or "UI prefs saved"))
    return true
end

local function markProfileDirty(reason)
    Helper.profile_dirty = true
    local dirtyState = moduleValue(externalProfilePersistence, "profilePersistenceTable", "dirtyState", {dirty_status = "Autosave: pending", delay_ms = 450}, "profile", reason)
    if Helper.widgets.profile_status and Helper.widgets.profile_status.setText then
        Helper.widgets.profile_status:setText(tostring(dirtyState.dirty_status or "Autosave: pending"))
    end
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
    if Helper.status_label and Helper.status_label.setText then
        Helper.status_label:setText("Status: Profile dirty")
    end
    if Helper.profile_save_event then
        removeEvent(Helper.profile_save_event)
    end
    Helper.profile_save_event = delay(function()
        Helper.profile_save_event = nil
        flushProfileSave()
    end, tonumber(dirtyState.delay_ms) or 450)
    if type(dirtyState.log_text) == "string" and dirtyState.log_text ~= "" then
        appendLog(dirtyState.log_text)
    end
end

markUiPrefsDirty = function(reason)
    Helper.ui_dirty = true
    local dirtyState = moduleValue(externalProfilePersistence, "profilePersistenceTable", "dirtyState", {dirty_status = "Autosave: pending", delay_ms = 450}, "ui_prefs", reason)
    if Helper.widgets.ui_status and Helper.widgets.ui_status.setText then
        Helper.widgets.ui_status:setText(tostring(dirtyState.dirty_status or "Autosave: pending"))
    end
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
    if Helper.ui_save_event then
        removeEvent(Helper.ui_save_event)
    end
    Helper.ui_save_event = delay(function()
        Helper.ui_save_event = nil
        flushUiPrefsSave()
    end, tonumber(dirtyState.delay_ms) or 450)
    if reason then
        appendLog("UI prefs changed: " .. reason)
    end
end

local function setLastPotionStatus(text)
    if Helper.widgets.last_potion and Helper.widgets.last_potion.setText then
        Helper.widgets.last_potion:setText(text)
    end
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
end

local function setHudText(text)
    if Helper.hud_label and Helper.hud_label.setText then
        Helper.hud_label:setText(text)
    end
end

local function throttledRuntimeStatus(reason, now)
    local tools = HELPER_CONFIG.tools or {}
    local interval = tools.block_log_ms or 3000
    if Helper.last_runtime_block_reason == reason and Helper.last_runtime_block_ms and now - Helper.last_runtime_block_ms < interval then
        return
    end
    Helper.last_runtime_block_reason = reason
    Helper.last_runtime_block_ms = now
    status(reason)
end

local setWidgetText = externalUi and externalUi.setWidgetText; local setWidgetChecked = externalUi and externalUi.setWidgetChecked

local function defer(callback)
    if addEvent then
        addEvent(callback)
    else
        callback()
    end
end

delay = function(callback, ms)
    if scheduleEvent then
        return scheduleEvent(callback, ms)
    end
    if addEvent then
        return addEvent(callback)
    end
    callback()
    return nil
end

local getWidgetChecked = externalUi and externalUi.getWidgetChecked
local showWidget = externalUi and externalUi.showWidget

function addToSection(section, widget)
    if not widget then
        return widget
    end
    if not section then
        return widget
    end
    Helper.sections[section] = Helper.sections[section] or {}
    table.insert(Helper.sections[section], widget)
    return widget
end

local function setSectionVisible(section, visible)
    local widgets = Helper.sections[section] or {}
    for _, widget in ipairs(widgets) do
        showWidget(widget, visible)
    end
end

function createWidget(kind, parent, id, text, x, y, width, height)
    local widget = moduleValue(externalUi, "createWidget", kind, parent, id, text, x, y, width, height)
    if widget ~= nil then
        return widget
    end
    return nil
end

local function sendHotkey(hotkey)
    if not hotkey or hotkey == "" then
        return false
    end
    if modules and modules.game_interface and modules.game_interface.sendHotkey then
        modules.game_interface.sendHotkey(hotkey)
        return true
    end
    if g_keyboard and g_keyboard.pressKey then
        g_keyboard.pressKey(hotkey)
        return true
    end
    return false
end

local function sendActionbarSlot(primarySlot, fallbackHotkey)
    local slot = moduleValue(externalHotkeys, "resolveActionbarSlot", primarySlot, fallbackHotkey)
    if not slot then
        return false, nil
    end
    return sendHotkey(slot), slot
end

local function castSpell(spell)
    if spell and spell ~= "" then
        g_game.talk(spell)
        return true
    end
    return false
end

local function getAttackTarget()
    if g_game and g_game.getAttackingCreature then
        local ok, creature = pcall(function()
            return g_game.getAttackingCreature()
        end)
        if ok then
            return creature
        end
    end
    return nil
end

local function normalizedCreatureName(creature)
    local name = moduleValue(externalTargeting, "normalizedName", creature)
    return type(name) == "string" and name or ""
end

local function isIgnoredCreatureName(creature)
    local name = normalizedCreatureName(creature)
    if name == "" then
        return false
    end
    return moduleValue(externalTargeting, "isIgnoredName", name, HELPER_CONFIG.tools.ignored_names or {}) == true
end

local pcallOptionalBool

local function creatureHasFriendlySummonFlag(creature, localPlayer)
    if not creature then
        return false
    end
    for _, methodName in ipairs({"isSummon", "isFamiliar", "isPet", "isPlayerSummon", "isLocalSummon"}) do
        if pcallOptionalBool(creature, methodName) == true then
            return true
        end
    end
    for _, methodName in ipairs({"getOwner", "getMaster", "getSummoner"}) do
        if creature[methodName] then
            local ok, owner = pcall(function()
                return creature[methodName](creature)
            end)
            if ok and owner and (owner == localPlayer or pcallOptionalBool(owner, "isLocalPlayer") == true) then
                return true
            end
        end
    end
    return false
end

local function isFriendlySummonCreature(creature, localPlayer)
    if HELPER_CONFIG.tools.block_friendly_summons == false then
        return false
    end
    if creatureHasFriendlySummonFlag(creature, localPlayer) then
        return true
    end
    return moduleValue(externalTargeting, "isFriendlySummonName", normalizedCreatureName(creature), HELPER_CONFIG.tools) == true
end

pcallOptionalBool = function(obj, methodName)
    if obj and obj[methodName] then
        local ok, result = pcall(function()
            return obj[methodName](obj)
        end)
        if ok then
            return result == true
        end
        return false
    end
    return nil
end

local function isLocalPlayerInProtectionZone()
    local player = g_game and g_game.getLocalPlayer and g_game.getLocalPlayer()
    if not player then
        return false
    end

    local policy = moduleValue(externalRuntimePolicy, "resolvedProtectionZonePolicy")
    if type(policy) ~= "table" then
        return true
    end
    local observation = {
        player_method_hit = anyPcallBool(player, policy.player_methods),
        player_state_hit = hasAnyState(player, "hasState", policy.player_state_values or {}),
        player_states = pcallNumber(player, "getStates"),
        state_flag_values = policy.state_flag_values or {},
        state_flag_fallbacks = policy.state_flag_fallbacks or {}
    }
    local pos = getThingPosition(player)
    if pos and g_map and g_map.getTile then
        local ok, tile = pcall(function()
            return g_map.getTile(pos)
        end)
        if ok and tile then
            observation.tile_method_hit = anyPcallBool(tile, policy.tile_methods)
            observation.tile_flags = pcallNumber(tile, "getFlags")
            observation.tile_flag_values = policy.tile_flag_values or {}
            observation.tile_flag_fallbacks = policy.tile_flag_fallbacks or {}
            observation.tile_has_flag_hit = hasAnyState(tile, "hasFlag", policy.tile_has_flag_values or {})
        end
    end
    local decision = moduleValue(externalRuntimePolicy, "protectionZoneDecision", observation)
    if decision ~= nil then
        return decision == true
    end
    return true
end

local function isMonsterCreature(creature, localPlayer)
    local decision = externalTargeting and externalTargeting.creatureTypeDecision
    if type(decision) ~= "function" then
        return false
    end
    local npcIcon = nil
    if creature and creature.getIcon then
        local iconOk, icon = pcall(creature.getIcon, creature)
        if iconOk then
            npcIcon = icon
        end
    end
    local ok, result = pcall(decision, {
        missing = not creature,
        is_local_player = creature == localPlayer,
        ignored_name = creature and isIgnoredCreatureName(creature) or false,
        blocking_npc_icon = creature and moduleValue(externalTargeting, "creatureHasBlockingNpcIcon", npcIcon, HELPER_CONFIG.tools) or false,
        friendly_summon = creature and isFriendlySummonCreature(creature, localPlayer) or false,
        is_npc = pcallOptionalBool(creature, "isNpc"),
        is_player = pcallOptionalBool(creature, "isPlayer"),
        attackable = pcallOptionalBool(creature, "isAttackable"),
        can_be_attacked = pcallOptionalBool(creature, "canBeAttacked"),
        targetable = pcallOptionalBool(creature, "isTargetable"),
        is_monster = pcallOptionalBool(creature, "isMonster")
    })
    return ok and result == true
end

local function getSpectatorsInRange(pos, range)
    if not pos then
        return {}
    end
    if g_map and g_map.getSpectatorsInRange then
        local ok, spectators = pcall(function()
            return g_map.getSpectatorsInRange(pos, false, range, range)
        end)
        if ok and spectators then
            return spectators
        end
    end
    if g_map and g_map.getSpectators then
        local ok, spectators = pcall(function()
            return g_map.getSpectators(pos, false)
        end)
        if ok and spectators then
            return spectators
        end
    end
    return {}
end

local function scanCombatArea(tools)
    local localPlayer = getLocalPlayer()
    local playerPos = getThingPosition(localPlayer)
    local attackRange = tools.attack_range or 7
    local scanRange = math.max(attackRange, 7)
    local scan = {
        adjacent = 0,
        close = 0,
        target_range = 0,
        visible = 0,
        by_range = {},
        directional_hits = {[0] = 0, [1] = 0, [2] = 0, [3] = 0},
        facing_direction = nil
    }
    if not localPlayer or not playerPos then
        return scan
    end
    if localPlayer.getDirection then local ok, value = pcall(function() return localPlayer:getDirection() end); if ok then scan.facing_direction = tonumber(value) end end
    for _, creature in ipairs(getSpectatorsInRange(playerPos, scanRange)) do
        if isMonsterCreature(creature, localPlayer) then
            local distance = moduleValue(externalRoute, "distanceChebyshev", playerPos, getThingPosition(creature))
            if distance then
                local creaturePos = getThingPosition(creature)
                if distance <= 1 then
                    scan.adjacent = scan.adjacent + 1
                    moduleValue(externalCombatRuntime, "recordDirectionalHit", scan, creaturePos and creaturePos.x - playerPos.x or 0, creaturePos and creaturePos.y - playerPos.y or 0)
                end
                if distance <= 2 then
                    scan.close = scan.close + 1
                end
                if distance <= attackRange then
                    scan.target_range = scan.target_range + 1
                end
                if distance <= 7 then
                    scan.visible = scan.visible + 1
                end
                for range = distance, scanRange do
                    scan.by_range[range] = (scan.by_range[range] or 0) + 1
                end
            end
        end
    end
    return scan
end
local function targetReachable(target, playerPos, maxRange)
    local targetPos = getThingPosition(target)
    local distance = moduleValue(externalRoute, "distanceChebyshev", playerPos, targetPos)
    if not targetPos or not distance then return false end
    if distance <= 1 then return true end
    if HELPER_CONFIG.tools.require_reachable_target ~= true then return true end
    if not g_map or not g_map.findPath then return true end
    local ok, directions = pcall(function()
        return g_map.findPath(playerPos, targetPos, tonumber(maxRange) or 20, 0)
    end)
    return ok and type(directions) == "table" and #directions > 0
end

local function isTargetInRange(target, maxRange)
    local localPlayer = getLocalPlayer()
    if not localPlayer or not isMonsterCreature(target, localPlayer) then
        return false
    end
    local distance = moduleValue(externalRoute, "distanceChebyshev", getThingPosition(localPlayer), getThingPosition(target))
    return distance ~= nil and distance <= maxRange and targetReachable(target, getThingPosition(localPlayer), maxRange)
end

local function getSafeAttackTarget(maxRange)
    local target = getAttackTarget()
    if not isTargetInRange(target, maxRange or HELPER_CONFIG.tools.attack_range or 7) then
        return nil
    end
    return target
end

local function isPlayerCreature(creature, localPlayer)
    if not creature or creature == localPlayer then
        return false
    end
    if creature.isPlayer then
        local ok, result = pcall(function()
            return creature:isPlayer()
        end)
        if ok then
            return result == true
        end
    end
    return false
end

local function isPartyMemberCreature(creature)
    return pcallOptionalBool(creature, "isPartyMember") == true
end

local function canShootCreature(creature)
    return pcallOptionalBool(creature, "canShoot") == true
end

local function maybeObserveHealFriend(now)
    local healFriend = HELPER_CONFIG.heal_friend or {}
    local observed = moduleValue(externalHealFriend, "observe", healFriend, now, {
        getLocalPlayer = getLocalPlayer,
        getThingPosition = getThingPosition,
        getSpectatorsInRange = getSpectatorsInRange,
        isPlayerCreature = isPlayerCreature,
        distanceChebyshev = type(externalRoute) == "table" and type(externalRoute.distanceChebyshev) == "function" and externalRoute.distanceChebyshev or nil,
        normalizedCreatureName = normalizedCreatureName,
        getCreatureHealthPercent = getCreatureHealthPercent,
        getCreatureId = currentTargetId,
        isPartyMemberCreature = isPartyMemberCreature,
        canShootCreature = canShootCreature,
        shortText = shortText
    })
    if observed == true then
        if Helper.widgets.heal_friend_status and Helper.widgets.heal_friend_status.setText then
            Helper.widgets.heal_friend_status:setText(fitText("Status: " .. tostring(healFriend.last_status), UI_LAYOUT.content_w - 14, 0.88))
        end
        return true
    elseif observed == false then
        return false
    end
    if healFriend.enabled == true and healFriend.observe_party == true then
        healFriend.last_status = "heal friend module unavailable"
        local text = moduleValue(externalHealFriend, "statusText", healFriend)
        healFriend.last_status = type(text) == "string" and text ~= "" and text or healFriend.last_status
        if Helper.widgets.heal_friend_status and Helper.widgets.heal_friend_status.setText then
            Helper.widgets.heal_friend_status:setText(fitText("Status: " .. tostring(healFriend.last_status), UI_LAYOUT.content_w - 14, 0.88))
        end
    end
    return false
end

local function buildTargetCandidate(creature, playerPos)
    local creaturePos = getThingPosition(creature)
    local localPlayer = getLocalPlayer()
    return {
        ref = creature,
        name = normalizedCreatureName(creature),
        distance = moduleValue(externalRoute, "distanceChebyshev", playerPos, creaturePos) or 99,
        hp = getCreatureHealthPercent(creature),
        reachable = targetReachable(creature, playerPos, HELPER_CONFIG.tools.attack_range or 7),
        is_summon = pcallOptionalBool(creature, "isSummon") == true,
        is_familiar = pcallOptionalBool(creature, "isFamiliar") == true,
        is_friendly_summon = isFriendlySummonCreature(creature, localPlayer)
    }
end

local function findBestAttackTarget(tools)
    local localPlayer = getLocalPlayer()
    local playerPos = getThingPosition(localPlayer)
    local maxRange = tools.attack_range or 7
    if not localPlayer or not playerPos then
        return nil
    end

    local candidates = {}
    for _, creature in ipairs(getSpectatorsInRange(playerPos, maxRange)) do
        if isMonsterCreature(creature, localPlayer) then
            local distance = moduleValue(externalRoute, "distanceChebyshev", playerPos, getThingPosition(creature))
            if distance and distance <= maxRange then
                candidates[#candidates + 1] = buildTargetCandidate(creature, playerPos)
            end
        end
    end

    for _, candidate in ipairs(candidates) do candidate.monster_count = #candidates end

    local best, decision = moduleValue(externalTargeting, "bestCandidate", candidates, tools)
    if type(best) == "table" and best.ref then
        return best.ref, decision
    end
    return nil
end

local combatBlockedReason
local clearUnsafeCurrentTarget
local combatRuntimeText

local function applyChaseMode(enabled)
    if not g_game or not g_game.setChaseMode then
        return false
    end
    local chaseMode = enabled and 1 or 0
    local ok = pcall(function()
        g_game.setChaseMode(chaseMode)
    end)
    return ok
end

local function retargetSafeMonster(now, tools)
    if not tools.auto_attack then
        return nil
    end
    if now - Helper.last_retarget_ms < (tools.retarget_delay_ms or 200) then
        return nil
    end
    local blocked = combatBlockedReason(tools)
    if blocked then
        clearUnsafeCurrentTarget(blocked, now, true)
        throttledRuntimeStatus(combatRuntimeText("targetingStatusText", "blocked", {reason = blocked}), now)
        return nil
    end

    local target, targetDecision = findBestAttackTarget(tools)
    if not target then
        clearUnsafeCurrentTarget("no valid monster target", now)
        throttledRuntimeStatus(combatRuntimeText("targetingStatusText", "no_valid_target"), now)
        Helper.last_retarget_ms = now
        return nil
    end
    if isFriendlySummonCreature(target, getLocalPlayer()) then
        clearUnsafeCurrentTarget("friendly summon/familiar target", now, true)
        throttledRuntimeStatus(combatRuntimeText("targetingStatusText", "friendly_summon"), now)
        Helper.last_retarget_ms = now
        return nil
    end

    local chase = tools.chase == true
    if type(targetDecision) == "table" and targetDecision.chase_policy == "follow" then chase = true end
    if type(targetDecision) == "table" and targetDecision.chase_policy == "stand" then chase = false end
    applyChaseMode(chase)
    local targetId = currentTargetId(target)
    local current = getCurrentAttackTarget()
    local currentId = currentTargetId(current)
    if targetId ~= nil and currentId == targetId then
        Helper.current_target_id = targetId
        Helper.last_retarget_ms = now
        return target
    end
    if g_game and g_game.attack then
        pcall(function() g_game.attack(target) end)
    end
    Helper.current_target_id = targetId
    Helper.target_start_ms = now
    Helper.last_retarget_ms = now

    if now - Helper.last_target_log_ms >= (tools.log_retarget_ms or 3000) then
        local targetName = target.getName and target:getName() or "monster"
        Helper.last_target_log_ms = now
        status(combatRuntimeText("targetingStatusText", "auto_target", {name = targetName}))
    end
    return target
end

combatBlockedReason = function(tools)
    if tools.pause_in_pz ~= false and isLocalPlayerInProtectionZone() then
        return "PZ safe"
    end
    return nil
end

clearUnsafeCurrentTarget = function(reason, now, forceClear)
    local target = getAttackTarget()
    if not target then
        return false
    end
    local localPlayer = getLocalPlayer()
    if not forceClear and localPlayer and isMonsterCreature(target, localPlayer) and isTargetInRange(target, HELPER_CONFIG.tools.attack_range or 7) then
        return false
    end
    if g_game then
        if g_game.cancelAttack then
            pcall(function() g_game.cancelAttack() end)
        end
        if g_game.stopAttack then
            pcall(function() g_game.stopAttack() end)
        end
        if g_game.attack then
            pcall(function() g_game.attack(nil) end)
        end
    end
    throttledRuntimeStatus(combatRuntimeText("targetingStatusText", "target_cleared", {reason = reason}), now)
    return true
end

local function runtimeBlockedReason(now)
    if not HELPER_CONFIG.enabled then
        return "Runtime disarmed"
    end
    local armBlocked = runtimeArmingBlockedReason()
    if armBlocked then
        HELPER_CONFIG.enabled = false
        return armBlocked
    end
    if not g_game or not g_game.isOnline or not g_game.isOnline() then
        return "Offline"
    end
    local tools = HELPER_CONFIG.tools or {}
    local blocked = combatBlockedReason(tools)
    if blocked then
        clearUnsafeCurrentTarget(blocked, now, true)
        return blocked
    end
    clearUnsafeCurrentTarget("non-monster target", now)
    return nil
end

local function updateCombatStats(target, nearby, visible)
    if Helper.widgets.monster_stats and Helper.widgets.monster_stats.setText then
        local targetName = target and target.getName and target:getName() or "none"
        Helper.widgets.monster_stats:setText("Target: " .. targetName .. " | nearby " .. nearby .. " / visible " .. visible)
    end
end

local MODULE_SHORT_LABELS = moduleValue(externalModules, "getShortLabels") or {}

local function decisionPipelineIsStale(now)
    local observedAt = tonumber(Helper.decision_pipeline_updated_at_ms)
    return type(Helper.decision_pipeline_result) == "table" and observedAt ~= nil and tonumber(now) ~= nil and now - observedAt > 5000
end

local function currentOperatorRuntimeState(now, blockedReason)
    return moduleValue(externalUi, "operatorRuntimeState", {
        enabled = HELPER_CONFIG.enabled == true,
        blocked_reason = blockedReason,
        stale = decisionPipelineIsStale(now),
    }) or "disabled"
end

local function updateOverviewStats(target, nearby, visible, hp, mp, nextAction, now)
    local targetName = target and target.getName and target:getName() or "none"
    local moduleSummaryText = moduleValue(externalModules, "registrySummary", MODULE_LANES, HELPER_CONFIG)
    if type(moduleSummaryText) ~= "string" or moduleSummaryText == "" then
        moduleSummaryText = "modules unavailable"
    end
    local runtimeReadinessText = moduleValue(externalModules, "readinessRow", "implemented", MODULE_LANES, HELPER_CONFIG, MODULE_SHORT_LABELS)
    if type(runtimeReadinessText) ~= "string" or runtimeReadinessText == "" then
        runtimeReadinessText = "implemented: modules unavailable"
    end
    local prototypeReadinessText = moduleValue(externalModules, "readinessRow", "prototype", MODULE_LANES, HELPER_CONFIG, MODULE_SHORT_LABELS)
    if type(prototypeReadinessText) ~= "string" or prototypeReadinessText == "" then
        prototypeReadinessText = "prototype: modules unavailable"
    end
    local loaderState = rawget(_G, "CTOA_OTCLIENT") or {}
    local bootSnapshot = moduleValue(externalModules, "bootSnapshot", loaderState.modules or {})
    local bootStatusText = moduleValue(externalModules, "bootSummary", bootSnapshot or {}) or "Boot status unavailable"
    local pipelineResult = Helper.decision_pipeline_result or {}
    local pipelineStatusText = moduleValue(externalDecisionPipeline, "summary", pipelineResult) or "Decision pipeline idle"
    local pipelineState = moduleValue(externalUi, "normalizeOperatorState", pipelineResult.status or "disabled") or "disabled"
    if decisionPipelineIsStale(now) then
        pipelineState = "stale"
        pipelineStatusText = "STALE | " .. pipelineStatusText
    end
    local bootState = moduleValue(externalUi, "normalizeOperatorState", bootSnapshot and bootSnapshot.status or "blocked") or "blocked"
    local runtimeState = currentOperatorRuntimeState(now, nil)
    local updater = externalUi and externalUi.updateOverviewStats
    if type(updater) ~= "function" then
        return false
    end
    local ok = pcall(updater, {
        widgets = Helper.widgets,
        content_width = UI_LAYOUT.content_w,
        set_metric_text = externalUi and externalUi.setMetricText,
        ui_style = UI_STYLE,
        align_left = AlignLeft,
        align_center = AlignCenter
    }, {
        profile_name = moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText),
        hp = hp,
        mp = mp,
        target_name = targetName,
        module_summary = moduleSummaryText,
        tools = HELPER_CONFIG.tools,
        nearby = nearby,
        visible = visible,
        next_action = nextAction,
        runtime_readiness = runtimeReadinessText,
        prototype_readiness = prototypeReadinessText,
        boot_status = bootStatusText,
        boot_state = bootState,
        pipeline_status = pipelineStatusText,
        pipeline_state = pipelineState,
        runtime_state = runtimeState
    })
    return ok == true
end

local function rotationWaitReason(tools, target, scan, now)
    local nearby = scan and scan.adjacent or 0
    local visible = scan and scan.visible or 0
    local spells = moduleValue(externalCombatRuntime, "rotationSpellRows", tools.rotation_spells or {}, {scan = scan, rotation_scan_range = tools.rotation_scan_range, last_spell_casts = tools.last_spell_casts}) or {}
    local rows = moduleValue(externalCombatRuntime, "spellReadiness", spells, {now_ms = now, default_cooldown_ms = tools.rotation_interval_ms or 1050})
    if type(rows) == "table" then spells = rows end
    local gapPlan = moduleValue(externalRecoveryRuntime, "recoveryActionGap", now, HELPER_CONFIG.healing, HELPER_CONFIG.tools)
    local text = moduleValue(externalCombatRuntime, "waitReason", {
            blocked_reason = combatBlockedReason(tools),
            recovery_gap_until_ms = gapPlan.active and gapPlan.until_ms or nil,
            auto_attack = tools.auto_attack,
            target_present = target ~= nil,
            action_lock_until_ms = tools.attack_action_lock_until_ms,
            spell_rotation = tools.spell_rotation,
            rune_enabled = tools.rune_enabled,
            rotation_interval_wait = now - (tools.last_attack_spell_ms or 0) < (tools.rotation_interval_ms or 1050),
            spells = spells,
            nearby = nearby,
            visible = visible,
            now_ms = now
    })
    if type(text) == "string" and text ~= "" then return text end
    return "Wait: mobs " .. tostring(nearby or 0) .. "/" .. tostring(visible or 0) .. " below spell rules"
end

local function canUseRuneOnTarget(tools, target)
    if not tools.rune_pvp_safe then
        return true
    end
    return isTargetInRange(target, tools.attack_range or 7)
end

local function lockOffensiveAction(tools, now)
    local lockMs = tools.attack_action_lock_ms or tools.rotation_interval_ms or 1050
    tools.attack_action_lock_until_ms = now + lockMs
    tools.last_attack_spell_ms = now
end

local function buildOffensiveAction(tools, target, scan, now)
    local visible = scan and scan.visible or 0
    local nearby = scan and scan.adjacent or 0
    local rotationSpell = nil
    if tools.spell_rotation and target then
        rotationSpell = moduleValue(externalCombatRuntime, "selectRotationSpell", tools, scan, now)
    end
    local spellStateEvidence = moduleValue(externalSpellStateRegistry, "observeAll", getLocalPlayer(), tools.spell_state_families, now, {
        read_states = function(player) return pcallNumber(player, "getStates") end
    })
    local spellStateDecisions = moduleValue(externalSpellStateRegistry, "decisionMap", tools.spell_state_families, spellStateEvidence, now, tools.last_spell_state_casts)
    local action = moduleValue(externalCombatRuntime, "offensiveAction", tools, {
            blocked_reason = combatBlockedReason(tools),
            target_present = target ~= nil,
            target_in_range = target and isTargetInRange(target, tools.attack_range or 7) or nil,
            visible = visible,
            nearby = nearby,
            now_ms = now,
            recovery_gap_active = moduleValue(externalRecoveryRuntime, "recoveryActionGap", now, HELPER_CONFIG.healing, HELPER_CONFIG.tools).active,
            rotation_spell = rotationSpell,
            rune_target_safe = canUseRuneOnTarget(tools, target),
            spell_state_decisions = spellStateDecisions
    })
    if type(action) == "table" then return action end
    return nil
end

combatRuntimeText = function(functionName, eventOrAction, data, fallback)
    local text = moduleValue(externalCombatRuntime, functionName, eventOrAction, data or {})
    return type(text) == "string" and text ~= "" and text or fallback or tostring(eventOrAction or "targeting")
end
local function executeOffensiveAction(tools, action, nearby, visible, now)
    if not action then return false end
    local blocked = combatBlockedReason(tools)
    if blocked then status(combatRuntimeText("actionStatusText", {kind = "blocked", reason = blocked}, {reason = blocked}, "Combat action status unavailable")); return false end
    if now < (tools.attack_action_lock_until_ms or 0) then status(combatRuntimeText("actionStatusText", {kind = "action_lock"}, {now_ms = now}, "Combat action status unavailable")); return false end
    if moduleValue(externalRecoveryRuntime, "recoveryActionGap", now, HELPER_CONFIG.healing, HELPER_CONFIG.tools).active then status(combatRuntimeText("actionStatusText", {kind = "recovery_gap"}, {now_ms = now}, "Combat action status unavailable")); return false end
    local descriptor = moduleValue(externalCombatRuntime, "dispatchDescriptor", action, tools)
    if type(descriptor) ~= "table" or descriptor.kind == "none" then return false end
    if descriptor.fight_mode and g_game and g_game.setFightMode then
        local mode = descriptor.fight_mode == "offensive" and (rawget(_G, "FightOffensive") or 1) or (rawget(_G, "FightDefensive") or 3)
        pcall(function() g_game.setFightMode(mode) end)
    end
    if descriptor.turn_direction ~= nil then
        local player = getLocalPlayer()
        local currentDirection = player and player.getDirection and player:getDirection() or nil
        local desiredDirection = tonumber(descriptor.turn_direction)
        if desiredDirection ~= nil and currentDirection ~= desiredDirection then
            if not g_game or type(g_game.turn) ~= "function" then status("Rotation blocked: turn API unavailable for " .. tostring(descriptor.words)); return false end
            local turned = pcall(function() g_game.turn(desiredDirection) end)
            if not turned then status("Rotation blocked: could not face " .. tostring(descriptor.words)); return false end
        end
    end
    local sent, slot = false, nil
    if descriptor.kind == "spell" and descriptor.words ~= "" then sent = castSpell(descriptor.words) end
    if descriptor.kind == "actionbar" then sent, slot = sendActionbarSlot(descriptor.slot, descriptor.hotkey) end
    if not sent then return false end
    moduleValue(externalCombatRuntime, "recordActionSuccess", tools, action, now)
    lockOffensiveAction(tools, now)
    local detail = {nearby = nearby, visible = visible, rune_name = action.rune_name or tools.rune_name or "rune", slot_text = moduleValue(externalHotkeys, "actionbarSlotText", slot) or "actionbar ?"}
    status(combatRuntimeText("actionStatusText", action, detail, "Combat action status unavailable"))
    return true
end
local function planNextCombatAction(target, scan, now)
    local tools = HELPER_CONFIG.tools
    local action = buildOffensiveAction(tools, target, scan, now)
    local fallback = rotationWaitReason(tools, target, scan, now)
    local text = moduleValue(externalCombatRuntime, "nextActionText", action, fallback)
    return type(text) == "string" and text ~= "" and text or fallback
end

local function combatDecisionStateText(tools, target, scan, now, nextAction)
    local visible = scan and scan.visible or 0
    local text = moduleValue(externalCombatRuntime, "decisionStateSummary", tools, {
        online = g_game and g_game.isOnline and g_game.isOnline() or false,
        in_protection_zone = isLocalPlayerInProtectionZone(),
        next_action = nextAction,
        target_present = target ~= nil,
        action_lock_until_ms = tools.attack_action_lock_until_ms or 0,
        auto_exeta = tools.auto_exeta,
        exeta_until_ms = (tools.last_exeta_ms or 0) + (tools.exeta_interval_ms or 5000),
        rune_enabled = tools.rune_enabled,
        rune_ready = moduleValue(externalCombatRuntime, "runeReady", tools, {target_present = target ~= nil, visible = visible or 0, now_ms = now}) == true,
        rune_until_ms = (tools.last_rune_ms or 0) + (tools.rune_cooldown_ms or 1000),
        now_ms = now
    }, {eligible = target ~= nil, reason = target and "selected" or "no_target", name = target and "monster" or "none", score = 0})
    if type(text) == "string" and text ~= "" then return fitText(text, UI_LAYOUT.content_w - 14, 0.78) end
    return tostring(nextAction or "idle") .. " | target=" .. (target and "monster" or "none")
end

local function readPlayerVitals()
    local player = getLocalPlayer()
    local vitals = moduleValue(externalRecoveryRuntime, "readVitals", player)
    if type(vitals) ~= "table" then
        vitals = moduleValue(externalRecoveryRuntime, "normalizeVitals", {})
    end
    if type(vitals) ~= "table" then
        vitals = {source = "none"}
    end
    Helper.last_vitals = vitals
    return vitals
end

local function maybeHeal(now, vitals)
    local healing = HELPER_CONFIG.healing
    if now - healing.last_cast_ms < healing.cooldown_ms then
        return false
    end

    vitals = vitals or readPlayerVitals()
    local hp = vitals.hp_percent
    if not hp then
        return false
    end

    local jitter = healing.threshold_jitter_percent or 3
    local nonce = math.floor(now / math.max(500, healing.cooldown_ms or 1000))
    local potionThreshold = moduleValue(externalRecoveryRuntime, "jitterThreshold", healing.potion_threshold, jitter, nonce + 31) or healing.potion_threshold
    local spellThreshold = moduleValue(externalRecoveryRuntime, "jitterThreshold", healing.spell_threshold, jitter, nonce + 53) or healing.spell_threshold

    if healing.potion_enabled and hp <= potionThreshold then
        local sent, slot = sendActionbarSlot(healing.potion_actionbar_slot, healing.potion_hotkey)
        if sent then
            healing.last_cast_ms = now
            healing.last_recovery_action_ms = now
            local slotText = moduleValue(externalHotkeys, "actionbarSlotText", slot) or "actionbar ?"
            local potionText = moduleValue(externalRecoveryRuntime, "potionStatusText", "Potion heal", nil, slotText, hp)
            if type(potionText) ~= "string" or potionText == "" then
                potionText = "Potion heal via " .. slotText .. " at " .. hp .. "%"
            end
            setLastPotionStatus("Last potion: " .. potionText:gsub("^Potion heal ", ""))
            status(potionText)
            return true
        end
    end

    if healing.spell_enabled and hp <= spellThreshold then
        local spell = moduleValue(externalRecoveryRuntime, "selectHealingSpell", healing, hp, nonce) or healing.spell
        local bridgeTrace = moduleValue(externalRecoveryBridge, "dispatchHealing", spell, vitals, now, false)
        if bridgeTrace and bridgeTrace.status == "executed" then
            healing.last_cast_ms = now
            healing.last_recovery_action_ms = now
            local spellText = moduleValue(externalRecoveryRuntime, "spellStatusText", spell, hp)
            status(type(spellText) == "string" and spellText ~= "" and spellText or ("Spell heal: " .. spell .. " at " .. hp .. "%"))
            return true
        end
    end
    return false
end

function setCavebotStatus(text)
    if Helper.widgets.cavebot_status and Helper.widgets.cavebot_status.setText then
        Helper.widgets.cavebot_status:setText(fitText("Status: " .. tostring(text or "idle"), UI_LAYOUT.content_w - 22, 0.9))
    end
end

local diagnosticsController = moduleValue(externalDiagnostics, "createController", {
    helper = Helper, config = HELPER_CONFIG, version = HELPER_VERSION,
    content_width = UI_LAYOUT.content_w, fit_text = fitText,
    update_snapshot = externalUi and externalUi.updateDiagnosticsSnapshot,
    serialize = externalProfileSchema and externalProfileSchema.serializeLua,
    now_ms = helperNowMs, status = status, delay = delay,
    get_player = getLocalPlayer, get_position = getThingPosition,
    read_vitals = readPlayerVitals, pcall_number = pcallNumber,
    online = isGameOnline, game = g_game, map = g_map, ui = g_ui,
    keyboard = g_keyboard, resources = g_resources, runtime_core = externalRuntimeCore,
    clock_millis = g_clock and g_clock.millis,
    refresh_operator = function() if refreshOperatorSummaries then refreshOperatorSummaries() end end,
    loot_adapter_text = function(containersOk, containers, online)
        local text = moduleValue(externalLootRuntime, "adapterSummary", HELPER_CONFIG.tools or {},
            {online = online, in_protection_zone = isLocalPlayerInProtectionZone()},
            {open_container_count = containersOk and moduleValue(externalDiagnostics, "tableCount", containers) or 0,
             corpse_candidate_count = 0, valuable_item_count = 0, free_capacity = 1})
        return type(text) == "string" and fitText(text, UI_LAYOUT.content_w - 14, 0.78) or ""
    end,
})

function maybeSampleDiagnostics(now)
    local tools = HELPER_CONFIG.tools or {}
    local flags = tools.feature_flags or {}
    if flags.diagnostics ~= true then
        return false
    end
    if now - (tools.last_diagnostics_sample_ms or 0) < (tools.diagnostics_sample_interval_ms or 5000) then
        return false
    end
    tools.last_diagnostics_sample_ms = now
    return diagnosticsController.runApiProbe("sample")
end

function runMovementApiProbe(reason)
    if Helper.movement_api_probe_ran and reason ~= "manual" then
        return false
    end

    local player = getLocalPlayer()
    local current = getThingPosition(player)
    local deferPlan = moduleValue(externalDiagnostics, "probeDeferredPlan", {reason = reason, label = "Move API", online = g_game and g_game.isOnline and g_game.isOnline() or false, has_player = player ~= nil, has_position = current ~= nil, requires_position = true, attempts = Helper.movement_api_probe_attempts, max_attempts = 120})
    if type(deferPlan) == "table" and deferPlan.defer == true then
        Helper.movement_api_probe_attempts = deferPlan.attempts or ((Helper.movement_api_probe_attempts or 0) + 1)
        if deferPlan.retry == true then
            delay(function() runMovementApiProbe("startup") end, deferPlan.retry_delay_ms or 2000)
        else
            status(deferPlan.status_text or "Move API probe deferred: no local player position")
        end
        return false
    end
    Helper.movement_api_probe_ran = true

    local tools = HELPER_CONFIG.tools or {}
    local routeMetadata = moduleValue(externalRoute, "probeMetadata", tools, current)
    if type(routeMetadata) ~= "table" then routeMetadata = {} end
    local target = routeMetadata.target
    local canWalkAvailable = hasApi(player, "canWalk")
    local canWalkOk, canWalkValue = safeCall(player, "canWalk", true)
    local pathAvailable = current ~= nil and target ~= nil and hasApi(g_map, "findPath")
    local pathOk, pathDirs, pathResult = false, nil, nil
    if pathAvailable then
        pathOk, pathDirs, pathResult = pcall(function()
            return g_map.findPath(current, target, 200, 0)
        end)
    end
    local report = moduleValue(externalCavebotRuntime, "probeReport", {
        reason = reason or "startup",
        api = {
            game_walk = hasApi(g_game, "walk"), game_auto_walk = hasApi(g_game, "autoWalk"),
            game_force_walk = hasApi(g_game, "forceWalk"), player_auto_walk = hasApi(player, "autoWalk"),
            player_stop_auto_walk = hasApi(player, "stopAutoWalk")
        },
        player_can_sample = {available = canWalkAvailable, ok = canWalkOk, value = canWalkValue},
        route_metadata = routeMetadata,
        path_sample = {
            available = pathAvailable, ok = pathOk, dirs_count = type(pathDirs) == "table" and #pathDirs or nil,
            result = pathResult, value = pathDirs, extra = pathResult, error = pathDirs
        }
    })
    local probeText = type(report) == "table" and report.text or nil
    status(probeText or "Move API probe unavailable")
    return true
end

function runMagicApiProbe(reason)
    if Helper.magic_api_probe_ran and reason ~= "manual" then
        return false
    end

    local player = getLocalPlayer()
    local current = getThingPosition(player)
    local deferPlan = moduleValue(externalDiagnostics, "probeDeferredPlan", {reason = reason, label = "Magic API", online = g_game and g_game.isOnline and g_game.isOnline() or false, has_player = player ~= nil, has_position = current ~= nil, requires_position = true, attempts = Helper.magic_api_probe_attempts, max_attempts = 120})
    if type(deferPlan) == "table" and deferPlan.defer == true then
        Helper.magic_api_probe_attempts = deferPlan.attempts or ((Helper.magic_api_probe_attempts or 0) + 1)
        if deferPlan.retry == true then
            delay(function() runMagicApiProbe("startup") end, deferPlan.retry_delay_ms or 2000)
        else
            status(deferPlan.status_text or "Magic API probe deferred: no local player position")
        end
        return false
    end
    Helper.magic_api_probe_ran = true

    local tools = HELPER_CONFIG.tools or {}
    local target = getSafeAttackTarget(tools.attack_range or 7)
    local scan = scanCombatArea(tools)
    local nearby = scan and scan.adjacent or 0
    local visible = scan and scan.visible or 0
    local action = buildOffensiveAction(tools, target, scan, g_clock and g_clock.millis and g_clock.millis() or 0)
    local probeText = moduleValue(externalDiagnostics, "magicApiProbeText", {
        reason = reason,
        version = HELPER_VERSION,
        game = g_game,
        target = target,
        nearby = nearby,
        visible = visible,
        spell_rotation = tools.spell_rotation,
        rune_enabled = tools.rune_enabled,
        rune_slot = moduleValue(externalHotkeys, "resolveActionbarSlot", tools.rune_actionbar_slot, tools.rune_hotkey),
        action = action,
    })
    if type(probeText) == "string" and probeText ~= "" then
        status(probeText)
    else
        status("Magic API probe unavailable")
    end
    return true
end

function refreshCavebotUi()
    local state = {waypoint_count = #(HELPER_CONFIG.tools.cavebot_waypoints or {}), current_index = HELPER_CONFIG.tools.cavebot_index or 1}
    local data = moduleValue(externalRoute, "uiState", HELPER_CONFIG.tools)
    if type(data) == "table" then
        state = data
    end
    if Helper.widgets.cavebot_wp_count and Helper.widgets.cavebot_wp_count.setText then
        Helper.widgets.cavebot_wp_count:setText(tostring(state.waypoint_count or 0))
    end
    if Helper.widgets.cavebot_current and Helper.widgets.cavebot_current.setText then
        Helper.widgets.cavebot_current:setText(tostring(state.current_index or 1))
    end
end

local function applyCavebotEditorAction(action, options)
    local result = {ok = false, message = "route unavailable"}
    local data = moduleValue(externalRoute, "editorAction", HELPER_CONFIG.tools, action, options or {})
    if type(data) == "table" then
        result = data
    end
    if result.ok == true and result.dirty_reason then
        markProfileDirty(result.dirty_reason)
    end
    refreshCavebotUi()
    setCavebotStatus(result.message or "route unavailable")
    return result.ok == true
end

function addCurrentCavebotWaypoint()
    local player = getLocalPlayer()
    local pos = getThingPosition(player)
    if not pos then
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", "no_player_position"))
        return false
    end
    return applyCavebotEditorAction("add", {pos = pos})
end

function deleteCurrentCavebotWaypoint(confirm)
    if confirm ~= true and moduleValue(externalModal, "isPending", Helper.pending_confirm, "cavebot_delete", helperNowMs()) ~= true then
        local request = {label = "no waypoint", timeout_ms = 4500}
        local data = moduleValue(externalRoute, "deleteRequest", HELPER_CONFIG.tools)
        if type(data) == "table" then
            request = data
        end
        Helper.pending_confirm = moduleValue(externalModal, "modalRequest", "cavebot_delete", request.label, request.timeout_ms, helperNowMs())
        local statusText = moduleValue(externalModal, "statusText", Helper.pending_confirm)
        setCavebotStatus(type(statusText) == "string" and statusText ~= "" and statusText or "confirmation pending")
        return false
    end
    Helper.pending_confirm = nil
    return applyCavebotEditorAction("delete")
end

function autoWalkTo(pos)
    if not pos then
        return false
    end

    local player = getLocalPlayer()
    local current = getThingPosition(player)
    local blockedOk, blocked = moduleCall(externalCavebotRuntime, "movementBlockedReason", {
        online = isGameOnline(), has_player = player ~= nil, has_position = current ~= nil,
        in_protection_zone = isLocalPlayerInProtectionZone()
    })
    if not blockedOk then blocked = "movement adapter unavailable" end
    local alreadyMoving = false
    if player and player.isAutoWalking then
        local walkingOk, walking = pcall(function()
            return player:isAutoWalking()
        end)
        alreadyMoving = walkingOk and walking == true
    end
    local movementCapability = moduleValue(externalCavebotRuntime, "movementCapabilityForPlayer", player, safeCall) or {can_move = false, can_move_value = nil}
    local preflight = {allowed = true}
    local planned = moduleValue(externalCavebotRuntime, "walkPreflight", {
        movement_enabled = HELPER_CONFIG.tools.cavebot_movement_enabled == true,
        blocked_reason = blocked,
        same_floor = current and pos and current.z == pos.z,
        api_available = player ~= nil and player.autoWalk ~= nil,
        already_moving = alreadyMoving,
        can_move = movementCapability.can_move,
        can_move_value = movementCapability.can_move_value
    })
    if type(planned) == "table" then
        preflight = planned
    end
    if preflight.already_moving then
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", preflight.status_event, preflight.status_data))
        return true
    end
    if not preflight.allowed then
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", preflight.status_event, preflight.status_data))
        return false
    end

    local pathOk, pathDirs, pathResult = safeGlobalCall(g_map, "findPath", current, pos, 200, 0)
    local pathText = moduleValue(externalCavebotRuntime, "pathText", {available = current ~= nil and pos ~= nil and hasApi(g_map, "findPath"), ok = pathOk, dirs_count = type(pathDirs) == "table" and #pathDirs or nil, result = pathResult, value = pathDirs, extra = pathResult, error = pathDirs}) or "n/a"

    local retry = (HELPER_CONFIG.tools.cavebot_retry_attempts or 0) > 0
    local ok, result = pcall(function()
        return player:autoWalk(pos, retry)
    end)
    status(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "traceText", "movement_attempt", {
        target = moduleValue(externalDiagnostics, "posText", pos) or "diagnostics unavailable",
        current = moduleValue(externalDiagnostics, "posText", current) or "diagnostics unavailable",
        path = pathText,
        retry = retry,
        ok = ok,
        result = result
    }))
    if ok and result ~= false then
        return true
    end
    return false
end

function testCavebotAutoWalk()
    local player = getLocalPlayer()
    local current = getThingPosition(player)

    local tools = HELPER_CONFIG.tools or {}
    local waypoints = tools.cavebot_waypoints or {}
    if #waypoints > 0 then
        tools.cavebot_index = math.max(1, math.min(tonumber(tools.cavebot_index) or 1, #waypoints))
    end
    local waypoint = waypoints[tools.cavebot_index or 1]
    local target = moduleValue(externalRoute, "position", waypoint)
    local movementCapability = moduleValue(externalCavebotRuntime, "movementCapabilityForPlayer", player, safeCall) or {can_move = false, can_move_value = nil}
    local plan = {allowed = true}
    local planned = moduleValue(externalCavebotRuntime, "testWalkPlan", {
        has_player_position = player ~= nil and current ~= nil,
        has_waypoint = #waypoints > 0,
        has_target = target ~= nil,
        same_floor = current and target and current.z == target.z,
        api_available = player ~= nil and player.autoWalk ~= nil,
        can_move = movementCapability.can_move,
        can_move_value = movementCapability.can_move_value,
        current_text = moduleValue(externalDiagnostics, "posText", current) or "diagnostics unavailable",
        target_text = moduleValue(externalDiagnostics, "posText", target) or "diagnostics unavailable"
    })
    if type(planned) == "table" then
        plan = planned
    end
    if not plan.allowed then
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", plan.status_event, plan.status_data))
        status(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "traceText", plan.trace_event or "test_blocked", plan.trace_data))
        return false
    end

    local pathOk, pathDirs, pathResult = safeGlobalCall(g_map, "findPath", current, target, 200, 0)
    local pathText = moduleValue(externalCavebotRuntime, "pathText", {available = current ~= nil and target ~= nil and hasApi(g_map, "findPath"), ok = pathOk, dirs_count = type(pathDirs) == "table" and #pathDirs or nil, result = pathResult, value = pathDirs, extra = pathResult, error = pathDirs}) or "n/a"

    local ok, result = pcall(function()
        return player:autoWalk(target, false)
    end)
    status(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "traceText", "test_attempt", {
        target = moduleValue(externalDiagnostics, "posText", target) or "diagnostics unavailable",
        current = moduleValue(externalDiagnostics, "posText", current) or "diagnostics unavailable",
        path = pathText,
        ok = ok,
        result = result
    }))
    if ok and result ~= false then
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", "test_sent", {label = moduleValue(externalRoute, "label", waypoint, tools.cavebot_index) or "#" .. tostring(tools.cavebot_index or "?")}))
        return true
    end
    setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", "test_failed"))
    return false
end

function maybeRunCavebot(now)
    local tools = HELPER_CONFIG.tools
    if not tools.cavebot_enabled then
        return false
    end
    if not tools.cavebot_movement_enabled then
        moduleValue(externalCavebotRuntime, "resetMovementState", tools)
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", "movement_disabled", nil, "movement disabled"))
        return false
    end
    local waypoints = tools.cavebot_waypoints or {}
    if now - (tools.cavebot_last_walk_ms or 0) < (tools.cavebot_step_delay_ms or 1200) then
        return false
    end

    local player = getLocalPlayer()
    local current = getThingPosition(player)
    local blockedOk, blocked = moduleCall(externalCavebotRuntime, "movementBlockedReason", {
        online = isGameOnline(), has_player = player ~= nil, has_position = current ~= nil,
        in_protection_zone = isLocalPlayerInProtectionZone()
    })
    if not blockedOk then blocked = "movement adapter unavailable" end
    if blocked then
        moduleValue(externalCavebotRuntime, "resetMovementState", tools)
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", "movement_blocked", {reason = blocked}))
        return false
    end

    local routeTarget = moduleValue(externalRoute, "activeTarget", tools, current, tools.cavebot_reach_distance or 1)
    if type(routeTarget) ~= "table" then routeTarget = {ok = false, status_event = "route_unavailable"} end
    if routeTarget.reached then
        moduleValue(externalCavebotRuntime, "resetMovementState", tools)
        status(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "traceText", "movement_reset", {reason = "waypoint reached"}))
    end
    if not routeTarget.ok then
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", routeTarget.status_event))
        return false
    end
    local waypoint = routeTarget.waypoint
    local target = routeTarget.target
    local targetIndex = routeTarget.index or tools.cavebot_index

    local adapterStatus = moduleValue(externalCavebotRuntime, "adapterStatusSummary", {
        cavebot_movement_enabled = tools.cavebot_movement_enabled,
        pause_in_pz = tools.pause_in_pz,
        retry_count = tools.cavebot_retry_attempts or 0,
        max_retries = tools.cavebot_retry_limit or 3
    }, {online = g_game and g_game.isOnline and g_game.isOnline() or false, in_protection_zone = isLocalPlayerInProtectionZone()},
        {count = #waypoints, selected_index = tonumber(tools.cavebot_index) or 0, has_target = target ~= nil})
    if type(adapterStatus) == "string" and adapterStatus ~= "" then
        setCavebotStatus(fitText(adapterStatus, UI_LAYOUT.content_w - 14, 0.78))
    end

    local stuck = moduleValue(externalRoute, "progress", tools, moduleValue(externalRoute, "posKey", current), moduleValue(externalRoute, "posKey", target), now) == true
    local retryDecision = moduleValue(externalCavebotRuntime, "retryDecision", {
        stuck = stuck,
        retry_budget_exceeded = moduleValue(externalCavebotRuntime, "cavebotRetryBudgetExceeded", tools),
        target = moduleValue(externalDiagnostics, "posText", target) or "diagnostics unavailable",
        current = moduleValue(externalDiagnostics, "posText", current) or "diagnostics unavailable",
        attempts = tools.cavebot_retry_attempts
    })
    if type(retryDecision) == "table" and retryDecision.disable_movement then
        tools.cavebot_movement_enabled = false
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", retryDecision.status_event, retryDecision.status_data))
        status(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "traceText", retryDecision.trace_event, retryDecision.trace_data))
        return false
    end

    if autoWalkTo(target) then
        tools.cavebot_last_walk_ms = now
        local walkingData = {waypoint_label = moduleValue(externalRoute, "label", waypoint, targetIndex) or "#" .. tostring(targetIndex or "?"), retry_status = moduleValue(externalRoute, "retryStatus", tools) or "retry unavailable", retry_count = tools.cavebot_retry_attempts or 0, retry_limit = tools.cavebot_retry_limit or 3}
        local walking = moduleValue(externalCavebotRuntime, "walkingStatus", walkingData)
        if type(walking) ~= "table" then
            walking = {event = "walking", data = walkingData}
        end
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", walking.event, walking.data, walking.text))
        return true
    end
    tools.cavebot_retry_attempts = (tools.cavebot_retry_attempts or 0) + 1
    local failedRetryDecision = moduleValue(externalCavebotRuntime, "retryDecision", {
        walk_failed = true,
        retry_budget_exceeded = moduleValue(externalCavebotRuntime, "cavebotRetryBudgetExceeded", tools),
        target = moduleValue(externalDiagnostics, "posText", target) or "diagnostics unavailable",
        retry_count = tools.cavebot_retry_attempts or 0
    })
    if type(failedRetryDecision) == "table" and failedRetryDecision.disable_movement then
        tools.cavebot_movement_enabled = false
        setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", failedRetryDecision.status_event, failedRetryDecision.status_data))
        status(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "traceText", failedRetryDecision.trace_event, failedRetryDecision.trace_data))
        return false
    end
    local retryStatus = failedRetryDecision
    if type(retryStatus) ~= "table" then
        retryStatus = {status_event = "walk_retry", status_data = {retry_count = tools.cavebot_retry_attempts or 0}}
    end
    setCavebotStatus(moduleValue(externalCavebotRuntime, "cavebotRuntimeText", "statusText", retryStatus.status_event, retryStatus.status_data))
    return false
end

function maybeManaPotion(now, vitals)
    local healing = HELPER_CONFIG.healing
    if not healing.mana_potion_enabled then
        return false
    end
    if moduleValue(externalRecoveryRuntime, "recoveryActionGap", now, HELPER_CONFIG.healing, HELPER_CONFIG.tools).active then
        return false
    end
    if now - (healing.last_mana_potion_ms or 0) < (healing.mana_potion_cooldown_ms or healing.cooldown_ms or 1000) then
        return false
    end

    vitals = vitals or readPlayerVitals()
    local mp = vitals.mana_percent
    local jitter = healing.threshold_jitter_percent or 3
    local nonce = math.floor(now / math.max(500, healing.mana_potion_cooldown_ms or healing.cooldown_ms or 1000))
    local manaThreshold = moduleValue(externalRecoveryRuntime, "jitterThreshold", healing.mana_potion_threshold or 45, jitter, nonce + 71) or (healing.mana_potion_threshold or 45)
    if not mp or mp > manaThreshold then
        return false
    end

    local sent, slot = sendActionbarSlot(healing.mana_potion_actionbar_slot, healing.mana_potion_hotkey)
    if sent then
        healing.last_mana_potion_ms = now
        healing.last_recovery_action_ms = now
        local slotText = moduleValue(externalHotkeys, "actionbarSlotText", slot) or "actionbar ?"
        local potionText = moduleValue(externalRecoveryRuntime, "potionStatusText", "Mana potion", nil, slotText, mp)
        if type(potionText) ~= "string" or potionText == "" then
            potionText = "Mana potion via " .. slotText .. " at " .. mp .. "%"
        end
        setLastPotionStatus("Last potion: " .. potionText:gsub("^Mana potion ", ""))
        status(potionText)
        return true
    end
    return false
end

function maybeSampleConditions(now)
    local conditions = HELPER_CONFIG.conditions or {}
    local sampled = moduleValue(externalConditions, "observe", conditions, now, {
        getLocalPlayer = getLocalPlayer,
        hasAnyState = hasAnyState,
        pcallNumber = pcallNumber
    })
    if sampled ~= nil then
        if sampled then
            if Helper.widgets.conditions_status and Helper.widgets.conditions_status.setText then
                Helper.widgets.conditions_status:setText(fitText("Status: " .. tostring(conditions.last_status), UI_LAYOUT.content_w - 14, 0.88))
            end
            return true
        end
        return false
    end
    if conditions.enabled == true and conditions.observe_states == true then
        conditions.last_status = "conditions module unavailable"
        if Helper.widgets.conditions_status and Helper.widgets.conditions_status.setText then
            Helper.widgets.conditions_status:setText(fitText("Status: " .. tostring(conditions.last_status), UI_LAYOUT.content_w - 14, 0.88))
        end
    end
    return false
end

function maybeSampleEquipment(now)
    local equipment = HELPER_CONFIG.equipment or {}
    local sampled = moduleValue(externalEquipment, "observe", equipment, now, {
        getLocalPlayer = getLocalPlayer,
        safeCall = safeCall
    })
    if sampled ~= nil then
        if sampled then
            if Helper.widgets.equipment_status and Helper.widgets.equipment_status.setText then
                Helper.widgets.equipment_status:setText(fitText("Status: " .. tostring(equipment.last_status), UI_LAYOUT.content_w - 14, 0.88))
            end
            return true
        end
        return false
    end
    if equipment.enabled == true and equipment.observe_slots == true then
        equipment.last_status = "equipment module unavailable"
        if Helper.widgets.equipment_status and Helper.widgets.equipment_status.setText then
            Helper.widgets.equipment_status:setText(fitText("Status: " .. tostring(equipment.last_status), UI_LAYOUT.content_w - 14, 0.88))
        end
    end
    return false
end

function maybeRunTimer(now)
    local tools = HELPER_CONFIG.tools or {}
    if combatBlockedReason(tools) then
        return false
    end
    local context = {
        online = g_game and g_game.isOnline and g_game.isOnline() or false,
        in_protection_zone = isLocalPlayerInProtectionZone(),
        now_ms = now
    }
    local plan = moduleValue(externalTimerRuntime, "plan", tools, context)
    if type(plan) ~= "table" then
        return false
    end
    local dispatch = moduleValue(externalTimerRuntime, "dispatch", plan, tools, {
        summary = function(runtimePlan)
            local summary = moduleValue(externalTimerRuntime, "summary", runtimePlan)
            if type(summary) == "string" and summary ~= "" then
                return fitText(summary, UI_LAYOUT.content_w - 14, 0.78)
            end
            return ""
        end
    })
    if type(dispatch) ~= "table" then
        return false
    end
    if dispatch.allowed ~= true then
        throttledRuntimeStatus(tostring(dispatch.status_text or "Timer adapter: hold"), now)
        return false
    end
    local message = tostring(dispatch.message or "")
    if message == "" then
        return false
    end
    if castSpell(message) then
        tools.last_timer_ms = now
        status(tostring(dispatch.status_text or ("Timer: " .. shortText(message, 32))))
        return true
    end
    return false
end

function maybeUseTools(now, vitals)
    local tools = HELPER_CONFIG.tools
    local blocked = combatBlockedReason(tools)
    if blocked then
        if Helper.widgets.monster_stats and Helper.widgets.monster_stats.setText then
            Helper.widgets.monster_stats:setText("Target: none | " .. blocked)
        end
        clearUnsafeCurrentTarget(blocked, now)
        throttledRuntimeStatus("Runtime blocked: " .. blocked, now)
        return
    end

    local target = getSafeAttackTarget(tools.attack_range or 7)
    if tools.auto_attack and not target then
        target = retargetSafeMonster(now, tools) or getSafeAttackTarget(tools.attack_range or 7)
    end
    local scan = scanCombatArea(tools)
    local nearby = scan.adjacent or 0
    local visible = scan.visible or 0
    vitals = vitals or readPlayerVitals()
    local hp = vitals.hp_percent or 0
    local mp = vitals.mana_percent or 0
    local nextAction = planNextCombatAction(target, scan, now)
    local decisionState = combatDecisionStateText(tools, target, scan, now, nextAction)
    updateCombatStats(target, nearby, visible)
    updateOverviewStats(target, nearby, visible, hp, mp, nextAction, now)
    if Helper.widgets.magic_footer and Helper.widgets.magic_footer.setText then
        Helper.widgets.magic_footer:setText(fitText("Magic " .. HELPER_VERSION .. ": " .. decisionState, UI_LAYOUT.content_w - 22, 0.82))
    end
    local hudRuntimeText = moduleValue(externalHud, "runtimeText", {
        version = HELPER_VERSION,
        profile = moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText),
        hp = hp,
        mp = mp,
        nearby = nearby,
        visible = visible,
        runtime_state = currentOperatorRuntimeState(now, nil),
        decision = decisionState
    })
    setHudText(type(hudRuntimeText) == "string" and hudRuntimeText ~= "" and hudRuntimeText or "HUD module unavailable | runtime gated")

    local hasteEvidence = moduleValue(externalSpellStateRegistry, "observeHaste", getLocalPlayer(), now, {
        read_states = function(player) return pcallNumber(player, "getStates") end
    })
    local hastePlan = moduleValue(externalSpellStateRegistry, "hasteDecision", tools, hasteEvidence, now)
    if type(hastePlan) == "table" and hastePlan.allowed == true then
        if castSpell(hastePlan.spell) then
            tools.last_haste_ms = now
            status("Auto haste: " .. tostring(hastePlan.spell))
        end
    end

    executeOffensiveAction(tools, buildOffensiveAction(tools, target, scan, now), nearby, visible, now)
end

function onThink()
    local projectLoader = rawget(_G, "CTOA_PROJECT_LOADER")
    if type(projectLoader) == "table" and projectLoader.active_project ~= "helper" then
        return
    end
    local now = helperNowMs()
    moduleValue(externalClientReporter, "report", Helper, HELPER_CONFIG, HELPER_VERSION, externalRuntimeCore, externalObservationAdapter, now, false, true)
    if not isGameOnline() then return end
    if now - (Helper.last_vocation_probe_ms or 0) >= 1000 then
        Helper.last_vocation_probe_ms = now
        local player = g_game and g_game.getLocalPlayer and g_game.getLocalPlayer() or nil
        local detected = moduleValue(externalVocationProfiles, "detect", player)
        if detected and detected ~= Helper.vocation_id and type(Helper.handleGameStart) == "function" then
            Helper.handleGameStart()
        end
    end
    processSmokeCommand()
    if not HELPER_CONFIG.enabled then
        local disarmedText = moduleValue(externalHud, "disarmedText")
        setHudText(type(disarmedText) == "string" and disarmedText ~= "" and disarmedText or "HUD module unavailable | runtime disarmed")
        throttledRuntimeStatus("Runtime disarmed", now)
        return
    end
    local blocked = runtimeBlockedReason(now)
    if blocked then
        throttledRuntimeStatus("Runtime blocked: " .. blocked, now)
        return
    end
    local vitals = readPlayerVitals()
    maybeHeal(now, vitals)
    maybeManaPotion(now, vitals)
    maybeObserveHealFriend(now)
    maybeSampleConditions(now)
    maybeSampleEquipment(now)
    maybeSampleDiagnostics(now)
    maybeRunCavebot(now)
    maybeRunTimer(now)
    maybeUseTools(now, vitals)
end

function syncFromUi(runtimeRequested)
    if Helper.widgets.enabled then
        local requestedEnabled = runtimeRequested
        if requestedEnabled == nil then requestedEnabled = getWidgetChecked(Helper.widgets.enabled) end
        if requestedEnabled then
            requestRuntimeSessionArm("runtime control")
        else
            Helper.runtime_session_armed = false
            moduleValue(externalRecoveryBridge, "disarm", "runtime_disabled")
        end
        local blocked = requestedEnabled and runtimeArmingBlockedReason() or nil
        if blocked then
            HELPER_CONFIG.enabled = false
            setWidgetChecked(Helper.widgets.enabled, false)
            setWidgetText(Helper.widgets.enabled, "BLOCKED")
            styleUi("styleRuntimeBadge", Helper.widgets.enabled, false, true, UI_STYLE, AlignCenter)
            status("Runtime arm blocked: " .. blocked)
        else
            HELPER_CONFIG.enabled = requestedEnabled
            setWidgetText(Helper.widgets.enabled, HELPER_CONFIG.enabled and "ARMED" or "DISARMED")
            styleUi("styleRuntimeBadge", Helper.widgets.enabled, HELPER_CONFIG.enabled, false, UI_STYLE, AlignCenter)
        end
    end
    if Helper.widgets.spell_heal then
        HELPER_CONFIG.healing.spell_enabled = getWidgetChecked(Helper.widgets.spell_heal)
    end
    if Helper.widgets.potion_heal then
        HELPER_CONFIG.healing.potion_enabled = getWidgetChecked(Helper.widgets.potion_heal)
    end
    status(HELPER_CONFIG.enabled and "Runtime armed" or "Runtime disarmed")
    markProfileDirty("sync")
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
end

function armRuntime(reason)
    if HELPER_CONFIG.enabled then
        return
    end
    local blocked = runtimeArmingBlockedReason()
    if blocked then
        HELPER_CONFIG.enabled = false
        setWidgetChecked(Helper.widgets.enabled, false)
        setWidgetText(Helper.widgets.enabled, "BLOCKED")
        styleUi("styleRuntimeBadge", Helper.widgets.enabled, false, true, UI_STYLE, AlignCenter)
        status("Runtime arm blocked: " .. blocked)
        return false
    end
    HELPER_CONFIG.enabled = true
    setWidgetChecked(Helper.widgets.enabled, true)
    setWidgetText(Helper.widgets.enabled, "ARMED")
    styleUi("styleRuntimeBadge", Helper.widgets.enabled, true, false, UI_STYLE, AlignCenter)
    status("Runtime armed: " .. tostring(reason or "module enabled"))
    if refreshOperatorSummaries then
        refreshOperatorSummaries()
    end
    return true
end

moduleValue(externalRecoveryBridge, "configure", {
    work_dir = function()
        if not g_resources or type(g_resources.getWorkDir) ~= "function" then return "" end
        local ok, value = pcall(function() return g_resources.getWorkDir() end)
        return ok and value or ""
    end,
    now_ms = helperNowMs,
    online = isGameOnline,
    player_ready = function() return getLocalPlayer() ~= nil end,
    in_protection_zone = isLocalPlayerInProtectionZone,
    cooldown_ms = function() return HELPER_CONFIG.healing.cooldown_ms or 1000 end,
    read_vitals = readPlayerVitals,
    select_spell = function(hp, now)
        local nonce = math.floor((tonumber(now) or 0) / math.max(500, tonumber(HELPER_CONFIG.healing.cooldown_ms) or 1000))
        return moduleValue(externalRecoveryRuntime, "selectHealingSpell", HELPER_CONFIG.healing, hp, nonce) or HELPER_CONFIG.healing.spell
    end,
    cast = castSpell,
    request_runtime_arm = requestRuntimeSessionArm,
    arm_runtime = armRuntime,
    enable_healing = function() HELPER_CONFIG.healing.spell_enabled = true end,
    kill_runtime = function()
        HELPER_CONFIG.enabled = false
        HELPER_CONFIG.healing.spell_enabled = false
        setWidgetChecked(Helper.widgets.enabled, false)
        setWidgetText(Helper.widgets.enabled, "KILLED")
    end,
    status = status,
})
Helper.recoveryBridgeStatus = function() return moduleValue(externalRecoveryBridge, "controlStatus") or "BRIDGE MISSING" end
Helper.recoveryBridgeArm = function() return moduleValue(externalRecoveryBridge, "controlArm") == true end
Helper.recoveryBridgeKill = function() return moduleValue(externalRecoveryBridge, "controlKill") == true end
Helper.recoveryBridgeDryRun = function() return moduleValue(externalRecoveryBridge, "controlDryRun") end
Helper.recoveryBridgeExecuteOnce = function() return moduleValue(externalRecoveryBridge, "controlExecuteOnce") == true end

moduleValue(externalConditionsExecuteOnce, "configure", {
    work_dir = function()
        if not g_resources or type(g_resources.getWorkDir) ~= "function" then return "" end
        local ok, value = pcall(function() return g_resources.getWorkDir() end)
        return ok and value or ""
    end,
    now_ms = helperNowMs,
    observe = function(now) return moduleValue(externalConditions, "executeOnceObservation", HELPER_CONFIG, now, {
        getLocalPlayer = getLocalPlayer, readVitals = readPlayerVitals, online = isGameOnline,
        inProtectionZone = isLocalPlayerInProtectionZone, hasAnyState = hasAnyState,
        pcallNumber = pcallNumber,
    }) end,
    cast = function(spell)
        local executed = castSpell(spell)
        if executed then HELPER_CONFIG.healing.last_cast_ms = helperNowMs() end
        return executed
    end,
    status = status,
})
Helper.conditionsExecuteOnce = function(command)
    return moduleValue(externalConditionsExecuteOnce, "controlExecuteOnce", command) == true
end

moduleValue(externalEquipmentExecuteOnce, "configure", {
    work_dir = function()
        if not g_resources or type(g_resources.getWorkDir) ~= "function" then return "" end
        local ok, value = pcall(function() return g_resources.getWorkDir() end)
        return ok and value or ""
    end,
    now_ms = helperNowMs,
    observe = function(now)
        return moduleValue(externalObservationAdapter, "equipmentShadowObservation", {
            observed_at_unix_ms = now, game = g_game, modules = modules,
        })
    end,
    move = function(payload)
        if not g_game or type(g_game.getContainers) ~= "function" or type(g_game.move) ~= "function" then return false end
        local player = getLocalPlayer(); if not player or type(player.getInventoryItem) ~= "function" then return false end
        local ringSlot = _G.InventorySlotFinger or _G.InventorySlotRing
        local okRing, ring = pcall(player.getInventoryItem, player, ringSlot)
        if not okRing or not ring or type(ring.getId) ~= "function" or ring:getId() ~= 3096 or type(ring.getPosition) ~= "function" then return false end
        local okContainers, containers = pcall(function() return g_game.getContainers() end)
        if not okContainers or type(containers) ~= "table" then return false end
        local candidate = nil
        for key, container in pairs(containers) do
            local containerId = type(container.getId) == "function" and container:getId() or tonumber(key)
            if tonumber(containerId) == tonumber(payload.container_id) and type(container.getItems) == "function" then
                local items = container:getItems(); local index = 0
                for _, item in pairs(type(items) == "table" and items or {}) do
                    index = index + 1
                    if index == tonumber(payload.slot_index) and type(item.getId) == "function" and item:getId() == 3097 then candidate = item end
                end
            end
        end
        if not candidate then return false end
        local destination = ring:getPosition(); if not destination then return false end
        local okMove = pcall(function() g_game.move(candidate, destination, 1) end)
        return okMove
    end,
    status = status,
})
Helper.equipmentExecuteOnce = function(command)
    return moduleValue(externalEquipmentExecuteOnce, "controlExecuteOnce", command) == true
end

moduleValue(externalHealFriendExecuteOnce, "configure", {
    work_dir = function()
        if not g_resources or type(g_resources.getWorkDir) ~= "function" then return "" end
        local ok, value = pcall(function() return g_resources.getWorkDir() end)
        return ok and value or ""
    end,
    now_ms = helperNowMs,
    vocation = function() return tostring(Helper.vocation_id or "") end,
    observe = function(now, binding)
        local target = binding or {}
        local base = moduleValue(externalObservationAdapter, "healFriendScan", {
            observed_at_unix_ms = now, game = g_game, map = g_map, modules = modules,
        }) or {}
        return moduleValue(externalHealFriend, "executeOnceObservation", {
            enabled = true, observe_party = true, friend_whitelist = {tostring(target.target_name or "")},
            friend_target_id = tonumber(target.target_id), friend_scan_range = tonumber(target.max_range) or 7,
            hp_threshold = tonumber(target.hp_threshold) or 70,
        }, now, {
            base_observation = base,
            getLocalPlayer = getLocalPlayer,
            getThingPosition = getThingPosition,
            getSpectatorsInRange = getSpectatorsInRange,
            isPlayerCreature = isPlayerCreature,
            distanceChebyshev = type(externalRoute) == "table" and type(externalRoute.distanceChebyshev) == "function" and externalRoute.distanceChebyshev or nil,
            normalizedCreatureName = normalizedCreatureName,
            getCreatureHealthPercent = getCreatureHealthPercent,
            getCreatureId = currentTargetId,
            isPartyMemberCreature = isPartyMemberCreature,
            canShootCreature = canShootCreature,
        })
    end,
    cast = castSpell,
    status = status,
})
Helper.healFriendExecuteOnce = function(command)
    return moduleValue(externalHealFriendExecuteOnce, "controlExecuteOnce", command) == true
end

function bindClick(widget, callback)
    if not widget then
        return
    end
    widget.onClick = function()
        callback()
        return true
    end
    widget.onMouseRelease = function()
        callback()
        return true
    end
end

Helper.setRuntimeModuleEnabled = function(path, value, reason)
    if type(path) ~= "table" or #path == 0 then
        return
    end
    local scope = HELPER_CONFIG
    for index = 1, #path - 1 do
        scope = scope[path[index]]
        if type(scope) ~= "table" then
            return
        end
    end
    if value == true then
        requestRuntimeSessionArm(reason or path[#path])
        local blocked = runtimeArmingBlockedReason()
        if blocked then
            scope[path[#path]] = false
            HELPER_CONFIG.enabled = false
            setWidgetChecked(Helper.widgets.enabled, false)
            setWidgetText(Helper.widgets.enabled, "BLOCKED")
            styleUi("styleRuntimeBadge", Helper.widgets.enabled, false, true, UI_STYLE, AlignCenter)
            status("Runtime module blocked: " .. tostring(reason or path[#path]) .. " (" .. blocked .. ")")
            return false
        end
    end
    scope[path[#path]] = value
    if value == true then
        armRuntime(reason or path[#path])
    end
    return true
end

function styleUi(name, ...)
    local fn = externalUi and externalUi[name]
    if type(fn) == "function" then
        return fn(...)
    end
    return nil
end

function addLabel(parent, id, text, x, y, width, section)
    local widget = createWidget("Label", parent, id, text, x, y, width or 210, 20)
    styleUi("styleLabel", widget, "default", UI_STYLE)
    return addToSection(section, widget)
end

function addSectionScaffold(parent, spec, panelX, bodyY, panelW, bodyH)
    if not spec then
        return nil
    end
    local geometry = styleUi("sectionBodyGeometry", panelX, bodyY, panelW, bodyH) or {}
    local body = createWidget("Label", parent, spec.body_id, "", geometry.x or (panelX - 2), geometry.y or bodyY, geometry.width or (panelW + 4), geometry.height or bodyH)
    styleUi("styleSectionBody", body, UI_STYLE)
    addToSection(spec.section, body)
    local headerY = spec.header_y or UI_LAYOUT.section_y
    local titleWidget = addLabel(parent, spec.header_id .. "Title", fitText(spec.title, math.floor(panelW * 0.45), 1.0), panelX, headerY, panelW, spec.section)
    styleUi("styleLabel", titleWidget, "accent", UI_STYLE)
    styleUi("styleSectionBandTitle", titleWidget, UI_STYLE, AlignLeft)
    local subtitleWidget = addLabel(parent, spec.header_id .. "Subtitle", fitText(spec.subtitle, math.floor(panelW * 0.52), 0.92), panelX, headerY + 2, panelW, spec.section)
    styleUi("styleLabel", subtitleWidget, "muted", UI_STYLE)
    styleUi("styleSectionBandSubtitle", subtitleWidget, UI_STYLE, AlignRight)
    local divider = createWidget("Label", parent, spec.header_id .. "Divider", "", panelX, headerY + 20, panelW, 1)
    styleUi("styleSectionBandDivider", divider, UI_STYLE)
    addToSection(spec.section, divider)
    return titleWidget, subtitleWidget
end

function addMetricCard(parent, id, label, value, x, y, width, section, active)
    local row = createWidget("Label", parent, id .. "Row", "", x, y, width, 23)
    styleUi("styleMetricRow", row, active, UI_STYLE)
    addToSection(section, row)

    local geometry = styleUi("metricCardGeometry", x, width) or {}
    local labelWidth = geometry.label_width or math.floor(width * 0.42)
    local valueWidth = geometry.value_width or (width - labelWidth - 18)
    local labelWidget = createWidget("Label", parent, id .. "Label", fitText(label, labelWidth - 8, 1.02), geometry.label_x or (x + 8), y + (geometry.label_y_offset or 3), labelWidth, geometry.label_height or 15)
    styleUi("styleMetricLabel", labelWidget, UI_STYLE, AlignLeft)
    addToSection(section, labelWidget)

    local valueWidget = createWidget("Label", parent, id .. "Value", fitText(value, valueWidth - 8, 1.02), geometry.value_x or (x + labelWidth + 10), y + (geometry.value_y_offset or 3), valueWidth, geometry.value_height or 15)
    styleUi("styleMetricValue", valueWidget, UI_STYLE, AlignRight)
    addToSection(section, valueWidget)

    return {
        row = row,
        label = labelWidget,
        value = valueWidget,
        label_width = labelWidth,
        value_width = valueWidth
    }
end

addSettingRow = function(parent, id, label, value, x, y, width, section, active) return styleUi("addSettingRow", uiRowAdapter(), parent, id, label, value, x, y, width, section, active) end
addToggleSettingRow = function(parent, id, label, getter, setter, x, y, width, section) return styleUi("addToggleSettingRow", uiRowAdapter(), parent, id, label, getter, setter, x, y, width, section) end

local SPELL_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "spell")
local CRITICAL_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "critical_spell")
local POTION_NAME_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "potion_name")
local MANA_POTION_NAME_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "mana_potion_name")
local HOTKEY_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "hotkey")
local RUNE_NAME_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "rune_name")
local SIO_SPELL_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "sio_spell")
local HEAL_FRIEND_PRIORITY_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "heal_friend_priority")
local MAGIC_PRIORITY_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "magic_priority")
local UI_HOTKEY_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "ui_hotkey")
THEME_PRESETS = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "theme_preset")
local TOOL_TIMEOUT_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "tool_timeout_ms")
local TIMER_INTERVAL_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "timer_interval_ms")
local TOOL_RANGE_CHOICES = moduleValue(externalProfileSchema, "profileSchemaTable", "optionList", {}, "tool_range")
local ROTATION_PRESETS = moduleValue(externalProfileSchema, "profileSchemaTable", "rotationPresets", {})

spellText = type(externalProfileSchema) == "table" and type(externalProfileSchema.spellLabel) == "function" and externalProfileSchema.spellLabel or tostring
potionText = type(externalProfileSchema) == "table" and type(externalProfileSchema.potionLabel) == "function" and externalProfileSchema.potionLabel or tostring
runeText = type(externalProfileSchema) == "table" and type(externalProfileSchema.runeLabel) == "function" and externalProfileSchema.runeLabel or tostring
healFriendPriorityText = type(externalProfileSchema) == "table" and type(externalProfileSchema.healFriendPriorityLabel) == "function" and externalProfileSchema.healFriendPriorityLabel or tostring
magicPriorityText = type(externalProfileSchema) == "table" and type(externalProfileSchema.magicPriorityLabel) == "function" and externalProfileSchema.magicPriorityLabel or tostring
themePresetText = type(externalProfileSchema) == "table" and type(externalProfileSchema.themePresetLabel) == "function" and externalProfileSchema.themePresetLabel or tostring
onOffText = function(value)
    local fallback = value and "ON" or "OFF"
    local text = moduleValue(externalProfileSchema, "profileSchemaValue", "onOffLabel", fallback, value)
    return type(text) == "string" and text ~= "" and text or fallback
end
profileBoolText = onOffText

autosaveText = function()
    local fallback = "saved"
    if Helper.profile_dirty or Helper.ui_dirty then
        fallback = "pending"
    end
    local text = moduleValue(externalProfileSchema, "profileSchemaValue", "autosaveLabel", fallback, {
            profile_dirty = Helper.profile_dirty == true,
            ui_dirty = Helper.ui_dirty == true
    })
    return type(text) == "string" and text ~= "" and text or fallback
end

local OPERATOR_SUMMARY_BRIDGES = {
    title = {fallback = "profile summary unavailable", args = function() return {
        version = HELPER_VERSION,
        profile_dirty = Helper.profile_dirty == true,
        ui_dirty = Helper.ui_dirty == true,
        profileSchema = externalProfileSchema,
        helpers = {
            displayProfileName = function() return moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText) end,
            autosaveText = autosaveText
        }
    } end},
    healing = {fallback = "healing summary unavailable", args = function() return HELPER_CONFIG, {
        profileSchema = externalProfileSchema,
        helpers = {
            onOffText = onOffText,
            actionbarSlotText = externalHotkeys and externalHotkeys.actionbarSlotText,
            resolveActionbarSlot = type(externalHotkeys) == "table" and type(externalHotkeys.resolveActionbarSlot) == "function" and externalHotkeys.resolveActionbarSlot or nil
        }
    } end},
    healFriend = {fallback = "Heal Friend module unavailable | runtime gated", args = function() return HELPER_CONFIG.heal_friend or {}, {
        healFriend = externalHealFriend,
        helpers = {onOffText = onOffText}
    } end},
    conditions = {fallback = "Conditions module unavailable | read-only", args = function() return HELPER_CONFIG.conditions or {}, {
        conditions = externalConditions,
        helpers = {onOffText = onOffText}
    } end},
    equipment = {fallback = "Equipment module unavailable | read-only", args = function() return HELPER_CONFIG.equipment or {}, {
        equipment = externalEquipment,
        helpers = {onOffText = onOffText}
    } end},
}

OPERATOR_SUMMARY_BRIDGES.scripting = {fallback = "Scripting module unavailable | runtime gated", args = function() return HELPER_CONFIG.scripting or {}, {
        scripting = externalScripting,
        helpers = {onOffText = onOffText}
} end}
OPERATOR_SUMMARY_BRIDGES.targeting = {fallback = "targeting summary unavailable", args = function() return HELPER_CONFIG.tools or {}, {
        targeting = externalTargeting,
        helpers = {onOffText = onOffText}
} end}
OPERATOR_SUMMARY_BRIDGES.magic = {fallback = "magic summary unavailable", args = function() return HELPER_CONFIG.tools or {}, {
        combatRuntime = externalCombatRuntime,
        helpers = {
            onOffText = onOffText,
            actionbarSlotText = externalHotkeys and externalHotkeys.actionbarSlotText,
            resolveActionbarSlot = type(externalHotkeys) == "table" and type(externalHotkeys.resolveActionbarSlot) == "function" and externalHotkeys.resolveActionbarSlot or nil
        }
} end}
OPERATOR_SUMMARY_BRIDGES.tools = {fallback = "tools summary unavailable", args = function() return HELPER_CONFIG, {
        featureFlags = externalFeatureFlags,
        profile = moduleValue(externalProfilePersistence, "exportProfile", HELPER_CONFIG, Helper.profile_name or "Built-in EK"),
        helpers = {onOffText = onOffText}
} end}
OPERATOR_SUMMARY_BRIDGES.profile = {fallback = "profile summary unavailable", args = function() return HELPER_CONFIG, {
        profile = moduleValue(externalProfilePersistence, "exportProfile", HELPER_CONFIG, Helper.profile_name or "Built-in EK"),
        profile_dirty = Helper.profile_dirty == true,
        ui_dirty = Helper.ui_dirty == true,
        profileSchema = externalProfileSchema,
        helpers = {
            displayProfileName = function() return moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText) end,
            spellText = spellText,
            autosaveLabel = autosaveText
        }
} end}
OPERATOR_SUMMARY_BRIDGES.ui = {fallback = "ui summary unavailable", args = function() return HELPER_CONFIG, {
        hud = externalHud,
        helpers = {
            onOffText = onOffText,
            hotkeyDisplayText = externalHotkeys and externalHotkeys.display,
            themePresetText = themePresetText
        }
} end}

refreshOperatorSummaries = function()
    local summaries = {
        title = moduleValue(externalOperatorSummary, "bridgeText", "title", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        healing = moduleValue(externalOperatorSummary, "bridgeText", "healing", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        heal_friend = moduleValue(externalOperatorSummary, "bridgeText", "healFriend", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        conditions = moduleValue(externalOperatorSummary, "bridgeText", "conditions", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        equipment = moduleValue(externalOperatorSummary, "bridgeText", "equipment", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        scripting = moduleValue(externalOperatorSummary, "bridgeText", "scripting", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        targeting = moduleValue(externalOperatorSummary, "bridgeText", "targeting", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        magic = moduleValue(externalOperatorSummary, "bridgeText", "magic", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        tools = moduleValue(externalOperatorSummary, "bridgeText", "tools", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        profile = moduleValue(externalOperatorSummary, "bridgeText", "profile", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable",
        ui = moduleValue(externalOperatorSummary, "bridgeText", "ui", OPERATOR_SUMMARY_BRIDGES) or "summary unavailable"
    }
    styleUi("refreshOperatorSummaries", {
        widgets = Helper.widgets,
        layout = UI_LAYOUT,
        fit_text = fitText,
        summaries = summaries
    })
end

function uiRowAdapter()
    return {
        create_widget = createWidget,
        add_to_section = addToSection,
        bind_click = bindClick,
        fit_text = fitText,
        set_widget_text = setWidgetText,
        layout = UI_LAYOUT,
        profile_field_geometry = function(x, width)
            local geometry = moduleValue(externalProfileSchema, "profileSchemaTable", "fieldGeometry", styleUi("profileFieldGeometry", x, width), x, width)
            return geometry.label_width and geometry or nil
        end,
        profile_cycle = function(options, current, direction)
            return moduleValue(externalProfileSchema, "profileSchemaValue", "cycleValue", current, options, current, direction)
        end,
        step_value = function(value, minValue, maxValue)
            local stepValue = moduleValue(externalProfileSchema, "profileSchemaValue", "stepValue", value, value, 0, minValue, maxValue)
            if type(stepValue) == "number" then
                return stepValue
            end
            return value
        end,
        mark_profile_dirty = markProfileDirty,
        mark_ui_prefs_dirty = markUiPrefsDirty,
        sync_from_ui = syncFromUi,
        style = UI_STYLE,
        align_center = AlignCenter
    }
end

addProfileCycleRow = function(parent, id, label, getter, setter, options, x, y, width, section, formatter, dirtyFn) return styleUi("addProfileCycleRow", uiRowAdapter(), parent, id, label, getter, setter, options, x, y, width, section, formatter, dirtyFn) end
addProfileStepRow = function(parent, id, label, getter, setter, step, minValue, maxValue, x, y, width, section, formatter, dirtyFn) return styleUi("addProfileStepRow", uiRowAdapter(), parent, id, label, getter, setter, step, minValue, maxValue, x, y, width, section, formatter, dirtyFn) end
addVectorStepRow = function(parent, id, label, getterX, setterX, getterY, setterY, step, minValue, maxValue, x, y, width, section, formatterX, formatterY, dirtyFn) return styleUi("addVectorStepRow", uiRowAdapter(), parent, id, label, getterX, setterX, getterY, setterY, step, minValue, maxValue, x, y, width, section, formatterX, formatterY, dirtyFn) end

function applyRotationPreset(presetId)
    for _, preset in ipairs(ROTATION_PRESETS) do
        if preset.id == presetId then
            local presetRules = {}
            for _, spell in ipairs(preset.spells) do
                presetRules[#presetRules + 1] = {
                    enabled = true,
                    words = spell.words,
                    use_mob_count = true,
                    min_nearby = spell.min_nearby,
                    cooldown_ms = spell.cooldown_ms,
                    max_nearby = spell.max_nearby,
                    scan_range = spell.scan_range,
                    directional = spell.directional == true
                }
            end
            local rules, decision = moduleValue(externalCombatRuntime, "replaceRotationRules", HELPER_CONFIG.tools, presetRules)
            if type(rules) ~= "table" or type(decision) ~= "table" or decision.allowed ~= true then
                status("Rotation preset blocked: combat runtime editor unavailable")
                return false
            end
            HELPER_CONFIG.tools.rotation_preset = presetId
            Helper.magic_rule_index = #rules > 0 and 1 or 0
            if Helper.widgets.profile_rotation_info and Helper.widgets.profile_rotation_info.setText then
                Helper.widgets.profile_rotation_info:setText(moduleValue(externalProfileSchema, "rotationSummaryText", HELPER_CONFIG.tools, {spellText = spellText, shortText = shortText}, "rotation summary unavailable"))
            end
            markProfileDirty("rotation_preset")
            return true
        end
    end
    return false
end

function addProfileRotationRow(parent, id, label, x, y, width, section)
    local options = moduleValue(externalProfileSchema, "profileSchemaTable", "rotationPresetIds", {}, ROTATION_PRESETS)
    if #options == 0 then
        for _, preset in ipairs(ROTATION_PRESETS) do
            options[#options + 1] = preset.id
        end
    end
    local formatter = moduleValue(externalProfileSchema, "rotationPresetFormatter", ROTATION_PRESETS)
    return addProfileCycleRow(parent, id, label, function()
        return HELPER_CONFIG.tools.rotation_preset or "smart"
    end, applyRotationPreset, options, x, y, width, section, formatter)
end

switchHuntingSubtab = function(subtab)
    Helper.active_hunting_tab = subtab or "targeting"
    setSectionVisible("hunting_targeting", Helper.active_tab == "hunting" and Helper.active_hunting_tab == "targeting")
    setSectionVisible("hunting_target_rules", Helper.active_tab == "hunting" and Helper.active_hunting_tab == "target_rules")
    setSectionVisible("hunting_magic", Helper.active_tab == "hunting" and Helper.active_hunting_tab == "magic")
    setSectionVisible("hunting_actions", Helper.active_tab == "hunting" and Helper.active_hunting_tab == "actions")
    setSectionVisible("hunting_magic_runtime", Helper.active_tab == "hunting" and Helper.active_hunting_tab == "magic_runtime")
    setWidgetText(Helper.widgets.hunting_targeting_tab, "Targeting")
    setWidgetText(Helper.widgets.hunting_target_rules_tab, "Target Rules")
    setWidgetText(Helper.widgets.hunting_magic_tab, "Spell Rules")
    setWidgetText(Helper.widgets.hunting_actions_tab, "Actions")
    setWidgetText(Helper.widgets.hunting_magic_runtime_tab, "Runtime")
    styleUi("styleSubtabState", Helper.widgets.hunting_targeting_tab, Helper.active_hunting_tab == "targeting", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.hunting_target_rules_tab, Helper.active_hunting_tab == "target_rules", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.hunting_magic_tab, Helper.active_hunting_tab == "magic", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.hunting_actions_tab, Helper.active_hunting_tab == "actions", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.hunting_magic_runtime_tab, Helper.active_hunting_tab == "magic_runtime", UI_STYLE, AlignCenter)
end

switchToolsSubtab = function(subtab)
    if subtab == "hud" then
        Helper.active_tools_tab = "helper"
        if Helper.active_tab == "tools" then
            switchTab("ui")
        end
        return
    end
    Helper.active_tools_tab = subtab or "helper"
    setSectionVisible("tools_helper", Helper.active_tab == "tools" and Helper.active_tools_tab == "helper")
    setSectionVisible("tools_pvp", Helper.active_tab == "tools" and Helper.active_tools_tab == "pvp")
    setSectionVisible("tools_timer", Helper.active_tab == "tools" and Helper.active_tools_tab == "timer")
    setSectionVisible("tools_diag", Helper.active_tab == "tools" and Helper.active_tools_tab == "diag")
    setWidgetText(Helper.widgets.tools_helper_tab, "Helper")
    setWidgetText(Helper.widgets.tools_pvp_tab, "PvP")
    setWidgetText(Helper.widgets.tools_timer_tab, "Timer")
    setWidgetText(Helper.widgets.tools_diag_tab, "Diag")
    styleUi("styleSubtabState", Helper.widgets.tools_helper_tab, Helper.active_tools_tab == "helper", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.tools_pvp_tab, Helper.active_tools_tab == "pvp", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.tools_timer_tab, Helper.active_tools_tab == "timer", UI_STYLE, AlignCenter)
    styleUi("styleSubtabState", Helper.widgets.tools_diag_tab, Helper.active_tools_tab == "diag", UI_STYLE, AlignCenter)
end

local CORE_MODULE_TABS = {
    overview = true,
    healing = true,
    targeting = true,
    magic = true,
    settings = true,
    engine = true,
}

local tabModuleId

tabModuleId = function(tab, huntingSubtab)
    if tab == "profile" then return "settings" end
    if tab == "ui" then return "engine" end
    if tab == "tools" then return "helper" end
    if tab == "hunting" then
        return (huntingSubtab == "targeting" or huntingSubtab == "target_rules") and "targeting" or "magic"
    end
    return tab
end

local function setModuleTabVisible(moduleId, value)
    HELPER_CONFIG.modules = HELPER_CONFIG.modules or {}
    HELPER_CONFIG.modules[moduleId] = value == true
    markProfileDirty("module_visibility")
    defer(function() rebuildUi() end)
end

switchTab = function(tab)
    local knownTabs = {
        overview = true,
        healing = true,
        heal_friend = true,
        conditions = true,
        hunting = true,
        cavebot = true,
        equipment = true,
        tools = true,
        scripting = true,
        profile = true,
        ui = true
    }
    if not knownTabs[tab or ""] then
        tab = "overview"
    end
    local smokeModuleId = tabModuleId and tabModuleId(Helper.smoke_tab, Helper.smoke_subtab) or nil
    if not moduleValue(externalModules, "moduleTabVisible", tabModuleId(tab, Helper.active_hunting_tab), HELPER_CONFIG.modules, smokeModuleId, CORE_MODULE_TABS) then
        tab = moduleValue(externalModules, "moduleTabVisible", "overview", HELPER_CONFIG.modules, smokeModuleId, CORE_MODULE_TABS) and "overview" or "profile"
    end
    Helper.active_tab = tab
    setSectionVisible("overview", tab == "overview")
    setSectionVisible("healing", tab == "healing")
    setSectionVisible("heal_friend", tab == "heal_friend")
    setSectionVisible("conditions", tab == "conditions")
    setSectionVisible("hunting", tab == "hunting")
    setSectionVisible("cavebot", tab == "cavebot")
    setSectionVisible("equipment", tab == "equipment")
    setSectionVisible("tools", tab == "tools")
    setSectionVisible("scripting", tab == "scripting")
    setSectionVisible("profile", tab == "profile")
    setSectionVisible("ui", tab == "ui")
    local targetingActive = tab == "hunting" and (Helper.active_hunting_tab == "targeting" or Helper.active_hunting_tab == "target_rules")
    local magicActive = tab == "hunting" and not targetingActive
    for _, nav in ipairs(Helper.sidebar_tabs or {}) do
        local active = tab == nav.target
        if nav.target == "hunting" then
            active = nav.subtab == "magic" and magicActive or nav.subtab ~= "magic" and targetingActive
        end
        setWidgetText(Helper.widgets[nav.key], (active and "> " or "  ") .. nav.label)
        styleUi("styleTabState", Helper.widgets[nav.key], active, UI_STYLE, AlignLeft)
        styleUi("styleTabRail", Helper.widgets[nav.key .. "_rail"], active, UI_STYLE)
    end
    switchHuntingSubtab(Helper.active_hunting_tab or "targeting")
    switchToolsSubtab(Helper.active_tools_tab or "helper")
    markUiPrefsDirty("active_tab")
end

function hideWindow()
    if Helper.window and Helper.window.hide then
        Helper.window:hide()
    end
end

function bindHelperHotkey(hotkey)
    local decision = moduleValue(externalHotkeys, "hotkeyBindingDecision", hotkey, Helper.bound_hotkey or HELPER_CONFIG.hotkey)
    if decision.allowed ~= true or decision.normalized == "" then
        return
    end
    local normalizedHotkey = decision.normalized
    if Helper.bound_hotkey and Helper.bound_hotkey ~= normalizedHotkey and g_keyboard and g_keyboard.unbindKeyDown then
        g_keyboard.unbindKeyDown(Helper.bound_hotkey)
    end
    Helper.bound_hotkey = normalizedHotkey
    HELPER_CONFIG.hotkey = normalizedHotkey
    if g_keyboard and g_keyboard.bindKeyDown then
        g_keyboard.bindKeyDown(normalizedHotkey, Helper.toggleWindow or toggleWindow)
    end
end

function updateAutoHideTimer()
    if Helper.auto_hide_event then
        removeEvent(Helper.auto_hide_event)
        Helper.auto_hide_event = nil
    end
    if not HELPER_CONFIG.auto_show_window and HELPER_CONFIG.auto_hide_ms and HELPER_CONFIG.auto_hide_ms > 0 then
        Helper.auto_hide_event = delay(function()
            Helper.auto_hide_event = nil
            hideWindow()
        end, HELPER_CONFIG.auto_hide_ms)
    end
end

function applyHudPrefs()
    HELPER_CONFIG.hud = HELPER_CONFIG.hud or {}
    if HELPER_CONFIG.hud.enabled then
        if not Helper.hud_label and g_ui and g_ui.createWidget then
            local root = rootWidget or nil
            local hudPos = moduleValue(externalHud, "position", HELPER_CONFIG.hud or {}) or {}
            local x, y = tonumber(hudPos.x) or 22, tonumber(hudPos.y) or 170
            local startText = moduleValue(externalHud, "startText")
            Helper.hud_label = createWidget("Label", root, "ctoaHelperHud", type(startText) == "string" and startText ~= "" and startText or "HUD module unavailable | starting", x, y, 210, 54)
            if Helper.hud_label and Helper.hud_label.setPhantom then
                Helper.hud_label:setPhantom(true)
            end
        end
        if Helper.hud_label then
            local hudPos = moduleValue(externalHud, "position", HELPER_CONFIG.hud or {}) or {}
            local x, y = tonumber(hudPos.x) or 22, tonumber(hudPos.y) or 170
            if Helper.hud_label.setPosition then
                Helper.hud_label:setPosition({x = x, y = y})
            elseif Helper.hud_label.move then
                Helper.hud_label:move(x, y)
            end
            showWidget(Helper.hud_label, true)
        end
    else
        if Helper.hud_label then
            showWidget(Helper.hud_label, false)
        end
    end
end

local buildUi

function rebuildUi()
    local wasVisible = Helper.window and Helper.window.isVisible and Helper.window:isVisible()
    local activeTab = Helper.active_tab or "healing"

    if Helper.window and Helper.window.destroy then
        Helper.window:destroy()
    end
    if Helper.hud_label and Helper.hud_label.destroy then
        Helper.hud_label:destroy()
    end

    Helper.window = nil
    Helper.hud_label = nil
    Helper.widgets = {}
    Helper.sections = {}

    applyUiPrefs()
    buildUi()
    bindHelperHotkey(HELPER_CONFIG.hotkey)
    applyHudPrefs()
    switchTab(activeTab)

            if Helper.window and not wasVisible and not HELPER_CONFIG.auto_show_window and Helper.window.hide then
                Helper.window:hide()
            end
end

buildUi = function()
    if not g_ui or not g_ui.createWidget then
        status("UI API unavailable; helper logic still active")
        return
    end

    local root = rootWidget or nil
    if root and root.getChildById then
        for _ = 1, 8 do
            local stale = root:getChildById("ctoaNativeHelperWindow")
            if not stale or stale == Helper.window then
                break
            end
            if stale.destroy then
                stale:destroy()
            else
                break
            end
        end
    end
    if HELPER_CONFIG.hud and HELPER_CONFIG.hud.enabled and not Helper.hud_label then
        local hudPos = moduleValue(externalHud, "position", HELPER_CONFIG.hud or {}) or {}
        local x, y = tonumber(hudPos.x) or 22, tonumber(hudPos.y) or 170
        local startText = moduleValue(externalHud, "startText")
        Helper.hud_label = createWidget("Label", root, "ctoaHelperHud", type(startText) == "string" and startText ~= "" and startText or "HUD module unavailable | starting", x, y, 210, 54)
        if Helper.hud_label and Helper.hud_label.setPhantom then
            Helper.hud_label:setPhantom(true)
        end
    end

    local window = createWidget("HeadlessWindow", root, "ctoaNativeHelperWindow", "", HELPER_CONFIG.window_x or 520, HELPER_CONFIG.window_y or 34, UI_LAYOUT.window_w, UI_LAYOUT.window_h)
    if not window then
        status("Could not create helper window")
        return
    end

    Helper.window = window
    applyWindowPlacement()
    styleUi("styleWindowRoot", window, UI_STYLE)

    local sx = UI_LAYOUT.sidebar_x
    local sw = UI_LAYOUT.sidebar_w
    local cx = UI_LAYOUT.content_x
    local cw = UI_LAYOUT.content_w
    local panel_x = cx + 8
    local panel_w = cw - 16
    local profile_gap = 12
    local profile_col_w = math.floor((panel_w - profile_gap) / 2)
    local profile_left_x = panel_x
    local profile_right_x = panel_x + profile_col_w + profile_gap
    local profile_block_w = panel_w
    local profile_status_w = panel_w - 116
    local profile_save_x = panel_x + panel_w - UI_LAYOUT.profile_save_w
    local body_y = UI_LAYOUT.content_body_y or 58
    local body_h = UI_LAYOUT.content_body_h or 252
    local operatorSummaries = moduleValue(externalOperatorSummary, "collect", OPERATOR_SUMMARY_BRIDGES, false) or {}
    Helper.cavebot_editor_bindings = moduleValue(externalRoute, "editorBindings", applyCavebotEditorAction) or {}
    local panel_renderer_base = {
        window = window, config = HELPER_CONFIG, helper = Helper, widgets = Helper.widgets, layout = UI_LAYOUT,
        panel_x = panel_x, panel_w = panel_w, body_y = body_y, body_h = body_h,
        create_widget = createWidget, style_action_button = function(widget, role, enabled) styleUi("styleActionButton", widget, role, enabled, UI_STYLE) end,
        add_to_section = addToSection,
        add_section_scaffold = addSectionScaffold,
        add_subtab_buttons = function(parent, provider, section, panelX, bodyY, panelW)
            local tabs = styleUi(provider, panelX, bodyY, panelW) or {}
            for _, tab in ipairs(tabs) do
                Helper.widgets[tab.key] = createWidget("Button", parent, tab.id, tab.text, tab.x, tab.y, tab.width, 20)
                addToSection(section, Helper.widgets[tab.key])
            end
            return tabs
        end,
        add_table_header = function(parent, id, leftText, rightText, x, y, width, section)
            local head = createWidget("Label", parent, id, "", x, y, width, 16)
            styleUi("styleTableHeader", head, UI_STYLE)
            addToSection(section, head)
            local leftWidth = math.floor(width * 0.56)
            local left = createWidget("Label", parent, id .. "Left", fitText(leftText, leftWidth, 1.02), x + 7, y + 1, leftWidth, 14)
            styleUi("styleTableHeaderLabel", left, nil, 0.96, UI_STYLE)
            addToSection(section, left)
            local right = createWidget("Label", parent, id .. "Right", fitText(rightText, 106, 0.98), x + width - 114, y + 1, 106, 14)
            styleUi("styleTableHeaderLabel", right, AlignRight, 0.94, UI_STYLE)
            addToSection(section, right)
            return head
        end,
        add_summary_strip = function(parent, id, text, x, y, width, section)
            local strip = createWidget("Label", parent, id, "", x, y, width, 20)
            styleUi("styleSummaryStrip", strip, UI_STYLE)
            addToSection(section, strip)
            local label = createWidget("Label", parent, id .. "Text", fitText(text, width - 16, 0.92), x + 8, y + 3, width - 16, 14)
            styleUi("styleSummaryStripLabel", label, UI_STYLE)
            addToSection(section, label)
            return label
        end,
        add_toggle_content_rows = function(parent, specs, x, width)
            for _, spec in ipairs(specs or {}) do
                addToggleSettingRow(parent, spec.id, spec.label, spec.getter, spec.setter, x, spec.y, width, spec.section)
            end
        end,
        add_profile_step_row = addProfileStepRow,
        add_section_band = function(parent, id, title, subtitle, x, y, width, section)
            local titleWidget = addLabel(parent, id .. "Title", fitText(title, math.floor(width * 0.45), 1.0), x, y, width, section)
            styleUi("styleLabel", titleWidget, "accent", UI_STYLE)
            styleUi("styleSectionBandTitle", titleWidget, UI_STYLE, AlignLeft)
            local subtitleWidget = addLabel(parent, id .. "Subtitle", fitText(subtitle, math.floor(width * 0.52), 0.92), x, y + 2, width, section)
            styleUi("styleLabel", subtitleWidget, "muted", UI_STYLE)
            styleUi("styleSectionBandSubtitle", subtitleWidget, UI_STYLE, AlignRight)
            local divider = createWidget("Label", parent, id .. "Divider", "", x, y + 20, width, 1)
            styleUi("styleSectionBandDivider", divider, UI_STYLE)
            addToSection(section, divider)
            return titleWidget, subtitleWidget
        end,
        add_footer_strip = function(parent, id, text, x, y, width, section)
            local strip = createWidget("Label", parent, id, "", x, y, width, 18)
            styleUi("styleFooterStrip", strip, UI_STYLE)
            addToSection(section, strip)
            local label = createWidget("Label", parent, id .. "Text", fitText(text, width - 14, 0.98), x + 7, y + 2, width - 14, 14)
            styleUi("styleFooterStripLabel", label, UI_STYLE)
            addToSection(section, label)
            return label
        end, add_profile_cycle_row = addProfileCycleRow, add_vector_step_row = addVectorStepRow,
        add_toggle_setting_row = addToggleSettingRow, add_setting_row = addSettingRow,
        add_priority_badge = function(parent, id, text, x, y, section, active)
            local badge = createWidget("Label", parent, id, tostring(text), x, y, 20, 18)
            styleUi("stylePriorityBadge", badge, active, UI_STYLE, AlignCenter)
            return addToSection(section, badge)
        end,
        bind_click = bindClick,
        spell_text = spellText, profile_number_text = tostring, percent_text = function(value) return "<= " .. tostring(value) .. "%" end, ms_text = function(value) return tostring(value) .. " ms" end
    }
    panel_renderer_base.add_table_headers = function(parent, specs)
        for _, spec in ipairs(specs or {}) do
            panel_renderer_base.add_table_header(parent, spec.id, spec.left, spec.right, spec.x, spec.y, spec.width, spec.section)
        end
    end
    local outerFrame = createWidget("Label", window, "ctoaOuterFrame", "", UI_LAYOUT.base_x, UI_LAYOUT.base_y, UI_LAYOUT.base_w, UI_LAYOUT.base_h)
    styleUi("styleWindowFrame", outerFrame, "outer", UI_STYLE)
    local sheetFrame = createWidget("Label", window, "ctoaSheetFrame", "", UI_LAYOUT.sheet_x, UI_LAYOUT.sheet_y, UI_LAYOUT.sheet_w, UI_LAYOUT.sheet_h)
    styleUi("styleWindowFrame", sheetFrame, "sheet", UI_STYLE)
    local titleBar = createWidget("Label", window, "ctoaWindowTitleBar", "", UI_LAYOUT.title_x, UI_LAYOUT.title_y, UI_LAYOUT.title_w, UI_LAYOUT.title_h)
    styleUi("styleWindowFrame", titleBar, "title", UI_STYLE)
    local titleLabel = createWidget("Label", window, "ctoaWindowTitleLabel", "CTOA Helper", UI_LAYOUT.title_x + 12, UI_LAYOUT.title_y + 2, 180, 14)
    styleUi("styleWindowTitleLabel", titleLabel, "title", UI_STYLE, AlignLeft, AlignRight)
    local titleState = createWidget("Label", window, "ctoaWindowTitleState", HELPER_VERSION .. " | " .. moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText), UI_LAYOUT.title_x + 204, UI_LAYOUT.title_y + 2, UI_LAYOUT.title_w - 216, 14)
    styleUi("styleWindowTitleLabel", titleState, "state", UI_STYLE, AlignLeft, AlignRight)
    Helper.widgets.title_state = titleState
    local innerTitle = createWidget("Label", window, "ctoaInnerTitleBar", "", UI_LAYOUT.inner_title_x, UI_LAYOUT.inner_title_y, UI_LAYOUT.inner_title_w, UI_LAYOUT.inner_title_h)
    styleUi("styleWindowFrame", innerTitle, "inner_title", UI_STYLE)
    local innerTitleText = createWidget("Label", window, "ctoaInnerTitleText", "Operator workspace", UI_LAYOUT.inner_title_x + 10, UI_LAYOUT.inner_title_y + 2, UI_LAYOUT.inner_title_w - 20, 14)
    styleUi("styleWindowTitleLabel", innerTitleText, "inner_title", UI_STYLE, AlignLeft, AlignRight)
    local panelTop = UI_LAYOUT.inner_title_y + UI_LAYOUT.inner_title_h + 10
    local panelHeight = UI_LAYOUT.sheet_y + UI_LAYOUT.sheet_h - panelTop - 12
    local sidebarBack = createWidget("Label", window, "ctoaSidebarBack", "", sx - 10, panelTop, sw + 20, panelHeight)
    styleUi("styleWindowFrame", sidebarBack, "sidebar", UI_STYLE)
    local contentBack = createWidget("Label", window, "ctoaContentBack", "", cx - 12, panelTop, cw + 24, panelHeight)
    styleUi("styleWindowFrame", contentBack, "content", UI_STYLE)
    local contentDivider = createWidget("Label", window, "ctoaContentDivider", "", cx - 18, panelTop + 2, 1, panelHeight - 4)
    styleUi("styleWindowFrame", contentDivider, "divider", UI_STYLE)
    local sideTitle = addLabel(window, "ctoaSideTitle", "Modules", sx, UI_LAYOUT.side_title_y, sw, nil)
    styleUi("styleLabel", sideTitle, "accent", UI_STYLE)
    styleUi("styleWindowTitleLabel", sideTitle, "side_title", UI_STYLE, AlignLeft, AlignRight)
    local sideSub = addLabel(window, "ctoaSideSub", "", sx, UI_LAYOUT.side_subtitle_y, sw, nil)
    styleUi("styleLabel", sideSub, "muted", UI_STYLE)
    styleUi("styleWindowTitleLabel", sideSub, "side_subtitle", UI_STYLE, AlignLeft, AlignRight)
    local sidebarTabs = styleUi("sidebarTabs", UI_LAYOUT) or {}
    Helper.sidebar_tabs = {}
    local visibleTabs = {}
    local smokeModuleId = tabModuleId and tabModuleId(Helper.smoke_tab, Helper.smoke_subtab) or nil
    for _, tab in ipairs(sidebarTabs) do
        local moduleId = tab.module_id or tabModuleId(tab.target, tab.subtab)
        if moduleValue(externalModules, "moduleTabVisible", moduleId, HELPER_CONFIG.modules, smokeModuleId, CORE_MODULE_TABS) then
            table.insert(visibleTabs, tab)
        end
    end
    local sidebarGeometry = styleUi("sidebarGeometry", UI_LAYOUT, visibleTabs) or {rows = {}}
    for index, tab in ipairs(visibleTabs) do
        local row = sidebarGeometry.rows[index] or {y = UI_LAYOUT.overview_tab_y + ((index - 1) * 20), height = 18}
        tab.label = string.gsub(tab.text or tab.target or "", "^%s+", "")
        Helper.widgets[tab.key] = createWidget("Button", window, tab.id, tab.text, sx + 4, row.y, sw - 4, row.height)
        Helper.widgets[tab.key .. "_rail"] = createWidget("Label", window, tab.id .. "Rail", "", sx, row.y, 2, row.height)
        table.insert(Helper.sidebar_tabs, tab)
    end
    if sidebarGeometry.utility_divider_y then
        local utilityDivider = createWidget("Label", window, "ctoaSidebarUtilityDivider", "", sx, sidebarGeometry.utility_divider_y, sw, 1)
        styleUi("styleWindowFrame", utilityDivider, "divider", UI_STYLE)
    end
    local sidebarStatusY = UI_LAYOUT.profile_caption_y - 6; local sidebarStatusH = (UI_LAYOUT.hint_y + 38) - sidebarStatusY
    local sidebarStatusFrame = createWidget("Label", window, "ctoaSidebarStatusFrame", "", sx - 2, sidebarStatusY, sw + 4, sidebarStatusH)
    styleUi("styleGroupedFrame", sidebarStatusFrame, UI_STYLE)
    local profileCaption = addLabel(window, "ctoaProfileCaption", "Profile", sx, UI_LAYOUT.profile_caption_y, sw, nil)
    styleUi("styleLabel", profileCaption, "muted", UI_STYLE)
    local profileNameCard = addLabel(window, "ctoaProfileName", moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText), sx, UI_LAYOUT.profile_card_y, sw, nil)
    styleUi("styleSidebarCard", profileNameCard, UI_STYLE)
    Helper.widgets.enabled = createWidget("Button", window, "ctoaHelperEnabled", HELPER_CONFIG.enabled and "ARMED" or "DISARMED", sx, UI_LAYOUT.enabled_y, sw, 20)
    setWidgetChecked(Helper.widgets.enabled, HELPER_CONFIG.enabled)
    styleUi("styleRuntimeBadge", Helper.widgets.enabled, HELPER_CONFIG.enabled, false, UI_STYLE, AlignCenter)
    if Helper.widgets.enabled then
        Helper.widgets.enabled.onClick = function() syncFromUi(not HELPER_CONFIG.enabled); return true end
    end
    Helper.status_label = createWidget("Label", window, "ctoaHelperStatus", "Status: OK", sx, UI_LAYOUT.status_y, sw, 20)
    styleUi("styleLabel", Helper.status_label, "status", UI_STYLE)
    local hintLabel = addLabel(window, "ctoaHint", "Look ID: " .. string.upper(tostring(Helper.vocation_id or "unknown")), sx, UI_LAYOUT.hint_y, sw, nil)
    styleUi("styleLabel", hintLabel, "muted", UI_STYLE)
    local buildLabel = addLabel(window, "ctoaSideBuild", "Build: local", sx, UI_LAYOUT.hint_y + 18, sw, nil)
    styleUi("styleLabel", buildLabel, "muted", UI_STYLE)
    bindClick(Helper.widgets.overview_tab, function() switchTab("overview") end)
    bindClick(Helper.widgets.healing_tab, function() switchTab("healing") end)
    bindClick(Helper.widgets.heal_friend_tab, function() switchTab("heal_friend") end)
    bindClick(Helper.widgets.conditions_tab, function() switchTab("conditions") end)
    bindClick(Helper.widgets.hunting_tab, function() Helper.active_hunting_tab = "targeting"; switchTab("hunting") end)
    bindClick(Helper.widgets.magic_tab, function() Helper.active_hunting_tab = "magic"; switchTab("hunting") end)
    bindClick(Helper.widgets.cavebot_tab, function() switchTab("cavebot") end)
    bindClick(Helper.widgets.equipment_tab, function() switchTab("equipment") end)
    bindClick(Helper.widgets.tools_tab, function() switchTab("tools") end)
    bindClick(Helper.widgets.scripting_tab, function() switchTab("scripting") end)
    bindClick(Helper.widgets.profile_tab, function() switchTab("profile") end)
    bindClick(Helper.widgets.ui_tab, function() switchTab("ui") end)

    styleUi("renderOverviewPanel", moduleValue(externalUi, "mergePanelRendererContext", {
        window = window, config = HELPER_CONFIG, helper = Helper, widgets = Helper.widgets, layout = UI_LAYOUT,
        panel_x = panel_x, panel_w = panel_w, body_y = body_y, body_h = UI_LAYOUT.content_body_h or 242,
        ui_style = UI_STYLE, align_center = AlignCenter,
        add_section_scaffold = addSectionScaffold, add_table_header = panel_renderer_base.add_table_header, create_widget = createWidget,
        style_ui = styleUi, add_to_section = addToSection, add_metric_card = addMetricCard, add_footer_strip = panel_renderer_base.add_footer_strip,
        fit_text = fitText, display_profile_name = function() return moduleValue(externalProfileSchema, "displayProfileName", Helper.profile_name, shortText) end
    }, {}))

    styleUi("renderHealingPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        healing_summary_text = operatorSummaries.healing, spell_choices = SPELL_CHOICES, hotkey_choices = HOTKEY_CHOICES
    }))
    styleUi("renderHealFriendPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        heal_friend_summary_text = operatorSummaries.heal_friend, sio_spell_choices = SIO_SPELL_CHOICES,
        heal_friend_priority_choices = HEAL_FRIEND_PRIORITY_CHOICES, heal_friend_priority_text = healFriendPriorityText
    }))
    styleUi("renderConditionsPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        conditions_summary_text = operatorSummaries.conditions
    }))

    local hunting_table_y = styleUi("subtabContentY", body_y) or (body_y + 26)
    styleUi("renderHuntingPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        content_y = hunting_table_y, switch_hunting_subtab = switchHuntingSubtab,
        targeting_summary_text = operatorSummaries.targeting, magic_summary_text = operatorSummaries.magic,
        profile_number_text = tostring, magic_priority_text = magicPriorityText,
        tool_range_choices = TOOL_RANGE_CHOICES, tool_timeout_choices = TOOL_TIMEOUT_CHOICES,
        magic_priority_choices = MAGIC_PRIORITY_CHOICES, hotkey_choices = HOTKEY_CHOICES,
        rune_name_choices = RUNE_NAME_CHOICES,
        ui_style = UI_STYLE, align_center = AlignCenter, targeting_module = externalTargeting,
        combat_runtime_module = externalCombatRuntime,
        mark_profile_dirty = markProfileDirty,
        format_target_name_list = function(key)
            return moduleValue(externalTargeting, "formatNameList", HELPER_CONFIG.tools[key] or {}) or ""
        end,
        update_target_name_list = function(key, text)
            local names, decision = moduleValue(externalTargeting, "updateNameList", HELPER_CONFIG.tools, key, text)
            if type(names) ~= "table" or type(decision) ~= "table" or decision.allowed ~= true then
                status("Target name policy blocked: " .. tostring(decision and decision.reason or "targeting module unavailable"))
                return false
            end
            markProfileDirty("target_name_policy:" .. tostring(key))
            return true
        end,
        magic_rule_state = function()
            local state = moduleValue(externalCombatRuntime, "rotationRuleState", HELPER_CONFIG.tools, Helper.magic_rule_index)
            if type(state) ~= "table" then
                return {index = 0, count = 0, rule = nil, summary = "editor unavailable"}
            end
            Helper.magic_rule_index = tonumber(state.index) or 0
            return state
        end,
        select_magic_rule = function(delta)
            local state = moduleValue(externalCombatRuntime, "rotationRuleState", HELPER_CONFIG.tools, Helper.magic_rule_index)
            if type(state) ~= "table" or tonumber(state.count) == nil or state.count < 1 then
                Helper.magic_rule_index = 0
                return false
            end
            Helper.magic_rule_index = math.max(1, math.min(state.count, (tonumber(state.index) or 1) + (tonumber(delta) or 0)))
            return true
        end,
        update_magic_rule = function(patch)
            local _, decision = moduleValue(externalCombatRuntime, "updateRotationRule", HELPER_CONFIG.tools, Helper.magic_rule_index, patch)
            if type(decision) ~= "table" or decision.allowed ~= true or decision.runtime_actions ~= false then
                status("Spell rule update blocked: " .. tostring(decision and decision.reason or "combat runtime editor unavailable"))
                return false
            end
            markProfileDirty("magic_rule_update")
            return true
        end,
        add_magic_rule = function()
            local index, decision = moduleValue(externalCombatRuntime, "addRotationRule", HELPER_CONFIG.tools, {
                enabled = false, words = "", use_mob_count = true, min_nearby = 1,
                max_nearby = 99, scan_range = 1, cooldown_ms = 2000, directional = false
            })
            if type(decision) ~= "table" or decision.allowed ~= true or decision.runtime_actions ~= false then
                status("Spell rule add blocked: " .. tostring(decision and decision.reason or "combat runtime editor unavailable"))
                return false
            end
            Helper.magic_rule_index = tonumber(index) or Helper.magic_rule_index
            markProfileDirty("magic_rule_add")
            return true
        end,
        remove_magic_rule = function()
            local index, decision = moduleValue(externalCombatRuntime, "removeRotationRule", HELPER_CONFIG.tools, Helper.magic_rule_index)
            if type(decision) ~= "table" or decision.allowed ~= true or decision.runtime_actions ~= false then
                status("Spell rule remove blocked: " .. tostring(decision and decision.reason or "combat runtime editor unavailable"))
                return false
            end
            Helper.magic_rule_index = tonumber(index) or 0
            markProfileDirty("magic_rule_remove")
            return true
        end,
        move_magic_rule = function(delta)
            local index, decision = moduleValue(externalCombatRuntime, "moveRotationRule", HELPER_CONFIG.tools, Helper.magic_rule_index, delta)
            if type(decision) ~= "table" or decision.allowed ~= true or decision.runtime_actions ~= false then
                status("Spell rule move blocked: " .. tostring(decision and decision.reason or "edge reached"))
                return false
            end
            Helper.magic_rule_index = tonumber(index) or Helper.magic_rule_index
            markProfileDirty("magic_rule_move")
            return true
        end
    }))

    styleUi("renderCavebotPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        create_widget = createWidget, style_action_button = function(widget, role, enabled) styleUi("styleActionButton", widget, role, enabled, UI_STYLE, AlignCenter) end, add_to_section = addToSection,
        profile_number_text = tostring,
        add_current_cavebot_waypoint = addCurrentCavebotWaypoint, delete_current_cavebot_waypoint = deleteCurrentCavebotWaypoint,
        move_current_cavebot_waypoint = Helper.cavebot_editor_bindings.move, select_cavebot_waypoint = Helper.cavebot_editor_bindings.select,
        clear_cavebot_waypoints = Helper.cavebot_editor_bindings.clear, test_cavebot_auto_walk = testCavebotAutoWalk
    }))

    styleUi("renderEquipmentPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        equipment_summary_text = operatorSummaries.equipment,
        equipment_family_rows = moduleValue(externalEquipmentFamilyRegistry, "uiRows", HELPER_CONFIG.equipment or {}, "ring") or {},
        set_equipment_family_enabled = function(key, value)
            return moduleValue(externalEquipmentFamilyRegistry, "setEnabled", HELPER_CONFIG.equipment or {}, key, value)
        end
    }))

    styleUi("renderToolsPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        content_y = hunting_table_y, switch_tools_subtab = switchToolsSubtab, tools_summary_text = operatorSummaries.tools,
        profile_number_text = tostring, profile_bool_text = profileBoolText, timer_interval_choices = TIMER_INTERVAL_CHOICES,
        timer_interval_text = function(value) return tostring(math.floor(value / 1000)) .. "s" end,
        feature_flags_text = function()
            local flags = HELPER_CONFIG.tools and HELPER_CONFIG.tools.feature_flags or {}
            local text = moduleValue(externalDiagnostics, "featureFlagsText", flags)
            return type(text) == "string" and text ~= "" and text or "Diagnostics module unavailable | flags pending"
        end,
        diagnostics_buffer_text = function()
            local limit = HELPER_CONFIG.tools and HELPER_CONFIG.tools.diagnostics_export_limit or 20
            local text = moduleValue(externalDiagnostics, "bufferText", Helper.diagnostics_buffer, limit)
            return type(text) == "string" and text ~= "" and text or "Diagnostics module unavailable | export gated"
        end, short_text = shortText,
        apply_hud_prefs = applyHudPrefs, refresh_api_snapshot_ui = diagnosticsController.refresh, mark_ui_prefs_dirty = markUiPrefsDirty
    }))

    styleUi("renderScriptingPanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        scripting_summary_text = operatorSummaries.scripting,
        build_scripting_policy_snapshot = function()
            local scripting = HELPER_CONFIG.scripting or {}
            local text = moduleValue(externalScripting, "policySnapshot", scripting)
            if type(text) == "string" and text ~= "" then
                return text
            end
            scripting.last_status = "scripting module unavailable"
            return scripting.last_status
        end
    }))

    styleUi("renderProfilePanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        profile_left_x = profile_left_x, profile_right_x = profile_right_x, profile_col_w = profile_col_w,
        profile_block_w = profile_block_w, profile_status_w = profile_status_w, profile_save_x = profile_save_x,
        add_profile_rotation_row = addProfileRotationRow,
        add_muted_label = function(parent, id, text, x, y, width, section)
            local widget = addLabel(parent, id, text, x, y, width, section)
            styleUi("styleLabel", widget, "muted", UI_STYLE)
            return widget
        end,
        create_widget = createWidget,
        style_action_button = function(widget, role, enabled) styleUi("styleActionButton", widget, role, enabled, UI_STYLE, AlignCenter) end, add_to_section = addToSection, flush_profile_save = flushProfileSave,
        profile_summary_text = operatorSummaries.profile, rotation_summary_text = rotationSummaryText,
        profile_number_text = tostring, profile_bool_text = profileBoolText,
        spell_text = spellText, potion_text = potionText, rune_text = runeText,
        spell_choices = SPELL_CHOICES, critical_choices = CRITICAL_CHOICES, hotkey_choices = HOTKEY_CHOICES,
        potion_name_choices = POTION_NAME_CHOICES, rune_name_choices = RUNE_NAME_CHOICES,
        module_visible = function(moduleId)
            return moduleValue(externalModules, "moduleTabVisible", moduleId, HELPER_CONFIG.modules, smokeModuleId, CORE_MODULE_TABS)
        end,
        set_module_visible = setModuleTabVisible
    }))

    styleUi("renderEnginePanel", moduleValue(externalUi, "mergePanelRendererContext", panel_renderer_base, {
        profile_left_x = profile_left_x, profile_right_x = profile_right_x, profile_col_w = profile_col_w,
        ui_summary_text = operatorSummaries.ui, hotkey_display_text = type(externalHotkeys) == "table" and type(externalHotkeys.display) == "function" and externalHotkeys.display or tostring, ui_hotkey_choices = UI_HOTKEY_CHOICES,
        apply_hotkey_choice = function(value) local decision = moduleValue(externalHotkeys, "hotkeyBindingDecision", value, HELPER_CONFIG.hotkey, UI_HOTKEY_CHOICES); if decision.allowed == true and decision.normalized ~= "" then HELPER_CONFIG.hotkey = decision.normalized; bindHelperHotkey(decision.normalized) end; updateAutoHideTimer() end,
        auto_hide_text = function(value) return value == 0 and "OFF" or tostring(value) .. " ms" end, update_auto_hide_timer = updateAutoHideTimer, apply_hud_prefs = applyHudPrefs,
        set_theme_preset = setThemePreset, theme_presets = THEME_PRESETS, theme_preset_text = themePresetText, set_compact_mode = setCompactMode, apply_window_placement = applyWindowPlacement,
        profile_number_text = tostring, profile_bool_text = profileBoolText, mark_ui_prefs_dirty = markUiPrefsDirty
    }))

    Helper.widgets.hide_button = createWidget("Button", window, "ctoaHideHelper", "Close", UI_LAYOUT.close_x, UI_LAYOUT.close_y, UI_LAYOUT.close_w, UI_LAYOUT.close_h)
    styleUi("styleActionButton", Helper.widgets.hide_button, "neutral", true, UI_STYLE, AlignCenter)
    bindClick(Helper.widgets.hide_button, hideWindow)
    refreshOperatorSummaries()
    switchTab(Helper.active_tab or "overview")

    if window.show and HELPER_CONFIG.auto_show_window ~= false then
        window:show()
        window:raise()
        window:focus()
    elseif window.hide then
        window:hide()
    end
end

function toggleWindow()
    if not Helper.window then
        buildUi()
        return
    end

    if Helper.window.isVisible and Helper.window:isVisible() then
        Helper.window:hide()
    elseif Helper.window.show then
        Helper.window:show()
        Helper.window:raise()
        Helper.window:focus()
    end
end

function init()
    if Helper.think_event then
        return
    end

    Helper.runtime_session_armed = false
    moduleValue(externalRecoveryBridge, "disarm", "helper_init")
    moduleValue(externalConditionsExecuteOnce, "reset")
    moduleValue(externalEquipmentExecuteOnce, "reset")
    moduleValue(externalHealFriendExecuteOnce, "reset")
    loadProfile()
    applySafeBootRuntimeGuard()
    loadUiPrefs()
    applyUiPrefs()
    buildUi()
    bindHelperHotkey(HELPER_CONFIG.hotkey)
    updateAutoHideTimer()
    applyHudPrefs()
    moduleValue(externalClientReporter, "report", Helper, HELPER_CONFIG, HELPER_VERSION, externalRuntimeCore, externalObservationAdapter, helperNowMs(), true, true)
    if Helper.window and Helper.window.show and HELPER_CONFIG.auto_show_window ~= false then
        Helper.window:show()
        Helper.window:raise()
        Helper.window:focus()
    end
    if Helper.smoke_tab then
        delay(function()
            if Helper.showTab then
                Helper.showTab(Helper.smoke_tab)
            else
                switchTab(Helper.smoke_tab)
            end
            if Helper.smoke_tab == "hunting" and Helper.smoke_subtab == "magic" then
                switchHuntingSubtab("magic")
            elseif Helper.smoke_tab == "tools" and Helper.smoke_subtab then
                switchToolsSubtab(Helper.smoke_subtab)
            end
            delay(function()
                if Helper.window and Helper.window.show then
                    Helper.window:show()
                    Helper.window:raise()
                    Helper.window:focus()
                end
                local smokeLabel = tostring(Helper.smoke_tab)
                if Helper.smoke_subtab and Helper.smoke_subtab ~= "" then
                    smokeLabel = smokeLabel .. "/" .. tostring(Helper.smoke_subtab)
                end
                status("Smoke tab visible: " .. smokeLabel)
            end, 900)
        end, 250)
    end
    Helper.think_event = cycleEvent(onThink, HELPER_CONFIG.tick_ms)
    if HELPER_CONFIG.tools and HELPER_CONFIG.tools.api_probe_enabled then
        delay(function()
            diagnosticsController.runApiProbe("startup")
        end, 900)
    end
    if HELPER_CONFIG.tools and HELPER_CONFIG.tools.cavebot_api_probe_enabled then
        delay(function()
            runMovementApiProbe("startup")
        end, 1200)
    end
    if HELPER_CONFIG.tools and HELPER_CONFIG.tools.magic_api_probe_enabled then
        delay(function()
            runMagicApiProbe("startup")
        end, 1800)
    end

    status(HELPER_CONFIG.enabled and "Enabled" or "Safe boot: runtime disabled")
    status("Initialized successfully " .. HELPER_VERSION)
end

function terminate()
    HELPER_CONFIG.enabled = false
    Helper.runtime_session_armed = false
    moduleValue(externalRecoveryBridge, "disarm", "helper_terminate")
    moduleValue(externalConditionsExecuteOnce, "kill", "helper_terminate")
    moduleValue(externalEquipmentExecuteOnce, "kill", "helper_terminate")
    moduleValue(externalHealFriendExecuteOnce, "kill", "helper_terminate")
    moduleValue(externalClientReporter, "report", Helper, HELPER_CONFIG, HELPER_VERSION, externalRuntimeCore, externalObservationAdapter, helperNowMs(), true, false)
    if Helper.think_event then
        removeEvent(Helper.think_event)
        Helper.think_event = nil
    end
    if Helper.auto_hide_event then
        removeEvent(Helper.auto_hide_event)
        Helper.auto_hide_event = nil
    end
    if Helper.ui_save_event then
        removeEvent(Helper.ui_save_event)
        Helper.ui_save_event = nil
    end
    if Helper.window and Helper.window.destroy then
        Helper.window:destroy()
        Helper.window = nil
    end
    if Helper.hud_label and Helper.hud_label.destroy then
        Helper.hud_label:destroy()
        Helper.hud_label = nil
    end
    if Helper.bound_hotkey and g_keyboard and g_keyboard.unbindKeyDown then
        g_keyboard.unbindKeyDown(Helper.bound_hotkey)
    end
    status("Terminated")
end

Helper.init = init
Helper.terminate = terminate
Helper.toggleWindow = toggleWindow
Helper.handleGameStart = function()
    delay(function()
        local player = g_game and g_game.getLocalPlayer and g_game.getLocalPlayer() or nil
        local detected = moduleValue(externalVocationProfiles, "detect", player)
        if detected and detected ~= Helper.vocation_id then
            if loadProfile(detected) then
                applySafeBootRuntimeGuard()
                applyUiPrefs()
                rebuildUi()
                status("Vocation profile selected: " .. tostring(moduleValue(externalVocationProfiles, "label", detected) or detected))
            else
                status("Vocation profile switch blocked: " .. tostring(detected))
            end
        end
        if Helper.window and Helper.window.show and HELPER_CONFIG.auto_show_window ~= false then
            Helper.window:show()
            Helper.window:raise()
        end
        moduleValue(externalClientReporter, "report", Helper, HELPER_CONFIG, HELPER_VERSION, externalRuntimeCore, externalObservationAdapter, helperNowMs(), true, true)
    end, 250)
end
Helper.showTab = function(tab)
    if not Helper.window then
        buildUi()
    end
    if Helper.window and Helper.window.show then
        Helper.window:show()
        Helper.window:raise()
        Helper.window:focus()
    end
    switchTab(tab or "overview")
end
Helper.config = HELPER_CONFIG
Helper.version = HELPER_VERSION
Helper.onThink = function(self)
    onThink()
end
Helper.reloadProfile = function()
    HELPER_CONFIG.enabled = false
    Helper.runtime_session_armed = false
    moduleValue(externalRecoveryBridge, "disarm", "profile_reload")
    loadProfile()
    applySafeBootRuntimeGuard()
    setWidgetChecked(Helper.widgets.enabled, false)
    status("Profile reloaded")
    return false
end
Helper.runMovementApiProbe = function()
    return runMovementApiProbe("manual")
end
Helper.runMagicApiProbe = function()
    return runMagicApiProbe("manual")
end
Helper.runApiProbe = function()
    return diagnosticsController.runApiProbe("manual")
end
Helper.exportDiagnostics = function()
    return diagnosticsController.export("manual")
end
Helper.setEnabled = function(enabled)
    local requested = enabled == true or enabled == "true" or enabled == 1
    if not requested then
        HELPER_CONFIG.enabled = false
        Helper.runtime_session_armed = false
        moduleValue(externalRecoveryBridge, "disarm", "external_disable")
        setWidgetChecked(Helper.widgets.enabled, false)
        status("Disabled")
        return true
    end
    local blocked = runtimeArmingBlockedReason()
    if blocked then
        HELPER_CONFIG.enabled = false
        setWidgetChecked(Helper.widgets.enabled, false)
        status("Runtime arm blocked: " .. blocked)
        return false
    end
    HELPER_CONFIG.enabled = true
    setWidgetChecked(Helper.widgets.enabled, HELPER_CONFIG.enabled)
    status("Enabled")
    return true
end
Helper.decision_pipeline_queue = Helper.decision_pipeline_queue or {}
Helper.decision_pipeline_result = Helper.decision_pipeline_result or nil
Helper.evaluateDecisionPipeline = function(entries, state)
    local pipelineState = {}
    for key, value in pairs(state or {}) do
        pipelineState[key] = value
    end
    pipelineState.queue = Helper.decision_pipeline_queue
    local result = moduleValue(externalDecisionPipeline, "evaluate", entries or {}, pipelineState)
    if type(result) ~= "table" then
        return nil
    end
    Helper.decision_pipeline_result = result
    Helper.decision_pipeline_updated_at_ms = tonumber(pipelineState.now_ms) or helperNowMs()
    if type(result.queue) == "table" then
        Helper.decision_pipeline_queue = result.queue
    end
    return result
end

_G.CTOA_Helper = Helper

function ensureCTOAManager()
    if not _G.CTOA_Manager then
        local manager = {
            modules = {}
        }
        function manager:registerModule(name, module)
            self.modules[name] = module
            return true
        end
        _G.CTOA_Manager = manager
    elseif type(_G.CTOA_Manager.registerModule) ~= "function" then
        function _G.CTOA_Manager:registerModule(name, module)
            self.modules = self.modules or {}
            self.modules[name] = module
            return true
        end
    end
    return _G.CTOA_Manager
end

local CTOA_Manager = ensureCTOAManager()
pcall(function()
    CTOA_Manager:registerModule("helper", {
        enabled = Helper.config.enabled,
        onThink = function() Helper:onThink() end,
        evaluateDecisionPipeline = function(entries, state)
            return Helper.evaluateDecisionPipeline(entries, state)
        end
    })
end)

init()
