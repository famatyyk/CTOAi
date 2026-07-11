-- ctoa_native_heal.lua  [CTOA OTClient Native]
-- Passive, profile-fed recovery module for OTClient.

local DEFAULT_HEAL_SETTINGS = {
    enabled = false,
    pause_in_pz = true,
    spell_enabled = false,
    potion_enabled = false,
    mana_potion_enabled = false,
    hp_critical = 30,
    hp_low = 65,
    mana_low = 40,
    heal_spell = "exura",
    heal_critical_spell = "exura gran",
    mana_spell = "utani hur",
    potion_hotkey = "F1",
    mana_potion_hotkey = "F2",
    cooldown_ms = 1000,
    mana_cooldown_ms = 1000,
}

local Heal = {
    think_event = nil,
    last_hp_action_ms = 0,
    last_mp_action_ms = 0,
    last_log_ms = 0,
}

local function appendLog(msg)
    local paths = {"ctoa_local.log", "user_dir/ctoa_local.log"}
    if g_resources and g_resources.getUserDir then
        local ok, userDir = pcall(function()
            return g_resources.getUserDir()
        end)
        if ok and userDir then
            paths[#paths + 1] = userDir .. "/ctoa_local.log"
        end
    end
    for _, path in ipairs(paths) do
        local f = io.open(path, "a")
        if f then
            f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-OTC-HEAL] " .. msg .. "\n")
            f:close()
            return
        end
    end
end

local function nowMs()
    if g_clock and g_clock.millis then
        local ok, value = pcall(function()
            return g_clock.millis()
        end)
        if ok and type(value) == "number" then
            return value
        end
    end
    return math.floor(os.clock() * 1000)
end

local function mergeSettings(base, override)
    local result = {}
    for key, value in pairs(base or {}) do
        result[key] = value
    end
    for key, value in pairs(override or {}) do
        result[key] = value
    end
    return result
end

local function helperConfig()
    local helper = rawget(_G, "CTOA_Helper")
    if helper and helper.config then
        local healing = helper.config.healing or {}
        local tools = helper.config.tools or {}
        local config = mergeSettings(DEFAULT_HEAL_SETTINGS, {
            enabled = helper.config.enabled == true,
            pause_in_pz = tools.pause_in_pz ~= false,
            spell_enabled = healing.spell_enabled == true,
            potion_enabled = healing.potion_enabled == true,
            mana_potion_enabled = healing.mana_potion_enabled == true,
            hp_critical = healing.critical_threshold or 30,
            hp_low = healing.spell_threshold or DEFAULT_HEAL_SETTINGS.hp_low,
            mana_low = healing.mana_potion_threshold or DEFAULT_HEAL_SETTINGS.mana_low,
            heal_spell = healing.spell or DEFAULT_HEAL_SETTINGS.heal_spell,
            heal_critical_spell = healing.critical_spell or DEFAULT_HEAL_SETTINGS.heal_critical_spell,
            mana_spell = healing.mana_spell or DEFAULT_HEAL_SETTINGS.mana_spell,
            potion_hotkey = healing.potion_actionbar_slot or healing.potion_hotkey or DEFAULT_HEAL_SETTINGS.potion_hotkey,
            mana_potion_hotkey = healing.mana_potion_actionbar_slot or healing.mana_potion_hotkey or DEFAULT_HEAL_SETTINGS.mana_potion_hotkey,
            cooldown_ms = healing.cooldown_ms or DEFAULT_HEAL_SETTINGS.cooldown_ms,
            mana_cooldown_ms = healing.mana_potion_cooldown_ms or healing.cooldown_ms or DEFAULT_HEAL_SETTINGS.mana_cooldown_ms,
        })
        config.potion_threshold = healing.potion_threshold or config.hp_low
        return config
    end
    return DEFAULT_HEAL_SETTINGS
end

local function localPlayer()
    if g_game and g_game.getLocalPlayer then
        local ok, player = pcall(function()
            return g_game.getLocalPlayer()
        end)
        if ok then
            return player
        end
    end
    return nil
end

local function percent(current, maximum)
    if type(current) == "number" and type(maximum) == "number" and maximum > 0 then
        return math.floor((current / maximum) * 100)
    end
    return nil
end

local function readVitals(player, eventHealth, eventMaxHealth, eventMana, eventMaxMana)
    local vitals = {
        hp_percent = percent(eventHealth, eventMaxHealth),
        mana_percent = percent(eventMana, eventMaxMana),
    }
    if player then
        if not vitals.hp_percent and player.getHealth and player.getMaxHealth then
            local okHealth, health = pcall(function()
                return player:getHealth()
            end)
            local okMax, maxHealth = pcall(function()
                return player:getMaxHealth()
            end)
            if okHealth and okMax then
                vitals.hp_percent = percent(health, maxHealth)
            end
        end
        if not vitals.mana_percent and player.getMana and player.getMaxMana then
            local okMana, mana = pcall(function()
                return player:getMana()
            end)
            local okMax, maxMana = pcall(function()
                return player:getMaxMana()
            end)
            if okMana and okMax then
                vitals.mana_percent = percent(mana, maxMana)
            end
        end
        if not vitals.hp_percent and player.getHealthPercent then
            local ok, hp = pcall(function()
                return player:getHealthPercent()
            end)
            if ok then
                vitals.hp_percent = hp
            end
        end
        if not vitals.mana_percent and player.getManaPercent then
            local ok, mp = pcall(function()
                return player:getManaPercent()
            end)
            if ok then
                vitals.mana_percent = mp
            end
        end
    end
    return vitals
end

local function isInProtectionZone(player)
    if not player then
        return false
    end
    for _, methodName in ipairs({"isInPz", "isInProtectionZone", "isInSafeZone"}) do
        if player[methodName] then
            local ok, result = pcall(function()
                return player[methodName](player)
            end)
            if ok and result == true then
                return true
            end
        end
    end
    return false
end

local function castSpell(words)
    if words and words ~= "" and g_game and g_game.talk then
        local ok = pcall(function()
            g_game.talk(words)
        end)
        return ok
    end
    return false
end

local function pressHotkey(hotkey)
    if hotkey and hotkey ~= "" and g_keyboard and g_keyboard.pressKey then
        local ok = pcall(function()
            g_keyboard.pressKey(hotkey)
        end)
        return ok
    end
    return false
end

local function chooseHealSpell(config, hp)
    if hp <= (config.hp_critical or DEFAULT_HEAL_SETTINGS.hp_critical) then
        return config.heal_critical_spell
    end
    return config.heal_spell
end

local function maybeRecover(vitals, reason)
    local config = helperConfig()
    if not config.enabled then
        return false
    end
    local player = localPlayer()
    if config.pause_in_pz ~= false and isInProtectionZone(player) then
        return false
    end
    local now = nowMs()
    vitals = vitals or readVitals(player)
    local hp = vitals.hp_percent
    local mp = vitals.mana_percent

    if hp and config.potion_enabled and hp <= (config.potion_threshold or config.hp_low) and now - Heal.last_hp_action_ms >= (config.cooldown_ms or 1000) then
        if pressHotkey(config.potion_hotkey) then
            Heal.last_hp_action_ms = now
            appendLog("HP potion via " .. tostring(config.potion_hotkey) .. " at " .. tostring(hp) .. "%")
            return true
        end
    end

    if hp and config.spell_enabled and hp <= (config.hp_low or 65) and now - Heal.last_hp_action_ms >= (config.cooldown_ms or 1000) then
        local spell = chooseHealSpell(config, hp)
        if castSpell(spell) then
            Heal.last_hp_action_ms = now
            appendLog("HP spell " .. tostring(spell) .. " at " .. tostring(hp) .. "% (" .. tostring(reason or "tick") .. ")")
            return true
        end
    end

    if mp and config.mana_potion_enabled and mp <= (config.mana_low or 40) and now - Heal.last_mp_action_ms >= (config.mana_cooldown_ms or 1000) then
        if pressHotkey(config.mana_potion_hotkey) then
            Heal.last_mp_action_ms = now
            appendLog("MP potion via " .. tostring(config.mana_potion_hotkey) .. " at " .. tostring(mp) .. "%")
            return true
        end
    end

    return false
end

local function onHealthChanged(localPlayerArg, health, maxHealth)
    maybeRecover(readVitals(localPlayerArg or localPlayer(), health, maxHealth, nil, nil), "health event")
end

local function onManaChanged(localPlayerArg, mana, maxMana)
    maybeRecover(readVitals(localPlayerArg or localPlayer(), nil, nil, mana, maxMana), "mana event")
end

local function onThink()
    if g_game and g_game.isOnline and not g_game.isOnline() then
        return
    end
    maybeRecover(nil, "cycle")
end

local function init()
    if LocalPlayer and connect then
        pcall(function()
            connect(LocalPlayer, {
                onHealthChanged = onHealthChanged,
                onManaChanged = onManaChanged,
            })
        end)
    end
    if cycleEvent and not Heal.think_event then
        Heal.think_event = cycleEvent(onThink, 250)
    end
    appendLog("CTOA Native Heal module loaded in passive profile-fed mode")
end

Heal.setEnabled = function(enabled)
    DEFAULT_HEAL_SETTINGS.enabled = enabled == true
    appendLog("Standalone heal " .. (DEFAULT_HEAL_SETTINGS.enabled and "enabled" or "disabled"))
end

Heal.onThink = onThink
Heal.maybeRecover = maybeRecover
_G.CTOA_NativeHeal = Heal

init()
