import json
from pathlib import Path

import pytest

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


def test_update_gate_rejects_invalid_bootstrap_json_without_echoing_content(
    tmp_path: Path,
):
    (tmp_path / "bootstrap-state.json").write_text(
        "{ token=secret-token-value",
        encoding="utf-8",
    )

    code, payload = run_gate(tmp_path)

    assert code == 6
    assert payload["status"] == "invalid_bootstrap_state"
    assert payload["reason"] == "invalid_json"
    assert "secret-token-value" not in str(payload)


def test_update_gate_rejects_oversized_bootstrap_state(tmp_path: Path):
    (tmp_path / "bootstrap-state.json").write_text(
        '{"product_version":"' + ("1" * 50_100) + '"}',
        encoding="utf-8",
    )

    code, payload = run_gate(tmp_path)

    assert code == 6
    assert payload["status"] == "invalid_bootstrap_state"
    assert payload["reason"] == "state_too_large"


def test_update_gate_rejects_invalid_version_or_schema(tmp_path: Path):
    state = {
        "product_version": "1.1.1",
        "bootstrap_schema_version": "not-an-int",
    }
    (tmp_path / "bootstrap-state.json").write_text(json.dumps(state), encoding="utf-8")

    code, payload = run_gate(tmp_path)

    assert code == 6
    assert payload["status"] == "invalid_bootstrap_state"
    assert payload["reason"] == "invalid_version_or_schema"


def test_update_gate_rejects_symlinked_bootstrap_state_before_read(tmp_path: Path):
    outside = tmp_path / "outside-bootstrap-state.json"
    outside.write_text(
        json.dumps({"product_version": "1.1.1", "bootstrap_schema_version": 1}),
        encoding="utf-8",
    )
    try:
        (tmp_path / "bootstrap-state.json").symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    code, payload = run_gate(tmp_path)

    assert code == 6
    assert payload["status"] == "invalid_bootstrap_state"
    assert payload["reason"] == "symlinked_state"
