local EventLogger = {}

EventLogger.config = {
  includePosition = true,
}

local function safeNumber(value, defaultValue)
  local n = tonumber(value)
  if n == nil then
    return defaultValue
  end
  return n
end

local function getStateValue(state, key, fallback)
  if type(state) ~= "table" then
    return fallback
  end
  local value = state[key]
  if value == nil then
    return fallback
  end
  return value
end

local function normalizePosition(position)
  if type(position) ~= "table" then
    return position
  end

  return {
    x = safeNumber(position.x or position[1], 0),
    y = safeNumber(position.y or position[2], 0),
    z = safeNumber(position.z or position[3], 0),
  }
end

local function encodeJson(value)
  local valueType = type(value)
  if valueType == "number" or valueType == "boolean" then
    return tostring(value)
  end
  if valueType ~= "table" then
    local s = tostring(value)
    s = s:gsub("\\", "\\\\"):gsub('"', '\\"')
    return '"' .. s .. '"'
  end

  local keys = {}
  for key in pairs(value) do
    table.insert(keys, key)
  end
  table.sort(keys, function(a, b)
    return tostring(a) < tostring(b)
  end)

  local parts = {}
  for _, key in ipairs(keys) do
    local encodedKey = encodeJson(key)
    local encodedValue = encodeJson(value[key])
    table.insert(parts, encodedKey .. ":" .. encodedValue)
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

function EventLogger.build(state)
  state = state or {}
  local payload = {
    timestamp = os.time(),
    hp = safeNumber(getStateValue(state, "hp", getStateValue(state, "hpPercent", 0)), 0),
    mana = safeNumber(getStateValue(state, "mana", getStateValue(state, "manaPercent", 0)), 0),
    exp = safeNumber(getStateValue(state, "exp", getStateValue(state, "experience", 0)), 0),
  }

  local position = getStateValue(state, "position", nil)
  if EventLogger.config.includePosition and position ~= nil then
    payload.position = normalizePosition(position)
  end

  return payload
end

function EventLogger.log(state)
  return EventLogger.build(state)
end

function EventLogger.toJsonLine(state)
  return encodeJson(EventLogger.build(state))
end

return EventLogger
