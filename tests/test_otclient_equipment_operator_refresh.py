from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ops import otclient_equipment_operator_refresh as refresh


READY_STATUS = {
    "capture_profile_doctor": "blocked",
    "observation_preview": "blocked",
    "dependency_preflight": "blocked",
    "candidate_catalog": "blocked",
    "capture_profile_change_plan": "blocked",
    "operator_readiness": "blocked",
}


class FakeEnvelope:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.run_id = "12345678-1234-4234-9234-123456789abc"
        self.fail_on = fail_on
        self.begin_calls = 0
        self.recorded: list[str] = []
        self.aborted: list[str] = []

    def begin_run(self, *, dev_dir: Path) -> dict[str, object]:
        del dev_dir
        self.begin_calls += 1
        if self.fail_on == "begin":
            raise RuntimeError("begin failed")
        return {"run_id": self.run_id}

    def record_stage(
        self, stage_id: str, run_id: str, *, dev_dir: Path
    ) -> dict[str, object]:
        del dev_dir
        assert run_id == self.run_id
        if self.fail_on == stage_id:
            raise RuntimeError("record failed")
        self.recorded.append(stage_id)
        return {"stage_id": stage_id}

    def finalize_run(self, run_id: str, *, dev_dir: Path) -> dict[str, object]:
        del dev_dir
        assert run_id == self.run_id
        if self.fail_on == "finalize":
            raise RuntimeError("finalize failed")
        return {
            "schema_version": "ctoa.equipment-operator-refresh-run.v1",
            "status": "completed",
            "run_id": run_id,
            "stage_order": list(self.recorded),
        }

    def abort_run(self, run_id: str, *, dev_dir: Path) -> dict[str, object]:
        del dev_dir
        assert run_id == self.run_id
        if self.fail_on == "abort":
            raise RuntimeError("abort failed")
        self.aborted.append(run_id)
        return {"status": "aborted", "run_id": run_id}


def _parity_payload(*, status: str = "passed") -> dict[str, object]:
    passed = status == "passed"
    return {
        "schema_version": refresh.PARITY_SCHEMA,
        "status": status,
        "artifact_count": 6,
        "checks": {name: passed for name in refresh.PARITY_CHECKS},
        "blockers": [] if passed else ["artifact_divergence:operator_readiness"],
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        **{name: False for name in refresh.FALSE_ACTION_FIELDS},
        "intrusive_actions_performed": [],
    }


class FakeRunner:
    def __init__(
        self,
        dev_dir: Path,
        *,
        fail_stage: str | None = None,
        parity_status: str = "passed",
        skip_write_stage: str | None = None,
    ) -> None:
        self.dev_dir = dev_dir
        self.fail_stage = fail_stage
        self.parity_status = parity_status
        self.skip_write_stage = skip_write_stage
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def __call__(
        self, command: list[str], **kwargs
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(command), dict(kwargs)))
        script_name = Path(command[1]).name
        stage = next(
            item for item in refresh.STAGES if item.script_filename == script_name
        )
        if stage.stage_id != self.skip_write_stage:
            payload: dict[str, object]
            if stage.stage_id == "consumer_parity":
                payload = _parity_payload(status=self.parity_status)
            else:
                payload = {
                    "schema_version": stage.schema_version,
                    "status": READY_STATUS[stage.stage_id],
                    "blockers": [f"{stage.stage_id}_fixture_blocked"],
                    "generation": len(self.calls),
                }
            output = self.dev_dir / stage.output_filename
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload), encoding="utf-8")
        exit_code = 0
        if stage.stage_id == self.fail_stage:
            exit_code = 2
        elif stage.stage_id == "consumer_parity" and self.parity_status != "passed":
            exit_code = 1
        return subprocess.CompletedProcess(command, exit_code, stdout="", stderr="")


def test_stage_contract_is_fixed_ordered_and_has_no_action_inputs() -> None:
    assert [stage.stage_id for stage in refresh.STAGES] == [
        "capture_profile_doctor",
        "observation_preview",
        "dependency_preflight",
        "candidate_catalog",
        "capture_profile_change_plan",
        "operator_readiness",
        "consumer_parity",
    ]
    assert all(stage.arguments == ("--allow-blocked",) for stage in refresh.STAGES[:-1])
    assert refresh.STAGES[-1].arguments == ()
    assert len({stage.output_filename for stage in refresh.STAGES}) == 7
    rendered = json.dumps(
        [
            {
                "script": stage.script_filename,
                "arguments": stage.arguments,
                "output": stage.output_filename,
            }
            for stage in refresh.STAGES
        ]
    ).lower()
    for forbidden in (
        "acceptance",
        "--init-local",
        "--equipped-item-id",
        "--candidate-item-id",
        "--candidate-container-id",
        "--candidate-slot-index",
        "--confirm",
        "shadow_replay.py",
        "shadow_snapshot.py",
    ):
        assert forbidden not in rendered


def test_refresh_runs_all_fixed_stages_and_requires_real_parity_pass(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    runner = FakeRunner(dev_dir)
    envelope = FakeEnvelope()

    summary = refresh.run_refresh(run_command=runner, envelope_backend=envelope)

    assert summary["status"] == "passed"
    assert summary["stage_count"] == summary["expected_stage_count"] == 7
    assert summary["failed_stage"] is None
    assert summary["parity_passed"] is True
    assert summary["run_envelope_status"] == "completed"
    assert summary["run_id"] == envelope.run_id
    assert len(summary["run_envelope_sha256"]) == 64
    assert envelope.recorded == [stage.stage_id for stage in refresh.STAGES]
    assert envelope.aborted == []
    assert summary["operator_inputs_ready"] is False
    assert len(summary["parity_sha256"]) == 64
    assert summary["blockers"] == []
    assert [item["stage_id"] for item in summary["stages"]] == [
        stage.stage_id for stage in refresh.STAGES
    ]
    assert all(item["artifact_refreshed"] is True for item in summary["stages"])
    assert all(item["ok"] is True for item in summary["stages"])
    assert [item["artifact_blocker_count"] for item in summary["stages"]] == [
        1,
        1,
        1,
        1,
        1,
        1,
        0,
    ]
    assert all(
        summary[name] is False
        for name in (
            *refresh.FALSE_ACTION_FIELDS,
            "local_profile_write_performed",
            "client_process_actions",
            "explicit_identifiers_accepted",
            "operator_confirmation_accepted",
            "acceptance_granted",
            "eligibility_changed",
            "operational_readiness_claimed",
        )
    )
    assert summary["intrusive_actions_performed"] == []

    for index, (command, kwargs) in enumerate(runner.calls):
        stage = refresh.STAGES[index]
        assert command == [
            sys.executable,
            str(refresh.OPS_DIR / stage.script_filename),
            *stage.arguments,
        ]
        assert kwargs["cwd"] == refresh.ROOT
        assert kwargs["shell"] is False
        assert kwargs["check"] is False
        assert kwargs["capture_output"] is True
        assert kwargs["env"]["CTOA_OPERATOR_MODE"] == "background_no_screen"


def test_refresh_fails_closed_when_parity_is_blocked(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    envelope = FakeEnvelope()
    summary = refresh.run_refresh(
        run_command=FakeRunner(dev_dir, parity_status="blocked"),
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["failed_stage"] == "consumer_parity"
    assert summary["parity_passed"] is False
    parity = summary["stages"][-1]
    assert parity["arguments"] == []
    assert parity["exit_code"] == 1
    assert "parity_status" in parity["blockers"]
    assert "stage_failed:consumer_parity" in summary["blockers"]
    assert summary["run_envelope_status"] == "aborted"
    assert envelope.aborted == [envelope.run_id]


def test_refresh_stops_before_downstream_stages_on_producer_error(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    runner = FakeRunner(dev_dir, fail_stage="dependency_preflight")

    envelope = FakeEnvelope()
    summary = refresh.run_refresh(
        run_command=runner,
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["failed_stage"] == "dependency_preflight"
    assert summary["stage_count"] == 3
    assert summary["parity_passed"] is False
    assert all(stage["stage_id"] != "consumer_parity" for stage in summary["stages"])
    assert summary["run_envelope_status"] == "aborted"
    assert envelope.aborted == [envelope.run_id]


def test_refresh_rejects_stale_artifact_reuse(tmp_path: Path, monkeypatch) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    first = refresh.STAGES[0]
    output = dev_dir / first.output_filename
    output.parent.mkdir(parents=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": first.schema_version,
                "status": "blocked",
                "blockers": ["stale_fixture"],
            }
        ),
        encoding="utf-8",
    )

    envelope = FakeEnvelope()
    summary = refresh.run_refresh(
        run_command=FakeRunner(dev_dir, skip_write_stage=first.stage_id),
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["failed_stage"] == first.stage_id
    assert summary["stage_count"] == 1
    assert "artifact_not_refreshed" in summary["stages"][0]["blockers"]
    assert envelope.aborted == [envelope.run_id]


def test_refresh_rejects_symlinked_fixed_output_before_spawning(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    dev_dir.mkdir(parents=True)
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    outside = tmp_path / "outside.json"
    outside.write_text("preserve", encoding="utf-8")
    output = dev_dir / refresh.STAGES[0].output_filename
    try:
        output.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")
    runner = FakeRunner(dev_dir)

    envelope = FakeEnvelope()
    summary = refresh.run_refresh(
        run_command=runner,
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["failed_stage"] == refresh.STAGES[0].stage_id
    assert summary["stages"][0]["blockers"] == ["fixed_output_path_unsafe"]
    assert runner.calls == []
    assert outside.read_text(encoding="utf-8") == "preserve"
    assert envelope.aborted == [envelope.run_id]


def test_cli_accepts_no_paths_ids_confirmations_or_acceptance_arguments() -> None:
    assert vars(refresh.parse_args([])) == {}
    for arguments in (
        ["--dev-dir", "outside"],
        ["--equipped-item-id", "3051"],
        ["--confirm", "anything"],
        ["accept"],
    ):
        with pytest.raises(SystemExit) as error:
            refresh.parse_args(arguments)
        assert error.value.code == 2


def test_refresh_fails_closed_when_envelope_record_or_finalize_fails(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    record_envelope = FakeEnvelope(fail_on="candidate_catalog")
    record_failure = refresh.run_refresh(
        run_command=FakeRunner(dev_dir),
        envelope_backend=record_envelope,
    )
    assert record_failure["status"] == "blocked"
    assert record_failure["failed_stage"] == "candidate_catalog"
    assert record_failure["run_envelope_status"] == "aborted"
    assert record_envelope.aborted == [record_envelope.run_id]

    other_dev_dir = tmp_path / "other" / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", other_dev_dir)
    final_envelope = FakeEnvelope(fail_on="finalize")
    final_failure = refresh.run_refresh(
        run_command=FakeRunner(other_dev_dir),
        envelope_backend=final_envelope,
    )
    assert final_failure["status"] == "blocked"
    assert final_failure["parity_passed"] is True
    assert final_failure["run_envelope_status"] == "aborted"
    assert "run_envelope:finalize_failed" in final_failure["blockers"]
    assert final_envelope.aborted == [final_envelope.run_id]


def test_refresh_reports_abort_failure_without_touching_another_run(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    envelope = FakeEnvelope(fail_on="abort")
    summary = refresh.run_refresh(
        run_command=FakeRunner(dev_dir, fail_stage="dependency_preflight"),
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["run_envelope_status"] == "blocked"
    assert summary["run_envelope_cleanup_error"] == "abort_failed"
    assert "run_envelope_cleanup:abort_failed" in summary["blockers"]
    assert envelope.aborted == []


def test_refresh_begin_failure_starts_no_stage_and_aborts_no_other_run(
    tmp_path: Path, monkeypatch
) -> None:
    dev_dir = tmp_path / "runtime" / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    envelope = FakeEnvelope(fail_on="begin")
    runner = FakeRunner(dev_dir)

    summary = refresh.run_refresh(
        run_command=runner,
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["run_id"] is None
    assert summary["run_envelope_error"] == "begin_failed"
    assert envelope.aborted == []
    assert runner.calls == []


def test_refresh_rejects_symlinked_runtime_root_before_begin_or_stage(
    tmp_path: Path, monkeypatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    runtime_link = tmp_path / "runtime-link"
    try:
        runtime_link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    dev_dir = runtime_link / "solteria_helper_dev"
    monkeypatch.setattr(refresh, "DEFAULT_DEV_DIR", dev_dir)
    envelope = FakeEnvelope()
    runner = FakeRunner(dev_dir)

    summary = refresh.run_refresh(
        run_command=runner,
        envelope_backend=envelope,
    )

    assert summary["status"] == "blocked"
    assert summary["run_envelope_error"] == "runtime_root_unsafe"
    assert envelope.begin_calls == 0
    assert envelope.aborted == []
    assert runner.calls == []
    assert not (outside / "solteria_helper_dev").exists()


def test_cli_emits_only_the_sanitized_summary_and_maps_exit_status(
    monkeypatch, capsys
) -> None:
    passed = {
        "schema_version": refresh.SUMMARY_SCHEMA,
        "status": "passed",
        "operator_inputs_ready": False,
        "parity_passed": True,
        "stages": [],
        "blockers": [],
    }
    monkeypatch.setattr(refresh, "run_refresh", lambda: passed)

    assert refresh.main([]) == 0
    assert json.loads(capsys.readouterr().out) == passed

    blocked = {**passed, "status": "blocked", "parity_passed": False}
    monkeypatch.setattr(refresh, "run_refresh", lambda: blocked)
    assert refresh.main([]) == 1
    assert json.loads(capsys.readouterr().out) == blocked
