from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows" / "solteria_safe_release.ps1"


RUNTIME_FILES = {
    "mods/ctoa_safe/ctoa_safe.otmod",
    "mods/ctoa_safe/ctoa_safe_loader.lua",
    "mods/ctoa_safe/ctoa_safe_helper.lua",
    "mods/ctoa_safe/styles/helper.otui",
    "mods/ctoa_safe/styles/spell.otui",
    "mods/ctoa_safe/styles/siolist.otui",
    "mods/ctoa_safe/styles/shooterPreset.otui",
}


def test_safe_release_is_seven_file_scoped_and_requires_explicit_live_approval() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '[ValidateSet("Validate", "Package", "Status", "Promote")]' in source
    assert "if (-not $ApproveLiveDeploy)" in source
    assert "Assert-LiveRoot -Candidate $SourceClient" in source
    assert '"mods/ctoa_safe/ctoa_safe.otmod"' in source
    assert '"mods/ctoa_safe/ctoa_safe_loader.lua"' in source
    assert '"mods/ctoa_safe/ctoa_safe_helper.lua"' in source
    for relative in sorted(RUNTIME_FILES):
        assert f'"{relative}"' in source
    assert source.count('"mods/ctoa_safe/') == 7
    assert "client_stopped_or_restarted = $false" in source
    assert "process_ids_before" in source and "process_ids_after" in source
    assert "source_live_sha256_match" in source


def test_safe_release_validate_produces_passed_seven_file_manifest(tmp_path: Path) -> None:
    out_dir = tmp_path / "safe-release"
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Action",
            "Validate",
            "-OutDir",
            str(out_dir),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    validation = json.loads((out_dir / "validation.json").read_text(encoding="utf-8-sig"))
    assert manifest["schema_version"] == "ctoa.safe-release-manifest.v1"
    assert manifest["safe_version"] == "3.3.0"
    assert len(manifest["files"]) == 7
    assert {entry["path"] for entry in manifest["files"]} == RUNTIME_FILES
    assert validation["status"] == "passed"
    assert validation["live_client_touched"] is False


def test_safe_release_package_contains_runtime_only(tmp_path: Path) -> None:
    out_dir = tmp_path / "safe-package"
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Action",
            "Package",
            "-OutDir",
            str(out_dir),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads((out_dir / "package.json").read_text(encoding="utf-8-sig"))
    archive = Path(report["archive"])
    assert report["runtime_file_count"] == 7
    assert report["source_code_local_only"] is True
    assert report["character_data_included"] is False
    assert report["reference_module_included"] is False
    with zipfile.ZipFile(archive) as zipped:
        names = {name.replace("\\", "/") for name in zipped.namelist() if not name.endswith("/")}
    assert names == RUNTIME_FILES


def test_safe_release_promote_refuses_without_approval(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Action",
            "Promote",
            "-OutDir",
            str(tmp_path / "safe-release"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode != 0
    assert "explicit -ApproveLiveDeploy" in completed.stderr
