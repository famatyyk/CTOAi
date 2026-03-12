local SupplyManager = {}

function SupplyManager.checkSupplies(supplies, minLevels)
  local alerts = {}
  for item, amount in pairs(supplies) do
    local min = minLevels[item] or 0
    if amount <= min then
      table.insert(alerts, { item = item, amount = amount, min = min })
    end
  end
  return alerts
end

function SupplyManager.shouldRefill(alerts)
  return #alerts > 0
end

return SupplyManager
