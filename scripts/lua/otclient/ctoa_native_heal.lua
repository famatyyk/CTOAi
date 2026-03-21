-- ctoa_native_heal.lua  [CTOA OTClient Native]
-- Advanced healing using full OTClient API integration

local HEAL_SETTINGS = {
    hp_critical = 30,
    hp_low = 65, 
    mana_low = 40,
    heal_spell = "exura",
    heal_critical_spell = "exura gran",
    mana_spell = "utani hur"
}

local lastHealTime = 0
local HEAL_COOLDOWN = 1000  -- 1 second

local function appendLog(msg)
    local f = io.open("ctoa_local.log", "a")
    if not f then
        f = io.open("user_dir/ctoa_local.log", "a")
    end
    if f then
        f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-OTC-HEAL] " .. msg .. "\n")
        f:close()
    end
end

local function onHealthChanged(localPlayer, health, maxHealth)
    local now = g_clock.millis()
    if now - lastHealTime < HEAL_COOLDOWN then return end
    
    local hpPercent = math.floor((health / maxHealth) * 100)
    local spell = nil
    
    if hpPercent <= HEAL_SETTINGS.hp_critical then
        spell = HEAL_SETTINGS.heal_critical_spell
    elseif hpPercent <= HEAL_SETTINGS.hp_low then
        spell = HEAL_SETTINGS.heal_spell
    end
    
    if spell then
        g_game.talk(spell)
        lastHealTime = now
        appendLog("Auto heal: " .. spell .. " (HP: " .. hpPercent .. "%)") 
        modules.game_console.addText('[CTOA] Heal: ' .. spell, MessageModes.ModeStatus)
    end
end

local function onManaChanged(localPlayer, mana, maxMana)
    if mana > 50 then  -- Don't cast if very low mana
        local manaPercent = math.floor((mana / maxMana) * 100)
        if manaPercent <= HEAL_SETTINGS.mana_low then
            g_game.talk(HEAL_SETTINGS.mana_spell)
            appendLog("Mana spell: " .. HEAL_SETTINGS.mana_spell .. " (MP: " .. manaPercent .. "%)") 
        end
    end
end

-- Connect to OTClient events
connect(LocalPlayer, { onHealthChanged = onHealthChanged })
connect(LocalPlayer, { onManaChanged = onManaChanged })

appendLog("CTOA Native Heal module loaded")