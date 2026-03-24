import json
from pathlib import Path

from scripts.ops.ctoa_update_gate import run_gate


def test_update_gate_requires_bootstrap_state(tmp_path: Path):
    code, payload = run_gate(tmp_path)
    assert code == 2
    assert payload["status"] == "bootstrap_required"


def test_update_gate_allows_current_bootstrapped_version(tmp_path: Path):
    state = {
        "product_version": "1.1.1",
        "bootstrap_schema_version": 1,
    }
    (tmp_path / "bootstrap-state.json").write_text(json.dumps(state), encoding="utf-8")

    code, payload = run_gate(tmp_path)
    assert code == 0
    assert payload["status"] == "launch_allowed"


def test_update_gate_blocks_outdated_version(tmp_path: Path):
    state = {
        "product_version": "1.0.0",
        "bootstrap_schema_version": 1,
    }
    (tmp_path / "bootstrap-state.json").write_text(json.dumps(state), encoding="utf-8")

    code, payload = run_gate(tmp_path)
    assert code == 4
    assert payload["status"] == "mandatory_update_required"