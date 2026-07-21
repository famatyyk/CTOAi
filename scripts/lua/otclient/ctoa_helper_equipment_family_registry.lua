-- Data-only equipment identity registry. Item IDs are transport states, not UI identity.

local Registry = rawget(_G, "CTOA_HELPER_EQUIPMENT_FAMILY_REGISTRY") or {}

local SCHEMA = "ctoa.equipment-family-registry.v1"
local ALLOWED_SLOTS = {ring = true, amulet = true}
local FAMILIES = {
    {
        key = "ring_primary",
        label = "Primary ring",
        slot = "ring",
        inventory_ids = {3093},
        equipped_ids = {3096},
        returned_ids = {3093},
        default_enabled = false,
        execution_scope = "p12_ring_only",
    },
    {
        key = "ring_secondary",
        label = "Secondary ring",
        slot = "ring",
        inventory_ids = {3097},
        equipped_ids = {3099},
        returned_ids = {3097},
        default_enabled = false,
        execution_scope = "p12_ring_only",
    },
}

local function copy(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for key, item in pairs(value) do result[key] = copy(item) end
    return result
end

local function validId(value)
    local number = tonumber(value)
    return number and number % 1 == 0 and number > 0 and number <= 65535
end

local function validateIds(values)
    if type(values) ~= "table" or #values == 0 then return false end
    local seen = {}
    for _, value in ipairs(values) do
        if not validId(value) or seen[tonumber(value)] then return false end
        seen[tonumber(value)] = true
    end
    return true
end

function Registry.validateFamily(family)
    local blockers = {}
    if type(family) ~= "table" then return false, {"family_table_required"} end
    if type(family.key) ~= "string" or not string.match(family.key, "^[a-z][a-z0-9_]*$") then blockers[#blockers + 1] = "family_key_invalid" end
    if type(family.label) ~= "string" or family.label == "" or #family.label > 48 then blockers[#blockers + 1] = "family_label_invalid" end
    if ALLOWED_SLOTS[tostring(family.slot)] ~= true then blockers[#blockers + 1] = "family_slot_invalid" end
    for _, field in ipairs({"inventory_ids", "equipped_ids", "returned_ids"}) do
        if not validateIds(family[field]) then blockers[#blockers + 1] = field .. "_invalid" end
    end
    if family.default_enabled ~= false then blockers[#blockers + 1] = "default_must_be_disabled" end
    if family.execution_scope ~= "p12_ring_only" and family.execution_scope ~= "passive_only" then blockers[#blockers + 1] = "execution_scope_invalid" end
    return #blockers == 0, blockers
end

function Registry.validate()
    local blockers, keys = {}, {}
    for index, family in ipairs(FAMILIES) do
        local ok, familyBlockers = Registry.validateFamily(family)
        if keys[family.key] then blockers[#blockers + 1] = "duplicate_family_key:" .. family.key end
        keys[family.key] = true
        if not ok then
            for _, blocker in ipairs(familyBlockers) do blockers[#blockers + 1] = tostring(index) .. ":" .. blocker end
        end
    end
    return #blockers == 0, blockers
end

function Registry.families(slot)
    local result = {}
    for _, family in ipairs(FAMILIES) do
        if slot == nil or tostring(family.slot) == tostring(slot) then result[#result + 1] = copy(family) end
    end
    return result
end

function Registry.byKey(key)
    for _, family in ipairs(FAMILIES) do
        if family.key == tostring(key or "") then return copy(family) end
    end
    return nil
end

local function contains(values, itemId)
    for _, value in ipairs(values or {}) do if tonumber(value) == tonumber(itemId) then return true end end
    return false
end

function Registry.match(slot, itemId)
    local matches = {}
    for _, family in ipairs(FAMILIES) do
        if family.slot == tostring(slot or "") then
            local inventory = contains(family.inventory_ids, itemId)
            local equipped = contains(family.equipped_ids, itemId)
            local returned = contains(family.returned_ids, itemId)
            if inventory or equipped or returned then
                local state = equipped and "equipped" or (inventory and returned and "inventory_or_returned" or (inventory and "inventory" or "returned"))
                matches[#matches + 1] = {family = copy(family), state = state}
            end
        end
    end
    if #matches ~= 1 then return nil, #matches == 0 and "unknown_item_state" or "ambiguous_item_state" end
    return matches[1], nil
end

function Registry.isEnabled(config, key)
    local enabled = type(config) == "table" and config.family_enabled or nil
    return type(enabled) == "table" and enabled[tostring(key or "")] == true
end

function Registry.setEnabled(config, key, value)
    if type(config) ~= "table" or not Registry.byKey(key) then return false, "unknown_family" end
    if type(config.family_enabled) ~= "table" then config.family_enabled = {} end
    config.family_enabled[tostring(key)] = value == true
    local anyRing = false
    for _, family in ipairs(FAMILIES) do
        if family.slot == "ring" and config.family_enabled[family.key] == true then anyRing = true end
    end
    config.ring_swap = anyRing
    return true, value == true and "enabled" or "disabled"
end

function Registry.uiRows(config, slot)
    local rows = {}
    for _, family in ipairs(Registry.families(slot)) do
        rows[#rows + 1] = {
            key = family.key,
            label = family.label,
            checked = Registry.isEnabled(config, family.key),
            slot = family.slot,
            item_ids_hidden = true,
            execution_scope = family.execution_scope,
        }
    end
    return rows
end

function Registry.enabledFamily(config, slot)
    local selected = {}
    for _, family in ipairs(FAMILIES) do
        if family.slot == tostring(slot or "") and Registry.isEnabled(config, family.key) then selected[#selected + 1] = family end
    end
    if #selected ~= 1 then return nil, #selected == 0 and "no_family_enabled" or "multiple_families_enabled" end
    return copy(selected[1]), nil
end

function Registry.proposeTransition(input)
    local value = type(input) == "table" and input or {}
    local blockers = {}
    if ALLOWED_SLOTS[tostring(value.slot)] ~= true then blockers[#blockers + 1] = "slot_invalid" end
    for _, field in ipairs({"before_equipped_id", "candidate_inventory_id", "after_equipped_id", "returned_inventory_id"}) do
        if not validId(value[field]) then blockers[#blockers + 1] = field .. "_invalid" end
    end
    local candidate = Registry.match(value.slot, value.candidate_inventory_id)
    local after = Registry.match(value.slot, value.after_equipped_id)
    local before = Registry.match(value.slot, value.before_equipped_id)
    local returned = Registry.match(value.slot, value.returned_inventory_id)
    local known = candidate and after and before and returned and
        candidate.family.key == after.family.key and before.family.key == returned.family.key
    return {
        schema_version = "ctoa.equipment-family-transition-proposal.v1",
        status = #blockers == 0 and (known and "known_transition" or "review_required") or "blocked",
        slot = value.slot,
        source_family_key = candidate and candidate.family.key or nil,
        displaced_family_key = before and before.family.key or nil,
        transition_known = known == true,
        operator_approval_required = known ~= true,
        blockers = blockers,
        dispatch_allowed = false,
        runtime_actions = false,
        execute_once_allowed = false,
        promotion_allowed = false,
    }
end

function Registry.contract()
    local valid, blockers = Registry.validate()
    return {
        schema_version = SCHEMA,
        mode = "data_only",
        valid = valid,
        blockers = blockers,
        family_count = #FAMILIES,
        item_ids_hidden_in_ui = true,
        unknown_transitions_require_approval = true,
        amulet_execution = false,
        runtime_actions = false,
        moves_items = false,
        equips_items = false,
        default_armed = false,
    }
end

_G.CTOA_HELPER_EQUIPMENT_FAMILY_REGISTRY = Registry
return Registry
