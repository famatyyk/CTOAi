from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_recovery_bridge_sandbox_smoke.py"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_recovery_bridge_sandbox_smoke_is_bounded_and_wired():
    source = SCRIPT.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert "ctoa.recovery-bridge-sandbox-smoke.v1" in source
    assert '"runtime_actions": False' in source
    assert '"live_promotion": False' in source
    assert "executor_invoked" in source
    assert "Loaded: ctoa_helper_recovery_bridge" in source
    assert "RecoveryBridgeSandboxSmoke" in wrapper
    assert "otclient_recovery_bridge_sandbox_smoke.py" in wrapper
