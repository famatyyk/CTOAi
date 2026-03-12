local EventLogger = {}

EventLogger.config = {
  includePosition = true,
}

function EventLogger.log(state)
  local payload = {
    timestamp = os.time(),
    hp = state.hp,
    mana = state.mana,
    exp = state.exp,
  }

  if EventLogger.config.includePosition and state.position then
    payload.position = state.position
  end

  return payload
end

return EventLogger
