-- status_beacon.lua  [CTOA Generated]
-- Lightweight periodic status message for quick observability.

local PERIOD_SECONDS = 300
local lastTick = 0

local function onThink()
    if not Player.isOnline() then return end

    local now = os.time()
    if (now - lastTick) < PERIOD_SECONDS then return end

    Game.addEvent("[Beacon] HP=" .. Player.getHpPercent() .. "% | Mana=" .. Player.getManaPercent() .. "%", "info")
    lastTick = now
end

register("onThink", onThink)
