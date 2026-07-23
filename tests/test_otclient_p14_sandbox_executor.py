from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "otclient_p14_sandbox_executor.py"
SPEC = importlib.util.spec_from_file_location("otclient_p14_sandbox_executor", SCRIPT)
assert SPEC and SPEC.loader
p14 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p14)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_package(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    source = tmp_path / "staged-package"
    files = {
        "ctoa_project_loader.lua": b"return { loader = 'p14' }\n",
        "mods/ctoa_chooser/ctoa_chooser.otmod": b"Module\n  name: chooser\n",
        "mods/ctoa_chooser/ctoa_chooser_loader.lua": b"return { chooser = true }\n",
        "mods/ctoa_otclient/ctoa_otclient.otmod": b"Module\n  version: v2.4.1\n",
        "mods/ctoa_otclient/ctoa_otclient_loader.lua": b"return { ui_only = true }\n",
    }
    manifest_files = []
    for relative, raw in sorted(files.items()):
        path = source.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        manifest_files.append(
            {"path": relative, "bytes": len(raw), "sha256": _sha256(raw)}
        )
    return source, {
        "schema_version": "ctoa.p14-helper-source-manifest.v1",
        "helper_version": "v2.4.1",
        "file_count": len(manifest_files),
        "files": manifest_files,
    }


def test_rehearsal_physically_changes_then_restores_full_copy(tmp_path: Path) -> None:
    source, manifest = _source_package(tmp_path)
    runs = tmp_path / "runs"
    before = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }

    prepared = p14.prepare_sandbox(
        runs_root=runs,
        run_id="a" * 16,
        source_root=source,
        source_manifest=manifest,
    )
    sandbox = runs / ("a" * 16) / "sandbox"
    assert prepared["file_count"] == len(before)
    expected_foundation_baseline = p14.canonical_sha256(
        {
            "schema_version": "ctoa.p14-rollback-baseline.v1",
            "helper_version": manifest["helper_version"],
            "file_count": manifest["file_count"],
            "files": manifest["files"],
        }
    )
    assert prepared["baseline_manifest_sha256"] == expected_foundation_baseline
    assert (
        prepared["sandbox_baseline_manifest_sha256"]
        != prepared["baseline_manifest_sha256"]
    )
    assert not (sandbox / p14.CANARY_MARKER_RELATIVE_PATH).exists()
    for relative, raw in before.items():
        copied = sandbox.joinpath(*relative.split("/"))
        assert copied.read_bytes() == raw
        assert copied.stat().st_nlink == 1

    canary = p14.apply_canary(runs_root=runs, run_id="a" * 16)
    assert canary["changed_file_count"] == 1
    assert canary["changed_manifest_sha256"] != canary["baseline_manifest_sha256"]
    assert (sandbox / p14.CANARY_MARKER_RELATIVE_PATH).is_file()
    health = p14.canary_health_check(runs_root=runs, run_id="a" * 16)
    assert health["status"] == "passed"

    rollback = p14.apply_rollback(runs_root=runs, run_id="a" * 16)
    assert rollback["restored_manifest_sha256"] == rollback["baseline_manifest_sha256"]
    assert not (sandbox / p14.CANARY_MARKER_RELATIVE_PATH).exists()
    for relative, raw in before.items():
        assert sandbox.joinpath(*relative.split("/")).read_bytes() == raw
        assert source.joinpath(*relative.split("/")).read_bytes() == raw


def test_single_call_rehearsal_returns_exact_transition(tmp_path: Path) -> None:
    source, manifest = _source_package(tmp_path)

    result = p14.run_sandbox_rehearsal(
        runs_root=tmp_path / "runs",
        run_id="b" * 16,
        source_root=source,
        source_manifest=manifest,
    )

    assert result["status"] == "passed"
    assert result["changed_file_count"] == 1
    assert result["baseline_manifest_sha256"] != result["changed_manifest_sha256"]
    assert result["restored_manifest_sha256"] == result["baseline_manifest_sha256"]
    assert result["canary_health"] == "passed"
    assert result["rollback"] == "rollback_verified"


def test_fixed_cli_writes_compact_execution_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, manifest = _source_package(tmp_path)
    manifest_path = tmp_path / "staged-helper-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(p14, "DEFAULT_RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(p14, "DEFAULT_EVIDENCE_ROOT", tmp_path / "evidence")
    monkeypatch.setattr(p14, "DEFAULT_STAGED_PACKAGE_ROOT", source)
    monkeypatch.setattr(p14, "DEFAULT_SOURCE_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "run", "--run-id", "1" * 16])

    assert p14.main() == 0
    result = json.loads(capsys.readouterr().out)
    receipt = tmp_path / "evidence" / ("1" * 16) / "sandbox-execution.json"
    assert result["status"] == "passed"
    assert json.loads(receipt.read_text(encoding="utf-8")) == result

    with pytest.raises(p14.SandboxError, match="evidence_run_already_exists"):
        p14.write_execution_evidence(
            evidence_root=tmp_path / "evidence", run_id="1" * 16, result=result
        )


def test_broker_api_uses_only_fixed_constants(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, manifest = _source_package(tmp_path)
    manifest_path = tmp_path / "staged-helper-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(p14, "DEFAULT_RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(p14, "DEFAULT_EVIDENCE_ROOT", tmp_path / "evidence")
    monkeypatch.setattr(p14, "DEFAULT_STAGED_PACKAGE_ROOT", source)
    monkeypatch.setattr(p14, "DEFAULT_SOURCE_MANIFEST_PATH", manifest_path)

    result = p14.run(run_id="2" * 16)

    assert result["status"] == "passed"
    assert (tmp_path / "evidence" / ("2" * 16) / "sandbox-execution.json").is_file()


def test_one_time_bundle_stage_derives_only_the_tracked_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle = tmp_path / "bundle"
    monkeypatch.setattr(p14, "DEFAULT_STAGED_PACKAGE_ROOT", bundle)
    monkeypatch.setattr(p14, "DEFAULT_SOURCE_MANIFEST_PATH", bundle / "helper-manifest.json")
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        result = p14.stage_fixed_bundle()
    finally:
        sys.path.pop(0)

    manifest = json.loads((bundle / "helper-manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "staged"
    assert result["helper_manifest_sha256"] == p14.canonical_sha256(manifest)
    assert manifest["file_count"] == len(manifest["files"])
    assert (bundle / "ctoa_project_loader.lua").is_file()
    with pytest.raises(p14.SandboxError, match="bundle_root_not_empty"):
        p14.stage_fixed_bundle()


def test_rejects_unsafe_run_id_manifest_path_and_source_drift(tmp_path: Path) -> None:
    source, manifest = _source_package(tmp_path)
    with pytest.raises(p14.SandboxError, match="run_id_invalid"):
        p14.prepare_sandbox(
            runs_root=tmp_path / "runs",
            run_id="../not-a-run",
            source_root=source,
            source_manifest=manifest,
        )

    unsafe = json.loads(json.dumps(manifest))
    unsafe["files"][0]["path"] = "mods/ctoa_otclient/../../escape.lua"
    with pytest.raises(p14.SandboxError, match="helper_path_invalid"):
        p14.prepare_sandbox(
            runs_root=tmp_path / "runs",
            run_id="c" * 16,
            source_root=source,
            source_manifest=unsafe,
        )

    drifted = json.loads(json.dumps(manifest))
    drifted["files"][0]["sha256"] = "0" * 64
    with pytest.raises(p14.SandboxError, match="source_manifest_binding_invalid"):
        p14.prepare_sandbox(
            runs_root=tmp_path / "runs",
            run_id="d" * 16,
            source_root=source,
            source_manifest=drifted,
        )


def test_rejects_hardlinked_source_file(tmp_path: Path) -> None:
    source, manifest = _source_package(tmp_path)
    target = source / "mods" / "ctoa_otclient" / "ctoa_otclient_loader.lua"
    linked = source / "mods" / "ctoa_otclient" / "linked-copy.lua"
    try:
        os.link(target, linked)
    except OSError as exc:
        pytest.skip(f"hardlinks unavailable: {exc}")

    with pytest.raises(p14.SandboxError, match="hardlink_rejected"):
        p14.prepare_sandbox(
            runs_root=tmp_path / "runs",
            run_id="e" * 16,
            source_root=source,
            source_manifest=manifest,
        )


def test_rejects_reparse_source_and_sandbox_drift_before_rollback(
    tmp_path: Path,
) -> None:
    source, manifest = _source_package(tmp_path)
    source_file = source / "mods" / "ctoa_otclient" / "ctoa_otclient_loader.lua"
    backing = source / "mods" / "ctoa_otclient" / "ctoa_otclient_loader.real.lua"
    source_file.replace(backing)
    try:
        os.symlink(backing, source_file)
    except OSError:
        backing.replace(source_file)
    else:
        with pytest.raises(p14.SandboxError, match="reparse_point_rejected"):
            p14.prepare_sandbox(
                runs_root=tmp_path / "reparse-runs",
                run_id="f" * 16,
                source_root=source,
                source_manifest=manifest,
            )
        source_file.unlink()
        backing.replace(source_file)

    runs = tmp_path / "runs"
    p14.prepare_sandbox(
        runs_root=runs,
        run_id="f" * 16,
        source_root=source,
        source_manifest=manifest,
    )
    p14.apply_canary(runs_root=runs, run_id="f" * 16)
    sandbox = runs / ("f" * 16) / "sandbox"
    unexpected = sandbox / "unexpected.txt"
    unexpected.write_text("drift", encoding="utf-8")

    with pytest.raises(p14.SandboxError, match="sandbox_manifest_path_set_invalid"):
        p14.apply_rollback(runs_root=runs, run_id="f" * 16)
    assert (sandbox / p14.CANARY_MARKER_RELATIVE_PATH).exists()
    unexpected.unlink()
    rollback = p14.apply_rollback(runs_root=runs, run_id="f" * 16)
    assert rollback["status"] == "rollback_verified"


def test_rejects_a_modified_baseline_file_after_canary(tmp_path: Path) -> None:
    source, manifest = _source_package(tmp_path)
    runs = tmp_path / "runs"
    run_id = "9" * 16
    p14.prepare_sandbox(
        runs_root=runs,
        run_id=run_id,
        source_root=source,
        source_manifest=manifest,
    )
    p14.apply_canary(runs_root=runs, run_id=run_id)
    sandbox_file = (
        runs
        / run_id
        / "sandbox"
        / "mods"
        / "ctoa_otclient"
        / "ctoa_otclient_loader.lua"
    )
    sandbox_file.write_bytes(b"return { unsafe = true }\n")

    with pytest.raises(p14.SandboxError, match="sandbox_manifest_drift"):
        p14.canary_health_check(runs_root=runs, run_id=run_id)


def test_cli_has_no_arbitrary_command_promotion_or_client_path_surface() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "shell=True" not in source
    assert "--source-root" not in source
    assert "--client" not in source
    assert "--command" not in source
    assert "promote" not in source.lower()
    assert '"run"' in source
