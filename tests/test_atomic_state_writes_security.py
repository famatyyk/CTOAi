import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_api_auth_store_atomic_write_uses_unique_hidden_temp_paths(tmp_path: Path) -> None:
    import api.main as api_main

    out = tmp_path / "auth_store.json"

    api_main._atomic_write_json(out, {"users": {}, "ok": True})

    assert json.loads(out.read_text(encoding="utf-8"))["ok"] is True
    assert not list(tmp_path.glob("*.json.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_api_auth_store_source_rejects_predictable_suffix_temp() -> None:
    source = (ROOT / "api" / "main.py").read_text(encoding="utf-8")

    assert 'path.with_suffix(path.suffix + ".tmp")' not in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(f.fileno())" in source


def test_runner_state_atomic_writes_use_unique_hidden_temp_paths(tmp_path: Path) -> None:
    import runner.runner as runner_mod

    yaml_out = tmp_path / "state.yaml"
    json_out = tmp_path / "summary.json"

    runner_mod.save_yaml(yaml_out, {"status": "ok"})
    runner_mod.save_json(json_out, {"status": "ok"})

    assert yaml.safe_load(yaml_out.read_text(encoding="utf-8"))["status"] == "ok"
    assert json.loads(json_out.read_text(encoding="utf-8"))["status"] == "ok"
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_runner_state_source_rejects_predictable_suffix_temp() -> None:
    source = (ROOT / "runner" / "runner.py").read_text(encoding="utf-8")

    assert 'path.with_suffix(path.suffix + ".tmp")' not in source
    assert "uuid.uuid4().hex" in source
    assert source.count("os.fsync(f.fileno())") >= 2
