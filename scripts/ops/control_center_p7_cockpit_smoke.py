#!/usr/bin/env python3
"""Validate the read-only Control Center P7 cockpit evidence contract.

This smoke is intentionally file-backed and read-only. It proves that the
generated P7 operator brief, release evidence pack, and Control Center action
audit agree before P6/P7 work is treated as operator-ready.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = Path("AI/generated/manifest.json")
DEFAULT_WORKFLOW_PATH = Path("AI/generated/P7_OPERATOR_WORKFLOW.json")
DEFAULT_ACTION_READINESS_PATH = Path("AI/generated/P7_ACTION_READINESS.json")
DEFAULT_SAFE_WRITE_DESIGN_PATH = Path("AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.json")
DEFAULT_OPERATOR_BRIEF_PATH = Path("AI/generated/P7_OPERATOR_BRIEF.json")
DEFAULT_RELEASE_EVIDENCE_PATH = Path("runtime/evidence/latest.json")
DEFAULT_ACTION_AUDIT_PATH = Path("runtime/control-center/action-audit.jsonl")
DEFAULT_JSON_OUT = Path("runtime/control-center/p7-cockpit-smoke.json")
DEFAULT_MD_OUT = Path("runtime/control-center/p7-cockpit-smoke.md")

MAX_JSON_BYTES = 1024 * 1024
MAX_JSONL_BYTES = 1024 * 1024
MAX_JSONL_LINE_BYTES = 20 * 1024

EXPECTED_SAFE_WRITE_ACTIONS = {
    "repo-hygiene-refresh": "ctoai_repo_hygiene_refresh",
    "api-cost-refresh": "ctoai_api_cost_refresh",
    "evidence-pack-refresh": "ctoai_evidence_pack_refresh",
    "engine-brain-refresh": "ctoai_engine_brain_refresh",
    "p7-cockpit-smoke-refresh": "ctoai_p7_cockpit_smoke_refresh",
}
EXPECTED_READ_ONLY_TOOLS = {
    "ctoai_engine_brain_status",
    "ctoai_engine_brain_self_check",
    "ctoai_engine_brain_brief",
    "ctoai_control_center_cockpit",
}
FORBIDDEN_TOOL_FRAGMENTS = ("deploy", "live", "promote", "solteria")


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
    try:
        with path.open("rb") as handle:
            opened_stat = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_stat.st_mode):
                return [], 0, [f"not_regular:{path.name}"]
            handle.seek(start)
            raw = handle.read(requested_bytes)
    except OSError as exc:
        return [], 0, [f"read_failed:{exc.__class__.__name__}"]
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
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    evidence: str,
    blocker: str = "",
) -> None:
    checks.append(
        {
            "name": name,
            "status": "passed" if ok else "blocked",
            "evidence": evidence,
            "blocker": blocker,
        }
    )


def tool_names(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return names


def enabled_safe_write_tools(payload: dict[str, Any]) -> dict[str, str]:
    tools: dict[str, str] = {}
    for item in payload.get("enabled_safe_write_tools", []):
        if isinstance(item, dict):
            action_id = str(item.get("action_id") or "")
            mcp_tool = str(item.get("mcp_tool") or "")
            if action_id and mcp_tool:
                tools[action_id] = mcp_tool
    return tools


def action_id_for_record(record: dict[str, Any]) -> str:
    return str(record.get("action") or record.get("action_id") or "")


def mcp_tool_for_action(action_id: str) -> str:
    return EXPECTED_SAFE_WRITE_ACTIONS.get(action_id, "")


def audit_records_by_action(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_action: dict[str, dict[str, Any]] = {}
    for record in records:
        action_id = action_id_for_record(record)
        if action_id not in EXPECTED_SAFE_WRITE_ACTIONS:
            continue
        previous = by_action.get(action_id)
        ready = (
            record.get("risk_class") == "safe_write"
            and record.get("authorized") is True
            and record.get("ok") is True
        )
        previous_ready = bool(previous and previous.get("ready") is True)
        if previous is None or ready or not previous_ready:
            by_action[action_id] = {
                "action_id": action_id,
                "mcp_tool": mcp_tool_for_action(action_id),
                "ready": ready,
                "authorized": record.get("authorized"),
                "ok": record.get("ok"),
                "dry_run": record.get("dry_run"),
                "risk_class": str(record.get("risk_class") or ""),
                "at": str(record.get("at") or record.get("created_at") or ""),
                "audit_id": str(record.get("audit_id") or ""),
            }
    return by_action


def build_report(
    root: Path = ROOT,
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    workflow_path: Path = DEFAULT_WORKFLOW_PATH,
    action_readiness_path: Path = DEFAULT_ACTION_READINESS_PATH,
    safe_write_design_path: Path = DEFAULT_SAFE_WRITE_DESIGN_PATH,
    operator_brief_path: Path = DEFAULT_OPERATOR_BRIEF_PATH,
    release_evidence_path: Path = DEFAULT_RELEASE_EVIDENCE_PATH,
    action_audit_path: Path = DEFAULT_ACTION_AUDIT_PATH,
) -> dict[str, Any]:
    root = root.resolve()
    paths = {
        "manifest": workspace_path(root, manifest_path),
        "operator_workflow": workspace_path(root, workflow_path),
        "action_readiness": workspace_path(root, action_readiness_path),
        "safe_write_design": workspace_path(root, safe_write_design_path),
        "operator_brief": workspace_path(root, operator_brief_path),
        "release_evidence": workspace_path(root, release_evidence_path),
        "action_audit": workspace_path(root, action_audit_path),
    }
    for path in paths.values():
        assert_inside_workspace(root, path)

    checks: list[dict[str, Any]] = []
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

    manifest = payloads["manifest"]
    add_check(
        checks,
        "manifest_p6_p7_ready",
        manifest.get("doc_sync_status") == "passed"
        and manifest.get("secret_guardrail_status") == "passed"
        and manifest.get("p6_readiness_status") == "ready_for_plugin_design"
        and manifest.get("p7_operator_workflow_status") == "safe_write_ready"
        and manifest.get("p7_action_readiness_status") == "safe_write_tools_enabled"
        and manifest.get("p7_safe_write_tool_design_status") == "implemented"
        and manifest.get("p7_operator_brief_status") == "ready",
        "manifest doc_sync/secret/P6/P7 status",
        "manifest_not_p6_p7_ready",
    )

    operator_brief = payloads["operator_brief"]
    brief_blockers = operator_brief.get("hard_blockers", [])
    add_check(
        checks,
        "operator_brief_ready",
        operator_brief.get("status") == "ready"
        and operator_brief.get("decision") == "ready_for_p7_operator_workflow"
        and isinstance(brief_blockers, list)
        and len(brief_blockers) == 0,
        display_path(paths["operator_brief"], root),
        "operator_brief_not_ready",
    )
    roadmap_generation = (
        operator_brief.get("roadmap_generation")
        if isinstance(operator_brief.get("roadmap_generation"), dict)
        else {}
    )
    add_check(
        checks,
        "operator_brief_roadmap_generation",
        roadmap_generation.get("status") == "ready"
        and roadmap_generation.get("doc_sync_status") == "passed"
        and int(roadmap_generation.get("ready_doc_count") or 0) == 3
        and int(roadmap_generation.get("doc_count") or 0) == 3
        and not roadmap_generation.get("hard_blockers"),
        display_path(paths["operator_brief"], root),
        "operator_brief_roadmap_generation_not_ready",
    )

    workflow = payloads["operator_workflow"]
    allowed_tools = tool_names(workflow.get("allowed_mcp_tools"))
    safe_write_tool_names = [
        item.get("name")
        for item in workflow.get("allowed_mcp_tools", [])
        if isinstance(item, dict) and item.get("risk_class") == "safe_write"
    ]
    forbidden_tools = [
        name
        for name in allowed_tools
        if any(fragment in name.lower() for fragment in FORBIDDEN_TOOL_FRAGMENTS)
    ]
    add_check(
        checks,
        "workflow_tool_policy",
        workflow.get("status") == "safe_write_ready"
        and set(EXPECTED_READ_ONLY_TOOLS).issubset(set(allowed_tools))
        and set(safe_write_tool_names) == set(EXPECTED_SAFE_WRITE_ACTIONS.values())
        and len(allowed_tools)
        == len(EXPECTED_READ_ONLY_TOOLS) + len(EXPECTED_SAFE_WRITE_ACTIONS)
        and not forbidden_tools,
        f"allowed={len(allowed_tools)} safe_write={len(safe_write_tool_names)}",
        "workflow_tool_policy_mismatch",
    )

    action_readiness = payloads["action_readiness"]
    enabled_tools = enabled_safe_write_tools(action_readiness)
    add_check(
        checks,
        "action_readiness_safe_write_tools",
        action_readiness.get("status") == "safe_write_tools_enabled"
        and action_readiness.get("candidate_count") == len(EXPECTED_SAFE_WRITE_ACTIONS)
        and action_readiness.get("audited_candidate_count")
        == len(EXPECTED_SAFE_WRITE_ACTIONS)
        and enabled_tools == EXPECTED_SAFE_WRITE_ACTIONS
        and not action_readiness.get("unexpected_mcp_write_tools"),
        f"enabled={len(enabled_tools)} audited={action_readiness.get('audited_candidate_count')}",
        "action_readiness_not_ready",
    )

    safe_write_design = payloads["safe_write_design"]
    add_check(
        checks,
        "safe_write_design_ready",
        safe_write_design.get("status") == "implemented"
        and safe_write_design.get("decision") == "ready_for_dry_run_operation"
        and safe_write_design.get("mode") == "dry_run_first"
        and safe_write_design.get("mcp_enabled") is True
        and safe_write_design.get("risk_class") == "safe_write"
        and safe_write_design.get("proposed_mcp_tool")
        in set(EXPECTED_SAFE_WRITE_ACTIONS.values()),
        display_path(paths["safe_write_design"], root),
        "safe_write_design_not_ready",
    )

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
    if (
        release_brief.get("generated_at")
        and operator_brief.get("generated_at")
        and release_brief.get("generated_at") != operator_brief.get("generated_at")
    ):
        warnings.append("release_evidence_operator_brief_timestamp_mismatch")
    add_check(
        checks,
        "release_evidence_p7_cockpit",
        release_brief.get("status") == "ready"
        and release_brief.get("decision") == "ready_for_p7_operator_workflow"
        and int(release_brief.get("hard_blocker_count") or 0) == 0
        and isinstance(release_brief.get("roadmap_generation"), dict)
        and release_brief["roadmap_generation"].get("status") == "ready"
        and release_audit.get("status") == "ready"
        and int(release_audit.get("record_count") or 0) >= 3,
        display_path(paths["release_evidence"], root),
        "release_evidence_not_p7_ready",
    )

    audit_records, audit_line_count, audit_warnings = read_jsonl_tail(
        paths["action_audit"]
    )
    warnings.extend(audit_warnings)
    latest_audits = audit_records_by_action(audit_records)
    ready_audit_count = sum(1 for audit in latest_audits.values() if audit["ready"])
    add_check(
        checks,
        "action_audit_safe_write_ready",
        ready_audit_count == len(EXPECTED_SAFE_WRITE_ACTIONS),
        f"ready={ready_audit_count}/{len(EXPECTED_SAFE_WRITE_ACTIONS)} lines={audit_line_count}",
        "action_audit_missing_ready_safe_write_record",
    )

    for check in checks:
        if check["status"] != "passed" and check["blocker"]:
            hard_blockers.append(str(check["blocker"]))

    hard_blockers = sorted(set(hard_blockers))
    status = "ready" if not hard_blockers else "blocked"
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "status": status,
        "policy": "Read-only P7 cockpit smoke validates generated Engine Brain, release evidence, and Control Center action audit state.",
        "hard_blockers": hard_blockers,
        "warnings": sorted(set(warnings)),
        "summary": {
            "checks": len(checks),
            "passed": sum(1 for check in checks if check["status"] == "passed"),
            "blocked": sum(1 for check in checks if check["status"] != "passed"),
            "allowed_mcp_tool_count": len(allowed_tools),
            "enabled_safe_write_tool_count": len(enabled_tools),
            "ready_safe_write_audit_count": ready_audit_count,
            "expected_safe_write_audit_count": len(EXPECTED_SAFE_WRITE_ACTIONS),
            "action_audit_line_count": audit_line_count,
        },
        "checks": checks,
        "safe_write_audits": [
            latest_audits.get(
                action_id,
                {
                    "action_id": action_id,
                    "mcp_tool": mcp_tool,
                    "ready": False,
                    "authorized": None,
                    "ok": None,
                    "dry_run": None,
                    "risk_class": "",
                    "at": "",
                    "audit_id": "",
                },
            )
            for action_id, mcp_tool in EXPECTED_SAFE_WRITE_ACTIONS.items()
        ],
        "source_paths": {
            name: display_path(path, root) for name, path in paths.items()
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Control Center P7 Cockpit Smoke",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        report["policy"],
        "",
        "## Summary",
        "",
        f"- Checks: `{report['summary']['passed']}/{report['summary']['checks']}` passed.",
        f"- Safe-write audits: `{report['summary']['ready_safe_write_audit_count']}/{report['summary']['expected_safe_write_audit_count']}` ready.",
        f"- Enabled safe-write MCP tools: `{report['summary']['enabled_safe_write_tool_count']}`.",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['status']}` | {check['evidence']} |"
        )
    lines.extend(["", "## Safe-Write Audits", "", "| Action | Tool | Ready | Latest |", "| --- | --- | --- | --- |"])
    for audit in report["safe_write_audits"]:
        lines.append(
            f"| `{audit['action_id']}` | `{audit['mcp_tool']}` | `{audit['ready']}` | `{audit['at'] or 'missing'}` |"
        )
    if report["hard_blockers"]:
        lines.extend(["", "## Hard Blockers", ""])
        lines.extend(f"- `{item}`" for item in report["hard_blockers"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{item}`" for item in report["warnings"])
    lines.append("")
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
        description="Validate read-only Control Center P7 cockpit evidence."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
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
