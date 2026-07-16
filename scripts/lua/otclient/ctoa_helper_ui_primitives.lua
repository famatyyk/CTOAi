-- ctoa_helper_ui_primitives.lua [CTOA OTClient Native]
-- Shared, passive widget/form primitives. No gameplay callbacks or runtime actions.

local Primitives = rawget(_G, "CTOA_HELPER_UI_PRIMITIVES") or {}

function Primitives.shortText(text, maxLen)
    text = tostring(text or "")
    maxLen = math.max(4, math.floor(tonumber(maxLen) or 24))
    if #text <= maxLen then
        return text
    end
    return string.sub(text, 1, maxLen - 3) .. "..."
end

function Primitives.fitText(text, width, fontScale)
    text = tostring(text or "")
    width = tonumber(width) or 80
    fontScale = tonumber(fontScale) or 0.9
    local approxCharPx = math.max(4.2, 6.2 * fontScale)
    local maxLen = math.max(4, math.floor(width / approxCharPx))
    return Primitives.shortText(text, maxLen)
end

function Primitives.setWidgetText(widget, text)
    if widget and widget.setText then
        widget:setText(text)
    end
end

function Primitives.setWidgetChecked(widget, checked)
    if widget and widget.setChecked then
        widget:setChecked(checked)
    end
end

function Primitives.getWidgetChecked(widget)
    if widget and widget.isChecked then
        return widget:isChecked()
    end
    return false
end

function Primitives.showWidget(widget, visible)
    if not widget then
        return
    end
    if visible and widget.show then
        widget:show()
    elseif not visible and widget.hide then
        widget:hide()
    end
end

function Primitives.createWidget(kind, parent, id, text, x, y, width, height)
    if not g_ui or not g_ui.createWidget then
        return nil
    end
    local ok, widget = pcall(function()
        return g_ui.createWidget(kind, parent)
    end)
    if not ok or not widget then
        return nil
    end
    if id and widget.setId then
        widget:setId(id)
    end
    Primitives.setWidgetText(widget, text or "")
    if widget.breakAnchors then
        widget:breakAnchors()
    end
    if widget.addAnchor and AnchorLeft and AnchorTop then
        widget:addAnchor(AnchorLeft, "parent", AnchorLeft)
        widget:addAnchor(AnchorTop, "parent", AnchorTop)
    end
    if widget.setMarginLeft then
        widget:setMarginLeft(x or 0)
    end
    if widget.setMarginTop then
        widget:setMarginTop(y or 0)
    elseif widget.setPosition then
        widget:setPosition({x = x or 0, y = y or 0})
    end
    if widget.resize then
        widget:resize(width or 120, height or 24)
    elseif widget.setWidth then
        widget:setWidth(width or 120)
        if widget.setHeight then
            widget:setHeight(height or 24)
        end
    end
    if widget.setTextAutoResize then
        widget:setTextAutoResize(false)
    end
    if kind == "Label" and widget.setPhantom then
        widget:setPhantom(true)
    end
    return widget
end

function Primitives.settingRowGeometry(x, width, layout)
    layout = layout or {}
    local valueWidth = math.max(92, (layout.value_w or 108))
    local valueX = x + width - valueWidth - 12
    return {
        value_width = valueWidth, value_x = valueX,
        name_width = valueX - x - 16, name_x = x + 8,
        name_y_offset = 3, value_back_y_offset = 2, value_back_height = 18,
        value_label_x_offset = 4, value_label_y_offset = 3, value_label_height = 15,
    }
end

function Primitives.metricCardGeometry(x, width)
    local labelWidth = math.floor(width * 0.42)
    local valueWidth = width - labelWidth - 18
    return {
        row_height = 23, label_width = labelWidth, value_width = valueWidth,
        label_x = x + 8, label_y_offset = 3, label_height = 15,
        value_x = x + labelWidth + 10, value_y_offset = 3, value_height = 15,
    }
end

function Primitives.profileFieldGeometry(x, width)
    local buttonWidth = 14
    local valueWidth = math.min(122, math.max(76, math.floor(width * 0.46)))
    local prevX = x + width - (buttonWidth * 2) - valueWidth - 10
    return {
        label_width = math.max(64, prevX - x - 14), prev_x = prevX,
        value_x = prevX + buttonWidth + 3, next_x = prevX + buttonWidth + valueWidth + 6,
        button_width = buttonWidth, value_width = valueWidth,
    }
end

function Primitives.sectionBodyGeometry(panelX, bodyY, panelW, bodyH)
    return {x = panelX - 2, y = bodyY, width = panelW + 4, height = bodyH}
end

function Primitives.mergeContext(base, extra)
    local context = {}
    for key, value in pairs(base or {}) do context[key] = value end
    for key, value in pairs(extra or {}) do context[key] = value end
    return context
end

function Primitives.ruleEditorNavigation(count, index, delta)
    local boundedCount = math.max(0, math.floor(tonumber(count) or 0))
    if boundedCount == 0 then
        return {index = 0, count = 0, can_previous = false, can_next = false, contained = true}
    end
    local current = math.max(1, math.min(boundedCount, math.floor(tonumber(index) or 1)))
    local selected = math.max(1, math.min(boundedCount, current + math.floor(tonumber(delta) or 0)))
    return {
        index = selected, count = boundedCount,
        can_previous = selected > 1, can_next = selected < boundedCount,
        contained = selected >= 1 and selected <= boundedCount,
    }
end

function Primitives.contract()
    return {
        mode = "passive",
        owns_widget_basics = true,
        owns_form_geometry = true,
        owns_bounded_rule_navigation = true,
        runtime_actions = false,
        dispatch_allowed = false,
        casts = false,
        attacks = false,
        walks = false,
        uses_items = false,
    }
end

_G.CTOA_HELPER_UI_PRIMITIVES = Primitives
return Primitives
