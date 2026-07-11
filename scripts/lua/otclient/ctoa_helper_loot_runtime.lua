-- ctoa_helper_loot_runtime.lua [CTOA OTClient Native]
-- Passive loot runtime adapter planner. This module never scans containers or moves items.

local LootRuntime = rawget(_G, "CTOA_HELPER_LOOT_RUNTIME") or {}

local function boolValue(value)
    return value == true
end

local function numberValue(value, fallback)
    local parsed = tonumber(value)
    if parsed == nil then
        return fallback
    end
    return parsed
end

local function runtimeBlockedReason(tools, context, container_snapshot)
    local cfg = tools or {}
    local env = context or {}
    local snapshot = container_snapshot or {}
    if not boolValue(cfg.experimental_loot) then
        return "feature_flag_disabled"
    end
    if not boolValue(cfg.auto_loot) and not boolValue(cfg.auto_open_corpses) then
        return "runtime_disabled"
    end
    if boolValue(cfg.pause_in_pz) and boolValue(env.in_protection_zone) then
        return "protection_zone"
    end
    if env.online == false then
        return "offline"
    end
    if boolValue(cfg.require_capacity) and numberValue(snapshot.free_capacity, 0) <= 0 then
        return "no_capacity"
    end
    if numberValue(snapshot.open_container_count, 0) <= 0 and not boolValue(cfg.auto_open_corpses) then
        return "no_open_container"
    end
    return nil
end

function LootRuntime.plan(tools, context, container_snapshot)
    local blocked = runtimeBlockedReason(tools, context, container_snapshot)
    local cfg = tools or {}
    local snapshot = container_snapshot or {}
    local openContainers = numberValue(snapshot.open_container_count, 0)
    local corpseCandidates = numberValue(snapshot.corpse_candidate_count, 0)
    local valuableItems = numberValue(snapshot.valuable_item_count, 0)
    if blocked then
        return {
            allowed = false,
            reason = blocked,
            next_action = "hold",
            open_container_count = openContainers,
            valuable_item_count = valuableItems,
        }
    end
    local lootOperation = "scan"
    if openContainers <= 0 and boolValue(cfg.auto_open_corpses) and corpseCandidates > 0 then
        lootOperation = "open"
    elseif valuableItems > 0 and boolValue(cfg.auto_loot) then
        lootOperation = "move"
    end
    return {
        allowed = true,
        reason = "planned",
        next_action = "plan_loot",
        loot_operation = lootOperation,
        open_container_count = openContainers,
        corpse_candidate_count = corpseCandidates,
        valuable_item_count = valuableItems,
        max_items_per_scan = numberValue(cfg.loot_max_items_per_scan, 3),
    }
end

function LootRuntime.summary(plan)
    if type(plan) ~= "table" then
        return "loot adapter idle"
    end
    return tostring(plan.next_action or "hold") ..
        " | " .. tostring(plan.reason or "unknown") ..
        " | items " .. tostring(plan.valuable_item_count or 0) ..
        " | containers " .. tostring(plan.open_container_count or 0)
end

function LootRuntime.adapterSummary(tools, context, container_snapshot)
    local cfg = tools or {}
    local flags = cfg.feature_flags or {}
    local plan = LootRuntime.plan({
        experimental_loot = flags.experimental_loot == true,
        auto_loot = cfg.auto_loot_containers == true,
        auto_open_corpses = cfg.auto_open_corpses == true,
        pause_in_pz = cfg.pause_in_pz == true,
        require_capacity = cfg.loot_require_capacity == true,
        loot_max_items_per_scan = cfg.loot_max_items_per_scan or 3,
    }, context or {}, container_snapshot or {})
    local text = LootRuntime.summary(plan)
    if text ~= "" then
        return text, plan
    end
    return tostring(plan.next_action or "hold") .. " | " .. tostring(plan.reason or "unknown"), plan
end

function LootRuntime.contract()
    return {
        module = "ctoa_helper_loot_runtime",
        mode = "passive",
        owns_runtime_plan = true,
        owns_adapter_summary = true,
        runtime_actions = false,
        scans_containers = false,
        opens_containers = false,
        moves_items = false,
        uses_items = false,
        requires_experimental_flag = true,
        requires_container_probe = true,
        requires_sandbox_attach = true,
    }
end

_G.CTOA_HELPER_LOOT_RUNTIME = LootRuntime

return LootRuntime
