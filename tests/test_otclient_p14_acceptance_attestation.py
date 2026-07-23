from __future__ import annotations

import base64
import copy
import importlib.util
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_p14_acceptance_attestation.py"
WORKFLOW = ROOT / ".github" / "workflows" / "p14-independent-runner-contract.yml"
SPEC = importlib.util.spec_from_file_location("otclient_p14_acceptance_attestation", SCRIPT)
assert SPEC and SPEC.loader
p14 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p14)

REVISION = "a" * 40
KEY = b"p14-acceptance-test-key-material-32-bytes-minimum"
KEY_ID = "p14-acceptance-test"
GENERATED_AT = "2026-07-16T16:00:00Z"
GUEST_RUN_ID = "0123456789abcdef"


def _roadmap_state() -> dict[str, object]:
    basis: dict[str, object] = {
        "schema_version": "ctoa.roadmap-state.v2",
        "generated_at": "2026-07-16T15:00:00Z",
        "status": "ready",
        "readiness_status": "awaiting_external",
        "phase": "P13",
        "phase_status": "runtime_evidence_ready",
        "next_phase": "P14",
        "freshness_status": "current",
        "tamper_status": "passed",
        "blockers": [],
        "warnings": ["runtime_module_gates_pending"],
        "authority": {
            "control_center_mode": "read_only",
            "runtime_executor_added": False,
            "runtime_actions": False,
            "live_authority": False,
            "p12_heal_friend_reopened": False,
            "runtime_mcp_write_tool_enabled": False,
            "roadmap_refresh_tool_enabled": True,
            "roadmap_refresh_risk_class": "safe_write",
            "allowed_output_paths": [
                "AI/generated/ROADMAP_STATE.json",
                "AI/generated/ROADMAP_STATE.md",
                "runtime/control-center/action-audit.jsonl",
            ],
        },
        "summary": {"runtime_authority_count": 0, "live_authority_count": 0},
    }
    return {**basis, "state_sha256": p14.foundation.canonical_sha256(basis)}


def _base_runner_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[dict[str, object], dict[str, object]]:
    helper_source = tmp_path / "scripts" / "lua" / "otclient"
    chooser_source = tmp_path / "scripts" / "lua" / "ctoa_chooser"
    helper_source.mkdir(parents=True)
    chooser_source.mkdir(parents=True)
    (helper_source / "helper.lua").write_text(
        "return { safe_boot = true }\n", encoding="utf-8"
    )
    (helper_source / "ctoa_otclient.otmod").write_text(
        "Module\n  name: CTOAi\n  version: v2.4.1\n", encoding="utf-8"
    )
    (chooser_source / "ctoa_chooser_loader.lua").write_text(
        "return true\n", encoding="utf-8"
    )
    (chooser_source / "ctoa_chooser.otmod").write_text(
        "Module\n  name: chooser\n", encoding="utf-8"
    )
    roadmap_path = tmp_path / "ROADMAP_STATE.json"
    roadmap_path.write_text(json.dumps(_roadmap_state()), encoding="utf-8")
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "scripts/lua/otclient", "scripts/lua/ctoa_chooser"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    monkeypatch.setattr(p14.foundation, "ROOT", tmp_path)
    monkeypatch.setattr(p14.foundation, "HELPER_SOURCE_PATH", helper_source)
    monkeypatch.setattr(p14.foundation, "CHOOSER_SOURCE_PATH", chooser_source)
    monkeypatch.setattr(p14.foundation, "ROADMAP_STATE_PATH", roadmap_path)
    request = p14.foundation.build_request(
        revision=REVISION,
        generated_at=GENERATED_AT,
        key=KEY,
        key_id=KEY_ID,
    )
    result = p14.foundation.verify_request(
        request,
        key=KEY,
        key_id=KEY_ID,
        runner_id="isolated-p14-runner",
        source_revision=REVISION,
        clean_checkout=True,
        generated_at=GENERATED_AT,
    )
    return request, result


def _proof(proof_id: str, *, passed: bool = True, salt: str = "1") -> dict[str, object]:
    return {
        "proof_id": proof_id,
        "status": "passed" if passed else "blocked",
        "artifact_count": 1 if passed else 0,
        "evidence_sha256": salt * 64 if passed else p14.ZERO_SHA256,
    }


def _report(
    request: dict[str, object], *, blocked: set[str] | None = None
) -> dict[str, object]:
    blocked = blocked or set()
    capabilities = []
    for index, capability_id in enumerate(request["required_capabilities"]):
        passed = capability_id not in blocked
        proofs = [
            _proof(proof_id, passed=passed, salt=str((index % 8) + 1))
            for proof_id in p14.CAPABILITY_PROOFS[capability_id]
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
                "status": "passed" if passed else "blocked",
                "proofs": proofs,
                "transition": transition,
            }
        )
    return {
        "schema_version": "ctoa.p14-acceptance-report.v1",
        "generated_at": GENERATED_AT,
        "source_revision": REVISION,
        "isolation": copy.deepcopy(p14.ISOLATION),
        "capabilities": capabilities,
    }


def _acceptance_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capabilities: list[str] | None = None,
) -> dict[str, object]:
    runner_request, runner_result = _base_runner_bundle(monkeypatch, tmp_path)
    return p14.build_acceptance_request(
        runner_request,
        runner_result,
        generated_at=GENERATED_AT,
        key=KEY,
        key_id=KEY_ID,
        required_capabilities=capabilities,
    )


def _guest_evidence_envelope(
    runner_request: dict[str, object], request: dict[str, object]
) -> tuple[dict[str, str], str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CTOAi P14 guest")])
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
    baseline = p14.foundation.canonical_sha256(
        p14.foundation._artifact_map(runner_request)["rollback_baseline"]["payload"]
    )
    report = _report(request)
    for capability in report["capabilities"]:
        if capability["transition"] is not None:
            capability["transition"]["baseline_manifest_sha256"] = baseline
            capability["transition"]["changed_manifest_sha256"] = "d" * 64
            capability["transition"]["restored_manifest_sha256"] = (
                "d" * 64
                if capability["capability"] == "canary_rehearsal"
                else baseline
            )
            capability["transition"]["changed_file_count"] = 1
    receipt = {
        "schema_version": "ctoa.p14-guest-receipt.v1",
        "receipt_id": "p14-guest-0123456789abcdef",
        "generated_at": GENERATED_AT,
        "binding": {
            "source_revision": request["binding"]["source_revision"],
            "helper_manifest_sha256": request["binding"]["helper_manifest_sha256"],
            "rollback_baseline_manifest_sha256": baseline,
            "snapshot_id": "p14-snapshot-001",
            "run_id": GUEST_RUN_ID,
        },
        "isolation": copy.deepcopy(p14.ISOLATION),
        "capabilities": report["capabilities"],
    }
    envelope = p14.guest_evidence.build_envelope(
        p14.guest_evidence.canonical_json_bytes(receipt),
        private_key=private_key,
        key_id="p14-guest-evidence",
    )
    certificate_b64 = base64.b64encode(
        certificate.public_bytes(serialization.Encoding.PEM)
    ).decode("ascii")
    return envelope, certificate_b64


def test_complete_attestation_is_signed_bound_and_secret_minimized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(monkeypatch, tmp_path)
    result = p14.build_acceptance_result(
        request, _report(request), key=KEY, key_id=KEY_ID
    )

    p14.verify_acceptance_bundle(request, result, key=KEY, key_id=KEY_ID)
    assert request["required_capabilities"] == list(p14.CAPABILITY_ORDER)
    assert result["status"] == "passed"
    assert result["blockers"] == []
    assert result["authority"] == p14.AUTHORITY
    serialized = json.dumps({"request": request, "result": result})
    assert str(tmp_path) not in serialized
    assert "isolated-p14-runner" not in serialized
    assert "http" not in serialized


def test_capability_subset_and_partial_result_are_derived_not_free_form(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(
        monkeypatch,
        tmp_path,
        ["rollback_rehearsal", "visual_regression", "canary_rehearsal"],
    )
    report = _report(request, blocked={"canary_rehearsal"})
    result = p14.build_acceptance_result(request, report, key=KEY, key_id=KEY_ID)

    assert request["required_capabilities"] == [
        "visual_regression",
        "canary_rehearsal",
        "rollback_rehearsal",
    ]
    assert result["status"] == "partial"
    assert result["blockers"] == ["p14_canary_rehearsal_not_proven"]
    p14.verify_acceptance_bundle(request, result, key=KEY, key_id=KEY_ID)


@pytest.mark.parametrize(
    ("capabilities", "blocked", "expected_status", "expected_blockers"),
    [
        (
            ["visual_regression", "canary_rehearsal"],
            {"canary_rehearsal"},
            "partial",
            ["p14_canary_rehearsal_not_proven"],
        ),
        (
            ["visual_regression"],
            {"visual_regression"},
            "blocked",
            ["p14_visual_regression_not_proven"],
        ),
    ],
)
def test_valid_nonpassed_attestation_exits_success_for_verify_and_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capabilities: list[str],
    blocked: set[str],
    expected_status: str,
    expected_blockers: list[str],
) -> None:
    runner_request, runner_result = _base_runner_bundle(monkeypatch, tmp_path)
    request = p14.build_acceptance_request(
        runner_request,
        runner_result,
        generated_at=GENERATED_AT,
        key=KEY,
        key_id=KEY_ID,
        required_capabilities=capabilities,
    )
    artifact_root = tmp_path / "acceptance-artifacts"
    artifact_root.mkdir()
    (artifact_root / "request.json").write_text(
        json.dumps(runner_request), encoding="utf-8"
    )
    (artifact_root / "acceptance-request.json").write_text(
        json.dumps(request), encoding="utf-8"
    )
    monkeypatch.setattr(
        p14,
        "_project_guest_evidence",
        lambda *args, **kwargs: _report(request, blocked=blocked),
    )
    monkeypatch.setattr(p14.foundation, "_signing_material", lambda: (KEY, KEY_ID))
    args = SimpleNamespace(artifact_root=str(artifact_root))

    assert p14._attest(args) == 0
    result = json.loads((artifact_root / "acceptance-result.json").read_text())
    assert result["status"] == expected_status
    assert result["blockers"] == expected_blockers
    assert p14._verify_result(args) == 0


def test_attest_requires_a_verified_guest_envelope_for_a_passed_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner_request, runner_result = _base_runner_bundle(monkeypatch, tmp_path)
    request = p14.build_acceptance_request(
        runner_request,
        runner_result,
        generated_at=GENERATED_AT,
        key=KEY,
        key_id=KEY_ID,
    )
    artifact_root = tmp_path / "guest-envelope-artifacts"
    artifact_root.mkdir()
    (artifact_root / "request.json").write_text(
        json.dumps(runner_request), encoding="utf-8"
    )
    (artifact_root / "acceptance-request.json").write_text(
        json.dumps(request), encoding="utf-8"
    )
    envelope, certificate_b64 = _guest_evidence_envelope(runner_request, request)
    (artifact_root / p14.GUEST_EVIDENCE_ENVELOPE_FILENAME).write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    monkeypatch.setattr(p14.foundation, "_signing_material", lambda: (KEY, KEY_ID))
    monkeypatch.setenv(p14.GUEST_EVIDENCE_CERT_ENV, certificate_b64)
    monkeypatch.setenv(p14.GUEST_EVIDENCE_KEY_ID_ENV, "p14-guest-evidence")
    monkeypatch.setenv(p14.GUEST_SNAPSHOT_ID_ENV, "p14-snapshot-001")
    monkeypatch.setenv(p14.GUEST_RUN_ID_ENV, GUEST_RUN_ID)
    args = SimpleNamespace(artifact_root=str(artifact_root))

    monkeypatch.setenv(p14.GUEST_RUN_ID_ENV, "fedcba9876543210")
    with pytest.raises(p14.AttestationError, match="guest_evidence_envelope_invalid"):
        p14._attest(args)

    monkeypatch.setenv(p14.GUEST_RUN_ID_ENV, GUEST_RUN_ID)
    assert p14._attest(args) == 0
    result = json.loads((artifact_root / "acceptance-result.json").read_text())
    assert result["status"] == "passed"
    assert (artifact_root / "acceptance-report.json").is_file()

    (artifact_root / p14.GUEST_EVIDENCE_ENVELOPE_FILENAME).unlink()
    with pytest.raises(p14.AttestationError, match="guest_evidence_envelope_missing"):
        p14._attest(args)


def test_verify_guest_evidence_has_no_attestation_write_side_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner_request, runner_result = _base_runner_bundle(monkeypatch, tmp_path)
    request = p14.build_acceptance_request(
        runner_request,
        runner_result,
        generated_at=GENERATED_AT,
        key=KEY,
        key_id=KEY_ID,
    )
    artifact_root = tmp_path / "guest-evidence-inspection-artifacts"
    artifact_root.mkdir()
    (artifact_root / "request.json").write_text(
        json.dumps(runner_request), encoding="utf-8"
    )
    (artifact_root / "acceptance-request.json").write_text(
        json.dumps(request), encoding="utf-8"
    )
    envelope, certificate_b64 = _guest_evidence_envelope(runner_request, request)
    (artifact_root / p14.GUEST_EVIDENCE_ENVELOPE_FILENAME).write_text(
        json.dumps(envelope), encoding="utf-8"
    )
    monkeypatch.setattr(p14.foundation, "_signing_material", lambda: (KEY, KEY_ID))
    monkeypatch.setenv(p14.GUEST_EVIDENCE_CERT_ENV, certificate_b64)
    monkeypatch.setenv(p14.GUEST_EVIDENCE_KEY_ID_ENV, "p14-guest-evidence")
    monkeypatch.setenv(p14.GUEST_SNAPSHOT_ID_ENV, "p14-snapshot-001")
    monkeypatch.setenv(p14.GUEST_RUN_ID_ENV, GUEST_RUN_ID)

    assert (
        p14._verify_guest_evidence(SimpleNamespace(artifact_root=str(artifact_root)))
        == 0
    )
    assert not (artifact_root / "acceptance-report.json").exists()
    assert not (artifact_root / "acceptance-result.json").exists()


def test_invalid_attestation_keeps_nonzero_exit_and_writes_no_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(monkeypatch, tmp_path, ["visual_regression"])
    artifact_root = tmp_path / "invalid-acceptance-artifacts"
    artifact_root.mkdir()
    (artifact_root / "acceptance-request.json").write_text(
        json.dumps(request), encoding="utf-8"
    )
    (artifact_root / "acceptance-report.json").write_text(
        json.dumps({"schema_version": "ctoa.p14-acceptance-report.v1"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(p14.foundation, "_signing_material", lambda: (KEY, KEY_ID))
    monkeypatch.setattr(
        p14,
        "parse_args",
        lambda: SimpleNamespace(
            handler=p14._attest, artifact_root=str(artifact_root)
        ),
    )

    assert p14.main() == 2
    assert not (artifact_root / "acceptance-result.json").exists()


def test_passed_proof_requires_nonempty_digest_bound_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(monkeypatch, tmp_path, ["visual_regression"])
    report = _report(request)
    report["capabilities"][0]["proofs"][0]["artifact_count"] = 0
    report["capabilities"][0]["proofs"][0]["evidence_sha256"] = p14.ZERO_SHA256

    with pytest.raises(p14.AttestationError, match="passed_proof_evidence_invalid"):
        p14.build_acceptance_result(request, report, key=KEY, key_id=KEY_ID)


def test_rollback_must_restore_exact_baseline_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(monkeypatch, tmp_path, ["rollback_rehearsal"])
    report = _report(request)
    report["capabilities"][0]["transition"]["restored_manifest_sha256"] = "c" * 64

    with pytest.raises(p14.AttestationError, match="capability_transition_invalid"):
        p14.build_acceptance_result(request, report, key=KEY, key_id=KEY_ID)


def test_result_tamper_or_rebinding_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(monkeypatch, tmp_path)
    result = p14.build_acceptance_result(
        request, _report(request), key=KEY, key_id=KEY_ID
    )
    result["request_id"] = "p14-accept-ffffffffffffffff"

    with pytest.raises(p14.AttestationError, match="acceptance_signature_invalid"):
        p14.verify_acceptance_bundle(request, result, key=KEY, key_id=KEY_ID)


def test_duplicate_capabilities_and_proof_substitution_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _acceptance_request(monkeypatch, tmp_path, ["visual_regression"])
    report = _report(request)
    report["capabilities"].append(copy.deepcopy(report["capabilities"][0]))
    with pytest.raises(p14.AttestationError, match="acceptance_capability_duplicate"):
        p14.build_acceptance_result(request, report, key=KEY, key_id=KEY_ID)

    report = _report(request)
    report["capabilities"][0]["proofs"][0]["proof_id"] = "canary_health_check"
    with pytest.raises(p14.AttestationError, match="capability_proof_set_invalid"):
        p14.build_acceptance_result(request, report, key=KEY, key_id=KEY_ID)


def test_acceptance_schemas_are_valid_draft_2020_12() -> None:
    for path in (
        p14.REQUEST_SCHEMA_PATH,
        p14.REPORT_SCHEMA_PATH,
        p14.RESULT_SCHEMA_PATH,
    ):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_cli_has_no_client_command_promotion_or_control_central_raw_artifact_surface() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "subprocess.Popen" not in source
    assert "Start-Process" not in source
    assert "solteria-client.exe" not in source
    assert '"promotion_approved": True' not in source
    assert '"raw_artifacts_in_control_central": False' in source


def test_workflow_tracks_acceptance_contract_and_prepares_only_a_request() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "schemas/ctoa-p14-*.schema.json" in source
    assert "tests/test_otclient_p14_acceptance_attestation.py" in source
    assert "tests/test_otclient_p14_guest_evidence.py" in source
    assert "otclient_p14_acceptance_attestation.py prepare" in source
    assert "otclient_p14_acceptance_attestation.py attest" in source
    assert "acceptance_envelope_b64" in source
    assert "guest_run_id" in source
    assert "guest-evidence-envelope.json" in source
    assert "CTOA_P14_GUEST_EVIDENCE_PUBLIC_CERT_B64" in source


def test_workflow_uploads_only_preflight_allowlisted_p14_evidence() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    protected_upload = source.split(
        "      - name: Upload protected contract evidence\n", 1
    )[1]

    assert "path: |" in protected_upload
    assert "runtime/p14_independent_runner/*.json" not in protected_upload
    for filename in (
        "request.json",
        "result.json",
        "acceptance-request.json",
        "acceptance-result.json",
        "acceptance-report.json",
    ):
        assert f"runtime/p14_independent_runner/{filename}" in protected_upload
    # These values may be consumed inside the protected job, but must never
    # become part of the downloadable artifact preflight parses.
    assert "guest-evidence-envelope.json" not in protected_upload
    assert "guest-run-claim.json" not in protected_upload
