#!/usr/bin/env python3
"""CTOA auto trainer.

Runs periodic training analysis from DB and writes versioned reports.
Designed for systemd timer execution every 6 hours.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from runner.agents import db
except ModuleNotFoundError:
    import sys
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from runner.agents import db

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(os.environ.get("CTOA_TRAINING_REPORT_DIR", str(ROOT / "runtime" / "training-reports")))

AGENTS = [
    "scout_agent",
    "ingest_agent",
    "brain_v2",
    "generator_agent",
    "validator_agent",
    "publisher_agent",
    "prompt_forge",
    "tool_advisor",
    "orchestrator",
    "queen_ctoa",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return db.query_all(sql, params)


def _row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    return db.query_one(sql, params)


def _quality_state() -> dict[str, Any]:
    row = _row(
        "SELECT dt, modules_generated, programs_generated, avg_quality, launcher_day "
        "FROM daily_stats ORDER BY dt DESC LIMIT 1"
    )
    if not row:
        return {
            "quality": 0.0,
            "modules": 0,
            "programs": 0,
            "launcher_day": False,
            "date": None,
        }
    return {
        "quality": float(row.get("avg_quality") or 0.0),
        "modules": int(row.get("modules_generated") or 0),
        "programs": int(row.get("programs_generated") or 0),
        "launcher_day": bool(row.get("launcher_day") or False),
        "date": str(row.get("dt")),
    }


def _failed_templates(limit: int = 8) -> list[dict[str, Any]]:
    return _rows(
        "SELECT template, COUNT(*) AS failures "
        "FROM modules WHERE status='FAILED' "
        "GROUP BY template ORDER BY failures DESC LIMIT %s",
        (limit,),
    )


def _recent_runs(limit: int = 60) -> list[dict[str, Any]]:
    return _rows(
        "SELECT agent, status, finished_at FROM agent_runs "
        "ORDER BY id DESC LIMIT %s",
        (limit,),
    )


def _success_ratio(runs: list[dict[str, Any]], agent: str) -> float:
    subset = [r for r in runs if str(r.get("agent")) == agent]
    if not subset:
        return 0.0
    ok = sum(1 for r in subset if str(r.get("status")) == "ok")
    return ok / len(subset)


def _recommendations(quality: dict[str, Any], failed: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, list[str]]:
    q = float(quality.get("quality") or 0.0)
    failed_templates = [str(x.get("template")) for x in failed if x.get("template")]

    rec: dict[str, list[str]] = {k: [] for k in AGENTS}

    if q < 85:
        rec["prompt_forge"].append("Increase constraints: edge cases + negative tests + explicit output contract")
        rec["validator_agent"].append("Tighten semantic checks for runtime safety")
        rec["generator_agent"].append("Prioritize deterministic output and remove unstable branches")
    elif q < 92:
        rec["prompt_forge"].append("Refine prompts for stability and TODO/FIXME elimination")
        rec["generator_agent"].append("Focus on first-pass pass rate improvements")
    else:
        rec["prompt_forge"].append("Keep quality baseline and optimize token cost per successful module")

    if failed_templates:
        top = ", ".join(failed_templates[:3])
        rec["brain_v2"].append(f"Reduce queue priority for unstable templates: {top}")
        rec["validator_agent"].append(f"Add targeted checks for templates: {top}")

    scout_ratio = _success_ratio(runs, "scout_agent")
    if scout_ratio < 0.80:
        rec["scout_agent"].append("Expand profile-specific probe paths and improve retries")
        rec["ingest_agent"].append("Harden no-data fallback and partial-ingest behavior")

    if _success_ratio(runs, "publisher_agent") < 0.95:
        rec["publisher_agent"].append("Improve release readiness checks before launcher gate")

    rec["tool_advisor"].append("Re-rank model/tools by quality-to-cost ratio from last 24h")
    rec["orchestrator"].append("Preserve graceful degradation when one stage reports errors")
    rec["queen_ctoa"].append("Review quality trend and enforce GO/NO-GO policy")

    for agent in AGENTS:
        if not rec[agent]:
            rec[agent].append("No urgent change; continue current strategy and monitor drift")

    return rec


def _render_markdown(quality: dict[str, Any], failed: list[dict[str, Any]], runs: list[dict[str, Any]], rec: dict[str, list[str]]) -> str:
    now = _now().replace(microsecond=0).isoformat()
    lines: list[str] = []
    lines.append("# CTOA Auto Trainer Report")
    lines.append("")
    lines.append(f"- generated_at: {now}")
    lines.append(f"- daily_stats_date: {quality.get('date')}")
    lines.append(f"- avg_quality: {quality.get('quality'):.2f}")
    lines.append(f"- modules_generated: {quality.get('modules')}")
    lines.append(f"- programs_generated: {quality.get('programs')}")
    lines.append(f"- launcher_day: {quality.get('launcher_day')}")
    lines.append("")

    lines.append("## Failure Hotspots")
    if not failed:
        lines.append("- none")
    else:
        for item in failed:
            lines.append(f"- {item.get('template')}: {item.get('failures')} failures")
    lines.append("")

    lines.append("## Agent Success Ratios (recent runs)")
    for agent in ["scout_agent", "ingest_agent", "brain_v2", "generator_agent", "validator_agent", "publisher_agent"]:
        ratio = _success_ratio(runs, agent)
        lines.append(f"- {agent}: {ratio*100:.1f}%")
    lines.append("")

    lines.append("## Training Actions")
    for agent in AGENTS:
        lines.append(f"### {agent}")
        for action in rec.get(agent, []):
            lines.append(f"- {action}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _write_reports(markdown: str, payload: dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now().strftime("%Y%m%d-%H%M%S")
    md_path = REPORT_DIR / f"auto-trainer-{stamp}.md"
    json_path = REPORT_DIR / f"auto-trainer-{stamp}.json"
    latest_md = REPORT_DIR / "latest.md"
    latest_json = REPORT_DIR / "latest.json"

    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    latest_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return md_path


def main() -> int:
    quality = _quality_state()
    failed = _failed_templates()
    runs = _recent_runs()
    rec = _recommendations(quality, failed, runs)

    report_payload = {
        "generated_at": _now().replace(microsecond=0).isoformat(),
        "quality": quality,
        "failed_templates": failed,
        "recommendations": rec,
    }
    markdown = _render_markdown(quality, failed, runs, rec)
    path = _write_reports(markdown, report_payload)

    msg = f"auto trainer report: {path.name}, quality={quality.get('quality', 0.0):.2f}"
    db.log_run("auto_trainer", "ok", msg)
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
