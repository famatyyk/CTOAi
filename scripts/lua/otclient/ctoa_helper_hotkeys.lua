-- ctoa_helper_hotkeys.lua [CTOA OTClient Native]
-- Passive hotkey text helpers. This module does not bind or send keys.

local Hotkeys = rawget(_G, "CTOA_HELPER_HOTKEYS") or {}

local MODIFIER_ORDER = {"Ctrl", "Alt", "Shift", "Meta"}
local MODIFIER_ALIASES = {
    ctrl = "Ctrl",
    control = "Ctrl",
    ctl = "Ctrl",
    alt = "Alt",
    shift = "Shift",
    meta = "Meta",
    cmd = "Meta",
    command = "Meta",
    win = "Meta",
    windows = "Meta",
}

local RESERVED_KEYS = {
    Escape = true,
    Enter = true,
    Return = true,
    Tab = true,
}

local function trim(value)
    if type(value) ~= "string" then
        return ""
    end
    return (value:gsub("^%s+", ""):gsub("%s+$", ""))
end

function Hotkeys.trim(value)
    return trim(value)
end

function Hotkeys.normalizeKeyName(value)
    local text = trim(value)
    if text == "" then
        return ""
    end
    local lowered = string.lower(text)
    if MODIFIER_ALIASES[lowered] then
        return MODIFIER_ALIASES[lowered]
    end
    local functionMatch = string.match(lowered, "^f(%d%d?)$")
    if functionMatch then
        local number = tonumber(functionMatch)
        if number and number >= 1 and number <= 24 then
            return "F" .. tostring(number)
        end
        return ""
    end
    if #text == 1 then
        return string.upper(text)
    end
    return text:gsub("^%l", string.upper)
end

function Hotkeys.normalize(value)
    local parsed = Hotkeys.parse(value)
    if parsed.valid then
        return parsed.normalized
    end
    return ""
end

function Hotkeys.parse(value)
    local text = trim(value)
    if text == "" then
        return {
            valid = false,
            normalized = "",
            reason = "empty",
            modifiers = {},
            key = ""
        }
    end
    local modifiers = {}
    local modifierList = {}
    local key = ""
    for part in string.gmatch(text, "[^+]+") do
        local normalized = Hotkeys.normalizeKeyName(part)
        if normalized == "" then
            return {
                valid = false,
                normalized = "",
                reason = "invalid_key",
                modifiers = modifierList,
                key = ""
            }
        end
        if MODIFIER_ALIASES[string.lower(normalized)] then
            local modifier = MODIFIER_ALIASES[string.lower(normalized)]
            modifiers[modifier] = true
        elseif normalized == "Ctrl" or normalized == "Alt" or normalized == "Shift" or normalized == "Meta" then
            modifiers[normalized] = true
        elseif key == "" then
            key = normalized
        else
            return {
                valid = false,
                normalized = "",
                reason = "multiple_keys",
                modifiers = modifierList,
                key = normalized
            }
        end
    end

    if key == "" then
        return {
            valid = false,
            normalized = "",
            reason = "missing_key",
            modifiers = modifierList,
            key = ""
        }
    end
    if RESERVED_KEYS[key] then
        return {
            valid = false,
            normalized = "",
            reason = "reserved_key",
            modifiers = modifierList,
            key = key
        }
    end

    local parts = {}
    for _, modifier in ipairs(MODIFIER_ORDER) do
        if modifiers[modifier] then
            table.insert(parts, modifier)
            table.insert(modifierList, modifier)
        end
    end
    table.insert(parts, key)
    return {
        valid = true,
        normalized = table.concat(parts, "+"),
        reason = "ok",
        modifiers = modifierList,
        key = key
    }
end

function Hotkeys.isAllowed(value, allowed)
    local normalized = Hotkeys.normalize(value)
    if normalized == "" or type(allowed) ~= "table" then
        return false
    end
    for _, candidate in ipairs(allowed) do
        if Hotkeys.normalize(candidate) == normalized then
            return true
        end
    end
    return false
end

function Hotkeys.bindingDecision(value, currentValue, allowed)
    local parsed = Hotkeys.parse(value)
    if not parsed.valid then
        return {
            allowed = false,
            reason = parsed.reason,
            normalized = "",
            previous = Hotkeys.normalize(currentValue),
            changed = false
        }
    end
    if type(allowed) == "table" and #allowed > 0 and not Hotkeys.isAllowed(parsed.normalized, allowed) then
        return {
            allowed = false,
            reason = "not_allowed",
            normalized = parsed.normalized,
            previous = Hotkeys.normalize(currentValue),
            changed = false
        }
    end
    local previous = Hotkeys.normalize(currentValue)
    return {
        allowed = true,
        reason = previous == parsed.normalized and "unchanged" or "changed",
        normalized = parsed.normalized,
        previous = previous,
        changed = previous ~= parsed.normalized
    }
end

function Hotkeys.display(value)
    local normalized = Hotkeys.normalize(value)
    if normalized == "" then
        return "unbound"
    end
    return normalized
end

function Hotkeys.actionbarSlotText(slot)
    if slot and slot ~= "" then
        return "actionbar " .. tostring(slot)
    end
    return "actionbar ?"
end

function Hotkeys.contract()
    return {
        mode = "passive",
        owns_actionbar_slot_text = true,
        owns_binding_decision = true,
        binds_keys = false,
        sends_keys = false,
        runtime_actions = false,
        modifier_order = MODIFIER_ORDER,
        gate = "Parser unit tests, safe boot check, UI preview, and no automatic new key bindings during loader init."
    }
end

_G.CTOA_HELPER_HOTKEYS = Hotkeys

return Hotkeys
