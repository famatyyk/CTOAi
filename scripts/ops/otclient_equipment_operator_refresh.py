#!/usr/bin/env python3
"""Refresh the fixed P10 operator evidence chain without runtime actions.

The orchestrator invokes only the seven fixed repo scripts declared below.  It
does not accept paths, item identifiers, confirmations, acceptance, replay, or
client-control arguments.  Producer stages may persist a coherent ``blocked``
report; the final consumer-parity stage must pass without ``--allow-blocked``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat

# Fixed repo scripts only; every subprocess call uses shell=False.
import subprocess  # nosec B404
import sys
from typing import Any, Callable

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_operator_refresh_run as refresh_envelope
else:  # pragma: no cover - direct script execution
    try:
        from scripts.ops import otclient_conditions_shadow_replay as documents
        from scripts.ops import (
            otclient_equipment_operator_refresh_run as refresh_envelope,
        )
    except ImportError:
        import otclient_conditions_shadow_replay as documents
        import otclient_equipment_operator_refresh_run as refresh_envelope


ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = ROOT / "scripts" / "ops"
DEFAULT_DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
SUMMARY_SCHEMA = "ctoa.equipment-operator-refresh-summary.v1"
PARITY_SCHEMA = "ctoa.equipment-consumer-parity.v1"
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
STAGE_TIMEOUT_SECONDS = 60

PARITY_CHECKS = {
    "schemas_valid",
    "status_parity",
    "blockers_parity",
    "hash_parity",
    "no_action_parity",
    "eligibility_parity",
    "consumer_contracts_valid",
}
FALSE_ACTION_FIELDS = (
    "runtime_actions",
    "dispatch_allowed",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "live_file_writes",
)
FORBIDDEN_ARGUMENTS = {
    "--init-local",
    "--equipped-item-id",
    "--candidate-item-id",
    "--candidate-container-id",
    "--candidate-slot-index",
    "--confirm",
    "--allow-blocked",  # parity may never receive this flag
    "--no-write",
}
FORBIDDEN_SCRIPT_FRAGMENTS = (
    "acceptance",
    "shadow_replay",
    "shadow_snapshot",
    "headless_evidence",
    "client_reporter",
)


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    script_filename: str
    arguments: tuple[str, ...]
    output_filename: str
    schema_version: str
    allowed_statuses: frozenset[str]


STAGES = (
    StageSpec(
        "capture_profile_doctor",
        "otclient_equipment_capture_profile_doctor.py",
        ("--allow-blocked",),
        "equipment_capture_profile_doctor.json",
        "ctoa.equipment-capture-profile-doctor.v1",
        frozenset({"ready", "blocked"}),
    ),
    StageSpec(
        "observation_preview",
        "otclient_equipment_observation_preview.py",
        ("--allow-blocked",),
        "equipment_observation_preview.json",
        "ctoa.equipment-observation-preview.v1",
        frozenset({"preview_ready", "blocked"}),
    ),
    StageSpec(
        "dependency_preflight",
        "otclient_equipment_dependency_preflight.py",
        ("--allow-blocked",),
        "equipment_dependency_preflight.json",
        "ctoa.equipment-dependency-preflight.v1",
        frozenset({"passed", "blocked"}),
    ),
    StageSpec(
        "candidate_catalog",
        "otclient_equipment_candidate_catalog.py",
        ("--allow-blocked",),
        "equipment_candidate_catalog.json",
        "ctoa.equipment-candidate-catalog.v1",
        frozenset({"catalog_ready", "blocked"}),
    ),
    StageSpec(
        "capture_profile_change_plan",
        "otclient_equipment_capture_profile_change_plan.py",
        ("--allow-blocked",),
        "equipment_capture_profile_change_plan.json",
        "ctoa.equipment-capture-profile-change-plan.v1",
        frozenset({"plan_generated", "blocked"}),
    ),
    StageSpec(
        "operator_readiness",
        "otclient_equipment_operator_readiness.py",
        ("--allow-blocked",),
        "equipment_operator_readiness.json",
        "ctoa.equipment-operator-readiness.v1",
        frozenset({"operator_inputs_ready", "blocked"}),
    ),
    StageSpec(
        "consumer_parity",
        "otclient_equipment_consumer_parity.py",
        (),
        "equipment_consumer_parity.json",
        PARITY_SCHEMA,
        frozenset({"passed"}),
    ),
)

RunCommand = Callable[..., subprocess.CompletedProcess[str]]


def _has_reparse_attribute(metadata: os.stat_result) -> bool:
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    return bool(int(getattr(metadata, "st_file_attributes", 0)) & reparse)


def _safe_regular_file(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and not _has_reparse_attribute(metadata)
    )


def _unsafe_existing_output(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return bool(
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _has_reparse_attribute(metadata)
    )


def _unsafe_existing_directory(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return bool(
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or _has_reparse_attribute(metadata)
    )


def _artifact_token(path: Path) -> tuple[object, ...] | None:
    if not _safe_regular_file(path):
        return None
    document = documents.read_document(path, MAX_ARTIFACT_BYTES)
    try:
        metadata = path.stat()
    except OSError:
        return None
    return (
        getattr(metadata, "st_dev", 0),
        getattr(metadata, "st_ino", 0),
        metadata.st_size,
        metadata.st_mtime_ns,
        getattr(metadata, "st_ctime_ns", 0),
        document.status,
        document.sha256,
    )


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def _parity_contract_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    checks = payload.get("checks")
    if payload.get("schema_version") != PARITY_SCHEMA:
        errors.append("parity_schema")
    if payload.get("status") != "passed":
        errors.append("parity_status")
    if payload.get("artifact_count") != 6:
        errors.append("parity_artifact_count")
    if payload.get("blockers") != []:
        errors.append("parity_blockers")
    if not (
        isinstance(checks, dict)
        and set(checks) == PARITY_CHECKS
        and all(checks.get(name) is True for name in PARITY_CHECKS)
    ):
        errors.append("parity_checks")
    if payload.get("eligibility_changed") is not False:
        errors.append("parity_eligibility_changed")
    if payload.get("eligibility_state") != "unchanged":
        errors.append("parity_eligibility_state")
    if payload.get("operational_readiness_claimed") is not False:
        errors.append("parity_readiness_claim")
    if any(payload.get(name) is not False for name in FALSE_ACTION_FIELDS):
        errors.append("parity_no_action")
    if payload.get("intrusive_actions_performed") != []:
        errors.append("parity_intrusive_actions")
    return errors


def _validate_stage_contracts() -> None:
    if tuple(stage.stage_id for stage in STAGES) != (
        "capture_profile_doctor",
        "observation_preview",
        "dependency_preflight",
        "candidate_catalog",
        "capture_profile_change_plan",
        "operator_readiness",
        "consumer_parity",
    ):
        raise RuntimeError("P10 refresh stage order changed")
    for stage in STAGES:
        lowered_script = stage.script_filename.lower()
        if any(fragment in lowered_script for fragment in FORBIDDEN_SCRIPT_FRAGMENTS):
            raise RuntimeError(f"forbidden P10 refresh script: {stage.script_filename}")
        if stage.stage_id == "consumer_parity":
            if stage.arguments:
                raise RuntimeError("consumer parity must run without arguments")
            continue
        if stage.arguments != ("--allow-blocked",):
            raise RuntimeError(
                f"producer {stage.stage_id} must use only --allow-blocked"
            )
        if any(
            argument in FORBIDDEN_ARGUMENTS - {"--allow-blocked"}
            for argument in stage.arguments
        ):
            raise RuntimeError(f"forbidden producer argument: {stage.stage_id}")


def _run_stage(
    stage: StageSpec,
    *,
    dev_dir: Path,
    run_command: RunCommand,
) -> dict[str, Any]:
    script_path = OPS_DIR / stage.script_filename
    output_path = dev_dir / stage.output_filename
    result: dict[str, Any] = {
        "stage_id": stage.stage_id,
        "script": _display_path(script_path),
        "arguments": list(stage.arguments),
        "output": _display_path(output_path),
        "allow_blocked": stage.arguments == ("--allow-blocked",),
        "exit_code": None,
        "process_ok": False,
        "artifact_load_status": "missing",
        "artifact_schema_version": None,
        "artifact_status": None,
        "artifact_sha256": None,
        "artifact_blocker_count": None,
        "artifact_refreshed": False,
        "ok": False,
        "blockers": [],
    }
    blockers: list[str] = result["blockers"]
    if not _safe_regular_file(script_path):
        blockers.append("fixed_script_missing_or_unsafe")
        return result
    if _unsafe_existing_directory(dev_dir.parent) or _unsafe_existing_directory(
        dev_dir
    ):
        blockers.append("fixed_output_parent_unsafe")
        return result
    if _unsafe_existing_output(output_path):
        blockers.append("fixed_output_path_unsafe")
        return result

    before = _artifact_token(output_path)
    command = [sys.executable, str(script_path), *stage.arguments]
    environment = os.environ.copy()
    environment["CTOA_OPERATOR_MODE"] = "background_no_screen"
    try:
        completed = run_command(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=STAGE_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        blockers.append("stage_timeout")
        return result
    except OSError:
        blockers.append("stage_process_error")
        return result

    result["exit_code"] = completed.returncode
    result["process_ok"] = completed.returncode == 0
    if completed.returncode != 0:
        blockers.append(f"stage_exit_{completed.returncode}")

    document = documents.read_document(output_path, MAX_ARTIFACT_BYTES)
    payload = document.payload if isinstance(document.payload, dict) else {}
    source_blockers = payload.get("blockers")
    artifact_blocker_count = (
        len(source_blockers)
        if isinstance(source_blockers, list)
        and all(isinstance(item, str) for item in source_blockers)
        else None
    )
    after = _artifact_token(output_path)
    result.update(
        artifact_load_status=document.status,
        artifact_schema_version=(
            payload.get("schema_version")
            if isinstance(payload.get("schema_version"), str)
            else None
        ),
        artifact_status=(
            payload.get("status") if isinstance(payload.get("status"), str) else None
        ),
        artifact_sha256=document.sha256 if document.status == "loaded" else None,
        artifact_blocker_count=artifact_blocker_count,
        artifact_refreshed=after is not None and after != before,
    )
    if document.status != "loaded":
        blockers.append(f"artifact_{document.status}")
    if payload.get("schema_version") != stage.schema_version:
        blockers.append("artifact_schema_invalid")
    if payload.get("status") not in stage.allowed_statuses:
        blockers.append("artifact_status_invalid")
    if after is None or after == before:
        blockers.append("artifact_not_refreshed")
    if stage.stage_id == "consumer_parity" and document.status == "loaded":
        blockers.extend(_parity_contract_errors(payload))
    result["blockers"] = list(dict.fromkeys(blockers))
    result["ok"] = not result["blockers"]
    return result


def run_refresh(
    *,
    run_command: RunCommand = subprocess.run,
    envelope_backend: Any = refresh_envelope,
) -> dict[str, Any]:
    _validate_stage_contracts()
    dev_dir = DEFAULT_DEV_DIR
    stage_results: list[dict[str, Any]] = []
    blockers: list[str] = []
    failed_stage: str | None = None
    envelope_run_id: str | None = None
    envelope_report: dict[str, Any] | None = None
    envelope_error: str | None = None
    envelope_cleanup_error: str | None = None
    envelope_aborted = False
    if _unsafe_existing_directory(dev_dir.parent) or _unsafe_existing_directory(
        dev_dir
    ):
        envelope_error = "runtime_root_unsafe"
        blockers.append("run_envelope:runtime_root_unsafe")
    else:
        try:
            pending = envelope_backend.begin_run(dev_dir=dev_dir)
            candidate_run_id = (
                pending.get("run_id") if isinstance(pending, dict) else None
            )
            if not isinstance(candidate_run_id, str):
                raise RuntimeError("run envelope did not return a run_id")
            envelope_run_id = candidate_run_id
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            envelope_error = getattr(exc, "code", "begin_failed")
            blockers.append(f"run_envelope:{envelope_error}")

    if envelope_run_id is not None:
        for stage in STAGES:
            stage_result = _run_stage(
                stage,
                dev_dir=dev_dir,
                run_command=run_command,
            )
            stage_results.append(stage_result)
            if not stage_result["ok"]:
                failed_stage = stage.stage_id
                blockers.append(f"stage_failed:{stage.stage_id}")
                blockers.extend(
                    f"{stage.stage_id}:{item}" for item in stage_result["blockers"]
                )
                break
            try:
                envelope_backend.record_stage(
                    stage.stage_id,
                    envelope_run_id,
                    dev_dir=dev_dir,
                )
            except (
                AttributeError,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as exc:
                envelope_error = getattr(exc, "code", "record_failed")
                failed_stage = stage.stage_id
                stage_result["ok"] = False
                stage_result["blockers"] = [
                    *stage_result["blockers"],
                    f"run_envelope:{envelope_error}",
                ]
                blockers.extend(
                    (
                        f"stage_failed:{stage.stage_id}",
                        f"{stage.stage_id}:run_envelope:{envelope_error}",
                    )
                )
                break

    parity = next(
        (result for result in stage_results if result["stage_id"] == "consumer_parity"),
        None,
    )
    parity_passed = bool(
        parity and parity["ok"] is True and parity["artifact_status"] == "passed"
    )
    readiness = next(
        (
            result
            for result in stage_results
            if result["stage_id"] == "operator_readiness"
        ),
        None,
    )
    operator_inputs_ready = bool(
        readiness
        and readiness["ok"] is True
        and readiness["artifact_status"] == "operator_inputs_ready"
    )
    if (
        envelope_run_id is not None
        and len(stage_results) == len(STAGES)
        and parity_passed
        and not blockers
    ):
        try:
            envelope_report = envelope_backend.finalize_run(
                envelope_run_id,
                dev_dir=dev_dir,
            )
            if envelope_report.get("status") != "completed":
                raise RuntimeError("run envelope did not complete")
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            envelope_error = getattr(exc, "code", "finalize_failed")
            blockers.append(f"run_envelope:{envelope_error}")
    envelope_completed = bool(
        envelope_report is not None and envelope_report.get("status") == "completed"
    )
    if envelope_run_id is not None and not envelope_completed:
        try:
            abort_report = envelope_backend.abort_run(
                envelope_run_id,
                dev_dir=dev_dir,
            )
            if (
                not isinstance(abort_report, dict)
                or abort_report.get("status") != "aborted"
            ):
                raise RuntimeError("run envelope abort did not complete")
            envelope_aborted = True
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            envelope_cleanup_error = getattr(exc, "code", "abort_failed")
            blockers.append(f"run_envelope_cleanup:{envelope_cleanup_error}")
    passed = (
        len(stage_results) == len(STAGES)
        and parity_passed
        and envelope_completed
        and not blockers
    )
    return {
        "schema_version": SUMMARY_SCHEMA,
        "status": "passed" if passed else "blocked",
        "stage_count": len(stage_results),
        "expected_stage_count": len(STAGES),
        "failed_stage": failed_stage,
        "parity_passed": parity_passed,
        "parity_sha256": parity.get("artifact_sha256") if parity else None,
        "run_id": envelope_run_id,
        "run_envelope_status": (
            "completed"
            if envelope_completed
            else "aborted"
            if envelope_aborted
            else "blocked"
            if envelope_error is not None or envelope_cleanup_error is not None
            else "incomplete"
        ),
        "run_envelope_path": _display_path(dev_dir / refresh_envelope.OUTPUT.name),
        "run_envelope_sha256": (
            documents.canonical_sha256(envelope_report)
            if envelope_report is not None
            else None
        ),
        "run_envelope_error": envelope_error,
        "run_envelope_cleanup_error": envelope_cleanup_error,
        "operator_inputs_ready": operator_inputs_ready,
        "stages": stage_results,
        "blockers": list(dict.fromkeys(blockers)),
        "repo_report_writes_only": True,
        "local_profile_write_performed": False,
        "client_process_actions": False,
        "explicit_identifiers_accepted": False,
        "operator_confirmation_accepted": False,
        "acceptance_granted": False,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        **{name: False for name in FALSE_ACTION_FIELDS},
        "intrusive_actions_performed": [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(argv)
    summary = run_refresh()
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
