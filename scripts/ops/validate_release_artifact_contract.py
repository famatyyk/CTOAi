#!/usr/bin/env python3
"""Validate release artifact sample against minimal required contract."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "sprint",
    "generated_at",
    "release_version",
    "baseline_version",
    "wave_1",
    "wave_2",
    "artifacts",
]

def fail(msg: str) -> int:
    print(msg)
    return 1


def resolve_sample() -> Path | None:
    env_sample = os.environ.get("CTOA_RELEASE_ARTIFACT_SAMPLE")
    candidates = []
    if env_sample:
        candidates.append(Path(env_sample))
    candidates.extend(
        [
            ROOT / "docs" / "release-artifact.sample.json",
            ROOT / "runtime" / "release-artifact.sample.json",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    sample = resolve_sample()
    if sample is None:
        return fail(
            "Missing sample artifact. Checked: docs/release-artifact.sample.json, runtime/release-artifact.sample.json"
        )

    payload = json.loads(sample.read_text(encoding="utf-8"))

    for key in REQUIRED:
        if key not in payload:
            return fail(f"Missing required key: {key}")

    if not isinstance(payload["artifacts"], list):
        return fail("artifacts must be an array")

    wave_1 = payload["wave_1"]
    wave_2 = payload["wave_2"]
    if not isinstance(wave_1, dict) or "status" not in wave_1:
        return fail("wave_1.status is required")
    if not isinstance(wave_2, dict) or "status" not in wave_2:
        return fail("wave_2.status is required")

    print("Release artifact contract validation passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
