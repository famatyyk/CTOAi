-- ctoa_helper_ui_composition.lua [CTOA OTClient Native]
-- Declarative tab, section, and action metadata. No profile mutation or gameplay callbacks.

local Composition = rawget(_G, "CTOA_HELPER_UI_COMPOSITION") or {}

function Composition.sidebarTabs(layout)
    layout = layout or {}
    return {
        {key = "overview_tab", id = "ctoaOverviewTab", text = "  Overview", y = layout.overview_tab_y, target = "overview"},
        {key = "healing_tab", id = "ctoaHealingTab", text = "  Healing", y = layout.healing_tab_y, target = "healing"},
        {key = "heal_friend_tab", id = "ctoaHealFriendTab", text = "  Heal Friend", y = layout.heal_friend_tab_y, target = "heal_friend"},
        {key = "conditions_tab", id = "ctoaConditionsTab", text = "  Conditions", y = layout.conditions_tab_y, target = "conditions"},
        {key = "hunting_tab", id = "ctoaHuntingTab", text = "  Targeting", y = layout.hunting_tab_y, target = "hunting", subtab = "targeting"},
        {key = "magic_tab", id = "ctoaMagicTab", text = "  Magic Shooter", y = layout.magic_tab_y, target = "hunting", subtab = "magic"},
        {key = "cavebot_tab", id = "ctoaCavebotTab", text = "  CaveBot", y = layout.cavebot_tab_y, target = "cavebot"},
        {key = "equipment_tab", id = "ctoaEquipmentTab", text = "  Equipment", y = layout.equipment_tab_y, target = "equipment"},
        {key = "tools_tab", id = "ctoaToolsTab", text = "  Helper", y = layout.tools_tab_y, target = "tools"},
        {key = "scripting_tab", id = "ctoaScriptingTab", text = "  Scripting", y = layout.scripting_tab_y, target = "scripting"},
        {key = "ui_tab", id = "ctoaUiTab", text = "  Settings", y = layout.ui_tab_y, target = "ui"},
        {key = "profile_tab", id = "ctoaProfileTab", text = "  Profile", y = layout.profile_tab_y, target = "profile"},
    }
end

function Composition.sidebarGeometry(layout, visibleTabs)
    layout = layout or {}
    visibleTabs = visibleTabs or {}
    local count = #visibleTabs
    local dense = count > 10
    local rowHeight = dense and 18 or 21
    local gap = dense and 1 or 2
    local step = rowHeight + gap
    local top = layout.overview_tab_y or 120
    local rows = {}
    local utilityIndex = nil
    for index, tab in ipairs(visibleTabs) do
        if not utilityIndex and (tab.target == "ui" or tab.target == "profile") then
            utilityIndex = index
        end
        rows[index] = {y = top + ((index - 1) * step), height = rowHeight, dense = dense}
    end
    return {
        count = count, dense = dense, mode = dense and "dense_overflow" or "standard",
        row_height = rowHeight, gap = gap, step = step, rows = rows,
        utility_index = utilityIndex,
        utility_divider_y = utilityIndex and (rows[utilityIndex].y - math.max(1, gap)) or nil,
    }
end

function Composition.huntingSubtabs(panelX, bodyY, panelW)
    local gap = 4
    local tabW = math.floor((panelW - (gap * 4)) / 5)
    return {
        {key = "hunting_targeting_tab", id = "ctoaHuntingTargetingTab", text = "Targeting", x = panelX, y = bodyY, width = tabW, target = "targeting"},
        {key = "hunting_target_rules_tab", id = "ctoaHuntingTargetRulesTab", text = "Target Rules", x = panelX + tabW + gap, y = bodyY, width = tabW, target = "target_rules"},
        {key = "hunting_magic_tab", id = "ctoaHuntingMagicTab", text = "Spell Rules", x = panelX + ((tabW + gap) * 2), y = bodyY, width = tabW, target = "magic"},
        {key = "hunting_actions_tab", id = "ctoaHuntingActionsTab", text = "Actions", x = panelX + ((tabW + gap) * 3), y = bodyY, width = tabW, target = "actions"},
        {key = "hunting_magic_runtime_tab", id = "ctoaHuntingMagicRuntimeTab", text = "Runtime", x = panelX + ((tabW + gap) * 4), y = bodyY, width = panelW - ((tabW + gap) * 4), target = "magic_runtime"},
    }
end

function Composition.subtabContentY(bodyY)
    return bodyY + 26
end

function Composition.toolsSubtabs(panelX, bodyY, panelW)
    local tabW = math.floor((panelW - 12) / 4)
    local gap = 4
    return {
        {key = "tools_helper_tab", id = "ctoaToolsHelperTab", text = "Helper", x = panelX, y = bodyY, width = tabW, target = "helper"},
        {key = "tools_pvp_tab", id = "ctoaToolsPvpTab", text = "PvP", x = panelX + tabW + gap, y = bodyY, width = tabW, target = "pvp"},
        {key = "tools_timer_tab", id = "ctoaToolsTimerTab", text = "Timer", x = panelX + (tabW + gap) * 2, y = bodyY, width = tabW, target = "timer"},
        {key = "tools_diag_tab", id = "ctoaToolsDiagTab", text = "Diag", x = panelX + (tabW + gap) * 3, y = bodyY, width = tabW, target = "diag"},
    }
end

function Composition.toolsTableHeaders(panelX, contentY, panelW)
    return {
        {id = "ctoaToolsPvpHead", left = "PvP", right = "Value", x = panelX, y = contentY, width = panelW, section = "tools_pvp"},
        {id = "ctoaToolsTimerHead", left = "Timer", right = "Value", x = panelX, y = contentY, width = panelW, section = "tools_timer"},
        {id = "ctoaToolsDiagHead", left = "Diagnostics", right = "Snapshot", x = panelX, y = contentY, width = panelW, section = "tools_diag"},
    }
end

function Composition.cavebotDelayChoices()
    return {600, 900, 1200, 1600, 2200}
end

function Composition.cavebotReachChoices()
    return {0, 1, 2, 3}
end

function Composition.msText(value)
    return tostring(value) .. " ms"
end

function Composition.cavebotActionSpecs(panelX, panelW, layout, callbacks)
    layout = layout or {}
    callbacks = callbacks or {}
    local actionW = math.floor((panelW - 18) / 4)
    local actionY1 = layout.row_7_y + 28
    local actionY2 = layout.row_7_y + 52
    return actionW, {
        {key = "cavebot_add", id = "ctoaCavebotAdd", text = "Add", x = panelX, y = actionY1, role = "primary", callback = callbacks.add},
        {key = "cavebot_delete", id = "ctoaCavebotDelete", text = "Del", x = panelX + actionW + 6, y = actionY1, role = "destructive", callback = callbacks.delete},
        {key = "cavebot_up", id = "ctoaCavebotUp", text = "Up", x = panelX + (actionW + 6) * 2, y = actionY1, role = "secondary", callback = callbacks.up},
        {key = "cavebot_down", id = "ctoaCavebotDown", text = "Down", x = panelX + (actionW + 6) * 3, y = actionY1, role = "secondary", callback = callbacks.down},
        {key = "cavebot_prev", id = "ctoaCavebotPrev", text = "Prev", x = panelX, y = actionY2, role = "neutral", callback = callbacks.prev},
        {key = "cavebot_next", id = "ctoaCavebotNext", text = "Next", x = panelX + actionW + 6, y = actionY2, role = "neutral", callback = callbacks.next},
        {key = "cavebot_clear", id = "ctoaCavebotClear", text = "Clear", x = panelX + (actionW + 6) * 2, y = actionY2, role = "destructive", callback = callbacks.clear},
        {key = "cavebot_test_walk", id = "ctoaCavebotTestWalk", text = "Test", x = panelX + (actionW + 6) * 3, y = actionY2, role = "secondary", callback = callbacks.test_walk},
    }
end

function Composition.contract()
    return {
        mode = "passive",
        owns_tab_specs = true,
        owns_section_specs = true,
        owns_action_metadata = true,
        mutates_profiles = false,
        runtime_actions = false,
        dispatch_allowed = false,
    }
end

_G.CTOA_HELPER_UI_COMPOSITION = Composition
return Composition
