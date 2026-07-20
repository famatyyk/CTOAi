from __future__ import annotations

import json

from scripts.ops.engine_brain_index import DEFAULT_OUT_DIR, build_indexes
from scripts.ops.engine_brain_pack import build_pack


def test_engine_brain_pack_writes_manifest_and_markdown(tmp_path):
    build_indexes(DEFAULT_OUT_DIR)
    pack_path = tmp_path / "pack.md"
    manifest_path = tmp_path / "pack.json"

    manifest = build_pack(
        pack_path, manifest_path, include_generated=False, max_chars_per_file=4000
    )

    assert pack_path.exists()
    assert manifest_path.exists()
    assert manifest["included_count"] > 5

    text = pack_path.read_text(encoding="utf-8")
    assert "CTOAi Engine Brain Pack" in text
    assert "AI/SYSTEM_PROMPT.md" in text
    assert "AI/generated/OWNERSHIP_MAP.md" in text
    assert "AI/generated/DOC_SYNC.md" in text
    assert "AI/generated/SECRET_GUARDRAIL.md" in text
    assert "AI/generated/P6_CODEX_INTEGRATION_READINESS.md" in text
    assert "AI/generated/P7_OPERATOR_WORKFLOW.md" in text
    assert "AI/generated/P7_ACTION_READINESS.md" in text
    assert "AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md" in text
    assert "AI/generated/P7_OPERATOR_BRIEF.md" in text
    assert "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md" in text
    assert "AI/P8_P16_EXECUTION_ROADMAP.md" in text
    assert "AI/P17_P24_HELPER_EVOLUTION_ROADMAP.md" in text
    assert "AI/P17_P24_HELPER_EVOLUTION_ROADMAP.json" in text
    assert "docs/otclient/HELPER_SIMPLIFICATION_AUDIT_2026-07-16.md" in text
    assert "scripts/lua/otclient/ctoa_helper_rule_engine.lua" in text
    assert "docs/otclient/P9_CONDITIONS_SHADOW_REPLAY_DESIGN.md" in text
    assert "docs/otclient/P9_CONDITIONS_SHADOW_ACCEPTANCE.md" in text
    assert "docs/otclient/P10_EQUIPMENT_SHADOW_REPLAY_DESIGN.md" in text
    assert "docs/otclient/P11_HEAL_FRIEND_SHADOW_REPLAY_DESIGN.md" in text
    assert "docs/otclient/P14_INDEPENDENT_RUNNER_CONTRACT.md" in text
    assert "docs/otclient/HELPER_RUNTIME_MODULE_GATES_V1.md" in text
    assert "Conditions -> Equipment -> Heal Friend" in text
    assert "deferred_high_risk" in text
    assert ".env*" in text
    assert "## `AI/generated/SYMBOL_MAP.md`" not in text
    assert "CTOA_LOCAL_MODEL_URL=" not in text

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == 1
    assert saved["include_generated"] is False


def test_engine_brain_pack_can_include_generated_sections(tmp_path):
    pack_path = tmp_path / "pack.md"
    manifest_path = tmp_path / "pack.json"

    manifest = build_pack(
        pack_path, manifest_path, include_generated=True, max_chars_per_file=1200
    )

    assert manifest["truncated_count"] >= 1
    roadmap_section = next(
        section
        for section in manifest["sections"]
        if section["path"]
        == "docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md"
    )
    assert roadmap_section["critical_markers"] == ["deferred_high_risk"]
    text = pack_path.read_text(encoding="utf-8")
    assert "AI/generated/FILE_TREE.md" in text


def test_engine_brain_pack_supports_helper_profile(tmp_path):
    build_indexes(DEFAULT_OUT_DIR)
    pack_path = tmp_path / "helper-pack.md"
    manifest_path = tmp_path / "helper-pack.json"

    manifest = build_pack(
        pack_path,
        manifest_path,
        profile="helper",
        include_generated=False,
        max_chars_per_file=4000,
    )
    assert any(
        section["path"] == "docs/otclient/HELPER_RUNTIME_BRIDGE_V1.md"
        for section in manifest["sections"]
    )
    assert any(
        section["path"] == "docs/otclient/HELPER_RUNTIME_MODULE_GATES_V1.md"
        for section in manifest["sections"]
    )

    assert manifest["profile"] == "helper"
    text = pack_path.read_text(encoding="utf-8")
    assert "Profile: `helper`" in text
    assert "AI/OTCLIENT_INDEX.md" in text
    assert "AI/P8_P16_EXECUTION_ROADMAP.md" in text
    assert "AI/P17_P24_HELPER_EVOLUTION_ROADMAP.md" in text
    assert "AI/P17_P24_HELPER_EVOLUTION_ROADMAP.json" in text
    assert "docs/otclient/HELPER_SIMPLIFICATION_AUDIT_2026-07-16.md" in text
    assert "scripts/lua/otclient/ctoa_helper_rule_engine.lua" in text
    assert "docs/otclient/P9_CONDITIONS_SHADOW_REPLAY_DESIGN.md" in text
    assert "docs/otclient/P9_CONDITIONS_SHADOW_ACCEPTANCE.md" in text
    assert "docs/otclient/P10_EQUIPMENT_SHADOW_REPLAY_DESIGN.md" in text
    assert "docs/otclient/P11_HEAL_FRIEND_SHADOW_REPLAY_DESIGN.md" in text
    assert "docs/otclient/solteria_helper_test_env.md" in text
    assert "docs/otclient/HELPER_RUNTIME_MODULE_GATES_V1.md" in text
    assert "docs/otclient/solteria_helper_module_workplan.md" in text
    assert "docs/otclient/solteria_helper_next_modules_plan.md" in text
    assert "docs/otclient/ctoai_runtime_2_execution_plan.md" in text
    assert "docs/otclient/solteria_helper_sandbox_smoke_queue.md" in text
    assert "docs/otclient/zerobot_reference.md" in text
    assert "docs/otclient/vbot_import_review.md" in text
    assert "scripts/ops/otclient_external_bot_intake.py" in text
    assert "scripts/ops/solteria_helper_sandbox_smoke_queue.py" in text
    assert "source_required" in text
    assert "AI/generated/SECRET_GUARDRAIL.md" in text
    assert "AI/generated/P6_CODEX_INTEGRATION_READINESS.md" in text
    assert "AI/generated/P7_OPERATOR_WORKFLOW.md" in text
    assert "AI/generated/P7_ACTION_READINESS.md" in text
    assert "AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md" in text
    assert "AI/generated/P7_OPERATOR_BRIEF.md" in text
    assert "AI/API_INDEX.md" not in text


def test_engine_brain_pack_supports_compact_control_central_profile(tmp_path):
    build_indexes(DEFAULT_OUT_DIR)
    compact_path = tmp_path / "control-central-pack.md"
    compact_manifest_path = tmp_path / "control-central-pack.json"
    full_path = tmp_path / "control-center-pack.md"
    full_manifest_path = tmp_path / "control-center-pack.json"

    compact = build_pack(
        compact_path,
        compact_manifest_path,
        profile="control-central",
        include_generated=True,
        max_chars_per_file=45000,
    )
    full = build_pack(
        full_path,
        full_manifest_path,
        profile="control-center",
        include_generated=True,
        max_chars_per_file=45000,
    )

    text = compact_path.read_text(encoding="utf-8")
    assert compact["profile"] == "control-central"
    assert compact["included_count"] == 10
    assert compact["truncated_count"] == 0
    assert "Profile: `control-central`" in text
    assert "AI/generated/manifest.json" in text
    assert "AI/generated/P7_OPERATOR_BRIEF.md" in text
    included_paths = {section["path"] for section in compact["sections"]}
    assert "AI/generated/FILE_TREE.md" not in included_paths
    assert "AI/generated/SYMBOL_MAP.md" not in included_paths
    assert "AI/ENGINE_BRAIN_STATUS.md" not in text
    assert compact["included_count"] < full["included_count"]
    assert compact_path.stat().st_size < full_path.stat().st_size * 0.25
