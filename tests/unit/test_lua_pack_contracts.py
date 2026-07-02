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


def test_supply_manager_contract():
    text = _read("scripts/lua/supply_manager.lua")
    assert "function SupplyManager.checkSupplies" in text
    assert "function SupplyManager.shouldRefill" in text
    assert "function SupplyManager.nextAction" in text
    assert "defaultReserve" in text


def test_target_priority_contract():
    text = _read("scripts/lua/target_priority.lua")
    assert "function TargetPriority.score" in text
    assert "function TargetPriority.pick" in text
    assert "function TargetPriority.normalize" in text
    assert "engaged" in text


def test_loot_filter_contract():
    text = _read("scripts/lua/loot_filter.lua")
    assert "function LootFilter.filter" in text
    assert "function LootFilter.shouldStack" in text
    assert "function LootFilter.shouldLoot" in text
    assert "function LootFilter.classify" in text
