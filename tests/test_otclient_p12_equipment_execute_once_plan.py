from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.ops import otclient_p12_equipment_execute_once_plan as plan


def _write(path: Path, value: dict) -> str:
    raw = (json.dumps(value, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _fixture(tmp_path: Path) -> dict[str, Path]:
    source = tmp_path / "bridge.lua"
    source.write_text("return {}\n", encoding="utf-8")
    registry = tmp_path / "registry.lua"
    registry.write_text(
        'key = "ring_primary"\ninventory_ids = {3093}\nequipped_ids = {3096}\n'
        'key = "ring_secondary"\ninventory_ids = {3097}\nequipped_ids = {3099}\n'
        "default_enabled = false\n",
        encoding="utf-8",
    )
    registry_sha = hashlib.sha256(registry.read_bytes()).hexdigest()
    profile = tmp_path / "profile.lua"
    profile.write_text(
        "family_enabled = {\n    ring_primary = false,\n    ring_secondary = true,\n}\n",
        encoding="utf-8",
    )
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest_sha = _write(
        manifest,
        {
            "helper_version": "v2.4.1",
            "files": [
                {"path": plan.MODULE_PATH, "sha256": source_sha},
                {"path": plan.REGISTRY_MODULE_PATH, "sha256": registry_sha},
            ],
        },
    )
    gates = tmp_path / "gates.json"
    _write(
        gates,
        {
            "status": "passed",
            "failed": [],
            "check_count": 19,
            "passed_count": 19,
            "manifest": {"sha256": manifest_sha},
            "observed": {"runtime_state": "disarmed"},
        },
    )
    receipt = tmp_path / "p10.json"
    _write(
        receipt,
        {
            "schema_version": "ctoa.equipment-shadow-acceptance.v1",
            "status": "accepted",
            "acceptance_granted": True,
            "action": "plan_ring_swap",
            "blockers": [],
            "dispatch_allowed": False,
            "runtime_actions": False,
            "execute_once_allowed": False,
            "promotion_allowed": False,
        },
    )
    capability = tmp_path / "capability.json"
    _write(
        capability,
        {
            "observed_at_unix_ms": 10_000,
            "heartbeat_status": "online",
            "online": True,
            "vocation": "ek",
            "runtime_state": "disarmed",
            "runtime_enabled": False,
            "equipment_shadow_observation": {
                "schema_version": "ctoa.equipment-shadow-observation.v1",
                "observed_at_unix_ms": 10_000,
                "observation_id": "equipment-10000",
                "online": "online",
                "alive": "alive",
                "protection_zone": "outside",
                "protection_zone_source": "player_states",
                "inventory_api_available": True,
                "containers_complete": True,
                "ring": {"present": True, "item_id": 3096, "count": 1},
                "candidates": [
                    {"container_id": 3, "slot_index": 1, "item_id": 3097, "count": 1}
                ],
                "cooldown": "ready",
                "cooldown_source": "game_cooldown_group",
                "producer_source": "otclient_guarded_adapter",
                "dispatch_allowed": False,
                "runtime_actions": False,
                "executes_plan": False,
                "execute_once_allowed": False,
                "promotion_allowed": False,
            },
        },
    )
    return {
        "manifest": manifest,
        "runtime_gates": gates,
        "p10_receipt": receipt,
        "capability": capability,
        "source": source,
        "registry_source": registry,
        "family_selection_profile": profile,
    }


def test_equipment_plan_binds_exact_current_ring_and_candidate(tmp_path: Path) -> None:
    report = plan.build_plan(_fixture(tmp_path), now_ms=10_100)
    assert report["status"] == "ready_for_sandbox_session_approval"
    assert report["blockers"] == []
    assert report["before_item_id"] == 3096
    assert report["before_family_key"] == "ring_primary"
    assert report["candidate_item_id"] == 3097
    assert report["candidate_family_key"] == "ring_secondary"
    assert report["requires_post_action_ring_id"] == 3099
    assert report["rollback_item_id"] == 3093
    assert report["source_container_id"] == 3
    assert report["source_slot_index"] == 1
    assert report["bridge_implemented"] is True
    assert report["attempt_count"] == 0
    assert report["intrusive_actions_performed"] == []
    assert all(report[field] is False for field in plan.FALSE_FLAGS)


def test_equipment_plan_fails_closed_in_pz_or_on_duplicate_candidate(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    capability = json.loads(paths["capability"].read_text())
    observation = capability["equipment_shadow_observation"]
    observation["protection_zone"] = "inside"
    observation["candidates"].append(dict(observation["candidates"][0]))
    _write(paths["capability"], capability)
    report = plan.build_plan(paths, now_ms=10_100)
    assert report["status"] == "blocked"
    assert "observation_protection_zone_not_ready" in report["blockers"]
    assert "candidate_ring_not_unique" in report["blockers"]
    assert report["execute_once_allowed"] is False


def test_equipment_plan_rejects_stale_capability(tmp_path: Path) -> None:
    report = plan.build_plan(_fixture(tmp_path), now_ms=30_001)
    assert report["status"] == "blocked"
    assert "capability_heartbeat_stale" in report["blockers"]


def test_equipment_plan_requires_exactly_secondary_family_selected(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    paths["family_selection_profile"].write_text(
        "family_enabled = {\n    ring_primary = true,\n    ring_secondary = true,\n}\n",
        encoding="utf-8",
    )
    report = plan.build_plan(paths, now_ms=10_100)
    assert report["status"] == "blocked"
    assert "family_selection_invalid" in report["blockers"]
