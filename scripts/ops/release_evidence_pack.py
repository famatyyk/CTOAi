#!/usr/bin/env python3
"""Assemble evidence packs from backlog sync and runtime artifacts.

This module keeps two related surfaces together:
- backlog release evidence generation for sprint state sync
- compact runtime evidence pack generation for Control Center sign-off flows
"""

from __future__ import annotations

import argparse
import json
import os
import datetime as dt
import stat
from pathlib import Path
from typing import Any


DEFAULT_RELEASES_DIR = Path("releases/evidence")
DEFAULT_JSON_OUT = Path("runtime/evidence/latest.json")
DEFAULT_MD_OUT = Path("runtime/evidence/latest.md")
DEFAULT_HELPER_DEV_DIR = Path("runtime/solteria_helper_dev")
DEFAULT_ENGINE_BRAIN_OPERATOR_BRIEF_PATH = Path("AI/generated/P7_OPERATOR_BRIEF.json")
MAX_EVIDENCE_JSON_BYTES = 1024 * 1024
MAX_ACTION_AUDIT_BYTES = 1024 * 1024
BACKGROUND_STATUS_SCHEMA = "ctoa.otclient-headless-status.v1"
BACKGROUND_STATUS_MODE = "background_no_screen"
BACKGROUND_STATUS_MAX_AGE_SECONDS = 30
BACKGROUND_STATUS_VALUES = {
    "ready",
    "blocked",
    "idle",
    "waiting_for_passive_heartbeat",
    "observation_pending",
}
BACKGROUND_INTEGRITY_STATUS_VALUES = {"passed", "failed", "untrusted_pin"}
BACKGROUND_CAPABILITY_STATUS_VALUES = {
    "fresh",
    "stale",
    "missing",
    "unsafe_runtime_claim",
    "schema_mismatch",
    "invalid_contract",
    "version_mismatch",
    "invalid_heartbeat",
    "heartbeat_before_process",
    "heartbeat_offline",
    "game_offline",
    "malformed",
    "oversize",
    "symlink_rejected",
    "not_regular",
    "not_object",
    "changed_during_open",
    "unreadable",
    "explicit_path_mismatch",
}
BACKGROUND_BLOCKER_VALUES = {
    "live_manifest_pin_untrusted",
    "live_manifest_parity_failed",
    "live_files_changed_or_unverifiable",
    "active_client_process_count_invalid",
    "active_client_process_start_invalid",
    "current_session_lua_exception",
    "client_process_changed_during_observation",
    "screenshot_count_changed_during_observation",
    *(f"capability_{status}" for status in BACKGROUND_CAPABILITY_STATUS_VALUES),
}


def _now_iso() -> str:
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _safe_filename(value: str) -> str:
    text = str(value or "").strip().lower()
    return (
        "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text)
        or "unknown"
    )


def build_release_evidence_pack(
    *,
    backlog_id: str,
    backlog_path: Path,
    state_path: Path,
    released_count: int,
    total_tasks: int,
    reason: str,
    mode: str = "wave1",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    completion_rate = (released_count / total_tasks) if total_tasks else 0.0
    pack_notes = list(notes or [])
    if not pack_notes and released_count == total_tasks:
        pack_notes.append("All backlog tasks synchronized to RELEASED.")

    return {
        "schema_version": "ctoa.release_evidence_pack.v1",
        "generated_at": _now_iso(),
        "backlog_id": backlog_id,
        "mode": mode,
        "reason": reason,
        "release": {
            "released_count": released_count,
            "total_tasks": total_tasks,
            "completion_rate": round(completion_rate, 4),
            "status": "complete" if released_count >= total_tasks else "partial",
        },
        "paths": {
            "backlog": str(backlog_path),
            "state": str(state_path),
        },
        "notes": pack_notes,
    }


def write_release_evidence_pack(
    output_dir: Path, pack: dict[str, Any]
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    backlog_id = _safe_filename(str(pack.get("backlog_id", "unknown")))
    json_path = output_dir / f"{backlog_id}-release-evidence-pack.json"
    md_path = output_dir / f"{backlog_id}-release-evidence-pack.md"

    json_path.write_text(
        json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    release = pack.get("release", {}) if isinstance(pack.get("release"), dict) else {}
    release_count = release.get("released_count", 0)
    total_tasks = release.get("total_tasks", 0)
    completion_rate = release.get("completion_rate", 0.0)
    notes = pack.get("notes", []) if isinstance(pack.get("notes"), list) else []

    md_lines = [
        f"# Release Evidence Pack: {pack.get('backlog_id', 'unknown')}",
        "",
        f"- generated_at: {pack.get('generated_at', '')}",
        f"- mode: {pack.get('mode', 'wave1')}",
        f"- reason: {pack.get('reason', '')}",
        f"- release_count: {release_count}/{total_tasks}",
        f"- completion_rate: {completion_rate}",
        f"- backlog_path: {pack.get('paths', {}).get('backlog', '')}",
        f"- state_path: {pack.get('paths', {}).get('state', '')}",
        "",
        "## Notes",
    ]
    if notes:
        md_lines.extend([f"- {note}" for note in notes])
    else:
        md_lines.append("- none")
    md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return json_path, md_path


def _configured_path(env_name: str, fallback: str) -> Path:
    value = os.getenv(env_name, "").strip()
    return Path(value) if value else Path(fallback)


def _safe_file_stat(path: Path) -> os.stat_result | None:
    try:
        file_stat = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(file_stat.st_mode):
        return None
    return file_stat


def _safe_dir_stat(path: Path) -> os.stat_result | None:
    try:
        dir_stat = path.lstat()
    except OSError:
        return None
    if not stat.S_ISDIR(dir_stat.st_mode):
        return None
    return dir_stat


def _read_text_bounded(path: Path, max_bytes: int) -> str:
    file_stat = _safe_file_stat(path)
    if file_stat is None:
        raise FileNotFoundError(path)
    if file_stat.st_size > max_bytes:
        raise ValueError(f"{path} is too large to read safely")
    with path.open("rb") as handle:
        opened_stat = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"{path} is not a regular file")
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"{path} is too large to read safely")
    return raw.decode("utf-8-sig")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(_read_text_bounded(path, MAX_EVIDENCE_JSON_BYTES))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"{path} must contain a JSON object")


def _read_json_or_none(path: Path) -> dict[str, Any] | None:
    if _safe_file_stat(path) is None:
        return None
    try:
        return _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _safe_nonnegative_int(value: Any) -> tuple[int, bool]:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value, True
    return 0, False


def _parse_utc_timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value or len(value) > 64:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.UTC)


def _background_status_summary(
    payload: dict[str, Any] | None,
    path: Path,
    *,
    now: dt.datetime | None = None,
    artifact_present: bool | None = None,
) -> dict[str, Any]:
    observed_at = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    present = payload is not None if artifact_present is None else artifact_present
    data = payload if isinstance(payload, dict) else {}
    integrity = data.get("integrity") if isinstance(data.get("integrity"), dict) else {}
    capability = (
        data.get("capability") if isinstance(data.get("capability"), dict) else {}
    )
    log = data.get("log") if isinstance(data.get("log"), dict) else {}

    raw_blockers = data.get("blockers")
    blockers_valid = (
        isinstance(raw_blockers, list)
        and len(raw_blockers) <= 16
        and all(item in BACKGROUND_BLOCKER_VALUES for item in raw_blockers)
    )
    blockers = list(raw_blockers[:8]) if blockers_valid else []

    matched_file_count, matched_valid = _safe_nonnegative_int(
        integrity.get("matched_file_count")
    )
    manifest_file_count, manifest_valid = _safe_nonnegative_int(
        integrity.get("manifest_file_count")
    )
    mutable_drift_count, mutable_valid = _safe_nonnegative_int(
        integrity.get("mutable_drift_count")
    )

    generated_at_raw = data.get("generated_at_utc")
    generated_at = _parse_utc_timestamp(generated_at_raw)
    age_seconds = (
        (observed_at - generated_at).total_seconds()
        if generated_at is not None
        else None
    )
    timestamp_fresh = bool(
        age_seconds is not None
        and 0 <= age_seconds <= BACKGROUND_STATUS_MAX_AGE_SECONDS
    )

    reported_status = data.get("status")
    mode = data.get("mode")
    process_state_value = data.get("process_state")
    runtime_state_value = capability.get("runtime_state") or log.get("runtime_state")
    integrity_status_value = integrity.get("status")
    capability_status_value = capability.get("status")
    contract_errors: list[str] = []
    checks = (
        ("schema_version", data.get("schema_version") == BACKGROUND_STATUS_SCHEMA),
        ("mode", mode == BACKGROUND_STATUS_MODE),
        ("status", reported_status in BACKGROUND_STATUS_VALUES),
        ("advisory_only", data.get("advisory_only") is True),
        (
            "safe_to_run_while_playing",
            data.get("safe_to_run_while_playing") is True,
        ),
        ("promotion_allowed", data.get("promotion_allowed") is False),
        ("dispatch_allowed", data.get("dispatch_allowed") is False),
        ("runtime_actions", data.get("runtime_actions") is False),
        ("blockers", blockers_valid),
        ("integrity", isinstance(data.get("integrity"), dict)),
        ("capability", isinstance(data.get("capability"), dict)),
        (
            "process_state",
            process_state_value in {"running", "not_running", "ambiguous"},
        ),
        (
            "runtime_state",
            runtime_state_value in {"armed", "disarmed", "unknown"},
        ),
        (
            "integrity_status",
            integrity_status_value in BACKGROUND_INTEGRITY_STATUS_VALUES,
        ),
        (
            "capability_status",
            capability_status_value in BACKGROUND_CAPABILITY_STATUS_VALUES,
        ),
        ("capability_fresh", isinstance(capability.get("fresh"), bool)),
        ("capability_runtime_actions", capability.get("runtime_actions") is False),
        (
            "capability_runtime_core_actions",
            capability.get("runtime_core_actions") is False,
        ),
        ("matched_file_count", matched_valid),
        ("manifest_file_count", manifest_valid),
        ("mutable_drift_count", mutable_valid),
        ("generated_at_utc", generated_at is not None),
    )
    contract_errors.extend(name for name, passed in checks if not passed)
    contract_valid = payload is not None and not contract_errors
    fresh = contract_valid and timestamp_fresh
    capability_fresh = capability.get("fresh") is True
    integrity_status = (
        integrity_status_value
        if integrity_status_value in BACKGROUND_INTEGRITY_STATUS_VALUES
        else "invalid"
    )
    capability_status = (
        capability_status_value
        if capability_status_value in BACKGROUND_CAPABILITY_STATUS_VALUES
        else "invalid"
    )
    ready = bool(
        contract_valid
        and fresh
        and reported_status == "ready"
        and integrity_status == "passed"
        and capability_status == "fresh"
        and capability_fresh
        and not blockers
    )

    if not present:
        effective_status = "missing"
    elif not contract_valid:
        effective_status = "blocked"
    elif not fresh:
        effective_status = "stale"
    elif ready:
        effective_status = "ready"
    elif reported_status == "ready":
        effective_status = "blocked"
    else:
        effective_status = str(reported_status)

    runtime_state = (
        runtime_state_value
        if runtime_state_value in {"armed", "disarmed"}
        else "unknown"
    )
    process_state = (
        process_state_value
        if process_state_value in {"running", "not_running", "ambiguous"}
        else "unknown"
    )

    return {
        "status": effective_status,
        "reported_status": (
            reported_status
            if reported_status in BACKGROUND_STATUS_VALUES
            else "invalid"
        ),
        "mode": mode if mode == BACKGROUND_STATUS_MODE else "invalid",
        "generated_at_utc": (
            generated_at.isoformat(timespec="seconds") if generated_at else ""
        ),
        "max_age_seconds": BACKGROUND_STATUS_MAX_AGE_SECONDS,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "fresh": fresh,
        "contract_valid": contract_valid,
        "contract_errors": contract_errors,
        "advisory_only": data.get("advisory_only") is True,
        "safe_to_run_while_playing": data.get("safe_to_run_while_playing") is True,
        "promotion_allowed": data.get("promotion_allowed") is True,
        "dispatch_allowed": data.get("dispatch_allowed") is True,
        "runtime_actions": data.get("runtime_actions") is True,
        "process_state": process_state,
        "integrity_status": integrity_status,
        "matched_file_count": matched_file_count,
        "manifest_file_count": manifest_file_count,
        "mutable_drift_count": mutable_drift_count,
        "capability_status": capability_status,
        "capability_fresh": capability_fresh,
        "runtime_state": runtime_state,
        "blockers": blockers,
        "path": str(path).replace("\\", "/"),
    }


def _count_jsonl_records(path: Path) -> int:
    file_stat = _safe_file_stat(path)
    if file_stat is None or file_stat.st_size <= 0:
        return 0
    requested_bytes = min(file_stat.st_size, MAX_ACTION_AUDIT_BYTES)
    start = max(0, file_stat.st_size - requested_bytes)
    try:
        with path.open("rb") as handle:
            opened_stat = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_stat.st_mode):
                return 0
            handle.seek(start)
            raw = handle.read(requested_bytes)
    except OSError:
        return 0
    text = raw.decode("utf-8-sig", errors="replace")
    if start > 0:
        _, _, text = text.partition("\n")
    count = 0
    for line in text.splitlines():
        if line.strip():
            count += 1
    return count


def _find_latest_markdown(releases_dir: Path) -> dict[str, str] | None:
    latest: tuple[float, Path] | None = None
    if _safe_dir_stat(releases_dir) is None:
        return None

    for path in releases_dir.rglob("*.md"):
        file_stat = _safe_file_stat(path)
        if file_stat is None:
            continue
        modified = file_stat.st_mtime
        if latest is None or modified > latest[0]:
            latest = (modified, path)

    if latest is None:
        return None

    modified_at = dt.datetime.fromtimestamp(latest[0], tz=dt.UTC).isoformat(
        timespec="seconds"
    )
    return {"path": str(latest[1]).replace("\\", "/"), "modified_at": modified_at}


def _count_markdown_files(releases_dir: Path) -> int:
    if _safe_dir_stat(releases_dir) is None:
        return 0
    return sum(
        1 for path in releases_dir.rglob("*.md") if _safe_file_stat(path) is not None
    )


def _helper_status(helper_dev_dir: Path) -> dict[str, Any]:
    manifest_path = helper_dev_dir / "manifest.json"
    validation_path = helper_dev_dir / "validation.json"
    readiness_path = helper_dev_dir / "release_readiness.json"
    gate_path = helper_dev_dir / "release_gate.json"
    goal_status_path = helper_dev_dir / "goal_status.json"
    module_contract_path = helper_dev_dir / "module_contract.json"
    module_audit_path = helper_dev_dir / "module_audit.json"
    smoke_preflight_path = helper_dev_dir / "smoke_preflight.json"
    smoke_status_path = helper_dev_dir / "smoke_status.json"
    live_promotion_path = helper_dev_dir / "live_promotion.json"
    background_status_path = helper_dev_dir / "background_status.json"

    helper_dir_safe = _safe_dir_stat(helper_dev_dir) is not None
    manifest = _read_json_or_none(manifest_path) if helper_dir_safe else None
    validation = _read_json_or_none(validation_path) if helper_dir_safe else None
    readiness = _read_json_or_none(readiness_path) if helper_dir_safe else None
    gate = _read_json_or_none(gate_path) if helper_dir_safe else None
    goal_status = _read_json_or_none(goal_status_path) if helper_dir_safe else None
    module_contract = (
        _read_json_or_none(module_contract_path) if helper_dir_safe else None
    )
    module_audit = _read_json_or_none(module_audit_path) if helper_dir_safe else None
    smoke_preflight = (
        _read_json_or_none(smoke_preflight_path) if helper_dir_safe else None
    )
    smoke_status = _read_json_or_none(smoke_status_path) if helper_dir_safe else None
    live_promotion = (
        _read_json_or_none(live_promotion_path) if helper_dir_safe else None
    )
    background_status = (
        _read_json_or_none(background_status_path) if helper_dir_safe else None
    )
    background_summary = _background_status_summary(
        background_status,
        background_status_path,
        artifact_present=_safe_file_stat(background_status_path) is not None,
    )

    gates = gate.get("gates", []) if gate else []
    live_approval_gate = next(
        (
            item
            for item in gates
            if isinstance(item, dict) and str(item.get("name", "")) == "live_approval"
        ),
        None,
    )
    live_approval_evidence = str((live_approval_gate or {}).get("evidence", ""))
    live_promotion_has_approval = (live_promotion or {}).get(
        "approval_switch"
    ) == "ApproveLiveDeploy"
    blockers = [
        f"{item.get('name', 'gate')}: {item.get('reason') or item.get('status') or 'pending'}"
        for item in gates
        if isinstance(item, dict) and item.get("status") != "passed"
    ]
    if not blockers and goal_status:
        blockers = [str(item) for item in goal_status.get("blockers", [])]
    sandbox_smoke_queue = {}
    if isinstance((goal_status or {}).get("sandbox_smoke_queue"), dict):
        raw_queue = (goal_status or {})["sandbox_smoke_queue"]
        raw_steps = raw_queue.get("next_steps", [])
        sandbox_smoke_queue = {
            "status": str(raw_queue.get("status", "missing")),
            "runtime_status": str(raw_queue.get("runtime_status", "")),
            "release_gate_status": str(raw_queue.get("release_gate_status", "")),
            "next_action": str(raw_queue.get("next_action", "")),
            "required_count": int(raw_queue.get("required_count", 0) or 0),
            "queued_count": int(raw_queue.get("queued_count", 0) or 0),
            "path": str(raw_queue.get("path", "")),
            "next_steps": [
                {
                    "order": int(item.get("order", 0) or 0),
                    "step_id": str(item.get("step_id", "")),
                    "status": str(item.get("status", "")),
                    "command": str(item.get("command", "")),
                }
                for item in raw_steps
                if isinstance(item, dict)
            ][:5],
        }

    release_gate_releasable_to_live = bool(
        gate and gate.get("releasable_to_live") is True
    )
    releasable_to_live = release_gate_releasable_to_live and not blockers
    release_gate_status = str(gate.get("status", "missing")) if gate else "missing"
    live_promoted = bool(
        release_gate_status == "passed"
        and release_gate_releasable_to_live
        and (live_approval_gate or {}).get("status") == "passed"
        and "live_promotion.json" in live_approval_evidence
        and live_promotion_has_approval
    )
    live_promotion_status = (
        "promoted"
        if live_promoted
        else "present"
        if live_promotion
        else "missing"
        if release_gate_releasable_to_live
        else "pending"
    )
    status = "missing"
    if manifest:
        status = (
            "promoted"
            if live_promoted
            else "releasable"
            if releasable_to_live
            else "blocked"
            if release_gate_status == "blocked" or blockers
            else "pending"
        )

    next_command = (
        str((gate or {}).get("next_command") or "")
        if release_gate_status == "passed"
        else str(
            (gate or {}).get("next_command")
            or (goal_status or {}).get("next_command")
            or (smoke_status or {}).get("next_command")
            or ""
        )
    )

    zip_info = readiness.get("zip", {}) if readiness else {}
    return {
        "status": status,
        "helper_version": str(
            (manifest or {}).get("helper_version")
            or (readiness or {}).get("helper_version")
            or (validation or {}).get("helper_version")
            or "unknown"
        ),
        "validation_status": str((validation or {}).get("status", "missing")),
        "release_readiness_status": str((readiness or {}).get("status", "missing")),
        "release_gate_status": release_gate_status,
        "releasable_to_live": releasable_to_live,
        "release_gate_releasable_to_live": release_gate_releasable_to_live,
        "smoke_preflight_status": str((smoke_preflight or {}).get("status", "missing")),
        "module_contract": {
            "status": str((module_contract or {}).get("status", "missing")),
            "passed_count": int((module_contract or {}).get("passed_count", 0) or 0),
            "check_count": int((module_contract or {}).get("check_count", 0) or 0),
            "forbidden_count": int(
                (module_contract or {}).get("forbidden_count", 0) or 0
            ),
            "path": str(module_contract_path).replace("\\", "/"),
        },
        "module_audit": {
            "status": str((module_audit or {}).get("status", "missing")),
            "helper_budget_status": str(
                (module_audit or {}).get("helper_budget_status", "missing")
            ),
            "helper_line_count": int(
                (module_audit or {}).get("helper_line_count", 0) or 0
            ),
            "helper_line_budget": int(
                (module_audit or {}).get("helper_line_budget", 0) or 0
            ),
            "next_supplemental_id": str(
                (module_audit or {}).get("next_supplemental_id", "")
            ),
            "next_module_id": str((module_audit or {}).get("next_module_id", "")),
            "path": str(module_audit_path).replace("\\", "/"),
        },
        "smoke_status": str((smoke_status or {}).get("status", "missing")),
        "live_promotion_status": live_promotion_status,
        "live_promoted": live_promoted,
        "live_promotion_created_at": str((live_promotion or {}).get("created_at", "")),
        "live_client": str((live_promotion or {}).get("live_client", "")),
        "live_backup_path": str((live_promotion or {}).get("backup", "")),
        "staged_file_count": len((manifest or {}).get("files", []))
        if isinstance((manifest or {}).get("files"), list)
        else 0,
        "package_path": str(zip_info.get("path", ""))
        if isinstance(zip_info, dict)
        else "",
        "package_sha256": str(zip_info.get("sha256", ""))
        if isinstance(zip_info, dict)
        else "",
        "blockers": blockers,
        "sandbox_smoke_queue": sandbox_smoke_queue,
        "background_status": background_summary,
        "next_action": str(
            (gate or {}).get("next_action")
            or (goal_status or {}).get("next_action")
            or "Run ValidateDev."
        ),
        "next_command": next_command,
        "paths": {
            "dev_dir": str(helper_dev_dir).replace("\\", "/"),
            "manifest": str(manifest_path).replace("\\", "/"),
            "validation": str(validation_path).replace("\\", "/"),
            "release_readiness": str(readiness_path).replace("\\", "/"),
            "release_gate": str(gate_path).replace("\\", "/"),
            "goal_status": str(goal_status_path).replace("\\", "/"),
            "module_contract": str(module_contract_path).replace("\\", "/"),
            "module_audit": str(module_audit_path).replace("\\", "/"),
            "sandbox_smoke_queue": str(
                (helper_dev_dir / "sandbox_smoke_queue.json")
            ).replace("\\", "/"),
            "smoke_preflight": str(smoke_preflight_path).replace("\\", "/"),
            "smoke_status": str(smoke_status_path).replace("\\", "/"),
            "live_promotion": str(live_promotion_path).replace("\\", "/"),
            "background_status": str(background_status_path).replace("\\", "/"),
        },
    }


def _p7_operator_brief_status(operator_brief_path: Path) -> dict[str, Any]:
    brief = _read_json_or_none(operator_brief_path)
    if brief is None:
        return {
            "status": "missing",
            "decision": "missing",
            "generated_at": "",
            "hard_blocker_count": 0,
            "warning_count": 0,
            "warnings": [],
            "next_safe_command": "Run .\\ctoa.ps1 brain refresh before P7 operator workflow review.",
            "policy": "Read-only generated operator brief. Do not run deploy/live actions from this artifact.",
            "action_readiness": {
                "status": "missing",
                "decision": "missing",
                "candidate_count": 0,
                "audited_candidate_count": 0,
                "mcp_write_tool_count": 0,
                "enabled_safe_write_tools": [],
                "next_safe_command": "",
            },
            "safe_write_tool_design": {
                "status": "missing",
                "decision": "missing",
                "selected_action_id": "",
                "proposed_mcp_tool": "",
                "risk_class": "",
                "mode": "missing",
                "mcp_enabled": False,
                "next_safe_command": "",
            },
            "roadmap_generation": {
                "status": "missing",
                "doc_sync_status": "missing",
                "doc_count": 0,
                "ready_doc_count": 0,
                "hard_blockers": ["missing_p7_operator_brief"],
                "next_action": "Run .\\ctoa.ps1 brain refresh before roadmap generation review.",
                "blocked_until": "",
            },
            "path": str(operator_brief_path).replace("\\", "/"),
        }

    hard_blockers = brief.get("hard_blockers", [])
    warnings = brief.get("warnings", [])
    hard_blockers = hard_blockers if isinstance(hard_blockers, list) else []
    warnings = warnings if isinstance(warnings, list) else []
    action_readiness = (
        brief.get("action_readiness")
        if isinstance(brief.get("action_readiness"), dict)
        else {}
    )
    enabled_safe_write_tools = (
        action_readiness.get("enabled_safe_write_tools")
        if isinstance(action_readiness.get("enabled_safe_write_tools"), list)
        else []
    )
    safe_write_tool_design = (
        brief.get("safe_write_tool_design")
        if isinstance(brief.get("safe_write_tool_design"), dict)
        else {}
    )
    roadmap_generation = (
        brief.get("roadmap_generation")
        if isinstance(brief.get("roadmap_generation"), dict)
        else {}
    )
    roadmap_hard_blockers = (
        roadmap_generation.get("hard_blockers")
        if isinstance(roadmap_generation.get("hard_blockers"), list)
        else []
    )
    return {
        "status": str(brief.get("status") or "missing"),
        "decision": str(brief.get("decision") or "missing"),
        "generated_at": str(brief.get("generated_at") or ""),
        "hard_blocker_count": len(hard_blockers),
        "warning_count": len(warnings),
        "warnings": [str(item) for item in warnings[:8]],
        "next_safe_command": str(brief.get("next_safe_command") or ""),
        "policy": str(brief.get("policy") or ""),
        "action_readiness": {
            "status": str(action_readiness.get("status", "missing")),
            "decision": str(action_readiness.get("decision", "missing")),
            "candidate_count": int(action_readiness.get("candidate_count", 0)),
            "audited_candidate_count": int(
                action_readiness.get("audited_candidate_count", 0)
            ),
            "mcp_write_tool_count": int(
                action_readiness.get("mcp_write_tool_count", 0)
            ),
            "enabled_safe_write_tools": [
                {
                    "action_id": str(item.get("action_id", "")),
                    "mcp_tool": str(item.get("mcp_tool", "")),
                    "risk_class": str(item.get("risk_class", "")),
                }
                for item in enabled_safe_write_tools
                if isinstance(item, dict)
            ],
            "next_safe_command": str(action_readiness.get("next_safe_command", "")),
        },
        "safe_write_tool_design": {
            "status": str(safe_write_tool_design.get("status", "missing")),
            "decision": str(safe_write_tool_design.get("decision", "missing")),
            "selected_action_id": str(
                safe_write_tool_design.get("selected_action_id", "")
            ),
            "proposed_mcp_tool": str(
                safe_write_tool_design.get("proposed_mcp_tool", "")
            ),
            "risk_class": str(safe_write_tool_design.get("risk_class", "")),
            "mode": str(safe_write_tool_design.get("mode", "missing")),
            "mcp_enabled": bool(safe_write_tool_design.get("mcp_enabled", False)),
            "next_safe_command": str(
                safe_write_tool_design.get("next_safe_command", "")
            ),
        },
        "roadmap_generation": {
            "status": str(roadmap_generation.get("status", "missing")),
            "doc_sync_status": str(
                roadmap_generation.get("doc_sync_status", "missing")
            ),
            "doc_count": int(roadmap_generation.get("doc_count", 0)),
            "ready_doc_count": int(roadmap_generation.get("ready_doc_count", 0)),
            "hard_blockers": [str(item) for item in roadmap_hard_blockers[:8]],
            "next_action": str(roadmap_generation.get("next_action", "")),
            "blocked_until": str(roadmap_generation.get("blocked_until", "")),
        },
        "path": str(operator_brief_path).replace("\\", "/"),
    }


def _list_release_sprints(releases_dir: Path) -> list[dict[str, Any]]:
    if _safe_dir_stat(releases_dir) is None:
        return []

    sprint_dirs = [
        path
        for path in releases_dir.iterdir()
        if path.name.startswith("sprint-") and _safe_dir_stat(path) is not None
    ]
    sprint_dirs.sort(key=lambda path: path.name, reverse=True)

    result: list[dict[str, Any]] = []
    for sprint_dir in sprint_dirs[:6]:
        md_files = sorted(
            [
                path
                for path in sprint_dir.glob("*.md")
                if _safe_file_stat(path) is not None
            ]
        )
        sprint_stat = _safe_dir_stat(sprint_dir)
        md_stats = [
            file_stat
            for path in md_files
            if (file_stat := _safe_file_stat(path)) is not None
        ]
        latest = max(
            (file_stat.st_mtime for file_stat in md_stats),
            default=sprint_stat.st_mtime if sprint_stat else 0,
        )
        result.append(
            {
                "sprint": sprint_dir.name,
                "file_count": len(md_files),
                "latest_modified_at": dt.datetime.fromtimestamp(
                    latest, tz=dt.UTC
                ).isoformat(timespec="seconds"),
            }
        )
    return result


def build_evidence_pack(
    releases_dir: Path | None = None,
    quality_path: Path | None = None,
    cost_report_path: Path | None = None,
    action_audit_path: Path | None = None,
    helper_dev_dir: Path | None = None,
    operator_brief_path: Path | None = None,
) -> dict[str, Any]:
    releases_dir = releases_dir or _configured_path(
        "CTOA_RELEASES_DIR", "releases/evidence"
    )
    quality_path = quality_path or _configured_path(
        "CTOA_REPO_HYGIENE_PATH",
        "runtime/repo-hygiene/local-pr-quality.json",
    )
    cost_report_path = cost_report_path or _configured_path(
        "CTOA_API_COST_REPORT_PATH", "runtime/api-cost/latest.json"
    )
    action_audit_path = action_audit_path or _configured_path(
        "CTOA_ACTION_AUDIT_PATH",
        "runtime/control-center/action-audit.jsonl",
    )
    helper_dev_dir = helper_dev_dir or _configured_path(
        "CTOA_HELPER_DEV_DIR", str(DEFAULT_HELPER_DEV_DIR)
    )
    operator_brief_path = operator_brief_path or _configured_path(
        "CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH",
        str(DEFAULT_ENGINE_BRAIN_OPERATOR_BRIEF_PATH),
    )

    latest_evidence = _find_latest_markdown(releases_dir)
    quality = _read_json_or_none(quality_path)
    cost_report = _read_json_or_none(cost_report_path)
    action_audit_count = _count_jsonl_records(action_audit_path)
    helper = _helper_status(helper_dev_dir)
    p7_operator_brief = _p7_operator_brief_status(operator_brief_path)

    quality_status = None
    if quality is not None:
        quality_status = str(quality.get("status", "unknown"))

    cost_status = "missing" if cost_report is None else "ready"
    cost_records = int(cost_report.get("records_seen", 0)) if cost_report else 0
    total_tokens = int(cost_report.get("total_tokens", 0)) if cost_report else 0
    total_cost = float(cost_report.get("total_cost_usd", 0.0)) if cost_report else 0.0

    recommendations: list[str] = []
    if quality is None:
        recommendations.append("Run repo hygiene quality generation before sign-off.")
    elif quality_status != "PASS":
        recommendations.append(
            "Review the repo hygiene findings before treating the pack as release-ready."
        )

    if cost_report is None:
        recommendations.append(
            f"Generate {cost_report_path} with scripts/ops/api_cost_report.py."
        )
    elif cost_records == 0:
        recommendations.append(
            "Cost report exists but has no records; verify eval artifacts in evals/runs."
        )

    if action_audit_count == 0:
        recommendations.append(
            "Exercise at least one Control Center action so the audit trail is visible."
        )

    if helper["status"] == "missing":
        recommendations.append(
            "Run PrepareDev and ValidateDev before Helper release review."
        )
    elif helper["status"] not in {"releasable", "promoted"}:
        recommendations.append(helper["next_action"])

    if p7_operator_brief["status"] == "missing":
        recommendations.append(
            "Run .\\ctoa.ps1 brain refresh before P7 operator workflow review."
        )
    elif p7_operator_brief["status"] != "ready":
        recommendations.append(
            p7_operator_brief["next_safe_command"]
            or "Review P7 operator brief blockers before workflow expansion."
        )

    if not recommendations:
        recommendations.append(
            "Evidence pack is ready for review. Keep fresh traces attached to the release note."
        )

    return {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "releases_dir": str(releases_dir).replace("\\", "/"),
        "quality_path": str(quality_path).replace("\\", "/"),
        "cost_report_path": str(cost_report_path).replace("\\", "/"),
        "action_audit_path": str(action_audit_path).replace("\\", "/"),
        "helper_dev_dir": str(helper_dev_dir).replace("\\", "/"),
        "engine_brain_operator_brief_path": str(operator_brief_path).replace("\\", "/"),
        "latest_release_evidence": None
        if latest_evidence is None
        else {
            "path": latest_evidence["path"],
            "modified_at": latest_evidence["modified_at"],
        },
        "release_evidence_file_count": _count_markdown_files(releases_dir),
        "release_sprints": _list_release_sprints(releases_dir),
        "repo_hygiene": {
            "status": quality_status or "missing",
            "finding_count": int(quality.get("finding_count", 0)) if quality else 0,
            "summary": quality.get("summary", {}) if quality else {},
        },
        "api_cost_report": {
            "status": cost_status,
            "records_seen": cost_records,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "anomaly_count": len(cost_report.get("anomalies", []))
            if cost_report
            else 0,
        },
        "control_center_audit": {
            "status": "ready" if action_audit_count else "missing",
            "record_count": action_audit_count,
        },
        "otclient_helper": helper,
        "p7_operator_brief": p7_operator_brief,
        "recommendations": recommendations,
    }


def render_markdown(pack: dict[str, Any]) -> str:
    latest = pack["latest_release_evidence"]
    lines = [
        "# CTOAi Evidence Pack",
        "",
        f"- Generated at (UTC): `{pack['generated_at_utc']}`",
        f"- Releases dir: `{pack['releases_dir']}`",
        f"- Release evidence files: `{pack['release_evidence_file_count']}`",
        f"- Repo hygiene status: `{pack['repo_hygiene']['status']}`",
        f"- API cost report status: `{pack['api_cost_report']['status']}`",
        f"- Control Center audit records: `{pack['control_center_audit']['record_count']}`",
        f"- OTClient Helper status: `{pack['otclient_helper']['status']}`",
        f"- OTClient Helper release gate: `{pack['otclient_helper']['release_gate_status']}`",
        f"- OTClient Helper releasable to live: `{pack['otclient_helper']['releasable_to_live']}`",
        f"- OTClient Helper live promotion: `{pack['otclient_helper']['live_promotion_status']}`",
        f"- P7 operator brief: `{pack['p7_operator_brief']['status']}`",
        f"- P7 operator decision: `{pack['p7_operator_brief']['decision']}`",
        f"- P7 action readiness: `{pack['p7_operator_brief']['action_readiness']['status']}`",
        f"- P7 safe-write design: `{pack['p7_operator_brief']['safe_write_tool_design']['status']}`",
        f"- P7 roadmap generation: `{pack['p7_operator_brief']['roadmap_generation']['status']}`",
    ]

    if latest is not None:
        lines.extend(
            [
                f"- Latest evidence file: `{latest['path']}`",
                f"- Latest evidence modified at: `{latest['modified_at']}`",
            ]
        )

    helper = pack["otclient_helper"]
    lines.extend(
        [
            "",
            "## OTClient Helper",
            "",
            f"- Helper version: `{helper['helper_version']}`",
            f"- Validation: `{helper['validation_status']}`",
            f"- SmokePreflight: `{helper['smoke_preflight_status']}`",
            f"- ModuleContract: `{helper.get('module_contract', {}).get('status', 'missing')}` "
            f"({helper.get('module_contract', {}).get('passed_count', 0)}/"
            f"{helper.get('module_contract', {}).get('check_count', 0)})",
            f"- ModuleAudit: `{helper.get('module_audit', {}).get('status', 'missing')}` "
            f"budget=`{helper.get('module_audit', {}).get('helper_budget_status', 'missing')}` "
            f"next=`{helper.get('module_audit', {}).get('next_supplemental_id', '') or 'none'}`",
            f"- SmokeStatus: `{helper['smoke_status']}`",
            f"- Sandbox smoke queue: `{helper.get('sandbox_smoke_queue', {}).get('status', 'missing')}`",
            f"- LivePromotion: `{helper['live_promotion_status']}`",
            f"- Live promoted at: `{helper['live_promotion_created_at'] or 'n/a'}`",
            f"- BackgroundNoScreen: `{helper.get('background_status', {}).get('status', 'missing')}` "
            f"integrity=`{helper.get('background_status', {}).get('integrity_status', 'missing')}` "
            f"capability=`{helper.get('background_status', {}).get('capability_status', 'missing')}` "
            f"contract_valid=`{helper.get('background_status', {}).get('contract_valid', False)}` "
            f"fresh=`{helper.get('background_status', {}).get('fresh', False)}` "
            f"advisory_only=`{helper.get('background_status', {}).get('advisory_only', False)}` "
            f"promotion_allowed=`{helper.get('background_status', {}).get('promotion_allowed', False)}` "
            f"dispatch_allowed=`{helper.get('background_status', {}).get('dispatch_allowed', False)}`",
            f"- Package SHA256: `{helper['package_sha256'] or 'missing'}`",
            f"- Next command: `{helper['next_command'] or 'n/a'}`",
        ]
    )
    if helper["blockers"]:
        lines.extend(["", "### Helper Blockers", ""])
        for blocker in helper["blockers"][:8]:
            lines.append(f"- {blocker}")
    sandbox_queue = helper.get("sandbox_smoke_queue", {})
    if sandbox_queue:
        lines.extend(
            [
                "",
                "### Sandbox Smoke Queue",
                "",
                f"- Runtime status: `{sandbox_queue.get('runtime_status', 'missing')}`",
                f"- Required/queued: `{sandbox_queue.get('required_count', 0)}/{sandbox_queue.get('queued_count', 0)}`",
                f"- Next action: `{sandbox_queue.get('next_action') or 'n/a'}`",
            ]
        )
        for step in sandbox_queue.get("next_steps", [])[:5]:
            lines.append(
                f"- `{step.get('step_id', '')}` `{step.get('status', '')}`: `{step.get('command', '')}`"
            )

    p7 = pack["p7_operator_brief"]
    lines.extend(
        [
            "",
            "## P7 Operator Brief",
            "",
            f"- Status: `{p7['status']}`",
            f"- Decision: `{p7['decision']}`",
            f"- Generated at: `{p7['generated_at'] or 'n/a'}`",
            f"- Hard blockers: `{p7['hard_blocker_count']}`",
            f"- Warnings: `{p7['warning_count']}`",
            f"- Action readiness: `{p7['action_readiness']['status']}`",
            (
                f"- Action candidates audited: "
                f"`{p7['action_readiness']['audited_candidate_count']}/{p7['action_readiness']['candidate_count']}`"
            ),
            f"- MCP write tools: `{p7['action_readiness']['mcp_write_tool_count']}`",
            f"- Action next safe command: `{p7['action_readiness']['next_safe_command'] or 'n/a'}`",
            f"- Safe-write design: `{p7['safe_write_tool_design']['status']}`",
            f"- Selected safe-write tool: `{p7['safe_write_tool_design']['proposed_mcp_tool'] or 'n/a'}`",
            f"- Safe-write MCP enabled: `{p7['safe_write_tool_design']['mcp_enabled']}`",
            f"- Design next safe command: `{p7['safe_write_tool_design']['next_safe_command'] or 'n/a'}`",
            f"- Roadmap generation: `{p7['roadmap_generation']['status']}`",
            (
                f"- Roadmap docs ready: "
                f"`{p7['roadmap_generation']['ready_doc_count']}/{p7['roadmap_generation']['doc_count']}`"
            ),
            f"- Roadmap doc sync: `{p7['roadmap_generation']['doc_sync_status']}`",
            f"- Roadmap next action: `{p7['roadmap_generation']['next_action'] or 'n/a'}`",
            f"- Next safe command: `{p7['next_safe_command'] or 'n/a'}`",
        ]
    )
    if p7["warnings"]:
        lines.extend(["", "### P7 Warnings", ""])
        for warning in p7["warnings"][:8]:
            lines.append(f"- {warning}")

    lines.extend(["", "## Recommendations", ""])
    for recommendation in pack["recommendations"]:
        lines.append(f"- {recommendation}")

    lines.extend(["", "## Release Sprints", ""])
    if pack["release_sprints"]:
        for sprint in pack["release_sprints"]:
            lines.append(
                f"- `{sprint['sprint']}`: {sprint['file_count']} files, latest `{sprint['latest_modified_at']}`"
            )
    else:
        lines.append("- No sprint evidence directories found.")

    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a compact evidence pack from local CTOAi artifacts."
    )
    parser.add_argument(
        "--releases-dir",
        type=Path,
        default=_configured_path("CTOA_RELEASES_DIR", "releases/evidence"),
    )
    parser.add_argument(
        "--quality-path",
        type=Path,
        default=_configured_path(
            "CTOA_REPO_HYGIENE_PATH", "runtime/repo-hygiene/local-pr-quality.json"
        ),
    )
    parser.add_argument(
        "--cost-report-path",
        type=Path,
        default=_configured_path(
            "CTOA_API_COST_REPORT_PATH", "runtime/api-cost/latest.json"
        ),
    )
    parser.add_argument(
        "--action-audit-path",
        type=Path,
        default=_configured_path(
            "CTOA_ACTION_AUDIT_PATH", "runtime/control-center/action-audit.jsonl"
        ),
    )
    parser.add_argument(
        "--helper-dev-dir",
        type=Path,
        default=_configured_path("CTOA_HELPER_DEV_DIR", str(DEFAULT_HELPER_DEV_DIR)),
    )
    parser.add_argument(
        "--operator-brief-path",
        type=Path,
        default=_configured_path(
            "CTOA_ENGINE_BRAIN_OPERATOR_BRIEF_PATH",
            str(DEFAULT_ENGINE_BRAIN_OPERATOR_BRIEF_PATH),
        ),
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=_configured_path(
            "CTOA_EVIDENCE_JSON_PATH", "runtime/evidence/latest.json"
        ),
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=_configured_path("CTOA_EVIDENCE_MD_PATH", "runtime/evidence/latest.md"),
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    pack = build_evidence_pack(
        args.releases_dir,
        args.quality_path,
        args.cost_report_path,
        args.action_audit_path,
        args.helper_dev_dir,
        args.operator_brief_path,
    )

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(pack, indent=2), encoding="utf-8")

    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(render_markdown(pack), encoding="utf-8")

    print(json.dumps(pack, indent=2))
    print(f"JSON evidence written to: {args.json_out}")
    print(f"Markdown evidence written to: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
