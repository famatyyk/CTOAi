from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from scripts.ops import otclient_p14_guest_evidence as guest_evidence


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_p14_replay_ledger.py"
WORKFLOW = ROOT / ".github" / "workflows" / "p14-independent-runner-contract.yml"
SPEC = importlib.util.spec_from_file_location("otclient_p14_replay_ledger", SCRIPT)
assert SPEC and SPEC.loader
ledger = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ledger)

REPOSITORY = "Famatyyk/CTOAi"
RUN_ID = "0123456789abcdef"
SNAPSHOT_ID = "p14-snapshot-001"


def _envelope(*, payload: bytes = b'{"p14":"evidence"}') -> dict[str, str]:
    return guest_evidence.build_envelope(
        payload,
        private_key=ec.generate_private_key(ec.SECP256R1()),
        key_id="p14-guest-evidence",
    )


def _claim(
    envelope: dict[str, str],
    *,
    repository: str = REPOSITORY,
    run_id: str = RUN_ID,
) -> dict[str, str]:
    return ledger.build_claim(
        repository=repository,
        run_id=run_id,
        envelope=envelope,
        workflow_run_id="123456789",
        workflow_run_attempt="1",
    )


def test_claim_is_stable_per_repository_and_guest_run_but_opaque() -> None:
    first = _claim(_envelope(payload=b"one"))
    second = _claim(_envelope(payload=b"two"))
    other_repository = _claim(_envelope(payload=b"one"), repository="other/CTOAi")

    assert first["repository"] == "famatyyk/ctoai"
    assert first["issue_title"] == second["issue_title"]
    assert first["run_commitment_sha256"] == second["run_commitment_sha256"]
    assert first["envelope_sha256"] != second["envelope_sha256"]
    assert first["issue_title"] != other_repository["issue_title"]
    assert RUN_ID not in first["issue_title"]
    assert RUN_ID not in first["issue_body"]
    assert SNAPSHOT_ID not in first["issue_body"]


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("repository", "invalid repository", "github_repository_invalid"),
        ("run_id", "not-a-run-id", "guest_run_id_invalid"),
    ],
)
def test_claim_rejects_unbounded_or_invalid_identity_values(
    field: str, value: str, blocker: str
) -> None:
    kwargs = {
        "repository": REPOSITORY,
        "run_id": RUN_ID,
        "envelope": _envelope(),
        "workflow_run_id": "123456789",
        "workflow_run_attempt": "1",
    }
    kwargs[field] = value

    with pytest.raises(ledger.ReplayLedgerError, match=blocker):
        ledger.build_claim(**kwargs)


def test_prepare_writes_a_strict_claim_without_raw_guest_identity(
    tmp_path: Path,
) -> None:
    envelope_path = tmp_path / "guest-evidence-envelope.json"
    envelope_path.write_text(json.dumps(_envelope()), encoding="utf-8")
    output = tmp_path / "guest-run-claim.json"

    assert (
        ledger._prepare(
            SimpleNamespace(
                repository=REPOSITORY,
                run_id=RUN_ID,
                envelope=str(envelope_path),
                workflow_run_id="123456789",
                workflow_run_attempt="1",
                output=str(output),
            )
        )
        == 0
    )
    claim = json.loads(output.read_text(encoding="utf-8"))

    assert claim["schema_version"] == ledger.LEDGER_SCHEMA_VERSION
    assert RUN_ID not in output.read_text(encoding="utf-8")
    assert SNAPSHOT_ID not in output.read_text(encoding="utf-8")
    assert "snapshot" not in output.read_text(encoding="utf-8").lower()
    assert not list(tmp_path.glob(".guest-run-claim.json.*"))


def test_prepare_rejects_an_invalid_envelope_before_writing_claim(
    tmp_path: Path,
) -> None:
    envelope_path = tmp_path / "guest-evidence-envelope.json"
    envelope_path.write_text('{"schema_version":"unexpected"}', encoding="utf-8")
    output = tmp_path / "guest-run-claim.json"
    args = SimpleNamespace(
        repository=REPOSITORY,
        run_id=RUN_ID,
        envelope=str(envelope_path),
        workflow_run_id="123456789",
        workflow_run_attempt="1",
        output=str(output),
    )

    with pytest.raises(guest_evidence.GuestEvidenceError):
        ledger._prepare(args)
    assert not output.exists()


def test_ledger_has_no_client_process_or_network_execution_surface() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "urllib" not in source
    assert "requests" not in source
    assert "VBoxManage" not in source
    assert "PromoteLive" not in source


def test_workflow_verifies_then_reserves_a_serialized_durable_claim() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "scripts/ops/otclient_p14_replay_ledger.py" in source
    assert "tests/test_otclient_p14_replay_ledger.py" in source
    assert "issues: write" in source
    assert "p14-guest-evidence-ledger-${{ github.repository_id }}" in source
    assert "cancel-in-progress: false" in source
    assert "verify-guest-evidence" in source
    assert "Reserve one-time verified guest run" in source
    assert "Invoke-RestMethod" in source
    assert "-Method Post" in source
    assert "-Method Patch" in source
    assert "/issues?state=all&per_page=100&page=$page" in source
    assert "/search/issues" not in source
    assert source.index("verify-guest-evidence") < source.index(
        "Reserve one-time verified guest run"
    ) < source.index("otclient_p14_acceptance_attestation.py attest")
