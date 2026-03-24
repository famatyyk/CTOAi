"""Sprint-028 validator: CI gate hardening for dashboard + nightly evidence interactions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

REQUIRED_FILES = [
    "workflows/backlog-sprint-028.yaml",
    "scripts/ops/sprint028_validate.py",
    "scripts/ops/nightly_stability.py",
    "scripts/ops/evidence_retention.py",
    "tests/test_mobile_console_dashboard_api.py",
    "tests/test_nightly_stability_artifact.py",
    "tests/test_evidence_retention_policy.py",
    ".vscode/tasks.json",
    ".github/workflows/ctoa-pipeline.yml",
]

REQUIRED_YAML_FILES = [
    "workflows/backlog-sprint-028.yaml",
]

REGRESSION_TEST_FILES = [
    "tests/test_mobile_console_dashboard_api.py",
    "tests/test_nightly_stability_artifact.py",
    "tests/test_evidence_retention_policy.py",
]



def _safe_yaml_load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)



def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr



def check_file_exists(root: Path, rel_path: str) -> dict:
    ok = (root / rel_path).exists()
    return {
        "id": f"file:{rel_path}",
        "ok": ok,
        "hint": "Create or restore missing Sprint-028 gate file" if not ok else "",
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



def check_pipeline_gate(root: Path) -> dict:
    pipeline_path = root / ".github/workflows/ctoa-pipeline.yml"
    if not pipeline_path.exists():
        return {"id": "pipeline_gate", "ok": False, "hint": "Pipeline file missing"}

    content = pipeline_path.read_text(encoding="utf-8")
    gate_present = "scripts/ops/sprint028_validate.py" in content
    artifact_present = "runtime/ci-artifacts/sprint-028-validation.json" in content
    evidence_upload_present = "runtime/ci-artifacts/nightly-stability-sprint-028-ci.json" in content

    ok = gate_present and artifact_present and evidence_upload_present

    hint_parts: list[str] = []
    if not gate_present:
        hint_parts.append("add Sprint-028 validator command")
    if not artifact_present:
        hint_parts.append("add Sprint-028 validation artifact path")
    if not evidence_upload_present:
        hint_parts.append("upload Sprint-028 nightly evidence artifact")

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
            "CTOA: Sprint-028 Validate CI Gate Hardening",
            "CTOA: Sprint-028 Wave-1 Run",
        ]
    )

    return {
        "id": "local_tasks",
        "ok": labels_present,
        "hint": "Add Sprint-028 validate and wave-1 tasks" if not labels_present else "",
    }



def check_backlog_item(root: Path) -> dict:
    path = root / "workflows/backlog-sprint-028.yaml"
    if not path.exists():
        return {"id": "backlog_item", "ok": False, "hint": "Sprint-028 backlog file missing"}

    content = path.read_text(encoding="utf-8")
    has_item = "id: CTOA-141" in content
    delivered = "id: CTOA-141" in content and "status: DELIVERED" in content.split("id: CTOA-141", 1)[1].split("- id:", 1)[0]

    if not has_item:
        return {"id": "backlog_item", "ok": False, "hint": "Missing CTOA-141 item in backlog"}
    if not delivered:
        return {"id": "backlog_item", "ok": False, "hint": "Mark CTOA-141 as DELIVERED after hardening"}
    return {"id": "backlog_item", "ok": True, "hint": ""}



def check_dashboard_regressions(root: Path) -> dict:
    python = sys.executable
    cmd = [python, "-m", "pytest", *REGRESSION_TEST_FILES, "-q"]
    code, output = _run(cmd, cwd=root)
    ok = code == 0
    tail = "\n".join(output.splitlines()[-20:])
    return {
        "id": "regression_dashboard_nightly",
        "ok": ok,
        "hint": "Focused regression tests failed" if not ok else "",
        "details": {
            "command": " ".join(cmd),
            "output_tail": tail,
        },
    }



def check_nightly_evidence_interaction(root: Path) -> dict:
    python = sys.executable
    nightly_rel = "runtime/ci-artifacts/nightly-stability-sprint-028-ci.json"
    cmd = [python, "scripts/ops/nightly_stability.py", "--json-out", nightly_rel]
    code, output = _run(cmd, cwd=root)
    if code != 0:
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": "Nightly stability batch failed",
            "details": {
                "command": " ".join(cmd),
                "output_tail": "\n".join(output.splitlines()[-20:]),
            },
        }

    nightly_path = root / nightly_rel
    if not nightly_path.exists():
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": "Nightly artifact was not created",
        }

    try:
        payload = json.loads(nightly_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": f"Nightly artifact JSON parse failed: {exc}",
        }

    required_keys = {
        "trend_24h",
        "trend_7d",
        "drift",
        "anomaly",
        "overall",
    }
    missing_keys = sorted(k for k in required_keys if k not in payload)
    if missing_keys:
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": f"Nightly artifact missing keys: {', '.join(missing_keys)}",
        }

    evidence_index = root / "runtime/evidence/sprint-027/evidence-index.json"
    if not evidence_index.exists():
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": "Evidence index missing after nightly run",
        }

    try:
        entries = json.loads(evidence_index.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": f"Evidence index JSON parse failed: {exc}",
        }

    if not isinstance(entries, list):
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": "Evidence index must be a JSON list",
        }

    expected_paths = {
        "runtime/ci-artifacts/nightly-stability-sprint-028-ci.json",
        "runtime/ci-artifacts/sprint-027-validation.json",
    }

    present_paths = {
        str(item.get("path", ""))
        for item in entries
        if isinstance(item, dict)
    }
    missing_paths = sorted(path for path in expected_paths if path not in present_paths)
    if missing_paths:
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": f"Evidence index missing expected paths: {', '.join(missing_paths)}",
        }

    missing_sha = [
        str(item.get("path", ""))
        for item in entries
        if isinstance(item, dict) and str(item.get("path", "")) in expected_paths and not item.get("sha256")
    ]
    if missing_sha:
        return {
            "id": "nightly_evidence_interaction",
            "ok": False,
            "hint": f"Evidence entries missing sha256: {', '.join(missing_sha)}",
        }

    return {
        "id": "nightly_evidence_interaction",
        "ok": True,
        "hint": "",
        "details": {
            "nightly_overall": payload.get("overall"),
            "anomaly_triggered": bool(payload.get("anomaly", {}).get("triggered")),
            "indexed_paths": sorted(p for p in present_paths if p in expected_paths),
        },
    }



def _collect_diagnostics(checks: list[dict]) -> dict:
    failed = [chk for chk in checks if not chk.get("ok", False)]
    severity_order = {
        "pipeline_gate": "critical",
        "regression_dashboard_nightly": "critical",
        "nightly_evidence_interaction": "critical",
        "local_tasks": "warning",
        "backlog_item": "warning",
    }

    failed_ids = [str(chk.get("id")) for chk in failed]
    critical_failed = [
        chk_id for chk_id in failed_ids if severity_order.get(chk_id, "info") == "critical"
    ]

    return {
        "failed_count": len(failed),
        "failed_ids": failed_ids,
        "critical_failed_ids": critical_failed,
    }



def validate(root: Path, run_tests: bool) -> dict:
    checks: list[dict] = []
    for rel in REQUIRED_FILES:
        checks.append(check_file_exists(root, rel))
    checks.extend(check_yaml_syntax(root))
    checks.append(check_pipeline_gate(root))
    checks.append(check_local_tasks(root))
    checks.append(check_backlog_item(root))

    if run_tests:
        checks.append(check_dashboard_regressions(root))
        checks.append(check_nightly_evidence_interaction(root))

    passed = sum(1 for c in checks if c.get("ok", False))
    total = len(checks)

    diagnostics = _collect_diagnostics(checks)

    return {
        "status": "PASS" if passed == total else "FAIL",
        "summary": f"{passed}/{total} checks passed",
        "checks": checks,
        "diagnostics": diagnostics,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint-028 CI gate hardening validator")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--json-out", help="Write JSON report to file")
    parser.add_argument("--run-tests", action="store_true", help="Run focused regressions + nightly evidence check")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root}")

    report = validate(root, run_tests=args.run_tests)

    if args.json_out:
        out_path = root / args.json_out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[sprint028_validate] Report written to {out_path}")

    print(f"[sprint028_validate] {report['status']} - {report['summary']}")
    for chk in report["checks"]:
        mark = "OK" if chk.get("ok") else "FAIL"
        hint = f"  hint: {chk['hint']}" if chk.get("hint") else ""
        print(f"  [{mark}] {chk['id']}{hint}")

    failed_ids = report.get("diagnostics", {}).get("failed_ids", [])
    if failed_ids:
        print(f"[sprint028_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
