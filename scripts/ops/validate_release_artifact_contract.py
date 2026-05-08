#!/usr/bin/env python3
"""Validate release artifact sample against minimal required contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "runtime" / "release-artifact.sample.json"
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

def main() -> int:
    if not SAMPLE.exists():
        return fail(f"Missing sample artifact: {SAMPLE.relative_to(ROOT).as_posix()}")

    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))

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
