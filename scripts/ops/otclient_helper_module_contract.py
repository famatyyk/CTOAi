#!/usr/bin/env python3
"""Validate OTClient helper passive module contracts before sandbox attach."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
DEFAULT_LOADER = OTCLIENT_DIR / "ctoa_otclient_loader.lua"
DEFAULT_REGISTRY = OTCLIENT_DIR / "ctoa_helper_modules.lua"
DEFAULT_JSON_OUT = ROOT / "runtime" / "solteria_helper_dev" / "module_contract.json"
DEFAULT_PLAN_OUT = ROOT / "docs" / "otclient" / "solteria_helper_module_contract.md"

PASSIVE_MODULES = [
    {
        "id": "modules",
        "loader_name": "ctoa_helper_modules",
        "file": "ctoa_helper_modules.lua",
        "global": "CTOA_HELPER_MODULES",
        "lane_id": "",
        "required_functions": [
            "getModuleLanes",
            "getShortLabels",
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
        ],
    },
    {
        "id": "domain_contract",
        "loader_name": "ctoa_helper_domain_contract",
        "file": "ctoa_helper_domain_contract.lua",
        "global": "CTOA_HELPER_DOMAIN_CONTRACT",
        "lane_id": "",
        "required_functions": [
            "schemaVersion",
            "lanes",
            "lane",
            "observationEnvelope",
            "planEnvelope",
            "summaryEnvelope",
            "validateEnvelope",
            "contract",
        ],
    },
    {
        "id": "rule_engine",
        "loader_name": "ctoa_helper_rule_engine",
        "file": "ctoa_helper_rule_engine.lua",
        "global": "CTOA_HELPER_RULE_ENGINE",
        "lane_id": "",
        "required_functions": [
            "sanitizeCondition",
            "sanitizeRule",
            "evaluate",
            "contract",
        ],
    },
    {
        "id": "ui_primitives",
        "loader_name": "ctoa_helper_ui_primitives",
        "file": "ctoa_helper_ui_primitives.lua",
        "global": "CTOA_HELPER_UI_PRIMITIVES",
        "lane_id": "",
        "required_functions": [
            "shortText",
            "fitText",
            "setWidgetText",
            "setWidgetChecked",
            "getWidgetChecked",
            "showWidget",
            "createWidget",
            "settingRowGeometry",
            "metricCardGeometry",
            "profileFieldGeometry",
            "sectionBodyGeometry",
            "mergeContext",
            "ruleEditorNavigation",
            "contract",
        ],
    },
    {
        "id": "ui_composition",
        "loader_name": "ctoa_helper_ui_composition",
        "file": "ctoa_helper_ui_composition.lua",
        "global": "CTOA_HELPER_UI_COMPOSITION",
        "lane_id": "",
        "required_functions": [
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
            "contract",
        ],
    },
    {
        "id": "ui_rule_editors",
        "loader_name": "ctoa_helper_ui_rule_editors",
        "file": "ctoa_helper_ui_rule_editors.lua",
        "global": "CTOA_HELPER_UI_RULE_EDITORS",
        "lane_id": "",
        "required_functions": [
            "addRuleEditorChrome",
            "addTargetRuleEditor",
            "addMagicRuleEditor",
            "addCombatActionRuleEditor",
            "contract",
        ],
    },
    {
        "id": "ui",
        "loader_name": "ctoa_helper_ui",
        "file": "ctoa_helper_ui.lua",
        "global": "CTOA_HELPER_UI",
        "lane_id": "",
        "required_functions": [
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
            "styleSubtabState",
            "styleMiniButton",
            "styleActionButton",
            "styleRuleCard",
            "styleMetricRow",
            "styleMetricLabel",
            "styleMetricValue",
            "styleSettingState",
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
            "addSettingRow",
            "addToggleSettingRow",
            "addProfileCycleRow",
            "addProfileStepRow",
            "addVectorStepRow",
            "sectionBodyGeometry",
            "sidebarTabs",
            "huntingSubtabs",
            "subtabContentY",
            "toolsSubtabs",
            "toolsTableHeaders",
            "cavebotDelayChoices",
            "cavebotReachChoices",
            "msText",
            "cavebotActionSpecs",
            "refreshOperatorSummaries",
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
        ],
    },
    {
        "id": "diagnostics",
        "loader_name": "ctoa_helper_diagnostics",
        "file": "ctoa_helper_diagnostics.lua",
        "global": "CTOA_HELPER_DIAGNOSTICS",
        "lane_id": "",
        "required_functions": [
            "boolText",
            "posText",
            "hasApi",
            "apiText",
            "valueText",
            "vocationProbeText",
            "apiSnapshotText",
            "apiProbeSnapshot",
            "apiProbeText",
            "magicApiProbeText",
            "featureFlagsText",
            "bufferText",
            "movementText",
            "magicLootText",
            "tableCount",
            "firstTableValue",
            "parseSmokeCommandText",
            "smokeCommandTarget",
            "smokeTabStatusText",
            "smokeCommandStatusText",
            "recordSnapshot",
            "exportBuffer",
            "contract",
        ],
    },
    {
        "id": "hotkeys",
        "loader_name": "ctoa_helper_hotkeys",
        "file": "ctoa_helper_hotkeys.lua",
        "global": "CTOA_HELPER_HOTKEYS",
        "lane_id": "",
        "required_functions": ["normalizeKeyName", "parse", "normalize", "isAllowed", "bindingDecision", "display", "contract"],
    },
    {
        "id": "modal",
        "loader_name": "ctoa_helper_modal",
        "file": "ctoa_helper_modal.lua",
        "global": "CTOA_HELPER_MODAL",
        "lane_id": "",
        "required_functions": ["request", "confirm", "cancel", "isExpired", "decision", "decisionText", "contract"],
    },
    {
        "id": "route",
        "loader_name": "ctoa_helper_route",
        "file": "ctoa_helper_route.lua",
        "global": "CTOA_HELPER_ROUTE",
        "lane_id": "",
        "required_functions": ["position", "label", "add", "clear", "select", "delete", "move", "editorAction", "retryBlocked", "progress", "activeTarget", "selectedSummary", "stats", "uiState", "deleteRequest", "contract"],
    },
    {
        "id": "targeting",
        "loader_name": "ctoa_helper_targeting",
        "file": "ctoa_helper_targeting.lua",
        "global": "CTOA_HELPER_TARGETING",
        "lane_id": "",
        "required_functions": ["normalizedName", "isIgnoredName", "hasBlockingNpcIcon", "creatureTypeDecision", "priorityRank", "scoreCandidate", "bestCandidate", "decision", "summary", "configSummary", "contract"],
    },
    {
        "id": "combat_runtime",
        "loader_name": "ctoa_helper_combat_runtime",
        "file": "ctoa_helper_combat_runtime.lua",
        "global": "CTOA_HELPER_COMBAT_RUNTIME",
        "lane_id": "",
        "required_functions": ["plan", "summary", "adapterSummary", "magicSummary", "msLeftText", "runeReady", "rotationSpellRows", "spellReadiness", "rotationSpell", "offensiveAction", "actionStatusText", "targetingStatusText", "nextActionText", "waitReason", "decisionState", "contract"],
    },
    {
        "id": "spell_state_registry",
        "loader_name": "ctoa_helper_spell_state_registry",
        "file": "ctoa_helper_spell_state_registry.lua",
        "global": "CTOA_HELPER_SPELL_STATE_REGISTRY",
        "lane_id": "",
        "required_functions": ["hasteFlag", "observeHaste", "hasteDecision", "summary", "contract"],
    },
    {
        "id": "cavebot_runtime",
        "loader_name": "ctoa_helper_cavebot_runtime",
        "file": "ctoa_helper_cavebot_runtime.lua",
        "global": "CTOA_HELPER_CAVEBOT_RUNTIME",
        "lane_id": "",
        "required_functions": [
            "plan",
            "summary",
            "decisionText",
            "adapterSummary",
            "adapterStatusText",
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
            "contract",
        ],
    },
    {
        "id": "loot_runtime",
        "loader_name": "ctoa_helper_loot_runtime",
        "file": "ctoa_helper_loot_runtime.lua",
        "global": "CTOA_HELPER_LOOT_RUNTIME",
        "lane_id": "",
        "required_functions": ["plan", "summary", "adapterSummary", "contract"],
    },
    {
        "id": "timer_runtime",
        "loader_name": "ctoa_helper_timer_runtime",
        "file": "ctoa_helper_timer_runtime.lua",
        "global": "CTOA_HELPER_TIMER_RUNTIME",
        "lane_id": "",
        "required_functions": ["plan", "summary", "probeSummary", "dispatch", "contract"],
    },
    {
        "id": "recovery_runtime",
        "loader_name": "ctoa_helper_recovery_runtime",
        "file": "ctoa_helper_recovery_runtime.lua",
        "global": "CTOA_HELPER_RECOVERY_RUNTIME",
        "lane_id": "",
        "required_functions": ["normalizeVitals", "selectHealingSpell", "potionStatusText", "spellStatusText", "actionGap", "summary", "contract"],
    },
    {
        "id": "profile_schema",
        "loader_name": "ctoa_helper_profile_schema",
        "file": "ctoa_helper_profile_schema.lua",
        "global": "CTOA_HELPER_PROFILE_SCHEMA",
        "lane_id": "",
        "required_functions": [
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
            "currentVersion",
            "currentSchema",
            "profileVersion",
            "migrationPlan",
            "migrate",
            "summary",
            "profileSchemaSuffix",
            "rotationPresetIds",
            "rotationPresetLabel",
            "rotationSummary",
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
        ],
    },
    {
        "id": "profile_persistence",
        "loader_name": "ctoa_helper_profile_persistence",
        "file": "ctoa_helper_profile_persistence.lua",
        "global": "CTOA_HELPER_PROFILE_PERSISTENCE",
        "lane_id": "",
        "required_functions": [
            "profileCandidates",
            "uiPrefsCandidates",
            "saveDefaults",
            "resolveSavePath",
            "fallbackSavePath",
            "saveText",
            "loadSuccessText",
            "loadFailureText",
            "dirtyState",
            "exportProfile",
            "contract",
        ],
    },
    {
        "id": "rule_presets",
        "loader_name": "ctoa_helper_rule_presets",
        "file": "ctoa_helper_rule_presets.lua",
        "global": "CTOA_HELPER_RULE_PRESETS",
        "lane_id": "",
        "required_functions": [
            "schemaVersion",
            "validate",
            "exportPreset",
            "importPreset",
            "contract",
        ],
    },
    {
        "id": "operator_summary",
        "loader_name": "ctoa_helper_operator_summary",
        "file": "ctoa_helper_operator_summary.lua",
        "global": "CTOA_HELPER_OPERATOR_SUMMARY",
        "lane_id": "",
        "required_functions": [
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
        ],
    },
    {
        "id": "planner",
        "loader_name": "ctoa_helper_planner",
        "file": "ctoa_helper_planner.lua",
        "global": "CTOA_HELPER_PLANNER",
        "lane_id": "",
        "required_functions": ["collect", "best", "summary", "summaryEnvelope", "contract"],
    },
    {
        "id": "runtime_policy",
        "loader_name": "ctoa_helper_runtime_policy",
        "file": "ctoa_helper_runtime_policy.lua",
        "global": "CTOA_HELPER_RUNTIME_POLICY",
        "lane_id": "",
        "required_functions": ["requiredGates", "protectionZonePolicy", "resolvedProtectionZonePolicy", "protectionZoneDecision", "snapshot", "decision", "summary", "contract"],
    },
    {
        "id": "dispatch_guard",
        "loader_name": "ctoa_helper_dispatch_guard",
        "file": "ctoa_helper_dispatch_guard.lua",
        "global": "CTOA_HELPER_DISPATCH_GUARD",
        "lane_id": "",
        "required_functions": ["classify", "decision", "summary", "contract"],
    },
    {
        "id": "plan_queue",
        "loader_name": "ctoa_helper_plan_queue",
        "file": "ctoa_helper_plan_queue.lua",
        "global": "CTOA_HELPER_PLAN_QUEUE",
        "lane_id": "",
        "required_functions": ["normalize", "enqueue", "trim", "summary", "contract"],
    },
    {
        "id": "runtime_readiness",
        "loader_name": "ctoa_helper_runtime_readiness",
        "file": "ctoa_helper_runtime_readiness.lua",
        "global": "CTOA_HELPER_RUNTIME_READINESS",
        "lane_id": "",
        "required_functions": ["requiredComponents", "requiredGates", "snapshot", "decision", "summary", "contract"],
    },
    {
        "id": "module_status",
        "loader_name": "ctoa_helper_module_status",
        "file": "ctoa_helper_module_status.lua",
        "global": "CTOA_HELPER_MODULE_STATUS",
        "lane_id": "",
        "required_functions": ["defaultOrder", "normalize", "snapshot", "summary", "contract"],
    },
    {
        "id": "action_catalog",
        "loader_name": "ctoa_helper_action_catalog",
        "file": "ctoa_helper_action_catalog.lua",
        "global": "CTOA_HELPER_ACTION_CATALOG",
        "lane_id": "",
        "required_functions": ["requiredGates", "all", "domains", "byAction", "classify", "summary", "contract"],
    },
    {
        "id": "decision_trace",
        "loader_name": "ctoa_helper_decision_trace",
        "file": "ctoa_helper_decision_trace.lua",
        "global": "CTOA_HELPER_DECISION_TRACE",
        "lane_id": "",
        "required_functions": ["record", "queue", "summary", "contract"],
    },
    {
        "id": "decision_pipeline",
        "loader_name": "ctoa_helper_decision_pipeline",
        "file": "ctoa_helper_decision_pipeline.lua",
        "global": "CTOA_HELPER_DECISION_PIPELINE",
        "lane_id": "",
        "required_functions": ["components", "evaluate", "summary", "blockers", "contract"],
    },
    {
        "id": "sandbox_handoff",
        "loader_name": "ctoa_helper_sandbox_handoff",
        "file": "ctoa_helper_sandbox_handoff.lua",
        "global": "CTOA_HELPER_SANDBOX_HANDOFF",
        "lane_id": "",
        "required_functions": ["steps", "snapshot", "next", "summary", "contract"],
    },
    {
        "id": "feature_flags",
        "loader_name": "ctoa_helper_feature_flags",
        "file": "ctoa_helper_feature_flags.lua",
        "global": "CTOA_HELPER_FEATURE_FLAGS",
        "lane_id": "",
        "required_functions": ["all", "safeFalseKeys", "byKey", "audit", "summary", "toolsSummary", "contract"],
    },
    {
        "id": "hud",
        "loader_name": "ctoa_helper_hud",
        "file": "ctoa_helper_hud.lua",
        "global": "CTOA_HELPER_HUD",
        "lane_id": "",
        "required_functions": [
            "startText",
            "disarmedText",
            "position",
            "state",
            "visibilityText",
            "runtimeText",
            "uiSummary",
            "operatorSummary",
            "contract",
        ],
    },
    {
        "id": "conditions",
        "loader_name": "ctoa_helper_conditions",
        "file": "ctoa_helper_conditions.lua",
        "global": "CTOA_HELPER_CONDITIONS",
        "lane_id": "conditions",
        "required_functions": ["flagText", "snapshot", "apiProbe", "observe", "plan", "summary", "contract"],
    },
    {
        "id": "equipment",
        "loader_name": "ctoa_helper_equipment",
        "file": "ctoa_helper_equipment.lua",
        "global": "CTOA_HELPER_EQUIPMENT",
        "lane_id": "equipment",
        "required_functions": ["slotText", "snapshot", "apiProbe", "observe", "plan", "summary", "contract"],
    },
    {
        "id": "scripting",
        "loader_name": "ctoa_helper_scripting",
        "file": "ctoa_helper_scripting.lua",
        "global": "CTOA_HELPER_SCRIPTING",
        "lane_id": "scripting",
        "required_functions": ["policySnapshot", "plan", "summary", "contract"],
    },
    {
        "id": "heal_friend",
        "loader_name": "ctoa_helper_heal_friend",
        "file": "ctoa_helper_heal_friend.lua",
        "global": "CTOA_HELPER_HEAL_FRIEND",
        "lane_id": "heal_friend",
        "required_functions": ["whitelistContainsName", "scan", "observe", "executeOnceObservation", "plan", "statusText", "decisionText", "summary", "contract"],
    },
]

FORBIDDEN_PASSIVE_PATTERNS = {
    "spell_cast": re.compile(r"\bcastSpell\s*\(|\bg_game\.talk\s*\(|\bsay\s*\("),
    "item_use": re.compile(
        r"\bg_game\.use(?:InventoryItem|InventoryItemWith)?\s*\(|\buseWith\s*\("
    ),
    "movement": re.compile(r"\bautoWalk\s*\(|\bg_game\.walk\s*\("),
    "snippet_eval": re.compile(r"\bloadstring\s*\(|\bload\s*\(|\bdofile\s*\("),
}

REQUIRED_LANES = {
    "healing",
    "combat",
    "cavebot",
    "loot",
    "timer",
    "heal_friend",
    "conditions",
    "equipment",
    "scripting",
}


@dataclass(frozen=True)
class ModuleContractItem:
    id: str
    file: str
    status: str
    loader_present: bool
    registry_present: bool
    global_present: bool
    return_present: bool
    missing_functions: list[str]
    forbidden_hits: list[str]


@dataclass(frozen=True)
class ModuleContractReport:
    name: str
    created_at: str
    status: str
    loader_path: str
    registry_path: str
    expected_module_count: int
    check_count: int
    passed_count: int
    failed_count: int
    registry_lane_count: int
    registry_missing: list[str]
    loader_missing: list[str]
    forbidden_count: int
    modules: list[ModuleContractItem]
    next_action: str
    live_safety: str


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def parse_loader_modules(loader_text: str) -> dict[str, str]:
    return {
        match.group("name"): match.group("file")
        for match in re.finditer(
            r'\{name\s*=\s*"(?P<name>[^"]+)",\s*file\s*=\s*"(?P<file>[^"]+)"[^}]*\}',
            loader_text,
        )
    }


def parse_registry_lanes(registry_text: str) -> set[str]:
    return set(re.findall(r'id\s*=\s*"([^"]+)"', registry_text))


def forbidden_hits(source: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in FORBIDDEN_PASSIVE_PATTERNS.items():
        if pattern.search(source):
            hits.append(name)
    return hits


def missing_functions(source: str, module_global: str, required: list[str]) -> list[str]:
    local_name = module_global.removeprefix("CTOA_HELPER_").title().replace("_", "")
    if module_global == "CTOA_HELPER_MODULES":
        local_name = "Registry"
    elif module_global == "CTOA_HELPER_UI_PRIMITIVES":
        local_name = "Primitives"
    elif module_global == "CTOA_HELPER_UI_COMPOSITION":
        local_name = "Composition"
    elif module_global == "CTOA_HELPER_UI_RULE_EDITORS":
        local_name = "RuleEditors"
    return [
        function_name
        for function_name in required
        if f"function {local_name}.{function_name}" not in source
    ]


def build_report(
    otclient_dir: Path = OTCLIENT_DIR,
    loader_path: Path = DEFAULT_LOADER,
    registry_path: Path = DEFAULT_REGISTRY,
) -> ModuleContractReport:
    loader_text = loader_path.read_text(encoding="utf-8")
    registry_text = registry_path.read_text(encoding="utf-8")
    # The loader owns the registry bootstrap; the registry owns the ordered
    # support-module graph. Validate both sources as one boot contract.
    loader_modules = parse_loader_modules(loader_text + "\n" + registry_text)
    registry_lanes = parse_registry_lanes(registry_text)
    registry_missing = sorted(REQUIRED_LANES - registry_lanes)
    modules: list[ModuleContractItem] = []

    for expected in PASSIVE_MODULES:
        source_path = otclient_dir / str(expected["file"])
        source = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
        loader_present = loader_modules.get(str(expected["loader_name"])) == expected["file"]
        lane_id = str(expected["lane_id"])
        registry_present = not lane_id or lane_id in registry_lanes
        global_name = str(expected["global"])
        global_present = (
            f'rawget(_G, "{global_name}")' in source
            and f"_G.{global_name}" in source
        )
        return_present = f"return {global_name.removeprefix('CTOA_HELPER_').title().replace('_', '')}" in source
        if expected["id"] == "modules":
            return_present = "return Registry" in source
        elif expected["id"] == "ui_primitives":
            return_present = "return Primitives" in source
        elif expected["id"] == "ui_composition":
            return_present = "return Composition" in source
        elif expected["id"] == "ui_rule_editors":
            return_present = "return RuleEditors" in source
        forbidden = forbidden_hits(source)
        missing_required = missing_functions(
            source,
            global_name,
            [str(item) for item in expected.get("required_functions", [])],
        )
        status = (
            "passed"
            if source_path.is_file()
            and loader_present
            and registry_present
            and global_present
            and return_present
            and not missing_required
            and not forbidden
            else "failed"
        )
        modules.append(
            ModuleContractItem(
                id=str(expected["id"]),
                file=str(expected["file"]),
                status=status,
                loader_present=loader_present,
                registry_present=registry_present,
                global_present=global_present,
                return_present=return_present,
                missing_functions=missing_required,
                forbidden_hits=forbidden,
            )
        )

    failed = [item for item in modules if item.status != "passed"]
    loader_missing = sorted(
        str(item["loader_name"])
        for item in PASSIVE_MODULES
        if loader_modules.get(str(item["loader_name"])) != item["file"]
    )
    forbidden_count = sum(len(item.forbidden_hits) for item in modules)
    status = "passed" if not failed and not registry_missing else "failed"
    return ModuleContractReport(
        name="otclient-helper-module-contract",
        created_at=datetime.now().replace(microsecond=0).isoformat(),
        status=status,
        loader_path=str(loader_path),
        registry_path=str(registry_path),
        expected_module_count=len(PASSIVE_MODULES),
        check_count=len(PASSIVE_MODULES),
        passed_count=sum(1 for item in modules if item.status == "passed"),
        failed_count=len(failed),
        registry_lane_count=len(registry_lanes & REQUIRED_LANES),
        registry_missing=registry_missing,
        loader_missing=loader_missing,
        forbidden_count=forbidden_count,
        modules=modules,
        next_action=(
            "Run ModuleStaticGates, then sandbox SmokeAttachModules."
            if status == "passed"
            else "Fix loader, registry, passive globals, or forbidden passive module actions before sandbox attach."
        ),
        live_safety=(
            "ModuleContract is repo-only static analysis; it does not launch, stop, attach to, promote, or overwrite any client."
        ),
    )


def render_markdown(report: ModuleContractReport) -> str:
    lines = [
        "# Solteria Helper Module Contract",
        "",
        f"- Status: `{report.status}`",
        f"- Expected modules: `{report.expected_module_count}`",
        f"- Passed modules: `{report.passed_count}`",
        f"- Failed modules: `{report.failed_count}`",
        f"- Registry lanes: `{report.registry_lane_count}` / `{len(REQUIRED_LANES)}`",
        f"- Forbidden passive hits: `{report.forbidden_count}`",
        f"- Next action: {report.next_action}",
        "",
        "## Rule",
        "",
        "Passive helper modules may observe, format, plan, or expose UI state. They must not cast spells, use items, walk, execute snippets, or load arbitrary files. Runtime actions stay in the guarded native helper domains and still require sandbox evidence.",
        "",
        "## Modules",
        "",
        "| Module | File | Status | Loader | Registry | Global | Return | Missing functions | Forbidden |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in report.modules:
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | {} | {} |".format(
                item.id,
                item.file,
                item.status,
                "yes" if item.loader_present else "no",
                "yes" if item.registry_present else "no",
                "yes" if item.global_present else "no",
                "yes" if item.return_present else "no",
                ", ".join(item.missing_functions) if item.missing_functions else "none",
                ", ".join(item.forbidden_hits) if item.forbidden_hits else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\ops\\otclient_helper_module_contract.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ModuleStaticGates",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--otclient-dir", type=Path, default=OTCLIENT_DIR)
    parser.add_argument("--loader", type=Path, default=DEFAULT_LOADER)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN_OUT)
    parser.add_argument("--no-plan-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.otclient_dir.resolve(),
        args.loader.resolve(),
        args.registry.resolve(),
    )
    write_json_atomic(args.json_out.resolve(), asdict(report))
    if not args.no_plan_write:
        write_text_atomic(args.plan_out.resolve(), render_markdown(report))
    print(f"[otclient-helper-module-contract] JSON: {args.json_out}")
    if not args.no_plan_write:
        print(f"[otclient-helper-module-contract] Plan: {args.plan_out}")
    print(
        "[otclient-helper-module-contract] Status: "
        f"{report.status} ({report.passed_count}/{report.expected_module_count})"
    )
    return 0 if report.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
