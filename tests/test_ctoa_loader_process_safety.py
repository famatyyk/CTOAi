import os
from pathlib import Path

import pytest

from scripts.ops import ctoa_loader


class _Proc:
    returncode = 0
    stdout = "synced\n"
    stderr = ""


def test_sync_with_output_uses_trusted_runner(monkeypatch, tmp_path: Path) -> None:
    sync_script = tmp_path / "sync-live-targets.py"
    sync_script.write_text("print('ok')\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Proc()

    monkeypatch.setattr(ctoa_loader, "SYNC_SCRIPT", sync_script)
    monkeypatch.setattr(ctoa_loader.process_safety, "run_trusted", fake_run)

    code, stdout, stderr = ctoa_loader._sync_with_output(
        tmp_path / "src", tmp_path / "dst"
    )

    assert (code, stdout, stderr) == (0, "synced", "")
    command = captured["command"]
    assert isinstance(command, list)
    assert command[1] == str(sync_script)
    assert "--source" in command
    assert captured["kwargs"]["check"] is False


def test_open_path_resolves_launcher_before_launch(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_resolve(name: str, **kwargs) -> str:
        captured["resolve"] = (name, kwargs)
        return "/trusted/opener"

    def fake_run(command: list[str], **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Proc()

    monkeypatch.setattr(ctoa_loader.os, "name", "posix", raising=False)
    monkeypatch.setattr(ctoa_loader.sys, "platform", "linux")
    monkeypatch.setattr(ctoa_loader.process_safety, "resolve_executable", fake_resolve)
    monkeypatch.setattr(ctoa_loader.process_safety, "run_trusted", fake_run)

    ctoa_loader._open_path(tmp_path)

    assert captured["resolve"] == ("xdg-open", {"env_var": "CTOA_FILE_OPENER_BIN"})
    assert captured["command"] == ["/trusted/opener", str(tmp_path)]
    assert captured["kwargs"]["check"] is False


def test_resolve_target_dir_rejects_parent_traversal(tmp_path: Path) -> None:
    root = tmp_path / "live-root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    assert ctoa_loader._resolve_target_dir(root, "../outside") is None


def test_open_target_dir_does_not_launch_parent_traversal(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "live-root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    launched: list[Path] = []
    monkeypatch.setattr(ctoa_loader, "_open_path", lambda path: launched.append(path))

    assert ctoa_loader._open_target_dir(root, "../outside") == 1
    assert launched == []


def test_export_manifest_rejects_parent_traversal(tmp_path: Path) -> None:
    root = tmp_path / "live-root"
    outside = tmp_path / "outside"
    out = tmp_path / "export.json"
    root.mkdir()
    outside.mkdir()
    (outside / "live-manifest.json").write_text("{}", encoding="utf-8")

    assert ctoa_loader._export_manifest(root, "../outside", out) == 1
    assert not out.exists()


def test_export_manifest_keeps_normal_export(tmp_path: Path) -> None:
    root = tmp_path / "live-root"
    target = root / "https-example.test"
    out = tmp_path / "export.json"
    payload = '{"url":"https://example.test","status":"published"}'
    target.mkdir(parents=True)
    (target / "live-manifest.json").write_text(payload, encoding="utf-8")

    assert ctoa_loader._export_manifest(root, "https-example.test", out) == 0
    assert out.read_text(encoding="utf-8") == payload


def test_resolve_target_dir_rejects_symlink_escape(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is unavailable on this platform")

    root = tmp_path / "live-root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        os.symlink(outside, root / "https-example.test", target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation not permitted: {exc}")

    assert ctoa_loader._resolve_target_dir(root, "https-example.test") is None


def test_export_manifest_rejects_symlink_manifest_escape(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is unavailable on this platform")

    root = tmp_path / "live-root"
    target = root / "https-example.test"
    outside = tmp_path / "outside"
    out = tmp_path / "export.json"
    target.mkdir(parents=True)
    outside.mkdir()
    outside_manifest = outside / "live-manifest.json"
    outside_manifest.write_text('{"url":"https://outside.test"}', encoding="utf-8")
    try:
        os.symlink(outside_manifest, target / "live-manifest.json")
    except OSError as exc:
        pytest.skip(f"symlink creation not permitted: {exc}")

    assert ctoa_loader._export_manifest(root, "https-example.test", out) == 1
    assert not out.exists()


def test_export_manifest_rejects_symlink_output_path(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is unavailable on this platform")

    root = tmp_path / "live-root"
    target = root / "https-example.test"
    outside = tmp_path / "outside"
    out = tmp_path / "export.json"
    target.mkdir(parents=True)
    outside.mkdir()
    (target / "live-manifest.json").write_text('{"ok":true}', encoding="utf-8")
    outside_export = outside / "export.json"
    outside_export.write_text("do-not-touch", encoding="utf-8")
    try:
        os.symlink(outside_export, out)
    except OSError as exc:
        pytest.skip(f"symlink creation not permitted: {exc}")

    assert ctoa_loader._export_manifest(root, "https-example.test", out) == 1
    assert outside_export.read_text(encoding="utf-8") == "do-not-touch"


def test_list_targets_ignores_unsafe_manifest_symlink(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is unavailable on this platform")

    root = tmp_path / "live-root"
    target = root / "https-example.test"
    outside = tmp_path / "outside"
    target.mkdir(parents=True)
    outside.mkdir()
    outside_manifest = outside / "live-manifest.json"
    outside_manifest.write_text(
        '{"url":"https://outside.test","status":"published"}',
        encoding="utf-8",
    )
    try:
        os.symlink(outside_manifest, target / "live-manifest.json")
    except OSError as exc:
        pytest.skip(f"symlink creation not permitted: {exc}")

    assert ctoa_loader._list_targets(root) == [
        {
            "name": "https-example.test",
            "path": str(target),
            "has_manifest": False,
            "url": "",
            "status": "",
        }
    ]


def test_resolve_target_dir_keeps_host_slug_lookup(tmp_path: Path) -> None:
    root = tmp_path / "live-root"
    target = root / "https-example.test"
    target.mkdir(parents=True)

    assert ctoa_loader._resolve_target_dir(root, "https://example.test/path") == target
