"""CTOA-146: Sprint-029 CI evidence hardening focused tests.

Verifies that nightly evidence artifacts are written to a canonical,
sprint-scoped path with all required fields so CI can discover them.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_nightly_stability():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "nightly_stability.py"
    spec = importlib.util.spec_from_file_location("nightly_stability", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sprint029_evidence_discoverable_at_canonical_path(monkeypatch, tmp_path: Path):
    """Sprint-029 evidence index must exist at the canonical CI-discoverable path."""
    ns = _load_nightly_stability()

    def fake_run(cmd: list[str], cwd: Path):
        if "pytest" in cmd:
            return 0, "10 passed in 1.00s\n"
        return 0, "ok\n"

    monkeypatch.setattr(ns, "_run", fake_run)

    out_path = tmp_path / "out" / "nightly.json"
    monkeypatch.setattr(
        ns.sys,
        "argv",
        [
            "nightly_stability.py",
            "--root",
            str(tmp_path),
            "--json-out",
            str(out_path),
            "--sprint",
            "029",
        ],
    )

    rc = ns.main()
    assert rc == 0

    canonical = tmp_path / "runtime" / "evidence" / "sprint-029" / "evidence-index.json"
    assert canonical.exists(), f"Evidence index not found at canonical path: {canonical}"

    entries = json.loads(canonical.read_text(encoding="utf-8"))
    assert isinstance(entries, list)
    paths = [e["path"] for e in entries]
    assert any("nightly" in p for p in paths), f"Nightly artifact not indexed: {paths}"


def test_sprint029_evidence_entries_have_required_fields(monkeypatch, tmp_path: Path):
    """Each evidence entry must carry all required fields for CI discoverability."""
    ns = _load_nightly_stability()

    def fake_run(cmd: list[str], cwd: Path):
        if "pytest" in cmd:
            return 0, "5 passed\n"
        return 0, "ok\n"

    monkeypatch.setattr(ns, "_run", fake_run)

    out_path = tmp_path / "out" / "nightly.json"
    monkeypatch.setattr(
        ns.sys,
        "argv",
        [
            "nightly_stability.py",
            "--root",
            str(tmp_path),
            "--json-out",
            str(out_path),
            "--sprint",
            "029",
        ],
    )
    ns.main()

    index_path = tmp_path / "runtime" / "evidence" / "sprint-029" / "evidence-index.json"
    entries = json.loads(index_path.read_text(encoding="utf-8"))
    required_fields = {"kind", "path", "sha256", "recorded_at", "sprint_id"}
    for entry in entries:
        missing = required_fields - set(entry.keys())
        assert not missing, f"Evidence entry missing fields {missing}: {entry}"
        assert entry["sprint_id"] == "029"
        assert entry["kind"] == "ci-artifact"
        assert entry["sha256"] and len(entry["sha256"]) == 64
