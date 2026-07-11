import json
import sqlite3
from pathlib import Path

import pytest

from scripts.ops.ctoa_product_bootstrap import bootstrap


ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_writes_local_json_and_sqlite_state(tmp_path: Path):
    result = bootstrap(
        state_dir=tmp_path,
        package_tier="pro",
        profile_name="customer-a",
        operator_handle="owner-a",
        deployment_mode="self-hosted",
        update_channel="stable",
    )

    assert result["ok"] is True

    user_config = json.loads((tmp_path / "user-config.json").read_text(encoding="utf-8"))
    bootstrap_state = json.loads((tmp_path / "bootstrap-state.json").read_text(encoding="utf-8"))

    assert user_config["profile_name"] == "customer-a"
    assert user_config["operator_handle"] == "owner-a"
    assert user_config["package_tier"] == "pro"
    assert user_config["features"]["mobile_console"] is True
    assert bootstrap_state["product_version"] == "1.1.1"
    assert bootstrap_state["bootstrap_schema_version"] == 1
    assert bootstrap_state["package_tier"] == "pro"

    conn = sqlite3.connect(tmp_path / "toolkit-state.db")
    try:
        config_row = conn.execute("SELECT profile_name, operator_handle FROM bootstrap_config").fetchone()
        state_row = conn.execute("SELECT product_version, bootstrap_schema_version FROM bootstrap_state").fetchone()
    finally:
        conn.close()

    assert config_row == ("customer-a", "owner-a")
    assert state_row == ("1.1.1", 1)

    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def _make_file_symlink(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")


def test_bootstrap_replaces_symlinked_local_json_without_touching_target(
    tmp_path: Path,
):
    outside = tmp_path / "outside-user-config.json"
    outside.write_text('{"profile_name": "outside"}\n', encoding="utf-8")
    _make_file_symlink(tmp_path / "user-config.json", outside)

    result = bootstrap(
        state_dir=tmp_path,
        package_tier="pro",
        profile_name="customer-a",
        operator_handle="owner-a",
        deployment_mode="self-hosted",
        update_channel="stable",
    )

    assert result["ok"] is True
    assert json.loads(outside.read_text(encoding="utf-8"))["profile_name"] == "outside"
    assert not (tmp_path / "user-config.json").is_symlink()
    user_config = json.loads((tmp_path / "user-config.json").read_text(encoding="utf-8"))
    assert user_config["profile_name"] == "customer-a"


def test_product_bootstrap_source_uses_atomic_state_writer() -> None:
    source = (ROOT / "scripts" / "ops" / "ctoa_product_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "user_config_path.write_text" not in source
    assert "bootstrap_state_path.write_text" not in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source
