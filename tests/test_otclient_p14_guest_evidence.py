from __future__ import annotations

import base64
import copy
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_p14_guest_evidence.py"
SPEC = importlib.util.spec_from_file_location("otclient_p14_guest_evidence", SCRIPT)
assert SPEC and SPEC.loader
p14 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p14)

GENERATED_AT = "2026-07-23T12:00:00Z"
BINDING = {
    "source_revision": "a" * 40,
    "helper_manifest_sha256": "b" * 64,
    "rollback_baseline_manifest_sha256": "c" * 64,
    "snapshot_id": "p14-snapshot-001",
    "run_id": "p14-run-001",
}


@pytest.fixture()
def signing_material() -> tuple[ec.EllipticCurvePrivateKey, bytes, str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CTOAi P14 test")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    return (
        private_key,
        certificate_pem,
        base64.b64encode(certificate_pem).decode("ascii"),
    )


def _proof(proof_id: str, *, passed: bool = True, salt: str = "1") -> dict[str, object]:
    return {
        "proof_id": proof_id,
        "status": "passed" if passed else "blocked",
        "artifact_count": 1 if passed else 0,
        "evidence_sha256": salt * 64 if passed else p14.ZERO_SHA256,
    }


def _capability(name: str, *, passed: bool = True, salt: str = "1") -> dict[str, object]:
    proofs = [
        _proof(proof_id, passed=passed, salt=salt)
        for proof_id in p14.CAPABILITY_PROOFS[name]
    ]
    transition: dict[str, object] | None = None
    if passed and name == "canary_rehearsal":
        transition = {
            "baseline_manifest_sha256": BINDING["rollback_baseline_manifest_sha256"],
            "changed_manifest_sha256": "d" * 64,
            "restored_manifest_sha256": "d" * 64,
            "changed_file_count": 1,
        }
    elif passed and name == "rollback_rehearsal":
        transition = {
            "baseline_manifest_sha256": BINDING["rollback_baseline_manifest_sha256"],
            "changed_manifest_sha256": "d" * 64,
            "restored_manifest_sha256": BINDING["rollback_baseline_manifest_sha256"],
            "changed_file_count": 1,
        }
    return {
        "capability": name,
        "status": "passed" if passed else "blocked",
        "proofs": proofs,
        "transition": transition,
    }


def _receipt(
    capabilities: list[dict[str, object]] | None = None,
    *,
    binding: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "ctoa.p14-guest-receipt.v1",
        "receipt_id": "p14-guest-0123456789abcdef",
        "generated_at": GENERATED_AT,
        "binding": copy.deepcopy(binding or BINDING),
        "isolation": copy.deepcopy(p14.ISOLATION),
        "capabilities": capabilities
        or [
            _capability("visual_regression", salt="1"),
            _capability("in_world_regression", salt="2"),
            _capability("canary_rehearsal", salt="3"),
            _capability("rollback_rehearsal", salt="4"),
        ],
    }


def _envelope(
    receipt: dict[str, object], private_key: ec.EllipticCurvePrivateKey
) -> dict[str, str]:
    return p14.build_envelope(
        p14.canonical_json_bytes(receipt),
        private_key=private_key,
        key_id="p14-guest-test",
    )


def test_binary_safe_ecdsa_envelope_round_trip(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, certificate_pem, _ = signing_material
    payload = b"\x00P14\xff\x10binary\x00payload"
    envelope = p14.build_envelope(
        payload,
        private_key=private_key,
        key_id="p14-guest-test",
    )
    public_key = p14.load_p256_public_key_from_certificate(certificate_pem)

    assert p14.verify_envelope(
        envelope,
        public_key=public_key,
        expected_key_id="p14-guest-test",
    ) == payload
    assert envelope["payload_sha256"] == p14.raw_sha256(payload)


def test_b64_certificate_verification_projects_exact_p14_v1_report(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, _, certificate_b64 = signing_material
    envelope = _envelope(_receipt(), private_key)

    report = p14.verify_and_project_envelope(
        envelope,
        public_certificate=certificate_b64,
        certificate_b64=True,
        expected_binding=BINDING,
        expected_key_id="p14-guest-test",
    )

    assert report["schema_version"] == "ctoa.p14-acceptance-report.v1"
    assert report["source_revision"] == BINDING["source_revision"]
    assert report["isolation"] == p14.ISOLATION
    assert [item["capability"] for item in report["capabilities"]] == list(
        p14.CAPABILITY_ORDER
    )
    serialized = json.dumps(report, sort_keys=True)
    for value in (
        "receipt_id",
        "snapshot_id",
        "run_id",
        "signature",
        "payload_b64",
    ):
        assert value not in serialized


@pytest.mark.parametrize("field", ["payload_b64", "payload_sha256", "signature"])
def test_tampered_envelope_is_rejected(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str], field: str
) -> None:
    private_key, certificate_pem, _ = signing_material
    envelope = _envelope(_receipt(), private_key)
    if field == "payload_b64":
        envelope[field] = base64.b64encode(b"tampered payload").decode("ascii")
    elif field == "payload_sha256":
        envelope[field] = "f" * 64
    else:
        envelope[field] = base64.b64encode(b"tampered signature").decode("ascii")
    public_key = p14.load_p256_public_key_from_certificate(certificate_pem)

    with pytest.raises(p14.GuestEvidenceError):
        p14.verify_envelope(envelope, public_key=public_key)


def test_binding_mismatch_rejects_replay_to_another_snapshot(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, certificate_pem, _ = signing_material
    receipt = _receipt()
    receipt["binding"]["snapshot_id"] = "p14-snapshot-other"
    envelope = _envelope(receipt, private_key)

    with pytest.raises(p14.GuestEvidenceError, match="receipt_binding_mismatch:snapshot_id"):
        p14.verify_and_project_envelope(
            envelope,
            public_certificate=certificate_pem,
            expected_binding=BINDING,
        )


def test_passed_proof_requires_nonzero_digest_bound_evidence(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, certificate_pem, _ = signing_material
    receipt = _receipt()
    proof = receipt["capabilities"][0]["proofs"][0]
    proof["artifact_count"] = 0
    proof["evidence_sha256"] = p14.ZERO_SHA256
    envelope = _envelope(receipt, private_key)

    with pytest.raises(p14.GuestEvidenceError, match="passed_proof_evidence_invalid"):
        p14.verify_and_project_envelope(
            envelope,
            public_certificate=certificate_pem,
            expected_binding=BINDING,
        )


def test_canary_and_rollback_must_form_one_manifest_chain(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, certificate_pem, _ = signing_material
    receipt = _receipt()
    receipt["capabilities"][3]["transition"]["changed_manifest_sha256"] = "e" * 64
    envelope = _envelope(receipt, private_key)

    with pytest.raises(p14.GuestEvidenceError, match="rollback_transition_chain_invalid"):
        p14.verify_and_project_envelope(
            envelope,
            public_certificate=certificate_pem,
            expected_binding=BINDING,
        )


def test_canary_requires_visual_and_in_world_prerequisites(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, certificate_pem, _ = signing_material
    receipt = _receipt([_capability("canary_rehearsal", salt="3")])
    envelope = _envelope(receipt, private_key)

    with pytest.raises(
        p14.GuestEvidenceError, match="canary_prerequisite_not_passed"
    ):
        p14.verify_and_project_envelope(
            envelope,
            public_certificate=certificate_pem,
            expected_binding=BINDING,
        )


def test_signed_duplicate_key_payload_is_rejected_before_projection(
    signing_material: tuple[ec.EllipticCurvePrivateKey, bytes, str],
) -> None:
    private_key, certificate_pem, _ = signing_material
    payload = (
        b'{"schema_version":"ctoa.p14-guest-receipt.v1",'
        b'"schema_version":"ctoa.p14-guest-receipt.v1"}'
    )
    envelope = p14.build_envelope(
        payload,
        private_key=private_key,
        key_id="p14-guest-test",
    )

    with pytest.raises(p14.GuestEvidenceError, match="duplicate_json_key:schema_version"):
        p14.verify_and_project_envelope(
            envelope,
            public_certificate=certificate_pem,
            expected_binding=BINDING,
        )


def test_non_p256_certificate_is_rejected() -> None:
    private_key = ec.generate_private_key(ec.SECP384R1())
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "wrong curve")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA384())
    )
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)

    with pytest.raises(p14.GuestEvidenceError, match="p256_public_key_required"):
        p14.load_p256_public_key_from_certificate(certificate_pem)


def test_schemas_are_valid_and_module_has_no_runtime_execution_surface() -> None:
    for path in (p14.ENVELOPE_SCHEMA_PATH, p14.RECEIPT_SCHEMA_PATH):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    source = SCRIPT.read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "Start-Process" not in source
    assert "VBoxManage" not in source
    assert "PromoteLive" not in source
