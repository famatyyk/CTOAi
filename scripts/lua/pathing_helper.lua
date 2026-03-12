local PathingHelper = {}

function PathingHelper.nextWaypoint(route, index)
  if route == nil or #route == 0 then
    return nil
  end

  local i = index or 1
  if i > #route then
    i = 1
  end

  return route[i], i + 1
end

function PathingHelper.retryBlocked(maxRetries, currentRetries)
  local retries = currentRetries or 0
  if retries >= (maxRetries or 3) then
    return false, retries
  end

  return true, retries + 1
end

return PathingHelper
