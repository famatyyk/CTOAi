local PathingHelper = {}

PathingHelper.config = {
  defaultMaxRetries = 3,
}

local function normalizeWaypoint(point)
  if type(point) ~= "table" then
    return nil
  end

  local x = tonumber(point.x or point[1])
  local y = tonumber(point.y or point[2])
  local z = tonumber(point.z or point[3] or 7)
  if x == nil or y == nil or z == nil then
    return nil
  end

  return { x = x, y = y, z = z }
end

function PathingHelper.normalizeRoute(route)
  local normalized = {}
  if type(route) ~= "table" then
    return normalized
  end

  for _, point in ipairs(route) do
    local waypoint = normalizeWaypoint(point)
    if waypoint then
      table.insert(normalized, waypoint)
    end
  end

  return normalized
end

function PathingHelper.nextWaypoint(route, index, fallback)
  local normalized = PathingHelper.normalizeRoute(route)
  if #normalized == 0 then
    return fallback, 1, true
  end

  local i = tonumber(index) or 1
  if i < 1 then
    i = 1
  end
  if i > #normalized then
    i = 1
  end

  return normalized[i], i + 1, false
end

function PathingHelper.retryBlocked(maxRetries, currentRetries, fallback)
  local retries = currentRetries or 0
  local limit = maxRetries or PathingHelper.config.defaultMaxRetries
  if retries >= limit then
    return false, retries, fallback
  end

  return true, retries + 1, nil
end

return PathingHelper
