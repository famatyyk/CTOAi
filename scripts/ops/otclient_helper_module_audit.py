#!/usr/bin/env python3
"""Audit OTClient Helper module readiness and modularization pressure."""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
DEFAULT_OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
DEFAULT_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_module_workplan.md"
DEFAULT_EVIDENCE_DIR = ROOT / "runtime" / "solteria_helper_dev"

STATIC_GATE_REPORTS = {
    "healing": ("healing_vitals_smoke.json", "healing"),
    "combat": ("combat_safety_smoke.json", "hunting_magic"),
    "cavebot": ("cavebot_safety_smoke.json", "cavebot"),
    "timer": ("timer_safety_smoke.json", "tools_timer"),
    "loot": ("loot_safety_smoke.json", "tools_diag"),
    "heal_friend": ("heal_friend_no_target_smoke.json", "heal_friend"),
    "conditions": ("conditions_observer_smoke.json", "conditions"),
    "equipment": ("equipment_observer_smoke.json", "equipment"),
    "scripting": ("scripting_policy_smoke.json", "scripting"),
}


MODULE_CONTRACTS = [
    {
        "id": "healing",
        "label": "Healing and recovery",
        "status_when_tokens": ["local function maybeHeal", "local function maybeManaPotion", "selectHealingSpell"],
        "target_file": "ctoa_native_heal.lua",
        "next_step": "Keep runtime logic mirrored in standalone passive recovery module and add sandbox HP/MP log smoke.",
        "gate": "ValidateDev plus in-world HP/MP sandbox log evidence.",
    },
    {
        "id": "combat",
        "label": "Targeting and magic shooter",
        "status_when_tokens": ["local function maybeUseTools", "retargetSafeMonster", "executeOffensiveAction"],
        "target_file": "ctoa_native_combat.lua",
        "next_step": "Extract shared target scoring/guards into a reusable helper runtime domain before adding more attacks.",
        "gate": "PZ/NPC regression log plus SmokeAttachAll hunting and hunting_magic views.",
    },
    {
        "id": "cavebot",
        "label": "CaveBot route and movement",
        "status_when_tokens": ["local function maybeRunCavebot", "function addCurrentCavebotWaypoint", "player:autoWalk(pos, retry)"],
        "target_file": "ctoa_native_helper.lua",
        "next_step": "Split route editing from movement execution into separate domain blocks before adding waypoint actions.",
        "gate": "Route editor static tests plus sandbox autoWalk retry-budget evidence.",
    },
    {
        "id": "loot",
        "label": "Loot scanner",
        "status_when_tokens": ["experimental_loot", "auto_open_corpses", "loot_max_items_per_scan"],
        "target_file": "ctoa_native_loot.lua",
        "next_step": "Promote loot from experimental flag only after in-world container scan evidence exists.",
        "gate": "ValidateDev plus bounded ctoa_local.log loot scan evidence in sandbox.",
    },
    {
        "id": "timer",
        "label": "Timer action",
        "status_when_tokens": ["local function maybeRunTimer", "timer_interval_ms", "last_timer_ms"],
        "target_file": "ctoa_native_helper.lua",
        "next_step": "Keep timer as a small bounded action; do not add arbitrary scripting through timer message.",
        "gate": "Static contract and sandbox log evidence for one timer tick.",
    },
    {
        "id": "heal_friend",
        "label": "Heal Friend",
        "status_when_tokens": ["heal_friend = {", "healFriendSummaryText", "maybeObserveHealFriend"],
        "prototype_only": True,
        "target_file": "ctoa_helper_heal_friend.lua",
        "next_step": "Run HealFriendNoTargetSmoke, then capture grouped in-world SmokeAttachModules evidence before any sio cast path.",
        "gate": "No runtime sio cast until whitelist UI, profile persistence, HealFriendNoTargetSmoke, ModuleStaticGates, and ModuleAttachSmoke evidence exist.",
    },
    {
        "id": "conditions",
        "label": "Conditions",
        "status_when_tokens": [
            "conditions = {",
            "conditionsSummaryText",
            "maybeSampleConditions",
            "externalConditions.observe",
        ],
        "prototype_only": True,
        "target_file": "ctoa_helper_conditions.lua",
        "next_step": "Run ConditionsObserverSmoke, then capture grouped in-world SmokeAttachModules state evidence before any recovery action.",
        "gate": "No condition recovery action until API probe evidence, passive plan contract, ConditionsObserverSmoke, ModuleStaticGates, and ModuleAttachSmoke pass.",
    },
    {
        "id": "equipment",
        "label": "Equipment",
        "status_when_tokens": [
            "equipment = {",
            "equipmentSummaryText",
            "maybeSampleEquipment",
            "externalEquipment.observe",
        ],
        "prototype_only": True,
        "target_file": "ctoa_helper_equipment.lua",
        "next_step": "Run EquipmentObserverSmoke, then capture grouped in-world SmokeAttachModules inventory evidence before any swap path.",
        "gate": "No runtime swap before inventory API probe output, passive plan contract, profile persistence, EquipmentObserverSmoke, ModuleStaticGates, and ModuleAttachSmoke.",
    },
    {
        "id": "scripting",
        "label": "Scripting",
        "status_when_tokens": [
            "scripting = {",
            "scriptingSummaryText",
            "buildScriptingPolicySnapshot",
            "externalScripting.policySnapshot",
        ],
        "prototype_only": True,
        "target_file": "ctoa_helper_scripting.lua",
        "next_step": "Run ScriptingPolicySmoke, then capture grouped in-world SmokeAttachModules policy shell evidence; keep eval and user snippets blocked.",
        "gate": "No user snippet execution until passive plan contract, security review, denylist tests, audit logging, ScriptingPolicySmoke, ModuleStaticGates, and ModuleAttachSmoke pass.",
    },
]


EXTRACTION_PHASES = [
    {
        "id": "module_registry",
        "target_file": "ctoa_helper_modules.lua",
        "source_domain": "MODULE_LANES, module lane lookup, readiness text",
        "safe_order": 1,
        "gate": "Registry parity test plus Overview readiness smoke.",
    },
    {
        "id": "diagnostics",
        "target_file": "ctoa_helper_diagnostics.lua",
        "source_domain": "log helpers, API probes, status snapshots, module evidence formatting",
        "safe_order": 2,
        "gate": "ValidateDev, UI preview, and no secret/runtime path leakage in generated evidence.",
    },
    {
        "id": "heal_friend",
        "target_file": "ctoa_helper_heal_friend.lua",
        "source_domain": "heal friend profile defaults, whitelist matching, observer sampling, UI summary",
        "safe_order": 3,
        "gate": "HealFriendNoTargetSmoke, ModuleStaticGates, and ModuleAttachSmoke before any sio runtime arm.",
    },
    {
        "id": "conditions",
        "target_file": "ctoa_helper_conditions.lua",
        "source_domain": "condition state API probes, read-only observer rows, passive recovery planner, profile defaults",
        "safe_order": 4,
        "gate": "ConditionsObserverSmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke before any recovery action.",
    },
    {
        "id": "equipment",
        "target_file": "ctoa_helper_equipment.lua",
        "source_domain": "inventory slot probes, passive ring/amulet swap planner, read-only UI summary",
        "safe_order": 5,
        "gate": "EquipmentObserverSmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke before any use/move action.",
    },
    {
        "id": "scripting",
        "target_file": "ctoa_helper_scripting.lua",
        "source_domain": "policy shell, deny-all snippet planner, audit metadata",
        "safe_order": 6,
        "gate": "ScriptingPolicySmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke; eval remains blocked.",
    },
]

SUPPLEMENTAL_REFACTOR_PLAN = [
    {
        "id": "combat_runtime_adapter",
        "target_file": "ctoa_helper_combat_runtime.lua",
        "source_domain": "combat arming, monster scan adapter, attack/cast execution guards",
        "safe_order": 1,
        "gate": "Combat runtime static contract, target scorer contract, monster-only regressions, PZ/NPC smoke, SmokeAttachAll hunting tabs.",
    },
    {
        "id": "cavebot_runtime_adapter",
        "target_file": "ctoa_helper_cavebot_runtime.lua",
        "source_domain": "movement execution, path probe, retry budget, PZ/offline movement guards",
        "safe_order": 2,
        "gate": "Route contract, cavebot static tests, in-world retry-budget evidence, SmokeAttachAll cavebot tab.",
    },
    {
        "id": "loot_runtime_adapter",
        "target_file": "ctoa_helper_loot_runtime.lua",
        "source_domain": "corpse/container scan orchestration, item move bounds, capacity guard",
        "safe_order": 3,
        "gate": "Container API probe, experimental_loot remains false by default, bounded sandbox loot log evidence.",
    },
    {
        "id": "timer_runtime_adapter",
        "target_file": "ctoa_helper_timer_runtime.lua",
        "source_domain": "bounded timer message/cast action, interval guard, action lock",
        "safe_order": 4,
        "gate": "Static no-eval contract, one-tick sandbox log evidence, no scripting bridge.",
    },
    {
        "id": "profile_schema_adapter",
        "target_file": "ctoa_helper_profile_schema.lua",
        "source_domain": "profile defaults, migration keys, rotation preset metadata, profile dirty reasons, profile UI persistence",
        "safe_order": 5,
        "gate": "Profile audit, schema snapshot, safe migration and rotation-summary tests, no key-order churn.",
    },
    {
        "id": "operator_summary_bridge",
        "target_file": "ctoa_helper_operator_summary.lua",
        "source_domain": "operator title, domain summary text, profile/UI summary bridge, and no-widget text composition",
        "safe_order": 6,
        "gate": "OperatorSummary static contract, profile schema and domain summary parity, ModuleStaticGates, UI preview, and sandbox SmokeAttachModules before any runtime bridge can consume summaries.",
    },
    {
        "id": "planner_coordinator",
        "target_file": "ctoa_helper_planner.lua",
        "source_domain": "passive plan collection, ranking, summary, and no-execution contract",
        "safe_order": 7,
        "gate": "Planner static contract, module planner regressions, ModuleStaticGates, and sandbox SmokeAttachModules before any runtime dispatcher wiring.",
    },
    {
        "id": "runtime_policy_guard",
        "target_file": "ctoa_helper_runtime_policy.lua",
        "source_domain": "shared runtime gate evaluation, manifest freshness, sandbox smoke, and live approval policy",
        "safe_order": 8,
        "gate": "RuntimePolicy static contract, ModuleStaticGates, current manifest, ModuleAttachSmoke, SmokeAttachAll, and explicit live approval before any dispatcher executes a plan.",
    },
    {
        "id": "dispatch_guard_coordinator",
        "target_file": "ctoa_helper_dispatch_guard.lua",
        "source_domain": "ranked plan classification, runtime policy handoff, and dispatch allow/deny reasons",
        "safe_order": 9,
        "gate": "DispatchGuard static contract, RuntimePolicy ready decision, sandbox attach evidence, and explicit live approval before any dispatcher bridge is wired.",
    },
    {
        "id": "plan_queue_coordinator",
        "target_file": "ctoa_helper_plan_queue.lua",
        "source_domain": "bounded guarded-decision queue, review summaries, and no-execution handoff state",
        "safe_order": 10,
        "gate": "PlanQueue static contract, DispatchGuard decision evidence, bounded queue tests, sandbox attach evidence, and explicit live approval before queued plans can feed any dispatcher bridge.",
    },
    {
        "id": "runtime_readiness_status",
        "target_file": "ctoa_helper_runtime_readiness.lua",
        "source_domain": "component readiness, gate readiness, queued-plan review status, and no-execution runtime bridge summary",
        "safe_order": 11,
        "gate": "RuntimeReadiness static contract, required component/gate coverage, current manifest, sandbox attach evidence, SmokeAttachAll, and explicit live approval before any runtime bridge is considered ready.",
    },
    {
        "id": "module_status_board",
        "target_file": "ctoa_helper_module_status.lua",
        "source_domain": "module readiness rows, status counts, blocker summary, and no-execution evidence board",
        "safe_order": 12,
        "gate": "ModuleStatus static contract, module contract coverage, ModuleStaticGates, sandbox attach evidence, and explicit live approval before status can support runtime enablement.",
    },
    {
        "id": "action_catalog_policy",
        "target_file": "ctoa_helper_action_catalog.lua",
        "source_domain": "runtime action capability names, domain mapping, risk class, required gates, and no-execution dispatch metadata",
        "safe_order": 13,
        "gate": "ActionCatalog static contract, action risk coverage, RuntimePolicy gate parity, ModuleStaticGates, sandbox attach evidence, and explicit live approval before any action can be dispatched.",
    },
    {
        "id": "decision_trace_review",
        "target_file": "ctoa_helper_decision_trace.lua",
        "source_domain": "plan/policy/guard/queue decision traces, missing gate summaries, and no-write review metadata",
        "safe_order": 14,
        "gate": "DecisionTrace static contract, policy/guard reason coverage, bounded queue trace, ModuleStaticGates, sandbox attach evidence, and explicit live approval before any trace informs runtime dispatch.",
    },
    {
        "id": "sandbox_handoff_checklist",
        "target_file": "ctoa_helper_sandbox_handoff.lua",
        "source_domain": "operator sandbox smoke checklist, required runtime gates, next-step summary, and no-launch/no-promote handoff metadata",
        "safe_order": 15,
        "gate": "SandboxHandoff static contract, Launch/ReadyCheck/SmokeAttachModules/SmokeAttachAll/ApproveLiveDeploy sequence coverage, ModuleStaticGates, and explicit live approval before live promotion.",
    },
    {
        "id": "feature_flag_matrix",
        "target_file": "ctoa_helper_feature_flags.lua",
        "source_domain": "safe false runtime flags, feature domains, required gates, and no-toggle profile audit metadata",
        "safe_order": 16,
        "gate": "FeatureFlags static contract, safe-default coverage, profile audit parity, ModuleStaticGates, SmokeAttachAll, and explicit live approval before runtime flags can be enabled.",
    },
]

HELPER_LINE_BUDGET = 4500
HELPER_FUNCTION_BUDGET = 130


@dataclass(frozen=True)
class ModuleAuditItem:
    id: str
    label: str
    status: str
    target_file: str
    evidence: list[str]
    next_step: str
    gate: str


@dataclass(frozen=True)
class ExtractionPlanItem:
    id: str
    target_file: str
    source_domain: str
    safe_order: int
    status: str
    gate: str


@dataclass(frozen=True)
class SupplementalPlanItem:
    id: str
    target_file: str
    source_domain: str
    safe_order: int
    status: str
    gate: str


@dataclass(frozen=True)
class ModuleAudit:
    name: str
    status: str
    helper_path: str
    helper_line_count: int
    helper_function_count: int
    helper_line_budget: int
    helper_function_budget: int
    helper_budget_status: str
    helper_shell_target: str
    modularization_pressure: str
    placeholder_count: int
    implemented_count: int
    prototype_count: int
    registry_count: int
    registry_missing: list[str]
    modules: list[ModuleAuditItem]
    extraction_plan: list[ExtractionPlanItem]
    supplemental_refactor_plan: list[SupplementalPlanItem]
    next_extraction_id: str
    next_supplemental_id: str
    next_phase: str
    next_module_id: str
    next_module_action: str
    plan_path: str


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


def _status_for_contract(contract: dict, helper_text: str, otclient_dir: Path) -> tuple[str, list[str]]:
    tokens = [token for token in contract["status_when_tokens"] if token in helper_text]
    target_file = otclient_dir / contract["target_file"]
    evidence = [f"helper:{token}" for token in tokens]
    if target_file.is_file():
        evidence.append(str(target_file))

    placeholder_token = f'addPlaceholderModule(window, "{contract["id"]}"'
    if placeholder_token in helper_text:
        return "placeholder", evidence
    if len(tokens) == len(contract["status_when_tokens"]) and target_file.is_file():
        if contract.get("prototype_only"):
            return "prototype", evidence
        return "implemented", evidence
    if tokens:
        return "prototype", evidence
    return "missing", evidence


def _passed_json(path: Path, accepted: set[str]) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return str(payload.get("status", "")).lower() in accepted


def _static_gate_evidence(module_id: str, evidence_dir: Path | None) -> list[str]:
    report_spec = STATIC_GATE_REPORTS.get(module_id)
    if evidence_dir is None or report_spec is None:
        return []
    report_name, tab_name = report_spec
    report_path = evidence_dir / report_name
    module_gates_path = evidence_dir / "module_static_gates.json"
    ready_path = evidence_dir / "ready_check.json"
    preview_dir = evidence_dir.parent / "otclient_ui_preview"
    screenshots = sorted(preview_dir.glob(f"solteria-helper-attach-{tab_name}-*.png"))
    if not (
        _passed_json(report_path, {"passed"})
        and _passed_json(module_gates_path, {"passed"})
        and _passed_json(ready_path, {"ready", "passed"})
        and screenshots
    ):
        return []
    newest_screenshot = max(screenshots, key=lambda path: path.stat().st_mtime)
    if newest_screenshot.stat().st_mtime < report_path.stat().st_mtime:
        return []
    return [str(report_path), str(module_gates_path), str(ready_path), str(newest_screenshot)]


def build_audit(
    helper_path: Path = DEFAULT_HELPER,
    otclient_dir: Path = DEFAULT_OTCLIENT_DIR,
    plan_path: Path = DEFAULT_PLAN,
    evidence_dir: Path | None = DEFAULT_EVIDENCE_DIR,
) -> ModuleAudit:
    helper_text = helper_path.read_text(encoding="utf-8")
    registry_path = otclient_dir / "ctoa_helper_modules.lua"
    registry_text = registry_path.read_text(encoding="utf-8") if registry_path.is_file() else ""
    helper_lines = helper_text.splitlines()
    function_count = len(re.findall(r"^\s*(?:local\s+)?function\s+", helper_text, re.MULTILINE))
    helper_budget_status = (
        "over_budget"
        if len(helper_lines) > HELPER_LINE_BUDGET or function_count > HELPER_FUNCTION_BUDGET
        else "within_budget"
    )
    modules: list[ModuleAuditItem] = []
    for contract in MODULE_CONTRACTS:
        status, evidence = _status_for_contract(contract, helper_text, otclient_dir)
        gate_evidence = _static_gate_evidence(str(contract["id"]), evidence_dir)
        if status in {"prototype", "implemented"} and gate_evidence:
            status = "static_gated"
            evidence.extend(gate_evidence)
        modules.append(
            ModuleAuditItem(
                id=contract["id"],
                label=contract["label"],
                status=status,
                target_file=contract["target_file"],
                evidence=evidence,
                next_step=contract["next_step"],
                gate=contract["gate"],
            )
        )

    placeholder_count = sum(1 for item in modules if item.status == "placeholder")
    prototype_count = sum(1 for item in modules if item.status == "prototype")
    registry_ids = set(re.findall(r'id\s*=\s*"([^"]+)"', registry_text))
    contract_ids = {str(contract["id"]) for contract in MODULE_CONTRACTS}
    registry_missing = sorted(contract_ids - registry_ids)
    pressure = "high" if len(helper_lines) >= 5000 or placeholder_count >= 3 else "medium"
    status = "needs_modularization" if pressure == "high" or placeholder_count else "ready"
    extraction_plan: list[ExtractionPlanItem] = []
    for phase in EXTRACTION_PHASES:
        target_file = str(phase["target_file"])
        target_exists = (otclient_dir / target_file).is_file()
        extraction_plan.append(
            ExtractionPlanItem(
                id=str(phase["id"]),
                target_file=target_file,
                source_domain=str(phase["source_domain"]),
                safe_order=int(phase["safe_order"]),
                status="extracted" if target_exists else "planned",
                gate=str(phase["gate"]),
            )
        )
    next_extraction = next((item for item in extraction_plan if item.status == "planned"), None)
    next_extraction_id = next_extraction.id if next_extraction else ""
    supplemental_plan: list[SupplementalPlanItem] = []
    for phase in SUPPLEMENTAL_REFACTOR_PLAN:
        target_file = str(phase["target_file"])
        target_exists = (otclient_dir / target_file).is_file()
        supplemental_plan.append(
            SupplementalPlanItem(
                id=str(phase["id"]),
                target_file=target_file,
                source_domain=str(phase["source_domain"]),
                safe_order=int(phase["safe_order"]),
                status="extracted" if target_exists else "planned",
                gate=str(phase["gate"]),
            )
        )
    next_supplemental = next((item for item in supplemental_plan if item.status == "planned"), None)
    next_supplemental_id = next_supplemental.id if next_supplemental else ""
    implemented_count = (
        sum(1 for item in modules if item.status in {"implemented", "static_gated"})
        + sum(1 for item in extraction_plan if item.status == "extracted")
        + sum(1 for item in supplemental_plan if item.status == "extracted")
    )
    next_phase = (
        "P6-module-lane: keep the main helper as UI composition shell; move runtime adapters behind static contracts and sandbox gates."
        if helper_budget_status == "over_budget" or status != "ready"
        else "Keep module gates current before adding new runtime actions."
    )
    prototype_only_ids = {str(contract["id"]) for contract in MODULE_CONTRACTS if contract.get("prototype_only")}
    next_module = next((item for item in modules if item.status == "prototype" and item.id in prototype_only_ids), None)
    if next_module is None:
        next_module = next((item for item in modules if item.status == "prototype"), None)
    if next_module is None:
        next_module = next((item for item in modules if item.status == "implemented"), None)
    next_module_id = next_module.id if next_module else ""
    next_module_action = next_module.next_step if next_module else "Keep module gates current before adding new runtime actions."
    return ModuleAudit(
        name="otclient-helper-module-audit",
        status=status,
        helper_path=str(helper_path),
        helper_line_count=len(helper_lines),
        helper_function_count=function_count,
        helper_line_budget=HELPER_LINE_BUDGET,
        helper_function_budget=HELPER_FUNCTION_BUDGET,
        helper_budget_status=helper_budget_status,
        helper_shell_target="UI composition, profile persistence, and guarded dispatch only; registry/domain logic belongs in helper modules/adapters.",
        modularization_pressure=pressure,
        placeholder_count=placeholder_count,
        implemented_count=implemented_count,
        prototype_count=prototype_count,
        registry_count=len(registry_ids & contract_ids),
        registry_missing=registry_missing,
        modules=modules,
        extraction_plan=extraction_plan,
        supplemental_refactor_plan=supplemental_plan,
        next_extraction_id=next_extraction_id,
        next_supplemental_id=next_supplemental_id,
        next_phase=next_phase,
        next_module_id=next_module_id,
        next_module_action=next_module_action,
        plan_path=str(plan_path),
    )


def render_markdown(audit: ModuleAudit) -> str:
    lines = [
        "# Solteria Helper Module Workplan",
        "",
        "## Current Decision",
        "",
        f"- Status: `{audit.status}`",
        f"- Helper lines: `{audit.helper_line_count}`",
        f"- Helper functions: `{audit.helper_function_count}`",
        f"- Helper line budget: `{audit.helper_line_budget}`",
        f"- Helper function budget: `{audit.helper_function_budget}`",
        f"- Helper budget status: `{audit.helper_budget_status}`",
        f"- Helper shell target: {audit.helper_shell_target}",
        f"- Modularization pressure: `{audit.modularization_pressure}`",
        f"- Placeholder modules: `{audit.placeholder_count}`",
        f"- Implemented modules: `{audit.implemented_count}`",
        f"- Prototype modules: `{audit.prototype_count}`",
        f"- Registry coverage: `{audit.registry_count}` / `{len(MODULE_CONTRACTS)}`",
        f"- Next extraction: `{audit.next_extraction_id or 'none'}`",
        f"- Next supplemental split: `{audit.next_supplemental_id or 'none'}`",
        f"- Next phase: {audit.next_phase}",
        f"- Next module action: `{audit.next_module_id}` - {audit.next_module_action}",
        "",
        "## Operating Rule",
        "",
        "New behavior must enter through a named module lane with profile keys, safe boot defaults, static tests, sandbox smoke evidence, and release-gate evidence. Do not add broad runtime logic directly to the main helper without updating this workplan and the module audit.",
        "",
        "The helper Overview must expose module readiness from `ctoa_helper_modules.lua` so operators can see implemented, prototype, armed, gated, and experimental lanes without enabling runtime actions.",
        "",
        "## Module Lanes",
        "",
        "| Module | Status | Target | Next step | Gate |",
        "|---|---:|---|---|---|",
    ]
    if audit.registry_missing:
        lines.insert(11, f"- Registry missing: `{', '.join(audit.registry_missing)}`")
    for item in audit.modules:
        lines.append(
            f"| `{item.id}` / {item.label} | `{item.status}` | `{item.target_file}` | {item.next_step} | {item.gate} |"
        )
    lines.extend(
        [
            "",
            "## Extraction Map",
            "",
            "| Order | Domain | Target | Status | Gate |",
            "|---:|---|---|---:|---|",
        ]
    )
    for item in sorted(audit.extraction_plan, key=lambda value: value.safe_order):
        lines.append(
            f"| {item.safe_order} | `{item.id}` / {item.source_domain} | `{item.target_file}` | `{item.status}` | {item.gate} |"
        )
    lines.extend(
        [
            "",
            "## Supplemental Refactor Plan",
            "",
            "This is the next wave after the passive helper modules are contracted. It exists because the main helper is still over budget and should become a composition shell instead of absorbing more runtime logic.",
            "",
            "| Order | Split | Target | Status | Gate |",
            "|---:|---|---|---:|---|",
        ]
    )
    for item in sorted(audit.supplemental_refactor_plan, key=lambda value: value.safe_order):
        lines.append(
            f"| {item.safe_order} | `{item.id}` / {item.source_domain} | `{item.target_file}` | `{item.status}` | {item.gate} |"
        )
    lines.extend(
        [
            "",
            "## P6 Module Lane",
            "",
            "1. Freeze the current helper UI contract with `ValidateDev`, `ctoa_helper_ui_preview.py`, and `SmokePreflight`.",
            "2. Extract domains in the `Extraction Map` order and keep the main helper as the UI composition shell.",
            "3. Execute the `Supplemental Refactor Plan` one adapter at a time; adapter files may plan or dispatch guarded actions only after static contracts exist.",
            "4. Convert prototype modules in order: Heal Friend observation, Conditions diagnostics, Equipment safe swaps, Scripting policy shell.",
            "5. For each module, add profile schema keys, safe boot defaults, tests, README/docs, `ModuleStaticGates`, and `SmokeAttachModules` before runtime enablement.",
            "6. Keep live promotion separate and require `PromoteLiveCtoa -ApproveLiveDeploy` after in-world `SmokeAttachAll` evidence.",
            "",
            "## Verification Commands",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\ops\\otclient_helper_module_audit.py --json-out runtime\\solteria_helper_dev\\module_audit.json",
            ".\\.venv\\Scripts\\python.exe -m pytest tests\\test_otclient_helper_module_audit.py tests\\test_otclient_helper_zerobot_shell.py tests\\test_otclient_helper_profile_audit.py tests\\test_ctoa_helper_smoke_report.py -q",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ValidateDev",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokePreflight",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ModuleStaticGates",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action SmokeAttachModules",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, default=DEFAULT_HELPER)
    parser.add_argument("--otclient-dir", type=Path, default=DEFAULT_OTCLIENT_DIR)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--no-plan-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_audit(
        args.helper.resolve(),
        args.otclient_dir.resolve(),
        args.plan_out.resolve(),
        args.evidence_dir.resolve(),
    )
    if args.json_out:
        write_json_atomic(args.json_out.resolve(), asdict(audit))
        print(f"[otclient-helper-module-audit] JSON: {args.json_out}")
    if not args.no_plan_write:
        write_text_atomic(args.plan_out.resolve(), render_markdown(audit))
        print(f"[otclient-helper-module-audit] Plan: {args.plan_out}")
    print(f"[otclient-helper-module-audit] Status: {audit.status}")
    print(f"[otclient-helper-module-audit] Next: {audit.next_phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
