local LootFilter = {}

local function hasValue(map, key)
  return type(map) == "table" and map[key] == true
end

function LootFilter.filter(items, whitelist, blacklist)
  items = items or {}
  whitelist = whitelist or {}
  blacklist = blacklist or {}
  local out = {}
  for _, item in ipairs(items) do
    local name = item and item.name
    local isBlacklisted = name ~= nil and hasValue(blacklist, name)
    local isWhitelisted = name ~= nil and hasValue(whitelist, name)
    local allowAll = next(whitelist) == nil
    if name ~= nil and not isBlacklisted and (allowAll or isWhitelisted) then
      table.insert(out, item)
    end
  end
  return out
end

function LootFilter.shouldStack(item)
  return item.stackable == true and item.count > 1
end

function LootFilter.shouldLoot(item, whitelist, blacklist)
  if type(item) ~= "table" or item.name == nil then
    return false
  end
  if hasValue(blacklist or {}, item.name) then
    return false
  end
  if whitelist == nil or next(whitelist) == nil then
    return true
  end
  return hasValue(whitelist, item.name)
end

function LootFilter.classify(item, whitelist, blacklist)
  if not LootFilter.shouldLoot(item, whitelist, blacklist) then
    return "skip"
  end
  if LootFilter.shouldStack(item) then
    return "stack"
  end
  return "loot"
end

return LootFilter
