-- ctoa_chooser_loader.lua [CTOA Project Loader]
-- The only normal CTOA autoload entrypoint. It activates Helper only after an
-- explicit choice, except for the fully flag-bound isolated P14 capture path.

local LOADER_VERSION = "2.1.1"
local P14_CAPTURE_FLAGS = {
    CTOA_P14_CAPTURE_HELPER_ACTIVATION = "helper-ui-only",
    CTOA_P14_ISOLATED_ENVIRONMENT = "true",
    CTOA_P14_CAPTURE_CONTEXT = "guest",
    CTOA_P14_OPERATOR_WORKSTATION_FOCUS_USED = "false",
    CTOA_P14_OPERATOR_WORKSTATION_INPUT_USED = "false",
    CTOA_P14_NETWORK_DISPATCH_USED = "false",
    CTOA_P14_LIVE_CLIENT_ACCESSED = "false",
    CTOA_P14_PROMOTION_ATTEMPTED = "false",
}

local PROJECTS = {
    helper = {
        module_name = "ctoa_otclient",
        loader_paths = {"/mods/ctoa_otclient/ctoa_otclient_loader.lua", "mods/ctoa_otclient/ctoa_otclient_loader.lua", "/scripts/lua/otclient/ctoa_otclient_loader.lua"},
        global_name = "CTOA_OTCLIENT",
        label = "CTOA Helper",
        activation = function(api)
            if type(api) ~= "table" or type(api.loadHelperOnly) ~= "function" then
                return false, "project_api_missing"
            end
            local callOk, result = pcall(api.loadHelperOnly)
            if not callOk then
                return false, tostring(result or "helper_load_failed")
            end
            if result == false or api.loaded ~= true then
                return false, "helper_load_rejected"
            end
            return true
        end,
    },
}

local Loader = rawget(_G, "CTOA_PROJECT_LOADER") or {}
_G.CTOA_PROJECT_LOADER = Loader

Loader.version = LOADER_VERSION
Loader.activation_pending = Loader.activation_pending == true
Loader.online_session = Loader.online_session == true
Loader.initialized = Loader.initialized == true
Loader.callbacks = Loader.callbacks or nil
Loader.window = Loader.window or nil
Loader.show_event = Loader.show_event or nil
Loader.capture_activation_event = Loader.capture_activation_event or nil

local function log(message)
    local text = "[CTOA-LOADER] " .. tostring(message)
    print(text)
    if g_resources and type(g_resources.getWorkDir) == "function" then
        local ok, workDir = pcall(function() return g_resources.getWorkDir() end)
        if ok and workDir and workDir ~= "" then
            local file = io.open(workDir .. "ctoa_project_loader.log", "a")
            if file then file:write(os.date("%Y-%m-%d %H:%M:%S") .. " " .. text .. "\n"); file:close() end
        end
    end
end

local function removeScheduled(event)
    if event and type(removeEvent) == "function" then
        pcall(removeEvent, event)
    end
end

-- This is deliberately narrower than a normal autoload. Only the isolated P14
-- capture process supplies every flag, so ordinary client sessions still require
-- an operator choice in the chooser UI.
local function p14CaptureActivationRequested()
    if not os or type(os.getenv) ~= "function" then return false end
    for name, expected in pairs(P14_CAPTURE_FLAGS) do
        local ok, value = pcall(function() return os.getenv(name) end)
        if not ok or value ~= expected then return false end
    end
    return true
end

local function fileExists(path)
    if g_resources and type(g_resources.fileExists) == "function" then
        local ok, exists = pcall(function() return g_resources.fileExists(path) end)
        if ok and exists then return true end
    end
    local file = io.open(path, "r")
    if file then file:close(); return true end
    return false
end

local function resolvePath(relativePath)
    if fileExists(relativePath) then return relativePath end
    return nil
end

local function projectApi(projectId)
    local project = PROJECTS[projectId]
    return project and rawget(_G, project.global_name) or nil
end

local function terminateProject(projectId, reason)
    local api = projectApi(projectId)
    if type(api) == "table" and type(api.terminate) == "function" then
        local ok, err = pcall(api.terminate, reason or "project_switch")
        if not ok then log("Terminate failed for " .. tostring(projectId) .. ": " .. tostring(err)) end
    end
end

local function terminateAllProjects(reason)
    terminateProject("helper", reason)
    Loader.active_project = nil
    Loader.selected_project = nil
    Loader.activation_pending = false
end

function Loader.isSelected(projectId)
    return Loader.online_session == true
        and Loader.selected_project == projectId
        and Loader.activation_pending == true
        and Loader.active_project == nil
end

local function destroyChooser()
    if Loader.window and Loader.window.destroy then pcall(function() Loader.window:destroy() end) end
    Loader.window = nil
end

local function createWidget(kind, parent, id, text, x, y, width, height)
    if not g_ui or type(g_ui.createWidget) ~= "function" then return nil end
    local ok, widget = pcall(function() return g_ui.createWidget(kind, parent) end)
    if not ok or not widget then return nil end
    if id and widget.setId then pcall(function() widget:setId(id) end) end
    if text and widget.setText then pcall(function() widget:setText(text) end) end
    if widget.breakAnchors then pcall(function() widget:breakAnchors() end) end
    if widget.addAnchor and AnchorLeft and AnchorTop then
        pcall(function()
            widget:addAnchor(AnchorLeft, "parent", AnchorLeft)
            widget:addAnchor(AnchorTop, "parent", AnchorTop)
        end)
    end
    if widget.setMarginLeft then pcall(function() widget:setMarginLeft(x or 0) end) end
    if widget.setMarginTop then pcall(function() widget:setMarginTop(y or 0) end) end
    if widget.resize then
        pcall(function() widget:resize(width or 120, height or 24) end)
    else
        if widget.setWidth then pcall(function() widget:setWidth(width or 120) end) end
        if widget.setHeight then pcall(function() widget:setHeight(height or 24) end) end
    end
    if kind == "Label" and widget.setPhantom then pcall(function() widget:setPhantom(true) end) end
    return widget
end

local function setColor(widget, color)
    if widget and widget.setColor then pcall(function() widget:setColor(color) end) end
end

local function setBackground(widget, color)
    if widget and widget.setBackgroundColor then pcall(function() widget:setBackgroundColor(color) end) end
end

local function loadProjectFile(projectId)
    local project = PROJECTS[projectId]
    local path = nil
    for _, candidate in ipairs(project and project.loader_paths or {}) do
        path = resolvePath(candidate)
        if path then break end
    end
    if not path then return false, "loader_not_found" end
    local ok, err = pcall(function() dofile(path) end)
    if not ok then return false, tostring(err) end
    local api = projectApi(projectId)
    if type(api) ~= "table" or type(project.activation) ~= "function" then
        return false, "project_api_missing"
    end
    local activationOk, activated, result = pcall(project.activation, api)
    if not activationOk or activated ~= true then
        return false, tostring(result or activated or "activation_rejected")
    end
    return true
end

function Loader.activate(projectId)
    if not PROJECTS[projectId] then return false, "unknown_project" end
    if not Loader.online_session then return false, "offline" end
    if Loader.activation_pending or Loader.active_project then return false, "project_already_selected" end

    destroyChooser()
    terminateAllProjects("before_selection")
    Loader.selected_project = projectId
    Loader.activation_pending = true

    local ok, err = loadProjectFile(projectId)
    Loader.activation_pending = false
    if not ok then
        terminateProject(projectId, "activation_failed")
        Loader.selected_project = nil
        log("Activation failed for " .. projectId .. ": " .. tostring(err))
        return false, err
    end

    Loader.active_project = projectId
    log(PROJECTS[projectId].label .. " active; no other CTOA project is packaged")
    return true
end

local function activateP14CaptureHelper()
    Loader.capture_activation_event = nil
    if not p14CaptureActivationRequested() then
        log("P14 capture activation rejected: required isolated flags are missing")
        return
    end
    local ok, reason = Loader.activate("helper")
    if not ok then
        log("P14 capture Helper activation failed: " .. tostring(reason))
    end
end

local function scheduleP14CaptureHelperActivation()
    if Loader.capture_activation_event then return end
    if type(scheduleEvent) == "function" then
        Loader.capture_activation_event = scheduleEvent(activateP14CaptureHelper, 600)
    else
        activateP14CaptureHelper()
    end
end

local function showChooser()
    if not Loader.online_session or Loader.active_project or Loader.window then return end
    local root = g_ui and g_ui.getRootWidget and g_ui.getRootWidget()
    if not root then log("Chooser UI unavailable"); return end

    local rootWidth = root.getWidth and root:getWidth() or 1024
    local rootHeight = root.getHeight and root:getHeight() or 768
    local width, height = 360, 156
    local left = math.floor((rootWidth - width) / 2)
    local top = math.floor((rootHeight - height) / 2.4)
    local window = createWidget("HeadlessWindow", root, "ctoaProjectChooser", "", left, top, width, height)
    if not window then return end
    Loader.window = window
    setBackground(window, "#262626")
    if window.setBorderColor then pcall(function() window:setBorderColor("#737373") end) end
    if window.setBorderWidth then pcall(function() window:setBorderWidth(1) end) end
    if window.setDraggable then pcall(function() window:setDraggable(true) end) end

    setBackground(createWidget("Label", window, "ctoaProjectHeader", "", 0, 0, width, 28), "#101010")
    setColor(createWidget("Label", window, "ctoaProjectTitle", "CTOA Loader " .. LOADER_VERSION, 12, 7, 250, 16), "#f0c56a")
    setColor(createWidget("Label", window, "ctoaProjectSubtitle", "Aktywuj Helper dla tej sesji:", 12, 38, 330, 16), "#d0d0d0")

    local helperButton = createWidget("Button", window, "ctoaChooseHelper", "CTOA HELPER", 12, 62, 336, 52)
    if helperButton then
        setBackground(helperButton, "#303040")
        helperButton.onClick = function() Loader.activate("helper") end
    end
    setColor(createWidget("Label", window, "ctoaHelperHint", "Main project P8-P16", 26, 95, 250, 14), "#a0a0c0")
    setColor(createWidget("Label", window, "ctoaSessionHint", "Selection resets each session; Helper starts disarmed.", 12, 126, 336, 14), "#888888")
    if window.show then pcall(function() window:show() end) end
    if window.raise then pcall(function() window:raise() end) end
end

local function onGameStart()
    terminateAllProjects("new_login")
    Loader.online_session = true
    removeScheduled(Loader.show_event)
    Loader.show_event = nil
    removeScheduled(Loader.capture_activation_event)
    Loader.capture_activation_event = nil
    if p14CaptureActivationRequested() then
        scheduleP14CaptureHelperActivation()
        return
    end
    if type(scheduleEvent) == "function" then
        Loader.show_event = scheduleEvent(function()
            Loader.show_event = nil
            showChooser()
        end, 600)
    else
        showChooser()
    end
end

local function onGameEnd()
    Loader.online_session = false
    removeScheduled(Loader.show_event)
    Loader.show_event = nil
    removeScheduled(Loader.capture_activation_event)
    Loader.capture_activation_event = nil
    destroyChooser()
    terminateAllProjects("logout")
    log("Session closed; project selection cleared")
end

function Loader.init()
    if Loader.initialized then return true end
    Loader.initialized = true
    terminateAllProjects("neutral_loader_start")
    if type(connect) == "function" and g_game then
        Loader.callbacks = {onGameStart = onGameStart, onGameEnd = onGameEnd}
        connect(g_game, Loader.callbacks)
    end
    if g_game and type(g_game.isOnline) == "function" then
        local ok, online = pcall(function() return g_game.isOnline() end)
        if ok and online then onGameStart() end
    end
    log("Neutral loader ready; no project loaded")
    return true
end

function Loader.terminate()
    onGameEnd()
    if Loader.callbacks and type(disconnect) == "function" and g_game then
        pcall(function() disconnect(g_game, Loader.callbacks) end)
    end
    Loader.callbacks = nil
    Loader.initialized = false
    log("Neutral loader terminated")
    return true
end

_G.CTOA_CHOOSER = Loader
return Loader
