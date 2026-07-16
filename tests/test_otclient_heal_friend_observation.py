from __future__ import annotations

from scripts.ops import otclient_conditions_shadow_replay as documents
from scripts.ops import otclient_heal_friend_observation as producer
from scripts.ops import otclient_heal_friend_profile_change_plan as profile
from scripts.ops import otclient_heal_friend_shadow_replay as replay


NOW = 1_784_093_000_000


def _capability() -> dict:
    candidate = {
        "target_id": 268435471, "target_name": "amir to moja dziwka",
        "hp_percent": 42, "distance": 1, "target_is_player": True,
        "target_is_self": False, "target_party_member": True,
        "target_visible": True, "target_same_floor": True,
    }
    self_candidate = dict(candidate, target_id=268435472, target_name="el cvvel", target_is_self=True)
    scan = {
        "status": "valid", "valid": True, "observed_at_unix_ms": NOW - 1000,
        "party_observed_at_unix_ms": NOW - 1000, "online": "online",
        "alive": "alive", "protection_zone": "outside",
        "protection_zone_source": "player_states", "self_id": 268435472,
        "candidates": [candidate, self_candidate], "cooldown": "ready",
        "cooldown_source": "game_cooldown_group",
    }
    return {
        "fresh": True, "contract_valid": True, "version_match": True,
        "heartbeat_after_process_start": True, "heal_friend_scan": scan,
    }


def test_observation_uses_only_profile_exact_target():
    profile_doc = documents.document_from_payload(
        profile.build_profile(268435471, "amir to moja dziwka")
    )
    report = producer.build_observation(
        profile_doc, _capability(), capability_sha256="a" * 64,
        generated_at_unix_ms=NOW,
    )
    assert report["status"] == "observation_ready"
    observation = report["observation"]
    assert observation["target_id"] == 268435471
    assert observation["self_id"] == 268435472
    assert observation["party_member_ids"] == [268435471, 268435472]
    assert replay._observation_valid(observation) is True
    assert all(report[field] is False for field in replay.FALSE_FLAGS)


def test_observation_fails_closed_if_exact_target_is_not_party():
    capability = _capability()
    capability["heal_friend_scan"]["candidates"][0]["target_party_member"] = False
    report = producer.build_observation(
        documents.document_from_payload(profile.build_profile(268435471, "amir to moja dziwka")),
        capability, capability_sha256="a" * 64, generated_at_unix_ms=NOW,
    )
    assert report["status"] == "blocked"
    assert report["observation"] is None
    assert "exact_target_guard_failed" in report["blockers"]
