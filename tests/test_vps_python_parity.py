import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_ENV_SURFACE = {
    "CTOA_RELEASES_DIR": ("releases/evidence", "/opt/ctoa/releases/evidence"),
    "CTOA_REPO_HYGIENE_PATH": (
        "runtime/repo-hygiene/local-pr-quality.json",
        "/opt/ctoa/runtime/repo-hygiene/local-pr-quality.json",
    ),
    "CTOA_API_COST_RUNS_DIR": ("evals/runs", "/opt/ctoa/evals/runs"),
    "CTOA_API_COST_REPORT_PATH": ("runtime/api-cost/latest.json", "/opt/ctoa/runtime/api-cost/latest.json"),
    "CTOA_API_COST_JSON_OUT": ("runtime/api-cost/latest.json", "/opt/ctoa/runtime/api-cost/latest.json"),
    "CTOA_API_COST_MD_OUT": ("runtime/api-cost/latest.md", "/opt/ctoa/runtime/api-cost/latest.md"),
    "CTOA_API_COST_MD_PATH": ("runtime/api-cost/latest.md", "/opt/ctoa/runtime/api-cost/latest.md"),
    "CTOA_EVAL_DATASET_PATH": (
        "evals/azure-activity-agent-eval-dataset.template.jsonl",
        "/opt/ctoa/evals/azure-activity-agent-eval-dataset.template.jsonl",
    ),
    "CTOA_PROMPT_VARIANTS_DIR": ("evals/prompt-variants", "/opt/ctoa/evals/prompt-variants"),
    "CTOA_ACTION_AUDIT_PATH": (
        "runtime/control-center/action-audit.jsonl",
        "/opt/ctoa/runtime/control-center/action-audit.jsonl",
    ),
    "CTOA_EVIDENCE_JSON_PATH": ("runtime/evidence/latest.json", "/opt/ctoa/runtime/evidence/latest.json"),
    "CTOA_EVIDENCE_MD_PATH": ("runtime/evidence/latest.md", "/opt/ctoa/runtime/evidence/latest.md"),
}

CONTROL_CENTER_EVIDENCE_ENV_NAMES = {
    "CTOA_RELEASES_DIR",
    "CTOA_REPO_HYGIENE_PATH",
    "CTOA_API_COST_REPORT_PATH",
    "CTOA_API_COST_MD_OUT",
    "CTOA_API_COST_MD_PATH",
    "CTOA_EVAL_DATASET_PATH",
    "CTOA_PROMPT_VARIANTS_DIR",
    "CTOA_ACTION_AUDIT_PATH",
    "CTOA_EVIDENCE_JSON_PATH",
    "CTOA_EVIDENCE_MD_PATH",
}


def test_control_center_launcher_uses_repo_local_python():
    text = (ROOT / "scripts" / "ops" / "launch_kamil_client_macro_studio.ps1").read_text(encoding="utf-8")

    assert "function Get-PythonExe" in text
    assert ".venv\\Scripts\\python.exe" in text
    assert "Start-Process -FilePath 'python'" not in text


def test_vps_systemd_services_use_repo_local_python():
    runner = (ROOT / "deploy" / "vps" / "systemd" / "ctoa-runner.service").read_text(encoding="utf-8")
    report = (ROOT / "deploy" / "vps" / "systemd" / "ctoa-report.service").read_text(encoding="utf-8")
    lab_runner = (ROOT / "deploy" / "vps" / "systemd" / "ctoa-lab-runner.service").read_text(encoding="utf-8")

    for service_text in (runner, report, lab_runner):
        assert "/opt/ctoa/.venv/bin/python3" in service_text
        assert "/usr/bin/python3" not in service_text


def test_ctoa_vps_script_pins_publish_and_validation_to_venv_python():
    text = (ROOT / "scripts" / "ops" / "ctoa-vps.ps1").read_text(encoding="utf-8")

    assert "/opt/ctoa/.venv/bin/python3 runner/runner.py report --publish" in text
    assert "/opt/ctoa/.venv/bin/python3 scripts/ops/gs-api-validator.py" in text


def test_control_center_evidence_env_surface_stays_in_sync():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    vps_setup = (ROOT / "deploy" / "vps" / "SETUP.md").read_text(encoding="utf-8")
    ctoa_vps = (ROOT / "scripts" / "ops" / "ctoa-vps.ps1").read_text(encoding="utf-8")
    control_center_config = (ROOT / "web" / "src" / "lib" / "controlCenterEvidenceConfig.ts").read_text(encoding="utf-8")

    for env_name, (local_value, vps_value) in EVIDENCE_ENV_SURFACE.items():
        assert f"{env_name}={local_value}" in env_example
        assert f"{env_name}={vps_value}" in vps_setup
        assert f"{env_name} {vps_value}" in ctoa_vps or f"{env_name}={vps_value}" in ctoa_vps

    for env_name in CONTROL_CENTER_EVIDENCE_ENV_NAMES:
        assert env_name in control_center_config

    assert 'configuredPathFrom(["CTOA_API_COST_MD_OUT", "CTOA_API_COST_MD_PATH"]' in control_center_config
    assert "CTOA_RELEASES_DIR=/opt/ctoa/releases' " not in ctoa_vps
    assert "CTOA_RELEASES_DIR=/opt/ctoa/releases\n" not in ctoa_vps


def test_operator_next_command_is_visible_in_cli_docs_and_dictionary():
    cli = (ROOT / "ctoa.ps1").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "CTOA_CLI.md").read_text(encoding="utf-8")
    dictionary = json.loads((ROOT / "schemas" / "ctoa-command-dictionary.json").read_text(encoding="utf-8"))

    commands = {entry["command"]: entry for entry in dictionary["commands"]}

    assert '"next" { Show-Next; break }' in cli
    assert '"nx" { Show-Next; break }' in cli
    assert "`next` (`nx`)" in docs
    assert ".\\ctoa.ps1 next" in docs
    assert commands["next"]["aliases"] == ["nx"]
    assert "recommended next step" in commands["next"]["description"]


def test_control_center_open_command_is_visible_in_cli_docs_and_dictionary():
    cli = (ROOT / "ctoa.ps1").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "CTOA_CLI.md").read_text(encoding="utf-8")
    dictionary = json.loads((ROOT / "schemas" / "ctoa-command-dictionary.json").read_text(encoding="utf-8"))

    commands = {entry["command"]: entry for entry in dictionary["commands"]}

    assert "function Open-ControlCenter" in cli
    assert "function Get-NpmExe" in cli
    assert 'foreach ($name in @("npm.cmd", "npm"))' in cli
    assert "Start-Process -FilePath $npm" in cli
    assert '"run", "dev"' in cli
    assert '"cc" { Open-ControlCenter; break }' in cli
    assert '"control-center" { Open-ControlCenter; break }' in cli
    assert "`cc` (`control-center`)" in docs
    assert ".\\ctoa.ps1 cc" in docs
    assert commands["cc"]["aliases"] == ["control-center"]
    assert "start web dev if needed" in commands["cc"]["description"]
