#!/usr/bin/env python3
"""Assemble a compact CTOAi evidence pack from local release and runtime artifacts.

The pack is evidence-first:
- it reads existing runtime/report files when present
- it reports missing inputs instead of guessing
- it produces both JSON and Markdown outputs for the Control Center and sign-off flows
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_RELEASES_DIR = Path("releases/evidence")
DEFAULT_JSON_OUT = Path("runtime/evidence/latest.json")
DEFAULT_MD_OUT = Path("runtime/evidence/latest.md")


def _configured_path(env_name: str, fallback: str) -> Path:
    value = os.getenv(env_name, "").strip()
    return Path(value) if value else Path(fallback)

def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"{path} must contain a JSON object")


def _count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            count += 1
    return count


def _find_latest_markdown(releases_dir: Path) -> dict[str, str] | None:
    latest: tuple[float, Path] | None = None
    if not releases_dir.exists():
        return None

    for path in releases_dir.rglob("*.md"):
        if not path.is_file():
            continue
        modified = path.stat().st_mtime
        if latest is None or modified > latest[0]:
            latest = (modified, path)

    if latest is None:
        return None

    modified_at = dt.datetime.fromtimestamp(latest[0], tz=dt.UTC).isoformat(timespec="seconds")
    return {"path": str(latest[1]).replace("\\", "/"), "modified_at": modified_at}


def _count_markdown_files(releases_dir: Path) -> int:
    if not releases_dir.exists():
        return 0
    return sum(1 for path in releases_dir.rglob("*.md") if path.is_file())


def _list_release_sprints(releases_dir: Path) -> list[dict[str, Any]]:
    if not releases_dir.exists():
        return []

    sprint_dirs = [path for path in releases_dir.iterdir() if path.is_dir() and path.name.startswith("sprint-")]
    sprint_dirs.sort(key=lambda path: path.name, reverse=True)

    result: list[dict[str, Any]] = []
    for sprint_dir in sprint_dirs[:6]:
        md_files = sorted([path for path in sprint_dir.glob("*.md") if path.is_file()])
        latest = max((path.stat().st_mtime for path in md_files), default=sprint_dir.stat().st_mtime)
        result.append(
            {
                "sprint": sprint_dir.name,
                "file_count": len(md_files),
                "latest_modified_at": dt.datetime.fromtimestamp(latest, tz=dt.UTC).isoformat(timespec="seconds"),
            }
        )
    return result


def build_evidence_pack(
    releases_dir: Path | None = None,
    quality_path: Path | None = None,
    cost_report_path: Path | None = None,
    action_audit_path: Path | None = None,
) -> dict[str, Any]:
    releases_dir = releases_dir or _configured_path("CTOA_RELEASES_DIR", "releases/evidence")
    quality_path = quality_path or _configured_path(
        "CTOA_REPO_HYGIENE_PATH",
        "runtime/repo-hygiene/local-pr-quality.json",
    )
    cost_report_path = cost_report_path or _configured_path("CTOA_API_COST_REPORT_PATH", "runtime/api-cost/latest.json")
    action_audit_path = action_audit_path or _configured_path(
        "CTOA_ACTION_AUDIT_PATH",
        "runtime/control-center/action-audit.jsonl",
    )

    latest_evidence = _find_latest_markdown(releases_dir)
    quality = _read_json(quality_path) if quality_path.exists() else None
    cost_report = _read_json(cost_report_path) if cost_report_path.exists() else None
    action_audit_count = _count_jsonl_records(action_audit_path)

    quality_status = None
    if quality is not None:
        quality_status = str(quality.get("status", "unknown"))

    cost_status = "missing" if cost_report is None else "ready"
    cost_records = int(cost_report.get("records_seen", 0)) if cost_report else 0
    total_tokens = int(cost_report.get("total_tokens", 0)) if cost_report else 0
    total_cost = float(cost_report.get("total_cost_usd", 0.0)) if cost_report else 0.0

    recommendations: list[str] = []
    if quality is None:
        recommendations.append("Run repo hygiene quality generation before sign-off.")
    elif quality_status != "PASS":
        recommendations.append("Review the repo hygiene findings before treating the pack as release-ready.")

    if cost_report is None:
        recommendations.append(f"Generate {cost_report_path} with scripts/ops/api_cost_report.py.")
    elif cost_records == 0:
        recommendations.append("Cost report exists but has no records; verify eval artifacts in evals/runs.")

    if action_audit_count == 0:
        recommendations.append("Exercise at least one Control Center action so the audit trail is visible.")

    if not recommendations:
        recommendations.append("Evidence pack is ready for review. Keep fresh traces attached to the release note.")

    return {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "releases_dir": str(releases_dir).replace("\\", "/"),
        "quality_path": str(quality_path).replace("\\", "/"),
        "cost_report_path": str(cost_report_path).replace("\\", "/"),
        "action_audit_path": str(action_audit_path).replace("\\", "/"),
        "latest_release_evidence": None
        if latest_evidence is None
        else {
            "path": latest_evidence["path"],
            "modified_at": latest_evidence["modified_at"],
        },
        "release_evidence_file_count": _count_markdown_files(releases_dir),
        "release_sprints": _list_release_sprints(releases_dir),
        "repo_hygiene": {
            "status": quality_status or "missing",
            "finding_count": int(quality.get("finding_count", 0)) if quality else 0,
            "summary": quality.get("summary", {}) if quality else {},
        },
        "api_cost_report": {
            "status": cost_status,
            "records_seen": cost_records,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "anomaly_count": len(cost_report.get("anomalies", [])) if cost_report else 0,
        },
        "control_center_audit": {
            "status": "ready" if action_audit_count else "missing",
            "record_count": action_audit_count,
        },
        "recommendations": recommendations,
    }


def render_markdown(pack: dict[str, Any]) -> str:
    latest = pack["latest_release_evidence"]
    lines = [
        "# CTOAi Evidence Pack",
        "",
        f"- Generated at (UTC): `{pack['generated_at_utc']}`",
        f"- Releases dir: `{pack['releases_dir']}`",
        f"- Release evidence files: `{pack['release_evidence_file_count']}`",
        f"- Repo hygiene status: `{pack['repo_hygiene']['status']}`",
        f"- API cost report status: `{pack['api_cost_report']['status']}`",
        f"- Control Center audit records: `{pack['control_center_audit']['record_count']}`",
    ]

    if latest is not None:
        lines.extend(
            [
                f"- Latest evidence file: `{latest['path']}`",
                f"- Latest evidence modified at: `{latest['modified_at']}`",
            ]
        )

    lines.extend(["", "## Recommendations", ""])
    for recommendation in pack["recommendations"]:
        lines.append(f"- {recommendation}")

    lines.extend(["", "## Release Sprints", ""])
    if pack["release_sprints"]:
        for sprint in pack["release_sprints"]:
            lines.append(
                f"- `{sprint['sprint']}`: {sprint['file_count']} files, latest `{sprint['latest_modified_at']}`"
            )
    else:
        lines.append("- No sprint evidence directories found.")

    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a compact evidence pack from local CTOAi artifacts.")
    parser.add_argument("--releases-dir", type=Path, default=_configured_path("CTOA_RELEASES_DIR", "releases/evidence"))
    parser.add_argument(
        "--quality-path",
        type=Path,
        default=_configured_path("CTOA_REPO_HYGIENE_PATH", "runtime/repo-hygiene/local-pr-quality.json"),
    )
    parser.add_argument(
        "--cost-report-path",
        type=Path,
        default=_configured_path("CTOA_API_COST_REPORT_PATH", "runtime/api-cost/latest.json"),
    )
    parser.add_argument(
        "--action-audit-path",
        type=Path,
        default=_configured_path("CTOA_ACTION_AUDIT_PATH", "runtime/control-center/action-audit.jsonl"),
    )
    parser.add_argument("--json-out", type=Path, default=_configured_path("CTOA_EVIDENCE_JSON_PATH", "runtime/evidence/latest.json"))
    parser.add_argument("--md-out", type=Path, default=_configured_path("CTOA_EVIDENCE_MD_PATH", "runtime/evidence/latest.md"))
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    pack = build_evidence_pack(args.releases_dir, args.quality_path, args.cost_report_path, args.action_audit_path)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(pack, indent=2), encoding="utf-8")

    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.write_text(render_markdown(pack), encoding="utf-8")

    print(json.dumps(pack, indent=2))
    print(f"JSON evidence written to: {args.json_out}")
    print(f"Markdown evidence written to: {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
