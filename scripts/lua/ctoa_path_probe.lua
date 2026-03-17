-- ctoa_path_probe.lua  [CTOA Diagnostic]
-- Writes probe lines every 5 seconds to multiple candidate paths.

local INTERVAL_SECONDS = 5
local lastTick = 0
local counter = 0

local targetPaths = {
    "ctoa_local.log",
    "user_dir/ctoa_local.log",
    "ctoa_probe.log",
    "user_dir/ctoa_probe.log"
}

local function tryAppend(path, line)
    local f = io.open(path, "a")
    if not f then return false end
    f:write(line .. "\n")
    f:close()
    return true
end

local function writeProbe(tag)
    counter = counter + 1
    local hp = 0
    local mana = 0
    if Player and Player.isOnline and Player.isOnline() then
        hp = Player.getHpPercent() or 0
        mana = Player.getManaPercent() or 0
    end

    local line = os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA-PROBE] " .. tag .. " #" .. counter .. " HP=" .. hp .. "% MANA=" .. mana .. "%"
    for _, path in ipairs(targetPaths) do
        tryAppend(path, line .. " -> " .. path)
    end
end

local function onThink()
    if not Player or not Player.isOnline or not Player.isOnline() then return end

    local now = os.time()
    if (now - lastTick) < INTERVAL_SECONDS then return end
    lastTick = now

    writeProbe("tick")
end

register("onThink", onThink)
writeProbe("loaded")
