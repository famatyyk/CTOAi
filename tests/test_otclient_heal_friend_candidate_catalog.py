from __future__ import annotations

import json

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_candidate_catalog as catalog


NOW_MS = 1_784_090_500_000


def _background() -> dict:
    candidate = {
        "target_id": 424242, "target_name": "fixture ally", "hp_percent": 42,
        "distance": 3, "target_is_player": True, "target_is_self": False,
        "target_party_member": True, "target_visible": True, "target_same_floor": True,
    }
    scan = {
        "status": "valid", "valid": True, "observed_at_unix_ms": NOW_MS - 1_000,
        "scan_complete": True, "producer_source": "otclient_guarded_adapter",
        "candidates": [candidate],
        **{field: False for field in catalog.FALSE_FLAGS},
    }
    return {
        "status": "ready",
        "capability": {"fresh": True, "contract_valid": True, "version_match": True, "heal_friend_scan": scan},
    }


def test_catalog_lists_without_selecting_or_recommending():
    report = catalog.build_catalog(documents.document_from_payload(_background()), NOW_MS)
    assert report["status"] == "catalog_ready"
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["target_id"] == 424242
    assert report["selection_policy"] == "none"
    assert report["recommendation"] is None
    assert all(report[field] is False for field in catalog.FALSE_FLAGS)


def test_catalog_fails_closed_for_stale_incomplete_or_unsafe_scan():
    cases = []
    stale = _background()
    stale["capability"]["heal_friend_scan"]["observed_at_unix_ms"] = NOW_MS - catalog.MAX_AGE_MS - 1
    cases.append(stale)
    incomplete = _background()
    incomplete["capability"]["heal_friend_scan"]["scan_complete"] = False
    cases.append(incomplete)
    unsafe = _background()
    unsafe["capability"]["heal_friend_scan"]["talks"] = True
    cases.append(unsafe)
    for payload in cases:
        report = catalog.build_catalog(documents.document_from_payload(payload), NOW_MS)
        assert report["status"] == "blocked"
        assert report["recommendation"] is None


def test_sandbox_catalog_uses_shared_capability_sanitizer(tmp_path):
    candidate = _background()["capability"]["heal_friend_scan"]["candidates"][0]
    scan = {
        "schema_version": "ctoa.heal-friend-scan.v1",
        "observed_at_unix_ms": NOW_MS - 1_000,
        "party_observed_at_unix_ms": NOW_MS - 1_000,
        "observation_id": "heal-friend-test",
        "online": "online",
        "alive": "alive",
        "protection_zone": "outside",
        "protection_zone_source": "player_states",
        "self_id": 100,
        "scan_complete": True,
        "candidates": [candidate],
        "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
        "producer_source": "otclient_guarded_adapter",
        **{field: False for field in catalog.FALSE_FLAGS},
    }
    payload = {
        "schema_version": "ctoa-client-capabilities-v1",
        "observed_at_unix_ms": NOW_MS - 1_000,
        "heartbeat_interval_ms": 5_000,
        "heartbeat_status": "online",
        "online": True,
        "helper_version": catalog.EXPECTED_HELPER_VERSION,
        "runtime_actions": False,
        "runtime_core": {"runtime_actions": False},
        "heal_friend_scan": scan,
    }
    path = tmp_path / "ctoa_client_capabilities.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = catalog.build_sandbox_catalog(
        path,
        now_unix_ms=NOW_MS,
        process_start_unix_ms=NOW_MS - 20_000,
    )

    assert report["status"] == "catalog_ready"
    assert report["source"] == "sandbox_capability"
    assert report["capability_status"] == "fresh"
    assert report["heartbeat_after_process_start"] is True
    assert report["candidate_count"] == 1
    assert report["recommendation"] is None


def test_sandbox_capability_path_is_fixed_to_codex_test_root():
    path = catalog.sandbox_capability_path(r"C:\Users\operator\AppData\Local")
    assert path.parts[-5:] == (
        "SolteriaCodexTest",
        "client",
        "mods",
        "ctoa_otclient",
        "ctoa_client_capabilities.json",
    )
