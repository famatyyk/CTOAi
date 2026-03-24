"""Sprint-027 validator: continuity, evidence publishing, and release-pack checks."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

try:
    from scripts.ops.evidence_retention import apply_retention_policy, read_retention_policy_from_env
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from evidence_retention import apply_retention_policy, read_retention_policy_from_env


REQUIRED_FILES = [
    "workflows/backlog-sprint-027.yaml",
    "workflows/sprint-027-quality-delivery-continuity-flow.yaml",
    "scripts/ops/sprint027_validate.py",
    ".vscode/tasks.json",
    ".github/workflows/ctoa-pipeline.yml",
    "runtime/experiments/sprint-027/CTOA-133.md",
    "runtime/experiments/sprint-027/CTOA-134.md",
    "runtime/experiments/sprint-027/CTOA-135.md",
    "runtime/experiments/sprint-027/CTOA-136.md",
    "runtime/experiments/sprint-027/CTOA-137.md",
]

REQUIRED_YAML_FILES = [
    "workflows/backlog-sprint-027.yaml",
    "workflows/sprint-027-quality-delivery-continuity-flow.yaml",
]

REQUIRED_HOOKS = {"on_start", "on_complete", "on_fail"}


def _safe_yaml_load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_file_exists(root: Path, rel_path: str) -> dict:
    ok = (root / rel_path).exists()
    return {
        "id": f"file:{rel_path}",
        "ok": ok,
        "hint": "Create or restore missing sprint-027 starter file" if not ok else "",
    }


def check_yaml_syntax(root: Path) -> list[dict]:
    checks = []
    for rel in REQUIRED_YAML_FILES:
        path = root / rel
        if not path.exists():
            checks.append({"id": f"syntax:{rel}", "ok": False, "hint": "File missing for syntax validation"})
            continue
        try:
            _safe_yaml_load(path)
            checks.append({"id": f"syntax:{rel}", "ok": True, "hint": ""})
        except Exception as exc:
            checks.append({"id": f"syntax:{rel}", "ok": False, "hint": f"YAML parse error: {exc}"})
    return checks


def check_missing_hooks(root: Path) -> dict:
    flow_path = root / "workflows/sprint-027-quality-delivery-continuity-flow.yaml"
    try:
        flow = _safe_yaml_load(flow_path)
    except Exception as exc:
        return {"id": "missing_hooks", "ok": False, "hint": f"Cannot load flow YAML: {exc}"}

    tasks = flow.get("tasks") or []
    missing: list[str] = []
    for task_def in tasks:
        task_id = task_def.get("id", "unknown")
        for req in REQUIRED_HOOKS:
            if req not in task_def or not task_def[req]:
                missing.append(f"{task_id}:{req}")

    return {
        "id": "missing_hooks",
        "ok": len(missing) == 0,
        "hint": f"Missing hooks: {', '.join(missing)}" if missing else "",
    }


def check_pipeline_gate(root: Path) -> dict:
    pipeline_path = root / ".github/workflows/ctoa-pipeline.yml"
    if not pipeline_path.exists():
        return {"id": "pipeline_gate", "ok": False, "hint": "Pipeline file missing"}

    content = pipeline_path.read_text(encoding="utf-8")
    gate_present = "scripts/ops/sprint027_validate.py" in content
    artifact_present = "runtime/ci-artifacts/sprint-027-validation.json" in content
    nightly_present = "scripts/ops/nightly_stability.py" in content
    evidence_present = "runtime/evidence/sprint-027" in content
    ok = gate_present and artifact_present and nightly_present and evidence_present

    hint_parts: list[str] = []
    if not gate_present:
        hint_parts.append("add Sprint-027 validator command")
    if not artifact_present:
        hint_parts.append("add Sprint-027 artifact path")
    if not nightly_present:
        hint_parts.append("add nightly stability CI step")
    if not evidence_present:
        hint_parts.append("upload runtime/evidence/sprint-027 artifacts")

    return {
        "id": "pipeline_gate",
        "ok": ok,
        "hint": "; ".join(hint_parts),
    }


def check_local_tasks(root: Path) -> dict:
    tasks_path = root / ".vscode/tasks.json"
    if not tasks_path.exists():
        return {"id": "local_tasks", "ok": False, "hint": "tasks.json missing"}

    content = tasks_path.read_text(encoding="utf-8")
    labels_present = all(
        needle in content
        for needle in [
            "CTOA: Sprint-027 Validate Quality + Delivery Continuity",
            "CTOA: Sprint-027 Wave-1 Run",
            "CTOA: Nightly Stability Batch",
        ]
    )

    return {
        "id": "local_tasks",
        "ok": labels_present,
        "hint": "Add Sprint-027 validate, nightly, and wave-1 tasks in .vscode/tasks.json" if not labels_present else "",
    }


def check_release_pack_state(root: Path) -> dict:
    release_path = root / "runtime/experiments/sprint-027/CTOA-137.md"
    if not release_path.exists():
        return {"id": "release_pack_state", "ok": False, "hint": "Release pack file missing"}

    content = release_path.read_text(encoding="utf-8")
    ok = "wave_1" in content and "v1.1.0" in content and "CTOA-133" in content
    return {
        "id": "release_pack_state",
        "ok": ok,
        "hint": "Update CTOA-137 release pack summary and gate markers" if not ok else "",
    }


def _record_evidence(root: Path, report_path: Path) -> None:
    evidence_dir = root / "runtime" / "evidence" / "sprint-027"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    sha = _sha256_file(report_path)
    sha_path = evidence_dir / f"{report_path.name}.sha256"
    sha_path.write_text(f"{sha}  {report_path.name}\n", encoding="utf-8")

    index_path = evidence_dir / "evidence-index.json"
    try:
        existing = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    except Exception:
        existing = []
    if not isinstance(existing, list):
        existing = []

    entry = {
        "kind": "validator-report",
        "path": str(report_path.relative_to(root)).replace("\\", "/"),
        "sha256": sha,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    filtered = [item for item in existing if isinstance(item, dict) and item.get("path") != entry["path"]]
    filtered.append(entry)
    max_entries, max_age_days = read_retention_policy_from_env()
    filtered = apply_retention_policy(
        filtered,
        max_entries=max_entries,
        max_age_days=max_age_days,
    )
    index_path.write_text(json.dumps(filtered, indent=2), encoding="utf-8")


def validate_sprint_027(root: Path) -> dict:
    checks: list[dict] = []
    for rel in REQUIRED_FILES:
        checks.append(check_file_exists(root, rel))
    checks.extend(check_yaml_syntax(root))
    checks.append(check_missing_hooks(root))
    checks.append(check_pipeline_gate(root))
    checks.append(check_local_tasks(root))
    checks.append(check_release_pack_state(root))

    passed = sum(1 for c in checks if c.get("ok", False))
    total = len(checks)

    return {
        "status": "PASS" if passed == total else "FAIL",
        "summary": f"{passed}/{total} checks passed",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sprint-027 starter validator for quality and delivery continuity"
    )
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--json-out", help="Write JSON report to file")
    parser.add_argument("--run-tests", action="store_true", help="Run all validation checks")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root}")

    report = validate_sprint_027(root)

    if args.json_out:
        out_path = root / args.json_out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        _record_evidence(root, out_path)
        print(f"[sprint027_validate] Report written to {out_path}")

    status = report["status"]
    summary = report["summary"]
    print(f"[sprint027_validate] {status} — {summary}")
    for chk in report["checks"]:
        mark = "OK" if chk.get("ok") else "FAIL"
        hint = f"  hint: {chk['hint']}" if chk.get("hint") else ""
        print(f"  [{mark}] {chk['id']}{hint}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
