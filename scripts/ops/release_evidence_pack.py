#!/usr/bin/env python3
"""Assemble evidence packs from backlog sync and runtime artifacts.

This module keeps two related surfaces together:
- backlog release evidence generation for sprint state sync
- compact runtime evidence pack generation for Control Center sign-off flows
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import datetime as dt
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_acceptance as conditions_acceptance
    from . import otclient_equipment_operator_refresh_run as equipment_refresh_run
    from . import otclient_equipment_shadow_acceptance as equipment_acceptance
    from . import otclient_heal_friend_shadow_acceptance as heal_friend_acceptance
    from . import (
        otclient_p12_conditions_execute_once_receipt as p12_conditions_receipt,
    )
    from . import (
        otclient_p12_equipment_execute_once_receipt as p12_equipment_receipt,
    )
    from . import (
        otclient_equipment_operator_readiness as equipment_operator_readiness,
    )
else:  # pragma: no cover - direct script execution
    try:
        from scripts.ops import (
            otclient_conditions_shadow_acceptance as conditions_acceptance,
            otclient_equipment_operator_refresh_run as equipment_refresh_run,
            otclient_equipment_operator_readiness as equipment_operator_readiness,
            otclient_equipment_shadow_acceptance as equipment_acceptance,
            otclient_heal_friend_shadow_acceptance as heal_friend_acceptance,
            otclient_p12_conditions_execute_once_receipt as p12_conditions_receipt,
            otclient_p12_equipment_execute_once_receipt as p12_equipment_receipt,
        )
    except ImportError:
        import otclient_conditions_shadow_acceptance as conditions_acceptance
        import otclient_equipment_operator_refresh_run as equipment_refresh_run
        import otclient_equipment_operator_readiness as equipment_operator_readiness
        import otclient_equipment_shadow_acceptance as equipment_acceptance
        import otclient_heal_friend_shadow_acceptance as heal_friend_acceptance
        import otclient_p12_conditions_execute_once_receipt as p12_conditions_receipt
        import otclient_p12_equipment_execute_once_receipt as p12_equipment_receipt


DEFAULT_RELEASES_DIR = Path("releases/evidence")
DEFAULT_JSON_OUT = Path("runtime/evidence/latest.json")
DEFAULT_MD_OUT = Path("runtime/evidence/latest.md")
DEFAULT_HELPER_DEV_DIR = Path("runtime/solteria_helper_dev")
DEFAULT_ENGINE_BRAIN_OPERATOR_BRIEF_PATH = Path("AI/generated/P7_OPERATOR_BRIEF.json")
DEFAULT_ENGINE_BRAIN_ROADMAP_STATE_PATH = Path("AI/generated/ROADMAP_STATE.json")
P14_RUNNER_PREFLIGHT_PATH = Path("runtime/control-center/p14-runner-preflight.json")
P14_RUNNER_PREFLIGHT_SCHEMA = "ctoa.p14-runner-preflight.v2"
P14_REMEDIATION_SCHEMA = "ctoa.p14-remediation-plan.v1"
P14_RUNNER_PREFLIGHT_MAX_AGE_SECONDS = 6 * 60 * 60
P14_REMEDIATION_ACTION_IDS = frozenset(
    {
        "none",
        "activate_p14_workflow",
        "restore_p14_runner_capacity",
        "harden_p14_environment",
        "configure_p14_signing_material",
        "allow_p14_source_branch",
        "refresh_p14_independent_runner_evidence",
        "collect_p14_visual_evidence",
        "collect_p14_in_world_evidence",
        "run_p14_canary_rehearsal",
        "run_p14_rollback_rehearsal",
        "review_p14_external_state",
    }
)
P14_REMEDIATION_ACTION_CONTRACTS = {
    "activate_p14_workflow": (
        "workflow_active",
        "guarded_write",
        "external_config",
    ),
    "restore_p14_runner_capacity": (
        "runner_capacity",
        "guarded_write",
        "external_config",
    ),
    "harden_p14_environment": (
        "environment_protection",
        "guarded_write",
        "external_config",
    ),
    "configure_p14_signing_material": (
        "signing_material",
        "guarded_write",
        "external_config",
    ),
    "allow_p14_source_branch": (
        "branch_scope",
        "guarded_write",
        "external_config",
    ),
    "refresh_p14_independent_runner_evidence": (
        "external_attestation",
        "safe_write",
        "external_runner",
    ),
    "collect_p14_visual_evidence": (
        "visual_attestation",
        "safe_write",
        "external_runner",
    ),
    "collect_p14_in_world_evidence": (
        "in_world_attestation",
        "safe_write",
        "external_runner",
    ),
    "run_p14_canary_rehearsal": (
        "canary_attestation",
        "guarded_write",
        "external_runner",
    ),
    "run_p14_rollback_rehearsal": (
        "rollback_attestation",
        "guarded_write",
        "external_runner",
    ),
    "review_p14_external_state": (
        "external_evidence_review",
        "read_only",
        "operator_review",
    ),
}
P14_REMEDIATION_CAPABILITIES = frozenset(
    {
        "workflow_active",
        "runner_capacity",
        "environment_protection",
        "signing_material",
        "branch_scope",
        "external_attestation",
        "visual_attestation",
        "in_world_attestation",
        "canary_attestation",
        "rollback_attestation",
        "external_evidence_review",
    }
)
P14_REMEDIATION_INTERACTIONS = frozenset(
    {"none", "external_config", "external_runner", "operator_review"}
)
P14_REMEDIATION_RISK_CLASSES = frozenset(
    {"read_only", "safe_write", "guarded_write"}
)
EVIDENCE_SCHEMA_VERSION = "ctoa.control-center.evidence.v2"
EVIDENCE_SOURCE_ACTION = "evidence-pack-refresh"
EVIDENCE_SOURCE_AUDIT_ID_RE = re.compile(
    r"^[0-9]{14,20}-evidence-pack-refresh$"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
P14_FOUNDATION_PATHS = (
    "schemas/ctoa-p14-acceptance-request.schema.json",
    "schemas/ctoa-p14-acceptance-report.schema.json",
    "schemas/ctoa-p14-acceptance-result.schema.json",
    "schemas/ctoa-p14-runner-request.schema.json",
    "schemas/ctoa-p14-runner-result.schema.json",
    "scripts/ops/otclient_p14_acceptance_attestation.py",
    "scripts/ops/otclient_p14_independent_runner.py",
    "scripts/ops/otclient_p14_runner_preflight.py",
    "tests/test_otclient_p14_acceptance_attestation.py",
    "tests/test_otclient_p14_independent_runner.py",
    "tests/test_otclient_p14_runner_preflight.py",
    ".github/workflows/p14-independent-runner-contract.yml",
    "docs/otclient/P14_INDEPENDENT_RUNNER_CONTRACT.md",
)
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
BACKGROUND_PIN_CLASSIFICATION_VALUES = {
    "trusted",
    "missing_or_unreadable_attestation",
    "legacy_or_unbound_attestation",
    "invalid_or_mismatched_attestation",
}
BACKGROUND_PIN_REQUIRED_ACTION_VALUES = {
    "none",
    "refresh_official_live_promotion_after_current_gates",
}
BACKGROUND_DIAGNOSTIC_STATUS_VALUES = {
    "not_required",
    "unavailable",
    "passed",
    "failed",
}
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
BACKGROUND_INTERACTION_CONTRACT = {
    "gui_automation": False,
    "mouse_keyboard_input": False,
    "window_focus": False,
    "screenshot_capture": False,
    "client_launch": False,
    "client_stop": False,
    "live_file_writes": False,
    "passive_reads_only": True,
    "evidence_write_scope": "runtime/solteria_helper_dev",
}
BACKGROUND_WRAPPER_INVARIANTS = {
    "client_process_stable": True,
    "screenshot_count_stable": True,
}
CONDITIONS_SHADOW_REPORT_SCHEMA = "ctoa.conditions-shadow-replay-report.v1"
CONDITIONS_SHADOW_TRACE_SCHEMA = "ctoa.conditions-shadow-trace.v1"
CONDITIONS_SHADOW_INPUT_SCHEMA = "ctoa.conditions-shadow-input.v1"
CONDITIONS_SHADOW_MODE = "offline_shadow_replay"
CONDITIONS_SHADOW_MAX_AGE_SECONDS = 30
CONDITIONS_SHADOW_OPERATIONAL_STATUS_VALUES = {
    "operational_acceptance_blocked",
    "shadow_plan_ready_for_operator_review",
}
CONDITIONS_SHADOW_TRACE_STATUS_VALUES = {
    "operational_acceptance_blocked",
    "shadow_plan_ready",
}
CONDITIONS_SHADOW_SCENARIO_STATUS_VALUES = {"failed", "passed"}
CONDITIONS_SHADOW_FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
)
EQUIPMENT_SHADOW_REPORT_SCHEMA = "ctoa.equipment-shadow-replay-report.v1"
EQUIPMENT_SHADOW_MODE = "offline_equipment_shadow_replay"
EQUIPMENT_SHADOW_MAX_AGE_SECONDS = 30
EQUIPMENT_SHADOW_STATUS_VALUES = {
    "operational_acceptance_blocked",
    "shadow_plan_ready_for_operator_review",
}
EQUIPMENT_SHADOW_FALSE_FLAGS = CONDITIONS_SHADOW_FALSE_FLAGS
P12_CONDITIONS_PLAN_BASIS_KEYS = (
    "schema_version",
    "lane",
    "vocation",
    "action",
    "spell",
    "spell_source",
    "predecessor_accepted_spell",
    "retry_budget",
    "mandatory_kill_and_disarm",
    "requires_fresh_paralyze_observation_ms",
    "manifest_sha256",
    "source_sha256",
    "ek_profile_sha256",
    "p9_receipt_sha256",
    "validation_sha256",
    "smoke_preflight_sha256",
    "module_static_gates_sha256",
    "module_contract_sha256",
)
P12_EQUIPMENT_PLAN_BASIS_KEYS = (
    "schema_version",
    "lane",
    "action",
    "slot",
    "before_item_id",
    "before_family_key",
    "candidate_item_id",
    "candidate_family_key",
    "source_container_id",
    "source_slot_index",
    "rollback_item_id",
    "retry_budget",
    "mandatory_kill_and_disarm",
    "requires_post_action_ring_id",
    "observation_id",
    "capability_sha256",
    "manifest_sha256",
    "runtime_gates_sha256",
    "p10_receipt_sha256",
    "source_sha256",
    "family_registry_sha256",
    "family_selection_profile_sha256",
)
P12_SAFE_PLAN_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "execute_once_allowed",
    "live_promotion",
)
P10_EQUIPMENT_CONSUMER_PARITY_SCHEMA = "ctoa.equipment-consumer-parity.v1"
P10_EQUIPMENT_OPERATOR_REFRESH_RUN_SCHEMA = equipment_refresh_run.SCHEMA_VERSION
EQUIPMENT_OPERATOR_ARTIFACT_FILES = {
    "equipment_capture_profile_doctor": "equipment_capture_profile_doctor.json",
    "equipment_observation_preview": "equipment_observation_preview.json",
    "equipment_dependency_preflight": "equipment_dependency_preflight.json",
    "equipment_candidate_catalog": "equipment_candidate_catalog.json",
    "equipment_capture_profile_change_plan": (
        "equipment_capture_profile_change_plan.json"
    ),
    "equipment_operator_readiness": "equipment_operator_readiness.json",
}
EQUIPMENT_OPERATOR_SOURCE_NAMES = {
    "equipment_capture_profile_doctor": "capture_doctor",
    "equipment_observation_preview": "observation_preview",
    "equipment_dependency_preflight": "dependency_preflight",
    "equipment_candidate_catalog": "candidate_catalog",
    "equipment_capture_profile_change_plan": "change_plan",
}
EQUIPMENT_OPERATOR_EXPECTED_SCHEMAS = {
    **{
        artifact: equipment_operator_readiness.EXPECTED_SCHEMAS[source]
        for artifact, source in EQUIPMENT_OPERATOR_SOURCE_NAMES.items()
    },
    "equipment_operator_readiness": equipment_operator_readiness.SCHEMA,
}
EQUIPMENT_OPERATOR_MAX_AGE_MS = equipment_operator_readiness.MAX_FRESH_AGE_MS
EQUIPMENT_SHADOW_REQUIRED_MUTATIONS = {
    "none",
    "inventory_ambiguous",
    "revision_drift",
    "missing_ring",
    "wrong_equipped_id",
    "wrong_candidate_id",
    "missing_rollback",
    "wrong_container",
    "stale_snapshot",
    "future_snapshot",
    "protection_zone",
    "cooldown_active",
    "p9_blocked",
    "p9_tampered",
    "unsafe_contract",
    "player_offline",
    "player_dead",
    "protection_zone_unknown",
    "protection_zone_untrusted",
    "candidate_zero",
    "rollback_wrong_id",
    "candidate_container_negative",
    "candidate_slot_zero",
    "rollback_slot_mismatch",
    "cooldown_unknown",
    "cooldown_untrusted",
    "retry_nonzero",
    "inventory_revision_zero",
    "rollback_revision_zero",
    "snapshot_extra_key",
}
CONDITIONS_SHADOW_REPORT_KEYS = {
    "schema_version",
    "generated_at_unix_ms",
    "mode",
    "operational_acceptance_status",
    "scenario_pack_status",
    "fixture_only_validation_passed",
    "runtime_readiness_claimed",
    "operational_trace",
    "scenario_pack",
    *CONDITIONS_SHADOW_FALSE_FLAGS,
    "intrusive_actions_performed",
}
CONDITIONS_SHADOW_TRACE_KEYS = {
    "schema_version",
    "trace_id",
    "source",
    "evaluated_at_unix_ms",
    "mode",
    "action",
    "condition",
    "spell",
    "input_sha256",
    "canonical_input_sha256",
    "observation_age_ms",
    "p8_age_ms",
    "recovery_trace_age_ms",
    "recovery_age_ms",
    "status",
    "decision",
    "blockers",
    "decision_sha256",
    "operator_review_required",
    *CONDITIONS_SHADOW_FALSE_FLAGS,
    "intrusive_actions_performed",
}
CONDITIONS_SHADOW_INPUT_HASH_KEYS = {
    "profile",
    "observation",
    "p8_proof",
    "recovery_trace",
    "recovery_proof",
}
CONDITIONS_SHADOW_SCENARIO_PACK_KEYS = {
    "status",
    "fixture_only",
    "operational_readiness_claimed",
    "scenario_pack_sha256",
    "total_count",
    "passed_count",
    "failed_count",
    "cases",
    *CONDITIONS_SHADOW_FALSE_FLAGS,
    "intrusive_actions_performed",
}
CONDITIONS_SHADOW_SCENARIO_CASE_KEYS = {
    "name",
    "mutation",
    "expected_status",
    "actual_status",
    "expected_blockers",
    "blockers",
    "canonical_input_sha256",
    "decision_sha256",
    "deterministic",
    "passed",
    *CONDITIONS_SHADOW_FALSE_FLAGS,
    "intrusive_actions_performed",
}
CONDITIONS_SHADOW_BLOCKER_ORDER = (
    "profile_missing",
    "profile_malformed",
    "profile_duplicate_keys",
    "profile_oversize",
    "profile_symlink_rejected",
    "profile_not_regular",
    "profile_unreadable",
    "profile_schema_invalid",
    "profile_action_mismatch",
    "profile_condition_mismatch",
    "profile_spell_mismatch",
    "profile_cooldown_policy_invalid",
    "profile_retry_budget_nonzero",
    "profile_p8_proof_not_required",
    "profile_recovery_proof_not_required",
    "profile_unsafe_contract",
    "observation_missing",
    "observation_malformed",
    "observation_duplicate_keys",
    "observation_oversize",
    "observation_symlink_rejected",
    "observation_not_regular",
    "observation_unreadable",
    "observation_envelope_invalid",
    "observation_schema_invalid",
    "observation_future",
    "observation_stale",
    "player_offline",
    "player_online_unknown",
    "player_dead",
    "player_life_unknown",
    "protection_zone_inside",
    "protection_zone_unknown",
    "protection_zone_source_untrusted",
    "condition_mismatch",
    "condition_absent",
    "condition_unknown",
    "cooldown_active",
    "cooldown_unknown",
    "cooldown_source_untrusted",
    "observation_unsafe_contract",
    "p8_missing",
    "p8_malformed",
    "p8_duplicate_keys",
    "p8_oversize",
    "p8_symlink_rejected",
    "p8_not_regular",
    "p8_unreadable",
    "p8_schema_invalid",
    "p8_future",
    "p8_stale",
    "p8_observation_hash_mismatch",
    "p8_operational_acceptance_blocked",
    "p8_unsafe_contract",
    "recovery_trace_missing",
    "recovery_trace_malformed",
    "recovery_trace_duplicate_keys",
    "recovery_trace_oversize",
    "recovery_trace_symlink_rejected",
    "recovery_trace_not_regular",
    "recovery_trace_unreadable",
    "recovery_trace_schema_invalid",
    "recovery_trace_future",
    "recovery_trace_stale",
    "recovery_trace_status_blocked",
    "recovery_trace_action_mismatch",
    "recovery_trace_unsafe_contract",
    "recovery_missing",
    "recovery_malformed",
    "recovery_duplicate_keys",
    "recovery_oversize",
    "recovery_symlink_rejected",
    "recovery_not_regular",
    "recovery_unreadable",
    "recovery_schema_invalid",
    "recovery_future",
    "recovery_stale",
    "recovery_status_blocked",
    "recovery_action_mismatch",
    "recovery_condition_mismatch",
    "recovery_spell_mismatch",
    "recovery_trace_hash_mismatch",
    "recovery_profile_hash_mismatch",
    "recovery_observation_hash_mismatch",
    "recovery_p8_hash_mismatch",
    "recovery_unsafe_contract",
    "fixture_observation_not_operational",
    "fixture_p8_proof_not_operational",
    "fixture_recovery_trace_not_operational",
    "fixture_recovery_proof_not_operational",
)
CONDITIONS_SHADOW_BLOCKER_RANK = {
    name: index for index, name in enumerate(CONDITIONS_SHADOW_BLOCKER_ORDER)
}
CONDITIONS_SHADOW_SCENARIO_MUTATIONS = {
    "none",
    "profile_wrong_action",
    "profile_wrong_condition",
    "profile_wrong_spell",
    "profile_retry_nonzero",
    "profile_future_version",
    "profile_malformed",
    "profile_duplicate_keys",
    "profile_oversized",
    "profile_symlinked",
    "profile_non_regular",
    "profile_extra_field",
    "observation_stale",
    "observation_future",
    "player_offline",
    "player_online_unknown",
    "player_dead",
    "player_life_unknown",
    "protection_zone_inside",
    "protection_zone_unknown",
    "condition_absent",
    "condition_unknown",
    "condition_wrong",
    "cooldown_active",
    "cooldown_unknown",
    "observation_extra_field",
    "observation_unsafe_contract",
    "p8_missing",
    "p8_blocked",
    "p8_stale",
    "p8_future",
    "p8_unsafe_contract",
    "p8_extra_field",
    "recovery_missing",
    "recovery_malformed",
    "recovery_status_blocked",
    "recovery_future",
    "recovery_stale",
    "recovery_wrong_action",
    "recovery_wrong_condition",
    "recovery_wrong_spell",
    "recovery_hash_mismatch",
    "recovery_extra_field",
    "recovery_unsafe_contract",
}
CONDITIONS_SHADOW_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CONDITIONS_SHADOW_TRACE_ID_RE = re.compile(r"^conditions-shadow-[0-9a-f]{16}$")
CONDITIONS_SHADOW_CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


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
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        RecursionError,
    ):
        return None


class _DuplicateJsonKeyError(ValueError):
    pass


def _reject_duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _parse_finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _json_shape_within_bounds(
    value: Any, *, max_depth: int = 64, max_nodes: int = 50_000
) -> bool:
    stack: list[tuple[Any, int]] = [(value, 0)]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if depth > max_depth or visited > max_nodes:
            return False
        if isinstance(current, dict):
            stack.extend((nested, depth + 1) for nested in current.values())
        elif isinstance(current, list):
            stack.extend((nested, depth + 1) for nested in current)
    return True


def _read_json_strict_or_none(path: Path) -> dict[str, Any] | None:
    if _safe_file_stat(path) is None:
        return None
    try:
        payload = json.loads(
            _read_text_bounded(path, MAX_EVIDENCE_JSON_BYTES),
            object_pairs_hook=_reject_duplicate_json_pairs,
            parse_constant=_reject_json_constant,
            parse_float=_parse_finite_json_float,
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        RecursionError,
    ):
        return None
    return (
        payload
        if isinstance(payload, dict) and _json_shape_within_bounds(payload)
        else None
    )


def _conditions_shadow_is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _conditions_shadow_is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and CONDITIONS_SHADOW_SHA256_RE.fullmatch(value) is not None
        and value != "0" * 64
    )


def _conditions_shadow_is_allowed(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _conditions_shadow_canonical_sha256(value: Any) -> str:
    return _canonical_json_sha256(value)


def _conditions_shadow_false_flags(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in CONDITIONS_SHADOW_FALSE_FLAGS)


def _conditions_shadow_empty_ledger(payload: dict[str, Any]) -> bool:
    return payload.get("intrusive_actions_performed") == []


def _conditions_shadow_blockers_valid(value: Any) -> bool:
    if not isinstance(value, list) or len(value) > len(CONDITIONS_SHADOW_BLOCKER_ORDER):
        return False
    if not all(isinstance(item, str) for item in value):
        return False
    if any(item not in CONDITIONS_SHADOW_BLOCKER_RANK for item in value):
        return False
    expected = sorted(set(value), key=CONDITIONS_SHADOW_BLOCKER_RANK.__getitem__)
    return value == expected


def _conditions_shadow_unique_errors(errors: list[str]) -> list[str]:
    return list(dict.fromkeys(errors))[:64]


def _conditions_shadow_trace_errors(
    trace: dict[str, Any], generated_at_unix_ms: Any
) -> list[str]:
    errors: list[str] = []
    if set(trace) != CONDITIONS_SHADOW_TRACE_KEYS:
        errors.append("operational_trace.exact_keys")
    if trace.get("schema_version") != CONDITIONS_SHADOW_TRACE_SCHEMA:
        errors.append("operational_trace.schema_version")
    if trace.get("source") != "operational":
        errors.append("operational_trace.source")
    if trace.get("mode") != "shadow_only":
        errors.append("operational_trace.mode")
    for key, expected in (
        ("action", "plan_paralyze_recovery"),
        ("condition", "paralyze"),
        ("spell", "exura"),
    ):
        if trace.get(key) != expected:
            errors.append(f"operational_trace.{key}")

    evaluated_at = trace.get("evaluated_at_unix_ms")
    if (
        not _conditions_shadow_is_int(evaluated_at)
        or evaluated_at <= 0
        or evaluated_at != generated_at_unix_ms
    ):
        errors.append("operational_trace.evaluated_at_unix_ms")
    for key in (
        "observation_age_ms",
        "p8_age_ms",
        "recovery_trace_age_ms",
        "recovery_age_ms",
    ):
        value = trace.get(key)
        if value is not None and not _conditions_shadow_is_int(value):
            errors.append(f"operational_trace.{key}")

    blockers = trace.get("blockers")
    blockers_valid = _conditions_shadow_blockers_valid(blockers)
    if not blockers_valid:
        errors.append("operational_trace.blockers")
    status = trace.get("status")
    if not _conditions_shadow_is_allowed(status, CONDITIONS_SHADOW_TRACE_STATUS_VALUES):
        errors.append("operational_trace.status")
    decision = trace.get("decision")
    if not _conditions_shadow_is_allowed(
        decision, {"hold", "would_plan_paralyze_recovery"}
    ):
        errors.append("operational_trace.decision")
    if blockers_valid and _conditions_shadow_is_allowed(
        status, CONDITIONS_SHADOW_TRACE_STATUS_VALUES
    ):
        expected_status = (
            "shadow_plan_ready" if not blockers else "operational_acceptance_blocked"
        )
        expected_decision = "would_plan_paralyze_recovery" if not blockers else "hold"
        if status != expected_status:
            errors.append("operational_trace.status_blocker_consistency")
        if decision != expected_decision:
            errors.append("operational_trace.decision_blocker_consistency")

    input_hashes = trace.get("input_sha256")
    input_hashes_valid = (
        isinstance(input_hashes, dict)
        and set(input_hashes) == CONDITIONS_SHADOW_INPUT_HASH_KEYS
        and all(_conditions_shadow_is_sha256(value) for value in input_hashes.values())
    )
    if not input_hashes_valid:
        errors.append("operational_trace.input_sha256")
    canonical_input_sha = trace.get("canonical_input_sha256")
    if not _conditions_shadow_is_sha256(canonical_input_sha):
        errors.append("operational_trace.canonical_input_sha256")
    elif input_hashes_valid and _conditions_shadow_is_int(evaluated_at):
        expected_input_sha = _conditions_shadow_canonical_sha256(
            {
                "schema_version": CONDITIONS_SHADOW_INPUT_SCHEMA,
                "evaluated_at_unix_ms": evaluated_at,
                "input_sha256": input_hashes,
            }
        )
        if canonical_input_sha != expected_input_sha:
            errors.append("operational_trace.canonical_input_sha256_mismatch")

    if trace.get("operator_review_required") is not True:
        errors.append("operational_trace.operator_review_required")
    for key in CONDITIONS_SHADOW_FALSE_FLAGS:
        if trace.get(key) is not False:
            errors.append(f"operational_trace.{key}")
    if not _conditions_shadow_empty_ledger(trace):
        errors.append("operational_trace.intrusive_actions_performed")

    decision_sha = trace.get("decision_sha256")
    if not _conditions_shadow_is_sha256(decision_sha):
        errors.append("operational_trace.decision_sha256")
    else:
        decision_basis = {
            "schema_version": CONDITIONS_SHADOW_TRACE_SCHEMA,
            "canonical_input_sha256": canonical_input_sha,
            "status": status,
            "decision": decision,
            "action": trace.get("action"),
            "condition": trace.get("condition"),
            "spell": trace.get("spell"),
            "observation_age_ms": trace.get("observation_age_ms"),
            "p8_age_ms": trace.get("p8_age_ms"),
            "recovery_trace_age_ms": trace.get("recovery_trace_age_ms"),
            "recovery_age_ms": trace.get("recovery_age_ms"),
            "blockers": blockers,
            "operator_review_required": trace.get("operator_review_required"),
            **{key: trace.get(key) for key in CONDITIONS_SHADOW_FALSE_FLAGS},
            "intrusive_actions_performed": trace.get("intrusive_actions_performed"),
        }
        if decision_sha != _conditions_shadow_canonical_sha256(decision_basis):
            errors.append("operational_trace.decision_sha256_mismatch")
    trace_id = trace.get("trace_id")
    if (
        not isinstance(trace_id, str)
        or CONDITIONS_SHADOW_TRACE_ID_RE.fullmatch(trace_id) is None
        or not isinstance(decision_sha, str)
        or trace_id != f"conditions-shadow-{decision_sha[:16]}"
    ):
        errors.append("operational_trace.trace_id")
    return errors


def _conditions_shadow_scenario_errors(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(pack) != CONDITIONS_SHADOW_SCENARIO_PACK_KEYS:
        errors.append("scenario_pack.exact_keys")
    status = pack.get("status")
    if not _conditions_shadow_is_allowed(
        status, CONDITIONS_SHADOW_SCENARIO_STATUS_VALUES
    ):
        errors.append("scenario_pack.status")
    if pack.get("fixture_only") is not True:
        errors.append("scenario_pack.fixture_only")
    if pack.get("operational_readiness_claimed") is not False:
        errors.append("scenario_pack.operational_readiness_claimed")
    if not _conditions_shadow_is_sha256(pack.get("scenario_pack_sha256")):
        errors.append("scenario_pack.scenario_pack_sha256")
    for key in CONDITIONS_SHADOW_FALSE_FLAGS:
        if pack.get(key) is not False:
            errors.append(f"scenario_pack.{key}")
    if not _conditions_shadow_empty_ledger(pack):
        errors.append("scenario_pack.intrusive_actions_performed")

    counts: dict[str, int] = {}
    for key in ("total_count", "passed_count", "failed_count"):
        value = pack.get(key)
        if not _conditions_shadow_is_int(value) or value < 0:
            errors.append(f"scenario_pack.{key}")
        else:
            counts[key] = value
    cases = pack.get("cases")
    if not isinstance(cases, list) or len(cases) > 128:
        errors.append("scenario_pack.cases")
        cases_to_validate: list[Any] = []
    else:
        cases_to_validate = cases

    seen_names: set[str] = set()
    passed_flags: list[bool] = []
    for index, case in enumerate(cases_to_validate):
        prefix = f"scenario_pack.cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix}.object")
            continue
        if set(case) != CONDITIONS_SHADOW_SCENARIO_CASE_KEYS:
            errors.append(f"{prefix}.exact_keys")
        name = case.get("name")
        if (
            not isinstance(name, str)
            or CONDITIONS_SHADOW_CASE_ID_RE.fullmatch(name) is None
            or name in seen_names
        ):
            errors.append(f"{prefix}.name")
        else:
            seen_names.add(name)
        if not _conditions_shadow_is_allowed(
            case.get("mutation"), CONDITIONS_SHADOW_SCENARIO_MUTATIONS
        ):
            errors.append(f"{prefix}.mutation")
        expected_status = case.get("expected_status")
        actual_status = case.get("actual_status")
        if not _conditions_shadow_is_allowed(
            expected_status, CONDITIONS_SHADOW_TRACE_STATUS_VALUES
        ):
            errors.append(f"{prefix}.expected_status")
        if not _conditions_shadow_is_allowed(
            actual_status, CONDITIONS_SHADOW_TRACE_STATUS_VALUES
        ):
            errors.append(f"{prefix}.actual_status")
        expected_blockers = case.get("expected_blockers")
        blockers = case.get("blockers")
        expected_blockers_valid = _conditions_shadow_blockers_valid(expected_blockers)
        blockers_valid = _conditions_shadow_blockers_valid(blockers)
        if not expected_blockers_valid:
            errors.append(f"{prefix}.expected_blockers")
        if not blockers_valid:
            errors.append(f"{prefix}.blockers")
        if expected_blockers_valid and _conditions_shadow_is_allowed(
            expected_status, CONDITIONS_SHADOW_TRACE_STATUS_VALUES
        ):
            expected_from_blockers = (
                "shadow_plan_ready"
                if not expected_blockers
                else "operational_acceptance_blocked"
            )
            if expected_status != expected_from_blockers:
                errors.append(f"{prefix}.expected_status_blocker_consistency")
        if blockers_valid and _conditions_shadow_is_allowed(
            actual_status, CONDITIONS_SHADOW_TRACE_STATUS_VALUES
        ):
            actual_from_blockers = (
                "shadow_plan_ready"
                if not blockers
                else "operational_acceptance_blocked"
            )
            if actual_status != actual_from_blockers:
                errors.append(f"{prefix}.actual_status_blocker_consistency")
        for key in ("canonical_input_sha256", "decision_sha256"):
            if not _conditions_shadow_is_sha256(case.get(key)):
                errors.append(f"{prefix}.{key}")
        deterministic = case.get("deterministic")
        passed = case.get("passed")
        if not isinstance(deterministic, bool):
            errors.append(f"{prefix}.deterministic")
        if not isinstance(passed, bool):
            errors.append(f"{prefix}.passed")
        else:
            passed_flags.append(passed)
        for key in CONDITIONS_SHADOW_FALSE_FLAGS:
            if case.get(key) is not False:
                errors.append(f"{prefix}.{key}")
        ledger_empty = _conditions_shadow_empty_ledger(case)
        if not ledger_empty:
            errors.append(f"{prefix}.intrusive_actions_performed")
        expected_passed = bool(
            deterministic is True
            and expected_status == actual_status
            and expected_blockers_valid
            and blockers_valid
            and expected_blockers == blockers
            and _conditions_shadow_false_flags(case)
            and ledger_empty
        )
        if isinstance(passed, bool) and passed is not expected_passed:
            errors.append(f"{prefix}.passed_consistency")

    if len(counts) == 3 and isinstance(cases, list) and len(cases) <= 128:
        total_count = counts["total_count"]
        passed_count = counts["passed_count"]
        failed_count = counts["failed_count"]
        if total_count != len(cases):
            errors.append("scenario_pack.total_count_consistency")
        if total_count == 0:
            if not (
                passed_count == 0
                and failed_count == 1
                and status == "failed"
                and cases == []
            ):
                errors.append("scenario_pack.empty_failure_consistency")
        else:
            actual_passed_count = sum(value is True for value in passed_flags)
            actual_failed_count = len(cases) - actual_passed_count
            if passed_count != actual_passed_count:
                errors.append("scenario_pack.passed_count_consistency")
            if failed_count != actual_failed_count:
                errors.append("scenario_pack.failed_count_consistency")
            expected_pack_status = (
                "passed" if actual_passed_count == len(cases) else "failed"
            )
            if status != expected_pack_status:
                errors.append("scenario_pack.status_count_consistency")
    return errors


def _conditions_shadow_contract_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(payload) != CONDITIONS_SHADOW_REPORT_KEYS:
        errors.append("report.exact_keys")
    if payload.get("schema_version") != CONDITIONS_SHADOW_REPORT_SCHEMA:
        errors.append("report.schema_version")
    if payload.get("mode") != CONDITIONS_SHADOW_MODE:
        errors.append("report.mode")
    generated_at = payload.get("generated_at_unix_ms")
    if not _conditions_shadow_is_int(generated_at) or generated_at <= 0:
        errors.append("report.generated_at_unix_ms")
    operational_status = payload.get("operational_acceptance_status")
    if not _conditions_shadow_is_allowed(
        operational_status, CONDITIONS_SHADOW_OPERATIONAL_STATUS_VALUES
    ):
        errors.append("report.operational_acceptance_status")
    scenario_status = payload.get("scenario_pack_status")
    if not _conditions_shadow_is_allowed(
        scenario_status, CONDITIONS_SHADOW_SCENARIO_STATUS_VALUES
    ):
        errors.append("report.scenario_pack_status")
    if not isinstance(payload.get("fixture_only_validation_passed"), bool):
        errors.append("report.fixture_only_validation_passed")
    if payload.get("runtime_readiness_claimed") is not False:
        errors.append("report.runtime_readiness_claimed")
    for key in CONDITIONS_SHADOW_FALSE_FLAGS:
        if payload.get(key) is not False:
            errors.append(f"report.{key}")
    if not _conditions_shadow_empty_ledger(payload):
        errors.append("report.intrusive_actions_performed")

    trace = payload.get("operational_trace")
    if not isinstance(trace, dict):
        errors.append("report.operational_trace")
    else:
        errors.extend(_conditions_shadow_trace_errors(trace, generated_at))
    scenario_pack = payload.get("scenario_pack")
    if not isinstance(scenario_pack, dict):
        errors.append("report.scenario_pack")
    else:
        errors.extend(_conditions_shadow_scenario_errors(scenario_pack))

    if isinstance(scenario_pack, dict):
        pack_status = scenario_pack.get("status")
        if scenario_status != pack_status:
            errors.append("report.scenario_pack_status_consistency")
        if payload.get("fixture_only_validation_passed") is not (
            pack_status == "passed"
        ):
            errors.append("report.fixture_validation_consistency")
    if isinstance(trace, dict) and isinstance(scenario_pack, dict):
        expected_operational_status = (
            "shadow_plan_ready_for_operator_review"
            if trace.get("status") == "shadow_plan_ready"
            and scenario_pack.get("status") == "passed"
            else "operational_acceptance_blocked"
        )
        if operational_status != expected_operational_status:
            errors.append("report.operational_status_consistency")
    return _conditions_shadow_unique_errors(errors)


def _conditions_shadow_summary(
    payload: dict[str, Any] | None,
    path: Path,
    *,
    now: dt.datetime | None = None,
    artifact_present: bool | None = None,
) -> dict[str, Any]:
    present = payload is not None if artifact_present is None else artifact_present
    data = payload if isinstance(payload, dict) else {}
    if not isinstance(payload, dict):
        errors = ["report.unreadable_or_malformed"]
    elif not _json_shape_within_bounds(payload):
        errors = ["report.structure_bounds"]
    else:
        errors = _conditions_shadow_contract_errors(data)
    contract_valid = payload is not None and not errors
    generated_at = data.get("generated_at_unix_ms")
    observed_at = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    age_seconds = (
        (observed_at.timestamp() * 1000 - generated_at) / 1000
        if _conditions_shadow_is_int(generated_at) and generated_at > 0
        else None
    )
    timestamp_fresh = bool(
        age_seconds is not None
        and 0 <= age_seconds <= CONDITIONS_SHADOW_MAX_AGE_SECONDS
    )
    fresh = contract_valid and timestamp_fresh
    reported_status = data.get("operational_acceptance_status")
    reported_status_valid = _conditions_shadow_is_allowed(
        reported_status, CONDITIONS_SHADOW_OPERATIONAL_STATUS_VALUES
    )
    if not present:
        effective_status = "missing"
    elif not contract_valid:
        effective_status = "invalid"
    elif not fresh:
        effective_status = "stale"
    else:
        effective_status = str(reported_status)

    trace = (
        data.get("operational_trace")
        if isinstance(data.get("operational_trace"), dict)
        else {}
    )
    scenario_pack = (
        data.get("scenario_pack") if isinstance(data.get("scenario_pack"), dict) else {}
    )
    blockers = trace.get("blockers")
    safe_blockers = (
        list(blockers) if _conditions_shadow_blockers_valid(blockers) else []
    )
    fixture_pack_passed = bool(
        contract_valid
        and data.get("fixture_only_validation_passed") is True
        and scenario_pack.get("status") == "passed"
    )
    safe_count_values: dict[str, int] = {}
    for key in ("total_count", "passed_count", "failed_count"):
        value = scenario_pack.get(key)
        safe_count_values[key] = (
            value if _conditions_shadow_is_int(value) and value >= 0 else 0
        )
    return {
        "status": effective_status,
        "reported_status": reported_status if reported_status_valid else "invalid",
        "mode": data.get("mode")
        if data.get("mode") == CONDITIONS_SHADOW_MODE
        else "invalid",
        "generated_at_unix_ms": generated_at
        if _conditions_shadow_is_int(generated_at) and generated_at > 0
        else 0,
        "max_age_seconds": CONDITIONS_SHADOW_MAX_AGE_SECONDS,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "fresh": fresh,
        "contract_valid": contract_valid,
        "contract_errors": errors,
        "trace_status": trace.get("status")
        if _conditions_shadow_is_allowed(
            trace.get("status"), CONDITIONS_SHADOW_TRACE_STATUS_VALUES
        )
        else "invalid",
        "decision": trace.get("decision") if contract_valid else "hold",
        "blockers": safe_blockers if contract_valid else [],
        "operator_review_required": bool(
            contract_valid and trace.get("operator_review_required") is True
        ),
        "fixture_validation_status": scenario_pack.get("status")
        if _conditions_shadow_is_allowed(
            scenario_pack.get("status"), CONDITIONS_SHADOW_SCENARIO_STATUS_VALUES
        )
        else "invalid",
        "fixture_only_validation_passed": fixture_pack_passed,
        "fixture_total_count": safe_count_values["total_count"],
        "fixture_passed_count": safe_count_values["passed_count"],
        "fixture_failed_count": safe_count_values["failed_count"],
        "runtime_readiness_claimed": False,
        **{key: False for key in CONDITIONS_SHADOW_FALSE_FLAGS},
        "intrusive_actions_performed": [],
        "path": str(path).replace("\\", "/"),
    }


def _equipment_shadow_summary(
    payload: dict[str, Any] | None,
    path: Path,
    *,
    now: dt.datetime | None = None,
    artifact_present: bool | None = None,
) -> dict[str, Any]:
    present = payload is not None if artifact_present is None else artifact_present
    data = payload if isinstance(payload, dict) else {}
    errors: list[str] = []
    expected_report_keys = {
        "schema_version",
        "generated_at_unix_ms",
        "mode",
        "operational_acceptance_status",
        "scenario_pack_status",
        "fixture_only_validation_passed",
        "runtime_readiness_claimed",
        "operational_trace",
        "scenario_pack",
        *EQUIPMENT_SHADOW_FALSE_FLAGS,
        "intrusive_actions_performed",
    }
    expected_trace_keys = {
        "schema_version",
        "status",
        "decision",
        "action",
        "blockers",
        "canonical_input_sha256",
        "plan",
        "rollback_simulation",
        *EQUIPMENT_SHADOW_FALSE_FLAGS,
        "intrusive_actions_performed",
        "trace_id",
        "source",
        "evaluated_at_unix_ms",
        "input_sha256",
        "decision_sha256",
        "observation_age_ms",
        "operator_review_required",
    }
    expected_scenario_keys = {
        "status",
        "scenario_pack_sha256",
        "total_count",
        "passed_count",
        "failed_count",
        "cases",
        *EQUIPMENT_SHADOW_FALSE_FLAGS,
        "intrusive_actions_performed",
    }
    expected_case_keys = {
        "name",
        "mutation",
        "expected_status",
        "actual_status",
        "expected_blockers",
        "blockers",
        "decision_sha256",
        "deterministic",
        "passed",
        *EQUIPMENT_SHADOW_FALSE_FLAGS,
        "intrusive_actions_performed",
    }

    def valid_sha(value: Any) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
        )

    def valid_trace(value: Any) -> bool:
        if not isinstance(value, dict) or set(value) != expected_trace_keys:
            return False
        if value.get("schema_version") != "ctoa.equipment-shadow-trace.v1":
            return False
        decision_sha = value.get("decision_sha256")
        if (
            not valid_sha(decision_sha)
            or value.get("trace_id") != f"equipment-shadow-{decision_sha[:16]}"
        ):
            return False
        if value.get("status") not in {
            "shadow_plan_ready",
            "operational_acceptance_blocked",
        }:
            return False
        if (
            value.get("decision") not in {"would_plan_ring_swap", "hold"}
            or value.get("action") != "plan_ring_swap"
        ):
            return False
        if not isinstance(value.get("blockers"), list) or not all(
            isinstance(item, str) for item in value["blockers"]
        ):
            return False
        if not valid_sha(value.get("canonical_input_sha256")) or not valid_sha(
            value.get("decision_sha256")
        ):
            return False
        if (
            value.get("rollback_simulation") not in {"ready", "blocked"}
            or value.get("operator_review_required") is not True
        ):
            return False
        if (
            any(value.get(key) is not False for key in EQUIPMENT_SHADOW_FALSE_FLAGS)
            or value.get("intrusive_actions_performed") != []
        ):
            return False
        if value.get("status") == "shadow_plan_ready" and (
            value["blockers"]
            or value["decision"] != "would_plan_ring_swap"
            or value["rollback_simulation"] != "ready"
        ):
            return False
        if value.get("status") == "operational_acceptance_blocked" and (
            value["decision"] != "hold" or value["rollback_simulation"] != "blocked"
        ):
            return False
        plan = value.get("plan")
        if value.get("status") == "shadow_plan_ready":
            expected_plan_keys = {
                "action",
                "slot",
                "before_item_id",
                "candidate_item_id",
                "rollback_item_id",
                "source_container_id",
                "source_slot_index",
                "rollback_container_id",
                "rollback_slot_index",
                "inventory_revision",
                "rollback_inventory_revision",
                "retry_budget",
                "dispatch_allowed",
            }
            if (
                not isinstance(plan, dict)
                or set(plan) != expected_plan_keys
                or plan.get("action") != "plan_ring_swap"
                or plan.get("slot") != "ring"
                or plan.get("dispatch_allowed") is not False
                or plan.get("retry_budget") != 0
                or plan.get("rollback_item_id") != plan.get("before_item_id")
                or plan.get("candidate_item_id") == plan.get("before_item_id")
                or plan.get("source_container_id") != plan.get("rollback_container_id")
                or plan.get("source_slot_index") != plan.get("rollback_slot_index")
                or plan.get("inventory_revision")
                != plan.get("rollback_inventory_revision")
            ):
                return False
        elif plan is not None:
            return False
        return (
            isinstance(value.get("input_sha256"), dict)
            and set(value["input_sha256"])
            == {"profile", "snapshot", "p9_trace", "p9_receipt"}
            and all(valid_sha(item) for item in value["input_sha256"].values())
        )

    def valid_scenario(value: Any) -> bool:
        if not isinstance(value, dict) or set(value) != expected_scenario_keys:
            return False
        if value.get("status") not in {"passed", "failed"} or not isinstance(
            value.get("cases"), list
        ):
            return False
        if (
            not valid_sha(value.get("scenario_pack_sha256"))
            or value.get("scenario_pack_sha256") == "0" * 64
        ):
            return False
        if (
            any(value.get(key) is not False for key in EQUIPMENT_SHADOW_FALSE_FLAGS)
            or value.get("intrusive_actions_performed") != []
        ):
            return False
        mutations: set[str] = set()
        for case in value["cases"]:
            if not isinstance(case, dict) or set(case) != expected_case_keys:
                return False
            if not isinstance(case.get("blockers"), list) or not isinstance(
                case.get("expected_blockers"), list
            ):
                return False
            if (
                not valid_sha(case.get("decision_sha256"))
                or case.get("deterministic") is not True
                or case.get("passed") is not True
            ):
                return False
            if (
                any(case.get(key) is not False for key in EQUIPMENT_SHADOW_FALSE_FLAGS)
                or case.get("intrusive_actions_performed") != []
            ):
                return False
            mutation = case.get("mutation")
            if (
                mutation not in EQUIPMENT_SHADOW_REQUIRED_MUTATIONS
                or mutation in mutations
            ):
                return False
            mutations.add(mutation)
        return (
            value.get("failed_count") == 0
            and value.get("passed_count")
            == value.get("total_count")
            == len(value["cases"])
            == 30
            and mutations == EQUIPMENT_SHADOW_REQUIRED_MUTATIONS
        )

    if not isinstance(payload, dict):
        errors.append("report.unreadable_or_malformed")
    else:
        if set(data) != expected_report_keys:
            errors.append("report.keys")
        if data.get("schema_version") != EQUIPMENT_SHADOW_REPORT_SCHEMA:
            errors.append("report.schema_version")
        if data.get("mode") != EQUIPMENT_SHADOW_MODE:
            errors.append("report.mode")
        if data.get("runtime_readiness_claimed") is not False:
            errors.append("report.runtime_readiness_claimed")
        if any(data.get(key) is not False for key in EQUIPMENT_SHADOW_FALSE_FLAGS):
            errors.append("report.unsafe_action_contract")
        if data.get("intrusive_actions_performed") != []:
            errors.append("report.intrusive_actions_performed")
        trace = data.get("operational_trace")
        scenario = data.get("scenario_pack")
        if not valid_trace(trace):
            errors.append("report.operational_trace")
        if not valid_scenario(scenario):
            errors.append("report.scenario_pack")
    generated_at = data.get("generated_at_unix_ms")
    observed_at = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    age_seconds = (
        (observed_at.timestamp() * 1000 - generated_at) / 1000
        if isinstance(generated_at, int)
        and not isinstance(generated_at, bool)
        and generated_at > 0
        else None
    )
    fresh = bool(
        age_seconds is not None and 0 <= age_seconds <= EQUIPMENT_SHADOW_MAX_AGE_SECONDS
    )
    contract_valid = present and not errors
    if not present:
        status = "missing"
    elif not contract_valid:
        status = "invalid"
    elif not fresh:
        status = "stale"
    else:
        status = data.get("operational_acceptance_status", "invalid")
        if status not in EQUIPMENT_SHADOW_STATUS_VALUES:
            status = "invalid"
    trace = (
        data.get("operational_trace")
        if isinstance(data.get("operational_trace"), dict)
        else {}
    )
    scenario = (
        data.get("scenario_pack") if isinstance(data.get("scenario_pack"), dict) else {}
    )
    return {
        "status": status,
        "reported_status": data.get("operational_acceptance_status", "invalid"),
        "mode": data.get("mode")
        if data.get("mode") == EQUIPMENT_SHADOW_MODE
        else "invalid",
        "generated_at_unix_ms": generated_at
        if isinstance(generated_at, int) and generated_at > 0
        else 0,
        "max_age_seconds": EQUIPMENT_SHADOW_MAX_AGE_SECONDS,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "fresh": fresh,
        "contract_valid": contract_valid,
        "contract_errors": errors,
        "trace_status": trace.get("status", "invalid"),
        "decision": trace.get("decision", "hold"),
        "blockers": trace.get("blockers", [])
        if isinstance(trace.get("blockers"), list)
        else [],
        "rollback_simulation": trace.get("rollback_simulation", "blocked"),
        "fixture_validation_status": scenario.get("status", "invalid"),
        "fixture_only_validation_passed": bool(
            contract_valid and scenario.get("status") == "passed"
        ),
        "runtime_readiness_claimed": False,
        **{key: False for key in EQUIPMENT_SHADOW_FALSE_FLAGS},
        "intrusive_actions_performed": [],
        "path": str(path).replace("\\", "/"),
    }


def _equipment_shadow_acceptance_summary(
    payload: dict[str, Any] | None,
    path: Path,
    equipment_report: dict[str, Any] | None,
    *,
    now: dt.datetime | None = None,
    artifact_present: bool | None = None,
) -> dict[str, Any]:
    present = payload is not None if artifact_present is None else artifact_present
    data = payload if isinstance(payload, dict) else {}
    receipt_contract_valid = bool(
        present and equipment_acceptance._receipt_contract(data)  # noqa: SLF001
    )
    created_at = data.get("created_at_unix_ms")
    observed_at = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    age_seconds = (
        (observed_at.timestamp() * 1000 - created_at) / 1000
        if isinstance(created_at, int)
        and not isinstance(created_at, bool)
        and created_at > 0
        else None
    )
    fresh = bool(
        receipt_contract_valid
        and age_seconds is not None
        and 0 <= age_seconds <= EQUIPMENT_SHADOW_MAX_AGE_SECONDS
    )
    report_sha = (
        _conditions_shadow_canonical_sha256(equipment_report)
        if isinstance(equipment_report, dict)
        else ""
    )
    report_hash_match = bool(
        receipt_contract_valid
        and report_sha
        and data.get("report_sha256") == report_sha
        and data.get("recomputed_report_sha256") == report_sha
    )
    report_summary = _equipment_shadow_summary(
        equipment_report,
        path.with_name("equipment_shadow_replay.json"),
        now=observed_at,
        artifact_present=isinstance(equipment_report, dict),
    )
    report_ready = bool(
        report_summary.get("contract_valid") is True
        and report_summary.get("fresh") is True
        and report_summary.get("status") == "shadow_plan_ready_for_operator_review"
        and report_summary.get("trace_status") == "shadow_plan_ready"
        and report_summary.get("decision") == "would_plan_ring_swap"
        and report_summary.get("blockers") == []
        and report_summary.get("rollback_simulation") == "ready"
        and report_summary.get("fixture_validation_status") == "passed"
        and report_summary.get("fixture_only_validation_passed") is True
    )
    contract_valid = bool(receipt_contract_valid and report_ready)
    accepted = bool(
        contract_valid
        and fresh
        and report_hash_match
        and data.get("status") == "accepted"
        and data.get("acceptance_granted") is True
        and data.get("receipt_persisted") is True
        and data.get("operational_inputs_fixture") is False
        and data.get("canonical_operational_paths") is True
    )
    if not present:
        status = "missing"
    elif not contract_valid or not report_hash_match:
        status = "invalid"
    elif not fresh:
        status = "stale"
    else:
        status = str(data.get("status") or "invalid")
    return {
        "status": status,
        "contract_valid": contract_valid,
        "fresh": fresh,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "report_hash_match": report_hash_match,
        "acceptance_granted": accepted,
        "receipt_persisted": data.get("receipt_persisted") is True,
        "operator_review_completed": data.get("operator_review_completed") is True,
        "operational_inputs_fixture": data.get("operational_inputs_fixture") is True,
        "canonical_operational_paths": data.get("canonical_operational_paths") is True,
        "p11_predecessor_eligible": accepted,
        "blockers": list(data.get("blockers") or [])
        if isinstance(data.get("blockers"), list)
        else [],
        "runtime_readiness_claimed": False,
        **{key: False for key in EQUIPMENT_SHADOW_FALSE_FLAGS},
        "intrusive_actions_performed": [],
        "path": str(path).replace("\\", "/"),
    }


def _p12_plan_contract_valid(
    payload: dict[str, Any] | None,
    *,
    schema: str,
    basis_keys: tuple[str, ...],
) -> bool:
    data = payload if isinstance(payload, dict) else {}
    blockers = data.get("blockers")
    status = data.get("status")
    plan_sha = data.get("plan_sha256")
    basis = {key: data.get(key) for key in basis_keys}
    return bool(
        data.get("schema_version") == schema
        and isinstance(plan_sha, str)
        and CONDITIONS_SHADOW_SHA256_RE.fullmatch(plan_sha)
        and plan_sha == _conditions_shadow_canonical_sha256(basis)
        and status in {"blocked", "ready_for_sandbox_session_approval"}
        and isinstance(blockers, list)
        and len(blockers) == len(set(blockers))
        and all(isinstance(item, str) and item for item in blockers)
        and (
            (status == "blocked" and bool(blockers))
            or (status != "blocked" and not blockers)
        )
        and data.get("attempt_count") == 0
        and data.get("session_approved") is False
        and data.get("execution_approved") is False
        and data.get("final_state") == "disarmed"
        and all(data.get(flag) is False for flag in P12_SAFE_PLAN_FLAGS)
        and data.get("intrusive_actions_performed") == []
    )


def _deterministic_receipt_matches(
    actual: dict[str, Any], expected: dict[str, Any], receipt_prefix: str
) -> bool:
    receipt_id = actual.get("receipt_id")
    return bool(
        set(actual) == set(expected)
        and isinstance(receipt_id, str)
        and re.fullmatch(rf"{re.escape(receipt_prefix)}[0-9a-f]{{16}}", receipt_id)
        and all(
            actual.get(key) == value
            for key, value in expected.items()
            if key != "receipt_id"
        )
    )


def _p12_conditions_summary(
    plan: dict[str, Any] | None,
    approval: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    plan_data = plan if isinstance(plan, dict) else {}
    approval_data = approval if isinstance(approval, dict) else {}
    trace_data = trace if isinstance(trace, dict) else {}
    receipt_data = receipt if isinstance(receipt, dict) else {}
    plan_contract_valid = _p12_plan_contract_valid(
        plan_data,
        schema=p12_conditions_receipt.plans.SCHEMA,
        basis_keys=P12_CONDITIONS_PLAN_BASIS_KEYS,
    )
    created_at = receipt_data.get("created_at_unix_ms")
    expected: dict[str, Any] = {}
    if isinstance(created_at, int) and not isinstance(created_at, bool):
        expected = p12_conditions_receipt.build_receipt(
            plan_data,
            approval_data,
            trace_data,
            now_ms=created_at,
        )
    contract_valid = bool(
        plan_contract_valid
        and expected
        and _deterministic_receipt_matches(receipt_data, expected, "p12-conditions-")
    )
    accepted = bool(
        contract_valid
        and receipt_data.get("status") == "accepted"
        and receipt_data.get("acceptance_granted") is True
        and receipt_data.get("attempt_count") == 1
        and receipt_data.get("retry_scheduled") is False
        and receipt_data.get("final_state") == "killed_and_disarmed"
        and receipt_data.get("downstream_authority_granted") is False
    )
    return {
        "status": "operational_acceptance_complete"
        if accepted
        else "operational_acceptance_blocked",
        "contract_valid": contract_valid,
        "acceptance_granted": accepted,
        "plan_sha256": str(receipt_data.get("plan_sha256") or ""),
        "receipt_id": str(receipt_data.get("receipt_id") or ""),
        "attempt_count": int(receipt_data.get("attempt_count") or 0),
        "retry_scheduled": receipt_data.get("retry_scheduled") is True,
        "final_state": str(receipt_data.get("final_state") or "unknown"),
        "downstream_authority_granted": receipt_data.get("downstream_authority_granted")
        is True,
        "blockers": list(receipt_data.get("blockers") or [])
        if isinstance(receipt_data.get("blockers"), list)
        else ["receipt_invalid"],
    }


def _p12_equipment_summary(
    current_plan: dict[str, Any] | None,
    approval: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    plan_data = current_plan if isinstance(current_plan, dict) else {}
    approval_data = approval if isinstance(approval, dict) else {}
    trace_data = trace if isinstance(trace, dict) else {}
    receipt_data = receipt if isinstance(receipt, dict) else {}
    current_plan_contract_valid = _p12_plan_contract_valid(
        plan_data,
        schema=p12_equipment_receipt.plans.SCHEMA,
        basis_keys=P12_EQUIPMENT_PLAN_BASIS_KEYS,
    )
    if plan_data.get("plan_sha256") == receipt_data.get("plan_sha256"):
        # The current Registry v1 plan was consumed. Recompute the receipt from
        # the exact persisted plan, including transformed 3099/3093
        # postconditions, instead of weakening it to the legacy contract.
        consumed_plan = plan_data
    else:
        # Preserve deterministic validation for the earlier consumed attempt,
        # whose rejected receipt predates the Registry v1 transformed-state
        # contract. A corrected replacement plan must remain distinct from it.
        consumed_plan = {
            "plan_sha256": receipt_data.get("plan_sha256"),
            "p10_receipt_sha256": receipt_data.get("p10_receipt_sha256"),
            "before_item_id": receipt_data.get("before_item_id"),
            "candidate_item_id": receipt_data.get("candidate_item_id"),
            "source_container_id": trace_data.get("source_container_id"),
            "source_slot_index": trace_data.get("source_slot_index"),
            "requires_post_action_ring_id": receipt_data.get("candidate_item_id"),
            "rollback_item_id": receipt_data.get("before_item_id"),
        }
    created_at = receipt_data.get("created_at_unix_ms")
    expected: dict[str, Any] = {}
    if isinstance(created_at, int) and not isinstance(created_at, bool):
        expected = p12_equipment_receipt.build_receipt(
            consumed_plan,
            approval_data,
            trace_data,
            now_ms=created_at,
        )
    receipt_contract_valid = bool(
        expected
        and _deterministic_receipt_matches(receipt_data, expected, "p12-equipment-")
    )
    terminal = (
        trace_data.get("terminal_snapshot")
        if isinstance(trace_data.get("terminal_snapshot"), dict)
        else {}
    )
    consumed_attempt = bool(
        receipt_contract_valid
        and trace_data.get("attempt_count") == 1
        and trace_data.get("retry_scheduled") is False
        and trace_data.get("final_state") == "killed_and_disarmed"
        and terminal.get("armed") is False
        and terminal.get("killed") is True
        and terminal.get("consumed") is True
        and terminal.get("attempt_count") == 1
    )
    accepted = bool(
        receipt_contract_valid
        and consumed_attempt
        and receipt_data.get("status") == "accepted"
        and receipt_data.get("acceptance_granted") is True
        and receipt_data.get("attempt_count") == 1
        and receipt_data.get("retry_scheduled") is False
        and receipt_data.get("final_state") == "killed_and_disarmed"
        and receipt_data.get("downstream_authority_granted") is False
        and receipt_data.get("live_promotion") is False
    )
    replacement_plan_distinct = bool(
        current_plan_contract_valid
        and receipt_contract_valid
        and plan_data.get("plan_sha256") != receipt_data.get("plan_sha256")
    )
    current_plan_safe = bool(
        current_plan_contract_valid
        and plan_data.get("attempt_count") == 0
        and plan_data.get("session_approved") is False
        and plan_data.get("execution_approved") is False
        and plan_data.get("final_state") == "disarmed"
        and all(plan_data.get(flag) is False for flag in P12_SAFE_PLAN_FLAGS)
        and plan_data.get("intrusive_actions_performed") == []
    )
    return {
        "status": "operational_acceptance_complete"
        if accepted
        else "operational_acceptance_blocked",
        "receipt_status": str(receipt_data.get("status") or "missing"),
        "receipt_contract_valid": receipt_contract_valid,
        "acceptance_granted": accepted,
        "consumed_attempt": consumed_attempt,
        "consumed_plan_sha256": str(receipt_data.get("plan_sha256") or ""),
        "consumed_receipt_id": str(receipt_data.get("receipt_id") or ""),
        "current_plan_status": str(plan_data.get("status") or "missing"),
        "current_plan_contract_valid": current_plan_contract_valid,
        "current_plan_safe": current_plan_safe,
        "current_plan_sha256": str(plan_data.get("plan_sha256") or ""),
        "current_plan_blockers": list(plan_data.get("blockers") or [])
        if isinstance(plan_data.get("blockers"), list)
        else ["plan_invalid"],
        "replacement_plan_distinct": replacement_plan_distinct,
        "attempt_count": int(
            receipt_data.get("attempt_count")
            if accepted
            else plan_data.get("attempt_count") or 0
        ),
        "session_approved": (
            approval_data.get("session_approved") is True
            if accepted
            else plan_data.get("session_approved") is True
        ),
        "execution_approved": (
            approval_data.get("execution_approved") is True
            if accepted
            else plan_data.get("execution_approved") is True
        ),
        "final_state": str(
            receipt_data.get("final_state")
            if accepted
            else plan_data.get("final_state") or "unknown"
        ),
        "downstream_authority_granted": receipt_data.get("downstream_authority_granted")
        is True,
    }


def _heal_friend_acceptance_contract_valid(payload: dict[str, Any] | None) -> bool:
    data = payload if isinstance(payload, dict) else {}
    try:
        basis = heal_friend_acceptance._receipt_basis(data)  # noqa: SLF001
    except KeyError:
        return False
    basis_sha = _conditions_shadow_canonical_sha256(basis)
    return bool(
        data.get("schema_version") == heal_friend_acceptance.SCHEMA
        and data.get("status") == "accepted"
        and data.get("acceptance_granted") is True
        and data.get("receipt_persisted") is True
        and data.get("operator_review_completed") is True
        and data.get("downstream_use_requires_separate_review") is True
        and data.get("blockers") == []
        and data.get("operational_inputs_fixture") is False
        and data.get("runtime_readiness_claimed") is False
        and all(
            data.get(flag) is False
            for flag in heal_friend_acceptance.replay.FALSE_FLAGS
        )
        and data.get("intrusive_actions_performed") == []
        and data.get("acceptance_basis_sha256") == basis_sha
        and data.get("receipt_id") == f"heal-friend-shadow-acceptance-{basis_sha[:16]}"
    )


def _safe_raw_sha256(path: Path, *, max_bytes: int = MAX_EVIDENCE_JSON_BYTES) -> str:
    file_stat = _safe_file_stat(path)
    if file_stat is None or file_stat.st_size > max_bytes:
        return ""
    try:
        with path.open("rb") as handle:
            opened_stat = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(opened_stat.st_mode)
                or opened_stat.st_size != file_stat.st_size
            ):
                return ""
            raw = handle.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return ""
            final_stat = os.fstat(handle.fileno())
            if (
                final_stat.st_size != opened_stat.st_size
                or final_stat.st_mtime_ns != opened_stat.st_mtime_ns
            ):
                return ""
    except OSError:
        return ""
    return hashlib.sha256(raw).hexdigest()


def _p12_heal_friend_closure_summary(
    payload: dict[str, Any] | None,
    *,
    artifact_present: bool,
    plan_path: Path,
    approval_path: Path,
    preflight_path: Path,
) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    bindings = {
        "plan": _safe_raw_sha256(plan_path),
        "approval": _safe_raw_sha256(approval_path),
        "preflight": _safe_raw_sha256(preflight_path),
    }
    false_flags = (
        "dispatch_allowed",
        "runtime_actions",
        "execute_once_allowed",
        "live_promotion",
        "downstream_authority_granted",
        "retry_scheduled",
        "execution_approval_permitted",
        "session_approval_reusable",
        "cast_performed",
        "talk_performed",
    )
    vocations = data.get("operator_declared_available_vocations")
    blockers = data.get("validation_blockers")
    contract_valid = bool(
        artifact_present
        and data.get("schema_version")
        == "ctoa.p12-heal-friend-no-compatible-vocation-closure.v1"
        and data.get("status") == "closed_blocked_no_compatible_vocation"
        and data.get("closure_granted") is True
        and data.get("session_approval_expired") is True
        and all(data.get(flag) is False for flag in false_flags)
        and data.get("attempt_count") == 0
        and data.get("retry_budget") == 0
        and data.get("final_state") == "disarmed"
        and data.get("intrusive_actions_performed") == []
        and blockers == []
        and data.get("closure_reason") == "no_compatible_sandbox_vocation"
        and data.get("required_vocation") == "ed"
        and isinstance(vocations, list)
        and bool(vocations)
        and "ed" not in vocations
        and all(isinstance(item, str) and item for item in vocations)
        and bool(bindings["plan"])
        and bool(bindings["approval"])
        and bool(bindings["preflight"])
        and data.get("plan_file_sha256") == bindings["plan"]
        and data.get("approval_file_sha256") == bindings["approval"]
        and data.get("preflight_file_sha256") == bindings["preflight"]
    )
    status = (
        "closed_blocked_no_compatible_vocation"
        if contract_valid
        else ("invalid" if artifact_present else "missing")
    )
    return {
        "status": status,
        "contract_valid": contract_valid,
        "closure_granted": data.get("closure_granted") is True,
        "closure_reason": str(data.get("closure_reason") or ""),
        "attempt_count": data.get("attempt_count")
        if isinstance(data.get("attempt_count"), int)
        else None,
        "retry_scheduled": data.get("retry_scheduled") is True,
        "final_state": str(data.get("final_state") or ""),
        "required_vocation": str(data.get("required_vocation") or ""),
        "available_vocations": [str(item) for item in vocations]
        if isinstance(vocations, list)
        else [],
        "downstream_authority_granted": data.get("downstream_authority_granted")
        is True,
        "runtime_actions": data.get("runtime_actions") is True,
        "live_promotion": data.get("live_promotion") is True,
        "binding_status": "passed"
        if contract_valid
        else ("blocked" if artifact_present else "missing"),
        "blockers": []
        if contract_valid
        else (["p12_heal_friend_closure_invalid"] if artifact_present else []),
    }


def _roadmap_state_contract_valid(payload: dict[str, Any] | None) -> bool:
    data = payload if isinstance(payload, dict) else {}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    authority = data.get("authority") if isinstance(data.get("authority"), dict) else {}
    registry = (
        data.get("schema_registry")
        if isinstance(data.get("schema_registry"), dict)
        else {}
    )
    preflight = (
        data.get("control_center_preflight")
        if isinstance(data.get("control_center_preflight"), dict)
        else {}
    )
    ledger = data.get("ledger") if isinstance(data.get("ledger"), list) else []
    source_health = (
        data.get("source_health") if isinstance(data.get("source_health"), list) else []
    )
    expected_ids = [
        "p8-background-acceptance",
        "p9-conditions-shadow-acceptance",
        "p10-equipment-shadow-acceptance",
        "p11-heal-friend-shadow-acceptance",
        "p12-conditions-execute-once",
        "p12-equipment-execute-once",
        "p12-heal-friend-no-compatible-vocation",
    ]
    expected_summary = {
        "ledger_count": 7,
        "accepted_count": 6,
        "closed_no_action_count": 1,
        "blocked_count": 0,
        "tampered_count": 0,
        "total_attempt_count": 2,
        "runtime_authority_count": 0,
        "live_authority_count": 0,
    }
    expected_outputs = [
        "AI/generated/ROADMAP_STATE.json",
        "AI/generated/ROADMAP_STATE.md",
        "runtime/control-center/action-audit.jsonl",
    ]
    state_sha = data.get("state_sha256")
    state_basis = {key: value for key, value in data.items() if key != "state_sha256"}
    return bool(
        data.get("schema_version") == "ctoa.roadmap-state.v2"
        and data.get("status") == "ready"
        and data.get("readiness_status") in {"ready", "awaiting_external"}
        and data.get("phase") == "P13"
        and data.get("phase_status") == "runtime_evidence_ready"
        and data.get("next_phase") == "P14"
        and data.get("freshness_status") == "current"
        and data.get("tamper_status") == "passed"
        and data.get("blockers") == []
        and isinstance(data.get("warnings"), list)
        and all(
            item == "runtime_module_gates_pending" for item in data.get("warnings", [])
        )
        and (
            (data.get("readiness_status") == "ready" and data.get("warnings") == [])
            or (
                data.get("readiness_status") == "awaiting_external"
                and data.get("warnings") == ["runtime_module_gates_pending"]
            )
        )
        and preflight.get("status") == "ready"
        and preflight.get("ready") is True
        and preflight.get("hard_blockers") == []
        and registry.get("status") == "passed"
        and registry.get("entry_count") == 7
        and len(source_health) >= 3
        and all(
            isinstance(item, dict)
            and (
                (
                    item.get("impact") == "required"
                    and item.get("availability") == "available"
                    and item.get("contract_status") == "passed"
                    and item.get("freshness_status") in {"current", "timeless"}
                )
                or (
                    item.get("impact") == "advisory"
                    and item.get("availability")
                    in {"available", "awaiting_external"}
                    and item.get("contract_status") in {"passed", "pending"}
                    and item.get("freshness_status")
                    in {"current", "stale", "timeless"}
                )
            )
            for item in source_health
        )
        and len(ledger) == 7
        and [item.get("decision_id") for item in ledger if isinstance(item, dict)]
        == expected_ids
        and all(
            isinstance(item, dict)
            and item.get("terminal") is True
            and item.get("integrity_status") == "passed"
            and item.get("freshness_status") == "immutable_terminal"
            and item.get("blockers") == []
            and item.get("downstream_authority_granted") is False
            and item.get("dispatch_allowed") is False
            and item.get("runtime_actions") is False
            and item.get("execute_once_allowed") is False
            and item.get("live_promotion") is False
            for item in ledger
        )
        and all(summary.get(key) == value for key, value in expected_summary.items())
        and authority.get("control_center_mode") == "read_only"
        and authority.get("runtime_executor_added") is False
        and authority.get("runtime_actions") is False
        and authority.get("live_authority") is False
        and authority.get("p12_heal_friend_reopened") is False
        and authority.get("runtime_mcp_write_tool_enabled") is False
        and authority.get("roadmap_refresh_tool_enabled") is True
        and authority.get("roadmap_refresh_risk_class") == "safe_write"
        and authority.get("allowed_output_paths") == expected_outputs
        and _conditions_shadow_is_sha256(state_sha)
        and _conditions_shadow_canonical_sha256(state_basis) == state_sha
    )


def _roadmap_state_audit_binding(
    action_audit_path: Path | None,
    *,
    actual_sha256: str,
) -> dict[str, str]:
    if action_audit_path is None or not actual_sha256:
        return {"status": "missing", "audit_id": "", "expected_sha256": ""}
    file_stat = _safe_file_stat(action_audit_path)
    if file_stat is None or file_stat.st_size <= 0:
        return {"status": "missing", "audit_id": "", "expected_sha256": ""}
    requested_bytes = min(file_stat.st_size, MAX_ACTION_AUDIT_BYTES)
    start = max(0, file_stat.st_size - requested_bytes)
    try:
        with action_audit_path.open("rb") as handle:
            opened_stat = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_stat.st_mode):
                return {"status": "missing", "audit_id": "", "expected_sha256": ""}
            handle.seek(start)
            raw = handle.read(requested_bytes)
    except OSError:
        return {"status": "missing", "audit_id": "", "expected_sha256": ""}
    text = raw.decode("utf-8-sig", errors="replace")
    if start > 0:
        _, _, text = text.partition("\n")
    for line in reversed(text.splitlines()):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(record, dict):
            continue
        output_hashes = (
            record.get("output_hashes")
            if isinstance(record.get("output_hashes"), dict)
            else {}
        )
        written_paths = (
            record.get("written_paths")
            if isinstance(record.get("written_paths"), list)
            else []
        )
        if (
            record.get("action") != "roadmap-state-refresh"
            or record.get("dry_run") is not False
            or "AI/generated/ROADMAP_STATE.json" not in written_paths
        ):
            continue
        expected_sha256 = str(
            output_hashes.get("AI/generated/ROADMAP_STATE.json") or ""
        )
        passed = bool(
            record.get("authorized") is True
            and record.get("ok") is True
            and expected_sha256 == actual_sha256
        )
        return {
            "status": "passed" if passed else "mismatch",
            "audit_id": str(record.get("audit_id") or ""),
            "expected_sha256": expected_sha256,
        }
    return {"status": "missing", "audit_id": "", "expected_sha256": ""}


def _roadmap_state_summary(
    payload: dict[str, Any] | None,
    *,
    artifact_present: bool,
    path: Path,
    action_audit_path: Path | None,
) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    file_sha256 = _safe_raw_sha256(path)
    contract_valid = artifact_present and _roadmap_state_contract_valid(data)
    audit_binding = _roadmap_state_audit_binding(
        action_audit_path,
        actual_sha256=file_sha256,
    )
    ready = contract_valid and audit_binding["status"] == "passed"
    return {
        "status": "runtime_evidence_ready"
        if ready
        else ("blocked" if artifact_present else "missing"),
        "contract_valid": contract_valid,
        "readiness_status": str(data.get("readiness_status") or "missing"),
        "warning_count": len(data.get("warnings", []))
        if isinstance(data.get("warnings"), list)
        else 0,
        "freshness_status": str(data.get("freshness_status") or "missing"),
        "tamper_status": str(data.get("tamper_status") or "missing"),
        "audit_binding_status": audit_binding["status"],
        "audit_id": audit_binding["audit_id"],
        "state_sha256": str(data.get("state_sha256") or ""),
        "file_sha256": file_sha256,
        "control_center_mode": str(
            (data.get("authority") or {}).get("control_center_mode") or ""
        )
        if isinstance(data.get("authority"), dict)
        else "",
        "runtime_authority_count": int(
            (data.get("summary") or {}).get("runtime_authority_count") or 0
        )
        if isinstance(data.get("summary"), dict)
        else 0,
        "live_authority_count": int(
            (data.get("summary") or {}).get("live_authority_count") or 0
        )
        if isinstance(data.get("summary"), dict)
        else 0,
        "blockers": []
        if ready
        else (["roadmap_state_or_audit_binding_invalid"] if artifact_present else []),
    }


def _roadmap_phase_state_summary(
    *,
    background: dict[str, Any],
    p9_receipt: dict[str, Any] | None,
    p10_receipt: dict[str, Any] | None,
    p11_receipt: dict[str, Any] | None,
    p12_conditions: dict[str, Any],
    p12_equipment: dict[str, Any],
    p12_heal_friend_artifact_present: bool,
    p12_heal_friend_closure: dict[str, Any] | None = None,
    roadmap_state: dict[str, Any] | None = None,
    p14_foundation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p8_complete = bool(
        background.get("contract_valid") is True
        and background.get("reported_status") == "ready"
        and background.get("integrity_status") == "passed"
        and background.get("capability_status") == "fresh"
        and background.get("blockers") == []
    )
    p9_complete = bool(
        isinstance(p9_receipt, dict)
        and conditions_acceptance._receipt_contract_valid(p9_receipt)  # noqa: SLF001
        and p9_receipt.get("status") == "accepted"
        and p9_receipt.get("acceptance_granted") is True
    )
    p10_complete = bool(
        isinstance(p10_receipt, dict)
        and equipment_acceptance._receipt_contract(p10_receipt)  # noqa: SLF001
        and p10_receipt.get("status") == "accepted"
        and p10_receipt.get("acceptance_granted") is True
    )
    p11_complete = _heal_friend_acceptance_contract_valid(p11_receipt)
    p12_conditions_complete = (
        p12_conditions.get("status") == "operational_acceptance_complete"
    )
    p12_equipment_status = str(
        p12_equipment.get("status") or "operational_acceptance_blocked"
    )
    closure = (
        p12_heal_friend_closure
        if isinstance(p12_heal_friend_closure, dict)
        else {
            "status": "review_required"
            if p12_heal_friend_artifact_present
            else "not_started",
            "contract_valid": False,
            "blockers": [],
        }
    )
    p12_heal_friend_status = str(closure.get("status") or "not_started")
    predecessor_states = {
        "p8": "operational_acceptance_complete"
        if p8_complete
        else "operational_acceptance_blocked",
        "p9": "operational_acceptance_complete"
        if p9_complete
        else "operational_acceptance_blocked",
        "p10": "operational_acceptance_complete"
        if p10_complete
        else "operational_acceptance_blocked",
        "p11": "operational_acceptance_complete"
        if p11_complete
        else "operational_acceptance_blocked",
    }
    equipment_blocked_boundary = bool(
        p12_equipment_status == "operational_acceptance_blocked"
        and p12_equipment.get("receipt_status") == "rejected"
        and p12_equipment.get("receipt_contract_valid") is True
        and p12_equipment.get("consumed_attempt") is True
        and p12_equipment.get("current_plan_status") == "blocked"
        and p12_equipment.get("current_plan_safe") is True
        and p12_equipment.get("replacement_plan_distinct") is True
    )
    equipment_complete_boundary = bool(
        p12_equipment_status == "operational_acceptance_complete"
        and p12_equipment.get("receipt_status") == "accepted"
        and p12_equipment.get("receipt_contract_valid") is True
        and p12_equipment.get("acceptance_granted") is True
        and p12_equipment.get("consumed_attempt") is True
        and p12_equipment.get("current_plan_status")
        == "ready_for_sandbox_session_approval"
        and p12_equipment.get("current_plan_safe") is True
        and p12_equipment.get("replacement_plan_distinct") is False
        and p12_equipment.get("attempt_count") == 1
        and p12_equipment.get("session_approved") is True
        and p12_equipment.get("execution_approved") is True
        and p12_equipment.get("final_state") == "killed_and_disarmed"
        and p12_equipment.get("downstream_authority_granted") is False
    )
    predecessor_complete = all(
        value == "operational_acceptance_complete"
        for value in predecessor_states.values()
    )
    closure_complete = bool(
        p12_heal_friend_status == "closed_blocked_no_compatible_vocation"
        and closure.get("contract_valid") is True
        and closure.get("attempt_count") == 0
        and closure.get("retry_scheduled") is False
        and closure.get("downstream_authority_granted") is False
        and closure.get("runtime_actions") is False
        and closure.get("live_promotion") is False
        and closure.get("blockers") == []
    )
    p12_complete = bool(
        predecessor_complete
        and p12_conditions_complete
        and equipment_complete_boundary
        and closure_complete
    )
    roadmap = (
        roadmap_state
        if isinstance(roadmap_state, dict)
        else {"status": "missing", "blockers": []}
    )
    roadmap_status = str(roadmap.get("status") or "missing")
    roadmap_ready = bool(
        roadmap_status == "runtime_evidence_ready"
        and roadmap.get("contract_valid") is True
        and roadmap.get("freshness_status") == "current"
        and roadmap.get("tamper_status") == "passed"
        and roadmap.get("audit_binding_status") == "passed"
        and roadmap.get("control_center_mode") == "read_only"
        and roadmap.get("runtime_authority_count") == 0
        and roadmap.get("live_authority_count") == 0
        and roadmap.get("blockers") == []
    )
    p14 = (
        p14_foundation
        if isinstance(p14_foundation, dict)
        else {
            "status": "missing",
            "contract_version": "ctoa.p14-runner-request.v1",
            "implementation_file_count": 0,
            "required_file_count": len(P14_FOUNDATION_PATHS),
            "operational_runner_result": "missing",
            "operational_ready": False,
            "runtime_authority_granted": False,
            "live_authority_granted": False,
            "promotion_approved": False,
            "mcp_write_tool_enabled": False,
            "blockers": ["p14_foundation_missing"],
        }
    )
    p14_foundation_ready = bool(
        p14.get("status") == "foundation_ready"
        and p14.get("implementation_file_count") == len(P14_FOUNDATION_PATHS)
        and p14.get("runtime_authority_granted") is False
        and p14.get("live_authority_granted") is False
        and p14.get("promotion_approved") is False
        and p14.get("mcp_write_tool_enabled") is False
        and p14.get("blockers") == []
    )
    legacy_p12_boundary = bool(
        predecessor_complete
        and p12_conditions_complete
        and (equipment_blocked_boundary or equipment_complete_boundary)
        and not closure_complete
    )
    aligned = bool(
        p12_complete
        and roadmap_status in {"missing", "runtime_evidence_ready"}
        and (not p14_foundation_ready or roadmap_ready)
    )
    status = (
        "p14_foundation_ready"
        if p12_complete and roadmap_ready and p14_foundation_ready
        else (
            "p13_runtime_evidence_ready"
            if p12_complete and roadmap_ready
            else (
                "p13_in_progress"
                if p12_complete and roadmap_status == "missing"
                else "needs_attention"
            )
        )
    )
    p13_status = (
        "runtime_evidence_ready"
        if roadmap_ready
        else (
            "implementation_in_progress"
            if p12_complete and roadmap_status == "missing"
            else "blocked"
        )
    )
    return {
        "status": status,
        "current_phase": "P14"
        if p14_foundation_ready and roadmap_ready
        else ("P13" if p12_complete else "P12"),
        "next_phase": "P14" if roadmap_ready else "P13",
        "aligned_with_current_roadmap": aligned,
        **predecessor_states,
        "p12": {
            "status": "complete"
            if p12_complete
            else (
                "legacy_boundary_incomplete"
                if legacy_p12_boundary
                else "needs_attention"
            ),
            "conditions": p12_conditions,
            "equipment": p12_equipment,
            "heal_friend": closure,
        },
        "p13": {
            "status": p13_status,
            "roadmap_state": roadmap,
            "control_center_mode": "read_only",
            "runtime_authority_granted": False,
            "live_authority_granted": False,
        },
        "p14": p14,
    }


def _p14_runner_preflight_summary(root: Path) -> dict[str, Any]:
    payload = _read_json_strict_or_none(root / P14_RUNNER_PREFLIGHT_PATH)
    if not isinstance(payload, dict):
        return {
            "status": "missing",
            "fresh": False,
            "contract_valid": False,
            "operational_result": "missing",
            "operational_ready": False,
            "hard_blockers": ["p14_runner_preflight_missing"],
            "warnings": [],
            "acceptance": {
                "status": "missing",
                "request_present": False,
                "result_present": False,
                "proven_capability_count": 0,
                "required_capability_count": 4,
                "complete": False,
                "capabilities": {
                    "visual_regression": False,
                    "in_world_regression": False,
                    "canary_rehearsal": False,
                    "rollback_rehearsal": False,
                },
            },
            "remediation": {
                "schema_version": P14_REMEDIATION_SCHEMA,
                "status": "review_required",
                "next_action": "review_p14_external_state",
                "interaction": "operator_review",
                "risk_class": "read_only",
                "action_count": 1,
                "ready_action_count": 1,
                "blocked_action_count": 0,
                "unknown_blocker_count": 1,
                "actions": [
                    {
                        "action_id": "review_p14_external_state",
                        "capability": "external_evidence_review",
                        "status": "ready",
                        "risk_class": "read_only",
                        "interaction": "operator_review",
                        "reason_codes": ["unclassified_blocker"],
                        "blocked_by": [],
                        "auto_executable": False,
                    }
                ],
            },
        }
    generated_at = _parse_utc_timestamp(payload.get("generated_at"))
    now = dt.datetime.now(dt.UTC)
    age_seconds = (
        max(0, int((now - generated_at).total_seconds()))
        if generated_at is not None and generated_at <= now
        else P14_RUNNER_PREFLIGHT_MAX_AGE_SECONDS + 1
    )
    fresh = age_seconds <= P14_RUNNER_PREFLIGHT_MAX_AGE_SECONDS
    authority = payload.get("authority") if isinstance(payload.get("authority"), dict) else {}
    authority_safe = all(
        authority.get(key) is False
        for key in (
            "runtime_actions",
            "live_authority",
            "promotion_approved",
            "mcp_write_tool_enabled",
        )
    )
    operational_result = str(payload.get("operational_result") or "missing")
    allowed_results = {
        "missing",
        "external_result_invalid",
        "externally_verified_stale",
        "externally_verified_current",
    }
    blockers = [
        str(item)[:120]
        for item in payload.get("hard_blockers", [])[:12]
        if isinstance(item, str) and re.fullmatch(r"[a-z0-9_:-]{1,120}", item)
    ] if isinstance(payload.get("hard_blockers"), list) else []
    warnings = [
        str(item)[:120]
        for item in payload.get("warnings", [])[:8]
        if isinstance(item, str) and re.fullmatch(r"[a-z0-9_:-]{1,120}", item)
    ] if isinstance(payload.get("warnings"), list) else []
    remediation = payload.get("remediation") if isinstance(payload.get("remediation"), dict) else {}
    remediation_actions: list[dict[str, Any]] = []
    raw_remediation_actions = remediation.get("actions")
    remediation_actions_valid = bool(
        isinstance(raw_remediation_actions, list)
        and len(raw_remediation_actions) <= 6
    )
    if remediation_actions_valid:
        for item in raw_remediation_actions[:6]:
            if not isinstance(item, dict):
                remediation_actions_valid = False
                break
            reason_codes = item.get("reason_codes")
            blocked_by = item.get("blocked_by")
            projected_reason_codes = [
                str(value)
                for value in reason_codes[:6]
                if isinstance(value, str)
                and re.fullmatch(r"p14_[a-z0-9_]{1,100}|unclassified_blocker", value)
            ] if isinstance(reason_codes, list) else []
            projected_blocked_by = [
                str(value)
                for value in blocked_by[:5]
                if isinstance(value, str) and value in P14_REMEDIATION_CAPABILITIES
            ] if isinstance(blocked_by, list) else []
            action_contract = P14_REMEDIATION_ACTION_CONTRACTS.get(
                str(item.get("action_id") or "")
            )
            action_valid = bool(
                action_contract is not None
                and action_contract
                == (
                    item.get("capability"),
                    item.get("risk_class"),
                    item.get("interaction"),
                )
                and item.get("status") in {"ready", "blocked"}
                and item.get("auto_executable") is False
                and isinstance(reason_codes, list)
                and len(reason_codes) <= 6
                and len(projected_reason_codes) == len(reason_codes[:6])
                and isinstance(blocked_by, list)
                and len(blocked_by) <= 5
                and len(projected_blocked_by) == len(blocked_by[:5])
                and (
                    item.get("status") == "ready" and not projected_blocked_by
                    or item.get("status") == "blocked" and bool(projected_blocked_by)
                )
            )
            if not action_valid:
                remediation_actions_valid = False
                break
            remediation_actions.append(
                {
                    "action_id": item["action_id"],
                    "capability": item["capability"],
                    "status": item["status"],
                    "risk_class": item["risk_class"],
                    "interaction": item["interaction"],
                    "reason_codes": projected_reason_codes,
                    "blocked_by": projected_blocked_by,
                    "auto_executable": False,
                }
            )
    remediation_authority = remediation.get("authority") if isinstance(remediation.get("authority"), dict) else {}
    remediation_action_ids = [item["action_id"] for item in remediation_actions]
    ready_remediation_action_ids = [
        item["action_id"]
        for item in remediation_actions
        if item["status"] == "ready"
    ]
    next_remediation_contract = P14_REMEDIATION_ACTION_CONTRACTS.get(
        str(remediation.get("next_action") or "")
    )
    remediation_valid = bool(
        remediation.get("schema_version") == P14_REMEDIATION_SCHEMA
        and remediation.get("status") in {"complete", "action_required", "review_required"}
        and remediation.get("next_action") in P14_REMEDIATION_ACTION_IDS
        and remediation.get("interaction") in P14_REMEDIATION_INTERACTIONS
        and remediation.get("risk_class") in P14_REMEDIATION_RISK_CLASSES
        and type(remediation.get("action_count")) is int
        and remediation.get("action_count") == len(remediation_actions)
        and type(remediation.get("ready_action_count")) is int
        and remediation.get("ready_action_count") == sum(
            1 for item in remediation_actions if item["status"] == "ready"
        )
        and type(remediation.get("blocked_action_count")) is int
        and remediation.get("blocked_action_count") == sum(
            1 for item in remediation_actions if item["status"] == "blocked"
        )
        and len(remediation_action_ids) == len(set(remediation_action_ids))
        and type(remediation.get("unknown_blocker_count")) is int
        and 0 <= remediation.get("unknown_blocker_count") <= 12
        and remediation_actions_valid
        and remediation_authority.get("auto_execute") is False
        and remediation_authority.get("live_mutation") is False
        and remediation_authority.get("authority_grant") is False
        and (
            (
                not blockers
                and remediation.get("status") == "complete"
                and remediation.get("next_action") == "none"
                and len(remediation_actions) == 0
            )
            or (
                bool(blockers)
                and remediation.get("status") in {"action_required", "review_required"}
                and remediation.get("next_action") != "none"
                and remediation.get("next_action") in ready_remediation_action_ids
                and next_remediation_contract is not None
                and next_remediation_contract[1:] == (
                    remediation.get("risk_class"),
                    remediation.get("interaction"),
                )
                and len(remediation_actions) > 0
            )
        )
    )
    remediation_projection = {
        "schema_version": P14_REMEDIATION_SCHEMA,
        "status": str(remediation.get("status") or "review_required")
        if remediation_valid
        else "review_required",
        "next_action": str(remediation.get("next_action") or "review_p14_external_state")
        if remediation_valid
        else "review_p14_external_state",
        "interaction": str(remediation.get("interaction") or "operator_review")
        if remediation_valid
        else "operator_review",
        "risk_class": str(remediation.get("risk_class") or "read_only")
        if remediation_valid
        else "read_only",
        "action_count": len(remediation_actions) if remediation_valid else 0,
        "ready_action_count": sum(
            1 for item in remediation_actions if item["status"] == "ready"
        ) if remediation_valid else 0,
        "blocked_action_count": sum(
            1 for item in remediation_actions if item["status"] == "blocked"
        ) if remediation_valid else 0,
        "unknown_blocker_count": int(remediation.get("unknown_blocker_count", 0))
        if remediation_valid
        and type(remediation.get("unknown_blocker_count", 0)) is int
        else 0,
        "actions": remediation_actions if remediation_valid else [],
    }
    acceptance = payload.get("acceptance") if isinstance(payload.get("acceptance"), dict) else {}
    acceptance_capabilities = (
        acceptance.get("capabilities")
        if isinstance(acceptance.get("capabilities"), dict)
        else {}
    )
    acceptance_capability_ids = {
        "visual_regression",
        "in_world_regression",
        "canary_rehearsal",
        "rollback_rehearsal",
    }
    acceptance_statuses = {
        "missing",
        "invalid",
        "request_ready",
        "partial",
        "result_untrusted",
        "passed",
    }
    acceptance_valid = bool(
        acceptance.get("status") in acceptance_statuses
        and isinstance(acceptance.get("request_present"), bool)
        and isinstance(acceptance.get("request_valid"), bool)
        and isinstance(acceptance.get("result_present"), bool)
        and isinstance(acceptance.get("result_valid"), bool)
        and isinstance(acceptance.get("signature_verification_passed"), bool)
        and isinstance(acceptance.get("source_current"), bool)
        and type(acceptance.get("proven_capability_count")) is int
        and 0 <= acceptance.get("proven_capability_count") <= 4
        and acceptance.get("required_capability_count") == 4
        and set(acceptance_capabilities) == acceptance_capability_ids
        and all(isinstance(value, bool) for value in acceptance_capabilities.values())
        and acceptance.get("proven_capability_count")
        == sum(1 for value in acceptance_capabilities.values() if value)
        and isinstance(acceptance.get("complete"), bool)
        and acceptance.get("complete") is all(acceptance_capabilities.values())
        and isinstance(acceptance.get("authority_safe"), bool)
    )
    acceptance_projection = {
        "status": str(acceptance.get("status") or "invalid")
        if acceptance_valid
        else "invalid",
        "request_present": acceptance.get("request_present") is True
        if acceptance_valid
        else False,
        "result_present": acceptance.get("result_present") is True
        if acceptance_valid
        else False,
        "proven_capability_count": int(acceptance.get("proven_capability_count", 0))
        if acceptance_valid
        else 0,
        "required_capability_count": 4,
        "complete": acceptance.get("complete") is True if acceptance_valid else False,
        "capabilities": {
            capability: acceptance_capabilities.get(capability) is True
            if acceptance_valid
            else False
            for capability in sorted(acceptance_capability_ids)
        },
    }
    contract_valid = bool(
        payload.get("schema_version") == P14_RUNNER_PREFLIGHT_SCHEMA
        and payload.get("status") in {"ready", "needs_attention", "unavailable"}
        and operational_result in allowed_results
        and isinstance(payload.get("operational_ready"), bool)
        and authority_safe
        and remediation_valid
        and acceptance_valid
    )
    if not contract_valid:
        blockers = ["p14_runner_preflight_invalid"]
    elif not fresh and "p14_runner_preflight_stale" not in blockers:
        blockers.append("p14_runner_preflight_stale")
    operational_ready = bool(
        contract_valid
        and fresh
        and payload.get("status") == "ready"
        and payload.get("operational_ready") is True
        and operational_result == "externally_verified_current"
        and not blockers
    )
    return {
        "status": str(payload.get("status") or "invalid")
        if contract_valid
        else "invalid",
        "fresh": fresh,
        "age_seconds": age_seconds,
        "contract_valid": contract_valid,
        "operational_result": operational_result
        if operational_result in allowed_results
        else "missing",
        "operational_ready": operational_ready,
        "hard_blockers": blockers,
        "warnings": warnings,
        "acceptance": acceptance_projection,
        "remediation": remediation_projection,
        "runner_online": bool(
            isinstance(payload.get("runner"), dict)
            and payload["runner"].get("online") is True
        ),
        "signature_verification_passed": bool(
            isinstance(payload.get("workflow"), dict)
            and payload["workflow"].get("signature_verification_passed") is True
        ),
        "authority_safe": authority_safe,
    }


def _p14_foundation_summary(root: Path = REPO_ROOT) -> dict[str, Any]:
    present: list[str] = []
    blockers: list[str] = []
    for relative in P14_FOUNDATION_PATHS:
        path = root.joinpath(*PurePosixPath(relative).parts)
        if _safe_file_stat(path) is None:
            blockers.append(f"missing_or_unsafe:{relative}")
        else:
            present.append(relative)
    result_path = root / "runtime" / "p14_independent_runner" / "result.json"
    result_present = _safe_file_stat(result_path) is not None
    runner_preflight = _p14_runner_preflight_summary(root)
    ready = len(present) == len(P14_FOUNDATION_PATHS) and not blockers
    return {
        "status": "foundation_ready" if ready else "blocked",
        "contract_version": "ctoa.p14-runner-request.v1",
        "implementation_file_count": len(present),
        "required_file_count": len(P14_FOUNDATION_PATHS),
        "operational_runner_result": (
            runner_preflight["operational_result"]
            if runner_preflight["contract_valid"]
            else "present_untrusted_until_external_key_verification"
            if result_present
            else "missing"
        ),
        "operational_ready": runner_preflight["operational_ready"],
        "operational_blockers": runner_preflight["hard_blockers"],
        "operational_warnings": runner_preflight["warnings"],
        "acceptance": runner_preflight["acceptance"],
        "remediation_plan": runner_preflight["remediation"],
        "runner_preflight": runner_preflight,
        "runtime_authority_granted": False,
        "live_authority_granted": False,
        "promotion_approved": False,
        "mcp_write_tool_enabled": False,
        "blockers": blockers,
    }


def _equipment_operator_missing_document() -> Any:
    return equipment_operator_readiness.documents.document_from_payload(None, "missing")


def _equipment_operator_read_document(
    path: Path,
    *,
    parent_safe: bool,
    max_bytes: int = equipment_operator_readiness.MAX_INPUT_BYTES,
) -> Any:
    if not parent_safe:
        return _equipment_operator_missing_document()
    return equipment_operator_readiness.documents.read_document(path, max_bytes)


def _equipment_operator_artifact_path(artifact: str) -> str:
    return f"runtime/solteria_helper_dev/{EQUIPMENT_OPERATOR_ARTIFACT_FILES[artifact]}"


def _equipment_operator_cross_hashes_valid(
    source: str,
    payload: dict[str, Any],
    documents: dict[str, Any],
) -> bool:
    canonical_sha256 = equipment_operator_readiness.documents.canonical_sha256
    if source == "capture_doctor":
        return True
    if source == "observation_preview":
        background = documents["background_status"]
        generated_at = payload.get("generated_at_unix_ms")
        if not equipment_operator_readiness._is_int(generated_at):  # noqa: SLF001
            return False
        try:
            expected = equipment_operator_readiness.observation_preview.build_preview(
                background=background,
                generated_at_unix_ms=generated_at,
            )
        except (AssertionError, KeyError, TypeError, ValueError):
            return False
        return payload == expected
    if source == "dependency_preflight":
        evaluated_at = payload.get("evaluated_at_unix_ms")
        if not equipment_operator_readiness._is_int(evaluated_at):  # noqa: SLF001
            return False
        dependency = equipment_operator_readiness.dependency_preflight
        try:
            expected = dependency.evaluate_preflight(
                dependency.EvidenceBundle(
                    p8_report=documents["p8_background_status"],
                    p9_report=documents["conditions_shadow_replay"],
                    p9_receipt=documents["conditions_shadow_acceptance"],
                    capture_doctor=documents["capture_doctor"],
                    observation_preview=documents["observation_preview"],
                ),
                evaluated_at_unix_ms=evaluated_at,
            )
        except (AssertionError, KeyError, TypeError, ValueError):
            return False
        return payload == expected
    if source == "candidate_catalog":
        generated_at = payload.get("generated_at_unix_ms")
        if not equipment_operator_readiness._is_int(generated_at):  # noqa: SLF001
            return False
        try:
            expected = equipment_operator_readiness.candidate_catalog.build_catalog(
                preview_document=documents["observation_preview"],
                generated_at_unix_ms=generated_at,
            )
        except (AssertionError, KeyError, TypeError, ValueError):
            return False
        return payload == expected

    hashes = payload.get("input_sha256")
    requested = payload.get("requested_identifiers")
    confirmation = payload.get("operator_confirmation")
    if not (
        payload.get("sources")
        == {
            "capture_doctor": "runtime/solteria_helper_dev/equipment_capture_profile_doctor.json",
            "observation_preview": "runtime/solteria_helper_dev/equipment_observation_preview.json",
            "target_profile": ".ctoa-local/otclient/equipment-shadow-capture-profile.json",
        }
        and isinstance(hashes, dict)
        and set(hashes)
        == {
            "capture_doctor",
            "capture_profile",
            "observation_preview",
            "observation",
        }
        and isinstance(requested, dict)
        and isinstance(confirmation, dict)
        and hashes.get("capture_doctor") == documents["capture_doctor"].sha256
        and hashes.get("observation_preview") == documents["observation_preview"].sha256
    ):
        return False
    doctor_payload = documents["capture_doctor"].payload
    preview_payload = documents["observation_preview"].payload
    if not (
        isinstance(doctor_payload, dict)
        and isinstance(preview_payload, dict)
        and hashes.get("capture_profile") == doctor_payload.get("sha256")
        and hashes.get("observation") == preview_payload.get("observation_sha256")
    ):
        return False
    input_binding = {
        "capture_doctor": hashes["capture_doctor"],
        "capture_profile": hashes["capture_profile"],
        "observation_preview": hashes["observation_preview"],
        "observation": hashes["observation"],
        "requested_identifiers": requested,
        "operator_confirmation_sha256": confirmation.get("confirmation_sha256"),
    }
    if payload.get("input_binding_sha256") != canonical_sha256(input_binding):
        return False
    generated_at = payload.get("generated_at_unix_ms")
    if not equipment_operator_readiness._is_int(generated_at):  # noqa: SLF001
        return False
    if confirmation.get("matched") is True:
        confirmation_value = equipment_operator_readiness.change_plan.EXACT_CONFIRMATION
    elif confirmation.get("provided") is True:
        confirmation_value = "invalid confirmation retained only as a boolean state"
    else:
        confirmation_value = None
    try:
        expected = equipment_operator_readiness.change_plan.evaluate_change_plan(
            equipment_operator_readiness.change_plan.CanonicalInputs(
                capture_doctor=documents["capture_doctor"],
                observation_preview=documents["observation_preview"],
            ),
            equipped_item_id=requested.get("equipped_item_id"),
            candidate_item_id=requested.get("candidate_item_id"),
            candidate_source_container_id=requested.get(
                "candidate_source_container_id"
            ),
            candidate_source_slot_index=requested.get("candidate_source_slot_index"),
            confirmation=confirmation_value,
            generated_at_unix_ms=generated_at,
        )
    except (AssertionError, KeyError, TypeError, ValueError):
        return False
    return payload == expected


def _equipment_operator_contract_valid(
    source: str,
    document: Any,
    documents: dict[str, Any],
) -> bool:
    payload = document.payload
    if document.status != "loaded" or not isinstance(payload, dict):
        return False
    try:
        if source == "capture_doctor":
            local_valid = equipment_operator_readiness.dependency_preflight._doctor_contract_valid(  # noqa: SLF001
                payload
            )
        elif source == "observation_preview":
            local_valid = equipment_operator_readiness.dependency_preflight._preview_contract_valid(  # noqa: SLF001
                payload
            )
        elif source == "dependency_preflight":
            local_valid = equipment_operator_readiness._dependency_contract_valid(  # noqa: SLF001
                payload
            )
        elif source == "candidate_catalog":
            local_valid = equipment_operator_readiness._catalog_contract_valid(  # noqa: SLF001
                payload
            )
        else:
            local_valid = equipment_operator_readiness._change_plan_contract_valid(  # noqa: SLF001
                payload
            )
    except (KeyError, TypeError, ValueError):
        local_valid = False
    no_action_valid = (
        payload.get("no_action_contract") is True
        and payload.get("runtime_actions") is False
        and payload.get("live_file_writes") is False
        and payload.get("runtime_readiness_claimed") is False
        if source == "capture_doctor"
        else equipment_operator_readiness._safe(payload)  # noqa: SLF001
    )
    return bool(
        local_valid
        and payload.get("schema_version")
        == equipment_operator_readiness.EXPECTED_SCHEMAS[source]
        and no_action_valid
        and _equipment_operator_cross_hashes_valid(source, payload, documents)
    )


def _equipment_operator_source_projection(
    *,
    artifact: str,
    source: str,
    document: Any,
    documents: dict[str, Any],
    now_ms: int,
) -> dict[str, Any]:
    payload = document.payload if isinstance(document.payload, dict) else {}
    contract_valid = _equipment_operator_contract_valid(source, document, documents)
    state = equipment_operator_readiness._state(  # noqa: SLF001
        source,
        document,
        now_ms=now_ms,
        preview_document=documents["observation_preview"],
    )
    fresh = bool(contract_valid and state.fresh)
    ready = bool(contract_valid and fresh and state.ready)
    if document.status == "missing":
        status = "missing"
    elif document.status != "loaded" or not contract_valid:
        status = "invalid"
    elif not fresh:
        status = "stale"
    else:
        status = str(payload.get("status") or "invalid")
    trusted_blockers = (
        [str(item) for item in payload.get("blockers", [])]
        if contract_valid and isinstance(payload.get("blockers"), list)
        else []
    )
    blockers = list(trusted_blockers)
    if status in {"missing", "invalid", "stale"}:
        blockers.append(f"{artifact}_{status}")
    if not blockers and not ready:
        blockers.append(f"{artifact}_{status}")
    blockers = list(dict.fromkeys(blockers))
    return {
        "path": _equipment_operator_artifact_path(artifact),
        "load_status": document.status,
        "schema_version": payload.get("schema_version")
        if isinstance(payload.get("schema_version"), str)
        else None,
        "status": status,
        "blockers": blockers,
        "sha256": document.sha256,
        "contract_valid": contract_valid,
        "fresh": fresh,
        "ready": ready,
        "age_ms": state.age_ms,
    }


def _equipment_operator_readiness_summary(
    helper_dev_dir: Path,
    *,
    helper_dir_safe: bool,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    observed_at = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    now_ms = int(observed_at.timestamp() * 1000)
    source_documents = {
        source: _equipment_operator_read_document(
            helper_dev_dir / EQUIPMENT_OPERATOR_ARTIFACT_FILES[artifact],
            parent_safe=helper_dir_safe,
        )
        for artifact, source in EQUIPMENT_OPERATOR_SOURCE_NAMES.items()
    }
    documents = {
        **source_documents,
        "background_status": _equipment_operator_read_document(
            helper_dev_dir / "background_status.json",
            parent_safe=helper_dir_safe,
            max_bytes=(
                equipment_operator_readiness.observation_preview.MAX_BACKGROUND_BYTES
            ),
        ),
        "p8_background_status": _equipment_operator_read_document(
            helper_dev_dir / "background_status.json",
            parent_safe=helper_dir_safe,
            max_bytes=(
                equipment_operator_readiness.dependency_preflight.MAX_INPUT_BYTES
            ),
        ),
        "conditions_shadow_replay": _equipment_operator_read_document(
            helper_dev_dir / "conditions_shadow_replay.json",
            parent_safe=helper_dir_safe,
        ),
        "conditions_shadow_acceptance": _equipment_operator_read_document(
            helper_dev_dir / "conditions_shadow_acceptance.json",
            parent_safe=helper_dir_safe,
        ),
    }
    artifacts = {
        artifact: _equipment_operator_source_projection(
            artifact=artifact,
            source=source,
            document=source_documents[source],
            documents=documents,
            now_ms=now_ms,
        )
        for artifact, source in EQUIPMENT_OPERATOR_SOURCE_NAMES.items()
    }

    readiness_artifact = "equipment_operator_readiness"
    readiness_document = _equipment_operator_read_document(
        helper_dev_dir / EQUIPMENT_OPERATOR_ARTIFACT_FILES[readiness_artifact],
        parent_safe=helper_dir_safe,
    )
    readiness_payload = (
        readiness_document.payload
        if isinstance(readiness_document.payload, dict)
        else {}
    )
    generated_at = readiness_payload.get("generated_at_unix_ms")
    age_ms = (
        now_ms - generated_at
        if equipment_operator_readiness._is_int(generated_at)  # noqa: SLF001
        else None
    )
    try:
        expected_readiness = (
            equipment_operator_readiness.evaluate_readiness(
                source_documents,
                generated_at_unix_ms=generated_at,
            )
            if equipment_operator_readiness._is_int(generated_at)  # noqa: SLF001
            and generated_at > 0
            else None
        )
    except (AssertionError, KeyError, TypeError, ValueError):
        expected_readiness = None
    readiness_contract_valid = bool(
        readiness_document.status == "loaded"
        and readiness_payload.get("schema_version")
        == EQUIPMENT_OPERATOR_EXPECTED_SCHEMAS[readiness_artifact]
        and expected_readiness is not None
        and readiness_payload == expected_readiness
        and equipment_operator_readiness._safe(readiness_payload)  # noqa: SLF001
        and all(item["contract_valid"] for item in artifacts.values())
    )
    readiness_fresh = bool(
        readiness_contract_valid
        and age_ms is not None
        and 0 <= age_ms <= EQUIPMENT_OPERATOR_MAX_AGE_MS
        and all(item["fresh"] for item in artifacts.values())
    )
    readiness_ready = bool(
        readiness_fresh
        and readiness_payload.get("status") == "operator_inputs_ready"
        and readiness_payload.get("operator_inputs_ready") is True
        and all(item["ready"] for item in artifacts.values())
    )
    if readiness_document.status == "missing":
        readiness_status = "missing"
    elif readiness_document.status != "loaded" or not readiness_contract_valid:
        readiness_status = "invalid"
    elif not readiness_fresh:
        readiness_status = "stale"
    else:
        readiness_status = str(readiness_payload.get("status") or "invalid")
    trusted_readiness_blockers = (
        [str(item) for item in readiness_payload.get("blockers", [])]
        if readiness_contract_valid
        and isinstance(readiness_payload.get("blockers"), list)
        else []
    )
    readiness_blockers = list(trusted_readiness_blockers)
    if readiness_status in {"missing", "invalid", "stale"}:
        readiness_blockers.append(f"{readiness_artifact}_{readiness_status}")
    if not readiness_blockers and not readiness_ready:
        readiness_blockers.append(f"{readiness_artifact}_{readiness_status}")
    readiness_blockers = list(dict.fromkeys(readiness_blockers))
    artifacts[readiness_artifact] = {
        "path": _equipment_operator_artifact_path(readiness_artifact),
        "load_status": readiness_document.status,
        "schema_version": readiness_payload.get("schema_version")
        if isinstance(readiness_payload.get("schema_version"), str)
        else None,
        "status": readiness_status,
        "blockers": readiness_blockers,
        "sha256": readiness_document.sha256,
        "contract_valid": readiness_contract_valid,
        "fresh": readiness_fresh,
        "ready": readiness_ready,
        "age_ms": age_ms,
    }

    if readiness_contract_valid and readiness_fresh:
        blockers = [str(item) for item in readiness_payload.get("blockers", [])]
    else:
        blockers = []
        for artifact in EQUIPMENT_OPERATOR_ARTIFACT_FILES:
            blockers.extend(artifacts[artifact]["blockers"])
    blockers = list(dict.fromkeys(blockers))
    if readiness_contract_valid and readiness_fresh:
        next_actions = [
            dict(item)
            for item in readiness_payload.get("next_actions", [])
            if isinstance(item, dict)
        ]
    else:
        next_actions = []
        for artifact, source in EQUIPMENT_OPERATOR_SOURCE_NAMES.items():
            category = artifacts[artifact]["status"]
            if category not in {"missing", "invalid", "stale"}:
                continue
            next_actions.append(
                {
                    "order": 0,
                    "source": source,
                    "category": category,
                    "command": equipment_operator_readiness.COMMANDS[source],
                    "instruction": equipment_operator_readiness._instruction(  # noqa: SLF001
                        source, category
                    ),
                    "changes_eligibility": False,
                    "action_scope": "passive_or_repo_only",
                }
            )
        next_actions.append(
            {
                "order": 0,
                "source": "equipment_operator_readiness",
                "category": (
                    "missing"
                    if readiness_status == "missing"
                    else "stale"
                    if readiness_status == "stale"
                    else "invalid"
                ),
                "command": ".\\ctoa.ps1 otp10ready",
                "instruction": "Regenerate the fixed read-only P10 operator-readiness artifact.",
                "changes_eligibility": False,
                "action_scope": "repo_only_review",
            }
        )
        for order, action in enumerate(next_actions, start=1):
            action["order"] = order

    reported_status = (
        str(readiness_payload.get("status"))
        if isinstance(readiness_payload.get("status"), str)
        else "missing"
        if readiness_document.status == "missing"
        else "invalid"
    )
    return {
        "schema_version": P10_EQUIPMENT_CONSUMER_PARITY_SCHEMA,
        "status": readiness_status,
        "reported_status": reported_status,
        "contract_valid": readiness_contract_valid,
        "fresh": readiness_fresh,
        "age_ms": age_ms,
        "operator_inputs_ready": readiness_ready,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "acceptance_granted": False,
        "operational_readiness_claimed": False,
        "read_only": True,
        "blockers": blockers,
        "next_actions": next_actions,
        "artifacts": artifacts,
        "paths": {
            artifact: _equipment_operator_artifact_path(artifact)
            for artifact in EQUIPMENT_OPERATOR_ARTIFACT_FILES
        },
        "live_file_writes": False,
        **{key: False for key in equipment_operator_readiness.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def _equipment_operator_refresh_run_summary(
    payload: dict[str, Any] | None,
    path: Path,
    *,
    artifact_present: bool,
    now_ms: int | None = None,
) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    errors = (
        equipment_refresh_run._schema_errors(equipment_refresh_run.REPORT_SCHEMA, data)
        if data
        else ["missing payload"]
    )  # noqa: SLF001
    valid = not errors
    completed = data.get("completed_at_unix_ms")
    current = (
        now_ms
        if now_ms is not None
        else int(dt.datetime.now(dt.UTC).timestamp() * 1000)
    )
    age = (
        current - completed
        if isinstance(completed, int) and not isinstance(completed, bool)
        else None
    )
    fresh = bool(
        valid
        and age is not None
        and 0 <= age <= equipment_refresh_run.MAX_ARTIFACT_AGE_MS
    )
    status = (
        "missing"
        if not artifact_present
        else "invalid"
        if not valid
        else "stale"
        if not fresh
        else "completed"
    )
    source_blockers = data.get("source_blockers", {}) if valid else {}
    blockers = (
        [
            f"{stage}: {item}"
            for stage, values in source_blockers.items()
            for item in values
        ]
        if isinstance(source_blockers, dict)
        else []
    )
    return {
        "path": str(path),
        "schema_version": P10_EQUIPMENT_OPERATOR_REFRESH_RUN_SCHEMA,
        "status": status,
        "reported_status": str(data.get("status", "missing")),
        "contract_valid": valid,
        "contract_errors": errors[:8] if artifact_present else [],
        "fresh": fresh,
        "age_ms": age,
        "run_id": str(data.get("run_id", "")) if valid else "",
        "started_at_unix_ms": data.get("started_at_unix_ms") if valid else None,
        "completed_at_unix_ms": completed if valid else None,
        "duration_ms": data.get("duration_ms") if valid else None,
        "canonical_aggregate_sha256": str(data.get("canonical_aggregate_sha256", ""))
        if valid
        else "",
        "artifact_hashes": data.get("artifact_hashes", {}) if valid else {},
        "source_statuses": data.get("source_statuses", {}) if valid else {},
        "source_blockers": source_blockers,
        "blockers": blockers,
        "no_action_verified": data.get("no_action_verified") is True
        if valid
        else False,
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
        "read_only": True,
    }


def _safe_nonnegative_int(value: Any) -> tuple[int, bool]:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value, True
    return 0, False


def _matches_exact_contract(value: Any, expected: dict[str, Any]) -> bool:
    return (
        isinstance(value, dict)
        and value.keys() == expected.keys()
        and all(
            type(value[key]) is type(expected_value) and value[key] == expected_value
            for key, expected_value in expected.items()
        )
    )


def _background_pin_error_valid(value: Any) -> bool:
    if not isinstance(value, str) or not 0 < len(value) <= 96:
        return False
    exact = {
        "live_manifest_schema_invalid",
        "live_manifest_origin_invalid",
        "live_manifest_timestamp_invalid",
        "live_manifest_helper_version_invalid",
        "manifest_files_missing",
        "manifest_entry_limit_exceeded",
        "manifest_total_bytes_exceeded",
        "live_promotion_name_invalid",
        "live_promotion_approval_invalid",
        "live_promotion_verification_invalid",
        "live_promotion_helper_version_mismatch",
        "live_promotion_file_count_mismatch",
        "live_promotion_manifest_path_mismatch",
        "live_promotion_manifest_sha256_mismatch",
        "live_promotion_client_path_mismatch",
        "live_promotion_timestamp_mismatch",
    }
    if value in exact:
        return True
    if re.fullmatch(
        r"live_(?:manifest|promotion)_(?:missing|empty|malformed|oversize|symlink_rejected|not_regular|not_object|changed_during_open|unreadable)",
        value,
    ):
        return True
    return (
        re.fullmatch(
            r"manifest_entry_[0-9]{1,3}_(?:invalid|path_invalid|duplicate|sha256_invalid|bytes_invalid)",
            value,
        )
        is not None
    )


def _background_pin_remediation_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "classification",
        "required_action",
        "observer_can_write_trust_anchor",
        "historical_rebinding_allowed",
        "requires_current_release_gate",
        "requires_explicit_live_approval",
    }:
        return False
    classification = value.get("classification")
    required_action = value.get("required_action")
    if (
        not isinstance(classification, str)
        or classification not in BACKGROUND_PIN_CLASSIFICATION_VALUES
        or not isinstance(required_action, str)
        or required_action not in BACKGROUND_PIN_REQUIRED_ACTION_VALUES
        or value.get("observer_can_write_trust_anchor") is not False
        or value.get("historical_rebinding_allowed") is not False
    ):
        return False
    trusted = classification == "trusted"
    return bool(
        required_action
        == (
            "none" if trusted else "refresh_official_live_promotion_after_current_gates"
        )
        and value.get("requires_current_release_gate") is (not trusted)
        and value.get("requires_explicit_live_approval") is (not trusted)
    )


def _background_diagnostic_parity_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "attempted",
        "status",
        "manifest_file_count",
        "matched_file_count",
        "mismatch_count",
        "mutable_drift_count",
        "profile_drift_count",
        "missing_count",
        "invalid_path_count",
        "oversize_count",
        "actual_total_bytes",
        "stable_during_observation",
        "acceptance_allowed",
    }:
        return False
    attempted = value.get("attempted")
    status = value.get("status")
    counts = [
        value.get(key)
        for key in (
            "manifest_file_count",
            "matched_file_count",
            "mismatch_count",
            "mutable_drift_count",
            "profile_drift_count",
            "missing_count",
            "invalid_path_count",
            "oversize_count",
            "actual_total_bytes",
        )
    ]
    if (
        not isinstance(attempted, bool)
        or not isinstance(status, str)
        or status not in BACKGROUND_DIAGNOSTIC_STATUS_VALUES
        or not all(_safe_nonnegative_int(item)[1] for item in counts)
        or not isinstance(value.get("stable_during_observation"), bool)
        or value.get("acceptance_allowed") is not False
        or value.get("mutable_drift_count") != value.get("profile_drift_count")
    ):
        return False
    if attempted:
        observed = sum(
            int(value.get(key) or 0)
            for key in (
                "matched_file_count",
                "mismatch_count",
                "mutable_drift_count",
                "missing_count",
                "invalid_path_count",
                "oversize_count",
            )
        )
        if (
            status not in {"passed", "failed"}
            or observed > value["manifest_file_count"]
        ):
            return False
    else:
        if status not in {"not_required", "unavailable"}:
            return False
    return True


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
    raw_pin_errors = integrity.get("pin_errors")
    pin_errors_present = "pin_errors" in integrity
    pin_errors_valid = bool(
        isinstance(raw_pin_errors, list)
        and len(raw_pin_errors) <= 32
        and all(isinstance(item, str) for item in raw_pin_errors)
        and len(raw_pin_errors) == len(set(raw_pin_errors))
        and all(_background_pin_error_valid(item) for item in raw_pin_errors)
    )
    pin_errors = list(raw_pin_errors) if pin_errors_valid else []
    pin_remediation = integrity.get("pin_remediation")
    pin_remediation_present = "pin_remediation" in integrity
    pin_remediation_valid = _background_pin_remediation_valid(pin_remediation)
    diagnostic_parity = integrity.get("diagnostic_parity")
    diagnostic_parity_present = "diagnostic_parity" in integrity
    diagnostic_parity_valid = _background_diagnostic_parity_valid(diagnostic_parity)

    raw_blockers = data.get("blockers")
    blockers_valid = (
        isinstance(raw_blockers, list)
        and len(raw_blockers) <= 16
        and all(
            isinstance(item, str) and item in BACKGROUND_BLOCKER_VALUES
            for item in raw_blockers
        )
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
    profile_drift_count, profile_drift_valid = _safe_nonnegative_int(
        integrity.get("profile_drift_count")
    )
    mismatch_count, mismatch_valid = _safe_nonnegative_int(
        integrity.get("mismatch_count")
    )
    missing_count, missing_valid = _safe_nonnegative_int(integrity.get("missing_count"))
    invalid_path_count, invalid_path_valid = _safe_nonnegative_int(
        integrity.get("invalid_path_count")
    )
    oversize_count, oversize_valid = _safe_nonnegative_int(
        integrity.get("oversize_count")
    )

    interaction_contract_valid = _matches_exact_contract(
        data.get("interaction_contract"), BACKGROUND_INTERACTION_CONTRACT
    )
    wrapper_invariants_valid = _matches_exact_contract(
        data.get("wrapper_invariants"), BACKGROUND_WRAPPER_INVARIANTS
    )
    status_checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    intrusive_actions_valid = (
        isinstance(data.get("intrusive_actions_performed"), list)
        and not data["intrusive_actions_performed"]
    )

    count_fields_valid = all(
        (
            matched_valid,
            manifest_valid,
            mutable_valid,
            profile_drift_valid,
            mismatch_valid,
            missing_valid,
            invalid_path_valid,
            oversize_valid,
        )
    )
    observed_file_count = sum(
        (
            matched_file_count,
            mismatch_count,
            mutable_drift_count,
            missing_count,
            invalid_path_count,
            oversize_count,
        )
    )
    integrity_count_consistent = (
        count_fields_valid and observed_file_count <= manifest_file_count
    )
    integrity_drift_consistent = (
        mutable_valid
        and profile_drift_valid
        and mutable_drift_count == profile_drift_count
    )
    live_files_unchanged = integrity.get("live_files_unchanged_during_observation")

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
    reported_status_valid = (
        isinstance(reported_status, str) and reported_status in BACKGROUND_STATUS_VALUES
    )
    process_state_valid = isinstance(
        process_state_value, str
    ) and process_state_value in {"running", "not_running", "ambiguous"}
    runtime_state_valid = isinstance(
        runtime_state_value, str
    ) and runtime_state_value in {"armed", "disarmed", "unknown"}
    integrity_status_valid = (
        isinstance(integrity_status_value, str)
        and integrity_status_value in BACKGROUND_INTEGRITY_STATUS_VALUES
    )
    capability_status_valid = (
        isinstance(capability_status_value, str)
        and capability_status_value in BACKGROUND_CAPABILITY_STATUS_VALUES
    )
    integrity_status_consistent = False
    if count_fields_valid and integrity_count_consistent and integrity_drift_consistent:
        adverse_counts = (
            mismatch_count,
            mutable_drift_count,
            missing_count,
            invalid_path_count,
            oversize_count,
        )
        if integrity_status_value == "passed":
            integrity_status_consistent = (
                matched_file_count == manifest_file_count
                and not any(adverse_counts)
                and live_files_unchanged is True
            )
        elif integrity_status_value == "failed":
            integrity_status_consistent = (
                matched_file_count != manifest_file_count or any(adverse_counts)
            )
        elif integrity_status_value == "untrusted_pin":
            integrity_status_consistent = not any((matched_file_count, *adverse_counts))
    contract_errors: list[str] = []
    checks = (
        ("schema_version", data.get("schema_version") == BACKGROUND_STATUS_SCHEMA),
        ("mode", mode == BACKGROUND_STATUS_MODE),
        ("status", reported_status_valid),
        ("advisory_only", data.get("advisory_only") is True),
        (
            "safe_to_run_while_playing",
            data.get("safe_to_run_while_playing") is True,
        ),
        ("promotion_allowed", data.get("promotion_allowed") is False),
        ("dispatch_allowed", data.get("dispatch_allowed") is False),
        ("runtime_actions", data.get("runtime_actions") is False),
        ("interaction_contract", interaction_contract_valid),
        ("wrapper_invariants", wrapper_invariants_valid),
        (
            "checks_no_screen_contract",
            status_checks.get("no_screen_contract") is True,
        ),
        (
            "checks_client_process_stable_during_wrapper",
            status_checks.get("client_process_stable_during_wrapper") is True,
        ),
        (
            "checks_screenshot_count_stable_during_wrapper",
            status_checks.get("screenshot_count_stable_during_wrapper") is True,
        ),
        ("intrusive_actions_performed", intrusive_actions_valid),
        ("blockers", blockers_valid),
        ("integrity", isinstance(data.get("integrity"), dict)),
        ("capability", isinstance(data.get("capability"), dict)),
        ("process_state", process_state_valid),
        ("runtime_state", runtime_state_valid),
        ("integrity_status", integrity_status_valid),
        ("capability_status", capability_status_valid),
        ("capability_fresh", isinstance(capability.get("fresh"), bool)),
        ("capability_runtime_actions", capability.get("runtime_actions") is False),
        (
            "capability_runtime_core_actions",
            capability.get("runtime_core_actions") is False,
        ),
        ("matched_file_count", matched_valid),
        ("manifest_file_count", manifest_valid),
        ("mutable_drift_count", mutable_valid),
        ("profile_drift_count", profile_drift_valid),
        ("mismatch_count", mismatch_valid),
        ("missing_count", missing_valid),
        ("invalid_path_count", invalid_path_valid),
        ("oversize_count", oversize_valid),
        (
            "live_files_unchanged_during_observation",
            isinstance(live_files_unchanged, bool),
        ),
        ("integrity_count_consistency", integrity_count_consistent),
        ("integrity_drift_consistency", integrity_drift_consistent),
        ("integrity_status_consistency", integrity_status_consistent),
        ("pin_errors", not pin_errors_present or pin_errors_valid),
        (
            "pin_remediation",
            not pin_remediation_present or pin_remediation_valid,
        ),
        (
            "diagnostic_parity",
            not diagnostic_parity_present or diagnostic_parity_valid,
        ),
        ("generated_at_utc", generated_at is not None),
    )
    contract_errors.extend(name for name, passed in checks if not passed)
    contract_valid = payload is not None and not contract_errors
    fresh = contract_valid and timestamp_fresh
    capability_fresh = capability.get("fresh") is True
    integrity_status = integrity_status_value if integrity_status_valid else "invalid"
    capability_status = (
        capability_status_value if capability_status_valid else "invalid"
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
        if isinstance(runtime_state_value, str)
        and runtime_state_value in {"armed", "disarmed"}
        else "unknown"
    )
    process_state = process_state_value if process_state_valid else "unknown"
    safe_pin_remediation = pin_remediation if pin_remediation_valid else {}
    safe_diagnostic = diagnostic_parity if diagnostic_parity_valid else {}

    return {
        "status": effective_status,
        "reported_status": reported_status if reported_status_valid else "invalid",
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
        "pin_errors": pin_errors,
        "pin_classification": str(
            safe_pin_remediation.get("classification") or "unknown"
        ),
        "pin_required_action": str(
            safe_pin_remediation.get("required_action") or "none"
        ),
        "pin_historical_rebinding_allowed": False,
        "pin_requires_explicit_live_approval": (
            safe_pin_remediation.get("requires_explicit_live_approval") is True
        ),
        "diagnostic_parity_status": str(safe_diagnostic.get("status") or "unknown"),
        "diagnostic_parity_attempted": safe_diagnostic.get("attempted") is True,
        "diagnostic_profile_drift_count": (
            int(safe_diagnostic.get("profile_drift_count") or 0)
        ),
        "diagnostic_stable_during_observation": (
            safe_diagnostic.get("stable_during_observation") is True
        ),
        "diagnostic_acceptance_allowed": False,
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


def _helper_status(
    helper_dev_dir: Path,
    *,
    roadmap_state_path: Path | None = None,
    action_audit_path: Path | None = None,
) -> dict[str, Any]:
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
    conditions_shadow_path = helper_dev_dir / "conditions_shadow_replay.json"
    conditions_shadow_acceptance_path = (
        helper_dev_dir / "conditions_shadow_acceptance.json"
    )
    equipment_shadow_path = helper_dev_dir / "equipment_shadow_replay.json"
    equipment_shadow_acceptance_path = (
        helper_dev_dir / "equipment_shadow_acceptance.json"
    )
    heal_friend_shadow_acceptance_path = (
        helper_dev_dir / "heal_friend_shadow_acceptance.json"
    )
    p12_conditions_plan_path = helper_dev_dir / "p12_conditions_execute_once_plan.json"
    p12_conditions_approval_path = (
        helper_dev_dir / "p12_conditions_session_approval.json"
    )
    p12_conditions_trace_path = (
        helper_dev_dir / "p12_conditions_execute_once_trace.json"
    )
    p12_conditions_receipt_path = (
        helper_dev_dir / "p12_conditions_execute_once_receipt.json"
    )
    p12_equipment_plan_path = helper_dev_dir / "p12_equipment_execute_once_plan.json"
    p12_equipment_approval_path = helper_dev_dir / "p12_equipment_session_approval.json"
    p12_equipment_trace_path = helper_dev_dir / "p12_equipment_execute_once_trace.json"
    p12_equipment_receipt_path = (
        helper_dev_dir / "p12_equipment_execute_once_receipt.json"
    )
    p12_heal_friend_plan_path = (
        helper_dev_dir / "p12_heal_friend_execute_once_plan.json"
    )
    p12_heal_friend_receipt_path = (
        helper_dev_dir / "p12_heal_friend_execute_once_receipt.json"
    )
    p12_heal_friend_approval_path = (
        helper_dev_dir / "p12_heal_friend_session_approval.json"
    )
    p12_heal_friend_preflight_path = (
        helper_dev_dir / "p12_heal_friend_execution_preflight.json"
    )
    p12_heal_friend_closure_path = (
        helper_dev_dir / "p12_heal_friend_no_compatible_vocation_closure.json"
    )

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
    conditions_shadow = (
        _read_json_strict_or_none(conditions_shadow_path) if helper_dir_safe else None
    )
    conditions_shadow_summary = _conditions_shadow_summary(
        conditions_shadow,
        conditions_shadow_path,
        artifact_present=_safe_file_stat(conditions_shadow_path) is not None,
    )
    conditions_shadow_acceptance = (
        _read_json_strict_or_none(conditions_shadow_acceptance_path)
        if helper_dir_safe
        else None
    )
    equipment_shadow = (
        _read_json_strict_or_none(equipment_shadow_path) if helper_dir_safe else None
    )
    equipment_shadow_summary = _equipment_shadow_summary(
        equipment_shadow,
        equipment_shadow_path,
        artifact_present=_safe_file_stat(equipment_shadow_path) is not None,
    )
    equipment_shadow_acceptance = (
        _read_json_strict_or_none(equipment_shadow_acceptance_path)
        if helper_dir_safe
        else None
    )
    equipment_shadow_acceptance_summary = _equipment_shadow_acceptance_summary(
        equipment_shadow_acceptance,
        equipment_shadow_acceptance_path,
        equipment_shadow,
        artifact_present=_safe_file_stat(equipment_shadow_acceptance_path) is not None,
    )
    heal_friend_shadow_acceptance = (
        _read_json_strict_or_none(heal_friend_shadow_acceptance_path)
        if helper_dir_safe
        else None
    )
    p12_conditions_plan = (
        _read_json_strict_or_none(p12_conditions_plan_path) if helper_dir_safe else None
    )
    p12_conditions_approval = (
        _read_json_strict_or_none(p12_conditions_approval_path)
        if helper_dir_safe
        else None
    )
    p12_conditions_trace = (
        _read_json_strict_or_none(p12_conditions_trace_path)
        if helper_dir_safe
        else None
    )
    p12_conditions_receipt_payload = (
        _read_json_strict_or_none(p12_conditions_receipt_path)
        if helper_dir_safe
        else None
    )
    p12_equipment_plan = (
        _read_json_strict_or_none(p12_equipment_plan_path) if helper_dir_safe else None
    )
    p12_equipment_approval = (
        _read_json_strict_or_none(p12_equipment_approval_path)
        if helper_dir_safe
        else None
    )
    p12_equipment_trace = (
        _read_json_strict_or_none(p12_equipment_trace_path) if helper_dir_safe else None
    )
    p12_equipment_receipt_payload = (
        _read_json_strict_or_none(p12_equipment_receipt_path)
        if helper_dir_safe
        else None
    )
    p12_heal_friend_closure_payload = (
        _read_json_strict_or_none(p12_heal_friend_closure_path)
        if helper_dir_safe
        else None
    )
    p12_heal_friend_closure_summary = _p12_heal_friend_closure_summary(
        p12_heal_friend_closure_payload,
        artifact_present=_safe_file_stat(p12_heal_friend_closure_path) is not None,
        plan_path=p12_heal_friend_plan_path,
        approval_path=p12_heal_friend_approval_path,
        preflight_path=p12_heal_friend_preflight_path,
    )
    roadmap_state_artifact_present = bool(
        roadmap_state_path is not None
        and _safe_file_stat(roadmap_state_path) is not None
    )
    roadmap_state_payload = (
        _read_json_strict_or_none(roadmap_state_path)
        if roadmap_state_path is not None and roadmap_state_artifact_present
        else None
    )
    roadmap_state_summary = _roadmap_state_summary(
        roadmap_state_payload,
        artifact_present=roadmap_state_artifact_present,
        path=roadmap_state_path or DEFAULT_ENGINE_BRAIN_ROADMAP_STATE_PATH,
        action_audit_path=action_audit_path,
    )
    p12_conditions_summary = _p12_conditions_summary(
        p12_conditions_plan,
        p12_conditions_approval,
        p12_conditions_trace,
        p12_conditions_receipt_payload,
    )
    p12_equipment_summary = _p12_equipment_summary(
        p12_equipment_plan,
        p12_equipment_approval,
        p12_equipment_trace,
        p12_equipment_receipt_payload,
    )
    roadmap_phase_state = _roadmap_phase_state_summary(
        background=background_summary,
        p9_receipt=conditions_shadow_acceptance,
        p10_receipt=equipment_shadow_acceptance,
        p11_receipt=heal_friend_shadow_acceptance,
        p12_conditions=p12_conditions_summary,
        p12_equipment=p12_equipment_summary,
        p12_heal_friend_artifact_present=bool(
            _safe_file_stat(p12_heal_friend_plan_path) is not None
            or _safe_file_stat(p12_heal_friend_receipt_path) is not None
        ),
        p12_heal_friend_closure=p12_heal_friend_closure_summary,
        roadmap_state=roadmap_state_summary,
        p14_foundation=_p14_foundation_summary(),
    )
    equipment_operator_summary = _equipment_operator_readiness_summary(
        helper_dev_dir,
        helper_dir_safe=helper_dir_safe,
    )
    equipment_refresh_path = helper_dev_dir / "equipment_operator_refresh_run.json"
    equipment_refresh_payload = (
        _read_json_strict_or_none(equipment_refresh_path) if helper_dir_safe else None
    )
    equipment_refresh_summary = _equipment_operator_refresh_run_summary(
        equipment_refresh_payload,
        equipment_refresh_path,
        artifact_present=_safe_file_stat(equipment_refresh_path) is not None,
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
    manifest_files = manifest.get("files", []) if isinstance(manifest, dict) else []
    live_promotion_contract_valid = bool(
        live_promotion_has_approval
        and (live_promotion or {}).get("verification") == "stage_live_sha256_match"
        and int((live_promotion or {}).get("verified_file_count", 0) or 0)
        == len(manifest_files)
        and len(manifest_files) > 0
        and str((live_promotion or {}).get("helper_version", ""))
        == str((manifest or {}).get("helper_version", ""))
        and live_approval_evidence
        in {"-ApproveLiveDeploy", "runtime/solteria_helper_dev/live_promotion.json"}
    )
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
        and live_promotion_contract_valid
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
        "conditions_shadow": conditions_shadow_summary,
        "equipment_shadow": equipment_shadow_summary,
        "equipment_shadow_acceptance": equipment_shadow_acceptance_summary,
        "roadmap_phase_state": roadmap_phase_state,
        "equipment_operator_readiness": equipment_operator_summary,
        "equipment_operator_refresh_run": equipment_refresh_summary,
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
            "conditions_shadow": str(conditions_shadow_path).replace("\\", "/"),
            "conditions_shadow_acceptance": str(
                conditions_shadow_acceptance_path
            ).replace("\\", "/"),
            "equipment_shadow": str(equipment_shadow_path).replace("\\", "/"),
            "equipment_shadow_acceptance": str(
                equipment_shadow_acceptance_path
            ).replace("\\", "/"),
            "heal_friend_shadow_acceptance": str(
                heal_friend_shadow_acceptance_path
            ).replace("\\", "/"),
            "p12_conditions_plan": str(p12_conditions_plan_path).replace("\\", "/"),
            "p12_conditions_receipt": str(p12_conditions_receipt_path).replace(
                "\\", "/"
            ),
            "p12_equipment_plan": str(p12_equipment_plan_path).replace("\\", "/"),
            "p12_equipment_receipt": str(p12_equipment_receipt_path).replace("\\", "/"),
            "p12_heal_friend_closure": str(p12_heal_friend_closure_path).replace(
                "\\", "/"
            ),
            "roadmap_state": str(
                roadmap_state_path or DEFAULT_ENGINE_BRAIN_ROADMAP_STATE_PATH
            ).replace("\\", "/"),
            "equipment_operator_readiness": _equipment_operator_artifact_path(
                "equipment_operator_readiness"
            ),
            "equipment_operator_refresh_run": str(equipment_refresh_path),
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
    roadmap_state_path: Path | None = None,
    source_audit_id: str = "",
) -> dict[str, Any]:
    source_audit_id = str(source_audit_id or "").strip()
    if source_audit_id and not EVIDENCE_SOURCE_AUDIT_ID_RE.fullmatch(source_audit_id):
        raise ValueError("source_audit_id must identify an evidence-pack-refresh audit")
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
    roadmap_state_path = roadmap_state_path or _configured_path(
        "CTOA_ENGINE_BRAIN_ROADMAP_STATE_PATH",
        str(DEFAULT_ENGINE_BRAIN_ROADMAP_STATE_PATH),
    )

    latest_evidence = _find_latest_markdown(releases_dir)
    quality = _read_json_or_none(quality_path)
    cost_report = _read_json_or_none(cost_report_path)
    action_audit_count = _count_jsonl_records(action_audit_path)
    helper = _helper_status(
        helper_dev_dir,
        roadmap_state_path=roadmap_state_path,
        action_audit_path=action_audit_path,
    )
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

    pack = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
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
    provenance = {
        "source_action": EVIDENCE_SOURCE_ACTION,
        "source_audit_id": source_audit_id,
        "binding_status": "bound" if source_audit_id else "standalone",
    }
    pack["provenance"] = provenance
    provenance["content_sha256"] = _canonical_json_sha256(pack)
    return pack


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
        f"- Evidence audit binding: `{pack['provenance']['binding_status']}`",
    ]

    if latest is not None:
        lines.extend(
            [
                f"- Latest evidence file: `{latest['path']}`",
                f"- Latest evidence modified at: `{latest['modified_at']}`",
            ]
        )

    helper = pack["otclient_helper"]
    phase_state = helper.get("roadmap_phase_state", {})
    p12_phase = (
        phase_state.get("p12") if isinstance(phase_state.get("p12"), dict) else {}
    )
    p12_conditions = (
        p12_phase.get("conditions")
        if isinstance(p12_phase.get("conditions"), dict)
        else {}
    )
    p12_equipment = (
        p12_phase.get("equipment")
        if isinstance(p12_phase.get("equipment"), dict)
        else {}
    )
    p12_heal_friend = (
        p12_phase.get("heal_friend")
        if isinstance(p12_phase.get("heal_friend"), dict)
        else {}
    )
    p13_phase = (
        phase_state.get("p13") if isinstance(phase_state.get("p13"), dict) else {}
    )
    p13_roadmap_state = (
        p13_phase.get("roadmap_state")
        if isinstance(p13_phase.get("roadmap_state"), dict)
        else {}
    )
    p14_phase = (
        phase_state.get("p14") if isinstance(phase_state.get("p14"), dict) else {}
    )
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
            f"- Roadmap phase evidence: `{phase_state.get('status', 'missing')}` "
            f"aligned=`{phase_state.get('aligned_with_current_roadmap', False)}`",
            f"- P8/P9/P10/P11: `{phase_state.get('p8', 'missing')}` / "
            f"`{phase_state.get('p9', 'missing')}` / "
            f"`{phase_state.get('p10', 'missing')}` / "
            f"`{phase_state.get('p11', 'missing')}`",
            f"- P12 Conditions/Equipment/Heal Friend: "
            f"`{p12_conditions.get('status', 'missing')}` / "
            f"`{p12_equipment.get('status', 'missing')}` / "
            f"`{p12_heal_friend.get('status', 'missing')}`",
            f"- P13 runtime evidence: `{p13_phase.get('status', 'missing')}` "
            f"contract_valid=`{p13_roadmap_state.get('contract_valid', False)}` "
            f"freshness=`{p13_roadmap_state.get('freshness_status', 'missing')}` "
            f"tamper=`{p13_roadmap_state.get('tamper_status', 'missing')}` "
            f"audit_binding=`{p13_roadmap_state.get('audit_binding_status', 'missing')}` "
            f"mode=`{p13_phase.get('control_center_mode', 'read_only')}`",
            f"- P14 independent runner: `{p14_phase.get('status', 'missing')}` "
            f"files=`{p14_phase.get('implementation_file_count', 0)}/"
            f"{p14_phase.get('required_file_count', len(P14_FOUNDATION_PATHS))}` "
            f"operational_result=`{p14_phase.get('operational_runner_result', 'missing')}` "
            f"operational_ready=`{p14_phase.get('operational_ready', False)}` "
            f"promotion_approved=`{p14_phase.get('promotion_approved', False)}`",
            f"- P12 Equipment current plan: "
            f"`{p12_equipment.get('current_plan_status', 'missing')}` "
            f"attempts=`{p12_equipment.get('attempt_count', 0)}` "
            f"session_approved=`{p12_equipment.get('session_approved', False)}` "
            f"execution_approved=`{p12_equipment.get('execution_approved', False)}`",
            f"- BackgroundNoScreen: `{helper.get('background_status', {}).get('status', 'missing')}` "
            f"integrity=`{helper.get('background_status', {}).get('integrity_status', 'missing')}` "
            f"capability=`{helper.get('background_status', {}).get('capability_status', 'missing')}` "
            f"contract_valid=`{helper.get('background_status', {}).get('contract_valid', False)}` "
            f"fresh=`{helper.get('background_status', {}).get('fresh', False)}` "
            f"advisory_only=`{helper.get('background_status', {}).get('advisory_only', False)}` "
            f"promotion_allowed=`{helper.get('background_status', {}).get('promotion_allowed', False)}` "
            f"dispatch_allowed=`{helper.get('background_status', {}).get('dispatch_allowed', False)}`",
            f"- Conditions Shadow: `{helper.get('conditions_shadow', {}).get('status', 'missing')}` "
            f"contract_valid=`{helper.get('conditions_shadow', {}).get('contract_valid', False)}` "
            f"fresh=`{helper.get('conditions_shadow', {}).get('fresh', False)}` "
            f"fixtures=`{helper.get('conditions_shadow', {}).get('fixture_validation_status', 'missing')}` "
            f"fixture_only_passed=`{helper.get('conditions_shadow', {}).get('fixture_only_validation_passed', False)}` "
            f"runtime_readiness_claimed=`{helper.get('conditions_shadow', {}).get('runtime_readiness_claimed', False)}` "
            f"dispatch_allowed=`{helper.get('conditions_shadow', {}).get('dispatch_allowed', False)}`",
            f"- Equipment Shadow: `{helper.get('equipment_shadow', {}).get('status', 'missing')}` "
            f"contract_valid=`{helper.get('equipment_shadow', {}).get('contract_valid', False)}` "
            f"fresh=`{helper.get('equipment_shadow', {}).get('fresh', False)}` "
            f"fixtures=`{helper.get('equipment_shadow', {}).get('fixture_validation_status', 'missing')}` "
            f"rollback=`{helper.get('equipment_shadow', {}).get('rollback_simulation', 'blocked')}` "
            f"dispatch_allowed=`{helper.get('equipment_shadow', {}).get('dispatch_allowed', False)}`",
            f"- Equipment Acceptance: `{helper.get('equipment_shadow_acceptance', {}).get('status', 'missing')}` "
            f"contract_valid=`{helper.get('equipment_shadow_acceptance', {}).get('contract_valid', False)}` "
            f"fresh=`{helper.get('equipment_shadow_acceptance', {}).get('fresh', False)}` "
            f"report_hash_match=`{helper.get('equipment_shadow_acceptance', {}).get('report_hash_match', False)}` "
            f"p11_eligible=`{helper.get('equipment_shadow_acceptance', {}).get('p11_predecessor_eligible', False)}`",
            f"- P10 Equipment Operator Readiness: `{helper.get('equipment_operator_readiness', {}).get('status', 'missing')}` "
            f"contract_valid=`{helper.get('equipment_operator_readiness', {}).get('contract_valid', False)}` "
            f"fresh=`{helper.get('equipment_operator_readiness', {}).get('fresh', False)}` "
            f"operator_inputs_ready=`{helper.get('equipment_operator_readiness', {}).get('operator_inputs_ready', False)}` "
            f"read_only=`{helper.get('equipment_operator_readiness', {}).get('read_only', True)}` "
            f"eligibility=`{helper.get('equipment_operator_readiness', {}).get('eligibility_state', 'unchanged')}`",
            f"- Package SHA256: `{helper['package_sha256'] or 'missing'}`",
            f"- Next command: `{helper['next_command'] or 'n/a'}`",
        ]
    )
    if helper["blockers"]:
        lines.extend(["", "### Helper Blockers", ""])
        for blocker in helper["blockers"][:8]:
            lines.append(f"- {blocker}")
    equipment_operator = helper.get("equipment_operator_readiness", {})
    if equipment_operator.get("blockers"):
        lines.extend(["", "### P10 Equipment Read-only Blockers", ""])
        for blocker in equipment_operator["blockers"][:8]:
            lines.append(f"- {blocker}")
    if equipment_operator.get("next_actions"):
        lines.extend(["", "### P10 Equipment Read-only Next Actions", ""])
        for action in equipment_operator["next_actions"][:7]:
            lines.append(
                f"- `{action.get('command', '')}`: {action.get('instruction', '')}"
            )
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
    parser.add_argument(
        "--source-audit-id",
        default="",
        help="Preallocated safe-write audit ID that binds this evidence artifact.",
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
        source_audit_id=args.source_audit_id,
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
