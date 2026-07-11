#!/usr/bin/env python3
"""Review confirmed P7 evidence before the next plugin action is designed."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OPERATOR_BRIEF_PATH = Path("AI/generated/P7_OPERATOR_BRIEF.json")
DEFAULT_RELEASE_EVIDENCE_PATH = Path("runtime/evidence/latest.json")
DEFAULT_ACTION_AUDIT_PATH = Path("runtime/control-center/action-audit.jsonl")
DEFAULT_P7_COCKPIT_SMOKE_PATH = Path("runtime/control-center/p7-cockpit-smoke.json")
DEFAULT_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH = Path(
    "runtime/control-center/p7-safe-write-dry-run-smoke.json"
)
DEFAULT_P6_HANDOFF_SMOKE_PATH = Path("runtime/control-center/p6-plugin-handoff-smoke.json")
DEFAULT_JSON_OUT = Path("runtime/control-center/p7-evidence-review.json")
DEFAULT_MD_OUT = Path("runtime/control-center/p7-evidence-review.md")

MAX_JSON_BYTES = 1024 * 1024
MAX_JSONL_BYTES = 1024 * 1024
MAX_JSONL_LINE_BYTES = 20 * 1024
SELECTED_ACTION_ID = "evidence-pack-refresh"
SELECTED_MCP_TOOL = "ctoai_evidence_pack_refresh"


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return "[external]/" + path.name


def workspace_path(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def assert_inside_workspace(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{path} must stay inside the workspace") from exc


def safe_file_stat(path: Path) -> os.stat_result | None:
    try:
        file_stat = path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(file_stat.st_mode):
        return None
    return file_stat


def read_text_bounded(path: Path, max_bytes: int) -> str:
    file_stat = safe_file_stat(path)
    if file_stat is None:
        raise FileNotFoundError(path)
    if file_stat.st_size > max_bytes:
        raise ValueError(f"{path} is too large to read safely")
    with path.open("rb") as handle:
        opened_stat = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"{path} is not a regular file")
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"{path} is too large to read safely")
    return raw.decode("utf-8-sig")


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(read_text_bounded(path, MAX_JSON_BYTES))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def read_jsonl_tail(path: Path) -> tuple[list[dict[str, Any]], int, list[str]]:
    file_stat = safe_file_stat(path)
    if file_stat is None:
        return [], 0, [f"missing:{path.name}"]
    requested_bytes = min(file_stat.st_size, MAX_JSONL_BYTES)
    start = max(0, file_stat.st_size - requested_bytes)
    warnings: list[str] = []
    with path.open("rb") as handle:
        opened_stat = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened_stat.st_mode):
            return [], 0, [f"not_regular:{path.name}"]
        handle.seek(start)
        raw = handle.read(requested_bytes)
    text = raw.decode("utf-8-sig", errors="replace")
    if start > 0:
        _, _, text = text.partition("\n")
        warnings.append("audit_tail_sampled")
    records: list[dict[str, Any]] = []
    total_lines = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        total_lines += 1
        if len(line.encode("utf-8", errors="ignore")) > MAX_JSONL_LINE_BYTES:
            warnings.append("audit_line_too_large")
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            warnings.append("audit_invalid_json_line")
            continue
        if isinstance(value, dict):
            records.append(value)
    return records, total_lines, sorted(set(warnings))


def add_check(
    checks: list[dict[str, str]],
    name: str,
    passed: bool,
    evidence: str,
    blocker: str = "",
) -> None:
    checks.append(
        {
            "name": name,
            "status": "passed" if passed else "blocked",
            "evidence": evidence,
            "blocker": "" if passed else blocker,
        }
    )


def latest_confirmed_evidence_refresh(records: list[dict[str, Any]]) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for record in records:
        if record.get("action") != SELECTED_ACTION_ID:
            continue
        if record.get("dry_run") is True:
            continue
        if record.get("risk_class") != "safe_write":
            continue
        if record.get("authorized") is not True or record.get("ok") is not True:
            continue
        latest = record
    return latest


def p7_cockpit_evidence_audit(payload: dict[str, Any]) -> dict[str, Any]:
    audits = payload.get("safe_write_audits")
    if not isinstance(audits, list):
        return {}
    for audit in audits:
        if isinstance(audit, dict) and audit.get("action_id") == SELECTED_ACTION_ID:
            return audit
    return {}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary")
    return value if isinstance(value, dict) else {}


def build_report(
    root: Path = ROOT,
    *,
    operator_brief_path: Path = DEFAULT_OPERATOR_BRIEF_PATH,
    release_evidence_path: Path = DEFAULT_RELEASE_EVIDENCE_PATH,
    action_audit_path: Path = DEFAULT_ACTION_AUDIT_PATH,
    p7_cockpit_smoke_path: Path = DEFAULT_P7_COCKPIT_SMOKE_PATH,
    p7_safe_write_dry_run_smoke_path: Path = DEFAULT_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH,
    p6_handoff_smoke_path: Path = DEFAULT_P6_HANDOFF_SMOKE_PATH,
) -> dict[str, Any]:
    root = root.resolve()
    paths = {
        "operator_brief": workspace_path(root, operator_brief_path),
        "release_evidence": workspace_path(root, release_evidence_path),
        "action_audit": workspace_path(root, action_audit_path),
        "p7_cockpit_smoke": workspace_path(root, p7_cockpit_smoke_path),
        "p7_safe_write_dry_run_smoke": workspace_path(root, p7_safe_write_dry_run_smoke_path),
        "p6_handoff_smoke": workspace_path(root, p6_handoff_smoke_path),
    }
    for path in paths.values():
        assert_inside_workspace(root, path)

    checks: list[dict[str, str]] = []
    hard_blockers: list[str] = []
    warnings: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}

    for name, path in paths.items():
        if name == "action_audit":
            continue
        try:
            payloads[name] = read_json_object(path)
            add_check(checks, f"read_{name}", True, display_path(path, root))
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            blocker = f"missing_or_invalid_{name}"
            hard_blockers.append(blocker)
            add_check(checks, f"read_{name}", False, display_path(path, root), blocker)
            payloads[name] = {}

    audit_records, audit_line_count, audit_warnings = read_jsonl_tail(
        paths["action_audit"]
    )
    warnings.extend(audit_warnings)
    latest_audit = latest_confirmed_evidence_refresh(audit_records)
    latest_audit_id = str(latest_audit.get("audit_id") or "")
    latest_audit_at = str(latest_audit.get("at") or latest_audit.get("created_at") or "")

    operator_brief = payloads["operator_brief"]
    release_evidence = payloads["release_evidence"]
    release_brief = (
        release_evidence.get("p7_operator_brief")
        if isinstance(release_evidence.get("p7_operator_brief"), dict)
        else {}
    )
    release_audit = (
        release_evidence.get("control_center_audit")
        if isinstance(release_evidence.get("control_center_audit"), dict)
        else {}
    )
    p7_smoke = payloads["p7_cockpit_smoke"]
    p7_smoke_summary = summary(p7_smoke)
    p7_smoke_audit = p7_cockpit_evidence_audit(p7_smoke)
    dry_run_smoke = payloads["p7_safe_write_dry_run_smoke"]
    dry_summary = summary(dry_run_smoke)
    p6_smoke = payloads["p6_handoff_smoke"]
    p6_summary = summary(p6_smoke)

    next_safe_command = str(operator_brief.get("next_safe_command") or "")
    add_check(
        checks,
        "operator_brief_review_or_design_ready",
        operator_brief.get("status") == "ready"
        and operator_brief.get("decision") == "ready_for_p7_operator_workflow"
        and not operator_brief.get("hard_blockers")
        and (
            "Review confirmed evidence-pack-refresh audit" in next_safe_command
            or "Design the next P7 plugin action" in next_safe_command
        ),
        display_path(paths["operator_brief"], root),
        "operator_brief_not_ready_for_p7_review",
    )
    add_check(
        checks,
        "confirmed_evidence_pack_audit_ready",
        bool(latest_audit_id),
        f"audit_id={latest_audit_id or 'missing'} lines={audit_line_count}",
        "missing_confirmed_evidence_pack_audit",
    )
    add_check(
        checks,
        "release_evidence_matches_operator_brief",
        release_brief.get("status") == "ready"
        and release_brief.get("decision") == "ready_for_p7_operator_workflow"
        and release_brief.get("generated_at") == operator_brief.get("generated_at")
        and int(release_brief.get("hard_blocker_count") or 0) == 0
        and release_audit.get("status") == "ready",
        display_path(paths["release_evidence"], root),
        "release_evidence_not_confirmed_for_p7",
    )
    add_check(
        checks,
        "p7_cockpit_smoke_includes_confirmed_audit",
        p7_smoke.get("status") == "ready"
        and p7_smoke_summary.get("passed") == p7_smoke_summary.get("checks")
        and int(p7_smoke_summary.get("blocked") or 0) == 0
        and p7_smoke_audit.get("audit_id") == latest_audit_id
        and p7_smoke_audit.get("dry_run") is False,
        display_path(paths["p7_cockpit_smoke"], root),
        "p7_cockpit_smoke_missing_confirmed_audit",
    )
    safe_write_tool_count = int(dry_summary.get("safe_write_tool_count") or 0)
    add_check(
        checks,
        "p7_safe_write_dry_run_smoke_ready",
        dry_run_smoke.get("status") == "ready"
        and safe_write_tool_count > 0
        and dry_summary.get("passed") == dry_summary.get("checks")
        and int(dry_summary.get("blocked") or 0) == 0
        and int(dry_summary.get("dry_run_ready_count") or 0) == safe_write_tool_count
        and int(dry_summary.get("preflight_ready_count") or 0) == safe_write_tool_count
        and int(dry_summary.get("bootstrap_allowed_count") or 0) == 0,
        display_path(paths["p7_safe_write_dry_run_smoke"], root),
        "p7_safe_write_dry_run_smoke_not_ready",
    )
    add_check(
        checks,
        "p6_plugin_handoff_ready",
        p6_smoke.get("status") == "ready"
        and p6_summary.get("passed") == p6_summary.get("checks")
        and int(p6_summary.get("blocked") or 0) == 0,
        display_path(paths["p6_handoff_smoke"], root),
        "p6_plugin_handoff_not_ready",
    )

    for check in checks:
        if check["status"] != "passed" and check["blocker"]:
            hard_blockers.append(check["blocker"])

    hard_blockers = sorted(set(hard_blockers))
    ready = not hard_blockers
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "status": "ready" if ready else "blocked",
        "outcome": (
            "ready_to_design_next_p7_plugin_action"
            if ready
            else "review_blocked"
        ),
        "policy": "Read-only review gate for confirmed P7 evidence before any new plugin action is designed.",
        "selected_action_id": SELECTED_ACTION_ID,
        "selected_mcp_tool": SELECTED_MCP_TOOL,
        "hard_blockers": hard_blockers,
        "warnings": sorted(set(warnings)),
        "summary": {
            "checks": len(checks),
            "passed": sum(1 for check in checks if check["status"] == "passed"),
            "blocked": sum(1 for check in checks if check["status"] != "passed"),
            "action_audit_line_count": audit_line_count,
            "confirmed_audit_id": latest_audit_id,
            "confirmed_audit_at": latest_audit_at,
            "release_evidence_generated_at": str(
                release_evidence.get("generated_at_utc") or ""
            ),
            "p7_cockpit_smoke_generated_at": str(p7_smoke.get("generated_at") or ""),
            "p6_handoff_smoke_generated_at": str(p6_smoke.get("generated_at") or ""),
        },
        "checks": checks,
        "next_action": (
            "Design the next P7/P6 plugin action only after risk model coverage, audit logging, Control Center gates, and targeted MCP tests exist."
            if ready
            else "Fix P7 evidence review blockers before adding another plugin action."
        ),
        "source_paths": {name: display_path(path, root) for name, path in paths.items()},
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Control Center P7 Evidence Review",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        f"Outcome: `{report['outcome']}`",
        "",
        report["policy"],
        "",
        "## Summary",
        "",
        f"- Checks: `{report['summary']['passed']}/{report['summary']['checks']}` passed.",
        f"- Confirmed audit: `{report['summary']['confirmed_audit_id'] or 'missing'}`.",
        f"- Action audit lines: `{report['summary']['action_audit_line_count']}`.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| `{check['name']}` | `{check['status']}` | {check['evidence']} |")
    if report["hard_blockers"]:
        lines.extend(["", "## Hard Blockers", ""])
        lines.extend(f"- `{item}`" for item in report["hard_blockers"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{item}`" for item in report["warnings"])
    lines.extend(["", "## Next Action", "", report["next_action"], ""])
    return "\n".join(lines)


def write_outputs(root: Path, report: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_path = workspace_path(root, json_out)
    md_path = workspace_path(root, md_out)
    assert_inside_workspace(root, json_path)
    assert_inside_workspace(root, md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review confirmed P7 evidence before the next plugin action."
    )
    parser.add_argument("--root", "--workspace", dest="root", type=Path, default=ROOT)
    parser.add_argument("--json-out", "--output", dest="json_out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    report = build_report(args.root)
    if not args.no_write:
        write_outputs(args.root.resolve(), report, args.json_out, args.md_out)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
