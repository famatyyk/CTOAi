#!/usr/bin/env python3
"""Capture the hash-bound P12 Heal Friend plan; never cast or send chat."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "runtime" / "solteria_helper_dev"
MANIFEST = DEV / "manifest.json"
RUNTIME_GATES = DEV / "runtime_module_gates_sandbox_smoke.json"
P11_RECEIPT = DEV / "heal_friend_shadow_acceptance.json"
P11_REPORT = DEV / "heal_friend_shadow_replay.json"
P12_EQUIPMENT_RECEIPT = DEV / "p12_equipment_execute_once_receipt.json"
SOURCE = ROOT / "scripts/lua/otclient/ctoa_helper_heal_friend_execute_once.lua"
OUTPUT = DEV / "p12_heal_friend_execute_once_plan.json"
MODULE_PATH = "mods/ctoa_otclient/ctoa_helper_heal_friend_execute_once.lua"
SCHEMA = "ctoa.p12-heal-friend-execute-once-plan.v1"
EXACT_VOCATION = "ed"
SPELL = "exura sio"
HP_THRESHOLD = 70
MAX_RANGE = 7
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "execute_once_allowed",
    "live_promotion",
)


def _canonical_sha(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value, hashlib.sha256(raw).hexdigest()


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def build_plan(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    selected = paths or {
        "manifest": MANIFEST,
        "runtime_gates": RUNTIME_GATES,
        "p11_receipt": P11_RECEIPT,
        "p11_report": P11_REPORT,
        "p12_equipment_receipt": P12_EQUIPMENT_RECEIPT,
        "source": SOURCE,
    }
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name, path in selected.items():
        if name == "source":
            continue
        try:
            docs[name], hashes[name] = _load(path)
        except (OSError, ValueError, json.JSONDecodeError):
            docs[name], hashes[name] = {}, "0" * 64
            blockers.append(f"{name}_missing_or_invalid")
    try:
        source_sha = hashlib.sha256(selected["source"].read_bytes()).hexdigest()
    except OSError:
        source_sha = "0" * 64
        blockers.append("source_missing")

    manifest = docs["manifest"]
    gates = docs["runtime_gates"]
    p11_receipt = docs["p11_receipt"]
    p11_report = docs["p11_report"]
    equipment_receipt = docs["p12_equipment_receipt"]
    entries = [
        item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and item.get("path") == MODULE_PATH
    ]
    if len(entries) != 1 or entries[0].get("sha256") != source_sha:
        blockers.append("source_manifest_parity_failed")
    gate_manifest = gates.get("manifest")
    if not (
        gates.get("status") == "passed"
        and gates.get("failed") == []
        and isinstance(gate_manifest, dict)
        and gate_manifest.get("sha256") == hashes["manifest"]
        and gates.get("observed", {}).get("runtime_state") == "disarmed"
    ):
        blockers.append("runtime_gates_not_current")
    if manifest.get("helper_version") != "v2.4.1":
        blockers.append("helper_version_mismatch")

    report_canonical_sha = _canonical_sha(p11_report) if p11_report else "0" * 64
    trace = (
        p11_report.get("operational_trace")
        if isinstance(p11_report.get("operational_trace"), dict)
        else {}
    )
    shadow_plan = trace.get("plan") if isinstance(trace.get("plan"), dict) else {}
    if not (
        p11_receipt.get("schema_version")
        == "ctoa.heal-friend-shadow-acceptance.v1"
        and p11_receipt.get("status") == "accepted"
        and p11_receipt.get("acceptance_granted") is True
        and p11_receipt.get("blockers") == []
        and p11_receipt.get("report_sha256") == report_canonical_sha
        and p11_receipt.get("recomputed_report_sha256") == report_canonical_sha
        and all(
            p11_receipt.get(flag) is False
            for flag in (
                "dispatch_allowed",
                "runtime_actions",
                "execute_once_allowed",
                "promotion_allowed",
                "casts",
                "talks",
            )
        )
    ):
        blockers.append("p11_acceptance_invalid")
    if not (
        p11_report.get("schema_version")
        == "ctoa.heal-friend-shadow-replay-report.v1"
        and p11_report.get("status") == "passed"
        and p11_report.get("source") == "operational"
        and trace.get("schema_version") == "ctoa.heal-friend-shadow-trace.v1"
        and trace.get("status") == "shadow_plan_ready"
        and trace.get("action") == "plan_sio"
        and trace.get("blockers") == []
    ):
        blockers.append("p11_operational_report_invalid")

    target_id = shadow_plan.get("target_id")
    target_name = shadow_plan.get("target_name")
    whitelist_revision = shadow_plan.get("whitelist_revision")
    if not isinstance(target_id, int) or target_id <= 0:
        blockers.append("exact_target_id_invalid")
    if not isinstance(target_name, str) or not target_name.strip():
        blockers.append("exact_target_name_invalid")
        target_name = ""
    if (
        not isinstance(whitelist_revision, str)
        or len(whitelist_revision) != 64
        or any(char not in "0123456789abcdef" for char in whitelist_revision)
    ):
        blockers.append("whitelist_revision_invalid")
    if not (
        shadow_plan.get("action") == "plan_sio"
        and shadow_plan.get("spell") == SPELL
        and shadow_plan.get("hp_threshold") == HP_THRESHOLD
        and shadow_plan.get("max_range") == MAX_RANGE
        and shadow_plan.get("retry_budget") == 0
        and all(
            shadow_plan.get(flag) is False
            for flag in ("dispatch_allowed", "runtime_actions", "casts", "talks")
        )
    ):
        blockers.append("p11_plan_contract_mismatch")

    if not (
        equipment_receipt.get("schema_version")
        == "ctoa.p12-equipment-execute-once-receipt.v1"
        and equipment_receipt.get("status") == "accepted"
        and equipment_receipt.get("acceptance_granted") is True
        and equipment_receipt.get("lane") == "equipment"
        and equipment_receipt.get("attempt_count") == 1
        and equipment_receipt.get("retry_budget") == 0
        and equipment_receipt.get("retry_scheduled") is False
        and equipment_receipt.get("final_state") == "killed_and_disarmed"
        and equipment_receipt.get("blockers") == []
        and equipment_receipt.get("downstream_authority_granted") is False
        and all(
            equipment_receipt.get(flag) is False for flag in FALSE_FLAGS
        )
    ):
        blockers.append("p12_equipment_receipt_invalid")

    normalized_name = target_name.strip().lower()
    basis = {
        "schema_version": SCHEMA,
        "lane": "heal_friend",
        "exact_vocation": EXACT_VOCATION,
        "action": "cast_exura_sio_exact_target",
        "spell": SPELL,
        "target_id": target_id,
        "target_name": normalized_name,
        "target_name_sha256": hashlib.sha256(normalized_name.encode()).hexdigest(),
        "whitelist_revision": whitelist_revision,
        "hp_threshold": HP_THRESHOLD,
        "max_range": MAX_RANGE,
        "retry_budget": 0,
        "mandatory_kill_and_disarm": True,
        "manifest_sha256": hashes["manifest"],
        "runtime_gates_sha256": hashes["runtime_gates"],
        "p11_receipt_sha256": hashes["p11_receipt"],
        "p11_report_sha256": report_canonical_sha,
        "p12_equipment_receipt_sha256": hashes["p12_equipment_receipt"],
        "source_sha256": source_sha,
    }
    plan_sha = _canonical_sha(basis)
    return {
        **basis,
        "plan_sha256": plan_sha,
        "status": "ready_for_sandbox_session_approval" if not blockers else "blocked",
        "blockers": blockers,
        "bridge_implemented": True,
        "required_session_confirmation": (
            f"zatwierdzam sesję sandbox P12 Heal Friend {plan_sha}"
        ),
        "required_execute_confirmation": (
            f"zatwierdzam wykonanie P12 Heal Friend {plan_sha}"
        ),
        "session_approved": False,
        "execution_approved": False,
        "attempt_count": 0,
        "retry_scheduled": False,
        "final_state": "disarmed",
        **{flag: False for flag in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main() -> int:
    plan = build_plan()
    _atomic_write(OUTPUT, plan)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0 if plan["status"] == "ready_for_sandbox_session_approval" else 1


if __name__ == "__main__":
    sys.exit(main())
