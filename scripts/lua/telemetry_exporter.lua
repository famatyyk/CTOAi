local TelemetryExporter = {}

local function escape(value)
  local s = tostring(value)
  s = s:gsub('\\', '\\\\'):gsub('"', '\\"')
  return s
end

function TelemetryExporter.toJsonLine(event)
  local parts = {}
  for k, v in pairs(event) do
    table.insert(parts, string.format('"%s":"%s"', escape(k), escape(v)))
  end
  return "{" .. table.concat(parts, ",") .. "}"
end

return TelemetryExporter
