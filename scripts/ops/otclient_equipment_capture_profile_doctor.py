#!/usr/bin/env python3
"""Diagnose the fixed, data-only P10 Equipment capture profile.

This command never reads an OTClient installation and never performs an item
action. It reports whether the ignored operator override is structurally ready
for the passive P10 snapshot producer.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import uuid
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_equipment_shadow_snapshot as snapshot
else:  # pragma: no cover
    import otclient_equipment_shadow_snapshot as snapshot


OUTPUT = snapshot.DEV_DIR / "equipment_capture_profile_doctor.json"
ZERO_KEYS = (
    "equipped_item_id",
    "candidate_item_id",
    "candidate_source_container_id",
)


def zero_id_skeleton() -> dict[str, Any]:
    """Return the exact unconfigured, no-action local capture profile."""

    payload: dict[str, Any] = {
        "schema_version": snapshot.CAPTURE_SCHEMA,
        "configured_by_operator": False,
        "slot": "ring",
        "equipped_item_id": 0,
        "candidate_item_id": 0,
        "candidate_source_container_id": 0,
        "candidate_source_slot_index": 0,
        "max_observation_age_ms": snapshot.MAX_AGE_MS,
        "retry_budget": 0,
        **{key: False for key in snapshot.FALSE_FLAGS},
    }
    if not snapshot._capture_profile_valid(payload):  # pragma: no cover - invariant
        raise RuntimeError("internal zero-ID capture profile is invalid")
    return payload


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    return stat.S_ISLNK(metadata.st_mode) or bool(
        int(getattr(metadata, "st_file_attributes", 0)) & reparse
    )


def _fixed_local_target() -> Path:
    target = Path(os.path.abspath(snapshot.DEFAULT_LOCAL_CAPTURE_PROFILE))
    expected = Path(
        os.path.abspath(
            snapshot.ROOT
            / ".ctoa-local"
            / "otclient"
            / "equipment-shadow-capture-profile.json"
        )
    )
    if os.path.normcase(str(target)) != os.path.normcase(str(expected)):
        raise ValueError("initializer target must be the fixed .ctoa-local profile")
    return target


def _ensure_safe_parent(target: Path) -> None:
    """Create only ordinary directories below ROOT and reject path indirection."""

    root = Path(os.path.abspath(snapshot.ROOT))
    try:
        relative_parent = target.parent.relative_to(root)
    except ValueError as exc:  # pragma: no cover - guarded by _fixed_local_target
        raise ValueError(
            "initializer target must stay below the repository root"
        ) from exc

    try:
        root_metadata = root.lstat()
    except FileNotFoundError as exc:  # pragma: no cover - repository invariant
        raise ValueError("repository root is missing") from exc
    if _is_link_or_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("repository root must be an ordinary directory")

    current = root
    for part in relative_parent.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                pass
            metadata = current.lstat()
        if _is_link_or_reparse(metadata):
            raise ValueError(
                "initializer parent must not contain a symlink or reparse point"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("initializer parent components must be directories")


def _target_metadata(target: Path) -> os.stat_result | None:
    try:
        return target.lstat()
    except FileNotFoundError:
        return None


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def initialize_local_profile() -> dict[str, Any]:
    """Exclusively publish the fixed zero-ID profile without reading OTClient.

    A complete, fsynced temporary file is hard-linked into the final name. Link
    creation is atomic and fails when any target already exists, so the
    initializer has no overwrite path.
    """

    target = _fixed_local_target()
    _ensure_safe_parent(target)
    existing = _target_metadata(target)
    if existing is not None:
        if _is_link_or_reparse(existing):
            raise ValueError(
                "initializer target must not be a symlink or reparse point"
            )
        raise FileExistsError(
            f"initializer never overwrites existing profile: {target}"
        )

    payload = zero_id_skeleton()
    encoded = snapshot.p9_replay.canonical_bytes(payload) + b"\n"
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary_metadata: os.stat_result | None = None
    published = False
    verified = False
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | int(getattr(os, "O_BINARY", 0))
            | int(getattr(os, "O_NOFOLLOW", 0))
        )
        descriptor = os.open(temporary, flags, 0o600)
        try:
            offset = 0
            while offset < len(encoded):
                written = os.write(descriptor, encoded[offset:])
                if written <= 0:  # pragma: no cover - defensive OS boundary
                    raise OSError("zero-ID capture profile write made no progress")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

        temporary_metadata = temporary.lstat()
        if _is_link_or_reparse(temporary_metadata) or not stat.S_ISREG(
            temporary_metadata.st_mode
        ):
            raise ValueError("initializer temporary file identity is invalid")

        _ensure_safe_parent(target)
        existing = _target_metadata(target)
        if existing is not None:
            if _is_link_or_reparse(existing):
                raise ValueError(
                    "initializer target must not be a symlink or reparse point"
                )
            raise FileExistsError(
                f"initializer never overwrites existing profile: {target}"
            )

        os.link(temporary, target, follow_symlinks=False)
        published = True
        target_metadata = target.lstat()
        if (
            _is_link_or_reparse(target_metadata)
            or not stat.S_ISREG(target_metadata.st_mode)
            or not _same_identity(temporary_metadata, target_metadata)
        ):
            raise ValueError("published initializer target identity is invalid")

        document = snapshot.p9_replay.read_document(target)
        expected_sha256 = snapshot.p9_replay.canonical_sha256(payload)
        if (
            document.status != "loaded"
            or document.payload != payload
            or document.sha256 != expected_sha256
        ):
            raise ValueError("published zero-ID capture profile verification failed")
        verified = True
        return {
            "status": "initialized_unconfigured",
            "path": str(target),
            "sha256": expected_sha256,
            "configured_by_operator": False,
            "runtime_readiness_claimed": False,
        }
    finally:
        if published and not verified and temporary_metadata is not None:
            target_metadata = _target_metadata(target)
            if target_metadata is not None and _same_identity(
                temporary_metadata, target_metadata
            ):
                target.unlink()
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def diagnose() -> dict[str, Any]:
    path, source = snapshot.resolve_capture_profile()
    document = snapshot.load_capture_profile(path, source)
    payload = document.payload if isinstance(document.payload, dict) else {}
    blockers: list[str] = []

    if source != "local_operator_override":
        blockers.append("local_operator_override_missing")
    if document.status != "loaded" or not snapshot._capture_profile_valid(payload):
        blockers.append("capture_profile_invalid")
    if payload.get("configured_by_operator") is not True:
        blockers.append("operator_confirmation_missing")
    if any(payload.get(key, 0) <= 0 for key in ZERO_KEYS):
        blockers.append("exact_ids_missing")
    equipped = payload.get("equipped_item_id")
    candidate = payload.get("candidate_item_id")
    if isinstance(equipped, int) and equipped > 0 and equipped == candidate:
        blockers.append("candidate_matches_equipped")

    status = "ready" if not blockers else "blocked"
    return {
        "schema_version": "ctoa.equipment-capture-profile-doctor.v1",
        "status": status,
        "source": source,
        "path": str(path),
        "sha256": document.sha256,
        "configured_by_operator": payload.get("configured_by_operator") is True,
        "slot": payload.get("slot"),
        "identifiers_present": all(payload.get(key, 0) > 0 for key in ZERO_KEYS),
        "candidate_slot_index_valid": isinstance(
            payload.get("candidate_source_slot_index"), int
        )
        and payload.get("candidate_source_slot_index", -1) >= 0,
        "no_action_contract": all(
            payload.get(key) is False for key in snapshot.FALSE_FLAGS
        ),
        "blockers": blockers,
        "next_action": (
            "Run .\\ctoa.ps1 otp10 after P9 acceptance and a fresh passive observation."
            if status == "ready"
            else (
                "Run .\\ctoa.ps1 otp10doctor init once, then set exact ring/container IDs."
                if source != "local_operator_override"
                else "Set exact ring/container IDs and explicitly confirm the local profile."
            )
        ),
        "runtime_actions": False,
        "live_file_writes": False,
        "runtime_readiness_claimed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--init-local",
        action="store_true",
        help="exclusively create the fixed ignored zero-ID local profile",
    )
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return zero for a structurally valid blocked diagnosis",
    )
    args = parser.parse_args(argv)

    initialized: dict[str, Any] | None = None
    if args.init_local:
        try:
            initialized = initialize_local_profile()
        except (OSError, ValueError) as exc:
            print(f"P10 capture-profile initializer blocked: {exc}", file=sys.stderr)
            return 2

    report = diagnose()
    snapshot._write_atomic(OUTPUT, OUTPUT, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if initialized is not None:
        if report["status"] != "blocked":  # pragma: no cover - zero-ID invariant
            raise RuntimeError(
                "zero-ID initializer unexpectedly produced a ready profile"
            )
        print(
            "P10 zero-ID local profile initialized; it remains unconfigured and "
            "no runtime readiness is claimed.",
            file=sys.stderr,
        )
        return 0
    print(f"P10 capture-profile doctor: {report['status']}", file=sys.stderr)
    return 0 if report["status"] == "ready" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
