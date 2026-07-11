from pathlib import Path

from scripts.ops import ctoa_helper_ui_preview as preview
from scripts.ops import ctoa_otprofile_builder as profile_builder


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
LOADER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_otclient_loader.lua"
MODULE_REGISTRY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modules.lua"
UI_HELPERS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_ui.lua"
CLIENT_REPORTER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_client_reporter.lua"
DIAGNOSTICS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_diagnostics.lua"
HOTKEYS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_hotkeys.lua"
MODAL = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modal.lua"
ROUTE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_route.lua"
TARGETING = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_targeting.lua"
COMBAT_RUNTIME = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua"
CAVEBOT_RUNTIME = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_cavebot_runtime.lua"
LOOT_RUNTIME = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_loot_runtime.lua"
TIMER_RUNTIME = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_timer_runtime.lua"
RECOVERY_RUNTIME = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_recovery_runtime.lua"
PROFILE_SCHEMA = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_schema.lua"
OPERATOR_SUMMARY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_operator_summary.lua"
PLANNER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_planner.lua"
RUNTIME_POLICY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_runtime_policy.lua"
DISPATCH_GUARD = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_dispatch_guard.lua"
PLAN_QUEUE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_plan_queue.lua"
RUNTIME_READINESS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_runtime_readiness.lua"
FEATURE_FLAGS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_feature_flags.lua"
HUD = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_hud.lua"
CONDITIONS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_conditions.lua"
EQUIPMENT = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_equipment.lua"
SCRIPTING = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_scripting.lua"
HEAL_FRIEND = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_heal_friend.lua"
SMOKE_SCRIPT = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


EXPECTED_SECTIONS = {
    "overview",
    "healing",
    "heal_friend",
    "conditions",
    "hunting",
    "hunting_targeting",
    "hunting_magic",
    "cavebot",
    "equipment",
    "tools",
    "tools_helper",
    "tools_pvp",
    "tools_hud",
    "tools_timer",
    "tools_diag",
    "scripting",
    "profile",
    "ui",
}


SMOKE_ALL_TABS = {
    "overview",
    "healing",
    "heal_friend",
    "conditions",
    "hunting",
    "hunting_magic",
    "cavebot",
    "equipment",
    "tools",
    "tools_pvp",
    "tools_hud",
    "tools_timer",
    "tools_diag",
    "scripting",
    "profile",
    "ui",
}


def test_zerobot_shell_sections_render_without_layout_issues():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    window = preview.extract_window(source)
    widgets = preview.extract_widgets(source + "\n" + ui_module)

    sections = {widget.section for widget in widgets}
    assert EXPECTED_SECTIONS <= sections
    assert preview.validate(window, widgets) == []


def test_helper_redesign_keeps_operator_layout_contract():
    source = HELPER.read_text(encoding="utf-8")

    assert "sidebar_w = 122" in source
    assert "window_w = 690" in source
    assert "content_w = 466" in source
    assert "value_w = 138" in source
    assert '"CTOA Helper"' in source
    assert '"Operator workspace"' in source
    assert 'HELPPER_VERSION .. " | " .. displayProfileName()' not in source
    assert 'HELPER_VERSION .. " | " .. displayProfileName()' in source
    assert 'local titleLabel = createWidget("Label", window, "ctoaWindowTitleLabel", "CTOA Helper"' in source
    assert 'local innerTitleText = createWidget("Label", window, "ctoaInnerTitleText", "Operator workspace"' in source
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    assert 'function styleTabState(widget, active)' not in source
    assert 'function styleSubtabState(widget, active)' not in source
    assert "for _, nav in ipairs(Helper.sidebar_tabs or {}) do" in source
    assert 'styleUi("styleTabState", Helper.widgets[nav.key], active, UI_STYLE, AlignLeft)' in source
    assert 'styleUi("styleTabRail", Helper.widgets[nav.key .. "_rail"], active, UI_STYLE)' in source
    assert 'styleUi("styleSubtabState", Helper.widgets.tools_helper_tab, Helper.active_tools_tab == "helper", UI_STYLE, AlignCenter)' in source
    assert "style.surface_raised or style.row_fill_active" in ui_module
    assert "style.edge_highlight or style.border_active" in ui_module
    assert 'background = active and style.row_fill_active or style.content_fill' in ui_module
    assert "function Ui.styleSectionBody" in ui_module
    assert "function Ui.stylePriorityBadge" in ui_module
    assert "function Ui.styleWindowFrame" in ui_module
    assert 'theme_preset = "graphite"' in source
    assert 'UI_THEMES[presetId or "graphite"] or UI_THEMES.graphite' in source
    graphite = source[source.index("graphite = {"):source.index("amber = {")]
    assert 'accent = "#f0c36a"' in graphite
    assert 'border_active = "#f0c36a"' in graphite
    assert "function Ui.sidebarGeometry" in ui_module
    assert "local dense = count > 10" in ui_module
    assert "local rowHeight = dense and 18 or 21" in ui_module
    assert "local gap = dense and 1 or 2" in ui_module
    assert 'mode = dense and "dense_overflow" or "standard"' in ui_module
    assert 'utility_divider_y = utilityIndex and' in ui_module
    assert 'createWidget("Button", window, "ctoaHelperEnabled"' in source
    assert 'styleUi("styleRuntimeBadge"' in source
    assert 'role = "destructive"' in ui_module
    assert 'role = "primary"' in ui_module
    assert "fontScale = 1.10" in ui_module
    assert "fontScale = 0.98" in ui_module
    assert 'action == "theme_set"' in source
    assert 'status("Smoke theme visible: " .. tostring(theme))' in source
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    assert '{"action", "tab", "subtab", "theme"}' in diagnostics
    assert "theme = theme" in diagnostics
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert '"ThemeSnapshotMatrix"' in smoke
    assert "function Invoke-ThemeSnapshotMatrix" in smoke
    assert '$themes = @("classic", "graphite", "amber", "emerald")' in smoke
    assert '$tabs = @("overview", "profile", "cavebot", "healing", "ui")' in smoke
    assert 'expected_count = 20' in smoke
    assert 'restored_theme = "graphite"' in smoke


def test_helper_client_reporter_is_passive_packaged_and_safe_by_default():
    source = HELPER.read_text(encoding="utf-8")
    reporter = CLIENT_REPORTER.read_text(encoding="utf-8")
    loader = boot_graph_source()
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_CLIENT_REPORTER")' in source
    assert 'rawget(_G, "g_app")' in source
    assert 'rawget(_G, "g_game")' in source
    assert 'rawget(_G, "g_resources")' in source
    assert "function Reporter.detect" in reporter
    assert "function Reporter.snapshot" in reporter
    assert "function Reporter.resolvePath" in reporter
    assert "function Reporter.writeSnapshot" in reporter
    assert 'local SCHEMA_VERSION = "ctoa-client-capabilities-v1"' in reporter
    assert "schema_version = SCHEMA_VERSION" in reporter
    assert 'protocol_status = protocolReady and "ready" or "pending_protocol_source"' in reporter
    assert "safe_fallback = not protocolReady" in reporter
    assert "runtime_actions = false" in reporter
    assert "g_game.attack" not in reporter
    assert "autoWalk" not in reporter
    assert "castSpell" not in reporter
    assert boot_graph_has_module(loader, "ctoa_helper_client_reporter", "ctoa_helper_client_reporter.lua")
    assert '"ctoa_helper_client_reporter.lua"' in smoke
    package_files = smoke[
        smoke.index("function Get-DevPackageFiles"):
        smoke.index("function Get-LiveRootFallbackFiles")
    ]
    assert '"mods/ctoa_otclient/ctoa_helper_client_reporter.lua"' in package_files


def test_helper_redesign_phase3_summaries_are_wired():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")

    assert "refreshOperatorSummaries" in source
    for helper in [
        "titleSummaryText",
        "healingSummaryText",
        "healFriendSummaryText",
        "conditionsSummaryText",
        "equipmentSummaryText",
        "scriptingSummaryText",
        "targetingSummaryText",
        "magicSummaryText",
        "toolsSummaryText",
        "profileSummaryText",
        "uiSummaryText",
    ]:
        assert helper not in source
    assert "function addSummaryStrip" not in source
    assert "function addFooterStrip" not in source
    assert "add_summary_strip = function(parent, id, text, x, y, width, section)" in source
    assert "add_footer_strip = function(parent, id, text, x, y, width, section)" in source

    for widget_id in [
        "ctoaHealingSummary",
    ]:
        assert widget_id in ui_module
    assert 'styleUi("renderHealingPanel"' in source
    assert "ctoaHuntingTargetingSummary" in ui_module
    assert "ctoaHuntingMagicSummary" in ui_module
    assert "ctoaProfileSummary" in ui_module
    assert "ctoaToolsSummary" in ui_module
    assert "ctoaUiSummary" in ui_module

    assert "Helper.widgets.title_state = titleState" in source
    assert 'title = moduleValue(externalOperatorSummary, "bridgeText", "title", OPERATOR_SUMMARY_BRIDGES)' in source
    assert 'styleUi("refreshOperatorSummaries"' in source
    assert "function Ui.refreshOperatorSummaries" in ui_module


def test_helper_has_module_lane_registry_for_all_runtime_surfaces():
    source = HELPER.read_text(encoding="utf-8")
    registry = MODULE_REGISTRY.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")

    assert "local MODULE_LANES = {}" in source
    assert "local MODULE_LANE_INDEX = {}" in source
    assert "local function rebuildModuleLaneIndex(lanes)" in source
    assert 'rawget(_G, "CTOA_HELPER_MODULES")' in source
    assert "_G.CTOA_HELPER_MODULES = Registry" in registry
    assert "function Registry.getModuleLanes()" in registry
    assert "function Registry.getShortLabels()" in registry
    assert "function Registry.laneEnabled" in registry
    assert "function Registry.registrySummary" in registry
    assert "function Registry.readinessTag" in registry
    assert "function Registry.readinessRow" in registry
    assert "owns_lane_readiness = true" in registry
    assert "owns_lane_enabled = true" in registry
    assert "owns_lane_runtime_text = true" in registry
    assert "owns_registry_summary = true" in registry
    assert "owns_readiness_row = true" in registry
    assert "local function moduleRegistrySummaryText()" not in source
    assert "local function moduleLaneEnabled(lane)" not in source
    assert "local function moduleLaneRuntimeText(lane)" not in source
    assert 'moduleValue(externalModules, "registrySummary", MODULE_LANES, HELPER_CONFIG)' in source
    assert "local function moduleReadinessRowText(stage)" not in source
    assert 'local MODULE_SHORT_LABELS = moduleValue(externalModules, "getShortLabels") or {}' in source
    assert 'moduleValue(externalModules, "readinessRow", "implemented", MODULE_LANES, HELPER_CONFIG, MODULE_SHORT_LABELS)' in source
    assert 'moduleValue(externalModules, "readinessRow", "prototype", MODULE_LANES, HELPER_CONFIG, MODULE_SHORT_LABELS)' in source
    assert "pcall(externalModules.registrySummary" not in source
    assert "pcall(externalModules.readinessTag" not in source
    assert "pcall(externalModules.readinessRow" not in source
    assert "local function moduleLaneReadinessTag" not in source
    assert "module_summary = moduleSummaryText" in source
    assert 'ctx.set_metric_text(widgets.overview_modules, "Modules", tostring(data.module_summary or "modules unavailable"), width)' in ui_module
    assert '"ctoaOverviewReadinessRuntime", "Runtime: pending"' in ui_module
    assert '"ctoaOverviewReadinessPrototype", "Prototype: pending"' in ui_module
    assert "runtime_readiness = runtimeReadinessText" in source
    assert "prototype_readiness = prototypeReadinessText" in source

    registry_start = source.index("local MODULE_LANES = {}")
    registry_end = source.index("local Helper = {")
    registry_source = source[registry_start:registry_end]

    for lane_id, profile_key, stage in [
        ("healing", "healing", "implemented"),
        ("combat", "tools", "implemented"),
        ("cavebot", "tools", "implemented"),
        ("loot", "tools", "implemented"),
        ("timer", "tools", "implemented"),
        ("heal_friend", "heal_friend", "prototype"),
        ("conditions", "conditions", "prototype"),
        ("equipment", "equipment", "prototype"),
        ("scripting", "scripting", "prototype"),
    ]:
        assert f'id = "{lane_id}"' not in registry_source
        assert f'profile_key = "{profile_key}"' not in registry_source
        assert f'stage = "{stage}"' not in registry_source
        assert f'id = "{lane_id}"' in registry
        assert f'profile_key = "{profile_key}"' in registry
        assert f'stage = "{stage}"' in registry

    assert "gate =" not in registry_source
    assert "getModuleLanes" in registry_source
    assert 'if lane.id == "healing" then' not in registry_source
    assert 'if lane.id == "combat" then' not in registry_source
    assert 'if lane.id == "cavebot" then' not in registry_source
    assert 'HELPER_CONFIG.tools.auto_attack == true' not in registry_source
    assert 'return tostring(implemented) .. " impl / " .. tostring(prototypes) .. " proto / " .. tostring(armed) .. " armed"' not in registry_source
    assert 'parts[#parts + 1] = tostring(label) .. ":" .. moduleLaneReadinessTag(lane)' not in registry_source
    assert 'return table.concat(parts, "  ")' not in registry_source
    assert "runtime_enabled = true" not in registry_source
    assert "castSpell(" not in registry_source
    assert "sendActionbarSlot(" not in registry_source
    assert "g_game.talk" not in registry_source

    assert "runtime_enabled = true" not in registry
    assert "castSpell(" not in registry
    assert "sendActionbarSlot(" not in registry
    assert "g_game.talk" not in registry


def test_helper_ui_primitives_are_guarded_and_packaged():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_UI")' in source
    assert 'rawget(_G, "CTOA_HELPER_UI")' in ui_module
    assert "_G.CTOA_HELPER_UI = Ui" in ui_module
    for function_name in [
        "shortText",
        "fitText",
        "setWidgetText",
        "styleWidget",
        "setWidgetChecked",
        "getWidgetChecked",
        "showWidget",
        "createWidget",
        "styleTabState",
        "styleTabRail",
        "styleRaisedCard",
        "styleInsetValue",
        "styleGroupedFrame",
        "styleSubtabState",
        "styleMiniButton",
            "styleActionButton",
            "styleRuntimeBadge",
        "styleRuleCard",
        "styleMetricRow",
        "styleMetricLabel",
        "styleMetricValue",
            "styleSettingState",
            "styleStateValue",
        "styleSectionBody",
        "styleTableHeader",
        "styleTableHeaderLabel",
        "styleFooterStrip",
        "styleFooterStripLabel",
        "styleSummaryStrip",
        "styleSummaryStripLabel",
        "styleSectionBandTitle",
        "styleSectionBandSubtitle",
        "styleSectionBandDivider",
        "stylePriorityBadge",
        "styleLabel",
        "styleWindowRoot",
        "styleWindowFrame",
        "styleWindowTitleLabel",
        "styleToggleButton",
        "styleCheckBox",
        "styleSidebarCard",
        "styleOverviewAvatarFrame",
        "styleOverviewAvatar",
        "styleOverviewAvatarName",
        "styleOverviewHpBar",
        "styleOverviewEquipSlot",
        "styleControlName",
        "settingRowGeometry",
        "metricCardGeometry",
        "metricTextPlan",
        "profileFieldGeometry",
        "vectorStepGeometry",
        "addSettingRow",
        "addToggleSettingRow",
        "sectionBodyGeometry",
            "sidebarTabs",
            "sidebarGeometry",
        "huntingSubtabs",
        "subtabContentY",
        "toolsSubtabs",
        "toolsTableHeaders",
        "cavebotDelayChoices",
        "cavebotReachChoices",
        "msText",
        "cavebotActionSpecs",
        "refreshOperatorSummaries",
        "renderOverviewPanel",
        "updateOverviewStats",
        "renderConditionsPanel",
        "renderEquipmentPanel",
        "renderCavebotPanel",
        "renderEnginePanel",
        "renderHealingPanel",
        "renderHealFriendPanel",
        "renderHuntingPanel",
        "renderProfilePanel",
        "renderScriptingPanel",
        "renderToolsPanel",
        "contract",
    ]:
        assert f"function Ui.{function_name}" in ui_module
    assert "local shortText = externalUi and externalUi.shortText or tostring" in source
    assert "local fitText = externalUi and externalUi.fitText or shortText" in source
    assert "pcall(externalUi.shortText" not in source
    assert "pcall(externalUi.fitText" not in source
    for ui_adapter in ["setWidgetText", "setWidgetChecked", "getWidgetChecked", "showWidget"]:
        assert f"externalUi and externalUi.{ui_adapter}" in source
    assert 'moduleValue(externalUi, "createWidget", kind, parent, id, text, x, y, width, height)' in source
    for ui_direct_pcall in [
        "pcall(externalUi.setWidgetText",
        "pcall(externalUi.styleWidget",
        "pcall(externalUi.setWidgetChecked",
        "pcall(externalUi.getWidgetChecked",
        "pcall(externalUi.showWidget",
        "pcall(externalUi.createWidget",
    ]:
        assert ui_direct_pcall not in source
    for delegated_style in [
        "styleTabState",
        "styleSubtabState",
        "styleMiniButton",
        "styleActionButton",
        "styleRuleCard",
        "styleMetricRow",
        "styleMetricLabel",
        "styleMetricValue",
        "styleSettingState",
        "styleSectionBody",
        "styleTableHeader",
        "styleTableHeaderLabel",
        "styleFooterStrip",
        "styleFooterStripLabel",
        "styleSummaryStrip",
        "styleSummaryStripLabel",
        "styleSectionBandTitle",
        "styleSectionBandSubtitle",
        "styleSectionBandDivider",
        "stylePriorityBadge",
        "styleLabel",
        "styleWindowRoot",
        "styleWindowFrame",
        "styleWindowTitleLabel",
        "styleToggleButton",
        "styleCheckBox",
        "styleSidebarCard",
        "styleOverviewAvatarFrame",
        "styleOverviewAvatar",
        "styleOverviewAvatarName",
        "styleOverviewHpBar",
        "styleOverviewEquipSlot",
        "styleControlName",
    ]:
        assert (
            f'styleUi("{delegated_style}"' in source
            or f'ctx.style_ui("{delegated_style}"' in ui_module
            or f"Ui.{delegated_style}(" in ui_module
        )
    assert "function Ui.styleProfileField" in ui_module
    assert "function Ui.styleVectorRow" in ui_module
    assert "function Ui.configureLayout" in ui_module
    assert 'moduleValue(externalUi, "configureLayout", UI_LAYOUT, HELPER_CONFIG.compact_mode == true)' in source
    assert "pcall(externalUi.configureLayout" not in source
    assert "UI_LAYOUT.overview_tab_y = 116" not in source
    assert "UI_LAYOUT.overview_tab_y = 120" not in source
    for delegated_geometry in [
        "settingRowGeometry",
        "metricCardGeometry",
        "metricTextPlan",
        "profileFieldGeometry",
        "sectionBodyGeometry",
    ]:
        assert f'styleUi("{delegated_geometry}"' in source or f"Ui.{delegated_geometry}(" in ui_module
    for delegated_builder in [
        "addProfileCycleRow",
        "addProfileStepRow",
        "addVectorStepRow",
    ]:
        assert f'styleUi("{delegated_builder}"' in source
        assert f"function Ui.{delegated_builder}" in ui_module
    assert "owns_row_geometry = true" in ui_module
    assert "owns_metric_card_geometry = true" in ui_module
    assert "owns_metric_text_plan = true" in ui_module
    assert "owns_setting_row_builders = true" in ui_module
    assert "owns_interactive_row_builders = true" in ui_module
    assert "owns_section_scaffold = true" in ui_module
    assert "function addSectionScaffold" in source
    assert "function addSectionBand" not in source
    assert "add_section_band = function(parent, id, title, subtitle, x, y, width, section)" in source
    for delegated_metadata in [
        "sidebarTabs",
        "subtabContentY",
    ]:
        assert f'styleUi("{delegated_metadata}"' in source
    assert 'styleUi("renderHuntingPanel"' in source
    assert 'styleUi("renderOverviewPanel"' in source
    assert "externalUi.updateOverviewStats" in source
    assert 'styleUi("renderToolsPanel"' in source
    assert 'styleUi("renderEnginePanel"' in source
    assert 'styleUi("renderHealingPanel"' in source
    assert 'styleUi("renderHealFriendPanel"' in source
    assert 'styleUi("renderConditionsPanel"' in source
    assert 'styleUi("renderEquipmentPanel"' in source
    assert 'styleUi("renderScriptingPanel"' in source
    assert 'ctx.add_subtab_buttons(window, "huntingSubtabs", "hunting", panelX, bodyY, panelW)' in ui_module
    assert 'ctx.add_subtab_buttons(window, "toolsSubtabs", "tools", panelX, bodyY, panelW)' in ui_module
    assert 'styleUi("renderProfilePanel"' in source
    assert "owns_tab_metadata = true" in ui_module
    assert "owns_subtab_content_metadata = true" in ui_module
    assert "owns_cavebot_action_metadata = true" in ui_module
    assert "owns_operator_summary_refresh = true" in ui_module
    assert "owns_overview_panel_renderer = true" in ui_module
    assert "owns_overview_stats_update = true" in ui_module
    assert "owns_cavebot_panel_renderer = true" in ui_module
    assert "owns_engine_panel_renderer = true" in ui_module
    assert "owns_healing_panel_renderer = true" in ui_module
    assert "owns_heal_friend_panel_renderer = true" in ui_module
    assert "owns_conditions_panel_renderer = true" in ui_module
    assert "owns_hunting_panel_renderer = true" in ui_module
    assert "owns_equipment_panel_renderer = true" in ui_module
    assert "owns_profile_panel_renderer = true" in ui_module
    assert "owns_scripting_panel_renderer = true" in ui_module
    assert "owns_tools_panel_renderer = true" in ui_module
    assert "function addSubtabButtons" not in source
    assert "add_subtab_buttons = function(parent, provider, section, panelX, bodyY, panelW)" in source
    assert "function addTableHeader" not in source
    assert "function addTableHeaders" not in source
    assert "function addToggleContentRows" not in source
    assert "panel_renderer_base.add_table_headers = function(parent, specs)" in source
    assert "add_toggle_content_rows = function(parent, specs, x, width)" in source
    assert 'ctx.add_toggle_content_rows(window, {' in ui_module
    direct_style_calls = [
        line
        for line in source.splitlines()
        if "styleWidget(" in line and not line.strip().startswith("function styleWidget")
    ]
    assert direct_style_calls == []
    assert "runtime_actions = false" in ui_module
    assert "executes_plans = false" in ui_module
    assert "casts = false" in ui_module
    assert "talks = false" in ui_module
    assert "attacks = false" in ui_module
    assert "walks = false" in ui_module
    assert "uses_items = false" in ui_module
    assert "owns_nav_style = true" in ui_module
    assert "owns_subtab_style = true" in ui_module
    assert "owns_button_style = true" in ui_module
    assert "owns_rule_card_style = true" in ui_module
    assert "owns_metric_style = true" in ui_module
    assert "owns_setting_state_style = true" in ui_module
    assert "owns_profile_field_style = true" in ui_module
    assert "owns_vector_row_style = true" in ui_module
    assert "owns_section_style = true" in ui_module
    assert "owns_strip_style = true" in ui_module
    assert "owns_badge_style = true" in ui_module
    assert "owns_label_style = true" in ui_module
    assert "owns_window_chrome_style = true" in ui_module
    assert "owns_toggle_style = true" in ui_module
    assert "owns_checkbox_style = true" in ui_module
    assert "owns_sidebar_card_style = true" in ui_module
    assert "owns_overview_avatar_style = true" in ui_module
    assert "owns_control_name_style = true" in ui_module
    assert "owns_layout_modes = true" in ui_module
    assert "owns_row_geometry = true" in ui_module
    assert "owns_tab_metadata = true" in ui_module
    assert "g_game" not in ui_module
    assert "autoWalk" not in ui_module
    assert "castSpell" not in ui_module
    assert "sendActionbarSlot" not in ui_module
    assert boot_graph_has_module(loader, "ctoa_helper_ui", "ctoa_helper_ui.lua")
    assert "ctoa_helper_ui.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_ui.lua' in script


def test_helper_diagnostics_domain_is_passive_and_wired():
    source = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_DIAGNOSTICS")' in source
    assert "_G.CTOA_HELPER_DIAGNOSTICS = Diagnostics" in diagnostics
    assert "function Diagnostics.appendLog" in diagnostics
    assert "function Diagnostics.exportPath" in diagnostics
    assert "function Diagnostics.boolText" in diagnostics
    assert "function Diagnostics.posText" in diagnostics
    assert "function Diagnostics.hasApi" in diagnostics
    assert "function Diagnostics.apiText" in diagnostics
    assert "function Diagnostics.valueText" in diagnostics
    assert "function Diagnostics.apiSnapshotText" in diagnostics
    assert "function Diagnostics.apiProbeSnapshot" in diagnostics
    assert "function Diagnostics.apiProbeText" in diagnostics
    assert "function Diagnostics.probeDeferredPlan" in diagnostics
    assert "function Diagnostics.magicApiProbeText" in diagnostics
    assert "function Diagnostics.featureFlagsText" in diagnostics
    assert "function Diagnostics.smokeCommandExists" in diagnostics
    assert "function Diagnostics.parseSmokeCommandText" in diagnostics
    assert "function Diagnostics.smokeCommandTarget" in diagnostics
    assert "function Diagnostics.smokeTabStatusText" in diagnostics
    assert "function Diagnostics.smokeCommandStatusText" in diagnostics
    assert "function Diagnostics.bufferText" in diagnostics
    assert "function Diagnostics.movementText" in diagnostics
    assert "function Diagnostics.magicLootText" in diagnostics
    assert "function Diagnostics.snapshotUiRows" in diagnostics
    assert "function Diagnostics.tableCount" in diagnostics
    assert "function Diagnostics.firstTableValue" in diagnostics
    assert "function Diagnostics.recordSnapshot" in diagnostics
    assert "function Diagnostics.exportBuffer" in diagnostics
    assert "function Diagnostics.contract" in diagnostics
    assert "owns_bool_text = true" in diagnostics
    assert "owns_pos_text = true" in diagnostics
    assert "owns_api_text = true" in diagnostics
    assert "owns_value_text = true" in diagnostics
    assert "owns_api_snapshot_text = true" in diagnostics
    assert "owns_api_probe_snapshot = true" in diagnostics
    assert "owns_api_probe_text = true" in diagnostics
    assert "owns_probe_deferred_plan = true" in diagnostics
    assert "owns_magic_api_probe_text = true" in diagnostics
    assert "owns_feature_flags_text = true" in diagnostics
    assert "owns_buffer_text = true" in diagnostics
    assert "owns_movement_text = true" in diagnostics
    assert "owns_magic_loot_text = true" in diagnostics
    assert "owns_snapshot_ui_rows = true" in diagnostics
    assert "owns_table_count = true" in diagnostics
    assert "owns_first_table_value = true" in diagnostics
    assert "owns_smoke_command_exists = true" in diagnostics
    assert "owns_smoke_command_parse = true" in diagnostics
    assert "owns_smoke_command_target = true" in diagnostics
    assert "owns_smoke_status_text = true" in diagnostics
    assert "owns_smoke_command_status_text = true" in diagnostics
    assert "owns_record_snapshot = true" in diagnostics
    assert "owns_export_buffer = true" in diagnostics
    assert 'moduleValue(externalDiagnostics, "apiSnapshotText"' in source
    assert 'moduleValue(externalDiagnostics, "featureFlagsText"' in source
    assert 'function diagnosticsText(functionName, fallback, ...)' not in source
    assert 'diagnosticsText("boolText"' not in source
    assert 'diagnosticsText("posText"' not in source
    assert 'moduleValue(externalDiagnostics, "boolText"' in source
    assert 'moduleValue(externalDiagnostics, "posText"' in source
    assert 'moduleValue(externalDiagnostics, "movementText"' in source
    assert 'moduleValue(externalDiagnostics, "magicLootText"' in source
    assert 'moduleValue(externalDiagnostics, "snapshotUiRows"' in source
    assert 'moduleValue(externalDiagnostics, "tableCount"' in source
    assert 'moduleValue(externalDiagnostics, "firstTableValue"' in source
    assert 'moduleValue(externalDiagnostics, "recordSnapshot"' in source
    assert 'moduleValue(externalDiagnostics, "exportBuffer"' in source
    assert 'moduleValue(externalDiagnostics, "apiProbeText"' in source
    assert 'moduleValue(externalDiagnostics, "probeDeferredPlan"' in source
    assert 'moduleValue(externalDiagnostics, "magicApiProbeText"' in source
    assert 'moduleValue(externalDiagnostics, "smokeCommandExists"' in source
    assert 'moduleValue(externalDiagnostics, "parseSmokeCommandText"' in source
    assert 'moduleValue(externalDiagnostics, "smokeCommandTarget"' in source
    assert 'moduleValue(externalDiagnostics, "smokeCommandStatusText"' in source
    assert "local function parseSmokeCommandText" not in source
    assert "local function smokeCommandTarget" not in source
    assert "function smokeCommandStatusText(event, data, fallback)" not in source
    assert "Diagnostics module unavailable | API pending" in source
    assert "Diagnostics module unavailable | flags pending" in source
    assert "Diagnostics module unavailable | export gated" in source
    assert "Diagnostics module unavailable | movement pending" in source
    assert "Diagnostics module unavailable | magic/loot pending" in source
    assert "ctoa_diag_export.lua" in diagnostics
    assert "castSpell(" not in diagnostics
    assert "sendActionbarSlot(" not in diagnostics
    assert "g_game.talk" not in diagnostics
    assert "g_game.attack" not in diagnostics
    assert "g_game.move" not in diagnostics
    assert "function apiSnapshotText()" not in source
    assert "function featureFlagsText()" not in source
    assert "function diagnosticsBufferText()" not in source
    assert "function diagnosticsMovementText()" not in source
    assert "function diagnosticsMagicLootText()" not in source
    diagnostics_slice = source[source.index("function refreshApiSnapshotUi()"):source.index("function runApiProbe(reason)")]
    assert "api = function()" not in diagnostics_slice
    assert "flags = function()" not in diagnostics_slice
    assert "movement = function()" not in diagnostics_slice
    assert "magic_loot = function()" not in diagnostics_slice
    assert "buffer = function()" not in diagnostics_slice
    assert "Generated by ctoa_native_helper.lua diagnostics export" not in diagnostics_slice
    assert "table.remove(buffer, 1)" not in diagnostics_slice
    assert '"Flags: diag="' not in diagnostics_slice
    assert '"Move: " .. tostring(snapshot.movement' not in diagnostics_slice
    assert '"Magic: " .. tostring(snapshot.magic' not in diagnostics_slice
    assert "for _, row in ipairs(rows) do" in diagnostics_slice
    assert "Helper.widgets.tools_diag_magic:setText" not in diagnostics_slice
    assert 'moduleValue(externalDiagnostics, "apiProbeSnapshot"' in source
    assert "API probe detail:" in diagnostics
    assert "API probe detail:" not in source
    smoke_slice = source[source.index("local function readSmokeCommand"):source.index("local function applySmokeCommand")]
    assert 'escaped .. "%s*=%s*"' not in smoke_slice
    assert 'action == "magic_probe"' not in smoke_slice
    assert 'action == "api_probe"' not in smoke_slice
    apply_smoke_slice = source[source.index("local function applySmokeCommand"):source.index("local function processSmokeCommand")]
    assert "externalDiagnostics.smokeTabStatusText" not in apply_smoke_slice
    assert "externalDiagnostics.smokeCommandBlockedText" not in apply_smoke_slice
    assert '"Smoke command blocked: " .. blocked' not in apply_smoke_slice
    process_smoke_slice = source[source.index("local function processSmokeCommand"):source.index("flushUiPrefsSave = function")]
    assert "externalDiagnostics.smokeCommandFailedText" not in process_smoke_slice
    assert '"Smoke command failed: " .. tostring(command)' not in process_smoke_slice
    formatter_slice = source[source.index("function setCavebotStatus(text)"):source.index("function refreshApiSnapshotUi()")]
    assert "function boolText(value)" not in formatter_slice
    assert "function posText(pos)" not in formatter_slice
    assert "function tableCount(value)" not in formatter_slice
    assert "function firstTableValue(value)" not in formatter_slice
    assert 'return value and "yes" or "no"' not in formatter_slice
    assert 'return tostring(pos.x) .. "," .. tostring(pos.y)' not in formatter_slice
    assert "for _ in pairs(value)" not in formatter_slice
    assert "for _, item in pairs(value)" not in formatter_slice


def test_placeholder_modules_have_visible_preview_rows():
    source = HELPER.read_text(encoding="utf-8")

    assert 'addPlaceholderModule(window, "heal_friend"' not in source
    assert 'addPlaceholderModule(window, "conditions"' not in source
    assert 'addPlaceholderModule(window, "equipment"' not in source
    assert 'addPlaceholderModule(window, "scripting"' not in source


def test_heal_friend_is_profiled_module_lane_without_runtime_casting():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    heal_friend = HEAL_FRIEND.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "heal_friend = {" in source
    assert 'rawget(_G, "CTOA_HELPER_HEAL_FRIEND")' in source
    assert "_G.CTOA_HELPER_HEAL_FRIEND = HealFriend" in heal_friend
    assert "function HealFriend.whitelistContainsName" in heal_friend
    assert "function HealFriend.scan" in heal_friend
    assert "function HealFriend.observe" in heal_friend
    assert "function HealFriend.plan" in heal_friend
    assert "function HealFriend.statusText" in heal_friend
    assert "function HealFriend.decisionText" in heal_friend
    assert "function HealFriend.summary" in heal_friend
    assert "function HealFriend.contract" in heal_friend
    assert "owns_whitelist_matching = true" in heal_friend
    assert "owns_scan = true" in heal_friend
    assert "owns_status_text = true" in heal_friend
    assert "owns_decision_text = true" in heal_friend
    assert "owns_summary_text = true" in heal_friend
    assert 'mode = "passive"' in heal_friend
    assert "runtime_actions = false" in heal_friend
    assert "casts = false" in heal_friend
    assert "talks = false" in heal_friend
    assert "requires_whitelist = true" in heal_friend
    assert "requires_sandbox_attach = true" in heal_friend
    assert 'next_action = "plan_sio"' in heal_friend
    assert "healFriendSummaryText = function()" not in source
    assert 'heal_friend = moduleValue(externalOperatorSummary, "bridgeText", "healFriend", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "local function maybeObserveHealFriend(now)" in source
    assert "local function scanHealFriendCandidates()" not in source
    assert "local function whitelistContainsName(" not in source
    assert "Heal Friend module unavailable | runtime gated" in source
    assert 'styleUi("renderHealFriendPanel"' in source
    assert '"ctoaHealFriendPlanner", "Planner"' in ui_module
    assert '"ctoaHealFriendObserveParty", "Observe party"' in ui_module
    assert '"ctoaHealFriendSpell", "Sio spell"' in ui_module
    assert '"ctoaHealFriendThreshold", "Friend HP"' in ui_module
    assert "Status: read-only pending; no sio cast until sandbox whitelist smoke passes" in ui_module
    assert "HELPER_CONFIG.heal_friend.runtime_enabled = false" in source
    assert "heal_friend = HELPER_CONFIG.heal_friend" not in source
    persistence = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_persistence.lua").read_text(encoding="utf-8")
    assert "heal_friend = {" in persistence
    assert "\n    heal_friend = {" in profile
    assert "friend_scan_range = 7" in profile
    assert "observed_count = 0" in profile
    assert "runtime_enabled = false" in profile
    assert 'castSpell(HELPER_CONFIG.heal_friend.sio_spell)' not in source
    assert "g_game.talk(HELPER_CONFIG.heal_friend.sio_spell)" not in source
    assert "castSpell(" not in heal_friend
    assert "sendActionbarSlot(" not in heal_friend
    assert "g_game.talk" not in heal_friend
    assert "g_game.attack" not in heal_friend
    observer_start = source.index("local function maybeObserveHealFriend(now)")
    observer_end = source.index("local function buildTargetCandidate")
    observer_source = source[observer_start:observer_end]
    assert "getSpectatorsInRange" in observer_source
    assert 'moduleValue(externalHealFriend, "observe", healFriend, now, {' in observer_source
    assert "pcall(externalHealFriend.observe" not in observer_source
    assert 'moduleValue(externalHealFriend, "statusText", healFriend)' in observer_source
    assert "externalHealFriend.statusText" not in observer_source
    assert "pcall(externalHealFriend.statusText" not in observer_source
    assert "whitelistContainsName" not in observer_source
    assert "heal friend module unavailable" in observer_source
    assert "castSpell(" not in observer_source
    assert "sendActionbarSlot(" not in observer_source
    assert "g_game.talk" not in observer_source


def test_coming_soon_sidebar_tabs_are_non_interactive():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")

    assert 'Helper.configureComingSoonTab(Helper.widgets.scripting_tab, "Scripting")' not in source
    assert "Helper.configureComingSoonTab = function" not in source
    assert "Scripting (Wkrótce / Coming Soon)" not in source
    assert "function Ui.styleInactiveNav" not in ui_module
    assert "function Ui.styleDisabledNav" not in ui_module
    assert "widget.onClick = nil" not in source
    assert "widget.onMouseRelease = nil" not in source
    assert 'bindClick(Helper.widgets.scripting_tab, function() switchTab("scripting") end)' in source


def test_conditions_is_read_only_profiled_module_lane():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    conditions_module = CONDITIONS.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "conditions = {" in source
    assert 'rawget(_G, "CTOA_HELPER_CONDITIONS")' in source
    assert "_G.CTOA_HELPER_CONDITIONS" in conditions_module
    assert "function Conditions.flagText" in conditions_module
    assert "function Conditions.snapshot" in conditions_module
    assert "function Conditions.apiProbe" in conditions_module
    assert "function Conditions.observe" in conditions_module
    assert "function Conditions.plan" in conditions_module
    assert "function Conditions.summary" in conditions_module
    assert "function Conditions.contract" in conditions_module
    assert 'action = "plan_paralyze_recovery"' in conditions_module
    assert 'reason = "runtime_gated"' in conditions_module
    assert 'reason = "protection_zone"' in conditions_module
    assert 'mode = "passive"' in conditions_module
    assert "owns_flag_text = true" in conditions_module
    assert "owns_snapshot = true" in conditions_module
    assert "owns_api_probe = true" in conditions_module
    assert "owns_observer = true" in conditions_module
    assert "owns_summary_text = true" in conditions_module
    assert "runtime_actions = false" in conditions_module
    assert "casts = false" in conditions_module
    assert "uses_items = false" in conditions_module
    assert "requires_sandbox_attach = true" in conditions_module
    assert "conditionsSummaryText = function()" not in source
    assert 'conditions = moduleValue(externalOperatorSummary, "bridgeText", "conditions", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "function maybeSampleConditions(now)" in source
    assert "local function buildConditionsApiProbeSnapshot()" not in source
    assert "local function buildConditionSnapshot()" not in source
    assert "local function conditionFlagText(" not in source
    assert "Conditions module unavailable | read-only" in source
    assert 'styleUi("renderConditionsPanel"' in source
    assert '"ctoaConditionsObserver", label = "Observer"' in ui_module
    assert '"ctoaConditionsStates", label = "Read states"' in ui_module
    assert '"ctoaConditionsApiProbe", "API probe"' in ui_module
    assert '"ctoaConditionsStatus", "Status: read-only pending"' in ui_module
    assert 'bindClick(Helper.widgets.conditions_tab, function() switchTab("conditions") end)' in source
    assert 'Helper.configureComingSoonTab(Helper.widgets.conditions_tab, "Conditions")' not in source
    assert "HELPER_CONFIG.conditions.runtime_enabled = false" in source
    assert "api_probe_enabled = true" in source
    assert "\n    conditions = {" in profile
    assert "api_probe_enabled = true" in profile
    assert 'api_probe_status = "pending"' in profile
    assert "runtime_enabled = false" in profile
    conditions_source = conditions_module
    assert "player.hasState=" in conditions_source
    assert "player.getStates=" in conditions_source
    assert "state.manaShield=" in conditions_source
    observer_start = source.index("function maybeSampleConditions(now)")
    observer_end = source.index("function maybeSampleEquipment(now)")
    observer_source = source[observer_start:observer_end]
    assert 'moduleValue(externalConditions, "observe", conditions, now, {' in observer_source
    assert "pcall(externalConditions.observe" not in observer_source
    assert "conditions module unavailable" in observer_source
    assert "player.hasState=" not in observer_source
    assert "castSpell(" not in conditions_source
    assert "sendActionbarSlot(" not in conditions_source
    assert "g_game.talk" not in conditions_source
    assert "g_game.attack" not in conditions_source


def test_hud_domain_is_passive_and_packaged():
    source = HELPER.read_text(encoding="utf-8")
    hud_module = HUD.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_HUD")' in source
    assert "_G.CTOA_HELPER_HUD" in hud_module
    assert "function Hud.startText" in hud_module
    assert "function Hud.disarmedText" in hud_module
    assert "function Hud.state" in hud_module
    assert "function Hud.visibilityText" in hud_module
    assert "function Hud.runtimeText" in hud_module
    assert "function Hud.uiSummary" in hud_module
    assert "function Hud.operatorSummary" in hud_module
    assert "function Hud.contract" in hud_module
    assert 'mode = "passive"' in hud_module
    assert "owns_start_text = true" in hud_module
    assert "owns_disarmed_text = true" in hud_module
    assert "owns_position = true" in hud_module
    assert "owns_runtime_text = true" in hud_module
    assert "owns_ui_summary = true" in hud_module
    assert "owns_operator_summary = true" in hud_module
    assert "runtime_actions = false" in hud_module
    assert "HUD module unavailable | starting" in source
    assert "HUD module unavailable | runtime disarmed" in source
    assert "HUD module unavailable | runtime gated" in source
    assert 'OPERATOR_SUMMARY_BRIDGES.ui' in source
    assert 'ui = moduleValue(externalOperatorSummary, "bridgeText", "ui", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "hud = externalHud" in source
    ui_summary_start = source.index("OPERATOR_SUMMARY_BRIDGES.ui")
    ui_summary_end = source.index("refreshOperatorSummaries = function()")
    ui_summary_source = source[ui_summary_start:ui_summary_end]
    assert '"Hotkey " .. hotkeyDisplayText(HELPER_CONFIG.hotkey)' not in ui_summary_source
    assert '" | Compact " .. onOffText(HELPER_CONFIG.compact_mode == true)' not in ui_summary_source
    assert '" | Theme " .. themePresetText(HELPER_CONFIG.theme_preset or "classic")' not in ui_summary_source
    assert "externalHud.uiSummary" not in ui_summary_source
    hud_slice = source[source.index("local function throttledRuntimeStatus("):source.index("local setWidgetText =")]
    assert "local function hudText(functionName, fallback, options)" not in source
    assert "local function hudStartText()" not in source
    assert "local function hudDisarmedText()" not in source
    assert "local function hudPosition()" not in source
    assert "local function hudRuntimeText(" not in source
    assert 'moduleValue(externalHud, "runtimeText", {' in source
    assert 'moduleValue(externalHud, "disarmedText")' in source
    assert 'moduleValue(externalHud, "startText")' in source
    assert "ZeroBot | starting" not in hud_slice
    assert "ZeroBot | runtime disarmed" not in hud_slice
    assert '"ZeroBot " .. HELPER_VERSION' not in hud_slice
    assert "ZeroBot | starting" in hud_module
    assert "ZeroBot | runtime disarmed" in hud_module
    assert '"ZeroBot " .. version' in hud_module
    assert "createWidget(" not in hud_module
    assert "showWidget(" not in hud_module
    assert "castSpell(" not in hud_module
    assert "g_game.talk" not in hud_module
    assert "g_game.attack" not in hud_module
    assert boot_graph_has_module(loader, "ctoa_helper_hud", "ctoa_helper_hud.lua")
    assert "ctoa_helper_hud.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_hud.lua' in script


def test_hotkeys_domain_is_passive_and_packaged():
    source = HELPER.read_text(encoding="utf-8")
    hotkeys_module = HOTKEYS.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_HOTKEYS")' in source
    assert "_G.CTOA_HELPER_HOTKEYS" in hotkeys_module
    assert "function Hotkeys.normalizeKeyName" in hotkeys_module
    assert "function Hotkeys.parse" in hotkeys_module
    assert "function Hotkeys.normalize" in hotkeys_module
    assert "function Hotkeys.isAllowed" in hotkeys_module
    assert "function Hotkeys.bindingDecision" in hotkeys_module
    assert "function Hotkeys.display" in hotkeys_module
    assert "function Hotkeys.actionbarSlotText" in hotkeys_module
    assert "function Hotkeys.contract" in hotkeys_module
    assert "owns_actionbar_slot_text = true" in hotkeys_module
    assert "owns_binding_decision = true" in hotkeys_module
    assert 'reason = "not_allowed"' in hotkeys_module
    assert 'reason = previous == parsed.normalized and "unchanged" or "changed"' in hotkeys_module
    assert 'reason = "multiple_keys"' in hotkeys_module
    assert 'reason = "missing_key"' in hotkeys_module
    assert 'reason = "reserved_key"' in hotkeys_module
    assert "binds_keys = false" in hotkeys_module
    assert "sends_keys = false" in hotkeys_module
    assert "runtime_actions = false" in hotkeys_module
    assert "local function normalizeHelperHotkey" in source
    assert "local function hotkeyValue" not in source
    assert "local function hotkeyBindingDecision" in source
    assert 'moduleValue(externalHotkeys, "bindingDecision", value, currentValue, allowed)' in source
    assert "local function hotkeyDisplayText" not in source
    assert 'moduleValue(externalHotkeys, "normalize", value)' in source
    assert "hotkey_display_text = externalHotkeys and externalHotkeys.display or tostring" in source
    assert '"actionbar " .. tostring(slot)' in hotkeys_module
    assert "local decision = hotkeyBindingDecision(hotkey, Helper.bound_hotkey or HELPER_CONFIG.hotkey)" in source
    assert "decision.allowed ~= true or decision.normalized == \"\"" in source
    assert "g_keyboard" not in hotkeys_module
    assert "bindKeyDown" not in hotkeys_module
    assert "unbindKeyDown" not in hotkeys_module
    assert "pressKey" not in hotkeys_module
    assert "g_game.talk" not in hotkeys_module
    assert "castSpell(" not in hotkeys_module
    assert "createWidget(" not in hotkeys_module
    assert boot_graph_has_module(loader, "ctoa_helper_hotkeys", "ctoa_helper_hotkeys.lua")
    assert "ctoa_helper_hotkeys.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_hotkeys.lua' in script


def test_modal_domain_is_passive_and_guards_destructive_actions():
    source = HELPER.read_text(encoding="utf-8")
    modal_module = MODAL.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_MODAL")' in source
    assert "_G.CTOA_HELPER_MODAL" in modal_module
    assert "function Modal.request" in modal_module
    assert "function Modal.confirm" in modal_module
    assert "function Modal.cancel" in modal_module
    assert "function Modal.isExpired" in modal_module
    assert "function Modal.decision" in modal_module
    assert "function Modal.decisionText" in modal_module
    assert "function Modal.isPending" in modal_module
    assert "function Modal.statusText" in modal_module
    assert "function Modal.buttonText" in modal_module
    assert "function Modal.contract" in modal_module
    assert "live_shortcuts = false" in modal_module
    assert "runtime_actions = false" in modal_module
    assert "owns_decision_text = true" in modal_module
    assert "confirmation_required" in modal_module
    assert "promote_live" in modal_module
    assert "local function modalValue" not in source
    assert "local function modalStatusText" not in source
    assert "pcall(externalModal[functionName]" not in source
    assert 'moduleValue(externalModal, "request", action, context, now, ttlMs)' in source
    assert 'moduleValue(externalModal, "isPending", Helper.pending_confirm, "cavebot_delete", helperNowMs())' in source
    assert 'moduleValue(externalModal, "statusText", Helper.pending_confirm)' in source
    assert "pending_confirm = nil" in source
    assert 'moduleValue(externalRoute, "deleteRequest"' in source
    assert 'modalRequest("cavebot_delete", request.label, request.timeout_ms)' in source
    assert 'deleteCurrentCavebotWaypoint(command.confirm == true)' in source
    assert 'applyCavebotEditorAction("delete")' in source
    assert "createWidget(" not in modal_module
    assert "showWidget(" not in modal_module
    assert "g_ui" not in modal_module
    assert "g_keyboard" not in modal_module
    assert "g_game.talk" not in modal_module
    assert "castSpell(" not in modal_module
    assert "PromoteLiveCtoa" not in modal_module
    assert boot_graph_has_module(loader, "ctoa_helper_modal", "ctoa_helper_modal.lua")
    assert "ctoa_helper_modal.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_modal.lua' in script


def test_route_domain_is_passive_and_packaged():
    source = HELPER.read_text(encoding="utf-8")
    route_module = ROUTE.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_ROUTE")' in source
    assert "_G.CTOA_HELPER_ROUTE" in route_module
    assert "function Route.position" in route_module
    assert "function Route.label" in route_module
    assert "function Route.posKey" in route_module
    assert "function Route.add" in route_module
    assert "function Route.select" in route_module
    assert "function Route.delete" in route_module
    assert "function Route.move" in route_module
    assert "function Route.editorAction" in route_module
    assert "function Route.retryStatus" in route_module
    assert "function Route.retryBlocked" in route_module
    assert "function Route.progress" in route_module
    assert "function Route.activeTarget" in route_module
    assert "function Route.stats" in route_module
    assert "function Route.selectedSummary" in route_module
    assert "function Route.uiState" in route_module
    assert "function Route.deleteRequest" in route_module
    assert "function Route.contract" in route_module
    assert 'mode = "passive"' in route_module
    assert "owns_editor_state = true" in route_module
    assert "owns_editor_action = true" in route_module
    assert "owns_position_key = true" in route_module
    assert "owns_progress_state = true" in route_module
    assert "owns_target_selection = true" in route_module
    assert "runtime_actions = false" in route_module
    assert "movement_enabled = false" in route_module
    assert "pathfinding = false" in route_module
    assert "local function moduleValue(module, functionName, ...)" in source
    assert 'moduleValue(externalRoute, "editorAction"' in source
    assert 'moduleValue(externalRoute, "posKey"' in source
    assert 'moduleValue(externalRoute, "progress"' in source
    assert 'moduleValue(externalRoute, "activeTarget"' in source
    assert 'moduleValue(externalRoute, "retryBlocked"' in source
    assert 'moduleValue(externalRoute, "uiState"' in source
    assert 'moduleValue(externalRoute, "deleteRequest"' in source
    assert 'moduleValue(externalRoute, "retryStatus", tools)' in source
    assert "local function routeRetryStatus" not in source
    assert "local function getWaypointPosition" not in source
    assert "local function waypointLabel" not in source
    assert "local x = tonumber(waypoint.x)" not in source
    assert "return \"retry \" .. tostring(tools and tools.cavebot_retry_attempts or 0)" not in source
    assert 'modalRequest("cavebot_delete", label, 4500)' not in source
    editor_slice = source[source.index("local function applyCavebotEditorAction"):source.index("function resetCavebotMovementState")]
    assert 'moduleValue(externalRoute, "editorAction"' in editor_slice
    assert "externalRoute.add" not in editor_slice
    assert "externalRoute.clear" not in editor_slice
    assert "externalRoute.select" not in editor_slice
    assert "externalRoute.delete(" not in editor_slice
    assert "externalRoute.move" not in editor_slice
    pos_key_slice = source[source.index("function posKey(pos)"):source.index("function hasApi(owner, methodName)")]
    assert 'moduleValue(externalRoute, "posKey", pos)' in pos_key_slice
    assert "autoWalk" not in route_module
    assert "findPath" not in route_module
    assert "g_map" not in route_module
    assert "g_game" not in route_module
    assert "g_ui" not in route_module
    assert "createWidget(" not in route_module
    assert "castSpell(" not in route_module
    assert boot_graph_has_module(loader, "ctoa_helper_route", "ctoa_helper_route.lua")
    assert "ctoa_helper_route.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_route.lua' in script


def test_targeting_domain_is_passive_and_packaged():
    source = HELPER.read_text(encoding="utf-8")
    targeting_module = TARGETING.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_TARGETING")' in source
    assert "_G.CTOA_HELPER_TARGETING" in targeting_module
    assert "function Targeting.normalizedName" in targeting_module
    assert "function Targeting.isIgnoredName" in targeting_module
    assert "function Targeting.hasBlockingNpcIcon" in targeting_module
    assert "function Targeting.isFriendlySummonName" in targeting_module
    assert "function Targeting.isFriendlySummonCandidate" in targeting_module
    assert "function Targeting.creatureTypeDecision" in targeting_module
    assert "function Targeting.priorityRank" in targeting_module
    assert "function Targeting.scoreCandidate" in targeting_module
    assert "function Targeting.bestCandidate" in targeting_module
    assert "function Targeting.decision" in targeting_module
    assert "function Targeting.summary" in targeting_module
    assert "function Targeting.configSummary" in targeting_module
    assert "function Targeting.contract" in targeting_module
    assert "owns_best_candidate = true" in targeting_module
    assert "owns_creature_type_decision = true" in targeting_module
    assert "owns_npc_icon_guard = true" in targeting_module
    assert "owns_friendly_summon_guard = true" in targeting_module
    assert 'mode = "passive"' in targeting_module
    assert "owns_config_summary = true" in targeting_module
    assert "owns_targeting_summary_text = true" in targeting_module
    assert "runtime_actions = false" in targeting_module
    assert "attacks = false" in targeting_module
    assert "casts = false" in targeting_module
    assert "creature_scan = false" in targeting_module
    assert 'reason = "ignored_name"' in targeting_module
    assert 'reason = "friendly_summon"' in targeting_module
    assert 'moduleValue(externalTargeting, "scoreCandidate", candidate, tools)' in source
    assert 'moduleValue(externalTargeting, "bestCandidate", candidates, tools)' in source
    assert "pcall(externalTargeting.bestCandidate, candidates, tools)" not in source
    assert "externalTargeting.creatureTypeDecision" in source
    assert 'moduleValue(externalTargeting, "normalizedName", creature)' in source
    assert 'moduleValue(externalTargeting, "isIgnoredName", name, HELPER_CONFIG.tools.ignored_names or {})' in source
    assert 'moduleValue(externalTargeting, "isFriendlySummonName", name, HELPER_CONFIG.tools)' in source
    assert "pcall(externalTargeting.normalizedName" not in source
    assert "pcall(externalTargeting.isIgnoredName" not in source
    assert "pcall(externalTargeting.isFriendlySummonName" not in source
    assert 'OPERATOR_SUMMARY_BRIDGES.targeting' in source
    assert 'targeting = moduleValue(externalOperatorSummary, "bridgeText", "targeting", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "targeting = externalTargeting" in source
    targeting_summary_start = source.index("OPERATOR_SUMMARY_BRIDGES.targeting")
    targeting_summary_end = source.index("OPERATOR_SUMMARY_BRIDGES.magic")
    targeting_summary_source = source[targeting_summary_start:targeting_summary_end]
    assert '"Targeting " .. onOffText(tools.auto_attack)' not in targeting_summary_source
    assert '" | Chase " .. onOffText(tools.chase == true)' not in targeting_summary_source
    assert '" | PZ guard " .. onOffText(tools.pause_in_pz == true)' not in targeting_summary_source
    assert "g_game.attack(target)" in source
    assert "g_game.attack" not in targeting_module
    assert "g_game" not in targeting_module
    assert "g_map" not in targeting_module
    assert "castSpell(" not in targeting_module
    assert "sendActionbarSlot" not in targeting_module
    assert "createWidget(" not in targeting_module
    assert boot_graph_has_module(loader, "ctoa_helper_targeting", "ctoa_helper_targeting.lua")
    assert "ctoa_helper_targeting.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_targeting.lua' in script


def test_combat_runtime_adapter_is_passive_and_packaged():
    adapter = COMBAT_RUNTIME.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    source = HELPER.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_COMBAT_RUNTIME" in adapter
    assert "function CombatRuntime.plan" in adapter
    assert "function CombatRuntime.summary" in adapter
    assert "function CombatRuntime.adapterSummary" in adapter
    assert "function CombatRuntime.magicSummary" in adapter
    assert "function CombatRuntime.msLeftText" in adapter
    assert "function CombatRuntime.runeReady" in adapter
    assert "function CombatRuntime.rotationSpellRows" in adapter
    assert "function CombatRuntime.spellReadiness" in adapter
    assert "function CombatRuntime.rotationSpell" in adapter
    assert "function CombatRuntime.offensiveAction" in adapter
    assert "function CombatRuntime.actionStatusText" in adapter
    assert "function CombatRuntime.targetingStatusText" in adapter
    assert "function CombatRuntime.nextActionText" in adapter
    assert "function CombatRuntime.decisionStateSummary" in adapter
    assert "function CombatRuntime.contract" in adapter
    assert 'mode = "passive"' in adapter
    assert "owns_adapter_summary = true" in adapter
    assert "owns_magic_summary = true" in adapter
    assert "owns_magic_summary_text = true" in adapter
    assert "owns_cooldown_text = true" in adapter
    assert "owns_rune_ready = true" in adapter
    assert "owns_rotation_spell_rows = true" in adapter
    assert "owns_spell_readiness = true" in adapter
    assert "owns_rotation_spell_selection = true" in adapter
    assert "owns_offensive_action_selection = true" in adapter
    assert "owns_action_status_text = true" in adapter
    assert "owns_targeting_status_text = true" in adapter
    assert "owns_next_action_text = true" in adapter
    assert "owns_decision_state_summary = true" in adapter
    assert "runtime_actions = false" in adapter
    assert "scans_creatures = false" in adapter
    assert "attacks = false" in adapter
    assert "casts = false" in adapter
    assert "uses_items = false" in adapter
    assert "requires_target_scorer = true" in adapter
    assert "g_game" not in adapter
    assert "g_map" not in adapter
    assert "g_ui" not in adapter
    assert "castSpell(" not in adapter
    assert "sendActionbarSlot" not in adapter
    assert "createWidget(" not in adapter
    assert "getSpectatorsInRange" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_combat_runtime", "ctoa_helper_combat_runtime.lua")
    assert "ctoa_helper_combat_runtime.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_combat_runtime.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_COMBAT_RUNTIME")' in source
    assert "local function moduleValue(module, functionName, ...)" in source
    assert "local function combatRuntimeAdapterSummary(tools, target)" not in source
    assert 'moduleValue(externalCombatRuntime, "decisionStateSummary", tools' in source
    combat_summary_source = source[source.index("local function combatDecisionStateText"):source.index("function readPlayerVitals")]
    assert "pcall(externalCombatRuntime.plan, tools, context, targetDecision)" not in combat_summary_source
    assert "pcall(externalCombatRuntime.summary, plan)" not in combat_summary_source
    assert "adapter_text = adapterText" not in combat_summary_source
    assert 'OPERATOR_SUMMARY_BRIDGES.magic' in source
    assert 'magic = moduleValue(externalOperatorSummary, "bridgeText", "magic", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "combatRuntime = externalCombatRuntime" in source
    assert 'moduleValue(externalCombatRuntime, "msLeftText"' not in source
    assert 'moduleValue(externalCombatRuntime, "runeReady", tools' in source
    assert 'moduleValue(externalCombatRuntime, "rotationSpellRows", tools.rotation_spells' in source
    assert 'moduleValue(externalCombatRuntime, "spellReadiness", spells' in source
    assert 'moduleValue(externalCombatRuntime, "rotationSpell", spells' in source
    assert 'moduleValue(externalCombatRuntime, "offensiveAction", tools' in source
    assert "local combatRuntimeText" in source
    assert "combatRuntimeText = function(functionName, eventOrAction, data, fallback)" in source
    assert source.index("local combatRuntimeText") < source.index("local function retargetSafeMonster")
    assert source.index("local combatRuntimeText") < source.index("clearUnsafeCurrentTarget = function")
    assert "moduleValue(externalCombatRuntime, functionName, eventOrAction, data or {})" in source
    assert "local function combatActionStatusText" not in source
    assert "local function combatTargetingStatusText" not in source
    assert 'moduleValue(externalCombatRuntime, "nextActionText", action, fallback)' in source
    assert 'moduleValue(externalCombatRuntime, "decisionState", {' not in source
    magic_summary_start = source.index("OPERATOR_SUMMARY_BRIDGES.magic")
    magic_summary_end = source.index("OPERATOR_SUMMARY_BRIDGES.tools")
    magic_summary_source = source[magic_summary_start:magic_summary_end]
    assert "local runeSlot = actionbarSlotText(resolveActionbarSlot" not in magic_summary_source
    assert '"Rotation " .. onOffText(tools.spell_rotation)' not in magic_summary_source
    assert '" | Rune " .. onOffText(tools.rune_enabled)' not in magic_summary_source
    assert "adapter_text = adapterText" not in source
    assert "local function msLeftText(untilMs, now)" not in source
    assert '"Targeting blocked: " .. blocked' not in source
    assert '"Targeting: no valid monster"' not in source
    assert '"Targeting blocked: friendly summon/familiar"' not in source
    assert '"Auto target: " .. tostring(targetName)' not in source
    assert '"Target cleared: " .. tostring(reason)' not in source
    assert '"Targeting blocked: " .. tostring(item.reason' in adapter
    assert '"Auto target: " .. tostring(item.name' in adapter
    assert '"Target cleared: " .. tostring(item.reason' in adapter


def test_cavebot_runtime_adapter_is_passive_and_packaged():
    adapter = CAVEBOT_RUNTIME.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    source = HELPER.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_CAVEBOT_RUNTIME" in adapter
    assert "function CavebotRuntime.plan" in adapter
    assert "function CavebotRuntime.summary" in adapter
    assert "function CavebotRuntime.decisionText" in adapter
    assert "function CavebotRuntime.adapterSummary" in adapter
    assert "function CavebotRuntime.adapterStatusText" in adapter
    assert "function CavebotRuntime.adapterStatusSummary" in adapter
    assert "function CavebotRuntime.movementCapability" in adapter
    assert "function CavebotRuntime.probeSnapshot" in adapter
    assert "function CavebotRuntime.probeSummary" in adapter
    assert "function CavebotRuntime.probeReport" in adapter
    assert "function CavebotRuntime.pathText" in adapter
    assert "function CavebotRuntime.movementBlockedReason" in adapter
    assert "function CavebotRuntime.walkPreflight" in adapter
    assert "function CavebotRuntime.testWalkPlan" in adapter
    assert "function CavebotRuntime.walkingStatus" in adapter
    assert "function CavebotRuntime.retryDecision" in adapter
    assert "function CavebotRuntime.statusText" in adapter
    assert "function CavebotRuntime.traceText" in adapter
    assert 'kind == "movement_reset"' in adapter
    assert '"Cavebot movement state reset: " .. tostring(item.reason or "manual")' in adapter
    assert "function CavebotRuntime.contract" in adapter
    assert "owns_decision_text = true" in adapter
    assert "owns_adapter_summary = true" in adapter
    assert "owns_adapter_status_text = true" in adapter
    assert "owns_adapter_status_summary = true" in adapter
    assert "owns_movement_capability = true" in adapter
    assert "owns_probe_snapshot = true" in adapter
    assert "owns_probe_summary_text = true" in adapter
    assert "owns_path_text = true" in adapter
    assert "owns_blocked_reason_text = true" in adapter
    assert "owns_walk_preflight = true" in adapter
    assert "owns_test_walk_plan = true" in adapter
    assert "owns_walking_status = true" in adapter
    assert "owns_retry_decision = true" in adapter
    assert "owns_status_text = true" in adapter
    assert "owns_trace_text = true" in adapter
    assert 'mode = "passive"' in adapter
    assert "runtime_actions = false" in adapter
    assert "movement_enabled = false" in adapter
    assert "pathfinding = false" in adapter
    assert "uses_map = false" in adapter
    assert "walks = false" in adapter
    assert "requires_route_engine = true" in adapter
    assert "requires_sandbox_attach = true" in adapter
    assert "autoWalk" not in adapter
    assert "findPath" not in adapter
    assert "g_map" not in adapter
    assert "g_game" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_cavebot_runtime", "ctoa_helper_cavebot_runtime.lua")
    assert "ctoa_helper_cavebot_runtime.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_cavebot_runtime.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_CAVEBOT_RUNTIME")' in source
    assert "local function moduleValue(module, functionName, ...)" in source
    assert "function cavebotRuntimeMovementCapability(player)" in source
    assert 'moduleValue(externalCavebotRuntime, "adapterStatusSummary"' in source
    assert 'moduleValue(externalCavebotRuntime, "adapterSummary"' not in source
    assert "function cavebotRuntimeAdapterStatusText(adapterText)" not in source
    assert '"adapter " .. adapterText' not in source
    assert '"adapter " .. text' in adapter
    adapter_summary_source = source[source.index('moduleValue(externalCavebotRuntime, "adapterStatusSummary"'):source.index('if type(adapterStatus) == "string"')]
    assert "pcall(externalCavebotRuntime.decisionText, plan)" not in adapter_summary_source
    assert "externalCavebotRuntime.plan" not in adapter_summary_source
    assert 'moduleValue(externalCavebotRuntime, "movementCapability"' in source
    assert 'moduleValue(externalCavebotRuntime, "probeReport"' in source
    probe_wrapper_source = source[source.index('moduleValue(externalCavebotRuntime, "probeReport"'):source.index("function runMagicApiProbe")]
    assert "externalCavebotRuntime.probeSnapshot" not in probe_wrapper_source
    assert "externalCavebotRuntime.probeSummary" not in probe_wrapper_source
    assert 'moduleValue(externalCavebotRuntime, "probeReport"' in probe_wrapper_source
    assert 'moduleValue(externalCavebotRuntime, "pathText"' in source
    assert "function cavebotRuntimePathText" not in source
    path_probe_source = source[source.index("function movementPathProbeText"):source.index("function cavebotMovementBlockedReason")]
    assert 'moduleValue(externalCavebotRuntime, "pathText"' in path_probe_source
    assert '"dirs=" .. tostring(#dirs)' not in path_probe_source
    assert '"non-table result=" .. tostring(dirs)' not in path_probe_source
    assert '"error:" .. tostring(dirs)' not in path_probe_source
    assert '"dirs=" .. tostring(data.dirs_count)' in adapter
    assert '"non-table result=" .. tostring(data.value)' in adapter
    assert 'moduleValue(externalCavebotRuntime, "movementBlockedReason"' in source
    assert 'moduleValue(externalCavebotRuntime, "walkPreflight"' in source
    assert 'moduleValue(externalCavebotRuntime, "testWalkPlan"' in source
    assert 'moduleValue(externalCavebotRuntime, "walkingStatus"' in source
    assert "function cavebotRuntimeWalkingStatus" not in source
    assert 'function cavebotRuntimeText(functionName, event, data, fallback)' in source
    assert 'moduleValue(externalCavebotRuntime, functionName, event, data or {})' in source
    assert "function cavebotRuntimeStatusText" not in source
    assert "function cavebotRuntimeTraceText" not in source
    assert 'cavebotRuntimeText("traceText", "movement_reset"' in source
    assert "CavebotRuntime.walkingStatus(item)" in adapter
    assert '"walking " .. tostring(label)' in adapter
    assert '"walking " .. tostring(item.label' not in adapter
    assert "Cavebot movement state reset:" not in source
    assert "Cavebot movement target=" not in source
    assert "Test walk target=" not in source
    assert "Test walk blocked" not in source
    assert "Cavebot movement disabled: retry budget reached" not in source
    assert "Cavebot movement disabled: walk failed retry budget" not in source
    assert "pcall(externalCavebotRuntime.summary, plan)" not in adapter_summary_source
    assert "setCavebotStatus(fitText(adapterStatus" in source


def test_loot_runtime_adapter_is_passive_and_packaged():
    adapter = LOOT_RUNTIME.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    source = HELPER.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_LOOT_RUNTIME" in adapter
    assert "function LootRuntime.plan" in adapter
    assert "function LootRuntime.summary" in adapter
    assert "function LootRuntime.adapterSummary" in adapter
    assert "function LootRuntime.contract" in adapter
    assert "owns_adapter_summary = true" in adapter
    assert 'mode = "passive"' in adapter
    assert "runtime_actions = false" in adapter
    assert "scans_containers = false" in adapter
    assert "opens_containers = false" in adapter
    assert "moves_items = false" in adapter
    assert "uses_items = false" in adapter
    assert "requires_experimental_flag = true" in adapter
    assert "requires_container_probe = true" in adapter
    assert "requires_sandbox_attach = true" in adapter
    assert "getContainers" not in adapter
    assert "getItems" not in adapter
    assert "g_game" not in adapter
    assert "g_map" not in adapter
    assert "move(" not in adapter
    assert "useWith" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_loot_runtime", "ctoa_helper_loot_runtime.lua")
    assert "ctoa_helper_loot_runtime.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_loot_runtime.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_LOOT_RUNTIME")' in source
    assert "function lootRuntimeAdapterSummary(tools, containers)" not in source
    assert 'moduleValue(externalLootRuntime, "adapterSummary"' in source
    assert "pcall(externalLootRuntime.adapterSummary" not in source
    assert "pcall(externalLootRuntime.plan, plannerTools, context, snapshot)" not in source
    assert "pcall(externalLootRuntime.summary, plan)" not in source
    assert '" adapter=" .. tostring(data.loot_adapter_text' in DIAGNOSTICS.read_text(encoding="utf-8")


def test_timer_runtime_adapter_is_passive_and_packaged():
    adapter = TIMER_RUNTIME.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_TIMER_RUNTIME" in adapter
    assert "function TimerRuntime.plan" in adapter
    assert "function TimerRuntime.summary" in adapter
    assert "function TimerRuntime.dispatch" in adapter
    assert "function TimerRuntime.contract" in adapter
    assert 'mode = "passive"' in adapter
    assert "owns_dispatch_decision = true" in adapter
    assert "runtime_actions = false" in adapter
    assert "talks = false" in adapter
    assert "casts = false" in adapter
    assert "evaluates = false" in adapter
    assert "loads_files = false" in adapter
    assert "requires_no_eval_gate = true" in adapter
    assert "requires_sandbox_attach = true" in adapter
    assert "g_game" not in adapter
    assert "castSpell(" not in adapter
    assert "loadstring" not in adapter
    assert "dofile" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_timer_runtime", "ctoa_helper_timer_runtime.lua")
    assert "ctoa_helper_timer_runtime.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_timer_runtime.lua' in script


def test_recovery_runtime_adapter_is_passive_and_consumed_by_shell():
    source = HELPER.read_text(encoding="utf-8")
    adapter = RECOVERY_RUNTIME.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_RECOVERY_RUNTIME" in adapter
    for function_name in [
        "normalizeVitals",
        "jitterThreshold",
        "selectHealingSpell",
        "potionStatusText",
        "spellStatusText",
        "actionGap",
        "summary",
        "contract",
    ]:
        assert f"function RecoveryRuntime.{function_name}" in adapter
    assert 'mode = "passive"' in adapter
    assert "owns_vitals_normalization = true" in adapter
    assert "owns_healing_spell_selection = true" in adapter
    assert "owns_recovery_status_text = true" in adapter
    assert "runtime_actions = false" in adapter
    assert "casts = false" in adapter
    assert "uses_items = false" in adapter
    assert "reads_otclient = false" in adapter
    assert "g_game" not in adapter
    assert "getLocalPlayer" not in adapter
    assert "castSpell" not in adapter
    assert "sendActionbarSlot" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_recovery_runtime", "ctoa_helper_recovery_runtime.lua")
    assert "ctoa_helper_recovery_runtime.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_recovery_runtime.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_RECOVERY_RUNTIME")' in source
    assert 'moduleValue(externalRecoveryRuntime, "normalizeVitals", snapshot)' in source
    assert 'moduleValue(externalRecoveryRuntime, "selectHealingSpell", healing, hp, nonce)' in source
    assert 'moduleValue(externalRecoveryRuntime, "potionStatusText"' in source
    assert 'moduleValue(externalRecoveryRuntime, "spellStatusText", spell, hp)' in source


def test_profile_schema_adapter_is_passive_and_packaged():
    adapter = PROFILE_SCHEMA.read_text(encoding="utf-8")
    persistence = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_persistence.lua").read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    source = HELPER.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_PROFILE_SCHEMA" in adapter
    assert "function ProfileSchema.requiredSections" in adapter
    assert "function ProfileSchema.sectionOrder" in adapter
    assert "function ProfileSchema.safeFalseKeys" in adapter
    assert "function ProfileSchema.optionList" in adapter
    assert "function ProfileSchema.rotationPresets" in adapter
    assert "function ProfileSchema.keyOrder" in adapter
    assert "function ProfileSchema.valueIndex" in adapter
    assert "function ProfileSchema.cycleValue" in adapter
    assert "function ProfileSchema.fieldGeometry" in adapter
    assert "function ProfileSchema.stepValue" in adapter
    assert "function ProfileSchema.mergeTable" in adapter
    assert "function ProfileSchema.serializeLua" in adapter
    assert "function ProfileSchema.currentVersion" in adapter
    assert "function ProfileSchema.currentSchema" in adapter
    assert "function ProfileSchema.profileVersion" in adapter
    assert "function ProfileSchema.migrationPlan" in adapter
    assert "function ProfileSchema.migrate" in adapter
    assert "function ProfileSchema.summary" in adapter
    assert "function ProfileSchema.profileSchemaSuffix" in adapter
    assert "function ProfileSchema.rotationPresetIds" in adapter
    assert "function ProfileSchema.rotationPresetLabel" in adapter
    assert "function ProfileSchema.rotationSummary" in adapter
    assert "function ProfileSchema.spellLabel" in adapter
    assert "function ProfileSchema.potionLabel" in adapter
    assert "function ProfileSchema.runeLabel" in adapter
    assert "function ProfileSchema.healFriendPriorityLabel" in adapter
    assert "function ProfileSchema.magicPriorityLabel" in adapter
    assert "function ProfileSchema.themePresetLabel" in adapter
    assert "function ProfileSchema.onOffLabel" in adapter
    assert "function ProfileSchema.autosaveLabel" in adapter
    assert "function ProfileSchema.titleSummary" in adapter
    assert "function ProfileSchema.healingSummary" in adapter
    assert "function ProfileSchema.profileSummary" in adapter
    assert "function ProfileSchema.contract" in adapter
    assert 'mode = "passive"' in adapter
    assert "owns_key_order_metadata = true" in adapter
    assert "owns_merge_table = true" in adapter
    assert "owns_lua_serializer = true" in adapter
    assert "owns_rotation_metadata = true" in adapter
    assert "owns_profile_labels = true" in adapter
    assert "owns_profile_summaries = true" in adapter
    assert "owns_title_summary = true" in adapter
    assert "owns_healing_summary = true" in adapter
    assert "owns_rotation_summary = true" in adapter
    assert "owns_versioned_migration_plan = true" in adapter
    assert "owns_safe_profile_migration = true" in adapter
    assert "runtime_actions = false" in adapter
    assert "loads_files = false" in adapter
    assert "saves_files = false" in adapter
    assert "migrates_files = false" in adapter
    assert "preserves_key_order = true" in adapter
    assert "requires_profile_audit = true" in adapter
    assert "requires_safe_boot_defaults = true" in adapter
    assert "g_resources" not in adapter
    assert "dofile" not in adapter
    assert "loadstring" not in adapter
    assert "write" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_profile_schema", "ctoa_helper_profile_schema.lua")
    assert boot_graph_has_module(loader, "ctoa_helper_profile_persistence", "ctoa_helper_profile_persistence.lua")
    assert "ctoa_helper_profile_schema.lua" in script
    assert "ctoa_helper_profile_persistence.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_profile_schema.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_profile_persistence.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_PROFILE_SCHEMA")' in source
    assert 'OPERATOR_SUMMARY_BRIDGES.profile' in source
    assert 'profile = moduleValue(externalOperatorSummary, "bridgeText", "profile", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "profileSchema = externalProfileSchema" in source
    assert "local function profileSchemaValue(functionName, fallback, ...)" in source
    assert "function profileSchemaText(functionName, fallback, ...)" not in source
    assert "local function profileSchemaTable(functionName, fallback, ...)" in source
    assert "moduleValue(externalProfileSchema, functionName" in source
    assert "function profileOptionList(key)" not in source
    assert 'profileSchemaTable("optionList", {}, key)' not in source
    assert 'profileSchemaValue("cycleValue", current, options, current, direction)' in source
    assert "local function profileValueIndex" not in source
    assert "function profileSchemaNumber(functionName, fallback, ...)" not in source
    assert "function profileFieldGeometry(x, width)" not in source
    assert 'profileSchemaTable("fieldGeometry", styleUi("profileFieldGeometry", x, width), x, width)' in source
    assert 'return geometry.label_width and geometry or nil' in source
    assert 'profileSchemaValue("stepValue", value, value, 0, minValue, maxValue)' in source
    assert 'if type(stepValue) == "number" then' in source
    assert "function Ui.addProfileStepRow" in UI_HELPERS.read_text(encoding="utf-8")
    assert 'local ROTATION_PRESETS = profileSchemaTable("rotationPresets", {})' in source
    assert 'moduleValue(externalProfileSchema, "mergeTable", base, override)' in source
    assert "pcall(externalProfileSchema.mergeTable" not in source
    assert 'moduleValue(externalProfileSchema, "serializeLua", value, rootKey, 0)' in source
    assert "pcall(externalProfileSchema.serializeLua" not in source
    assert 'rawget(_G, "CTOA_HELPER_PROFILE_PERSISTENCE")' in source
    assert "local function profilePersistenceValue(functionName, fallback, ...)" in source
    assert 'profilePersistenceTable("profileCandidates"' in source
    assert 'profilePersistenceTable("uiPrefsCandidates"' in source
    assert 'profilePersistenceValue("resolveSavePath"' in source
    assert 'profilePersistenceValue("saveText"' in source
    assert 'profilePersistenceTable("uiPrefsPlan"' in source
    assert 'profilePersistenceTable("dirtyState"' in source
    assert 'profilePersistenceValue("exportProfile"' in source
    assert 'profilePersistenceValue("exportUiPrefs"' in source
    assert "function ProfilePersistence.exportProfile" in persistence
    assert "function ProfilePersistence.exportUiPrefs" in persistence
    assert "function ProfilePersistence.uiPrefsPlan" in persistence
    assert "owns_ui_prefs_plan = true" in persistence
    assert "owns_export_ui_prefs = true" in persistence
    assert "owns_export_profile = true" in persistence
    assert "local function profileKeyOrder(key)" not in source
    assert "local PROFILE_KEY_ORDER = profileKeyOrder" not in source
    assert 'local PROFILE_KEY_ORDER = {"name"' not in source
    assert 'local TOOLS_KEY_ORDER = {' not in source
    assert "local function luaQuote(value)" not in source
    assert "local function serializeLua(value, indent, order)" not in source
    assert "local function isArrayTable(value)" not in source
    assert 'local SPELL_CHOICES = profileSchemaTable("optionList", {}, "spell")' in source
    assert "local SPELL_CHOICES = {" not in source
    assert '"rotationPresetIds"' in source
    assert 'profileSchemaTable("rotationPresetIds", {}, ROTATION_PRESETS)' in source
    assert '"rotationPresetLabel"' in source
    assert 'profileSchemaValue("rotationPresetLabel", fallback, ROTATION_PRESETS, value)' in source
    assert '"rotationSummary"' in source
    assert 'profileSchemaText(' not in source
    assert "externalProfileSchema.spellLabel" in source
    assert "local PROFILE_LABEL_BRIDGES = {" not in source
    assert 'spellText = (externalProfileSchema and externalProfileSchema.spellLabel) or tostring' in source
    assert 'potionText = (externalProfileSchema and externalProfileSchema.potionLabel) or tostring' in source
    assert 'runeText = (externalProfileSchema and externalProfileSchema.runeLabel) or tostring' in source
    assert 'local function profileLabelText(labelName, value)' not in source
    assert 'spellText = function(value) return profileLabelText("spell", value) end' not in source
    assert "externalProfileSchema.potionLabel" in source
    assert "externalProfileSchema.runeLabel" in source
    assert "externalProfileSchema.healFriendPriorityLabel" in source
    assert "externalProfileSchema.magicPriorityLabel" in source
    assert "externalProfileSchema.themePresetLabel" in source
    assert '"autosaveLabel"' in source
    assert 'profileSchemaValue("onOffLabel", fallback, value)' in source
    assert 'profileSchemaValue("autosaveLabel", fallback, {' in source
    summary_start = source.index("local OPERATOR_SUMMARY_BRIDGES = {")
    summary_end = source.index("refreshOperatorSummaries = function()")
    summary_source = source[summary_start:summary_end]
    assert 'profile = moduleValue(externalOperatorSummary, "bridgeText", "profile", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "pcall(externalOperatorSummary[functionName]" not in source
    assert 'HELPER_VERSION .. " | " .. displayProfileName() .. " | " .. autosaveText()' not in summary_source
    assert '" | HP spell " .. onOffText(healing.spell_enabled)' not in summary_source
    assert '" | Spell " .. spellText(healing.spell or "?")' not in summary_source
    assert '" | Rotation " .. tostring(tools.rotation_preset or "custom")' not in summary_source

    rotation_start = source.index("function rotationSummaryText()")
    rotation_end = source.index("Helper.findRotationSpell = function(words)")
    rotation_source = source[rotation_start:rotation_end]
    assert "local pieces = {}" not in rotation_source
    assert 'pieces[#pieces + 1] = "..."' not in rotation_source
    assert '"Rotation: " .. shortText(table.concat(pieces, " | "), 52)' not in rotation_source


def test_feature_flags_adapter_is_passive_and_consumed_by_tools_summary():
    adapter = FEATURE_FLAGS.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    source = HELPER.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_FEATURE_FLAGS" in adapter
    assert "function FeatureFlags.audit" in adapter
    assert "function FeatureFlags.summary" in adapter
    assert "function FeatureFlags.toolsSummary" in adapter
    assert "function FeatureFlags.contract" in adapter
    assert 'mode = "passive"' in adapter
    assert "owns_tools_summary = true" in adapter
    assert "runtime_actions = false" in adapter
    assert "toggles_flags = false" in adapter
    assert "writes_profile = false" in adapter
    assert "g_game" not in adapter
    assert "autoWalk" not in adapter
    assert "castSpell" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_feature_flags", "ctoa_helper_feature_flags.lua")
    assert "ctoa_helper_feature_flags.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_feature_flags.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_FEATURE_FLAGS")' in source
    assert 'OPERATOR_SUMMARY_BRIDGES.tools' in source
    assert 'tools = moduleValue(externalOperatorSummary, "bridgeText", "tools", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "featureFlags = externalFeatureFlags" in source
    assert "profile = exportProfile()" in source
    assert "externalFeatureFlags.audit" not in source
    assert "externalFeatureFlags.toolsSummary" not in source
    tools_summary_start = source.index("OPERATOR_SUMMARY_BRIDGES.tools")
    tools_summary_end = source.index("OPERATOR_SUMMARY_BRIDGES.profile")
    tools_summary_source = source[tools_summary_start:tools_summary_end]
    assert '" | " .. summary' not in tools_summary_source
    assert '" | Flags " .. tostring(audit.status or "unknown")' not in tools_summary_source
    assert '"Haste " .. onOffText(tools.auto_haste)' not in tools_summary_source
    assert '" | Exeta " .. onOffText(tools.auto_exeta)' not in tools_summary_source
    assert '" | Diagnostics " .. onOffText(tools.feature_flags' not in tools_summary_source


def test_operator_summary_adapter_is_passive_and_packaged():
    adapter = OPERATOR_SUMMARY.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    source = HELPER.read_text(encoding="utf-8")

    assert "_G.CTOA_HELPER_OPERATOR_SUMMARY" in adapter
    for function_name in [
        "title",
        "healing",
        "healFriend",
        "conditions",
        "equipment",
        "scripting",
        "targeting",
        "magic",
        "tools",
        "profile",
        "ui",
        "bridgeText",
        "contract",
    ]:
        assert f"function OperatorSummary.{function_name}" in adapter
    assert 'mode = "passive"' in adapter
    assert "owns_operator_summary_text = true" in adapter
    assert "owns_profile_summary_bridge = true" in adapter
    assert "owns_module_summary_bridge = true" in adapter
    assert "creates_widgets = false" in adapter
    assert "runtime_actions = false" in adapter
    assert "executes_plans = false" in adapter
    assert "dispatch_allowed = false" in adapter
    assert "g_game" not in adapter
    assert "g_ui" not in adapter
    assert "autoWalk" not in adapter
    assert "castSpell" not in adapter
    assert "createWidget(" not in adapter
    assert boot_graph_has_module(loader, "ctoa_helper_operator_summary", "ctoa_helper_operator_summary.lua")
    assert "ctoa_helper_operator_summary.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_operator_summary.lua' in script
    assert 'rawget(_G, "CTOA_HELPER_OPERATOR_SUMMARY")' in source
    assert "function operatorSummaryText" not in source
    assert 'moduleValue(externalOperatorSummary, "bridgeText"' in source
    assert "local OPERATOR_SUMMARY_BRIDGES" in source
    assert "local function operatorSummaryBridgeText" not in source
    assert "titleSummaryText = function()" not in source
    assert "uiSummaryText = function()" not in source
    assert "local operatorSummaries = {" in source
    assert "function OperatorSummary.bridgeText" in adapter
    assert "owns_bridge_dispatch = true" in adapter
    assert 'title = {fallback = "profile summary unavailable"' in source
    assert 'healFriend = {fallback = "Heal Friend module unavailable | runtime gated"' in source
    assert 'OPERATOR_SUMMARY_BRIDGES.tools' in source
    assert 'OPERATOR_SUMMARY_BRIDGES.profile' in source
    assert 'OPERATOR_SUMMARY_BRIDGES.ui' in source


def test_planner_domain_is_passive_and_packaged():
    planner = PLANNER.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_PLANNER")' in planner
    assert "_G.CTOA_HELPER_PLANNER = Planner" in planner
    assert "function Planner.collect" in planner
    assert "function Planner.best" in planner
    assert "function Planner.summary" in planner
    assert "function Planner.contract" in planner
    assert 'plan_sio = 2' in planner
    assert 'plan_ring_swap = 2' in planner
    assert 'plan_attack = 3' in planner
    assert 'reason = "planner_error"' in planner
    assert 'reason = "missing_plan"' in planner
    assert 'mode = "passive"' in planner
    assert "runtime_actions = false" in planner
    assert "executes_plans = false" in planner
    assert "casts = false" in planner
    assert "talks = false" in planner
    assert "uses_items = false" in planner
    assert "walks = false" in planner
    assert "g_game" not in planner
    assert "g_map" not in planner
    assert "g_ui" not in planner
    assert "autoWalk" not in planner
    assert "castSpell(" not in planner
    assert "dofile" not in planner
    assert boot_graph_has_module(loader, "ctoa_helper_planner", "ctoa_helper_planner.lua")
    assert "ctoa_helper_planner.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_planner.lua' in script


def test_runtime_policy_is_passive_gatekeeper_and_packaged():
    policy = RUNTIME_POLICY.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_RUNTIME_POLICY")' in policy
    assert "_G.CTOA_HELPER_RUNTIME_POLICY = RuntimePolicy" in policy
    assert "function RuntimePolicy.requiredGates" in policy
    assert "function RuntimePolicy.protectionZonePolicy" in policy
    assert "function RuntimePolicy.resolvedProtectionZonePolicy" in policy
    assert "function RuntimePolicy.protectionZoneDecision" in policy
    assert "function RuntimePolicy.snapshot" in policy
    assert "function RuntimePolicy.decision" in policy
    assert "function RuntimePolicy.summary" in policy
    assert "function RuntimePolicy.contract" in policy
    assert '"manifest_current"' in policy
    assert '"module_static_gates"' in policy
    assert '"module_attach_smoke"' in policy
    assert '"smoke_attach_all"' in policy
    assert '"live_approval"' in policy
    assert 'mode = "passive"' in policy
    assert "runtime_actions = false" in policy
    assert "executes_plans = false" in policy
    assert "owns_protection_zone_policy = true" in policy
    assert "owns_resolved_protection_zone_policy = true" in policy
    assert "owns_protection_zone_decision = true" in policy
    assert "requires_module_attach_smoke = true" in policy
    assert "requires_smoke_attach_all = true" in policy
    assert "requires_live_approval = true" in policy
    assert "g_game" not in policy
    assert "g_map" not in policy
    assert "g_ui" not in policy
    assert "autoWalk" not in policy
    assert "castSpell(" not in policy
    assert "g_game.talk" not in policy
    assert "dofile" not in policy
    assert 'local externalRuntimePolicy = rawget(_G, "CTOA_HELPER_RUNTIME_POLICY")' in HELPER.read_text(encoding="utf-8")
    assert boot_graph_has_module(loader, "ctoa_helper_runtime_policy", "ctoa_helper_runtime_policy.lua")
    assert "ctoa_helper_runtime_policy.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_runtime_policy.lua' in script


def test_dispatch_guard_is_passive_policy_handoff_and_packaged():
    guard = DISPATCH_GUARD.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_DISPATCH_GUARD")' in guard
    assert "_G.CTOA_HELPER_DISPATCH_GUARD = DispatchGuard" in guard
    assert "function DispatchGuard.classify" in guard
    assert "function DispatchGuard.decision" in guard
    assert "function DispatchGuard.summary" in guard
    assert "function DispatchGuard.contract" in guard
    assert "policy_not_ready" in guard
    assert "sandbox_attach_required" in guard
    assert 'mode = "passive"' in guard
    assert "runtime_actions = false" in guard
    assert "executes_plans = false" in guard
    assert "dispatch_allowed = false" in guard
    assert "requires_runtime_policy = true" in guard
    assert "requires_sandbox_attach = true" in guard
    assert "requires_live_approval = true" in guard
    assert "g_game" not in guard
    assert "g_map" not in guard
    assert "g_ui" not in guard
    assert "autoWalk" not in guard
    assert "castSpell(" not in guard
    assert "g_game.talk" not in guard
    assert "dofile" not in guard
    assert boot_graph_has_module(loader, "ctoa_helper_dispatch_guard", "ctoa_helper_dispatch_guard.lua")
    assert "ctoa_helper_dispatch_guard.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_dispatch_guard.lua' in script


def test_plan_queue_is_passive_bounded_decision_queue_and_packaged():
    queue = PLAN_QUEUE.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_PLAN_QUEUE")' in queue
    assert "_G.CTOA_HELPER_PLAN_QUEUE = PlanQueue" in queue
    assert "function PlanQueue.normalize" in queue
    assert "function PlanQueue.enqueue" in queue
    assert "function PlanQueue.trim" in queue
    assert "function PlanQueue.summary" in queue
    assert "function PlanQueue.contract" in queue
    assert "DEFAULT_LIMIT = 12" in queue
    assert "while #result > maxItems" in queue
    assert "table.remove(result, 1)" in queue
    assert 'mode = "passive"' in queue
    assert "runtime_actions = false" in queue
    assert "executes_plans = false" in queue
    assert "dispatch_allowed = false" in queue
    assert "bounded_queue = true" in queue
    assert "requires_planner = true" in queue
    assert "requires_dispatch_guard = true" in queue
    assert "g_game" not in queue
    assert "g_map" not in queue
    assert "g_ui" not in queue
    assert "autoWalk" not in queue
    assert "castSpell(" not in queue
    assert "g_game.talk" not in queue
    assert "dofile" not in queue
    assert boot_graph_has_module(loader, "ctoa_helper_plan_queue", "ctoa_helper_plan_queue.lua")
    assert "ctoa_helper_plan_queue.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_plan_queue.lua' in script


def test_runtime_readiness_is_passive_bridge_status_and_packaged():
    readiness = RUNTIME_READINESS.read_text(encoding="utf-8")
    loader = boot_graph_source()
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert 'rawget(_G, "CTOA_HELPER_RUNTIME_READINESS")' in readiness
    assert "_G.CTOA_HELPER_RUNTIME_READINESS = RuntimeReadiness" in readiness
    assert "function RuntimeReadiness.requiredComponents" in readiness
    assert "function RuntimeReadiness.requiredGates" in readiness
    assert "function RuntimeReadiness.snapshot" in readiness
    assert "function RuntimeReadiness.decision" in readiness
    assert "function RuntimeReadiness.summary" in readiness
    assert "function RuntimeReadiness.contract" in readiness
    for token in ['"planner"', '"runtime_policy"', '"dispatch_guard"', '"plan_queue"']:
        assert token in readiness
    for token in ['"manifest_current"', '"module_static_gates"', '"module_attach_smoke"', '"smoke_attach_all"', '"live_approval"']:
        assert token in readiness
    assert 'mode = "passive"' in readiness
    assert "runtime_actions = false" in readiness
    assert "executes_plans = false" in readiness
    assert "dispatch_allowed = false" in readiness
    assert "requires_plan_queue = true" in readiness
    assert "requires_live_approval = true" in readiness
    assert "g_game" not in readiness
    assert "g_map" not in readiness
    assert "g_ui" not in readiness
    assert "autoWalk" not in readiness
    assert "castSpell(" not in readiness
    assert "g_game.talk" not in readiness
    assert "dofile" not in readiness
    assert boot_graph_has_module(loader, "ctoa_helper_runtime_readiness", "ctoa_helper_runtime_readiness.lua")
    assert "ctoa_helper_runtime_readiness.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_runtime_readiness.lua' in script


def test_equipment_is_read_only_profiled_module_lane():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    equipment_module = EQUIPMENT.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "equipment = {" in source
    assert 'rawget(_G, "CTOA_HELPER_EQUIPMENT")' in source
    assert "_G.CTOA_HELPER_EQUIPMENT" in equipment_module
    assert "function Equipment.slotText" in equipment_module
    assert "function Equipment.snapshot" in equipment_module
    assert "function Equipment.apiProbe" in equipment_module
    assert "function Equipment.observe" in equipment_module
    assert "function Equipment.plan" in equipment_module
    assert "function Equipment.summary" in equipment_module
    assert "function Equipment.contract" in equipment_module
    assert 'next_action = "plan_ring_swap"' in equipment_module
    assert 'next_action = "plan_amulet_swap"' in equipment_module
    assert 'reason = "runtime_gated"' in equipment_module
    assert 'reason = "pvp_gear_lock"' in equipment_module
    assert 'reason = "hp_above_threshold"' in equipment_module
    assert 'mode = "passive"' in equipment_module
    assert "owns_slot_text = true" in equipment_module
    assert "owns_snapshot = true" in equipment_module
    assert "owns_api_probe = true" in equipment_module
    assert "owns_observer = true" in equipment_module
    assert "owns_summary_text = true" in equipment_module
    assert "runtime_actions = false" in equipment_module
    assert "swaps = false" in equipment_module
    assert "moves_items = false" in equipment_module
    assert "requires_sandbox_attach = true" in equipment_module
    assert "equipmentSummaryText = function()" not in source
    assert 'equipment = moduleValue(externalOperatorSummary, "bridgeText", "equipment", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "function maybeSampleEquipment(now)" in source
    assert "local function buildEquipmentApiProbeSnapshot()" not in source
    assert "local function buildEquipmentSnapshot()" not in source
    assert "local function inventorySlotText(" not in source
    assert "Equipment module unavailable | read-only" in source
    assert 'styleUi("renderEquipmentPanel"' in source
    assert '"ctoaEquipmentObserver", label = "Observer"' in ui_module
    assert '"ctoaEquipmentSlots", label = "Read slots"' in ui_module
    assert '"ctoaEquipmentRingPlan", label = "Ring plan"' in ui_module
    assert '"ctoaEquipmentApiProbe", "API probe"' in ui_module
    assert '"ctoaEquipmentStatus", "Status: read-only pending; swap runtime gated"' in ui_module
    assert 'bindClick(Helper.widgets.equipment_tab, function() switchTab("equipment") end)' in source
    assert 'Helper.configureComingSoonTab(Helper.widgets.equipment_tab, "Equipment")' not in source
    assert "HELPER_CONFIG.equipment.runtime_enabled = false" in source
    assert "api_probe_enabled = true" in source
    assert "\n    equipment = {" in profile
    assert "api_probe_enabled = true" in profile
    assert 'api_probe_status = "pending"' in profile
    assert "runtime_enabled = false" in profile
    equipment_source = equipment_module
    assert "player.getInventoryItem=" in equipment_source
    observer_start = source.index("function maybeSampleEquipment(now)")
    observer_end = source.index("function maybeRunTimer(now)")
    observer_source = source[observer_start:observer_end]
    assert 'moduleValue(externalEquipment, "observe", equipment, now, {' in observer_source
    assert "pcall(externalEquipment.observe" not in observer_source
    assert "equipment module unavailable" in observer_source
    assert "player.getInventoryItem=" not in observer_source
    assert "castSpell(" not in equipment_source
    assert "sendActionbarSlot(" not in equipment_source
    assert "g_game.talk" not in equipment_source
    assert "g_game.move" not in equipment_source
    assert "moveTo" not in equipment_source
    assert "useInventoryItem" not in equipment_source
    assert "g_game.use" not in equipment_source


def test_scripting_is_policy_shell_without_runtime_execution():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    scripting_module = SCRIPTING.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "scripting = {" in source
    assert 'rawget(_G, "CTOA_HELPER_SCRIPTING")' in source
    assert "_G.CTOA_HELPER_SCRIPTING" in scripting_module
    assert "function Scripting.policySnapshot" in scripting_module
    assert "function Scripting.plan" in scripting_module
    assert "function Scripting.summary" in scripting_module
    assert "function Scripting.contract" in scripting_module
    assert 'next_action = "audit_only"' in scripting_module
    assert 'next_action = "policy_review"' in scripting_module
    assert 'reason = "unsafe_scripting_flag"' in scripting_module
    assert 'reason = "runtime_scripting_blocked"' in scripting_module
    assert 'reason = "snippet_execution_blocked"' in scripting_module
    assert 'mode = "passive"' in scripting_module
    assert "owns_policy_snapshot = true" in scripting_module
    assert "owns_summary_text = true" in scripting_module
    assert "runtime_actions = false" in scripting_module
    assert "executes_snippets = false" in scripting_module
    assert "loads_files = false" in scripting_module
    assert "requires_security_review = true" in scripting_module
    assert "requires_sandbox_attach = true" in scripting_module
    assert "scriptingSummaryText = function()" not in source
    assert 'scripting = moduleValue(externalOperatorSummary, "bridgeText", "scripting", OPERATOR_SUMMARY_BRIDGES)' in source
    assert "function buildScriptingPolicySnapshot()" not in source
    assert "build_scripting_policy_snapshot = function()" in source
    assert 'moduleValue(externalScripting, "policySnapshot", scripting)' in source
    assert "pcall(externalScripting.policySnapshot" not in source
    assert "Scripting module unavailable | runtime gated" in source
    assert "scripting module unavailable" in source
    assert 'styleUi("renderScriptingPanel"' in source
    assert '"ctoaScriptingPolicy", "Policy shell"' in ui_module
    assert '"ctoaScriptingSnippets", "Snippets"' in ui_module
    assert '"ctoaScriptingEval", "Runtime eval"' in ui_module
    assert '"ctoaScriptingStatus", "Status: " .. policyText()' in ui_module
    assert 'bindClick(Helper.widgets.scripting_tab, function() switchTab("scripting") end)' in source
    assert 'Helper.configureComingSoonTab(Helper.widgets.scripting_tab, "Scripting")' not in source
    assert "HELPER_CONFIG.scripting.runtime_enabled = false" in source
    assert "HELPER_CONFIG.scripting.allow_user_snippets = false" in source
    assert "HELPER_CONFIG.scripting.allow_runtime_eval = false" in source
    assert "\n    scripting = {" in profile
    assert 'policy_mode = "deny_all"' in profile
    scripting_source = scripting_module
    assert "loadstring" not in scripting_source
    assert "dofile(" not in scripting_source
    assert "pcall(function()" not in scripting_source
    assert "g_game.talk" not in scripting_source
    assert "castSpell(" not in scripting_source
    fallback_source = source[
        source.index("build_scripting_policy_snapshot = function()") : source.index('styleUi("renderProfilePanel"')
    ]
    assert "unsafe scripting flag" not in fallback_source
    assert "runtime scripting disabled" not in fallback_source
    assert '" | Snippets "' not in fallback_source


def test_cavebot_tab_is_interactive_waypoint_loop():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")

    assert 'bindClick(Helper.widgets.cavebot_tab, function() switchTab("cavebot") end)' in source
    assert 'styleUi("renderCavebotPanel"' in source
    assert "cavebot_delay_choices = {600, 900, 1200, 1600, 2200}" not in source
    assert "cavebot_reach_choices = {0, 1, 2, 3}" not in source
    assert "function Ui.cavebotActionSpecs" in ui_module
    assert "Ui.cavebotDelayChoices()" in ui_module
    assert "Ui.cavebotReachChoices()" in ui_module
    assert 'ctx.add_toggle_setting_row(window, "ctoaCavebotEnabled"' in ui_module
    assert 'ctx.add_toggle_setting_row(window, "ctoaCavebotMovement"' in ui_module
    assert 'id = "ctoaCavebotAdd", text = "Add"' in ui_module
    assert 'id = "ctoaCavebotTestWalk", text = "Test"' in ui_module
    assert 'id = "ctoaCavebotDelete", text = "Del"' in ui_module
    assert 'id = "ctoaCavebotUp", text = "Up"' in ui_module
    assert 'id = "ctoaCavebotDown", text = "Down"' in ui_module
    assert 'id = "ctoaCavebotPrev", text = "Prev"' in ui_module
    assert 'id = "ctoaCavebotNext", text = "Next"' in ui_module
    assert "function selectCavebotWaypoint(delta)" in source
    assert "function deleteCurrentCavebotWaypoint(confirm)" in source
    assert "function moveCurrentCavebotWaypoint(delta)" in source
    assert 'action == "cavebot_delete"' in source
    assert 'action == "cavebot_move_up"' in source
    assert 'action == "cavebot_move_down"' in source
    assert 'action == "cavebot_prev"' in source
    assert 'action == "cavebot_next"' in source
    assert 'action == "cavebot_probe"' in source
    assert "function testCavebotAutoWalk()" in source
    assert "return player:autoWalk(target, false)" in source
    assert 'moduleValue(externalCavebotRuntime, "testWalkPlan"' in source
    assert 'function maybeRunCavebot(now)' in source
    assert "cavebot_movement_enabled = false" in source
    assert 'cavebotRuntimeText("statusText", "movement_disabled"' in source
    assert "g_game.autoWalk(" not in source
    assert "g_game.walk(" not in source
    assert 'cavebotRuntimeText("traceText", "movement_attempt"' in source
    assert "runMovementApiProbe" in source
    assert 'label = "Move API"' in source
    assert "Helper.movement_api_probe_attempts <= 120" not in source
    assert "g_map.findPath(current, target, 200, 0)" in source
    assert "cavebot_retry_limit = 3" in source
    assert "cavebotMovementBlockedReason(player, current)" in source
    assert "isLocalPlayerInProtectionZone()" in source
    assert "return player:autoWalk(pos, retry)" in source
    assert 'tools.cavebot_movement_enabled = false' in source
    assert 'moduleValue(externalCavebotRuntime, "retryDecision"' in source
    assert 'trace_event = "retry_budget_disabled"' in CAVEBOT_RUNTIME.read_text(encoding="utf-8")
    assert 'setCavebotStatus(cavebotRuntimeText("statusText", "no_player_position"))' in source
    assert 'setCavebotStatus("no player position")' not in source
    assert 'kind == "no_player_position"' in CAVEBOT_RUNTIME.read_text(encoding="utf-8")


def test_cavebot_route_editor_does_not_trigger_movement():
    source = HELPER.read_text(encoding="utf-8")
    route_module = ROUTE.read_text(encoding="utf-8")

    editor_start = source.index("function selectCavebotWaypoint(delta)")
    editor_end = source.index("function autoWalkTo(pos)")
    editor_source = source[editor_start:editor_end]

    assert "table.remove(waypoints, index)" in route_module
    assert "waypoints[index], waypoints[target] = waypoints[target], waypoints[index]" in route_module
    assert "table.remove(waypoints, index)" not in editor_source
    assert "waypoints[index], waypoints[target] = waypoints[target], waypoints[index]" not in editor_source
    assert 'applyCavebotEditorAction("select"' in editor_source
    assert 'applyCavebotEditorAction("delete"' in editor_source
    assert 'applyCavebotEditorAction("move"' in editor_source
    assert "markProfileDirty(result.dirty_reason)" in source
    assert 'dirtyReason = "cavebot_delete"' in route_module
    assert 'dirtyReason = "cavebot_reorder"' in route_module
    assert "refreshCavebotUi()" in source[source.index("local function applyCavebotEditorAction"):source.index("function addCurrentCavebotWaypoint")]
    assert "setCavebotStatus(" in source[source.index("local function applyCavebotEditorAction"):source.index("function addCurrentCavebotWaypoint")]
    assert "autoWalkTo(" not in editor_source
    assert ":autoWalk(" not in editor_source
    assert "g_game.autoWalk(" not in editor_source
    assert "g_game.walk(" not in editor_source


def test_cavebot_runtime_has_guarded_retry_budget_before_looped_movement():
    source = HELPER.read_text(encoding="utf-8")

    runtime_start = source.index("function resetCavebotMovementState(reason)")
    runtime_end = source.index("function maybeManaPotion(now, vitals)")
    runtime_source = source[runtime_start:runtime_end]

    assert 'return "offline"' in runtime_source
    assert 'return "PZ guard"' in runtime_source
    assert "noteCavebotProgress(tools, current, target, now)" in runtime_source
    assert "cavebotRetryBudgetExceeded(tools)" in runtime_source
    assert "tools.cavebot_retry_attempts = (tools.cavebot_retry_attempts or 0) + 1" in runtime_source
    assert "tools.cavebot_movement_enabled = false" in runtime_source
    assert "resetCavebotMovementState(\"waypoint reached\")" in runtime_source
    assert 'cavebotRuntimeText("traceText", "movement_reset"' in runtime_source
    assert "Cavebot movement state reset:" not in runtime_source
    assert "Cavebot movement target=" not in runtime_source
    assert "Test walk target=" not in runtime_source
    assert "Cavebot movement disabled: retry budget reached" not in runtime_source
    assert "Cavebot movement disabled: walk failed retry budget" not in runtime_source
    assert "local retry = (HELPER_CONFIG.tools.cavebot_retry_attempts or 0) > 0" in runtime_source
    assert 'moduleValue(externalCavebotRuntime, "walkPreflight"' in runtime_source
    assert 'moduleValue(externalCavebotRuntime, "walkingStatus"' in runtime_source
    assert 'moduleValue(externalCavebotRuntime, "retryDecision"' in runtime_source
    assert "player:autoWalk(pos, retry)" in runtime_source
    assert "g_game.autoWalk(" not in runtime_source
    assert "g_game.walk(" not in runtime_source


def test_smokeall_lists_every_zerobot_shell_view():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert '"HealingVitalsSmoke"' in script
    assert '"CombatSafetySmoke"' in script
    assert '"CavebotSafetySmoke"' in script
    assert '"TimerSafetySmoke"' in script
    assert '"LootSafetySmoke"' in script

    for action in ["PrepareDev", "ValidateDev", "Setup", "SmokePreflight", "SmokeStatus", "SmokeQueue", "GoalStatus", "LocalReady", "Launch", "Smoke", "SmokeAll", "SmokeAttach", "SmokeAttachModules", "SmokeAttachAll", "HealFriendNoTargetSmoke", "ConditionsObserverSmoke", "EquipmentObserverSmoke", "ScriptingPolicySmoke", "PlannerStaticSmoke", "RuntimePolicyStaticSmoke", "DispatchGuardStaticSmoke", "PlanQueueStaticSmoke", "RuntimeReadinessStaticSmoke", "ModuleStatusStaticSmoke", "ActionCatalogStaticSmoke", "DecisionTraceStaticSmoke", "SandboxHandoffStaticSmoke", "FeatureFlagsStaticSmoke", "HudStaticSmoke", "HotkeysStaticSmoke", "ModalStaticSmoke", "InputContractsStaticSmoke", "RouteStaticSmoke", "TargetingStaticSmoke", "CombatRuntimeStaticSmoke", "CavebotRuntimeStaticSmoke", "LootRuntimeStaticSmoke", "TimerRuntimeStaticSmoke", "ProfileSchemaStaticSmoke", "OperatorSummaryStaticSmoke", "ExternalBotImportGateStaticSmoke", "HelperShellBudgetStaticSmoke", "HelperShellBudgetPlanStaticSmoke", "ModuleContract", "ModuleAudit", "ModuleStaticGates", "Snapshot", "ReadyCheck", "BackupLiveCtoa", "PromoteLiveCtoa", "EmergencyRepairLiveCtoa", "DisableLiveCtoa", "EnableLiveCtoa", "EnableLiveCtoaUiOnly", "Stop"]:
        assert f'"{action}"' in script
    for tab in SMOKE_ALL_TABS:
        assert f'"{tab}"' in script


def test_solteria_dev_lane_packages_without_touching_live_client():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert '[string]$DevDir = "runtime\\solteria_helper_dev"' in script
    assert "function New-DevPackage" in script
    assert "function Invoke-DevValidation" in script
    assert "Compress-Archive" in script
    assert "manifest.json" in script
    assert "CHANGELOG.md" in script
    assert "validation.json" in script
    assert "release_readiness.json" in script
    assert "Get-FileHash -Algorithm SHA256" in script
    assert "function Write-JsonAtomic" in script
    assert 'Move-Item -LiteralPath $tmp -Destination $Path -Force' in script
    assert "function Write-TextAtomic" in script
    assert "function Write-DevChangelog" in script
    assert "function Write-DevValidationReport" in script
    assert "function Write-ReleaseReadinessReport" in script
    assert "ctoa_otclient_{0}.zip" in script
    assert "No live Solteria files are changed by PrepareDev or ValidateDev." in script
    assert "Live client untouched." in script
    assert "function Invoke-SmokePreflight" in script
    assert "smoke_preflight.json" in script
    assert "SmokePreflight runs Setup and hash checks only" in script
    assert "if ($missingPackage)" in script
    assert "New-DevPackage" in script
    assert "ctoa_helper_modules.lua" in script
    assert "ctoa_helper_ui.lua" in script
    assert "ctoa_helper_diagnostics.lua" in script
    assert "ctoa_helper_hotkeys.lua" in script
    assert "ctoa_helper_modal.lua" in script
    assert "ctoa_helper_route.lua" in script
    assert "ctoa_helper_targeting.lua" in script
    assert "ctoa_helper_combat_runtime.lua" in script
    assert "ctoa_helper_cavebot_runtime.lua" in script
    assert "ctoa_helper_loot_runtime.lua" in script
    assert "ctoa_helper_timer_runtime.lua" in script
    assert "ctoa_helper_profile_schema.lua" in script
    assert "ctoa_helper_profile_persistence.lua" in script
    assert "ctoa_helper_operator_summary.lua" in script
    assert "ctoa_helper_planner.lua" in script
    assert "ctoa_helper_runtime_policy.lua" in script
    assert "ctoa_helper_dispatch_guard.lua" in script
    assert "ctoa_helper_plan_queue.lua" in script
    assert "ctoa_helper_runtime_readiness.lua" in script
    assert "ctoa_helper_hud.lua" in script
    assert "ctoa_helper_conditions.lua" in script
    assert "ctoa_helper_equipment.lua" in script
    assert "ctoa_helper_scripting.lua" in script
    assert "ctoa_helper_heal_friend.lua" in script
    assert 'mods/ctoa_otclient/ctoa_helper_modules.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_ui.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_diagnostics.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_hotkeys.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_modal.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_route.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_targeting.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_combat_runtime.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_cavebot_runtime.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_loot_runtime.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_timer_runtime.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_profile_schema.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_profile_persistence.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_planner.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_runtime_policy.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_dispatch_guard.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_plan_queue.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_runtime_readiness.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_hud.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_conditions.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_equipment.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_scripting.lua' in script
    assert 'mods/ctoa_otclient/ctoa_helper_heal_friend.lua' in script
    assert "manifest = [pscustomobject]" in script
    assert '$manifest.created_at.ToString("s")' in script
    assert "created_at = $manifestCreatedAt" in script
    assert "function Invoke-SmokeStatus" in script
    assert "function Invoke-HealingVitalsSmoke" in script
    assert "healing_vitals_smoke.json" in script
    assert "sandbox_read_only_vitals" in script
    assert "runtime_remains_disarmed" in script
    assert "-Action SmokeAttach -Tab healing" in script
    assert "function Invoke-CombatSafetySmoke" in script
    assert "combat_safety_smoke.json" in script
    assert "sandbox_read_only_combat_safety" in script
    assert "targeting_guards" in script
    assert "combat_policy_guards" in script
    assert "function Invoke-CavebotSafetySmoke" in script
    assert "cavebot_safety_smoke.json" in script
    assert "sandbox_read_only_cavebot_safety" in script
    assert "route_retry_guards" in script
    assert "cavebot_policy_guards" in script
    assert "function Invoke-TimerSafetySmoke" in script
    assert "timer_safety_smoke.json" in script
    assert "sandbox_passive_timer_tick" in script
    assert "passive_timer_tick" in script
    assert "function Invoke-LootSafetySmoke" in script
    assert "loot_safety_smoke.json" in script
    assert "sandbox_read_only_container_probe" in script
    assert "feature_flag_disabled" in script
    assert "zero_planned_items" in script
    assert "-Action SmokeAttach -Tab tools_diag" in script
    assert "function Invoke-HealFriendNoTargetSmoke" in script
    assert "heal_friend_no_target_smoke.json" in script
    assert "function Invoke-ConditionsObserverSmoke" in script
    assert "conditions_observer_smoke.json" in script
    assert "state_api_probe_present" in script
    assert "-Action SmokeAttach -Tab conditions" in script
    assert "function Invoke-EquipmentObserverSmoke" in script
    assert "equipment_observer_smoke.json" in script
    assert "inventory_api_probe_present" in script
    assert "no_move_or_use_in_observer" in script
    assert "-Action SmokeAttach -Tab equipment" in script
    assert "function Invoke-ScriptingPolicySmoke" in script
    assert "scripting_policy_smoke.json" in script
    assert "unsafe_flags_block_status" in script
    assert "no_eval_loader_in_policy" in script
    assert "no_runtime_call_in_policy" in script
    assert "-Action SmokeAttach -Tab scripting" in script
    assert "function Invoke-PlannerStaticSmoke" in script
    assert "planner_static_smoke.json" in script
    assert "solteria-helper-planner-static-smoke" in script
    assert "static_passive_planner_contract" in script
    assert "no_runtime_actions" in script
    assert "no_otclient_globals" in script
    assert "-Action PlannerStaticSmoke" in script
    assert "function Invoke-RuntimePolicyStaticSmoke" in script
    assert "runtime_policy_static_smoke.json" in script
    assert "solteria-helper-runtime-policy-static-smoke" in script
    assert "static_passive_runtime_policy_contract" in script
    assert "required_gates" in script
    assert '"module_attach_smoke"' in script
    assert '"smoke_attach_all"' in script
    assert '"live_approval"' in script
    assert "-Action RuntimePolicyStaticSmoke" in script
    assert "function Invoke-DispatchGuardStaticSmoke" in script
    assert "dispatch_guard_static_smoke.json" in script
    assert "solteria-helper-dispatch-guard-static-smoke" in script
    assert "static_passive_dispatch_guard_contract" in script
    assert "policy_handoff" in script
    assert "sandbox_attach_required" in script
    assert "-Action DispatchGuardStaticSmoke" in script
    assert "function Invoke-PlanQueueStaticSmoke" in script
    assert "plan_queue_static_smoke.json" in script
    assert "solteria-helper-plan-queue-static-smoke" in script
    assert "static_passive_plan_queue_contract" in script
    assert "bounded_queue" in script
    assert "-Action PlanQueueStaticSmoke" in script
    assert "function Invoke-RuntimeReadinessStaticSmoke" in script
    assert "runtime_readiness_static_smoke.json" in script
    assert "solteria-helper-runtime-readiness-static-smoke" in script
    assert "static_passive_runtime_readiness_contract" in script
    assert "component_coverage" in script
    assert "gate_coverage" in script
    assert "-Action RuntimeReadinessStaticSmoke" in script
    assert "function Invoke-ModuleContract" in script
    assert "otclient_helper_module_contract.py" in script
    assert "module_contract.json" in script
    assert "solteria_helper_module_contract.md" in script
    assert '"ModuleContract" {' in script
    assert "function Invoke-ModuleAudit" in script
    assert "otclient_helper_module_audit.py" in script
    assert "module_audit.json" in script
    assert "solteria_helper_module_workplan.md" in script
    assert '"ModuleAudit" {' in script
    assert "function Invoke-ModuleStaticGates" in script
    assert "module_static_gates.json" in script
    assert "solteria-helper-module-static-gates" in script
    assert "ModuleStaticGates runs repo-only static module gates" in script
    assert "function Invoke-TargetingStaticSmoke" in script
    assert "targeting_static_smoke.json" in script
    assert "solteria-helper-targeting-static-smoke" in script
    assert "static_passive_target_scorer_contract" in script
    assert "owns_target_score = true" in script
    assert "runtime_execution_stays_in_helper" in script
    assert "-Action TargetingStaticSmoke" in script
    assert "-Action SmokeAttach -Tab hunting" in script
    assert "function Invoke-CombatRuntimeStaticSmoke" in script
    assert "combat_runtime_static_smoke.json" in script
    assert "solteria-helper-combat-runtime-static-smoke" in script
    assert "static_passive_combat_runtime_contract" in script
    assert "owns_runtime_plan = true" in script
    assert "owns_wait_reason_text = true" in script
    assert "owns_decision_state_text = true" in script
    assert "helper_uses_combat_runtime_adapter" in script
    assert "-Action CombatRuntimeStaticSmoke" in script
    assert "-Action SmokeAttach -Tab hunting_magic" in script
    assert "function Invoke-CavebotRuntimeStaticSmoke" in script
    assert "cavebot_runtime_static_smoke.json" in script
    assert "solteria-helper-cavebot-runtime-static-smoke" in script
    assert "static_passive_cavebot_runtime_contract" in script
    assert "helper_uses_cavebot_runtime_adapter" in script
    assert "-Action CavebotRuntimeStaticSmoke" in script
    assert "function Invoke-LootRuntimeStaticSmoke" in script
    assert "loot_runtime_static_smoke.json" in script
    assert "solteria-helper-loot-runtime-static-smoke" in script
    assert "static_passive_loot_runtime_contract" in script
    assert "helper_uses_loot_runtime_adapter" in script
    assert "-Action LootRuntimeStaticSmoke" in script
    assert "-Action SmokeAttach -Tab tools_diag" in script
    assert "function Invoke-SmokeAttachModules" in script
    assert "module_attach_smoke.json" in script
    assert "solteria-helper-module-attach-smoke" in script
    assert "SmokeAttachModules attaches only to an already-running sandbox client" in script
    assert "Run SmokeAttachAll for final in-world visual acceptance." in script
    assert "function Invoke-LocalReady" in script
    assert "local_ready.json" in script
    assert "ready_for_sandbox" in script
    assert "LocalReady runs local packaging, static validation, SmokePreflight, ModuleStaticGates, GoalStatus, and SmokeQueue only" in script
    assert "function Invoke-SmokeQueue" in script
    assert "sandbox_smoke_queue.json" in script
    assert "solteria_helper_sandbox_smoke_queue.py" in script
    assert "sandbox_smoke_queue_status" in script
    assert '"SmokeQueue" {' in script
    assert "Invoke-GoalStatus" in script
    assert "no_cast_in_observer" in script
    assert "no_actionbar_in_observer" in script
    assert "no_talk_in_observer" in script
    assert '"HealFriendNoTargetSmoke" {' in script
    assert '"HealingVitalsSmoke" {' in script
    assert '"CombatSafetySmoke" {' in script
    assert '"CavebotSafetySmoke" {' in script
    assert '"TimerSafetySmoke" {' in script
    assert '"LootSafetySmoke" {' in script
    assert '"ConditionsObserverSmoke" {' in script
    assert '"EquipmentObserverSmoke" {' in script
    assert '"ScriptingPolicySmoke" {' in script
    assert '"PlannerStaticSmoke" {' in script
    assert '"RuntimePolicyStaticSmoke" {' in script
    assert '"DispatchGuardStaticSmoke" {' in script
    assert '"PlanQueueStaticSmoke" {' in script
    assert '"RuntimeReadinessStaticSmoke" {' in script
    assert '"HudStaticSmoke" {' in script
    assert '"HotkeysStaticSmoke" {' in script
    assert '"ModalStaticSmoke" {' in script
    assert "function Invoke-InputContractsStaticSmoke" in script
    assert "otclient_input_contract_fixtures.py" in script
    assert "input_contract_fixtures.json" in script
    assert "solteria_helper_input_contracts.md" in script
    assert '"InputContractsStaticSmoke" {' in script
    assert 'module = "input_contracts"' in script
    assert '"RouteStaticSmoke" {' in script
    assert '"TargetingStaticSmoke" {' in script
    assert '"CombatRuntimeStaticSmoke" {' in script
    assert '"CavebotRuntimeStaticSmoke" {' in script
    assert '"LootRuntimeStaticSmoke" {' in script
    assert "function Invoke-TimerRuntimeStaticSmoke" in script
    assert "timer_runtime_static_smoke.json" in script
    assert '"TimerRuntimeStaticSmoke" {' in script
    assert "function Invoke-ProfileSchemaStaticSmoke" in script
    assert "profile_schema_static_smoke.json" in script
    assert "moduleValue(externalProfileSchema, functionName" in script
    assert "pcall(externalProfileSchema[functionName]" not in script
    assert '"ProfileSchemaStaticSmoke" {' in script
    assert "function Invoke-OperatorSummaryStaticSmoke" in script
    assert "operator_summary_static_smoke.json" in script
    assert '"OperatorSummaryStaticSmoke" {' in script
    assert "function Invoke-ExternalBotImportGateStaticSmoke" in script
    assert "external_bot_import_gate_static_smoke.json" in script
    assert "solteria-helper-external-bot-import-gate-static-smoke" in script
    assert "runtime_import_allowed" in script
    assert "direct_copy_allowed" in script
    assert "runtime_gate_mapping" in script
    assert '"ExternalBotImportGateStaticSmoke" {' in script
    assert "function Invoke-HelperShellBudgetStaticSmoke" in script
    assert "helper_shell_budget_static_smoke.json" in script
    assert "solteria-helper-shell-budget-static-smoke" in script
    assert "helper_hard_line_ceiling" in script
    assert "UI composition, profile persistence, and guarded dispatch only" in script
    assert '"HelperShellBudgetStaticSmoke" {' in script
    assert "function Invoke-HelperShellBudgetPlanStaticSmoke" in script
    assert "helper_shell_budget_plan.json" in script
    assert "otclient_helper_shell_budget_plan.py" in script
    assert '"HelperShellBudgetPlanStaticSmoke" {' in script
    assert 'module = "helper_shell_budget_plan"' in script
    assert '"ModuleStaticGates" {' in script
    assert '"SmokeAttachModules" {' in script
    assert '"LocalReady" {' in script
    assert "function Get-SandboxProcessSummaries" in script
    assert "smoke_status.json" in script
    assert "SmokeStatus is read-only" in script
    assert "Write-JsonAtomic -InputObject $report -Path $path -Depth 8" in script
    assert "function Invoke-GoalStatus" in script
    assert "goal_status.json" in script
    assert "function Write-GoalHandoff" in script
    assert "function Read-SmokeQueueSummary" in script
    assert "function Read-ModuleAuditSummary" in script
    assert "GOAL_HANDOFF.md" in script
    assert "## Sandbox Smoke Queue" in script
    assert "Queue status:" in script
    assert "Next queue action:" in script
    assert "queue {0}. {1}: {2}; command: {3}" in script
    assert "sandbox_smoke_queue = $smokeQueue" in script
    assert "required_count" in script
    assert "queued_count" in script
    assert "next_steps" in script
    assert "## Module Workplan" in script
    assert "module_audit = $moduleAudit" in script
    assert "Helper budget:" in script
    assert "next_supplemental_id" in script
    assert "Supplemental Refactor Plan" in script
    assert "next_module_action" in script
    assert "heal_friend_no_target_smoke.json" in script
    assert "next_module_evidence_status" in script
    assert "next_module_command" in script
    assert "static_gate_summary" in script
    assert "static_gate_passed_count" in script
    assert "next_extraction_id" in script
    assert "extraction_plan" in script
    assert "### Extraction Map" in script
    assert "safe_order" in script
    assert "Static gates:" in script
    assert "conditions_observer_smoke.json" in script
    assert "equipment_observer_smoke.json" in script
    assert "scripting_policy_smoke.json" in script
    assert "planner_static_smoke.json" in script
    assert "runtime_policy_static_smoke.json" in script
    assert "dispatch_guard_static_smoke.json" in script
    assert "plan_queue_static_smoke.json" in script
    assert "runtime_readiness_static_smoke.json" in script
    assert "Capture in-world SmokeAttachModules evidence for prototype module tabs" in script
    assert "-Action HealFriendNoTargetSmoke" in script
    assert "-Action SmokeAttach -Tab heal_friend" in script
    assert "-Action ConditionsObserverSmoke" in script
    assert "-Action EquipmentObserverSmoke" in script
    assert "-Action ScriptingPolicySmoke" in script
    assert "-Action PlannerStaticSmoke" in script
    assert "-Action RuntimePolicyStaticSmoke" in script
    assert "-Action DispatchGuardStaticSmoke" in script
    assert "-Action PlanQueueStaticSmoke" in script
    assert "-Action RuntimeReadinessStaticSmoke" in script
    assert "Next module command:" in script
    assert "Next module action:" in script
    assert "Goal handoff:" in script
    assert "handoff_path =" in script
    assert "Goal dashboard:" in script
    assert "dashboard_path =" in script
    assert "Invoke-SmokeStatus" in script
    assert "GoalStatus refreshes SmokeStatus and dev audit files only" in script
    assert "Write-JsonAtomic -InputObject $status -Path $statusPath -Depth 8" in script
    assert '"GoalStatus" {' in script
    assert "smoke_preflight_status = $preflightStatus" in script
    assert "Launch the sandbox client, enter test character, then run SmokeAttachModules." in script
    assert "next_command = $nextCommand" in script
    assert "Next command: $nextCommand" in script
    assert '"SmokeStatus" {' in script
    assert '$stageRoot = Join-Path (Join-Path $repo $DevDir) "latest"' in script
    assert "function Copy-CtoaRuntimeFile" in script
    assert "$stagePath = Join-Path $stageRoot $StageRelative" in script
    assert "Copy-Item -LiteralPath $stagePath -Destination $Destination -Force" in script
    assert "$sourcePath = Join-Path $repo $RepoRelative" in script
    assert "Copy-Item -LiteralPath $sourcePath -Destination $Destination -Force" in script
    assert 'Copy-CtoaRuntimeFile -StageRelative "mods\\ctoa_otclient\\$name" -RepoRelative "scripts\\lua\\otclient\\$name" -Destination (Join-Path $modDir $name)' in script
    assert 'Copy-CtoaRuntimeFile -StageRelative "ctoa_otclient_loader.lua" -RepoRelative "scripts\\lua\\otclient\\ctoa_otclient_loader.lua" -Destination (Join-Path $ClientDir "ctoa_otclient_loader.lua")' in script
    assert 'Copy-CtoaRuntimeFile -StageRelative "ctoa_ek_profile.lua" -RepoRelative "scripts\\lua\\otclient\\ctoa_ek_profile.lua" -Destination (Join-Path $ClientDir "ctoa_ek_profile.lua")' in script
    assert '"ctoa_helper_cavebot_runtime.lua"' in script
    assert '"ctoa_native_helper.lua"' in script
    assert '"ctoa_ek_profile.lua"' in script
    assert '"SmokePreflight" {' in script
    assert "& python -m pytest tests\\test_otclient_helper_zerobot_shell.py tests\\test_solteria_api_audit.py tests\\test_ctoa_helper_smoke_report.py tests\\test_solteria_helper_release_gate.py tests\\test_solteria_helper_goal_audit.py -q" in script
    assert "& python scripts\\ops\\ctoa_helper_ui_preview.py" in script
    assert "& python scripts\\ops\\solteria_api_audit.py --client-dir $SourceClient" in script
    assert "& python scripts\\ops\\solteria_helper_release_gate.py --dev-dir $outRoot --allow-blocked" in script
    assert "& python scripts\\ops\\solteria_helper_goal_audit.py --dev-dir $outRoot --allow-blocked" in script


def test_solteria_sandbox_path_guard_rejects_live_client_aliases():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "function Assert-SandboxClientPath" in script
    assert "$rootWithSeparator = $root + [System.IO.Path]::DirectorySeparatorChar" in script
    assert "-not $full.Equals($root, [System.StringComparison]::OrdinalIgnoreCase)" in script
    assert "-not $full.StartsWith($rootWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)" in script
    assert "$sourceWithSeparator = $sourceFull + [System.IO.Path]::DirectorySeparatorChar" in script
    assert "$sandboxFull.Equals($sourceFull, [System.StringComparison]::OrdinalIgnoreCase)" in script
    assert "$sandboxFull.StartsWith($sourceWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)" in script
    assert "Refusing to treat SourceClient as sandbox" in script
    assert "$sandboxRoot = Assert-SandboxClientPath -SandboxPath $SandboxClient -SourcePath $SourceClient" in script

    smoke_attach_source = script[
        script.index("function Invoke-SmokeAttach"):
        script.index("function Invoke-SmokeAttachAll")
    ]
    assert smoke_attach_source.index("Assert-SandboxClientPath") < smoke_attach_source.index("Sync-CtoaRuntimeFiles")


def test_solteria_updated_client_boot_hook_is_controlled():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "function Ensure-CtoaBootHook" in script
    assert "-- CTOA-BOOT-BEGIN" in script
    assert "ctoa_boot.log" in script
    assert "local loader = '/ctoa_otclient_loader.lua'" in script
    assert "local ctoaOriginalLoadModules = loadModules" in script
    assert "local result = ctoaOriginalLoadModules(...)" in script
    assert "$content.Replace($needle, $hook + $needle)" in script

    sandbox_source = script[script.index("function Initialize-Sandbox"):script.index("function Invoke-SmokePreflight")]
    assert "Ensure-CtoaBootHook -ClientDir $sandboxRoot" in sandbox_source
    assert 'Join-Path $sandboxRoot "ctoa_boot.log"' in sandbox_source

    backup_source = script[script.index("function New-LiveCtoaBackup"):script.index("function Assert-LiveDeployApproved")]
    assert '@("init.lua") + (Get-DevPackageFiles) + (Get-LiveRootFallbackFiles)' in backup_source

    promotion_source = script[script.index("function Invoke-LivePromotion"):script.index("function Capture-Screenshot")]
    assert "Ensure-CtoaBootHook -ClientDir $SourceClient" in promotion_source
    assert "function Get-LiveRootFallbackFiles" in script
    assert "ctoa_native_helper.lua" in script
    assert "Get-LiveRootFallbackFiles" in promotion_source
    assert "Remove-Item -LiteralPath $fallbackPath -Force" in promotion_source
    assert "removed_root_fallbacks = $removedRootFallbacks" in promotion_source


def test_live_promotion_requires_explicit_approval_and_fresh_backup():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$ApproveLiveDeploy" in script
    assert "[switch]$LaunchAfterPromote" in script
    assert '[string]$SmokeReport = ""' in script
    assert "function New-LiveCtoaBackup" in script
    assert "backup_manifest.json" in script
    assert "function Assert-LiveDeployApproved" in script
    assert "Refusing live promotion without explicit approval" in script
    assert "function Assert-ReleaseGateForLivePromotion" in script
    assert "--approved" in script
    assert "--smoke-report" in script
    assert "Refusing live promotion because release_gate is not passed" in script
    assert "function Invoke-LivePromotion" in script
    assert "Assert-LiveDeployApproved" in script
    promotion_source = script[script.index("function Invoke-LivePromotion"):script.index("function Capture-Screenshot")]
    assert "Invoke-DevValidation" not in promotion_source
    assert "Invoke-SmokePreflight" not in promotion_source
    assert "Checking existing release gate for staged package before live promotion." in promotion_source
    assert "Assert-ReleaseGateForLivePromotion -OutRoot $outRoot" in script
    assert script.index("Assert-ReleaseGateForLivePromotion -OutRoot $outRoot") < script.index("$backupRoot = New-LiveCtoaBackup")
    assert "$backupRoot = New-LiveCtoaBackup" in script
    assert "Copy-Item -LiteralPath $sourcePath -Destination $destPath -Force" in script
    assert "function Assert-LivePromotionMatchesStage" in script
    assert "Promotion verification failed: live file is missing" in script
    assert "Promotion verification failed: SHA256 mismatch" in script
    assert "$verifiedFileCount = Assert-LivePromotionMatchesStage -Stage $stage -LiveClient $SourceClient" in promotion_source
    assert 'verification = "stage_live_sha256_match"' in promotion_source
    assert "Ensure-CtoaBootHook -ClientDir $SourceClient" in script
    assert 'launch_after_promote = $LaunchAfterPromote.IsPresent' in promotion_source
    assert 'status = "not_requested"' in promotion_source
    assert "live_promotion.json" in script
    assert '"BackupLiveCtoa" {' in script
    assert '"PromoteLiveCtoa" {' in script


def test_live_promotion_launch_after_promote_is_explicit_and_non_restart():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "function Start-LiveClientAfterPromotion" in script
    launch_source = script[
        script.index("function Start-LiveClientAfterPromotion"):
        script.index("function Get-DevPackageFiles")
    ]
    assert "Get-SourceClientProcessSummaries" in launch_source
    assert 'status = "already_running"' in launch_source
    assert "Start-Process -FilePath $exe -WorkingDirectory $sourceRoot -PassThru" in launch_source
    assert "Stop-Process" not in launch_source
    assert "Restart" not in launch_source

    promotion_source = script[
        script.index("function Invoke-LivePromotion"):
        script.index("function Capture-Screenshot")
    ]
    assert "if ($LaunchAfterPromote)" in promotion_source
    assert "Start-LiveClientAfterPromotion" in promotion_source
    assert "Use -LaunchAfterPromote to launch the live client after promotion" in promotion_source
    assert "it does not stop or restart the live client" in promotion_source


def test_live_emergency_repair_is_audited_and_removes_root_fallback():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "EmergencyRepairLiveCtoa" in script
    assert "function Invoke-LiveEmergencyRepair" in script
    emergency_source = script[
        script.index("function Invoke-LiveEmergencyRepair"):
        script.index("function Capture-Screenshot")
    ]
    assert "New-LiveCtoaBackup" in emergency_source
    assert "release_gate_bypassed = $true" in emergency_source
    assert "EmergencyRepairLiveCtoa" in emergency_source
    assert "Get-LiveRootFallbackFiles" in emergency_source
    assert "Remove-Item -LiteralPath $fallbackPath -Force" in emergency_source
    assert "Ensure-CtoaBootHook -ClientDir $SourceClient" in emergency_source
    assert "live_emergency_repair.json" in emergency_source
    assert "does not stop or restart the live client" in emergency_source
    assert '"EmergencyRepairLiveCtoa" {' in script


def test_helper_logs_subtab_smoke_markers():
    source = HELPER.read_text(encoding="utf-8")

    assert "smoke_subtab" in source
    assert 'smokeLabel = smokeLabel .. "/" .. tostring(Helper.smoke_subtab)' in source


def test_helper_supports_runtime_smoke_command_file():
    source = HELPER.read_text(encoding="utf-8")
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "ctoa_smoke_command.lua" in source
    smoke_path_start = source.index("local function getSmokeCommandPath()")
    smoke_path_end = source.index("local function getDiagnosticsExportPath()")
    smoke_path_source = source[smoke_path_start:smoke_path_end]
    assert 'string.sub(Helper.ui_path, 1, 1) ~= "/"' in smoke_path_source
    assert 'return workDir .. "ctoa_smoke_command.lua"' in smoke_path_source
    assert 'g_resources.getWorkDir() .. "mods/ctoa_otclient/ctoa_smoke_command.lua"' not in smoke_path_source
    assert "processSmokeCommand()" in source
    assert "parseSmokeCommandText" in source
    assert "pcall(readSmokeCommand, path)" in source
    assert "applySmokeCommand(command)" in source
    assert 'action == "cavebot_probe"' in source
    assert 'action == "cavebot_test_walk"' in source
    assert 'action == "magic_probe"' in source
    assert 'action == "api_probe"' in source
    assert 'action == "diag_export"' in source
    assert 'moduleValue(externalDiagnostics, "smokeCommandExists", path, g_resources, io)' in source
    assert "loadfile" not in source
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    assert "Smoke command blocked: " not in source
    assert "Smoke command failed: " not in source
    assert "Smoke command blocked: " in diagnostics
    assert "Smoke command failed: " in diagnostics
    write_command = script[
        script.index("function Write-SmokeCommand"):
        script.index("function Sync-CtoaRuntimeFiles")
    ]
    assert "tab=$ActiveTab" in write_command
    assert "subtab=$SmokeSubtab" in write_command
    assert "return {" not in write_command


def test_helper_otclient_architecture_hooks_are_registered():
    source = HELPER.read_text(encoding="utf-8")

    assert 'local HELPER_VERSION = "v2.2.1"' in source
    assert 'io.open("ctoa_local.log", "a")' in source
    assert 'g_resources.getUserDir()' in source
    assert 'userDir .. "/ctoa_local.log"' in source
    assert 'status("Initialized successfully " .. HELPER_VERSION)' in source
    assert "g_keyboard.bindKeyDown(normalizedHotkey, Helper.toggleWindow or toggleWindow)" in source
    assert "Helper.think_event = cycleEvent(onThink, HELPER_CONFIG.tick_ms)" in source
    assert "function ensureCTOAManager()" in source
    assert 'CTOA_Manager:registerModule("helper", {' in source
    assert "enabled = Helper.config.enabled" in source
    assert "onThink = function() Helper:onThink() end" in source


def test_loader_is_helper_ui_only_and_loads_without_online_gate():
    source = LOADER.read_text(encoding="utf-8")

    assert 'version = "2.2.1"' in source
    assert 'mode = "helper-ui-only"' in source
    assert 'local HELPER_MODULE = "ctoa_native_helper.lua"' in source
    assert 'local BOOTSTRAP_MODULE = {name = "ctoa_helper_modules", file = "ctoa_helper_modules.lua"}' in source
    assert "local function supportManifest()" in source
    assert "registry.getSupportModules()" in source
    assert "registry.validateSupportModules(modules)" in source
    assert "for _, module in ipairs(modules) do" in source
    assert "local function loadSupportModules(moduleDir)" in source
    assert "local function loadSupportModulesFromFilesystem()" in source
    assert "loadSupportModules(moduleDir)" in source
    assert "loadSupportModulesFromFilesystem()" in source
    assert "onGameStart = onGameStart" in source
    assert "scheduleHelperLoad()" in source
    assert "loadHelperOnly()" in source
    assert "loadHelperFromFilesystem" in source
    assert "local function bootLog(msg)" in source
    assert "bootLog(msg)" in source
    assert 'g_resources.getWorkDir() .. "mods/ctoa_otclient/" .. HELPER_MODULE' in source
    assert 'g_resources.getWorkDir() .. "mods/ctoa_otclient/",' in source
    assert "user_dir/ctoa_otclient/" not in source
    assert "g_resources.getWorkDir() .. HELPER_MODULE" not in source
    assert "g_resources.getWorkDir()," not in source
    assert 'log("Resource helper path not resolved; trying filesystem fallback")' in source
    assert 'log("Deferred helper load: game is not online")' not in source
    assert 'log("CTOA loader armed; waiting for game start")' not in source
    assert "if isOnline() then" not in source
    assert "initializeCTOA()" not in source
    assert "loadRuntimeModules()" not in source.split("CTOA_OTCLIENT.loadRuntimeModules", 1)[0]
    assert "Initialization complete: helper UI loaded; runtime modules skipped" in source


def test_helper_safe_boot_disables_runtime_automation():
    source = HELPER.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")
    loot = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_loot.lua").read_text(encoding="utf-8")

    assert "safe_boot_runtime_disabled = true" in source
    assert "local function applySafeBootRuntimeGuard()" in source
    assert "local function runtimeArmingBlockedReason()" in source
    assert 'return "safe boot runtime disabled"' in source
    assert "Runtime arm blocked: " in source
    assert "Runtime module blocked: " in source
    assert "HELPER_CONFIG.tools.auto_attack = false" in source
    assert "processSmokeCommand()\n    if not HELPER_CONFIG.enabled then" in source
    assert "\n    enabled = false," in profile
    assert "\n    safe_boot_runtime_disabled = true," in profile
    assert "auto_attack = false" in profile
    assert "auto_open_corpses = false" in loot
    assert "enabled = false" in loot
    assert "experimental_loot == true" in loot


def test_otprofile_builder_emits_safe_boot_profile_shape():
    profile = profile_builder.default_profile()
    rendered = profile_builder.render_profile(profile)

    assert "\n    enabled = false," in rendered
    assert "\n    safe_boot_runtime_disabled = true," in rendered
    assert "\n    heal_friend = {" in rendered
    assert "friend_scan_range = 7" in rendered
    assert "observed_count = 0" in rendered
    assert "\n    conditions = {" in rendered
    assert "\n    equipment = {" in rendered
    assert "api_probe_enabled = true" in rendered
    assert "\n    scripting = {" in rendered
    assert "runtime_enabled = false" in rendered
    assert "auto_attack = false" in rendered
    assert "block_friendly_summons = true" in rendered
    assert "friendly_summon_name_fragments" in rendered
    assert "auto_exeta = false" in rendered
    assert "potion_actionbar_slot = \"F1\"" in rendered
    assert "mana_potion_enabled = true" in rendered
    assert "rune_enabled = false" in rendered
    assert "cavebot_movement_enabled = false" in rendered


def test_helper_runtime_arming_has_pz_and_non_monster_guards():
    source = HELPER.read_text(encoding="utf-8")

    assert "local function runtimeBlockedReason(now)" in source
    assert "clearUnsafeCurrentTarget(blocked, now, true)" in source
    assert 'clearUnsafeCurrentTarget("non-monster target", now)' in source
    assert 'throttledRuntimeStatus("Runtime blocked: " .. blocked, now)' in source
    assert '"Runtime armed"' in source
    assert "externalTargeting.creatureTypeDecision" in source
    assert 'pcallOptionalBool(creature, "isNpc")' in source
    assert 'pcallOptionalBool(creature, "isPlayer")' in source
    assert "return result == true" in source
    assert "clearUnsafeCurrentTarget = function(reason, now, forceClear)" in source
    assert "if not forceClear and localPlayer and isMonsterCreature(target, localPlayer) and isTargetInRange(target, HELPER_CONFIG.tools.attack_range or 7) then" in source
    assert "local states = pcallNumber(player, \"getStates\")" in source
    assert "observation.tile_flags = pcallNumber(tile, \"getFlags\")" in source
    assert 'moduleValue(externalRuntimePolicy, "resolvedProtectionZonePolicy")' in source
    assert 'moduleValue(externalRuntimePolicy, "protectionZoneDecision", observation)' in source
    assert "local function runtimePolicyProtectionZonePolicy()" not in source
    assert "local function runtimePolicyProtectionZoneDecision(observation)" not in source
    assert "function RuntimePolicy.resolvedProtectionZonePolicy" in RUNTIME_POLICY.read_text(encoding="utf-8")
    assert "collectNumericFlags(data.state_flag_values, data.state_flag_fallbacks)" in RUNTIME_POLICY.read_text(encoding="utf-8")


def test_helper_targeting_on_executes_safe_monster_retarget():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")
    targeting = TARGETING.read_text(encoding="utf-8")

    assert "local function findBestAttackTarget(tools)" in source
    assert "local function retargetSafeMonster(now, tools)" in source
    assert "target = retargetSafeMonster(now, tools) or getSafeAttackTarget" in source
    assert "pcall(function() g_game.attack(target) end)" in source
    assert "pcall(function() g_game.follow(target) end)" not in source
    assert "tools.retarget_delay_ms or 200" in source
    assert "isMonsterCreature(creature, localPlayer)" in source
    assert "block_friendly_summons = true" in source
    assert "block_friendly_summons = true" in profile
    assert "friendly_summon_name_fragments" in source
    assert "friendly_summon_name_fragments" in profile
    assert "local function isFriendlySummonCreature(creature, localPlayer)" in source
    assert "isFriendlySummonCreature(target, getLocalPlayer())" in source
    assert "is_friendly_summon = isFriendlySummonCreature(creature, localPlayer)" in source
    assert '"isSummon"' in source
    assert '"isFamiliar"' in source
    assert 'clearUnsafeCurrentTarget("friendly summon/familiar target", now, true)' in source
    assert 'throttledRuntimeStatus(combatRuntimeText("targetingStatusText", "friendly_summon"), now)' in source
    assert 'function CombatRuntime.targetingStatusText(event, data)' in COMBAT_RUNTIME.read_text(encoding="utf-8")
    assert "function Targeting.isFriendlySummonName" in targeting
    assert "function Targeting.isFriendlySummonCandidate" in targeting
    assert 'reason = "friendly_summon"' in targeting
    assert "owns_friendly_summon_guard = true" in targeting
    assert 'throttledRuntimeStatus(combatRuntimeText("targetingStatusText", "no_valid_target"), now)' in source
    assert "local function applyChaseMode(enabled)" in source
    assert "g_game.setChaseMode(chaseMode)" in source
    assert "applyChaseMode(tools.chase == true)" in source
    assert "chase = true" in source
    assert "chase = true" in profile
    assert "auto_follow = false" in source
    assert "auto_follow = false" in profile
    assert '"ctoaChaseTargeting", "Chase"' in ui_module
    assert 'id = "ctoaChaseTools", label = "Chase mode"' in ui_module
    assert '"Chase/follow"' not in source
    assert '"Auto Follow"' not in source


def test_helper_blocks_npc_icons_and_known_npc_names_before_attack():
    source = HELPER.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")
    targeting = TARGETING.read_text(encoding="utf-8")

    assert "block_npc_icons = true" in source
    assert "local function creatureHasBlockingNpcIcon(creature)" in source
    assert 'moduleValue(externalTargeting, "hasBlockingNpcIcon", creature, HELPER_CONFIG.tools)' in source
    assert "pcall(externalTargeting.hasBlockingNpcIcon" not in source
    assert "function Targeting.hasBlockingNpcIcon" in targeting
    assert "return creature:getIcon()" in targeting
    assert "creatureHasBlockingNpcIcon(creature)" in source
    for name in ["hireling", "selmir", "andrew", "brumgar"]:
        assert f'"{name}"' in source
        assert f'"{name}"' in profile


def test_runtime_modules_auto_arm_helper_runtime():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")

    assert "function armRuntime(reason)" in source
    assert "setWidgetChecked(Helper.widgets.enabled, true)" in source
    assert "Helper.setRuntimeModuleEnabled = function(path, value, reason)" in source
    assert 'helper.setRuntimeModuleEnabled({"tools", "auto_attack"}, value, "targeting")' in ui_module
    assert 'helper.setRuntimeModuleEnabled({"healing", "spell_enabled"}, value, "spell healing")' in ui_module
    assert 'helper.setRuntimeModuleEnabled({"tools", "spell_rotation"}, value, "spell rotation")' in ui_module
    assert 'helper.setRuntimeModuleEnabled({"tools", "rune_enabled"}, value, "rune shooter")' in ui_module
    assert 'moduleValue(externalHud, "disarmedText")' in source
    assert 'setHudText(type(disarmedText) == "string" and disarmedText ~= "" and disarmedText or "HUD module unavailable | runtime disarmed")' in source


def test_healing_and_magic_cards_expose_actionbar_box_controls():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")

    assert '"ctoaSpellHeal", "HP spell"' in ui_module
    assert '"ctoaPotionHeal", "HP potion"' in ui_module
    assert '"ctoaPotionHotkeyHealing", "HP box"' in ui_module
    assert '"ctoaManaPotionHeal", "MP potion"' in ui_module
    assert '"ctoaManaPotionThresholdHealing", "MP pot %"' in ui_module
    assert '"ctoaManaPotionHotkeyHealing", "MP box"' in ui_module
    assert "healing.potion_actionbar_slot = value" in ui_module
    assert "healing.mana_potion_actionbar_slot = value" in ui_module
    assert "tools.rune_actionbar_slot = value" in ui_module
    assert '"ctoaRotationGranMobs", "Gran mobs"' in ui_module
    assert '"ctoaRotationExoriMobs", "Exori mobs"' in ui_module
    assert '"ctoaRotationMinMobs", "Min mobs"' in ui_module
    assert '"ctoaRotationLockMs", "Spell lock"' in ui_module
    assert '"ctoaRuneHotkeyMagic", "Rune box"' in ui_module
    assert '"Decision: waiting for runtime"' in ui_module
    assert '"Magic " .. HELPER_VERSION .. ": "' in source
    assert "HUD module unavailable | runtime gated" in source


def test_actionbar_slots_are_the_runtime_source_for_potions_and_runes():
    source = HELPER.read_text(encoding="utf-8")

    assert "local function resolveActionbarSlot(primarySlot, fallbackHotkey)" in source
    assert "local function sendActionbarSlot(primarySlot, fallbackHotkey)" in source
    assert "local function actionbarSlotText(slot)" not in source
    assert "sendActionbarSlot(healing.potion_actionbar_slot, healing.potion_hotkey)" in source
    assert "sendActionbarSlot(healing.mana_potion_actionbar_slot, healing.mana_potion_hotkey)" in source
    assert "sendActionbarSlot(tools.rune_actionbar_slot, tools.rune_hotkey)" in source
    assert 'moduleValue(externalHotkeys, "actionbarSlotText", slot) or "actionbar ?"' in source
    assert 'moduleValue(externalHotkeys, "actionbarSlotText", runeSlot) or "actionbar ?"' in source
    assert '"Potion heal via " .. slotText .. " at " .. hp .. "%"' in source
    assert '"Mana potion via " .. slotText .. " at " .. mp .. "%"' in source
    assert "slot_text = slotText" in source
    assert "sendHotkey(healing.potion_hotkey)" not in source
    assert "healing.mana_potion_hotkey or healing.mana_potion_actionbar_slot" not in source
    assert "tools.rune_hotkey or tools.rune_actionbar_slot" not in source


def test_rotation_debug_reports_runtime_decision_reasons():
    source = HELPER.read_text(encoding="utf-8")
    combat_runtime = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua").read_text(encoding="utf-8")

    assert "local function scanCombatArea(tools)" in source
    assert "local function rotationWaitReason(tools, target, scan, now)" in source
    assert "local function combatDecisionStateText(tools, target, scan, now, nextAction)" in source
    assert 'moduleValue(externalCombatRuntime, "waitReason", {' in source
    assert 'moduleValue(externalCombatRuntime, "decisionStateSummary", tools' in source
    assert 'moduleValue(externalCombatRuntime, "offensiveAction", tools' in source
    assert 'moduleValue(externalCombatRuntime, "runeReady", tools' in source
    assert "function CombatRuntime.offensiveAction" in combat_runtime
    assert "function CombatRuntime.runeReady" in combat_runtime
    assert "function CombatRuntime.rotationSpellRows" in combat_runtime
    assert "function CombatRuntime.spellReadiness" in combat_runtime
    assert "function CombatRuntime.rotationSpell" in combat_runtime
    assert "function CombatRuntime.actionStatusText" in combat_runtime
    assert "function CombatRuntime.nextActionText" in combat_runtime
    assert "function CombatRuntime.decisionStateSummary" in combat_runtime
    assert '"Wait: action lock "' in combat_runtime
    assert '"Wait: rotation interval"' in combat_runtime
    assert '"Wait: mobs " .. tostring(state.nearby or 0)' in combat_runtime
    assert 'local targetText = state.target_present and "target=monster" or "target=none"' in combat_runtime
    assert '" | " .. targetText' in combat_runtime
    assert '" | lock " .. CombatRuntime.msLeftText' in combat_runtime
    assert '" | exeta " .. exetaState' in combat_runtime
    assert '" | rune " .. runeState' in combat_runtime
    assert "owns_decision_state_summary = true" in combat_runtime
    assert '"Offensive action blocked: " .. tostring(env.reason' in combat_runtime
    assert '"Auto exeta: " .. tostring(item.spell' in combat_runtime
    assert '"Rotation: " .. tostring(spell.words' in combat_runtime
    assert '"Rune: " .. tostring(env.rune_name' in combat_runtime
    assert "local scan = scanCombatArea(tools)" in source
    assert "planNextCombatAction(target, scan, now)" in source
    assert 'moduleValue(externalCombatRuntime, "nextActionText", action, fallback)' in source
    assert 'moduleValue(externalCombatRuntime, "rotationSpellRows", tools.rotation_spells' in source
    assert 'moduleValue(externalCombatRuntime, "spellReadiness", spells' in source
    assert 'moduleValue(externalCombatRuntime, "rotationSpell", spells' in source
    assert "local function monsterCountForRange" not in source
    assert "local function monsterCountForSpell" not in source
    assert "local decisionState = combatDecisionStateText(tools, target, scan, now, nextAction)" in source
    assert 'Helper.widgets.magic_footer:setText(fitText("Magic " .. HELPER_VERSION' in source


def test_combat_action_selection_lives_in_passive_runtime_adapter():
    source = HELPER.read_text(encoding="utf-8")
    combat_runtime = COMBAT_RUNTIME.read_text(encoding="utf-8")

    build_start = source.index("local function buildOffensiveAction(tools, target, scan, now)")
    build_end = source.index("local function executeOffensiveAction(tools, action, nearby, visible, now)")
    build_source = source[build_start:build_end]

    assert 'moduleValue(externalCombatRuntime, "offensiveAction", tools' in build_source
    assert 'moduleValue(externalCombatRuntime, "runeReady", tools' in source
    assert 'moduleValue(externalCombatRuntime, "rotationSpellRows", tools.rotation_spells' in source
    assert 'moduleValue(externalCombatRuntime, "rotationSpell", spells' in source
    assert "spellReady(tools" not in source
    assert 'return {kind = "rune"}' not in build_source
    assert 'kind = "exeta"' not in build_source
    assert 'kind = "rotation"' not in build_source
    assert 'return {kind = "rune"}' in combat_runtime
    assert 'kind = "exeta"' in combat_runtime
    assert 'kind = "rotation"' in combat_runtime
    assert "castSpell(" not in combat_runtime
    assert "sendActionbarSlot" not in combat_runtime
    assert "g_game" not in combat_runtime
    assert "g_map" not in combat_runtime


def test_offensive_actions_are_pz_aware_and_rate_limited_at_execution():
    source = HELPER.read_text(encoding="utf-8")

    start = source.index("local function executeOffensiveAction(tools, action, nearby, visible, now)")
    end = source.index("local function planNextCombatAction(target, scan, now)")
    execute_source = source[start:end]

    assert "local blocked = combatBlockedReason(tools)" in execute_source
    assert 'status(combatRuntimeText("actionStatusText", {kind = "blocked", reason = blocked}' in execute_source
    assert "now < (tools.attack_action_lock_until_ms or 0)" in execute_source
    assert 'status(combatRuntimeText("actionStatusText", {kind = "action_lock"}' in execute_source
    assert "recoveryActionGap(now).active" in execute_source
    assert 'status(combatRuntimeText("actionStatusText", {kind = "recovery_gap"}' in execute_source
    assert '"Offensive action blocked: " .. blocked' not in execute_source
    assert '"Offensive action blocked: action lock"' not in execute_source
    assert '"Offensive action blocked: recovery gap"' not in execute_source
    assert '"Auto exeta: " .. action.spell' not in execute_source
    assert '"Rotation: " .. action.spell.words' not in execute_source
    assert '"Rune: " .. (tools.rune_name or "rune")' not in execute_source
    plan_start = source.index("local function planNextCombatAction(target, scan, now)")
    plan_end = source.index("local function combatDecisionStateText(tools, target, scan, now, nextAction)")
    plan_source = source[plan_start:plan_end]
    assert '"Next: " .. action.spell' not in plan_source
    assert '"Next: rune/AoE"' not in plan_source
    assert '"Next: " .. action.spell.words' not in plan_source
    assert "lockOffensiveAction(tools, now)" in execute_source
    assert "tools.last_exeta_ms = now" in execute_source
    assert "tools.last_spell_casts[action.spell.words] = now" in execute_source
    assert "tools.last_rune_ms = now" in execute_source


def test_magic_v11b_has_safe_api_probe():
    source = HELPER.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")

    assert "magic_api_probe_enabled = true" in source
    assert "magic_api_probe_enabled = true" in profile
    assert "function runMagicApiProbe(reason)" in source
    assert "Magic API probe (" in diagnostics
    assert 'moduleValue(externalDiagnostics, "magicApiProbeText"' in source
    assert "talk=\" .. Diagnostics.apiText(data.game, \"talk\")" in diagnostics
    assert "useInventoryItemWith=\" .. Diagnostics.apiText(data.game, \"useInventoryItemWith\")" in diagnostics
    assert "findItemInContainers=\" .. Diagnostics.apiText(data.game, \"findItemInContainers\")" in diagnostics
    magic_probe_start = source.index("function runMagicApiProbe(reason)")
    magic_probe_end = source.index("function refreshCavebotUi()")
    magic_probe_source = source[magic_probe_start:magic_probe_end]
    assert '" talk=" .. boolText(g_game and g_game.talk)' not in magic_probe_source
    assert '" useInventoryItemWith=" .. boolText(g_game and g_game.useInventoryItemWith)' not in magic_probe_source
    assert '" findItemInContainers=" .. boolText(g_game and g_game.findItemInContainers)' not in magic_probe_source
    assert '" states=" .. tostring(data.states or "n/a") ..' in diagnostics
    assert '" tileFlags=" .. tostring(data.tile_flags or "n/a")' in diagnostics
    assert "Helper.magic_api_probe_attempts <= 120" not in magic_probe_source
    assert 'label = "Magic API"' in magic_probe_source
    assert "max_attempts = 120" in magic_probe_source
    assert "requires_position = true" in magic_probe_source
    assert "runMagicApiProbe(\"startup\")" in source
    assert "Helper.runMagicApiProbe = function()" in source
    assert "return runMagicApiProbe(\"manual\")" in source


def test_helper_v11b_has_central_api_registry_probe():
    source = HELPER.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")

    assert "api_probe_enabled = true" in source
    assert "api_probe_enabled = true" in profile
    assert "function hasApi(owner, methodName)" in source
    assert "function runApiProbe(reason)" in source
    assert "Helper.api_snapshot = snapshot" in source
    assert "function apiSnapshotText()" not in source
    assert "function refreshApiSnapshotUi()" in source
    assert "refreshApiSnapshotUi()" in source
    assert 'moduleValue(externalDiagnostics, "apiProbeText"' in source
    assert "API probe (" in diagnostics
    assert "API probe (" not in source
    assert "API probe detail:" in diagnostics
    assert "API probe detail:" not in source
    assert "runApiProbe(\"startup\")" in source
    assert 'label = "API"' in source
    assert "Helper.runApiProbe = function()" in source
    assert "return runApiProbe(\"manual\")" in source
    assert 'action == "api_probe"' in source
    for token in [
        'Diagnostics.apiText(player, "autoWalk")',
        'Diagnostics.apiText(map, "findPath")',
        'Diagnostics.apiText(game, "attack")',
        'Diagnostics.apiText(game, "talk")',
        'Diagnostics.apiText(ui, "createWidget")',
        'Diagnostics.apiText(keyboard, "bindKeyDown")',
        'Diagnostics.apiText(resources, "getUserDir")',
        'Diagnostics.apiText(container, "getItems")',
        'Diagnostics.apiText(game, "move")',
    ]:
        assert token in diagnostics


def test_helper_v11b_exposes_api_snapshot_in_tools_ui():
    source = HELPER.read_text(encoding="utf-8")
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")

    assert 'ctx.widgets.tools_api_snapshot = ctx.add_footer_strip(window, "ctoaToolsApiSnapshot", "API: pending probe"' in ui_module
    assert 'moduleValue(externalDiagnostics, "snapshotUiRows"' in source
    assert 'moduleValue(externalDiagnostics, "apiSnapshotText"' in source
    assert '"API " .. tostring(snapshot.version or version or "?")' in diagnostics


def test_helper_tools_diag_tab_exposes_api_and_feature_flags():
    source = HELPER.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "tools_diag" in source
    ui_module = UI_HELPERS.read_text(encoding="utf-8")
    assert 'function Ui.toolsSubtabs' in ui_module
    assert '{key = "tools_diag_tab", id = "ctoaToolsDiagTab", text = "Diag"' in ui_module
    assert 'ctx.add_subtab_buttons(window, "toolsSubtabs", "tools", panelX, bodyY, panelW)' in ui_module
    assert "ctx.add_table_headers(window, Ui.toolsTableHeaders(panelX, contentY, panelW))" in ui_module
    assert 'ctx.bind_click(ctx.widgets.tools_diag_tab, function() ctx.switch_tools_subtab("diag") end)' in ui_module
    assert 'setSectionVisible("tools_diag", Helper.active_tab == "tools" and Helper.active_tools_tab == "diag")' in source
    assert 'ctx.widgets.tools_diag_core = ctx.add_footer_strip(window, "ctoaToolsDiagCore", "API: pending probe"' in ui_module
    assert 'ctx.widgets.tools_diag_flags = ctx.add_footer_strip(window, "ctoaToolsDiagFlags", ctx.feature_flags_text()' in ui_module
    assert "function featureFlagsText()" not in source
    assert 'moduleValue(externalDiagnostics, "featureFlagsText"' in source
    assert "feature_flags = {" in source
    assert "experimental_cavebot = false" in source
    assert "experimental_loot = false" in source
    assert "experimental_combat = false" in source
    assert "feature_flags = {" in profile


def test_helper_bounded_diagnostics_export_is_wired():
    source = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "diagnostics_export_limit = 20" in source
    assert "diagnostics_sample_interval_ms = 5000" in source
    assert "diagnostics_export_limit = 20" in profile
    assert "diagnostics_sample_interval_ms = 5000" in profile
    assert 'return g_resources.getWorkDir() .. "mods/ctoa_otclient/ctoa_diag_export.lua"' in source
    assert "function recordDiagnosticsSnapshot(reason, snapshot)" in source
    assert 'moduleValue(externalDiagnostics, "recordSnapshot"' in source
    assert "while #nextBuffer > limit do" in diagnostics
    assert "table.remove(nextBuffer, 1)" in diagnostics
    assert "function exportDiagnosticsBuffer(reason)" in source
    assert 'moduleValue(externalDiagnostics, "exportBuffer"' in source
    assert '"-- ctoa_diag_export.lua\\n"' in diagnostics
    assert "samples = Helper.diagnostics_buffer or {}" in source
    assert "function maybeSampleDiagnostics(now)" in source
    assert 'return runApiProbe("sample")' in source
    assert "maybeSampleDiagnostics(now)" in source
    assert 'action == "diag_export"' in source
    assert "Helper.exportDiagnostics = function()" in source
    for token in [
        "player = snapshot.player",
        "movement = snapshot.movement",
        "combat = snapshot.combat",
        "magic = snapshot.magic",
        "loot = snapshot.loot",
    ]:
        assert token in diagnostics


def test_recovery_actions_do_not_hard_stop_targeting_or_rotation():
    source = HELPER.read_text(encoding="utf-8")
    combat_runtime = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua").read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "local function recoveryActionGap(now)" in source
    assert 'moduleValue(externalRecoveryRuntime, "actionGap", now, lastActionMs, gapMs)' in source
    assert '"Wait: recovery gap "' in combat_runtime
    assert "if recentlyHealed(now)" not in source
    assert "maybeHeal(now, vitals)" in source
    assert "maybeManaPotion(now, vitals)" in source
    assert "maybeUseTools(now, vitals)" in source
    assert "mana_potion_enabled = true" in source
    assert "mana_potion_threshold = 45" in source
    assert "mana_potion_hotkey = \"F2\"" in source
    assert "mana_potion_enabled = true" in profile
    assert "recovery_action_gap_ms = 250" in source
    assert "recovery_action_gap_ms = 250" in profile


def test_timer_runtime_is_bounded_and_profile_persisted():
    source = HELPER.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")
    adapter = TIMER_RUNTIME.read_text(encoding="utf-8")

    assert "function maybeRunTimer(now)" in source
    assert "combatBlockedReason(tools)" in source
    assert 'rawget(_G, "CTOA_HELPER_TIMER_RUNTIME")' in source
    assert 'moduleValue(externalTimerRuntime, "plan", tools, context)' in source
    assert 'moduleValue(externalTimerRuntime, "summary", runtimePlan)' in source
    assert 'moduleValue(externalTimerRuntime, "dispatch", plan, tools, {' in source
    assert "pcall(externalTimerRuntime.plan" not in source
    assert "pcall(externalTimerRuntime.summary" not in source
    assert "pcall(externalTimerRuntime.dispatch" not in source
    assert '"Timer adapter: " .. adapterText' in adapter
    assert "math.max(1000, numberValue(cfg.timer_interval_ms, 60000))" in adapter
    timer_start = source.index("function maybeRunTimer(now)")
    timer_end = source.index("function maybeUseTools(now, vitals)")
    timer_source = source[timer_start:timer_end]
    assert "math.max(1000, tonumber(tools.timer_interval_ms) or 60000)" not in timer_source
    assert "now - (tools.last_timer_ms or 0) < interval" not in timer_source
    assert 'status(tostring(dispatch.status_text or ("Timer: " .. shortText(message, 32))))' in source
    assert "maybeRunTimer(now)" in source
    assert '"last_timer_ms"' in (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_persistence.lua").read_text(encoding="utf-8")
    assert "last_timer_ms = 0" in profile


def test_standalone_heal_and_loot_are_profile_fed_and_passive():
    heal = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_heal.lua").read_text(encoding="utf-8")
    loot = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_loot.lua").read_text(encoding="utf-8")

    assert "local DEFAULT_HEAL_SETTINGS = {" in heal
    assert "enabled = false" in heal
    assert 'local helper = rawget(_G, "CTOA_Helper")' in heal
    assert "helper.config.enabled == true" in heal
    assert "onHealthChanged = onHealthChanged" in heal
    assert "onManaChanged = onManaChanged" in heal
    assert "Heal.maybeRecover = maybeRecover" in heal

    assert "local LOOT_CONFIG = {" in loot
    assert "enabled = false" in loot
    assert 'local helper = rawget(_G, "CTOA_Helper")' in loot
    assert "flags.experimental_loot == true" in loot
    assert "local function sortedValuableItems(container)" in loot
    assert "lootScore(left) > lootScore(right)" in loot
    assert "Loot.scanOpenContainers = scanOpenContainers" in loot


def test_healing_spell_rotation_has_threshold_rules():
    source = HELPER.read_text(encoding="utf-8")
    adapter = RECOVERY_RUNTIME.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert "local function selectHealingSpell(healing, hp, now)" in source
    assert 'moduleValue(externalRecoveryRuntime, "selectHealingSpell", healing, hp, nonce)' in source
    assert "cfg.spell_rotation or {}" in adapter
    assert "threshold = 85" in profile
    assert "threshold = 55" in profile
    assert "threshold = 30" in profile


def test_helper_login_singleton_module_visibility_and_healing_jitter_contracts():
    source = HELPER.read_text(encoding="utf-8")
    loader = LOADER.read_text(encoding="utf-8")
    ui = UI_HELPERS.read_text(encoding="utf-8")
    recovery = RECOVERY_RUNTIME.read_text(encoding="utf-8")
    profile = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua").read_text(encoding="utf-8")

    assert 'local existingHelper = rawget(_G, "CTOA_Helper")' in source
    assert "return existingHelper" in source
    assert 'log("Game ended; helper singleton retained for next login")' in loader
    assert 'log("Game started; reused existing helper singleton")' in loader
    assert "CTOA_OTCLIENT.loaded = false" not in loader
    assert 'root:getChildById("ctoaNativeHelperWindow")' in source
    assert "function RecoveryRuntime.jitterThreshold" in recovery
    assert "threshold_jitter_percent = 3" in source
    assert "threshold_jitter_percent = 3" in profile
    assert '"ctoaProfilePotionName"' not in ui
    assert '"ctoaProfileRuneName"' not in ui
    for module_key in ["heal_friend", "conditions", "cavebot", "equipment", "helper", "scripting"]:
        assert f'key = "{module_key}"' in ui


def test_healing_uses_real_local_player_vitals_before_percent_fallback():
    source = HELPER.read_text(encoding="utf-8")
    adapter = RECOVERY_RUNTIME.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")

    assert "local function readPlayerVitals()" in source
    assert 'moduleValue(externalRecoveryRuntime, "normalizeVitals", snapshot)' in source
    assert 'source = "none"' in adapter
    assert '{field = "hp", method = "getHealth"}' in source
    assert '{field = "max_hp", method = "getMaxHealth"}' in source
    assert '{field = "mana", method = "getMana"}' in source
    assert '{field = "max_mana", method = "getMaxMana"}' in source
    assert "player[read.method](player)" in source
    assert 'vitals.source = "real"' in adapter
    assert 'vitals.source = "percent_api"' in adapter
    assert "local vitals = readPlayerVitals()" in source
    assert "maybeHeal(now, vitals)" in source
    assert "maybeManaPotion(now, vitals)" in source
    assert "local function getHealthPercent()" not in source
    assert "local function getManaPercent()" not in source
    assert "local function maybeHeal(now, vitals)" in source
    assert "function maybeManaPotion(now, vitals)" in source
    assert "function maybeUseTools(now, vitals)" in source
    assert "local vitals = readPlayerVitals()\n    maybeHeal(now, vitals)\n    maybeManaPotion(now, vitals)" in source
    assert "maybeUseTools(now, vitals)" in source
    assert '"vitals=" .. tostring(vitals.source or "none")' in diagnostics


def test_smoke_runner_supports_attach_without_restart():
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")

    assert "SmokeAttach" in script
    assert "SmokeAttachAll" in script
    assert "Write-SmokeCommand" in script
    assert "No running sandbox client window found for SmokeAttach" in script
    assert "If Select Character is visible, enter the character first" in script
    assert "Wait-ForSmokeTab -ActiveTab $resolved.Active -SmokeSubtab $resolved.Subtab -Required" in script
    assert "Get-SmokeLogLineCount" in script
    assert "-AfterLineCount $lineCountBeforeCommand" in script
    assert "[string]$RunId" in script
    assert "--prefix solteria-helper-attach --in-world" in script
    assert "[solteria-helper-test-env] Attach run id:" in script
    assert "Invoke-Snapshot" in script
    assert "solteria-helper-snapshot-" in script
    assert "Invoke-ReadyCheck" in script
    assert "function Write-ReadyCheckReport" in script
    assert "ready_check.json" in script
    assert "$moduleArray = @($modules.ToArray())" in script
    assert "blocked_no_sandbox_window" in script
    assert "blocked_by_character_modal_or_helper_offline" in script
    assert "Ready: in-world attach smoke can switch helper tabs." in script
    assert "Not ready: blocked_by_character_modal or helper not online." in script
    assert "Set-LiveCtoaEnabled" in script
    assert "Set-LiveCtoaUiOnly" in script
    assert "ctoa_otclient_loader.lua" in script

def boot_graph_source() -> str:
    return LOADER.read_text(encoding="utf-8") + "\n" + MODULE_REGISTRY.read_text(encoding="utf-8")


def boot_graph_has_module(source: str, name: str, file_name: str) -> bool:
    prefix = f'{{name = "{name}", file = "{file_name}"'
    return prefix + "}" in source or prefix + "," in source
