from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROADMAP_JSON = ROOT / "AI" / "P17_P24_HELPER_EVOLUTION_ROADMAP.json"
ROADMAP_MD = ROOT / "AI" / "P17_P24_HELPER_EVOLUTION_ROADMAP.md"
AUDIT_MD = ROOT / "docs" / "otclient" / "HELPER_SIMPLIFICATION_AUDIT_2026-07-16.md"
NATIVE_HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
HELPER_UI = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_ui.lua"


def test_helper_evolution_roadmap_preserves_release_boundaries() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))

    assert roadmap["schema_version"] == "ctoa.helper-evolution-roadmap.v1"
    assert roadmap["status"] == "static_refactor_in_progress"
    assert roadmap["primary_project"] == "CTOAi Helper"
    assert roadmap["secondary_project"] == "CTOAi Safe"
    assert roadmap["current_evidence_dependency"] == "P14"
    assert roadmap["execution_policy"] == {
        "static_refactor_during_p14": True,
        "runtime_acceptance_requires_p14_complete": True,
        "sandbox_first": True,
        "live_requires_separate_explicit_approval": True,
        "safe_acceptance_never_satisfies_helper_gates": True,
    }
    assert [phase["id"] for phase in roadmap["phases"]] == [
        "P17",
        "P18",
        "P19",
        "P20",
        "P21",
        "P22",
        "P23",
        "P24",
        "P25",
        "P26",
        "P27",
        "P28",
    ]


def test_condition_contract_is_generic_instead_of_vocation_hardcoded() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    contract = roadmap["condition_contract"]

    assert contract["metrics"] == [
        "hp_percent",
        "mana_percent",
        "monster_count",
        "distance",
        "pz",
        "active_condition",
    ]
    assert contract["operators"] == ["<", "<=", "=", "!=", ">=", ">"]
    assert contract["combinators"] == ["AND", "OR"]
    assert contract["dispatch_controls"] == [
        "cooldown",
        "hysteresis",
        "bounded_randomization",
    ]


def test_roadmap_and_audit_record_confirmed_helper_debt() -> None:
    roadmap_text = ROADMAP_MD.read_text(encoding="utf-8")
    audit_text = AUDIT_MD.read_text(encoding="utf-8")

    for marker in (
        "P17", "P18", "P19", "P20", "P21", "P22",
        "P23", "P24", "P25", "P26", "P27", "P28",
    ):
        assert marker in roadmap_text

    for marker in (
        "hasAttackTarget",
        "countMonsters",
        "ctoaToolsHudEnabled",
        "ctoaUiHudEnabled",
        "Auto Haste",
    ):
        assert marker in audit_text


def test_p17_2_removes_proven_dead_native_locals() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    helper_text = NATIVE_HELPER.read_text(encoding="utf-8")

    assert roadmap["baseline"]["current_native_helper_lines"] == len(helper_text.splitlines()) == 3576
    assert roadmap["baseline"]["current_native_helper_functions"] == 102
    p17 = next(item for item in roadmap["phases"] if item["id"] == "P17")
    p17_9 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P17.9")
    assert p17["status"] == "complete"
    assert p17_9["validation"]["module_audit_status"] == "ready"
    for name in roadmap["baseline"]["resolved_dead_local_candidates"]:
        assert f"local function {name}(" not in helper_text


def test_p18_1_closes_versioned_rule_migration_without_runtime_authority() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    p18 = next(item for item in roadmap["phases"] if item["id"] == "P18")
    slice_ = next(item for item in roadmap["immediate_slices"] if item["id"] == "P18.1")

    assert p18["status"] == "complete"
    assert slice_["status"] == "complete"
    assert slice_["runtime_authority"] is False
    assert slice_["validation"]["legacy_rules_safe_disabled"] is True
    assert slice_["validation"]["future_versions_fail_closed"] is True

    p21 = next(item for item in roadmap["phases"] if item["id"] == "P21")
    p21_1 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P21.1")
    assert p21["status"] == "complete"
    assert p21_1["status"] == "complete"
    assert p21_1["runtime_authority"] is False

    p21_2 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P21.2")
    assert p21_1["validation"]["vocation_pack_bytes_removed"] == 1416
    assert p21_2["status"] == "complete"
    assert p21_2["runtime_authority"] is False
    assert p21_2["validation"]["removed_native_shell_lines"] == 180

    p22 = next(item for item in roadmap["phases"] if item["id"] == "P22")
    p22_1 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P22.1")
    assert p22["status"] == "complete"
    assert p22_1["status"] == "complete"
    assert p22_1["runtime_authority"] is False
    assert p22_1["validation"]["shared_rule_editor_chrome_consumers"] == 3
    assert p22_1["validation"]["preview_layout_issues"] == 0

    p22_2 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P22.2")
    assert p22_2["status"] == "complete"
    assert p22_2["runtime_authority"] is False
    assert p22_2["validation"]["distinct_visual_roles"] == 4
    assert p22_2["validation"]["compact_preview_layout_issues"] == 0

    p23 = next(item for item in roadmap["phases"] if item["id"] == "P23")
    p23_1 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P23.1")
    assert p23["status"] == "complete"
    assert p23_1["status"] == "complete"
    assert p23_1["runtime_authority"] is False
    assert p23_1["validation"]["parity_cases"] == 10
    assert p23_1["validation"]["safe_runtime_tree_files_added"] == 0

    p23_2 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P23.2")
    assert p23_2["status"] == "complete"
    assert p23_2["runtime_authority"] is False
    assert p23_2["validation"]["decision"] == "no_shared_runtime_core"
    assert p23_2["validation"]["shared_runtime_files"] == 0
    assert p23_2["validation"]["runtime_randomization_parity"] is False
    assert p23_2["validation"]["targeted_tests"] == 52
    assert p23_2["validation"]["module_audit_status"] == "ready"
    assert p23_2["validation"]["engine_brain_doc_sync"] == "passed"
    assert p23_2["validation"]["engine_brain_secret_guardrail"] == "passed"
    assert p23_2["validation"]["engine_brain_doctor"] == "warn"
    assert p23_2["validation"]["engine_brain_doctor_failures"] == 0

    p24_1 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P24.1")
    assert p24_1["status"] == "complete"
    assert p24_1["runtime_authority"] is False
    assert p24_1["validation"]["p18_p23_replay_tests"] == 61
    assert p24_1["validation"]["independent_runner_status"] == "externally_verified_stale"
    assert p24_1["validation"]["canary_execution_authorized"] is False

    p24 = next(item for item in roadmap["phases"] if item["id"] == "P24")
    p24_2 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P24.2")
    assert p24["status"] == "in_progress"
    assert p24_2["status"] == "in_progress"
    assert p24_2["runtime_authority"] is False
    assert p24_2["validation"]["official_stage_file_count"] == 63
    assert p24_2["validation"]["github_hosted_current_revision"] is True
    assert p24_2["validation"]["self_hosted_runner_online"] is False

    p25 = next(item for item in roadmap["phases"] if item["id"] == "P25")
    p25_1 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P25.1")
    p25_2 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P25.2")
    assert p25["status"] == "complete"
    assert p25_1["status"] == "complete"
    assert p25_1["runtime_authority"] is False
    assert p25_1["validation"]["package_files_before"] == 65
    assert p25_1["validation"]["package_files_after"] == 62
    assert p25_1["validation"]["legacy_runtime_files_in_zip"] == 0
    assert p25_2["status"] == "complete"
    assert p25_2["runtime_authority"] is False
    assert p25_2["validation"]["derived_active_inventory_consumers"] == 4

    p26_1 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P26.1")
    p26_2 = next(item for item in roadmap["immediate_slices"] if item["id"] == "P26.2")
    p26 = next(item for item in roadmap["phases"] if item["id"] == "P26")
    assert p26["status"] == "in_progress"
    assert p26_1["status"] == "complete"
    assert p26_1["runtime_authority"] is False
    assert p26_1["validation"]["official_stage_file_count"] == 63
    assert p26_1["validation"]["preview_layout_issues"] == 0
    assert p26_2["status"] == "not_started"
    assert p26_2["runtime_authority"] is False


def test_p19_1_opens_target_name_policy_without_runtime_authority() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    ui_text = HELPER_UI.read_text(encoding="utf-8")
    targeting_text = (ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_targeting.lua").read_text(encoding="utf-8")

    slice_ = next(item for item in roadmap["immediate_slices"] if item["id"] == "P19.1")
    assert slice_["status"] == "complete"
    assert slice_["runtime_authority"] is False
    assert '"ctoaTargetRuleEditorIgnored"' in ui_text
    assert '"ctoaTargetRuleEditorPriority"' in ui_text
    assert "function Targeting.updateNameList" in targeting_text
    assert roadmap["baseline"]["confirmed_rigid_lanes"] == []


def test_p19_2_opens_ordered_spell_rules_without_runtime_authority() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    ui_text = HELPER_UI.read_text(encoding="utf-8")
    combat_text = (
        ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua"
    ).read_text(encoding="utf-8")

    slice_ = next(item for item in roadmap["immediate_slices"] if item["id"] == "P19.2")
    assert slice_["status"] == "complete"
    assert slice_["runtime_authority"] is False
    assert slice_["validation"]["preview_layout_issues"] == 0
    assert '"ctoaMagicRuleEditor"' in ui_text
    assert '"ctoaMagicRuleAdd"' in ui_text
    assert '"ctoaMagicRuleRemove"' in ui_text
    assert "function CombatRuntime.addRotationRule" in combat_text
    assert "function CombatRuntime.moveRotationRule" in combat_text
    assert '"ctoaRotationGranMobs"' not in ui_text


def test_p19_3_completes_ordered_target_and_combat_action_configuration() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    ui_text = HELPER_UI.read_text(encoding="utf-8")
    targeting_text = (
        ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_targeting.lua"
    ).read_text(encoding="utf-8")
    combat_text = (
        ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua"
    ).read_text(encoding="utf-8")

    slice_ = next(item for item in roadmap["immediate_slices"] if item["id"] == "P19.3")
    phase = next(item for item in roadmap["phases"] if item["id"] == "P19")
    assert slice_["status"] == "complete" and slice_["runtime_authority"] is False
    assert phase["status"] == "complete"
    assert slice_["validation"]["preview_widgets"] == 208
    assert '"ctoaTargetRuleAdd"' in ui_text and '"ctoaTargetRuleDown"' in ui_text
    assert '"ctoaCombatActionAdd"' in ui_text and '"ctoaCombatActionDown"' in ui_text
    assert "function Targeting.matchTargetRule" in targeting_text
    assert "function CombatRuntime.runeAction" in combat_text
    assert roadmap["baseline"]["confirmed_rigid_lanes"] == []


def test_p20_completes_data_driven_spell_state_and_anti_spam_contract() -> None:
    roadmap = json.loads(ROADMAP_JSON.read_text(encoding="utf-8"))
    registry_text = (
        ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_spell_state_registry.lua"
    ).read_text(encoding="utf-8")
    combat_text = (
        ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua"
    ).read_text(encoding="utf-8")

    slice_ = next(item for item in roadmap["immediate_slices"] if item["id"] == "P20.1")
    phase = next(item for item in roadmap["phases"] if item["id"] == "P20")
    assert slice_["status"] == "complete" and slice_["runtime_authority"] is False
    assert phase["status"] == "complete"
    assert slice_["validation"]["deterministic_transition_replay"] is True
    assert "function SpellStateRegistry.observeAll" in registry_text
    assert "function SpellStateRegistry.decisionMap" in registry_text
    assert "bounded_unknown_fallback" in registry_text
    assert "stateDecisions[rule.state_id].allowed == true" in combat_text
    for vocation in ("ek", "ms", "ed", "rp"):
        profile = (ROOT / "scripts" / "lua" / "otclient" / f"ctoa_{vocation}_profile.lua").read_text(encoding="utf-8")
        assert "spell_state_families" in profile


def test_p17_3_has_one_hud_configuration_owner() -> None:
    ui_text = HELPER_UI.read_text(encoding="utf-8")
    helper_text = NATIVE_HELPER.read_text(encoding="utf-8")

    assert "ctoaToolsHudEnabled" not in ui_text
    assert "ctoaToolsHudPos" not in ui_text
    assert "ctoaToolsHudTab" not in ui_text
    assert ui_text.count('"ctoaUiHudEnabled"') == 1
    assert ui_text.count('"ctoaUiHudPos"') == 1
    assert 'if subtab == "hud" then' in helper_text
    assert 'switchTab("ui")' in helper_text
