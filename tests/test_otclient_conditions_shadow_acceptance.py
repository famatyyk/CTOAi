from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.ops import otclient_conditions_shadow_acceptance as acceptance


replay = acceptance.replay
ROOT = Path(__file__).resolve().parents[1]
P9_FIXTURES = ROOT / "tests" / "fixtures" / "otclient_conditions_shadow_replay"
ACCEPTANCE_FIXTURES = (
    ROOT / "tests" / "fixtures" / "otclient_conditions_shadow_acceptance"
)
NOW_MS = 1_783_800_000_000


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(replay.canonical_bytes(payload) + b"\n")


def _ready_workspace(
    tmp_path: Path, evaluated_at: int = NOW_MS
) -> acceptance.EvidencePaths:
    evidence = tmp_path / "evidence"
    profile_path = evidence / "profile.json"
    p8_path = evidence / "p8.json"
    recovery_trace_path = evidence / "recovery-trace.json"
    recovery_proof_path = evidence / "recovery-proof.json"
    scenario_path = evidence / "scenarios.json"
    report_path = evidence / "report.json"

    profile = _read_json(replay.DEFAULT_PROFILE)
    observation = _read_json(P9_FIXTURES / "positive-observation.json")
    observation["observed_at_unix_ms"] = evaluated_at - 1_000
    observation["observation_id"] = "operational-paralyze-observation"
    observation["producer_source"] = "otclient_guarded_adapter"
    recovery_trace = _read_json(P9_FIXTURES / "positive-recovery-trace.json")
    recovery_trace["observed_at_unix_ms"] = evaluated_at - 2_000
    recovery_trace["source"] = "recovery_shadow"
    recovery_trace["trace_id"] = ""
    recovery_trace["trace_id"] = "recovery-shadow-" + replay.canonical_sha256(
        {key: value for key, value in recovery_trace.items() if key != "trace_id"}
    )[:16]
    observed_at = datetime.fromtimestamp(
        (evaluated_at - 2_000) / 1000, tz=timezone.utc
    ).isoformat()
    observation_envelope = {
        **observation,
        "status": "valid",
        "present": True,
        "valid": True,
        "validation_errors": [],
        "p9_blocker": None,
    }
    p8 = {
        "schema_version": replay.P8_BACKGROUND_SCHEMA,
        "status": "ready",
        "mode": "background_no_screen",
        "generated_at_utc": observed_at,
        "advisory_only": True,
        "safe_to_run_while_playing": True,
        "promotion_allowed": False,
        "dispatch_allowed": False,
        "runtime_actions": False,
        "process_state": "running",
        "interaction_contract": {
            "gui_automation": False,
            "mouse_keyboard_input": False,
            "window_focus": False,
            "screenshot_capture": False,
            "client_launch": False,
            "client_stop": False,
            "live_file_writes": False,
            "passive_reads_only": True,
            "evidence_write_scope": "runtime/solteria_helper_dev",
        },
        "checks": {
            "trusted_live_manifest_pin": True,
            "live_manifest_parity": True,
            "live_files_unchanged": True,
            "exact_active_client_process": True,
            "fresh_online_heartbeat": True,
            "helper_version_match": True,
            "capability_fail_closed": True,
            "no_screen_contract": True,
            "client_process_stable_during_wrapper": True,
            "screenshot_count_stable_during_wrapper": True,
        },
        "wrapper_invariants": {
            "client_process_stable": True,
            "screenshot_count_stable": True,
        },
        "intrusive_actions_performed": [],
        "integrity": {
            "manifest_sha256": "b" * 64,
            "helper_version": "v2.3.0",
        },
        "capability": {
            "runtime_actions": False,
            "runtime_core_actions": False,
            "conditions_observation": observation_envelope,
        },
        "blockers": [],
    }
    recovery_proof = _read_json(P9_FIXTURES / "positive-recovery-proof.json")
    recovery_proof["observed_at_unix_ms"] = evaluated_at - 2_000
    recovery_proof["source"] = "recovery_shadow"
    scenarios = _read_json(replay.DEFAULT_SCENARIO_PACK)

    _write_json(profile_path, profile)
    _write_json(recovery_trace_path, recovery_trace)
    _write_json(scenario_path, scenarios)
    _write_json(p8_path, p8)
    profile_document = replay.read_document(profile_path)
    raw_p8_document = replay.read_document(p8_path)
    observation_document = replay.extract_embedded_observation(raw_p8_document)
    recovery_trace_document = replay.read_document(recovery_trace_path)
    p8_document = replay.normalize_p8_proof(raw_p8_document, observation_document)
    recovery_proof["recovery_trace_sha256"] = recovery_trace_document.sha256
    recovery_proof["profile_sha256"] = profile_document.sha256
    recovery_proof["observation_sha256"] = observation_document.sha256
    recovery_proof["p8_proof_sha256"] = p8_document.sha256
    recovery_proof["proof_id"] = ""
    recovery_proof["proof_id"] = "conditions-recovery-" + replay.canonical_sha256(
        {key: value for key, value in recovery_proof.items() if key != "proof_id"}
    )[:16]
    _write_json(recovery_proof_path, recovery_proof)
    recovery_proof_document = replay.read_document(recovery_proof_path)
    scenario_document = replay.read_document(scenario_path, replay.MAX_SCENARIO_BYTES)
    report = replay.build_report(
        profile_document=profile_document,
        raw_p8_document=raw_p8_document,
        recovery_trace_document=recovery_trace_document,
        recovery_proof_document=recovery_proof_document,
        scenario_document=scenario_document,
        evaluated_at_unix_ms=evaluated_at,
        explicit_observation_document=None,
    )
    assert report["operational_acceptance_status"] == (
        "shadow_plan_ready_for_operator_review"
    )
    assert report["scenario_pack_status"] == "passed"
    _write_json(report_path, report)
    return acceptance.EvidencePaths(
        report=report_path,
        profile=profile_path,
        p8_proof=p8_path,
        recovery_trace=recovery_trace_path,
        recovery_proof=recovery_proof_path,
        scenario_pack=scenario_path,
        observation=None,
    )


def _allow_test_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acceptance, "_canonical_operational_paths", lambda paths: True)


def _assert_no_action(receipt: dict[str, object]) -> None:
    assert receipt["runtime_readiness_claimed"] is False
    assert receipt["intrusive_actions_performed"] == []
    for key in replay.FALSE_FLAGS:
        assert receipt[key] is False


def test_acceptance_schema_and_scenario_fixture_are_strict_and_closed():
    schema = _read_json(ROOT / "schemas" / "conditions-shadow-acceptance.schema.json")
    fixture = _read_json(ACCEPTANCE_FIXTURES / "scenarios.json")

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == acceptance.RECEIPT_KEYS
    assert schema["properties"]["input_sha256"]["additionalProperties"] is False
    Draft202012Validator.check_schema(schema)
    blocker_values = set(schema["properties"]["blockers"]["items"]["enum"])
    assert blocker_values == set(acceptance.BLOCKER_ORDER)
    assert fixture["schema_version"] == (
        "ctoa.conditions-shadow-acceptance-scenarios.v1"
    )
    assert fixture["fixture_only"] is True
    assert fixture["operational_acceptance_claimed"] is False
    assert len(fixture["cases"]) == 4


@pytest.mark.parametrize(
    "case",
    _read_json(ACCEPTANCE_FIXTURES / "scenarios.json")["cases"],
    ids=lambda case: case["name"],
)
def test_ready_report_confirmation_matrix_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: dict[str, object]
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=case["confirmation"],
        write_requested=case["write_requested"],
        now_unix_ms=NOW_MS,
    )

    assert receipt["status"] == case["expected_status"]
    assert acceptance._receipt_contract_valid(receipt)
    assert receipt["acceptance_granted"] is (case["expected_status"] == "accepted")
    assert receipt["operator_review_completed"] is (
        case["expected_status"] == "accepted"
    )
    assert receipt["canonical_operational_paths"] is True
    schema = _read_json(ROOT / "schemas" / "conditions-shadow-acceptance.schema.json")
    Draft202012Validator(schema).validate(receipt)
    _assert_no_action(receipt)


def test_noncanonical_paths_cannot_create_an_accepted_receipt(tmp_path: Path):
    paths = _ready_workspace(tmp_path)

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )

    assert receipt["status"] == "blocked"
    assert receipt["acceptance_granted"] is False
    assert receipt["canonical_operational_paths"] is False
    assert "noncanonical_operational_paths" in receipt["blockers"]


@pytest.mark.parametrize(
    ("mutation", "expected_blocker"),
    [
        ("extra_key", "report_schema_invalid"),
        ("dispatch_true", "unsafe_action_contract"),
        ("case_runtime_true", "unsafe_action_contract"),
        ("decision_hash", "report_recompute_mismatch"),
    ],
)
def test_report_mutations_never_accept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected_blocker: str,
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    report = _read_json(paths.report)
    trace = report["operational_trace"]
    pack = report["scenario_pack"]
    assert isinstance(trace, dict)
    assert isinstance(pack, dict)
    cases = pack["cases"]
    assert isinstance(cases, list) and cases and isinstance(cases[0], dict)
    if mutation == "extra_key":
        report["unvalidated"] = False
    elif mutation == "dispatch_true":
        report["dispatch_allowed"] = True
    elif mutation == "case_runtime_true":
        cases[0]["runtime_actions"] = True
    elif mutation == "decision_hash":
        trace["decision_sha256"] = "a" * 64
    else:  # pragma: no cover
        raise AssertionError(mutation)
    _write_json(paths.report, report)

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )

    assert receipt["status"] == "blocked"
    assert receipt["acceptance_granted"] is False
    assert expected_blocker in receipt["blockers"]
    _assert_no_action(receipt)


@pytest.mark.parametrize(
    ("now_ms", "expected_blocker"),
    [
        (NOW_MS - 1, "report_future"),
        (NOW_MS + acceptance.MAX_REPORT_AGE_MS + 1, "report_stale"),
    ],
)
def test_future_or_stale_report_cannot_accept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    now_ms: int,
    expected_blocker: str,
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=now_ms,
    )

    assert receipt["status"] == "blocked"
    assert expected_blocker in receipt["blockers"]
    assert receipt["acceptance_granted"] is False


@pytest.mark.parametrize("duplicate_value", ["false", "true"])
def test_duplicate_safe_or_unsafe_report_key_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    duplicate_value: str,
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    raw = paths.report.read_text(encoding="utf-8").rstrip()
    paths.report.write_text(
        raw[:-1] + f',"dispatch_allowed":{duplicate_value}' + "}\n",
        encoding="utf-8",
    )

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )

    assert receipt["status"] == "blocked"
    assert "report_duplicate_keys" in receipt["blockers"]
    assert receipt["acceptance_granted"] is False


def test_fixture_operational_inputs_can_never_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    report_path = tmp_path / "fixture-report.json"
    documents = replay._fixture_documents()
    report = replay.build_report(
        profile_document=documents[0],
        raw_p8_document=documents[2],
        recovery_trace_document=documents[3],
        recovery_proof_document=documents[4],
        scenario_document=replay.read_document(
            replay.DEFAULT_SCENARIO_PACK, replay.MAX_SCENARIO_BYTES
        ),
        evaluated_at_unix_ms=NOW_MS,
        explicit_observation_document=documents[1],
    )
    _write_json(report_path, report)
    paths = acceptance.EvidencePaths(
        report=report_path,
        profile=replay.DEFAULT_PROFILE,
        p8_proof=P9_FIXTURES / "positive-p8-proof.json",
        recovery_trace=P9_FIXTURES / "positive-recovery-trace.json",
        recovery_proof=P9_FIXTURES / "positive-recovery-proof.json",
        scenario_pack=replay.DEFAULT_SCENARIO_PACK,
        observation=P9_FIXTURES / "positive-observation.json",
    )
    _allow_test_paths(monkeypatch)

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )

    assert receipt["status"] == "blocked"
    assert "operational_inputs_fixture" in receipt["blockers"]
    assert "operational_status_not_ready" in receipt["blockers"]
    assert receipt["acceptance_granted"] is False


def test_changed_current_input_breaks_report_recomputation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    recovery = _read_json(paths.recovery_proof)
    recovery["observed_at_unix_ms"] = NOW_MS - 3_000
    _write_json(paths.recovery_proof, recovery)

    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )

    assert receipt["status"] == "blocked"
    assert "report_recompute_mismatch" in receipt["blockers"]
    assert receipt["acceptance_granted"] is False


def test_only_contract_valid_accepted_receipt_can_be_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )
    output = tmp_path / "runtime" / "conditions_shadow_acceptance.json"
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(acceptance, "_now_unix_ms", lambda: NOW_MS)

    persisted_receipt = acceptance.write_accepted_receipt(
        output,
        paths=paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
    )

    persisted = _read_json(output)
    assert persisted == persisted_receipt == receipt
    with pytest.raises(ValueError, match="exact operator confirmation"):
        acceptance.write_accepted_receipt(
            output,
            paths=paths,
            confirmation="wrong",
        )


def test_forged_or_stale_receipt_cannot_cross_the_writer_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    output = tmp_path / "runtime" / "conditions_shadow_acceptance.json"
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(
        acceptance,
        "_now_unix_ms",
        lambda: NOW_MS + acceptance.MAX_REPORT_AGE_MS + 1,
    )

    stale = acceptance.write_accepted_receipt(
        output,
        paths=paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
    )

    assert stale["status"] == "blocked"
    assert stale["acceptance_granted"] is False
    assert "report_stale" in stale["blockers"]
    assert not output.exists()

    forged = copy.deepcopy(stale)
    forged["status"] = "accepted"
    forged["acceptance_granted"] = True
    forged["operator_review_completed"] = True
    forged["receipt_persisted"] = True
    forged["blockers"] = []
    forged["report_age_ms"] = 10**12
    assert acceptance._receipt_contract_valid(forged) is False


def test_accepted_receipt_rejects_resealed_basis_id_and_zero_hash_mutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    receipt, _ = acceptance.evaluate_acceptance(
        paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
        write_requested=True,
        now_unix_ms=NOW_MS,
    )
    schema = _read_json(ROOT / "schemas" / "conditions-shadow-acceptance.schema.json")

    bad_basis = copy.deepcopy(receipt)
    bad_basis["acceptance_basis_sha256"] = "f" * 64
    assert acceptance._receipt_contract_valid(bad_basis) is False
    bad_id = copy.deepcopy(receipt)
    bad_id["receipt_id"] = "conditions-shadow-acceptance-ffffffffffffffff"
    assert acceptance._receipt_contract_valid(bad_id) is False

    for field in ("scenario_pack_sha256", "canonical_input_sha256"):
        forged = copy.deepcopy(receipt)
        forged[field] = acceptance.ZERO_SHA256
        basis_sha = replay.canonical_sha256(acceptance._acceptance_basis(forged))
        forged["acceptance_basis_sha256"] = basis_sha
        forged["receipt_id"] = f"conditions-shadow-acceptance-{basis_sha[:16]}"
        assert acceptance._receipt_contract_valid(forged) is False
        assert list(Draft202012Validator(schema).iter_errors(forged))


def test_writer_rechecks_evidence_immediately_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    output = tmp_path / "runtime" / "conditions_shadow_acceptance.json"
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(acceptance, "_now_unix_ms", lambda: NOW_MS)
    original_evaluate = acceptance.evaluate_acceptance
    call_count = 0

    def evaluate_with_late_change(*args: object, **kwargs: object):
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            recovery = _read_json(paths.recovery_proof)
            recovery["observed_at_unix_ms"] = NOW_MS - 3_000
            _write_json(paths.recovery_proof, recovery)
        return original_evaluate(*args, **kwargs)

    monkeypatch.setattr(acceptance, "evaluate_acceptance", evaluate_with_late_change)

    blocked = acceptance.write_accepted_receipt(
        output,
        paths=paths,
        confirmation=acceptance.EXACT_CONFIRMATION,
    )

    assert blocked["status"] == "blocked"
    assert "evidence_changed_before_write" in blocked["blockers"]
    assert not output.exists()


def test_cli_writes_only_after_exact_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _ready_workspace(tmp_path)
    _allow_test_paths(monkeypatch)
    output = tmp_path / "runtime" / "conditions_shadow_acceptance.json"
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", tmp_path / "runtime")
    monkeypatch.setattr(acceptance, "_now_unix_ms", lambda: NOW_MS)
    base_args = [
        "--report",
        str(paths.report),
        "--profile",
        str(paths.profile),
        "--p8-proof",
        str(paths.p8_proof),
        "--recovery-trace",
        str(paths.recovery_trace),
        "--recovery-proof",
        str(paths.recovery_proof),
        "--scenario-pack",
        str(paths.scenario_pack),
        "--json-out",
        str(output),
    ]

    assert acceptance.main(base_args) == 0
    assert not output.exists()
    assert acceptance.main(base_args + ["--confirm", "wrong"]) == 1
    assert not output.exists()
    assert (
        acceptance.main(
            base_args + ["--confirm", acceptance.EXACT_CONFIRMATION, "--no-write"]
        )
        == 0
    )
    assert not output.exists()
    assert (
        acceptance.main(base_args + ["--confirm", acceptance.EXACT_CONFIRMATION]) == 0
    )
    assert _read_json(output)["status"] == "accepted"


def test_output_path_is_runtime_only_and_rejects_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = tmp_path / "runtime"
    output = runtime / "conditions_shadow_acceptance.json"
    runtime.mkdir()
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", runtime)

    with pytest.raises(ValueError, match="must equal"):
        acceptance._validate_output_path(tmp_path / "elsewhere.json")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    try:
        output.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")
    with pytest.raises(ValueError, match="regular non-link"):
        acceptance._validate_output_path(output)


def test_output_path_rejects_reparse_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runtime = tmp_path / "runtime"
    real = runtime / "real"
    linked = runtime / "linked"
    real.mkdir(parents=True)
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are not available: {exc}")
    output = linked / "conditions_shadow_acceptance.json"
    monkeypatch.setattr(acceptance, "DEFAULT_OUTPUT", output)
    monkeypatch.setattr(acceptance, "RUNTIME_ROOT", runtime)

    with pytest.raises(ValueError, match="ancestors must not contain reparse"):
        acceptance._validate_output_path(output)
