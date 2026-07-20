from __future__ import annotations

import datetime as dt

from scripts.ops import otclient_p14_runner_preflight as preflight


AUTHORITY = {key: False for key in preflight.AUTHORITY_FIELDS}
REVISION = "a" * 40


def _request() -> dict:
    return {
        "schema_version": "ctoa.p14-runner-request.v1",
        "request_id": "p14-1111111111111111",
        "source": {
            "revision": REVISION,
            "helper_manifest_sha256": "c" * 64,
        },
        "authority": dict(AUTHORITY),
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": "independent-runner-prod-v1",
            "value": "a" * 64,
        },
    }


def _result(request: dict) -> dict:
    return {
        "schema_version": "ctoa.p14-runner-result.v1",
        "result_id": "p14-result-2222222222222222",
        "request_id": request["request_id"],
        "request_sha256": preflight.canonical_sha256(request),
        "status": "passed",
        "runner": {
            "artifact_only": True,
            "clean_checkout_proven": True,
            "revision_match": True,
            "source_revision": REVISION,
            "live_client_accessed": False,
            "network_dispatch_used": False,
            "operator_workstation_focus_used": False,
            "operator_workstation_input_used": False,
        },
        "checks": [{"id": "schema", "status": "passed"}],
        "rollback": {"status": "manifest_replay_passed"},
        "authority": dict(AUTHORITY),
        "blockers": [],
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": "independent-runner-prod-v1",
            "value": "b" * 64,
        },
    }


def _acceptance_bundle(request: dict, result: dict) -> tuple[dict, dict]:
    capabilities = []
    for index, capability_id in enumerate(preflight.ACCEPTANCE_CAPABILITIES):
        proofs = [
            {
                "proof_id": proof_id,
                "status": "passed",
                "artifact_count": 1,
                "evidence_sha256": str(index + 1) * 64,
            }
            for proof_id in preflight.ACCEPTANCE_PROOFS[capability_id]
        ]
        transition = None
        if capability_id == "canary_rehearsal":
            transition = {
                "baseline_manifest_sha256": "a" * 64,
                "changed_manifest_sha256": "b" * 64,
                "restored_manifest_sha256": "b" * 64,
                "changed_file_count": 3,
            }
        elif capability_id == "rollback_rehearsal":
            transition = {
                "baseline_manifest_sha256": "a" * 64,
                "changed_manifest_sha256": "b" * 64,
                "restored_manifest_sha256": "a" * 64,
                "changed_file_count": 3,
            }
        capabilities.append(
            {
                "capability": capability_id,
                "status": "passed",
                "proofs": proofs,
                "transition": transition,
            }
        )
    acceptance_request = {
        "schema_version": "ctoa.p14-acceptance-request.v1",
        "request_id": "p14-accept-3333333333333333",
        "phase": "P14",
        "status": "ready_for_isolated_acceptance",
        "binding": {
            "source_revision": REVISION,
            "runner_request_id": request["request_id"],
            "runner_result_id": result["result_id"],
            "runner_request_sha256": preflight.canonical_sha256(request),
            "runner_result_sha256": preflight.canonical_sha256(result),
            "helper_manifest_sha256": request["source"]["helper_manifest_sha256"],
        },
        "required_capabilities": list(preflight.ACCEPTANCE_CAPABILITIES),
        "authority": dict(AUTHORITY),
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": "independent-runner-prod-v1",
            "value": "d" * 64,
        },
    }
    acceptance_result = {
        "schema_version": "ctoa.p14-acceptance-result.v1",
        "request_id": acceptance_request["request_id"],
        "request_sha256": preflight.canonical_sha256(acceptance_request),
        "source_revision": REVISION,
        "status": "passed",
        "isolation": dict(preflight.ACCEPTANCE_ISOLATION),
        "capabilities": capabilities,
        "blockers": [],
        "authority": dict(AUTHORITY),
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": "independent-runner-prod-v1",
            "value": "e" * 64,
        },
    }
    return acceptance_request, acceptance_result


def _inputs(
    *,
    secure_environment: bool = True,
    revision: str = REVISION,
    acceptance: bool = True,
) -> dict:
    now = dt.datetime(2026, 7, 16, 15, 0, tzinfo=dt.UTC)
    request = _request()
    result = _result(request)
    acceptance_request, acceptance_result = _acceptance_bundle(request, result)
    return {
        "workflow": {
            "name": preflight.WORKFLOW_NAME,
            "path": preflight.WORKFLOW_PATH,
            "state": "active",
        },
        "run": {
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "updatedAt": (now - dt.timedelta(hours=1)).isoformat(),
            "jobs": [
                {
                    "name": preflight.PROTECTED_JOB,
                    "conclusion": "success",
                    "steps": [
                        {"name": preflight.VERIFY_STEP, "conclusion": "success"},
                        {
                            "name": preflight.VERIFY_ACCEPTANCE_STEP,
                            "conclusion": "success",
                        },
                    ],
                }
            ],
        },
        "runners": {},
        "environment": {
            "name": preflight.ENVIRONMENT_NAME,
            "can_admins_bypass": not secure_environment,
            "protection_rules": [
                {
                    "type": "required_reviewers",
                    "reviewers": [{"type": "User"}],
                }
            ]
            if secure_environment
            else [{"type": "branch_policy"}],
        },
        "secrets": {"secrets": [{"name": preflight.SECRET_NAME}]},
        "variables": {
            "variables": [
                {
                    "name": preflight.KEY_ID_VARIABLE,
                    "value": "independent-runner-prod-v1",
                }
            ]
        },
        "branch_policies": {
            "branch_policies": [{"name": "codex/p14-independent-runner"}]
        },
        "artifacts": {
            "artifacts": [
                {
                    "name": f"{preflight.PROTECTED_ARTIFACT_PREFIX}1",
                    "expired": False,
                    "expires_at": (now + dt.timedelta(days=5)).isoformat(),
                }
            ]
        },
        "request": request,
        "result": result,
        "acceptance_request": acceptance_request if acceptance else {},
        "acceptance_result": acceptance_result if acceptance else {},
        "current_branch": "codex/p14-independent-runner",
        "current_head": revision,
        "generated_at": now,
    }


def test_current_secure_external_result_is_operationally_ready():
    payload = preflight.build_preflight(**_inputs())

    assert payload["status"] == "ready"
    assert payload["operational_result"] == "externally_verified_current"
    assert payload["operational_ready"] is True
    assert payload["hard_blockers"] == []
    assert payload["remediation"] == {
        "schema_version": preflight.REMEDIATION_SCHEMA_VERSION,
        "status": "complete",
        "next_action": "none",
        "interaction": "none",
        "risk_class": "read_only",
        "action_count": 0,
        "ready_action_count": 0,
        "blocked_action_count": 0,
        "unknown_blocker_count": 0,
        "actions": [],
        "authority": {
            "auto_execute": False,
            "live_mutation": False,
            "authority_grant": False,
        },
        "policy": "Capability-derived external remediation. Unknown blockers fail to review; no action auto-executes or grants authority.",
    }
    assert payload["runner"] == {
        "provider": "github_hosted",
        "label": "windows-latest",
        "ephemeral": True,
        "matching_count": 1,
        "online": True,
        "required_labels_complete": True,
    }
    assert payload["environment"]["required_reviewer_configured"] is True
    assert payload["environment"]["admin_bypass_disabled"] is True
    assert payload["result"]["structural_valid"] is True
    assert payload["acceptance"]["complete"] is True
    assert payload["acceptance"]["proven_capability_count"] == 4
    assert payload["authority"] == AUTHORITY
    assert preflight._authority_safe(payload["authority"]) is True


def test_realistic_environment_gap_and_old_revision_fail_closed():
    payload = preflight.build_preflight(
        **_inputs(secure_environment=False, revision="b" * 40)
    )

    assert payload["status"] == "needs_attention"
    assert payload["operational_result"] == "externally_verified_stale"
    assert payload["operational_ready"] is False
    assert payload["hard_blockers"] == [
        "p14_environment_required_reviewer_missing",
        "p14_environment_admin_bypass_enabled",
        "p14_self_hosted_result_revision_mismatch",
        "p14_visual_regression_not_proven",
        "p14_in_world_regression_not_proven",
        "p14_canary_rehearsal_not_proven",
        "p14_rollback_rehearsal_not_proven",
    ]
    assert payload["result"]["structural_valid"] is True
    assert payload["result"]["source_revision_match"] is False
    remediation = payload["remediation"]
    assert remediation["status"] == "action_required"
    assert remediation["next_action"] == "harden_p14_environment"
    assert remediation["interaction"] == "external_config"
    assert remediation["risk_class"] == "guarded_write"
    assert remediation["ready_action_count"] == 1
    assert remediation["blocked_action_count"] == 5
    assert remediation["actions"][0]["reason_codes"] == [
        "p14_environment_admin_bypass_enabled",
        "p14_environment_required_reviewer_missing",
    ]
    assert remediation["actions"][1]["action_id"] == (
        "refresh_p14_independent_runner_evidence"
    )
    assert remediation["actions"][1]["status"] == "blocked"
    assert remediation["actions"][1]["blocked_by"] == ["environment_protection"]


def test_github_hosted_capacity_ignores_stale_self_hosted_runner_state():
    values = _inputs(
        secure_environment=False,
        revision="b" * 40,
        acceptance=False,
    )
    values["runners"] = {
        "runners": [{"status": "offline", "labels": [{"name": "ctoa-p14"}]}]
    }

    payload = preflight.build_preflight(**values)

    remediation = payload["remediation"]
    assert payload["runner"]["provider"] == "github_hosted"
    assert payload["runner"]["online"] is True
    assert "p14_required_runner_offline" not in payload["hard_blockers"]
    assert remediation["next_action"] == "harden_p14_environment"
    assert remediation["action_count"] == 6
    assert remediation["ready_action_count"] == 1
    assert remediation["blocked_action_count"] == 5
    assert [item["action_id"] for item in remediation["actions"]] == [
        "harden_p14_environment",
        "refresh_p14_independent_runner_evidence",
        "collect_p14_visual_evidence",
        "collect_p14_in_world_evidence",
        "run_p14_canary_rehearsal",
        "run_p14_rollback_rehearsal",
    ]
    assert remediation["actions"][-1]["blocked_by"] == ["canary_attestation"]


def test_tampered_result_is_never_promoted_to_external_attestation():
    values = _inputs()
    values["result"]["authority"]["runtime_actions"] = True

    payload = preflight.build_preflight(**values)

    assert payload["status"] == "needs_attention"
    assert payload["operational_result"] == "external_result_invalid"
    assert payload["operational_ready"] is False
    assert "p14_self_hosted_result_invalid" in payload["hard_blockers"]
    assert payload["result"]["authority_safe"] is False


def test_unavailable_snapshot_does_not_echo_failure_details():
    payload = preflight.unavailable_snapshot()
    serialized = str(payload)

    assert payload["status"] == "unavailable"
    assert payload["hard_blockers"] == ["p14_external_state_unavailable"]
    assert payload["remediation"]["next_action"] == "review_p14_external_state"
    assert payload["remediation"]["unknown_blocker_count"] == 1
    assert payload["authority"] == AUTHORITY
    assert preflight._authority_safe(payload["authority"]) is True
    assert "exception" not in serialized.lower()
    assert "token" not in serialized.lower()


def test_current_revision_gap_is_a_direct_refresh_without_fake_environment_work():
    payload = preflight.build_preflight(**_inputs(revision="b" * 40))

    assert payload["hard_blockers"] == [
        "p14_self_hosted_result_revision_mismatch",
        "p14_visual_regression_not_proven",
        "p14_in_world_regression_not_proven",
        "p14_canary_rehearsal_not_proven",
        "p14_rollback_rehearsal_not_proven",
    ]
    assert payload["remediation"]["next_action"] == (
        "refresh_p14_independent_runner_evidence"
    )
    assert payload["remediation"]["actions"][0]["status"] == "ready"
    assert payload["remediation"]["actions"][0]["blocked_by"] == []


def test_missing_acceptance_is_a_capability_plan_not_an_unknown_error():
    payload = preflight.build_preflight(**_inputs(acceptance=False))

    assert payload["acceptance"]["status"] == "missing"
    assert payload["hard_blockers"] == [
        "p14_visual_regression_not_proven",
        "p14_in_world_regression_not_proven",
        "p14_canary_rehearsal_not_proven",
        "p14_rollback_rehearsal_not_proven",
    ]
    remediation = payload["remediation"]
    assert remediation["next_action"] == "collect_p14_visual_evidence"
    assert remediation["ready_action_count"] == 2
    assert remediation["blocked_action_count"] == 2
    assert [item["status"] for item in remediation["actions"]] == [
        "ready",
        "ready",
        "blocked",
        "blocked",
    ]
    assert remediation["actions"][2]["blocked_by"] == [
        "in_world_attestation",
        "visual_attestation",
    ]
    assert remediation["actions"][3]["blocked_by"] == ["canary_attestation"]


def test_unknown_blocker_fails_to_bounded_review_without_echoing_input():
    payload = preflight.build_remediation_plan(["secret-value-that-must-not-echo"])
    serialized = str(payload)

    assert payload["status"] == "review_required"
    assert payload["next_action"] == "review_p14_external_state"
    assert payload["unknown_blocker_count"] == 1
    assert "secret-value-that-must-not-echo" not in serialized
    assert payload["authority"] == {
        "auto_execute": False,
        "live_mutation": False,
        "authority_grant": False,
    }
