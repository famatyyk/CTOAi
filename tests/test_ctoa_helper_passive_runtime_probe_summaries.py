from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts" / "lua" / "otclient"
HELPER = OTCLIENT / "ctoa_native_helper.lua"
DIAGNOSTICS = OTCLIENT / "ctoa_helper_diagnostics.lua"
TIMER_RUNTIME = OTCLIENT / "ctoa_helper_timer_runtime.lua"
MODULE_CONTRACT = ROOT / "scripts" / "ops" / "otclient_helper_module_contract.py"


def test_vocation_probe_summary_is_owned_by_passive_diagnostics() -> None:
    helper = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    contract = MODULE_CONTRACT.read_text(encoding="utf-8")

    assert "function Diagnostics.vocationProbeText" in diagnostics
    assert '"Vocation probe: raw=" .. tostring(data.raw)' in diagnostics
    assert "owns_vocation_probe_text = true" in diagnostics
    assert '"vocationProbeText"' in contract
    assert 'moduleValue(externalDiagnostics, "vocationProbeText", {' in helper
    assert 'status("Vocation probe: raw="' not in helper


def test_timer_probe_summary_is_owned_by_passive_timer_adapter() -> None:
    helper = HELPER.read_text(encoding="utf-8")
    timer = TIMER_RUNTIME.read_text(encoding="utf-8")
    contract = MODULE_CONTRACT.read_text(encoding="utf-8")

    assert "function TimerRuntime.probeSummary" in timer
    assert 'return "Timer probe: " .. TimerRuntime.summary(plan)' in timer
    assert "owns_probe_summary_text = true" in timer
    assert '"probeSummary"' in contract
    assert 'moduleValue(externalTimerRuntime, "probeSummary", plan)' in helper
    assert 'status("Timer probe: "' not in helper


def test_probe_observations_and_runtime_mutation_remain_shell_owned() -> None:
    helper = HELPER.read_text(encoding="utf-8")
    diagnostics = DIAGNOSTICS.read_text(encoding="utf-8")
    timer = TIMER_RUNTIME.read_text(encoding="utf-8")

    profile_probe = helper[
        helper.index("local function loadProfile") : helper.index(
            "local function applySafeBootRuntimeGuard"
        )
    ]
    timer_probe = helper[
        helper.index('elseif action == "timer_probe"') : helper.index(
            'elseif action == "diag_export"'
        )
    ]

    assert "g_game.getLocalPlayer" in profile_probe
    assert "Helper.vocation_id =" in profile_probe
    assert "HELPER_CONFIG.vocation =" in profile_probe
    assert "g_game.isOnline" in timer_probe
    assert "g_clock.millis" in timer_probe
    assert 'moduleValue(externalTimerRuntime, "plan"' in timer_probe
    assert "g_game" not in diagnostics
    assert "g_game" not in timer
    assert "castSpell(" not in timer
    assert "autoWalk(" not in timer
