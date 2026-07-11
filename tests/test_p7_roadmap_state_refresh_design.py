from pathlib import Path

from scripts.ops.engine_brain_pack import PROFILE_FILES


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "P7_ROADMAP_STATE_REFRESH_DESIGN.md"
RISK_MODEL = ROOT / "docs" / "CTOAI_COMMAND_RISK_MODEL.md"
ROADMAP = ROOT / "AI" / "FEATURE_ROADMAP.md"


def test_next_p7_action_has_complete_design_but_is_not_enabled():
    design = DESIGN.read_text(encoding="utf-8")
    risk = RISK_MODEL.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for marker in [
        "roadmap-state-refresh",
        "ctoai_roadmap_state_refresh",
        "design_only",
        "safe_write",
        "dry_run=true",
        "refresh roadmap state",
        "runtime/control-center/action-audit.jsonl",
        "ctoai_control_center_cockpit",
        "active safe-write tool count remains five",
    ]:
        assert marker in design
    assert "Roadmap state refresh" in risk and "design_only" in risk
    assert "**Roadmap state refresh**" in roadmap
    assert "active safe-write tool count stays five" in roadmap
    assert "docs/P7_ROADMAP_STATE_REFRESH_DESIGN.md" in PROFILE_FILES["all"]
    assert "docs/P7_ROADMAP_STATE_REFRESH_DESIGN.md" in PROFILE_FILES["control-center"]
