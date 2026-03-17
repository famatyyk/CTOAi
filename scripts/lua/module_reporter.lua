-- module_reporter.lua  [CTOA Generated]
-- Writes periodic CTOA status lines to local file (no UI console calls).

local INTERVAL_SECONDS = 120
local lastReportAt = 0
local didIntro = false

local function appendLog(text)
    local f = io.open("ctoa_local.log", "a")
    if not f then
        f = io.open("user_dir/ctoa_local.log", "a")
    end
    if not f then return end
    f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA] " .. text .. "\n")
    f:close()
end

local function logLine(text)
    appendLog(text)
end

local function onThink()
    if not Player.isOnline() then return end

    local now = os.time()

    if not didIntro then
        logLine("Log stream active: module_reporter, auto_reconnect, flee_logic, combo_spells, emergency_heal, proximity_watch.")
        didIntro = true
        lastReportAt = now
        return
    end

    if (now - lastReportAt) >= INTERVAL_SECONDS then
        logLine("Heartbeat HP=" .. Player.getHpPercent() .. "% Mana=" .. Player.getManaPercent() .. "%")
        lastReportAt = now
    end
end

register("onThink", onThink)

appendLog("module_reporter loaded")
