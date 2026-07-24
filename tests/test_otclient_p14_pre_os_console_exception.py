from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "otclient"
WINDOWS = ROOT / "scripts" / "windows"
STAGE_CONTRACT = DOCS / "P14_STAGE_ONLY_BOOTSTRAP_CONTRACT.md"
RUNBOOK = DOCS / "P14_APPLIANCE_BOOTSTRAP_RUNBOOK.md"
RUNNER_CONTRACT = DOCS / "P14_INDEPENDENT_RUNNER_CONTRACT.md"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pre_os_console_exception_is_fixed_media_only_and_audit_only() -> None:
    source = _source(STAGE_CONTRACT)
    normalized = " ".join(source.split())

    assert "Pre-OS fixed-media console activation exception" in source
    assert "CTOA-P14-Runner-Fresh-20260724" in source
    assert "before Windows PE has started" in source
    assert "local VirtualBox console `Space` **or** `Enter` event" in source
    assert "for each fresh boot attempt" in source
    assert "SHA-256 was checked before the boot attempt" in normalized
    assert "every NIC remains `none`" in source
    assert "shared folders, clipboard, drag and drop, VRDE, USB passthrough" in normalized
    assert "Stop all console input as soon as Windows PE or Windows Setup is visible" in normalized
    assert "pre-os-fixed-media-activation-receipt.json" in source
    assert "ctoa.p14-pre-os-fixed-media-activation.v1" in source
    assert "an operator audit record only" in source
    assert "not an acceptance artifact" in _source(RUNNER_CONTRACT)

    for forbidden in (
        "credentials",
        "guestcontrol",
        "keyboardputscancode",
        "mouseput",
        "sendkeys",
        "RDP",
        "VRDE",
    ):
        assert forbidden in source


def test_exception_does_not_relax_post_bootstrap_input_prohibitions() -> None:
    runbook = _source(RUNBOOK)
    runner_contract = _source(RUNNER_CONTRACT)

    assert "does not authorize input during OOBE, sign-in, staging, baseline" in runbook
    assert "The runner never supplies credentials,\nunlocks Windows, or sends keyboard/mouse input." in runner_contract
    assert "It gives neither the binder nor the runner any\nkeyboard/mouse" in runner_contract

    protected_scripts = (
        "otclient_p14_appliance_bind.ps1",
        "otclient_p14_baseline_capture.ps1",
        "otclient_p14_guest_broker.ps1",
        "otclient_p14_guest_provision.ps1",
        "otclient_p14_stage_bootstrap.ps1",
        "otclient_p14_stage_host.ps1",
        "otclient_p14_vm_capture.ps1",
        "otclient_p14_vm_runner.ps1",
    )
    for script in protected_scripts:
        source = _source(WINDOWS / script).lower()
        for forbidden in ("guestcontrol", "keyboardputscancode", "mouseput", "sendkeys"):
            assert forbidden not in source, f"{script} contains {forbidden}"
