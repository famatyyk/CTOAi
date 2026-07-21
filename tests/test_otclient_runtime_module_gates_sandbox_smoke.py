from pathlib import Path

from scripts.ops import otclient_runtime_module_gates_sandbox_smoke as smoke


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_runtime_module_gates_sandbox_smoke.py"
WRAPPER = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"


def test_runtime_module_gate_sandbox_smoke_is_fail_closed_and_wired():
    source = SCRIPT.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")

    assert '"sequence": ["conditions", "equipment", "heal_friend"]' in source
    assert '"conditions": "blocked_fail_closed"' in source
    assert '"equipment": "blocked_fail_closed"' in source
    assert '"heal_friend": "blocked_fail_closed"' in source
    assert '"combat": "deferred_high_risk"' in source
    assert '"cavebot": "deferred_high_risk"' in source
    assert '"dispatch_allowed": False' in source
    assert '"runtime_actions": False' in source
    assert '"live_promotion": False' in source
    assert "source_manifest_parity" in source
    assert "outside_protection_zone_confirmed" in source
    assert "outside_pz_fail_closed_enforced" in source
    assert "synthetic_action_bound_acceptance" in source
    assert '"acceptance_ready": False' in source
    assert "action_not_approved_v1" in source
    assert "RuntimeModuleGatesSandboxSmoke" in wrapper
    assert "otclient_runtime_module_gates_sandbox_smoke.py" in wrapper


def test_runtime_module_gate_sandbox_smoke_scopes_probe_to_current_session():
    log_text = "\n".join(
        [
            "old Initialized successfully v2.2.1",
            "old [CTOA-OTC-HELPER] API probe (startup): core[online=yes localPlayer=yes] player[hp=10/10 pz=no]",
            "old [CTOA-OTC-HELPER] Runtime disarmed",
            "new Initialized successfully v2.2.1",
        ]
    )

    session = smoke.current_session(log_text)

    assert session.startswith("Initialized successfully v2.2.1")
    assert smoke.latest_api_probe(session) == ""
    assert smoke.latest_runtime_state(session) == "unknown"


def test_runtime_module_gate_sandbox_smoke_uses_latest_runtime_marker():
    session = "\n".join(
        [
            "Initialized successfully v2.2.1",
            "[CTOA-OTC-HELPER] Runtime armed: module enabled",
            "[CTOA-OTC-HELPER] Runtime disarmed",
        ]
    )
    assert smoke.latest_runtime_state(session) == "disarmed"

    rearmed = session + "\n[CTOA-OTC-HELPER] Runtime armed"
    assert smoke.latest_runtime_state(rearmed) == "armed"


def test_runtime_module_gate_sandbox_smoke_accepts_current_manual_probe():
    session = "\n".join(
        [
            "Initialized successfully v2.2.1",
            "[CTOA-OTC-HELPER] API probe (startup): core[online=no]",
            "[CTOA-OTC-HELPER] API probe (manual): core[online=yes localPlayer=yes] player[hp=10/10 pz=no]",
        ]
    )
    assert "(manual)" in smoke.latest_api_probe(session)
