#!/usr/bin/env python3
"""Verify signed isolated P14 guest evidence and project safe v1 acceptance reports.

This module intentionally handles only evidence envelopes.  It does not launch a
client, execute a sandbox action, copy files, or grant promotion authority.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import hmac
import json
import re
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
ENVELOPE_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-guest-evidence-envelope.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-guest-receipt.schema.json"
ACCEPTANCE_REPORT_SCHEMA_PATH = ROOT / "schemas" / "ctoa-p14-acceptance-report.schema.json"

MAX_JSON_BYTES = 64 * 1024
MAX_CERTIFICATE_BYTES = 32 * 1024
MAX_SIGNATURE_BYTES = 1024
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
SIGNATURE_DOMAIN = b"CTOAi-P14-guest-evidence-envelope/v1\x00"
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
BINDING_FIELDS = (
    "source_revision",
    "helper_manifest_sha256",
    "rollback_baseline_manifest_sha256",
    "snapshot_id",
    "run_id",
)
ISOLATION = {
    "isolated_environment": True,
    "operator_workstation_focus_used": False,
    "operator_workstation_input_used": False,
    "network_dispatch_used": False,
    "live_client_accessed": False,
    "promotion_attempted": False,
}


class GuestEvidenceError(ValueError):
    """Raised when a guest evidence envelope or receipt is not trustworthy."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GuestEvidenceError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise GuestEvidenceError(f"non_finite_json_number:{value}")


def canonical_json_bytes(value: Any) -> bytes:
    """Encode a JSON value deterministically before it is signed."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _read_regular_file(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> bytes:
    if not path.exists() or not path.is_file() or _is_reparse(path):
        raise GuestEvidenceError(f"regular_file_required:{path.name}")
    before = path.stat()
    if before.st_size < 1 or before.st_size > max_bytes:
        raise GuestEvidenceError(f"file_size_invalid:{path.name}")
    raw = path.read_bytes()
    after = path.stat()
    stable = (
        before.st_size == after.st_size == len(raw)
        and before.st_mtime_ns == after.st_mtime_ns
        and getattr(before, "st_ino", 0) == getattr(after, "st_ino", 0)
    )
    if not stable:
        raise GuestEvidenceError(f"file_changed_during_read:{path.name}")
    return raw


def load_strict_json_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_JSON_BYTES:
        raise GuestEvidenceError(f"json_bytes_invalid:{label}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuestEvidenceError(f"invalid_json:{label}") from exc
    if not isinstance(value, dict):
        raise GuestEvidenceError(f"json_object_required:{label}")
    return value


def load_strict_json_file(path: Path) -> dict[str, Any]:
    return load_strict_json_bytes(_read_regular_file(path), label=path.name)


def _validate_schema(payload: dict[str, Any], schema_path: Path) -> None:
    schema = load_strict_json_file(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "root"
        raise GuestEvidenceError(f"schema_invalid:{schema_path.name}:{location}")


def _decode_base64(value: Any, *, label: str, max_bytes: int) -> bytes:
    if not isinstance(value, str) or not value or len(value) % 4:
        raise GuestEvidenceError(f"base64_invalid:{label}")
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise GuestEvidenceError(f"base64_invalid:{label}") from exc
    if not raw or len(raw) > max_bytes:
        raise GuestEvidenceError(f"base64_size_invalid:{label}")
    if base64.b64encode(raw).decode("ascii") != value:
        raise GuestEvidenceError(f"base64_noncanonical:{label}")
    return raw


def _require_safe_key_id(key_id: str) -> None:
    if not SAFE_ID_RE.fullmatch(key_id):
        raise GuestEvidenceError("key_id_invalid")


def _require_p256_private_key(key: Any) -> ec.EllipticCurvePrivateKey:
    if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
        raise GuestEvidenceError("p256_private_key_required")
    return key


def _require_p256_public_key(key: Any) -> ec.EllipticCurvePublicKey:
    if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
        raise GuestEvidenceError("p256_public_key_required")
    return key


def _signature_input(key_id: str, payload: bytes) -> bytes:
    _require_safe_key_id(key_id)
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_JSON_BYTES:
        raise GuestEvidenceError("payload_size_invalid")
    key_id_bytes = key_id.encode("ascii")
    return (
        SIGNATURE_DOMAIN
        + len(key_id_bytes).to_bytes(2, "big")
        + key_id_bytes
        + len(payload).to_bytes(8, "big")
        + payload
    )


def load_p256_public_key_from_certificate(
    certificate_pem: bytes | str,
) -> ec.EllipticCurvePublicKey:
    """Load a P-256 verification key from PEM certificate bytes or text."""

    if isinstance(certificate_pem, str):
        certificate_pem = certificate_pem.encode("utf-8")
    if (
        not isinstance(certificate_pem, bytes)
        or not certificate_pem
        or len(certificate_pem) > MAX_CERTIFICATE_BYTES
    ):
        raise GuestEvidenceError("public_certificate_invalid")
    try:
        certificate = x509.load_pem_x509_certificate(certificate_pem)
    except ValueError as exc:
        raise GuestEvidenceError("public_certificate_invalid") from exc
    return _require_p256_public_key(certificate.public_key())


def load_p256_public_key_from_certificate_b64(
    certificate_b64: str,
) -> ec.EllipticCurvePublicKey:
    """Load a P-256 verification key from a base64-encoded PEM certificate."""

    certificate_pem = _decode_base64(
        certificate_b64,
        label="public_certificate",
        max_bytes=MAX_CERTIFICATE_BYTES,
    )
    return load_p256_public_key_from_certificate(certificate_pem)


def load_p256_private_key_from_pem(private_key_pem: bytes) -> ec.EllipticCurvePrivateKey:
    """Load an unencrypted P-256 signing key without exposing it in diagnostics."""

    if (
        not isinstance(private_key_pem, bytes)
        or not private_key_pem
        or len(private_key_pem) > MAX_CERTIFICATE_BYTES
    ):
        raise GuestEvidenceError("private_key_invalid")
    try:
        key = serialization.load_pem_private_key(private_key_pem, password=None)
    except (TypeError, ValueError) as exc:
        raise GuestEvidenceError("private_key_invalid") from exc
    return _require_p256_private_key(key)


def build_envelope(
    payload: bytes,
    *,
    private_key: ec.EllipticCurvePrivateKey,
    key_id: str,
) -> dict[str, str]:
    """Sign arbitrary bounded binary payload bytes in an ECDSA P-256 envelope."""

    key = _require_p256_private_key(private_key)
    signing_input = _signature_input(key_id, payload)
    signature = key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    if len(signature) > MAX_SIGNATURE_BYTES:
        raise GuestEvidenceError("signature_size_invalid")
    envelope = {
        "schema_version": "ctoa.p14-guest-evidence-envelope.v1",
        "algorithm": "ecdsa-p256-sha256",
        "key_id": key_id,
        "payload_b64": base64.b64encode(payload).decode("ascii"),
        "payload_sha256": raw_sha256(payload),
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    _validate_schema(envelope, ENVELOPE_SCHEMA_PATH)
    return envelope


def validate_envelope_shape(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize only the strict public envelope shape."""

    if not isinstance(envelope, Mapping):
        raise GuestEvidenceError("envelope_object_required")
    payload = dict(envelope)
    _validate_schema(payload, ENVELOPE_SCHEMA_PATH)
    return payload


def verify_envelope(
    envelope: Mapping[str, Any],
    *,
    public_key: ec.EllipticCurvePublicKey,
    expected_key_id: str | None = None,
) -> bytes:
    """Verify a bounded envelope and return its exact binary payload bytes."""

    payload = validate_envelope_shape(envelope)
    key_id = payload["key_id"]
    if expected_key_id is not None:
        _require_safe_key_id(expected_key_id)
        if not hmac.compare_digest(key_id, expected_key_id):
            raise GuestEvidenceError("envelope_key_id_mismatch")
    raw_payload = _decode_base64(
        payload["payload_b64"],
        label="payload",
        max_bytes=MAX_JSON_BYTES,
    )
    if not hmac.compare_digest(raw_sha256(raw_payload), payload["payload_sha256"]):
        raise GuestEvidenceError("payload_sha256_mismatch")
    signature = _decode_base64(
        payload["signature"],
        label="signature",
        max_bytes=MAX_SIGNATURE_BYTES,
    )
    key = _require_p256_public_key(public_key)
    try:
        key.verify(
            signature,
            _signature_input(key_id, raw_payload),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature as exc:
        raise GuestEvidenceError("envelope_signature_invalid") from exc
    return raw_payload


def _require_binding(
    binding: Any,
    expected_binding: Mapping[str, str] | None,
) -> dict[str, str]:
    if not isinstance(binding, dict) or set(binding) != set(BINDING_FIELDS):
        raise GuestEvidenceError("receipt_binding_invalid")
    normalized = {field: binding[field] for field in BINDING_FIELDS}
    if expected_binding is None:
        return normalized
    if not set(expected_binding).issubset(BINDING_FIELDS):
        raise GuestEvidenceError("receipt_expected_binding_invalid")
    for field, expected in expected_binding.items():
        if not isinstance(expected, str) or not hmac.compare_digest(normalized[field], expected):
            raise GuestEvidenceError(f"receipt_binding_mismatch:{field}")
    return normalized


def _normalize_proof(proof: Any, *, proof_id: str) -> dict[str, Any]:
    if not isinstance(proof, dict) or set(proof) != {
        "proof_id",
        "status",
        "artifact_count",
        "evidence_sha256",
    }:
        raise GuestEvidenceError(f"proof_invalid:{proof_id}")
    if proof.get("proof_id") != proof_id:
        raise GuestEvidenceError(f"proof_order_invalid:{proof_id}")
    status = proof.get("status")
    artifact_count = proof.get("artifact_count")
    evidence_sha256 = proof.get("evidence_sha256")
    if type(artifact_count) is not int or not isinstance(evidence_sha256, str):
        raise GuestEvidenceError(f"proof_value_invalid:{proof_id}")
    if status == "passed":
        if not 1 <= artifact_count <= 16 or evidence_sha256 == ZERO_SHA256:
            raise GuestEvidenceError(f"passed_proof_evidence_invalid:{proof_id}")
    elif status == "blocked":
        if artifact_count != 0 or evidence_sha256 != ZERO_SHA256:
            raise GuestEvidenceError(f"blocked_proof_evidence_invalid:{proof_id}")
    else:
        raise GuestEvidenceError(f"proof_status_invalid:{proof_id}")
    return {
        "proof_id": proof_id,
        "status": status,
        "artifact_count": artifact_count,
        "evidence_sha256": evidence_sha256,
    }


def _normalize_transition(
    capability: str,
    transition: Any,
    *,
    baseline_manifest_sha256: str,
) -> dict[str, Any] | None:
    if capability in {"visual_regression", "in_world_regression"}:
        if transition is not None:
            raise GuestEvidenceError(f"unexpected_transition:{capability}")
        return None
    if not isinstance(transition, dict) or set(transition) != {
        "baseline_manifest_sha256",
        "changed_manifest_sha256",
        "restored_manifest_sha256",
        "changed_file_count",
    }:
        raise GuestEvidenceError(f"transition_invalid:{capability}")
    baseline = transition["baseline_manifest_sha256"]
    changed = transition["changed_manifest_sha256"]
    restored = transition["restored_manifest_sha256"]
    changed_file_count = transition["changed_file_count"]
    if (
        not all(isinstance(value, str) and SHA256_RE.fullmatch(value) for value in (
            baseline,
            changed,
            restored,
        ))
        or type(changed_file_count) is not int
        or changed_file_count != 1
        or baseline != baseline_manifest_sha256
        or changed == baseline
    ):
        raise GuestEvidenceError(f"transition_binding_invalid:{capability}")
    if capability == "canary_rehearsal" and restored != changed:
        raise GuestEvidenceError("canary_transition_restore_invalid")
    if capability == "rollback_rehearsal" and restored != baseline:
        raise GuestEvidenceError("rollback_transition_restore_invalid")
    return {
        "baseline_manifest_sha256": baseline,
        "changed_manifest_sha256": changed,
        "restored_manifest_sha256": restored,
        "changed_file_count": changed_file_count,
    }


def _normalize_capability(
    capability: Any,
    *,
    expected_capability: str,
    baseline_manifest_sha256: str,
) -> dict[str, Any]:
    if not isinstance(capability, dict) or set(capability) != {
        "capability",
        "status",
        "proofs",
        "transition",
    }:
        raise GuestEvidenceError(f"capability_invalid:{expected_capability}")
    if capability.get("capability") != expected_capability:
        raise GuestEvidenceError(f"capability_order_invalid:{expected_capability}")
    raw_proofs = capability.get("proofs")
    expected_proofs = CAPABILITY_PROOFS[expected_capability]
    if not isinstance(raw_proofs, list) or len(raw_proofs) != len(expected_proofs):
        raise GuestEvidenceError(f"capability_proof_count_invalid:{expected_capability}")
    proofs = [
        _normalize_proof(proof, proof_id=proof_id)
        for proof, proof_id in zip(raw_proofs, expected_proofs, strict=True)
    ]
    status = capability.get("status")
    all_passed = all(proof["status"] == "passed" for proof in proofs)
    if (status == "passed") != all_passed:
        raise GuestEvidenceError(f"capability_status_invalid:{expected_capability}")
    transition = _normalize_transition(
        expected_capability,
        capability.get("transition"),
        baseline_manifest_sha256=baseline_manifest_sha256,
    )
    return {
        "capability": expected_capability,
        "status": status,
        "proofs": proofs,
        "transition": transition,
    }


def _validate_capability_dependencies(capabilities: Mapping[str, dict[str, Any]]) -> None:
    canary = capabilities.get("canary_rehearsal")
    rollback = capabilities.get("rollback_rehearsal")
    if canary and canary["status"] == "passed":
        for prerequisite in ("visual_regression", "in_world_regression"):
            if capabilities.get(prerequisite, {}).get("status") != "passed":
                raise GuestEvidenceError(f"canary_prerequisite_not_passed:{prerequisite}")
    if rollback and rollback["status"] == "passed":
        if not canary or canary["status"] != "passed":
            raise GuestEvidenceError("rollback_canary_prerequisite_not_passed")
        canary_transition = canary["transition"]
        rollback_transition = rollback["transition"]
        if (
            canary_transition is None
            or rollback_transition is None
            or canary_transition["baseline_manifest_sha256"]
            != rollback_transition["baseline_manifest_sha256"]
            or canary_transition["changed_manifest_sha256"]
            != rollback_transition["changed_manifest_sha256"]
        ):
            raise GuestEvidenceError("rollback_transition_chain_invalid")


def validate_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_binding: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Validate a signed-payload receipt before accepting any proof projection."""

    if not isinstance(receipt, Mapping):
        raise GuestEvidenceError("receipt_object_required")
    payload = dict(receipt)
    _validate_schema(payload, RECEIPT_SCHEMA_PATH)
    binding = _require_binding(payload["binding"], expected_binding)
    if payload.get("isolation") != ISOLATION:
        raise GuestEvidenceError("receipt_isolation_invalid")
    raw_capabilities = payload.get("capabilities")
    if not isinstance(raw_capabilities, list):
        raise GuestEvidenceError("receipt_capabilities_invalid")
    names = [item.get("capability") if isinstance(item, dict) else None for item in raw_capabilities]
    if len(names) != len(set(names)):
        raise GuestEvidenceError("receipt_capability_duplicate")
    expected_names = [name for name in CAPABILITY_ORDER if name in names]
    if names != expected_names:
        raise GuestEvidenceError("receipt_capability_order_invalid")
    normalized = [
        _normalize_capability(
            capability,
            expected_capability=capability_name,
            baseline_manifest_sha256=binding["rollback_baseline_manifest_sha256"],
        )
        for capability, capability_name in zip(raw_capabilities, names, strict=True)
    ]
    by_name = {item["capability"]: item for item in normalized}
    _validate_capability_dependencies(by_name)
    return {
        "schema_version": "ctoa.p14-guest-receipt.v1",
        "receipt_id": payload["receipt_id"],
        "generated_at": payload["generated_at"],
        "binding": binding,
        "isolation": copy.deepcopy(ISOLATION),
        "capabilities": normalized,
    }


def project_receipt_to_p14_report(
    receipt: Mapping[str, Any],
    *,
    expected_binding: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return the exact safe surface accepted by P14 acceptance-report v1."""

    validated = validate_receipt(receipt, expected_binding=expected_binding)
    report = {
        "schema_version": "ctoa.p14-acceptance-report.v1",
        "generated_at": validated["generated_at"],
        "source_revision": validated["binding"]["source_revision"],
        "isolation": copy.deepcopy(ISOLATION),
        "capabilities": copy.deepcopy(validated["capabilities"]),
    }
    _validate_schema(report, ACCEPTANCE_REPORT_SCHEMA_PATH)
    return report


def verify_and_project_envelope(
    envelope: Mapping[str, Any],
    *,
    public_certificate: bytes | str,
    expected_binding: Mapping[str, str],
    expected_key_id: str | None = None,
    certificate_b64: bool = False,
) -> dict[str, Any]:
    """Verify a P-256 guest envelope and project only safe P14 report fields."""

    if certificate_b64:
        if not isinstance(public_certificate, str):
            raise GuestEvidenceError("public_certificate_invalid")
        public_key = load_p256_public_key_from_certificate_b64(public_certificate)
    else:
        public_key = load_p256_public_key_from_certificate(public_certificate)
    raw_receipt = verify_envelope(
        envelope,
        public_key=public_key,
        expected_key_id=expected_key_id,
    )
    receipt = load_strict_json_bytes(raw_receipt, label="guest_receipt")
    return project_receipt_to_p14_report(
        receipt,
        expected_binding=expected_binding,
    )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json_bytes(payload) + b"\n"
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _binding_from_args(args: argparse.Namespace) -> dict[str, str]:
    return {
        "source_revision": args.source_revision,
        "helper_manifest_sha256": args.helper_manifest_sha256,
        "rollback_baseline_manifest_sha256": args.rollback_baseline_manifest_sha256,
        "snapshot_id": args.snapshot_id,
        "run_id": args.run_id,
    }


def _sign(args: argparse.Namespace) -> int:
    receipt = load_strict_json_file(Path(args.receipt))
    validate_receipt(receipt)
    private_key = load_p256_private_key_from_pem(
        _read_regular_file(Path(args.private_key), max_bytes=MAX_CERTIFICATE_BYTES)
    )
    envelope = build_envelope(
        canonical_json_bytes(receipt),
        private_key=private_key,
        key_id=args.key_id,
    )
    output = Path(args.output)
    _write_json_atomic(output, envelope)
    print(
        json.dumps(
            {
                "schema_version": 1,
                "status": "signed",
                "key_id": envelope["key_id"],
                "payload_sha256": envelope["payload_sha256"],
                "output": output.name,
            },
            sort_keys=True,
        )
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    envelope = load_strict_json_file(Path(args.envelope))
    if args.public_cert_b64 is not None:
        certificate: bytes | str = args.public_cert_b64
        certificate_b64 = True
    else:
        certificate = _read_regular_file(
            Path(args.public_cert), max_bytes=MAX_CERTIFICATE_BYTES
        )
        certificate_b64 = False
    report = verify_and_project_envelope(
        envelope,
        public_certificate=certificate,
        certificate_b64=certificate_b64,
        expected_binding=_binding_from_args(args),
        expected_key_id=args.expected_key_id,
    )
    output = Path(args.output)
    _write_json_atomic(output, report)
    print(
        json.dumps(
            {
                "schema_version": 1,
                "status": "verified",
                "source_revision": report["source_revision"],
                "capability_count": len(report["capabilities"]),
                "output": output.name,
            },
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sign = subparsers.add_parser("sign", help="Sign a strict guest receipt into an envelope.")
    sign.add_argument("--receipt", required=True)
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--key-id", required=True)
    sign.add_argument("--output", required=True)
    sign.set_defaults(handler=_sign)

    verify = subparsers.add_parser(
        "verify", help="Verify a guest envelope and emit a strict P14 v1 report."
    )
    verify.add_argument("--envelope", required=True)
    certificate = verify.add_mutually_exclusive_group(required=True)
    certificate.add_argument("--public-cert")
    certificate.add_argument("--public-cert-b64")
    verify.add_argument("--expected-key-id")
    verify.add_argument("--source-revision", required=True)
    verify.add_argument("--helper-manifest-sha256", required=True)
    verify.add_argument("--rollback-baseline-manifest-sha256", required=True)
    verify.add_argument("--snapshot-id", required=True)
    verify.add_argument("--run-id", required=True)
    verify.add_argument("--output", required=True)
    verify.set_defaults(handler=_verify)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        return int(args.handler(args))
    except (GuestEvidenceError, OSError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "blocked",
                    "blockers": [str(exc)],
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
