#!/usr/bin/env python3
"""Build and verify capability-driven P14 isolated acceptance attestations."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

try:
    from scripts.ops import otclient_p14_independent_runner as foundation
except ModuleNotFoundError:  # Direct script execution from scripts/ops.
    import otclient_p14_independent_runner as foundation


ROOT = Path(__file__).resolve().parents[2]
REQUEST_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-acceptance-request.schema.json"
REPORT_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-acceptance-report.schema.json"
RESULT_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-acceptance-result.schema.json"
DEFAULT_ARTIFACT_ROOT = ROOT / "runtime" / "p14_independent_runner"
ZERO_SHA256 = "0" * 64
CAPABILITY_ORDER = (
    "visual_regression",
    "in_world_regression",
    "canary_rehearsal",
    "rollback_rehearsal",
)
CAPABILITY_PROOFS = {
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
CAPABILITY_BLOCKERS = {
    "visual_regression": "p14_visual_regression_not_proven",
    "in_world_regression": "p14_in_world_regression_not_proven",
    "canary_rehearsal": "p14_canary_rehearsal_not_proven",
    "rollback_rehearsal": "p14_rollback_rehearsal_not_proven",
}
ISOLATION = {
    "isolated_environment": True,
    "operator_workstation_focus_used": False,
    "operator_workstation_input_used": False,
    "network_dispatch_used": False,
    "live_client_accessed": False,
    "promotion_attempted": False,
}
AUTHORITY = copy.deepcopy(foundation.AUTHORITY)


class AttestationError(ValueError):
    """Raised when an acceptance artifact violates the bounded contract."""


def _schema_registry() -> Registry:
    resources: list[tuple[str, Resource[Any]]] = []
    for path in (REQUEST_SCHEMA_PATH, REPORT_SCHEMA_PATH, RESULT_SCHEMA_PATH):
        schema = foundation.load_strict_json(path)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str):
            raise AttestationError("schema_id_missing")
        resources.append((schema_id, Resource.from_contents(schema)))
        resources.append((path.name, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def validate_schema(payload: dict[str, Any], path: Path) -> None:
    schema = foundation.load_strict_json(path)
    try:
        validator = Draft202012Validator(
            schema,
            registry=_schema_registry(),
            format_checker=FormatChecker(),
        )
        errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    except Exception as exc:
        raise AttestationError("schema_resolution_failed") from exc
    if errors:
        location = ".".join(str(item) for item in errors[0].path) or "root"
        raise AttestationError(f"schema_invalid:{path.name}:{location}")


def _required_capabilities(values: list[str] | tuple[str, ...] | None) -> list[str]:
    requested = list(values or CAPABILITY_ORDER)
    if (
        not requested
        or len(requested) > len(CAPABILITY_ORDER)
        or len(requested) != len(set(requested))
        or any(item not in CAPABILITY_PROOFS for item in requested)
    ):
        raise AttestationError("required_capabilities_invalid")
    requested_set = set(requested)
    return [item for item in CAPABILITY_ORDER if item in requested_set]


def build_acceptance_request(
    runner_request: dict[str, Any],
    runner_result: dict[str, Any],
    *,
    generated_at: str,
    key: bytes,
    key_id: str,
    required_capabilities: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    try:
        foundation.verify_result_bundle(
            runner_request,
            runner_result,
            key=key,
            key_id=key_id,
        )
    except foundation.ContractError as exc:
        raise AttestationError("runner_result_binding_invalid") from exc
    if runner_result.get("status") != "passed":
        raise AttestationError("runner_result_not_passed")

    source = runner_request.get("source")
    runner = runner_result.get("runner")
    if not isinstance(source, dict) or not isinstance(runner, dict):
        raise AttestationError("runner_source_binding_missing")
    revision = source.get("revision")
    if revision != runner.get("source_revision") or runner.get("revision_match") is not True:
        raise AttestationError("runner_source_binding_invalid")

    capabilities = _required_capabilities(required_capabilities)
    binding = {
        "source_revision": revision,
        "runner_request_id": runner_request["request_id"],
        "runner_result_id": runner_result["result_id"],
        "runner_request_sha256": foundation.canonical_sha256(runner_request),
        "runner_result_sha256": foundation.canonical_sha256(runner_result),
        "helper_manifest_sha256": source["helper_manifest_sha256"],
    }
    seed = {"binding": binding, "required_capabilities": capabilities}
    request: dict[str, Any] = {
        "schema_version": "ctoa.p14-acceptance-request.v1",
        "generated_at": generated_at,
        "request_id": f"p14-accept-{foundation.canonical_sha256(seed)[:16]}",
        "phase": "P14",
        "status": "ready_for_isolated_acceptance",
        "binding": binding,
        "required_capabilities": capabilities,
        "constraints": {
            "artifact_only_handoff": True,
            "isolated_environment_required": True,
            "operator_workstation_focus_allowed": False,
            "operator_workstation_input_allowed": False,
            "network_dispatch_allowed": False,
            "live_client_access_allowed": False,
            "promotion_allowed": False,
            "sensitive_payload_export_allowed": False,
        },
        "evidence_policy": {
            "digest_algorithm": "sha256",
            "raw_artifacts_in_control_central": False,
            "max_artifacts_per_proof": 16,
            "max_bundle_bytes": 33_554_432,
        },
        "authority": copy.deepcopy(AUTHORITY),
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": key_id,
            "value": ZERO_SHA256,
        },
    }
    foundation._apply_signature(request, key)
    validate_schema(request, REQUEST_SCHEMA_PATH)
    return request


def _proofs_by_id(capability: dict[str, Any]) -> dict[str, dict[str, Any]]:
    proofs = capability.get("proofs")
    if not isinstance(proofs, list):
        raise AttestationError("capability_proofs_invalid")
    by_id: dict[str, dict[str, Any]] = {}
    for proof in proofs:
        if not isinstance(proof, dict) or not isinstance(proof.get("proof_id"), str):
            raise AttestationError("capability_proof_invalid")
        proof_id = proof["proof_id"]
        if proof_id in by_id:
            raise AttestationError("capability_proof_duplicate")
        by_id[proof_id] = proof
    return by_id


def _transition_valid(capability: str, transition: Any) -> bool:
    if capability in {"visual_regression", "in_world_regression"}:
        return transition is None
    if not isinstance(transition, dict):
        return False
    baseline = transition.get("baseline_manifest_sha256")
    changed = transition.get("changed_manifest_sha256")
    restored = transition.get("restored_manifest_sha256")
    changed_count = transition.get("changed_file_count")
    common = bool(
        isinstance(baseline, str)
        and isinstance(changed, str)
        and isinstance(restored, str)
        and baseline != changed
        and type(changed_count) is int
        and 1 <= changed_count <= 256
    )
    if not common:
        return False
    if capability == "canary_rehearsal":
        return restored == changed
    return restored == baseline


def _normalize_capability(capability: dict[str, Any]) -> dict[str, Any]:
    capability_id = capability.get("capability")
    expected_proofs = CAPABILITY_PROOFS.get(str(capability_id))
    if expected_proofs is None:
        raise AttestationError("capability_unknown")
    proofs = _proofs_by_id(capability)
    if set(proofs) != set(expected_proofs):
        raise AttestationError(f"capability_proof_set_invalid:{capability_id}")

    normalized_proofs: list[dict[str, Any]] = []
    for proof_id in expected_proofs:
        proof = proofs[proof_id]
        status = proof.get("status")
        artifact_count = proof.get("artifact_count")
        digest = proof.get("evidence_sha256")
        if status == "passed" and (
            type(artifact_count) is not int
            or not 1 <= artifact_count <= 16
            or digest == ZERO_SHA256
        ):
            raise AttestationError(f"passed_proof_evidence_invalid:{proof_id}")
        normalized_proofs.append(
            {
                "proof_id": proof_id,
                "status": status,
                "artifact_count": artifact_count,
                "evidence_sha256": digest,
            }
        )

    status = capability.get("status")
    all_passed = all(item["status"] == "passed" for item in normalized_proofs)
    if (status == "passed") != all_passed:
        raise AttestationError(f"capability_status_invalid:{capability_id}")
    transition = copy.deepcopy(capability.get("transition"))
    if not _transition_valid(str(capability_id), transition):
        raise AttestationError(f"capability_transition_invalid:{capability_id}")
    return {
        "capability": capability_id,
        "status": status,
        "proofs": normalized_proofs,
        "transition": transition,
    }


def normalize_report(
    request: dict[str, Any], report: dict[str, Any]
) -> list[dict[str, Any]]:
    validate_schema(request, REQUEST_SCHEMA_PATH)
    validate_schema(report, REPORT_SCHEMA_PATH)
    if report.get("source_revision") != request.get("binding", {}).get("source_revision"):
        raise AttestationError("acceptance_source_revision_mismatch")
    if report.get("isolation") != ISOLATION:
        raise AttestationError("acceptance_isolation_invalid")

    raw_capabilities = report.get("capabilities")
    if not isinstance(raw_capabilities, list):
        raise AttestationError("acceptance_capabilities_invalid")
    by_id: dict[str, dict[str, Any]] = {}
    for item in raw_capabilities:
        if not isinstance(item, dict) or not isinstance(item.get("capability"), str):
            raise AttestationError("acceptance_capability_invalid")
        capability_id = item["capability"]
        if capability_id in by_id:
            raise AttestationError("acceptance_capability_duplicate")
        by_id[capability_id] = item
    requested = request.get("required_capabilities")
    if not isinstance(requested, list) or set(by_id) != set(requested):
        raise AttestationError("acceptance_capability_set_invalid")
    return [_normalize_capability(by_id[item]) for item in requested]


def build_acceptance_result(
    request: dict[str, Any],
    report: dict[str, Any],
    *,
    key: bytes,
    key_id: str,
) -> dict[str, Any]:
    try:
        foundation._verify_signature(request, key, key_id)
    except foundation.ContractError as exc:
        raise AttestationError("acceptance_request_signature_invalid") from exc
    capabilities = normalize_report(request, report)
    blockers = [
        CAPABILITY_BLOCKERS[item["capability"]]
        for item in capabilities
        if item["status"] != "passed"
    ]
    passed_count = len(capabilities) - len(blockers)
    status = (
        "passed"
        if not blockers
        else "partial"
        if passed_count
        else "blocked"
    )
    result_seed = {
        "request_id": request["request_id"],
        "request_sha256": foundation.canonical_sha256(request),
        "capabilities": capabilities,
    }
    result: dict[str, Any] = {
        "schema_version": "ctoa.p14-acceptance-result.v1",
        "generated_at": report["generated_at"],
        "result_id": f"p14-accept-result-{foundation.canonical_sha256(result_seed)[:16]}",
        "request_id": request["request_id"],
        "request_sha256": foundation.canonical_sha256(request),
        "status": status,
        "source_revision": report["source_revision"],
        "isolation": copy.deepcopy(ISOLATION),
        "capabilities": capabilities,
        "blockers": blockers,
        "authority": copy.deepcopy(AUTHORITY),
        "signature": {
            "algorithm": "hmac-sha256",
            "key_id": key_id,
            "value": ZERO_SHA256,
        },
    }
    foundation._apply_signature(result, key)
    validate_schema(result, RESULT_SCHEMA_PATH)
    return result


def verify_acceptance_bundle(
    request: dict[str, Any],
    result: dict[str, Any],
    *,
    key: bytes,
    key_id: str,
) -> None:
    validate_schema(request, REQUEST_SCHEMA_PATH)
    validate_schema(result, RESULT_SCHEMA_PATH)
    try:
        foundation._verify_signature(request, key, key_id)
        foundation._verify_signature(result, key, key_id)
    except foundation.ContractError as exc:
        raise AttestationError("acceptance_signature_invalid") from exc
    if (
        result.get("request_id") != request.get("request_id")
        or result.get("request_sha256") != foundation.canonical_sha256(request)
        or result.get("source_revision") != request.get("binding", {}).get("source_revision")
        or result.get("isolation") != ISOLATION
        or result.get("authority") != AUTHORITY
    ):
        raise AttestationError("acceptance_result_binding_invalid")

    synthetic_report = {
        "schema_version": "ctoa.p14-acceptance-report.v1",
        "generated_at": result.get("generated_at"),
        "source_revision": result.get("source_revision"),
        "isolation": result.get("isolation"),
        "capabilities": result.get("capabilities"),
    }
    normalized = normalize_report(request, synthetic_report)
    blockers = [
        CAPABILITY_BLOCKERS[item["capability"]]
        for item in normalized
        if item["status"] != "passed"
    ]
    passed_count = len(normalized) - len(blockers)
    expected_status = "passed" if not blockers else "partial" if passed_count else "blocked"
    if result.get("capabilities") != normalized or result.get("blockers") != blockers:
        raise AttestationError("acceptance_result_projection_invalid")
    if result.get("status") != expected_status:
        raise AttestationError("acceptance_result_status_invalid")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _prepare(args: argparse.Namespace) -> int:
    key, key_id = foundation._signing_material()
    root = foundation._artifact_root(args.artifact_root)
    request = foundation.load_strict_json(root / "request.json")
    result = foundation.load_strict_json(root / "result.json")
    acceptance = build_acceptance_request(
        request,
        result,
        generated_at=_utc_now(),
        key=key,
        key_id=key_id,
        required_capabilities=args.capability,
    )
    if not args.dry_run:
        foundation._write_json_atomic(root / "acceptance-request.json", acceptance)
    _print(
        {
            "schema_version": 1,
            "action": "p14-acceptance-prepare",
            "status": "dry_run" if args.dry_run else "completed",
            "request_id": acceptance["request_id"],
            "required_capabilities": acceptance["required_capabilities"],
            "would_write": ["acceptance-request.json"],
            "authority": AUTHORITY,
        }
    )
    return 0


def _attest(args: argparse.Namespace) -> int:
    key, key_id = foundation._signing_material()
    root = foundation._artifact_root(args.artifact_root)
    request = foundation.load_strict_json(root / "acceptance-request.json")
    report = foundation.load_strict_json(root / "acceptance-report.json")
    result = build_acceptance_result(request, report, key=key, key_id=key_id)
    foundation._write_json_atomic(root / "acceptance-result.json", result)
    _print(
        {
            "schema_version": 1,
            "action": "p14-acceptance-attest",
            "status": result["status"],
            "result_id": result["result_id"],
            "capability_count": len(result["capabilities"]),
            "passed_capability_count": sum(
                1 for item in result["capabilities"] if item["status"] == "passed"
            ),
            "blockers": result["blockers"],
            "authority": AUTHORITY,
        }
    )
    return 0 if result["status"] == "passed" else 2


def _verify_result(args: argparse.Namespace) -> int:
    key, key_id = foundation._signing_material()
    root = foundation._artifact_root(args.artifact_root)
    request = foundation.load_strict_json(root / "acceptance-request.json")
    result = foundation.load_strict_json(root / "acceptance-result.json")
    verify_acceptance_bundle(request, result, key=key, key_id=key_id)
    _print(
        {
            "schema_version": 1,
            "action": "p14-acceptance-verify-result",
            "status": result["status"],
            "result_id": result["result_id"],
            "blockers": result["blockers"],
            "authority": AUTHORITY,
        }
    )
    return 0 if result["status"] == "passed" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare", help="Bind a signed acceptance request to a verified runner result."
    )
    prepare.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    prepare.add_argument(
        "--capability",
        action="append",
        choices=CAPABILITY_ORDER,
        help="Request a capability subset; defaults to the complete P14 acceptance set.",
    )
    prepare.add_argument("--dry-run", action="store_true")
    prepare.set_defaults(handler=_prepare)

    attest = subparsers.add_parser(
        "attest", help="Normalize an isolated report and emit a signed acceptance result."
    )
    attest.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    attest.set_defaults(handler=_attest)

    verify = subparsers.add_parser(
        "verify-result", help="Verify exact request/result and capability-proof bindings."
    )
    verify.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    verify.set_defaults(handler=_verify_result)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        return int(args.handler(args))
    except (AttestationError, foundation.ContractError) as exc:
        _print(
            {
                "schema_version": 1,
                "status": "blocked",
                "blockers": [str(exc)],
                "authority": AUTHORITY,
            }
        )
        return 2
    except (OSError, subprocess.SubprocessError):
        _print(
            {
                "schema_version": 1,
                "status": "blocked",
                "blockers": ["bounded_io_or_git_operation_failed"],
                "authority": AUTHORITY,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
