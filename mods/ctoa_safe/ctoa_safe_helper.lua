-- ctoa_safe_helper.lua [CTOA Safe v3.3.0]
-- Local, clean-room implementation of the KingsVale game_helper interaction contract.
-- Runtime distribution stays self-contained and Safe never arms itself on load.
-- Structure: [Healing] [Tools] [KVShooter] [Explicit arm] [Status]

-- ============================================================
-- GUARD: only one instance
-- ============================================================
local existing = rawget(_G, "CTOA_SAFE")
if type(existing) == "table" and existing._loaded then
    if type(existing.handleGameStart) == "function" then
        pcall(existing.handleGameStart)
    end
    return existing
end

-- ============================================================
-- CONSTANTS
-- ============================================================
local SAFE_VERSION  = "v3.3.0"
local TICK_MS       = 500
local AUTOSAVE_MS   = 600
local WINDOW_W      = 272
local WINDOW_H      = 638
local ROW_H         = 26
local EDIT_W        = 318
local EDIT_H        = 550

-- Observable KingsVale layout contract. Hidden controls are also denied by the
-- runtime guards below, so a stale/imported profile cannot bypass vocation UI.
local VOCATION_UI_CONTRACT = {
    ek   = {label="Knight",   spell_slots=3, potion_slots=3, friend_healing=false, auto_exeta=true},
    monk = {label="Monk",     spell_slots=3, potion_slots=3, friend_healing=true,  auto_exeta=true},
    rp   = {label="Paladin",  spell_slots=3, potion_slots=3, friend_healing=false, auto_exeta=true},
    ms   = {label="Sorcerer", spell_slots=2, potion_slots=2, friend_healing=true,  auto_exeta=false},
    ed   = {label="Druid",    spell_slots=3, potion_slots=3, friend_healing=true,  auto_exeta=false},
}

local function vocationUiContract(vocation)
    return VOCATION_UI_CONTRACT[tostring(vocation or ""):lower()] or VOCATION_UI_CONTRACT.ek
end

-- ============================================================
-- DEFAULT CONFIG
-- ============================================================
local DEFAULTS = {
    enabled                  = false,
    safe_boot_runtime_disabled = true,
    tick_ms                  = TICK_MS,
    hotkey                   = "Ctrl+B",
    window_x                 = 20,
    window_y                 = 60,
    healing = {
        enabled              = true,
        spell_enabled        = true,
        spell_threshold      = 80,
        spell                = "exura ico",
        critical_spell       = "exura med ico",
        critical_threshold   = 50,
        potion_enabled       = true,
        potion_threshold     = 62,
        potion_name          = "Ultimate Health Potion",
        potion_hotkey        = "F1",
        potion_item_id       = 0,
        mana_potion_enabled  = true,
        mana_threshold       = 45,
        hp_randomization     = 4,
        mana_randomization   = 4,
        mana_potion_name     = "Mana Potion",
        mana_hotkey          = "F2",
        mana_item_id         = 0,
        cooldown_ms          = 950,
        potion_rules         = {
            {resource="hp", item_id=0, hotkey="F1", threshold=62, enabled=false, cooldown_ms=950},
            {resource="hp", item_id=0, hotkey="", threshold=50, enabled=false, cooldown_ms=950},
            {resource="mana", item_id=0, hotkey="F2", threshold=50, enabled=false, cooldown_ms=950},
        },
        friend_enabled       = false,
        friend_names         = {},
        friend_rules         = {
            {name="", words="exura sio", threshold=80, cooldown_ms=950, enabled=true},
            {name="", words="exura sio", threshold=50, cooldown_ms=950, enabled=false},
            {name="", words="exura gran sio", threshold=80, cooldown_ms=950, enabled=true},
            {name="", words="exura gran sio", threshold=50, cooldown_ms=950, enabled=false},
        },
        rules                = {
            {kind="critical", words="exura med ico", threshold=50, cooldown_ms=950},
            {kind="heal", words="exura ico", threshold=80, cooldown_ms=950},
        },
        spell_slots          = {
            {id=0, words="exura ico", percent=80, enabled=true},
            {id=0, words="exura med ico", percent=50, enabled=true},
            {id=0, words="", percent=80, enabled=false},
        },
        last_cast_ms         = 0,
        last_potion_ms       = 0,
        last_mana_ms         = 0,
    },
    combat = {
        enabled              = true,
        auto_attack          = true,
        chase                = true,
        spell_rotation       = true,
        rotation_preset      = "smart",
        rotation_interval_ms = 1050,
        last_rotation_ms     = 0,
        auto_exeta           = true,
        exeta_min_visible    = 2,
        exeta_interval_ms    = 5000,
        last_exeta_ms        = 0,
        exeta_spells         = {
            {words = "exeta res", min_nearby = 2, cooldown_ms = 5000},
            {words = "exeta amp res", min_nearby = 3, cooldown_ms = 5000},
        },
        attack_range         = 7,
        target_timeout_ms    = 10000,
        target_rules        = {},
        auto_target_mode    = 1,
        magic_shooter_on_hold = false,
        auto_target_hotkey  = "F11",
        auto_shooter_hotkey = "F11",
        auto_target_both    = "F12",
        auto_change_profile = "",
        current_locked_target_id = 0,
        selected_shooter_profile = "Default",
        shooter_profiles    = {
            Default = {
                spells = {
                    {id=0, words="", percent=80, creatures=1, priority=1, self_cast=false, force_cast=false},
                    {id=0, words="", percent=80, creatures=1, priority=1, self_cast=false, force_cast=false},
                    {id=0, words="", percent=80, creatures=1, priority=1, self_cast=false, force_cast=false},
                    {id=0, words="", percent=80, creatures=1, priority=1, self_cast=false, force_cast=false},
                    {id=0, words="", percent=80, creatures=1, priority=1, self_cast=false, force_cast=false},
                    {id=0, words="", percent=80, creatures=1, priority=1, self_cast=false, force_cast=false},
                },
                runes = {
                    {id=0, creatures=1, priority=1, force_cast=false},
                    {id=0, creatures=1, priority=1, force_cast=false},
                },
                auto_target_mode = 1,
            },
        },
        rotation_spells      = {
            {words = "exori gran",     use_mob_count = true, min_nearby = 3, max_distance = 3, cooldown_ms = 6000},
            {words = "exori min",      use_mob_count = true, min_nearby = 2, max_distance = 3, cooldown_ms = 4000},
            {words = "exori",          use_mob_count = true, min_nearby = 2, max_distance = 3, cooldown_ms = 4000},
            {words = "exori gran ico", use_mob_count = true, min_nearby = 1, max_distance = 7, cooldown_ms = 6000},
            {words = "exori ico",      use_mob_count = true, min_nearby = 1, max_distance = 1, cooldown_ms = 2000},
            {words = "exori hur",      use_mob_count = true, min_nearby = 1, max_distance = 5, cooldown_ms = 2000},
        },
    },
    conditions = {
        enabled              = true,
        mana_shield          = false,
        mana_shield_spell    = "utamo vita",
        paralyze             = true,
        paralyze_spell       = "exura",
        poison               = false,
        poison_spell         = "exana pox",
        utamo                = {
            {id=0, words="utamo vita", enabled=false, percent=77},
        },
        sample_interval_ms   = 1500,
        last_sample_ms       = 0,
    },
    support = {
        enabled              = false,
        rules                = {},
    },
    tools = {
        enabled              = true,
        mana_training        = false,
        mana_training_item_id = 0,
        mana_training_threshold = 100,
        mana_training_interval_ms = 1500,
        auto_haste           = false,
        haste_spell_id       = 0,
        haste_spell          = "utani hur",
        pz_cast              = false,
        exercise_training    = false,
        exercise_item_id     = 0,
        exercise_interval_ms = 3000,
        change_gold          = false,
        gold_item_id         = 3031,
        auto_eat_food        = false,
        food_item_id         = 3725,
        auto_reconnect       = false,
        buff                 = {
            {id=0, words="", enabled=false, safecast=true},
        },
        ammo_config          = {
            {id=0, enabled=false},
            {id=0, enabled=false},
        },
        amulet_percent       = 80,
        ring_percent         = 80,
        equip_amulet         = false,
        amulet_item_id       = 0,
        amulet_threshold     = 50,
        amulet_resource      = "hp",
        equip_ring           = false,
        ring_item_id         = 0,
        ring_threshold       = 50,
        ring_resource        = "hp",
        amulet_config        = {
            {id=0, enabled=false, percent=80, health=true, mana=false},
            {id=0, enabled=false, percent=80, health=true, mana=false},
        },
        ring_config          = {
            {id=0, enabled=false, percent=80, health=true, mana=false},
            {id=0, enabled=false, percent=80, health=true, mana=false},
        },
        action_interval_ms   = 1000,
    },
    timer = {
        enabled              = false,
        interval_ms          = 60000,
        message              = "!timer",
        last_ms              = 0,
    },
}

-- ============================================================
-- DEEP COPY / MERGE HELPERS
-- ============================================================
local function deepCopy(t)
    if type(t) ~= "table" then return t end
    local r = {}
    for k, v in pairs(t) do r[k] = deepCopy(v) end
    return r
end

-- ============================================================
-- RUNTIME STATE
-- ============================================================
local CFG = deepCopy(DEFAULTS)

local RT = {
    armed          = false,
    think_event    = nil,
    save_event     = nil,
    profile_dirty  = false,
    profile_path   = nil,
    vocation       = "ek",
    profile_name   = "CTOA Safe Default",
    active_preset  = "default",
    presets        = {},
    profile_migrated = false,
    shooter_hold   = false,
}

-- ============================================================
-- UI STATE
-- ============================================================
local UI = {
    root           = nil,
    window         = nil,
    title_label    = nil,
    status_label   = nil,
    enable_btn     = nil,
    module_rows    = {},
    edit_panel     = nil,
    edit_close_btn = nil,
    active_edit    = nil,
    selected_module = 1,
    active_page    = "healing",
    page_panel     = nil,
    tab_buttons    = {},
    spell_modal    = nil,
    preset_name    = nil,
    bound_keys     = {},
    bound_up_keys  = {},
    loading_selection = false,
}

-- ============================================================
-- UTILITY: OTClient helpers
-- ============================================================
local function nowMs()
    if g_clock and g_clock.millis then
        local ok, v = pcall(function() return g_clock.millis() end)
        if ok and tonumber(v) then return tonumber(v) end
    end
    return (os.time and os.time() or 0) * 1000
end

local function isOnline()
    if not g_game or not g_game.isOnline then return false end
    local ok, v = pcall(function() return g_game.isOnline() end)
    return ok and v == true
end

local function safeProjectActive()
    local loader = rawget(_G, "CTOA_PROJECT_LOADER")
    return type(loader) == "table" and loader.active_project == "safe"
end

local function getPlayer()
    if not g_game or not g_game.getLocalPlayer then return nil end
    local ok, p = pcall(function() return g_game.getLocalPlayer() end)
    return ok and p or nil
end

local function getHpPercent()
    local p = getPlayer()
    if p and p.getHealthPercent then
        local ok, v = pcall(function() return p:getHealthPercent() end)
        if ok and tonumber(v) then return tonumber(v) end
    end
    return 100
end

local function getMpPercent()
    local p = getPlayer()
    if p and p.getManaPercent then
        local ok, v = pcall(function() return p:getManaPercent() end)
        if ok and tonumber(v) then return tonumber(v) end
    end
    return 100
end

local function creatureTypeValue(creature)
    if not creature or type(creature.getType)~="function" then return nil end
    local ok,value=pcall(function() return creature:getType() end)
    return ok and tonumber(value) or nil
end

local function isNpcCreature(creature)
    if not creature then return false end
    if type(creature.isNpc)=="function" then
        local ok,value=pcall(function() return creature:isNpc() end)
        if ok and value==true then return true end
    end
    local value=creatureTypeValue(creature)
    if value~=nil and value==(tonumber(rawget(_G,"CreatureTypeNpc")) or 2) then return true end
    if type(creature.getId)=="function" then
        local ok,id=pcall(function() return creature:getId() end)
        if ok and tonumber(id) and tonumber(id)>=0x80000000 then return true end
    end
    if type(creature.getIcon)=="function" then
        local ok,icon=pcall(function() return creature:getIcon() end)
        icon=ok and tonumber(icon) or 0
        if icon>0 then return true end
    end
    return false
end

local function isPlayerCreature(creature)
    if not creature then return false end
    if type(creature.isPlayer)=="function" then
        local ok,value=pcall(function() return creature:isPlayer() end)
        if ok and value==true then return true end
    end
    local value=creatureTypeValue(creature)
    return value~=nil and value==(tonumber(rawget(_G,"CreatureTypePlayer")) or 0)
end

local function getNearbyMonsterCount(range)
    local player = getPlayer()
    if not player then return 0 end
    local playerPos = nil
    if player.getPosition then
        local ok, value = pcall(function() return player:getPosition() end)
        if ok then playerPos = value end
    end
    if not playerPos then return 0 end
    local boundedRange = math.max(1, math.min(10, tonumber(range) or 7))
    local creatures = {}
    if g_map and type(g_map.getSpectatorsInRange) == "function" then
        local ok, value = pcall(function()
            return g_map.getSpectatorsInRange(playerPos, false, boundedRange, boundedRange)
        end)
        if ok and type(value) == "table" then creatures = value end
    elseif g_map and type(g_map.getSpectators) == "function" then
        local ok, value = pcall(function()
            return g_map.getSpectators(playerPos, false)
        end)
        if ok and type(value) == "table" then creatures = value end
    end
    local count = 0
    for _, c in ipairs(creatures) do
        local monster = false
        local blocked = isNpcCreature(c) or isPlayerCreature(c)
        if not blocked and c and c.getName then
            local ok, value = pcall(function() return c:getName() end)
            local name = ok and type(value)=="string" and value:lower() or ""
            blocked = name:match("exercise%s+dummy$") ~= nil or name=="training dummy"
        end
        if c and c.isMonster then
            local ok, value = pcall(function() return c:isMonster() end)
            monster = ok and value == true
        end
        if monster and not blocked then
            local ok, pos = pcall(function() return c:getPosition() end)
            if ok and pos and pos.z == playerPos.z then
                local dx = math.abs(pos.x - playerPos.x)
                local dy = math.abs(pos.y - playerPos.y)
                if math.max(dx, dy) <= boundedRange then count = count + 1 end
            end
        end
    end
    return count
end

local function getVisiblePlayerByName(name)
    name = type(name) == "string" and name:lower() or ""
    if name == "" or not g_map then return nil end
    local player = getPlayer(); if not player or not player.getPosition then return nil end
    local okPos, position = pcall(function() return player:getPosition() end); if not okPos or not position then return nil end
    local ok, creatures
    if type(g_map.getSpectatorsInRange) == "function" then
        ok, creatures = pcall(function() return g_map.getSpectatorsInRange(position,false,10,10) end)
    elseif type(g_map.getSpectators) == "function" then
        ok, creatures = pcall(function() return g_map.getSpectators(position,false) end)
    end
    if not ok or type(creatures) ~= "table" then return nil end
    for _, creature in ipairs(creatures) do
        local okPlayer, isPlayer = pcall(function() return creature:isPlayer() end)
        local okName, creatureName = pcall(function() return creature:getName() end)
        if okPlayer and isPlayer and okName and type(creatureName)=="string" and creatureName:lower()==name then return creature end
    end
    return nil
end

local function getCreatureHealthPercent(creature)
    if not creature or type(creature.getHealthPercent) ~= "function" then return 100 end
    local ok, value = pcall(function() return creature:getHealthPercent() end)
    return ok and math.max(0,math.min(100,tonumber(value) or 100)) or 100
end

local function optionalBool(object, methodName)
    if not object or type(object[methodName]) ~= "function" then return nil end
    local ok, value = pcall(function() return object[methodName](object) end)
    if not ok then ok, value = pcall(function() return object[methodName]() end) end
    if not ok or type(value) ~= "boolean" then return nil end
    return value
end

local function numericCall(object, methodName)
    if not object or type(object[methodName]) ~= "function" then return nil end
    local ok, value = pcall(function() return object[methodName](object) end)
    if not ok then ok, value = pcall(function() return object[methodName]() end) end
    if not ok or type(value) ~= "number" then return nil end
    return value
end

local function hasBitFlag(value, flag)
    if type(value) ~= "number" or type(flag) ~= "number" or flag <= 0 then return false end
    if bit32 and bit32.band then return bit32.band(value,flag) == flag end
    if bit and bit.band then return bit.band(value,flag) == flag end
    return value % (flag * 2) >= flag
end

local function appendEvidence(evidence, source)
    evidence[#evidence+1] = source
end

local function protectionZoneEvidence()
    local evidence = {}
    if g_game then
        for _, methodName in ipairs({"isInPz", "isInProtectionZone", "isInSafeZone", "isProtected"}) do
            if optionalBool(g_game, methodName) == true then appendEvidence(evidence,"game:"..methodName) end
        end
    end
    local player = getPlayer()
    if not player then return false,evidence end
    for _, methodName in ipairs({"isInPz", "isInProtectionZone", "isInSafeZone", "isProtected"}) do
        if optionalBool(player, methodName) == true then appendEvidence(evidence,"player:"..methodName) end
    end
    if type(player.hasState) == "function" then
        local states = {"ProtectionZone", "Pz", "SafeZone"}
        for _, globalName in ipairs({"CreatureStateProtectionZone","CreatureStatePz","CreatureStateSafeZone"}) do
            local value = rawget(_G,globalName)
            if value ~= nil then states[#states+1] = value end
        end
        for _, state in ipairs(states) do
            local ok, value = pcall(function() return player:hasState(state) end)
            if ok and value == true then appendEvidence(evidence,"player:hasState:"..tostring(state)) end
        end
    end
    local playerStates = numericCall(player,"getStates")
    local playerStateFlags = {16384}
    for _, name in ipairs({"CreatureStateProtectionZone","CreatureStatePz","CreatureStateSafeZone"}) do
        local flag = rawget(_G,name); if type(flag)=="number" then playerStateFlags[#playerStateFlags+1]=flag end
    end
    for _, flag in ipairs(playerStateFlags) do
        if hasBitFlag(playerStates,flag) then appendEvidence(evidence,"player:getStates:"..tostring(flag)) end
    end
    if g_map and type(g_map.getTile) == "function" and type(player.getPosition) == "function" then
        local okPosition, position = pcall(function() return player:getPosition() end)
        local okTile, tile = false, nil
        if okPosition and position then okTile, tile = pcall(function() return g_map.getTile(position) end) end
        if okTile and tile then
            for _, methodName in ipairs({"isPz", "isProtectionZone", "isSafeZone"}) do
                if optionalBool(tile, methodName) == true then appendEvidence(evidence,"tile:"..methodName) end
            end
            local tileFlags = numericCall(tile,"getFlags")
            local protectionFlags = {1}
            for _, name in ipairs({"TILESTATE_PROTECTIONZONE","TileStateProtectionZone","TileStatePz"}) do
                local flag = rawget(_G,name); if type(flag)=="number" then protectionFlags[#protectionFlags+1]=flag end
            end
            for _, flag in ipairs(protectionFlags) do
                if hasBitFlag(tileFlags,flag) then appendEvidence(evidence,"tile:getFlags:"..tostring(flag)) end
            end
            if type(tile.hasFlag) == "function" then
                local flags = {"TILESTATE_PROTECTIONZONE", "TileStateProtectionZone", "ProtectionZone", "Pz", 1}
                for _, globalName in ipairs({"TILESTATE_PROTECTIONZONE","TileStateProtectionZone","TileStatePz"}) do
                    local value = rawget(_G,globalName)
                    if value ~= nil then flags[#flags+1] = value end
                end
                for _, flag in ipairs(flags) do
                    local ok, value = pcall(function() return tile:hasFlag(flag) end)
                    if ok and value == true then appendEvidence(evidence,"tile:hasFlag:"..tostring(flag)) end
                end
            end
        end
    end
    return #evidence > 0,evidence
end

local function isInProtectionZone()
    local inside = protectionZoneEvidence()
    return inside == true
end

local BLOCKED_NPC_DIALOGUE = {hi=true, hello=true, trade=true, bye=true}

local function sendAutomationText(words, options)
    words = type(words) == "string" and words:gsub("^%s+", ""):gsub("%s+$", "") or ""
    options = type(options) == "table" and options or {}
    if words == "" or BLOCKED_NPC_DIALOGUE[words:lower()] then return false end
    if options.spell == true and options.allow_in_pz ~= true and isInProtectionZone() then return false end
    if not g_game or type(g_game.talk) ~= "function" then return false end
    return pcall(function() g_game.talk(words) end)
end

local function castSpell(words, options)
    options = type(options) == "table" and options or {}
    options.spell = true
    return sendAutomationText(words, options)
end

local function pressHotkey(key)
    if not key or key == "" then return false end
    if modules and modules.game_interface and modules.game_interface.sendHotkey then
        pcall(function() modules.game_interface.sendHotkey(key) end)
        return true
    end
    if g_keyboard and g_keyboard.pressKey then
        pcall(function() g_keyboard.pressKey(key) end)
        return true
    end
    return false
end

local function safeLog(msg)
    if modules and modules.game_console and modules.game_console.addText then
        pcall(function() modules.game_console.addText("[CTOA-SAFE] " .. msg) end)
    end
    print("[CTOA-SAFE] " .. msg)
end

-- File-based diagnostic log (goes to ctoa_safe.log via getWorkDir)
local function fileLog(msg)
    if g_resources and g_resources.getWorkDir then
        local ok, wd = pcall(function() return g_resources.getWorkDir() end)
        if ok and wd and wd ~= "" then
            local f = io.open(wd .. "ctoa_safe_debug.log", "a")
            if f then
                f:write(os.date("%H:%M:%S") .. " " .. tostring(msg) .. "\n")
                f:close()
            end
        end
    end
    safeLog(msg)
end

-- ============================================================
-- STATUS DISPLAY
-- ============================================================
local function setStatus(msg)
    safeLog(msg)
    if UI.status_label and UI.status_label.setText then
        UI.status_label:setText(msg)
    end
end

local function updateTitle()
    local armed = RT.armed and (CFG.enabled and "ON" or "armed") or "safe"
    local voc   = string.upper(RT.vocation or "?")
    local title = "CTOA Safe " .. SAFE_VERSION .. "  [" .. voc .. "]  " .. armed
    if UI.title_label and UI.title_label.setText then
        UI.title_label:setText(title)
    end
end

-- ============================================================
-- PROFILE LOAD / SAVE (dedicated JSON; never reads or writes Helper profiles)
-- ============================================================
local PROFILE_SCHEMA = "ctoa-safe-profile-v3"
local LEGACY_PROFILE_SCHEMA = "ctoa-safe-profile-v2"
local MAX_PROFILE_BYTES = 131072
local MAX_PRESETS = 12

local function clamp(value, minimum, maximum, fallback)
    local number = tonumber(value)
    if not number then return fallback end
    return math.max(minimum, math.min(maximum, math.floor(number)))
end

local function useInventoryItemPlain(itemId)
    itemId = tonumber(itemId) or 0
    if itemId <= 0 or not g_game then return false end
    if type(g_game.useInventoryItem) == "function" then
        return pcall(function() g_game.useInventoryItem(itemId) end)
    end
    return false
end

local function useInventoryItemOn(itemId, target)
    itemId = tonumber(itemId) or 0
    if itemId <= 0 or not target or not g_game or type(g_game.useInventoryItemWith) ~= "function" then return false end
    return pcall(function() g_game.useInventoryItemWith(itemId, target, -1) end)
end

local function useInventoryItemOnSelf(itemId)
    return useInventoryItemOn(itemId, getPlayer())
end

-- Compatibility name for healing/support rules: those items are explicitly self-targeted.
local function useInventoryItem(itemId)
    return useInventoryItemOnSelf(itemId)
end

local EXERCISE_DUMMY_NAMES = {
    ["exercise dummy"] = true,
    ["training dummy"] = true,
    ["durable exercise dummy"] = true,
    ["private exercise dummy"] = true,
    ["expert exercise dummy"] = true,
}

local EXERCISE_DUMMY_IDS = {
    [5787]=true,[5788]=true,
    [28558]=true,[28559]=true,[28560]=true,[28561]=true,
    [28562]=true,[28563]=true,[28564]=true,[28565]=true,
}

local EXERCISE_WEAPON_FAMILIES = {
    [28552]="exercise_sword",[28553]="exercise_axe",[28554]="exercise_club",
    [28555]="exercise_bow",[28556]="exercise_rod",[28557]="exercise_wand",
    [35279]="durable_exercise_sword",[35280]="durable_exercise_axe",
    [35281]="durable_exercise_club",[35282]="durable_exercise_bow",
    [35283]="durable_exercise_rod",[35284]="durable_exercise_wand",
    [35285]="lasting_exercise_sword",[35286]="lasting_exercise_axe",
    [35287]="lasting_exercise_club",[35288]="lasting_exercise_bow",
    [35289]="lasting_exercise_rod",[35290]="lasting_exercise_wand",
    [44066]="durable_exercise_shield",[50294]="durable_exercise_wraps",
}

local function thingId(thing)
    if not thing or type(thing.getId)~="function" then return 0 end
    local ok,id=pcall(function() return thing:getId() end)
    return ok and math.max(0,math.floor(tonumber(id) or 0)) or 0
end

local function exerciseWeaponFamily(thingOrId)
    local id=type(thingOrId)=="number" and math.floor(thingOrId) or thingId(thingOrId)
    if EXERCISE_WEAPON_FAMILIES[id] then return EXERCISE_WEAPON_FAMILIES[id] end
    if type(thingOrId)=="table" or type(thingOrId)=="userdata" then
        for _,accessor in ipairs({"getName","getDescription","getTooltip"}) do
            if type(thingOrId[accessor])=="function" then
                local ok,text=pcall(function() return thingOrId[accessor](thingOrId) end)
                if ok and type(text)=="string" then
                    local role=text:lower():match("exercise%s+(sword|axe|club|bow|rod|wand|shield|wraps)")
                    if role then return "metadata_exercise_"..role end
                end
            end
        end
    end
    return nil
end

local EXERCISE_VOCATION_FAMILIES = {
    ek={sword=true,axe=true,club=true,shield=true},
    rp={bow=true},
    ms={rod=true,wand=true},
    ed={rod=true,wand=true},
    monk={wraps=true},
}

local function exerciseFamilyRole(family)
    family=type(family)=="string" and family or ""
    for _,role in ipairs({"sword","axe","club","bow","rod","wand","shield","wraps"}) do
        if family:match(role.."$") then return role end
    end
    return nil
end

local function findExerciseWeaponIdForVocation(vocation)
    if not g_game or type(g_game.getContainers)~="function" then return 0,nil end
    local allowed=EXERCISE_VOCATION_FAMILIES[vocation] or {}
    local okContainers,containers=pcall(function() return g_game.getContainers() end)
    if not okContainers or type(containers)~="table" then return 0,nil end
    local fallbackId,fallbackFamily=0,nil
    for _,container in pairs(containers) do
        if container and type(container.getItems)=="function" then
            local okItems,items=pcall(function() return container:getItems() end)
            if okItems and type(items)=="table" then
                for _,item in ipairs(items) do
                    local family=exerciseWeaponFamily(item)
                    local id=thingId(item)
                    if family and id>0 then
                        if fallbackId==0 then fallbackId,fallbackFamily=id,family end
                        if allowed[exerciseFamilyRole(family)] then return id,family end
                    end
                end
            end
        end
    end
    return fallbackId,fallbackFamily
end

local function isExerciseDummy(thing)
    if not thing then return false end
    if EXERCISE_DUMMY_IDS[thingId(thing)] then return true end
    for _, accessor in ipairs({"getName", "getDescription", "getTooltip"}) do
        if type(thing[accessor]) == "function" then
            local ok, text = pcall(function() return thing[accessor](thing) end)
            if ok and type(text) == "string" then
                text = text:lower():gsub("^%s+", ""):gsub("%s+$", "")
                if EXERCISE_DUMMY_NAMES[text] == true
                    or text:match("exercise%s+dummy") ~= nil
                    or text:match("training%s+dummy") ~= nil then
                    return true
                end
            end
        end
    end
    return false
end

local function findExerciseDummy()
    local player = getPlayer()
    if not player or type(player.getPosition) ~= "function" or not g_map then return nil end
    local okPosition, position = pcall(function() return player:getPosition() end)
    if not okPosition or not position then return nil end
    local ok, creatures = false, nil
    if type(g_map.getSpectatorsInRange) == "function" then
        ok, creatures = pcall(function() return g_map.getSpectatorsInRange(position,false,7,7) end)
    elseif type(g_map.getSpectators) == "function" then
        ok, creatures = pcall(function() return g_map.getSpectators(position,false) end)
    end
    local best, bestDistance = nil, math.huge
    local function consider(thing, targetPosition)
        if isExerciseDummy(thing) and targetPosition and targetPosition.z == position.z then
            local distance = math.max(math.abs(targetPosition.x-position.x),math.abs(targetPosition.y-position.y))
            if distance <= 7 and distance < bestDistance then best, bestDistance = thing, distance end
        end
    end
    if ok and type(creatures) == "table" then
        for _, creature in ipairs(creatures) do
            if type(creature.getPosition) == "function" then
                local okTarget, targetPosition = pcall(function() return creature:getPosition() end)
                if okTarget then consider(creature,targetPosition) end
            end
        end
    end
    -- Official-style exercise dummies are map items, not necessarily creatures.
    -- Scan the loaded floor so useInventoryItemWith receives the actual item Thing.
    if type(g_map.getTiles) == "function" then
        local okTiles, tiles = pcall(function() return g_map.getTiles(position.z) end)
        if okTiles and type(tiles) == "table" then
            for _, tile in ipairs(tiles) do
                local okTilePosition, tilePosition = false, nil
                if tile and type(tile.getPosition) == "function" then
                    okTilePosition, tilePosition = pcall(function() return tile:getPosition() end)
                end
                if okTilePosition and tilePosition and tilePosition.z == position.z
                    and math.max(math.abs(tilePosition.x-position.x),math.abs(tilePosition.y-position.y)) <= 7
                    and type(tile.getItems) == "function" then
                    local okItems, items = pcall(function() return tile:getItems() end)
                    if okItems and type(items) == "table" then
                        for _, item in ipairs(items) do consider(item,tilePosition) end
                    end
                end
            end
        end
    end
    return best
end

local function useExerciseItem(itemId)
    itemId = tonumber(itemId) or 0
    if itemId <= 0 or not g_game or type(g_game.useInventoryItemWith) ~= "function" then return false end
    local target = findExerciseDummy()
    if not target then return false end
    return useInventoryItemOn(itemId, target)
end

local function randomizedThreshold(base, spread)
    local center = math.max(1, math.min(99, math.floor(tonumber(base) or 50)))
    local radius = math.max(0, math.min(20, math.floor(tonumber(spread) or 0)))
    if radius == 0 then return center end
    return math.max(1, math.min(99, center + math.random(-radius, radius)))
end

local function ruleThreshold(rule)
    if rule._trigger_threshold then return rule._trigger_threshold end
    local minimum = math.max(1, math.min(99, math.floor(tonumber(rule.threshold_min) or 60)))
    local maximum = math.max(minimum, math.min(99, math.floor(tonumber(rule.threshold_max) or minimum)))
    rule._trigger_threshold = minimum == maximum and minimum or math.random(minimum, maximum)
    return rule._trigger_threshold
end

local function selectConfiguredTarget(rules,maxDistance)
    rules=type(rules)=="table" and rules or {}
    if not g_map then return nil end
    local player=getPlayer(); if not player or not player.getPosition then return nil end
    local okPos,playerPos=pcall(function() return player:getPosition() end); if not okPos or not playerPos then return nil end
    local ok,list=pcall(function() return g_map.getSpectatorsInRange(playerPos,false,10,10) end)
    if not ok or type(list)~="table" then return nil end
    local best,bestRule,bestPriority,bestDistance=nil,nil,-1,999
    for _,creature in ipairs(list) do
        local okMonster,isMonster=pcall(function() return creature:isMonster() end)
        local isNpc=isNpcCreature(creature)
        local isPlayer=isPlayerCreature(creature)
        local attackable=optionalBool(creature,"isAttackable")
        if okMonster and isMonster and not isNpc and not isPlayer and attackable~=false and not isExerciseDummy(creature) then
            local _,name=pcall(function() return creature:getName() end); local _,pos=pcall(function() return creature:getPosition() end)
            if type(name)=="string" and pos and pos.z==playerPos.z then
                local distance=math.max(math.abs(pos.x-playerPos.x),math.abs(pos.y-playerPos.y))
                if #rules==0 and distance<=math.max(1,math.min(10,tonumber(maxDistance) or 7)) and distance<bestDistance then
                    best,bestRule,bestPriority,bestDistance=creature,nil,0,distance
                else
                    for _,rule in ipairs(rules) do
                        local pattern="^"..rule.name:lower():gsub("([%%%^%$%(%)%.%[%]%+%-%?])","%%%1"):gsub("%*",".*").."$"
                        if name:lower():match(pattern) and distance<=rule.max_distance and (rule.priority>bestPriority or (rule.priority==bestPriority and distance<bestDistance)) then best,bestRule,bestPriority,bestDistance=creature,rule,rule.priority,distance end
                    end
                end
            end
        end
    end
    return best,bestRule
end

local function sameCreature(left,right)
    if left==right and left~=nil then return true end
    if not left or not right then return false end
    if left.getId and right.getId then
        local okLeft,leftId=pcall(function() return left:getId() end)
        local okRight,rightId=pcall(function() return right:getId() end)
        if okLeft and okRight and leftId~=nil and rightId~=nil then return leftId==rightId end
    end
    return false
end

local function safeCombatCreature(creature)
    if not creature or isExerciseDummy(creature) then return false end
    if isNpcCreature(creature) or isPlayerCreature(creature) then return false end
    if optionalBool(creature,"isAttackable")==false then return false end
    if type(creature.isMonster)~="function" then return false end
    local ok,value=pcall(function() return creature:isMonster() end)
    return ok and value==true
end

local function attackingCreature()
    if not g_game or type(g_game.getAttackingCreature)~="function" then return nil end
    local ok,value=pcall(function() return g_game.getAttackingCreature() end)
    return ok and value or nil
end

local function cleanString(value, fallback, maximum)
    if type(value) ~= "string" then return fallback end
    value = value:gsub("[%z\1-\31]", "")
    if value == "" or #value > maximum then return fallback end
    return value
end

local function cleanBoolean(value, fallback)
    if type(value) ~= "boolean" then return fallback end
    return value
end

local function profilePath(vocId)
    if not g_resources or type(g_resources.getWorkDir) ~= "function" then return nil end
    local ok, workDir = pcall(function() return g_resources.getWorkDir() end)
    if not ok or type(workDir) ~= "string" or workDir == "" then return nil end
    local id = ({ek=true, rp=true, ms=true, ed=true})[vocId] and vocId or "ek"
    return workDir .. "ctoa_safe_" .. id .. "_profile.json"
end

local function cleanStringList(value, fallback, maximumItems)
    if type(value) ~= "table" then return deepCopy(fallback) end
    local result = {}
    for index = 1, math.min(#value, maximumItems) do
        local item = cleanString(value[index], nil, 64)
        if item then result[#result + 1] = item end
    end
    if #result == 0 then return deepCopy(fallback) end
    return result
end

local function cleanExetaRotation(value, fallback, legacyMinimum, legacyCooldown)
    if type(value) ~= "table" then return deepCopy(fallback) end
    local result = {}
    for index = 1, math.min(#value, 16) do
        local item = value[index]
        local words = type(item) == "string" and cleanString(item, nil, 64)
            or type(item) == "table" and cleanString(item.words, nil, 64)
        if words then
            result[#result + 1] = {
                words = words,
                min_nearby = clamp(type(item) == "table" and item.min_nearby or legacyMinimum, 1, 20, legacyMinimum or 2),
                cooldown_ms = clamp(type(item) == "table" and item.cooldown_ms or legacyCooldown, 500, 120000, legacyCooldown or 5000),
            }
        end
    end
    if #result == 0 then return deepCopy(fallback) end
    return result
end

local function cleanRotation(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback) end
    local result = {}
    for index = 1, math.min(#value, 32) do
        local item = value[index]
        if type(item) == "table" then
            local words = cleanString(item.words, nil, 64)
            if words then
                result[#result + 1] = {
                    words = words,
                    min_nearby = clamp(item.min_nearby, 0, 20, 1),
                    max_nearby = clamp(item.max_nearby, 0, 20, 20),
                    use_mob_count = cleanBoolean(item.use_mob_count, true),
                    max_distance = clamp(item.max_distance, 1, 10, 7),
                    cooldown_ms = clamp(item.cooldown_ms, 250, 120000, 2000),
                }
            end
        end
    end
    if #result == 0 then return deepCopy(fallback) end
    return result
end

local function cleanTargets(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local result = {}
    for _, item in ipairs(value) do
        if type(item) == "table" then
            local name = cleanString(item.name, nil, 64)
            if name and name ~= "" and #result < 32 then
                result[#result + 1] = {name = name,
                    priority = clamp(item.priority, 0, 10, 5),
                    max_distance = clamp(item.max_distance, 1, 10, 7),
                    chase = cleanBoolean(item.chase, true)}
            end
        end
    end
    return result
end

local function cleanHealingRules(value, fallback)
    if type(value)~="table" then return deepCopy(fallback or {}) end
    local out={}
    for _,item in ipairs(value) do
        if type(item)=="table" then
            local words=cleanString(item.words,nil,64); local kind=cleanString(item.kind,"heal",16)
            if words and words~="" and (kind=="heal" or kind=="critical" or kind=="support") and #out<16 then
                out[#out+1]={kind=kind,words=words,threshold=clamp(item.threshold,1,99,80),cooldown_ms=clamp(item.cooldown_ms,250,60000,950)}
            end
        end
    end
    return #out>0 and out or deepCopy(fallback or {})
end

local function cleanSupportRules(value, fallback)
    if type(value)~="table" then return deepCopy(fallback or {}) end
    local out={}
    for _,item in ipairs(value) do
        if type(item)=="table" then
            local action=cleanString(item.action,"spell",16)
            local resource=cleanString(item.resource,"always",16)
            local words=cleanString(item.words,"",64)
            local itemId=clamp(item.item_id,0,65535,0)
            if (action=="spell" or action=="item") and (resource=="always" or resource=="hp" or resource=="mana") and #out<16 then
                if (action=="spell" and words~="") or (action=="item" and itemId>0) then
                    local thresholdMin=clamp(item.threshold_min,1,99,60)
                    local thresholdMax=clamp(item.threshold_max,thresholdMin,99,math.max(thresholdMin,70))
                    out[#out+1]={action=action,resource=resource,words=words,item_id=itemId,
                        threshold_min=thresholdMin,threshold_max=thresholdMax,
                        interval_ms=clamp(item.interval_ms,250,3600000,1000)}
                end
            end
        end
    end
    return out
end

local function cleanSpellSlots(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local out = {}
    for index = 1, math.min(#value, 3) do
        local item = type(value[index]) == "table" and value[index] or {}
        out[index] = {
            id = clamp(item.id, 0, 65535, 0),
            words = cleanString(item.words, "", 64),
            percent = clamp(item.percent or item.threshold, 1, 100, 80),
            enabled = cleanBoolean(item.enabled, false),
        }
    end
    while #out < 3 do out[#out + 1] = deepCopy((fallback or DEFAULTS.healing.spell_slots)[#out + 1]) end
    return out
end

local function cleanPotionRules(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local out = {}
    for index = 1, math.min(#value, 3) do
        local item = type(value[index]) == "table" and value[index] or {}
        local resource = cleanString(item.resource, index == 3 and "mana" or "hp", 8)
        if resource ~= "mana" then resource = "hp" end
        out[#out + 1] = {
            resource = resource,
            item_id = clamp(item.item_id or item.id, 0, 65535, 0),
            hotkey = cleanString(item.hotkey, "", 32),
            threshold = clamp(item.threshold or item.percent, 1, 100, index == 1 and 62 or 50),
            enabled = cleanBoolean(item.enabled, true),
            priority = clamp(item.priority, 0, 10, 0),
            cooldown_ms = clamp(item.cooldown_ms, 250, 60000, 950),
        }
    end
    while #out < 3 do
        local index = #out + 1
        out[index] = deepCopy((fallback or DEFAULTS.healing.potion_rules)[index])
    end
    return out
end

local function cleanFriendRules(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local out = {}
    for index = 1, math.min(#value, 4) do
        local item = type(value[index]) == "table" and value[index] or {}
        out[#out + 1] = {
            name = cleanString(item.name, "", 64),
            words = cleanString(item.words, index <= 2 and "exura sio" or "exura gran sio", 64),
            threshold = clamp(item.threshold or item.percent, 1, 100, index % 2 == 1 and 80 or 50),
            cooldown_ms = clamp(item.cooldown_ms, 250, 60000, 950),
            enabled = cleanBoolean(item.enabled, true),
        }
    end
    if #out == 0 then return deepCopy(fallback or {}) end
    return out
end

local function cleanEquipConfig(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local out = {}
    for index = 1, math.min(#value, 2) do
        local item = type(value[index]) == "table" and value[index] or {}
        out[index] = {
            id = clamp(item.id or item.item_id, 0, 65535, 0),
            enabled = cleanBoolean(item.enabled, false),
            percent = clamp(item.percent or item.threshold, 1, 100, 80),
            health = cleanBoolean(item.health, true),
            mana = cleanBoolean(item.mana, false),
        }
    end
    while #out < 2 do
        out[#out + 1] = deepCopy((fallback or {})[#out + 1] or {id=0,enabled=false,percent=80,health=true,mana=false})
    end
    return out
end

local function cleanToggleConfig(value, fallback, maximum)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local out = {}
    for index = 1, math.min(#value, maximum or 2) do
        local item = type(value[index]) == "table" and value[index] or {}
        out[index] = {
            id=clamp(item.id,0,65535,0),words=cleanString(item.words,"",64),
            enabled=cleanBoolean(item.enabled,false),safecast=cleanBoolean(item.safecast,true),
            percent=clamp(item.percent,1,100,80),
        }
    end
    if #out == 0 then return deepCopy(fallback or {}) end
    return out
end

local function cleanShooterProfiles(value, fallback)
    if type(value) ~= "table" then return deepCopy(fallback or {}) end
    local profiles, count = {}, 0
    for name, profile in pairs(value) do
        if type(name) == "string" and type(profile) == "table" and count < 12 then
            local cleanName = cleanString(name, nil, 48)
            if cleanName then
                local result = {spells={}, runes={}, auto_target_mode=clamp(profile.auto_target_mode or profile.autoTargetMode,0,10,1)}
                local spells = type(profile.spells) == "table" and profile.spells or {}
                for index = 1, math.min(#spells, 6) do
                    local spell = type(spells[index]) == "table" and spells[index] or {}
                    result.spells[index] = {
                        id=clamp(spell.id,0,65535,0), words=cleanString(spell.words,"",64),
                        percent=clamp(spell.percent,1,100,80), creatures=clamp(spell.creatures,1,20,1),
                        priority=clamp(spell.priority,1,10,1), self_cast=cleanBoolean(spell.self_cast or spell.selfCast,false),
                        force_cast=cleanBoolean(spell.force_cast or spell.forceCast,false),
                    }
                end
                while #result.spells < 6 do
                    result.spells[#result.spells + 1] = {id=0,words="",percent=80,creatures=1,priority=1,self_cast=false,force_cast=false}
                end
                local runes = type(profile.runes) == "table" and profile.runes or {}
                for index = 1, math.min(#runes, 2) do
                    local rune = type(runes[index]) == "table" and runes[index] or {}
                    result.runes[index] = {id=clamp(rune.id,0,65535,0),creatures=clamp(rune.creatures,1,20,1),priority=clamp(rune.priority,1,10,1),force_cast=cleanBoolean(rune.force_cast or rune.forceCast,false)}
                end
                while #result.runes < 2 do result.runes[#result.runes + 1] = {id=0,creatures=1,priority=1,force_cast=false} end
                profiles[cleanName] = result
                count = count + 1
            end
        end
    end
    if count == 0 then return deepCopy(fallback or {}) end
    return profiles
end

local function cleanTools(value, fallback)
    value = type(value) == "table" and value or {}
    fallback = type(fallback) == "table" and fallback or DEFAULTS.tools
    local out = deepCopy(fallback)
    out.enabled = cleanBoolean(value.enabled, out.enabled)
    out.mana_training = cleanBoolean(value.mana_training, out.mana_training)
    out.mana_training_item_id = clamp(value.mana_training_item_id, 0, 65535, out.mana_training_item_id)
    out.mana_training_threshold = clamp(value.mana_training_threshold, 1, 100, out.mana_training_threshold)
    out.mana_training_interval_ms = clamp(value.mana_training_interval_ms, 250, 3600000, out.mana_training_interval_ms)
    out.auto_haste = cleanBoolean(value.auto_haste, out.auto_haste)
    out.haste_spell_id = clamp(value.haste_spell_id,0,65535,out.haste_spell_id)
    out.haste_spell = cleanString(value.haste_spell, out.haste_spell, 64)
    out.pz_cast = cleanBoolean(value.pz_cast, out.pz_cast)
    out.exercise_training = cleanBoolean(value.exercise_training, out.exercise_training)
    out.exercise_item_id = clamp(value.exercise_item_id, 0, 65535, out.exercise_item_id)
    out.exercise_interval_ms = clamp(value.exercise_interval_ms, 250, 3600000, out.exercise_interval_ms)
    out.change_gold = cleanBoolean(value.change_gold, out.change_gold)
    out.gold_item_id = clamp(value.gold_item_id, 0, 65535, out.gold_item_id)
    out.auto_eat_food = cleanBoolean(value.auto_eat_food, out.auto_eat_food)
    out.food_item_id = clamp(value.food_item_id, 0, 65535, out.food_item_id)
    out.auto_reconnect = cleanBoolean(value.auto_reconnect, out.auto_reconnect)
    out.buff = cleanToggleConfig(value.buff, out.buff, 1)
    out.ammo_config = cleanToggleConfig(value.ammo_config, out.ammo_config, 2)
    out.amulet_percent = clamp(value.amulet_percent,1,100,out.amulet_percent)
    out.ring_percent = clamp(value.ring_percent,1,100,out.ring_percent)
    for _, slot in ipairs({"amulet", "ring"}) do
        out["equip_" .. slot] = cleanBoolean(value["equip_" .. slot], out["equip_" .. slot])
        out[slot .. "_item_id"] = clamp(value[slot .. "_item_id"], 0, 65535, out[slot .. "_item_id"])
        out[slot .. "_threshold"] = clamp(value[slot .. "_threshold"], 1, 100, out[slot .. "_threshold"])
        local resource = cleanString(value[slot .. "_resource"], out[slot .. "_resource"], 8)
        out[slot .. "_resource"] = resource == "mana" and "mana" or "hp"
    end
    out.amulet_config = cleanEquipConfig(value.amulet_config, out.amulet_config)
    out.ring_config = cleanEquipConfig(value.ring_config, out.ring_config)
    out.action_interval_ms = clamp(value.action_interval_ms, 250, 60000, out.action_interval_ms)
    return out
end

local function detectVocation()
    local p = getPlayer()
    if not p then return "ek", "fallback" end
    local function fromValue(value)
        local byId = {[1]="ek",[2]="rp",[3]="ms",[4]="ed",[5]="ms",[6]="ed",[7]="rp",[8]="ek"}
        local resolved = byId[tonumber(value)]
        if resolved or type(value) ~= "string" then return resolved end
        local lower=value:lower()
        if lower:find("monk",1,true) then return "monk"
        elseif lower:find("sorcerer",1,true) then return "ms"
        elseif lower:find("druid",1,true) then return "ed"
        elseif lower:find("paladin",1,true) then return "rp"
        elseif lower:find("knight",1,true) then return "ek" end
        return nil
    end
    -- Try getVocationId
    local vocId
    if p.getVocationId then
        local ok, v = pcall(function() return p:getVocationId() end)
        if ok and v then vocId = fromValue(v) end
    end
    -- Solteria/OTCv8 exposes the base vocation through getVocation().
    if not vocId and p.getVocation then
        local ok, vocation = pcall(function() return p:getVocation() end)
        if ok then vocId = fromValue(vocation) end
    end
    if not vocId and p.getName then
        local ok, name = pcall(function() return p:getName() end)
        if ok and name then
            local lower = string.lower(name)
            if string.find(lower, "monk") then vocId = "monk"
            elseif string.find(lower, "knight") then vocId = "ek"
            elseif string.find(lower, "paladin") then vocId = "rp"
            elseif string.find(lower, "sorcerer") then vocId = "ms"
            elseif string.find(lower, "druid") then vocId = "ed"
            end
        end
    end
    return vocId or "ek", "detection"
end

local function presetPath(vocId, suffix)
    local base = profilePath(vocId)
    if not base then return nil end
    return base:gsub("_profile%.json$", suffix)
end

local function cleanPresetId(value, fallback)
    local id = type(value) == "string" and value:lower() or ""
    id = id:gsub("[^a-z0-9_-]", "_"):gsub("_+", "_"):gsub("^_+", ""):gsub("_+$", "")
    if id == "" then id = fallback or "preset" end
    return id:sub(1, 32)
end

local function keysAllowed(value, allowed)
    if type(value) ~= "table" then return false end
    for key in pairs(value) do
        if type(key) ~= "number" and not allowed[key] then return false end
    end
    return true
end

local PRESET_KEYS = {id=true,name=true,hotkey=true,window_x=true,window_y=true,healing=true,combat=true,conditions=true,support=true,tools=true,timer=true}
local MODULE_KEYS = {
    healing={enabled=true,spell_enabled=true,spell_threshold=true,spell=true,critical_spell=true,critical_threshold=true,potion_enabled=true,potion_threshold=true,potion_hotkey=true,potion_item_id=true,mana_potion_enabled=true,mana_threshold=true,hp_randomization=true,mana_randomization=true,mana_hotkey=true,mana_item_id=true,cooldown_ms=true,rules=true,spell_slots=true,potion_rules=true,friend_enabled=true,friend_names=true,friend_rules=true},
    combat={enabled=true,auto_attack=true,chase=true,spell_rotation=true,rotation_preset=true,rotation_interval_ms=true,rotation_spells=true,target_rules=true,auto_exeta=true,exeta_min_visible=true,exeta_interval_ms=true,exeta_spells=true,attack_range=true,target_timeout_ms=true,selected_shooter_profile=true,shooter_profiles=true,auto_target_mode=true,magic_shooter_on_hold=true,auto_target_hotkey=true,auto_shooter_hotkey=true,auto_target_both=true,auto_change_profile=true,current_locked_target_id=true},
    conditions={enabled=true,mana_shield=true,mana_shield_spell=true,paralyze=true,paralyze_spell=true,poison=true,poison_spell=true,utamo=true,sample_interval_ms=true},
    support={enabled=true,rules=true},
    tools={enabled=true,mana_training=true,mana_training_item_id=true,mana_training_threshold=true,mana_training_interval_ms=true,auto_haste=true,haste_spell_id=true,haste_spell=true,pz_cast=true,exercise_training=true,exercise_item_id=true,exercise_interval_ms=true,change_gold=true,gold_item_id=true,auto_eat_food=true,food_item_id=true,auto_reconnect=true,buff=true,ammo_config=true,amulet_percent=true,ring_percent=true,equip_amulet=true,amulet_item_id=true,amulet_threshold=true,amulet_resource=true,equip_ring=true,ring_item_id=true,ring_threshold=true,ring_resource=true,amulet_config=true,ring_config=true,action_interval_ms=true},
    timer={enabled=true,interval_ms=true,message=true},
}

local RULE_KEYS = {
    healing={kind=true,words=true,threshold=true,cooldown_ms=true},
    rotation={words=true,min_nearby=true,max_nearby=true,use_mob_count=true,max_distance=true,cooldown_ms=true},
    target={name=true,priority=true,max_distance=true,chase=true},
    exeta={words=true,min_nearby=true,cooldown_ms=true},
    support={action=true,resource=true,words=true,item_id=true,threshold_min=true,threshold_max=true,interval_ms=true},
    potion={resource=true,item_id=true,hotkey=true,threshold=true,enabled=true,priority=true,cooldown_ms=true},
    friend={name=true,words=true,threshold=true,cooldown_ms=true,enabled=true},
    spellslot={id=true,words=true,percent=true,enabled=true},
}

local function validRuleList(value, allowed)
    if value == nil then return true end
    if type(value) ~= "table" then return false end
    for key, rule in pairs(value) do
        if type(key) ~= "number" or type(rule) ~= "table" or not keysAllowed(rule, allowed) then return false end
    end
    return true
end

local function validPresetShape(preset)
    if not keysAllowed(preset, PRESET_KEYS) then return false end
    for moduleId, allowed in pairs(MODULE_KEYS) do
        if preset[moduleId] ~= nil and (type(preset[moduleId]) ~= "table" or not keysAllowed(preset[moduleId], allowed)) then return false end
        if moduleId ~= "tools" and type(preset[moduleId]) ~= "table" then return false end
    end
    if not validRuleList(preset.healing.rules, RULE_KEYS.healing) then return false end
    if not validRuleList(preset.combat.rotation_spells, RULE_KEYS.rotation) then return false end
    if not validRuleList(preset.combat.target_rules, RULE_KEYS.target) then return false end
    if not validRuleList(preset.combat.exeta_spells, RULE_KEYS.exeta) then return false end
    if not validRuleList(preset.support.rules, RULE_KEYS.support) then return false end
    if not validRuleList(preset.healing.potion_rules, RULE_KEYS.potion) then return false end
    if not validRuleList(preset.healing.friend_rules, RULE_KEYS.friend) then return false end
    if not validRuleList(preset.healing.spell_slots, RULE_KEYS.spellslot) then return false end
    return true
end

local function validLibrary(data, vocId)
    if not keysAllowed(data, {schema_version=true,vocation=true,active_preset=true,presets=true}) then return false end
    if data.schema_version ~= PROFILE_SCHEMA or data.vocation ~= vocId or type(data.presets) ~= "table" then return false end
    if #data.presets < 1 or #data.presets > MAX_PRESETS then return false end
    local ids = {}
    for _, preset in ipairs(data.presets) do
        if not validPresetShape(preset) then return false end
        local id = cleanPresetId(preset.id, "")
        if id == "" or ids[id] then return false end
        ids[id] = true
    end
    return ids[cleanPresetId(data.active_preset, "")] == true
end

local function findPreset(id)
    id = cleanPresetId(id, "default")
    for index, preset in ipairs(RT.presets) do
        if preset.id == id then return preset, index end
    end
    return nil, nil
end

local function applyPresetData(data, vocId)
    local healing = type(data.healing) == "table" and data.healing or {}
    CFG.healing.enabled = cleanBoolean(healing.enabled, CFG.healing.enabled)
    CFG.healing.spell_enabled = cleanBoolean(healing.spell_enabled, CFG.healing.spell_enabled)
    CFG.healing.spell_threshold = clamp(healing.spell_threshold, 1, 99, CFG.healing.spell_threshold)
    CFG.healing.spell = cleanString(healing.spell, CFG.healing.spell, 64)
    CFG.healing.critical_spell = cleanString(healing.critical_spell, CFG.healing.critical_spell, 64)
    CFG.healing.critical_threshold = clamp(healing.critical_threshold, 1, 99, CFG.healing.critical_threshold)
    CFG.healing.potion_enabled = cleanBoolean(healing.potion_enabled, CFG.healing.potion_enabled)
    CFG.healing.potion_threshold = clamp(healing.potion_threshold, 1, 99, CFG.healing.potion_threshold)
    CFG.healing.potion_hotkey = cleanString(healing.potion_hotkey, CFG.healing.potion_hotkey, 32)
    CFG.healing.potion_item_id = clamp(healing.potion_item_id, 0, 65535, CFG.healing.potion_item_id)
    CFG.healing.mana_potion_enabled = cleanBoolean(healing.mana_potion_enabled, CFG.healing.mana_potion_enabled)
    CFG.healing.mana_threshold = clamp(healing.mana_threshold, 1, 99, CFG.healing.mana_threshold)
    CFG.healing.hp_randomization = clamp(healing.hp_randomization, 0, 20, CFG.healing.hp_randomization)
    CFG.healing.mana_randomization = clamp(healing.mana_randomization, 0, 20, CFG.healing.mana_randomization)
    CFG.healing.mana_hotkey = cleanString(healing.mana_hotkey, CFG.healing.mana_hotkey, 32)
    CFG.healing.mana_item_id = clamp(healing.mana_item_id, 0, 65535, CFG.healing.mana_item_id)
    CFG.healing.cooldown_ms = clamp(healing.cooldown_ms, 250, 10000, CFG.healing.cooldown_ms)
    CFG.healing.rules = cleanHealingRules(healing.rules, CFG.healing.rules)
    CFG.healing.spell_slots = cleanSpellSlots(healing.spell_slots, CFG.healing.spell_slots)
    CFG.healing.potion_rules = cleanPotionRules(healing.potion_rules, CFG.healing.potion_rules)
    CFG.healing.friend_enabled = cleanBoolean(healing.friend_enabled, CFG.healing.friend_enabled)
    CFG.healing.friend_names = cleanStringList(healing.friend_names, CFG.healing.friend_names, 16)
    CFG.healing.friend_rules = cleanFriendRules(healing.friend_rules, CFG.healing.friend_rules)

    local combat = type(data.combat) == "table" and data.combat or {}
    CFG.combat.enabled = cleanBoolean(combat.enabled, CFG.combat.enabled)
    CFG.combat.auto_attack = cleanBoolean(combat.auto_attack, CFG.combat.auto_attack)
    CFG.combat.chase = cleanBoolean(combat.chase, CFG.combat.chase)
    CFG.combat.spell_rotation = cleanBoolean(combat.spell_rotation, CFG.combat.spell_rotation)
    local preset = cleanString(combat.rotation_preset, CFG.combat.rotation_preset, 24)
    CFG.combat.rotation_preset = ({smart=true, safe=true, aggressive=true, custom=true})[preset] and preset or "custom"
    CFG.combat.rotation_interval_ms = clamp(combat.rotation_interval_ms, 250, 60000, CFG.combat.rotation_interval_ms)
    CFG.combat.rotation_spells = cleanRotation(combat.rotation_spells, CFG.combat.rotation_spells)
    CFG.combat.target_rules = cleanTargets(combat.target_rules, CFG.combat.target_rules)
    CFG.combat.auto_exeta = cleanBoolean(combat.auto_exeta, CFG.combat.auto_exeta)
    CFG.combat.exeta_min_visible = clamp(combat.exeta_min_visible, 1, 20, CFG.combat.exeta_min_visible)
    CFG.combat.exeta_interval_ms = clamp(combat.exeta_interval_ms, 500, 120000, CFG.combat.exeta_interval_ms)
    CFG.combat.exeta_spells = cleanExetaRotation(combat.exeta_spells, CFG.combat.exeta_spells,
        CFG.combat.exeta_min_visible, CFG.combat.exeta_interval_ms)
    CFG.combat.attack_range = clamp(combat.attack_range, 1, 10, CFG.combat.attack_range)
    CFG.combat.target_timeout_ms = clamp(combat.target_timeout_ms, 1000, 120000, CFG.combat.target_timeout_ms)
    CFG.combat.auto_target_mode = clamp(combat.auto_target_mode,0,10,CFG.combat.auto_target_mode)
    CFG.combat.magic_shooter_on_hold = cleanBoolean(combat.magic_shooter_on_hold,CFG.combat.magic_shooter_on_hold)
    CFG.combat.auto_target_hotkey = cleanString(combat.auto_target_hotkey,CFG.combat.auto_target_hotkey,32)
    CFG.combat.auto_shooter_hotkey = cleanString(combat.auto_shooter_hotkey,CFG.combat.auto_shooter_hotkey,32)
    CFG.combat.auto_target_both = cleanString(combat.auto_target_both,CFG.combat.auto_target_both,32)
    CFG.combat.auto_change_profile = cleanString(combat.auto_change_profile,CFG.combat.auto_change_profile,64)
    CFG.combat.current_locked_target_id = 0
    CFG.combat.shooter_profiles = cleanShooterProfiles(combat.shooter_profiles, CFG.combat.shooter_profiles)
    local selectedShooter = cleanString(combat.selected_shooter_profile, CFG.combat.selected_shooter_profile, 48)
    CFG.combat.selected_shooter_profile = CFG.combat.shooter_profiles[selectedShooter] and selectedShooter or "Default"

    local conditions = type(data.conditions) == "table" and data.conditions or {}
    CFG.conditions.enabled = cleanBoolean(conditions.enabled, CFG.conditions.enabled)
    CFG.conditions.mana_shield = cleanBoolean(conditions.mana_shield, CFG.conditions.mana_shield)
    CFG.conditions.mana_shield_spell = cleanString(conditions.mana_shield_spell, CFG.conditions.mana_shield_spell, 64)
    CFG.conditions.paralyze = cleanBoolean(conditions.paralyze, CFG.conditions.paralyze)
    CFG.conditions.paralyze_spell = cleanString(conditions.paralyze_spell, CFG.conditions.paralyze_spell, 64)
    CFG.conditions.poison = cleanBoolean(conditions.poison, CFG.conditions.poison)
    CFG.conditions.poison_spell = cleanString(conditions.poison_spell, CFG.conditions.poison_spell, 64)
    CFG.conditions.utamo = cleanToggleConfig(conditions.utamo, CFG.conditions.utamo, 1)
    CFG.conditions.sample_interval_ms = clamp(conditions.sample_interval_ms, 250, 60000, CFG.conditions.sample_interval_ms)

    local support = type(data.support)=="table" and data.support or {}
    CFG.support.enabled = cleanBoolean(support.enabled,CFG.support.enabled)
    CFG.support.rules = cleanSupportRules(support.rules,CFG.support.rules)

    CFG.tools = cleanTools(data.tools, CFG.tools)

    local timer = type(data.timer) == "table" and data.timer or {}
    CFG.timer.enabled = cleanBoolean(timer.enabled, CFG.timer.enabled)
    CFG.timer.interval_ms = clamp(timer.interval_ms, 10000, 3600000, CFG.timer.interval_ms)
    CFG.timer.message = cleanString(timer.message, CFG.timer.message, 64)

    CFG.hotkey = cleanString(data.hotkey, CFG.hotkey, 32)
    CFG.window_x = clamp(data.window_x, -4096, 4096, CFG.window_x)
    CFG.window_y = clamp(data.window_y, -4096, 4096, CFG.window_y)
    CFG.enabled = false
    CFG.safe_boot_runtime_disabled = true
    RT.profile_name = cleanString(data.name, "CTOA Safe " .. string.upper(vocId), 64)
    return true
end

local function currentPresetSnapshot(id, name)
    return {
        id = cleanPresetId(id, "default"),
        name = cleanString(name, "CTOA Safe Default", 64),
        hotkey = CFG.hotkey,
        window_x = CFG.window_x,
        window_y = CFG.window_y,
        healing = {
            enabled = CFG.healing.enabled, spell_enabled = CFG.healing.spell_enabled,
            spell_threshold = CFG.healing.spell_threshold, spell = CFG.healing.spell,
            critical_spell = CFG.healing.critical_spell, critical_threshold = CFG.healing.critical_threshold,
            potion_enabled = CFG.healing.potion_enabled, potion_threshold = CFG.healing.potion_threshold,
            potion_hotkey = CFG.healing.potion_hotkey, mana_potion_enabled = CFG.healing.mana_potion_enabled,
            potion_item_id = CFG.healing.potion_item_id, mana_item_id = CFG.healing.mana_item_id,
            mana_threshold = CFG.healing.mana_threshold, mana_hotkey = CFG.healing.mana_hotkey,
            hp_randomization = CFG.healing.hp_randomization, mana_randomization = CFG.healing.mana_randomization,
            cooldown_ms = CFG.healing.cooldown_ms,
            rules = cleanHealingRules(CFG.healing.rules, DEFAULTS.healing.rules),
            spell_slots = cleanSpellSlots(CFG.healing.spell_slots, DEFAULTS.healing.spell_slots),
            potion_rules = cleanPotionRules(CFG.healing.potion_rules, DEFAULTS.healing.potion_rules),
            friend_enabled = CFG.healing.friend_enabled,
            friend_names = cleanStringList(CFG.healing.friend_names, {}, 16),
            friend_rules = cleanFriendRules(CFG.healing.friend_rules, DEFAULTS.healing.friend_rules),
        },
        combat = {
            enabled = CFG.combat.enabled, auto_attack = CFG.combat.auto_attack, chase = CFG.combat.chase,
            spell_rotation = CFG.combat.spell_rotation, rotation_preset = CFG.combat.rotation_preset,
            rotation_interval_ms = CFG.combat.rotation_interval_ms, rotation_spells = cleanRotation(CFG.combat.rotation_spells, DEFAULTS.combat.rotation_spells),
            auto_exeta = CFG.combat.auto_exeta, exeta_min_visible = CFG.combat.exeta_min_visible,
            exeta_interval_ms = CFG.combat.exeta_interval_ms,
            exeta_spells = cleanExetaRotation(CFG.combat.exeta_spells, DEFAULTS.combat.exeta_spells, CFG.combat.exeta_min_visible, CFG.combat.exeta_interval_ms),
            attack_range = CFG.combat.attack_range, target_timeout_ms = CFG.combat.target_timeout_ms,
            target_rules = cleanTargets(CFG.combat.target_rules, DEFAULTS.combat.target_rules),
            auto_target_mode = CFG.combat.auto_target_mode,
            magic_shooter_on_hold = CFG.combat.magic_shooter_on_hold,
            auto_target_hotkey = CFG.combat.auto_target_hotkey,
            auto_shooter_hotkey = CFG.combat.auto_shooter_hotkey,
            auto_target_both = CFG.combat.auto_target_both,
            auto_change_profile = CFG.combat.auto_change_profile,
            current_locked_target_id = 0,
            selected_shooter_profile = CFG.combat.selected_shooter_profile,
            shooter_profiles = cleanShooterProfiles(CFG.combat.shooter_profiles, DEFAULTS.combat.shooter_profiles),
        },
        conditions = {
            enabled = CFG.conditions.enabled, mana_shield = CFG.conditions.mana_shield,
            mana_shield_spell = CFG.conditions.mana_shield_spell, paralyze = CFG.conditions.paralyze,
            paralyze_spell = CFG.conditions.paralyze_spell, poison = CFG.conditions.poison,
            poison_spell = CFG.conditions.poison_spell,
            utamo = cleanToggleConfig(CFG.conditions.utamo, DEFAULTS.conditions.utamo, 1),
            sample_interval_ms = CFG.conditions.sample_interval_ms,
        },
        support = {enabled=CFG.support.enabled,rules=cleanSupportRules(CFG.support.rules,DEFAULTS.support.rules)},
        tools = cleanTools(CFG.tools, DEFAULTS.tools),
        timer = {enabled = CFG.timer.enabled, interval_ms = CFG.timer.interval_ms, message = CFG.timer.message},
    }
end

local saveProfile

local function loadProfile()
    local vocId = detectVocation()
    RT.vocation = vocId
    local path = profilePath(vocId)
    RT.profile_path = path
    RT.profile_migrated = false
    RT.active_preset = "default"
    RT.profile_name = "CTOA Safe " .. string.upper(vocId)
    RT.presets = {currentPresetSnapshot(RT.active_preset, RT.profile_name)}
    if not path or type(json) ~= "table" or type(json.decode) ~= "function" then
        setStatus("Safe profile unavailable: JSON support missing")
        return false
    end
    local file = io.open(path, "rb")
    if not file then
        setStatus("New Safe profile: " .. string.upper(vocId))
        return false
    end
    local size = file:seek("end") or 0
    file:seek("set", 0)
    if size <= 0 or size > MAX_PROFILE_BYTES then
        file:close(); setStatus("Safe profile rejected: invalid size"); return false
    end
    local content = file:read("*a"); file:close()
    local ok, data = pcall(json.decode, content)
    if not ok or type(data) ~= "table" or data.vocation ~= vocId then
        setStatus("Safe profile rejected: malformed JSON or vocation mismatch"); return false
    end
    if data.schema_version == LEGACY_PROFILE_SCHEMA then
        RT.active_preset = "default"
        RT.profile_name = cleanString(data.name, "CTOA Safe " .. string.upper(vocId), 64)
        applyPresetData(data, vocId)
        RT.presets = {currentPresetSnapshot(RT.active_preset, RT.profile_name)}
        RT.profile_migrated = true
        saveProfile()
        setStatus("Safe profile migrated v2 -> v3: " .. RT.profile_name)
        return true
    end
    if not validLibrary(data, vocId) then
        setStatus("Safe profile rejected: v3 schema or unknown field"); return false
    end
    RT.presets = deepCopy(data.presets)
    RT.active_preset = cleanPresetId(data.active_preset, "default")
    local preset = findPreset(RT.active_preset)
    if not preset then setStatus("Safe profile rejected: active preset missing"); return false end
    applyPresetData(preset, vocId)
    setStatus("Safe preset: " .. RT.profile_name)
    return true
end

saveProfile = function()
    local savePath = profilePath(RT.vocation)
    if not savePath or type(json) ~= "table" or type(json.encode) ~= "function" then return false end
    local _, index = findPreset(RT.active_preset)
    local snapshot = currentPresetSnapshot(RT.active_preset, RT.profile_name)
    if index then RT.presets[index] = snapshot else RT.presets[#RT.presets + 1] = snapshot end
    if #RT.presets > MAX_PRESETS then return false end
    local export = {schema_version=PROFILE_SCHEMA,vocation=RT.vocation,active_preset=RT.active_preset,presets=deepCopy(RT.presets)}
    local encodedOk, content = pcall(json.encode, export)
    if not encodedOk or type(content) ~= "string" or #content > MAX_PROFILE_BYTES then return false end
    local temporary = savePath .. ".tmp"
    local backup = savePath .. ".bak"
    local ok = pcall(function()
        local file = assert(io.open(temporary, "wb"))
        file:write(content)
        file:close()
        os.remove(backup)
        os.rename(savePath, backup)
        local moved, moveError = os.rename(temporary, savePath)
        if not moved then
            os.rename(backup, savePath)
            error(moveError or "profile replace failed")
        end
    end)
    if not ok then pcall(os.remove, temporary); return false end
    RT.profile_path  = savePath
    RT.profile_dirty = false
    return true
end

local function selectPreset(id)
    local preset = findPreset(id)
    if not preset then return false end
    RT.active_preset = preset.id
    applyPresetData(preset, RT.vocation)
    CFG.enabled = false; RT.armed = false
    return saveProfile()
end

local function createPreset(name)
    if #RT.presets >= MAX_PRESETS then return false end
    local base = cleanPresetId(name, "preset")
    local id, suffix = base, 2
    while findPreset(id) do id = base .. "_" .. tostring(suffix); suffix = suffix + 1 end
    RT.active_preset = id
    RT.profile_name = cleanString(name, "Preset " .. tostring(#RT.presets + 1), 64)
    RT.presets[#RT.presets + 1] = currentPresetSnapshot(id, RT.profile_name)
    CFG.enabled = false; RT.armed = false
    return saveProfile(), id
end

local function deletePreset(id)
    if #RT.presets <= 1 then return false end
    local _, index = findPreset(id)
    if not index then return false end
    table.remove(RT.presets, index)
    if RT.active_preset == cleanPresetId(id, "") then
        RT.active_preset = RT.presets[1].id
        applyPresetData(RT.presets[1], RT.vocation)
    end
    CFG.enabled = false; RT.armed = false
    return saveProfile()
end

local function exportPreset()
    if type(json) ~= "table" or type(json.encode) ~= "function" then return false end
    local preset = currentPresetSnapshot(RT.active_preset, RT.profile_name)
    local path = presetPath(RT.vocation, "_" .. preset.id .. "_export.json")
    if not path then return false end
    local ok, content = pcall(json.encode, {schema_version=PROFILE_SCHEMA,vocation=RT.vocation,active_preset=preset.id,presets={preset}})
    if not ok or type(content) ~= "string" or #content > MAX_PROFILE_BYTES then return false end
    local temporary = path .. ".tmp"
    local written = pcall(function() local file=assert(io.open(temporary,"wb"));file:write(content);file:close();os.remove(path);assert(os.rename(temporary,path)) end)
    if not written then pcall(os.remove, temporary); return false end
    return true, path
end

local function importPreset()
    if type(json) ~= "table" or type(json.decode) ~= "function" or #RT.presets >= MAX_PRESETS then return false end
    local path = presetPath(RT.vocation, "_import.json")
    local file = path and io.open(path, "rb") or nil
    if not file then return false end
    local size=file:seek("end") or 0;file:seek("set",0)
    if size<=0 or size>MAX_PROFILE_BYTES then file:close();return false end
    local content=file:read("*a");file:close()
    local ok,data=pcall(json.decode,content)
    if not ok or not validLibrary(data,RT.vocation) or #data.presets~=1 then return false end
    local imported=deepCopy(data.presets[1]);local base=cleanPresetId(imported.id,"imported");local id,suffix=base,2
    while findPreset(id) do id=base.."_"..tostring(suffix);suffix=suffix+1 end
    imported.id=id;RT.presets[#RT.presets+1]=imported;RT.active_preset=id
    applyPresetData(imported,RT.vocation);CFG.enabled=false;RT.armed=false
    return saveProfile(), id
end

-- ============================================================
-- KINGSVALE HELPER.JSON COMPATIBILITY ADAPTER
-- ============================================================
local markDirty
local scheduleAutosave
local KINGSVALE_SETTINGS_SCHEMA = "kingsvale-helper-json-v1"

local function resolveSpellWordsById(id, fallback)
    id = tonumber(id) or 0
    if id <= 0 then return fallback or "" end
    local sources = {rawget(_G,"SpellInfo"), rawget(_G,"Spells"), rawget(_G,"spells")}
    local gameLib = rawget(_G,"modules") and modules.gamelib or nil
    if type(gameLib) == "table" then
        sources[#sources + 1] = gameLib.SpellInfo
        sources[#sources + 1] = gameLib.Spells
    end
    for _, source in ipairs(sources) do
        if type(source) == "table" then
            local entry = source[id] or source[tostring(id)]
            if type(entry) == "table" then
                local words = entry.words or entry.formula or entry.incantation
                if type(words) == "string" and words ~= "" then return cleanString(words, fallback or "", 64) end
            end
            for _, candidate in pairs(source) do
                if type(candidate) == "table" and tonumber(candidate.id) == id then
                    local words = candidate.words or candidate.formula or candidate.incantation
                    if type(words) == "string" and words ~= "" then return cleanString(words, fallback or "", 64) end
                end
            end
        end
    end
    return fallback or ""
end

local function applyKingsValeSettings(data)
    if type(data) ~= "table" then return false, "settings_not_table" end

    if type(data.spells) == "table" then
        local slots = {}
        for index = 1, math.min(#data.spells, 3) do
            local source = type(data.spells[index]) == "table" and data.spells[index] or {}
            local previous = CFG.healing.spell_slots[index] or DEFAULTS.healing.spell_slots[index]
            local id = clamp(source.id, 0, 65535, 0)
            slots[index] = {id=id, words=resolveSpellWordsById(id, previous.words), percent=clamp(source.percent,1,100,80), enabled=id>0 or previous.enabled}
        end
        CFG.healing.spell_slots = cleanSpellSlots(slots, CFG.healing.spell_slots)
        local resolvedRules = {}
        for _, slot in ipairs(CFG.healing.spell_slots) do
            if slot.enabled and slot.words ~= "" then
                resolvedRules[#resolvedRules + 1] = {kind="heal",words=slot.words,threshold=slot.percent,cooldown_ms=950}
            end
        end
        if #resolvedRules > 0 then CFG.healing.rules = cleanHealingRules(resolvedRules,CFG.healing.rules) end
    end

    if type(data.potions) == "table" then
        local potions = {}
        for index = 1, math.min(#data.potions, 3) do
            local source = type(data.potions[index]) == "table" and data.potions[index] or {}
            potions[index] = {
                resource=index == 2 and "mana" or (index == 3 and "mana" or "hp"),
                item_id=source.id, threshold=source.percent, priority=source.priority,
                enabled=(tonumber(source.id) or 0)>0, cooldown_ms=950, hotkey="",
            }
        end
        CFG.healing.potion_rules = cleanPotionRules(potions, CFG.healing.potion_rules)
        CFG.healing.potion_enabled = false
        CFG.healing.mana_potion_enabled = false
    end

    local friends, names = {}, {}
    local function addFriends(list, words)
        if type(list) ~= "table" then return end
        for index = 1, math.min(#list, 2) do
            local source = type(list[index]) == "table" and list[index] or {}
            local name = cleanString(source.name, "", 64)
            friends[#friends + 1] = {name=name,words=words,threshold=source.percent,enabled=source.enabled,cooldown_ms=950}
            if name ~= "" then names[#names + 1] = name end
        end
    end
    addFriends(data.friendhealing, "exura sio")
    addFriends(data.gransiohealing, "exura gran sio")
    if #friends > 0 then
        CFG.healing.friend_rules = cleanFriendRules(friends, CFG.healing.friend_rules)
        CFG.healing.friend_names = cleanStringList(names, CFG.healing.friend_names, 16)
        CFG.healing.friend_enabled = true
    end

    CFG.combat.shooter_profiles = cleanShooterProfiles(data.shooterProfiles, CFG.combat.shooter_profiles)
    local selected = cleanString(data.selectedShooterProfile, CFG.combat.selected_shooter_profile, 48)
    if CFG.combat.shooter_profiles[selected] then CFG.combat.selected_shooter_profile = selected end
    CFG.combat.auto_attack = cleanBoolean(data.autoTargetEnabled, CFG.combat.auto_attack)
    CFG.combat.spell_rotation = cleanBoolean(data.magicShooterEnabled, CFG.combat.spell_rotation)
    CFG.combat.auto_exeta = cleanBoolean(data.autoExeta, CFG.combat.auto_exeta)
    CFG.combat.auto_target_mode = clamp(data.autoTargetMode,0,10,CFG.combat.auto_target_mode)
    CFG.combat.magic_shooter_on_hold = cleanBoolean(data.magicShooterOnHold,CFG.combat.magic_shooter_on_hold)
    CFG.combat.auto_target_hotkey = cleanString(data.autoTargetHotkey,CFG.combat.auto_target_hotkey,32)
    CFG.combat.auto_shooter_hotkey = cleanString(data.autoShooterHotkey,CFG.combat.auto_shooter_hotkey,32)
    CFG.combat.auto_target_both = cleanString(data.autoTargetBoth,CFG.combat.auto_target_both,32)
    CFG.combat.auto_change_profile = cleanString(data.autoChangeProfile,CFG.combat.auto_change_profile,64)
    CFG.combat.current_locked_target_id = 0

    CFG.tools.auto_eat_food = cleanBoolean(data.autoEatFood, CFG.tools.auto_eat_food)
    CFG.tools.change_gold = cleanBoolean(data.autoChangeGold, CFG.tools.change_gold)
    CFG.tools.auto_reconnect = cleanBoolean(data.autoReconnect,CFG.tools.auto_reconnect)
    CFG.tools.amulet_percent = clamp(data.amuletPercent,1,100,CFG.tools.amulet_percent)
    CFG.tools.ring_percent = clamp(data.ringPercent,1,100,CFG.tools.ring_percent)
    if type(data.training) == "table" and type(data.training[1]) == "table" then
        CFG.tools.mana_training_item_id = clamp(data.training[1].id,0,65535,CFG.tools.mana_training_item_id)
        CFG.tools.mana_training = cleanBoolean(data.training[1].enabled,CFG.tools.mana_training)
        CFG.tools.mana_training_threshold = clamp(data.training[1].percent,1,100,CFG.tools.mana_training_threshold)
    end
    if type(data.haste) == "table" and type(data.haste[1]) == "table" then
        CFG.tools.auto_haste = cleanBoolean(data.haste[1].enabled,CFG.tools.auto_haste)
        CFG.tools.pz_cast = not cleanBoolean(data.haste[1].safecast,not CFG.tools.pz_cast)
        CFG.tools.haste_spell_id = clamp(data.haste[1].id,0,65535,CFG.tools.haste_spell_id)
        CFG.tools.haste_spell = resolveSpellWordsById(data.haste[1].id,CFG.tools.haste_spell)
    end
    CFG.tools.amulet_config = cleanEquipConfig(data.amuletConfig, CFG.tools.amulet_config)
    CFG.tools.ring_config = cleanEquipConfig(data.ringConfig, CFG.tools.ring_config)
    CFG.tools.ammo_config = cleanToggleConfig(data.ammoConfig,CFG.tools.ammo_config,2)
    CFG.tools.buff = cleanToggleConfig(data.buff,CFG.tools.buff,1)
    if CFG.tools.buff[1] and CFG.tools.buff[1].id>0 then CFG.tools.buff[1].words=resolveSpellWordsById(CFG.tools.buff[1].id,CFG.tools.buff[1].words) end
    CFG.conditions.utamo = cleanToggleConfig(data.utamo,CFG.conditions.utamo,1)
    if CFG.conditions.utamo[1] and CFG.conditions.utamo[1].id>0 then
        CFG.conditions.utamo[1].words=resolveSpellWordsById(CFG.conditions.utamo[1].id,CFG.conditions.utamo[1].words~="" and CFG.conditions.utamo[1].words or "utamo vita")
        CFG.conditions.mana_shield=false
    end
    CFG.hotkey = cleanString(data.autoHelperEnabled, CFG.hotkey, 32)

    CFG.enabled = false
    RT.armed = false
    markDirty()
    scheduleAutosave()
    setStatus("KingsVale helper.json adapted; Safe remains disarmed")
    return true
end

local function kingsValeSettingsSnapshot()
    local spells = {}
    for index, slot in ipairs(cleanSpellSlots(CFG.healing.spell_slots, DEFAULTS.healing.spell_slots)) do
        spells[index] = {id=slot.id,percent=slot.percent}
    end
    local potions = {}
    for index, slot in ipairs(cleanPotionRules(CFG.healing.potion_rules, DEFAULTS.healing.potion_rules)) do
        potions[index] = {priority=slot.priority,id=slot.item_id,percent=slot.threshold}
    end
    local friendhealing, gransiohealing = {}, {}
    for _, rule in ipairs(cleanFriendRules(CFG.healing.friend_rules, DEFAULTS.healing.friend_rules)) do
        local target = rule.words:find("gran sio",1,true) and gransiohealing or friendhealing
        if #target < 2 then target[#target + 1] = {name=rule.name or "",enabled=rule.enabled,percent=rule.threshold} end
    end
    while #friendhealing < 2 do friendhealing[#friendhealing + 1] = {name="",enabled=false,percent=80} end
    while #gransiohealing < 2 do gransiohealing[#gransiohealing + 1] = {name="",enabled=false,percent=80} end

    local shooterProfiles = {}
    for name, profile in pairs(cleanShooterProfiles(CFG.combat.shooter_profiles, DEFAULTS.combat.shooter_profiles)) do
        local exported = {spells={},runes={},autoTargetMode=profile.auto_target_mode}
        for index, spell in ipairs(profile.spells) do
            exported.spells[index]={priority=spell.priority,creatures=spell.creatures,selfCast=spell.self_cast,id=spell.id,forceCast=spell.force_cast,percent=spell.percent}
        end
        for index, rune in ipairs(profile.runes) do
            exported.runes[index]={priority=rune.priority,id=rune.id,forceCast=rune.force_cast,creatures=rune.creatures}
        end
        shooterProfiles[name]=exported
    end
    return {
        spells=spells,potions=potions,shooterProfiles=shooterProfiles,selectedShooterProfile=CFG.combat.selected_shooter_profile,
        autoEatFood=CFG.tools.auto_eat_food,autoChangeGold=CFG.tools.change_gold,autoTargetEnabled=CFG.combat.auto_attack,
        autoTargetMode=CFG.combat.auto_target_mode,magicShooterEnabled=CFG.combat.spell_rotation,
        magicShooterOnHold=CFG.combat.magic_shooter_on_hold,currentLockedTargetId=0,
        autoTargetHotkey=CFG.combat.auto_target_hotkey,autoShooterHotkey=CFG.combat.auto_shooter_hotkey,
        autoTargetBoth=CFG.combat.auto_target_both,autoChangeProfile=CFG.combat.auto_change_profile,
        autoExeta=CFG.combat.auto_exeta,autoHelperEnabled=CFG.hotkey,autoReconnect=CFG.tools.auto_reconnect,
        helperEnabled=false,friendhealing=friendhealing,gransiohealing=gransiohealing,
        training={{id=CFG.tools.mana_training_item_id,enabled=CFG.tools.mana_training,percent=CFG.tools.mana_training_threshold}},
        haste={{id=CFG.tools.haste_spell_id,enabled=CFG.tools.auto_haste,safecast=not CFG.tools.pz_cast}},
        buff={{id=CFG.tools.buff[1] and CFG.tools.buff[1].id or 0,enabled=CFG.tools.buff[1] and CFG.tools.buff[1].enabled or false,safecast=CFG.tools.buff[1] and CFG.tools.buff[1].safecast or true}},
        utamo={{id=CFG.conditions.utamo[1] and CFG.conditions.utamo[1].id or 0,enabled=CFG.conditions.utamo[1] and CFG.conditions.utamo[1].enabled or false,percent=CFG.conditions.utamo[1] and CFG.conditions.utamo[1].percent or 80}},
        ammoConfig={{id=CFG.tools.ammo_config[1] and CFG.tools.ammo_config[1].id or 0,enabled=CFG.tools.ammo_config[1] and CFG.tools.ammo_config[1].enabled or false},{id=CFG.tools.ammo_config[2] and CFG.tools.ammo_config[2].id or 0,enabled=CFG.tools.ammo_config[2] and CFG.tools.ammo_config[2].enabled or false}},
        amuletPercent=CFG.tools.amulet_percent,ringPercent=CFG.tools.ring_percent,
        amuletConfig=deepCopy(CFG.tools.amulet_config),ringConfig=deepCopy(CFG.tools.ring_config),
    }
end

local function importKingsValeSettings(path)
    if type(json) ~= "table" or type(json.decode) ~= "function" then return false, "json_unavailable" end
    if type(path) ~= "string" or path == "" then return false, "path_required" end
    local file = io.open(path,"rb"); if not file then return false,"file_missing" end
    local size=file:seek("end") or 0;file:seek("set",0)
    if size<=0 or size>MAX_PROFILE_BYTES then file:close();return false,"invalid_size" end
    local content=file:read("*a");file:close()
    local ok,data=pcall(json.decode,content);if not ok then return false,"malformed_json" end
    return applyKingsValeSettings(data)
end

local function exportKingsValeSettings(path)
    if type(json) ~= "table" or type(json.encode) ~= "function" then return false,"json_unavailable" end
    path = type(path)=="string" and path or presetPath(RT.vocation,"_kingsvale_helper.json")
    if not path or path=="" then return false,"path_unavailable" end
    local ok,content=pcall(json.encode,kingsValeSettingsSnapshot())
    if not ok or type(content)~="string" or #content>MAX_PROFILE_BYTES then return false,"encode_failed" end
    local temporary=path..".tmp"
    local written=pcall(function() local file=assert(io.open(temporary,"wb"));file:write(content);file:close();os.remove(path);assert(os.rename(temporary,path)) end)
    if not written then pcall(os.remove,temporary);return false,"write_failed" end
    return true,path
end

markDirty = function()
    RT.profile_dirty = true
end

scheduleAutosave = function()
    if RT.save_event then
        removeEvent(RT.save_event)
        RT.save_event = nil
    end
    if type(scheduleEvent) == "function" then
        RT.save_event = scheduleEvent(function()
            if RT.profile_dirty then saveProfile() end
            RT.save_event = nil
        end, AUTOSAVE_MS)
    end
end

-- ============================================================
-- WIDGET FACTORY (self-contained, no ctoa_helper_ui.lua dep)
-- ============================================================
local function mkWidget(kind, parent, id, text, x, y, w, h)
    if not g_ui or not g_ui.createWidget then return nil end
    local ok, widget = pcall(function() return g_ui.createWidget(kind, parent) end)
    if not ok or not widget then return nil end
    if id   and widget.setId   then pcall(function() widget:setId(id) end) end
    if text and widget.setText then pcall(function() widget:setText(text) end) end
    if widget.breakAnchors then pcall(function() widget:breakAnchors() end) end
    if widget.addAnchor and AnchorLeft and AnchorTop then
        pcall(function()
            widget:addAnchor(AnchorLeft, "parent", AnchorLeft)
            widget:addAnchor(AnchorTop,  "parent", AnchorTop)
        end)
    end
    -- Position: margin preferred, setPosition as fallback
    local posOk = false
    if widget.setMarginLeft and widget.setMarginTop then
        local ok2 = pcall(function()
            widget:setMarginLeft(x or 0)
            widget:setMarginTop(y or 0)
        end)
        posOk = ok2
    end
    if not posOk and widget.setPosition then
        pcall(function() widget:setPosition({x = x or 0, y = y or 0}) end)
    end
    if widget.resize then
        pcall(function() widget:resize(w or 120, h or 20) end)
    else
        if widget.setWidth  then pcall(function() widget:setWidth(w or 120) end) end
        if widget.setHeight then pcall(function() widget:setHeight(h or 20) end) end
    end
    if widget.setTextAutoResize then pcall(function() widget:setTextAutoResize(false) end) end
    if kind == "Label" then
        if widget.setPhantom then pcall(function() widget:setPhantom(true) end) end
        if widget.setFontScale then pcall(function() widget:setFontScale(1.0) end) end
    end
    return widget
end

local function setColor(widget, hex)
    if widget and widget.setColor then
        pcall(function() widget:setColor(hex) end)
    end
end

local function setBg(widget, hex)
    if widget and widget.setBackgroundColor then
        pcall(function() widget:setBackgroundColor(hex) end)
    end
end

local function setFontScale(widget, scale)
    if widget and widget.setFontScale then
        pcall(function() widget:setFontScale(scale) end)
    end
end

-- ============================================================
-- SAFE-BOOT GUARD
-- ============================================================
local function applySafeBoot()
    RT.armed = false
    CFG.enabled = false
    CFG.safe_boot_runtime_disabled = true
    RT.compatibility_runtime_disabled = true
    setStatus("Safe boot: click ENABLE to arm")
end

-- ============================================================
-- MODULE DEFINITIONS
-- ============================================================
local MODULES = {
    {id = "healing",    label = "HEALING",     icon = "[H]",  cfg_key = "healing"},
    {id = "combat",     label = "COMBAT",      icon = "[C]",  cfg_key = "combat"},
    {id = "conditions", label = "CONDITIONS",  icon = "[D]",  cfg_key = "conditions"},
    {id = "support",    label = "SUPPORT",     icon = "[S]",  cfg_key = "support"},
    {id = "timer",      label = "TIMER",       icon = "[T]",  cfg_key = "timer"},
}

-- ============================================================
-- EDIT PANELS
-- ============================================================
local function destroyEditPanel()
    if UI.edit_panel then
        if UI.edit_panel.destroy then UI.edit_panel:destroy() end
        UI.edit_panel = nil
    end
    UI.active_edit = nil
end

-- Generic number row: label + [-] [value] [+]
local function mkNumRow(parent, id, label, x, y, getValue, onDelta)
    mkWidget("Label", parent, id .. "Lbl", label, x, y + 3, 130, 16)
    local minus = mkWidget("Button", parent, id .. "Minus", "-", x + 136, y, 20, 20)
    local valLbl = mkWidget("Label", parent, id .. "Val", tostring(getValue()), x + 158, y + 3, 44, 14)
    setColor(valLbl, "#f0c56a")
    local plus = mkWidget("Button", parent, id .. "Plus", "+", x + 204, y, 20, 20)
    if minus then minus.onClick = function()
        onDelta(-1)
        valLbl:setText(tostring(getValue()))
        markDirty(); scheduleAutosave()
    end end
    if plus then plus.onClick = function()
        onDelta(1)
        valLbl:setText(tostring(getValue()))
        markDirty(); scheduleAutosave()
    end end
    return valLbl
end

-- Generic checkbox row
local function mkCheckRow(parent, id, label, x, y, getValue, onToggle)
    local chk = mkWidget("CheckBox", parent, id .. "Chk", "", x, y, 16, 16)
    if chk and chk.setChecked then chk:setChecked(getValue()) end
    mkWidget("Label", parent, id .. "Lbl", label, x + 20, y + 2, 200, 14)
    if chk then chk.onCheckChange = function(w, checked)
        onToggle(checked)
        markDirty(); scheduleAutosave()
    end end
    return chk
end

local function droppedItemId(draggedWidget)
    if not draggedWidget then return 0 end
    local candidate=draggedWidget.currentDragThing
    if type(candidate)=="number" then return math.max(0,math.floor(candidate)) end
    if candidate and type(candidate.getId)=="function" then
        local ok,value=pcall(function() return candidate:getId() end)
        if ok and tonumber(value) then return math.max(0,math.floor(tonumber(value))) end
    end
    local readers={
        function() return draggedWidget:getItemId() end,
        function() return draggedWidget:getItem():getId() end,
        function() return draggedWidget.item:getItemId() end,
        function() return draggedWidget.cache.itemId end,
    }
    for _,reader in ipairs(readers) do
        local ok,value=pcall(reader)
        if ok and tonumber(value) and tonumber(value)>0 then return math.floor(tonumber(value)) end
    end
    return 0
end

local function configureItemSettingSlot(slot, tooltip)
    if not slot then return end
    slot.selectable=true
    slot.editable=true
    if slot.setVirtual then pcall(function() slot:setVirtual(true) end) end
    if slot.setDraggable then pcall(function() slot:setDraggable(true) end) end
    if slot.setFocusable then pcall(function() slot:setFocusable(true) end) end
    if slot.setTooltip then pcall(function() slot:setTooltip(tooltip or "Drop item from backpack or actionbar") end) end
end

local function mkItemSlot(parent,id,label,x,y,itemId,onItemChanged)
    mkWidget("Label",parent,id.."Lbl",label,x,y+8,112,16)
    local backdrop=mkWidget("Label",parent,id.."Backdrop","",x+116,y-2,38,38)
    setBg(backdrop,"#141414")
    if backdrop and backdrop.setBorderColor then pcall(function() backdrop:setBorderColor("#8a8a8a") end) end
    if backdrop and backdrop.setBorderWidth then pcall(function() backdrop:setBorderWidth(1) end) end
    local slot=mkWidget("UIItem",parent,id.."Slot","",x+118,y,34,34)
    if not slot then
        slot=mkWidget("Item",parent,id.."Slot","",x+118,y,34,34)
    end
    if slot then
        configureItemSettingSlot(slot,"Drop item from backpack or actionbar; click if item selector is available")
        if slot.setItemId then pcall(function() slot:setItemId(tonumber(itemId) or 0) end) end
        slot.onDrop=function(self,draggedWidget)
            local newId=droppedItemId(draggedWidget)
            if newId<=0 then return false end
            if self.setItemId then pcall(function() self:setItemId(newId) end) end
            onItemChanged(newId)
            markDirty(); scheduleAutosave()
            return true
        end
    end
    local clear=mkWidget("Button",parent,id.."Clear","CLEAR",x+158,y+6,58,22)
    if clear then clear.onClick=function()
        if slot and slot.setItemId then pcall(function() slot:setItemId(0) end) end
        onItemChanged(0); markDirty(); scheduleAutosave()
    end end
    return slot
end

local function mkTextRow(parent, id, label, x, y, value, onChange, width)
    mkWidget("Label", parent, id .. "Lbl", label, x, y + 3, 105, 16)
    local edit = mkWidget("TextEdit", parent, id .. "Edit", tostring(value or ""), x + 108, y, width or 180, 20)
    if edit then
        if edit.setMaxLength then pcall(function() edit:setMaxLength(512) end) end
        edit.onTextChange = function(_, text)
            onChange(tostring(text or ""))
            if not UI.loading_selection then markDirty(); scheduleAutosave() end
        end
    end
    return edit
end

local function joinList(items)
    local result = {}
    for _, item in ipairs(items or {}) do result[#result + 1] = tostring(item) end
    return table.concat(result, ", ")
end

local function parseList(text, fallback)
    local result = {}
    for item in tostring(text or ""):gmatch("[^,;]+") do
        item = item:gsub("^%s+", ""):gsub("%s+$", "")
        if item ~= "" and #item <= 64 and #result < 16 then result[#result + 1] = item end
    end
    return #result > 0 and result or fallback
end

local function rotationText(spells)
    local result = {}
    for _, spell in ipairs(spells or {}) do
        result[#result + 1] = table.concat({spell.words or "", spell.min_nearby or 1, spell.max_nearby or 99, spell.cooldown_ms or 2000}, "|")
    end
    return table.concat(result, "; ")
end

local function parseRotation(text, fallback)
    local result = {}
    for entry in tostring(text or ""):gmatch("[^;]+") do
        local words, minimum, maximum, cooldown = entry:match("^%s*(.-)%s*|%s*(%d+)%s*|%s*(%d+)%s*|%s*(%d+)%s*$")
        if words and words ~= "" and #words <= 64 and #result < 16 then
            result[#result + 1] = {words = words,
                min_nearby = math.max(1, math.min(30, tonumber(minimum) or 1)),
                max_nearby = math.max(1, math.min(30, tonumber(maximum) or 30)),
                cooldown_ms = math.max(250, math.min(60000, tonumber(cooldown) or 2000))}
        end
    end
    return #result > 0 and result or fallback
end

local function mkRuleList(parent, id, x, y, width, height, items, describe)
    local state = {selected = (#items > 0) and 1 or nil, rows = {}}
    local box = mkWidget("Panel", parent, id .. "Box", "", x, y, width, height)
    setBg(box, "#1d1d1d")
    local function refresh()
        for _, row in ipairs(state.rows) do if row.destroy then row:destroy() end end
        state.rows = {}
        for index, item in ipairs(items) do
            local row = mkWidget("Button", box, id .. "Row" .. index, describe(item, index), 2, 2 + (index - 1) * 22, width - 4, 20)
            if row then
                if index == state.selected then setBg(row, "#3b3322") end
                row.onClick = function()
                    state.selected = index; refresh()
                    if type(state.onSelect)=="function" then state.onSelect(item,index) end
                end
                state.rows[#state.rows + 1] = row
            end
        end
    end
    state.refresh = refresh
    refresh()
    return state
end

local function removeSelected(items, state)
    if state.selected and items[state.selected] then
        table.remove(items, state.selected)
        if #items == 0 then state.selected = nil else state.selected = math.min(state.selected, #items) end
        state.refresh(); markDirty(); scheduleAutosave()
    end
end

local function moveSelected(items, state, delta)
    local from=state.selected; local to=from and (from+delta) or nil
    if from and to and items[from] and items[to] then
        items[from],items[to]=items[to],items[from]; state.selected=to
        state.refresh(); markDirty(); scheduleAutosave()
    end
end

local openEditPanel

local function openEditHealing(parent, x, y)
    local H = CFG.healing
    local rules = H.rules
    setColor(mkWidget("Label", parent, "ehTitle", "HEALING RULES", x + 10, y, 290, 16), "#f0c56a")
    local list = mkRuleList(parent, "healRules", x + 10, y + 22, 294, 120, rules,
        function(v) return string.format("[%s] %s  HP<=%d%%", v.kind, v.words, v.threshold) end)
    local spell = mkTextRow(parent, "healAdd", "Spell", x + 10, y + 150, "", function() end)
    local threshold,kind = 70,"heal"
    local kindLabel=mkWidget("Label",parent,"healKindValue",kind,x+118,y+179,90,16); setColor(kindLabel,"#f0c56a")
    mkWidget("Label",parent,"healKindLabel","Rule type",x+10,y+179,100,16)
    local kindCycle=mkWidget("Button",parent,"healKindCycle","CHANGE",x+214,y+176,90,20)
    if kindCycle then kindCycle.onClick=function() if kind=="heal" then kind="critical" elseif kind=="critical" then kind="support" else kind="heal" end; if kindLabel then kindLabel:setText(kind) end end end
    local thresholdValue=mkNumRow(parent, "healHp", "HP threshold", x + 10, y + 202, function() return threshold end,
        function(d) threshold = math.max(1, math.min(99, threshold + d * 5)) end)
    list.onSelect=function(item)
        UI.loading_selection=true
        if spell and spell.setText then spell:setText(item.words or "") end
        threshold=item.threshold or 70; kind=item.kind or "heal"
        if thresholdValue then thresholdValue:setText(tostring(threshold)) end
        if kindLabel then kindLabel:setText(kind) end
        UI.loading_selection=false
    end
    local plus = mkWidget("Button", parent, "healPlus", "+ ADD RULE", x + 10, y + 232, 140, 24)
    local minus = mkWidget("Button", parent, "healMinus", "- REMOVE", x + 164, y + 232, 140, 24)
    if plus then plus.onClick = function()
        local words = spell and spell:getText() or ""
        if words ~= "" then rules[#rules + 1] = {kind=kind, words=words, threshold=threshold, cooldown_ms=950}; list.selected=#rules; list.refresh(); markDirty(); scheduleAutosave() end
    end end
    if minus then minus.onClick = function() removeSelected(rules, list) end end
    mkTextRow(parent, "ehPotKey", "HP potion key", x + 10, y + 270, H.potion_hotkey, function(v) H.potion_hotkey=v end)
    mkTextRow(parent, "ehManaKey", "Mana potion key", x + 10, y + 296, H.mana_hotkey, function(v) H.mana_hotkey=v end)
    local edit=mkWidget("Button",parent,"healEdit","EDIT SELECTED",x+10,y+326,140,22)
    local up=mkWidget("Button",parent,"healUp","UP",x+164,y+326,66,22)
    local down=mkWidget("Button",parent,"healDown","DOWN",x+238,y+326,66,22)
    if edit then edit.onClick=function() local item=list.selected and rules[list.selected]; local words=spell and spell:getText() or ""; if item and words~="" then item.words=words; item.kind=kind; item.threshold=threshold; list.refresh(); markDirty(); scheduleAutosave() end end end
    if up then up.onClick=function() moveSelected(rules,list,-1) end end
    if down then down.onClick=function() moveSelected(rules,list,1) end end
    mkNumRow(parent,"healPotionPct","HP potion %",x+10,y+356,function() return H.potion_threshold end,
        function(d) H.potion_threshold=math.max(1,math.min(99,H.potion_threshold+d)) end)
    mkNumRow(parent,"healHpRandom","HP random +/-",x+10,y+382,function() return H.hp_randomization end,
        function(d) H.hp_randomization=math.max(0,math.min(20,H.hp_randomization+d)) end)
    mkNumRow(parent,"healManaPct","Mana potion %",x+10,y+408,function() return H.mana_threshold end,
        function(d) H.mana_threshold=math.max(1,math.min(99,H.mana_threshold+d)) end)
    mkNumRow(parent,"healManaRandom","Mana random +/-",x+10,y+434,function() return H.mana_randomization end,
        function(d) H.mana_randomization=math.max(0,math.min(20,H.mana_randomization+d)) end)
    mkItemSlot(parent,"healHpItem","HP item",x+10,y+462,H.potion_item_id,function(id) H.potion_item_id=id end)
    mkItemSlot(parent,"healManaItem","Mana item",x+10,y+500,H.mana_item_id,function(id) H.mana_item_id=id end)
end

local function openEditCombat(parent, x, y)
    local C = CFG.combat
    setColor(mkWidget("Label", parent, "ecTitle2", "TARGETING", x + 10, y, 290, 16), "#f0c56a")
    local targets = mkRuleList(parent, "targetRules", x + 10, y + 20, 294, 82, C.target_rules,
        function(v) return string.format("P%d  %s  range:%d", v.priority, v.name, v.max_distance) end)
    local targetName = mkTextRow(parent, "targetName", "Monster", x + 10, y + 108, "", function() end)
    local priority, distance = 5, 7
    local priorityValue=mkNumRow(parent, "targetPriority", "Priority", x + 10, y + 134, function() return priority end, function(d) priority=math.max(0,math.min(10,priority+d)) end)
    local distanceValue=mkNumRow(parent, "targetDistance", "Max distance", x + 10, y + 160, function() return distance end, function(d) distance=math.max(1,math.min(10,distance+d)) end)
    targets.onSelect=function(item)
        UI.loading_selection=true
        if targetName and targetName.setText then targetName:setText(item.name or "") end
        priority=item.priority or 5; distance=item.max_distance or 7
        if priorityValue then priorityValue:setText(tostring(priority)) end
        if distanceValue then distanceValue:setText(tostring(distance)) end
        UI.loading_selection=false
    end
    local targetPlus=mkWidget("Button",parent,"targetPlus","+ TARGET",x+10,y+188,140,22)
    local targetMinus=mkWidget("Button",parent,"targetMinus","- TARGET",x+164,y+188,140,22)
    if targetPlus then targetPlus.onClick=function() local name=targetName and targetName:getText() or ""; if name~="" then C.target_rules[#C.target_rules+1]={name=name,priority=priority,max_distance=distance,chase=C.chase}; targets.selected=#C.target_rules; targets.refresh(); markDirty(); scheduleAutosave() end end end
    if targetMinus then targetMinus.onClick=function() removeSelected(C.target_rules,targets) end end
    local targetEdit=mkWidget("Button",parent,"targetEdit","EDIT",x+10,y+214,92,22); local targetUp=mkWidget("Button",parent,"targetUp","UP",x+108,y+214,92,22); local targetDown=mkWidget("Button",parent,"targetDown","DOWN",x+206,y+214,98,22)
    if targetEdit then targetEdit.onClick=function() local item=targets.selected and C.target_rules[targets.selected]; local name=targetName and targetName:getText() or ""; if item and name~="" then item.name=name; item.priority=priority; item.max_distance=distance; targets.refresh(); markDirty(); scheduleAutosave() end end end
    if targetUp then targetUp.onClick=function() moveSelected(C.target_rules,targets,-1) end end
    if targetDown then targetDown.onClick=function() moveSelected(C.target_rules,targets,1) end end

    setColor(mkWidget("Label", parent, "rotationTitle", "SPELL ROTATION", x + 10, y + 244, 290, 16), "#f0c56a")
    local rotations=mkRuleList(parent,"rotationRules",x+10,y+264,294,78,C.rotation_spells,
        function(v)
            local countText=v.use_mob_count==false and "any mobs" or string.format("%d+ mobs",v.min_nearby or 1)
            return string.format("%s  %s <=%d sqm",v.words,countText,v.max_distance or 7)
        end)
    local rotationSpell=mkTextRow(parent,"rotationSpell","Spell",x+10,y+348,"",function() end)
    local minMobs,distance,cooldown,useMobCount=1,7,2000,true
    local countCheck=mkCheckRow(parent,"rotationCount","Require monster count",x+10,y+374,function() return useMobCount end,function(v) useMobCount=v end)
    local minValue=mkNumRow(parent,"rotationMin","Monsters >=",x+10,y+398,function() return minMobs end,function(d) minMobs=math.max(1,math.min(20,minMobs+d)) end)
    local distanceValue=mkNumRow(parent,"rotationDistance","Distance (sqm)",x+10,y+424,function() return distance end,function(d) distance=math.max(1,math.min(10,distance+d)) end)
    local cooldownValue=mkNumRow(parent,"rotationCd","Cooldown ms",x+10,y+450,function() return cooldown end,function(d) cooldown=math.max(250,math.min(60000,cooldown+d*250)) end)
    rotations.onSelect=function(item)
        UI.loading_selection=true
        if rotationSpell and rotationSpell.setText then rotationSpell:setText(item.words or "") end
        minMobs=item.min_nearby or 1; distance=item.max_distance or 7; cooldown=item.cooldown_ms or 2000; useMobCount=item.use_mob_count~=false
        if minValue then minValue:setText(tostring(minMobs)) end
        if distanceValue then distanceValue:setText(tostring(distance)) end
        if countCheck and countCheck.setChecked then countCheck:setChecked(useMobCount) end
        if cooldownValue then cooldownValue:setText(tostring(cooldown)) end
        UI.loading_selection=false
    end
    local rotationPlus=mkWidget("Button",parent,"rotationPlus","+ SPELL",x+10,y+478,140,22)
    local rotationMinus=mkWidget("Button",parent,"rotationMinus","- SPELL",x+164,y+478,140,22)
    if rotationPlus then rotationPlus.onClick=function() local words=rotationSpell and rotationSpell:getText() or ""; if words~="" then C.rotation_spells[#C.rotation_spells+1]={words=words,use_mob_count=useMobCount,min_nearby=minMobs,max_distance=distance,cooldown_ms=cooldown}; rotations.selected=#C.rotation_spells; rotations.refresh(); C.rotation_preset="custom"; markDirty(); scheduleAutosave() end end end
    if rotationMinus then rotationMinus.onClick=function() removeSelected(C.rotation_spells,rotations) end end
    local rotationEdit=mkWidget("Button",parent,"rotationEdit","EDIT",x+10,y+506,92,22); local rotationUp=mkWidget("Button",parent,"rotationUp","UP",x+108,y+506,92,22); local rotationDown=mkWidget("Button",parent,"rotationDown","DOWN",x+206,y+506,98,22)
    if rotationEdit then rotationEdit.onClick=function() local item=rotations.selected and C.rotation_spells[rotations.selected]; local words=rotationSpell and rotationSpell:getText() or ""; if item and words~="" then item.words=words; item.use_mob_count=useMobCount; item.min_nearby=minMobs; item.max_distance=distance; item.cooldown_ms=cooldown; rotations.refresh(); markDirty(); scheduleAutosave() end end end
    if rotationUp then rotationUp.onClick=function() moveSelected(C.rotation_spells,rotations,-1) end end
    if rotationDown then rotationDown.onClick=function() moveSelected(C.rotation_spells,rotations,1) end end
    local exetaEditor=mkWidget("Button",parent,"openExetaEditor","EDIT EXETA ROTATION",x+10,y+534,294,22)
    if exetaEditor then exetaEditor.onClick=function() openEditPanel("combat_exeta") end end
    if false then
    local row = y
    setColor(mkWidget("Label", parent, "ecTitle", "— Combat editor —", x + 10, row, EDIT_W - 20, 16), "#f0c56a")
    row = row + 24

    mkCheckRow(parent, "ecAA",   "Auto Attack",    x + 10, row, function() return C.auto_attack end,   function(v) C.auto_attack = v end)
    row = row + 22
    mkCheckRow(parent, "ecChase","Chase",           x + 10, row, function() return C.chase end,         function(v) C.chase = v end)
    row = row + 22
    mkCheckRow(parent, "ecRot",  "Spell Rotation",  x + 10, row, function() return C.spell_rotation end, function(v) C.spell_rotation = v end)
    row = row + 22
    mkCheckRow(parent, "ecExeta","Auto Exeta",      x + 10, row, function() return C.auto_exeta end,    function(v) C.auto_exeta = v end)
    row = row + 24

    mkNumRow(parent, "ecExetaMin", "Exeta min vis", x + 10, row,
        function() return C.exeta_min_visible end,
        function(d) C.exeta_min_visible = math.max(1, C.exeta_min_visible + d) end)
    row = row + 26

    mkTextRow(parent, "ecExeta", "Exeta spells", x + 10, row, joinList(C.exeta_spells),
        function(v) C.exeta_spells = parseList(v, C.exeta_spells) end)
    row = row + 24
    mkNumRow(parent, "ecRange", "Attack range", x + 10, row,
        function() return C.attack_range end,
        function(d) C.attack_range = math.max(1, math.min(10, C.attack_range + d)) end)
    row = row + 26
    mkNumRow(parent, "ecRotInt", "Rotation ms", x + 10, row,
        function() return C.rotation_interval_ms end,
        function(d) C.rotation_interval_ms = math.max(250, math.min(60000, C.rotation_interval_ms + d * 250)) end)
    row = row + 26
    mkTextRow(parent, "ecRotList", "Spell|min|max|ms", x + 10, row, rotationText(C.rotation_spells),
        function(v) C.rotation_spells = parseRotation(v, C.rotation_spells); C.rotation_preset = "custom" end)
    end
end

local function openEditExeta(parent,x,y)
    local C=CFG.combat
    setColor(mkWidget("Label",parent,"exetaTitle","EXETA ROTATION",x+10,y,290,16),"#f0c56a")
    mkCheckRow(parent,"exetaEnabled","Auto Exeta",x+10,y+22,function() return C.auto_exeta end,function(v) C.auto_exeta=v end)
    local list=mkRuleList(parent,"exetaRules",x+10,y+48,294,126,C.exeta_spells,
        function(v) return string.format("%s  %d+ mobs  %d ms",v.words or "",v.min_nearby or 2,v.cooldown_ms or 5000) end)
    local spell=mkTextRow(parent,"exetaSpell","Spell",x+10,y+184,"",function() end)
    local minimum,cooldown=2,5000
    local minValue=mkNumRow(parent,"exetaMin","Monsters >=",x+10,y+212,function() return minimum end,
        function(d) minimum=math.max(1,math.min(20,minimum+d)) end)
    local cooldownValue=mkNumRow(parent,"exetaCooldown","Cooldown ms",x+10,y+240,function() return cooldown end,
        function(d) cooldown=math.max(500,math.min(120000,cooldown+d*500)) end)
    list.onSelect=function(item)
        UI.loading_selection=true
        if spell and spell.setText then spell:setText(item.words or "") end
        minimum=item.min_nearby or 2;cooldown=item.cooldown_ms or 5000
        if minValue then minValue:setText(tostring(minimum)) end
        if cooldownValue then cooldownValue:setText(tostring(cooldown)) end
        UI.loading_selection=false
    end
    local plus=mkWidget("Button",parent,"exetaPlus","+ EXETA",x+10,y+278,140,22)
    local minus=mkWidget("Button",parent,"exetaMinus","- EXETA",x+164,y+278,140,22)
    if plus then plus.onClick=function()
        local words=spell and spell:getText() or ""
        if words~="" then C.exeta_spells[#C.exeta_spells+1]={words=words,min_nearby=minimum,cooldown_ms=cooldown};list.selected=#C.exeta_spells;list.refresh();markDirty();scheduleAutosave() end
    end end
    if minus then minus.onClick=function() removeSelected(C.exeta_spells,list) end end
    local edit=mkWidget("Button",parent,"exetaEdit","EDIT",x+10,y+306,92,22)
    local up=mkWidget("Button",parent,"exetaUp","UP",x+108,y+306,92,22)
    local down=mkWidget("Button",parent,"exetaDown","DOWN",x+206,y+306,98,22)
    if edit then edit.onClick=function()
        local item=list.selected and C.exeta_spells[list.selected];local words=spell and spell:getText() or ""
        if item and words~="" then item.words=words;item.min_nearby=minimum;item.cooldown_ms=cooldown;list.refresh();markDirty();scheduleAutosave() end
    end end
    if up then up.onClick=function() moveSelected(C.exeta_spells,list,-1) end end
    if down then down.onClick=function() moveSelected(C.exeta_spells,list,1) end end
    local back=mkWidget("Button",parent,"exetaBack","BACK TO COMBAT",x+10,y+352,294,24)
    if back then back.onClick=function() openEditPanel("combat") end end
end

local function openEditConditions(parent, x, y)
    local CC = CFG.conditions
    local row = y
    setColor(mkWidget("Label", parent, "ecoTitle", "CONDITIONS / SUPPORT", x + 10, row, EDIT_W - 20, 16), "#f0c56a")
    row = row + 24
    mkCheckRow(parent, "ecoMS",  "Mana Shield",    x + 10, row, function() return CC.mana_shield end,  function(v) CC.mana_shield = v end)
    row = row + 22
    mkTextRow(parent, "ecoMSSpell", "Shield spell", x + 10, row, CC.mana_shield_spell, function(v) CC.mana_shield_spell = v end)
    row = row + 24
    mkCheckRow(parent, "ecoPar", "Cure Paralyze",  x + 10, row, function() return CC.paralyze end,     function(v) CC.paralyze = v end)
    row = row + 22
    mkTextRow(parent, "ecoParSpell", "Paralyze spell", x + 10, row, CC.paralyze_spell, function(v) CC.paralyze_spell = v end)
    row = row + 24
    mkCheckRow(parent, "ecoPoi", "Cure Poison",    x + 10, row, function() return CC.poison end,       function(v) CC.poison = v end)
    row = row + 22
    mkTextRow(parent, "ecoPoiSpell", "Poison spell", x + 10, row, CC.poison_spell, function(v) CC.poison_spell = v end)
end

local function openEditSupport(parent,x,y)
    local S=CFG.support
    setColor(mkWidget("Label",parent,"supportTitle","SUPPORT RULES: SPELL / ITEM",x+10,y,290,16),"#f0c56a")
    mkCheckRow(parent,"supportEnabled","Enabled",x+10,y+22,function() return S.enabled end,function(v) S.enabled=v end)
    local list=mkRuleList(parent,"supportRules",x+10,y+48,294,100,S.rules,
        function(v)
            local action=v.action=="item" and ("item:"..tostring(v.item_id or 0)) or (v.words or "spell")
            local condition=v.resource=="always" and "always" or string.format("%s<=%d-%d%%",v.resource or "hp",v.threshold_min or 60,v.threshold_max or 70)
            return string.format("[%s] %s  %s",v.action or "spell",action,condition)
        end)
    local action,resource,interval,minimum,maximum,itemId="spell","always",1000,60,70,0
    mkWidget("Label",parent,"supportActionLbl","Action",x+10,y+157,100,16)
    local actionBtn=mkWidget("Button",parent,"supportAction",string.upper(action),x+118,y+152,96,22)
    if actionBtn then actionBtn.onClick=function() action=action=="spell" and "item" or "spell"; actionBtn:setText(string.upper(action)) end end
    mkWidget("Label",parent,"supportResourceLbl","Trigger",x+10,y+183,100,16)
    local resourceBtn=mkWidget("Button",parent,"supportResource",string.upper(resource),x+118,y+178,96,22)
    if resourceBtn then resourceBtn.onClick=function()
        if resource=="always" then resource="hp" elseif resource=="hp" then resource="mana" else resource="always" end
        resourceBtn:setText(string.upper(resource))
    end end
    local spell=mkTextRow(parent,"supportSpell","Spell",x+10,y+204,"",function() end)
    local slot=mkItemSlot(parent,"supportItem","Drop item",x+10,y+232,itemId,function(id) itemId=id end)
    local minValue=mkNumRow(parent,"supportMin","Threshold min %",x+10,y+270,function() return minimum end,function(d) minimum=math.max(1,math.min(maximum,minimum+d)) end)
    local maxValue=mkNumRow(parent,"supportMax","Threshold max %",x+10,y+296,function() return maximum end,function(d) maximum=math.max(minimum,math.min(99,maximum+d)) end)
    local intervalValue=mkNumRow(parent,"supportInterval","Cooldown ms",x+10,y+322,function() return interval end,
        function(d) interval=math.max(1000,math.min(3600000,interval+d*250)) end)
    list.onSelect=function(item)
        UI.loading_selection=true
        if spell and spell.setText then spell:setText(item.words or "") end
        action=item.action or "spell"; resource=item.resource or "always"; itemId=item.item_id or 0
        interval=item.interval_ms or 1000; minimum=item.threshold_min or 60; maximum=item.threshold_max or 70
        if actionBtn then actionBtn:setText(string.upper(action)) end
        if resourceBtn then resourceBtn:setText(string.upper(resource)) end
        if slot and slot.setItemId then slot:setItemId(itemId) end
        if intervalValue then intervalValue:setText(tostring(interval)) end
        if minValue then minValue:setText(tostring(minimum)) end
        if maxValue then maxValue:setText(tostring(maximum)) end
        UI.loading_selection=false
    end
    local plus=mkWidget("Button",parent,"supportPlus","+ RULE",x+10,y+350,140,22)
    local minus=mkWidget("Button",parent,"supportMinus","- RULE",x+164,y+350,140,22)
    if plus then plus.onClick=function()
        local words=spell and spell:getText() or ""
        if (action=="spell" and words~="") or (action=="item" and itemId>0) then
            S.rules[#S.rules+1]={action=action,resource=resource,words=words,item_id=itemId,threshold_min=minimum,threshold_max=maximum,interval_ms=interval}
            list.selected=#S.rules; list.refresh(); markDirty(); scheduleAutosave()
        end
    end end
    if minus then minus.onClick=function() removeSelected(S.rules,list) end end
    local edit=mkWidget("Button",parent,"supportEdit","EDIT",x+10,y+378,92,22)
    local up=mkWidget("Button",parent,"supportUp","UP",x+108,y+378,92,22)
    local down=mkWidget("Button",parent,"supportDown","DOWN",x+206,y+378,98,22)
    if edit then edit.onClick=function()
        local item=list.selected and S.rules[list.selected]; local words=spell and spell:getText() or ""
        if item and ((action=="spell" and words~="") or (action=="item" and itemId>0)) then
            item.action=action; item.resource=resource; item.words=words; item.item_id=itemId
            item.threshold_min=minimum; item.threshold_max=maximum; item.interval_ms=interval
            list.refresh(); markDirty(); scheduleAutosave()
        end
    end end
    if up then up.onClick=function() moveSelected(S.rules,list,-1) end end
    if down then down.onClick=function() moveSelected(S.rules,list,1) end end
end

local function openEditTimer(parent, x, y)
    local T = CFG.timer
    local row = y
    setColor(mkWidget("Label", parent, "etTitle", "TIMER", x + 10, row, EDIT_W - 20, 16), "#f0c56a")
    row = row + 24
    mkCheckRow(parent, "etEn", "Enabled", x + 10, row, function() return T.enabled end, function(v) T.enabled = v end)
    row = row + 24
    mkNumRow(parent, "etInt", "Interval (sec)", x + 10, row,
        function() return math.floor(T.interval_ms / 1000) end,
        function(d) T.interval_ms = math.max(10, T.interval_ms + d * 10000) end)
end

local EDIT_BUILDERS = {
    healing    = openEditHealing,
    combat     = openEditCombat,
    conditions = openEditConditions,
    support    = openEditSupport,
    timer      = openEditTimer,
    combat_exeta = openEditExeta,
}

openEditPanel = function(moduleId)
    if not UI.window then return end
    destroyEditPanel()

    local root = g_ui and g_ui.getRootWidget and g_ui.getRootWidget()
    if not root then return end

    -- Create floating panel near the main window
    local px = (CFG.window_x or 20) + WINDOW_W + 6
    local py = CFG.window_y or 60
    local panelW = EDIT_W + 22
    if root.getWidth then
        local ok,width=pcall(function() return root:getWidth() end)
        if ok and tonumber(width) then px=math.max(4,math.min(px,tonumber(width)-panelW-4)) end
    end
    if root.getHeight then
        local ok,height=pcall(function() return root:getHeight() end)
        if ok and tonumber(height) then py=math.max(4,math.min(py,tonumber(height)-(EDIT_H+50)-4)) end
    end

    local panel = mkWidget("HeadlessWindow", root, "csEditPanel", "", px, py, panelW, EDIT_H + 50)
    if not panel then return end
    setBg(panel, "#262626")
    if panel.setBorderColor then pcall(function() panel:setBorderColor("#b58c42") end) end
    if panel.setBorderWidth then pcall(function() panel:setBorderWidth(1) end) end
    if panel.setDraggable   then panel:setDraggable(true) end

    -- Close button
    local closeBtn = mkWidget("Button", panel, "csEditClose", "[X]", panelW - 30, 4, 22, 20)
    if closeBtn then closeBtn.onClick = function() destroyEditPanel() end end

    -- Module label
    local modLabel = ""
    for _, m in ipairs(MODULES) do if m.id == moduleId then modLabel = m.icon .. " " .. m.label end end
    if moduleId == "combat_exeta" then modLabel = "[C] COMBAT / EXETA" end
    setColor(mkWidget("Label", panel, "csEditModLbl", modLabel, 10, 6, 160, 16), "#ffffff")

    -- Build module-specific content
    local builder = EDIT_BUILDERS[moduleId]
    if builder then
        pcall(function() builder(panel, 4, 30) end)
    end

    UI.edit_panel  = panel
    UI.active_edit = moduleId
    fileLog("edit panel opened module=" .. tostring(moduleId))
end

-- ============================================================
-- MODULE ROW REFRESH
-- ============================================================
local function moduleEnabled(modId)
    local cfg = CFG[modId]
    if type(cfg) == "table" then return cfg.enabled ~= false end
    return false
end

local function refreshModuleRows()
    for index, row in ipairs(UI.module_rows) do
        local modId = row.id
        local enabled = moduleEnabled(modId)
        if row.chk and row.chk.setChecked then
            pcall(function() row.chk:setChecked(enabled) end)
        end
        if row.status_lbl then
            local txt = enabled and "ON " or "OFF"
            row.status_lbl:setText(txt)
            setColor(row.status_lbl, enabled and "#93d987" or "#a0a0a0")
        end
        if row.background then setBg(row.background,index==UI.selected_module and "#453b26" or (index%2==0 and "#2e2e2e" or "#303030")) end
    end
end

local function refreshPresetUi()
    if UI.preset_name and UI.preset_name.setText then pcall(function() UI.preset_name:setText(RT.profile_name or "") end) end
end

local function clampWindowPosition(root,x,y,width,height)
    local rootWidth,rootHeight=1920,1080
    if root and root.getWidth then local ok,value=pcall(function() return root:getWidth() end);if ok and tonumber(value) then rootWidth=tonumber(value) end end
    if root and root.getHeight then local ok,value=pcall(function() return root:getHeight() end);if ok and tonumber(value) then rootHeight=tonumber(value) end end
    return math.max(0,math.min(tonumber(x) or 20,math.max(0,rootWidth-width))),
        math.max(0,math.min(tonumber(y) or 60,math.max(0,rootHeight-height)))
end

-- ============================================================
-- BUILD UI
-- ============================================================
local PARITY_PAGES = {
    {id="healing",label="Healing",icon="[H]"},
    {id="tools",label="Tools",icon="[T]"},
    {id="shooter",label="KVShooter",icon="[S]"},
}
local PARITY_WIDGET_CONTRACT = {
    "csTabhealing","csTabtools","csTabshooter","csSpellSelector",
    "csEnableSio","csManaTrainingItem","csAutoExeta","csEnableShooter",
}

local SPELL_CATALOG = {
    ek = {
        {name="Light Healing",words="exura ico",level=1,kind="healing"},
        {name="Wound Cleansing",words="exura ico",level=8,kind="healing"},
        {name="Intense Wound Cleansing",words="exura gran ico",level=80,kind="healing"},
        {name="Front Sweep",words="exori min",level=35,kind="aggressive"},
        {name="Berserk",words="exori",level=35,kind="aggressive"},
        {name="Fierce Berserk",words="exori gran",level=90,kind="aggressive"},
        {name="Brutal Strike",words="exori ico",level=16,kind="aggressive"},
        {name="Groundshaker",words="exori mas",level=33,kind="aggressive"},
    },
    ms = {
        {name="Light Healing",words="exura",level=8,kind="healing"},
        {name="Intense Healing",words="exura gran",level=20,kind="healing"},
        {name="Ultimate Healing",words="exura vita",level=30,kind="healing"},
        {name="Energy Strike",words="exori vis",level=12,kind="aggressive"},
        {name="Flame Strike",words="exori flam",level=14,kind="aggressive"},
        {name="Energy Wave",words="exevo vis hur",level=38,kind="aggressive"},
        {name="Rage of the Skies",words="exevo gran mas vis",level=55,kind="aggressive"},
        {name="Hell's Core",words="exevo gran mas flam",level=60,kind="aggressive"},
    },
    rp = {
        {name="Divine Healing",words="exura san",level=20,kind="healing"},
        {name="Salvation",words="exura gran san",level=60,kind="healing"},
        {name="Divine Missile",words="exori san",level=40,kind="aggressive"},
        {name="Strong Ethereal Spear",words="exori gran con",level=90,kind="aggressive"},
        {name="Divine Caldera",words="exevo mas san",level=50,kind="aggressive"},
    },
    ed = {
        {name="Light Healing",words="exura",level=8,kind="healing"},
        {name="Intense Healing",words="exura gran",level=20,kind="healing"},
        {name="Ultimate Healing",words="exura vita",level=30,kind="healing"},
        {name="Heal Friend",words="exura sio",level=18,kind="healing"},
        {name="Strong Ice Strike",words="exori gran frigo",level=80,kind="aggressive"},
        {name="Ice Wave",words="exevo frigo hur",level=38,kind="aggressive"},
        {name="Eternal Winter",words="exevo gran mas frigo",level=60,kind="aggressive"},
    },
    -- KingsVale Monk spells are server-specific. Imported IDs are resolved from
    -- the runtime SpellInfo table; the selector also accepts explicit words.
    monk = {},
}

local selectParityPage

local function importParityStyles()
    if not g_ui or type(g_ui.importStyle) ~= "function" then return false end
    local paths = {
        "/mods/ctoa_safe/styles/helper.otui",
        "/mods/ctoa_safe/styles/spell.otui",
        "/mods/ctoa_safe/styles/siolist.otui",
        "/mods/ctoa_safe/styles/shooterPreset.otui",
    }
    local imported = true
    for _, path in ipairs(paths) do
        local ok = pcall(function() g_ui.importStyle(path) end)
        if not ok then imported = false; fileLog("style import fallback: " .. path) end
    end
    return imported
end

local function paritySection(parent,id,text,y)
    local bg=mkWidget("CTOASafeSection",parent,id.."Bg",text,2,y,264,20)
    if not bg then
        bg=mkWidget("Label",parent,id.."Bg",text,2,y,264,20);setBg(bg,"#161616");setColor(bg,"#e3c06b")
    end
    return y+22
end

local function parityCheck(parent,id,label,x,y,getValue,onChange,width)
    local check=mkWidget("CheckBox",parent,id,"",x,y,15,15)
    if check and check.setChecked then pcall(function() check:setChecked(getValue()==true) end) end
    local text=mkWidget("Label",parent,id.."Label",label,x+19,y+1,width or 120,15);setColor(text,"#ededed")
    if check then check.onCheckChange=function(_,checked) onChange(checked==true);markDirty();scheduleAutosave() end end
    return check
end

local function parityPercent(parent,id,x,y,getValue,onChange)
    local minus=mkWidget("Button",parent,id.."Minus","-",x,y,18,20)
    local value=mkWidget("Label",parent,id.."Value",tostring(getValue()).."%",x+20,y+3,38,15);setColor(value,"#f0c56a")
    local plus=mkWidget("Button",parent,id.."Plus","+",x+60,y,18,20)
    local function delta(amount)
        onChange(clamp(getValue()+amount,1,100,getValue()))
        if value and value.setText then value:setText(tostring(getValue()).."%") end
        markDirty();scheduleAutosave()
    end
    if minus then minus.onClick=function() delta(-1) end end
    if plus then plus.onClick=function() delta(1) end end
    return value
end

local function parityItem(parent,id,x,y,getId,onChange)
    local backdrop=mkWidget("Label",parent,id.."Backdrop","",x,y,30,30);setBg(backdrop,"#111111")
    if backdrop and backdrop.setBorderColor then pcall(function() backdrop:setBorderColor("#787878") end) end
    if backdrop and backdrop.setBorderWidth then pcall(function() backdrop:setBorderWidth(1) end) end
    local slot=mkWidget("CTOASafeItem",parent,id,"",x+1,y+1,28,28)
    if not slot then slot=mkWidget("UIItem",parent,id,"",x+1,y+1,28,28) end
    if not slot then slot=mkWidget("Item",parent,id,"",x+1,y+1,28,28) end
    if slot and slot.setItemId then pcall(function() slot:setItemId(tonumber(getId()) or 0) end) end
    if slot then
        configureItemSettingSlot(slot,"Drop item from backpack or actionbar; click if item selector is available")
        slot.onDrop=function(self,draggedWidget)
            local newId=droppedItemId(draggedWidget)
            if newId<=0 then return false end
            onChange(newId);if self.setItemId then pcall(function() self:setItemId(newId) end) end
            markDirty();scheduleAutosave();return true
        end
    end
    return slot
end

local function destroySpellModal()
    if UI.spell_modal and UI.spell_modal.destroy then pcall(function() UI.spell_modal:destroy() end) end
    UI.spell_modal=nil
end

local function openSpellSelector(kind,currentWords,onApply)
    destroySpellModal()
    local parent=UI.root or UI.window;if not parent then return end
    local modal=mkWidget("CTOASafeSpellSelector",parent,"csSpellSelector","",300,70,390,440)
    if not modal then modal=mkWidget("HeadlessWindow",parent,"csSpellSelector","",300,70,390,440) end
    if not modal then return end
    UI.spell_modal=modal;setBg(modal,"#232323")
    if modal.setBorderColor then pcall(function() modal:setBorderColor("#8d7749") end) end
    if modal.setBorderWidth then pcall(function() modal:setBorderWidth(1) end) end
    if modal.setDraggable then pcall(function() modal:setDraggable(true) end) end
    local title=kind=="healing" and "Assign Healing Spell" or "Assign Aggressive Spell"
    local titleBg=mkWidget("Label",modal,"csSpellSelectorTitleBg","",0,0,390,28);setBg(titleBg,"#111111")
    local titleLabel=mkWidget("Label",modal,"csSpellSelectorTitle",title,10,6,330,16);setColor(titleLabel,"#f0c56a")
    local close=mkWidget("Button",modal,"csSpellSelectorClose","X",360,4,24,20);if close then close.onClick=destroySpellModal end

    local selected={words=currentWords or "",name=currentWords or "Custom spell",level=0}
    local selectedLabel=mkWidget("Label",modal,"csSpellSelected",selected.name.."  ["..selected.words.."]",10,36,368,18);setColor(selectedLabel,"#ffffff")
    local search=mkWidget("TextEdit",modal,"csSpellSearch","",10,62,368,24)
    if search and search.setPlaceholderText then pcall(function() search:setPlaceholderText("Type to search") end) end
    local listPanel=mkWidget("Panel",modal,"csSpellList",10,92,368,268);setBg(listPanel,"#191919")
    local rowWidgets={}
    local catalog=SPELL_CATALOG[RT.vocation] or SPELL_CATALOG.ek
    local function rebuild(query)
        for _,widget in ipairs(rowWidgets) do if widget and widget.destroy then pcall(function() widget:destroy() end) end end
        rowWidgets={};query=tostring(query or ""):lower();local row=0
        for _,spell in ipairs(catalog) do
            if spell.kind==kind and (query=="" or spell.name:lower():find(query,1,true) or spell.words:lower():find(query,1,true)) then
                local y=row*31
                local button=mkWidget("Button",modal,"csSpellRow"..tostring(row+1),spell.name.."   "..spell.words.."   Lv."..tostring(spell.level),12,93+y,364,29)
                rowWidgets[#rowWidgets+1]=button
                if button then
                    local candidate=spell
                    button.onClick=function()
                        selected={words=candidate.words,name=candidate.name,level=candidate.level}
                        selectedLabel:setText(selected.name.."  ["..selected.words.."]")
                    end
                end
                row=row+1
            end
        end
    end
    if search then search.onTextChange=function(_,text) rebuild(text) end end
    rebuild("")
    parityCheck(modal,"csSpellLearntOnly","Only show learnt spells",10,369,function() return true end,function() end,180)
    mkWidget("Label",modal,"csSpellParameterLabel","Spell words",205,369,68,16)
    local parameter=mkWidget("TextEdit",modal,"csSpellParameter",currentWords or "",275,366,103,22)
    if parameter and parameter.setPlaceholderText then pcall(function() parameter:setPlaceholderText("custom words") end) end
    local function applyCustomWords()
        if parameter and parameter.getText then
            local words=cleanString(parameter:getText(),"",64)
            if words~="" then selected={words=words,name="Custom spell",level=0} end
        end
    end
    local okButton=mkWidget("Button",modal,"csSpellOk","OK",120,407,72,24)
    local applyButton=mkWidget("Button",modal,"csSpellApply","Apply",198,407,72,24)
    local cancelButton=mkWidget("Button",modal,"csSpellCancel","Cancel",276,407,72,24)
    if applyButton then applyButton.onClick=function() applyCustomWords();onApply(selected);markDirty();scheduleAutosave() end end
    if okButton then okButton.onClick=function() applyCustomWords();onApply(selected);markDirty();scheduleAutosave();destroySpellModal() end end
    if cancelButton then cancelButton.onClick=destroySpellModal end
end

local function buildHealingPage(parent)
    local H=CFG.healing
    local layout=vocationUiContract(RT.vocation)
    local title=mkWidget("Label",parent,"csHealingTitle","Auto Healing Helper",6,4,250,18);setColor(title,"#ffffff")
    local y=paritySection(parent,"csSpellHealing","Spell Healing",26)
    for index=1,layout.spell_slots do
        local slot=H.spell_slots[index]
        parityCheck(parent,"csHealSpellEnabled"..index,"",5,y+3,function() return slot.enabled end,function(value) slot.enabled=value end,1)
        local words=slot.words~="" and slot.words or "Select spell"
        local select=mkWidget("Button",parent,"csHealSpell"..index,words,25,y,145,22)
        if select then select.onClick=function() openSpellSelector("healing",slot.words,function(spell)
            slot.words=spell.words;slot.enabled=true
            local rule=H.rules[index] or {kind="heal",cooldown_ms=950};rule.words=spell.words;rule.threshold=slot.percent;H.rules[index]=rule
            selectParityPage("healing")
        end) end end
        parityPercent(parent,"csHealSpellPercent"..index,177,y,function() return slot.percent end,function(value)
            slot.percent=value;if H.rules[index] then H.rules[index].threshold=value end
        end)
        y=y+27
    end

    y=paritySection(parent,"csPotionHealing","Potion Healing",y+1)
    for index=1,layout.potion_slots do
        local rule=H.potion_rules[index]
        parityCheck(parent,"csPotionEnabled"..index,"",5,y+7,function() return rule.enabled end,function(value)
            rule.enabled=value;H.potion_enabled=false;H.mana_potion_enabled=false
        end,1)
        parityItem(parent,"csPotionItem"..index,25,y,function() return rule.item_id end,function(value) rule.item_id=value end)
        local label=mkWidget("Label",parent,"csPotionLabel"..index,(rule.resource=="mana" and "Mana" or "Health").." potion "..index,61,y+7,105,16);setColor(label,"#ededed")
        parityPercent(parent,"csPotionPercent"..index,177,y+5,function() return rule.threshold end,function(value) rule.threshold=value end)
        y=y+34
    end

    if layout.friend_healing then
        y=paritySection(parent,"csFriendHealing","Friend Healing Helper",y+1)
        for index=1,4 do
            local rule=H.friend_rules[index]
            parityCheck(parent,"csSioEnabled"..index,"",5,y+3,function() return rule.enabled end,function(value) rule.enabled=value end,1)
            local label=index<=2 and "Sio" or "Gran Sio"
            local name=mkWidget("TextEdit",parent,"csSioName"..index,rule.name or "",25,y,112,22)
            if name and name.setPlaceholderText then pcall(function() name:setPlaceholderText(label.." friend") end) end
            if name then name.onTextChange=function(_,text) rule.name=cleanString(text,"",64);markDirty();scheduleAutosave() end end
            parityPercent(parent,"csSioPercent"..index,145,y+1,function() return rule.threshold end,function(value) rule.threshold=value end)
            y=y+26
        end
        parityCheck(parent,"csEnableSio","Enable Sio",7,y+2,function() return H.friend_enabled end,function(value) H.friend_enabled=value end,110)
    end
end

local function buildToolsPage(parent)
    local T=CFG.tools
    local layout=vocationUiContract(RT.vocation)
    local title=mkWidget("Label",parent,"csToolsTitle","Tools Helper",6,4,250,18);setColor(title,"#ffffff")
    local y=paritySection(parent,"csManaTraining","Mana Training",26)
    parityItem(parent,"csManaTrainingItem",7,y,function() return T.mana_training_item_id end,function(value) T.mana_training_item_id=value end)
    parityCheck(parent,"csManaTrainingEnable","Enable",44,y+7,function() return T.mana_training end,function(value) T.mana_training=value end,60)
    parityPercent(parent,"csManaTrainingPercent",177,y+5,function() return T.mana_training_threshold end,function(value) T.mana_training_threshold=value end)
    y=paritySection(parent,"csAutoHaste","Auto Haste",y+35)
    parityCheck(parent,"csAutoHasteEnable","Enable",7,y+2,function() return T.auto_haste end,function(value) T.auto_haste=value end,70)
    parityCheck(parent,"csPzCast","PZ Cast",105,y+2,function() return T.pz_cast end,function(value) T.pz_cast=value end,70)
    local haste=mkWidget("Button",parent,"csHasteSpell",T.haste_spell,184,y,77,21)
    if haste then haste.onClick=function() openSpellSelector("aggressive",T.haste_spell,function(spell) T.haste_spell=spell.words;selectParityPage("tools") end) end end
    y=paritySection(parent,"csExerciseTraining","Exercise Training",y+27)
    parityItem(parent,"csExerciseItem",7,y,function() return T.exercise_item_id end,function(value) T.exercise_item_id=value end)
    parityCheck(parent,"csExerciseEnable","Enable",44,y+7,function() return T.exercise_training end,function(value) T.exercise_training=value end,80)
    y=paritySection(parent,"csOtherTools","Others Tools",y+35)
    parityCheck(parent,"csChangeGold","Change Gold",7,y+2,function() return T.change_gold end,function(value) T.change_gold=value end,76)
    parityCheck(parent,"csAutoEatFood","Auto Eat Food",98,y+2,function() return T.auto_eat_food end,function(value) T.auto_eat_food=value end,82)
    if layout.auto_exeta then
        parityCheck(parent,"csAutoExeta","Auto Exeta",194,y+2,function() return CFG.combat.auto_exeta end,function(value) CFG.combat.auto_exeta=value end,66)
    end

    local function equipmentSection(id,title,config,startY)
        local rowY=paritySection(parent,id,title,startY)
        for index=1,2 do
            local rule=config[index]
            parityCheck(parent,id.."Enabled"..index,"",5,rowY+7,function() return rule.enabled end,function(value) rule.enabled=value end,1)
            parityItem(parent,id.."Item"..index,25,rowY,function() return rule.id end,function(value) rule.id=value end)
            local hp=mkWidget("Button",parent,id.."Resource"..index,rule.mana and "MP" or "HP",61,rowY+5,36,21)
            if hp then hp.onClick=function() rule.mana=not rule.mana;rule.health=not rule.mana;hp:setText(rule.mana and "MP" or "HP");markDirty();scheduleAutosave() end end
            parityPercent(parent,id.."Percent"..index,177,rowY+5,function() return rule.percent end,function(value) rule.percent=value end)
            rowY=rowY+34
        end
        return rowY
    end
    y=equipmentSection("csEquipAmulet","Equip Amulet",T.amulet_config,y+27)
    y=equipmentSection("csEquipRing","Equip Ring",T.ring_config,y+1)
    y=paritySection(parent,"csAdditionalTools","Defense / Client",y+1)
    parityCheck(parent,"csBuffEnable","Buff",5,y+2,function() return T.buff[1].enabled end,function(value) T.buff[1].enabled=value end,45)
    parityCheck(parent,"csAutoReconnect","Reconnect",65,y+2,function() return T.auto_reconnect end,function(value) T.auto_reconnect=value end,82)
    local buffWords=T.buff[1].words~="" and T.buff[1].words or "Select buff spell"
    local buffSpell=mkWidget("Button",parent,"csBuffSpell",buffWords,7,y+21,116,25)
    if buffSpell then buffSpell.onClick=function() openSpellSelector("support",T.buff[1].words,function(spell)
        T.buff[1].words=spell.words;T.buff[1].enabled=true;selectParityPage("tools")
    end) end end
    parityItem(parent,"csAmmoOneItem",139,y+19,function() return T.ammo_config[1].id end,function(value) T.ammo_config[1].id=value end)
    parityItem(parent,"csAmmoTwoItem",175,y+19,function() return T.ammo_config[2].id end,function(value) T.ammo_config[2].id=value end)
    parityCheck(parent,"csAmmoOneEnable","1",211,y+20,function() return T.ammo_config[1].enabled end,function(value) T.ammo_config[1].enabled=value end,18)
    parityCheck(parent,"csAmmoTwoEnable","2",239,y+20,function() return T.ammo_config[2].enabled end,function(value) T.ammo_config[2].enabled=value end,18)
end

local function buildShooterPage(parent)
    local C=CFG.combat
    local title=mkWidget("Label",parent,"csShooterTitle","KVShooter",6,4,250,18);setColor(title,"#ffffff")
    local y=paritySection(parent,"csShooterPresets","Presets",26)
    local profile=C.shooter_profiles[C.selected_shooter_profile] or C.shooter_profiles.Default
    local profileName=mkWidget("TextEdit",parent,"csShooterPresetName",C.selected_shooter_profile,6,y,118,22)
    local rename=mkWidget("Button",parent,"csShooterRename","Rename Preset",128,y,92,22)
    local remove=mkWidget("Button",parent,"csShooterDelete","X",224,y,18,22)
    local add=mkWidget("Button",parent,"csShooterNew","+",244,y,18,22)
    if rename then rename.onClick=function()
        local newName=cleanString(profileName and profileName.getText and profileName:getText() or "","",48)
        if newName~="" and not C.shooter_profiles[newName] then C.shooter_profiles[newName]=profile;C.shooter_profiles[C.selected_shooter_profile]=nil;C.selected_shooter_profile=newName;markDirty();scheduleAutosave();selectParityPage("shooter") end
    end end
    if remove then remove.onClick=function()
        local count=0;for _ in pairs(C.shooter_profiles) do count=count+1 end
        if count>1 then C.shooter_profiles[C.selected_shooter_profile]=nil;for name in pairs(C.shooter_profiles) do C.selected_shooter_profile=name;break end;markDirty();scheduleAutosave();selectParityPage("shooter") end
    end end
    if add then add.onClick=function()
        local base="New Preset";local name=base;local index=2;while C.shooter_profiles[name] do name=base.." "..tostring(index);index=index+1 end
        C.shooter_profiles[name]=deepCopy(DEFAULTS.combat.shooter_profiles.Default);C.selected_shooter_profile=name;markDirty();scheduleAutosave();selectParityPage("shooter")
    end end

    y=paritySection(parent,"csSpellShooter","Spell Shooter Helper",y+27)
    mkWidget("Label",parent,"csShooterColumns","Spell                 Mana %   Creatures   Priority",6,y,254,15)
    y=y+17
    for index=1,6 do
        local spell=profile.spells[index]
        local text=spell.words~="" and spell.words or ((spell.id or 0)>0 and ("Spell #"..tostring(spell.id)) or "Select spell")
        local choose=mkWidget("Button",parent,"csShooterSpell"..index,text,6,y,112,23)
        if choose then choose.onClick=function() openSpellSelector("aggressive",spell.words,function(selected)
            spell.words=selected.words;spell.id=0;selectParityPage("shooter")
        end) end end
        local mana=mkWidget("Button",parent,"csShooterMana"..index,tostring(spell.percent).."%",121,y,42,23)
        if mana then mana.onClick=function() spell.percent=spell.percent>=100 and 10 or spell.percent+10;mana:setText(tostring(spell.percent).."%");markDirty();scheduleAutosave() end end
        local creatures=mkWidget("Button",parent,"csShooterCreatures"..index,tostring(spell.creatures).."+",166,y,42,23)
        if creatures then creatures.onClick=function() spell.creatures=spell.creatures>=10 and 1 or spell.creatures+1;creatures:setText(tostring(spell.creatures).."+");markDirty();scheduleAutosave() end end
        local priority=mkWidget("Button",parent,"csShooterPriority"..index,tostring(spell.priority).."st",211,y,51,23)
        if priority then priority.onClick=function() spell.priority=spell.priority>=6 and 1 or spell.priority+1;priority:setText(tostring(spell.priority).."st");markDirty();scheduleAutosave() end end
        y=y+27
    end

    y=paritySection(parent,"csShooterRunes","Rune Shooter",y+1)
    for index=1,2 do
        local rune=profile.runes[index]
        parityItem(parent,"csShooterRune"..index,7,y,function() return rune.id end,function(value) rune.id=value end)
        mkWidget("Label",parent,"csShooterRuneLabel"..index,"Rune "..index,43,y+7,52,16)
        local creatures=mkWidget("Button",parent,"csShooterRuneCreatures"..index,tostring(rune.creatures).."+",112,y+5,44,21)
        if creatures then creatures.onClick=function() rune.creatures=rune.creatures>=10 and 1 or rune.creatures+1;creatures:setText(tostring(rune.creatures).."+");markDirty();scheduleAutosave() end end
        local priority=mkWidget("Button",parent,"csShooterRunePriority"..index,"P"..tostring(rune.priority),163,y+5,44,21)
        if priority then priority.onClick=function() rune.priority=rune.priority>=8 and 1 or rune.priority+1;priority:setText("P"..tostring(rune.priority));markDirty();scheduleAutosave() end end
        parityCheck(parent,"csShooterRuneForce"..index,"Force",212,y+7,function() return rune.force_cast end,function(value) rune.force_cast=value end,48)
        y=y+34
    end
    parityCheck(parent,"csAutoTarget","Auto Target",7,y+2,function() return C.auto_attack end,function(value) C.auto_attack=value end,100)
    parityCheck(parent,"csEnableShooter","Enable Shooter Helper",127,y+2,function() return C.spell_rotation end,function(value) C.spell_rotation=value end,130)
    parityCheck(parent,"csShooterOnHold","On Hold",7,y+27,function() return C.magic_shooter_on_hold end,function(value) C.magic_shooter_on_hold=value end,70)
    local setKeys=mkWidget("Button",parent,"csShooterSetKeys","Set Key (Target/Shooter)",94,y+23,168,24)
    if setKeys then setKeys.onClick=function()
        if C.auto_target_hotkey==C.auto_shooter_hotkey then C.auto_target_hotkey="F10";C.auto_shooter_hotkey="F11" else C.auto_target_hotkey="F11";C.auto_shooter_hotkey="F11" end
        setStatus("Target "..C.auto_target_hotkey.." | Shooter "..C.auto_shooter_hotkey.." | Both "..C.auto_target_both.." (reload to bind)")
        markDirty();scheduleAutosave()
    end end
end

selectParityPage = function(pageId)
    if UI.page_panel and UI.page_panel.destroy then pcall(function() UI.page_panel:destroy() end) end
    UI.page_panel=nil;UI.active_page=pageId
    if not UI.window then return end
    local panel=mkWidget("CTOASafePage",UI.window,"csPage"..pageId,"",2,66,268,490)
    if not panel then panel=mkWidget("Panel",UI.window,"csPage"..pageId,"",2,66,268,490);setBg(panel,"#292929") end
    UI.page_panel=panel
    for _, page in ipairs(PARITY_PAGES) do
        local button=UI.tab_buttons[page.id]
        if button then setBg(button,page.id==pageId and "#514426" or "#1b1b1b") end
    end
    if pageId=="tools" then buildToolsPage(panel)
    elseif pageId=="shooter" then buildShooterPage(panel)
    else buildHealingPage(panel) end
end

local function buildLegacyUI()
    fileLog("buildUI: start")

    -- Get root widget — try multiple methods used by different OTC forks
    local root = nil
    if not root and g_ui and g_ui.getRootWidget then
        local ok, r = pcall(function() return g_ui.getRootWidget() end)
        if ok and r then root = r end
    end
    if not root and rawget(_G, "modules") and modules.game_interface then
        local gi = modules.game_interface
        if gi.getRootWidget then
            local ok, r = pcall(function() return gi.getRootWidget() end)
            if ok and r then root = r end
        end
        if not root and gi.getMapWidget then
            local ok, r = pcall(function() return gi.getMapWidget() end)
            if ok and r and r.getParent then root = r:getParent() end
        end
    end
    if not root then
        fileLog("buildUI: root widget unavailable, aborting")
        return
    end
    fileLog("buildUI: root ok, type=" .. type(root))

    -- ---- Window ----
    local numModules = #MODULES
    local WIN_H = 28 + numModules * ROW_H + 34 + 4 + 32 + 22 + 24
    local winX,winY = clampWindowPosition(root,CFG.window_x or 500,CFG.window_y or 80,WINDOW_W,WIN_H)
    CFG.window_x,CFG.window_y=winX,winY

    local win = mkWidget("HeadlessWindow", root, "ctoaSafeWindow", "",
        winX, winY, WINDOW_W, WIN_H)
    if not win then fileLog("buildUI: ERROR window nil"); return end
    fileLog("buildUI: window created ok")
    setBg(win, "#262626")
    if win.setBorderColor then pcall(function() win:setBorderColor("#737373") end) end
    if win.setBorderWidth then pcall(function() win:setBorderWidth(1) end) end
    if win.setDraggable   then pcall(function() win:setDraggable(true) end) end
    if win.setMovable     then pcall(function() win:setMovable(true) end) end
    -- Show immediately so it's definitely visible
    if win.show  then pcall(function() win:show() end) end
    if win.raise then pcall(function() win:raise() end) end
    UI.window = win

    -- Remember position on move
    win.onPositionChange = function(w, newPos)
        if newPos then CFG.window_x = newPos.x; CFG.window_y = newPos.y;markDirty();scheduleAutosave() end
    end

    -- ---- Title bar ----
    local titleBg = mkWidget("Label", win, "csTitle", "", 0, 0, WINDOW_W, 26)
    setBg(titleBg, "#101010")

    UI.title_label = mkWidget("Label", win, "csTitleText",
        "CTOA Safe " .. SAFE_VERSION, 8, 5, WINDOW_W - 60, 16)
    setColor(UI.title_label, "#f0c56a")
    setFontScale(UI.title_label, 1.0)

    local closeBtn = mkWidget("Button", win, "csCloseBtn", "[X]", WINDOW_W - 24, 3, 20, 20)
    if closeBtn then closeBtn.onClick = function()
        if win.hide then win:hide() end
    end end

    -- Divider under title
    local sep1 = mkWidget("Label", win, "csSep1", "", 0, 26, WINDOW_W, 1)
    setBg(sep1, "#707070")

    -- ---- Module rows ----
    UI.module_rows = {}
    local rowY = 28
    for i, mod in ipairs(MODULES) do
        local cfg = CFG[mod.id] or {}
        local enabled = cfg.enabled ~= false

        -- Row background (alternate)
        local rowBg = mkWidget("Label", win, "csRow" .. i, "", 0, rowY, WINDOW_W, ROW_H - 1)
        setBg(rowBg, i % 2 == 0 and "#2e2e2e" or "#303030")

        -- Toggle checkbox
        local chk = mkWidget("CheckBox", win, "csMod" .. mod.id .. "Chk", "", 6, rowY + 5, 14, 14)
        if chk and chk.setChecked then pcall(function() chk:setChecked(enabled) end) end
        local modRef = mod -- closure capture
        if chk then chk.onCheckChange = function(w, checked)
            if type(CFG[modRef.id]) == "table" then
                CFG[modRef.id].enabled = checked
            end
            markDirty(); scheduleAutosave()
            refreshModuleRows()
        end end

        -- Icon + Label
        local iconLbl = mkWidget("Label", win, "csModIcon" .. i, mod.icon, 24, rowY + 5, 16, 14)
        setColor(iconLbl, "#eeeeee")

        local nameLbl = mkWidget("Label", win, "csModName" .. i, mod.label, 42, rowY + 5, 128, 14)
        setColor(nameLbl, "#ffffff")
        setFontScale(nameLbl, 1.0)

        -- Status text (ON/OFF)
        local statusTxt = enabled and "ON " or "OFF"
        local statusLbl = mkWidget("Label", win, "csModStat" .. i, statusTxt, 174, rowY + 5, 30, 14)
        setColor(statusLbl, enabled and "#93d987" or "#a0a0a0")
        setFontScale(statusLbl, 0.82)

        -- Edit button
        local editBtn = mkWidget("Button", win, "csEdit" .. mod.id, "edit", 210, rowY + 3, 46, 20)
        if editBtn then
            local midCopy = mod.id
            local indexCopy = i
            editBtn.onClick = function()
                UI.selected_module=indexCopy;refreshModuleRows()
                if UI.active_edit == midCopy then
                    destroyEditPanel()
                else
                    openEditPanel(midCopy)
                end
            end
        end

        -- Separator line
        local rowSep = mkWidget("Label", win, "csRowSep" .. i, "", 0, rowY + ROW_H - 1, WINDOW_W, 1)
        setBg(rowSep, "#383838")

        table.insert(UI.module_rows, {id = mod.id, chk = chk, status_lbl = statusLbl,background=rowBg,edit=editBtn})
        rowY = rowY + ROW_H
    end

    local presetY=rowY+2
    mkWidget("Label",win,"csPresetLbl","Preset",8,presetY+5,42,18)
    UI.preset_name=mkWidget("TextEdit",win,"csPresetName",RT.profile_name,50,presetY+2,112,22)
    if UI.preset_name then UI.preset_name.onTextChange=function(widget,text)
        if UI.loading_selection then return end
        RT.profile_name=cleanString(text,RT.profile_name,64);markDirty();scheduleAutosave()
    end end
    local prev=mkWidget("Button",win,"csPresetPrev","<",166,presetY+2,26,22)
    local next=mkWidget("Button",win,"csPresetNext",">",194,presetY+2,26,22)
    local add=mkWidget("Button",win,"csPresetAdd","+",222,presetY+2,26,22)
    local imp=mkWidget("Button",win,"csPresetImport","IMP",250,presetY+2,38,22)
    local exp=mkWidget("Button",win,"csPresetExport","EXP",290,presetY+2,42,22)
    local function cyclePreset(delta)
        local _,index=findPreset(RT.active_preset);if not index then return end
        local target=((index-1+delta)%#RT.presets)+1
        if selectPreset(RT.presets[target].id) then refreshPresetUi();refreshModuleRows();setStatus("Preset: "..RT.profile_name) end
    end
    if prev then prev.onClick=function() cyclePreset(-1) end end
    if next then next.onClick=function() cyclePreset(1) end end
    if add then add.onClick=function() local ok=createPreset("Preset "..tostring(#RT.presets+1));if ok then refreshPresetUi();setStatus("Preset created: "..RT.profile_name) end end end
    if imp then imp.onClick=function() local ok=importPreset();if ok then refreshPresetUi();refreshModuleRows();setStatus("Preset imported: "..RT.profile_name) else setStatus("Import rejected or file missing") end end end
    if exp then exp.onClick=function() local ok,path=exportPreset();setStatus(ok and ("Preset exported: "..tostring(path)) or "Preset export failed") end end

    -- ---- Enable / Disable button ----
    local sepY = presetY + 28
    local sep2 = mkWidget("Label", win, "csSep2", "", 0, sepY, WINDOW_W, 1)
    setBg(sep2, "#707070")

    local btnY = sepY + 4
    UI.enable_btn = mkWidget("Button", win, "csEnableBtn",
        CFG.enabled and "[ DISABLE ]" or "[ ENABLE ]",
        8, btnY, WINDOW_W - 16, 28)
    if UI.enable_btn then
        setBg(UI.enable_btn, CFG.enabled and "#3a1818" or "#1a3020")
        UI.enable_btn.onClick = function()
            if CFG.enabled then
                CFG.enabled = false
                RT.armed     = false
                UI.enable_btn:setText("[ ENABLE ]")
                setBg(UI.enable_btn, "#1a3020")
                setStatus("Disabled")
            else
                if not safeProjectActive() then
                    CFG.enabled = false
                    RT.armed = false
                    setStatus("Arm blocked: CTOA Safe is not the selected project")
                    updateTitle()
                    return
                end
                CFG.enabled = true
                RT.armed     = true
                UI.enable_btn:setText("[ DISABLE ]")
                setBg(UI.enable_btn, "#3a1818")
                setStatus("Armed and running")
            end
            markDirty(); scheduleAutosave()
            updateTitle()
        end
    end

    -- ---- Status bar ----
    local statusY = btnY + 32
    UI.status_label = mkWidget("Label", win, "csStatus", "Initializing...", 8, statusY, WINDOW_W - 16, 16)
    setColor(UI.status_label, "#eeeeee")
    setFontScale(UI.status_label, 0.95)

    -- ---- Footer ----
    local footerY = statusY + 18
    local footer = mkWidget("Label", win, "csFooter", "", 0, footerY, WINDOW_W, 20)
    setBg(footer, "#101010")
    local verLbl = mkWidget("Label", win, "csFooterVer", "CTOA Safe " .. SAFE_VERSION, 8, footerY + 3, 140, 14)
    setColor(verLbl, "#737373")
    setFontScale(verLbl, 0.9)

    updateTitle()
    refreshModuleRows()
end

local function buildUI()
    fileLog("buildUI: KingsVale parity surface start")
    local root=nil
    if g_ui and type(g_ui.getRootWidget)=="function" then local ok,value=pcall(function() return g_ui.getRootWidget() end);if ok then root=value end end
    if not root and rawget(_G,"modules") and modules.game_interface then
        if type(modules.game_interface.getRootWidget)=="function" then local ok,value=pcall(function() return modules.game_interface.getRootWidget() end);if ok then root=value end end
        if not root and type(modules.game_interface.getMapWidget)=="function" then
            local ok,map=pcall(function() return modules.game_interface.getMapWidget() end)
            if ok and map and map.getParent then root=map:getParent() end
        end
    end
    if not root then fileLog("buildUI: root widget unavailable");return end
    UI.root=root;importParityStyles()
    local winX,winY=clampWindowPosition(root,CFG.window_x or 20,CFG.window_y or 60,WINDOW_W,WINDOW_H)
    CFG.window_x,CFG.window_y=winX,winY
    local win=mkWidget("CTOASafeWindow",root,"ctoaSafeWindow","",winX,winY,WINDOW_W,WINDOW_H)
    if not win then win=mkWidget("HeadlessWindow",root,"ctoaSafeWindow","",winX,winY,WINDOW_W,WINDOW_H) end
    if not win then fileLog("buildUI: parity window unavailable");return end
    UI.window=win;setBg(win,"#242424")
    if win.setBorderColor then pcall(function() win:setBorderColor("#7f6b41") end) end
    if win.setBorderWidth then pcall(function() win:setBorderWidth(1) end) end
    if win.setDraggable then pcall(function() win:setDraggable(true) end) end
    if win.setMovable then pcall(function() win:setMovable(true) end) end
    win.onPositionChange=function(_,position) if position then CFG.window_x=position.x;CFG.window_y=position.y;markDirty();scheduleAutosave() end end

    local header=mkWidget("Label",win,"csParityHeader","",0,0,WINDOW_W,30);setBg(header,"#0f0f0f")
    UI.title_label=mkWidget("Label",win,"csTitleText","CTOA Safe "..SAFE_VERSION,8,7,214,16);setColor(UI.title_label,"#f0c56a")
    local closeTop=mkWidget("Button",win,"csCloseBtn","X",244,4,23,22)
    if closeTop then closeTop.onClick=function() if win.hide then win:hide() end end end

    UI.tab_buttons={}
    for index,page in ipairs(PARITY_PAGES) do
        local x=(index-1)*90+2
        local tab=mkWidget("CTOASafeTab",win,"csTab"..page.id,page.icon.." "..page.label,x,33,index==3 and 88 or 86,29)
        if not tab then tab=mkWidget("Button",win,"csTab"..page.id,page.icon.." "..page.label,x,33,index==3 and 88 or 86,29) end
        UI.tab_buttons[page.id]=tab;setBg(tab,"#1b1b1b")
        if tab then local pageCopy=page.id;tab.onClick=function() selectParityPage(pageCopy) end end
    end

    local footer=mkWidget("Label",win,"csParityFooter","",0,558,WINDOW_W,80);setBg(footer,"#111111")
    UI.status_label=mkWidget("Label",win,"csStatus","Helper Status: Disabled",8,565,252,17);setColor(UI.status_label,"#a9a9a9")
    UI.enable_btn=mkWidget("Button",win,"csEnableBtn","Enable Helper",8,588,126,26)
    local setKey=mkWidget("Button",win,"csSetKey","Set Key ("..tostring(CFG.hotkey)..")",138,588,91,26)
    local close=mkWidget("Button",win,"csFooterClose","Close",233,588,34,26)
    if close then close.onClick=function() if win.hide then win:hide() end end end
    if setKey then setKey.onClick=function()
        CFG.hotkey=CFG.hotkey=="F9" and "Ctrl+B" or "F9"
        setKey:setText("Set Key ("..CFG.hotkey..")");setStatus("Hotkey selected: "..CFG.hotkey.." (reload to bind)");markDirty();scheduleAutosave()
    end end
    if UI.enable_btn then
        UI.enable_btn.onClick=function()
            if CFG.enabled and RT.armed then
                CFG.enabled=false;RT.armed=false;UI.enable_btn:setText("Enable Helper");setBg(UI.enable_btn,"#292929")
                setStatus("Helper Status: Disabled");setColor(UI.status_label,"#a9a9a9")
            else
                if not safeProjectActive() then CFG.enabled=false;RT.armed=false;setStatus("Arm blocked: Safe project not selected");return end
                CFG.enabled=true;RT.armed=true;UI.enable_btn:setText("Disable Helper");setBg(UI.enable_btn,"#24442b")
                setStatus("Helper Status: Enabled  [OK]");setColor(UI.status_label,"#83dc8a")
            end
            markDirty();scheduleAutosave();updateTitle()
        end
    end
    local version=mkWidget("Label",win,"csFooterVer","Safe local runtime | "..SAFE_VERSION,8,619,250,14);setColor(version,"#6f6f6f")
    selectParityPage(UI.active_page or "healing")
    updateTitle()
    if win.show then pcall(function() win:show() end) end
    if win.raise then pcall(function() win:raise() end) end
    fileLog("buildUI: KingsVale parity surface ready")
end

-- ============================================================
-- HOTKEY BINDING
-- ============================================================
local function bindHotkey()
    if not CFG.hotkey or CFG.hotkey == "" then return end
    if g_keyboard and g_keyboard.bindKeyDown then
        local function bind(key,callback)
            local ok=pcall(function() g_keyboard.bindKeyDown(key,callback) end)
            if ok then UI.bound_keys[#UI.bound_keys+1]=key end
        end
        bind(CFG.hotkey, function()
                if UI.window then
                    if UI.window.isVisible and UI.window:isVisible() then
                        UI.window:hide()
                    elseif UI.window.show then
                        UI.window:show(); UI.window:raise()
                    end
                end
            end)
        bind("Ctrl+Tab",function()
            if not safeProjectActive() or not UI.window then return end
            local index=1;for i,page in ipairs(PARITY_PAGES) do if page.id==UI.active_page then index=i;break end end
            selectParityPage(PARITY_PAGES[(index%#PARITY_PAGES)+1].id)
        end)
        bind("Ctrl+Shift+Tab",function()
            if not safeProjectActive() or not UI.window then return end
            local index=1;for i,page in ipairs(PARITY_PAGES) do if page.id==UI.active_page then index=i;break end end
            selectParityPage(PARITY_PAGES[((index-2)%#PARITY_PAGES)+1].id)
        end)
        bind("Ctrl+E",function()
            if not safeProjectActive() then return end
            local module=MODULES[UI.selected_module];if module then openEditPanel(module.id) end
        end)
        bind("Ctrl+Space",function()
            if not safeProjectActive() then return end
            local moduleId=UI.active_page=="shooter" and "combat" or UI.active_page
            local cfg=CFG[moduleId]
            if cfg then cfg.enabled=not cfg.enabled;markDirty();scheduleAutosave();selectParityPage(UI.active_page) end
        end)
        local C=CFG.combat
        local function refreshShooterHotkeyStatus(label)
            markDirty();scheduleAutosave();setStatus(label);if UI.active_page=="shooter" then selectParityPage("shooter") end
        end
        local function toggleTarget() C.auto_attack=not C.auto_attack;refreshShooterHotkeyStatus("Auto Target: "..(C.auto_attack and "Enabled" or "Disabled")) end
        local function toggleShooter() C.spell_rotation=not C.spell_rotation;refreshShooterHotkeyStatus("Shooter: "..(C.spell_rotation and "Enabled" or "Disabled")) end
        local function toggleBoth()
            local enabled=not (C.auto_attack and C.spell_rotation);C.auto_attack=enabled;C.spell_rotation=enabled
            refreshShooterHotkeyStatus("Target/Shooter: "..(enabled and "Enabled" or "Disabled"))
        end
        if C.magic_shooter_on_hold then
            bind(C.auto_shooter_hotkey,function() RT.shooter_hold=true end)
            if g_keyboard.bindKeyUp then
                local ok=pcall(function() g_keyboard.bindKeyUp(C.auto_shooter_hotkey,function() RT.shooter_hold=false end) end)
                if ok then UI.bound_up_keys[#UI.bound_up_keys+1]=C.auto_shooter_hotkey end
            end
            if C.auto_target_hotkey~=C.auto_shooter_hotkey then bind(C.auto_target_hotkey,toggleTarget) end
        elseif C.auto_target_hotkey==C.auto_shooter_hotkey then
            bind(C.auto_target_hotkey,toggleBoth)
        else
            bind(C.auto_target_hotkey,toggleTarget);bind(C.auto_shooter_hotkey,toggleShooter)
        end
        if C.auto_target_both~=C.auto_target_hotkey and C.auto_target_both~=C.auto_shooter_hotkey then bind(C.auto_target_both,toggleBoth) end
    end
end

local function unbindHotkeys()
    if g_keyboard and g_keyboard.unbindKeyDown then
        for _,key in ipairs(UI.bound_keys) do pcall(function() g_keyboard.unbindKeyDown(key) end) end
    end
    if g_keyboard and g_keyboard.unbindKeyUp then
        for _,key in ipairs(UI.bound_up_keys) do pcall(function() g_keyboard.unbindKeyUp(key) end) end
    end
    UI.bound_keys={}
    UI.bound_up_keys={}
    RT.shooter_hold=false
end

-- ============================================================
-- RUNTIME: HEALING
-- ============================================================
local function runHealing()
    local H = CFG.healing
    if not H.enabled then return end
    local now = nowMs()
    local hp  = getHpPercent()
    local mp  = getMpPercent()

    if H.spell_enabled then
        for _,slot in ipairs(H.spell_slots or {}) do
            local cooldown=slot.cooldown_ms or H.cooldown_ms or 950
            slot._trigger_threshold = slot._trigger_threshold or randomizedThreshold(slot.percent or 80,H.hp_randomization)
            if slot.enabled and type(slot.words)=="string" and slot.words~=""
                and hp<=slot._trigger_threshold and (now-(slot._last_cast or 0))>=cooldown then
                if castSpell(slot.words) then
                    slot._last_cast=now
                    slot._trigger_threshold=nil
                    H.last_cast_ms=now
                end
                break
            end
        end
    end

    -- KingsVale-compatible three potion slots. They are opt-in and never execute on load.
    for _, rule in ipairs(H.potion_rules or {}) do
        local resourceValue = rule.resource == "mana" and mp or hp
        if rule.enabled and resourceValue <= (rule.threshold or 50)
            and (now - (rule._last_use or 0)) >= (rule.cooldown_ms or H.cooldown_ms or 950) then
            local used = (rule.item_id or 0) > 0 and useInventoryItem(rule.item_id) or pressHotkey(rule.hotkey)
            if used then rule._last_use = now end
            break
        end
    end

    if vocationUiContract(RT.vocation).friend_healing and H.friend_enabled then
        for _, rule in ipairs(H.friend_rules or {}) do
            local friend = rule.enabled and getVisiblePlayerByName(rule.name) or nil
            if friend and getCreatureHealthPercent(friend) <= (rule.threshold or 80)
                and (now - (rule._last_cast or 0)) >= (rule.cooldown_ms or 950) then
                local safeName = tostring(rule.name or ""):gsub('["\\]', '')
                if safeName ~= "" and castSpell((rule.words or "exura sio") .. ' "' .. safeName .. '"') then
                    rule._last_cast = now
                end
                break
            end
        end
    end
end

-- ============================================================
-- RUNTIME: COMBAT / SPELL ROTATION
-- ============================================================
local function runSelectedShooterProfile(now)
    local C = CFG.combat
    local profile = C.shooter_profiles and C.shooter_profiles[C.selected_shooter_profile]
    if type(profile) ~= "table" then return false, false end
    local actions = {}
    for _, spell in ipairs(profile.spells or {}) do
        local words = cleanString(spell.words,"",64)
        if words == "" and (spell.id or 0) > 0 then words = resolveSpellWordsById(spell.id,"") end
        if words ~= "" then actions[#actions + 1] = {kind="spell",words=words,rule=spell} end
    end
    for _, rune in ipairs(profile.runes or {}) do
        if (rune.id or 0) > 0 then actions[#actions + 1] = {kind="rune",item_id=rune.id,rule=rune} end
    end
    if #actions == 0 then return false, false end
    table.sort(actions,function(left,right) return (left.rule.priority or 1) < (right.rule.priority or 1) end)
    if (now - (C.last_rotation_ms or 0)) < (C.rotation_interval_ms or 1050) then return true, false end
    local nearby, mana = getNearbyMonsterCount(C.attack_range), getMpPercent()
    local target=attackingCreature()
    if not safeCombatCreature(target) then target=nil end
    for _, action in ipairs(actions) do
        local rule = action.rule
        local hasCombatContext = rule.self_cast==true or target~=nil or nearby>0
        local enoughCreatures = hasCombatContext and (rule.force_cast or nearby >= (rule.creatures or 1))
        local enoughMana = action.kind == "rune" or mana >= (rule.percent or 1)
        if enoughCreatures and enoughMana then
            local used = action.kind == "spell" and castSpell(action.words)
                or (target~=nil and useInventoryItemOn(action.item_id,target))
            if used then C.last_rotation_ms=now;rule._last_cast=now;return true,true end
        end
    end
    return true, false
end

local function runCombat()
    local C = CFG.combat
    if not C.enabled then return end
    local now = nowMs()

    if C.auto_attack and C.auto_target_mode~=0 and g_game and type(g_game.attack)=="function" then
        local target,targetRule=selectConfiguredTarget(C.target_rules,C.attack_range)
        local current=attackingCreature()
        local currentNpc=isNpcCreature(current)
        local currentPlayer=isPlayerCreature(current)
        if current and (currentNpc or currentPlayer or not safeCombatCreature(current)) then
            if type(g_game.cancelAttack)=="function" then pcall(function() g_game.cancelAttack() end) end
            current=nil;C.current_locked_target_id=0;C._target_started_ms=0
        elseif current then
            local currentId=0
            if type(current.getId)=="function" then local ok,value=pcall(function() return current:getId() end);currentId=ok and tonumber(value) or 0 end
            if C.current_locked_target_id~=currentId then C.current_locked_target_id=currentId;C._target_started_ms=now end
            if (C._target_started_ms or 0)>0 and (now-C._target_started_ms)>=(C.target_timeout_ms or 10000) then
                if type(g_game.cancelAttack)=="function" then pcall(function() g_game.cancelAttack() end) end
                current=nil;C.current_locked_target_id=0;C._target_started_ms=0
            end
        end
        if target and not sameCreature(current,target) then
            pcall(function() g_game.attack(target) end)
            if type(target.getId)=="function" then local ok,value=pcall(function() return target:getId() end);C.current_locked_target_id=ok and tonumber(value) or 0 end
            C._target_started_ms=now
            if C.chase and (not targetRule or targetRule.chase~=false) and type(g_game.follow)=="function" then pcall(function() g_game.follow(target) end) end
        end
    end

    -- Spell rotation
    if C.spell_rotation and (not C.magic_shooter_on_hold or RT.shooter_hold) then
        runSelectedShooterProfile(now)
    end

    -- Auto Exeta
    if vocationUiContract(RT.vocation).auto_exeta and C.auto_exeta then
        if (now - C.last_exeta_ms) >= C.exeta_interval_ms then
            local nearby = getNearbyMonsterCount(C.attack_range)
            if nearby >= (C.exeta_min_visible or 2) then
                local spells = C.exeta_spells or {}
                for _,spell in ipairs(spells) do
                    local minimum=spell.min_nearby or C.exeta_min_visible or 2
                    local cooldown=spell.cooldown_ms or C.exeta_interval_ms or 5000
                    if nearby>=minimum and (now-(spell._last_cast or 0))>=cooldown then
                        castSpell(spell.words);spell._last_cast=now;C.last_exeta_ms=now;break
                    end
                end
            end
        end
    end
end

-- ============================================================
-- RUNTIME: CONDITIONS
-- ============================================================
local function runConditions()
    local CC = CFG.conditions
    if not CC.enabled then return end
    local now = nowMs()
    if (now - CC.last_sample_ms) < CC.sample_interval_ms then return end
    CC.last_sample_ms = now

    local p = getPlayer()
    if not p then return end

    local manaShieldCast=false
    local utamo=CC.utamo and CC.utamo[1]
    if utamo and utamo.enabled and getHpPercent()<=(utamo.percent or 80) then
        local hasManaShield=false
        if p.hasCondition then local ok,value=pcall(function() return p:hasCondition(ConditionManaShield or 64) end);hasManaShield=ok and value==true end
        if not hasManaShield then
            local words=utamo.words~="" and utamo.words or resolveSpellWordsById(utamo.id,"utamo vita")
            manaShieldCast=castSpell(words)==true
        end
    end

    -- Mana shield (cast if not active)
    if CC.mana_shield and CC.mana_shield_spell and not manaShieldCast then
        local hasManaShield = false
        if p.hasCondition then
            local ok, v = pcall(function() return p:hasCondition(ConditionManaShield or 64) end)
            hasManaShield = ok and v
        end
        if not hasManaShield then castSpell(CC.mana_shield_spell) end
    end

    -- Cure paralyze
    if CC.paralyze and CC.paralyze_spell then
        local isParalyzed = false
        if p.hasCondition then
            local ok, v = pcall(function() return p:hasCondition(ConditionParalyze or 4) end)
            isParalyzed = ok and v
        end
        if isParalyzed then castSpell(CC.paralyze_spell) end
    end

    if CC.poison and CC.poison_spell then
        local isPoisoned = false
        if p.hasCondition then
            local ok, v = pcall(function() return p:hasCondition(ConditionPoison or 1) end)
            isPoisoned = ok and v
        end
        if isPoisoned then castSpell(CC.poison_spell) end
    end
end

-- ============================================================
-- RUNTIME: SUPPORT SPELLS
-- ============================================================
local function runSupport()
    local S=CFG.support
    if not S.enabled then return end
    local now=nowMs()
    local hp=getHpPercent()
    local mp=getMpPercent()
    for _,rule in ipairs(S.rules or {}) do
        local resource=rule.resource or "always"
        local ready=resource=="always"
        if resource=="hp" then ready=hp<=ruleThreshold(rule) end
        if resource=="mana" then ready=mp<=ruleThreshold(rule) end
        if ready and (now-(rule._last_cast or 0)) >= (rule.interval_ms or 1000) then
            local used=false
            if rule.action=="item" then used=useInventoryItem(rule.item_id) else used=castSpell(rule.words) end
            if used then rule._last_cast=now; rule._trigger_threshold=nil end
            break
        end
    end
end

-- ============================================================
-- RUNTIME: KINGSVALE-COMPATIBLE TOOLS
-- ============================================================
local function runTools()
    local T = CFG.tools
    if type(T) ~= "table" or not T.enabled then return end
    local now, hp, mp = nowMs(), getHpPercent(), getMpPercent()
    local player = getPlayer()
    local function ready(key, interval)
        local stamp = T[key] or 0
        if (now - stamp) < (interval or T.action_interval_ms or 1000) then return false end
        T[key] = now
        return true
    end

    if T.mana_training and mp >= (T.mana_training_threshold or 100) and (T.mana_training_item_id or 0) > 0
        and ready("_last_mana_training",T.mana_training_interval_ms) then
        useInventoryItemOnSelf(T.mana_training_item_id)
    end

    if T.auto_haste and player and ready("_last_haste_check",1500) then
        local hasHaste = false
        if type(player.hasCondition) == "function" then
            local ok, value = pcall(function() return player:hasCondition(ConditionHaste or 16) end)
            hasHaste = ok and value == true
        end
        if not hasHaste then castSpell(T.haste_spell,{allow_in_pz=T.pz_cast==true}) end
    end

    if T.exercise_training and ready("_last_exercise",T.exercise_interval_ms) then
        local exerciseItemId=tonumber(T.exercise_item_id) or 0
        if exerciseItemId<=0 then
            local detectedId,detectedFamily=findExerciseWeaponIdForVocation(RT.vocation)
            if detectedId>0 then
                T.exercise_item_id=detectedId
                exerciseItemId=detectedId
                fileLog("exercise weapon auto-detected family="..tostring(detectedFamily).." id="..tostring(detectedId))
                markDirty();scheduleAutosave()
            end
        end
        if exerciseItemId>0 then useExerciseItem(exerciseItemId) end
    end
    if T.change_gold and (T.gold_item_id or 0) > 0 and ready("_last_gold",2000) then useInventoryItemPlain(T.gold_item_id) end
    if T.auto_eat_food and (T.food_item_id or 0) > 0 and ready("_last_food",30000) then useInventoryItemPlain(T.food_item_id) end
    local buff=T.buff and T.buff[1]
    if buff and buff.enabled and ready("_last_buff",30000) then
        local words=buff.words~="" and buff.words or resolveSpellWordsById(buff.id,"")
        if words~="" then castSpell(words) end
    end
    for index, ammo in ipairs(T.ammo_config or {}) do
        if ammo.enabled and (ammo.id or 0)>0 and ready("_last_ammo_"..tostring(index),5000) then useInventoryItemPlain(ammo.id) end
    end

    local function runEquipment(config, key)
        for _, rule in ipairs(config or {}) do
            local resource = rule.mana and mp or hp
            if rule.enabled and (rule.id or 0) > 0 and resource <= (rule.percent or 80) and ready(key,1500) then
                useInventoryItemPlain(rule.id)
                return
            end
        end
    end
    runEquipment(T.amulet_config,"_last_amulet")
    runEquipment(T.ring_config,"_last_ring")
end

-- ============================================================
-- RUNTIME: TIMER
-- ============================================================
local function runTimer()
    local T = CFG.timer
    if not T.enabled then return end
    local now = nowMs()
    if (now - T.last_ms) >= T.interval_ms then
        T.last_ms = now
        if T.message and T.message ~= "" then
            sendAutomationText(T.message,{spell=false})
        end
    end
end

-- ============================================================
-- THINK LOOP
-- ============================================================
local function runAutoReconnect()
    local T=CFG.tools
    if not T or not T.auto_reconnect then return false end
    local now=nowMs();if (now-(RT._last_reconnect or 0))<10000 then return false end
    RT._last_reconnect=now
    local enterGame=rawget(_G,"modules") and modules.client_entergame or nil
    if type(enterGame)=="table" and type(enterGame.doLogin)=="function" then
        local ok=pcall(function() enterGame.doLogin() end)
        if ok then setStatus("Auto reconnect requested") end
        return ok
    end
    setStatus("Auto reconnect unavailable in this fork")
    return false
end

local function onThink()
    if not safeProjectActive() then return end
    if not CFG.enabled or not RT.armed then return end
    if not isOnline() then runAutoReconnect();return end

    local ok, err = pcall(runHealing)
    if not ok then safeLog("healing error: " .. tostring(err)) end

    ok, err = pcall(runCombat)
    if not ok then safeLog("combat error: " .. tostring(err)) end

    -- Compatibility-only modules have no controls on the three-page Safe surface.
    -- Their profile data is retained, but they cannot dispatch invisibly.
    if not RT.compatibility_runtime_disabled then
        ok, err = pcall(runConditions)
        if not ok then safeLog("conditions error: " .. tostring(err)) end
        ok, err = pcall(runSupport)
        if not ok then safeLog("support error: " .. tostring(err)) end
    end

    ok, err = pcall(runTools)
    if not ok then safeLog("tools error: " .. tostring(err)) end

    if not RT.compatibility_runtime_disabled then
        ok, err = pcall(runTimer)
        if not ok then safeLog("timer error: " .. tostring(err)) end
    end
end

-- ============================================================
-- PUBLIC API
-- ============================================================
local function thingName(thing)
    if not thing or type(thing.getName)~="function" then return "" end
    local ok,name=pcall(function() return thing:getName() end)
    return ok and type(name)=="string" and name or ""
end

local function environmentFamilySnapshot(radius)
    radius=math.max(1,math.min(10,math.floor(tonumber(radius) or 7)))
    local inside,evidence=protectionZoneEvidence()
    local snapshot={
        protection_zone=inside,
        protection_zone_evidence=evidence,
        creatures={},
        items={},
        inventory_items={},
    }
    local player=getPlayer()
    if not player or type(player.getPosition)~="function" or not g_map then return snapshot end
    local okPosition,position=pcall(function() return player:getPosition() end)
    if not okPosition or not position then return snapshot end
    local okCreatures,creatures=false,nil
    if type(g_map.getSpectatorsInRange)=="function" then
        okCreatures,creatures=pcall(function() return g_map.getSpectatorsInRange(position,false,radius,radius) end)
    elseif type(g_map.getSpectators)=="function" then
        okCreatures,creatures=pcall(function() return g_map.getSpectators(position,false) end)
    end
    if okCreatures and type(creatures)=="table" then
        for _,creature in ipairs(creatures) do
            if #snapshot.creatures>=64 then break end
            local id=thingId(creature)
            local creatureType=numericCall(creature,"getType")
            local icon=numericCall(creature,"getIcon")
            local family="unknown"
            if isNpcCreature(creature) then family="npc"
            elseif isPlayerCreature(creature) then family="player"
            elseif isExerciseDummy(creature) then family="exercise_dummy"
            elseif optionalBool(creature,"isMonster")==true then family="monster" end
            snapshot.creatures[#snapshot.creatures+1]={id=id,name=thingName(creature),type=creatureType,icon=icon,family=family}
        end
    end
    if type(g_map.getTiles)=="function" then
        local okTiles,tiles=pcall(function() return g_map.getTiles(position.z) end)
        if okTiles and type(tiles)=="table" then
            for _,tile in ipairs(tiles) do
                if #snapshot.items>=128 then break end
                local okTilePosition,tilePosition=false,nil
                if tile and type(tile.getPosition)=="function" then okTilePosition,tilePosition=pcall(function() return tile:getPosition() end) end
                if okTilePosition and tilePosition and tilePosition.z==position.z
                    and math.max(math.abs(tilePosition.x-position.x),math.abs(tilePosition.y-position.y))<=radius
                    and type(tile.getItems)=="function" then
                    local okItems,items=pcall(function() return tile:getItems() end)
                    if okItems and type(items)=="table" then
                        for _,item in ipairs(items) do
                            if #snapshot.items>=128 then break end
                            local family=isExerciseDummy(item) and "exercise_dummy" or exerciseWeaponFamily(item)
                            if family then snapshot.items[#snapshot.items+1]={id=thingId(item),name=thingName(item),family=family} end
                        end
                    end
                end
            end
        end
    end
    if g_game and type(g_game.getContainers)=="function" then
        local okContainers,containers=pcall(function() return g_game.getContainers() end)
        if okContainers and type(containers)=="table" then
            for _,container in pairs(containers) do
                if #snapshot.inventory_items>=128 then break end
                if container and type(container.getItems)=="function" then
                    local okItems,items=pcall(function() return container:getItems() end)
                    if okItems and type(items)=="table" then
                        for _,item in ipairs(items) do
                            if #snapshot.inventory_items>=128 then break end
                            local family=exerciseWeaponFamily(item) or (isExerciseDummy(item) and "exercise_dummy" or nil)
                            if family then snapshot.inventory_items[#snapshot.inventory_items+1]={id=thingId(item),name=thingName(item),family=family} end
                        end
                    end
                end
            end
        end
    end
    return snapshot
end

local CTOA_SAFE = rawget(_G, "CTOA_SAFE") or {}
_G["CTOA_SAFE"] = CTOA_SAFE
CTOA_SAFE._loaded  = true
CTOA_SAFE.version  = SAFE_VERSION
CTOA_SAFE.config   = CFG

function CTOA_SAFE.environmentFamilySnapshot(radius)
    return environmentFamilySnapshot(radius)
end

function CTOA_SAFE.init()
    if RT.think_event or UI.window then return true end
    fileLog("CTOA_SAFE.init() called version=" .. SAFE_VERSION .. " pages=healing,tools,kvshooter compatibility=" .. KINGSVALE_SETTINGS_SCHEMA)
    loadProfile()
    fileLog("profile loaded")
    applySafeBoot()
    fileLog("safe boot applied")

    local uiOk, uiErr = pcall(buildUI)
    if uiOk then
        fileLog("buildUI ok, window=" .. tostring(UI.window ~= nil))
    else
        fileLog("buildUI ERROR: " .. tostring(uiErr))
    end

    bindHotkey()

    if type(cycleEvent) == "function" then
        RT.think_event = cycleEvent(onThink, CFG.tick_ms or TICK_MS)
    end

    -- Belt+suspenders: show window again after init
    if UI.window then
        if UI.window.show  then pcall(function() UI.window:show() end) end
        if UI.window.raise then pcall(function() UI.window:raise() end) end
    end

    setStatus("Ready " .. SAFE_VERSION)
    updateTitle()
    local environment=environmentFamilySnapshot(7)
    fileLog("environment snapshot pz="..tostring(environment.protection_zone)
        .." pz_sources="..table.concat(environment.protection_zone_evidence or {},",")
        .." creatures="..tostring(#(environment.creatures or {}))
        .." family_items="..tostring(#(environment.items or {}))
        .." inventory_family_items="..tostring(#(environment.inventory_items or {})))
    for _,creature in ipairs(environment.creatures or {}) do
        if creature.family=="npc" or creature.family=="exercise_dummy" then
            fileLog("environment creature family="..tostring(creature.family)
                .." id="..tostring(creature.id).." type="..tostring(creature.type)
                .." icon="..tostring(creature.icon).." name="..tostring(creature.name))
        end
    end
    for _,item in ipairs(environment.items or {}) do
        fileLog("environment item family="..tostring(item.family)
            .." id="..tostring(item.id).." name="..tostring(item.name))
    end
    for _,item in ipairs(environment.inventory_items or {}) do
        fileLog("environment inventory family="..tostring(item.family)
            .." id="..tostring(item.id).." name="..tostring(item.name))
    end
    fileLog("CTOA_SAFE.init() complete, window=" .. tostring(UI.window ~= nil))
    return true
end

function CTOA_SAFE.terminate()
    CFG.enabled = false
    RT.armed = false
    if RT.think_event and type(removeEvent) == "function" then pcall(removeEvent, RT.think_event); RT.think_event = nil end
    if RT.save_event and type(removeEvent) == "function" then pcall(removeEvent, RT.save_event); RT.save_event = nil end
    destroyEditPanel()
    destroySpellModal()
    if UI.window and UI.window.destroy then UI.window:destroy(); UI.window = nil end
    unbindHotkeys()
    CTOA_SAFE._loaded = false
    safeLog("Terminated")
    return true
end

function CTOA_SAFE.handleGameStart()
    local vocId = detectVocation()
    if vocId ~= RT.vocation then
        safeLog("Vocation changed: " .. vocId)
        RT.vocation = vocId
        loadProfile()
        refreshModuleRows()
        if UI.window then selectParityPage(UI.active_page or "healing") end
    end
    if UI.window and UI.window.show then
        UI.window:show(); UI.window:raise()
    end
    updateTitle()
end

function CTOA_SAFE.toggle()
    if UI.enable_btn and UI.enable_btn.onClick then
        UI.enable_btn.onClick()
    end
end

function CTOA_SAFE.setEnabled(enabled)
    local requested = enabled == true or enabled == "true" or enabled == 1
    if not requested then
        CFG.enabled = false
        RT.armed = false
        if UI.enable_btn and UI.enable_btn.setText then UI.enable_btn:setText("Enable Helper") end
        setStatus("Helper Status: Disabled")
        updateTitle()
        return true
    end
    if not safeProjectActive() then
        CFG.enabled = false
        RT.armed = false
        setStatus("Arm blocked: CTOA Safe is not the selected project")
        return false
    end
    CFG.enabled = true
    RT.armed = true
    if UI.enable_btn and UI.enable_btn.setText then UI.enable_btn:setText("Disable Helper") end
    setStatus("Helper Status: Enabled  [OK]")
    updateTitle()
    return true
end

function CTOA_SAFE.vocationUiContract(vocation)
    local source=vocationUiContract(vocation)
    return {
        label=source.label,
        spell_slots=source.spell_slots,
        potion_slots=source.potion_slots,
        friend_healing=source.friend_healing,
        auto_exeta=source.auto_exeta,
    }
end

function CTOA_SAFE.saveProfile()
    return saveProfile()
end

function CTOA_SAFE.createPreset(name) return createPreset(name) end
function CTOA_SAFE.selectPreset(id) return selectPreset(id) end
function CTOA_SAFE.deletePreset(id) return deletePreset(id) end
function CTOA_SAFE.exportPreset() return exportPreset() end
function CTOA_SAFE.importPreset() return importPreset() end
function CTOA_SAFE.importKingsValeSettings(path) return importKingsValeSettings(path) end
function CTOA_SAFE.exportKingsValeSettings(path) return exportKingsValeSettings(path) end
function CTOA_SAFE.kingsValeContract()
    return {schema=KINGSVALE_SETTINGS_SCHEMA,settings=kingsValeSettingsSnapshot(),safe_boot_override=true,source_files_embedded=false}
end

function CTOA_SAFE.profileContract()
    return {
        schema_version = PROFILE_SCHEMA,
        legacy_schema_version = LEGACY_PROFILE_SCHEMA,
        path = profilePath(RT.vocation),
        import_path = presetPath(RT.vocation, "_import.json"),
        format = "json",
        helper_profile_compatible = false,
        persists_runtime_arm = false,
        max_bytes = MAX_PROFILE_BYTES,
        max_presets = MAX_PRESETS,
        active_preset = RT.active_preset,
        preset_count = #RT.presets,
        compatibility = KINGSVALE_SETTINGS_SCHEMA,
        pages = {"Healing","Tools","KVShooter"},
        widget_contract = deepCopy(PARITY_WIDGET_CONTRACT),
        keyboard = {toggle=CFG.hotkey,next_module="Ctrl+Tab",previous_module="Ctrl+Shift+Tab",edit_module="Ctrl+E",toggle_module="Ctrl+Space"},
    }
end

return CTOA_SAFE
