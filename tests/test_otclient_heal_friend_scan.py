from __future__ import annotations

import copy

from scripts.ops import otclient_headless_evidence as evidence


NOW_MS = 1_784_090_500_000


def _scan() -> dict:
    return {
        "schema_version": evidence.HEAL_FRIEND_SCAN_SCHEMA,
        "observed_at_unix_ms": NOW_MS,
        "party_observed_at_unix_ms": NOW_MS,
        "observation_id": f"heal-friend-{NOW_MS}",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_states",
        "self_id": 111,
        "scan_complete": True,
        "candidates": [
            {
                "target_id": 424242,
                "target_name": "fixture ally",
                "hp_percent": 42,
                "distance": 3,
                "target_is_player": True,
                "target_is_self": False,
                "target_party_member": True,
                "target_visible": True,
                "target_same_floor": True,
            }
        ],
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
        "dispatch_allowed": False,
        "runtime_actions": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "casts": False,
        "talks": False,
    }


def test_heal_friend_scan_is_strictly_normalized_without_selecting_a_target():
    result = evidence.summarize_heal_friend_scan(
        _scan(), expected_observed_at_unix_ms=NOW_MS, require_timestamp_binding=True
    )
    assert result["status"] == "valid"
    assert result["p11_blocker"] is None
    assert result["candidates"][0]["target_id"] == 424242
    assert all(result[field] is False for field in evidence.HEAL_FRIEND_SCAN_ACTION_FLAGS)


def test_heal_friend_scan_rejects_extra_unsafe_and_noncanonical_data():
    mutations = []
    extra = _scan()
    extra["secret"] = "C:/private"
    mutations.append(extra)
    unsafe = _scan()
    unsafe["casts"] = True
    mutations.append(unsafe)
    name = _scan()
    name["candidates"][0]["target_name"] = " Fixture  Ally "
    mutations.append(name)
    timestamp = _scan()
    timestamp["party_observed_at_unix_ms"] -= 1
    mutations.append(timestamp)
    for payload in mutations:
        result = evidence.summarize_heal_friend_scan(
            payload, expected_observed_at_unix_ms=NOW_MS, require_timestamp_binding=True
        )
        assert result["status"] == "invalid"
        assert result["candidates"] == []
        assert result["p11_blocker"] == "heal_friend_scan_invalid"


def test_capability_marks_nested_heal_friend_action_claim_unsafe():
    payload = {
        "schema_version": evidence.CAPABILITY_SCHEMA,
        "observed_at_unix_ms": NOW_MS,
        "heartbeat_interval_ms": evidence.EXPECTED_HEARTBEAT_INTERVAL_MS,
        "heartbeat_status": "online",
        "online": True,
        "helper_version": "2.4.1",
        "runtime_actions": False,
        "runtime_core": {"runtime_actions": False},
        "heal_friend_scan": _scan(),
    }
    safe = evidence.summarize_capability(
        payload,
        "loaded",
        NOW_MS + 1_000,
        process_start_unix_ms=NOW_MS - 1_000,
        expected_helper_version="2.4.1",
    )
    assert safe["contract_valid"] is True
    assert safe["heal_friend_scan"]["status"] == "valid"

    poisoned = copy.deepcopy(payload)
    poisoned["heal_friend_scan"]["talks"] = True
    blocked = evidence.summarize_capability(
        poisoned,
        "loaded",
        NOW_MS + 1_000,
        process_start_unix_ms=NOW_MS - 1_000,
        expected_helper_version="2.4.1",
    )
    assert blocked["status"] == "unsafe_runtime_claim"
    assert blocked["contract_valid"] is False
