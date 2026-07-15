#!/usr/bin/env python3
"""Finalize one strict, no-action P10 operator refresh run.

The CLI is deliberately stateful and fixed-path:

* ``--begin`` creates a private pending journal and invalidates the prior final
  envelope;
* ``--record-stage`` binds the next fixed artifact to the current run; and
* ``--finalize`` re-reads every artifact, verifies the ordered receipts and
  writes ``runtime/solteria_helper_dev/equipment_operator_refresh_run.json``.
* ``--abort`` removes only a matching pending UUID after a failed run and
  preserves the last completed envelope.

It never launches OTClient, accepts evidence, changes eligibility, dispatches
an action, or writes live-client files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any
import uuid

from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions

try:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_consumer_parity as parity
except ImportError:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_consumer_parity as parity


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
OUTPUT = DEV_DIR / "equipment_operator_refresh_run.json"
PENDING = DEV_DIR / ".equipment_operator_refresh_run.pending.json"
REPORT_SCHEMA = ROOT / "schemas" / "equipment-operator-refresh-run.schema.json"

SCHEMA_VERSION = "ctoa.equipment-operator-refresh-run.v1"
PENDING_SCHEMA_VERSION = "ctoa.equipment-operator-refresh-run.pending.v1"
ABORT_SCHEMA_VERSION = "ctoa.equipment-operator-refresh-run-abort.v1"
ERROR_SCHEMA_VERSION = "ctoa.equipment-operator-refresh-run-error.v1"
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_RUN_DURATION_MS = 30_000
MAX_ARTIFACT_AGE_MS = 30_000
MAX_ARTIFACT_SKEW_MS = 30_000
MAX_FUTURE_SKEW_MS = 1_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

FALSE_SAFETY_FIELDS = (
    "runtime_actions",
    "dispatch_allowed",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "live_file_writes",
    "eligibility_changed",
    "acceptance_granted",
    "operational_readiness_claimed",
)


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    filename: str
    schema_filename: str
    schema_version: str
    source_timestamp_key: str | None
    ready_status: str
    parity_artifact_id: str | None


STAGES = (
    StageSpec(
        "capture_profile_doctor",
        "equipment_capture_profile_doctor.json",
        "equipment-capture-profile-doctor.schema.json",
        "ctoa.equipment-capture-profile-doctor.v1",
        None,
        "ready",
        "capture_profile_doctor",
    ),
    StageSpec(
        "observation_preview",
        "equipment_observation_preview.json",
        "equipment-observation-preview.schema.json",
        "ctoa.equipment-observation-preview.v1",
        "generated_at_unix_ms",
        "preview_ready",
        "observation_preview",
    ),
    StageSpec(
        "dependency_preflight",
        "equipment_dependency_preflight.json",
        "equipment-dependency-preflight.schema.json",
        "ctoa.equipment-dependency-preflight.v1",
        "evaluated_at_unix_ms",
        "passed",
        "dependency_preflight",
    ),
    StageSpec(
        "candidate_catalog",
        "equipment_candidate_catalog.json",
        "equipment-candidate-catalog.schema.json",
        "ctoa.equipment-candidate-catalog.v1",
        "generated_at_unix_ms",
        "catalog_ready",
        "candidate_catalog",
    ),
    StageSpec(
        "capture_profile_change_plan",
        "equipment_capture_profile_change_plan.json",
        "equipment-capture-profile-change-plan.schema.json",
        "ctoa.equipment-capture-profile-change-plan.v1",
        "generated_at_unix_ms",
        "plan_generated",
        "capture_profile_change_plan",
    ),
    StageSpec(
        "operator_readiness",
        "equipment_operator_readiness.json",
        "equipment-operator-readiness.schema.json",
        "ctoa.equipment-operator-readiness.v1",
        "generated_at_unix_ms",
        "operator_inputs_ready",
        "operator_readiness",
    ),
    StageSpec(
        "consumer_parity",
        "equipment_consumer_parity.json",
        "equipment-consumer-parity-report.schema.json",
        parity.PARITY_SCHEMA_VERSION,
        None,
        "passed",
        None,
    ),
)
STAGE_BY_ID = {stage.stage_id: stage for stage in STAGES}
STAGE_ORDER = tuple(stage.stage_id for stage in STAGES)
PARITY_SPEC_BY_ID = {spec.artifact_id: spec for spec in parity.ARTIFACT_SPECS}

PENDING_KEYS = {
    "schema_version",
    "status",
    "run_id",
    "started_at_unix_ms",
    "expected_stage_order",
    "stage_receipts",
    "eligibility_changed",
    "eligibility_state",
    "acceptance_granted",
    "operational_readiness_claimed",
    "runtime_actions",
    "dispatch_allowed",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "live_file_writes",
    "intrusive_actions_performed",
}
RECEIPT_KEYS = {
    "stage_index",
    "stage_id",
    "artifact_filename",
    "schema_version",
    "reported_status",
    "blockers",
    "artifact_sha256",
    "artifact_modified_at_unix_ms",
    "source_timestamp_unix_ms",
    "recorded_at_unix_ms",
    "no_action_valid",
    "eligibility_valid",
}


class RefreshRunError(RuntimeError):
    """A stable fail-closed finalizer error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ArtifactSnapshot:
    stage: StageSpec
    payload: dict[str, Any]
    sha256: str
    modified_at_unix_ms: int
    source_timestamp_unix_ms: int | None
    reported_status: str
    blockers: list[str]


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_run_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise RefreshRunError(
            "run_id_invalid", "run_id must be a canonical UUID"
        ) from exc
    if parsed.version != 4 or str(parsed) != value:
        raise RefreshRunError("run_id_invalid", "run_id must be a lowercase UUIDv4")
    return value


def _is_reparse(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _regular_lstat(path: Path, *, missing_code: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise RefreshRunError(
            missing_code, f"required fixed file is missing: {path.name}"
        ) from exc
    except OSError as exc:
        raise RefreshRunError(
            "file_unreadable", f"cannot inspect fixed file: {path.name}"
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
        raise RefreshRunError("reparse_rejected", f"reparse file rejected: {path.name}")
    if not stat.S_ISREG(metadata.st_mode):
        raise RefreshRunError("not_regular", f"regular file required: {path.name}")
    return metadata


def _ensure_dev_dir(dev_dir: Path) -> Path:
    candidate = dev_dir
    while True:
        try:
            candidate_metadata = candidate.lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise RefreshRunError(
                "runtime_root_unsafe", "cannot inspect the fixed runtime root chain"
            ) from exc
        else:
            if (
                stat.S_ISLNK(candidate_metadata.st_mode)
                or _is_reparse(candidate_metadata)
                or not stat.S_ISDIR(candidate_metadata.st_mode)
            ):
                raise RefreshRunError(
                    "runtime_root_unsafe",
                    f"runtime root chain must contain real directories: {candidate}",
                )
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    dev_dir.mkdir(parents=True, exist_ok=True)
    metadata = dev_dir.lstat()
    if (
        stat.S_ISLNK(metadata.st_mode)
        or _is_reparse(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
    ):
        raise RefreshRunError(
            "runtime_root_unsafe", "fixed runtime root must be a real directory"
        )
    return dev_dir


def _fixed_path(dev_dir: Path, name: str) -> Path:
    if name not in {OUTPUT.name, PENDING.name}:
        raise RefreshRunError(
            "output_path_invalid", "unexpected finalizer state filename"
        )
    path = dev_dir / name
    if path.parent.resolve(strict=False) != dev_dir.resolve(strict=False):
        raise RefreshRunError(
            "output_path_invalid", "finalizer state escaped the fixed runtime root"
        )
    return path


def _write_atomic(path: Path, payload: dict[str, Any], *, dev_dir: Path) -> None:
    _ensure_dev_dir(dev_dir)
    fixed = _fixed_path(dev_dir, path.name)
    try:
        metadata = fixed.lstat()
    except FileNotFoundError:
        metadata = None
    if metadata is not None and (
        stat.S_ISLNK(metadata.st_mode)
        or _is_reparse(metadata)
        or not stat.S_ISREG(metadata.st_mode)
    ):
        raise RefreshRunError(
            "output_target_unsafe", f"unsafe output target: {fixed.name}"
        )
    temporary = fixed.with_name(f".{fixed.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(documents.canonical_bytes(payload) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(fixed)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _remove_regular(path: Path, *, missing_ok: bool) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return
        raise RefreshRunError("state_missing", f"state file is missing: {path.name}")
    if (
        stat.S_ISLNK(metadata.st_mode)
        or _is_reparse(metadata)
        or not stat.S_ISREG(metadata.st_mode)
    ):
        raise RefreshRunError(
            "state_target_unsafe", f"unsafe state target: {path.name}"
        )
    try:
        path.unlink()
    except OSError as exc:
        raise RefreshRunError(
            "state_remove_failed", f"cannot remove state file: {path.name}"
        ) from exc


def _read_object(
    path: Path, *, missing_code: str
) -> tuple[dict[str, Any], os.stat_result]:
    before = _regular_lstat(path, missing_code=missing_code)
    document = documents.read_document(path, MAX_DOCUMENT_BYTES)
    if document.payload is None or document.status != "loaded":
        raise RefreshRunError(
            f"artifact_{document.status}",
            f"strict JSON load failed for {path.name}: {document.status}",
        )
    after = _regular_lstat(path, missing_code=missing_code)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise RefreshRunError(
            "changed_during_read", f"file changed during read: {path.name}"
        )
    return document.payload, after


def _schema_errors(schema_path: Path, payload: dict[str, Any]) -> list[str]:
    schema, _ = _read_object(schema_path, missing_code="schema_missing")
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
    except jsonschema_exceptions.SchemaError as exc:  # pragma: no cover
        raise RefreshRunError(
            "schema_invalid", f"invalid schema: {schema_path.name}"
        ) from exc
    return sorted(
        f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in validator.iter_errors(payload)
    )


def _safety_payload() -> dict[str, Any]:
    return {
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "acceptance_granted": False,
        "operational_readiness_claimed": False,
        "runtime_actions": False,
        "dispatch_allowed": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "live_file_writes": False,
        "intrusive_actions_performed": [],
    }


def _validate_safety(payload: dict[str, Any], expected: dict[str, object]) -> None:
    divergent = [name for name, value in expected.items() if payload.get(name) != value]
    if divergent:
        raise RefreshRunError(
            "no_action_divergence",
            "unsafe or divergent fields: " + ", ".join(sorted(divergent)),
        )


def _load_snapshot(stage: StageSpec, *, dev_dir: Path) -> ArtifactSnapshot:
    path = dev_dir / stage.filename
    payload, metadata = _read_object(path, missing_code="artifact_missing")
    schema_errors = _schema_errors(ROOT / "schemas" / stage.schema_filename, payload)
    if schema_errors:
        raise RefreshRunError(
            "artifact_schema_invalid",
            f"{stage.stage_id} failed schema: {schema_errors[0]}",
        )
    if payload.get("schema_version") != stage.schema_version:
        raise RefreshRunError(
            "schema_version_mismatch", f"schema mismatch for {stage.stage_id}"
        )
    reported_status = payload.get("status")
    blockers = payload.get("blockers")
    if not isinstance(reported_status, str):
        raise RefreshRunError("status_invalid", f"status missing for {stage.stage_id}")
    if not isinstance(blockers, list) or not all(
        isinstance(item, str) for item in blockers
    ):
        raise RefreshRunError(
            "blockers_invalid", f"blockers invalid for {stage.stage_id}"
        )
    if len(set(blockers)) != len(blockers):
        raise RefreshRunError(
            "blockers_invalid", f"duplicate blockers for {stage.stage_id}"
        )
    if (reported_status == stage.ready_status) != (len(blockers) == 0):
        raise RefreshRunError(
            "status_blockers_mismatch", f"status/blockers mismatch for {stage.stage_id}"
        )

    if stage.parity_artifact_id is None:
        checks = payload.get("checks")
        contracts = payload.get("consumer_contracts")
        expected_parity = {
            **_safety_payload(),
        }
        expected_parity.pop("acceptance_granted")
        _validate_safety(payload, expected_parity)
        if (
            reported_status != "passed"
            or blockers
            or payload.get("artifact_count") != 6
            or not isinstance(checks, dict)
            or not checks
            or not all(value is True for value in checks.values())
            or not isinstance(contracts, dict)
            or any(
                not isinstance(contracts.get(name), dict)
                or contracts[name].get("contract_valid") is not True
                for name in ("python", "web")
            )
        ):
            raise RefreshRunError(
                "parity_not_passed", "consumer parity is not fully passed"
            )
    else:
        parity_spec = PARITY_SPEC_BY_ID[stage.parity_artifact_id]
        _validate_safety(payload, parity_spec.no_action)
        _validate_safety(payload, parity_spec.eligibility)

    source_timestamp: int | None = None
    if stage.source_timestamp_key is not None:
        value = payload.get(stage.source_timestamp_key)
        if not _is_int(value) or value <= 0:
            raise RefreshRunError(
                "source_timestamp_invalid", f"timestamp invalid for {stage.stage_id}"
            )
        source_timestamp = value
    return ArtifactSnapshot(
        stage=stage,
        payload=payload,
        sha256=documents.canonical_sha256(payload),
        modified_at_unix_ms=metadata.st_mtime_ns // 1_000_000,
        source_timestamp_unix_ms=source_timestamp,
        reported_status=reported_status,
        blockers=list(blockers),
    )


def _assert_fresh(snapshot: ArtifactSnapshot, *, started_at: int, now_ms: int) -> None:
    modified = snapshot.modified_at_unix_ms
    if modified < started_at:
        raise RefreshRunError(
            "mixed_run_detected", f"{snapshot.stage.stage_id} predates this run"
        )
    if modified > now_ms + MAX_FUTURE_SKEW_MS:
        raise RefreshRunError(
            "artifact_future", f"{snapshot.stage.stage_id} has a future mtime"
        )
    if now_ms - modified > MAX_ARTIFACT_AGE_MS:
        raise RefreshRunError("artifact_stale", f"{snapshot.stage.stage_id} is stale")
    source_timestamp = snapshot.source_timestamp_unix_ms
    if source_timestamp is not None:
        if source_timestamp < started_at:
            raise RefreshRunError(
                "mixed_run_detected",
                f"{snapshot.stage.stage_id} source timestamp predates this run",
            )
        if source_timestamp > now_ms + MAX_FUTURE_SKEW_MS:
            raise RefreshRunError(
                "artifact_future",
                f"{snapshot.stage.stage_id} source timestamp is future",
            )
        if now_ms - source_timestamp > MAX_ARTIFACT_AGE_MS:
            raise RefreshRunError(
                "artifact_stale", f"{snapshot.stage.stage_id} source timestamp is stale"
            )


def _validate_receipt(receipt: Any, *, index: int, started_at: int) -> dict[str, Any]:
    stage = STAGES[index]
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise RefreshRunError(
            "pending_invalid", f"receipt {index + 1} has an invalid shape"
        )
    if (
        receipt.get("stage_index") != index + 1
        or receipt.get("stage_id") != stage.stage_id
    ):
        raise RefreshRunError(
            "stage_order_mismatch", f"receipt order diverged at {stage.stage_id}"
        )
    if receipt.get("artifact_filename") != stage.filename:
        raise RefreshRunError(
            "artifact_name_mismatch", f"artifact name diverged at {stage.stage_id}"
        )
    if receipt.get("schema_version") != stage.schema_version:
        raise RefreshRunError(
            "schema_version_mismatch", f"receipt schema diverged at {stage.stage_id}"
        )
    if not isinstance(receipt.get("reported_status"), str):
        raise RefreshRunError(
            "pending_invalid", f"receipt status invalid at {stage.stage_id}"
        )
    blockers = receipt.get("blockers")
    if not isinstance(blockers, list) or not all(
        isinstance(item, str) for item in blockers
    ):
        raise RefreshRunError(
            "pending_invalid", f"receipt blockers invalid at {stage.stage_id}"
        )
    if not isinstance(receipt.get("artifact_sha256"), str) or not SHA256_RE.fullmatch(
        receipt["artifact_sha256"]
    ):
        raise RefreshRunError(
            "pending_invalid", f"receipt hash invalid at {stage.stage_id}"
        )
    for name in ("artifact_modified_at_unix_ms", "recorded_at_unix_ms"):
        if not _is_int(receipt.get(name)) or receipt[name] < started_at:
            raise RefreshRunError(
                "pending_invalid", f"receipt time invalid at {stage.stage_id}"
            )
    source_timestamp = receipt.get("source_timestamp_unix_ms")
    if source_timestamp is not None and (
        not _is_int(source_timestamp) or source_timestamp < started_at
    ):
        raise RefreshRunError(
            "pending_invalid", f"source time invalid at {stage.stage_id}"
        )
    if (
        receipt.get("no_action_valid") is not True
        or receipt.get("eligibility_valid") is not True
    ):
        raise RefreshRunError(
            "pending_invalid", f"safety receipt invalid at {stage.stage_id}"
        )
    return receipt


def _validate_pending(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != PENDING_KEYS:
        raise RefreshRunError(
            "pending_invalid", "pending journal has unexpected fields"
        )
    if (
        payload.get("schema_version") != PENDING_SCHEMA_VERSION
        or payload.get("status") != "recording"
    ):
        raise RefreshRunError("pending_invalid", "pending journal header is invalid")
    _canonical_run_id(payload.get("run_id"))
    started_at = payload.get("started_at_unix_ms")
    if not _is_int(started_at) or started_at <= 0:
        raise RefreshRunError("pending_invalid", "pending start timestamp is invalid")
    if payload.get("expected_stage_order") != list(STAGE_ORDER):
        raise RefreshRunError(
            "stage_order_mismatch", "pending stage order is not canonical"
        )
    _validate_safety(payload, _safety_payload())
    receipts = payload.get("stage_receipts")
    if not isinstance(receipts, list) or len(receipts) > len(STAGES):
        raise RefreshRunError("pending_invalid", "pending receipt list is invalid")
    previous_recorded = started_at
    previous_modified = started_at
    for index, receipt in enumerate(receipts):
        validated = _validate_receipt(receipt, index=index, started_at=started_at)
        if validated["recorded_at_unix_ms"] < previous_recorded:
            raise RefreshRunError(
                "stage_order_mismatch", "receipt timestamps are not ordered"
            )
        if validated["artifact_modified_at_unix_ms"] < previous_modified:
            raise RefreshRunError(
                "stage_order_mismatch", "artifact mtimes are not ordered"
            )
        previous_recorded = validated["recorded_at_unix_ms"]
        previous_modified = validated["artifact_modified_at_unix_ms"]
    return payload


def _load_pending(dev_dir: Path) -> dict[str, Any]:
    payload, _ = _read_object(
        _fixed_path(dev_dir, PENDING.name), missing_code="pending_missing"
    )
    return _validate_pending(payload)


def _verify_receipts(
    pending: dict[str, Any], *, dev_dir: Path, now_ms: int
) -> list[ArtifactSnapshot]:
    started_at = pending["started_at_unix_ms"]
    snapshots: list[ArtifactSnapshot] = []
    for index, receipt in enumerate(pending["stage_receipts"]):
        stage = STAGES[index]
        snapshot = _load_snapshot(stage, dev_dir=dev_dir)
        _assert_fresh(snapshot, started_at=started_at, now_ms=now_ms)
        if snapshot.sha256 != receipt["artifact_sha256"]:
            raise RefreshRunError(
                "hash_mismatch",
                f"artifact hash changed after receipt: {stage.stage_id}",
            )
        if snapshot.modified_at_unix_ms != receipt["artifact_modified_at_unix_ms"]:
            raise RefreshRunError(
                "mtime_mismatch",
                f"artifact mtime changed after receipt: {stage.stage_id}",
            )
        if snapshot.source_timestamp_unix_ms != receipt["source_timestamp_unix_ms"]:
            raise RefreshRunError(
                "timestamp_mismatch", f"source timestamp changed: {stage.stage_id}"
            )
        if (
            snapshot.reported_status != receipt["reported_status"]
            or snapshot.blockers != receipt["blockers"]
        ):
            raise RefreshRunError(
                "status_blockers_mismatch", f"status/blockers changed: {stage.stage_id}"
            )
        snapshots.append(snapshot)
    return snapshots


def begin_run(
    *, dev_dir: Path, now_ms: int | None = None, run_id: str | None = None
) -> dict[str, Any]:
    dev_dir = _ensure_dev_dir(dev_dir)
    pending_path = _fixed_path(dev_dir, PENDING.name)
    try:
        pending_path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise RefreshRunError(
            "run_already_pending", "an unfinished refresh run already exists"
        )
    started_at = _now_ms() if now_ms is None else now_ms
    if not _is_int(started_at) or started_at <= 0:
        raise RefreshRunError(
            "time_invalid", "run start time must be a positive integer"
        )
    selected_run_id = _canonical_run_id(
        run_id if run_id is not None else str(uuid.uuid4())
    )
    output_path = _fixed_path(dev_dir, OUTPUT.name)
    try:
        output_metadata = output_path.lstat()
    except FileNotFoundError:
        pass
    else:
        if (
            stat.S_ISLNK(output_metadata.st_mode)
            or _is_reparse(output_metadata)
            or not stat.S_ISREG(output_metadata.st_mode)
        ):
            raise RefreshRunError(
                "output_target_unsafe",
                "existing completed envelope is not a regular file",
            )
    pending = {
        "schema_version": PENDING_SCHEMA_VERSION,
        "status": "recording",
        "run_id": selected_run_id,
        "started_at_unix_ms": started_at,
        "expected_stage_order": list(STAGE_ORDER),
        "stage_receipts": [],
        **_safety_payload(),
    }
    _write_atomic(pending_path, pending, dev_dir=dev_dir)
    return pending


def abort_run(run_id: str, *, dev_dir: Path) -> dict[str, Any]:
    """Remove only the matching pending journal and preserve completed output."""

    pending = _load_pending(dev_dir)
    canonical_run_id = _canonical_run_id(run_id)
    if canonical_run_id != pending["run_id"]:
        raise RefreshRunError(
            "run_id_mismatch", "run_id does not match the pending run"
        )
    final_output = _fixed_path(dev_dir, OUTPUT.name)
    final_output_preserved = False
    try:
        output_metadata = final_output.lstat()
    except FileNotFoundError:
        pass
    else:
        if (
            stat.S_ISLNK(output_metadata.st_mode)
            or _is_reparse(output_metadata)
            or not stat.S_ISREG(output_metadata.st_mode)
        ):
            raise RefreshRunError(
                "output_target_unsafe", "completed envelope target became unsafe"
            )
        final_output_preserved = True
    _remove_regular(_fixed_path(dev_dir, PENDING.name), missing_ok=False)
    return {
        "schema_version": ABORT_SCHEMA_VERSION,
        "status": "aborted",
        "run_id": canonical_run_id,
        "pending_removed": True,
        "final_output_preserved": final_output_preserved,
        **_safety_payload(),
    }


def record_stage(
    stage_id: str,
    run_id: str,
    *,
    dev_dir: Path,
    now_ms: int | None = None,
) -> dict[str, Any]:
    pending = _load_pending(dev_dir)
    if _canonical_run_id(run_id) != pending["run_id"]:
        raise RefreshRunError(
            "run_id_mismatch", "run_id does not match the pending run"
        )
    recorded_at = _now_ms() if now_ms is None else now_ms
    started_at = pending["started_at_unix_ms"]
    if not _is_int(recorded_at) or recorded_at < started_at:
        raise RefreshRunError("time_invalid", "stage record time predates the run")
    if recorded_at - started_at > MAX_RUN_DURATION_MS:
        raise RefreshRunError("run_stale", "refresh run exceeded its duration budget")
    receipts = pending["stage_receipts"]
    if len(receipts) >= len(STAGES):
        raise RefreshRunError("stage_overflow", "all fixed stages are already recorded")
    expected = STAGES[len(receipts)]
    if stage_id != expected.stage_id:
        raise RefreshRunError(
            "stage_order_mismatch",
            f"expected {expected.stage_id}, received {stage_id}",
        )
    _verify_receipts(pending, dev_dir=dev_dir, now_ms=recorded_at)
    snapshot = _load_snapshot(expected, dev_dir=dev_dir)
    _assert_fresh(snapshot, started_at=started_at, now_ms=recorded_at)
    if (
        receipts
        and snapshot.modified_at_unix_ms < receipts[-1]["artifact_modified_at_unix_ms"]
    ):
        raise RefreshRunError(
            "stage_order_mismatch", "new artifact mtime predates the prior stage"
        )
    receipt = {
        "stage_index": len(receipts) + 1,
        "stage_id": expected.stage_id,
        "artifact_filename": expected.filename,
        "schema_version": expected.schema_version,
        "reported_status": snapshot.reported_status,
        "blockers": snapshot.blockers,
        "artifact_sha256": snapshot.sha256,
        "artifact_modified_at_unix_ms": snapshot.modified_at_unix_ms,
        "source_timestamp_unix_ms": snapshot.source_timestamp_unix_ms,
        "recorded_at_unix_ms": recorded_at,
        "no_action_valid": True,
        "eligibility_valid": True,
    }
    pending["stage_receipts"] = [*receipts, receipt]
    _validate_pending(pending)
    _write_atomic(_fixed_path(dev_dir, PENDING.name), pending, dev_dir=dev_dir)
    return receipt


def _verify_parity_bindings(snapshots: list[ArtifactSnapshot]) -> None:
    parity_snapshot = snapshots[-1]
    parity_rows = parity_snapshot.payload.get("artifacts")
    if not isinstance(parity_rows, dict):  # schema protects this; keep fail closed
        raise RefreshRunError(
            "parity_binding_invalid", "parity artifact rows are missing"
        )
    for snapshot in snapshots[:-1]:
        artifact_id = snapshot.stage.parity_artifact_id
        row = parity_rows.get(artifact_id) if artifact_id is not None else None
        if not isinstance(row, dict) or row.get("sha256") != snapshot.sha256:
            raise RefreshRunError(
                "parity_hash_mismatch",
                f"parity hash does not bind {snapshot.stage.stage_id}",
            )
        if (
            row.get("status") != snapshot.reported_status
            or row.get("blockers") != snapshot.blockers
        ):
            raise RefreshRunError(
                "parity_status_mismatch",
                f"parity status/blockers do not bind {snapshot.stage.stage_id}",
            )
        if row.get("divergences") != []:
            raise RefreshRunError(
                "parity_divergence",
                f"parity reports divergence for {snapshot.stage.stage_id}",
            )


def finalize_run(
    run_id: str,
    *,
    dev_dir: Path,
    now_ms: int | None = None,
) -> dict[str, Any]:
    pending = _load_pending(dev_dir)
    if _canonical_run_id(run_id) != pending["run_id"]:
        raise RefreshRunError(
            "run_id_mismatch", "run_id does not match the pending run"
        )
    completed_at = _now_ms() if now_ms is None else now_ms
    started_at = pending["started_at_unix_ms"]
    if not _is_int(completed_at) or completed_at < started_at:
        raise RefreshRunError("time_invalid", "completion time predates the run")
    duration_ms = completed_at - started_at
    if duration_ms > MAX_RUN_DURATION_MS:
        raise RefreshRunError("run_stale", "refresh run exceeded its duration budget")
    if len(pending["stage_receipts"]) != len(STAGES):
        raise RefreshRunError(
            "stage_count_mismatch", "all seven ordered stages are required"
        )
    snapshots = _verify_receipts(pending, dev_dir=dev_dir, now_ms=completed_at)
    _verify_parity_bindings(snapshots)
    modified_times = [snapshot.modified_at_unix_ms for snapshot in snapshots]
    artifact_skew_ms = max(modified_times) - min(modified_times)
    if artifact_skew_ms > MAX_ARTIFACT_SKEW_MS:
        raise RefreshRunError(
            "artifact_skew_exceeded", "artifact mtime skew exceeded the fixed budget"
        )
    oldest_age_ms = max(completed_at - value for value in modified_times)
    if oldest_age_ms > MAX_ARTIFACT_AGE_MS:
        raise RefreshRunError("artifact_stale", "one or more artifacts are stale")

    receipts = pending["stage_receipts"]
    aggregate_binding = {
        "run_id": run_id,
        "started_at_unix_ms": started_at,
        "completed_at_unix_ms": completed_at,
        "stage_receipts": receipts,
    }
    readiness = snapshots[-2].payload
    all_source_stages_ready = all(
        snapshot.reported_status == snapshot.stage.ready_status
        for snapshot in snapshots[:-1]
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "run_id": run_id,
        "started_at_unix_ms": started_at,
        "completed_at_unix_ms": completed_at,
        "duration_ms": duration_ms,
        "stage_count": len(STAGES),
        "stage_order": list(STAGE_ORDER),
        "stage_receipts": receipts,
        "artifact_hashes": {
            snapshot.stage.stage_id: snapshot.sha256 for snapshot in snapshots
        },
        "source_statuses": {
            snapshot.stage.stage_id: snapshot.reported_status for snapshot in snapshots
        },
        "source_blockers": {
            snapshot.stage.stage_id: snapshot.blockers for snapshot in snapshots
        },
        "canonical_aggregate_sha256": documents.canonical_sha256(aggregate_binding),
        "artifact_skew_ms": artifact_skew_ms,
        "max_artifact_skew_ms": MAX_ARTIFACT_SKEW_MS,
        "oldest_artifact_age_ms": oldest_age_ms,
        "freshness_max_age_ms": MAX_ARTIFACT_AGE_MS,
        "hashes_verified": True,
        "schemas_verified": True,
        "no_action_verified": True,
        "eligibility_verified": True,
        "mixed_run_detected": False,
        "stale_artifact_detected": False,
        "hash_mismatch_detected": False,
        "all_source_stages_ready": all_source_stages_ready,
        "operator_inputs_ready_observed": readiness.get("operator_inputs_ready")
        is True,
        **_safety_payload(),
        "live_safety": (
            "EquipmentOperatorRefreshRun binds fixed repo-only P10 artifacts and their parity receipt; "
            "it does not launch or control OTClient, accept evidence, change eligibility, dispatch "
            "actions, or write live-client files."
        ),
    }
    report_errors = _schema_errors(REPORT_SCHEMA, report)
    if report_errors:
        raise RefreshRunError("report_schema_invalid", report_errors[0])
    _write_atomic(_fixed_path(dev_dir, OUTPUT.name), report, dev_dir=dev_dir)
    _remove_regular(_fixed_path(dev_dir, PENDING.name), missing_ok=False)
    return report


def _error_payload(error: RefreshRunError) -> dict[str, Any]:
    return {
        "schema_version": ERROR_SCHEMA_VERSION,
        "status": "blocked",
        "error_code": error.code,
        "message": str(error),
        **_safety_payload(),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--begin", action="store_true")
    action.add_argument("--record-stage", choices=STAGE_ORDER)
    action.add_argument("--finalize", action="store_true")
    action.add_argument("--abort", action="store_true")
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.begin:
            if args.run_id is not None:
                raise RefreshRunError(
                    "arguments_invalid", "--begin generates its own run_id"
                )
            result = begin_run(dev_dir=DEV_DIR)
        elif args.record_stage is not None:
            if args.run_id is None:
                raise RefreshRunError(
                    "arguments_invalid", "--record-stage requires --run-id"
                )
            receipt = record_stage(args.record_stage, args.run_id, dev_dir=DEV_DIR)
            result = {
                "schema_version": PENDING_SCHEMA_VERSION,
                "status": "stage_recorded",
                "run_id": args.run_id,
                "stage_receipt": receipt,
                **_safety_payload(),
            }
        elif args.finalize:
            if args.run_id is None:
                raise RefreshRunError(
                    "arguments_invalid", "--finalize requires --run-id"
                )
            result = finalize_run(args.run_id, dev_dir=DEV_DIR)
        else:
            if args.run_id is None:
                raise RefreshRunError("arguments_invalid", "--abort requires --run-id")
            result = abort_run(args.run_id, dev_dir=DEV_DIR)
    except RefreshRunError as exc:
        print(json.dumps(_error_payload(exc), ensure_ascii=True, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
