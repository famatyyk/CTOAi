import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCH_JSON = ROOT / ".vscode" / "launch.json"
TASKS_JSON = ROOT / ".vscode" / "tasks.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_mobile_console_launch_uses_loopback_and_env_secrets() -> None:
    payload = _load_json(LAUNCH_JSON)
    launch = next(
        item
        for item in payload["configurations"]
        if item["name"] == "CTOA: Start Mobile Console (dev)"
    )

    assert launch["args"][launch["args"].index("--host") + 1] == "127.0.0.1"
    assert "0.0.0.0" not in launch["args"]
    assert launch["preLaunchTask"] == "CTOA: Preflight Mobile Console Env"
    assert launch["env"] == {
        "CTOA_OWNER_USER": "${env:CTOA_OWNER_USER}",
        "CTOA_OWNER_PASSWORD": "${env:CTOA_OWNER_PASSWORD}",
        "CTOA_OPERATOR_USER": "${env:CTOA_OPERATOR_USER}",
        "CTOA_OPERATOR_PASSWORD": "${env:CTOA_OPERATOR_PASSWORD}",
        "CTOA_MOBILE_TOKEN": "${env:CTOA_MOBILE_TOKEN}",
    }


def test_vscode_configs_do_not_embed_mobile_console_dev_secrets() -> None:
    combined = LAUNCH_JSON.read_text(encoding="utf-8") + TASKS_JSON.read_text(
        encoding="utf-8"
    )

    assert "ctoa2026" not in combined
    assert "dev-token" not in combined
    assert '"CTOA_OWNER_PASSWORD": "cto' not in combined
    assert '"CTOA_OPERATOR_PASSWORD": "cto' not in combined


def test_mobile_console_tasks_use_preflight_and_loopback_bind() -> None:
    payload = _load_json(TASKS_JSON)
    tasks = {item["label"]: item for item in payload["tasks"]}

    dev_task = tasks["CTOA: Start Mobile Console (dev)"]
    assert dev_task["dependsOn"] == ["CTOA: Preflight Mobile Console Env"]
    assert "--host 127.0.0.1" in dev_task["command"]
    assert "--host 0.0.0.0" not in dev_task["command"]

    baseline_task = tasks["CTOA: Start Mobile Console (local baseline)"]
    assert baseline_task["dependsOn"] == ["CTOA: Preflight Mobile Console Env"]
    assert "--host 127.0.0.1" in " ".join(baseline_task["args"])
