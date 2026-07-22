#!/usr/bin/env python3
"""Build a bounded, secret-free snapshot of P14 independent-runner readiness."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any
import zipfile


SCHEMA_VERSION = "ctoa.p14-runner-preflight.v2"
REMEDIATION_SCHEMA_VERSION = "ctoa.p14-remediation-plan.v1"
DEFAULT_REPOSITORY = "famatyyk/CTOAi"
WORKFLOW_PATH = ".github/workflows/p14-independent-runner-contract.yml"
WORKFLOW_NAME = "P14 Independent Runner Contract"
ENVIRONMENT_NAME = "p14-independent-runner"
PROTECTED_JOB = "Protected GitHub-hosted Windows signed artifact replay"
PROTECTED_ARTIFACT_PREFIX = "p14-protected-contract-"
LEGACY_PROTECTED_JOB = "Self-hosted Windows signed artifact replay"
LEGACY_ARTIFACT_PREFIX = "p14-self-hosted-contract-"
PROTECTED_ARTIFACT_PREFIXES = (
    PROTECTED_ARTIFACT_PREFIX,
    LEGACY_ARTIFACT_PREFIX,
)
RUNNER_PROVIDER = "github_hosted"
RUNNER_LABEL = "windows-latest"
# Compatibility alias for consumers that import the old constant directly.
SELF_HOSTED_JOB = PROTECTED_JOB
VERIFY_STEP = "Verify signed result handoff"
VERIFY_ACCEPTANCE_STEP = "Verify signed acceptance attestation"
SECRET_NAME = "CTOA_P14_RUNNER_SIGNING_KEY"
KEY_ID_VARIABLE = "CTOA_P14_RUNNER_KEY_ID"
AUTHORITY_FIELDS = (
    "live_authority",
    "mcp_write_tool_enabled",
    "p12_reopened",
    "promotion_approved",
    "runtime_actions",
    "runtime_executor_added",
)
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_COMMAND_BYTES = 512 * 1024
MAX_ARTIFACT_ZIP_BYTES = 1024 * 1024
MAX_ARTIFACT_MEMBER_BYTES = 128 * 1024
MAX_RUN_AGE_SECONDS = 24 * 60 * 60
EXPIRY_WARNING_SECONDS = 48 * 60 * 60

REMEDIATION_RULES: tuple[dict[str, Any], ...] = (
    {
        "action_id": "activate_p14_workflow",
        "capability": "workflow_active",
        "blockers": frozenset({"p14_workflow_not_active"}),
        "requires": frozenset(),
        "risk_class": "guarded_write",
        "interaction": "external_config",
        "priority": 100,
    },
    {
        "action_id": "restore_p14_runner_capacity",
        "capability": "runner_capacity",
        "blockers": frozenset(
            {"p14_required_runner_missing", "p14_required_runner_offline"}
        ),
        "requires": frozenset(),
        "risk_class": "guarded_write",
        "interaction": "external_config",
        "priority": 95,
    },
    {
        "action_id": "harden_p14_environment",
        "capability": "environment_protection",
        "blockers": frozenset(
            {
                "p14_environment_missing",
                "p14_environment_required_reviewer_missing",
                "p14_environment_admin_bypass_enabled",
            }
        ),
        "requires": frozenset(),
        "risk_class": "guarded_write",
        "interaction": "external_config",
        "priority": 90,
    },
    {
        "action_id": "configure_p14_signing_material",
        "capability": "signing_material",
        "blockers": frozenset(
            {"p14_signing_secret_missing", "p14_signing_key_id_missing"}
        ),
        "requires": frozenset(),
        "risk_class": "guarded_write",
        "interaction": "external_config",
        "priority": 85,
    },
    {
        "action_id": "allow_p14_source_branch",
        "capability": "branch_scope",
        "blockers": frozenset({"p14_environment_branch_policy_missing"}),
        "requires": frozenset(),
        "risk_class": "guarded_write",
        "interaction": "external_config",
        "priority": 80,
    },
    {
        "action_id": "refresh_p14_independent_runner_evidence",
        "capability": "external_attestation",
        "blockers": frozenset(
            {
                "p14_self_hosted_run_not_successful",
                "p14_workflow_signature_verification_missing",
                "p14_self_hosted_artifact_missing",
                "p14_self_hosted_artifact_expired",
                "p14_self_hosted_result_invalid",
                "p14_self_hosted_result_revision_mismatch",
                "p14_self_hosted_result_stale",
            }
        ),
        "requires": frozenset(
            {
                "workflow_active",
                "runner_capacity",
                "environment_protection",
                "signing_material",
                "branch_scope",
            }
        ),
        "risk_class": "safe_write",
        "interaction": "external_runner",
        "priority": 50,
    },
    {
        "action_id": "collect_p14_visual_evidence",
        "capability": "visual_attestation",
        "blockers": frozenset({"p14_visual_regression_not_proven"}),
        "requires": frozenset({"external_attestation"}),
        "risk_class": "safe_write",
        "interaction": "external_runner",
        "priority": 45,
    },
    {
        "action_id": "collect_p14_in_world_evidence",
        "capability": "in_world_attestation",
        "blockers": frozenset({"p14_in_world_regression_not_proven"}),
        "requires": frozenset({"external_attestation"}),
        "risk_class": "safe_write",
        "interaction": "external_runner",
        "priority": 44,
    },
    {
        "action_id": "run_p14_canary_rehearsal",
        "capability": "canary_attestation",
        "blockers": frozenset({"p14_canary_rehearsal_not_proven"}),
        "requires": frozenset({"visual_attestation", "in_world_attestation"}),
        "risk_class": "guarded_write",
        "interaction": "external_runner",
        "priority": 30,
    },
    {
        "action_id": "run_p14_rollback_rehearsal",
        "capability": "rollback_attestation",
        "blockers": frozenset({"p14_rollback_rehearsal_not_proven"}),
        "requires": frozenset({"canary_attestation"}),
        "risk_class": "guarded_write",
        "interaction": "external_runner",
        "priority": 20,
    },
)
MAX_REMEDIATION_ACTIONS = len(REMEDIATION_RULES) + 1
KNOWN_REMEDIATION_BLOCKERS = frozenset(
    blocker for rule in REMEDIATION_RULES for blocker in rule["blockers"]
)


class PreflightError(RuntimeError):
    """Raised when bounded external evidence cannot be collected safely."""


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _timestamp(value: Any) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def _safe_seconds(delta: dt.timedelta) -> int:
    return max(0, int(delta.total_seconds()))


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _authority_safe(value: Any) -> bool:
    authority = _mapping(value)
    return set(authority) == set(AUTHORITY_FIELDS) and all(
        authority.get(key) is False for key in AUTHORITY_FIELDS
    )


def _disabled_authority() -> dict[str, bool]:
    """Build the output authority boundary from the canonical field registry."""

    return {key: False for key in AUTHORITY_FIELDS}


def build_remediation_plan(blockers: list[str]) -> dict[str, Any]:
    """Derive a bounded capability plan without exposing external identities or values."""
    unique_blockers = list(dict.fromkeys(str(item) for item in blockers))
    blocker_set = set(unique_blockers)
    unknown_count = sum(
        1 for item in unique_blockers if item not in KNOWN_REMEDIATION_BLOCKERS
    )
    selected_rules = [
        rule for rule in REMEDIATION_RULES if blocker_set.intersection(rule["blockers"])
    ]
    missing_capabilities = {str(rule["capability"]) for rule in selected_rules}
    actions: list[dict[str, Any]] = []

    if unknown_count:
        actions.append(
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
        )

    for rule in selected_rules:
        missing_requirements = sorted(
            str(item) for item in rule["requires"] if item in missing_capabilities
        )
        actions.append(
            {
                "action_id": str(rule["action_id"]),
                "capability": str(rule["capability"]),
                "status": "blocked" if missing_requirements else "ready",
                "risk_class": str(rule["risk_class"]),
                "interaction": str(rule["interaction"]),
                "reason_codes": sorted(blocker_set.intersection(rule["blockers"]))[:6],
                "blocked_by": missing_requirements[:5],
                "auto_executable": False,
            }
        )

    priority = {
        str(rule["action_id"]): int(rule["priority"]) for rule in REMEDIATION_RULES
    }
    priority["review_p14_external_state"] = 110
    actions.sort(
        key=lambda item: (
            item["status"] != "ready",
            -priority.get(str(item["action_id"]), 0),
            str(item["action_id"]),
        )
    )
    selected = next(
        (item for item in actions if item["status"] == "ready"),
        None,
    )
    bounded_actions = actions[:MAX_REMEDIATION_ACTIONS]
    complete = not unique_blockers
    return {
        "schema_version": REMEDIATION_SCHEMA_VERSION,
        "status": "complete"
        if complete
        else "review_required"
        if unknown_count
        else "action_required",
        "next_action": str(selected["action_id"]) if selected else "none",
        "interaction": str(selected["interaction"]) if selected else "none",
        "risk_class": str(selected["risk_class"]) if selected else "read_only",
        "action_count": len(bounded_actions),
        "ready_action_count": sum(
            1 for item in bounded_actions if item["status"] == "ready"
        ),
        "blocked_action_count": sum(
            1 for item in bounded_actions if item["status"] == "blocked"
        ),
        "unknown_blocker_count": unknown_count,
        "actions": bounded_actions,
        "authority": {
            "auto_execute": False,
            "live_mutation": False,
            "authority_grant": False,
        },
        "policy": "Capability-derived external remediation. Unknown blockers fail to review; no action auto-executes or grants authority.",
    }


def remediation_plan_valid(value: Any) -> bool:
    """Validate the minimized remediation graph without trusting its producer."""
    if not isinstance(value, dict):
        return False
    actions = value.get("actions")
    counts = (
        value.get("action_count"),
        value.get("ready_action_count"),
        value.get("blocked_action_count"),
        value.get("unknown_blocker_count"),
    )
    if (
        value.get("schema_version") != REMEDIATION_SCHEMA_VERSION
        or not isinstance(actions, list)
        or len(actions) > MAX_REMEDIATION_ACTIONS
        or any(type(item) is not int or item < 0 for item in counts)
    ):
        return False
    action_count, ready_count, blocked_count, unknown_count = counts
    if len(actions) != action_count or ready_count + blocked_count != action_count:
        return False
    if value.get("authority") not in (
        None,
        {
            "auto_execute": False,
            "live_mutation": False,
            "authority_grant": False,
        },
    ):
        return False
    if value.get("status") == "complete":
        return bool(
            value.get("next_action") == "none"
            and value.get("interaction") == "none"
            and value.get("risk_class") == "read_only"
            and counts == (0, 0, 0, 0)
            and actions == []
        )
    if value.get("status") not in {"action_required", "review_required"}:
        return False

    contracts = {str(item["action_id"]): item for item in REMEDIATION_RULES}
    capabilities = {
        str(item.get("capability")) for item in actions if isinstance(item, dict)
    }
    seen: set[str] = set()
    ready_actions: list[dict[str, Any]] = []
    observed_blocked = 0
    review_seen = False
    for item in actions:
        if not isinstance(item, dict):
            return False
        action_id = str(item.get("action_id") or "")
        if not action_id or action_id in seen:
            return False
        seen.add(action_id)
        blocked_by = item.get("blocked_by")
        reason_codes = item.get("reason_codes")
        if (
            not isinstance(blocked_by, list)
            or len(blocked_by) > 5
            or len(set(blocked_by)) != len(blocked_by)
            or not isinstance(reason_codes, list)
            or not 1 <= len(reason_codes) <= 6
            or len(set(reason_codes)) != len(reason_codes)
            or item.get("auto_executable") is not False
        ):
            return False
        if action_id == "review_p14_external_state":
            review_seen = True
            expected = {
                "capability": "external_evidence_review",
                "status": "ready",
                "risk_class": "read_only",
                "interaction": "operator_review",
                "reason_codes": ["unclassified_blocker"],
                "blocked_by": [],
            }
        else:
            contract = contracts.get(action_id)
            if contract is None or not set(reason_codes).issubset(contract["blockers"]):
                return False
            expected_blocked_by = sorted(
                str(required)
                for required in contract["requires"]
                if required in capabilities
            )[:5]
            expected = {
                "capability": str(contract["capability"]),
                "status": "blocked" if expected_blocked_by else "ready",
                "risk_class": str(contract["risk_class"]),
                "interaction": str(contract["interaction"]),
                "reason_codes": reason_codes,
                "blocked_by": expected_blocked_by,
            }
        if any(
            item.get(key) != expected_value for key, expected_value in expected.items()
        ):
            return False
        if item.get("status") == "ready":
            ready_actions.append(item)
        else:
            observed_blocked += 1

    selected = next(
        (
            item
            for item in ready_actions
            if item.get("action_id") == value.get("next_action")
        ),
        None,
    )
    return bool(
        selected
        and len(ready_actions) == ready_count
        and observed_blocked == blocked_count
        and value.get("interaction") == selected.get("interaction")
        and value.get("risk_class") == selected.get("risk_class")
        and review_seen is (unknown_count > 0)
        and value.get("status")
        == ("review_required" if unknown_count else "action_required")
    )


def _step_passed(job: dict[str, Any], name: str) -> bool:
    return any(
        step.get("name") == name and step.get("conclusion") == "success"
        for step in _rows(job.get("steps"))
    )


def _protected_job(run: dict[str, Any]) -> dict[str, Any]:
    jobs = _rows(run.get("jobs"))
    protected = next(
        (item for item in jobs if item.get("name") == PROTECTED_JOB), {}
    )
    return protected or next(
        (item for item in jobs if item.get("name") == LEGACY_PROTECTED_JOB), {}
    )


def _protected_run_attempted(run: dict[str, Any]) -> bool:
    job = _protected_job(run)
    return bool(
        job
        and job.get("status") != "skipped"
        and job.get("conclusion") != "skipped"
    )


def _structural_result_valid(request: dict[str, Any], result: dict[str, Any]) -> bool:
    checks = _rows(result.get("checks"))
    request_signature = _mapping(request.get("signature"))
    result_signature = _mapping(result.get("signature"))
    runner = _mapping(result.get("runner"))
    rollback = _mapping(result.get("rollback"))
    return bool(
        request.get("schema_version") == "ctoa.p14-runner-request.v1"
        and result.get("schema_version") == "ctoa.p14-runner-result.v1"
        and result.get("status") == "passed"
        and result.get("request_id") == request.get("request_id")
        and result.get("request_sha256") == canonical_sha256(request)
        and _authority_safe(request.get("authority"))
        and _authority_safe(result.get("authority"))
        and result.get("blockers") == []
        and len(checks) > 0
        and all(check.get("status") == "passed" for check in checks)
        and runner.get("artifact_only") is True
        and runner.get("clean_checkout_proven") is True
        and runner.get("revision_match") is True
        and runner.get("live_client_accessed") is False
        and runner.get("network_dispatch_used") is False
        and runner.get("operator_workstation_focus_used") is False
        and runner.get("operator_workstation_input_used") is False
        and rollback.get("status") == "manifest_replay_passed"
        and request_signature.get("algorithm") == "hmac-sha256"
        and result_signature.get("algorithm") == "hmac-sha256"
        and request_signature.get("key_id") == result_signature.get("key_id")
        and bool(request_signature.get("value"))
        and bool(result_signature.get("value"))
    )


ACCEPTANCE_CAPABILITIES = (
    "visual_regression",
    "in_world_regression",
    "canary_rehearsal",
    "rollback_rehearsal",
)
ACCEPTANCE_PROOFS = {
    "visual_regression": (
        "isolated_visual_capture",
        "independent_visual_review",
    ),
    "in_world_regression": (
        "isolated_client_launch",
        "helper_runtime_smoke",
        "independent_in_world_review",
    ),
    "canary_rehearsal": (
        "sandbox_canary_apply",
        "canary_health_check",
    ),
    "rollback_rehearsal": (
        "rollback_apply",
        "baseline_restore_verified",
    ),
}
ACCEPTANCE_BLOCKERS = {
    "visual_regression": "p14_visual_regression_not_proven",
    "in_world_regression": "p14_in_world_regression_not_proven",
    "canary_rehearsal": "p14_canary_rehearsal_not_proven",
    "rollback_rehearsal": "p14_rollback_rehearsal_not_proven",
}
ACCEPTANCE_ISOLATION = {
    "isolated_environment": True,
    "operator_workstation_focus_used": False,
    "operator_workstation_input_used": False,
    "network_dispatch_used": False,
    "live_client_accessed": False,
    "promotion_attempted": False,
}


def _signature_safe(value: Any, expected_key_id: str) -> bool:
    signature = _mapping(value)
    return bool(
        signature.get("algorithm") == "hmac-sha256"
        and signature.get("key_id") == expected_key_id
        and isinstance(signature.get("value"), str)
        and SHA256_RE.fullmatch(signature["value"])
    )


def _acceptance_transition_valid(capability: str, value: Any) -> bool:
    if capability in {"visual_regression", "in_world_regression"}:
        return value is None
    transition = _mapping(value)
    baseline = transition.get("baseline_manifest_sha256")
    changed = transition.get("changed_manifest_sha256")
    restored = transition.get("restored_manifest_sha256")
    changed_count = transition.get("changed_file_count")
    common = bool(
        isinstance(baseline, str)
        and SHA256_RE.fullmatch(baseline)
        and isinstance(changed, str)
        and SHA256_RE.fullmatch(changed)
        and isinstance(restored, str)
        and SHA256_RE.fullmatch(restored)
        and baseline != changed
        and type(changed_count) is int
        and 1 <= changed_count <= 256
    )
    if not common:
        return False
    return restored == (changed if capability == "canary_rehearsal" else baseline)


def _acceptance_capability_valid(value: Any) -> tuple[str, bool] | None:
    capability = _mapping(value)
    capability_id = str(capability.get("capability") or "")
    expected_proofs = ACCEPTANCE_PROOFS.get(capability_id)
    proofs = _rows(capability.get("proofs"))
    if expected_proofs is None or len(proofs) != len(expected_proofs):
        return None
    proof_map = {str(item.get("proof_id") or ""): item for item in proofs}
    if len(proof_map) != len(proofs) or set(proof_map) != set(expected_proofs):
        return None
    for proof_id in expected_proofs:
        proof = proof_map[proof_id]
        status = proof.get("status")
        count = proof.get("artifact_count")
        digest = proof.get("evidence_sha256")
        if (
            status not in {"passed", "blocked"}
            or type(count) is not int
            or not 0 <= count <= 16
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
            or status == "passed"
            and (count < 1 or digest == "0" * 64)
        ):
            return None
    passed = all(proof_map[item].get("status") == "passed" for item in expected_proofs)
    if capability.get("status") != ("passed" if passed else "blocked"):
        return None
    if not _acceptance_transition_valid(capability_id, capability.get("transition")):
        return None
    return capability_id, passed


def _acceptance_summary(
    runner_request: dict[str, Any],
    runner_result: dict[str, Any],
    acceptance_request: dict[str, Any],
    acceptance_result: dict[str, Any],
    *,
    source_current: bool,
    signature_step_passed: bool,
) -> dict[str, Any]:
    request_present = bool(acceptance_request)
    result_present = bool(acceptance_result)
    runner_source = _mapping(runner_request.get("source"))
    runner_signature = _mapping(runner_request.get("signature"))
    key_id = str(runner_signature.get("key_id") or "")
    binding = _mapping(acceptance_request.get("binding"))
    required = acceptance_request.get("required_capabilities")
    required_valid = bool(
        isinstance(required, list)
        and 1 <= len(required) <= len(ACCEPTANCE_CAPABILITIES)
        and len(required) == len(set(required))
        and all(item in ACCEPTANCE_CAPABILITIES for item in required)
    )
    request_valid = bool(
        request_present
        and acceptance_request.get("schema_version") == "ctoa.p14-acceptance-request.v1"
        and acceptance_request.get("phase") == "P14"
        and acceptance_request.get("status") == "ready_for_isolated_acceptance"
        and required_valid
        and binding.get("source_revision") == runner_source.get("revision")
        and binding.get("runner_request_id") == runner_request.get("request_id")
        and binding.get("runner_result_id") == runner_result.get("result_id")
        and binding.get("runner_request_sha256") == canonical_sha256(runner_request)
        and binding.get("runner_result_sha256") == canonical_sha256(runner_result)
        and binding.get("helper_manifest_sha256")
        == runner_source.get("helper_manifest_sha256")
        and _authority_safe(acceptance_request.get("authority"))
        and _signature_safe(acceptance_request.get("signature"), key_id)
    )

    capability_rows = _rows(acceptance_result.get("capabilities"))
    capability_states: dict[str, bool] = {}
    capabilities_valid = bool(
        request_valid and len(capability_rows) == len(required or [])
    )
    if capabilities_valid:
        for row in capability_rows:
            normalized = _acceptance_capability_valid(row)
            if normalized is None or normalized[0] in capability_states:
                capabilities_valid = False
                break
            capability_states[normalized[0]] = normalized[1]
        if set(capability_states) != set(required or []):
            capabilities_valid = False

    expected_blockers = (
        [
            ACCEPTANCE_BLOCKERS[item]
            for item in required or []
            if capability_states.get(item) is not True
        ]
        if capabilities_valid
        else []
    )
    passed_count = sum(1 for value in capability_states.values() if value)
    expected_status = (
        "passed"
        if capabilities_valid and not expected_blockers
        else "partial"
        if capabilities_valid and passed_count
        else "blocked"
    )
    result_valid = bool(
        result_present
        and request_valid
        and capabilities_valid
        and acceptance_result.get("schema_version") == "ctoa.p14-acceptance-result.v1"
        and acceptance_result.get("request_id") == acceptance_request.get("request_id")
        and acceptance_result.get("request_sha256")
        == canonical_sha256(acceptance_request)
        and acceptance_result.get("source_revision") == binding.get("source_revision")
        and acceptance_result.get("status") == expected_status
        and acceptance_result.get("blockers") == expected_blockers
        and acceptance_result.get("isolation") == ACCEPTANCE_ISOLATION
        and _authority_safe(acceptance_result.get("authority"))
        and _signature_safe(acceptance_result.get("signature"), key_id)
    )
    trusted = bool(result_valid and source_current and signature_step_passed)
    proven = {
        capability: bool(trusted and capability_states.get(capability) is True)
        for capability in ACCEPTANCE_CAPABILITIES
    }
    complete = all(proven.values())
    status = (
        "passed"
        if complete
        else "result_untrusted"
        if result_present and not trusted
        else "partial"
        if result_valid and passed_count
        else "request_ready"
        if request_valid
        else "missing"
        if not request_present and not result_present
        else "invalid"
    )
    return {
        "status": status,
        "request_present": request_present,
        "request_valid": request_valid,
        "result_present": result_present,
        "result_valid": result_valid,
        "signature_verification_passed": signature_step_passed,
        "source_current": source_current,
        "proven_capability_count": sum(1 for value in proven.values() if value),
        "required_capability_count": len(ACCEPTANCE_CAPABILITIES),
        "capabilities": proven,
        "complete": complete,
        "authority_safe": bool(
            _authority_safe(acceptance_request.get("authority"))
            and _authority_safe(acceptance_result.get("authority"))
        )
        if request_present and result_present
        else False,
    }


def build_preflight(
    *,
    workflow: dict[str, Any],
    run: dict[str, Any],
    runners: dict[str, Any],
    environment: dict[str, Any],
    secrets: dict[str, Any],
    variables: dict[str, Any],
    branch_policies: dict[str, Any],
    artifacts: dict[str, Any],
    request: dict[str, Any],
    result: dict[str, Any],
    current_branch: str,
    current_head: str,
    acceptance_request: dict[str, Any] | None = None,
    acceptance_result: dict[str, Any] | None = None,
    generated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    """Build a fail-closed projection from already collected GitHub evidence."""
    # Kept in the call contract so older callers can pass their runner snapshot.
    # GitHub-hosted capacity is derived from the active workflow instead of a
    # repository-level self-hosted runner registration.
    del runners
    now = (generated_at or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    blockers: list[str] = []
    warnings: list[str] = []

    workflow_active = bool(
        workflow.get("name") == WORKFLOW_NAME
        and workflow.get("path") == WORKFLOW_PATH
        and workflow.get("state") == "active"
    )
    if not workflow_active:
        blockers.append("p14_workflow_not_active")

    runner_capacity_ready = workflow_active

    rules = _rows(environment.get("protection_rules"))
    reviewer_rules = [
        item for item in rules if item.get("type") == "required_reviewers"
    ]
    reviewer_count = sum(len(_rows(item.get("reviewers"))) for item in reviewer_rules)
    required_reviewer_configured = reviewer_count > 0
    admin_bypass_disabled = environment.get("can_admins_bypass") is False
    if environment.get("name") != ENVIRONMENT_NAME:
        blockers.append("p14_environment_missing")
    if not required_reviewer_configured:
        blockers.append("p14_environment_required_reviewer_missing")
    if not admin_bypass_disabled:
        blockers.append("p14_environment_admin_bypass_enabled")

    secret_names = {
        str(item.get("name") or "") for item in _rows(secrets.get("secrets"))
    }
    variable_rows = _rows(variables.get("variables"))
    signing_secret_configured = SECRET_NAME in secret_names
    key_id_configured = any(
        item.get("name") == KEY_ID_VARIABLE
        and bool(str(item.get("value") or "").strip())
        for item in variable_rows
    )
    if not signing_secret_configured:
        blockers.append("p14_signing_secret_missing")
    if not key_id_configured:
        blockers.append("p14_signing_key_id_missing")

    policy_names = {
        str(item.get("name") or "")
        for item in _rows(branch_policies.get("branch_policies"))
    }
    branch_allowed = current_branch in policy_names
    if not branch_allowed:
        blockers.append("p14_environment_branch_policy_missing")

    protected_job = _protected_job(run)
    run_success = bool(
        run.get("event") == "workflow_dispatch"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and protected_job.get("conclusion") == "success"
    )
    signature_verification_passed = _step_passed(protected_job, VERIFY_STEP)
    acceptance_signature_verification_passed = _step_passed(
        protected_job, VERIFY_ACCEPTANCE_STEP
    )
    if not run_success:
        blockers.append("p14_self_hosted_run_not_successful")
    if not signature_verification_passed:
        blockers.append("p14_workflow_signature_verification_missing")

    artifact_rows = _rows(artifacts.get("artifacts"))
    protected_artifact = next(
        (
            item
            for item in artifact_rows
            if str(item.get("name") or "").startswith(PROTECTED_ARTIFACT_PREFIXES)
        ),
        {},
    )
    artifact_present = bool(protected_artifact)
    artifact_unexpired = artifact_present and protected_artifact.get("expired") is False
    if not artifact_present:
        blockers.append("p14_self_hosted_artifact_missing")
    elif not artifact_unexpired:
        blockers.append("p14_self_hosted_artifact_expired")

    structural_result_valid = _structural_result_valid(request, result)
    if not structural_result_valid:
        blockers.append("p14_self_hosted_result_invalid")

    source = _mapping(request.get("source"))
    runner_result = _mapping(result.get("runner"))
    result_revision = str(
        runner_result.get("source_revision") or source.get("revision") or ""
    )
    source_revision_match = bool(
        re.fullmatch(r"[0-9a-f]{40}", current_head)
        and result_revision == current_head
        and runner_result.get("source_revision") == source.get("revision")
    )
    if structural_result_valid and not source_revision_match:
        blockers.append("p14_self_hosted_result_revision_mismatch")

    acceptance = _acceptance_summary(
        request,
        result,
        _mapping(acceptance_request),
        _mapping(acceptance_result),
        source_current=bool(structural_result_valid and source_revision_match),
        signature_step_passed=acceptance_signature_verification_passed,
    )
    for capability, blocker in ACCEPTANCE_BLOCKERS.items():
        if acceptance["capabilities"].get(capability) is not True:
            blockers.append(blocker)

    run_time = _timestamp(run.get("updatedAt") or run.get("updated_at"))
    run_age_seconds = (
        _safe_seconds(now - run_time) if run_time is not None and now >= run_time else 0
    )
    run_fresh = bool(run_time is not None and run_age_seconds <= MAX_RUN_AGE_SECONDS)
    if run_success and not run_fresh:
        blockers.append("p14_self_hosted_result_stale")

    expires_at = _timestamp(protected_artifact.get("expires_at"))
    expires_in_seconds = (
        _safe_seconds(expires_at - now)
        if expires_at is not None and expires_at >= now
        else 0
    )
    if artifact_unexpired and expires_in_seconds <= EXPIRY_WARNING_SECONDS:
        warnings.append("p14_self_hosted_artifact_expiring")

    blockers = list(dict.fromkeys(blockers))
    warnings = list(dict.fromkeys(warnings))
    operational_ready = not blockers
    if structural_result_valid and signature_verification_passed:
        operational_result = (
            "externally_verified_current"
            if source_revision_match
            else "externally_verified_stale"
        )
    elif request or result:
        operational_result = "external_result_invalid"
    else:
        operational_result = "missing"

    remediation = build_remediation_plan(blockers)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "status": "ready" if operational_ready else "needs_attention",
        "operational_result": operational_result,
        "operational_ready": operational_ready,
        "hard_blockers": blockers,
        "warnings": warnings,
        "workflow": {
            "active": workflow_active,
            "runner_provider": RUNNER_PROVIDER,
            "protected_run_success": run_success,
            "self_hosted_run_success": run_success,
            "signature_verification_passed": signature_verification_passed,
            "acceptance_signature_verification_passed": (
                acceptance_signature_verification_passed
            ),
            "run_fresh": run_fresh,
            "run_age_seconds": run_age_seconds,
        },
        "runner": {
            "provider": RUNNER_PROVIDER,
            "label": RUNNER_LABEL,
            "ephemeral": True,
            "matching_count": 1 if runner_capacity_ready else 0,
            "online": runner_capacity_ready,
            "required_labels_complete": runner_capacity_ready,
        },
        "environment": {
            "required_reviewer_configured": required_reviewer_configured,
            "required_reviewer_count": reviewer_count,
            "admin_bypass_disabled": admin_bypass_disabled,
            "branch_allowed": branch_allowed,
            "signing_secret_configured": signing_secret_configured,
            "key_id_configured": key_id_configured,
        },
        "artifact": {
            "present": artifact_present,
            "unexpired": artifact_unexpired,
            "expires_in_seconds": expires_in_seconds,
        },
        "result": {
            "status": str(result.get("status") or "missing")[:40],
            "structural_valid": structural_result_valid,
            "source_revision_match": source_revision_match,
            "clean_checkout_proven": runner_result.get("clean_checkout_proven") is True,
            "authority_safe": _authority_safe(result.get("authority")),
            "rollback_status": str(
                _mapping(result.get("rollback")).get("status") or "missing"
            )[:80],
        },
        "acceptance": acceptance,
        "remediation": remediation,
        "authority": _disabled_authority(),
        "policy": "Read-only external preflight. Secret values, signatures, runner identity, URLs, commands, and artifact payloads are omitted.",
    }


def _run(
    command: list[str], *, binary: bool = False, cwd: Path | None = None
) -> str | bytes:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=not binary,
        timeout=30,
        cwd=cwd,
    )
    if completed.returncode != 0:
        raise PreflightError("external_command_failed")
    output = completed.stdout
    if len(output) > MAX_COMMAND_BYTES:
        raise PreflightError("external_response_too_large")
    return output


def _json_command(command: list[str]) -> Any:
    output = _run(command)
    try:
        return json.loads(str(output))
    except json.JSONDecodeError as exc:
        raise PreflightError("external_response_invalid") from exc


def _artifact_bundle(
    repository: str, artifact_id: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw = _run(
        [
            "gh",
            "api",
            f"repos/{repository}/actions/artifacts/{artifact_id}/zip",
        ],
        binary=True,
    )
    if not isinstance(raw, bytes) or len(raw) > MAX_ARTIFACT_ZIP_BYTES:
        raise PreflightError("artifact_archive_invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members: dict[str, zipfile.ZipInfo] = {}
            for item in archive.infolist():
                if item.is_dir():
                    raise PreflightError("artifact_members_invalid")
                member_path = PurePosixPath(item.filename)
                name = member_path.name
                # Artifact input is untrusted. Require exactly one flat,
                # allowlisted filename so a nested member cannot shadow a
                # required file after basename normalization.
                if (
                    "\\" in item.filename
                    or member_path.is_absolute()
                    or len(member_path.parts) != 1
                    or item.filename != name
                    or name in members
                ):
                    raise PreflightError("artifact_members_invalid")
                members[name] = item
            names = set(members)
            required_names = {"request.json", "result.json"}
            allowed_names = required_names | {
                "acceptance-request.json",
                "acceptance-result.json",
                # This is an isolated-runner input which can contain free-form
                # evidence. Its signed, minimized derivative is
                # acceptance-result.json; never load the report into this
                # public preflight projection.
                "acceptance-report.json",
            }
            if (
                not required_names.issubset(names)
                or not names.issubset(allowed_names)
                or "acceptance-result.json" in names
                and "acceptance-request.json" not in names
            ):
                raise PreflightError("artifact_members_invalid")
            values: dict[str, dict[str, Any]] = {}
            for name, member in members.items():
                if (
                    member.file_size <= 0
                    or member.file_size > MAX_ARTIFACT_MEMBER_BYTES
                ):
                    raise PreflightError("artifact_member_size_invalid")
                if name == "acceptance-report.json":
                    continue
                payload = json.loads(archive.read(member))
                if not isinstance(payload, dict):
                    raise PreflightError("artifact_payload_invalid")
                values[name] = payload
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError("artifact_archive_invalid") from exc
    return (
        values["request.json"],
        values["result.json"],
        values.get("acceptance-request.json", {}),
        values.get("acceptance-result.json", {}),
    )


def collect_preflight(
    repository: str = DEFAULT_REPOSITORY, *, workspace: Path | None = None
) -> dict[str, Any]:
    if not REPOSITORY_RE.fullmatch(repository):
        raise PreflightError("repository_invalid")
    root = (workspace or Path(__file__).resolve().parents[2]).resolve(strict=True)
    workflow_rows = _json_command(
        [
            "gh",
            "workflow",
            "list",
            "--all",
            "--repo",
            repository,
            "--json",
            "name,path,state,id",
        ]
    )
    workflow = next(
        (item for item in _rows(workflow_rows) if item.get("path") == WORKFLOW_PATH),
        {},
    )
    runs = _json_command(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repository,
            "--workflow",
            PurePosixPath(WORKFLOW_PATH).name,
            "--limit",
            "20",
            "--json",
            "databaseId,status,conclusion,event,headBranch,headSha,createdAt,updatedAt",
        ]
    )
    candidate_runs = [
        item for item in _rows(runs) if item.get("event") == "workflow_dispatch"
    ]
    if not candidate_runs:
        raise PreflightError("manual_run_missing")
    run: dict[str, Any] = {}
    run_id = 0
    for candidate in candidate_runs:
        try:
            candidate_id = int(candidate.get("databaseId") or 0)
        except (TypeError, ValueError) as exc:
            raise PreflightError("manual_run_invalid") from exc
        if candidate_id <= 0:
            continue
        candidate_run = _mapping(
            _json_command(
                [
                    "gh",
                    "run",
                    "view",
                    str(candidate_id),
                    "--repo",
                    repository,
                    "--json",
                    "databaseId,status,conclusion,event,headBranch,headSha,createdAt,updatedAt,jobs",
                ]
            )
        )
        # The default dispatch leaves the protected job skipped. Select the
        # newest run that actually attempted it, even when it failed, so an
        # older passing replay cannot mask the current protected state.
        if (
            candidate_run.get("event") == "workflow_dispatch"
            and _protected_run_attempted(candidate_run)
        ):
            run_id = candidate_id
            run = candidate_run
            break
    if run_id <= 0:
        raise PreflightError("protected_manual_run_missing")
    environment = _json_command(
        ["gh", "api", f"repos/{repository}/environments/{ENVIRONMENT_NAME}"]
    )
    secrets = _json_command(
        [
            "gh",
            "api",
            f"repos/{repository}/environments/{ENVIRONMENT_NAME}/secrets",
        ]
    )
    variables = _json_command(
        [
            "gh",
            "api",
            f"repos/{repository}/environments/{ENVIRONMENT_NAME}/variables",
        ]
    )
    branch_policies = _json_command(
        [
            "gh",
            "api",
            f"repos/{repository}/environments/{ENVIRONMENT_NAME}/deployment-branch-policies",
        ]
    )
    artifacts = _json_command(
        ["gh", "api", f"repos/{repository}/actions/runs/{run_id}/artifacts"]
    )
    artifact = next(
        (
            item
            for item in _rows(_mapping(artifacts).get("artifacts"))
            if str(item.get("name") or "").startswith(PROTECTED_ARTIFACT_PREFIXES)
        ),
        {},
    )
    artifact_id = int(artifact.get("id") or 0)
    request: dict[str, Any] = {}
    result: dict[str, Any] = {}
    acceptance_request: dict[str, Any] = {}
    acceptance_result: dict[str, Any] = {}
    if artifact_id > 0 and artifact.get("expired") is False:
        request, result, acceptance_request, acceptance_result = _artifact_bundle(
            repository, artifact_id
        )
    current_branch = str(
        _run(["git", "branch", "--show-current"], cwd=root)
    ).strip()
    current_head = str(_run(["git", "rev-parse", "HEAD"], cwd=root)).strip()
    return build_preflight(
        workflow=workflow,
        run=_mapping(run),
        runners={},
        environment=_mapping(environment),
        secrets=_mapping(secrets),
        variables=_mapping(variables),
        branch_policies=_mapping(branch_policies),
        artifacts=_mapping(artifacts),
        request=request,
        result=result,
        acceptance_request=acceptance_request,
        acceptance_result=acceptance_result,
        current_branch=current_branch,
        current_head=current_head,
    )


def unavailable_snapshot() -> dict[str, Any]:
    blockers = ["p14_external_state_unavailable"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "status": "unavailable",
        "operational_result": "missing",
        "operational_ready": False,
        "hard_blockers": blockers,
        "warnings": [],
        "remediation": build_remediation_plan(blockers),
        "authority": _disabled_authority(),
        "policy": "Read-only external preflight. Failure details and external data are omitted.",
    }


def _write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.workspace.resolve(strict=False)
    try:
        payload = collect_preflight(args.repository, workspace=root)
    except (OSError, subprocess.SubprocessError, PreflightError):
        payload = unavailable_snapshot()
    if not args.no_write:
        output = root / "runtime" / "control-center" / "p14-runner-preflight.json"
        _write_atomic(output, payload)
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("status") != "unavailable" else 2


if __name__ == "__main__":
    raise SystemExit(main())
