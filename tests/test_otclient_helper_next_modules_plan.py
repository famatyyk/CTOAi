import json
from pathlib import Path

from scripts.ops import otclient_helper_next_modules_plan as plan


def test_next_modules_plan_is_safe_and_ordered():
    payload = plan.build_payload()
    modules = payload["candidate_modules"]
    supplemental = payload["supplemental_execution"]

    assert payload["status"] == "p13_ready_to_start"
    assert (
        payload["operational_acceptance_status"]
        == "p12_heal_friend_closed_no_action"
    )
    assert payload["active_phase"] == {
        "phase": "P13",
        "conditions": "operational_acceptance_complete",
        "equipment": "operational_acceptance_complete",
        "heal_friend": "closed_blocked_no_compatible_vocation",
        "next_action": "Start P13 Runtime Evidence And Machine-Readable Roadmap State; preserve the ED-only Heal Friend closure as terminal no-action evidence and do not reuse its expired session approval.",
    }
    assert (
        payload["current_budget_priority"]["source"]
        == "runtime/solteria_helper_dev/helper_shell_budget_plan.json"
    )
    expected_domains = payload["current_budget_priority"]["next_extraction_domains"]
    assert expected_domains == ["roadmap_state_evidence"]
    assert (
        payload["current_budget_priority"]["top_non_shell_domain"]
        == "roadmap_state_evidence"
    )
    if plan.SHELL_BUDGET_JSON.exists():
        budget = json.loads(plan.SHELL_BUDGET_JSON.read_text(encoding="utf-8"))
        raw_domains = payload["current_budget_priority"]["raw_next_extraction_domains"]
        assert raw_domains == budget["next_extraction_domains"]
        assert {"diagnostics_smoke", "runtime_cavebot", "runtime_combat"}.issubset(
            raw_domains
        )
    else:
        assert payload["current_budget_priority"]["raw_next_extraction_domains"] == []
    assert payload["source_policy"]["vbot"] == "capability_mapping_only"
    assert (
        payload["source_policy"]["external_bot_intake"]
        == "scripts/ops/otclient_external_bot_intake.py"
    )
    assert (
        "runtime_import_allowed must remain false"
        in payload["source_policy"]["external_bot_import_gate"]
    )
    assert [item["module_id"] for item in modules] == [
        "ui_primitives",
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
        "vbot_import",
    ]
    assert modules[0]["status"] == "static_gated"
    assert modules[0]["first_slice"].startswith("Move text fitting")
    assert "below cavebot/combat pressure" in modules[0]["source_basis"]
    assert modules[1]["status"] == "static_gated"
    assert modules[1]["first_slice"].startswith("Extract HUD state formatting")
    assert modules[2]["status"] == "static_gated"
    assert "no automatic new key bindings" in modules[2]["gate"]
    assert modules[3]["status"] == "static_gated"
    assert "explicit approval path retained" in modules[3]["gate"]
    assert modules[4]["status"] == "static_gated"
    assert (
        "remaining runtime pressure at combat/cavebot adapters"
        in modules[4]["source_basis"]
    )
    assert "no movement at loader init" in modules[4]["gate"]
    assert modules[5]["status"] == "static_gated"
    assert "Monster-only regression tests" in modules[5]["gate"]
    assert modules[6]["status"] == "deferred_high_risk_refactor_only"
    assert "no loader-time combat actions" in modules[6]["gate"]
    assert modules[7]["status"] == "deferred_high_risk_refactor_only"
    assert "no loader-time movement" in modules[7]["gate"]
    assert modules[8]["status"] == "static_gated"
    assert "no loader-time loot actions" in modules[8]["gate"]
    assert modules[9]["status"] == "static_gated"
    assert "no loader-time timer actions" in modules[9]["gate"]
    assert modules[10]["status"] == "static_gated"
    assert "no loader-time profile writes" in modules[10]["gate"]
    assert modules[-1]["status"] == "capability_mapping_only"
    assert [item["workstream"] for item in supplemental] == [
        "ui_primitives",
        "target_scorer",
        "route_engine",
        "conditions_runtime_gate",
        "equipment_runtime_gate",
        "heal_friend_runtime_gate",
        "scripting_policy",
        "operator_summary_bridge",
        "input_contracts",
        "profile_persistence",
        "runtime_bridge_review",
    ]
    assert supplemental[0]["status"] == "in_progress_static_gated"
    assert "ctoa_helper_ui.lua owns text fit" in supplemental[0]["current_slice"]
    assert "CaveBot action/choice metadata" in supplemental[0]["current_slice"]
    assert supplemental[1]["status"] == "in_progress_static_gated"
    assert "bestCandidate" in supplemental[1]["current_slice"]
    assert supplemental[2]["status"] == "in_progress_static_gated"
    assert "progress state" in supplemental[2]["current_slice"]
    assert "active target advancement" in supplemental[2]["current_slice"]
    assert (
        "movement blocked-reason/status/trace/path result text"
        in supplemental[2]["current_slice"]
    )
    assert "movement API probe summary text" in supplemental[2]["current_slice"]
    assert supplemental[7]["workstream"] == "operator_summary_bridge"
    assert "operator summary" in supplemental[7]["gate"].lower()
    assert supplemental[8]["workstream"] == "input_contracts"
    assert "InputContractsStaticSmoke" in supplemental[8]["gate"]
    assert "HotkeysStaticSmoke" in supplemental[8]["gate"]
    assert "ModalStaticSmoke" in supplemental[8]["gate"]
    assert "otclient_input_contract_fixtures.py" in supplemental[8]["current_slice"]
    assert supplemental[3]["status"] == "operational_acceptance_complete"
    assert supplemental[4]["status"] == "operational_acceptance_complete"
    assert supplemental[5]["status"] == "closed_blocked_no_compatible_vocation"
    assert "vocation_must_be_ed" in supplemental[5]["current_slice"]
    assert "attempt count 0" in supplemental[5]["current_slice"]
    assert "p13_ready_to_start" == supplemental[-1]["status"]
    assert "deferred_high_risk" in supplemental[-1]["current_slice"]
    assert all(
        "SmokeAttach" in item["gate"]
        or item["module_id"]
        in {
            "ui_primitives",
            "hotkeys",
            "modal_confirm",
            "profile_schema",
            "vbot_import",
        }
        for item in modules
    )
    assert "no direct copy" in payload["source_policy"]["rule"]


def test_vbot_import_review_keeps_capability_mapping_only_contract():
    review = (plan.ROOT / "docs" / "otclient" / "vbot_import_review.md").read_text(
        encoding="utf-8"
    )

    assert "Status: `capability_mapping_only`" in review
    assert "No source archive was imported into this checkout" in review
    assert "otclient_external_bot_intake.py" in review
    assert "`import_gate.runtime_import_allowed`" in review
    assert "`capability_mapping_only`" in review
    assert "`runtime_gate_mapping`" in review
    assert "`combat_runtime`" in review
    assert "License text or explicit permission note" in review
    assert "SHA256" in review
    assert "Secret scan result" in review
    assert "Only behavior-level capability mapping is permitted." in review
    assert "`ctoa_helper_targeting.lua`" in review
    assert "`ctoa_helper_route.lua`" in review
    assert "`ctoa_helper_heal_friend.lua`" in review
    assert "SmokeAttachModules" in review
    assert "PromoteLiveCtoa" in review


def test_next_modules_plan_markdown_calls_out_runtime_blockers():
    payload = plan.build_payload()
    markdown = plan.render_markdown(payload)

    assert "# Solteria Helper Next Modules Plan" in markdown
    assert "Current extraction map: complete" in markdown
    expected_domains = payload["current_budget_priority"]["next_extraction_domains"]
    expected_top = expected_domains[0] if expected_domains else "unavailable"
    assert f"Budget top non-shell domain: `{expected_top}`" in markdown
    assert (
        f"Budget next extraction domains: `{', '.join(expected_domains[:3])}"
        in markdown
    )
    assert "External vBot source: `capability_mapping_only`" in markdown
    assert (
        "External bot intake: `scripts/ops/otclient_external_bot_intake.py`" in markdown
    )
    assert "External bot import gate:" in markdown
    assert "`ui_primitives` / Guarded UI primitives split | `static_gated`" in markdown
    assert "`hud` / HUD overlay domain | `static_gated`" in markdown
    assert "`hotkeys` / Hotkey normalization domain | `static_gated`" in markdown
    assert "`modal_confirm` / Confirmation modal domain | `static_gated`" in markdown
    assert "`route_engine` / Cavebot route engine split | `static_gated`" in markdown
    assert "`target_scorer` / Combat target scorer split | `static_gated`" in markdown
    assert "`conditions_runtime_gate`" in markdown
    assert "`conditions_runtime_gate` | `operational_acceptance_complete`" in markdown
    assert "44-case fixture pack" in markdown
    assert "ctoa.ps1 otp9" in markdown
    assert "`equipment_runtime_gate`" in markdown
    assert "ctoa_helper_equipment_runtime_gate.lua owns" in markdown
    assert "EquipmentRuntimeGateStaticSmoke" in markdown
    assert "`equipment_runtime_gate` | `operational_acceptance_complete`" in markdown
    assert "p12-equipment-bdf7027cf48c438d" in markdown
    assert "`heal_friend_runtime_gate`" in markdown
    assert "ctoa_helper_heal_friend_runtime_gate.lua owns" in markdown
    assert "HealFriendRuntimeGateStaticSmoke" in markdown
    assert "closed_blocked_no_compatible_vocation" in markdown
    assert "p12_heal_friend_no_compatible_vocation_closure.json" in markdown
    assert "`scripting_policy`" in markdown
    assert "ctoa_helper_scripting.lua owns policy snapshots" in markdown
    assert "ScriptingPolicySmoke" in markdown
    assert "`operator_summary_bridge`" in markdown
    assert (
        "ctoa_helper_operator_summary.lua owns title/domain/profile/UI summary composition"
        in markdown
    )
    assert "OperatorSummaryStaticSmoke" in markdown
    assert "`input_contracts`" in markdown
    assert "ctoa_helper_hotkeys.lua owns passive binding decisions" in markdown
    assert "InputContractsStaticSmoke" in markdown
    assert (
        "`combat_runtime` / Combat runtime planner split | `deferred_high_risk_refactor_only`"
        in markdown
    )
    assert (
        "`cavebot_runtime` / Cavebot runtime planner split | `deferred_high_risk_refactor_only`"
        in markdown
    )
    assert "Raw shell-budget signals (refactor-only)" in markdown
    assert "active target advancement" in markdown
    assert "movement blocked-reason/status/trace/path result text" in markdown
    assert "movement API probe summary text" in markdown
    assert "`loot_runtime` / Loot runtime planner split | `static_gated`" in markdown
    assert "`timer_runtime` / Timer runtime planner split | `static_gated`" in markdown
    assert (
        "`profile_schema` / Profile schema, persistence policy, rotation metadata, and migration metadata | `static_gated`"
        in markdown
    )
    assert "## Supplemental Execution Plan" in markdown
    assert "`ui_primitives` | `in_progress_static_gated`" in markdown
    assert "ctoa_helper_ui.lua owns text fit" in markdown
    assert "`target_scorer` | `in_progress_static_gated`" in markdown
    assert "Targeting owns bestCandidate ranking" in markdown
    assert "`profile_persistence` | `in_progress_static_gated`" in markdown
    assert (
        "ctoa_helper_profile_persistence.lua now owns passive load candidates"
        in markdown
    )
    assert "`runtime_bridge_review` | `p13_ready_to_start`" in markdown
    assert "ROADMAP_STATE.json" in markdown
    assert "Conditions -> Equipment -> Heal Friend" in markdown
    assert "`ctoa_helper_hud.lua`" in markdown
    assert "`ctoa_helper_route.lua`" in markdown
    assert "`docs/otclient/vbot_import_review.md`" in markdown
    assert "PromoteLiveCtoa" in markdown


def test_next_modules_plan_writes_atomic_json_and_markdown(tmp_path: Path):
    json_out = tmp_path / "next_modules_plan.json"
    plan_out = tmp_path / "next_modules_plan.md"

    payload = plan.build_payload()
    plan.write_text_atomic(json_out, json.dumps(payload, indent=2))
    plan.write_text_atomic(plan_out, plan.render_markdown(payload))

    saved = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = plan_out.read_text(encoding="utf-8")

    assert saved["candidate_modules"][0]["module_id"] == "ui_primitives"
    assert saved["candidate_modules"][0]["status"] == "static_gated"
    assert saved["candidate_modules"][1]["module_id"] == "hud"
    assert saved["candidate_modules"][1]["status"] == "static_gated"
    assert saved["candidate_modules"][2]["module_id"] == "hotkeys"
    assert saved["candidate_modules"][2]["status"] == "static_gated"
    assert saved["candidate_modules"][3]["module_id"] == "modal_confirm"
    assert saved["candidate_modules"][3]["status"] == "static_gated"
    assert saved["candidate_modules"][4]["module_id"] == "route_engine"
    assert saved["candidate_modules"][4]["status"] == "static_gated"
    assert saved["candidate_modules"][5]["module_id"] == "target_scorer"
    assert saved["candidate_modules"][5]["status"] == "static_gated"
    assert saved["candidate_modules"][6]["module_id"] == "combat_runtime"
    assert saved["candidate_modules"][6]["status"] == "deferred_high_risk_refactor_only"
    assert saved["candidate_modules"][7]["module_id"] == "cavebot_runtime"
    assert saved["candidate_modules"][7]["status"] == "deferred_high_risk_refactor_only"
    assert saved["candidate_modules"][8]["module_id"] == "loot_runtime"
    assert saved["candidate_modules"][8]["status"] == "static_gated"
    assert saved["candidate_modules"][9]["module_id"] == "timer_runtime"
    assert saved["candidate_modules"][9]["status"] == "static_gated"
    assert saved["candidate_modules"][10]["module_id"] == "profile_schema"
    assert saved["candidate_modules"][10]["status"] == "static_gated"
    assert saved["candidate_modules"][-1]["module_id"] == "vbot_import"
    assert saved["supplemental_execution"][0]["workstream"] == "ui_primitives"
    assert saved["supplemental_execution"][0]["status"] == "in_progress_static_gated"
    assert saved["supplemental_execution"][1]["workstream"] == "target_scorer"
    assert saved["supplemental_execution"][1]["status"] == "in_progress_static_gated"
    assert saved["supplemental_execution"][7]["workstream"] == "operator_summary_bridge"
    assert saved["supplemental_execution"][7]["status"] == "in_progress_static_gated"
    assert saved["supplemental_execution"][8]["workstream"] == "input_contracts"
    assert saved["supplemental_execution"][8]["status"] == "in_progress_static_gated"
    assert (
        "otclient_input_contract_fixtures.py"
        in saved["supplemental_execution"][8]["current_slice"]
    )
    assert "import_gate" in saved["candidate_modules"][-1]["first_slice"]
    assert "runtime_gate_mapping" in saved["candidate_modules"][-1]["gate"]
    assert "Operator Sequence" in markdown
    assert "Supplemental Execution Plan" in markdown
    assert "Promote a module from `contracted` to `static_gated`" in markdown
    assert "ctoa_helper_module_status.lua" in markdown
    assert "ctoa_helper_action_catalog.lua" in markdown
    assert "ctoa_helper_decision_trace.lua" in markdown
    assert "ctoa_helper_sandbox_handoff.lua" in markdown
    assert "ctoa_helper_feature_flags.lua" in markdown
    assert list(tmp_path.glob(".*.tmp")) == []
