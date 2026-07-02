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


def test_api_cost_report_includes_eval_artifact_summary(tmp_path):
    module = _load_module()
    dataset_path = tmp_path / "evals" / "azure-activity-agent-eval-dataset.template.jsonl"
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "AZ-001",
                        "category": "rbac_change",
                        "priority": "high",
                        "input": {"operationName": {"value": "Microsoft.Authorization/roleAssignments/write"}},
                        "expected": {"must_include": ["timeline_summary"]},
                    }
                ),
                json.dumps(
                    {
                        "case_id": "AZ-002",
                        "category": "network_delete_failed",
                        "priority": "high",
                        "input": {"operationName": {"value": "Microsoft.Network/networkSecurityGroups/securityRules/delete"}},
                        "expected": {"must_include": ["operation_summary"]},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    prompt_variants_dir = tmp_path / "evals" / "prompt-variants"
    prompt_variants_dir.mkdir(parents=True)
    (prompt_variants_dir / "baseline.md").write_text("# baseline\n", encoding="utf-8")
    (prompt_variants_dir / "strict.md").write_text("# strict\n", encoding="utf-8")

    summary = module.load_eval_artifact_summary(dataset_path, prompt_variants_dir)

    assert summary["dataset_cases"] == 2
    assert summary["prompt_variant_count"] == 2
    assert summary["prompt_variants"] == ["baseline", "strict"]
    assert summary["category_counts"] == {"rbac_change": 1, "network_delete_failed": 1}
    assert summary["priority_counts"] == {"high": 2}


def test_api_cost_report_uses_configured_defaults(tmp_path, monkeypatch):
    dataset_path = tmp_path / "custom" / "dataset.jsonl"
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text(json.dumps({"case_id": "case-1", "category": "custom", "priority": "low"}) + "\n", encoding="utf-8")
    prompt_variants_dir = tmp_path / "custom" / "prompt-variants"
    prompt_variants_dir.mkdir(parents=True)
    (prompt_variants_dir / "variant-a.md").write_text("# variant\n", encoding="utf-8")

    monkeypatch.setenv("CTOA_EVAL_DATASET_PATH", str(dataset_path))
    monkeypatch.setenv("CTOA_PROMPT_VARIANTS_DIR", str(prompt_variants_dir))

    module = _load_module()
    summary = module.load_eval_artifact_summary()

    assert summary["dataset_path"] == str(dataset_path).replace("\\", "/")
    assert summary["dataset_cases"] == 1
    assert summary["prompt_variants_dir"] == str(prompt_variants_dir).replace("\\", "/")
    assert summary["prompt_variant_count"] == 1


def test_api_cost_report_uses_md_path_alias(tmp_path, monkeypatch):
    md_out = tmp_path / "custom" / "runtime" / "api-cost" / "latest.md"
    monkeypatch.setenv("CTOA_API_COST_MD_PATH", str(md_out))
    monkeypatch.delenv("CTOA_API_COST_MD_OUT", raising=False)

    module = _load_module()
    parser = module._build_parser()

    assert parser.parse_args([]).md_out == md_out
