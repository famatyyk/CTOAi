#!/usr/bin/env python3
"""Generate API token and cost reports from eval run artifacts.

The report is intentionally evidence-first:
- real cost is read from run records when present
- estimated cost is used only when an explicit pricing JSON is provided
- missing prices are reported instead of guessed
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_RUNS_DIR = Path("evals/runs")
DEFAULT_JSON_OUT = Path("runtime/api-cost/latest.json")
DEFAULT_MD_OUT = Path("runtime/api-cost/latest.md")


@dataclass
class CostRecord:
    path: str
    record_id: str
    timestamp: str | None
    component: str
    variant: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None
    score: float | None


def _read_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []

    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
            else:
                raise ValueError(f"{path}:{line_no} is not a JSON object")
        return rows

    payload = json.loads(text)
    return _extract_records(payload)


def _read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            raise ValueError(f"{path}:{line_no} is not a JSON object")
    return rows


def _configured_path(env_name: str, fallback: str) -> Path:
    value = os.getenv(env_name, "").strip()
    return Path(value) if value else Path(fallback)


def _configured_path_from(env_names: list[str], fallback: str) -> Path:
    for env_name in env_names:
        value = os.getenv(env_name, "").strip()
        if value:
            return Path(value)
    return Path(fallback)


def _configured_optional_path(env_name: str) -> Path | None:
    value = os.getenv(env_name, "").strip()
    return Path(value) if value else None


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("records", "results", "rows", "runs", "evals", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return [payload]


def _nested_get(payload: dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        cur: Any = payload
        ok = True
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                ok = False
                break
            cur = cur[part]
        if ok and cur is not None:
            return cur
    return default


def _as_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        return int(float(stripped))
    return 0


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return float(stripped)
    return None


def _timestamp_to_day(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(raw).date().isoformat()
    except ValueError:
        return value[:10] if len(value) >= 10 else None


def _load_pricing(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Pricing JSON must be an object keyed by model name")

    pricing: dict[str, dict[str, float]] = {}
    for model, config in payload.items():
        if not isinstance(config, dict):
            continue
        pricing[str(model)] = {
            "input_per_1m": float(config.get("input_per_1m", config.get("input", 0.0))),
            "output_per_1m": float(config.get("output_per_1m", config.get("output", 0.0))),
        }
    return pricing


def _extract_cost_record(
    raw: dict[str, Any],
    path: Path,
    index: int,
    pricing: dict[str, dict[str, float]],
) -> CostRecord:
    model = str(_nested_get(raw, ("model", "response.model", "request.model"), "unknown"))
    component = str(_nested_get(raw, ("component", "agent", "task", "eval_name", "suite"), "unknown"))
    variant = str(_nested_get(raw, ("variant", "prompt_variant", "prompt.name", "case.variant"), "default"))

    input_tokens = _as_int(
        _nested_get(raw, ("usage.input_tokens", "usage.prompt_tokens", "prompt_tokens", "input_tokens"), 0)
    )
    output_tokens = _as_int(
        _nested_get(raw, ("usage.output_tokens", "usage.completion_tokens", "completion_tokens", "output_tokens"), 0)
    )
    total_tokens = _as_int(_nested_get(raw, ("usage.total_tokens", "total_tokens"), 0))
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    if input_tokens == 0 and output_tokens == 0 and total_tokens:
        input_tokens = total_tokens

    cost_usd = _as_float(
        _nested_get(raw, ("cost_usd", "estimated_cost_usd", "usage.cost_usd", "billing.cost_usd"), None)
    )
    if cost_usd is None and model in pricing:
        prices = pricing[model]
        cost_usd = (
            input_tokens * prices["input_per_1m"] / 1_000_000.0
            + output_tokens * prices["output_per_1m"] / 1_000_000.0
        )

    record_id = str(_nested_get(raw, ("id", "case_id", "run_id", "request_id"), f"{path.name}:{index}"))
    timestamp = _nested_get(raw, ("timestamp", "created_at", "completed_at", "time"), None)
    score = _as_float(_nested_get(raw, ("score", "quality_score", "eval.score", "metrics.score"), None))

    return CostRecord(
        path=str(path).replace("\\", "/"),
        record_id=record_id,
        timestamp=str(timestamp) if timestamp is not None else None,
        component=component,
        variant=variant,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        score=score,
    )


def load_cost_records(runs_dir: Path, pricing: dict[str, dict[str, float]] | None = None) -> list[CostRecord]:
    if not runs_dir.exists():
        return []

    pricing = pricing or {}
    records: list[CostRecord] = []
    paths = sorted(
        [
            path
            for path in runs_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
        ]
    )
    for path in paths:
        for index, raw in enumerate(_read_json_or_jsonl(path), start=1):
            record = _extract_cost_record(raw, path, index, pricing)
            if record.total_tokens or record.cost_usd is not None:
                records.append(record)
    return records


def load_eval_artifact_summary(
    dataset_path: Path | None = None,
    prompt_variants_dir: Path | None = None,
) -> dict[str, Any]:
    dataset_path = dataset_path or _configured_path(
        "CTOA_EVAL_DATASET_PATH",
        "evals/azure-activity-agent-eval-dataset.template.jsonl",
    )
    prompt_variants_dir = prompt_variants_dir or _configured_path("CTOA_PROMPT_VARIANTS_DIR", "evals/prompt-variants")
    dataset_records = _read_jsonl_records(dataset_path) if dataset_path.exists() else []
    dataset_cases = len(dataset_records)
    category_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for record in dataset_records:
        category = str(record.get("category", "unknown"))
        priority = str(record.get("priority", "unknown"))
        category_counts[category] = category_counts.get(category, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    prompt_variants = sorted(
        path.stem
        for path in prompt_variants_dir.glob("*.md")
        if path.is_file()
    ) if prompt_variants_dir.exists() else []
    return {
        "dataset_path": str(dataset_path).replace("\\", "/"),
        "dataset_cases": dataset_cases,
        "category_counts": dict(sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))),
        "priority_counts": dict(sorted(priority_counts.items(), key=lambda item: (-item[1], item[0]))),
        "prompt_variants_dir": str(prompt_variants_dir).replace("\\", "/"),
        "prompt_variant_count": len(prompt_variants),
        "prompt_variants": prompt_variants,
    }


def _sum_by(records: list[CostRecord], field: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for record in records:
        key = str(getattr(record, field))
        bucket = buckets.setdefault(
            key,
            {
                field: key,
                "records": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "missing_cost_records": 0,
            },
        )
        bucket["records"] += 1
        bucket["input_tokens"] += record.input_tokens
        bucket["output_tokens"] += record.output_tokens
        bucket["total_tokens"] += record.total_tokens
        if record.cost_usd is None:
            bucket["missing_cost_records"] += 1
        else:
            bucket["cost_usd"] += record.cost_usd

    return sorted(buckets.values(), key=lambda item: (item["cost_usd"], item["total_tokens"]), reverse=True)


def build_report(
    records: list[CostRecord],
    runs_dir: Path,
    anomaly_threshold: float,
    dataset_path: Path | None = None,
    prompt_variants_dir: Path | None = None,
) -> dict[str, Any]:
    total_tokens = sum(record.total_tokens for record in records)
    total_cost = sum(record.cost_usd or 0.0 for record in records)
    records_with_cost = sum(1 for record in records if record.cost_usd is not None)
    days = sorted({day for day in (_timestamp_to_day(record.timestamp) for record in records) if day})
    day_count = max(len(days), 1) if records else 0

    by_component = _sum_by(records, "component")
    by_model = _sum_by(records, "model")
    by_variant = _sum_by(records, "variant")
    eval_artifacts = load_eval_artifact_summary(dataset_path, prompt_variants_dir)

    anomalies: list[dict[str, Any]] = []
    for bucket in by_component:
        token_share = (bucket["total_tokens"] / total_tokens) if total_tokens else 0.0
        cost_share = (bucket["cost_usd"] / total_cost) if total_cost else 0.0
        if token_share >= anomaly_threshold or cost_share >= anomaly_threshold:
            anomalies.append(
                {
                    "component": bucket["component"],
                    "token_share": round(token_share, 4),
                    "cost_share": round(cost_share, 4),
                    "total_tokens": bucket["total_tokens"],
                    "cost_usd": round(bucket["cost_usd"], 6),
                }
            )

    top_component = by_component[0] if by_component else None
    reduction_pct = 0.0
    if top_component and total_tokens:
        reduction_pct = min(35.0, round((top_component["total_tokens"] / total_tokens) * 25.0, 2))

    recommendations = _build_recommendations(records, anomalies, records_with_cost, reduction_pct, eval_artifacts)

    report = {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "source_dir": str(runs_dir).replace("\\", "/"),
        "records_seen": len(records),
        "records_with_cost": records_with_cost,
        "records_missing_cost": len(records) - records_with_cost,
        "total_input_tokens": sum(record.input_tokens for record in records),
        "total_output_tokens": sum(record.output_tokens for record in records),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "avg_cost_per_1k_tokens": round((total_cost / total_tokens) * 1000.0, 6) if total_tokens else None,
        "token_burn_per_day": round(total_tokens / day_count, 2) if day_count else 0.0,
        "cost_burn_per_day_usd": round(total_cost / day_count, 6) if day_count else 0.0,
        "token_burn_reduction_pct": reduction_pct,
        "eval_artifacts": eval_artifacts,
        "by_component": by_component,
        "by_model": by_model,
        "by_variant": by_variant,
        "anomalies": anomalies,
        "top_records": [
            {
                "record_id": record.record_id,
                "component": record.component,
                "variant": record.variant,
                "model": record.model,
                "total_tokens": record.total_tokens,
                "cost_usd": None if record.cost_usd is None else round(record.cost_usd, 6),
                "path": record.path,
            }
            for record in sorted(records, key=lambda item: (item.cost_usd or 0.0, item.total_tokens), reverse=True)[:10]
        ],
        "recommendations": recommendations,
    }
    return report


def _build_recommendations(
    records: list[CostRecord],
    anomalies: list[dict[str, Any]],
    records_with_cost: int,
    reduction_pct: float,
    eval_artifacts: dict[str, Any],
) -> list[str]:
    if not records:
        return [
            "Create evals/runs/ and store JSON or JSONL run artifacts with usage.total_tokens or cost_usd fields.",
            f"Use the existing eval dataset at {eval_artifacts['dataset_path']} to keep the run corpus anchored.",
            "Add cost_usd to eval records or run this report with --pricing-json for explicit local estimates.",
        ]

    recommendations: list[str] = []
    if records_with_cost < len(records):
        recommendations.append(
            "Some records have token usage but no cost_usd; add billing export data or provide --pricing-json before treating dollars as final."
        )
    if anomalies:
        names = ", ".join(item["component"] for item in anomalies[:3])
        recommendations.append(
            f"Investigate high-share component(s): {names}; projected targeted token reduction is {reduction_pct:.2f}%."
        )
    else:
        recommendations.append("No component crossed the anomaly threshold; keep collecting per-run usage evidence.")
    recommendations.append("Use APICostOptimizerAgent recommendations as guarded proposals, not automatic model downgrades.")
    return recommendations


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CTOAi API Cost Report",
        "",
        f"- Generated at (UTC): `{report['generated_at_utc']}`",
        f"- Source dir: `{report['source_dir']}`",
        f"- Records: `{report['records_seen']}`",
        f"- Total tokens: `{report['total_tokens']}`",
        f"- Total cost USD: `{report['total_cost_usd']}`",
        f"- Token burn / day: `{report['token_burn_per_day']}`",
        f"- Cost burn / day USD: `{report['cost_burn_per_day_usd']}`",
        f"- Suggested targeted token reduction: `{report['token_burn_reduction_pct']}%`",
        "",
        "## Top Components",
        "",
        "| Component | Records | Tokens | Cost USD | Missing Cost Records |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in report["by_component"][:10]:
        lines.append(
            f"| {item['component']} | {item['records']} | {item['total_tokens']} | {item['cost_usd']:.6f} | {item['missing_cost_records']} |"
        )

    lines.extend(["", "## Recommendations", ""])
    for recommendation in report["recommendations"]:
        lines.append(f"- {recommendation}")

    lines.extend(["", "## Eval Artifacts", ""])
    lines.append(f"- Dataset cases: `{report['eval_artifacts']['dataset_cases']}`")
    lines.append(f"- Prompt variants: `{report['eval_artifacts']['prompt_variant_count']}`")
    if report["eval_artifacts"]["prompt_variants"]:
        lines.append(f"- Variant names: `{', '.join(report['eval_artifacts']['prompt_variants'])}`")

    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate API cost report from evals/runs artifacts.")
    parser.add_argument("--runs-dir", type=Path, default=_configured_path("CTOA_API_COST_RUNS_DIR", "evals/runs"))
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=_configured_path(
            "CTOA_EVAL_DATASET_PATH",
            "evals/azure-activity-agent-eval-dataset.template.jsonl",
        ),
    )
    parser.add_argument(
        "--prompt-variants-dir",
        type=Path,
        default=_configured_path("CTOA_PROMPT_VARIANTS_DIR", "evals/prompt-variants"),
    )
    parser.add_argument("--pricing-json", type=Path, default=_configured_optional_path("CTOA_API_COST_PRICING_JSON"))
    parser.add_argument("--json-out", type=Path, default=_configured_path("CTOA_API_COST_JSON_OUT", "runtime/api-cost/latest.json"))
    parser.add_argument(
        "--md-out",
        type=Path,
        default=_configured_path_from(["CTOA_API_COST_MD_OUT", "CTOA_API_COST_MD_PATH"], "runtime/api-cost/latest.md"),
    )
    parser.add_argument("--anomaly-threshold", type=float, default=float(os.getenv("CTOA_API_COST_ANOMALY_THRESHOLD", "0.30")))
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    pricing = _load_pricing(args.pricing_json)
    records = load_cost_records(args.runs_dir, pricing)
    report = build_report(records, args.runs_dir, args.anomaly_threshold, args.dataset_path, args.prompt_variants_dir)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(render_markdown(report), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"JSON report written to: {args.json_out}")
    print(f"Markdown report written to: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
