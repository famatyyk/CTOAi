local SupplyManager = {}

SupplyManager.config = {
  defaultReserve = 0,
}

local function asNumber(value, fallback)
  local n = tonumber(value)
  if n == nil then
    return fallback
  end
  return n
end

function SupplyManager.checkSupplies(supplies, minLevels)
  supplies = supplies or {}
  minLevels = minLevels or {}
  local alerts = {}

  for item, minAmount in pairs(minLevels) do
    local min = asNumber(minAmount, SupplyManager.config.defaultReserve)
    local current = asNumber(supplies[item], 0)
    if current <= min then
      table.insert(alerts, {
        item = item,
        amount = current,
        min = min,
        missing = math.max(0, min - current),
      })
    end
  end

  return alerts
end

function SupplyManager.shouldRefill(alerts, maxAlerts)
  local count = #(alerts or {})
  local limit = tonumber(maxAlerts) or 1
  return count >= limit
end

function SupplyManager.nextAction(supplies, minLevels, maxAlerts)
  local alerts = SupplyManager.checkSupplies(supplies, minLevels)
  if SupplyManager.shouldRefill(alerts, maxAlerts) then
    return "REFILL", alerts
  end
  return "CONTINUE", alerts
end

return SupplyManager
