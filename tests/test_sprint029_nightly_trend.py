"""CTOA-144: Sprint-029 nightly trend automation focused tests.

Verifies that the nightly stability batch produces a valid artifact with
full drift visibility fields when invoked for sprint-029.
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


def test_sprint029_nightly_artifact_has_drift_visibility_fields(monkeypatch, tmp_path: Path):
    """Artifact must contain all drift visibility fields required by CTOA-144."""
    ns = _load_nightly_stability()

    def fake_run(cmd: list[str], cwd: Path):
        if "pytest" in cmd:
            return 0, "12 passed in 1.40s\n"
        return 0, "validator ok\n"

    monkeypatch.setattr(ns, "_run", fake_run)

    out_path = tmp_path / "artifacts" / "nightly-sprint029.json"
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
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))

    # Core artifact fields
    required_top = {"date", "timestamp", "tests_passed", "tests_failed", "validator_status", "overall",
                    "trend_24h", "trend_7d", "drift", "anomaly"}
    assert required_top.issubset(set(payload.keys()))

    # Drift visibility fields
    drift = payload["drift"]
    assert "success_rate_delta_7d_vs_24h" in drift
    assert "error_count_delta_7d_vs_24h" in drift
    assert "dominant_reason_code_changed" in drift

    # Evidence path must be sprint-029 specific
    evidence_index = tmp_path / "runtime" / "evidence" / "sprint-029" / "evidence-index.json"
    assert evidence_index.exists(), f"Sprint-029 evidence index not written: {evidence_index}"


def test_sprint029_nightly_evidence_entries_carry_sprint_id(monkeypatch, tmp_path: Path):
    """Every evidence entry must include sprint_id='029' for CI discoverability (CTOA-146 crossover)."""
    ns = _load_nightly_stability()

    def fake_run(cmd: list[str], cwd: Path):
        if "pytest" in cmd:
            return 0, "8 passed in 0.90s\n"
        return 0, "ok\n"

    monkeypatch.setattr(ns, "_run", fake_run)

    out_path = tmp_path / "artifacts" / "nightly.json"
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
    assert isinstance(entries, list)
    assert len(entries) >= 1
    for entry in entries:
        assert entry.get("sprint_id") == "029", f"Missing sprint_id in entry: {entry}"
