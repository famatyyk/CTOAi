#!/usr/bin/env python3
"""Exercise the bounded P7 safe-write MCP tools in dry-run mode.

The smoke talks to the local CTOAi Engine Brain plugin over stdio, calls only
the allowed safe-write tools with dry_run=true, and verifies that each
call appended a sanitized Control Center action-audit record.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_ROOT = Path.home() / "plugins" / "ctoai-engine-brain"
DEFAULT_ACTION_AUDIT_PATH = Path("runtime/control-center/action-audit.jsonl")
DEFAULT_JSON_OUT = Path("runtime/control-center/p7-safe-write-dry-run-smoke.json")
DEFAULT_MD_OUT = Path("runtime/control-center/p7-safe-write-dry-run-smoke.md")
MAX_STDOUT_BYTES = 2 * 1024 * 1024
MAX_JSONL_BYTES = 1024 * 1024
MAX_JSONL_LINE_BYTES = 20 * 1024
EXPECTED_SAFE_WRITE_TOOLS = [
    ("repo-hygiene-refresh", "ctoai_repo_hygiene_refresh"),
    ("api-cost-refresh", "ctoai_api_cost_refresh"),
    ("evidence-pack-refresh", "ctoai_evidence_pack_refresh"),
    ("engine-brain-refresh", "ctoai_engine_brain_refresh"),
    ("p7-cockpit-smoke-refresh", "ctoai_p7_cockpit_smoke_refresh"),
    ("roadmap-state-refresh", "ctoai_roadmap_state_refresh"),
    (
        "full-workspace-validation-refresh",
        "ctoai_full_workspace_validation_refresh",
    ),
]
EXPECTED_READ_ONLY_TOOLS = {
    "ctoai_control_central",
    "ctoai_engine_brain_status",
    "ctoai_engine_brain_self_check",
    "ctoai_engine_brain_brief",
    "ctoai_control_center_cockpit",
}
FORBIDDEN_TOOL_FRAGMENTS = ("deploy", "live", "promote", "solteria")
FINALIZABLE_BOOTSTRAP_BLOCKERS = {
    "freshness:evidence:stale",
    "p6_plugin_handoff_smoke_not_ready",
    "p7_operator_brief_not_ready",
    "p7_safe_write_audit_not_ready",
    "p7_cockpit_smoke_not_ready",
    "p7_safe_write_dry_run_smoke_not_ready",
    "runtime_evidence_integrity_not_verified",
}


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
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"{path} exceeds {max_bytes} bytes")
    return data.decode("utf-8", errors="replace")


def read_jsonl_tail(path: Path) -> list[dict[str, Any]]:
    file_stat = safe_file_stat(path)
    if file_stat is None:
        return []
    with path.open("rb") as handle:
        if file_stat.st_size > MAX_JSONL_BYTES:
            handle.seek(max(0, file_stat.st_size - MAX_JSONL_BYTES))
            handle.readline()
        data = handle.read(MAX_JSONL_BYTES)
    records: list[dict[str, Any]] = []
    for raw_line in data.splitlines():
        if len(raw_line) > MAX_JSONL_LINE_BYTES:
            continue
        try:
            payload = json.loads(raw_line.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def plugin_command(plugin_root: Path) -> list[str]:
    config_path = plugin_root / ".mcp.json"
    config = json.loads(read_text_bounded(config_path, 128 * 1024))
    servers = config.get("mcpServers") if isinstance(config, dict) else {}
    server = servers.get("ctoai-engine-brain") if isinstance(servers, dict) else {}
    args = server.get("args") if isinstance(server, dict) else []
    command = server.get("command") if isinstance(server, dict) else ""
    if not isinstance(command, str) or not isinstance(args, list):
        raise ValueError("Invalid ctoai-engine-brain MCP config")
    safe_args = [str(item) for item in args]
    if command.lower() in {"python", "python.exe", "py"}:
        command = sys.executable
    script_args = [plugin_root / item for item in safe_args if item.endswith(".py")]
    for script in script_args:
        if safe_file_stat(script) is None:
            raise FileNotFoundError(script)
    return [command, *safe_args]


def mcp_messages(root: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ctoa-p7-dry-run-smoke", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    for index, (_action_id, tool_name) in enumerate(EXPECTED_SAFE_WRITE_TOOLS, start=3):
        messages.append(
            {
                "jsonrpc": "2.0",
                "id": index,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {
                        "workspace": str(root),
                        "dry_run": True,
                        "reason": "P7 safe-write dry-run smoke",
                    },
                },
            }
        )
    return messages


def parse_mcp_responses(stdout: str) -> dict[int, dict[str, Any]]:
    responses: dict[int, dict[str, Any]] = {}
    if len(stdout.encode("utf-8", errors="replace")) > MAX_STDOUT_BYTES:
        raise ValueError("MCP stdout exceeded bounded parser limit")
    for line in stdout.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict) and isinstance(payload.get("id"), int):
            responses[int(payload["id"])] = payload
    return responses


def tool_text_payload(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    content = result.get("content") if isinstance(result.get("content"), list) else []
    if not content or not isinstance(content[0], dict):
        return {}
    text = content[0].get("text")
    if not isinstance(text, str):
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def latest_record_by_audit_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_audit: dict[str, dict[str, Any]] = {}
    for record in records:
        audit_id = str(record.get("audit_id") or "")
        if audit_id:
            by_audit[audit_id] = record
    return by_audit


def latest_record_by_action(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_action: dict[str, dict[str, Any]] = {}
    for record in records:
        action = str(record.get("action") or "")
        if action:
            by_action[action] = record
    return by_action


def preflight_bootstrap_allowed(preflight: dict[str, Any]) -> bool:
    return (
        preflight.get("dry_run_bootstrap_allowed") is True
        or preflight.get("bootstrap_allowed") is True
    )


def finalizable_bootstrap_preflight(preflight: dict[str, Any]) -> bool:
    blockers = {
        str(item)
        for item in preflight.get("hard_blockers", [])
        if str(item).strip()
    }
    return (
        preflight_bootstrap_allowed(preflight)
        and bool(blockers)
        and blockers.issubset(FINALIZABLE_BOOTSTRAP_BLOCKERS)
    )


def add_check(
    checks: list[dict[str, str]],
    name: str,
    passed: bool,
    evidence: str,
    blocker: str,
) -> None:
    checks.append(
        {
            "name": name,
            "status": "passed" if passed else "blocked",
            "evidence": evidence,
            "blocker": "" if passed else blocker,
        }
    )


def build_report(root: Path, plugin_root: Path) -> dict[str, Any]:
    root = root.resolve()
    plugin_root = plugin_root.resolve()
    command = plugin_command(plugin_root)
    messages = mcp_messages(root)
    action_audit_path = root / DEFAULT_ACTION_AUDIT_PATH
    prior_audit_ids = {
        str(record.get("audit_id") or "")
        for record in read_jsonl_tail(action_audit_path)
        if str(record.get("audit_id") or "")
    }
    completed = subprocess.run(
        command,
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        cwd=plugin_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    responses = parse_mcp_responses(completed.stdout)
    checks: list[dict[str, str]] = []
    hard_blockers: list[str] = []
    warnings: list[str] = []

    add_check(
        checks,
        "mcp_process",
        completed.returncode == 0,
        display_path(plugin_root / ".mcp.json", root),
        "mcp_process_failed",
    )
    if completed.stderr.strip():
        warnings.append("mcp_stderr")

    tools_response = responses.get(2, {})
    tools_result = (
        tools_response.get("result")
        if isinstance(tools_response.get("result"), dict)
        else {}
    )
    tools = tools_result.get("tools") if isinstance(tools_result.get("tools"), list) else []
    tool_names = [
        str(tool.get("name"))
        for tool in tools
        if isinstance(tool, dict) and tool.get("name")
    ]
    forbidden_tools = [
        name
        for name in tool_names
        if any(fragment in name.lower() for fragment in FORBIDDEN_TOOL_FRAGMENTS)
    ]
    expected_tool_names = {tool for _action, tool in EXPECTED_SAFE_WRITE_TOOLS}
    add_check(
        checks,
        "mcp_tool_policy",
        EXPECTED_READ_ONLY_TOOLS.issubset(set(tool_names))
        and expected_tool_names.issubset(set(tool_names))
        and not forbidden_tools,
        f"tools={len(tool_names)}",
        "mcp_tool_policy_mismatch",
    )

    audit_records = read_jsonl_tail(action_audit_path)
    records_by_audit = latest_record_by_audit_id(audit_records)
    new_records_by_action = latest_record_by_action(
        [
            record
            for record in audit_records
            if str(record.get("audit_id") or "") not in prior_audit_ids
        ]
    )
    safe_write_results: list[dict[str, Any]] = []
    for index, (action_id, tool_name) in enumerate(EXPECTED_SAFE_WRITE_TOOLS, start=3):
        payload = tool_text_payload(responses.get(index, {}))
        preflight = (
            payload.get("preflight")
            if isinstance(payload.get("preflight"), dict)
            else {}
        )
        audit_id = str(payload.get("audit_id") or "")
        record = (
            records_by_audit.get(audit_id, {})
            if audit_id
            else new_records_by_action.get(action_id, {})
        )
        bootstrap_allowed = preflight_bootstrap_allowed(preflight)
        preflight_ready = (
            preflight.get("ok") is True
            or bootstrap_allowed
        )
        projected_payload_ready = (
            payload.get("schema_version") == 2
            and payload.get("audit_recorded") is True
            and payload.get("result_code") == "plan_recorded"
        )
        legacy_payload_ready = (
            payload.get("schema_version") == 1
            and "DRY RUN ONLY" in str(payload.get("output") or "")
        )
        payload_ready = (
            payload.get("status") == "dry_run"
            and payload.get("action") == action_id
            and payload.get("tool") == tool_name
            and payload.get("risk_class") == "safe_write"
            and payload.get("dry_run") is True
            and payload.get("ok") is True
            and preflight_ready
            and (projected_payload_ready or legacy_payload_ready)
        )
        add_check(
            checks,
            f"{action_id}_payload",
            payload_ready,
            tool_name,
            f"{action_id}_payload_not_ready",
        )
        record_ready = (
            record.get("action") == action_id
            and record.get("risk_class") == "safe_write"
            and record.get("dry_run") is True
            and record.get("authorized") is True
            and record.get("ok") is True
        )
        add_check(
            checks,
            f"{action_id}_audit",
            record_ready,
            display_path(action_audit_path, root),
            f"{action_id}_audit_not_ready",
        )
        safe_write_results.append(
            {
                "action_id": action_id,
                "mcp_tool": tool_name,
                "status": str(payload.get("status") or "missing"),
                "ok": payload.get("ok") is True,
                "dry_run": payload.get("dry_run") is True,
                "audit_record_ready": record_ready,
                "preflight_status": str(preflight.get("status") or "missing"),
                "preflight_ok": preflight.get("ok") is True,
                "preflight_bootstrap_allowed": bootstrap_allowed,
                "preflight_bootstrap_used": False,
                "preflight_hard_blockers": [
                    str(item)
                    for item in preflight.get("hard_blockers", [])
                    if str(item).strip()
                ],
                "preflight_finalizable": finalizable_bootstrap_preflight(preflight),
            }
        )

    all_dry_run_audits_ready = (
        len(safe_write_results) == len(EXPECTED_SAFE_WRITE_TOOLS)
        and all(
            item["status"] == "dry_run"
            and item["dry_run"]
            and item["ok"]
            and item["audit_record_ready"]
            for item in safe_write_results
        )
    )
    if all_dry_run_audits_ready:
        for item in safe_write_results:
            if (
                not item["preflight_ok"]
                and item["preflight_bootstrap_allowed"]
                and item["preflight_finalizable"]
            ):
                item["preflight_ok"] = True
                item["preflight_bootstrap_used"] = True
                item["preflight_bootstrap_allowed"] = False

    for check in checks:
        if check["status"] != "passed" and check["blocker"]:
            hard_blockers.append(check["blocker"])

    hard_blockers = sorted(set(hard_blockers))
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "status": "ready" if not hard_blockers else "blocked",
        "policy": "Dry-run-only smoke for bounded P7 safe-write MCP tools. It never confirms or executes refresh commands.",
        "hard_blockers": hard_blockers,
        "warnings": sorted(set(warnings)),
        "summary": {
            "checks": len(checks),
            "passed": sum(1 for check in checks if check["status"] == "passed"),
            "blocked": sum(1 for check in checks if check["status"] != "passed"),
            "safe_write_tool_count": len(EXPECTED_SAFE_WRITE_TOOLS),
            "dry_run_ready_count": sum(
                1
                for item in safe_write_results
                if item["status"] == "dry_run" and item["audit_record_ready"]
            ),
            "preflight_ready_count": sum(
                1
                for item in safe_write_results
                if item["status"] == "dry_run"
                and item["audit_record_ready"]
                and item["preflight_ok"]
            ),
            "bootstrap_allowed_count": sum(
                1
                for item in safe_write_results
                if item["preflight_bootstrap_allowed"]
            ),
        },
        "checks": checks,
        "safe_write_results": safe_write_results,
        "source_paths": {
            "plugin_root": display_path(plugin_root, root),
            "mcp_config": display_path(plugin_root / ".mcp.json", root),
            "action_audit": display_path(action_audit_path, root),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Control Center P7 Safe-Write Dry-Run Smoke",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        report["policy"],
        "",
        "## Summary",
        "",
        f"- Checks: `{report['summary']['passed']}/{report['summary']['checks']}` passed.",
        f"- Dry-run ready tools: `{report['summary']['dry_run_ready_count']}/{report['summary']['safe_write_tool_count']}`.",
        f"- Preflight-ready tools: `{report['summary'].get('preflight_ready_count', 0)}/{report['summary']['safe_write_tool_count']}`.",
        f"- Bootstrap-allowed tools: `{report['summary'].get('bootstrap_allowed_count', 0)}`.",
        "",
        "## Safe-Write Results",
        "",
        "| Action | Tool | Status | Audit ready | Preflight | Bootstrap |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in report["safe_write_results"]:
        lines.append(
            f"| `{result['action_id']}` | `{result['mcp_tool']}` | `{result['status']}` | `{result['audit_record_ready']}` | `{result.get('preflight_ok', False)}` | `{result.get('preflight_bootstrap_allowed', False)}` |"
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
        description="Run dry-run-only smoke for P7 safe-write MCP tools."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--plugin-root", type=Path, default=DEFAULT_PLUGIN_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    report = build_report(args.root, args.plugin_root)
    if not args.no_write:
        write_outputs(args.root.resolve(), report, args.json_out, args.md_out)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
