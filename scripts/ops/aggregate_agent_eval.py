#!/usr/bin/env python3
"""Aggregate metrics from a JSONL evaluation result file."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "pass"}
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/ops/aggregate_agent_eval.py <results.jsonl>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Missing file: {path}")
        return 2

    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    total = len(rows)
    if total == 0:
        print("No rows found in results file.")
        return 2

    required_cov = sum(float(r.get("required_fields_coverage", 0)) for r in rows) / total
    facts_ok = sum(1 for r in rows if _as_bool(r.get("facts_vs_inference_ok", 0))) / total
    next_step_ok = sum(1 for r in rows if _as_bool(r.get("next_step_grounded", 0))) / total

    tp = fp = fn = 0
    for r in rows:
        pred = _as_bool(r.get("high_impact_detected", 0))
        exp = _as_bool(r.get("expected_high_impact", 0))
        if pred and exp:
            tp += 1
        elif pred and not exp:
            fp += 1
        elif (not pred) and exp:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    summary = {
        "total_cases": total,
        "required_fields_coverage_rate": round(required_cov, 4),
        "facts_vs_inference_compliance_rate": round(facts_ok, 4),
        "next_step_grounding_rate": round(next_step_ok, 4),
        "high_impact_detection_precision": round(precision, 4),
        "high_impact_detection_recall": round(recall, 4),
    }

    print(json.dumps(summary, indent=2))
    out_path = path.with_suffix(path.suffix + ".summary.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8-sig")
    print(f"Summary written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

