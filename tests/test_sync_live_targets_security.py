import importlib.util
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "sync-live-targets.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_live_targets", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_live_targets_replaces_only_child_directory(tmp_path: Path) -> None:
    module = load_module()
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "https-example.test").mkdir(parents=True)
    (source / "https-example.test" / "live-manifest.json").write_text(
        "{}", encoding="utf-8"
    )
    (target / "https-example.test").mkdir(parents=True)
    (target / "https-example.test" / "stale.txt").write_text("stale", encoding="utf-8")

    report = module.sync_live_targets(source, target)

    synced_file = target / "https-example.test" / "live-manifest.json"
    assert report["ok"] is True
    assert report["synced_count"] == 1
    assert synced_file.exists()
    assert not (target / "https-example.test" / "stale.txt").exists()


def test_sync_live_targets_rejects_target_inside_source(tmp_path: Path) -> None:
    module = load_module()
    source = tmp_path / "source"
    target = source / "nested-target"

    with pytest.raises(ValueError, match="must not be the source root or inside it"):
        module.sync_live_targets(source, target)


def test_sync_live_targets_rejects_unsafe_source_directory_name(tmp_path: Path) -> None:
    module = load_module()
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "bad name").mkdir(parents=True)

    with pytest.raises(ValueError, match="safe slugs"):
        module.sync_live_targets(source, target)


def test_sync_live_targets_rejects_existing_target_symlink(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is unavailable on this platform")

    module = load_module()
    source = tmp_path / "source"
    target = tmp_path / "target"
    outside = tmp_path / "outside"
    (source / "https-example.test").mkdir(parents=True)
    (source / "https-example.test" / "live-manifest.json").write_text(
        "{}", encoding="utf-8"
    )
    target.mkdir()
    outside.mkdir()

    try:
        os.symlink(outside, target / "https-example.test", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation not permitted: {exc}")

    with pytest.raises(
        ValueError, match="outside live target root|unsafe live target path"
    ):
        module.sync_live_targets(source, target)

    assert outside.exists()
