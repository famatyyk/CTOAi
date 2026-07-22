from pathlib import Path

from scripts.ops.engine_brain_pack import PROFILE_FILES


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "P7_ROADMAP_STATE_REFRESH_DESIGN.md"
RISK_MODEL = ROOT / "docs" / "CTOAI_COMMAND_RISK_MODEL.md"
ROADMAP = ROOT / "AI" / "FEATURE_ROADMAP.md"


def test_p13_roadmap_refresh_is_registered_but_fail_closed():
    design = DESIGN.read_text(encoding="utf-8")
    risk = RISK_MODEL.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")

    for marker in [
        "roadmap-state-refresh",
        "ctoai_roadmap_state_refresh",
        "registered_fail_closed",
        "safe_write",
        "dry_run=false",
        "refresh roadmap state",
        "runtime/control-center/action-audit.jsonl",
        "no runtime executor",
        "P8–P12/P14 evidence rebaseline",
    ]:
        assert marker in design
    assert "Registered native dry-run-first candidate" in risk
    assert "registered bounded" in roadmap
    assert "docs/P7_ROADMAP_STATE_REFRESH_DESIGN.md" in PROFILE_FILES["all"]
    assert "docs/P7_ROADMAP_STATE_REFRESH_DESIGN.md" in PROFILE_FILES["control-center"]
