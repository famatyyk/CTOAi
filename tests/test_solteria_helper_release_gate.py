import json
import hashlib
import os
from pathlib import Path

from scripts.ops import solteria_helper_release_gate as gate


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_release_gate_atomic_json_write_leaves_complete_artifact(tmp_path: Path):
    out = tmp_path / "release_gate.json"

    gate.write_json_atomic(out, {"status": "blocked", "gates": [{"name": "SmokeAttachAll"}]})

    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "blocked"
    assert list(tmp_path.glob(".*.tmp")) == []
    source = Path(gate.__file__).read_text(encoding="utf-8")
    assert ".{path.name}.{os.getpid()}.tmp" not in source
    assert "uuid.uuid4().hex" in source
    assert "os.fsync(handle.fileno())" in source


def _write_static_artifacts(dev_dir: Path) -> None:
    (dev_dir / "CHANGELOG.md").write_text("# changelog\n", encoding="utf-8")
    stage = dev_dir / "latest"
    stage.mkdir()
    staged_file = stage / "ctoa_otclient_loader.lua"
    staged_file.write_text("loader", encoding="utf-8")
    staged_sha256 = hashlib.sha256(b"loader").hexdigest()
    _write_json(
        dev_dir / "manifest.json",
        {
            "name": "solteria-helper-dev",
            "created_at": "2026-07-06T03:00:00",
            "stage": str(stage),
            "files": [{"path": "ctoa_otclient_loader.lua", "sha256": staged_sha256}],
        },
    )
    _write_json(dev_dir / "validation.json", {"status": "passed"})
    zip_path = dev_dir / "ctoa_otclient_v1.1b.zip"
    zip_path.write_bytes(b"zip")
    zip_sha256 = hashlib.sha256(b"zip").hexdigest()
    _write_json(
        dev_dir / "release_readiness.json",
        {
            "status": "static-passed",
            "zip": {"path": str(zip_path), "sha256": zip_sha256},
        },
    )
    _write_json(
        dev_dir / "smoke_preflight.json",
        {"status": "passed", "manifest": {"created_at": "2026-07-06T03:00:00"}},
    )
    _write_json(
        dev_dir / "module_static_gates.json",
        {"status": "passed", "gate_count": 6, "passed_count": 6, "failed_count": 0},
    )
    _write_json(
        dev_dir / "module_attach_smoke.json",
        {"status": "passed", "module_count": 4, "passed_count": 4, "failed_count": 0},
    )


def _write_complete_smoke_report(path: Path) -> None:
    views = []
    for view in gate.EXPECTED_SMOKE_VIEWS:
        screenshot = path.parent / f"solteria-helper-attach-{view}-20260706-030000.png"
        screenshot.write_bytes(b"png")
        views.append({"view": view, "screenshot": str(screenshot), "size_bytes": 3})
    _write_json(
        path,
        {
            "covered_count": len(gate.EXPECTED_SMOKE_VIEWS),
            "expected_count": len(gate.EXPECTED_SMOKE_VIEWS),
            "missing": [],
            "acceptance_status": "ready_for_visual_review",
            "modal_limited": False,
            "views": views,
        },
    )


def test_release_gate_blocks_without_inworld_smoke_and_approval(tmp_path: Path):
    _write_static_artifacts(tmp_path)

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert report.releasable_to_live is False
    assert any(item.name == "SmokeAttachAll" and item.status == "pending" for item in report.gates)
    assert any(item.name == "live_approval" and item.status == "pending" for item in report.gates)
    assert "SmokeAttachAll" in report.next_action
    assert report.next_command.endswith("-Action Launch")


def test_release_gate_uses_smoke_status_next_command_for_smokeattach_blocker(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(
        tmp_path / "smoke_status.json",
        {
            "status": "character_modal",
            "next_action": "Enter the sandbox test character, then run ReadyCheck or SmokeAttachAll.",
            "next_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ReadyCheck",
        },
    )

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert report.next_command.endswith("-Action ReadyCheck")


def test_release_gate_runs_smokeattachall_when_readycheck_is_ready(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(tmp_path / "smoke_status.json", {"status": "ready_for_readycheck", "next_command": "readycheck"})
    _write_json(tmp_path / "ready_check.json", {"status": "ready"})

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert report.next_command.endswith("-Action SmokeAttachAll")


def test_release_gate_runs_smokeattachmodules_when_module_attach_is_missing_and_ready(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    (tmp_path / "module_attach_smoke.json").unlink()
    _write_json(tmp_path / "smoke_status.json", {"status": "ready_for_readycheck", "next_command": "readycheck"})
    _write_json(tmp_path / "ready_check.json", {"status": "ready"})

    report = gate.build_report(tmp_path)

    module_gate = next(item for item in report.gates if item.name == "ModuleAttachSmoke")
    assert module_gate.status == "pending"
    assert report.next_command.endswith("-Action SmokeAttachModules")


def test_release_gate_blocks_when_module_attach_failed(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(
        tmp_path / "module_attach_smoke.json",
        {"status": "failed", "module_count": 4, "passed_count": 3, "failed_count": 1},
    )

    report = gate.build_report(tmp_path)

    module_gate = next(item for item in report.gates if item.name == "ModuleAttachSmoke")
    assert module_gate.status == "blocked"
    assert "did not pass all prototype module attach tabs" in module_gate.reason


def test_release_gate_blocks_when_module_attach_is_stale(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    attach_gate = tmp_path / "module_attach_smoke.json"
    os.utime(attach_gate, (1, 1))

    report = gate.build_report(tmp_path)

    module_gate = next(item for item in report.gates if item.name == "ModuleAttachSmoke")
    assert module_gate.status == "blocked"
    assert "stale" in module_gate.reason


def test_release_gate_ignores_stale_readycheck_when_sandbox_is_not_running(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(
        tmp_path / "smoke_status.json",
        {
            "status": "not_running",
            "next_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action Launch",
        },
    )
    _write_json(tmp_path / "ready_check.json", {"status": "ready"})

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert report.next_command.endswith("-Action Launch")


def test_release_gate_passes_with_complete_inworld_smoke_and_approval(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=True)

    assert report.status == "passed"
    assert report.releasable_to_live is True
    assert all(item.status == "passed" for item in report.gates)
    assert "PromoteLiveCtoa -ApproveLiveDeploy" in report.next_command


def test_release_gate_points_to_live_promotion_when_only_approval_is_pending(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=False)

    assert report.status == "blocked"
    assert any(item.name == "live_approval" and item.status == "pending" for item in report.gates)
    assert "PromoteLiveCtoa -ApproveLiveDeploy" in report.next_command


def test_release_gate_accepts_durable_live_promotion_evidence(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    live_root = tmp_path / "live"
    live_root.mkdir()
    (live_root / "ctoa_otclient_loader.lua").write_text("loader", encoding="utf-8")
    _write_json(
        tmp_path / "live_promotion.json",
        {
            "approval_switch": "ApproveLiveDeploy",
            "live_client": str(live_root),
        },
    )

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=False)

    assert report.status == "passed"
    assert report.releasable_to_live is True
    approval_gate = next(item for item in report.gates if item.name == "live_approval")
    assert approval_gate.status == "passed"
    assert approval_gate.evidence.endswith("live_promotion.json")


def test_release_gate_blocks_stale_live_promotion_evidence(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    live_root = tmp_path / "live"
    live_root.mkdir()
    (live_root / "ctoa_otclient_loader.lua").write_text("loader", encoding="utf-8")
    promotion = tmp_path / "live_promotion.json"
    _write_json(
        promotion,
        {
            "approval_switch": "ApproveLiveDeploy",
            "live_client": str(live_root),
        },
    )
    manifest_mtime = (tmp_path / "manifest.json").stat().st_mtime
    os.utime(promotion, (manifest_mtime - 60, manifest_mtime - 60))

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=False)

    approval_gate = next(item for item in report.gates if item.name == "live_approval")
    assert approval_gate.status == "blocked"
    assert "older than the current dev manifest" in approval_gate.reason


def test_release_gate_blocks_when_live_promotion_hashes_do_not_match(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    live_root = tmp_path / "live"
    live_root.mkdir()
    (live_root / "ctoa_otclient_loader.lua").write_text("different", encoding="utf-8")
    _write_json(
        tmp_path / "live_promotion.json",
        {
            "approval_switch": "ApproveLiveDeploy",
            "live_client": str(live_root),
        },
    )

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=False)

    approval_gate = next(item for item in report.gates if item.name == "live_approval")
    assert approval_gate.status == "blocked"
    assert "do not match current manifest" in approval_gate.reason


def test_release_gate_blocks_when_live_root_helper_fallback_remains(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    live_root = tmp_path / "live"
    live_root.mkdir()
    (live_root / "ctoa_otclient_loader.lua").write_text("loader", encoding="utf-8")
    (live_root / "ctoa_native_helper.lua").write_text("stale root helper", encoding="utf-8")
    _write_json(
        tmp_path / "live_promotion.json",
        {
            "approval_switch": "ApproveLiveDeploy",
            "live_client": str(live_root),
        },
    )

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=False)

    approval_gate = next(item for item in report.gates if item.name == "live_approval")
    assert approval_gate.status == "blocked"
    assert "forbidden root helper fallback" in approval_gate.reason


def test_release_gate_blocks_when_live_root_profile_hash_drifts(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    stage = tmp_path / "latest"
    staged_profile = stage / "ctoa_ek_profile.lua"
    staged_profile.write_text("safe profile", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append(
        {
            "path": "ctoa_ek_profile.lua",
            "sha256": hashlib.sha256(b"safe profile").hexdigest(),
        }
    )
    _write_json(manifest_path, manifest)
    os.utime(tmp_path / "module_static_gates.json")
    os.utime(tmp_path / "module_attach_smoke.json")
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    live_root = tmp_path / "live"
    live_root.mkdir()
    (live_root / "ctoa_otclient_loader.lua").write_text("loader", encoding="utf-8")
    (live_root / "ctoa_ek_profile.lua").write_text("unsafe profile drift", encoding="utf-8")
    _write_json(
        tmp_path / "live_promotion.json",
        {
            "approval_switch": "ApproveLiveDeploy",
            "live_client": str(live_root),
        },
    )

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=False)

    approval_gate = next(item for item in report.gates if item.name == "live_approval")
    assert approval_gate.status == "blocked"
    assert "ctoa_ek_profile.lua" in approval_gate.reason


def test_release_gate_blocks_when_smoke_report_lacks_view_evidence(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_json(
        smoke,
        {
            "covered_count": len(gate.EXPECTED_SMOKE_VIEWS),
            "expected_count": len(gate.EXPECTED_SMOKE_VIEWS),
            "missing": [],
            "acceptance_status": "ready_for_visual_review",
            "modal_limited": False,
            "views": [],
        },
    )

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=True)

    smoke_gate = next(item for item in report.gates if item.name == "SmokeAttachAll")
    assert smoke_gate.status == "blocked"
    assert "required view screenshot evidence" in smoke_gate.reason


def test_release_gate_blocks_when_smoke_report_screenshot_file_is_missing(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    data = json.loads(smoke.read_text(encoding="utf-8"))
    missing = Path(data["views"][0]["screenshot"])
    missing.unlink()
    smoke.write_text(json.dumps(data), encoding="utf-8")

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=True)

    smoke_gate = next(item for item in report.gates if item.name == "SmokeAttachAll")
    assert smoke_gate.status == "blocked"
    assert data["views"][0]["view"] in smoke_gate.reason


def test_release_gate_blocks_when_smoke_report_is_older_than_manifest(tmp_path: Path):
    smoke = tmp_path / "smoke.json"
    _write_complete_smoke_report(smoke)
    _write_static_artifacts(tmp_path)
    manifest_mtime = (tmp_path / "manifest.json").stat().st_mtime
    os.utime(smoke, (manifest_mtime - 60, manifest_mtime - 60))

    report = gate.build_report(tmp_path, smoke_report=smoke, approved=True)

    smoke_gate = next(item for item in report.gates if item.name == "SmokeAttachAll")
    assert smoke_gate.status == "blocked"
    assert "stale for the current dev manifest" in smoke_gate.reason
    assert report.next_command.endswith("-Action Launch")


def test_release_gate_discovers_latest_inworld_smoke_report(tmp_path: Path):
    screenshot_dir = tmp_path / "shots"
    screenshot_dir.mkdir()
    older = screenshot_dir / "solteria-helper-smokeall-inworld-20260705-0100.json"
    newer = screenshot_dir / "solteria-helper-smokeall-inworld-20260705-0200.json"
    coverage = screenshot_dir / "solteria-helper-smokeall-coverage-20260705-0300.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")
    coverage.write_text("{}", encoding="utf-8")

    older.touch()
    coverage.touch()
    newer.touch()

    assert gate.find_latest_inworld_smoke_report(screenshot_dir) == newer


def test_release_gate_ignores_modal_limited_coverage_reports(tmp_path: Path):
    screenshot_dir = tmp_path / "shots"
    screenshot_dir.mkdir()
    (screenshot_dir / "solteria-helper-smokeall-coverage-20260705-0300.json").write_text("{}", encoding="utf-8")

    assert gate.find_latest_inworld_smoke_report(screenshot_dir) is None


def test_release_gate_blocks_when_smoke_preflight_is_missing(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    (tmp_path / "smoke_preflight.json").unlink()

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert any(item.name == "SmokePreflight" and item.status == "pending" for item in report.gates)
    assert "SmokePreflight" in report.next_action
    assert report.next_command.endswith("-Action SmokePreflight")


def test_release_gate_blocks_when_smoke_preflight_failed(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(tmp_path / "smoke_preflight.json", {"status": "failed"})

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert any(item.name == "SmokePreflight" and item.status == "blocked" for item in report.gates)
    assert "sandbox files do not match" in report.next_action


def test_release_gate_blocks_when_smoke_preflight_is_stale_for_manifest(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(
        tmp_path / "smoke_preflight.json",
        {"status": "passed", "manifest": {"created_at": "2026-07-06T02:00:00"}},
    )

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    assert any(item.name == "SmokePreflight" and item.status == "blocked" for item in report.gates)
    assert "stale" in report.next_action
    assert report.next_command.endswith("-Action SmokePreflight")


def test_release_gate_accepts_preflight_manifest_hash_across_datetime_formats(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    _write_json(
        tmp_path / "smoke_preflight.json",
        {
            "status": "passed",
            "manifest": {
                "created_at": "07/06/2026 03:00:00",
                "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            },
        },
    )

    report = gate.build_report(tmp_path)

    preflight = next(item for item in report.gates if item.name == "SmokePreflight")
    assert preflight.status == "passed"


def test_release_gate_blocks_when_module_static_gates_are_missing(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    (tmp_path / "module_static_gates.json").unlink()

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    module_gate = next(item for item in report.gates if item.name == "ModuleStaticGates")
    assert module_gate.status == "pending"
    assert "ModuleStaticGates" in report.next_action
    assert report.next_command.endswith("-Action ModuleStaticGates")


def test_release_gate_blocks_when_module_static_gates_failed(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(
        tmp_path / "module_static_gates.json",
        {"status": "failed", "gate_count": 5, "passed_count": 4, "failed_count": 1},
    )

    report = gate.build_report(tmp_path)

    module_gate = next(item for item in report.gates if item.name == "ModuleStaticGates")
    assert module_gate.status == "blocked"
    assert "did not pass all prototype module gates" in module_gate.reason
    assert report.next_command.endswith("-Action ModuleStaticGates")


def test_release_gate_blocks_when_module_static_gates_are_stale(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    module_gates = tmp_path / "module_static_gates.json"
    manifest_mtime = (tmp_path / "manifest.json").stat().st_mtime
    os.utime(module_gates, (manifest_mtime - 60, manifest_mtime - 60))

    report = gate.build_report(tmp_path)

    module_gate = next(item for item in report.gates if item.name == "ModuleStaticGates")
    assert module_gate.status == "blocked"
    assert "stale" in module_gate.reason
    assert report.next_command.endswith("-Action ModuleStaticGates")


def test_release_gate_blocks_when_zip_evidence_is_missing(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    _write_json(
        tmp_path / "release_readiness.json",
        {
            "status": "static-passed",
            "zip": {},
        },
    )

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    zip_gate = next(item for item in report.gates if item.name == "zip")
    assert zip_gate.status == "blocked"
    assert zip_gate.evidence == "not provided"
    assert "Missing versioned ZIP" in report.next_action


def test_release_gate_blocks_when_zip_hash_does_not_match_readiness(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    zip_path = tmp_path / "ctoa_otclient_v1.1b.zip"
    _write_json(
        tmp_path / "release_readiness.json",
        {
            "status": "static-passed",
            "zip": {"path": str(zip_path), "sha256": "0" * 64},
        },
    )

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    zip_gate = next(item for item in report.gates if item.name == "zip")
    assert zip_gate.status == "blocked"
    assert "SHA256" in zip_gate.reason
    assert "ZIP SHA256" in report.next_action


def test_release_gate_blocks_when_manifest_stage_file_is_missing(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    (tmp_path / "latest" / "ctoa_otclient_loader.lua").unlink()

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    manifest_gate = next(item for item in report.gates if item.name == "manifest")
    assert manifest_gate.status == "blocked"
    assert "staged file hashes do not match" in manifest_gate.reason
    assert "ctoa_otclient_loader.lua" in report.next_action


def test_release_gate_blocks_when_manifest_stage_hash_mismatches(tmp_path: Path):
    _write_static_artifacts(tmp_path)
    (tmp_path / "latest" / "ctoa_otclient_loader.lua").write_text("changed", encoding="utf-8")

    report = gate.build_report(tmp_path)

    assert report.status == "blocked"
    manifest_gate = next(item for item in report.gates if item.name == "manifest")
    assert manifest_gate.status == "blocked"
    assert "staged file hashes do not match" in manifest_gate.reason
