local AutoHeal = {}

AutoHeal.config = {
  hpThreshold = 45,
  manaThreshold = 20,
  cooldownSeconds = 2,
}

function AutoHeal.shouldCast(state, lastCastAt)
  local now = os.time()
  if lastCastAt and (now - lastCastAt) < AutoHeal.config.cooldownSeconds then
    return false
  end

  if state.hpPercent <= AutoHeal.config.hpThreshold then
    return true
  end

  if state.manaPercent <= AutoHeal.config.manaThreshold then
    return true
  end

  return false
end

return AutoHeal
