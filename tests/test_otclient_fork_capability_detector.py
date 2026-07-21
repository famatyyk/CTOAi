from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_fork_capability_detector.py"
SPEC = importlib.util.spec_from_file_location("fork_detector", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_detects_redemption_from_bounded_primary_markers(tmp_path: Path) -> None:
    (tmp_path / "src/framework").mkdir(parents=True)
    (tmp_path / "modules/corelib").mkdir(parents=True)
    (tmp_path / "modules/game_interface/widgets").mkdir(parents=True)
    (tmp_path / "modules/game_actionbar").mkdir(parents=True)
    (tmp_path / "init.lua").write_text('g_app.setName("OTClient - Redemption")', encoding="utf-8")
    (tmp_path / "src/framework/config.h").write_text(
        '#define STATE_RPC_TEXT "github.com/mehah/otclient"', encoding="utf-8"
    )
    (tmp_path / "modules/corelib/keybind.lua").write_text("", encoding="utf-8")
    (tmp_path / "modules/game_interface/widgets/uiitem.lua").write_text("", encoding="utf-8")

    report = MODULE.detect(tmp_path)
    assert report["status"] == "detected"
    assert report["adapter"] == "redemption-mehah"
    assert report["read_only"] is True
    assert report["credentials_read"] is False
    assert report["connection_attempted"] is False
    assert report["capabilities"]["keybind_api"] is True
    assert report["capabilities"]["ui_item"] is True
    assert report["capabilities"]["action_bar"] is True


def test_otcv8_specific_module_outweighs_base_copyright(tmp_path: Path) -> None:
    (tmp_path / "modules/game_bot").mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        "OTCv8 derived from https://github.com/edubart/otclient", encoding="utf-8"
    )
    report = MODULE.detect(tmp_path)
    assert report["status"] == "detected"
    assert report["adapter"] == "otcv8"
    assert report["candidates"][0]["score"] > report["candidates"][1]["score"]


def test_unknown_tree_fails_closed_without_guessing(tmp_path: Path) -> None:
    (tmp_path / "init.lua").write_text("g_app.setName('Custom Client')", encoding="utf-8")
    report = MODULE.detect(tmp_path)
    assert report["status"] == "unknown"
    assert report["adapter"] is None
    assert report["confidence"] == 0


def test_detector_never_reads_profile_or_environment_secret_files(tmp_path: Path) -> None:
    (tmp_path / "init.lua").write_text("OTClient - Redemption", encoding="utf-8")
    (tmp_path / ".env").write_text("OTS_PASSWORD=do-not-read", encoding="utf-8")
    (tmp_path / "settings").mkdir()
    (tmp_path / "settings/clientoptions.json").write_text(
        '{"password":"do-not-read"}', encoding="utf-8"
    )
    report = MODULE.detect(tmp_path)
    assert ".env" not in report["inspected_marker_files"]
    assert "settings/clientoptions.json" not in report["inspected_marker_files"]
    assert report["credentials_read"] is False
