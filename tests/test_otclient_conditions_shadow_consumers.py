import copy
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = ROOT / "scripts" / "ops"
RELEASE_SCRIPT = OPS_DIR / "release_evidence_pack.py"
CORE_SCRIPT = OPS_DIR / "otclient_conditions_shadow_replay.py"
EVALUATED_AT_UNIX_MS = 1_783_800_000_000


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if str(OPS_DIR) not in sys.path:
    sys.path.insert(0, str(OPS_DIR))

core = _load_module("conditions_shadow_core_for_consumers", CORE_SCRIPT)
release = _load_module("release_evidence_pack_for_conditions_shadow", RELEASE_SCRIPT)


def _report(evaluated_at_unix_ms: int = EVALUATED_AT_UNIX_MS) -> dict[str, object]:
    return core.build_report(
        profile_document=core.read_document(core.DEFAULT_PROFILE),
        raw_p8_document=core.read_document(core.FIXTURE_DIR / "positive-p8-proof.json"),
        recovery_trace_document=core.read_document(
            core.FIXTURE_DIR / "positive-recovery-trace.json"
        ),
        recovery_proof_document=core.read_document(
            core.FIXTURE_DIR / "positive-recovery-proof.json"
        ),
        scenario_document=core.read_document(
            core.DEFAULT_SCENARIO_PACK, core.MAX_SCENARIO_BYTES
        ),
        evaluated_at_unix_ms=evaluated_at_unix_ms,
        explicit_observation_document=core.read_document(
            core.FIXTURE_DIR / "positive-observation.json"
        ),
    )


def _as_utc(unix_ms: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(unix_ms / 1000, tz=dt.UTC)


def _make_ready(report: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(report)
    trace = result["operational_trace"]
    assert isinstance(trace, dict)
    trace["status"] = "shadow_plan_ready"
    trace["decision"] = "would_plan_paralyze_recovery"
    trace["blockers"] = []
    decision_basis = {
        "schema_version": core.TRACE_SCHEMA,
        "canonical_input_sha256": trace["canonical_input_sha256"],
        "status": trace["status"],
        "decision": trace["decision"],
        "action": trace["action"],
        "condition": trace["condition"],
        "spell": trace["spell"],
        "observation_age_ms": trace["observation_age_ms"],
        "p8_age_ms": trace["p8_age_ms"],
        "recovery_trace_age_ms": trace["recovery_trace_age_ms"],
        "recovery_age_ms": trace["recovery_age_ms"],
        "blockers": trace["blockers"],
        "operator_review_required": True,
        **{key: False for key in core.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    trace["decision_sha256"] = core.canonical_sha256(decision_basis)
    trace["trace_id"] = f"conditions-shadow-{trace['decision_sha256'][:16]}"
    result["operational_acceptance_status"] = "shadow_plan_ready_for_operator_review"
    return result


def test_release_consumer_accepts_blocked_runtime_and_separates_fixture_pass():
    report = _report()
    summary = release._conditions_shadow_summary(
        report,
        Path("runtime/solteria_helper_dev/conditions_shadow_replay.json"),
        now=_as_utc(EVALUATED_AT_UNIX_MS),
        artifact_present=True,
    )

    assert summary["status"] == "operational_acceptance_blocked"
    assert summary["contract_valid"] is True
    assert summary["fresh"] is True
    assert summary["trace_status"] == "operational_acceptance_blocked"
    assert summary["fixture_validation_status"] == "passed"
    assert summary["fixture_only_validation_passed"] is True
    assert summary["fixture_passed_count"] == summary["fixture_total_count"]
    assert summary["fixture_failed_count"] == 0
    assert summary["runtime_readiness_claimed"] is False
    assert summary["intrusive_actions_performed"] == []
    assert all(summary[key] is False for key in core.FALSE_FLAGS)


def test_release_consumer_accepts_ready_status_only_as_operator_review():
    report = _make_ready(_report())
    summary = release._conditions_shadow_summary(
        report,
        Path("conditions_shadow_replay.json"),
        now=_as_utc(EVALUATED_AT_UNIX_MS),
        artifact_present=True,
    )

    assert summary["status"] == "shadow_plan_ready_for_operator_review"
    assert summary["decision"] == "would_plan_paralyze_recovery"
    assert summary["operator_review_required"] is True
    assert summary["runtime_readiness_claimed"] is False
    assert summary["dispatch_allowed"] is False


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("report_extra_key", "report.exact_keys"),
        ("report_flag_true", "report.dispatch_allowed"),
        ("report_nonempty_ledger", "report.intrusive_actions_performed"),
        ("trace_extra_key", "operational_trace.exact_keys"),
        ("trace_flag_true", "operational_trace.runtime_actions"),
        (
            "trace_nonempty_ledger",
            "operational_trace.intrusive_actions_performed",
        ),
        ("bad_status", "report.operational_status_consistency"),
        ("report_status_shape", "report.operational_acceptance_status"),
        ("trace_status_shape", "operational_trace.status"),
        ("trace_decision_shape", "operational_trace.decision"),
        ("bad_decision_hash", "operational_trace.decision_sha256_mismatch"),
        ("bad_trace_timestamp", "operational_trace.evaluated_at_unix_ms"),
        ("scenario_extra_key", "scenario_pack.exact_keys"),
        ("bad_passed_count", "scenario_pack.passed_count_consistency"),
        ("bad_scenario_status", "scenario_pack.status_count_consistency"),
        ("scenario_status_shape", "scenario_pack.status"),
        ("case_extra_key", "scenario_pack.cases[0].exact_keys"),
        ("case_flag_true", "scenario_pack.cases[0].executes_plan"),
        (
            "case_nonempty_ledger",
            "scenario_pack.cases[0].intrusive_actions_performed",
        ),
        ("case_unknown_blocker", "scenario_pack.cases[0].blockers"),
        ("case_mutation_shape", "scenario_pack.cases[0].mutation"),
        ("case_expected_status_shape", "scenario_pack.cases[0].expected_status"),
        ("case_bad_hash", "scenario_pack.cases[0].decision_sha256"),
    ],
)
def test_release_consumer_mutations_fail_closed(mutation: str, expected_error: str):
    report = _report()
    trace = report["operational_trace"]
    pack = report["scenario_pack"]
    assert isinstance(trace, dict)
    assert isinstance(pack, dict)
    cases = pack["cases"]
    assert isinstance(cases, list) and cases
    case = cases[0]
    assert isinstance(case, dict)

    if mutation == "report_extra_key":
        report["unvalidated"] = False
    elif mutation == "report_flag_true":
        report["dispatch_allowed"] = True
    elif mutation == "report_nonempty_ledger":
        report["intrusive_actions_performed"] = ["client_input"]
    elif mutation == "trace_extra_key":
        trace["unvalidated"] = False
    elif mutation == "trace_flag_true":
        trace["runtime_actions"] = True
    elif mutation == "trace_nonempty_ledger":
        trace["intrusive_actions_performed"] = ["screenshot_capture"]
    elif mutation == "bad_status":
        report["operational_acceptance_status"] = (
            "shadow_plan_ready_for_operator_review"
        )
    elif mutation == "report_status_shape":
        report["operational_acceptance_status"] = {"unexpected": "shape"}
    elif mutation == "trace_status_shape":
        trace["status"] = {"unexpected": "shape"}
    elif mutation == "trace_decision_shape":
        trace["decision"] = ["hold"]
    elif mutation == "bad_decision_hash":
        trace["decision_sha256"] = "a" * 64
    elif mutation == "bad_trace_timestamp":
        trace["evaluated_at_unix_ms"] = EVALUATED_AT_UNIX_MS - 1
    elif mutation == "scenario_extra_key":
        pack["unvalidated"] = False
    elif mutation == "bad_passed_count":
        pack["passed_count"] = 0
    elif mutation == "bad_scenario_status":
        pack["status"] = "failed"
        report["scenario_pack_status"] = "failed"
        report["fixture_only_validation_passed"] = False
    elif mutation == "scenario_status_shape":
        pack["status"] = {"unexpected": "shape"}
    elif mutation == "case_extra_key":
        case["unvalidated"] = False
    elif mutation == "case_flag_true":
        case["executes_plan"] = True
    elif mutation == "case_nonempty_ledger":
        case["intrusive_actions_performed"] = ["dispatch"]
    elif mutation == "case_unknown_blocker":
        case["blockers"] = ["unknown_blocker"]
    elif mutation == "case_mutation_shape":
        case["mutation"] = {"unexpected": "shape"}
    elif mutation == "case_expected_status_shape":
        case["expected_status"] = ["shadow_plan_ready"]
    elif mutation == "case_bad_hash":
        case["decision_sha256"] = "not-a-sha"
    else:  # pragma: no cover - parametrization is exhaustive
        raise AssertionError(f"unsupported mutation: {mutation}")

    summary = release._conditions_shadow_summary(
        report,
        Path("conditions_shadow_replay.json"),
        now=_as_utc(EVALUATED_AT_UNIX_MS),
        artifact_present=True,
    )

    assert summary["status"] == "invalid"
    assert summary["contract_valid"] is False
    assert summary["fresh"] is False
    assert summary["runtime_readiness_claimed"] is False
    assert summary["dispatch_allowed"] is False
    assert summary["intrusive_actions_performed"] == []
    assert expected_error in summary["contract_errors"]


@pytest.mark.parametrize("offset_seconds", [-1, 31])
def test_release_consumer_future_or_expired_report_is_stale(offset_seconds: int):
    report = _report()
    summary = release._conditions_shadow_summary(
        report,
        Path("conditions_shadow_replay.json"),
        now=_as_utc(EVALUATED_AT_UNIX_MS) + dt.timedelta(seconds=offset_seconds),
        artifact_present=True,
    )

    assert summary["contract_valid"] is True
    assert summary["fresh"] is False
    assert summary["status"] == "stale"
    assert summary["runtime_readiness_claimed"] is False


def test_release_consumer_rejects_deep_in_memory_shape_without_recursion_error():
    report = _report()
    trace = report["operational_trace"]
    assert isinstance(trace, dict)
    nested: object = 0
    for _ in range(992):
        nested = [nested]
    trace["observation_age_ms"] = nested

    summary = release._conditions_shadow_summary(
        report,
        Path("conditions_shadow_replay.json"),
        now=_as_utc(EVALUATED_AT_UNIX_MS),
        artifact_present=True,
    )

    assert summary["status"] == "invalid"
    assert summary["contract_valid"] is False
    assert summary["contract_errors"] == ["report.structure_bounds"]
    assert summary["dispatch_allowed"] is False


@pytest.mark.parametrize("duplicate_value", ["false", "true"])
def test_helper_status_rejects_duplicate_safe_or_unsafe_json_keys(
    tmp_path: Path, duplicate_value: str
):
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    raw = json.dumps(_report())
    duplicate = raw[:-1] + f',"dispatch_allowed":{duplicate_value}' + "}"
    (helper_dev_dir / "conditions_shadow_replay.json").write_text(
        duplicate, encoding="utf-8"
    )

    summary = release._helper_status(helper_dev_dir)["conditions_shadow"]

    assert summary["status"] == "invalid"
    assert summary["contract_valid"] is False
    assert summary["runtime_readiness_claimed"] is False
    assert summary["dispatch_allowed"] is False


@pytest.mark.parametrize("nonfinite_number", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_helper_status_rejects_nonfinite_json_numbers(
    tmp_path: Path, nonfinite_number: str
):
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "conditions_shadow_replay.json").write_text(
        f'{{"schema_version":{nonfinite_number}}}', encoding="utf-8"
    )

    summary = release._helper_status(helper_dev_dir)["conditions_shadow"]

    assert summary["status"] == "invalid"
    assert summary["contract_valid"] is False
    assert summary["runtime_readiness_claimed"] is False
    assert summary["dispatch_allowed"] is False


@pytest.mark.parametrize("depth", [80, 1100])
def test_helper_status_rejects_excessive_json_nesting(tmp_path: Path, depth: int):
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    (helper_dev_dir / "conditions_shadow_replay.json").write_text(
        '{"deep":' + "[" * depth + "0" + "]" * depth + "}", encoding="utf-8"
    )

    summary = release._helper_status(helper_dev_dir)["conditions_shadow"]

    assert summary["status"] == "invalid"
    assert summary["contract_valid"] is False
    assert summary["runtime_readiness_claimed"] is False
    assert summary["dispatch_allowed"] is False


def test_helper_status_exposes_missing_conditions_path(tmp_path: Path):
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)

    helper = release._helper_status(helper_dev_dir)

    assert helper["conditions_shadow"]["status"] == "missing"
    assert helper["conditions_shadow"]["contract_valid"] is False
    assert helper["paths"]["conditions_shadow"].endswith(
        "conditions_shadow_replay.json"
    )


def test_helper_status_and_markdown_expose_fixture_pass_without_runtime_claim(
    tmp_path: Path,
):
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    now_ms = int(dt.datetime.now(dt.UTC).timestamp() * 1000)
    (helper_dev_dir / "conditions_shadow_replay.json").write_text(
        json.dumps(_report(now_ms)), encoding="utf-8"
    )

    pack = release.build_evidence_pack(
        tmp_path / "releases" / "evidence",
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
        helper_dev_dir,
        tmp_path / "AI" / "generated" / "P7_OPERATOR_BRIEF.json",
    )
    conditions = pack["otclient_helper"]["conditions_shadow"]
    markdown = release.render_markdown(pack)

    assert conditions["status"] == "operational_acceptance_blocked"
    assert conditions["fixture_only_validation_passed"] is True
    assert conditions["runtime_readiness_claimed"] is False
    assert "- Conditions Shadow: `operational_acceptance_blocked`" in markdown
    assert "fixtures=`passed`" in markdown
    assert "fixture_only_passed=`True`" in markdown
    assert "runtime_readiness_claimed=`False`" in markdown


def test_helper_status_does_not_follow_symlinked_conditions_report(tmp_path: Path):
    helper_dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    helper_dev_dir.mkdir(parents=True)
    outside = tmp_path / "outside-conditions.json"
    outside.write_text(json.dumps(_report()), encoding="utf-8")
    linked = helper_dev_dir / "conditions_shadow_replay.json"
    try:
        linked.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    summary = release._helper_status(helper_dev_dir)["conditions_shadow"]

    assert summary["status"] == "missing"
    assert summary["contract_valid"] is False
    assert summary["blockers"] == []
