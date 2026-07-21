#!/usr/bin/env python3
"""Produce one passive P11 observation for the approved exact sandbox target."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_capture_profile_apply as local_reader
    from . import otclient_equipment_observation_preview as writer
    from . import otclient_heal_friend_candidate_catalog as catalog
    from . import otclient_heal_friend_profile_change_plan as profile_plan
    from . import otclient_heal_friend_shadow_replay as replay
    from .otclient_headless_evidence import load_json_bounded, summarize_capability
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_capture_profile_apply as local_reader
    import otclient_equipment_observation_preview as writer
    import otclient_heal_friend_candidate_catalog as catalog
    import otclient_heal_friend_profile_change_plan as profile_plan
    import otclient_heal_friend_shadow_replay as replay
    from otclient_headless_evidence import load_json_bounded, summarize_capability


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / profile_plan.TARGET_RELPATH
OUTPUT = profile_plan.DEV_DIR / "heal_friend_observation.json"
MAX_BYTES = 256 * 1024


def build_observation(
    profile: documents.InputDocument,
    capability: dict[str, Any],
    *,
    capability_sha256: str,
    generated_at_unix_ms: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    profile_payload = profile.payload
    if profile.status != "loaded" or not replay._profile_valid(profile_payload):  # noqa: SLF001
        blockers.append("profile_missing_or_invalid")
        profile_payload = None
    if not (
        capability.get("fresh") is True
        and capability.get("contract_valid") is True
        and capability.get("version_match") is True
        and capability.get("heartbeat_after_process_start") is True
    ):
        blockers.append("capability_not_fresh_or_invalid")
    scan = capability.get("heal_friend_scan")
    if (
        not isinstance(scan, dict)
        or scan.get("status") != "valid"
        or scan.get("valid") is not True
    ):
        blockers.append("heal_friend_scan_invalid")
        scan = {}
    target = None
    if isinstance(profile_payload, dict):
        expected = profile_payload["whitelist"][0]
        matches = [
            item
            for item in scan.get("candidates", [])
            if isinstance(item, dict)
            and item.get("target_id") == expected["target_id"]
            and item.get("target_name") == expected["target_name"]
        ]
        if len(matches) == 1:
            target = matches[0]
        else:
            blockers.append("exact_target_missing_or_ambiguous")
    if target is not None and not (
        target.get("target_is_player") is True
        and target.get("target_is_self") is False
        and target.get("target_party_member") is True
        and target.get("target_visible") is True
        and target.get("target_same_floor") is True
    ):
        blockers.append("exact_target_guard_failed")
    if blockers:
        return {
            "schema_version": "ctoa.heal-friend-observation-producer.v1",
            "generated_at_unix_ms": generated_at_unix_ms,
            "status": "blocked",
            "profile_sha256": profile.sha256,
            "capability_sha256": capability_sha256,
            "observation": None,
            "blockers": blockers,
            **{field: False for field in replay.FALSE_FLAGS},
            "intrusive_actions_performed": [],
        }
    assert isinstance(profile_payload, dict) and isinstance(target, dict)
    observed_at = scan["observed_at_unix_ms"]
    party_ids = sorted(
        {
            item["target_id"]
            for item in scan["candidates"]
            if isinstance(item, dict)
            and item.get("target_party_member") is True
            and isinstance(item.get("target_id"), int)
            and item["target_id"] > 0
        }
    )
    observation = {
        "schema_version": replay.OBSERVATION_SCHEMA,
        "observation_id": f"heal-friend-{observed_at}",
        "observed_at_unix_ms": observed_at,
        "party_observed_at_unix_ms": scan["party_observed_at_unix_ms"],
        "producer_source": "otclient_guarded_adapter",
        "online": scan["online"],
        "alive": scan["alive"],
        "protection_zone": scan["protection_zone"],
        "protection_zone_source": scan["protection_zone_source"],
        "self_id": scan["self_id"],
        "target_id": target["target_id"],
        "observed_target_id": target["target_id"],
        "current_target_id": target["target_id"],
        "target_name": target["target_name"],
        "observed_target_name": target["target_name"],
        "current_target_name": target["target_name"],
        "whitelist_revision": profile_payload["whitelist_revision"],
        "party_member_ids": party_ids,
        "target_is_player": target["target_is_player"],
        "target_is_self": target["target_is_self"],
        "target_visible": target["target_visible"],
        "target_same_floor": target["target_same_floor"],
        "distance": target["distance"],
        "observed_target_hp_percent": target["hp_percent"],
        "current_target_hp_percent": target["hp_percent"],
        "cooldown": scan["cooldown"],
        "cooldown_source": scan["cooldown_source"],
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    valid = replay._observation_valid(observation)  # noqa: SLF001
    return {
        "schema_version": "ctoa.heal-friend-observation-producer.v1",
        "generated_at_unix_ms": generated_at_unix_ms,
        "status": "observation_ready" if valid else "blocked",
        "profile_sha256": profile.sha256,
        "capability_sha256": capability_sha256,
        "observation_sha256": documents.canonical_sha256(observation),
        "observation": observation,
        "blockers": [] if valid else ["observation_contract_invalid"],
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-start-unix-ms", required=True, type=int)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    now = int(time.time() * 1000)
    capability_path = catalog.sandbox_capability_path()
    raw, load_status = load_json_bounded(capability_path)
    capability = summarize_capability(
        raw,
        load_status,
        now,
        process_start_unix_ms=args.process_start_unix_ms,
        expected_helper_version=catalog.EXPECTED_HELPER_VERSION,
    )
    capability_sha = (
        documents.canonical_sha256(raw)
        if isinstance(raw, dict)
        else documents.ZERO_SHA256
    )
    report = build_observation(
        local_reader._strict_local_document(PROFILE),  # noqa: SLF001
        capability,
        capability_sha256=capability_sha,
        generated_at_unix_ms=now,
    )
    writer._write_atomic(OUTPUT, OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "observation_ready" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
