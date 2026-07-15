#!/usr/bin/env python3
"""Apply one reviewed P10 capture-profile plan to the fixed local override.

This tool never reads or controls OTClient and never moves an item.  It accepts
only the fixed repo-runtime plan and fixed ignored local profile, verifies their
canonical hashes and schemas, requires a plan-hash-bound Polish confirmation,
then performs an atomic local profile write with a retained ``.bak`` copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import uuid
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_capture_profile_change_plan as change_plan
    from . import otclient_equipment_shadow_snapshot as snapshot
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_capture_profile_change_plan as change_plan
    import otclient_equipment_shadow_snapshot as snapshot


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    ROOT
    / "runtime"
    / "solteria_helper_dev"
    / "equipment_capture_profile_change_plan.json"
)
PROFILE_PATH = (
    ROOT / ".ctoa-local" / "otclient" / "equipment-shadow-capture-profile.json"
)
BACKUP_PATH = PROFILE_PATH.with_suffix(PROFILE_PATH.suffix + ".bak")
RECEIPT_PATH = (
    ROOT
    / "runtime"
    / "solteria_helper_dev"
    / "equipment_capture_profile_apply_receipt.json"
)
PLAN_SCHEMA_PATH = (
    ROOT / "schemas" / "equipment-capture-profile-change-plan.schema.json"
)
PROFILE_SCHEMA_PATH = ROOT / "schemas" / "equipment-shadow-capture-profile.schema.json"
MAX_BYTES = 256 * 1024


def exact_confirmation(plan_sha256: str) -> str:
    return f"zatwierdzam zastosowanie planu P10 {plan_sha256}"


def _load_schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def _schema_valid(payload: Any, path: Path) -> bool:
    return not list(Draft202012Validator(_load_schema(path)).iter_errors(payload))


def _strict_local_document(path: Path) -> documents.InputDocument:
    root = Path(os.path.abspath(ROOT))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return documents.InputDocument(None, "unreadable", documents.ZERO_SHA256)
    current = root
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        if (
            stat.S_ISLNK(metadata.st_mode)
            or int(getattr(metadata, "st_file_attributes", 0)) & reparse
        ):
            return documents.InputDocument(
                None, "symlink_rejected", documents.ZERO_SHA256
            )
    return documents.read_document(path, MAX_BYTES)


def _write_local_atomic(path: Path, payload: dict[str, Any]) -> None:
    local_root = Path(os.path.abspath(ROOT / ".ctoa-local" / "otclient"))
    resolved = Path(os.path.abspath(path))
    if resolved.parent != local_root:
        raise ValueError("local profile output escaped the fixed operator directory")
    local_root.mkdir(parents=True, exist_ok=True)
    if local_root.is_symlink() or (path.exists() and path.is_symlink()):
        raise ValueError("local profile path must not be a symlink")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | int(getattr(os, "O_BINARY", 0))
            | int(getattr(os, "O_NOFOLLOW", 0)),
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as handle:
                handle.write(documents.canonical_bytes(payload) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            os.close(descriptor)
        temporary.replace(path)
        persisted = _strict_local_document(path)
        if (
            persisted.status != "loaded"
            or persisted.sha256 != documents.canonical_sha256(payload)
        ):
            raise ValueError("atomic local profile verification failed")
    finally:
        temporary.unlink(missing_ok=True)


def apply_plan(*, plan_sha256: str, confirmation: str | None) -> dict[str, Any]:
    blockers: list[str] = []
    plan_doc = _strict_local_document(PLAN_PATH)
    profile_doc = _strict_local_document(PROFILE_PATH)
    plan_payload = plan_doc.payload if plan_doc.status == "loaded" else None
    current_profile = profile_doc.payload if profile_doc.status == "loaded" else None

    if not isinstance(plan_payload, dict) or not _schema_valid(
        plan_payload, PLAN_SCHEMA_PATH
    ):
        blockers.append("plan_invalid")
    if not isinstance(current_profile, dict) or not _schema_valid(
        current_profile, PROFILE_SCHEMA_PATH
    ):
        blockers.append("current_profile_invalid")

    plan = plan_payload.get("plan") if isinstance(plan_payload, dict) else None
    canonical_plan_sha = (
        documents.canonical_sha256(plan) if isinstance(plan, dict) else None
    )
    if (
        not isinstance(plan_payload, dict)
        or plan_payload.get("status") != "plan_generated"
        or plan_payload.get("blockers") != []
        or plan_payload.get("plan_sha256") != canonical_plan_sha
        or canonical_plan_sha != plan_sha256
    ):
        blockers.append("plan_sha256_mismatch")

    proposed = None
    expected_current = None
    proposed_sha = None
    if isinstance(plan, dict):
        expected_current = plan.get("expected_current_profile_sha256")
        proposed_sha = plan.get("proposed_profile_sha256")
        diff = plan.get("diff")
        if isinstance(diff, dict):
            proposed = diff.get("set")
    if profile_doc.sha256 != expected_current:
        blockers.append("current_profile_sha256_mismatch")
    if (
        not isinstance(proposed, dict)
        or not _schema_valid(proposed, PROFILE_SCHEMA_PATH)
        or documents.canonical_sha256(proposed) != proposed_sha
        or any(proposed.get(key) is not False for key in change_plan.FALSE_FLAGS)
    ):
        blockers.append("proposed_profile_invalid")

    expected_confirmation = exact_confirmation(plan_sha256)
    if confirmation != expected_confirmation:
        blockers.append("operator_confirmation_mismatch")

    blockers = list(dict.fromkeys(blockers))
    base = {
        "schema_version": "ctoa.equipment-capture-profile-apply.v1",
        "status": "blocked" if blockers else "applied",
        "plan_sha256": plan_sha256,
        "before_profile_sha256": profile_doc.sha256
        if profile_doc.status == "loaded"
        else None,
        "after_profile_sha256": proposed_sha if not blockers else None,
        "confirmation_sha256": (
            hashlib.sha256(expected_confirmation.encode("utf-8")).hexdigest()
            if confirmation == expected_confirmation
            else None
        ),
        "blockers": blockers,
        "profile_write_performed": False,
        "backup_path": None,
        "runtime_actions": False,
        "dispatch_allowed": False,
        "item_movement_performed": False,
        "live_file_writes": False,
        "acceptance_granted": False,
    }
    if blockers:
        return base

    assert isinstance(current_profile, dict) and isinstance(proposed, dict)
    _write_local_atomic(BACKUP_PATH, current_profile)
    _write_local_atomic(PROFILE_PATH, proposed)
    base["profile_write_performed"] = True
    base["backup_path"] = (
        ".ctoa-local/otclient/equipment-shadow-capture-profile.json.bak"
    )
    snapshot._write_atomic(RECEIPT_PATH, RECEIPT_PATH, base)
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--confirm")
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    report = apply_plan(plan_sha256=args.plan_sha256, confirmation=args.confirm)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "applied" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
