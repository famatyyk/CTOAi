-- ctoa_helper_ui_rule_editors.lua [CTOA OTClient Native]
-- Passive Target, Spell, and Combat Action editor presentation with injected callbacks.

local RuleEditors = rawget(_G, "CTOA_HELPER_UI_RULE_EDITORS") or {}

function RuleEditors.addRuleEditorChrome(ui, ctx, window, spec)
    spec = spec or {}
    local add = spec.add
    if type(add) ~= "function" then
        return {}
    end
    local panelX = tonumber(spec.panel_x) or 0
    local panelW = tonumber(spec.panel_w) or 0
    local rowY = tonumber(spec.row_y) or 0
    local selector = add("Label", spec.selector_id, spec.empty_text or "0/0 no rules", panelX + 42, rowY + 3, panelW - 84, 16)
    ui.styleLabel(selector, "accent", ctx.ui_style, ctx.align_center)
    local previous = add("Button", spec.previous_id, "<", panelX, rowY, 34, 22)
    local nextRule = add("Button", spec.next_id, ">", panelX + panelW - 34, rowY, 34, 22)
    ui.styleMiniButton(previous, ctx.ui_style, ctx.align_center)
    ui.styleMiniButton(nextRule, ctx.ui_style, ctx.align_center)
    ctx.bind_click(previous, function()
        if type(spec.on_previous) == "function" then spec.on_previous() end
    end)
    ctx.bind_click(nextRule, function()
        if type(spec.on_next) == "function" then spec.on_next() end
    end)

    local actionButtons = {}
    local actions = spec.actions or {}
    local actionGap = 4
    local actionW = #actions > 0 and math.floor((panelW - (actionGap * (#actions - 1))) / #actions) or panelW
    for index, action in ipairs(actions) do
        local button = add("Button", action.id, action.text, panelX + ((index - 1) * (actionW + actionGap)), spec.action_y, actionW, 22)
        ctx.style_action_button(button, action.role or "neutral", true)
        ctx.bind_click(button, function()
            if type(action.callback) == "function" then action.callback() end
        end)
        actionButtons[action.id] = button
    end
    return {selector = selector, previous = previous, next_rule = nextRule, actions = actionButtons}
end

function RuleEditors.addTargetRuleEditor(ui, ctx, window, tools, panelX, panelW, layout)
    local section = "hunting_target_rules"
    local widgets = ctx.widgets
    local targeting = ctx.targeting_module or {}
    local selectedIndex = 1
    local loading = false
    local function add(kind, id, text, x, y, width, height)
        local widget = ctx.create_widget(kind, window, id, text, x, y, width, height)
        ctx.add_to_section(section, widget)
        return widget
    end
    local function call(name, ...)
        if type(targeting[name]) ~= "function" then return nil, {allowed = false, reason = "targeting_module_unavailable"} end
        local ok, value, decision = pcall(targeting[name], ...)
        if not ok then return nil, {allowed = false, reason = "target_rule_editor_error"} end
        return value, decision
    end
    local function state()
        local value = call("targetRuleState", tools, selectedIndex)
        if type(value) ~= "table" then return {index = 0, count = 0, rule = nil, summary = "editor unavailable"} end
        selectedIndex = tonumber(value.index) or 0
        return value
    end
    local function mutate(name, ...)
        local value, decision = call(name, tools, ...)
        if type(decision) ~= "table" or decision.allowed ~= true or decision.runtime_actions ~= false then return false, value end
        if type(ctx.mark_profile_dirty) == "function" then ctx.mark_profile_dirty("target_rule_editor") end
        return true, value
    end

    local chrome = RuleEditors.addRuleEditorChrome(ui, ctx, window, {
        add = add,
        panel_x = panelX,
        panel_w = panelW,
        row_y = layout.row_2_y,
        action_y = layout.row_7_y + 52,
        selector_id = "ctoaTargetRuleEditor",
        previous_id = "ctoaTargetRulePrev",
        next_id = "ctoaTargetRuleNext",
        empty_text = "0/0 no target rules",
        on_previous = function()
            local current = state()
            selectedIndex = ui.ruleEditorNavigation(current.count, current.index, -1).index
            widgets.target_rule_refresh()
        end,
        on_next = function()
            local current = state()
            selectedIndex = ui.ruleEditorNavigation(current.count, current.index, 1).index
            widgets.target_rule_refresh()
        end,
        actions = {
            {id = "ctoaTargetRuleAdd", text = "+ ADD", role = "primary", callback = function()
                local ok, value = mutate("addTargetRule", {enabled = false, name_pattern = ""})
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.target_rule_refresh()
            end},
            {id = "ctoaTargetRuleRemove", text = "REMOVE", role = "danger", callback = function()
                local ok, value = mutate("removeTargetRule", selectedIndex)
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.target_rule_refresh()
            end},
            {id = "ctoaTargetRuleUp", text = "UP", callback = function()
                local ok, value = mutate("moveTargetRule", selectedIndex, -1)
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.target_rule_refresh()
            end},
            {id = "ctoaTargetRuleDown", text = "DOWN", callback = function()
                local ok, value = mutate("moveTargetRule", selectedIndex, 1)
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.target_rule_refresh()
            end},
        },
    })
    local selector = chrome.selector

    local nameLabel = add("Label", "ctoaTargetRuleNameLabel", "Name / blank = any", panelX, layout.row_3_y + 3, 126, 18)
    ui.styleLabel(nameLabel, "muted", ctx.ui_style)
    local nameEdit = add("TextEdit", "ctoaTargetRuleName", "", panelX + 132, layout.row_3_y, panelW - 132, 22)
    ui.styleTextEdit(nameEdit, ctx.ui_style)
    if nameEdit and nameEdit.setMaxLength then pcall(function() nameEdit:setMaxLength(64) end) end

    local values = {}
    local function addPair(id, label, leftKey, rightKey, y, suffix)
        local labelWidget = add("Label", id .. "Label", label, panelX, y + 3, 98, 18)
        ui.styleLabel(labelWidget, "muted", ctx.ui_style)
        local function group(key, x)
            local minus = add("Button", id .. key .. "Minus", "-", x, y, 24, 22)
            local value = add("Label", id .. key .. "Value", "0", x + 26, y + 3, 48, 16)
            local plus = add("Button", id .. key .. "Plus", "+", x + 76, y, 24, 22)
            ui.styleMiniButton(minus, ctx.ui_style, ctx.align_center)
            ui.styleLabel(value, "default", ctx.ui_style, ctx.align_center)
            ui.styleMiniButton(plus, ctx.ui_style, ctx.align_center)
            values[key] = {widget = value, suffix = suffix or ""}
            local function change(delta)
                local rule = state().rule or {}
                mutate("updateTargetRule", selectedIndex, {[key] = (tonumber(rule[key]) or 0) + delta})
                widgets.target_rule_refresh()
            end
            ctx.bind_click(minus, function() change(-1) end)
            ctx.bind_click(plus, function() change(1) end)
        end
        group(leftKey, panelX + 104)
        group(rightKey, panelX + panelW - 100)
    end
    addPair("ctoaTargetRuleHp", "HP min / max", "min_hp", "max_hp", layout.row_4_y, "%")
    addPair("ctoaTargetRuleDistance", "Dist min / max", "min_distance", "max_distance", layout.row_5_y, "")
    addPair("ctoaTargetRuleCount", "Mobs min / max", "min_count", "max_count", layout.row_6_y, "")

    local priorityLabel = add("Label", "ctoaTargetRulePriorityLabel", "Priority", panelX, layout.row_7_y + 3, 78, 18)
    ui.styleLabel(priorityLabel, "muted", ctx.ui_style)
    local priorityMinus = add("Button", "ctoaTargetRulePriorityMinus", "-", panelX + 82, layout.row_7_y, 24, 22)
    local priorityValue = add("Label", "ctoaTargetRulePriorityValue", "50", panelX + 108, layout.row_7_y + 3, 48, 16)
    local priorityPlus = add("Button", "ctoaTargetRulePriorityPlus", "+", panelX + 158, layout.row_7_y, 24, 22)
    local chaseButton = add("Button", "ctoaTargetRuleChase", "Chase inherit", panelX + 190, layout.row_7_y, panelW - 190, 22)
    ui.styleMiniButton(priorityMinus, ctx.ui_style, ctx.align_center)
    ui.styleLabel(priorityValue, "default", ctx.ui_style, ctx.align_center)
    ui.styleMiniButton(priorityPlus, ctx.ui_style, ctx.align_center)
    ui.styleToggleButton(chaseButton, false, ctx.ui_style, ctx.align_center)
    local enabledButton = add("Button", "ctoaTargetRuleEnabled", "Enabled OFF", panelX, layout.row_7_y + 26, panelW, 22)

    widgets.target_rule_refresh = function()
        local current = state()
        local rule = current.rule or {}
        loading = true
        ui.setWidgetText(selector, current.summary or "0/0 no target rules")
        ui.setWidgetText(nameEdit, rule.name_pattern or "")
        loading = false
        for key, item in pairs(values) do ui.setWidgetText(item.widget, tostring(rule[key] or 0) .. item.suffix) end
        ui.setWidgetText(priorityValue, tostring(rule.priority or 0))
        ui.setWidgetText(chaseButton, "Chase " .. tostring(rule.chase_policy or "inherit"))
        ui.styleToggleButton(chaseButton, rule.chase_policy ~= "inherit", ctx.ui_style, ctx.align_center)
        ui.setWidgetText(enabledButton, "Enabled " .. (rule.enabled == true and "ON" or "OFF"))
        ui.styleToggleButton(enabledButton, rule.enabled == true, ctx.ui_style, ctx.align_center)
    end
    ctx.bind_click(priorityMinus, function() local rule = state().rule or {}; mutate("updateTargetRule", selectedIndex, {priority = (rule.priority or 50) - 1}); widgets.target_rule_refresh() end)
    ctx.bind_click(priorityPlus, function() local rule = state().rule or {}; mutate("updateTargetRule", selectedIndex, {priority = (rule.priority or 50) + 1}); widgets.target_rule_refresh() end)
    ctx.bind_click(chaseButton, function()
        local current = tostring((state().rule or {}).chase_policy or "inherit")
        local nextValue = current == "inherit" and "follow" or (current == "follow" and "stand" or "inherit")
        mutate("updateTargetRule", selectedIndex, {chase_policy = nextValue}); widgets.target_rule_refresh()
    end)
    ctx.bind_click(enabledButton, function() local rule = state().rule or {}; mutate("updateTargetRule", selectedIndex, {enabled = rule.enabled ~= true}); widgets.target_rule_refresh() end)
    if nameEdit then nameEdit.onTextChange = function(_, text) if not loading then mutate("updateTargetRule", selectedIndex, {name_pattern = text}) end end end
    widgets.target_rule_refresh()
end

function RuleEditors.addMagicRuleEditor(ui, ctx, window, tools, panelX, panelW, layout)
    local section = "hunting_magic"
    local widgets = ctx.widgets
    local loading = false
    local function add(kind, id, text, x, y, width, height)
        local widget = ctx.create_widget(kind, window, id, text, x, y, width, height)
        ctx.add_to_section(section, widget)
        return widget
    end
    local chrome = RuleEditors.addRuleEditorChrome(ui, ctx, window, {
        add = add,
        panel_x = panelX,
        panel_w = panelW,
        row_y = layout.row_2_y,
        action_y = layout.row_7_y + 52,
        selector_id = "ctoaMagicRuleEditor",
        previous_id = "ctoaMagicRulePrev",
        next_id = "ctoaMagicRuleNext",
        empty_text = "0/0 no spell rules",
        on_previous = function() ctx.select_magic_rule(-1); widgets.magic_rule_refresh() end,
        on_next = function() ctx.select_magic_rule(1); widgets.magic_rule_refresh() end,
        actions = {
            {id = "ctoaMagicRuleAdd", text = "+ ADD", role = "primary", callback = function() ctx.add_magic_rule(); widgets.magic_rule_refresh() end},
            {id = "ctoaMagicRuleRemove", text = "REMOVE", role = "danger", callback = function() ctx.remove_magic_rule(); widgets.magic_rule_refresh() end},
            {id = "ctoaMagicRuleUp", text = "UP", callback = function() ctx.move_magic_rule(-1); widgets.magic_rule_refresh() end},
            {id = "ctoaMagicRuleDown", text = "DOWN", callback = function() ctx.move_magic_rule(1); widgets.magic_rule_refresh() end},
        },
    })
    local selector = chrome.selector

    local wordsLabel = add("Label", "ctoaMagicRuleWordsLabel", "Spell words", panelX, layout.row_3_y + 3, 96, 18)
    ui.styleLabel(wordsLabel, "muted", ctx.ui_style)
    local wordsEdit = add("TextEdit", "ctoaMagicRuleWords", "", panelX + 104, layout.row_3_y, panelW - 104, 22)
    ui.styleTextEdit(wordsEdit, ctx.ui_style)
    if wordsEdit and wordsEdit.setMaxLength then pcall(function() wordsEdit:setMaxLength(64) end) end

    local valueWidgets = {}
    local function addNumberRow(id, label, key, y, step)
        local name = add("Label", id .. "Label", label, panelX, y + 3, 126, 18)
        ui.styleLabel(name, "muted", ctx.ui_style)
        local minus = add("Button", id .. "Minus", "-", panelX + panelW - 144, y, 28, 22)
        local value = add("Label", id .. "Value", "0", panelX + panelW - 110, y + 3, 70, 16)
        local plus = add("Button", id .. "Plus", "+", panelX + panelW - 34, y, 34, 22)
        ui.styleMiniButton(minus, ctx.ui_style, ctx.align_center)
        ui.styleLabel(value, "default", ctx.ui_style, ctx.align_center)
        ui.styleMiniButton(plus, ctx.ui_style, ctx.align_center)
        valueWidgets[key] = value
        local function change(direction)
            local state = ctx.magic_rule_state()
            local rule = state.rule or {}
            ctx.update_magic_rule({[key] = (tonumber(rule[key]) or 0) + (step * direction)})
            widgets.magic_rule_refresh()
        end
        ctx.bind_click(minus, function() change(-1) end)
        ctx.bind_click(plus, function() change(1) end)
    end
    addNumberRow("ctoaMagicRuleMin", "Minimum mobs", "min_nearby", layout.row_4_y, 1)
    addNumberRow("ctoaMagicRuleMax", "Maximum mobs", "max_nearby", layout.row_5_y, 1)
    addNumberRow("ctoaMagicRuleCooldown", "Cooldown", "cooldown_ms", layout.row_6_y, 250)
    addNumberRow("ctoaMagicRuleRange", "Scan range", "scan_range", layout.row_7_y, 1)

    local toggleY = layout.row_7_y + 26
    local toggleGap = 4
    local toggleW = math.floor((panelW - (toggleGap * 2)) / 3)
    local toggles = {}
    for index, spec in ipairs({
        {id = "ctoaMagicRuleEnabled", key = "enabled", label = "Enabled"},
        {id = "ctoaMagicRuleMobCount", key = "use_mob_count", label = "Mob count"},
        {id = "ctoaMagicRuleDirectional", key = "directional", label = "Directional"},
    }) do
        local button = add("Button", spec.id, spec.label, panelX + ((index - 1) * (toggleW + toggleGap)), toggleY, toggleW, 22)
        toggles[spec.key] = {button = button, label = spec.label}
        ctx.bind_click(button, function()
            local state = ctx.magic_rule_state()
            local rule = state.rule or {}
            ctx.update_magic_rule({[spec.key] = rule[spec.key] ~= true})
            widgets.magic_rule_refresh()
        end)
    end

    widgets.magic_rule_refresh = function()
        local state = ctx.magic_rule_state()
        local rule = state.rule or {}
        loading = true
        ui.setWidgetText(selector, state.summary or "0/0 no spell rules")
        ui.setWidgetText(wordsEdit, rule.words or "")
        loading = false
        ui.setWidgetText(valueWidgets.min_nearby, tostring(rule.min_nearby or 0))
        ui.setWidgetText(valueWidgets.max_nearby, tostring(rule.max_nearby or 0))
        ui.setWidgetText(valueWidgets.cooldown_ms, tostring(rule.cooldown_ms or 0) .. " ms")
        ui.setWidgetText(valueWidgets.scan_range, tostring(rule.scan_range or 0) .. " sqm")
        for key, item in pairs(toggles) do
            local active = rule[key] == true
            ui.setWidgetText(item.button, item.label .. " " .. (active and "ON" or "OFF"))
            ui.styleToggleButton(item.button, active, ctx.ui_style, ctx.align_center)
        end
    end
    if wordsEdit then
        wordsEdit.onTextChange = function(_, text)
            if not loading then ctx.update_magic_rule({words = text}) end
        end
    end
    widgets.magic_rule_refresh()
end

function RuleEditors.addCombatActionRuleEditor(ui, ctx, window, tools, panelX, panelW, layout)
    local section = "hunting_actions"
    local widgets = ctx.widgets
    local runtime = ctx.combat_runtime_module or {}
    local selectedIndex = 1
    local loading = false
    local function add(kind, id, text, x, y, width, height)
        local widget = ctx.create_widget(kind, window, id, text, x, y, width, height)
        ctx.add_to_section(section, widget)
        return widget
    end
    local function call(name, ...)
        if type(runtime[name]) ~= "function" then return nil, {allowed = false, reason = "combat_runtime_unavailable"} end
        local ok, value, decision = pcall(runtime[name], ...)
        if not ok then return nil, {allowed = false, reason = "combat_action_editor_error"} end
        return value, decision
    end
    local function state()
        local value = call("combatActionRuleState", tools, selectedIndex)
        if type(value) ~= "table" then return {index = 0, count = 0, rule = nil, summary = "editor unavailable"} end
        selectedIndex = tonumber(value.index) or 0
        return value
    end
    local function mutate(name, ...)
        local value, decision = call(name, tools, ...)
        if type(decision) ~= "table" or decision.allowed ~= true or decision.runtime_actions ~= false then return false, value end
        if type(ctx.mark_profile_dirty) == "function" then ctx.mark_profile_dirty("combat_action_rule_editor") end
        return true, value
    end

    local chrome = RuleEditors.addRuleEditorChrome(ui, ctx, window, {
        add = add,
        panel_x = panelX,
        panel_w = panelW,
        row_y = layout.row_2_y,
        action_y = layout.row_7_y + 26,
        selector_id = "ctoaCombatActionRuleEditor",
        previous_id = "ctoaCombatActionRulePrev",
        next_id = "ctoaCombatActionRuleNext",
        empty_text = "0/0 no action rules",
        on_previous = function()
            local current = state()
            selectedIndex = ui.ruleEditorNavigation(current.count, current.index, -1).index
            widgets.combat_action_rule_refresh()
        end,
        on_next = function()
            local current = state()
            selectedIndex = ui.ruleEditorNavigation(current.count, current.index, 1).index
            widgets.combat_action_rule_refresh()
        end,
        actions = {
            {id = "ctoaCombatActionAdd", text = "+ ADD", role = "primary", callback = function()
                local ok, value = mutate("addCombatActionRule", {enabled = false, kind = "rune"})
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.combat_action_rule_refresh()
            end},
            {id = "ctoaCombatActionRemove", text = "REMOVE", role = "danger", callback = function()
                local ok, value = mutate("removeCombatActionRule", selectedIndex)
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.combat_action_rule_refresh()
            end},
            {id = "ctoaCombatActionUp", text = "UP", callback = function()
                local ok, value = mutate("moveCombatActionRule", selectedIndex, -1)
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.combat_action_rule_refresh()
            end},
            {id = "ctoaCombatActionDown", text = "DOWN", callback = function()
                local ok, value = mutate("moveCombatActionRule", selectedIndex, 1)
                if ok and tonumber(value) then selectedIndex = tonumber(value) end
                widgets.combat_action_rule_refresh()
            end},
        },
    })
    local selector = chrome.selector

    local textLabel = add("Label", "ctoaCombatActionTextLabel", "Rune / spell", panelX, layout.row_3_y + 3, 96, 18)
    ui.styleLabel(textLabel, "muted", ctx.ui_style)
    local textEdit = add("TextEdit", "ctoaCombatActionText", "", panelX + 104, layout.row_3_y, panelW - 104, 22)
    ui.styleTextEdit(textEdit, ctx.ui_style)
    if textEdit and textEdit.setMaxLength then pcall(function() textEdit:setMaxLength(64) end) end

    local splitGap = 6
    local splitW = math.floor((panelW - splitGap) / 2)
    local kindButton = add("Button", "ctoaCombatActionKind", "Kind rune", panelX, layout.row_4_y, splitW, 22)
    local modeButton = add("Button", "ctoaCombatActionMode", "Box F5", panelX + splitW + splitGap, layout.row_4_y, splitW, 22)

    local values = {}
    local function addNumber(id, label, key, x, width, y, step)
        local labelWidget = add("Label", id .. "Label", label, x, y + 3, math.max(54, width - 108), 18)
        ui.styleLabel(labelWidget, "muted", ctx.ui_style)
        local minus = add("Button", id .. "Minus", "-", x + width - 102, y, 24, 22)
        local value = add("Label", id .. "Value", "0", x + width - 76, y + 3, 48, 16)
        local plus = add("Button", id .. "Plus", "+", x + width - 24, y, 24, 22)
        ui.styleMiniButton(minus, ctx.ui_style, ctx.align_center)
        ui.styleLabel(value, "default", ctx.ui_style, ctx.align_center)
        ui.styleMiniButton(plus, ctx.ui_style, ctx.align_center)
        values[key] = value
        local function change(delta)
            local rule = state().rule or {}
            mutate("updateCombatActionRule", selectedIndex, {[key] = (tonumber(rule[key]) or 0) + (step * delta)})
            widgets.combat_action_rule_refresh()
        end
        ctx.bind_click(minus, function() change(-1) end)
        ctx.bind_click(plus, function() change(1) end)
    end
    addNumber("ctoaCombatActionMin", "Min mobs", "min_count", panelX, splitW, layout.row_5_y, 1)
    addNumber("ctoaCombatActionMax", "Max mobs", "max_count", panelX + splitW + splitGap, splitW, layout.row_5_y, 1)
    addNumber("ctoaCombatActionCooldown", "Cooldown", "cooldown_ms", panelX, panelW, layout.row_6_y, 250)

    local toggleGap = 4
    local toggleW = math.floor((panelW - (toggleGap * 2)) / 3)
    local toggles = {}
    for index, spec in ipairs({
        {id = "ctoaCombatActionEnabled", key = "enabled", label = "Enabled"},
        {id = "ctoaCombatActionTarget", key = "require_target", label = "Target"},
        {id = "ctoaCombatActionPvpSafe", key = "pvp_safe", label = "PvP safe"},
    }) do
        local button = add("Button", spec.id, spec.label, panelX + ((index - 1) * (toggleW + toggleGap)), layout.row_7_y, toggleW, 22)
        toggles[spec.key] = {button = button, label = spec.label}
        ctx.bind_click(button, function()
            local rule = state().rule or {}
            mutate("updateCombatActionRule", selectedIndex, {[spec.key] = rule[spec.key] ~= true})
            widgets.combat_action_rule_refresh()
        end)
    end

    local function cycle(valuesList, current)
        for index, value in ipairs(valuesList) do if value == current then return valuesList[(index % #valuesList) + 1] end end
        return valuesList[1]
    end
    widgets.combat_action_rule_refresh = function()
        local current = state()
        local rule = current.rule or {}
        loading = true
        ui.setWidgetText(selector, current.summary or "0/0 no action rules")
        ui.setWidgetText(textEdit, rule.action_text or "")
        loading = false
        ui.setWidgetText(kindButton, "Kind " .. tostring(rule.kind or "rune"))
        local mode = rule.kind == "stance" and tostring(rule.stance_mode or "offensive") or tostring(rule.hotkey or "none")
        ui.setWidgetText(modeButton, (rule.kind == "stance" and "Mode " or "Box ") .. mode)
        ui.setWidgetText(values.min_count, tostring(rule.min_count or 0))
        ui.setWidgetText(values.max_count, tostring(rule.max_count or 0))
        ui.setWidgetText(values.cooldown_ms, tostring(rule.cooldown_ms or 0) .. " ms")
        for key, item in pairs(toggles) do
            local active = rule[key] == true
            ui.setWidgetText(item.button, item.label .. " " .. (active and "ON" or "OFF"))
            ui.styleToggleButton(item.button, active, ctx.ui_style, ctx.align_center)
        end
    end
    ctx.bind_click(kindButton, function() local rule = state().rule or {}; mutate("updateCombatActionRule", selectedIndex, {kind = rule.kind == "stance" and "rune" or "stance"}); widgets.combat_action_rule_refresh() end)
    ctx.bind_click(modeButton, function()
        local rule = state().rule or {}
        if rule.kind == "stance" then mutate("updateCombatActionRule", selectedIndex, {stance_mode = rule.stance_mode == "defensive" and "offensive" or "defensive"})
        else mutate("updateCombatActionRule", selectedIndex, {hotkey = cycle(ctx.hotkey_choices or {"F1"}, rule.hotkey)}) end
        widgets.combat_action_rule_refresh()
    end)
    if textEdit then textEdit.onTextChange = function(_, text) if not loading then mutate("updateCombatActionRule", selectedIndex, {action_text = text}) end end end
    widgets.combat_action_rule_refresh()
end



function RuleEditors.contract()
    return {
        mode = "passive",
        owns_shared_editor_chrome = true,
        owns_target_rule_editor = true,
        owns_magic_rule_editor = true,
        owns_combat_action_rule_editor = true,
        callbacks_injected = true,
        mutates_profiles_directly = false,
        runtime_actions = false,
        dispatch_allowed = false,
        casts = false,
        talks = false,
        attacks = false,
        walks = false,
        uses_items = false,
    }
end

_G.CTOA_HELPER_UI_RULE_EDITORS = RuleEditors
return RuleEditors
