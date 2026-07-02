import json
from pathlib import Path

from scripts.ops.validate_package_boundaries import validate_package_boundaries


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_validate_package_boundaries_passes_for_repo_manifests():
    issues = validate_package_boundaries(
        core_manifest=PROJECT_ROOT / "product" / "packages" / "core.manifest.json",
        pro_manifest=PROJECT_ROOT / "product" / "packages" / "pro.manifest.json",
        studio_manifest=PROJECT_ROOT / "product" / "packages" / "studio.manifest.json",
    )

    assert issues == []


def test_validate_package_boundaries_detects_core_mobile_console_leak(tmp_path: Path):
    core_manifest = tmp_path / "core.manifest.json"
    pro_manifest = tmp_path / "pro.manifest.json"
    studio_manifest = tmp_path / "studio.manifest.json"

    core_payload = json.loads((PROJECT_ROOT / "product" / "packages" / "core.manifest.json").read_text(encoding="utf-8"))
    pro_payload = json.loads((PROJECT_ROOT / "product" / "packages" / "pro.manifest.json").read_text(encoding="utf-8"))
    studio_payload = json.loads((PROJECT_ROOT / "product" / "packages" / "studio.manifest.json").read_text(encoding="utf-8"))

    core_payload["include_paths"] = list(core_payload.get("include_paths", [])) + ["mobile_console"]

    core_manifest.write_text(json.dumps(core_payload, indent=2), encoding="utf-8")
    pro_manifest.write_text(json.dumps(pro_payload, indent=2), encoding="utf-8")
    studio_manifest.write_text(json.dumps(studio_payload, indent=2), encoding="utf-8")

    issues = validate_package_boundaries(core_manifest, pro_manifest, studio_manifest)

    assert any("must not include mobile_console" in issue for issue in issues)
