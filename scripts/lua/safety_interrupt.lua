local SafetyInterrupt = {}

SafetyInterrupt.config = {
  criticalHp = 25,
}

function SafetyInterrupt.shouldInterrupt(state)
  return state.hpPercent <= SafetyInterrupt.config.criticalHp
end

function SafetyInterrupt.nextAction(state)
  if SafetyInterrupt.shouldInterrupt(state) then
    return "RETREAT"
  end
  return "CONTINUE"
end

return SafetyInterrupt
