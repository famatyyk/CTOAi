from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


PLUGIN_SCRIPTS = Path.home() / "plugins" / "ctoai-engine-brain" / "scripts"
pytestmark = pytest.mark.skipif(
    not PLUGIN_SCRIPTS.is_dir(),
    reason="Engine Brain operator plugin is not installed",
)


def load_evidence_io_module():
    if str(PLUGIN_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PLUGIN_SCRIPTS))
    path = PLUGIN_SCRIPTS / "ctoai_evidence_io.py"
    spec = importlib.util.spec_from_file_location("ctoai_evidence_io_for_tests", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rejects_oversize_non_objects_and_duplicate_keys(tmp_path: Path):
    evidence_io = load_evidence_io_module()
    payload = tmp_path / "payload.json"

    payload.write_text('{"first": 1, "first": 2}', encoding="utf-8")
    assert evidence_io.load_json_object(payload, 1024) == {}

    payload.write_text("[]", encoding="utf-8")
    assert evidence_io.load_json_object(payload, 1024) == {}

    payload.write_text('{"safe": true}', encoding="utf-8")
    assert evidence_io.load_json_object(payload, 4) == {}


def test_reject_symlinks(tmp_path: Path):
    evidence_io = load_evidence_io_module()
    source = tmp_path / "source.json"
    source.write_text('{"safe": true}', encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        os.symlink(source, link)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable in this test environment: {exc}")

    assert evidence_io.read_bounded_bytes(link, 1024) is None


def test_read_bounded_tail_reports_a_stable_suffix(tmp_path: Path):
    evidence_io = load_evidence_io_module()
    evidence = tmp_path / "audit.jsonl"
    evidence.write_bytes(b"first\nsecond\nthird\n")

    result = evidence_io.read_bounded_tail(evidence, len(b"third\n"))
    assert result is not None
    data, source_bytes, truncated = result
    assert data == b"third\n"
    assert source_bytes == evidence.stat().st_size
    assert truncated is True
