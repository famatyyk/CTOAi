#!/usr/bin/env python3
"""Produce the canonical passive Recovery predecessor evidence for P9.

The producer consumes only the current BackgroundNoScreen artifact and the
tracked data-only Conditions profile.  It never attaches to OTClient, invokes
the Recovery executor, or turns a blocked P8/observation into ready evidence.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as replay
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime"
DEV_DIR = RUNTIME_ROOT / "solteria_helper_dev"
DEFAULT_BACKGROUND = DEV_DIR / "background_status.json"
DEFAULT_PROFILE = ROOT / "config" / "otclient" / "conditions-shadow-profile.json"
DEFAULT_TRACE = DEV_DIR / "recovery_bridge_trace.json"
DEFAULT_PROOF = DEV_DIR / "conditions_recovery_proof.json"

FALSE_FLAGS = replay.FALSE_FLAGS
BLOCKER_ORDER = (
    "background_missing",
    "background_invalid",
    "profile_invalid",
    "profile_unsafe_contract",
    "observation_missing",
    "observation_invalid",
    "observation_future",
    "observation_stale",
    "player_offline",
    "player_dead",
    "protection_zone_inside",
    "protection_zone_unknown",
    "condition_absent",
    "condition_unknown",
    "cooldown_active",
    "cooldown_unknown",
    "p8_invalid",
    "p8_future",
    "p8_stale",
    "p8_observation_hash_mismatch",
    "p8_operational_acceptance_blocked",
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}


def _ordered(values: Iterable[str]) -> list[str]:
    return sorted(set(values), key=BLOCKER_RANK.__getitem__)[:16]


def _age(timestamp: Any, now_ms: int) -> int | None:
    if not replay._is_int(timestamp) or timestamp <= 0:
        return None
    return now_ms - timestamp


def build_evidence(
    *,
    background: replay.InputDocument,
    profile: replay.InputDocument,
    generated_at_unix_ms: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build hash-bound trace/proof documents without performing an action."""

    blockers: set[str] = set()
    observation = replay.extract_embedded_observation(background)
    p8 = replay.normalize_p8_proof(background, observation)

    if background.status != "loaded":
        blockers.add("background_missing" if background.status == "missing" else "background_invalid")
    if profile.status != "loaded" or not isinstance(profile.payload, dict):
        blockers.add("profile_invalid")
    elif not replay._profile_structurally_valid(profile.payload):
        blockers.add("profile_invalid")
    else:
        expected_profile = {
            "mode": "shadow_only",
            "action": replay.ACTION,
            "condition": replay.CONDITION,
            "spell": replay.SPELL,
            "max_observation_age_ms": 6000,
            "cooldown_required": "ready",
            "retry_budget": 0,
            "requires_p8_ready": True,
            "requires_recovery_trace": True,
        }
        if any(profile.payload.get(key) != value for key, value in expected_profile.items()):
            blockers.add("profile_invalid")
        if not replay._false_flags(profile.payload):
            blockers.add("profile_unsafe_contract")

    if observation.status != "loaded" or not isinstance(observation.payload, dict):
        blockers.add("observation_missing" if observation.status == "missing" else "observation_invalid")
    elif not replay._observation_structurally_valid(observation.payload):
        blockers.add("observation_invalid")
    else:
        item = observation.payload
        age = _age(item.get("observed_at_unix_ms"), generated_at_unix_ms)
        if age is not None and age < 0:
            blockers.add("observation_future")
        elif age is None or age > 6000:
            blockers.add("observation_stale")
        if item.get("online") != "online":
            blockers.add("player_offline")
        if item.get("alive") != "alive":
            blockers.add("player_dead")
        if item.get("protection_zone") == "inside":
            blockers.add("protection_zone_inside")
        elif item.get("protection_zone") != "outside" or item.get(
            "protection_zone_source"
        ) not in {"player_method", "player_states"}:
            blockers.add("protection_zone_unknown")
        if item.get("condition_id") != replay.CONDITION or item.get("condition_state") == "absent":
            blockers.add("condition_absent")
        elif item.get("condition_state") != "present":
            blockers.add("condition_unknown")
        if item.get("cooldown") == "active":
            blockers.add("cooldown_active")
        elif item.get("cooldown") != "ready" or item.get("cooldown_source") != "game_cooldown_group":
            blockers.add("cooldown_unknown")
        if item.get("producer_source") != "otclient_guarded_adapter" or not replay._false_flags(item):
            blockers.add("observation_invalid")

    if p8.status != "loaded" or not isinstance(p8.payload, dict) or not replay._p8_structurally_valid(p8.payload):
        blockers.add("p8_invalid")
    else:
        item = p8.payload
        age = _age(item.get("observed_at_unix_ms"), generated_at_unix_ms)
        if age is not None and age < 0:
            blockers.add("p8_future")
        elif age is None or age > replay.MAX_P8_AGE_MS:
            blockers.add("p8_stale")
        if observation.status == "loaded" and item.get("conditions_observation_sha256") != observation.sha256:
            blockers.add("p8_observation_hash_mismatch")
        if item.get("source") != "background_no_screen" or not replay._p8_acceptance_ready(item):
            blockers.add("p8_operational_acceptance_blocked")

    ordered = _ordered(blockers)
    ready = not ordered
    source_timestamps = [generated_at_unix_ms]
    for document in (observation, p8):
        if isinstance(document.payload, dict):
            timestamp = document.payload.get("observed_at_unix_ms")
            if replay._is_int(timestamp) and timestamp > 0:
                source_timestamps.append(timestamp)
    evidence_at_unix_ms = min(source_timestamps)
    trace_basis = {
        "schema_version": replay.RECOVERY_TRACE_SCHEMA,
        "observed_at_unix_ms": evidence_at_unix_ms,
        "source": "recovery_shadow",
        "status": "ready" if ready else "blocked",
        "decision": "plan_heal" if ready else "hold",
        "guard": "passed" if ready else "blocked",
        "action": replay.SPELL if "profile_invalid" not in blockers else "other",
        "result": "dry_run",
        "blockers": ordered,
        "dry_run": True,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    trace = {
        **trace_basis,
        "trace_id": f"recovery-shadow-{replay.canonical_sha256(trace_basis)[:16]}",
    }
    proof_basis = {
        "schema_version": replay.RECOVERY_PROOF_SCHEMA,
        "observed_at_unix_ms": evidence_at_unix_ms,
        "status": "ready" if ready else "blocked",
        "source": "recovery_shadow",
        "action": replay.ACTION,
        "condition": replay.CONDITION,
        "spell": replay.SPELL,
        "recovery_trace_sha256": replay.canonical_sha256(trace),
        "profile_sha256": profile.sha256,
        "observation_sha256": observation.sha256,
        "p8_proof_sha256": p8.sha256,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    proof = {
        **proof_basis,
        "proof_id": f"conditions-recovery-{replay.canonical_sha256(proof_basis)[:16]}",
    }
    return trace, proof


def _validate_output(path: Path, expected: Path) -> None:
    if os.path.normcase(str(path.resolve(strict=False))) != os.path.normcase(str(expected.resolve(strict=False))):
        raise ValueError(f"output must equal {expected}")
    boundary = RUNTIME_ROOT.resolve(strict=False)
    if not path.resolve(strict=False).is_relative_to(boundary):
        raise ValueError(f"output must stay under {boundary}")
    current = boundary
    relative = Path(os.path.abspath(path.parent)).relative_to(Path(os.path.abspath(boundary)))
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
        if stat.S_ISLNK(metadata.st_mode) or int(getattr(metadata, "st_file_attributes", 0)) & reparse:
            raise ValueError("output parent must not contain a symlink or reparse point")


def _write_atomic(path: Path, expected: Path, payload: dict[str, Any]) -> None:
    _validate_output(path, expected)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(replay.canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        _validate_output(path, expected)
        temporary.replace(path)
        persisted = replay.read_document(path)
        if persisted.status != "loaded" or persisted.sha256 != replay.canonical_sha256(payload):
            raise ValueError("persisted output verification failed")
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true")
    parser.add_argument("--generated-at-unix-ms", type=int, default=None)
    args = parser.parse_args(argv)
    generated_at = args.generated_at_unix_ms or int(time.time() * 1000)
    trace, proof = build_evidence(
        background=replay.read_document(DEFAULT_BACKGROUND),
        profile=replay.read_document(DEFAULT_PROFILE),
        generated_at_unix_ms=generated_at,
    )
    if not args.no_write:
        _write_atomic(DEFAULT_TRACE, DEFAULT_TRACE, trace)
        persisted_trace = replay.read_document(DEFAULT_TRACE)
        if (
            persisted_trace.status != "loaded"
            or persisted_trace.sha256 != proof["recovery_trace_sha256"]
        ):
            raise ValueError("Recovery trace changed before proof persistence")
        _write_atomic(DEFAULT_PROOF, DEFAULT_PROOF, proof)
    print(replay.canonical_bytes({"trace": trace, "proof": proof}).decode("utf-8"))
    return 0 if proof["status"] == "ready" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
