"""Generate the next OTClient Helper module plan after extraction."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "runtime" / "solteria_helper_dev" / "next_modules_plan.json"
DEFAULT_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_next_modules_plan.md"
SHELL_BUDGET_JSON = ROOT / "runtime" / "solteria_helper_dev" / "helper_shell_budget_plan.json"


@dataclass(frozen=True)
class CandidateModule:
    order: int
    module_id: str
    label: str
    source_basis: str
    target_file: str
    first_slice: str
    gate: str
    blocked_until: str


@dataclass(frozen=True)
class SupplementalExecution:
    order: int
    workstream: str
    status: str
    current_slice: str
    next_slice: str
    gate: str


CANDIDATES = [
    CandidateModule(
        order=0,
        module_id="ui_primitives",
        label="Guarded UI primitives split",
        source_basis="Current UI composition shell plus passive UI adapter; corrected budget keeps it below cavebot/combat pressure",
        target_file="ctoa_helper_ui.lua",
        first_slice="Move text fitting, widget styling, checkbox state helpers, visibility helpers, guarded createWidget wrapper, nav/subtab style functions, button/card style descriptors, metric row styling, setting/profile/vector row styling, section/table/strip styling, priority badge styling, label styling, window chrome styling, toggle/checkbox/sidebar-card styling, overview avatar/equipment styling, control-name styling, row geometry, and tab metadata behind CTOA_HELPER_UI.",
        gate="ModuleContract, UI preview, HelperShellBudgetPlanStaticSmoke, ModuleStaticGates, and current LocalReady.",
        blocked_until="Further UI builder extraction waits for sandbox SmokeAttachModules so visual regressions can be checked in-world.",
    ),
    CandidateModule(
        order=1,
        module_id="hud",
        label="HUD overlay domain",
        source_basis="ZeroBot HUD wrapper reference plus current Tools/HUD controls",
        target_file="ctoa_helper_hud.lua",
        first_slice="Extract HUD state formatting and visibility/draggable summary without adding new overlay actions.",
        gate="HUD static contract, UI preview, ModuleStaticGates, and in-world SmokeAttach -Tab tools_hud.",
        blocked_until="Current sandbox SmokeAttachModules and fresh SmokeAttachAll evidence exist.",
    ),
    CandidateModule(
        order=2,
        module_id="hotkeys",
        label="Hotkey normalization domain",
        source_basis="ZeroBot hotkeymanager reference plus current Ctrl+H binding",
        target_file="ctoa_helper_hotkeys.lua",
        first_slice="Add parser/normalizer tests for modifier strings; keep runtime binding unchanged.",
        gate="Parser unit tests, safe boot check, UI preview, and no automatic new key bindings during loader init.",
        blocked_until="HUD extraction has tests and sandbox attach evidence.",
    ),
    CandidateModule(
        order=3,
        module_id="modal_confirm",
        label="Confirmation modal domain",
        source_basis="ZeroBot custom modal wrapper reference plus helper profile/reset workflows",
        target_file="ctoa_helper_modal.lua",
        first_slice="Create a passive modal lifecycle wrapper for destructive helper commands; no live-client action shortcuts.",
        gate="Static lifecycle tests, UI preview, no PromoteLiveCtoa bypass, and explicit approval path retained.",
        blocked_until="Hotkey parser is isolated and profile commands remain guarded.",
    ),
    CandidateModule(
        order=4,
        module_id="route_engine",
        label="Cavebot route engine split",
        source_basis="Route engine is static-gated; current shell budget now points remaining runtime pressure at combat/cavebot adapters",
        target_file="ctoa_helper_route.lua",
        first_slice="Move route labels, waypoint mutation, active target advancement, and retry-budget status into a domain module; keep autoWalk gated.",
        gate="Route editor static tests, SmokeAttach -Tab cavebot, PZ/offline guard evidence, and no movement at loader init.",
        blocked_until="Sandbox SmokeAttachModules proves current cavebot tab state in-world.",
    ),
    CandidateModule(
        order=5,
        module_id="target_scorer",
        label="Combat target scorer split",
        source_basis="Current monster-only target guards plus bot decision scoring concepts",
        target_file="ctoa_helper_targeting.lua",
        first_slice="Extract candidate scoring and ignored-name checks; keep attack/cast execution in existing guarded runtime.",
        gate="Monster-only regression tests, PZ/NPC smoke evidence, and SmokeAttachAll hunting/hunting_magic screenshots.",
        blocked_until="Route engine extraction is stable and combat runtime evidence is fresh.",
    ),
    CandidateModule(
        order=6,
        module_id="combat_runtime",
        label="Combat runtime planner split",
        source_basis="Current guarded combat runtime plus target scorer and passive adapter plan",
        target_file="ctoa_helper_combat_runtime.lua",
        first_slice="Keep passive combat planning, wait-reason text, decision-state text, and cooldown text in the runtime adapter; keep attack, cast, rune, and exeta execution in guarded helper runtime.",
        gate="Combat runtime static contract, SmokeAttach -Tab hunting_magic, PZ/offline/target-required plan evidence, and no loader-time combat actions.",
        blocked_until="Target scorer static gate is stable and sandbox combat tabs have fresh attach evidence.",
    ),
    CandidateModule(
        order=7,
        module_id="cavebot_runtime",
        label="Cavebot runtime planner split",
        source_basis="Current guarded autoWalk retry loop plus route engine and passive cavebot adapter plan",
        target_file="ctoa_helper_cavebot_runtime.lua",
        first_slice="Keep passive cavebot planning, movement decision text, movement blocked-reason/status/trace/path result text, and movement API probe summary text in the runtime adapter; keep autoWalk/findPath execution in guarded helper runtime.",
        gate="Cavebot runtime static contract, SmokeAttach -Tab cavebot, PZ/offline/empty-route/retry plan evidence, and no loader-time movement.",
        blocked_until="Route engine static gate is stable and sandbox cavebot tab has fresh attach evidence.",
    ),
    CandidateModule(
        order=8,
        module_id="loot_runtime",
        label="Loot runtime planner split",
        source_basis="Current loot feature flag, API probe, and passive loot adapter plan",
        target_file="ctoa_helper_loot_runtime.lua",
        first_slice="Use a passive loot runtime planner for diagnostics text; keep container scan/open/move/use behavior outside loader init and guarded by feature flags.",
        gate="Loot runtime static contract, SmokeAttach -Tab tools_diag, feature-flag/offline/container plan evidence, and no loader-time loot actions.",
        blocked_until="Experimental loot stays feature-flagged and sandbox diagnostics have fresh attach evidence.",
    ),
    CandidateModule(
        order=9,
        module_id="timer_runtime",
        label="Timer runtime planner split",
        source_basis="Current guarded timer loop plus passive timer adapter plan",
        target_file="ctoa_helper_timer_runtime.lua",
        first_slice="Use a passive timer runtime planner for timer decision/status text; keep talk/cast execution in the guarded helper runtime.",
        gate="Timer runtime static contract, SmokeAttach -Tab tools_timer, disabled/PZ/offline/message plan evidence, and no loader-time timer actions.",
        blocked_until="Timer remains disabled by default and sandbox tools timer tab has fresh attach evidence.",
    ),
    CandidateModule(
        order=10,
        module_id="profile_schema",
        label="Profile schema, persistence policy, rotation metadata, and migration metadata",
        source_basis="Current EK profile defaults plus passive profile schema adapter plan",
        target_file="ctoa_helper_profile_schema.lua + ctoa_helper_profile_persistence.lua",
        first_slice="Use passive profile schema metadata for required sections, safe false keys, rotation preset labels/summaries, migration readiness, load candidate lists, save path policy, generated save headers, load/save status text, and autosave metadata; keep file reads/writes in existing guarded profile audit/persistence shell paths.",
        gate="Profile schema static contract, profile audit parity, safe-boot false-key coverage, rotation-summary coverage, key-order preservation, and no loader-time profile writes.",
        blocked_until="Profile audit and ModuleStaticGates stay current for the staged helper manifest.",
    ),
    CandidateModule(
        order=11,
        module_id="vbot_import",
        label="External vBot/vBot-like import lane",
        source_basis="source_required: no vBot source is present in this checkout",
        target_file="docs/otclient/vbot_import_review.md",
        first_slice="If a vBot source tree is provided, run otclient_external_bot_intake.py and require its import_gate before capability mapping; no direct copy without license/source notes.",
        gate="Intake import_gate, source provenance note, secret scan, license/provenance review, runtime_gate_mapping, and mapping into existing module gates.",
        blocked_until="User provides the actual vBot source or a reviewed local archive.",
    ),
]

SUPPLEMENTAL_EXECUTION = [
    SupplementalExecution(
        order=0,
        workstream="ui_primitives",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_ui.lua owns text fit, widget style, checkbox state, visibility, guarded createWidget, nav/subtab style, button/card style, metric row/value style, setting/profile/vector row style, section/table/header strip style, priority badge style, label style, window chrome style, toggle/checkbox/sidebar-card style, overview avatar/equipment slot style, control-name style primitives, setting/profile/vector/section row geometry, sidebar/subtab metadata, section scaffold metadata, subtab content offsets, tools table-header metadata, CaveBot action/choice metadata, interactive profile/vector row builders, the passive Hunting targeting/magic panel renderer, the passive CaveBot editor renderer, the passive Tools helper/PvP/HUD/timer/diag panel renderer, the passive Settings/Profile renderer, and the passive Engine/HUD/layout renderer; helper shell now delegates all direct styleWidget calls, row geometry, tab metadata, repeated body/header scaffolding, subtab button creation, cavebot waypoint editor composition/action metadata, tools table headers, hunting targeting/magic composition, tools helper/PvP/HUD/timer/diag composition, profile/settings composition, Engine/HUD/layout composition, and profile cycle/step/vector row construction through UI functions with guarded shell adapters.",
        next_slice="Extract remaining runtime probe summaries into passive runtime adapters while keeping value getters/setters, route mutation, and runtime arming in guarded shell adapters.",
        gate="ModuleContract, UI preview, HelperShellBudgetPlanStaticSmoke, ModuleStaticGates, current LocalReady, then SmokeAttachModules for in-world visual evidence.",
    ),
    SupplementalExecution(
        order=1,
        workstream="target_scorer",
        status="in_progress_static_gated",
        current_slice="Targeting owns bestCandidate ranking; helper now builds OTClient candidate snapshots and delegates best-target choice to ctoa_helper_targeting.lua.",
        next_slice="Move the remaining PZ/NPC reason summaries into targeting/combat runtime adapters before adding any new combat feature.",
        gate="TargetingStaticSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach hunting and hunting_magic tabs in sandbox before runtime enablement.",
    ),
    SupplementalExecution(
        order=2,
        workstream="route_engine",
        status="in_progress_static_gated",
        current_slice="Route labels, waypoint mutation, active target advancement, retry status, progress state, retryBlocked, selected summary, passive CaveBot editor panel, cavebot runtime decision text, movement blocked-reason/status/trace/path result text, and movement API probe summary text are module/UI-owned.",
        next_slice="Move the next cavebot route/probe metadata slice into route/cavebot runtime adapters while keeping movement execution in guarded runtime.",
        gate="RouteStaticSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach cavebot tab in sandbox.",
    ),
    SupplementalExecution(
        order=3,
        workstream="heal_friend_observer",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_heal_friend.lua owns whitelist matching, visible-player scan, observer updates, runtime plan, status text, decision text, and summary text; helper shell now only passes OTClient context and renders module output.",
        next_slice="Refresh sandbox no-target evidence, add whitelist persistence review, and keep sio execution unavailable until ModuleAttachSmoke, SmokeAttachAll, and live approval are current.",
        gate="HealFriendNoTargetSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach heal_friend tab in sandbox before any sio runtime bridge.",
    ),
    SupplementalExecution(
        order=4,
        workstream="conditions_observer",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_conditions.lua owns condition flag text, state snapshots, API probe text, observer sampling, passive recovery plan, and summary text; helper shell now only passes OTClient context and renders module output.",
        next_slice="Add sandbox state evidence and keep condition recovery actions unavailable until API probe output, ModuleAttachSmoke, SmokeAttachAll, and live approval are current.",
        gate="ConditionsObserverSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach conditions tab in sandbox before any condition recovery runtime bridge.",
    ),
    SupplementalExecution(
        order=5,
        workstream="equipment_observer",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_equipment.lua owns slot text, equipment snapshots, inventory API probe text, observer sampling, passive swap plan, and summary text; helper shell now only passes OTClient context and renders module output.",
        next_slice="Add sandbox inventory slot evidence and keep ring/amulet swap actions unavailable until inventory API output, ModuleAttachSmoke, SmokeAttachAll, and live approval are current.",
        gate="EquipmentObserverSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach equipment tab in sandbox before any equipment swap runtime bridge.",
    ),
    SupplementalExecution(
        order=6,
        workstream="scripting_policy",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_scripting.lua owns policy snapshots, deny-all planning, and summary text; helper shell only delegates policy rendering and keeps eval/snippets forced off.",
        next_slice="Add sandbox policy-shell evidence and keep all snippet/eval execution unavailable until security review, audit logging, ModuleAttachSmoke, SmokeAttachAll, and live approval are current.",
        gate="ScriptingPolicySmoke, ModuleStaticGates, current LocalReady, then SmokeAttach scripting tab in sandbox; no runtime eval or snippet bridge.",
    ),
    SupplementalExecution(
        order=7,
        workstream="operator_summary_bridge",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_operator_summary.lua owns title/domain/profile/UI summary composition; helper shell now only passes local context and renders returned text.",
        next_slice="Move any remaining operator-facing summary branches into the module before adding new runtime features, keeping summaries passive and widget-free.",
        gate="Operator summary static contract, OperatorSummaryStaticSmoke, ModuleStaticGates, UI preview, current LocalReady, then SmokeAttachModules in sandbox before summaries can inform runtime bridge decisions.",
    ),
    SupplementalExecution(
        order=8,
        workstream="input_contracts",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_hotkeys.lua owns passive binding decisions, ctoa_helper_modal.lua owns passive confirmation decision text, and otclient_input_contract_fixtures.py now records behavior fixtures for parser and modal states.",
        next_slice="Expand fixture cases whenever a new keyboard shortcut, destructive helper action, or external bot command mapping is proposed; keep actual binding and execution inside guarded helper shell paths.",
        gate="InputContractsStaticSmoke, HotkeysStaticSmoke, ModalStaticSmoke, ModuleStaticGates, current LocalReady, and no loader-time key binding beyond the existing guarded helper toggle.",
    ),
    SupplementalExecution(
        order=9,
        workstream="profile_persistence",
        status="in_progress_static_gated",
        current_slice="ctoa_helper_profile_schema.lua owns key order, serializer, labels, summaries, and schema metadata; ctoa_helper_profile_persistence.lua now owns passive load candidates, save path fallback policy, generated save headers, load/save status text, and autosave delay metadata. The helper shell still owns every dofile, io.open, dirty flag mutation, and save execution path.",
        next_slice="Move profile export field grouping into schema/persistence descriptors once profile audit parity has fixtures for every generated section; keep actual profile writes in guarded shell paths.",
        gate="Profile schema contract, ProfileSchemaStaticSmoke, module contract, profile audit parity, HelperShellBudgetPlanStaticSmoke, ModuleStaticGates, and current LocalReady.",
    ),
    SupplementalExecution(
        order=10,
        workstream="runtime_bridge_review",
        status="blocked_by_sandbox_evidence",
        current_slice="Runtime policy, dispatch guard, queue, readiness, action catalog, decision trace, sandbox handoff, and feature flags are static-gated only.",
        next_slice="After sandbox SmokeAttachModules and SmokeAttachAll, review whether any plan can move from passive decision text to guarded runtime dispatcher wiring.",
        gate="No runtime bridge until ModuleAttachSmoke, SmokeAttachAll, and explicit PromoteLiveCtoa -ApproveLiveDeploy path stay green.",
    ),
]


def current_budget_priority() -> dict:
    source = str(SHELL_BUDGET_JSON.relative_to(ROOT))
    if not SHELL_BUDGET_JSON.is_file():
        return {
            "status": "missing",
            "source": source,
            "next_extraction_domains": [],
            "top_non_shell_domain": "",
            "next_action": "Run otclient_helper_shell_budget_plan.py before choosing the next extraction.",
        }
    payload = json.loads(SHELL_BUDGET_JSON.read_text(encoding="utf-8"))
    domains = payload.get("next_extraction_domains") or []
    return {
        "status": payload.get("status", "unknown"),
        "source": source,
        "helper_line_count": payload.get("helper_line_count"),
        "helper_function_count": payload.get("helper_function_count"),
        "next_extraction_domains": domains,
        "top_non_shell_domain": domains[0] if domains else "",
        "next_action": payload.get("next_action", ""),
    }


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


def build_payload() -> dict:
    candidate_modules = []
    smoke_script = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"
    smoke_source = smoke_script.read_text(encoding="utf-8") if smoke_script.is_file() else ""
    for item in CANDIDATES:
        data = asdict(item)
        if item.module_id == "vbot_import":
            data["status"] = "source_required"
        elif item.module_id == "ui_primitives" and "ctoa_helper_ui.lua" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "hud" and "HudStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "hotkeys" and "HotkeysStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "modal_confirm" and "ModalStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "route_engine" and "RouteStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "target_scorer" and "TargetingStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "combat_runtime" and "CombatRuntimeStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "cavebot_runtime" and "CavebotRuntimeStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "loot_runtime" and "LootRuntimeStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "timer_runtime" and "TimerRuntimeStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id == "profile_schema" and "ProfileSchemaStaticSmoke" in smoke_source:
            data["status"] = "static_gated"
        elif item.module_id in {
            "hud",
            "hotkeys",
            "modal_confirm",
            "route_engine",
            "target_scorer",
            "combat_runtime",
            "cavebot_runtime",
            "loot_runtime",
            "timer_runtime",
            "profile_schema",
            "ui_primitives",
        } and ".contract" in (
            ROOT / "scripts" / "lua" / "otclient" / item.target_file
        ).read_text(encoding="utf-8"):
            data["status"] = "contracted"
        elif (ROOT / "scripts" / "lua" / "otclient" / item.target_file).is_file():
            data["status"] = "started"
        else:
            data["status"] = "planned"
        candidate_modules.append(data)
    return {
        "schema_version": 1,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "status": "ready_for_sandbox_then_next_module_design",
        "current_budget_priority": current_budget_priority(),
        "source_policy": {
            "zerobot_reference": "docs/otclient/zerobot_reference.md",
            "vbot": "source_required",
            "external_bot_intake": "scripts/ops/otclient_external_bot_intake.py",
            "external_bot_import_gate": "import_gate.runtime_import_allowed must remain false until mapped module gates and sandbox evidence pass",
            "rule": "Use external bots as capability checklists and naming references only; no direct copy without provenance review; keep CTOAi safe boot, gates, and tests.",
        },
        "prerequisites": [
            "Run SmokeAttachModules after sandbox character is in-world.",
            "Run SmokeAttachAll for the current dev manifest before enabling runtime actions.",
            "Keep PromoteLiveCtoa behind -ApproveLiveDeploy.",
        ],
        "candidate_modules": candidate_modules,
        "supplemental_execution": [asdict(item) for item in SUPPLEMENTAL_EXECUTION],
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Solteria Helper Next Modules Plan",
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        "- Current extraction map: complete.",
        f"- Budget priority source: `{payload['current_budget_priority']['source']}`.",
        f"- Budget top non-shell domain: `{payload['current_budget_priority']['top_non_shell_domain']}`.",
        f"- Budget next extraction domains: `{', '.join(payload['current_budget_priority']['next_extraction_domains'])}`.",
        "- Runtime blocker: in-world `SmokeAttachModules` and fresh `SmokeAttachAll` are still required before runtime enablement.",
        "- External vBot source: `source_required`; do not claim vBot-derived implementation until source/provenance is present.",
        "",
        "## Source Policy",
        "",
        f"- ZeroBot reference: `{payload['source_policy']['zerobot_reference']}`",
        f"- vBot: `{payload['source_policy']['vbot']}`",
        f"- External bot intake: `{payload['source_policy']['external_bot_intake']}`",
        f"- External bot import gate: {payload['source_policy']['external_bot_import_gate']}",
        f"- Rule: {payload['source_policy']['rule']}",
        "",
        "## Prerequisites",
        "",
    ]
    for item in payload["prerequisites"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Candidate Modules",
            "",
            "| Order | Module | Status | Source basis | Target | First slice | Gate | Blocked until |",
            "|---:|---|---:|---|---|---|---|---|",
        ]
    )
    for item in payload["candidate_modules"]:
        lines.append(
            f"| {item['order']} | `{item['module_id']}` / {item['label']} | `{item['status']}` | {item['source_basis']} | `{item['target_file']}` | {item['first_slice']} | {item['gate']} | {item['blocked_until']} |"
        )
    lines.extend(
        [
            "",
            "## Supplemental Execution Plan",
            "",
            "| Order | Workstream | Status | Current slice | Next slice | Gate |",
            "|---:|---|---:|---|---|---|",
        ]
    )
    for item in payload["supplemental_execution"]:
        lines.append(
            f"| {item['order']} | `{item['workstream']}` | `{item['status']}` | {item['current_slice']} | {item['next_slice']} | {item['gate']} |"
        )
    lines.extend(
        [
            "",
            "## Operator Sequence",
            "",
            "1. Finish sandbox attach evidence for the current package.",
            "2. Keep the new module as passive/read-only unless its gate explicitly allows runtime action.",
            "3. Add profile keys, safe boot defaults, module registry entry, package copy, README note, static smoke, and release-gate evidence for every new module.",
            "4. Promote a module from `contracted` to `static_gated` only after its dedicated static smoke is included in `ModuleStaticGates`.",
            "5. Maintain the supplemental status-board lane (`ctoa_helper_module_status.lua`) so module readiness, blockers, and static-only modules remain visible before any runtime bridge work.",
            "6. Maintain the supplemental action-catalog lane (`ctoa_helper_action_catalog.lua`) so future features declare action names, risk class, and required gates before any dispatcher can consume them.",
            "7. Maintain the supplemental decision-trace lane (`ctoa_helper_decision_trace.lua`) so runtime policy and dispatch guard reasons are visible before any queued plan is reviewed.",
            "8. Maintain the supplemental sandbox-handoff lane (`ctoa_helper_sandbox_handoff.lua`) so Launch, ReadyCheck, SmokeAttachModules, SmokeAttachAll, and PromoteLiveCtoa approval remain one explicit operator sequence.",
            "9. Maintain the supplemental feature-flag lane (`ctoa_helper_feature_flags.lua`) so every future feature declares default disabled state, domain, and required gate before runtime code can consume it.",
            "10. Only then consider runtime enablement, and only in sandbox first.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Solteria Helper next module plan")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()

    payload = build_payload()
    write_text_atomic(args.json_out, json.dumps(payload, indent=2))
    write_text_atomic(args.plan_out, render_markdown(payload))
    print(f"[otclient-helper-next-modules-plan] JSON: {args.json_out}")
    print(f"[otclient-helper-next-modules-plan] Plan: {args.plan_out}")
    print(f"[otclient-helper-next-modules-plan] Status: {payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
