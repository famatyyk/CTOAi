from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "deploy" / "vps" / "wrappers" / "ctoa-root-action.sh"


def _script_text() -> str:
    return WRAPPER.read_text(encoding="utf-8")


def test_deploy_root_action_dashboard_health_uses_private_temp_file() -> None:
    script = _script_text()
    start = script.index("PrintDashboardHealth()")
    end = script.index("case \"$action\" in")
    helper = script[start:end]

    assert "/tmp/ctoa-health.out" not in script
    assert 'health_out="$(mktemp "${TMPDIR:-/tmp}/ctoa-health.XXXXXX")"' in helper
    assert 'cleanup_files+=("$health_out")' in helper
    assert "trap cleanup EXIT" in script
    assert 'curl -sS -o "$health_out"' in helper
    assert 'cat "$health_out"' in helper


def test_deploy_root_action_reuses_dashboard_health_helper() -> None:
    script = _script_text()

    assert script.count("PrintDashboardHealth") == 3
    assert "dashboard-snapshot)" in script
    assert "healthcheck-one-shot)" in script
    assert "Unsupported wrapper action" in script
