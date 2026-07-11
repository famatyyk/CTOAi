import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
PINNED_POSTCSS_VERSION = "8.5.16"
MIN_SAFE_POSTCSS_VERSION = (8, 5, 10)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _version_tuple(version: str) -> tuple[int, int, int]:
    core = version.split("-", 1)[0]
    parts = core.split(".")
    numbers = [int(part) for part in parts[:3]]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def test_web_package_pins_postcss_override_for_next_advisory() -> None:
    package_json = _read_json(WEB_ROOT / "package.json")

    assert package_json["devDependencies"]["postcss"] == PINNED_POSTCSS_VERSION
    assert package_json["overrides"]["postcss"] == "$postcss"


def test_web_lockfile_has_no_vulnerable_postcss_tree() -> None:
    lockfile = _read_json(WEB_ROOT / "package-lock.json")
    packages = lockfile["packages"]

    postcss_entries = {
        package_path: package_data["version"]
        for package_path, package_data in packages.items()
        if package_path.endswith("node_modules/postcss")
    }

    assert postcss_entries, "package-lock.json must include the patched PostCSS package"
    assert "node_modules/next/node_modules/postcss" not in packages

    for package_path, version in postcss_entries.items():
        assert _version_tuple(version) >= MIN_SAFE_POSTCSS_VERSION, (
            f"{package_path} uses vulnerable PostCSS {version}; keep GHSA-qx2v-qp2m-jg93 "
            f"mitigated with the root {PINNED_POSTCSS_VERSION} override"
        )
