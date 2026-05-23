from pathlib import Path


def test_phase5_incident_runbook_exists_and_has_core_sections():
    runbook = Path(__file__).resolve().parents[1] / "docs" / "runbook-phase5-alerts-incident.md"
    assert runbook.exists()
    content = runbook.read_text(encoding="utf-8")
    assert "# Phase-5 Alerts Incident Runbook" in content
    assert "## Trigger" in content
    assert "## Corrective Actions" in content
    assert "## Exit Criteria" in content


def test_phase5_scheduler_scripts_exist_and_reference_strict_sync_flow():
    root = Path(__file__).resolve().parents[1]
    runner = root / "scripts" / "ops" / "run-phase5-morning-sync.ps1"
    installer = root / "scripts" / "ops" / "install-phase5-morning-sync-task.ps1"
    remover = root / "scripts" / "ops" / "remove-phase5-morning-sync-task.ps1"

    assert runner.exists()
    assert installer.exists()
    assert remover.exists()

    runner_content = runner.read_text(encoding="utf-8")
    installer_content = installer.read_text(encoding="utf-8")
    remover_content = remover.read_text(encoding="utf-8")

    assert "phase5_nightly_sync.py" in runner_content
    assert "--require-complete --auto-close-step9" in runner_content
    assert "schtasks /Create" in installer_content
    assert "CTOA-Phase5-MorningSync" in installer_content
    assert "schtasks /Delete" in remover_content


def test_vscode_tasks_include_phase5_scheduler_install_remove_entries():
    tasks = Path(__file__).resolve().parents[1] / ".vscode" / "tasks.json"
    content = tasks.read_text(encoding="utf-8")

    assert '"label": "CTOA: Install Phase-5 Morning Sync Task"' in content
    assert '"label": "CTOA: Remove Phase-5 Morning Sync Task"' in content
