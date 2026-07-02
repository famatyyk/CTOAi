import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ops" / "release_evidence_pack.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_evidence_pack", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_evidence_pack_handles_missing_artifacts(tmp_path: Path):
    module = _load_module()

    pack = module.build_evidence_pack(
        tmp_path / "releases" / "evidence",
        tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json",
        tmp_path / "runtime" / "api-cost" / "latest.json",
        tmp_path / "runtime" / "control-center" / "action-audit.jsonl",
    )

    assert pack["release_evidence_file_count"] == 0
    assert pack["repo_hygiene"]["status"] == "missing"
    assert pack["api_cost_report"]["status"] == "missing"
    assert pack["control_center_audit"]["record_count"] == 0
    assert any("repo hygiene" in item.lower() for item in pack["recommendations"])
    assert any("api_cost_report" in item for item in pack["recommendations"])


def test_build_evidence_pack_reads_current_artifacts(tmp_path: Path):
    module = _load_module()

    releases_dir = tmp_path / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-056"
    sprint_dir.mkdir(parents=True)
    evidence_file = sprint_dir / "CTOA-300.md"
    evidence_file.write_text("# Evidence\n", encoding="utf-8")

    quality_path = tmp_path / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        """
{
  "status": "PASS",
  "finding_count": 0,
  "summary": {
    "private_count": 0,
    "public_count": 0,
    "review_count": 0
  }
}
""".strip(),
        encoding="utf-8",
    )

    cost_path = tmp_path / "runtime" / "api-cost" / "latest.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(
        """
{
  "records_seen": 3,
  "total_tokens": 1234,
  "total_cost_usd": 1.25,
  "anomalies": [{"component": "prompt-forge"}]
}
""".strip(),
        encoding="utf-8",
    )

    audit_path = tmp_path / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"ok": true}\n{"ok": false}\n', encoding="utf-8")

    pack = module.build_evidence_pack(releases_dir, quality_path, cost_path, audit_path)

    assert pack["release_evidence_file_count"] == 1
    assert pack["repo_hygiene"]["status"] == "PASS"
    assert pack["api_cost_report"]["status"] == "ready"
    assert pack["api_cost_report"]["records_seen"] == 3
    assert pack["api_cost_report"]["anomaly_count"] == 1
    assert pack["control_center_audit"]["record_count"] == 2
    assert pack["latest_release_evidence"]["path"].endswith("CTOA-300.md")
    assert pack["release_sprints"][0]["sprint"] == "sprint-056"


def test_build_evidence_pack_uses_configured_defaults(tmp_path: Path, monkeypatch):
    releases_dir = tmp_path / "configured" / "releases" / "evidence"
    sprint_dir = releases_dir / "sprint-099"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "CTOA-999.md").write_text("# Evidence\n", encoding="utf-8")

    quality_path = tmp_path / "configured" / "runtime" / "repo-hygiene" / "local-pr-quality.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(json.dumps({"status": "PASS", "finding_count": 0, "summary": {}}), encoding="utf-8")

    cost_path = tmp_path / "configured" / "runtime" / "api-cost" / "latest.json"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(json.dumps({"records_seen": 1, "total_tokens": 10, "total_cost_usd": 0.1}), encoding="utf-8")

    audit_path = tmp_path / "configured" / "runtime" / "control-center" / "action-audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text('{"ok": true}\n', encoding="utf-8")

    monkeypatch.setenv("CTOA_RELEASES_DIR", str(releases_dir))
    monkeypatch.setenv("CTOA_REPO_HYGIENE_PATH", str(quality_path))
    monkeypatch.setenv("CTOA_API_COST_REPORT_PATH", str(cost_path))
    monkeypatch.setenv("CTOA_ACTION_AUDIT_PATH", str(audit_path))

    module = _load_module()
    pack = module.build_evidence_pack()

    assert pack["releases_dir"] == str(releases_dir).replace("\\", "/")
    assert pack["quality_path"] == str(quality_path).replace("\\", "/")
    assert pack["cost_report_path"] == str(cost_path).replace("\\", "/")
    assert pack["action_audit_path"] == str(audit_path).replace("\\", "/")
    assert pack["latest_release_evidence"]["path"].endswith("CTOA-999.md")
