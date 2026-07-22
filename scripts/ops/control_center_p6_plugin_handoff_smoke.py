#!/usr/bin/env python3
"""Validate the read-only P6 plugin handoff evidence contract.

This smoke is file-backed and read-only. It proves that the generated P6
readiness artifact, installed plugin manifest, P7 operator brief, and P7 smoke
evidence agree before the operator treats P6 as ready for fresh-thread plugin
verification.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN_ROOT = Path.home() / "plugins" / "ctoai-engine-brain"
DEFAULT_P6_READINESS_PATH = Path("AI/generated/P6_CODEX_INTEGRATION_READINESS.json")
DEFAULT_OPERATOR_WORKFLOW_PATH = Path("AI/generated/P7_OPERATOR_WORKFLOW.json")
DEFAULT_OPERATOR_BRIEF_PATH = Path("AI/generated/P7_OPERATOR_BRIEF.json")
DEFAULT_P7_COCKPIT_SMOKE_PATH = Path("runtime/control-center/p7-cockpit-smoke.json")
DEFAULT_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH = Path(
    "runtime/control-center/p7-safe-write-dry-run-smoke.json"
)
DEFAULT_JSON_OUT = Path("runtime/control-center/p6-plugin-handoff-smoke.json")
DEFAULT_MD_OUT = Path("runtime/control-center/p6-plugin-handoff-smoke.md")

MAX_JSON_BYTES = 1024 * 1024
EXPECTED_READ_ONLY_TOOLS = {
    "ctoai_control_central",
    "ctoai_engine_brain_status",
    "ctoai_engine_brain_self_check",
    "ctoai_engine_brain_brief",
    "ctoai_control_center_cockpit",
}
EXPECTED_SAFE_WRITE_TOOLS = {
    "ctoai_repo_hygiene_refresh",
    "ctoai_api_cost_refresh",
    "ctoai_evidence_pack_refresh",
    "ctoai_engine_brain_refresh",
    "ctoai_p7_cockpit_smoke_refresh",
    "ctoai_roadmap_state_refresh",
    "ctoai_full_workspace_validation_refresh",
}
EXPECTED_BLOCKED_CLASSES = {"guarded_write", "dangerous", "forbidden_ui"}
FORBIDDEN_TOOL_FRAGMENTS = ("deploy", "live", "promote", "solteria")


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return "[external]/" + path.name


def plugin_display_path(path: Path) -> str:
    parts = path.parts
    if "ctoai-engine-brain" in parts:
        index = parts.index("ctoai-engine-brain")
        return "[external]/" + "/".join(parts[index:])
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
            "blocker": "" if ok else blocker,
        }
    )


def checks_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return []
    return [check for check in checks if isinstance(check, dict)]


def check_by_name(checks: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for check in checks:
        if str(check.get("name") or "") == name:
            return check
    return None


def installed_cache_version(check: dict[str, Any] | None) -> str:
    if not check:
        return ""
    match = re.search(r"version\s+([A-Za-z0-9.+_-]+)", str(check.get("evidence") or ""))
    return match.group(1) if match else ""


def plugin_mcp_server(payload: dict[str, Any]) -> dict[str, Any]:
    servers = payload.get("mcpServers")
    if not isinstance(servers, dict):
        return {}
    server = servers.get("ctoai-engine-brain")
    return server if isinstance(server, dict) else {}


def plugin_mcp_absolute_script_ready(plugin_root: Path, payload: dict[str, Any]) -> bool:
    server = plugin_mcp_server(payload)
    args = server.get("args") if isinstance(server.get("args"), list) else []
    expected_script = plugin_root / "scripts" / "ctoai_engine_brain_mcp.py"
    try:
        expected_resolved = expected_script.resolve(strict=True)
    except OSError:
        return False
    for arg in args:
        if not isinstance(arg, str):
            continue
        arg_path = Path(arg)
        if not arg_path.is_absolute():
            continue
        try:
            if arg_path.resolve(strict=True) == expected_resolved:
                return True
        except OSError:
            continue
    return False


def allowed_tools(payload: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    tools = payload.get("allowed_mcp_tools")
    read_only: list[str] = []
    safe_write: list[str] = []
    all_tools: list[str] = []
    if not isinstance(tools, list):
        return read_only, safe_write, all_tools
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "")
        risk_class = str(tool.get("risk_class") or "")
        if not name:
            continue
        all_tools.append(name)
        if risk_class == "read_only":
            read_only.append(name)
        if risk_class == "safe_write":
            safe_write.append(name)
    return read_only, safe_write, all_tools


def blocked_classes(payload: dict[str, Any]) -> set[str]:
    classes: set[str] = set()
    for item in payload.get("blocked_action_classes", []):
        if isinstance(item, dict) and item.get("risk_class"):
            classes.add(str(item["risk_class"]))
    return classes


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary")
    return value if isinstance(value, dict) else {}


def build_report(
    root: Path = ROOT,
    *,
    plugin_root: Path | None = None,
    p6_readiness_path: Path = DEFAULT_P6_READINESS_PATH,
    operator_workflow_path: Path = DEFAULT_OPERATOR_WORKFLOW_PATH,
    operator_brief_path: Path = DEFAULT_OPERATOR_BRIEF_PATH,
    p7_cockpit_smoke_path: Path = DEFAULT_P7_COCKPIT_SMOKE_PATH,
    p7_safe_write_dry_run_smoke_path: Path = DEFAULT_P7_SAFE_WRITE_DRY_RUN_SMOKE_PATH,
) -> dict[str, Any]:
    root = root.resolve()
    if plugin_root is None:
        configured_plugin_root = os.environ.get("CTOAI_ENGINE_BRAIN_PLUGIN_ROOT")
        plugin_root = (
            Path(configured_plugin_root).expanduser()
            if configured_plugin_root
            else DEFAULT_PLUGIN_ROOT
        )
    plugin_root = plugin_root.resolve()
    paths = {
        "p6_readiness": workspace_path(root, p6_readiness_path),
        "operator_workflow": workspace_path(root, operator_workflow_path),
        "operator_brief": workspace_path(root, operator_brief_path),
        "p7_cockpit_smoke": workspace_path(root, p7_cockpit_smoke_path),
        "p7_safe_write_dry_run_smoke": workspace_path(
            root, p7_safe_write_dry_run_smoke_path
        ),
    }
    for path in paths.values():
        assert_inside_workspace(root, path)
    plugin_manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    plugin_mcp_path = plugin_root / ".mcp.json"

    checks: list[dict[str, Any]] = []
    hard_blockers: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}

    for name, path in paths.items():
        try:
            payloads[name] = read_json_object(path)
            add_check(checks, f"read_{name}", True, display_path(path, root))
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            blocker = f"missing_or_invalid_{name}"
            hard_blockers.append(blocker)
            add_check(checks, f"read_{name}", False, display_path(path, root), blocker)
            payloads[name] = {}

    try:
        plugin_manifest = read_json_object(plugin_manifest_path)
        add_check(
            checks,
            "read_plugin_manifest",
            True,
            plugin_display_path(plugin_manifest_path),
        )
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        plugin_manifest = {}
        hard_blockers.append("missing_or_invalid_plugin_manifest")
        add_check(
            checks,
            "read_plugin_manifest",
            False,
            plugin_display_path(plugin_manifest_path),
            "missing_or_invalid_plugin_manifest",
        )

    try:
        plugin_mcp_config = read_json_object(plugin_mcp_path)
        add_check(
            checks,
            "read_plugin_mcp_config",
            True,
            plugin_display_path(plugin_mcp_path),
        )
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        plugin_mcp_config = {}
        hard_blockers.append("missing_or_invalid_plugin_mcp_config")
        add_check(
            checks,
            "read_plugin_mcp_config",
            False,
            plugin_display_path(plugin_mcp_path),
            "missing_or_invalid_plugin_mcp_config",
        )

    mcp_server = plugin_mcp_server(plugin_mcp_config)
    add_check(
        checks,
        "plugin_mcp_absolute_script_ready",
        mcp_server.get("type") == "stdio"
        and mcp_server.get("command") == "python"
        and plugin_mcp_absolute_script_ready(plugin_root, plugin_mcp_config),
        plugin_display_path(plugin_root / "scripts" / "ctoai_engine_brain_mcp.py"),
        "plugin_mcp_start_path_not_runnable",
    )

    p6_readiness = payloads["p6_readiness"]
    p6_checks = checks_from_payload(p6_readiness)
    p6_passed_count = sum(1 for check in p6_checks if check.get("status") == "passed")
    p6_blocked_count = sum(1 for check in p6_checks if check.get("status") != "passed")
    marketplace_check = check_by_name(p6_checks, "ctoai_plugin_marketplace_entry")
    installed_cache_check = check_by_name(p6_checks, "ctoai_plugin_installed_cache")
    mcp_contract_checks = [
        check for check in p6_checks if "_mcp_contract" in str(check.get("name") or "")
    ]
    passed_mcp_contract_count = sum(
        1 for check in mcp_contract_checks if check.get("status") == "passed"
    )
    cache_version = installed_cache_version(installed_cache_check)

    add_check(
        checks,
        "p6_readiness_ready",
        p6_readiness.get("status") == "ready_for_plugin_design"
        and p6_checks
        and p6_blocked_count == 0,
        f"checks={p6_passed_count}/{len(p6_checks)}",
        "p6_readiness_not_ready",
    )
    add_check(
        checks,
        "p6_marketplace_ready",
        marketplace_check is not None and marketplace_check.get("status") == "passed",
        str(marketplace_check.get("evidence") if marketplace_check else "missing"),
        "p6_marketplace_not_ready",
    )
    add_check(
        checks,
        "p6_installed_cache_ready",
        installed_cache_check is not None
        and installed_cache_check.get("status") == "passed"
        and bool(cache_version),
        str(installed_cache_check.get("evidence") if installed_cache_check else "missing"),
        "p6_installed_cache_not_ready",
    )
    add_check(
        checks,
        "p6_mcp_contracts_ready",
        bool(mcp_contract_checks)
        and passed_mcp_contract_count == len(mcp_contract_checks),
        f"contracts={passed_mcp_contract_count}/{len(mcp_contract_checks)}",
        "p6_mcp_contracts_not_ready",
    )
    add_check(
        checks,
        "plugin_manifest_version_match",
        plugin_manifest.get("name") == "ctoai-engine-brain"
        and bool(cache_version)
        and plugin_manifest.get("version") == cache_version,
        plugin_display_path(plugin_manifest_path),
        "plugin_manifest_version_mismatch",
    )

    operator_workflow = payloads["operator_workflow"]
    read_only_tools, safe_write_tools, all_tools = allowed_tools(operator_workflow)
    forbidden_tools = [
        name
        for name in all_tools
        if any(fragment in name.lower() for fragment in FORBIDDEN_TOOL_FRAGMENTS)
    ]
    add_check(
        checks,
        "p7_operator_workflow_policy",
        operator_workflow.get("status") == "safe_write_ready"
        and set(read_only_tools) == EXPECTED_READ_ONLY_TOOLS
        and set(safe_write_tools) == EXPECTED_SAFE_WRITE_TOOLS
        and blocked_classes(operator_workflow).issuperset(EXPECTED_BLOCKED_CLASSES)
        and not forbidden_tools,
        f"read_only={len(read_only_tools)} safe_write={len(safe_write_tools)} blocked_classes={len(blocked_classes(operator_workflow))}",
        "p7_operator_workflow_policy_mismatch",
    )

    operator_brief = payloads["operator_brief"]
    cockpit_handoff = (
        operator_brief.get("cockpit_handoff")
        if isinstance(operator_brief.get("cockpit_handoff"), dict)
        else {}
    )
    hard_brief_blockers = operator_brief.get("hard_blockers")
    add_check(
        checks,
        "p7_operator_brief_ready",
        operator_brief.get("status") == "ready"
        and operator_brief.get("decision") == "ready_for_p7_operator_workflow"
        and isinstance(hard_brief_blockers, list)
        and len(hard_brief_blockers) == 0
        and cockpit_handoff.get("status") == "ready",
        display_path(paths["operator_brief"], root),
        "p7_operator_brief_not_ready",
    )

    p7_cockpit_smoke = payloads["p7_cockpit_smoke"]
    cockpit_summary = summary(p7_cockpit_smoke)
    add_check(
        checks,
        "p7_cockpit_smoke_ready",
        p7_cockpit_smoke.get("status") == "ready"
        and int(cockpit_summary.get("checks") or 0) > 0
        and cockpit_summary.get("passed") == cockpit_summary.get("checks")
        and int(cockpit_summary.get("blocked") or 0) == 0,
        f"checks={cockpit_summary.get('passed', 0)}/{cockpit_summary.get('checks', 0)}",
        "p7_cockpit_smoke_not_ready",
    )

    p7_dry_run_smoke = payloads["p7_safe_write_dry_run_smoke"]
    dry_summary = summary(p7_dry_run_smoke)
    safe_write_count = int(dry_summary.get("safe_write_tool_count") or 0)
    add_check(
        checks,
        "p7_safe_write_dry_run_smoke_ready",
        p7_dry_run_smoke.get("status") == "ready"
        and safe_write_count > 0
        and dry_summary.get("passed") == dry_summary.get("checks")
        and int(dry_summary.get("blocked") or 0) == 0
        and int(dry_summary.get("dry_run_ready_count") or 0) == safe_write_count
        and int(dry_summary.get("preflight_ready_count") or 0) == safe_write_count
        and int(dry_summary.get("bootstrap_allowed_count") or 0) == 0,
        f"dry_run={dry_summary.get('dry_run_ready_count', 0)}/{safe_write_count}",
        "p7_safe_write_dry_run_smoke_not_ready",
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
        "policy": "Read-only P6 plugin handoff smoke validates generated P6 readiness, plugin install metadata, and P7 operator evidence before fresh-thread verification.",
        "hard_blockers": hard_blockers,
        "warnings": [],
        "summary": {
            "checks": len(checks),
            "passed": sum(1 for check in checks if check["status"] == "passed"),
            "blocked": sum(1 for check in checks if check["status"] != "passed"),
            "p6_check_count": len(p6_checks),
            "p6_passed_count": p6_passed_count,
            "mcp_contract_count": len(mcp_contract_checks),
            "passed_mcp_contract_count": passed_mcp_contract_count,
            "allowed_tool_count": len(all_tools),
            "read_only_tool_count": len(read_only_tools),
            "safe_write_tool_count": len(safe_write_tools),
            "installed_cache_version": cache_version,
            "plugin_manifest_version": str(plugin_manifest.get("version") or ""),
            "fresh_thread_required": True,
            "current_thread_tool_discovery_status": "requires_fresh_thread",
        },
        "fresh_thread_verification": {
            "status": "pending_fresh_thread",
            "recommended_tool_order": [
                "ctoai_engine_brain_brief",
                "ctoai_control_center_cockpit",
                "ctoai_engine_brain_self_check",
            ],
            "expected_read_only_tools": sorted(EXPECTED_READ_ONLY_TOOLS),
            "expected_safe_write_tools": sorted(EXPECTED_SAFE_WRITE_TOOLS),
            "next_action": "Open a fresh Codex thread and verify the installed ctoai-engine-brain plugin tools are visible before adding more P6 actions.",
        },
        "checks": checks,
        "source_paths": {
            name: display_path(path, root) for name, path in paths.items()
        }
        | {
            "plugin_manifest": plugin_display_path(plugin_manifest_path),
            "plugin_mcp_config": plugin_display_path(plugin_mcp_path),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary_data = report["summary"]
    fresh = report["fresh_thread_verification"]
    lines = [
        "# Control Center P6 Plugin Handoff Smoke",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        report["policy"],
        "",
        "## Summary",
        "",
        f"- Checks: `{summary_data['passed']}/{summary_data['checks']}` passed.",
        f"- P6 readiness checks: `{summary_data['p6_passed_count']}/{summary_data['p6_check_count']}`.",
        f"- MCP contracts: `{summary_data['passed_mcp_contract_count']}/{summary_data['mcp_contract_count']}`.",
        f"- Installed cache version: `{summary_data['installed_cache_version'] or 'missing'}`.",
        f"- Current-thread discovery: `{summary_data['current_thread_tool_discovery_status']}`.",
        "",
        "## Fresh-Thread Verification",
        "",
        f"- Status: `{fresh['status']}`.",
        f"- Next action: {fresh['next_action']}",
        f"- Tool order: `{', '.join(fresh['recommended_tool_order'])}`.",
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
    if report["hard_blockers"]:
        lines.extend(["", "## Hard Blockers", ""])
        lines.extend(f"- `{item}`" for item in report["hard_blockers"])
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
        description="Validate read-only P6 plugin handoff evidence."
    )
    parser.add_argument("--root", "--workspace", dest="root", type=Path, default=ROOT)
    parser.add_argument(
        "--plugin-root",
        type=Path,
        default=Path(os.environ.get("CTOAI_ENGINE_BRAIN_PLUGIN_ROOT", ""))
        if os.environ.get("CTOAI_ENGINE_BRAIN_PLUGIN_ROOT")
        else DEFAULT_PLUGIN_ROOT,
    )
    parser.add_argument("--json-out", "--output", dest="json_out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    report = build_report(args.root, plugin_root=args.plugin_root)
    if not args.no_write:
        write_outputs(args.root.resolve(), report, args.json_out, args.md_out)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
