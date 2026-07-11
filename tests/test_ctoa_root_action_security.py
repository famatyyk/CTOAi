from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_ACTION = ROOT / "scripts" / "ops" / "ctoa-root-action.sh"


def _script_text() -> str:
    return ROOT_ACTION.read_text(encoding="utf-8")


def test_root_action_dashboard_health_uses_private_temp_file() -> None:
    script = _script_text()
    start = script.index("Dashboard health")
    end = script.index("InspectReportEnv")
    block = script[start:end]

    assert "/tmp/ctoa-health.out" not in script
    assert 'health_out="$(mktemp "${TMPDIR:-/tmp}/ctoa-health.XXXXXX")"' in block
    assert "trap 'rm -f \"$health_out\"' EXIT" in block
    assert 'curl -sS -o "$health_out"' in block
    assert 'cat "$health_out"' in block


def test_root_action_keeps_action_allowlist_and_rejects_unknown_actions() -> None:
    script = _script_text()

    assert 'case "$action" in' in script
    for action in (
        "validate-services)",
        "inspect-report-env)",
        "healthcheck-one-shot)",
        "worktree-drycheck)",
        "install-worktree-drycheck-cron)",
    ):
        assert action in script
    assert "Unsupported wrapper action" in script
    assert "exit 64" in script
