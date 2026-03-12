local TargetPriority = {}

local weights = {
  lowHealth = 4,
  highThreat = 5,
  closeDistance = 2,
}

function TargetPriority.score(target)
  local score = 0
  if target.lowHealth then score = score + weights.lowHealth end
  if target.highThreat then score = score + weights.highThreat end
  if target.closeDistance then score = score + weights.closeDistance end
  return score
end

function TargetPriority.pick(targets)
  local best = nil
  local bestScore = -1
  for _, t in ipairs(targets) do
    local s = TargetPriority.score(t)
    if s > bestScore then
      bestScore = s
      best = t
    end
  end
  return best, bestScore
end

return TargetPriority
