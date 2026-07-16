-- ctoa_helper_ui.lua [CTOA OTClient Native]
-- Guarded UI primitives for the helper shell. This module does not run gameplay actions.

local Ui = rawget(_G, "CTOA_HELPER_UI") or {}
local Primitives = rawget(_G, "CTOA_HELPER_UI_PRIMITIVES") or {}
local Composition = rawget(_G, "CTOA_HELPER_UI_COMPOSITION") or {}

local DEFAULT_STYLE = {
    text = "#ffffff",
    muted = "#eeeeee",
    accent = "#f0c56a",
    accent_soft = "#dfbf72",
    good = "#a6f08f",
    off = "#c0c0c0",
    panel = "#262626",
    panel_dark = "#101010",
    panel_subtle = "#2e2e2e",
    panel_surface = "#1a1a1a",
    panel_raised = "#383838",
    border = "#737373",
    divider = "#707070",
    border_active = "#b58c42",
    sidebar_fill = "#181818",
    content_fill = "#171717",
    row_fill = "#303030",
    row_fill_active = "#3d3d3d",
    value_fill = "#0d0d0d",
    button_fill = "#474747",
    button_fill_active = "#545454",
}

local THEMES = {
    classic = {
        text = "#ffffff", muted = "#eeeeee", accent = "#f0c56a", accent_soft = "#c8b16f",
        good = "#93d987", off = "#a0a0a0", panel = "#262626", panel_dark = "#101010",
        panel_subtle = "#2e2e2e", panel_surface = "#1a1a1a", panel_raised = "#383838",
        border = "#737373", divider = "#707070", border_active = "#b58c42",
        sidebar_fill = "#181818", content_fill = "#171717", row_fill = "#303030",
        row_fill_active = "#3d3d3d", value_fill = "#0d0d0d", button_fill = "#474747",
        button_fill_active = "#545454",
    },
    graphite = {
        text = "#f0f2f5", muted = "#a8b0b8", accent = "#f0c36a", accent_soft = "#d7ae55",
        good = "#9be7a0", off = "#8a9096", panel = "#23262b", panel_dark = "#1d2024",
        panel_subtle = "#2a2f35", panel_surface = "#262b31", panel_raised = "#313843",
        border = "#4f5964", divider = "#3f4750", border_active = "#f0c36a",
        sidebar_fill = "#2a2f35", content_fill = "#252a30", row_fill = "#30353b",
        row_fill_active = "#363c43", value_fill = "#22272c", button_fill = "#3d4650",
        button_fill_active = "#495561",
    },
    amber = {
        text = "#f8f0dd", muted = "#c9bfa8", accent = "#f0c36a", accent_soft = "#d7ae55",
        good = "#b9e36d", off = "#aea28a", panel = "#2f291f", panel_dark = "#241f17",
        panel_subtle = "#3a3125", panel_surface = "#2f291d", panel_raised = "#4a3920",
        border = "#7a6644", divider = "#5b4a30", border_active = "#f0c36a",
        sidebar_fill = "#322b1f", content_fill = "#312a20", row_fill = "#3a3125",
        row_fill_active = "#433726", value_fill = "#292218", button_fill = "#56452d",
        button_fill_active = "#6a5432",
    },
    emerald = {
        text = "#ecfff0", muted = "#a7c2ab", accent = "#7fd7a8", accent_soft = "#69bd8e",
        good = "#8ddf93", off = "#91a097", panel = "#1f2b23", panel_dark = "#18231c",
        panel_subtle = "#243328", panel_surface = "#213126", panel_raised = "#2e4633",
        border = "#4d7356", divider = "#38543f", border_active = "#7fd7a8",
        sidebar_fill = "#243328", content_fill = "#223127", row_fill = "#28392d",
        row_fill_active = "#2d4033", value_fill = "#1d2a20", button_fill = "#36503d",
        button_fill_active = "#44664d",
    },
}

local BASE_LAYOUT = {
    outer_margin = 18, column_gap = 14, window_w = 690, window_h = 560,
    base_x = 10, base_y = 10, base_w = 664, base_h = 524,
    sheet_x = 28, sheet_y = 54, sheet_w = 634, sheet_h = 482,
    inner_title_x = 38, inner_title_y = 64, inner_title_w = 614, inner_title_h = 18,
    title_x = 14, title_y = 14, title_w = 658, title_h = 18,
    sidebar_x = 44, sidebar_w = 122, content_x = 186, content_w = 466,
    card_w = 466, value_w = 138, ui_value_row_w = 344,
    profile_left_x = 204, profile_right_x = 378, profile_col_w = 216,
    profile_block_w = 420, profile_status_w = 326,
    profile_save_x = 676, profile_save_w = 78, profile_save_h = 24,
    close_x = 586, close_w = 66, close_h = 24,
}

local function copyTable(source)
    local result = {}
    for key, value in pairs(source or {}) do result[key] = value end
    return result
end

local COMPACT_LAYOUT = {
    overview_tab_y = 116,
    healing_tab_y = 134,
    heal_friend_tab_y = 152,
    conditions_tab_y = 170,
    hunting_tab_y = 188,
    magic_tab_y = 206,
    cavebot_tab_y = 224,
    equipment_tab_y = 242,
    tools_tab_y = 260,
    ui_tab_y = 278,
    scripting_tab_y = 296,
    profile_tab_y = 314,
    content_body_y = 120,
    content_body_h = 292,
    ui_runtime_row_1_y = 148,
    ui_runtime_row_2_y = 174,
    ui_runtime_row_3_y = 200,
    ui_runtime_row_4_y = 226,
    ui_theme_section_y = 250,
    ui_theme_row_1_y = 274,
    ui_theme_info_y = 296,
    ui_layout_section_y = 312,
    ui_layout_row_1_y = 336,
    ui_layout_row_2_y = 360,
    side_title_y = 94,
    side_subtitle_y = 108,
    profile_caption_y = 350,
    profile_card_y = 370,
    enabled_y = 400,
    status_y = 424,
    hint_y = 446,
    section_y = 92,
    row_1_y = 148,
    row_2_y = 174,
    row_3_y = 200,
    row_4_y = 226,
    row_5_y = 252,
    row_6_y = 278,
    row_7_y = 304,
    profile_row_1_y = 148,
    profile_row_2_y = 172,
    profile_row_3_y = 196,
    profile_row_4_y = 220,
    profile_row_5_y = 244,
    profile_row_6_y = 268,
    profile_rotation_y = 292,
    profile_rotation_info_y = 314,
    ui_summary_y = 210,
    footer_y = 382,
    profile_footer_y = 382,
    profile_save_y = 382,
    close_y = 514,
}

local DEFAULT_LAYOUT = {
    side_title_y = 98,
    side_subtitle_y = 112,
    overview_tab_y = 120,
    healing_tab_y = 138,
    heal_friend_tab_y = 156,
    conditions_tab_y = 174,
    hunting_tab_y = 192,
    magic_tab_y = 210,
    cavebot_tab_y = 228,
    equipment_tab_y = 246,
    tools_tab_y = 264,
    ui_tab_y = 282,
    scripting_tab_y = 300,
    profile_tab_y = 318,
    content_body_y = 124,
    content_body_h = 304,
    ui_runtime_row_1_y = 152,
    ui_runtime_row_2_y = 180,
    ui_runtime_row_3_y = 208,
    ui_runtime_row_4_y = 236,
    ui_theme_section_y = 258,
    ui_theme_row_1_y = 286,
    ui_theme_info_y = 310,
    ui_layout_section_y = 326,
    ui_layout_row_1_y = 350,
    ui_layout_row_2_y = 374,
    profile_caption_y = 358,
    profile_card_y = 378,
    enabled_y = 408,
    status_y = 432,
    hint_y = 454,
    section_y = 96,
    row_1_y = 152,
    row_2_y = 180,
    row_3_y = 208,
    row_4_y = 236,
    row_5_y = 264,
    row_6_y = 292,
    row_7_y = 320,
    profile_row_1_y = 152,
    profile_row_2_y = 178,
    profile_row_3_y = 204,
    profile_row_4_y = 230,
    profile_row_5_y = 256,
    profile_row_6_y = 282,
    profile_rotation_y = 310,
    profile_rotation_info_y = 332,
    ui_summary_y = 220,
    footer_y = 398,
    profile_footer_y = 408,
    profile_save_y = 406,
    close_y = 514,
}

function Ui.configureLayout(layout, compact)
    local target = layout or {}
    local source = compact and COMPACT_LAYOUT or DEFAULT_LAYOUT
    for key, value in pairs(source) do
        target[key] = value
    end
    return target
end

function Ui.newStyle()
    return copyTable(DEFAULT_STYLE)
end

function Ui.themes()
    local result = {}
    for id, theme in pairs(THEMES) do result[id] = copyTable(theme) end
    return result
end

function Ui.newLayout()
    return Ui.configureLayout(copyTable(BASE_LAYOUT), false)
end

function Ui.shortText(text, maxLen)
    return Primitives.shortText(text, maxLen)
end

function Ui.fitText(text, width, fontScale)
    return Primitives.fitText(text, width, fontScale)
end

function Ui.setWidgetText(widget, text)
    return Primitives.setWidgetText(widget, text)
end

function Ui.styleWidget(widget, opts)
    if not widget or not opts then
        return widget
    end
    if opts.color and widget.setColor then
        pcall(function() widget:setColor(opts.color) end)
    end
    if opts.background and widget.setBackgroundColor then
        pcall(function() widget:setBackgroundColor(opts.background) end)
    end
    if opts.border and widget.setBorderColor then
        pcall(function() widget:setBorderColor(opts.border) end)
    end
    if opts.borderWidth and widget.setBorderWidth then
        pcall(function() widget:setBorderWidth(opts.borderWidth) end)
    end
    if opts.opacity and widget.setOpacity then
        pcall(function() widget:setOpacity(opts.opacity) end)
    end
    if opts.align and widget.setTextAlign then
        pcall(function() widget:setTextAlign(opts.align) end)
    end
    if opts.fontScale and widget.setFontScale then
        pcall(function() widget:setFontScale(opts.fontScale) end)
    end
    return widget
end

function Ui.setWidgetChecked(widget, checked)
    return Primitives.setWidgetChecked(widget, checked)
end

function Ui.getWidgetChecked(widget)
    return Primitives.getWidgetChecked(widget)
end

function Ui.showWidget(widget, visible)
    return Primitives.showWidget(widget, visible)
end

function Ui.createWidget(kind, parent, id, text, x, y, width, height)
    return Primitives.createWidget(kind, parent, id, text, x, y, width, height)
end

function Ui.styleTabState(widget, active, style, alignLeft)
    style = style or {}
    Ui.styleWidget(widget, {
        color = active and style.text or style.muted,
        background = active and (style.surface_raised or style.row_fill_active) or (style.surface_low or style.sidebar_fill),
        border = active and (style.edge_highlight or style.border_active) or (style.edge_shadow or style.sidebar_fill),
        borderWidth = 1,
        align = alignLeft,
        fontScale = active and 1.02 or 0.94,
        opacity = active and 1.0 or 0.86
    })
end

function Ui.styleTabRail(widget, active, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = active and style.accent or (style.surface_low or style.sidebar_fill),
        border = active and style.accent or (style.surface_low or style.sidebar_fill),
        borderWidth = 1,
        opacity = active and 1.0 or 0.0
    })
end

function Ui.styleRaisedCard(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.surface_raised or style.panel_raised,
        border = style.edge_highlight or style.border,
        borderWidth = 1,
        opacity = 1.0
    })
end

function Ui.styleInsetValue(widget, active, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.surface_inset or style.value_fill,
        border = active and (style.edge_highlight or style.border_active) or (style.edge_shadow or style.divider),
        borderWidth = 1,
        opacity = 1.0
    })
end

function Ui.styleGroupedFrame(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.surface_low or style.panel_surface,
        border = style.edge_shadow or style.divider,
        borderWidth = 1,
        opacity = 0.96
    })
end

function Ui.styleSubtabState(widget, active, style, alignCenter)
    style = style or {}
    Ui.styleWidget(widget, {
        color = active and style.text or style.muted,
        background = active and style.row_fill_active or style.content_fill,
        border = active and style.border_active or style.content_fill,
        borderWidth = 1,
        align = alignCenter,
        fontScale = active and 1.02 or 0.94,
        opacity = active and 1.0 or 0.78
    })
end

function Ui.styleMiniButton(widget, style, alignCenter)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text,
        background = style.panel_surface,
        border = style.edge_highlight or style.divider,
        borderWidth = 1,
        opacity = 1.0,
        align = alignCenter,
        fontScale = 0.98
    })
end

function Ui.styleActionButton(widget, role, enabled, style, alignCenter)
    style = style or {}
    role = role == true and "primary" or role == false and "neutral" or role or "neutral"
    if role == "danger" then role = "destructive" end
    enabled = enabled ~= false
    local background = style.button_fill
    local border = style.edge_shadow or style.divider
    local color = style.text
    if role == "primary" then
        background = style.surface_raised or style.button_fill_active
        border = style.accent
        color = style.text
    elseif role == "secondary" then
        background = style.button_fill_active
        border = style.edge_highlight or style.border_active
        color = style.text
    elseif role == "destructive" then
        background = style.surface_inset or style.value_fill
        border = style.state_blocked or style.off
        color = style.state_blocked or style.off
    end
    Ui.styleWidget(widget, {
        color = enabled and color or style.muted,
        background = background,
        border = border,
        borderWidth = 1,
        opacity = enabled and 1.0 or 0.55,
        align = alignCenter,
        fontScale = 1.10
    })
end

function Ui.normalizeOperatorState(value)
    local normalized = string.lower(tostring(value or "disabled"))
    if normalized == "active" or normalized == "armed" or normalized == "ready" or normalized == "review_ready" or normalized == "on" or normalized == "passed" then
        return "active"
    end
    if normalized == "blocked" or normalized == "missing" or normalized == "missing_components" or normalized == "failed" or normalized == "error" or normalized == "unavailable" then
        return "blocked"
    end
    if normalized == "stale" or normalized == "unknown" or normalized == "pending" then
        return "stale"
    end
    return "disabled"
end

function Ui.operatorRuntimeState(snapshot)
    local item = snapshot or {}
    local blockedReason = item.blocked_reason
    if item.blocked == true or (type(blockedReason) == "string" and blockedReason ~= "") then
        return "blocked"
    end
    if item.stale == true then
        return "stale"
    end
    if item.enabled == true or item.active == true then
        return "active"
    end
    return "disabled"
end

function Ui.styleOperatorState(widget, state, style, align)
    style = style or {}
    local normalized = Ui.normalizeOperatorState(state)
    local stateColor = style.state_off or style.off
    if normalized == "active" then
        stateColor = style.state_on or style.good
    elseif normalized == "blocked" then
        stateColor = style.state_blocked or style.off
    elseif normalized == "stale" then
        stateColor = style.state_stale or style.accent or style.off
    end
    Ui.styleWidget(widget, {
        color = stateColor,
        background = style.surface_inset or style.value_fill,
        border = stateColor,
        borderWidth = 1,
        opacity = 1.0,
        align = align,
        fontScale = 0.94
    })
    return normalized
end

function Ui.styleRuntimeBadge(widget, armed, blocked, style, alignCenter)
    local state = Ui.operatorRuntimeState({enabled = armed == true, blocked = blocked == true})
    return Ui.styleOperatorState(widget, state, style, alignCenter)
end

function Ui.styleRuleCard(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text,
        background = style.surface_raised or style.panel_surface,
        border = style.edge_shadow or style.border,
        borderWidth = 1,
        opacity = 0.9
    })
end

function Ui.styleMetricRow(widget, active, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = active and (style.surface_raised or style.row_fill_active) or (style.surface_low or style.panel_surface),
        border = style.edge_shadow or style.panel_surface,
        borderWidth = 1,
        opacity = active and 0.98 or 0.86
    })
end

function Ui.styleMetricLabel(widget, style, alignLeft)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.muted,
        align = alignLeft,
        fontScale = 0.98
    })
end

function Ui.styleMetricValue(widget, style, alignRight)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text,
        align = alignRight,
        fontScale = 1.08
    })
end

function Ui.styleSettingState(row, valueBack, valueLabel, active, style, alignCenter)
    style = style or {}
    Ui.styleWidget(row, {
        background = active and (style.surface_raised or style.row_fill_active) or (style.surface_low or style.panel_surface),
        border = style.edge_shadow or style.panel_surface,
        borderWidth = 1,
        opacity = active and 0.98 or 0.88
    })
    Ui.styleWidget(valueBack, {
        background = style.surface_inset or style.value_fill,
        border = active and (style.state_on or style.accent_soft) or (style.edge_shadow or style.border),
        borderWidth = 1,
        opacity = 1.0
    })
    Ui.styleWidget(valueLabel, {
        color = active and style.text or style.muted,
        align = alignCenter,
        fontScale = 1.16
    })
end

function Ui.styleTextEdit(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text or "#e5e7eb",
        background = style.surface_inset or style.surface_low or "#171923",
        border = style.edge_shadow or style.border or "#4b5563",
        borderWidth = 1,
        opacity = 1.0,
    })
end

function Ui.styleStateValue(widget, state, style, alignCenter)
    style = style or {}
    local normalized = Ui.normalizeOperatorState(state)
    local color = style.state_off or style.off
    if normalized == "active" then
        color = style.state_on or style.good
    elseif normalized == "blocked" then
        color = style.state_blocked or style.off
    elseif normalized == "stale" then
        color = style.state_stale or style.accent or style.off
    end
    Ui.styleWidget(widget, {
        color = color,
        align = alignCenter,
        fontScale = 1.16,
        opacity = 1.0
    })
end

function Ui.styleProfileField(row, valueBack, valueLabel, active, style, alignCenter)
    style = style or {}
    Ui.styleWidget(row, {
        background = active and (style.surface_raised or style.row_fill_active) or (style.surface_low or style.panel_surface),
        border = style.edge_shadow or style.panel_surface,
        borderWidth = 1,
        opacity = active and 0.96 or 0.86
    })
    Ui.styleWidget(valueBack, {
        background = style.surface_inset or style.value_fill,
        border = active and (style.edge_highlight or style.accent_soft) or (style.edge_shadow or style.divider),
        borderWidth = 1,
        opacity = 1.0
    })
    Ui.styleWidget(valueLabel, {
        color = style.text,
        align = alignCenter,
        fontScale = 1.12
    })
end

function Ui.styleVectorRow(row, valueBacks, valueLabels, style, alignCenter)
    style = style or {}
    Ui.styleWidget(row, {
        background = style.panel_surface,
        border = style.panel_surface,
        borderWidth = 1,
        opacity = 0.9
    })
    for _, valueBack in ipairs(valueBacks or {}) do
        Ui.styleWidget(valueBack, {
            background = style.value_fill,
            border = style.divider,
            borderWidth = 1,
            opacity = 0.98
        })
    end
    for _, valueLabel in ipairs(valueLabels or {}) do
        Ui.styleWidget(valueLabel, {
            color = style.text,
            align = alignCenter,
            fontScale = 1.06
        })
    end
end

function Ui.styleSectionBody(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.surface_low or style.panel_surface,
        border = style.edge_shadow or style.panel_surface,
        borderWidth = 1,
        opacity = 1.0
    })
end

function Ui.styleTableHeader(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.content_fill,
        border = style.content_fill,
        borderWidth = 1,
        opacity = 0.96
    })
end

function Ui.styleTableHeaderLabel(widget, align, fontScale, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.muted,
        align = align,
        fontScale = fontScale
    })
end

function Ui.styleFooterStrip(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.surface_inset or style.panel_dark,
        border = style.edge_shadow or style.divider,
        borderWidth = 1,
        opacity = 0.86
    })
end

function Ui.styleFooterStripLabel(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.muted,
        fontScale = 0.94
    })
end

function Ui.styleSummaryStrip(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.surface_raised or style.row_fill_active,
        border = style.edge_highlight or style.row_fill_active,
        borderWidth = 1,
        opacity = 0.92
    })
end

function Ui.styleSummaryStripLabel(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text,
        fontScale = 0.96
    })
end

function Ui.styleSectionBandTitle(widget, style, alignLeft)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.panel_surface,
        border = style.content_fill,
        borderWidth = 1,
        opacity = 0.0
    })
    Ui.styleWidget(widget, {
        align = alignLeft,
        fontScale = 1.12,
        color = style.accent
    })
end

function Ui.styleSectionBandSubtitle(widget, style, alignRight)
    style = style or {}
    Ui.styleWidget(widget, {
        align = alignRight,
        color = style.muted,
        fontScale = 0.9
    })
end

function Ui.styleSectionBandDivider(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.divider,
        border = style.divider,
        borderWidth = 1,
        opacity = 0.45
    })
end

function Ui.stylePriorityBadge(widget, active, style, alignCenter)
    style = style or {}
    Ui.styleWidget(widget, {
        color = active and style.accent or style.muted,
        background = active and style.value_fill or style.panel_dark,
        border = active and style.border_active or style.divider,
        borderWidth = 1,
        opacity = 1.0,
        align = alignCenter,
        fontScale = 0.96
    })
end

function Ui.styleLabel(widget, variant, style, align)
    style = style or {}
    local opts = {
        color = style.text,
        fontScale = 1.0,
        align = align
    }
    if variant == "muted" then
        opts.color = style.muted
        opts.fontScale = 1.06
    elseif variant == "accent" then
        opts.color = style.accent
    elseif variant == "status" then
        opts.color = style.text
        opts.fontScale = 1.0
    end
    Ui.styleWidget(widget, opts)
end

function Ui.styleWindowRoot(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.panel,
        border = style.border,
        borderWidth = 1,
        opacity = 1.0
    })
end

function Ui.styleWindowFrame(widget, variant, style)
    style = style or {}
    local background = style.panel
    local border = style.panel
    local opacity = 1.0
    if variant == "outer" then
        background = style.panel_dark
        border = style.border
    elseif variant == "title" then
        background = style.panel_subtle
        border = style.panel_subtle
    elseif variant == "inner_title" then
        background = style.panel_dark
        border = style.panel_dark
        opacity = 0.82
    elseif variant == "sidebar" then
        background = style.sidebar_fill
        border = style.sidebar_fill
        opacity = 0.9
    elseif variant == "content" then
        background = style.content_fill
        border = style.content_fill
        opacity = 0.95
    elseif variant == "divider" then
        background = style.divider
        border = style.divider
        opacity = 0.38
    end
    Ui.styleWidget(widget, {
        background = background,
        border = border,
        borderWidth = 1,
        opacity = opacity
    })
end

function Ui.styleWindowTitleLabel(widget, variant, style, alignLeft, alignRight)
    style = style or {}
    local opts = {
        color = style.muted,
        align = alignLeft,
        fontScale = 0.9
    }
    if variant == "title" then
        opts.color = style.accent
        opts.align = alignLeft
        opts.fontScale = 0.98
    elseif variant == "state" then
        opts.color = style.muted
        opts.align = alignRight
        opts.fontScale = 0.86
    elseif variant == "side_title" then
        opts.color = style.accent
        opts.align = alignLeft
        opts.fontScale = 1.02
    elseif variant == "side_subtitle" then
        opts.color = style.muted
        opts.align = alignLeft
        opts.fontScale = 0.86
    end
    Ui.styleWidget(widget, opts)
end

function Ui.styleToggleButton(widget, enabled, style, alignCenter)
    style = style or {}
    Ui.styleWidget(widget, {
        color = enabled and style.good or style.off,
        background = enabled and "#30372e" or style.panel_dark,
        border = enabled and "#5f8057" or style.border,
        borderWidth = 1,
        align = alignCenter,
        fontScale = 1.08
    })
end

function Ui.styleCheckBox(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.muted,
        background = style.sidebar_fill,
        border = style.sidebar_fill,
        borderWidth = 1,
        opacity = 0.9,
        fontScale = 0.94
    })
end

function Ui.styleSidebarCard(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text,
        background = style.surface_raised or style.panel_dark,
        border = style.edge_highlight or style.border,
        borderWidth = 1,
        opacity = 0.88,
        fontScale = 1.02
    })
end

function Ui.styleOverviewAvatarFrame(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.panel_dark,
        border = style.border,
        borderWidth = 1,
        opacity = 1.0
    })
end

function Ui.styleOverviewAvatar(widget, style, alignCenter)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.accent,
        align = alignCenter,
        fontScale = 1.34
    })
end

function Ui.styleOverviewAvatarName(widget, style, alignCenter)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.text,
        align = alignCenter,
        fontScale = 1.0
    })
end

function Ui.styleOverviewHpBar(widget)
    Ui.styleWidget(widget, {
        background = "#3d8f3a",
        border = "#5fa95b",
        borderWidth = 1,
        opacity = 1.0
    })
end

function Ui.styleOverviewEquipSlot(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        background = style.value_fill,
        border = style.divider,
        borderWidth = 1,
        opacity = 0.96
    })
end

function Ui.styleControlName(widget, style)
    style = style or {}
    Ui.styleWidget(widget, {
        color = style.muted,
        fontScale = 0.98
    })
end

function Ui.settingRowGeometry(x, width, layout)
    return Primitives.settingRowGeometry(x, width, layout)
end

function Ui.metricCardGeometry(x, width)
    return Primitives.metricCardGeometry(x, width)
end

function Ui.metricTextPlan(label, value, widget, width, layout)
    layout = layout or {}
    local defaultWidth = width or layout.content_w or 360
    local labelWidth = 150
    local valueWidth = defaultWidth - 170
    if type(widget) == "table" then
        labelWidth = widget.label_width or labelWidth
        valueWidth = widget.value_width or valueWidth
    end
    return {
        label_text = Ui.fitText(label, labelWidth - 8, 1.02),
        value_text = Ui.fitText(value, valueWidth - 8, 1.02),
        fallback_text = Ui.fitText(tostring(label or "") .. "  |  " .. tostring(value or ""), defaultWidth - 10, 1.02)
    }
end

function Ui.setMetricText(widget, label, value, width, layout)
    local textPlan = Ui.metricTextPlan(label, value, widget, width, layout)
    if type(widget) == "table" and widget.value then
        if widget.label and widget.label.setText then
            widget.label:setText(textPlan.label_text)
        end
        widget.value:setText(textPlan.value_text)
        return
    end
    if widget and widget.setText then
        widget:setText(textPlan.fallback_text)
    end
end

function Ui.profileFieldGeometry(x, width)
    return Primitives.profileFieldGeometry(x, width)
end

function Ui.vectorStepGeometry(x, width)
    local labelWidth = math.max(104, width - 292)
    local controlsX = x + labelWidth + 16
    local buttonWidth = 16
    local valueWidth = 42
    local gap = 5
    local xValueBack = controlsX + 14 + buttonWidth + gap
    local xNext = xValueBack + valueWidth + gap
    local yBase = xNext + buttonWidth + 18
    local yValueBack = yBase + 14 + buttonWidth + gap
    return {
        label_width = labelWidth,
        controls_x = controlsX,
        button_width = buttonWidth,
        value_width = valueWidth,
        gap = gap,
        name_x = x + 10,
        name_y_offset = 3,
        tag_y_offset = 3,
        control_y_offset = 2,
        value_y_offset = 3,
        x_tag_x = controlsX,
        x_prev_x = controlsX + 14,
        x_value_back_x = xValueBack,
        x_value_x = xValueBack + 2,
        x_next_x = xNext,
        y_tag_x = yBase,
        y_prev_x = yBase + 14,
        y_value_back_x = yValueBack,
        y_value_x = yValueBack + 2,
        y_next_x = yValueBack + valueWidth + gap
    }
end

local function adapterStyle(adapter)
    adapter = adapter or {}
    return adapter.style or {}, adapter.align_center
end

local function adapterProfileFieldGeometry(adapter, x, width)
    adapter = adapter or {}
    local geometry = nil
    if type(adapter.profile_field_geometry) == "function" then
        geometry = adapter.profile_field_geometry(x, width)
    end
    geometry = geometry or Ui.profileFieldGeometry(x, width)
    return geometry.label_width, geometry.prev_x, geometry.value_x, geometry.next_x, geometry.button_width, geometry.value_width
end

function Ui.addProfileCycleRow(adapter, parent, id, label, getter, setter, options, x, y, width, section, formatter, dirtyFn)
    adapter = adapter or {}
    local style, alignCenter = adapterStyle(adapter)
    local createWidget = adapter.create_widget
    local addToSection = adapter.add_to_section
    local bindClick = adapter.bind_click
    local fitText = adapter.fit_text or Ui.fitText
    local setWidgetText = adapter.set_widget_text or Ui.setWidgetText
    local profileCycle = adapter.profile_cycle
    if type(createWidget) ~= "function" or type(addToSection) ~= "function" or type(bindClick) ~= "function" or type(profileCycle) ~= "function" then
        return nil
    end

    local row = createWidget("Button", parent, id .. "Row", "", x, y, width, 24)
    addToSection(section, row)

    local labelWidth, prevX, valueX, nextX, buttonWidth, valueWidth = adapterProfileFieldGeometry(adapter, x, width)
    local name = createWidget("Label", parent, id .. "Name", fitText(label, labelWidth, 1.0), x + 10, y + 3, labelWidth, 15)
    Ui.styleControlName(name, style)
    addToSection(section, name)

    local prev = createWidget("Button", parent, id .. "Prev", "<", prevX, y + 2, buttonWidth, 16)
    local valueBack = createWidget("Label", parent, id .. "ValueBack", "", valueX, y + 2, valueWidth, 16)
    local valueLabel = createWidget("Label", parent, id .. "Value", "", valueX + 2, y + 3, valueWidth - 4, 14)
    local next = createWidget("Button", parent, id .. "Next", ">", nextX, y + 2, buttonWidth, 16)
    addToSection(section, prev)
    addToSection(section, valueBack)
    addToSection(section, valueLabel)
    addToSection(section, next)
    Ui.styleMiniButton(prev, style, alignCenter)
    Ui.styleMiniButton(next, style, alignCenter)

    local function refresh()
        local value = getter()
        setWidgetText(valueLabel, fitText(formatter and formatter(value) or tostring(value), valueWidth - 4, 1.08))
        Ui.styleProfileField(row, valueBack, valueLabel, true, style, alignCenter)
    end

    local markDirty = dirtyFn or adapter.mark_profile_dirty
    bindClick(prev, function()
        local updated = setter(profileCycle(options, getter(), -1))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id)
        end
    end)
    bindClick(next, function()
        local updated = setter(profileCycle(options, getter(), 1))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id)
        end
    end)
    bindClick(row, function()
        local updated = setter(profileCycle(options, getter(), 1))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id)
        end
    end)

    refresh()
    return row
end

function Ui.addProfileStepRow(adapter, parent, id, label, getter, setter, step, minValue, maxValue, x, y, width, section, formatter, dirtyFn)
    adapter = adapter or {}
    local style, alignCenter = adapterStyle(adapter)
    local createWidget = adapter.create_widget
    local addToSection = adapter.add_to_section
    local bindClick = adapter.bind_click
    local fitText = adapter.fit_text or Ui.fitText
    local setWidgetText = adapter.set_widget_text or Ui.setWidgetText
    local stepValue = adapter.step_value
    if type(createWidget) ~= "function" or type(addToSection) ~= "function" or type(bindClick) ~= "function" then
        return nil
    end

    local row = createWidget("Button", parent, id .. "Row", "", x, y, width, 24)
    addToSection(section, row)

    local labelWidth, prevX, valueX, nextX, buttonWidth, valueWidth = adapterProfileFieldGeometry(adapter, x, width)
    local name = createWidget("Label", parent, id .. "Name", fitText(label, labelWidth, 1.0), x + 10, y + 3, labelWidth, 15)
    Ui.styleControlName(name, style)
    addToSection(section, name)

    local prev = createWidget("Button", parent, id .. "Prev", "-", prevX, y + 2, buttonWidth, 16)
    local valueBack = createWidget("Label", parent, id .. "ValueBack", "", valueX, y + 2, valueWidth, 16)
    local valueLabel = createWidget("Label", parent, id .. "Value", "", valueX + 2, y + 3, valueWidth - 4, 14)
    local next = createWidget("Button", parent, id .. "Next", "+", nextX, y + 2, buttonWidth, 16)
    addToSection(section, prev)
    addToSection(section, valueBack)
    addToSection(section, valueLabel)
    addToSection(section, next)
    Ui.styleMiniButton(prev, style, alignCenter)
    Ui.styleMiniButton(next, style, alignCenter)

    local markDirty = dirtyFn or adapter.mark_profile_dirty
    local function setValue(nextValue)
        if type(stepValue) == "function" then
            nextValue = stepValue(nextValue, minValue, maxValue)
        end
        local updated = setter(nextValue)
        if updated == false then
            return false
        end
        setWidgetText(valueLabel, fitText(formatter and formatter(nextValue) or tostring(nextValue), valueWidth - 4, 1.08))
        Ui.styleProfileField(row, valueBack, valueLabel, true, style, alignCenter)
        if markDirty then
            markDirty(id)
        end
        return true
    end

    bindClick(prev, function()
        if setValue((getter() or 0) - step) == false then
            return
        end
    end)
    bindClick(next, function()
        if setValue((getter() or 0) + step) == false then
            return
        end
    end)
    bindClick(row, function()
        if setValue((getter() or 0) + step) == false then
            return
        end
    end)

    setWidgetText(valueLabel, fitText(formatter and formatter(getter()) or tostring(getter()), valueWidth - 4, 1.08))
    Ui.styleProfileField(row, valueBack, valueLabel, true, style, alignCenter)
    return row
end

function Ui.addVectorStepRow(adapter, parent, id, label, getterX, setterX, getterY, setterY, step, minValue, maxValue, x, y, width, section, formatterX, formatterY, dirtyFn)
    adapter = adapter or {}
    local style, alignCenter = adapterStyle(adapter)
    local createWidget = adapter.create_widget
    local addToSection = adapter.add_to_section
    local bindClick = adapter.bind_click
    local setWidgetText = adapter.set_widget_text or Ui.setWidgetText
    if type(createWidget) ~= "function" or type(addToSection) ~= "function" or type(bindClick) ~= "function" then
        return nil
    end

    local row = createWidget("Button", parent, id .. "Row", "", x, y, width, 24)
    addToSection(section, row)

    local geometry = Ui.vectorStepGeometry(x, width)
    local labelWidth = geometry.label_width
    local buttonWidth = geometry.button_width
    local valueWidth = geometry.value_width
    local name = createWidget("Label", parent, id .. "Name", Ui.fitText(label, labelWidth, 1.02), geometry.name_x, y + geometry.name_y_offset, labelWidth, 15)
    Ui.styleControlName(name, style)
    addToSection(section, name)

    local xTag = createWidget("Label", parent, id .. "XTag", "X", geometry.x_tag_x, y + geometry.tag_y_offset, 10, 15)
    local xPrev = createWidget("Button", parent, id .. "XPrev", "-", geometry.x_prev_x, y + geometry.control_y_offset, buttonWidth, 16)
    local xValueBack = createWidget("Label", parent, id .. "XValueBack", "", geometry.x_value_back_x, y + geometry.control_y_offset, valueWidth, 16)
    local xValue = createWidget("Label", parent, id .. "XValue", "", geometry.x_value_x, y + geometry.value_y_offset, valueWidth - 4, 14)
    local xNext = createWidget("Button", parent, id .. "XNext", "+", geometry.x_next_x, y + geometry.control_y_offset, buttonWidth, 16)
    local yTag = createWidget("Label", parent, id .. "YTag", "Y", geometry.y_tag_x, y + geometry.tag_y_offset, 10, 15)
    local yPrev = createWidget("Button", parent, id .. "YPrev", "-", geometry.y_prev_x, y + geometry.control_y_offset, buttonWidth, 16)
    local yValueBack = createWidget("Label", parent, id .. "YValueBack", "", geometry.y_value_back_x, y + geometry.control_y_offset, valueWidth, 16)
    local yValue = createWidget("Label", parent, id .. "YValue", "", geometry.y_value_x, y + geometry.value_y_offset, valueWidth - 4, 14)
    local yNext = createWidget("Button", parent, id .. "YNext", "+", geometry.y_next_x, y + geometry.control_y_offset, buttonWidth, 16)
    addToSection(section, xTag)
    addToSection(section, xPrev)
    addToSection(section, xValueBack)
    addToSection(section, xValue)
    addToSection(section, xNext)
    addToSection(section, yTag)
    addToSection(section, yPrev)
    addToSection(section, yValueBack)
    addToSection(section, yValue)
    addToSection(section, yNext)
    Ui.styleMiniButton(xPrev, style, alignCenter)
    Ui.styleMiniButton(xNext, style, alignCenter)
    Ui.styleMiniButton(yPrev, style, alignCenter)
    Ui.styleMiniButton(yNext, style, alignCenter)

    local markDirty = dirtyFn or adapter.mark_ui_prefs_dirty or adapter.mark_profile_dirty
    local function clampValue(value)
        if minValue then
            value = math.max(minValue, value)
        end
        if maxValue then
            value = math.min(maxValue, value)
        end
        return value
    end

    local function refresh()
        setWidgetText(xValue, formatterX and formatterX(getterX()) or tostring(getterX()))
        setWidgetText(yValue, formatterY and formatterY(getterY()) or tostring(getterY()))
        Ui.styleVectorRow(row, {xValueBack, yValueBack}, {xValue, yValue}, style, alignCenter)
    end

    bindClick(xPrev, function()
        local updated = setterX(clampValue((getterX() or 0) - step))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id .. "_x")
        end
    end)
    bindClick(xNext, function()
        local updated = setterX(clampValue((getterX() or 0) + step))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id .. "_x")
        end
    end)
    bindClick(yPrev, function()
        local updated = setterY(clampValue((getterY() or 0) - step))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id .. "_y")
        end
    end)
    bindClick(yNext, function()
        local updated = setterY(clampValue((getterY() or 0) + step))
        if updated == false then
            return
        end
        refresh()
        if markDirty then
            markDirty(id .. "_y")
        end
    end)

    refresh()
    return row
end

function Ui.addSettingRow(adapter, parent, id, label, value, x, y, width, section, active)
    adapter = adapter or {}
    local style, alignCenter = adapterStyle(adapter)
    local createWidget = adapter.create_widget
    local addToSection = adapter.add_to_section
    local fitText = adapter.fit_text or Ui.fitText
    if type(createWidget) ~= "function" or type(addToSection) ~= "function" then
        return nil
    end

    local row = createWidget("Button", parent, id .. "Row", "", x, y, width, 23)
    addToSection(section, row)

    local geometry = Ui.settingRowGeometry(x, width, adapter.layout)
    local valueWidth = geometry.value_width or 108
    local valueX = geometry.value_x or (x + width - valueWidth - 12)
    local nameWidth = geometry.name_width or (valueX - x - 16)
    local name = createWidget("Label", parent, id .. "Name", fitText(label, nameWidth, 1.02), geometry.name_x or (x + 8), y + (geometry.name_y_offset or 3), nameWidth, 15)
    Ui.styleControlName(name, style)
    addToSection(section, name)

    local valueBack = createWidget("Label", parent, id .. "ValueBack", "", valueX, y + (geometry.value_back_y_offset or 2), valueWidth, geometry.value_back_height or 18)
    addToSection(section, valueBack)

    local valueLabel = createWidget("Label", parent, id .. "Value", fitText(value, valueWidth - 8, 1.08), valueX + (geometry.value_label_x_offset or 4), y + (geometry.value_label_y_offset or 3), valueWidth - 8, geometry.value_label_height or 15)
    Ui.styleSettingState(row, valueBack, valueLabel, active, style, alignCenter)
    addToSection(section, valueLabel)

    return row, name, valueLabel, valueBack
end

function Ui.addToggleSettingRow(adapter, parent, id, label, getter, setter, x, y, width, section)
    adapter = adapter or {}
    local bindClick = adapter.bind_click
    local setWidgetText = adapter.set_widget_text or Ui.setWidgetText
    if type(bindClick) ~= "function" then
        return nil
    end
    local function valueText()
        return getter() and "ON" or "OFF"
    end
    local row, _, valueLabel, valueBack = Ui.addSettingRow(adapter, parent, id, label, valueText(), x, y, width, section, getter())
    local style, alignCenter = adapterStyle(adapter)
    Ui.styleStateValue(valueLabel, getter() and "on" or "off", style, alignCenter)
    bindClick(row, function()
        setter(not getter())
        setWidgetText(valueLabel, valueText())
        local style, alignCenter = adapterStyle(adapter)
        Ui.styleSettingState(row, valueBack, valueLabel, getter(), style, alignCenter)
        Ui.styleStateValue(valueLabel, getter() and "on" or "off", style, alignCenter)
        if type(adapter.sync_from_ui) == "function" then
            adapter.sync_from_ui()
        end
        if type(adapter.mark_profile_dirty) == "function" then
            adapter.mark_profile_dirty(id)
        end
    end)
    return row
end

function Ui.sectionBodyGeometry(panelX, bodyY, panelW, bodyH)
    return Primitives.sectionBodyGeometry(panelX, bodyY, panelW, bodyH)
end

function Ui.mergePanelRendererContext(base, extra)
    return Primitives.mergeContext(base, extra)
end

function Ui.sidebarTabs(layout)
    return Composition.sidebarTabs(layout)
end

function Ui.sidebarGeometry(layout, visibleTabs)
    return Composition.sidebarGeometry(layout, visibleTabs)
end

function Ui.huntingSubtabs(panelX, bodyY, panelW)
    return Composition.huntingSubtabs(panelX, bodyY, panelW)
end

function Ui.subtabContentY(bodyY)
    return Composition.subtabContentY(bodyY)
end

function Ui.toolsSubtabs(panelX, bodyY, panelW)
    return Composition.toolsSubtabs(panelX, bodyY, panelW)
end

function Ui.toolsTableHeaders(panelX, contentY, panelW)
    return Composition.toolsTableHeaders(panelX, contentY, panelW)
end

function Ui.cavebotDelayChoices()
    return Composition.cavebotDelayChoices()
end

function Ui.cavebotReachChoices()
    return Composition.cavebotReachChoices()
end

function Ui.msText(value)
    return Composition.msText(value)
end

function Ui.cavebotActionSpecs(panelX, panelW, layout, callbacks)
    return Composition.cavebotActionSpecs(panelX, panelW, layout, callbacks)
end

function Ui.renderOverviewPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local cfg = ctx.config or {}
    local helper = ctx.helper or {}
    local widgets = ctx.widgets or helper.widgets or {}
    local profileName = ctx.display_profile_name and ctx.display_profile_name() or ""

    ctx.add_section_scaffold(window, {section = "overview", body_id = "ctoaOverviewBody", header_id = "ctoaOverviewHeader", title = "Overview", subtitle = "compact live status"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.add_table_header(window, "ctoaOverviewTableHead", "Live status", "Value", panelX, ctx.body_y, panelW, "overview")
    widgets.overview_character = ctx.add_metric_card(window, "ctoaOverviewCharacter", "Character", profileName, panelX, layout.row_1_y, panelW, "overview", true)
    widgets.overview_health = ctx.add_metric_card(window, "ctoaOverviewHealth", "HP / MP", "0% / 0%", panelX, layout.row_2_y, panelW, "overview", true)
    widgets.overview_target = ctx.add_metric_card(window, "ctoaOverviewTarget", "Target", "none", panelX, layout.row_3_y, panelW, "overview", false)
    widgets.overview_modules = ctx.add_metric_card(window, "ctoaOverviewModules", "Modules", "Healing / Targeting", panelX, layout.row_4_y, panelW, "overview", true)
    widgets.overview_magic = ctx.add_metric_card(window, "ctoaOverviewMagic", "Magic", "Rotation / Rune", panelX, layout.row_5_y, panelW, "overview", false)
    widgets.overview_mobs = ctx.add_footer_strip(window, "ctoaOverviewMobs", "Monsters: nearby 0 / visible 0", panelX, layout.row_6_y, panelW, "overview")
    widgets.overview_readiness_runtime = ctx.add_footer_strip(window, "ctoaOverviewReadinessRuntime", "Runtime: pending", panelX, layout.row_7_y, panelW, "overview")
    widgets.overview_readiness_prototype = ctx.add_footer_strip(window, "ctoaOverviewReadinessPrototype", "Prototype: pending", panelX, layout.row_7_y + 22, panelW, "overview")
    widgets.overview_next = ctx.add_footer_strip(window, "ctoaOverviewNext", "Next action: idle", panelX, layout.footer_y, panelW, "overview")
end

function Ui.updateOverviewStats(ctx, snapshot)
    if not ctx then
        return false
    end
    local widgets = ctx.widgets or {}
    local data = snapshot or {}
    local width = tonumber(ctx.content_width) or 320
    local tools = data.tools or {}

    if widgets.overview_character then
        ctx.set_metric_text(widgets.overview_character, "Character", tostring(data.profile_name or ""), width)
    end
    if widgets.overview_health then
        ctx.set_metric_text(widgets.overview_health, "HP / MP", tostring(data.hp or 0) .. "% / " .. tostring(data.mp or 0) .. "%", width)
    end
    if widgets.overview_target then
        ctx.set_metric_text(widgets.overview_target, "Target", Ui.shortText(data.target_name or "none", 18), width)
    end
    if widgets.overview_modules then
        ctx.set_metric_text(widgets.overview_modules, "Modules", tostring(data.module_summary or "modules unavailable"), width)
    end
    if widgets.overview_magic then
        local magicText = (tools.spell_rotation and "Rotation" or "No rotation") .. " / " .. (tools.rune_enabled and "Rune" or "No rune")
        ctx.set_metric_text(widgets.overview_magic, "Magic", magicText, width)
    end
    if widgets.overview_next and widgets.overview_next.setText then
        widgets.overview_next:setText(Ui.fitText("Next action: " .. tostring(data.next_action or "idle"), width - 14, 0.84))
    end
    if widgets.overview_mobs and widgets.overview_mobs.setText then
        widgets.overview_mobs:setText("Monsters: nearby " .. tostring(data.nearby or 0) .. " / visible " .. tostring(data.visible or 0))
    end
    if widgets.overview_readiness_runtime and widgets.overview_readiness_runtime.setText then
        widgets.overview_readiness_runtime:setText(Ui.fitText("Runtime: " .. tostring(data.runtime_readiness or "modules unavailable"), width - 148, 0.78))
    end
    if widgets.overview_readiness_prototype and widgets.overview_readiness_prototype.setText then
        widgets.overview_readiness_prototype:setText(Ui.fitText("Prototype: " .. tostring(data.prototype_readiness or "modules unavailable"), width - 148, 0.78))
    end
    if widgets.ui_boot_status and widgets.ui_boot_status.setText then
        widgets.ui_boot_status:setText(Ui.fitText(tostring(data.boot_status or "Boot status unavailable"), width - 14, 0.78))
        Ui.styleOperatorState(widgets.ui_boot_status, data.boot_state, ctx.ui_style, ctx.align_left)
    end
    if widgets.ui_pipeline_status and widgets.ui_pipeline_status.setText then
        widgets.ui_pipeline_status:setText(Ui.fitText(tostring(data.pipeline_status or "Decision pipeline idle"), width - 14, 0.78))
        Ui.styleOperatorState(widgets.ui_pipeline_status, data.pipeline_state, ctx.ui_style, ctx.align_left)
    end
    if widgets.enabled then
        local runtimeState = Ui.normalizeOperatorState(data.runtime_state)
        Ui.setWidgetText(widgets.enabled, string.upper(runtimeState))
        Ui.styleOperatorState(widgets.enabled, runtimeState, ctx.ui_style, ctx.align_center)
    end
    return true
end

function Ui.updateDiagnosticsSnapshot(ctx, values, rows)
    if not ctx then
        return false
    end
    local widgets = ctx.widgets or {}
    local fitText = ctx.fit_text or Ui.fitText
    local width = tonumber(ctx.content_width) or 320
    local descriptors = type(rows) == "table" and rows or {
        {widget = "tools_api_snapshot", text = "api", scale = 0.78},
        {widget = "tools_diag_core", text = "api", scale = 0.78},
        {widget = "tools_diag_flags", text = "flags", scale = 0.82},
        {widget = "tools_diag_detail", text = "movement", scale = 0.72},
        {widget = "tools_diag_magic", text = "magic_loot", scale = 0.72},
        {widget = "tools_diag_export", text = "buffer", scale = 0.86},
    }
    local data = values or {}
    for _, row in ipairs(descriptors) do
        local widget = widgets[row.widget or ""]
        local text = data[row.text or ""]
        if widget and widget.setText and text ~= nil then
            widget:setText(fitText(tostring(text), width - 14, row.scale or 0.78))
        end
    end
    return true
end

function Ui.refreshOperatorSummaries(ctx)
    if not ctx then
        return false
    end
    local widgets = ctx.widgets or {}
    local layout = ctx.layout or {}
    local fitText = ctx.fit_text or Ui.fitText
    local summaries = ctx.summaries or {}
    local titleWidth = (layout.title_w or 420) - 220
    local contentWidth = (layout.content_w or 394) - 28
    local rows = {
        {key = "title_state", text = summaries.title, width = titleWidth, scale = 0.86},
        {key = "healing_summary", text = summaries.healing, width = contentWidth, scale = 0.88},
        {key = "heal_friend_summary", text = summaries.heal_friend, width = contentWidth, scale = 0.88},
        {key = "conditions_summary", text = summaries.conditions, width = contentWidth, scale = 0.88},
        {key = "equipment_summary", text = summaries.equipment, width = contentWidth, scale = 0.88},
        {key = "scripting_summary", text = summaries.scripting, width = contentWidth, scale = 0.88},
        {key = "hunting_targeting_summary", text = summaries.targeting, width = contentWidth, scale = 0.88},
        {key = "hunting_magic_summary", text = summaries.magic, width = contentWidth, scale = 0.88},
        {key = "tools_summary", text = summaries.tools, width = contentWidth, scale = 0.88},
        {key = "profile_summary", text = summaries.profile, width = contentWidth, scale = 0.88},
        {key = "ui_summary", text = summaries.ui, width = contentWidth, scale = 0.88}
    }
    for _, row in ipairs(rows) do
        local widget = widgets[row.key]
        if widget and widget.setText and row.text then
            widget:setText(fitText(row.text, row.width, row.scale))
        end
    end
    return true
end

function Ui.renderHealingPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local healing = (ctx.config or {}).healing or {}
    local helper = ctx.helper or {}

    ctx.add_section_scaffold(window, {section = "healing", body_id = "ctoaHealingBody", header_id = "ctoaHealingHeader", title = "Healing", subtitle = "HP / MP recovery"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.widgets.healing_summary = ctx.add_summary_strip(window, "ctoaHealingSummary", ctx.healing_summary_text, panelX, ctx.body_y, panelW, "healing")
    ctx.add_priority_badge(window, "ctoaHealingSpellPriority", "1", panelX, layout.row_1_y + 2, "healing", healing.spell_enabled)
    ctx.add_toggle_setting_row(window, "ctoaSpellHeal", "HP spell", function() return healing.spell_enabled end, function(value) helper.setRuntimeModuleEnabled({"healing", "spell_enabled"}, value, "spell healing") end, panelX + 26, layout.row_1_y, panelW - 26, "healing")
    ctx.add_profile_step_row(window, "ctoaSpellThresholdHealing", "HP spell %", function() return healing.spell_threshold end, function(value) healing.spell_threshold = value end, 5, 1, 100, panelX + 26, layout.row_2_y, panelW - 26, "healing", ctx.percent_text)
    ctx.add_profile_cycle_row(window, "ctoaSpellNameHealing", "Spell", function() return healing.spell end, function(value) healing.spell = value end, ctx.spell_choices, panelX + 26, layout.row_3_y, panelW - 26, "healing", ctx.spell_text)
    ctx.add_priority_badge(window, "ctoaHealingPotionPriority", "2", panelX, layout.row_4_y + 2, "healing", healing.potion_enabled)
    ctx.add_toggle_setting_row(window, "ctoaPotionHeal", "HP potion", function() return healing.potion_enabled end, function(value) helper.setRuntimeModuleEnabled({"healing", "potion_enabled"}, value, "potion healing") end, panelX + 26, layout.row_4_y, panelW - 26, "healing")
    ctx.add_profile_step_row(window, "ctoaPotionThresholdHealing", "HP pot %", function() return healing.potion_threshold end, function(value) healing.potion_threshold = value end, 1, 1, 100, panelX + 26, layout.row_5_y, panelW - 26, "healing", ctx.percent_text)
    ctx.add_profile_cycle_row(window, "ctoaPotionHotkeyHealing", "HP box", function() return healing.potion_hotkey end, function(value) healing.potion_hotkey = value; healing.potion_actionbar_slot = value end, ctx.hotkey_choices, panelX + 26, layout.row_6_y, panelW - 26, "healing", ctx.profile_number_text)
    ctx.add_priority_badge(window, "ctoaHealingManaPotionPriority", "3", panelX, layout.row_7_y + 2, "healing", healing.mana_potion_enabled)
    ctx.add_toggle_setting_row(window, "ctoaManaPotionHeal", "MP potion", function() return healing.mana_potion_enabled end, function(value) helper.setRuntimeModuleEnabled({"healing", "mana_potion_enabled"}, value, "mana potion") end, panelX + 26, layout.row_7_y, panelW - 26, "healing")
    ctx.add_profile_step_row(window, "ctoaManaPotionThresholdHealing", "MP pot %", function() return healing.mana_potion_threshold end, function(value) healing.mana_potion_threshold = value end, 1, 1, 100, panelX + 26, layout.row_7_y + 26, panelW - 26, "healing", ctx.percent_text)
    ctx.add_profile_cycle_row(window, "ctoaManaPotionHotkeyHealing", "MP box", function() return healing.mana_potion_hotkey end, function(value) healing.mana_potion_hotkey = value; healing.mana_potion_actionbar_slot = value end, ctx.hotkey_choices, panelX + 26, layout.row_7_y + 52, panelW - 26, "healing", ctx.profile_number_text)
    local bridgeButtonW = math.floor((panelW - 8) / 3)
    ctx.widgets.recovery_bridge_arm = ctx.create_widget("Button", window, "ctoaRecoveryBridgeArm", "ARM bridge", panelX, layout.footer_y, bridgeButtonW, 22)
    ctx.widgets.recovery_bridge_dry_run = ctx.create_widget("Button", window, "ctoaRecoveryBridgeDryRun", "Dry run", panelX + bridgeButtonW + 4, layout.footer_y, bridgeButtonW, 22)
    ctx.widgets.recovery_bridge_kill = ctx.create_widget("Button", window, "ctoaRecoveryBridgeKill", "KILL", panelX + (bridgeButtonW + 4) * 2, layout.footer_y, bridgeButtonW, 22)
    for _, widget in ipairs({ctx.widgets.recovery_bridge_arm, ctx.widgets.recovery_bridge_dry_run, ctx.widgets.recovery_bridge_kill}) do
        ctx.style_action_button(widget, widget == ctx.widgets.recovery_bridge_kill and "danger" or "primary", true)
        ctx.add_to_section("healing", widget)
    end
    ctx.bind_click(ctx.widgets.recovery_bridge_arm, helper.recoveryBridgeArm)
    ctx.bind_click(ctx.widgets.recovery_bridge_dry_run, helper.recoveryBridgeDryRun)
    ctx.bind_click(ctx.widgets.recovery_bridge_kill, helper.recoveryBridgeKill)
    ctx.widgets.last_potion = ctx.add_footer_strip(window, "ctoaLastPotion", "Bridge: " .. helper.recoveryBridgeStatus() .. " | Last potion: none", panelX, layout.footer_y + 24, panelW, "healing")
end

function Ui.renderHealFriendPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local healFriend = (ctx.config or {}).heal_friend or {}

    ctx.add_section_scaffold(window, {section = "heal_friend", body_id = "ctoaHealFriendBody", header_id = "ctoaHealFriendHeader", title = "Heal Friend", subtitle = "sio planner / whitelist"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.widgets.heal_friend_summary = ctx.add_summary_strip(window, "ctoaHealFriendSummary", ctx.heal_friend_summary_text, panelX, ctx.body_y, panelW, "heal_friend")
    ctx.add_toggle_setting_row(window, "ctoaHealFriendPlanner", "Planner", function() return healFriend.enabled end, function(value) healFriend.enabled = value == true end, panelX, layout.row_2_y, panelW, "heal_friend")
    ctx.add_toggle_setting_row(window, "ctoaHealFriendObserveParty", "Observe party", function() return healFriend.observe_party end, function(value) healFriend.observe_party = value == true end, panelX, layout.row_3_y, panelW, "heal_friend")
    ctx.add_profile_cycle_row(window, "ctoaHealFriendSpell", "Sio spell", function() return healFriend.sio_spell end, function(value) healFriend.sio_spell = value end, ctx.sio_spell_choices, panelX, layout.row_4_y, panelW, "heal_friend", ctx.spell_text)
    ctx.add_profile_step_row(window, "ctoaHealFriendThreshold", "Friend HP", function() return healFriend.hp_threshold end, function(value) healFriend.hp_threshold = value end, 5, 1, 100, panelX, layout.row_5_y, panelW, "heal_friend", ctx.percent_text)
    ctx.add_profile_cycle_row(window, "ctoaHealFriendPriority", "Priority", function() return healFriend.priority end, function(value) healFriend.priority = value end, ctx.heal_friend_priority_choices, panelX, layout.row_6_y, panelW, "heal_friend", ctx.heal_friend_priority_text)
    ctx.add_toggle_setting_row(window, "ctoaHealFriendRequireWhitelist", "Whitelist only", function() return healFriend.require_whitelist end, function(value) healFriend.require_whitelist = value == true end, panelX, layout.row_7_y, panelW, "heal_friend")
    ctx.add_profile_step_row(window, "ctoaHealFriendCooldown", "Cooldown", function() return healFriend.cooldown_ms end, function(value) healFriend.cooldown_ms = value end, 250, 500, 5000, panelX, layout.row_7_y + 26, panelW, "heal_friend", ctx.ms_text)
    ctx.widgets.heal_friend_status = ctx.add_footer_strip(window, "ctoaHealFriendStatus", "Status: read-only pending; no sio cast until sandbox whitelist smoke passes", panelX, layout.footer_y, panelW, "heal_friend")
end

function Ui.renderConditionsPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local conditions = (ctx.config or {}).conditions or {}

    ctx.add_section_scaffold(window, {section = "conditions", body_id = "ctoaConditionsBody", header_id = "ctoaConditionsHeader", title = "Conditions", subtitle = "state observer / no actions"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.widgets.conditions_summary = ctx.add_summary_strip(window, "ctoaConditionsSummary", ctx.conditions_summary_text, panelX, ctx.body_y, panelW, "conditions")
    ctx.add_toggle_content_rows(window, {
        {id = "ctoaConditionsObserver", label = "Observer", getter = function() return conditions.enabled end, setter = function(value) conditions.enabled = value == true end, y = layout.row_2_y, section = "conditions"},
        {id = "ctoaConditionsStates", label = "Read states", getter = function() return conditions.observe_states end, setter = function(value) conditions.observe_states = value == true end, y = layout.row_3_y, section = "conditions"},
        {id = "ctoaConditionsShield", label = "Mana shield", getter = function() return conditions.mana_shield end, setter = function(value) conditions.mana_shield = value == true end, y = layout.row_4_y, section = "conditions"},
        {id = "ctoaConditionsParalyze", label = "Paralyze", getter = function() return conditions.paralyze end, setter = function(value) conditions.paralyze = value == true end, y = layout.row_5_y, section = "conditions"},
        {id = "ctoaConditionsPoison", label = "Poison", getter = function() return conditions.poison end, setter = function(value) conditions.poison = value == true end, y = layout.row_6_y, section = "conditions"}
    }, panelX, panelW)
    ctx.add_profile_step_row(window, "ctoaConditionsSampleMs", "Sample", function() return conditions.sample_interval_ms end, function(value) conditions.sample_interval_ms = value end, 250, 500, 5000, panelX, layout.row_7_y, panelW, "conditions", ctx.ms_text)
    ctx.add_toggle_setting_row(window, "ctoaConditionsApiProbe", "API probe", function() return conditions.api_probe_enabled ~= false end, function(value) conditions.api_probe_enabled = value == true end, panelX, layout.row_7_y + 26, panelW, "conditions")
    ctx.widgets.conditions_status = ctx.add_footer_strip(window, "ctoaConditionsStatus", "Status: read-only pending", panelX, layout.footer_y, panelW, "conditions")
end

function Ui.renderEquipmentPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local equipment = (ctx.config or {}).equipment or {}

    ctx.add_section_scaffold(window, {section = "equipment", body_id = "ctoaEquipmentBody", header_id = "ctoaEquipmentHeader", title = "Equipment", subtitle = "slot observer / no swaps"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.widgets.equipment_summary = ctx.add_summary_strip(window, "ctoaEquipmentSummary", ctx.equipment_summary_text, panelX, ctx.body_y, panelW, "equipment")
    local rows = {
        {id = "ctoaEquipmentObserver", label = "Observer", getter = function() return equipment.enabled end, setter = function(value) equipment.enabled = value == true end, y = layout.row_2_y, section = "equipment"},
        {id = "ctoaEquipmentSlots", label = "Read slots", getter = function() return equipment.observe_slots end, setter = function(value) equipment.observe_slots = value == true end, y = layout.row_3_y, section = "equipment"}
    }
    local familyYs = {layout.row_4_y, layout.row_5_y, layout.row_6_y}
    for index, family in ipairs(ctx.equipment_family_rows or {}) do
        if familyYs[index] then
            local key = tostring(family.key or "")
            rows[#rows + 1] = {
                id = "ctoaEquipmentFamily" .. tostring(index),
                label = tostring(family.label or "Equipment family"),
                getter = function() return type(equipment.family_enabled) == "table" and equipment.family_enabled[key] == true end,
                setter = function(value)
                    if type(ctx.set_equipment_family_enabled) == "function" then ctx.set_equipment_family_enabled(key, value == true) end
                end,
                y = familyYs[index],
                section = "equipment"
            }
        end
    end
    ctx.add_toggle_content_rows(window, rows, panelX, panelW)
    ctx.add_profile_cycle_row(window, "ctoaEquipmentWeaponSet", "Weapon set", function() return equipment.weapon_set end, function(value) equipment.weapon_set = value end, {"manual", "shield", "two_hand"}, panelX, layout.row_6_y, panelW, "equipment", tostring)
    ctx.add_profile_step_row(window, "ctoaEquipmentHp", "HP guard", function() return equipment.hp_threshold end, function(value) equipment.hp_threshold = value end, 5, 1, 100, panelX, layout.row_7_y, panelW, "equipment", ctx.percent_text)
    ctx.add_toggle_setting_row(window, "ctoaEquipmentApiProbe", "API probe", function() return equipment.api_probe_enabled ~= false end, function(value) equipment.api_probe_enabled = value == true end, panelX, layout.row_7_y + 26, panelW, "equipment")
    ctx.widgets.equipment_status = ctx.add_footer_strip(window, "ctoaEquipmentStatus", "Status: read-only pending; swap runtime gated", panelX, layout.footer_y, panelW, "equipment")
end

function Ui.renderScriptingPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local scripting = (ctx.config or {}).scripting or {}
    local policyText = ctx.build_scripting_policy_snapshot or function() return "policy unavailable" end

    ctx.add_section_scaffold(window, {section = "scripting", body_id = "ctoaScriptingBody", header_id = "ctoaScriptingHeader", title = "Scripting", subtitle = "policy shell / no eval"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.widgets.scripting_summary = ctx.add_summary_strip(window, "ctoaScriptingSummary", ctx.scripting_summary_text, panelX, ctx.body_y, panelW, "scripting")
    ctx.add_toggle_setting_row(window, "ctoaScriptingPolicy", "Policy shell", function() return scripting.enabled end, function(value) scripting.enabled = value == true; policyText() end, panelX, layout.row_2_y, panelW, "scripting")
    ctx.add_profile_cycle_row(window, "ctoaScriptingMode", "Policy mode", function() return scripting.policy_mode end, function(value) scripting.policy_mode = value; policyText() end, {"deny_all", "audit_only"}, panelX, layout.row_3_y, panelW, "scripting", tostring)
    ctx.add_toggle_setting_row(window, "ctoaScriptingSnippets", "Snippets", function() return scripting.allow_user_snippets end, function(value) scripting.allow_user_snippets = false; policyText() end, panelX, layout.row_4_y, panelW, "scripting")
    ctx.add_toggle_setting_row(window, "ctoaScriptingEval", "Runtime eval", function() return scripting.allow_runtime_eval end, function(value) scripting.allow_runtime_eval = false; policyText() end, panelX, layout.row_5_y, panelW, "scripting")
    ctx.add_toggle_setting_row(window, "ctoaScriptingAudit", "Audit log", function() return scripting.audit_log end, function(value) scripting.audit_log = value == true end, panelX, layout.row_6_y, panelW, "scripting")
    ctx.add_toggle_setting_row(window, "ctoaScriptingSandbox", "Sandbox req", function() return scripting.sandbox_required end, function(value) scripting.sandbox_required = value ~= false end, panelX, layout.row_7_y, panelW, "scripting")
    ctx.add_setting_row(window, "ctoaScriptingCommand", "Command model", tostring(scripting.command_model or "none"), panelX, layout.row_7_y + 26, panelW, "scripting", true)
    ctx.widgets.scripting_status = ctx.add_footer_strip(window, "ctoaScriptingStatus", "Status: " .. policyText(), panelX, layout.footer_y, panelW, "scripting")
end

function Ui.ruleEditorNavigation(count, index, delta)
    return Primitives.ruleEditorNavigation(count, index, delta)
end

function Ui.addRuleEditorChrome(ctx, window, spec)
    spec = spec or {}
    local add = spec.add
    if type(add) ~= "function" then
        return {}
    end
    local panelX = tonumber(spec.panel_x) or 0
    local panelW = tonumber(spec.panel_w) or 0
    local rowY = tonumber(spec.row_y) or 0
    local selector = add("Label", spec.selector_id, spec.empty_text or "0/0 no rules", panelX + 42, rowY + 3, panelW - 84, 16)
    Ui.styleLabel(selector, "accent", ctx.ui_style, ctx.align_center)
    local previous = add("Button", spec.previous_id, "<", panelX, rowY, 34, 22)
    local nextRule = add("Button", spec.next_id, ">", panelX + panelW - 34, rowY, 34, 22)
    Ui.styleMiniButton(previous, ctx.ui_style, ctx.align_center)
    Ui.styleMiniButton(nextRule, ctx.ui_style, ctx.align_center)
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

function Ui.addTargetRuleEditor(ctx, window, tools, panelX, panelW, layout)
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

    local chrome = Ui.addRuleEditorChrome(ctx, window, {
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
            selectedIndex = Ui.ruleEditorNavigation(current.count, current.index, -1).index
            widgets.target_rule_refresh()
        end,
        on_next = function()
            local current = state()
            selectedIndex = Ui.ruleEditorNavigation(current.count, current.index, 1).index
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
    Ui.styleLabel(nameLabel, "muted", ctx.ui_style)
    local nameEdit = add("TextEdit", "ctoaTargetRuleName", "", panelX + 132, layout.row_3_y, panelW - 132, 22)
    Ui.styleTextEdit(nameEdit, ctx.ui_style)
    if nameEdit and nameEdit.setMaxLength then pcall(function() nameEdit:setMaxLength(64) end) end

    local values = {}
    local function addPair(id, label, leftKey, rightKey, y, suffix)
        local labelWidget = add("Label", id .. "Label", label, panelX, y + 3, 98, 18)
        Ui.styleLabel(labelWidget, "muted", ctx.ui_style)
        local function group(key, x)
            local minus = add("Button", id .. key .. "Minus", "-", x, y, 24, 22)
            local value = add("Label", id .. key .. "Value", "0", x + 26, y + 3, 48, 16)
            local plus = add("Button", id .. key .. "Plus", "+", x + 76, y, 24, 22)
            Ui.styleMiniButton(minus, ctx.ui_style, ctx.align_center)
            Ui.styleLabel(value, "default", ctx.ui_style, ctx.align_center)
            Ui.styleMiniButton(plus, ctx.ui_style, ctx.align_center)
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
    Ui.styleLabel(priorityLabel, "muted", ctx.ui_style)
    local priorityMinus = add("Button", "ctoaTargetRulePriorityMinus", "-", panelX + 82, layout.row_7_y, 24, 22)
    local priorityValue = add("Label", "ctoaTargetRulePriorityValue", "50", panelX + 108, layout.row_7_y + 3, 48, 16)
    local priorityPlus = add("Button", "ctoaTargetRulePriorityPlus", "+", panelX + 158, layout.row_7_y, 24, 22)
    local chaseButton = add("Button", "ctoaTargetRuleChase", "Chase inherit", panelX + 190, layout.row_7_y, panelW - 190, 22)
    Ui.styleMiniButton(priorityMinus, ctx.ui_style, ctx.align_center)
    Ui.styleLabel(priorityValue, "default", ctx.ui_style, ctx.align_center)
    Ui.styleMiniButton(priorityPlus, ctx.ui_style, ctx.align_center)
    Ui.styleToggleButton(chaseButton, false, ctx.ui_style, ctx.align_center)
    local enabledButton = add("Button", "ctoaTargetRuleEnabled", "Enabled OFF", panelX, layout.row_7_y + 26, panelW, 22)

    widgets.target_rule_refresh = function()
        local current = state()
        local rule = current.rule or {}
        loading = true
        Ui.setWidgetText(selector, current.summary or "0/0 no target rules")
        Ui.setWidgetText(nameEdit, rule.name_pattern or "")
        loading = false
        for key, item in pairs(values) do Ui.setWidgetText(item.widget, tostring(rule[key] or 0) .. item.suffix) end
        Ui.setWidgetText(priorityValue, tostring(rule.priority or 0))
        Ui.setWidgetText(chaseButton, "Chase " .. tostring(rule.chase_policy or "inherit"))
        Ui.styleToggleButton(chaseButton, rule.chase_policy ~= "inherit", ctx.ui_style, ctx.align_center)
        Ui.setWidgetText(enabledButton, "Enabled " .. (rule.enabled == true and "ON" or "OFF"))
        Ui.styleToggleButton(enabledButton, rule.enabled == true, ctx.ui_style, ctx.align_center)
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

function Ui.addMagicRuleEditor(ctx, window, tools, panelX, panelW, layout)
    local section = "hunting_magic"
    local widgets = ctx.widgets
    local loading = false
    local function add(kind, id, text, x, y, width, height)
        local widget = ctx.create_widget(kind, window, id, text, x, y, width, height)
        ctx.add_to_section(section, widget)
        return widget
    end
    local chrome = Ui.addRuleEditorChrome(ctx, window, {
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
    Ui.styleLabel(wordsLabel, "muted", ctx.ui_style)
    local wordsEdit = add("TextEdit", "ctoaMagicRuleWords", "", panelX + 104, layout.row_3_y, panelW - 104, 22)
    Ui.styleTextEdit(wordsEdit, ctx.ui_style)
    if wordsEdit and wordsEdit.setMaxLength then pcall(function() wordsEdit:setMaxLength(64) end) end

    local valueWidgets = {}
    local function addNumberRow(id, label, key, y, step)
        local name = add("Label", id .. "Label", label, panelX, y + 3, 126, 18)
        Ui.styleLabel(name, "muted", ctx.ui_style)
        local minus = add("Button", id .. "Minus", "-", panelX + panelW - 144, y, 28, 22)
        local value = add("Label", id .. "Value", "0", panelX + panelW - 110, y + 3, 70, 16)
        local plus = add("Button", id .. "Plus", "+", panelX + panelW - 34, y, 34, 22)
        Ui.styleMiniButton(minus, ctx.ui_style, ctx.align_center)
        Ui.styleLabel(value, "default", ctx.ui_style, ctx.align_center)
        Ui.styleMiniButton(plus, ctx.ui_style, ctx.align_center)
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
        Ui.setWidgetText(selector, state.summary or "0/0 no spell rules")
        Ui.setWidgetText(wordsEdit, rule.words or "")
        loading = false
        Ui.setWidgetText(valueWidgets.min_nearby, tostring(rule.min_nearby or 0))
        Ui.setWidgetText(valueWidgets.max_nearby, tostring(rule.max_nearby or 0))
        Ui.setWidgetText(valueWidgets.cooldown_ms, tostring(rule.cooldown_ms or 0) .. " ms")
        Ui.setWidgetText(valueWidgets.scan_range, tostring(rule.scan_range or 0) .. " sqm")
        for key, item in pairs(toggles) do
            local active = rule[key] == true
            Ui.setWidgetText(item.button, item.label .. " " .. (active and "ON" or "OFF"))
            Ui.styleToggleButton(item.button, active, ctx.ui_style, ctx.align_center)
        end
    end
    if wordsEdit then
        wordsEdit.onTextChange = function(_, text)
            if not loading then ctx.update_magic_rule({words = text}) end
        end
    end
    widgets.magic_rule_refresh()
end

function Ui.addCombatActionRuleEditor(ctx, window, tools, panelX, panelW, layout)
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

    local chrome = Ui.addRuleEditorChrome(ctx, window, {
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
            selectedIndex = Ui.ruleEditorNavigation(current.count, current.index, -1).index
            widgets.combat_action_rule_refresh()
        end,
        on_next = function()
            local current = state()
            selectedIndex = Ui.ruleEditorNavigation(current.count, current.index, 1).index
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
    Ui.styleLabel(textLabel, "muted", ctx.ui_style)
    local textEdit = add("TextEdit", "ctoaCombatActionText", "", panelX + 104, layout.row_3_y, panelW - 104, 22)
    Ui.styleTextEdit(textEdit, ctx.ui_style)
    if textEdit and textEdit.setMaxLength then pcall(function() textEdit:setMaxLength(64) end) end

    local splitGap = 6
    local splitW = math.floor((panelW - splitGap) / 2)
    local kindButton = add("Button", "ctoaCombatActionKind", "Kind rune", panelX, layout.row_4_y, splitW, 22)
    local modeButton = add("Button", "ctoaCombatActionMode", "Box F5", panelX + splitW + splitGap, layout.row_4_y, splitW, 22)

    local values = {}
    local function addNumber(id, label, key, x, width, y, step)
        local labelWidget = add("Label", id .. "Label", label, x, y + 3, math.max(54, width - 108), 18)
        Ui.styleLabel(labelWidget, "muted", ctx.ui_style)
        local minus = add("Button", id .. "Minus", "-", x + width - 102, y, 24, 22)
        local value = add("Label", id .. "Value", "0", x + width - 76, y + 3, 48, 16)
        local plus = add("Button", id .. "Plus", "+", x + width - 24, y, 24, 22)
        Ui.styleMiniButton(minus, ctx.ui_style, ctx.align_center)
        Ui.styleLabel(value, "default", ctx.ui_style, ctx.align_center)
        Ui.styleMiniButton(plus, ctx.ui_style, ctx.align_center)
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
        Ui.setWidgetText(selector, current.summary or "0/0 no action rules")
        Ui.setWidgetText(textEdit, rule.action_text or "")
        loading = false
        Ui.setWidgetText(kindButton, "Kind " .. tostring(rule.kind or "rune"))
        local mode = rule.kind == "stance" and tostring(rule.stance_mode or "offensive") or tostring(rule.hotkey or "none")
        Ui.setWidgetText(modeButton, (rule.kind == "stance" and "Mode " or "Box ") .. mode)
        Ui.setWidgetText(values.min_count, tostring(rule.min_count or 0))
        Ui.setWidgetText(values.max_count, tostring(rule.max_count or 0))
        Ui.setWidgetText(values.cooldown_ms, tostring(rule.cooldown_ms or 0) .. " ms")
        for key, item in pairs(toggles) do
            local active = rule[key] == true
            Ui.setWidgetText(item.button, item.label .. " " .. (active and "ON" or "OFF"))
            Ui.styleToggleButton(item.button, active, ctx.ui_style, ctx.align_center)
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

function Ui.renderHuntingPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local bodyY = ctx.body_y
    local bodyH = ctx.body_h
    local contentY = ctx.content_y or Ui.subtabContentY(bodyY)
    local cfg = ctx.config or {}
    local tools = cfg.tools or {}
    local helper = ctx.helper or {}

    ctx.add_section_scaffold(window, {section = "hunting", body_id = "ctoaHuntingBody", header_id = "ctoaHuntingHeader", title = "Hunting", subtitle = "targeting / magic shooter"}, panelX, bodyY, panelW, bodyH)
    ctx.add_subtab_buttons(window, "huntingSubtabs", "hunting", panelX, bodyY, panelW)
    ctx.bind_click(ctx.widgets.hunting_targeting_tab, function() ctx.switch_hunting_subtab("targeting") end)
    ctx.bind_click(ctx.widgets.hunting_target_rules_tab, function() ctx.switch_hunting_subtab("target_rules") end)
    ctx.bind_click(ctx.widgets.hunting_magic_tab, function() ctx.switch_hunting_subtab("magic") end)
    ctx.bind_click(ctx.widgets.hunting_actions_tab, function() ctx.switch_hunting_subtab("actions") end)
    ctx.bind_click(ctx.widgets.hunting_magic_runtime_tab, function() ctx.switch_hunting_subtab("magic_runtime") end)

    ctx.widgets.hunting_targeting_summary = ctx.add_summary_strip(window, "ctoaHuntingTargetingSummary", ctx.targeting_summary_text, panelX, contentY, panelW, "hunting_targeting")
    ctx.add_toggle_setting_row(window, "ctoaAutoAttack", "Targeting", function() return tools.auto_attack end, function(value) helper.setRuntimeModuleEnabled({"tools", "auto_attack"}, value, "targeting") end, panelX, layout.row_2_y, panelW, "hunting_targeting")
    ctx.add_toggle_setting_row(window, "ctoaChaseTargeting", "Chase", function() return tools.chase == true end, function(value) tools.chase = value == true end, panelX, layout.row_3_y, panelW, "hunting_targeting")
    ctx.add_toggle_setting_row(window, "ctoaHoldTarget", "Hold Target", function() return tools.hold_target end, function(value) tools.hold_target = value end, panelX, layout.row_4_y, panelW, "hunting_targeting")
    ctx.add_profile_cycle_row(window, "ctoaAttackRange", "Attack range", function() return tools.attack_range end, function(value) tools.attack_range = value end, ctx.tool_range_choices, panelX, layout.row_5_y, panelW, "hunting_targeting", ctx.profile_number_text)
    local function addNamePolicyEditor(id, label, key, y)
        local labelWidth = math.min(104, math.floor(panelW * 0.26))
        local editorX = panelX + labelWidth + 8
        local editorWidth = panelW - labelWidth - 8
        local labelWidget = ctx.create_widget("Label", window, id .. "Label", label, panelX, y + 3, labelWidth, 18)
        Ui.styleLabel(labelWidget, "muted", ctx.ui_style)
        ctx.add_to_section("hunting_targeting", labelWidget)
        local value = type(ctx.format_target_name_list) == "function" and ctx.format_target_name_list(key) or ""
        local editor = ctx.create_widget("TextEdit", window, id, value, editorX, y, editorWidth, 22)
        Ui.styleTextEdit(editor, ctx.ui_style)
        if editor and editor.setMaxLength then
            pcall(function() editor:setMaxLength(1024) end)
        end
        if editor then
            editor.onTextChange = function(_, text)
                if type(ctx.update_target_name_list) == "function" then
                    ctx.update_target_name_list(key, text)
                end
            end
        end
        ctx.add_to_section("hunting_targeting", editor)
        return editor
    end
    ctx.widgets.target_rule_editor_ignored = addNamePolicyEditor("ctoaTargetRuleEditorIgnored", "Ignored names", "ignored_names", layout.row_6_y)
    ctx.widgets.target_rule_editor_priority = addNamePolicyEditor("ctoaTargetRuleEditorPriority", "Priority order", "priority_names", layout.row_7_y)
    ctx.widgets.monster_stats = ctx.add_footer_strip(window, "ctoaMonsterStats", "Comma separated | priority order is left to right", panelX, layout.footer_y, panelW, "hunting_targeting")

    ctx.widgets.hunting_target_rules_summary = ctx.add_summary_strip(window, "ctoaHuntingTargetRulesSummary", "Ordered filters | mandatory safety guards stay outside rules", panelX, contentY, panelW, "hunting_target_rules")
    Ui.addTargetRuleEditor(ctx, window, tools, panelX, panelW, layout)
    ctx.widgets.target_rules_footer = ctx.add_footer_strip(window, "ctoaTargetRulesFooter", "Profile data only | lower priority number wins", panelX, layout.footer_y + 10, panelW, "hunting_target_rules")

    ctx.widgets.hunting_magic_summary = ctx.add_summary_strip(window, "ctoaHuntingMagicSummary", ctx.magic_summary_text, panelX, contentY, panelW, "hunting_magic")
    Ui.addMagicRuleEditor(ctx, window, tools, panelX, panelW, layout)
    ctx.widgets.magic_footer = ctx.add_footer_strip(window, "ctoaMagicFooter", "Profile data only | actions remain runtime-gated", panelX, layout.footer_y + 10, panelW, "hunting_magic")

    ctx.widgets.hunting_actions_summary = ctx.add_summary_strip(window, "ctoaHuntingActionsSummary", "Ordered rune / stance rules | arbitrary server words", panelX, contentY, panelW, "hunting_actions")
    Ui.addCombatActionRuleEditor(ctx, window, tools, panelX, panelW, layout)
    ctx.widgets.hunting_actions_footer = ctx.add_footer_strip(window, "ctoaHuntingActionsFooter", "Profile data only | global activation remains on Runtime", panelX, layout.footer_y + 10, panelW, "hunting_actions")

    ctx.widgets.hunting_magic_runtime_summary = ctx.add_summary_strip(window, "ctoaHuntingMagicRuntimeSummary", ctx.magic_summary_text, panelX, contentY, panelW, "hunting_magic_runtime")
    ctx.add_toggle_setting_row(window, "ctoaSpellRotation", "Spell Rotation", function() return tools.spell_rotation end, function(value) helper.setRuntimeModuleEnabled({"tools", "spell_rotation"}, value, "spell rotation") end, panelX, layout.row_2_y, panelW, "hunting_magic_runtime")
    ctx.add_toggle_setting_row(window, "ctoaRuneShooter", "Rune Shooter", function() return tools.rune_enabled end, function(value) helper.setRuntimeModuleEnabled({"tools", "rune_enabled"}, value, "rune shooter") end, panelX, layout.row_3_y, panelW, "hunting_magic_runtime")
    ctx.add_toggle_setting_row(window, "ctoaAutoStanceMagic", "Auto stance", function() return tools.auto_stance end, function(value) helper.setRuntimeModuleEnabled({"tools", "auto_stance"}, value, "auto stance") end, panelX, layout.row_4_y, panelW, "hunting_magic_runtime")
    ctx.add_profile_cycle_row(window, "ctoaMagicPriority", "Priority", function() return tools.magic_priority or "rotation" end, function(value) tools.magic_priority = value end, ctx.magic_priority_choices, panelX, layout.row_5_y, panelW, "hunting_magic_runtime", ctx.magic_priority_text)
    ctx.add_profile_step_row(window, "ctoaRotationLockMs", "Spell lock", function() return tools.attack_action_lock_ms or 1050 end, function(value) tools.attack_action_lock_ms = value; tools.rotation_interval_ms = value end, 250, 750, 3000, panelX, layout.row_6_y, panelW, "hunting_magic_runtime", function(value) return tostring(value) .. " ms" end)
    ctx.add_toggle_setting_row(window, "ctoaAutoExetaMagic", "Auto exeta", function() return tools.auto_exeta end, function(value) helper.setRuntimeModuleEnabled({"tools", "auto_exeta"}, value, "auto exeta") end, panelX, layout.row_7_y, panelW, "hunting_magic_runtime")
    ctx.widgets.magic_runtime_footer = ctx.add_footer_strip(window, "ctoaMagicRuntimeFooter", "Decision: waiting for runtime", panelX, layout.footer_y, panelW, "hunting_magic_runtime")
end

function Ui.renderCavebotPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local cfg = ctx.config or {}
    local tools = cfg.tools or {}
    local helper = ctx.helper or {}

    ctx.add_section_scaffold(window, {section = "cavebot", body_id = "ctoaCavebotBody", header_id = "ctoaCavebotHeader", title = "CaveBot", subtitle = "simple waypoint loop"}, panelX, ctx.body_y, panelW, ctx.body_h)
    ctx.add_table_header(window, "ctoaCavebotTableHead", "Route", "Value", panelX, ctx.body_y, panelW, "cavebot")
    ctx.add_toggle_setting_row(window, "ctoaCavebotEnabled", "Cavebot", function() return tools.cavebot_enabled end, function(value) helper.setRuntimeModuleEnabled({"tools", "cavebot_enabled"}, value, "cavebot") end, panelX, layout.row_2_y, panelW, "cavebot")
    ctx.add_toggle_setting_row(window, "ctoaCavebotMovement", "Movement", function() return tools.cavebot_movement_enabled end, function(value) helper.setRuntimeModuleEnabled({"tools", "cavebot_movement_enabled"}, value, "cavebot movement") end, panelX, layout.row_3_y, panelW, "cavebot")
    ctx.add_profile_cycle_row(window, "ctoaCavebotDelay", "Step delay", function() return tools.cavebot_step_delay_ms end, function(value) tools.cavebot_step_delay_ms = value end, ctx.cavebot_delay_choices or Ui.cavebotDelayChoices(), panelX, layout.row_4_y, panelW, "cavebot", ctx.ms_text or Ui.msText)
    ctx.add_profile_cycle_row(window, "ctoaCavebotReach", "Reach dist", function() return tools.cavebot_reach_distance end, function(value) tools.cavebot_reach_distance = value end, ctx.cavebot_reach_choices or Ui.cavebotReachChoices(), panelX, layout.row_5_y, panelW, "cavebot", ctx.profile_number_text)

    local _, _, cavebotWpCount = ctx.add_setting_row(window, "ctoaCavebotWpCount", "Waypoints", tostring(#(tools.cavebot_waypoints or {})), panelX, layout.row_6_y, panelW, "cavebot", true)
    ctx.widgets.cavebot_wp_count = cavebotWpCount
    local _, _, cavebotCurrent = ctx.add_setting_row(window, "ctoaCavebotCurrent", "Current", tostring(tools.cavebot_index or 1), panelX, layout.row_7_y, panelW, "cavebot", true)
    ctx.widgets.cavebot_current = cavebotCurrent

    local actionW, buttons = Ui.cavebotActionSpecs(panelX, panelW, layout, {
        add = ctx.add_current_cavebot_waypoint,
        delete = ctx.delete_current_cavebot_waypoint,
        up = function() ctx.move_current_cavebot_waypoint(-1) end,
        down = function() ctx.move_current_cavebot_waypoint(1) end,
        prev = function() ctx.select_cavebot_waypoint(-1) end,
        next = function() ctx.select_cavebot_waypoint(1) end,
        clear = ctx.clear_cavebot_waypoints,
        test_walk = ctx.test_cavebot_auto_walk
    })
    for _, spec in ipairs(buttons) do
        ctx.widgets[spec.key] = ctx.create_widget("Button", window, spec.id, spec.text, spec.x, spec.y, actionW, 20)
        ctx.style_action_button(ctx.widgets[spec.key], spec.role, true)
        ctx.add_to_section("cavebot", ctx.widgets[spec.key])
        ctx.bind_click(ctx.widgets[spec.key], spec.callback)
    end
    ctx.widgets.cavebot_status = ctx.add_footer_strip(window, "ctoaCavebotStatus", "Status: idle", panelX, layout.footer_y + 28, panelW, "cavebot")
end

function Ui.renderToolsPanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local panelX = ctx.panel_x
    local panelW = ctx.panel_w
    local bodyY = ctx.body_y
    local bodyH = ctx.body_h
    local contentY = ctx.content_y or Ui.subtabContentY(bodyY)
    local cfg = ctx.config or {}
    local tools = cfg.tools or {}
    local helper = ctx.helper or {}
    local featureFlags = tools.feature_flags or {}

    ctx.add_section_scaffold(window, {section = "tools", body_id = "ctoaToolsBody", header_id = "ctoaToolsHeader", title = "Tools", subtitle = "helper / PvP / timer / diag"}, panelX, bodyY, panelW, bodyH)
    ctx.add_subtab_buttons(window, "toolsSubtabs", "tools", panelX, bodyY, panelW)
    ctx.bind_click(ctx.widgets.tools_helper_tab, function() ctx.switch_tools_subtab("helper") end)
    ctx.bind_click(ctx.widgets.tools_pvp_tab, function() ctx.switch_tools_subtab("pvp") end)
    ctx.bind_click(ctx.widgets.tools_timer_tab, function() ctx.switch_tools_subtab("timer") end)
    ctx.bind_click(ctx.widgets.tools_diag_tab, function() ctx.switch_tools_subtab("diag") end)
    ctx.add_table_headers(window, Ui.toolsTableHeaders(panelX, contentY, panelW))

    ctx.widgets.tools_summary = ctx.add_summary_strip(window, "ctoaToolsSummary", ctx.tools_summary_text, panelX, contentY, panelW, "tools_helper")
    ctx.add_toggle_content_rows(window, {
        {id = "ctoaChaseTools", label = "Chase mode", getter = function() return tools.chase == true end, setter = function(value) tools.chase = value == true end, y = layout.row_2_y, section = "tools_helper"},
        {id = "ctoaAutoHasteTools", label = "Auto Haste", getter = function() return tools.auto_haste end, setter = function(value) helper.setRuntimeModuleEnabled({"tools", "auto_haste"}, value, "auto haste") end, y = layout.row_3_y, section = "tools_helper"},
        {id = "ctoaAutoExetaTools", label = "Auto Exeta", getter = function() return tools.auto_exeta end, setter = function(value) helper.setRuntimeModuleEnabled({"tools", "auto_exeta"}, value, "auto exeta") end, y = layout.row_4_y, section = "tools_helper"},
        {id = "ctoaPauseInPzTools", label = "Pause in PZ", getter = function() return tools.pause_in_pz end, setter = function(value) tools.pause_in_pz = value end, y = layout.row_6_y, section = "tools_helper"}
    }, panelX, panelW)
    ctx.add_profile_step_row(window, "ctoaExetaMinVisible", "Exeta min mobs", function() return tools.exeta_min_visible end, function(value) tools.exeta_min_visible = value end, 1, 1, 8, panelX, layout.row_5_y, panelW, "tools_helper", ctx.profile_number_text)
    ctx.widgets.tools_api_snapshot = ctx.add_footer_strip(window, "ctoaToolsApiSnapshot", "API: pending probe", panelX, layout.row_7_y, panelW, "tools_helper")
    ctx.add_footer_strip(window, "ctoaToolsFooter", "Support modules active only outside PZ", panelX, layout.footer_y, panelW, "tools_helper")

    ctx.add_toggle_content_rows(window, {
        {id = "ctoaRunePvpSafeTools", label = "Rune PvP safe", getter = function() return tools.rune_pvp_safe end, setter = function(value) tools.rune_pvp_safe = value end, y = layout.row_2_y, section = "tools_pvp"},
        {id = "ctoaHoldTargetPvp", label = "Hold Target", getter = function() return tools.hold_target end, setter = function(value) tools.hold_target = value end, y = layout.row_3_y, section = "tools_pvp"},
        {id = "ctoaPauseInPzPvp", label = "Pause in PZ", getter = function() return tools.pause_in_pz end, setter = function(value) tools.pause_in_pz = value end, y = layout.row_4_y, section = "tools_pvp"},
        {id = "ctoaRuneRequiresTargetPvp", label = "Rune needs target", getter = function() return tools.rune_requires_target end, setter = function(value) tools.rune_requires_target = value end, y = layout.row_5_y, section = "tools_pvp"}
    }, panelX, panelW)
    ctx.add_footer_strip(window, "ctoaToolsPvpFooter", "PvP guards protect shooter and targeting", panelX, layout.footer_y, panelW, "tools_pvp")

    ctx.add_toggle_setting_row(window, "ctoaToolsTimerEnabled", "Timer enabled", function() return tools.timer_enabled end, function(value) helper.setRuntimeModuleEnabled({"tools", "timer_enabled"}, value, "timer") end, panelX, layout.row_2_y, panelW, "tools_timer")
    ctx.add_profile_cycle_row(window, "ctoaToolsTimerInterval", "Interval", function() return tools.timer_interval_ms end, function(value) tools.timer_interval_ms = value end, ctx.timer_interval_choices, panelX, layout.row_3_y, panelW, "tools_timer", ctx.timer_interval_text)
    ctx.add_setting_row(window, "ctoaToolsTimerMessage", "Message", ctx.short_text(tools.timer_message or "timer", 10), panelX, layout.row_4_y, panelW, "tools_timer", true)
    ctx.add_footer_strip(window, "ctoaToolsTimerFooter", "Timer UI ready; action loop stays disabled by default", panelX, layout.footer_y, panelW, "tools_timer")

    ctx.widgets.tools_diag_core = ctx.add_footer_strip(window, "ctoaToolsDiagCore", "API: pending probe", panelX, layout.row_2_y, panelW, "tools_diag")
    ctx.widgets.tools_diag_flags = ctx.add_footer_strip(window, "ctoaToolsDiagFlags", ctx.feature_flags_text(), panelX, layout.row_3_y, panelW, "tools_diag")
    ctx.widgets.tools_diag_detail = ctx.add_footer_strip(window, "ctoaToolsDiagMove", "Move: pending", panelX, layout.row_4_y, panelW, "tools_diag")
    ctx.widgets.tools_diag_magic = ctx.add_footer_strip(window, "ctoaToolsDiagMagic", "Magic: pending | Loot: pending", panelX, layout.row_5_y, panelW, "tools_diag")
    ctx.add_toggle_setting_row(window, "ctoaToolsDiagEnabled", "Diagnostics", function() return featureFlags.diagnostics == true end, function(value) tools.feature_flags = tools.feature_flags or {}; tools.feature_flags.diagnostics = value == true; ctx.refresh_api_snapshot_ui() end, panelX, layout.row_6_y, panelW, "tools_diag")
    ctx.widgets.tools_diag_export = ctx.add_footer_strip(window, "ctoaToolsDiagExport", ctx.diagnostics_buffer_text(), panelX, layout.row_7_y, panelW, "tools_diag")
    ctx.add_footer_strip(window, "ctoaToolsDiagFooter", "Read-only diagnostics; no runtime action is triggered", panelX, layout.footer_y, panelW, "tools_diag")
end

function Ui.renderProfilePanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local cfg = ctx.config or {}
    local healing = cfg.healing or {}
    local modules = cfg.modules or {}

    ctx.add_section_scaffold(window, {section = "profile", body_id = "ctoaProfileBody", header_id = "ctoaProfileHeader", title = "Profile", subtitle = "healing / modules / presets"}, ctx.panel_x, ctx.body_y, ctx.panel_w, ctx.body_h)
    ctx.widgets.profile_summary = ctx.add_summary_strip(window, "ctoaProfileSummary", ctx.profile_summary_text, ctx.panel_x, ctx.body_y, ctx.panel_w, "profile")
    ctx.add_profile_cycle_row(window, "ctoaProfileSpell", "Heal spell", function() return healing.spell end, function(value) healing.spell = value end, ctx.spell_choices, ctx.profile_left_x, layout.profile_row_1_y, ctx.profile_col_w, "profile", ctx.spell_text)
    ctx.add_profile_step_row(window, "ctoaProfileSpellThreshold", "Spell HP", function() return healing.spell_threshold end, function(value) healing.spell_threshold = value end, 1, 1, 100, ctx.profile_left_x, layout.profile_row_2_y, ctx.profile_col_w, "profile", function(value) return "<= " .. tostring(value) .. "%" end)
    ctx.add_profile_cycle_row(window, "ctoaProfilePotionHotkey", "HP hotkey", function() return healing.potion_hotkey end, function(value) healing.potion_hotkey = value; healing.potion_actionbar_slot = value end, ctx.hotkey_choices, ctx.profile_left_x, layout.profile_row_3_y, ctx.profile_col_w, "profile", ctx.profile_number_text)
    ctx.add_profile_step_row(window, "ctoaProfilePotionThreshold", "Potion HP", function() return healing.potion_threshold end, function(value) healing.potion_threshold = value end, 1, 1, 100, ctx.profile_left_x, layout.profile_row_4_y, ctx.profile_col_w, "profile", function(value) return "<= " .. tostring(value) .. "%" end)
    ctx.add_profile_cycle_row(window, "ctoaProfileManaHotkey", "MP hotkey", function() return healing.mana_potion_hotkey end, function(value) healing.mana_potion_hotkey = value; healing.mana_potion_actionbar_slot = value end, ctx.hotkey_choices, ctx.profile_left_x, layout.profile_row_5_y, ctx.profile_col_w, "profile", ctx.profile_number_text)
    ctx.add_profile_step_row(window, "ctoaProfileThresholdJitter", "Random +/-", function() return healing.threshold_jitter_percent or 3 end, function(value) healing.threshold_jitter_percent = value end, 1, 0, 5, ctx.profile_left_x, layout.profile_row_6_y, ctx.profile_col_w, "profile", function(value) return tostring(value) .. "%" end)

    local moduleRows = {
        {id = "ctoaModuleHealFriend", label = "Heal Friend", key = "heal_friend", y = layout.profile_row_1_y},
        {id = "ctoaModuleConditions", label = "Conditions", key = "conditions", y = layout.profile_row_2_y},
        {id = "ctoaModuleCavebot", label = "CaveBot", key = "cavebot", y = layout.profile_row_3_y},
        {id = "ctoaModuleEquipment", label = "Equipment", key = "equipment", y = layout.profile_row_4_y},
        {id = "ctoaModuleHelper", label = "Helper tools", key = "helper", y = layout.profile_row_5_y},
        {id = "ctoaModuleScripting", label = "Scripting", key = "scripting", y = layout.profile_row_6_y},
    }
    for _, row in ipairs(moduleRows) do
        local moduleKey = row.key
        ctx.add_profile_cycle_row(window, row.id, row.label, function() return ctx.module_visible(moduleKey) end, function(value) modules[moduleKey] = value == true; ctx.set_module_visible(moduleKey, value) end, {false, true}, ctx.profile_right_x, row.y, ctx.profile_col_w, "profile", ctx.profile_bool_text)
    end
    ctx.widgets.profile_status = ctx.add_footer_strip(window, "ctoaProfileStatus", "Autosave: live", ctx.profile_left_x, layout.profile_footer_y, ctx.profile_status_w, "profile")
    ctx.widgets.profile_save = ctx.create_widget("Button", window, "ctoaProfileSave", "Save now", ctx.profile_save_x, layout.profile_save_y, layout.profile_save_w, layout.profile_save_h)
    ctx.style_action_button(ctx.widgets.profile_save, "primary", true)
    ctx.add_to_section("profile", ctx.widgets.profile_save)
    ctx.bind_click(ctx.widgets.profile_save, ctx.flush_profile_save)
end

function Ui.renderEnginePanel(ctx)
    if not ctx then
        return
    end
    local layout = ctx.layout or {}
    local window = ctx.window
    local cfg = ctx.config or {}

    ctx.add_section_scaffold(window, {section = "ui", body_id = "ctoaUiBody", header_id = "ctoaUiRuntimeHeader", title = "Settings", subtitle = "hotkey / appearance / HUD"}, ctx.panel_x, ctx.body_y, ctx.panel_w, ctx.body_h)
    ctx.widgets.ui_summary = ctx.add_summary_strip(window, "ctoaUiSummary", ctx.ui_summary_text, ctx.panel_x, ctx.body_y, ctx.panel_w, "ui")
    ctx.add_profile_cycle_row(window, "ctoaUiHotkey", "Hotkey", function() return ctx.hotkey_display_text(cfg.hotkey) end, function(value) ctx.apply_hotkey_choice(value) end, ctx.ui_hotkey_choices, ctx.profile_left_x, layout.ui_runtime_row_1_y, ctx.profile_col_w, "ui", ctx.profile_number_text, ctx.mark_ui_prefs_dirty)
    ctx.add_profile_step_row(window, "ctoaUiAutoHide", "Hide", function() return cfg.auto_hide_ms end, function(value) cfg.auto_hide_ms = value; ctx.update_auto_hide_timer() end, 250, 0, 5000, ctx.profile_right_x, layout.ui_runtime_row_1_y, ctx.profile_col_w, "ui", ctx.auto_hide_text, ctx.mark_ui_prefs_dirty)
    ctx.add_profile_cycle_row(window, "ctoaUiHudEnabled", "HUD enabled", function() return cfg.hud and cfg.hud.enabled end, function(value) cfg.hud = cfg.hud or {}; cfg.hud.enabled = value; ctx.apply_hud_prefs() end, {false, true}, ctx.panel_x, layout.ui_runtime_row_2_y, ctx.panel_w, "ui", ctx.profile_bool_text, ctx.mark_ui_prefs_dirty)
    ctx.add_vector_step_row(window, "ctoaUiHudPos", "HUD position", function() return cfg.hud and cfg.hud.x or 22 end, function(value) cfg.hud = cfg.hud or {}; cfg.hud.x = value; ctx.apply_hud_prefs() end, function() return cfg.hud and cfg.hud.y or 170 end, function(value) cfg.hud = cfg.hud or {}; cfg.hud.y = value; ctx.apply_hud_prefs() end, 5, 0, 500, ctx.panel_x, layout.ui_runtime_row_3_y, layout.ui_value_row_w, "ui", ctx.profile_number_text, ctx.profile_number_text, ctx.mark_ui_prefs_dirty)

    ctx.add_section_band(window, "ctoaUiThemeHeader", "Theme", "palette", ctx.panel_x, layout.ui_theme_section_y, ctx.panel_w, "ui")
    ctx.add_profile_cycle_row(window, "ctoaUiThemePreset", "Theme preset", function() return cfg.theme_preset or "graphite" end, ctx.set_theme_preset, ctx.theme_presets, ctx.panel_x, layout.ui_theme_row_1_y, ctx.panel_w, "ui", ctx.theme_preset_text)
    ctx.add_section_band(window, "ctoaUiLayoutHeader", "Layout", "compact / position", ctx.panel_x, layout.ui_layout_section_y, ctx.panel_w, "ui")
    ctx.add_profile_cycle_row(window, "ctoaUiCompactMode", "Compact mode", function() return cfg.compact_mode and true or false end, ctx.set_compact_mode, {false, true}, ctx.panel_x, layout.ui_layout_row_1_y, ctx.panel_w, "ui", ctx.profile_bool_text)
    ctx.add_vector_step_row(window, "ctoaUiWindowPos", "Window position", function() return cfg.window_x or 520 end, function(value) cfg.window_x = value; ctx.apply_window_placement() end, function() return cfg.window_y or 34 end, function(value) cfg.window_y = value; ctx.apply_window_placement() end, 10, 0, 2000, ctx.panel_x, layout.ui_layout_row_2_y, layout.ui_value_row_w, "ui", ctx.profile_number_text, ctx.profile_number_text, ctx.mark_ui_prefs_dirty)
    ctx.widgets.ui_boot_status = ctx.add_footer_strip(window, "ctoaUiBootStatus", "Boot status pending", ctx.panel_x, layout.footer_y, ctx.panel_w, "ui")
    ctx.widgets.ui_pipeline_status = ctx.add_footer_strip(window, "ctoaUiPipelineStatus", "Decision pipeline idle", ctx.panel_x, layout.footer_y + 22, ctx.panel_w, "ui")
end

function Ui.contract()
    return {
        module = "ctoa_helper_ui",
        mode = "guarded_ui_primitives",
        owns_text_fit = true,
        owns_widget_style = true,
        owns_widget_create_wrapper = true,
        owns_nav_style = true,
        owns_adaptive_sidebar_geometry = true,
        owns_panel_renderer_context_merge = true,
        owns_utility_navigation_divider = true,
        owns_subtab_style = true,
        owns_button_style = true,
        owns_button_roles = true,
        owns_runtime_state_badge = true,
        owns_four_state_operator_feedback = true,
        owns_bounded_rule_editor_navigation = true,
        owns_state_value_colors = true,
        owns_rule_card_style = true,
        owns_rule_editor_chrome = true,
        owns_single_settings_surface = true,
        owns_magic_rule_editor = true,
        owns_magic_runtime_subtab = true,
        owns_target_rule_editor = true,
        owns_action_parameter_editor = true,
        owns_combat_action_rule_editor = true,
        owns_metric_style = true,
        owns_setting_state_style = true,
        owns_text_edit_style = true,
        owns_profile_field_style = true,
        owns_vector_row_style = true,
        owns_section_style = true,
        owns_strip_style = true,
        owns_badge_style = true,
        owns_label_style = true,
        owns_window_chrome_style = true,
        owns_toggle_style = true,
        owns_checkbox_style = true,
        owns_sidebar_card_style = true,
        owns_overview_avatar_style = true,
        owns_control_name_style = true,
        owns_layout_modes = true,
        owns_row_geometry = true,
        owns_metric_card_geometry = true,
        owns_metric_text_plan = true,
        owns_setting_row_builders = true,
        owns_interactive_row_builders = true,
        owns_section_scaffold = true,
        owns_tab_metadata = true,
        owns_subtab_content_metadata = true,
        owns_cavebot_action_metadata = true,
        owns_operator_summary_refresh = true,
        owns_overview_panel_renderer = true,
        owns_overview_stats_update = true,
        owns_diagnostics_snapshot_update = true,
        owns_cavebot_panel_renderer = true,
        owns_engine_panel_renderer = true,
        owns_engine_status_rows = true,
        owns_healing_panel_renderer = true,
        owns_heal_friend_panel_renderer = true,
        owns_conditions_panel_renderer = true,
        owns_hunting_panel_renderer = true,
        owns_target_name_policy_editor = true,
        owns_equipment_panel_renderer = true,
        owns_profile_panel_renderer = true,
        owns_scripting_panel_renderer = true,
        owns_tools_panel_renderer = true,
        runtime_actions = false,
        executes_plans = false,
        dispatch_allowed = false,
        casts = false,
        talks = false,
        attacks = false,
        walks = false,
        uses_items = false,
    }
end

_G.CTOA_HELPER_UI = Ui
return Ui
