import importlib.util
import json
import os
from pathlib import Path


def _load_nightly_stability_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "nightly_stability.py"
    spec = importlib.util.spec_from_file_location("nightly_stability", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nightly_stability_writes_valid_artifact_schema(monkeypatch, tmp_path: Path):
    nightly_stability = _load_nightly_stability_module()
    calls = []

    manifests_dir = tmp_path / "generated" / "manifests"
    ready_run = manifests_dir / "run_ready"
    failed_run = manifests_dir / "run_failed"
    ready_run.mkdir(parents=True, exist_ok=True)
    failed_run.mkdir(parents=True, exist_ok=True)
    (ready_run / "manifest.json").write_text(
        json.dumps({"run_id": "run_ready", "generated": [{"task_id": "SRV1"}], "failed": []}),
        encoding="utf-8",
    )
    (failed_run / "manifest.json").write_text(
        json.dumps({"run_id": "run_failed", "generated": [], "failed": [{"task_id": "SRV2"}]}),
        encoding="utf-8",
    )
    now = int(__import__("time").time())
    os.utime(ready_run / "manifest.json", (now, now))
    os.utime(failed_run / "manifest.json", (now, now))

    def fake_run(cmd: list[str], cwd: Path):
        calls.append((cmd, cwd))
        if "pytest" in cmd:
            return 0, "19 passed in 2.31s\n"
        return 0, "validator ok\n"

    monkeypatch.setattr(nightly_stability, "_run", fake_run)

    out_path = tmp_path / "artifacts" / "nightly.json"
    argv = [
        "nightly_stability.py",
        "--root",
        str(tmp_path),
        "--json-out",
        str(out_path),
        "--sprint",
        "027",
        "--dry-run",
    ]
    monkeypatch.setattr(nightly_stability.sys, "argv", argv)

    rc = nightly_stability.main()
    assert rc == 0
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))

    required_keys = {
        "date",
        "timestamp",
        "tests_passed",
        "tests_failed",
        "validator_status",
        "overall",
        "trend_24h",
        "trend_7d",
        "drift",
        "anomaly",
    }
    assert required_keys.issubset(set(payload.keys()))

    assert isinstance(payload["date"], str)
    assert len(payload["date"]) == 8
    assert payload["date"].isdigit()

    assert isinstance(payload["timestamp"], str)
    assert payload["timestamp"].endswith("Z")

    assert payload["tests_passed"] == 19
    assert payload["tests_failed"] == 0
    assert payload["validator_status"] == "PASS"
    assert payload["overall"] == "PASS"
    assert payload["trend_24h"]["runs_total"] == 2
    assert payload["trend_24h"]["error_count"] == 1
    assert payload["trend_24h"]["dominant_reason_code"] in {"ARTIFACTS_READY", "GENERATION_FAILED"}
    assert payload["trend_7d"]["runs_total"] == 2
    assert "success_rate_delta_7d_vs_24h" in payload["drift"]
    assert payload["anomaly"]["triggered"] is False
    assert payload["anomaly"]["low_sample"] is True
    assert payload["anomaly"]["thresholds"]["min_runs_24h"] == 4

    evidence_index = tmp_path / "runtime" / "evidence" / "sprint-027" / "evidence-index.json"
    assert evidence_index.exists()

    # pytest and sprint validator should both be executed.
    assert len(calls) == 2
