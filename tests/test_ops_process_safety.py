from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_smoke_must_pass_resolves_executable_before_launch(monkeypatch):
    module = _load_module("smoke_must_pass", "scripts/ops/smoke_must_pass.py")
    calls: dict[str, object] = {}

    def fake_resolve_executable(name: str, **_kwargs):
        calls["resolved"] = name
        return "/trusted/python"

    def fake_run(command: list[str], **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        module.process_safety, "resolve_executable", fake_resolve_executable
    )
    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    ok, result = module.run_step("unit", ["python", "-m", "pytest"])

    assert ok is True
    assert result["status"] == "pass"
    assert calls["resolved"] == "python"
    assert calls["command"] == ["/trusted/python", "-m", "pytest"]
    assert calls["kwargs"]["check"] is False


def test_run_validator_preflight_uses_resolved_python(monkeypatch, tmp_path: Path):
    module = _load_module(
        "run_validator_with_preflight", "scripts/ops/run_validator_with_preflight.py"
    )
    validator = tmp_path / "validator.py"
    validator.write_text("print('ok')\n", encoding="utf-8")
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        module.process_safety, "resolve_python", lambda: "/trusted/python"
    )

    def fake_run(command: list[str]):
        calls["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["run_validator_with_preflight.py", str(validator), "--flag"],
    )

    assert module.main() == 0
    assert calls["command"] == ["/trusted/python", str(validator), "--flag"]


def test_nightly_stability_run_resolves_executable_before_launch(
    monkeypatch, tmp_path: Path
):
    module = _load_module("nightly_stability", "scripts/ops/nightly_stability.py")
    calls: dict[str, object] = {}

    def fake_resolve_executable(name: str, **_kwargs):
        calls["resolved"] = name
        return "/trusted/python"

    def fake_run(command: list[str], **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(
        module.process_safety, "resolve_executable", fake_resolve_executable
    )
    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    code, output = module._run(["python", "-m", "pytest"], cwd=tmp_path)

    assert code == 0
    assert output == "ok\n"
    assert calls["resolved"] == "python"
    assert calls["command"] == ["/trusted/python", "-m", "pytest"]
    assert calls["kwargs"]["cwd"] == tmp_path
    assert calls["kwargs"]["capture_output"] is True
    assert calls["kwargs"]["text"] is True


def test_sprint_validator_run_resolves_executable_before_launch(
    monkeypatch, tmp_path: Path
):
    module = _load_module("sprint041_validate", "scripts/ops/sprint041_validate.py")
    calls: dict[str, object] = {}

    def fake_resolve_executable(name: str, **_kwargs):
        calls["resolved"] = name
        return "/trusted/python"

    def fake_run(command: list[str], **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(
        module.process_safety, "resolve_executable", fake_resolve_executable
    )
    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    code, output = module._run(["python", "-m", "pytest"], cwd=tmp_path)

    assert code == 0
    assert output == "ok\n"
    assert calls["resolved"] == "python"
    assert calls["command"] == ["/trusted/python", "-m", "pytest"]
    assert calls["kwargs"]["cwd"] == tmp_path
    assert calls["kwargs"]["capture_output"] is True
    assert calls["kwargs"]["text"] is True


def test_late_sprint_validator_quality_check_uses_trusted_runner(monkeypatch):
    module = _load_module("sprint070_validate", "scripts/ops/sprint070_validate.py")
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        module.process_safety, "resolve_python", lambda: "/trusted/python"
    )

    def fake_run(command: list[str], **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="passed\n", stderr="")

    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    result = module._check_quality(run_tests=True)

    assert result["ok"] is True
    assert calls["command"] == [
        "/trusted/python",
        "-m",
        "pytest",
        "tests/test_repo_cleanup_waves_contract.py",
        "-q",
    ]
    assert calls["kwargs"]["capture_output"] is True
    assert calls["kwargs"]["text"] is True


def test_rosetta_python_assembler_uses_resolved_python(monkeypatch, tmp_path: Path):
    module = _load_module("rosetta_bundle", "scripts/ops/rosetta_bundle.py")
    script = tmp_path / "assembler.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr(
        module.process_safety, "resolve_python", lambda: "/trusted/python"
    )

    assert module._resolve_assembler(str(script)) == ["/trusted/python", str(script)]


def test_kv_attach_first_hit_launches_target_through_process_safety():
    source = (ROOT / "scripts/ops/kv_attach_first_hit.py").read_text(encoding="utf-8")

    assert "process_safety.start_trusted" in source
    assert "import subprocess" not in source


def test_x64dbg_dynamic_pass_uses_trusted_launchers():
    source = (ROOT / "scripts/ops/run-x64dbg-enc3-dynamic-pass.py").read_text(
        encoding="utf-8"
    )

    assert "process_safety.start_trusted" in source
    assert "process_safety.run_trusted" in source
    assert "process_safety.resolve_executable" in source
    assert "import subprocess" not in source


def test_executor_drift_checker_generator_uses_process_safety(
    monkeypatch, tmp_path: Path
):
    from runner.agents import executor as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "runner").mkdir()

    module.TrackCAgent.create_drift_checker()

    source = (tmp_path / "runner" / "drift_checker.py").read_text(encoding="utf-8")
    assert "from runner import process_safety" in source
    assert 'process_safety.resolve_executable("systemctl")' in source
    assert "process_safety.run_trusted" in source
    assert "subprocess.run" not in source
    assert "import subprocess" not in source


def test_executor_doc_generators_write_timestamped_files(monkeypatch, tmp_path: Path):
    from runner.agents import executor as module

    monkeypatch.setattr(module, "ROOT", tmp_path)

    module.TrackAAgent.create_runbook_disk_emergency()
    module.TrackAAgent.create_validation_checklist()

    runbook = (tmp_path / "docs" / "runbook-disk-emergency.md").read_text(
        encoding="utf-8"
    )
    checklist = (tmp_path / "docs" / "VALIDATION_CHECKLIST.md").read_text(
        encoding="utf-8"
    )
    assert "{timestamp}" not in runbook
    assert "{timestamp}" not in checklist
    assert "Last Updated:" in runbook
    assert "Last Updated:" in checklist


def test_activation_agent_sync_hook_uses_resolved_python(monkeypatch, tmp_path: Path):
    module = _load_module("activation_agent", "runner/agents/activation_agent.py")
    hook = tmp_path / "sync-live-targets.py"
    source = tmp_path / "live-targets"
    target = tmp_path / "bot-live"
    hook.write_text("print('ok')\n", encoding="utf-8")
    calls: dict[str, object] = {}

    monkeypatch.setattr(module, "AUTO_DEPLOY", True)
    monkeypatch.setattr(module, "SYNC_HOOK", hook)
    monkeypatch.setattr(module, "LIVE_TARGETS_DIR", source)
    monkeypatch.setattr(module, "BOT_LIVE_ROOT", target)
    monkeypatch.setattr(
        module.process_safety, "resolve_python", lambda: "/trusted/python"
    )

    def fake_run(command: list[str], **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout='{"ok": true}', stderr="")

    monkeypatch.setattr(module.process_safety, "run_trusted", fake_run)

    result = module._run_sync_hook()

    assert result["ok"] is True
    assert result["report"] == {"ok": True}
    assert calls["command"] == [
        "/trusted/python",
        str(hook),
        "--source",
        str(source),
        "--target",
        str(target),
    ]
    assert calls["kwargs"]["timeout"] == 120
    assert calls["kwargs"]["check"] is False
