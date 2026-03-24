"""Nightly stability batch: runs tests + sprint026_validate and writes a timestamped artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.ops.evidence_retention import apply_retention_policy, read_retention_policy_from_env
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from evidence_retention import apply_retention_policy, read_retention_policy_from_env


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def _reason_code_from_manifest(manifest: dict) -> str:
    generated = manifest.get("generated")
    failed = manifest.get("failed")
    generated_count = len(generated) if isinstance(generated, list) else 0
    failed_count = len(failed) if isinstance(failed, list) else 0

    if generated_count > 0:
        return "ARTIFACTS_READY"
    if failed_count > 0:
        return "GENERATION_FAILED"
    return "ARTIFACTS_PENDING"


def _collect_manifest_entries(root: Path) -> list[dict]:
    manifests_dir = root / "generated" / "manifests"
    if not manifests_dir.exists():
        return []

    entries: list[dict] = []
    for manifest_path in sorted(manifests_dir.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        try:
            mtime = manifest_path.stat().st_mtime
        except Exception:
            mtime = 0.0

        entries.append(
            {
                "run_id": manifest.get("run_id") or manifest_path.parent.name,
                "reason_code": _reason_code_from_manifest(manifest),
                "timestamp": mtime,
            }
        )

    return entries


def _compute_window_trend(entries: list[dict], window_seconds: int) -> dict:
    window_start = datetime.now(UTC).timestamp() - window_seconds
    scoped = [entry for entry in entries if float(entry.get("timestamp", 0.0)) >= window_start]

    by_reason_code: dict[str, int] = {}
    for entry in scoped:
        reason_code = str(entry.get("reason_code", "ARTIFACTS_PENDING"))
        by_reason_code[reason_code] = by_reason_code.get(reason_code, 0) + 1

    runs_total = len(scoped)
    success_total = by_reason_code.get("ARTIFACTS_READY", 0)
    dominant_reason_code = None
    if by_reason_code:
        dominant_reason_code = sorted(by_reason_code.items(), key=lambda item: (-int(item[1]), str(item[0])))[0][0]

    return {
        "window_hours": int(window_seconds / 3600),
        "runs_total": runs_total,
        "success_rate": round((success_total / runs_total) if runs_total else 1.0, 4),
        "error_count": int(by_reason_code.get("GENERATION_FAILED", 0)),
        "dominant_reason_code": dominant_reason_code,
        "by_reason_code": by_reason_code,
    }


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _read_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
        return parsed if parsed > 0 else default
    except ValueError:
        return default


def _compute_anomaly_signal(trend_24h: dict, trend_7d: dict) -> dict:
    min_runs_24h = _read_int_env("CTOA_ANOMALY_MIN_RUNS_24H", 4)
    success_rate_drop_threshold = _read_float_env("CTOA_ANOMALY_SUCCESS_RATE_DROP", 0.08)
    error_count_spike_threshold = _read_int_env("CTOA_ANOMALY_ERROR_COUNT_SPIKE", 2)

    runs_24h = int(trend_24h.get("runs_total", 0) or 0)
    success_rate_24h = float(trend_24h.get("success_rate", 1.0) or 1.0)
    success_rate_7d = float(trend_7d.get("success_rate", 1.0) or 1.0)
    error_count_24h = int(trend_24h.get("error_count", 0) or 0)
    error_count_7d = int(trend_7d.get("error_count", 0) or 0)

    success_rate_drop = round(success_rate_7d - success_rate_24h, 4)
    error_count_spike = error_count_24h - error_count_7d
    dominant_reason_code_shifted = trend_24h.get("dominant_reason_code") != trend_7d.get("dominant_reason_code")

    low_sample = runs_24h < min_runs_24h

    triggered_reasons: list[str] = []
    if success_rate_drop >= success_rate_drop_threshold:
        triggered_reasons.append("success_rate_drop")
    if error_count_spike >= error_count_spike_threshold:
        triggered_reasons.append("error_count_spike")

    # Ignore dominant reason shifts on small sample windows to reduce false positives.
    if dominant_reason_code_shifted and not low_sample and error_count_24h > 0:
        triggered_reasons.append("dominant_reason_shift")

    return {
        "triggered": len(triggered_reasons) > 0,
        "reasons": triggered_reasons,
        "low_sample": low_sample,
        "metrics": {
            "runs_24h": runs_24h,
            "success_rate_drop": success_rate_drop,
            "error_count_spike": error_count_spike,
            "dominant_reason_code_shifted": dominant_reason_code_shifted,
        },
        "thresholds": {
            "min_runs_24h": min_runs_24h,
            "success_rate_drop": success_rate_drop_threshold,
            "error_count_spike": error_count_spike_threshold,
        },
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _upsert_evidence_index(index_path: Path, entry: dict) -> None:
    existing: list[dict] = []
    if index_path.exists():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                existing = [item for item in payload if isinstance(item, dict)]
        except Exception:
            existing = []

    filtered = [item for item in existing if item.get("path") != entry.get("path")]
    filtered.append(entry)
    max_entries, max_age_days = read_retention_policy_from_env()
    filtered = apply_retention_policy(
        filtered,
        max_entries=max_entries,
        max_age_days=max_age_days,
    )
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(filtered, indent=2), encoding="utf-8")


def _record_evidence(root: Path, artifact_paths: list[Path]) -> None:
    index_path = root / "runtime" / "evidence" / "sprint-027" / "evidence-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for artifact_path in artifact_paths:
        if not artifact_path.exists():
            continue
        sha = _sha256_file(artifact_path)
        sha_path = index_path.parent / f"{artifact_path.name}.sha256"
        sha_path.write_text(f"{sha}  {artifact_path.name}\n", encoding="utf-8")
        _upsert_evidence_index(
            index_path,
            {
                "kind": "ci-artifact",
                "path": str(artifact_path.relative_to(root)).replace("\\", "/"),
                "sha256": sha,
                "recorded_at": recorded_at,
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="CTOA nightly stability batch")
    parser.add_argument("--root", default=".", help="Workspace root directory")
    parser.add_argument("--json-out", help="Write artifact JSON to file")
    parser.add_argument("--dry-run", action="store_true", help="Alias for normal run (always writes artifact)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    python = sys.executable

    print("[nightly_stability] Running pytest...")
    test_code, test_out = _run(
        [python, "-m", "pytest", "tests/", "--ignore=tests/e2e", "-q", "--tb=no"],
        cwd=root,
    )
    tests_passed = test_code == 0
    # parse summary line e.g. "8 passed" or "6 passed, 2 failed"
    passed_count = 0
    failed_count = 0
    for line in test_out.splitlines():
        if "passed" in line or "failed" in line or "error" in line:
            import re
            m = re.search(r"(\d+) passed", line)
            if m:
                passed_count = int(m.group(1))
            m = re.search(r"(\d+) failed", line)
            if m:
                failed_count = int(m.group(1))

    print(f"[nightly_stability] Tests: passed={passed_count} failed={failed_count}")

    print("[nightly_stability] Running sprint027_validate...")
    validator_artifact = root / "runtime" / "ci-artifacts" / "sprint-027-validation.json"
    val_script = root / "scripts" / "ops" / "sprint027_validate.py"
    val_code, val_out = _run(
        [python, str(val_script), "--run-tests", "--json-out", str(validator_artifact.relative_to(root))],
        cwd=root,
    )
    validator_status = "PASS" if val_code == 0 else "FAIL"
    print(f"[nightly_stability] Validator: {validator_status}")

    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    date_str = datetime.now(UTC).strftime("%Y%m%d")

    manifest_entries = _collect_manifest_entries(root)
    trend_24h = _compute_window_trend(manifest_entries, window_seconds=24 * 3600)
    trend_7d = _compute_window_trend(manifest_entries, window_seconds=7 * 24 * 3600)

    artifact = {
        "date": date_str,
        "timestamp": timestamp,
        "tests_passed": passed_count,
        "tests_failed": failed_count,
        "validator_status": validator_status,
        "overall": "PASS" if tests_passed and validator_status == "PASS" else "FAIL",
        "trend_24h": trend_24h,
        "trend_7d": trend_7d,
        "drift": {
            "success_rate_delta_7d_vs_24h": round(trend_7d["success_rate"] - trend_24h["success_rate"], 4),
            "error_count_delta_7d_vs_24h": int(trend_7d["error_count"] - trend_24h["error_count"]),
            "dominant_reason_code_changed": trend_24h["dominant_reason_code"] != trend_7d["dominant_reason_code"],
        },
        "anomaly": _compute_anomaly_signal(trend_24h, trend_7d),
    }

    out_path_str = args.json_out or f"runtime/ci-artifacts/nightly-stability-{date_str}.json"
    out_path = root / out_path_str if not Path(out_path_str).is_absolute() else Path(out_path_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    _record_evidence(root, [out_path, validator_artifact])
    print(f"[nightly_stability] Artifact written to {out_path}")
    print(f"[nightly_stability] Overall: {artifact['overall']}")

    return 0 if artifact["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
