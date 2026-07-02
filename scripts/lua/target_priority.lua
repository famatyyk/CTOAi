local TargetPriority = {}

local weights = {
  lowHealth = 4,
  highThreat = 5,
  closeDistance = 2,
  engaged = 1,
}

local function asNumber(value, fallback)
  local n = tonumber(value)
  if n == nil then
    return fallback
  end
  return n
end

local function normalizeTarget(target)
  if type(target) ~= "table" then
    return nil
  end

  return {
    id = target.id,
    name = target.name,
    lowHealth = target.lowHealth == true or asNumber(target.healthPercent, 100) <= 30,
    highThreat = target.highThreat == true or asNumber(target.threat, 0) >= 5,
    closeDistance = target.closeDistance == true or asNumber(target.distance, 99) <= 3,
    engaged = target.engaged == true,
    healthPercent = asNumber(target.healthPercent, 100),
    threat = asNumber(target.threat, 0),
    distance = asNumber(target.distance, 99),
  }
end

function TargetPriority.score(target)
  target = normalizeTarget(target)
  if target == nil then
    return -1
  end

  local score = 0
  if target.lowHealth then score = score + weights.lowHealth end
  if target.highThreat then score = score + weights.highThreat end
  if target.closeDistance then score = score + weights.closeDistance end
  if target.engaged then score = score + weights.engaged end
  return score
end

function TargetPriority.pick(targets)
  if type(targets) ~= "table" then
    return nil, -1
  end

  local best = nil
  local bestScore = -1
  for _, t in ipairs(targets) do
    local normalized = normalizeTarget(t)
    local s = TargetPriority.score(normalized)
    if normalized ~= nil and (
      s > bestScore
      or (s == bestScore and best ~= nil and normalized.healthPercent < best.healthPercent)
      or (s == bestScore and best ~= nil and normalized.distance < best.distance)
    ) then
      bestScore = s
      best = normalized
    end
  end
  return best, bestScore
end

function TargetPriority.normalize(target)
  return normalizeTarget(target)
end

return TargetPriority
