-- ctoa_helper_hud.lua [CTOA OTClient Native]
-- Passive HUD text helpers. It never creates widgets or triggers runtime actions.

local Hud = rawget(_G, "CTOA_HELPER_HUD") or {}

local DEFAULT_X = 22
local DEFAULT_Y = 170
local DEFAULT_WIDTH = 210
local DEFAULT_HEIGHT = 54

function Hud.startText()
    return "ZeroBot | starting"
end

function Hud.disarmedText()
    return "ZeroBot | runtime disarmed"
end

function Hud.position(config)
    local hud = config or {}
    return {
        x = tonumber(hud.x) or DEFAULT_X,
        y = tonumber(hud.y) or DEFAULT_Y
    }
end

function Hud.state(config, runtime)
    local hud = config or {}
    local runtimeState = runtime or {}
    local pos = Hud.position(hud)
    return {
        enabled = hud.enabled == true,
        visible = hud.enabled == true and runtimeState.visible ~= false,
        draggable = hud.draggable == true,
        x = pos.x,
        y = pos.y,
        width = tonumber(hud.width) or DEFAULT_WIDTH,
        height = tonumber(hud.height) or DEFAULT_HEIGHT,
        profile = tostring(runtimeState.profile or "profile"),
        decision = tostring(runtimeState.decision or "idle")
    }
end

function Hud.visibilityText(state)
    local hudState = state or {}
    if hudState.enabled ~= true then
        return "disabled"
    end
    if hudState.visible == false then
        return "hidden"
    end
    if hudState.draggable == true then
        return "visible draggable"
    end
    return "visible locked"
end

function Hud.runtimeText(options)
    options = options or {}
    local version = tostring(options.version or "?")
    local profile = tostring(options.profile or "profile")
    local hp = tonumber(options.hp) or 0
    local mp = tonumber(options.mp) or 0
    local nearby = tonumber(options.nearby) or 0
    local visible = tonumber(options.visible) or 0
    local decision = tostring(options.decision or "idle")
    return "ZeroBot " .. version .. " | " .. profile ..
        "\nHP " .. tostring(hp) .. "% MP " .. tostring(mp) .. "% | Mobs " .. tostring(nearby) .. "/" .. tostring(visible) ..
        "\n" .. decision
end

function Hud.uiSummary(config, helpers)
    helpers = helpers or {}
    local hud = config or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local state = Hud.state(hud, {})
    return "HUD " .. onOffText(state.enabled) ..
        " | " .. Hud.visibilityText(state) ..
        " | " .. tostring(state.x) .. "," .. tostring(state.y) ..
        " | " .. tostring(state.width) .. "x" .. tostring(state.height)
end

function Hud.operatorSummary(config, helpers)
    helpers = helpers or {}
    local cfg = config or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local hotkeyDisplayText = helpers.hotkeyDisplayText or tostring
    local themePresetText = helpers.themePresetText or tostring
    local hudText = Hud.uiSummary(cfg.hud or {}, helpers)
    return "Hotkey " .. hotkeyDisplayText(cfg.hotkey) ..
        " | " .. hudText ..
        " | Compact " .. onOffText(cfg.compact_mode == true) ..
        " | Theme " .. themePresetText(cfg.theme_preset or "classic")
end

function Hud.contract()
    return {
        mode = "passive",
        creates_widgets = false,
        owns_start_text = true,
        owns_disarmed_text = true,
        owns_position = true,
        owns_runtime_text = true,
        owns_ui_summary = true,
        owns_operator_summary = true,
        runtime_actions = false,
        default_x = DEFAULT_X,
        default_y = DEFAULT_Y,
        default_width = DEFAULT_WIDTH,
        default_height = DEFAULT_HEIGHT,
        gate = "HUD static contract, UI preview, ModuleStaticGates, and in-world SmokeAttach -Tab tools_hud."
    }
end

_G.CTOA_HELPER_HUD = Hud
return Hud
