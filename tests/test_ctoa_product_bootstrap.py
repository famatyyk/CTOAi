import json
import sqlite3
from pathlib import Path

from scripts.ops.ctoa_product_bootstrap import bootstrap


def test_bootstrap_writes_local_json_and_sqlite_state(tmp_path: Path):
    result = bootstrap(
        state_dir=tmp_path,
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
    assert bootstrap_state["product_version"] == "1.1.1"
    assert bootstrap_state["bootstrap_schema_version"] == 1

    conn = sqlite3.connect(tmp_path / "toolkit-state.db")
    try:
        config_row = conn.execute("SELECT profile_name, operator_handle FROM bootstrap_config").fetchone()
        state_row = conn.execute("SELECT product_version, bootstrap_schema_version FROM bootstrap_state").fetchone()
    finally:
        conn.close()

    assert config_row == ("customer-a", "owner-a")
    assert state_row == ("1.1.1", 1)