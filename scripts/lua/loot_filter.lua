local LootFilter = {}

function LootFilter.filter(items, whitelist, blacklist)
  local out = {}
  for _, item in ipairs(items) do
    local isBlacklisted = blacklist[item.name] == true
    local isWhitelisted = whitelist[item.name] == true
    if not isBlacklisted and isWhitelisted then
      table.insert(out, item)
    end
  end
  return out
end

function LootFilter.shouldStack(item)
  return item.stackable == true and item.count > 1
end

return LootFilter
