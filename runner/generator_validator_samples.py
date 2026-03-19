#!/usr/bin/env python3
"""Export sample generator/validator artifacts for CI uploads.

This script never fails hard when data is missing. It emits placeholder files,
so CI can always upload a predictable artifact bundle.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_latest_manifest(manifests_dir: Path) -> dict[str, Any] | None:
    latest = manifests_dir / "latest.json"
    if not latest.exists():
        return None
    try:
        latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None

    run_id = str(latest_payload.get("run_id", "")).strip()
    manifest_path = Path(str(latest_payload.get("manifest_path", "")).strip())
    if not manifest_path.exists() and run_id:
        candidate = manifests_dir / run_id / "manifest.json"
        if candidate.exists():
            manifest_path = candidate
    if not manifest_path.exists():
        return None

    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return {
        "run_id": run_id or manifest_payload.get("run_id"),
        "manifest_path": str(manifest_path),
        "manifest": manifest_payload,
    }


def build_generator_sample(latest_manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not latest_manifest:
        return {
            "ok": False,
            "generated_at": now_iso(),
            "reason": "No generator manifest found",
            "generated_count": 0,
            "sample": [],
        }

    manifest = latest_manifest.get("manifest") or {}
    generated = manifest.get("generated") if isinstance(manifest, dict) else []
    if not isinstance(generated, list):
        generated = []

    sample = []
    for row in generated[:20]:
        if not isinstance(row, dict):
            continue
        sample.append(
            {
                "task_id": row.get("task_id"),
                "template": row.get("template"),
                "output_file": row.get("output_file"),
                "output_path": row.get("output_path"),
                "queued_at": row.get("queued_at"),
                "generated_at": row.get("generated_at"),
            }
        )

    return {
        "ok": True,
        "generated_at": now_iso(),
        "run_id": latest_manifest.get("run_id"),
        "manifest_path": latest_manifest.get("manifest_path"),
        "generated_count": len(generated),
        "sample": sample,
    }


def build_validator_sample(latest_manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not latest_manifest:
        return {
            "ok": False,
            "generated_at": now_iso(),
            "reason": "No generator manifest found",
            "failed_count": 0,
            "failed_modules": [],
        }

    manifest = latest_manifest.get("manifest") or {}
    failed = manifest.get("failed") if isinstance(manifest, dict) else []
    if not isinstance(failed, list):
        failed = []

    trimmed_failed = []
    for row in failed[:20]:
        if not isinstance(row, dict):
            continue
        trimmed_failed.append(
            {
                "task_id": row.get("task_id"),
                "template": row.get("template"),
                "error": row.get("error"),
                "queued_at": row.get("queued_at"),
            }
        )

    return {
        "ok": True,
        "generated_at": now_iso(),
        "run_id": latest_manifest.get("run_id"),
        "failed_count": len(failed),
        "failed_modules": trimmed_failed,
        "note": "Detailed validator quality data is stored in DB modules table (quality_score, test_log, validated_at).",
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def write_markdown(path: Path, generator_payload: dict[str, Any], validator_payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Generator + Validator Sample Artifacts")
    lines.append("")
    lines.append(f"- Generated at: {now_iso()}")
    lines.append(f"- Generator sample available: {generator_payload.get('ok')}")
    lines.append(f"- Validator sample available: {validator_payload.get('ok')}")
    lines.append("")
    lines.append("## Generator")
    lines.append(f"- Run ID: {generator_payload.get('run_id', '-')}")
    lines.append(f"- Generated count: {generator_payload.get('generated_count', 0)}")
    lines.append("")
    lines.append("## Validator")
    lines.append(f"- Failed count: {validator_payload.get('failed_count', 0)}")
    lines.append(f"- Note: {validator_payload.get('note', validator_payload.get('reason', 'n/a'))}")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifests_dir = Path(os.getenv("CTOA_GENERATOR_MANIFEST_DIR", "/opt/ctoa/generated/manifests"))
    out_dir = Path(os.getenv("CTOA_ARTIFACTS_DIR", "runtime/ci-artifacts/generator-validator"))

    latest_manifest = load_latest_manifest(manifests_dir)
    generator_payload = build_generator_sample(latest_manifest)
    validator_payload = build_validator_sample(latest_manifest)

    write_json(out_dir / "generator-sample.json", generator_payload)
    write_json(out_dir / "validator-sample.json", validator_payload)
    write_markdown(out_dir / "summary.md", generator_payload, validator_payload)

    print(f"[generator-validator-samples] wrote artifacts to {out_dir}")


if __name__ == "__main__":
    main()
