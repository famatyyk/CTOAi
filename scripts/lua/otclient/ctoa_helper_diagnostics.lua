-- ctoa_helper_diagnostics.lua [CTOA OTClient Native]
-- Passive diagnostics helpers for logs and evidence exports.

local Diagnostics = rawget(_G, "CTOA_HELPER_DIAGNOSTICS") or {}

function Diagnostics.boolText(value)
    return value and "yes" or "no"
end

function Diagnostics.trimText(value)
    local text = tostring(value or "")
    return string.gsub(text, "^%s*(.-)%s*$", "%1")
end

function Diagnostics.posText(pos)
    if type(pos) ~= "table" then
        return "nil"
    end
    return tostring(pos.x) .. "," .. tostring(pos.y) .. "," .. tostring(pos.z)
end

function Diagnostics.hasApi(owner, methodName)
    return owner ~= nil and type(owner[methodName]) == "function"
end

function Diagnostics.apiText(owner, methodName)
    return Diagnostics.boolText(Diagnostics.hasApi(owner, methodName))
end

function Diagnostics.valueText(ok, value)
    if not ok then
        return "n/a"
    end
    if type(value) == "table" then
        return "table"
    end
    if value == nil then
        return "nil"
    end
    return tostring(value)
end

function Diagnostics.vocationProbeText(snapshot)
    local data = snapshot or {}
    return "Vocation probe: raw=" .. tostring(data.raw) ..
        " resolved=" .. tostring(data.resolved) ..
        " source=" .. tostring(data.source)
end

local function unavailableRuntimeCoreSnapshot()
    return {
            schema_version = "ctoa.runtime-core.v1",
            status = "unavailable",
            mode = "passive",
            runtime_actions = false,
            registered_modules = 0,
            registered_tasks = 0,
            enabled_tasks = 0,
            disabled_tasks = 0,
            failed_tasks = 0,
            tasks_deferred = 0,
            task_failures = 0,
        }
end

function Diagnostics.runtimeCoreSnapshot(runtimeCore)
    local core = runtimeCore or rawget(_G, "CTOA_HELPER_RUNTIME_CORE")
    if type(core) ~= "table" or type(core.statusSnapshot) ~= "function" then
        return unavailableRuntimeCoreSnapshot()
    end
    local ok, snapshot = pcall(core.statusSnapshot)
    if not ok or type(snapshot) ~= "table" then
        return unavailableRuntimeCoreSnapshot()
    end
    snapshot.status = "available"
    snapshot.runtime_actions = false
    return snapshot
end

function Diagnostics.runtimeCoreText(snapshot)
    local item = type(snapshot) == "table" and snapshot or Diagnostics.runtimeCoreSnapshot(nil)
    return "Runtime: " .. tostring(item.status or "available") ..
        " tasks=" .. tostring(item.enabled_tasks or 0) .. "/" .. tostring(item.registered_tasks or 0) ..
        " deferred=" .. tostring(item.tasks_deferred or 0) ..
        " failed=" .. tostring(item.task_failures or 0)
end

function Diagnostics.apiSnapshotText(snapshot, version)
    if type(snapshot) ~= "table" then
        return "API: pending probe"
    end
    return "API " .. tostring(snapshot.version or version or "?") ..
        " | " .. tostring(snapshot.core or "core=n/a") ..
        " | " .. tostring(snapshot.player or "player=n/a") ..
        " | " .. Diagnostics.runtimeCoreText(snapshot.runtime_core)
end

function Diagnostics.apiProbeSnapshot(options)
    local data = options or {}
    local vitals = data.vitals or {}
    local game = data.game
    local map = data.map
    local player = data.player
    local target = data.target
    local ui = data.ui
    local keyboard = data.keyboard
    local resources = data.resources
    local container = data.container
    return {
        version = data.version,
        core =
            "online=" .. Diagnostics.boolText(data.online) ..
            " localPlayer=" .. Diagnostics.boolText(player) ..
            " clockMillis=" .. Diagnostics.boolText(data.clock_millis) ..
            " pos=" .. Diagnostics.posText(data.current_pos),
        player =
            "vitals=" .. tostring(vitals.source or "none") ..
            " hp=" .. tostring(vitals.hp or "n/a") .. "/" .. tostring(vitals.max_hp or "n/a") ..
            " hpPct=" .. tostring(vitals.hp_percent or "n/a") ..
            " mana=" .. tostring(vitals.mana or "n/a") .. "/" .. tostring(vitals.max_mana or "n/a") ..
            " manaPct=" .. tostring(vitals.mana_percent or "n/a") ..
            " pz=" .. Diagnostics.valueText(data.pz_ok, data.pz) ..
            " states=" .. tostring(data.states or "n/a") ..
            " tileFlags=" .. tostring(data.tile_flags or "n/a"),
        movement =
            "player.autoWalk=" .. Diagnostics.apiText(player, "autoWalk") ..
            " player.stopAutoWalk=" .. Diagnostics.apiText(player, "stopAutoWalk") ..
            " player.canWalk=" .. Diagnostics.valueText(data.can_walk_ok, data.can_walk) ..
            " player.isAutoWalking=" .. Diagnostics.valueText(data.auto_walking_ok, data.auto_walking) ..
            " map.findPath=" .. Diagnostics.apiText(map, "findPath") ..
            " map.getSpectatorsInRange=" .. Diagnostics.apiText(map, "getSpectatorsInRange") ..
            " map.getCreaturesInRange=" .. Diagnostics.apiText(map, "getCreaturesInRange") ..
            " game.forceWalk=" .. Diagnostics.apiText(game, "forceWalk"),
        combat =
            "attack=" .. Diagnostics.apiText(game, "attack") ..
            " cancelAttack=" .. Diagnostics.apiText(game, "cancelAttack") ..
            " setChaseMode=" .. Diagnostics.apiText(game, "setChaseMode") ..
            " getAttackingCreature=" .. Diagnostics.apiText(game, "getAttackingCreature") ..
            " target=" .. Diagnostics.boolText(data.target_ok and target) ..
            " targetName=" .. tostring(data.target_name or "n/a"),
        magic =
            "talk=" .. Diagnostics.apiText(game, "talk") ..
            " useInventoryItemWith=" .. Diagnostics.apiText(game, "useInventoryItemWith") ..
            " findItemInContainers=" .. Diagnostics.apiText(game, "findItemInContainers"),
        ui =
            "createWidget=" .. Diagnostics.apiText(ui, "createWidget") ..
            " bindKeyDown=" .. Diagnostics.apiText(keyboard, "bindKeyDown") ..
            " unbindKeyDown=" .. Diagnostics.apiText(keyboard, "unbindKeyDown") ..
            " userDir=" .. Diagnostics.apiText(resources, "getUserDir") ..
            " workDir=" .. Diagnostics.apiText(resources, "getWorkDir") ..
            " fileExists=" .. Diagnostics.apiText(resources, "fileExists"),
        loot =
            "getContainers=" .. Diagnostics.apiText(game, "getContainers") ..
            " containers=" .. tostring(data.container_count or 0) ..
            " container.getItems=" .. Diagnostics.apiText(container, "getItems") ..
            " container.getItemsCount=" .. Diagnostics.apiText(container, "getItemsCount") ..
            " move=" .. Diagnostics.apiText(game, "move") ..
            " adapter=" .. tostring(data.loot_adapter_text ~= "" and data.loot_adapter_text or "n/a"),
        runtime_core = Diagnostics.runtimeCoreSnapshot(data.runtime_core),
    }
end

function Diagnostics.apiProbeText(options)
    local data = options or {}
    local snapshot = data.snapshot or {}
    return "API probe (" .. tostring(data.reason or "startup") .. "): version=" ..
        tostring(snapshot.version or data.version or "?") ..
        " core[" .. tostring(snapshot.core or "n/a") .. "] player[" ..
        tostring(snapshot.player or "n/a") .. "]",
        "API probe detail: movement[" .. tostring(snapshot.movement or "n/a") ..
        "] combat[" .. tostring(snapshot.combat or "n/a") .. "] magic[" ..
        tostring(snapshot.magic or "n/a") .. "] ui[" ..
        tostring(snapshot.ui or "n/a") .. "] loot[" ..
        tostring(snapshot.loot or "n/a") .. "]"
end

function Diagnostics.probeDeferredPlan(options)
    local data = options or {}
    if data.reason == "manual" then
        return {defer = false}
    end
    if data.online ~= false and data.has_player == true and (data.requires_position ~= true or data.has_position == true) then
        return {defer = false}
    end
    local attempts = (tonumber(data.attempts) or 0) + 1
    local retry = attempts <= (tonumber(data.max_attempts) or 120)
    local label = tostring(data.label or "API")
    local missing = data.requires_position == true and "no local player position" or "no local player"
    return {
        defer = true,
        attempts = attempts,
        retry = retry,
        retry_delay_ms = tonumber(data.retry_delay_ms) or 2000,
        status_text = label .. " probe deferred: " .. missing,
    }
end

function Diagnostics.magicApiProbeText(options)
    local data = options or {}
    local action = data.action
    local actionText = data.action_text or (action and action.kind) or "none"
    if action and action.spell then
        actionText = tostring(action.kind or "spell") .. ":" .. tostring(action.spell.words or action.spell)
    end
    return "Magic API probe (" .. tostring(data.reason or "startup") .. "): " ..
        "version=" .. tostring(data.version or "?") ..
        " talk=" .. Diagnostics.apiText(data.game, "talk") ..
        " useInventoryItemWith=" .. Diagnostics.apiText(data.game, "useInventoryItemWith") ..
        " findItemInContainers=" .. Diagnostics.apiText(data.game, "findItemInContainers") ..
        " target=" .. Diagnostics.boolText(data.target) ..
        " nearby=" .. tostring(data.nearby or 0) ..
        " visible=" .. tostring(data.visible or 0) ..
        " rotation=" .. Diagnostics.boolText(data.spell_rotation) ..
        " rune=" .. Diagnostics.boolText(data.rune_enabled) ..
        " runeSlot=" .. tostring(data.rune_slot or "?") ..
        " action=" .. actionText
end

function Diagnostics.featureFlagsText(flags)
    flags = flags or {}
    return "Flags: diag=" .. Diagnostics.boolText(flags.diagnostics == true) ..
        " cave=" .. Diagnostics.boolText(flags.experimental_cavebot == true) ..
        " loot=" .. Diagnostics.boolText(flags.experimental_loot == true) ..
        " combat=" .. Diagnostics.boolText(flags.experimental_combat == true)
end

function Diagnostics.appendLog(msg, prefix)
    local f = nil
    if g_resources and g_resources.getWorkDir then
        local ok, workDir = pcall(function()
            return g_resources.getWorkDir()
        end)
        if ok and workDir and workDir ~= "" then
            local last = string.sub(workDir, -1)
            local separator = (last == "/" or last == "\\") and "" or "/"
            f = io.open(workDir .. separator .. "ctoa_local.log", "a")
        end
    end
    if not f and g_resources and g_resources.getUserDir then
        local ok, userDir = pcall(function()
            return g_resources.getUserDir()
        end)
        if ok and userDir and userDir ~= "" then
            f = io.open(userDir .. "/ctoa_local.log", "a")
        end
    end
    if not f then
        f = io.open("ctoa_local.log", "a")
    end
    if f then
        f:write(os.date("%Y-%m-%d %H:%M:%S") .. " [" .. tostring(prefix or "CTOA-OTC-HELPER") .. "] " .. tostring(msg or "") .. "\n")
        f:close()
        return true
    end
    return false
end

function Diagnostics.exportPath(uiPath)
    if type(uiPath) == "string" and uiPath ~= "" then
        return string.gsub(uiPath, "ctoa_ui_prefs%.lua$", "ctoa_diag_export.lua")
    end
    if g_resources and g_resources.getWorkDir then
        return g_resources.getWorkDir() .. "mods/ctoa_otclient/ctoa_diag_export.lua"
    end
    return "ctoa_diag_export.lua"
end

function Diagnostics.bufferText(buffer, limit)
    local count = #(buffer or {})
    return "Export: " .. tostring(count) .. "/" .. tostring(limit or 20) .. " samples"
end

function Diagnostics.movementText(snapshot)
    snapshot = snapshot or {}
    return "Move: " .. tostring(snapshot.movement or "pending")
end

function Diagnostics.magicLootText(snapshot)
    snapshot = snapshot or {}
    return "Magic: " .. tostring(snapshot.magic or "pending") ..
        " | Loot: " .. tostring(snapshot.loot or "pending")
end

function Diagnostics.snapshotUiRows()
    return {
        {widget = "tools_api_snapshot", text = "api", scale = 0.78},
        {widget = "tools_diag_core", text = "api", scale = 0.78},
        {widget = "tools_diag_flags", text = "flags", scale = 0.82},
        {widget = "tools_diag_detail", text = "movement", scale = 0.72},
        {widget = "tools_diag_magic", text = "magic_loot", scale = 0.72},
        {widget = "tools_diag_export", text = "buffer", scale = 0.86},
    }
end

function Diagnostics.snapshotUiValues(snapshot, flags, buffer, limit, version)
    return {
        api = Diagnostics.apiSnapshotText(snapshot, version),
        flags = Diagnostics.featureFlagsText(flags),
        movement = Diagnostics.movementText(snapshot),
        magic_loot = Diagnostics.magicLootText(snapshot),
        buffer = Diagnostics.bufferText(buffer, limit),
    }
end

function Diagnostics.tableCount(value)
    if type(value) ~= "table" then
        return 0
    end
    local count = 0
    for _ in pairs(value) do
        count = count + 1
    end
    return count
end

function Diagnostics.firstTableValue(value)
    if type(value) ~= "table" then
        return nil
    end
    for _, item in pairs(value) do
        return item
    end
    return nil
end

function Diagnostics.smokeCommandValue(text, key)
    local escaped = tostring(key or "")
    local patterns = {
        escaped .. "%s*=%s*\"([^\"]*)\"",
        escaped .. "%s*=%s*'([^']*)'",
        escaped .. "%s*=%s*([%w_%-/]+)",
    }
    for _, pattern in ipairs(patterns) do
        local value = string.match(text, pattern)
        if value ~= nil then
            return Diagnostics.trimText(value)
        end
    end
    return nil
end

function Diagnostics.smokeCommandExists(path, resources, ioLib)
    if resources and resources.fileExists then
        local ok, exists = pcall(function()
            return resources.fileExists(path)
        end)
        if ok and exists then
            return true
        end
    end
    local fileApi = ioLib or io
    if fileApi and fileApi.open then
        local ok, file = pcall(function()
            return fileApi.open(path, "r")
        end)
        if ok and file then
            file:close()
            return true
        end
    end
    return false
end

function Diagnostics.parseSmokeCommandText(text)
    if type(text) ~= "string" or text == "" or #text > 4096 then
        return nil
    end
    local command = {}
    local hasValue = false
    for _, key in ipairs({"action", "tab", "subtab", "theme", "session_id", "plan_sha256", "p9_receipt_sha256", "p10_receipt_sha256", "p11_receipt_sha256", "p12_equipment_receipt_sha256", "retry_budget", "before_item_id", "candidate_item_id", "source_container_id", "source_slot_index", "target_id", "target_name", "whitelist_revision", "hp_threshold", "max_range"}) do
        local value = Diagnostics.smokeCommandValue(text, key)
        if value and value ~= "" then
            command[key] = value
            hasValue = true
        end
    end
    local confirm = Diagnostics.smokeCommandValue(text, "confirm")
    if confirm == "true" then
        command.confirm = true
        hasValue = true
    end
    for _, key in ipairs({"session_approved", "execution_approved"}) do
        if Diagnostics.smokeCommandValue(text, key) == "true" then
            command[key] = true
            hasValue = true
        end
    end
    if hasValue then
        return command
    end
    return nil
end

function Diagnostics.smokeCommandTarget(command)
    if type(command) ~= "table" then
        return nil
    end
    local action = command.action
    local tab = command.tab
    local subtab = command.subtab
    local theme = command.theme
    if (type(tab) ~= "string" or tab == "") and type(action) == "string" and string.find(action, "^cavebot_") then
        tab = "cavebot"
    elseif (type(tab) ~= "string" or tab == "") and action == "magic_probe" then
        tab = "hunting"
        subtab = "magic"
    elseif (type(tab) ~= "string" or tab == "") and action == "api_probe" then
        tab = "tools"
        subtab = "helper"
    elseif (type(tab) ~= "string" or tab == "") and action == "diag_export" then
        tab = "tools"
        subtab = "diag"
    end
    if type(tab) ~= "string" or tab == "" then
        return nil
    end
    return {
        action = action,
        tab = tab,
        subtab = subtab,
        theme = theme,
        confirm = command.confirm == true
    }
end

function Diagnostics.smokeTabLabel(target)
    if type(target) ~= "table" then
        return ""
    end
    local label = tostring(target.tab or "")
    if type(target.subtab) == "string" and target.subtab ~= "" then
        label = label .. "/" .. target.subtab
    end
    return label
end

function Diagnostics.smokeTabStatusText(target)
    return "Smoke tab visible: " .. Diagnostics.smokeTabLabel(target)
end

function Diagnostics.smokeCommandStatusText(event, data)
    data = data or {}
    if event == "tab_visible" then
        return Diagnostics.smokeTabStatusText(data.target or data)
    elseif event == "blocked" then
        return "Smoke command blocked: " .. tostring(data.reason or "unknown")
    elseif event == "failed" then
        return "Smoke command failed: " .. tostring(data.value)
    end
    return "Smoke command: " .. tostring(event or "unknown")
end

function Diagnostics.smokeCommandBlockedText(reason)
    return Diagnostics.smokeCommandStatusText("blocked", {reason = reason})
end

function Diagnostics.smokeCommandFailedText(value)
    return Diagnostics.smokeCommandStatusText("failed", {value = value})
end

function Diagnostics.recordSnapshot(buffer, options)
    options = options or {}
    local snapshot = options.snapshot
    if type(snapshot) ~= "table" then
        return buffer or {}, false
    end
    local nextBuffer = buffer or {}
    local limit = math.max(1, math.min(tonumber(options.limit) or 20, 100))
    nextBuffer[#nextBuffer + 1] = {
        version = options.version,
        reason = tostring(options.reason or "sample"),
        captured_ms = tonumber(options.captured_ms) or 0,
        core = snapshot.core,
        player = snapshot.player,
        movement = snapshot.movement,
        combat = snapshot.combat,
        magic = snapshot.magic,
        loot = snapshot.loot,
        runtime_core = snapshot.runtime_core
    }
    while #nextBuffer > limit do
        table.remove(nextBuffer, 1)
    end
    return nextBuffer, true
end

function Diagnostics.exportBuffer(options)
    options = options or {}
    local path = options.path or Diagnostics.exportPath(options.ui_path)
    local file = io and io.open and io.open(path, "w") or nil
    if not file then
        if type(options.status) == "function" then
            options.status("Diagnostics export failed")
        end
        return false
    end
    local payload = {
        version = options.version,
        reason = tostring(options.reason or "manual"),
        exported_ms = tonumber(options.exported_ms) or 0,
        samples = options.samples or {}
    }
    file:write("-- ctoa_diag_export.lua\n")
    file:write("-- Generated by ctoa_helper_diagnostics.lua diagnostics export.\n\n")
    file:write("return " .. options.serialize(payload, 0) .. "\n")
    file:close()
    if type(options.status) == "function" then
        options.status("Diagnostics exported: " .. path)
    end
    if type(options.refresh) == "function" then
        options.refresh()
    end
    return true
end

function Diagnostics.contract()
    return {
        module = "ctoa_helper_diagnostics",
        mode = "passive",
        owns_formatters = true,
        owns_bool_text = true,
        owns_pos_text = true,
        owns_api_text = true,
        owns_value_text = true,
        owns_vocation_probe_text = true,
        owns_runtime_core_snapshot = true,
        owns_runtime_core_text = true,
        owns_api_snapshot_text = true,
        owns_api_probe_snapshot = true,
        owns_api_probe_text = true,
        owns_probe_deferred_plan = true,
        owns_magic_api_probe_text = true,
        owns_feature_flags_text = true,
        owns_workdir_log_path = true,
        owns_buffer_text = true,
        owns_movement_text = true,
        owns_magic_loot_text = true,
        owns_snapshot_ui_rows = true,
        owns_snapshot_ui_values = true,
        owns_table_count = true,
        owns_first_table_value = true,
        owns_smoke_command_exists = true,
        owns_smoke_command_parse = true,
        owns_smoke_command_target = true,
        owns_smoke_status_text = true,
        owns_smoke_command_status_text = true,
        owns_record_snapshot = true,
        owns_export_buffer = true,
        runtime_actions = false,
        executes_plans = false,
        writes_profile = false,
        requires_module_static_gates = true,
    }
end

_G.CTOA_HELPER_DIAGNOSTICS = Diagnostics
return Diagnostics
