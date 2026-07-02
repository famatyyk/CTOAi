from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_event_logger_contract():
    text = _read("scripts/lua/event_logger.lua")
    assert "function EventLogger.build" in text
    assert "function EventLogger.log" in text
    assert "function EventLogger.toJsonLine" in text
    assert "includePosition" in text


def test_pathing_helper_contract():
    text = _read("scripts/lua/pathing_helper.lua")
    assert "function PathingHelper.normalizeRoute" in text
    assert "function PathingHelper.nextWaypoint" in text
    assert "function PathingHelper.retryBlocked" in text
    assert "defaultMaxRetries" in text


def test_auto_heal_contract():
    text = _read("scripts/lua/auto_heal.lua")
    assert "function AutoHeal.shouldCast" in text
    assert "function AutoHeal.nextAction" in text
    assert "criticalHpThreshold" in text
    assert "cooldownSeconds" in text
