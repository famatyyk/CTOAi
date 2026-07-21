-- ctoa_helper_equipment_runtime_gate.lua [CTOA OTClient Native]
-- Equipment v1 safety gate. It approves only a dry-run, rollback-ready ring plan.

local EquipmentRuntimeGate = rawget(_G, "CTOA_HELPER_EQUIPMENT_RUNTIME_GATE") or {}
local Gate = rawget(_G, "CTOA_HELPER_RUNTIME_MODULE_GATE")

local REQUIRED_TRUE = {
    "manifest_current",
    "module_static_gates",
    "module_attach_smoke",
    "smoke_attach_all",
    "equipment_observer_smoke",
    "equipment_observation_current",
    "sandbox",
    "operator_confirmed",
    "runtime_disarmed",
    "dry_run",
    "online",
    "player_alive",
    "client_ready",
    "outside_protection_zone",
    "inventory_unambiguous",
    "free_slot_confirmed",
    "rollback_supported",
}

local function finiteNumber(value)
    local result = tonumber(value)
    if not result or result ~= result or result == math.huge or result == -math.huge then return nil end
    return result
end

local function integer(value)
    local result = finiteNumber(value)
    if not result or result % 1 ~= 0 then return nil end
    return result
end

local function itemId(value)
    local result = integer(value)
    if not result or result <= 0 or result > 65535 then return nil end
    return result
end

local function runtimeLanesDisabled(value)
    return type(value) == "table" and value.combat == "disabled" and value.cavebot == "disabled"
end

function EquipmentRuntimeGate.evaluate(input)
    local data = input or {}
    if type(Gate) ~= "table" or type(Gate.evaluate) ~= "function" then
        return {status = "blocked", accepted = false, blockers = {"gate_engine_missing"}}
    end
    local trace = Gate.evaluate({
        schema_version = "ctoa.equipment-runtime-safety-gate.v1",
        gate_id = "equipment_runtime_gate",
        phase = "equipment_after_conditions",
        domain = "equipment",
        allowed_actions = {"plan_ring_swap"},
        required_true = REQUIRED_TRUE,
        required_false = {"protection_zone", "live_promotion"},
    }, data)
    if type(Gate.acceptedTrace) ~= "function" or not Gate.acceptedTrace(data.conditions_gate_trace, "conditions_runtime_gate", "plan_paralyze_recovery", "ctoa.conditions-runtime-safety-gate.v1") then
        Gate.block(trace, "conditions_gate_trace_required")
    end
    if not runtimeLanesDisabled(data.runtime_lane_states) then Gate.block(trace, "high_risk_lanes_must_be_disabled") end
    if tostring(data.evidence_id or "") == "" then Gate.block(trace, "evidence_id_required") end
    if tostring(data.observation_id or "") == "" then Gate.block(trace, "observation_id_required") end

    local equipped = itemId(data.equipped_item_id)
    local candidate = itemId(data.candidate_item_id)
    local rollback = itemId(data.rollback_item_id)
    if not equipped then Gate.block(trace, "equipped_item_id_invalid") end
    if not candidate then Gate.block(trace, "candidate_item_id_invalid") end
    if equipped and candidate and equipped == candidate then Gate.block(trace, "candidate_matches_equipped") end
    if not rollback or rollback ~= equipped then Gate.block(trace, "rollback_snapshot_mismatch") end
    if tostring(data.slot_name or ""):lower() ~= "ring" or tostring(data.rollback_slot_name or ""):lower() ~= "ring" then
        Gate.block(trace, "ring_slot_snapshot_required")
    end
    local sourceContainer = integer(data.candidate_source_container_id)
    local rollbackContainer = integer(data.rollback_destination_container_id)
    if not sourceContainer or sourceContainer < 0 or not rollbackContainer or rollbackContainer ~= sourceContainer then
        Gate.block(trace, "rollback_container_snapshot_mismatch")
    end
    local sourceSlot = integer(data.candidate_source_slot_index)
    local rollbackSlot = integer(data.rollback_destination_slot_index)
    if not sourceSlot or sourceSlot < 1 or not rollbackSlot or rollbackSlot ~= sourceSlot then
        Gate.block(trace, "rollback_container_slot_snapshot_mismatch")
    end
    local inventoryRevision = tostring(data.inventory_revision or "")
    if inventoryRevision == "" or tostring(data.rollback_inventory_revision or "") ~= inventoryRevision then
        Gate.block(trace, "rollback_inventory_revision_mismatch")
    end

    local observedAt = integer(data.observed_at_ms)
    local evaluatedAt = integer(data.evaluated_at_ms)
    if not observedAt or observedAt < 0 or not evaluatedAt or evaluatedAt < observedAt then
        Gate.block(trace, "observation_timestamp_invalid")
    elseif evaluatedAt - observedAt > 1000 then
        Gate.block(trace, "observation_stale")
    else
        trace.observation_age_ms = evaluatedAt - observedAt
    end
    local cooldown = integer(data.cooldown_ms)
    local elapsed = integer(data.cooldown_elapsed_ms)
    if not cooldown or cooldown < 1000 or cooldown > 60000 then Gate.block(trace, "cooldown_invalid") end
    if not elapsed or elapsed < 0 then
        Gate.block(trace, "cooldown_elapsed_invalid")
    elseif cooldown and elapsed < cooldown then
        Gate.block(trace, "cooldown_active")
    end
    if integer(data.retry_budget) ~= 0 then Gate.block(trace, "equipment_retry_forbidden") end
    return Gate.finish(trace)
end

function EquipmentRuntimeGate.contract()
    return {
        module = "ctoa_helper_equipment_runtime_gate",
        mode = "sandbox_dry_run_gate",
        phase = "equipment_after_conditions",
        allowed_action = "plan_ring_swap",
        default_closed = true,
        requires_conditions_gate = true,
        requires_bound_conditions_trace = true,
        requires_exact_item_ids = true,
        requires_rollback_snapshot = true,
        requires_ring_slot_and_container_snapshot = true,
        derives_observation_age_from_timestamps = true,
        requires_cooldown_elapsed = true,
        retries_forbidden = true,
        requires_operator_confirmation = true,
        blocks_protection_zone = true,
        combat_deferred = true,
        cavebot_deferred = true,
        dispatch_allowed = false,
        runtime_actions = false,
        live_promotion = false,
    }
end

_G.CTOA_HELPER_EQUIPMENT_RUNTIME_GATE = EquipmentRuntimeGate
return EquipmentRuntimeGate
