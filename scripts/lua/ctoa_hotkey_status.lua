-- ctoa_hotkey_status.lua  [CTOA Generated]
-- Emits one-shot [CTOA] status whenever wsad/chat mode is toggled.

local lastCheck = 0
local lastWsad = nil

local function appendLog(text)
    local f = io.open("ctoa_local.log", "a")
    if not f then
        f = io.open("user_dir/ctoa_local.log", "a")
    end
    if not f then return end
    f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [CTOA] " .. text .. "\n")
    f:close()
end

local function readWsadWalking()
    local f = io.open("config.otml", "r")
    if not f then return nil end

    local value = nil
    for line in f:lines() do
        local v = string.match(line, "^wsadWalking:%s*(%a+)")
        if v then
            value = (string.lower(v) == "true")
            break
        end
    end

    f:close()
    return value
end

local function emitStatus(state)
    local wsadText = state and "ON" or "OFF"
    local hp = Player.getHpPercent()
    local mana = Player.getManaPercent()
    appendLog("HOTKEY STATUS | WSAD=" .. wsadText .. " | HP=" .. hp .. "% | MANA=" .. mana .. "%")
end

local function onThink()
    if not Player.isOnline() then return end

    local now = os.time()
    if now == lastCheck then return end
    lastCheck = now

    local current = readWsadWalking()
    if current == nil then return end

    if lastWsad == nil then
        lastWsad = current
        return
    end

    if current ~= lastWsad then
        lastWsad = current
        emitStatus(current)
    end
end

register("onThink", onThink)

appendLog("ctoa_hotkey_status loaded")
