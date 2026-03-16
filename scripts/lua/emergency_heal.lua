-- emergency_heal.lua  [CTOA Generated]
-- Last-line heal when HP drops too low.

local HEAL_AT_HP = 28
local COOLDOWN_SECONDS = 2
local lastCastAt = 0

local function onThink()
    if not Player.isOnline() then return end

    local now = os.time()
    if (now - lastCastAt) < COOLDOWN_SECONDS then return end

    if Player.getHpPercent() <= HEAL_AT_HP then
        Player.say("exura gran")
        lastCastAt = now
    end
end

register("onThink", onThink)
