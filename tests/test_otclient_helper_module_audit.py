import json
from pathlib import Path

from scripts.ops import otclient_helper_module_audit as audit


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"


def test_module_audit_tracks_remaining_function_modularization_pressure():
    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=None)

    assert result.name == "otclient-helper-module-audit"
    assert result.status == "ready"
    assert result.helper_line_count <= result.helper_line_budget
    assert result.helper_line_budget == 4500
    assert result.helper_function_budget == 130
    assert result.helper_budget_status == "within_budget"
    assert "UI composition" in result.helper_shell_target
    assert result.modularization_pressure == "medium"
    assert result.placeholder_count == 0
    assert result.implemented_count >= 4
    assert result.prototype_count >= 4
    assert result.registry_count == 9
    assert result.registry_missing == []
    assert result.next_extraction_id == ""
    assert result.next_supplemental_id == ""
    assert len(result.extraction_plan) == 6
    assert len(result.supplemental_refactor_plan) == 16
    assert result.next_phase == "Keep module gates current before adding new runtime actions."
    assert result.next_module_id == "conditions"
    assert "ConditionsRuntimeGate" in result.next_module_action


def test_module_audit_maps_runtime_and_placeholder_lanes():
    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=None)
    modules = {item.id: item for item in result.modules}

    for module_id in ["healing", "combat", "cavebot", "loot", "timer"]:
        assert modules[module_id].status in {"implemented", "prototype"}
        assert modules[module_id].gate
        assert modules[module_id].next_step

    assert modules["cavebot"].target_file == "ctoa_native_helper.lua"
    assert modules["heal_friend"].status == "prototype"
    assert modules["heal_friend"].target_file == "ctoa_helper_heal_friend.lua"
    assert "HealFriendRuntimeGate" in modules["heal_friend"].gate
    assert "Conditions/Equipment" in modules["heal_friend"].gate
    assert "Combat/CaveBot disabled" in modules["heal_friend"].gate
    assert modules["conditions"].status == "prototype"
    assert modules["conditions"].target_file == "ctoa_helper_conditions.lua"
    assert "ConditionsRuntimeGate" in modules["conditions"].gate
    assert "Recovery acceptance" in modules["conditions"].gate
    assert "ConditionsRuntimeGate" in modules["conditions"].next_step
    assert modules["equipment"].status == "prototype"
    assert modules["equipment"].target_file == "ctoa_helper_equipment.lua"
    assert "EquipmentRuntimeGate" in modules["equipment"].gate
    assert "rollback snapshot" in modules["equipment"].gate
    assert "EquipmentRuntimeGate" in modules["equipment"].next_step
    assert modules["scripting"].status == "prototype"
    assert modules["scripting"].target_file == "ctoa_helper_scripting.lua"
    assert "No user snippet execution" in modules["scripting"].gate
    assert "ScriptingPolicySmoke" in modules["scripting"].gate
    assert "SmokeAttachModules" in modules["scripting"].next_step

    assert all(item.status != "placeholder" for item in result.modules)


def test_module_audit_defines_professional_extraction_map():
    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=None)
    plan = {item.id: item for item in result.extraction_plan}

    assert list(plan) == [
        "module_registry",
        "diagnostics",
        "conditions",
        "equipment",
        "heal_friend",
        "scripting",
    ]
    assert plan["module_registry"].target_file == "ctoa_helper_modules.lua"
    assert plan["module_registry"].safe_order == 1
    assert plan["module_registry"].status == "extracted"
    assert "Registry parity test" in plan["module_registry"].gate
    assert plan["diagnostics"].target_file == "ctoa_helper_diagnostics.lua"
    assert plan["diagnostics"].status == "extracted"
    assert "no secret/runtime path leakage" in plan["diagnostics"].gate
    assert plan["conditions"].status == "extracted"
    assert plan["conditions"].safe_order == 3
    assert plan["equipment"].status == "extracted"
    assert plan["equipment"].safe_order == 4
    assert plan["heal_friend"].target_file == "ctoa_helper_heal_friend.lua"
    assert plan["heal_friend"].status == "extracted"
    assert plan["heal_friend"].safe_order == 5
    assert "Conditions and Equipment" in plan["heal_friend"].gate
    assert plan["scripting"].status == "extracted"
    assert plan["scripting"].safe_order == 6
    assert "eval remains blocked" in plan["scripting"].gate


def test_module_audit_defines_supplemental_runtime_refactor_plan():
    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=None)
    plan = {item.id: item for item in result.supplemental_refactor_plan}

    assert list(plan) == [
        "combat_runtime_adapter",
        "cavebot_runtime_adapter",
        "loot_runtime_adapter",
        "timer_runtime_adapter",
        "profile_schema_adapter",
        "operator_summary_bridge",
        "planner_coordinator",
        "runtime_policy_guard",
        "dispatch_guard_coordinator",
        "plan_queue_coordinator",
        "runtime_readiness_status",
        "module_status_board",
        "action_catalog_policy",
        "decision_trace_review",
        "sandbox_handoff_checklist",
        "feature_flag_matrix",
    ]
    assert plan["combat_runtime_adapter"].target_file == "ctoa_helper_combat_runtime.lua"
    assert plan["combat_runtime_adapter"].status == "extracted"
    assert "Combat runtime static contract" in plan["combat_runtime_adapter"].gate
    assert "target scorer contract" in plan["combat_runtime_adapter"].gate
    assert "SmokeAttachAll hunting tabs" in plan["combat_runtime_adapter"].gate
    assert plan["cavebot_runtime_adapter"].target_file == "ctoa_helper_cavebot_runtime.lua"
    assert plan["cavebot_runtime_adapter"].status == "extracted"
    assert "Route contract" in plan["cavebot_runtime_adapter"].gate
    assert plan["loot_runtime_adapter"].target_file == "ctoa_helper_loot_runtime.lua"
    assert plan["loot_runtime_adapter"].status == "extracted"
    assert "experimental_loot remains false" in plan["loot_runtime_adapter"].gate
    assert plan["timer_runtime_adapter"].target_file == "ctoa_helper_timer_runtime.lua"
    assert plan["timer_runtime_adapter"].status == "extracted"
    assert "no-eval contract" in plan["timer_runtime_adapter"].gate
    assert plan["profile_schema_adapter"].target_file == "ctoa_helper_profile_schema.lua"
    assert plan["profile_schema_adapter"].status == "extracted"
    assert "no key-order churn" in plan["profile_schema_adapter"].gate
    assert plan["operator_summary_bridge"].target_file == "ctoa_helper_operator_summary.lua"
    assert plan["operator_summary_bridge"].status == "extracted"
    assert "OperatorSummary static contract" in plan["operator_summary_bridge"].gate
    assert "UI preview" in plan["operator_summary_bridge"].gate
    assert plan["planner_coordinator"].target_file == "ctoa_helper_planner.lua"
    assert plan["planner_coordinator"].status == "extracted"
    assert "Planner static contract" in plan["planner_coordinator"].gate
    assert "sandbox SmokeAttachModules" in plan["planner_coordinator"].gate
    assert plan["runtime_policy_guard"].target_file == "ctoa_helper_runtime_policy.lua"
    assert plan["runtime_policy_guard"].status == "extracted"
    assert "RuntimePolicy static contract" in plan["runtime_policy_guard"].gate
    assert "explicit live approval" in plan["runtime_policy_guard"].gate
    assert plan["dispatch_guard_coordinator"].target_file == "ctoa_helper_dispatch_guard.lua"
    assert plan["dispatch_guard_coordinator"].status == "extracted"
    assert "DispatchGuard static contract" in plan["dispatch_guard_coordinator"].gate
    assert "dispatcher bridge" in plan["dispatch_guard_coordinator"].gate
    assert plan["plan_queue_coordinator"].target_file == "ctoa_helper_plan_queue.lua"
    assert plan["plan_queue_coordinator"].status == "extracted"
    assert "PlanQueue static contract" in plan["plan_queue_coordinator"].gate
    assert "bounded queue tests" in plan["plan_queue_coordinator"].gate
    assert plan["runtime_readiness_status"].target_file == "ctoa_helper_runtime_readiness.lua"
    assert plan["runtime_readiness_status"].status == "extracted"
    assert "RuntimeReadiness static contract" in plan["runtime_readiness_status"].gate
    assert "required component/gate coverage" in plan["runtime_readiness_status"].gate
    assert plan["module_status_board"].target_file == "ctoa_helper_module_status.lua"
    assert plan["module_status_board"].status == "extracted"
    assert "ModuleStatus static contract" in plan["module_status_board"].gate
    assert "module contract coverage" in plan["module_status_board"].gate
    assert plan["action_catalog_policy"].target_file == "ctoa_helper_action_catalog.lua"
    assert plan["action_catalog_policy"].status == "extracted"
    assert "ActionCatalog static contract" in plan["action_catalog_policy"].gate
    assert "action risk coverage" in plan["action_catalog_policy"].gate
    assert plan["decision_trace_review"].target_file == "ctoa_helper_decision_trace.lua"
    assert plan["decision_trace_review"].status == "extracted"
    assert "DecisionTrace static contract" in plan["decision_trace_review"].gate
    assert "policy/guard reason coverage" in plan["decision_trace_review"].gate
    assert plan["sandbox_handoff_checklist"].target_file == "ctoa_helper_sandbox_handoff.lua"
    assert plan["sandbox_handoff_checklist"].status == "extracted"
    assert "SandboxHandoff static contract" in plan["sandbox_handoff_checklist"].gate
    assert "SmokeAttachAll" in plan["sandbox_handoff_checklist"].gate
    assert plan["feature_flag_matrix"].target_file == "ctoa_helper_feature_flags.lua"
    assert plan["feature_flag_matrix"].status == "extracted"
    assert "FeatureFlags static contract" in plan["feature_flag_matrix"].gate
    assert "safe-default coverage" in plan["feature_flag_matrix"].gate


def test_module_audit_writes_atomic_json_and_plan(tmp_path: Path):
    json_out = tmp_path / "module_audit.json"
    plan_out = tmp_path / "module_workplan.md"

    result = audit.build_audit(HELPER, OTCLIENT_DIR, plan_out, evidence_dir=None)
    audit.write_json_atomic(json_out, json.loads(json.dumps(result, default=lambda value: value.__dict__)))
    audit.write_text_atomic(plan_out, audit.render_markdown(result))

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    plan = plan_out.read_text(encoding="utf-8")

    assert payload["status"] == "ready"
    assert payload["next_module_id"] == "conditions"
    assert payload["next_extraction_id"] == ""
    assert payload["next_supplemental_id"] == ""
    assert payload["helper_budget_status"] == "within_budget"
    assert payload["extraction_plan"][0]["target_file"] == "ctoa_helper_modules.lua"
    assert payload["extraction_plan"][0]["status"] == "extracted"
    assert payload["extraction_plan"][1]["target_file"] == "ctoa_helper_diagnostics.lua"
    assert payload["extraction_plan"][1]["status"] == "extracted"
    assert payload["extraction_plan"][2]["target_file"] == "ctoa_helper_conditions.lua"
    assert payload["extraction_plan"][2]["status"] == "extracted"
    assert payload["extraction_plan"][3]["target_file"] == "ctoa_helper_equipment.lua"
    assert payload["extraction_plan"][3]["status"] == "extracted"
    assert payload["extraction_plan"][4]["target_file"] == "ctoa_helper_heal_friend.lua"
    assert payload["extraction_plan"][4]["status"] == "extracted"
    assert payload["extraction_plan"][5]["target_file"] == "ctoa_helper_scripting.lua"
    assert payload["extraction_plan"][5]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][0]["target_file"] == "ctoa_helper_combat_runtime.lua"
    assert payload["supplemental_refactor_plan"][0]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][1]["target_file"] == "ctoa_helper_cavebot_runtime.lua"
    assert payload["supplemental_refactor_plan"][1]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][2]["target_file"] == "ctoa_helper_loot_runtime.lua"
    assert payload["supplemental_refactor_plan"][2]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][3]["target_file"] == "ctoa_helper_timer_runtime.lua"
    assert payload["supplemental_refactor_plan"][3]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][4]["target_file"] == "ctoa_helper_profile_schema.lua"
    assert payload["supplemental_refactor_plan"][4]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][5]["target_file"] == "ctoa_helper_operator_summary.lua"
    assert payload["supplemental_refactor_plan"][5]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][6]["target_file"] == "ctoa_helper_planner.lua"
    assert payload["supplemental_refactor_plan"][6]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][7]["target_file"] == "ctoa_helper_runtime_policy.lua"
    assert payload["supplemental_refactor_plan"][7]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][8]["target_file"] == "ctoa_helper_dispatch_guard.lua"
    assert payload["supplemental_refactor_plan"][8]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][9]["target_file"] == "ctoa_helper_plan_queue.lua"
    assert payload["supplemental_refactor_plan"][9]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][10]["target_file"] == "ctoa_helper_runtime_readiness.lua"
    assert payload["supplemental_refactor_plan"][10]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][11]["target_file"] == "ctoa_helper_module_status.lua"
    assert payload["supplemental_refactor_plan"][11]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][12]["target_file"] == "ctoa_helper_action_catalog.lua"
    assert payload["supplemental_refactor_plan"][12]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][13]["target_file"] == "ctoa_helper_decision_trace.lua"
    assert payload["supplemental_refactor_plan"][13]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][14]["target_file"] == "ctoa_helper_sandbox_handoff.lua"
    assert payload["supplemental_refactor_plan"][14]["status"] == "extracted"
    assert payload["supplemental_refactor_plan"][15]["target_file"] == "ctoa_helper_feature_flags.lua"
    assert payload["supplemental_refactor_plan"][15]["status"] == "extracted"
    assert "# Solteria Helper Module Workplan" in plan
    assert "P6 Module Lane" in plan
    assert "Extraction Map" in plan
    assert "Supplemental Refactor Plan" in plan
    assert "Next module action" in plan
    assert "Next extraction" in plan
    assert "Next supplemental split" in plan
    assert "Helper budget status" in plan
    assert "Registry coverage" in plan
    assert "SmokeAttachModules" in plan
    assert "Overview must expose module readiness from `ctoa_helper_modules.lua`" in plan
    assert "PromoteLiveCtoa -ApproveLiveDeploy" in plan
    assert list(tmp_path.glob(".*.tmp")) == []


def test_module_workplan_markdown_lists_verification_commands():
    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=None)
    markdown = audit.render_markdown(result)

    assert "otclient_helper_module_audit.py" in markdown
    assert "test_otclient_helper_module_audit.py" in markdown
    assert "solteria_helper_test_env.ps1 -Action ValidateDev" in markdown
    assert "solteria_helper_test_env.ps1 -Action SmokePreflight" in markdown
    assert "solteria_helper_test_env.ps1 -Action ModuleStaticGates" in markdown
    assert "solteria_helper_test_env.ps1 -Action SmokeAttachModules" in markdown


def test_module_audit_promotes_only_fresh_static_gate_evidence(tmp_path: Path):
    evidence_dir = tmp_path / "solteria_helper_dev"
    preview_dir = tmp_path / "otclient_ui_preview"
    evidence_dir.mkdir()
    preview_dir.mkdir()
    for name, status in [
        ("heal_friend_no_target_smoke.json", "passed"),
        ("module_static_gates.json", "passed"),
        ("ready_check.json", "ready"),
    ]:
        (evidence_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")
    (preview_dir / "solteria-helper-attach-heal_friend-20260711-040616.png").write_bytes(b"png")

    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=evidence_dir)
    modules = {item.id: item for item in result.modules}

    assert modules["heal_friend"].status == "static_gated"
    assert modules["conditions"].status == "prototype"
    assert result.next_module_id == "conditions"
    assert "ConditionsRuntimeGate" in result.next_module_action


def test_module_audit_promotes_healing_after_fresh_vitals_and_tab_evidence(tmp_path: Path):
    evidence_dir = tmp_path / "solteria_helper_dev"
    preview_dir = tmp_path / "otclient_ui_preview"
    evidence_dir.mkdir()
    preview_dir.mkdir()
    for name, status in [
        ("healing_vitals_smoke.json", "passed"),
        ("module_static_gates.json", "passed"),
        ("ready_check.json", "ready"),
    ]:
        (evidence_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")
    (preview_dir / "solteria-helper-attach-healing-20260711-041846.png").write_bytes(b"png")

    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=evidence_dir)
    modules = {item.id: item for item in result.modules}

    assert modules["healing"].status == "static_gated"
    assert modules["combat"].status == "prototype"


def test_module_audit_promotes_combat_after_fresh_safety_and_magic_tab_evidence(tmp_path: Path):
    evidence_dir = tmp_path / "solteria_helper_dev"
    preview_dir = tmp_path / "otclient_ui_preview"
    evidence_dir.mkdir()
    preview_dir.mkdir()
    for name, status in [
        ("combat_safety_smoke.json", "passed"),
        ("module_static_gates.json", "passed"),
        ("ready_check.json", "ready"),
    ]:
        (evidence_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")
    (preview_dir / "solteria-helper-attach-hunting_magic-20260711-042144.png").write_bytes(b"png")

    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=evidence_dir)
    modules = {item.id: item for item in result.modules}

    assert modules["combat"].status == "static_gated"
    assert modules["cavebot"].status == "prototype"


def test_module_audit_promotes_cavebot_after_fresh_safety_and_tab_evidence(tmp_path: Path):
    evidence_dir = tmp_path / "solteria_helper_dev"
    preview_dir = tmp_path / "otclient_ui_preview"
    evidence_dir.mkdir()
    preview_dir.mkdir()
    for name, status in [
        ("cavebot_safety_smoke.json", "passed"),
        ("module_static_gates.json", "passed"),
        ("ready_check.json", "ready"),
    ]:
        (evidence_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")
    (preview_dir / "solteria-helper-attach-cavebot-20260711-042148.png").write_bytes(b"png")

    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=evidence_dir)
    modules = {item.id: item for item in result.modules}

    assert modules["cavebot"].status == "static_gated"
    assert modules["timer"].status == "prototype"


def test_module_audit_promotes_timer_after_fresh_passive_tick_and_tab_evidence(tmp_path: Path):
    evidence_dir = tmp_path / "solteria_helper_dev"
    preview_dir = tmp_path / "otclient_ui_preview"
    evidence_dir.mkdir()
    preview_dir.mkdir()
    for name, status in [
        ("timer_safety_smoke.json", "passed"),
        ("module_static_gates.json", "passed"),
        ("ready_check.json", "ready"),
    ]:
        (evidence_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")
    (preview_dir / "solteria-helper-attach-tools_timer-20260711-042202.png").write_bytes(b"png")

    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=evidence_dir)
    modules = {item.id: item for item in result.modules}

    assert modules["timer"].status == "static_gated"


def test_module_audit_promotes_loot_after_fresh_read_only_probe_and_diag_evidence(tmp_path: Path):
    evidence_dir = tmp_path / "solteria_helper_dev"
    preview_dir = tmp_path / "otclient_ui_preview"
    evidence_dir.mkdir()
    preview_dir.mkdir()
    for name, status in [
        ("loot_safety_smoke.json", "passed"),
        ("module_static_gates.json", "passed"),
        ("ready_check.json", "ready"),
    ]:
        (evidence_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")
    (preview_dir / "solteria-helper-attach-tools_diag-20260711-042205.png").write_bytes(b"png")

    result = audit.build_audit(HELPER, OTCLIENT_DIR, evidence_dir=evidence_dir)
    modules = {item.id: item for item in result.modules}

    assert modules["loot"].status == "static_gated"
