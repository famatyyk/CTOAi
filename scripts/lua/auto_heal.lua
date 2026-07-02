local AutoHeal = {}

AutoHeal.config = {
  hpThreshold = 45,
  manaThreshold = 20,
  cooldownSeconds = 2,
  criticalHpThreshold = 25,
  hpSpell = "exura",
  manaSpell = "exura mana",
}

local function readPercent(state, primaryKey, fallbackKey)
  if type(state) ~= "table" then
    return 100
  end

  local value = state[primaryKey]
  if value == nil and fallbackKey then
    value = state[fallbackKey]
  end

  return tonumber(value) or 100
end

local function pickHealReason(state, config)
  local cfg = config or AutoHeal.config
  local hpPercent = readPercent(state, "hpPercent", "hp")
  local manaPercent = readPercent(state, "manaPercent", "mana")

  if hpPercent <= (cfg.criticalHpThreshold or cfg.hpThreshold or AutoHeal.config.hpThreshold) then
    return "critical_hp"
  end

  if hpPercent <= (cfg.hpThreshold or AutoHeal.config.hpThreshold) then
    return "hp"
  end

  if manaPercent <= (cfg.manaThreshold or AutoHeal.config.manaThreshold) then
    return "mana"
  end

  return nil
end

function AutoHeal.shouldCast(state, lastCastAt, config)
  local cfg = config or AutoHeal.config
  local now = os.time()
  if lastCastAt and (now - lastCastAt) < (cfg.cooldownSeconds or AutoHeal.config.cooldownSeconds) then
    return false
  end

  return pickHealReason(state, cfg) ~= nil
end

function AutoHeal.nextAction(state, lastCastAt, config)
  local cfg = config or AutoHeal.config
  local shouldCast = AutoHeal.shouldCast(state, lastCastAt, cfg)
  if not shouldCast then
    return "CONTINUE", nil
  end

  local reason = pickHealReason(state, cfg)
  if reason == "critical_hp" or reason == "hp" then
    return "CAST", cfg.hpSpell or AutoHeal.config.hpSpell
  end

  return "CAST", cfg.manaSpell or AutoHeal.config.manaSpell
end

return AutoHeal
