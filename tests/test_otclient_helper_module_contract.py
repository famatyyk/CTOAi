import json
import shutil
import subprocess
from pathlib import Path

from scripts.ops import otclient_helper_module_contract as contract


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
LOADER = OTCLIENT_DIR / "ctoa_otclient_loader.lua"
REGISTRY = OTCLIENT_DIR / "ctoa_helper_modules.lua"


def test_module_bridge_has_no_duplicate_domain_fallbacks_and_saves_fail_closed() -> None:
    helper = (OTCLIENT_DIR / "ctoa_native_helper.lua").read_text(encoding="utf-8")
    bridge = helper[helper.index("local function moduleCall") : helper.index("local externalLanes")]
    profile_save = helper[helper.index("flushProfileSave = function()") : helper.index("local PRIVILEGED_SMOKE_ACTIONS")]
    ui_save = helper[helper.index("flushUiPrefsSave = function()") : helper.index("local function markProfileDirty")]

    assert "elseif functionName" not in bridge
    assert "return 99999999" not in bridge
    assert 'status("Profile save blocked: required profile owner unavailable")' in profile_save
    assert 'status("UI prefs save blocked: required profile owner unavailable")' in ui_save
    assert profile_save.index('moduleValue(externalProfileSchema, "serializeLua"') < profile_save.index('io.open(path, "w")')
    assert ui_save.index('moduleValue(externalProfileSchema, "serializeLua"') < ui_save.index('io.open(path, "w")')


def test_extracted_route_targeting_and_cavebot_helpers_fail_closed_without_owner(
    tmp_path: Path,
):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for extracted-helper validation"
    helper_source = (OTCLIENT_DIR / "ctoa_native_helper.lua").read_text(
        encoding="utf-8"
    )
    bridge_start = helper_source.index("local function moduleCall")
    bridge_end = helper_source.index("local externalLanes")
    bridge_source = helper_source[bridge_start:bridge_end]
    probe = tmp_path / "route_targeting_cavebot_extraction_probe.lua"
    probe.write_text(
        bridge_source
        + r"""
local route = dofile(arg[1])
local targeting = dofile(arg[2])
local cavebot = dofile(arg[3])

assert(moduleValue(route, "distanceChebyshev", {x = 1, y = 1, z = 7}, {x = 4, y = 3, z = 7}) == 3)
assert(moduleValue(route, "distanceChebyshev", {x = 1, y = 1, z = 7}, {x = 4, y = 3, z = 8}) == nil)
assert(moduleValue(route, "posKey", {x = 10, y = 20, z = 7}) == "10:20:7")
assert(moduleValue(targeting, "creatureHasBlockingNpcIcon", 1, {block_npc_icons = true}) == true)
assert(moduleValue(targeting, "creatureHasBlockingNpcIcon", 0, {block_npc_icons = true}) == false)
assert(moduleValue(targeting, "isFriendlySummonName", "knight familiar", {block_friendly_summons = true}) == true)
assert(moduleValue(targeting, "targetCandidateScore", {name = "demon", distance = 2, hp = 50}, {priority_names = {"demon"}}) == 10250)
assert(moduleValue(cavebot, "cavebotRuntimeText", "statusText", "walk_retry", {retry_count = 2}) == "walk retry 2")
assert(moduleValue(cavebot, "cavebotRuntimeText", "missing", "event", {}, "fallback") == "fallback")
assert(moduleValue(cavebot, "cavebotRetryBudgetExceeded", {cavebot_retry_attempts = 3, cavebot_retry_limit = 3}) == true)
assert(moduleValue(cavebot, "cavebotRetryBudgetExceeded", {cavebot_retry_attempts = 2, cavebot_retry_limit = 3}) == false)

local malformed = {profileSchemaValue = "not-a-function", normalizeHelperHotkey = false, modalRequest = 7}
for _, name in ipairs({"displayProfileName", "profileSchemaValue", "profileSchemaTable", "profilePersistenceValue", "normalizeHelperHotkey", "hotkeyBindingDecision", "modalRequest", "mergeTable", "serializeLua", "exportProfile", "exportUiPrefs", "resolveActionbarSlot", "isFriendlySummonName"}) do
  assert(moduleValue(nil, name, "value") == nil)
  assert(moduleValue(malformed, name, "value") == nil)
end

assert(route.contract().owns_distance_chebyshev == true)
assert(targeting.contract().owns_target_candidate_score == true)
assert(cavebot.contract().owns_runtime_text_bridge == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            lua,
            str(probe),
            str(OTCLIENT_DIR / "ctoa_helper_route.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_targeting.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_cavebot_runtime.lua"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_extracted_combat_recovery_registry_and_ui_helpers_fail_closed_without_owner(
    tmp_path: Path,
):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for extracted-helper validation"
    helper_source = (OTCLIENT_DIR / "ctoa_native_helper.lua").read_text(
        encoding="utf-8"
    )
    bridge_start = helper_source.index("local function moduleCall")
    bridge_end = helper_source.index("local externalLanes")
    probe = tmp_path / "combat_recovery_registry_ui_extraction_probe.lua"
    probe.write_text(
        helper_source[bridge_start:bridge_end]
        + r"""
local recovery = dofile(arg[1])
local combat = dofile(arg[2])
local schema = dofile(arg[3])
local registry = dofile(arg[4])
local primitives = dofile(arg[5])
local ui = dofile(arg[6])
assert(primitives.contract().runtime_actions == false)

local gap = recovery.recoveryActionGap(1200, {last_recovery_action_ms = 1000}, {recovery_action_gap_ms = 250})
assert(gap.active == true and gap.until_ms == 1250 and gap.remaining_ms == 50)
assert(recovery.recoveryActionGap(1300, {last_recovery_action_ms = 1000}, {recovery_action_gap_ms = 250}).active == false)
local healing = {spell = "exura ico", critical_spell = "exura med ico", threshold_jitter_percent = 0, spell_rotation = {}}
assert(recovery.selectHealingSpell(healing, 20, 1) == "exura med ico")

local tools = {
  rotation_spells = {{words = "exori", min_nearby = 2, cooldown_ms = 1000}},
  rotation_scan_range = 1,
  last_spell_casts = {},
  rotation_interval_ms = 1000,
  attack_action_lock_until_ms = 0,
  last_attack_spell_ms = 0,
}
local spell = combat.selectRotationSpell(tools, {adjacent = 3}, 2000)
assert(type(spell) == "table" and spell.words == "exori")
assert(combat.runeReady({rune_enabled = true, rune_requires_target = true, rune_min_visible = 1, last_rune_ms = 0, rune_cooldown_ms = 1000}, {target_present = true, visible = 1, now_ms = 2000}) == true)

local formatter = schema.rotationPresetFormatter({{id = "smart", label = "Smart"}})
assert(formatter("smart") == "Smart" and formatter("custom") == "custom")
local summary = schema.rotationSummaryText({rotation_spells = {{words = "exori", min_nearby = 2}}}, {})
assert(string.find(summary, "Rotation:", 1, true) == 1)

local index = registry.rebuildModuleLaneIndex({{id = "combat"}, {id = "healing"}})
assert(index.combat.id == "combat" and index.healing.id == "healing")
assert(registry.moduleTabVisible("overview", {}, nil, {overview = true}) == true)
assert(registry.moduleTabVisible("conditions", {}, nil, {overview = true}) == false)
assert(registry.moduleTabVisible("conditions", {}, "conditions", {overview = true}) == true)
local context = ui.mergePanelRendererContext({a = 1, b = 1}, {b = 2, c = 3})
assert(context.a == 1 and context.b == 2 and context.c == 3)

assert(moduleValue(nil, "selectRotationSpell", tools, {adjacent = 3}, 2000) == nil)
for _, name in ipairs({"recoveryActionGap", "runeReady", "selectHealingSpell", "rotationSummaryText", "rotationPresetFormatter", "rebuildModuleLaneIndex", "moduleTabVisible", "mergePanelRendererContext"}) do
  assert(moduleValue(nil, name, {}) == nil)
end

assert(recovery.contract().owns_recovery_action_gap_bridge == true)
assert(combat.contract().owns_select_rotation_spell == true)
assert(schema.contract().owns_rotation_preset_formatter == true)
assert(registry.contract().owns_lane_index == true)
assert(ui.contract().owns_panel_renderer_context_merge == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            lua,
            str(probe),
            str(OTCLIENT_DIR / "ctoa_helper_recovery_runtime.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_combat_runtime.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_profile_schema.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_modules.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_ui_primitives.lua"),
            str(OTCLIENT_DIR / "ctoa_helper_ui.lua"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_module_contract_passes_current_passive_modules():
    report = contract.build_report(OTCLIENT_DIR, LOADER, REGISTRY)

    assert report.name == "otclient-helper-module-contract"
    assert report.status == "passed"
    assert report.expected_module_count == 36
    assert report.passed_count == 36
    assert report.failed_count == 0
    assert report.registry_lane_count == 9
    assert report.registry_missing == []
    assert report.loader_missing == []
    assert report.forbidden_count == 0
    assert "sandbox SmokeAttachModules" in report.next_action
    assert "does not launch" in report.live_safety


def test_module_contract_requires_loader_registry_global_and_return():
    report = contract.build_report(OTCLIENT_DIR, LOADER, REGISTRY)
    modules = {item.id: item for item in report.modules}

    for module_id in [
        "modules",
        "domain_contract",
        "rule_engine",
        "ui",
        "diagnostics",
        "hotkeys",
        "modal",
        "route",
        "targeting",
        "combat_runtime",
        "cavebot_runtime",
        "loot_runtime",
        "timer_runtime",
        "profile_schema",
        "profile_persistence",
        "operator_summary",
        "planner",
        "runtime_policy",
        "dispatch_guard",
        "plan_queue",
        "runtime_readiness",
        "module_status",
        "action_catalog",
        "decision_trace",
        "decision_pipeline",
        "sandbox_handoff",
        "feature_flags",
        "hud",
        "conditions",
        "equipment",
        "scripting",
        "heal_friend",
    ]:
        item = modules[module_id]
        assert item.status == "passed"
        assert item.loader_present
        assert item.registry_present
        assert item.global_present
        assert item.return_present
        assert item.missing_functions == []
        assert item.forbidden_hits == []

    registry_source = REGISTRY.read_text(encoding="utf-8")
    for function_name in [
        "getModuleLanes",
        "rebuildModuleLaneIndex",
        "getShortLabels",
        "moduleTabVisible",
        "getSupportModules",
        "validateSupportModules",
        "bootSnapshot",
        "bootSummary",
        "laneEnabled",
        "laneRuntimeText",
        "registrySummary",
        "readinessTag",
        "readinessRow",
        "contract",
    ]:
        assert f"function Registry.{function_name}" in registry_source
    assert "owns_lane_readiness = true" in registry_source
    assert "owns_lane_index = true" in registry_source
    assert "owns_module_tab_visibility = true" in registry_source
    assert "owns_lane_enabled = true" in registry_source
    assert "owns_lane_runtime_text = true" in registry_source
    assert "owns_registry_summary = true" in registry_source
    assert "owns_readiness_row = true" in registry_source
    assert "owns_boot_manifest = true" in registry_source
    assert "validates_boot_dependencies = true" in registry_source
    assert "owns_boot_status = true" in registry_source
    assert "runtime_actions = false" in registry_source

    diagnostics_source = (OTCLIENT_DIR / "ctoa_helper_diagnostics.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "boolText",
        "posText",
        "hasApi",
        "apiText",
        "valueText",
        "apiSnapshotText",
        "apiProbeSnapshot",
        "apiProbeText",
        "probeDeferredPlan",
        "magicApiProbeText",
        "featureFlagsText",
        "bufferText",
        "snapshotUiRows",
        "snapshotUiValues",
        "smokeCommandExists",
        "parseSmokeCommandText",
        "smokeCommandTarget",
        "smokeTabStatusText",
        "smokeCommandStatusText",
        "movementText",
        "magicLootText",
        "tableCount",
        "firstTableValue",
        "recordSnapshot",
        "exportBuffer",
        "contract",
    ]:
        assert f"function Diagnostics.{function_name}" in diagnostics_source
    assert "owns_bool_text = true" in diagnostics_source
    assert "owns_pos_text = true" in diagnostics_source
    assert "owns_api_text = true" in diagnostics_source
    assert "owns_value_text = true" in diagnostics_source
    assert "owns_api_snapshot_text = true" in diagnostics_source
    assert "owns_api_probe_snapshot = true" in diagnostics_source
    assert "owns_api_probe_text = true" in diagnostics_source
    assert "owns_probe_deferred_plan = true" in diagnostics_source
    assert "owns_magic_api_probe_text = true" in diagnostics_source
    assert "owns_feature_flags_text = true" in diagnostics_source
    assert "owns_buffer_text = true" in diagnostics_source
    assert "owns_snapshot_ui_rows = true" in diagnostics_source
    assert "owns_snapshot_ui_values = true" in diagnostics_source
    assert "owns_movement_text = true" in diagnostics_source
    assert "owns_magic_loot_text = true" in diagnostics_source
    assert "owns_table_count = true" in diagnostics_source
    assert "owns_first_table_value = true" in diagnostics_source
    assert "owns_smoke_command_exists = true" in diagnostics_source
    assert "owns_smoke_command_parse = true" in diagnostics_source
    assert "owns_smoke_command_target = true" in diagnostics_source
    assert "owns_smoke_status_text = true" in diagnostics_source
    assert "owns_smoke_command_status_text = true" in diagnostics_source
    assert "owns_record_snapshot = true" in diagnostics_source
    assert "owns_export_buffer = true" in diagnostics_source
    assert "runtime_actions = false" in diagnostics_source

    hotkeys_source = (OTCLIENT_DIR / "ctoa_helper_hotkeys.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "trim",
        "normalizeKeyName",
        "parse",
        "normalize",
        "isAllowed",
        "bindingDecision",
        "normalizeHelperHotkey",
        "hotkeyBindingDecision",
        "resolveActionbarSlot",
        "display",
        "actionbarSlotText",
        "contract",
    ]:
        assert f"function Hotkeys.{function_name}" in hotkeys_source
    assert 'local MODIFIER_ORDER = {"Ctrl", "Alt", "Shift", "Meta"}' in hotkeys_source
    assert 'reason = "multiple_keys"' in hotkeys_source
    assert 'reason = "missing_key"' in hotkeys_source
    assert 'reason = "reserved_key"' in hotkeys_source
    assert 'reason = "not_allowed"' in hotkeys_source
    assert "owns_actionbar_slot_text = true" in hotkeys_source
    assert "owns_binding_decision = true" in hotkeys_source
    assert "owns_hotkey_normalization = true" in hotkeys_source
    assert "owns_actionbar_slot_resolution = true" in hotkeys_source
    assert "binds_keys = false" in hotkeys_source
    assert "sends_keys = false" in hotkeys_source
    assert "runtime_actions = false" in hotkeys_source

    combat_runtime_source = (OTCLIENT_DIR / "ctoa_helper_combat_runtime.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "plan",
        "summary",
        "adapterSummary",
        "magicSummary",
        "msLeftText",
        "runeReady",
        "rotationSpellRows",
        "spellReadiness",
        "rotationSpell",
        "selectRotationSpell",
        "offensiveAction",
        "actionStatusText",
        "targetingStatusText",
        "nextActionText",
        "waitReason",
        "decisionState",
        "decisionStateSummary",
        "contract",
    ]:
        assert f"function CombatRuntime.{function_name}" in combat_runtime_source
    assert "owns_runtime_plan = true" in combat_runtime_source
    assert "owns_adapter_summary = true" in combat_runtime_source
    assert "owns_magic_summary = true" in combat_runtime_source
    assert "owns_magic_summary_text = true" in combat_runtime_source
    assert "owns_cooldown_text = true" in combat_runtime_source
    assert "owns_rune_ready = true" in combat_runtime_source
    assert "owns_rotation_spell_rows = true" in combat_runtime_source
    assert "owns_spell_readiness = true" in combat_runtime_source
    assert "owns_rotation_spell_selection = true" in combat_runtime_source
    assert "owns_select_rotation_spell = true" in combat_runtime_source
    assert "owns_offensive_action_selection = true" in combat_runtime_source
    assert "owns_action_status_text = true" in combat_runtime_source
    assert "owns_targeting_status_text = true" in combat_runtime_source
    assert "owns_next_action_text = true" in combat_runtime_source
    assert "owns_wait_reason_text = true" in combat_runtime_source
    assert "owns_decision_state_text = true" in combat_runtime_source
    assert "owns_decision_state_summary = true" in combat_runtime_source
    assert "runtime_actions = false" in combat_runtime_source
    assert "attacks = false" in combat_runtime_source
    assert "casts = false" in combat_runtime_source
    assert "uses_items = false" in combat_runtime_source

    ui_source = (OTCLIENT_DIR / "ctoa_helper_ui.lua").read_text(encoding="utf-8")
    for function_name in [
        "shortText",
        "configureLayout",
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
        "styleProfileField",
        "styleVectorRow",
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
        "addProfileCycleRow",
        "addProfileStepRow",
        "addVectorStepRow",
        "sectionBodyGeometry",
        "mergePanelRendererContext",
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
        "renderOverviewPanel",
        "updateOverviewStats",
        "renderCavebotPanel",
        "renderEnginePanel",
        "renderHuntingPanel",
        "renderProfilePanel",
        "renderToolsPanel",
        "contract",
    ]:
        assert f"function Ui.{function_name}" in ui_source
    assert "owns_text_fit = true" in ui_source
    assert "owns_widget_style = true" in ui_source
    assert "owns_widget_create_wrapper = true" in ui_source
    assert "owns_nav_style = true" in ui_source
    assert "owns_subtab_style = true" in ui_source
    assert "owns_button_style = true" in ui_source
    assert "owns_rule_card_style = true" in ui_source
    assert "owns_metric_style = true" in ui_source
    assert "owns_setting_state_style = true" in ui_source
    assert "owns_profile_field_style = true" in ui_source
    assert "owns_vector_row_style = true" in ui_source
    assert "owns_section_style = true" in ui_source
    assert "owns_strip_style = true" in ui_source
    assert "owns_badge_style = true" in ui_source
    assert "owns_label_style = true" in ui_source
    assert "owns_window_chrome_style = true" in ui_source
    assert "owns_toggle_style = true" in ui_source
    assert "owns_checkbox_style = true" in ui_source
    assert "owns_sidebar_card_style = true" in ui_source
    assert "owns_overview_avatar_style = true" in ui_source
    assert "owns_control_name_style = true" in ui_source
    assert "owns_layout_modes = true" in ui_source
    assert "owns_row_geometry = true" in ui_source
    assert "owns_metric_card_geometry = true" in ui_source
    assert "owns_metric_text_plan = true" in ui_source
    assert "owns_interactive_row_builders = true" in ui_source
    assert "owns_section_scaffold = true" in ui_source
    assert "owns_panel_renderer_context_merge = true" in ui_source
    assert "owns_tab_metadata = true" in ui_source
    assert "owns_subtab_content_metadata = true" in ui_source
    assert "owns_cavebot_action_metadata = true" in ui_source
    assert "owns_overview_panel_renderer = true" in ui_source
    assert "owns_overview_stats_update = true" in ui_source
    assert "owns_diagnostics_snapshot_update = true" in ui_source
    assert "owns_cavebot_panel_renderer = true" in ui_source
    assert "owns_engine_panel_renderer = true" in ui_source
    assert "owns_hunting_panel_renderer = true" in ui_source
    assert "owns_profile_panel_renderer = true" in ui_source
    assert "owns_tools_panel_renderer = true" in ui_source
    assert "runtime_actions = false" in ui_source
    assert "executes_plans = false" in ui_source
    assert "dispatch_allowed = false" in ui_source
    assert "casts = false" in ui_source
    assert "talks = false" in ui_source
    assert "attacks = false" in ui_source
    assert "walks = false" in ui_source
    assert "uses_items = false" in ui_source

    modal_source = (OTCLIENT_DIR / "ctoa_helper_modal.lua").read_text(encoding="utf-8")
    for function_name in [
        "request",
        "modalRequest",
        "isPending",
        "isExpired",
        "confirm",
        "cancel",
        "decision",
        "decisionText",
        "statusText",
        "buttonText",
        "contract",
    ]:
        assert f"function Modal.{function_name}" in modal_source
    assert "local DEFAULT_TTL_MS = 4500" in modal_source
    assert "promote_live = true" in modal_source
    assert 'reason = "confirmation_required"' in modal_source
    assert "creates_widgets = false" in modal_source
    assert "live_shortcuts = false" in modal_source
    assert "owns_modal_request = true" in modal_source
    assert "owns_decision_text = true" in modal_source
    assert "runtime_actions = false" in modal_source

    hud_source = (OTCLIENT_DIR / "ctoa_helper_hud.lua").read_text(encoding="utf-8")
    for function_name in [
        "startText",
        "disarmedText",
        "position",
        "state",
        "visibilityText",
        "runtimeText",
        "uiSummary",
        "operatorSummary",
        "contract",
    ]:
        assert f"function Hud.{function_name}" in hud_source
    assert "owns_start_text = true" in hud_source
    assert "owns_disarmed_text = true" in hud_source
    assert "owns_position = true" in hud_source
    assert "owns_runtime_text = true" in hud_source
    assert "owns_ui_summary = true" in hud_source
    assert "owns_operator_summary = true" in hud_source
    assert "creates_widgets = false" in hud_source
    assert "runtime_actions = false" in hud_source

    route_source = (OTCLIENT_DIR / "ctoa_helper_route.lua").read_text(encoding="utf-8")
    for function_name in [
        "distanceChebyshev",
        "position",
        "label",
        "posKey",
        "add",
        "clear",
        "select",
        "delete",
        "move",
        "retryStatus",
        "retryBlocked",
        "progress",
        "stats",
        "selectedSummary",
        "uiState",
        "deleteRequest",
        "contract",
    ]:
        assert f"function Route.{function_name}" in route_source
    assert "owns_waypoint_mutation = true" in route_source
    assert "owns_editor_state = true" in route_source
    assert "owns_distance_chebyshev = true" in route_source
    assert "owns_position_key = true" in route_source
    assert "owns_target_selection = true" in route_source
    assert "owns_retry_status = true" in route_source
    assert "owns_progress_state = true" in route_source
    assert "runtime_actions = false" in route_source
    assert "movement_enabled = false" in route_source
    assert "pathfinding = false" in route_source

    targeting_source = (OTCLIENT_DIR / "ctoa_helper_targeting.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "normalizedName",
        "isIgnoredName",
        "hasBlockingNpcIcon",
        "creatureHasBlockingNpcIcon",
        "isFriendlySummonName",
        "creatureTypeDecision",
        "priorityRank",
        "scoreCandidate",
        "targetCandidateScore",
        "bestCandidate",
        "decision",
        "summary",
        "configSummary",
        "contract",
    ]:
        assert f"function Targeting.{function_name}" in targeting_source
    assert "owns_target_score = true" in targeting_source
    assert "owns_best_candidate = true" in targeting_source
    assert "owns_creature_type_decision = true" in targeting_source
    assert "owns_ignored_names = true" in targeting_source
    assert "owns_npc_icon_guard = true" in targeting_source
    assert "owns_blocking_npc_icon_value = true" in targeting_source
    assert "owns_friendly_summon_name = true" in targeting_source
    assert "owns_target_candidate_score = true" in targeting_source
    assert "owns_config_summary = true" in targeting_source
    assert "owns_targeting_summary_text = true" in targeting_source
    assert "runtime_actions = false" in targeting_source
    assert "attacks = false" in targeting_source
    assert "casts = false" in targeting_source
    assert "creature_scan = false" in targeting_source

    combat_runtime_source = (OTCLIENT_DIR / "ctoa_helper_combat_runtime.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "plan",
        "summary",
        "adapterSummary",
        "magicSummary",
        "msLeftText",
        "runeReady",
        "rotationSpellRows",
        "spellReadiness",
        "rotationSpell",
        "selectRotationSpell",
        "offensiveAction",
        "actionStatusText",
        "targetingStatusText",
        "nextActionText",
        "contract",
    ]:
        assert f"function CombatRuntime.{function_name}" in combat_runtime_source
    assert "owns_runtime_plan = true" in combat_runtime_source
    assert "owns_adapter_summary = true" in combat_runtime_source
    assert "owns_magic_summary = true" in combat_runtime_source
    assert "owns_magic_summary_text = true" in combat_runtime_source
    assert "owns_cooldown_text = true" in combat_runtime_source
    assert "owns_rune_ready = true" in combat_runtime_source
    assert "owns_rotation_spell_rows = true" in combat_runtime_source
    assert "owns_spell_readiness = true" in combat_runtime_source
    assert "owns_select_rotation_spell = true" in combat_runtime_source
    assert "owns_offensive_action_selection = true" in combat_runtime_source
    assert "owns_action_status_text = true" in combat_runtime_source
    assert "owns_targeting_status_text = true" in combat_runtime_source
    assert "runtime_actions = false" in combat_runtime_source
    assert "scans_creatures = false" in combat_runtime_source
    assert "attacks = false" in combat_runtime_source
    assert "casts = false" in combat_runtime_source
    assert "uses_items = false" in combat_runtime_source
    assert "requires_target_scorer = true" in combat_runtime_source

    cavebot_runtime_source = (
        OTCLIENT_DIR / "ctoa_helper_cavebot_runtime.lua"
    ).read_text(encoding="utf-8")
    for function_name in [
        "plan",
        "summary",
        "decisionText",
        "adapterSummary",
        "adapterStatusText",
        "adapterStatusSummary",
        "movementCapability",
        "probeSnapshot",
        "probeSummary",
        "probeReport",
        "pathText",
        "movementBlockedReason",
        "walkPreflight",
        "testWalkPlan",
        "walkingStatus",
        "retryDecision",
        "statusText",
        "traceText",
        "cavebotRuntimeText",
        "cavebotRetryBudgetExceeded",
        "contract",
    ]:
        assert f"function CavebotRuntime.{function_name}" in cavebot_runtime_source
    assert "owns_runtime_plan = true" in cavebot_runtime_source
    assert "owns_decision_text = true" in cavebot_runtime_source
    assert "owns_adapter_summary = true" in cavebot_runtime_source
    assert "owns_adapter_status_text = true" in cavebot_runtime_source
    assert "owns_adapter_status_summary = true" in cavebot_runtime_source
    assert "owns_movement_capability = true" in cavebot_runtime_source
    assert "owns_probe_snapshot = true" in cavebot_runtime_source
    assert "owns_probe_summary_text = true" in cavebot_runtime_source
    assert "owns_probe_report = true" in cavebot_runtime_source
    assert "owns_blocked_reason_text = true" in cavebot_runtime_source
    assert "owns_walk_preflight = true" in cavebot_runtime_source
    assert "owns_test_walk_plan = true" in cavebot_runtime_source
    assert "owns_walking_status = true" in cavebot_runtime_source
    assert "owns_retry_decision = true" in cavebot_runtime_source
    assert "owns_status_text = true" in cavebot_runtime_source
    assert "owns_trace_text = true" in cavebot_runtime_source
    assert "owns_runtime_text_bridge = true" in cavebot_runtime_source
    assert "owns_retry_budget = true" in cavebot_runtime_source
    assert "runtime_actions = false" in cavebot_runtime_source
    assert "movement_enabled = false" in cavebot_runtime_source
    assert "pathfinding = false" in cavebot_runtime_source
    assert "uses_map = false" in cavebot_runtime_source
    assert "walks = false" in cavebot_runtime_source
    assert "requires_route_engine = true" in cavebot_runtime_source

    loot_runtime_source = (OTCLIENT_DIR / "ctoa_helper_loot_runtime.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["plan", "summary", "adapterSummary", "contract"]:
        assert f"function LootRuntime.{function_name}" in loot_runtime_source
    assert "owns_runtime_plan = true" in loot_runtime_source
    assert "owns_adapter_summary = true" in loot_runtime_source
    assert "runtime_actions = false" in loot_runtime_source
    assert "scans_containers = false" in loot_runtime_source
    assert "opens_containers = false" in loot_runtime_source
    assert "moves_items = false" in loot_runtime_source
    assert "uses_items = false" in loot_runtime_source
    assert "requires_experimental_flag = true" in loot_runtime_source
    assert "requires_container_probe = true" in loot_runtime_source

    timer_runtime_source = (OTCLIENT_DIR / "ctoa_helper_timer_runtime.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["plan", "summary", "dispatch", "contract"]:
        assert f"function TimerRuntime.{function_name}" in timer_runtime_source
    assert "owns_runtime_plan = true" in timer_runtime_source
    assert "owns_dispatch_decision = true" in timer_runtime_source
    assert "runtime_actions = false" in timer_runtime_source
    assert "talks = false" in timer_runtime_source
    assert "casts = false" in timer_runtime_source
    assert "evaluates = false" in timer_runtime_source
    assert "loads_files = false" in timer_runtime_source
    assert "requires_sandbox_attach = true" in timer_runtime_source

    recovery_runtime_source = (
        OTCLIENT_DIR / "ctoa_helper_recovery_runtime.lua"
    ).read_text(encoding="utf-8")
    for function_name in [
        "normalizeVitals",
        "readVitals",
        "selectHealingSpell",
        "potionStatusText",
        "spellStatusText",
        "actionGap",
        "recoveryActionGap",
        "summary",
        "contract",
    ]:
        assert f"function RecoveryRuntime.{function_name}" in recovery_runtime_source
    assert "owns_vitals_normalization = true" in recovery_runtime_source
    assert "owns_vitals_read = true" in recovery_runtime_source
    assert "owns_healing_spell_selection = true" in recovery_runtime_source
    assert "owns_recovery_status_text = true" in recovery_runtime_source
    assert "owns_recovery_action_gap = true" in recovery_runtime_source
    assert "owns_recovery_action_gap_bridge = true" in recovery_runtime_source
    assert "runtime_actions = false" in recovery_runtime_source
    assert "reads_otclient = false" in recovery_runtime_source

    profile_schema_source = (OTCLIENT_DIR / "ctoa_helper_profile_schema.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "requiredSections",
        "sectionOrder",
        "safeFalseKeys",
        "optionList",
        "rotationPresets",
        "keyOrder",
        "valueIndex",
        "cycleValue",
        "fieldGeometry",
        "stepValue",
        "displayProfileName",
        "profileSchemaValue",
        "profileSchemaTable",
        "mergeTable",
        "serializeLua",
        "currentVersion",
        "currentSchema",
        "profileVersion",
        "migrationPlan",
        "migrate",
        "summary",
        "profileSchemaSuffix",
        "rotationPresetIds",
        "rotationPresetLabel",
        "rotationPresetFormatter",
        "rotationSummary",
        "rotationSummaryText",
        "spellLabel",
        "potionLabel",
        "runeLabel",
        "healFriendPriorityLabel",
        "magicPriorityLabel",
        "themePresetLabel",
        "onOffLabel",
        "autosaveLabel",
        "titleSummary",
        "healingSummary",
        "profileSummary",
        "contract",
    ]:
        assert f"function ProfileSchema.{function_name}" in profile_schema_source
    assert "owns_schema_metadata = true" in profile_schema_source
    assert "owns_versioned_migration_plan = true" in profile_schema_source
    assert "owns_safe_profile_migration = true" in profile_schema_source
    assert "owns_key_order_metadata = true" in profile_schema_source
    assert "owns_merge_table = true" in profile_schema_source
    assert "owns_lua_serializer = true" in profile_schema_source
    assert "owns_display_profile_name = true" in profile_schema_source
    assert "owns_schema_value_bridge = true" in profile_schema_source
    assert "owns_schema_table_bridge = true" in profile_schema_source
    assert "owns_rotation_metadata = true" in profile_schema_source
    assert "owns_profile_labels = true" in profile_schema_source
    assert "owns_profile_summaries = true" in profile_schema_source
    assert "owns_title_summary = true" in profile_schema_source
    assert "owns_healing_summary = true" in profile_schema_source
    assert "owns_rotation_summary = true" in profile_schema_source
    assert "owns_rotation_preset_formatter = true" in profile_schema_source
    assert "owns_rotation_summary_text = true" in profile_schema_source
    assert "runtime_actions = false" in profile_schema_source
    assert "loads_files = false" in profile_schema_source
    assert "saves_files = false" in profile_schema_source
    assert "migrates_files = false" in profile_schema_source
    assert "preserves_key_order = true" in profile_schema_source
    assert "requires_profile_audit = true" in profile_schema_source
    assert "requires_safe_boot_defaults = true" in profile_schema_source

    profile_persistence_source = (
        OTCLIENT_DIR / "ctoa_helper_profile_persistence.lua"
    ).read_text(encoding="utf-8")
    for function_name in [
        "profileCandidates",
        "uiPrefsCandidates",
        "saveDefaults",
        "resolveSavePath",
        "fallbackSavePath",
        "saveText",
        "loadSuccessText",
        "loadFailureText",
        "profilePersistenceValue",
        "profilePersistenceTable",
        "uiPrefsPlan",
        "dirtyState",
        "exportProfile",
        "exportUiPrefs",
        "contract",
    ]:
        assert (
            f"function ProfilePersistence.{function_name}" in profile_persistence_source
        )
    assert "owns_load_candidates = true" in profile_persistence_source
    assert "owns_save_path_policy = true" in profile_persistence_source
    assert "owns_save_headers = true" in profile_persistence_source
    assert "owns_autosave_metadata = true" in profile_persistence_source
    assert "owns_load_status_text = true" in profile_persistence_source
    assert "owns_ui_prefs_plan = true" in profile_persistence_source
    assert "owns_fallback_save_path = true" in profile_persistence_source
    assert "owns_export_profile = true" in profile_persistence_source
    assert "owns_export_ui_prefs = true" in profile_persistence_source
    assert "owns_persistence_value_bridge = true" in profile_persistence_source
    assert "owns_persistence_table_bridge = true" in profile_persistence_source
    assert "runtime_actions = false" in profile_persistence_source
    assert "loads_files = false" in profile_persistence_source
    assert "saves_files = false" in profile_persistence_source
    assert "migrates_files = false" in profile_persistence_source
    assert "writes_profile = false" in profile_persistence_source
    assert "touches_otclient_globals = false" in profile_persistence_source
    assert "preserves_key_order = true" in profile_persistence_source
    assert "requires_profile_schema = true" in profile_persistence_source
    assert "requires_profile_audit = true" in profile_persistence_source
    assert "requires_safe_boot_defaults = true" in profile_persistence_source

    operator_summary_source = (
        OTCLIENT_DIR / "ctoa_helper_operator_summary.lua"
    ).read_text(encoding="utf-8")
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
        assert f"function OperatorSummary.{function_name}" in operator_summary_source
    assert "owns_operator_summary_text = true" in operator_summary_source
    assert "owns_profile_summary_bridge = true" in operator_summary_source
    assert "owns_module_summary_bridge = true" in operator_summary_source
    assert "owns_bridge_dispatch = true" in operator_summary_source
    assert "function OperatorSummary.collect" in operator_summary_source
    assert "owns_summary_collection = true" in operator_summary_source
    assert "creates_widgets = false" in operator_summary_source
    assert "runtime_actions = false" in operator_summary_source
    assert "executes_plans = false" in operator_summary_source
    assert "dispatch_allowed = false" in operator_summary_source
    assert "requires_module_static_gates = true" in operator_summary_source
    assert "requires_sandbox_attach = true" in operator_summary_source

    planner_source = (OTCLIENT_DIR / "ctoa_helper_planner.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["collect", "best", "summary", "summaryEnvelope", "contract"]:
        assert f"function Planner.{function_name}" in planner_source

    runtime_policy_source = (OTCLIENT_DIR / "ctoa_helper_runtime_policy.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "requiredGates",
        "protectionZonePolicy",
        "resolvedProtectionZonePolicy",
        "protectionZoneDecision",
        "snapshot",
        "decision",
        "summary",
        "contract",
    ]:
        assert f"function RuntimePolicy.{function_name}" in runtime_policy_source
    assert "runtime_actions = false" in runtime_policy_source
    assert "executes_plans = false" in runtime_policy_source
    assert "owns_protection_zone_policy = true" in runtime_policy_source
    assert "owns_resolved_protection_zone_policy = true" in runtime_policy_source
    assert "owns_protection_zone_decision = true" in runtime_policy_source
    assert "requires_module_attach_smoke = true" in runtime_policy_source
    assert "requires_smoke_attach_all = true" in runtime_policy_source
    assert "requires_live_approval = true" in runtime_policy_source

    dispatch_guard_source = (OTCLIENT_DIR / "ctoa_helper_dispatch_guard.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["classify", "decision", "summary", "contract"]:
        assert f"function DispatchGuard.{function_name}" in dispatch_guard_source
    assert "runtime_actions = false" in dispatch_guard_source
    assert "executes_plans = false" in dispatch_guard_source
    assert "dispatch_allowed = false" in dispatch_guard_source
    assert "requires_runtime_policy = true" in dispatch_guard_source
    assert "requires_sandbox_attach = true" in dispatch_guard_source
    assert "requires_live_approval = true" in dispatch_guard_source

    plan_queue_source = (OTCLIENT_DIR / "ctoa_helper_plan_queue.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["normalize", "enqueue", "trim", "summary", "contract"]:
        assert f"function PlanQueue.{function_name}" in plan_queue_source
    assert "runtime_actions = false" in plan_queue_source
    assert "executes_plans = false" in plan_queue_source
    assert "dispatch_allowed = false" in plan_queue_source
    assert "bounded_queue = true" in plan_queue_source
    assert "requires_planner = true" in plan_queue_source
    assert "requires_dispatch_guard = true" in plan_queue_source

    readiness_source = (OTCLIENT_DIR / "ctoa_helper_runtime_readiness.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "requiredComponents",
        "requiredGates",
        "snapshot",
        "decision",
        "summary",
        "contract",
    ]:
        assert f"function RuntimeReadiness.{function_name}" in readiness_source
    assert "runtime_actions = false" in readiness_source
    assert "executes_plans = false" in readiness_source
    assert "dispatch_allowed = false" in readiness_source
    assert "requires_runtime_policy = true" in readiness_source
    assert "requires_dispatch_guard = true" in readiness_source
    assert "requires_plan_queue = true" in readiness_source
    assert "requires_module_attach_smoke = true" in readiness_source
    assert "requires_smoke_attach_all = true" in readiness_source
    assert "requires_live_approval = true" in readiness_source

    module_status_source = (OTCLIENT_DIR / "ctoa_helper_module_status.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "defaultOrder",
        "normalize",
        "snapshot",
        "summary",
        "contract",
    ]:
        assert f"function ModuleStatus.{function_name}" in module_status_source
    assert "runtime_actions = false" in module_status_source
    assert "executes_plans = false" in module_status_source
    assert "dispatch_allowed = false" in module_status_source
    assert "normalizes_module_status = true" in module_status_source
    assert "exposes_status_board = true" in module_status_source
    assert "requires_module_contract = true" in module_status_source
    assert "requires_module_static_gates = true" in module_status_source

    action_catalog_source = (OTCLIENT_DIR / "ctoa_helper_action_catalog.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "requiredGates",
        "all",
        "domains",
        "byAction",
        "classify",
        "summary",
        "contract",
    ]:
        assert f"function ActionCatalog.{function_name}" in action_catalog_source
    assert "plan_attack" in action_catalog_source
    assert "plan_walk" in action_catalog_source
    assert "plan_sio" in action_catalog_source
    assert "plan_ring_swap" in action_catalog_source
    assert "runtime_actions = false" in action_catalog_source
    assert "executes_plans = false" in action_catalog_source
    assert "dispatch_allowed = false" in action_catalog_source
    assert "catalogs_action_risk = true" in action_catalog_source
    assert "requires_module_attach_smoke = true" in action_catalog_source
    assert "requires_smoke_attach_all = true" in action_catalog_source
    assert "requires_live_approval = true" in action_catalog_source

    decision_trace_source = (OTCLIENT_DIR / "ctoa_helper_decision_trace.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["record", "queue", "summary", "contract"]:
        assert f"function DecisionTrace.{function_name}" in decision_trace_source
    assert "runtime_actions = false" in decision_trace_source
    assert "executes_plans = false" in decision_trace_source
    assert "dispatch_allowed = false" in decision_trace_source
    assert "writes_logs = false" in decision_trace_source
    assert "traces_policy_reasons = true" in decision_trace_source
    assert "traces_guard_reasons = true" in decision_trace_source
    assert "traces_missing_gates = true" in decision_trace_source
    assert "requires_action_catalog = true" in decision_trace_source

    sandbox_handoff_source = (
        OTCLIENT_DIR / "ctoa_helper_sandbox_handoff.lua"
    ).read_text(encoding="utf-8")
    for function_name in ["steps", "snapshot", "next", "summary", "contract"]:
        assert f"function SandboxHandoff.{function_name}" in sandbox_handoff_source
    assert "solteria_helper_test_env.ps1 -Action Launch" in sandbox_handoff_source
    assert "solteria_helper_test_env.ps1 -Action ReadyCheck" in sandbox_handoff_source
    assert (
        "solteria_helper_test_env.ps1 -Action SmokeAttachModules"
        in sandbox_handoff_source
    )
    assert (
        "solteria_helper_test_env.ps1 -Action SmokeAttachAll" in sandbox_handoff_source
    )
    assert "PromoteLiveCtoa -ApproveLiveDeploy" in sandbox_handoff_source
    assert "runtime_actions = false" in sandbox_handoff_source
    assert "launches_client = false" in sandbox_handoff_source
    assert "attaches_client = false" in sandbox_handoff_source
    assert "promotes_live = false" in sandbox_handoff_source

    feature_flags_source = (OTCLIENT_DIR / "ctoa_helper_feature_flags.lua").read_text(
        encoding="utf-8"
    )
    for function_name in [
        "all",
        "safeFalseKeys",
        "byKey",
        "audit",
        "summary",
        "toolsSummary",
        "contract",
    ]:
        assert f"function FeatureFlags.{function_name}" in feature_flags_source
    assert "tools.auto_haste" in feature_flags_source
    assert "tools.cavebot_movement_enabled" in feature_flags_source
    assert "tools.feature_flags.experimental_loot" in feature_flags_source
    assert "scripting.allow_runtime_eval" in feature_flags_source
    assert "local function valueAtPath" in feature_flags_source
    assert 'string.gmatch(path, "[^.]+")' in feature_flags_source
    assert "local value = valueAtPath(cfg, flag.key)" in feature_flags_source
    assert "runtime_actions = false" in feature_flags_source
    assert "toggles_flags = false" in feature_flags_source
    assert "writes_profile = false" in feature_flags_source
    assert "owns_safe_defaults = true" in feature_flags_source
    assert "owns_tools_summary = true" in feature_flags_source

    heal_friend_source = (OTCLIENT_DIR / "ctoa_helper_heal_friend.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["plan", "statusText", "decisionText", "contract"]:
        assert f"function HealFriend.{function_name}" in heal_friend_source
    assert "owns_whitelist_matching = true" in heal_friend_source
    assert "owns_scan = true" in heal_friend_source
    assert "owns_status_text = true" in heal_friend_source
    assert "owns_decision_text = true" in heal_friend_source
    assert "owns_summary_text = true" in heal_friend_source

    conditions_source = (OTCLIENT_DIR / "ctoa_helper_conditions.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["plan", "contract"]:
        assert f"function Conditions.{function_name}" in conditions_source
    assert "owns_flag_text = true" in conditions_source
    assert "owns_snapshot = true" in conditions_source
    assert "owns_api_probe = true" in conditions_source
    assert "owns_observer = true" in conditions_source
    assert "owns_summary_text = true" in conditions_source

    equipment_source = (OTCLIENT_DIR / "ctoa_helper_equipment.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["plan", "shadowPlan", "contract"]:
        assert f"function Equipment.{function_name}" in equipment_source
    assert "owns_slot_text = true" in equipment_source
    assert "owns_snapshot = true" in equipment_source
    assert "owns_api_probe = true" in equipment_source
    assert "owns_observer = true" in equipment_source
    assert "owns_summary_text = true" in equipment_source
    assert "owns_shadow_ring_plan = true" in equipment_source
    assert "shadow_plan_data_only = true" in equipment_source
    assert "rollback_revision_required = true" in equipment_source

    scripting_source = (OTCLIENT_DIR / "ctoa_helper_scripting.lua").read_text(
        encoding="utf-8"
    )
    for function_name in ["plan", "contract"]:
        assert f"function Scripting.{function_name}" in scripting_source
    assert "owns_policy_snapshot = true" in scripting_source
    assert "owns_summary_text = true" in scripting_source


def test_module_contract_blocks_forbidden_passive_actions(tmp_path: Path):
    otclient_dir = tmp_path / "otclient"
    otclient_dir.mkdir()
    for path in OTCLIENT_DIR.glob("ctoa_helper_*.lua"):
        (otclient_dir / path.name).write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    loader = tmp_path / "loader.lua"
    registry = tmp_path / "registry.lua"
    loader.write_text(LOADER.read_text(encoding="utf-8"), encoding="utf-8")
    registry.write_text(REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
    route = otclient_dir / "ctoa_helper_route.lua"
    route.write_text(
        route.read_text(encoding="utf-8") + "\nplayer:autoWalk(pos)\n", encoding="utf-8"
    )

    report = contract.build_report(otclient_dir, loader, registry)
    modules = {item.id: item for item in report.modules}

    assert report.status == "failed"
    assert report.forbidden_count == 1
    assert modules["route"].status == "failed"
    assert modules["route"].forbidden_hits == ["movement"]
    assert "forbidden passive module actions" in report.next_action


def test_module_contract_writes_json_and_markdown(tmp_path: Path):
    report = contract.build_report(OTCLIENT_DIR, LOADER, REGISTRY)
    json_out = tmp_path / "module_contract.json"
    plan_out = tmp_path / "module_contract.md"

    contract.write_json_atomic(
        json_out, json.loads(json.dumps(report, default=lambda value: value.__dict__))
    )
    contract.write_text_atomic(plan_out, contract.render_markdown(report))

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = plan_out.read_text(encoding="utf-8")

    assert payload["status"] == "passed"
    assert payload["passed_count"] == 36
    assert "# Solteria Helper Module Contract" in markdown
    assert "Passive helper modules may observe" in markdown
    assert "otclient_helper_module_contract.py" in markdown
    assert "ModuleStaticGates" in markdown
    assert list(tmp_path.glob(".*.tmp")) == []
