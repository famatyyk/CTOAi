import importlib.util
import json
from pathlib import Path


def _load_contract_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "validate_release_artifact_contract.py"
    spec = importlib.util.spec_from_file_location("validate_release_artifact_contract", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_artifact_contract_accepts_committed_sample(monkeypatch, tmp_path):
    module = _load_contract_module()
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "sprint": "041",
                "generated_at": "2026-05-18T00:00:00Z",
                "release_version": "v1.14.0",
                "baseline_version": "v1.13.0",
                "wave_1": {"status": "PASS"},
                "wave_2": {"status": "PASS"},
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CTOA_RELEASE_ARTIFACT_SAMPLE", str(sample))

    assert module.main() == 0


def test_release_artifact_contract_reports_missing_required_keys(monkeypatch, tmp_path, capsys):
    module = _load_contract_module()
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "sprint": "041",
                "generated_at": "2026-05-18T00:00:00Z",
                "release_version": "v1.14.0",
                "wave_1": {"status": "PASS"},
                "wave_2": {"status": "PASS"},
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CTOA_RELEASE_ARTIFACT_SAMPLE", str(sample))

    assert module.main() == 1
    assert "Missing required key: baseline_version" in capsys.readouterr().out

