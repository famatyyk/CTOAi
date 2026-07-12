-- ctoa_helper_equipment.lua [CTOA OTClient Native]
-- Read-only equipment observer domain. It never swaps, moves, or uses items.

local Equipment = rawget(_G, "CTOA_HELPER_EQUIPMENT") or {}

local function boolText(value)
    return value and "yes" or "no"
end

function Equipment.slotText(player, label, slotCandidates, ctx)
    ctx = ctx or {}
    if not player or not player.getInventoryItem then
        return label .. ":api?"
    end
    for _, slot in ipairs(slotCandidates or {}) do
        if slot ~= nil then
            local ok, item = pcall(function()
                return player:getInventoryItem(slot)
            end)
            if ok then
                if item then
                    local nameOk, name = false, nil
                    if ctx.safeCall then
                        nameOk, name = ctx.safeCall(item, "getName")
                    end
                    if nameOk and name and name ~= "" then
                        return label .. ":" .. tostring(name)
                    end
                    local idOk, itemId = false, nil
                    if ctx.safeCall then
                        idOk, itemId = ctx.safeCall(item, "getId")
                    end
                    if idOk and itemId then
                        return label .. ":#" .. tostring(itemId)
                    end
                    return label .. ":item"
                end
                return label .. ":empty"
            end
        end
    end
    return label .. ":slot?"
end

function Equipment.snapshot(ctx)
    ctx = ctx or {}
    local player = ctx.getLocalPlayer and ctx.getLocalPlayer() or nil
    local parts = {
        Equipment.slotText(player, "ring", {_G.InventorySlotFinger, _G.InventorySlotRing}, ctx),
        Equipment.slotText(player, "amulet", {_G.InventorySlotNecklace, _G.InventorySlotAmulet}, ctx),
        Equipment.slotText(player, "left", {_G.InventorySlotLeft, _G.InventorySlotLeftHand}, ctx),
        Equipment.slotText(player, "right", {_G.InventorySlotRight, _G.InventorySlotRightHand}, ctx)
    }
    return table.concat(parts, " | ")
end

function Equipment.apiProbe(config, ctx)
    ctx = ctx or {}
    local equipment = config or {}
    if equipment.api_probe_enabled == false then
        equipment.api_probe_status = "api probe off"
        return equipment.api_probe_status
    end
    equipment.api_probe_count = (equipment.api_probe_count or 0) + 1
    local player = ctx.getLocalPlayer and ctx.getLocalPlayer() or nil
    local parts = {
        "player.getInventoryItem=" .. boolText(player and player.getInventoryItem),
        "slot.ring=" .. boolText(_G.InventorySlotFinger or _G.InventorySlotRing),
        "slot.amulet=" .. boolText(_G.InventorySlotNecklace or _G.InventorySlotAmulet),
        "slot.left=" .. boolText(_G.InventorySlotLeft or _G.InventorySlotLeftHand),
        "slot.right=" .. boolText(_G.InventorySlotRight or _G.InventorySlotRightHand)
    }
    equipment.api_probe_status = table.concat(parts, " ")
    return equipment.api_probe_status
end

function Equipment.observe(config, now, ctx)
    ctx = ctx or {}
    local equipment = config or {}
    if not equipment.enabled or not equipment.observe_slots then
        return false
    end
    if now - (equipment.last_sample_ms or 0) < (equipment.sample_interval_ms or 1500) then
        return false
    end
    equipment.last_sample_ms = now
    equipment.last_status = Equipment.snapshot(ctx) .. " | " .. Equipment.apiProbe(equipment, ctx)
    return true
end

function Equipment.plan(config, observation, context)
    local equipment = config or {}
    local observed = observation or {}
    local ctx = context or {}
    local hp = tonumber(observed.hp_percent or ctx.hp_percent or 100) or 100
    local threshold = tonumber(equipment.hp_threshold or 45) or 45
    local plan = {
        next_action = "hold",
        reason = "planner_disabled",
        runtime_actions = false
    }
    if not equipment.enabled then
        return plan
    end
    if equipment.runtime_enabled ~= true or ctx.runtime_allowed ~= true then
        plan.reason = "runtime_gated"
        return plan
    end
    if equipment.pvp_gear_lock == true and ctx.pvp_detected == true then
        plan.reason = "pvp_gear_lock"
        return plan
    end
    if hp > threshold then
        plan.reason = "hp_above_threshold"
        plan.hp_percent = hp
        plan.threshold = threshold
        return plan
    end
    if equipment.ring_swap == true then
        plan.next_action = "plan_ring_swap"
        plan.reason = "hp_threshold"
        plan.hp_percent = hp
        plan.threshold = threshold
        return plan
    end
    if equipment.amulet_swap == true then
        plan.next_action = "plan_amulet_swap"
        plan.reason = "hp_threshold"
        plan.hp_percent = hp
        plan.threshold = threshold
        return plan
    end
    plan.reason = "no_swap_enabled"
    return plan
end

-- Build a bounded, data-only ring plan for the P10 shadow lane.  This helper
-- never calls an inventory API and never mutates a slot; the runtime gate and
-- offline replay remain the only consumers allowed to review the plan.
function Equipment.shadowPlan(snapshot)
    local observed = type(snapshot) == "table" and snapshot or {}
    local blockers = {}
    local equipped = tonumber(observed.equipped_item_id)
    local candidate = tonumber(observed.candidate_item_id)
    local rollback = tonumber(observed.rollback_item_id)
    if observed.slot_name ~= "ring" or observed.rollback_slot_name ~= "ring" then blockers[#blockers + 1] = "ring_slot_snapshot_required" end
    if not equipped or equipped <= 0 or not candidate or candidate <= 0 then blockers[#blockers + 1] = "item_id_snapshot_required" end
    if equipped and candidate and equipped == candidate then blockers[#blockers + 1] = "candidate_matches_equipped" end
    if not rollback or rollback ~= equipped then blockers[#blockers + 1] = "rollback_snapshot_mismatch" end
    if tostring(observed.inventory_revision or "") == "" or tostring(observed.rollback_inventory_revision or "") ~= tostring(observed.inventory_revision or "") then blockers[#blockers + 1] = "inventory_revision_drift" end
    if observed.inventory_unambiguous ~= true then blockers[#blockers + 1] = "inventory_ambiguous" end
    if observed.protection_zone ~= "outside" then blockers[#blockers + 1] = "protection_zone_not_outside" end
    local plan = {
        action = "plan_ring_swap", slot = "ring", before_item_id = equipped,
        candidate_item_id = candidate, rollback_item_id = rollback,
        inventory_revision = tostring(observed.inventory_revision or ""),
        rollback_inventory_revision = tostring(observed.rollback_inventory_revision or ""),
        dispatch_allowed = false, runtime_actions = false, retry_budget = 0,
    }
    return {
        schema_version = "ctoa.equipment-shadow-plan.v1", mode = "shadow_only",
        status = #blockers == 0 and "shadow_plan_ready" or "operational_acceptance_blocked",
        action = "plan_ring_swap", blockers = blockers, plan = plan,
        rollback_simulation = #blockers == 0 and "ready" or "blocked",
        dispatch_allowed = false, runtime_actions = false, executes_plan = false,
        execute_once_allowed = false, promotion_allowed = false,
        intrusive_actions_performed = {},
    }
end

function Equipment.summary(config, helpers)
    helpers = helpers or {}
    local equipment = config or {}
    local onOffText = helpers.onOffText or function(value)
        return value and "ON" or "OFF"
    end
    local runtimeText = equipment.runtime_enabled and "runtime ON" or "read-only"
    local planText = equipment.runtime_enabled and "planner gated" or "planner passive"
    return "Observer " .. onOffText(equipment.enabled == true) ..
        " | Ring " .. onOffText(equipment.ring_swap == true) ..
        " | Amulet " .. onOffText(equipment.amulet_swap == true) ..
        " | API " .. onOffText(equipment.api_probe_enabled ~= false) ..
        " | " .. tostring(equipment.weapon_set or "manual") ..
        " | " .. runtimeText ..
        " | " .. planText
end

function Equipment.contract()
    return {
        mode = "passive",
        owns_slot_text = true,
        owns_snapshot = true,
        owns_api_probe = true,
        owns_observer = true,
        owns_summary_text = true,
        owns_shadow_ring_plan = true,
        shadow_plan_data_only = true,
        rollback_revision_required = true,
        runtime_actions = false,
        swaps = false,
        moves_items = false,
        requires_runtime_gate = true,
        requires_sandbox_attach = true
    }
end

_G.CTOA_HELPER_EQUIPMENT = Equipment
return Equipment
