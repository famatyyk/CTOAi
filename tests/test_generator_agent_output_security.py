from __future__ import annotations

from pathlib import Path

import pytest

from runner.agents import generator_agent as module


def _patch_db(
    monkeypatch: pytest.MonkeyPatch, executed: list[tuple[str, tuple]]
) -> None:
    def fake_query_one(sql: str, params=()):  # noqa: ANN001
        if "SELECT url FROM servers" in sql:
            return {"url": "https://example.test/world"}
        if "SELECT url, name, game_type FROM servers" in sql:
            return {
                "url": "https://example.test/world",
                "name": "Example",
                "game_type": "tibia-ot",
            }
        raise AssertionError(f"Unexpected query_one SQL: {sql}")

    monkeypatch.setattr(module.db, "query_one", fake_query_one)
    monkeypatch.setattr(module.db, "query_all", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        module.db,
        "execute",
        lambda sql, params=(): executed.append((str(sql), tuple(params))),
    )


def _mod(output_file: str | None) -> dict:
    return {
        "server_id": 1,
        "task_id": "task-1",
        "template": "auto_heal",
        "output_file": output_file,
        "queued_at": "2026-07-06T00:00:00+00:00",
    }


def test_generator_output_file_stays_under_generated_server_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[tuple[str, tuple]] = []
    monkeypatch.setattr(module, "OUTPUT_BASE", tmp_path / "generated")
    _patch_db(monkeypatch, executed)

    result = module.generate_module(_mod("profiles/auto_heal.lua"))

    output_path = Path(result["output_path"])
    assert (
        output_path
        == tmp_path / "generated" / "example_test_world" / "profiles" / "auto_heal.lua"
    )
    assert output_path.read_text(encoding="utf-8").startswith("-- auto_heal.lua")
    assert executed


@pytest.mark.parametrize(
    "output_file",
    [
        "../escape.lua",
        "profiles/../../escape.lua",
        "/tmp/escape.lua",
        "C:/temp/escape.lua",
        "profiles\\escape.lua",
        "bad:name.lua",
    ],
)
def test_generator_rejects_unsafe_output_file_before_write_or_db_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_file: str,
) -> None:
    executed: list[tuple[str, tuple]] = []
    monkeypatch.setattr(module, "OUTPUT_BASE", tmp_path / "generated")
    _patch_db(monkeypatch, executed)

    with pytest.raises(ValueError, match="Unsafe generated output path"):
        module.generate_module(_mod(output_file))

    assert executed == []
    assert not (tmp_path / "escape.lua").exists()
    generated_files = [
        path for path in (tmp_path / "generated").rglob("*") if path.is_file()
    ]
    assert generated_files == []


def test_generator_rejects_symlinked_server_output_dir_before_write_or_db_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[tuple[str, tuple]] = []
    output_base = tmp_path / "generated"
    output_base.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (output_base / "example_test_world").symlink_to(
            outside, target_is_directory=True
        )
    except OSError:
        pytest.skip("Symlink creation is not available in this environment")
    monkeypatch.setattr(module, "OUTPUT_BASE", output_base)
    _patch_db(monkeypatch, executed)

    with pytest.raises(ValueError, match="escapes output directory"):
        module.generate_module(_mod("profiles/auto_heal.lua"))

    assert executed == []
    assert list(outside.rglob("*")) == []


def test_generator_manifest_rejects_symlinked_latest_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_base = tmp_path / "generated"
    manifests = output_base / "manifests"
    manifests.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_latest = outside / "latest.json"
    outside_latest.write_text("existing\n", encoding="utf-8")
    try:
        (manifests / "latest.json").symlink_to(outside_latest)
    except OSError:
        pytest.skip("Symlink creation is not available in this environment")
    monkeypatch.setattr(module, "OUTPUT_BASE", output_base)

    with pytest.raises(ValueError, match="must not be a symlink"):
        module._write_run_manifest(
            run_started_at="2026-07-06T00:00:00+00:00",
            generated=[],
            failed=[],
        )

    assert outside_latest.read_text(encoding="utf-8") == "existing\n"


def test_generator_manifest_rejects_symlinked_manifests_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_base = tmp_path / "generated"
    output_base.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (output_base / "manifests").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available in this environment")
    monkeypatch.setattr(module, "OUTPUT_BASE", output_base)

    with pytest.raises(ValueError, match="escapes output directory"):
        module._write_run_manifest(
            run_started_at="2026-07-06T00:00:00+00:00",
            generated=[],
            failed=[],
        )

    assert list(outside.rglob("*")) == []
