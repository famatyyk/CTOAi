#!/usr/bin/env python3
"""Build the hash-bound P12 Conditions sandbox-session plan; never execute it."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "runtime" / "solteria_helper_dev"
MANIFEST = DEV / "manifest.json"
VALIDATION = DEV / "validation.json"
PREFLIGHT = DEV / "smoke_preflight.json"
STATIC_GATES = DEV / "module_static_gates.json"
MODULE_CONTRACT = DEV / "module_contract.json"
P9_RECEIPT = DEV / "conditions_shadow_acceptance.json"
SOURCE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_conditions_execute_once.lua"
EK_PROFILE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_ek_profile.lua"
OUTPUT = DEV / "p12_conditions_execute_once_plan.json"
MODULE_PATH = "mods/ctoa_otclient/ctoa_helper_conditions_execute_once.lua"
EK_PROFILE_PATH = "mods/ctoa_otclient/ctoa_ek_profile.lua"
SCHEMA = "ctoa.p12-conditions-execute-once-plan.v1"
FALSE_FLAGS = ("dispatch_allowed", "runtime_actions", "execute_once_allowed", "live_promotion")


def _read(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value, hashlib.sha256(raw).hexdigest()


def _created_at(value: Any) -> datetime:
    return datetime.fromisoformat(str(value))


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_plan(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    selected = paths or {
        "manifest": MANIFEST,
        "validation": VALIDATION,
        "preflight": PREFLIGHT,
        "static_gates": STATIC_GATES,
        "module_contract": MODULE_CONTRACT,
        "p9_receipt": P9_RECEIPT,
        "source": SOURCE,
        "ek_profile": EK_PROFILE,
    }
    blockers: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for name in ("manifest", "validation", "preflight", "static_gates", "module_contract", "p9_receipt"):
        try:
            docs[name], hashes[name] = _read(selected[name])
        except (OSError, ValueError, json.JSONDecodeError):
            blockers.append(f"{name}_missing_or_invalid")
            docs[name], hashes[name] = {}, "0" * 64

    try:
        source_sha = hashlib.sha256(selected["source"].read_bytes()).hexdigest()
    except OSError:
        source_sha = "0" * 64
        blockers.append("source_missing")
    try:
        ek_profile_bytes = selected["ek_profile"].read_bytes()
        ek_profile_text = ek_profile_bytes.decode("utf-8")
        ek_profile_sha = hashlib.sha256(ek_profile_bytes).hexdigest()
        if not re.search(r'healing\s*=\s*\{.*?\bspell\s*=\s*"exura ico"', ek_profile_text, re.DOTALL):
            blockers.append("ek_profile_spell_mismatch")
    except (OSError, UnicodeError):
        ek_profile_sha = "0" * 64
        blockers.append("ek_profile_missing")

    manifest = docs["manifest"]
    entries = [item for item in manifest.get("files", []) if isinstance(item, dict) and item.get("path") == MODULE_PATH]
    if len(entries) != 1 or entries[0].get("sha256") != source_sha:
        blockers.append("source_manifest_parity_failed")
    profile_entries = [item for item in manifest.get("files", []) if isinstance(item, dict) and item.get("path") == EK_PROFILE_PATH]
    if len(profile_entries) != 1 or profile_entries[0].get("sha256") != ek_profile_sha:
        blockers.append("ek_profile_manifest_parity_failed")
    if manifest.get("helper_version") != "v2.4.1":
        blockers.append("helper_version_mismatch")
    if docs["validation"].get("status") != "passed":
        blockers.append("validation_not_passed")
    preflight_manifest = docs["preflight"].get("manifest")
    if not isinstance(preflight_manifest, dict) or docs["preflight"].get("status") != "passed" or preflight_manifest.get("sha256") != hashes["manifest"]:
        blockers.append("smoke_preflight_not_current")
    if not (docs["static_gates"].get("status") == "passed" and docs["static_gates"].get("failed_count") == 0):
        blockers.append("module_static_gates_not_passed")
    if not (docs["module_contract"].get("status") == "passed" and docs["module_contract"].get("failed_count") == 0):
        blockers.append("module_contract_not_passed")
    try:
        manifest_time = _created_at(manifest.get("created_at"))
        for name in ("validation", "static_gates", "module_contract"):
            if _created_at(docs[name].get("created_at")) < manifest_time:
                blockers.append(f"{name}_stale")
    except (TypeError, ValueError):
        blockers.append("evidence_timestamp_invalid")

    receipt = docs["p9_receipt"]
    if not (
        receipt.get("schema_version") == "ctoa.conditions-shadow-acceptance.v1"
        and receipt.get("status") == "accepted"
        and receipt.get("acceptance_granted") is True
        and receipt.get("receipt_persisted") is True
        and receipt.get("action") == "plan_paralyze_recovery"
        and receipt.get("condition") == "paralyze"
        and receipt.get("spell") == "exura"
        and receipt.get("blockers") == []
        and all(receipt.get(flag) is False for flag in ("dispatch_allowed", "runtime_actions", "execute_once_allowed", "promotion_allowed"))
    ):
        blockers.append("p9_acceptance_invalid")

    basis = {
        "schema_version": SCHEMA,
        "lane": "conditions",
        "vocation": "ek",
        "action": "cast_exura_ico",
        "spell": "exura ico",
        "spell_source": "ctoa_ek_profile.healing.spell",
        "predecessor_accepted_spell": "exura",
        "retry_budget": 0,
        "mandatory_kill_and_disarm": True,
        "requires_fresh_paralyze_observation_ms": 1000,
        "manifest_sha256": hashes["manifest"],
        "source_sha256": source_sha,
        "ek_profile_sha256": ek_profile_sha,
        "p9_receipt_sha256": hashes["p9_receipt"],
        "validation_sha256": hashes["validation"],
        "smoke_preflight_sha256": hashes["preflight"],
        "module_static_gates_sha256": hashes["static_gates"],
        "module_contract_sha256": hashes["module_contract"],
    }
    plan_sha = hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        **basis,
        "status": "ready_for_sandbox_session_approval" if not blockers else "blocked",
        "plan_sha256": plan_sha,
        "blockers": blockers,
        "required_session_confirmation": f"zatwierdzam sesję sandbox P12 Conditions {plan_sha}",
        "required_execute_confirmation": f"zatwierdzam wykonanie P12 Conditions {plan_sha}",
        "session_approved": False,
        "execution_approved": False,
        "attempt_count": 0,
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
