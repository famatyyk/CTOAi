-- proximity_watch.lua  [CTOA Generated]
-- Alerts when another player is close for safer manual reaction.

local WARN_RANGE = 7
local COOLDOWN_SECONDS = 15
local lastAlertAt = 0

local function onThink()
    if not Player.isOnline() then return end

    local now = os.time()
    if (now - lastAlertAt) < COOLDOWN_SECONDS then return end

    for _, c in ipairs(Creature.getAll()) do
        if c.isPlayer and c.name ~= Player.name then
            local d = math.abs(c.x - Player.x) + math.abs(c.y - Player.y)
            if d <= WARN_RANGE then
                Game.playSound("alert.wav")
                Game.addEvent("[Watch] Player nearby: " .. c.name, "warning")
                lastAlertAt = now
                return
            end
        end
    end
end

register("onThink", onThink)
