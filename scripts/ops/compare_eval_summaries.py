#!/usr/bin/env python3
"""Compare multiple eval summary files and choose the best variant."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_KEYS = (
    "required_fields_coverage_rate",
    "facts_vs_inference_compliance_rate",
    "next_step_grounding_rate",
    "high_impact_detection_precision",
    "high_impact_detection_recall",
)


def _variant_from_path(path: Path) -> str:
    name = path.name
    if name.startswith("results."):
        parts = name.split(".")
        if len(parts) >= 4:
            return parts[1]
    return path.stem


def _load_summary(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise ValueError(f"Missing keys in {path}: {', '.join(missing)}")
    payload["variant"] = payload.get("variant") or _variant_from_path(path)
    payload["path"] = str(path).replace('\\', '/')
    return payload


def _score_key(summary: dict) -> tuple:
    return (
        float(summary["high_impact_detection_precision"]),
        float(summary["high_impact_detection_recall"]),
        float(summary["facts_vs_inference_compliance_rate"]),
        float(summary["required_fields_coverage_rate"]),
        float(summary["next_step_grounding_rate"]),
        summary["variant"],
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/ops/compare_eval_summaries.py <summary1.json> <summary2.json> ..."
        )
        return 2

    paths = [Path(arg) for arg in sys.argv[1:]]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(json.dumps({"error": "missing_files", "paths": missing}, indent=2))
        return 2

    summaries = [_load_summary(path) for path in paths]
    winner = sorted(summaries, key=_score_key, reverse=True)[0]

    result = {
        "winner": winner["variant"],
        "winner_path": winner["path"],
        "comparison_order": [
            "high_impact_detection_precision",
            "high_impact_detection_recall",
            "facts_vs_inference_compliance_rate",
            "required_fields_coverage_rate",
            "next_step_grounding_rate",
        ],
        "summaries": summaries,
    }

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
