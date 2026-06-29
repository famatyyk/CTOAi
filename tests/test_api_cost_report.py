import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "api_cost_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("api_cost_report", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_api_cost_report_handles_missing_runs_dir(tmp_path):
    module = _load_module()

    records = module.load_cost_records(tmp_path / "missing")
    report = module.build_report(records, tmp_path / "missing", anomaly_threshold=0.30)

    assert report["records_seen"] == 0
    assert report["total_tokens"] == 0
    assert report["total_cost_usd"] == 0.0
    assert "evals/runs" in report["recommendations"][0]


def test_api_cost_report_reads_jsonl_usage_and_cost(tmp_path):
    module = _load_module()
    runs_dir = tmp_path / "evals" / "runs"
    runs_dir.mkdir(parents=True)
    run_file = runs_dir / "sample.jsonl"
    run_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "case-1",
                        "component": "prompt-forge",
                        "variant": "baseline",
                        "model": "model-a",
                        "usage": {"input_tokens": 1000, "output_tokens": 250},
                        "cost_usd": 0.03,
                        "created_at": "2026-06-29T08:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "case_id": "case-2",
                        "component": "prompt-forge",
                        "variant": "strict",
                        "model": "model-a",
                        "usage": {"total_tokens": 500},
                        "cost_usd": 0.01,
                        "created_at": "2026-06-29T09:00:00Z",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    records = module.load_cost_records(runs_dir)
    report = module.build_report(records, runs_dir, anomaly_threshold=0.30)

    assert report["records_seen"] == 2
    assert report["records_with_cost"] == 2
    assert report["total_tokens"] == 1750
    assert report["total_cost_usd"] == 0.04
    assert report["by_component"][0]["component"] == "prompt-forge"
    assert report["anomalies"][0]["component"] == "prompt-forge"


def test_api_cost_report_uses_explicit_pricing_json(tmp_path):
    module = _load_module()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "run.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "id": "priced",
                        "component": "api-cost-optimizer",
                        "model": "model-priced",
                        "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pricing = {"model-priced": {"input_per_1m": 2.0, "output_per_1m": 8.0}}

    records = module.load_cost_records(runs_dir, pricing)
    report = module.build_report(records, runs_dir, anomaly_threshold=0.30)

    assert report["records_seen"] == 1
    assert report["records_with_cost"] == 1
    assert report["total_tokens"] == 1_500_000
    assert report["total_cost_usd"] == 6.0
