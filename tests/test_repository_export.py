from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ops.repository_export import ExportError, _collect, build_export


def test_collect_deduplicates_overlapping_roots_and_excludes_private_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "product").mkdir(parents=True)
    (source / "product" / "keep.lua").write_text("return true\n", encoding="utf-8")
    (source / "product" / "secret.log").write_text("private\n", encoding="utf-8")
    spec = {"roots": ["product", "product/keep.lua"], "exclude": ["*.log"]}

    files = _collect("demo", spec, source)

    assert [item.relative.as_posix() for item in files] == ["product/keep.lua"]


def test_build_export_writes_manifest_and_readme(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_text("safe\n", encoding="utf-8")
    spec = {"name": "Demo", "roots": ["keep.txt"], "exclude": []}

    metadata = build_export("demo", spec, tmp_path / "out", write=True, root=source)
    destination = tmp_path / "out" / "Demo"

    assert metadata["file_count"] == 1
    assert (destination / "keep.txt").read_text(encoding="utf-8") == "safe\n"
    assert (destination / "README.md").exists()
    manifest = json.loads((destination / "EXPORT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["history_included"] is False
    assert manifest["files"][0]["path"] == "keep.txt"


def test_build_export_refuses_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_text("safe\n", encoding="utf-8")
    out = tmp_path / "out"
    (out / "Demo").mkdir(parents=True)

    with pytest.raises(ExportError, match="destination already exists"):
        build_export(
            "demo",
            {"name": "Demo", "roots": ["keep.txt"]},
            out,
            write=True,
            root=source,
        )
