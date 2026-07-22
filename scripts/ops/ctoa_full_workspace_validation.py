#!/usr/bin/env python3
"""Run the fixed CTOAi full-workspace validation registry.

This is deliberately a narrow, fail-closed safe-write entry point.  It accepts
no command, path, or output overrides: every registry item and the only
evidence destination are defined in this module.  A dry run merely describes
the fixed registry; it never starts a process or writes an artifact.
"""

from __future__ import annotations

import argparse
import json
import stat
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner import process_safety  # noqa: E402


CONFIRMATION = "refresh full workspace validation"
OUTPUT_RELATIVE_PATH = Path("runtime/audits/ctoai-full-workspace-validation.json")
PLUGIN_ROOT = Path.home() / "plugins" / "ctoai-engine-brain"
MAX_REASON_BYTES = 512
MAX_RESULT_BYTES = 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024

MCP_REQUIRED_READ_ONLY_TOOLS = frozenset(
    {
        "ctoai_control_central",
        "ctoai_engine_brain_status",
        "ctoai_engine_brain_self_check",
        "ctoai_engine_brain_brief",
        "ctoai_control_center_cockpit",
    }
)
MCP_ALLOWED_SAFE_WRITE_TOOLS = frozenset(
    {
        "ctoai_repo_hygiene_refresh",
        "ctoai_api_cost_refresh",
        "ctoai_evidence_pack_refresh",
        "ctoai_engine_brain_refresh",
        "ctoai_p7_cockpit_smoke_refresh",
        "ctoai_roadmap_state_refresh",
        "ctoai_full_workspace_validation_refresh",
    }
)
# The MCP server is deliberately a closed surface: the five read-only tools and
# the seven declared safe-write candidates are the complete policy.  Keeping
# the combined name preserves the small test helper and makes omission checks
# explicit at the handshake boundary.
MCP_REQUIRED_TOOLS = MCP_REQUIRED_READ_ONLY_TOOLS | MCP_ALLOWED_SAFE_WRITE_TOOLS


@dataclass(frozen=True)
class ValidationSpec:
    """One immutable, local validation entry.

    ``kind`` is intentionally not a user-supplied command.  It selects one of
    the trusted command constructors below, keeping the registry auditable and
    preventing this utility from becoming a generic command runner.
    """

    identifier: str
    kind: str
    timeout_seconds: int


@dataclass(frozen=True)
class ExecutionResult:
    """Private process result used only to derive bounded evidence."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


VALIDATION_REGISTRY: tuple[ValidationSpec, ...] = (
    ValidationSpec("python_non_e2e", "python_non_e2e", 900),
    ValidationSpec("web_lint", "web_lint", 300),
    ValidationSpec("web_tests", "web_tests", 300),
    ValidationSpec("diff_check", "diff_check", 60),
    ValidationSpec("brain_refresh", "brain_refresh", 240),
    ValidationSpec("brain_doctor", "brain_doctor", 240),
    ValidationSpec("brain_pack_all", "brain_pack_all", 240),
    ValidationSpec("p6_plugin_self_check", "p6_plugin_self_check", 180),
    ValidationSpec("p6_plugin_mcp", "p6_plugin_mcp", 180),
    ValidationSpec("p7_operator_brief", "p7_operator_brief", 180),
    ValidationSpec("p7_generated_brief", "p7_generated_brief", 30),
)


def _regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _fixed_workspace_path(root: Path, relative: Path) -> Path:
    """Return a fixed, non-symlinked path that remains under ``root``."""

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("fixed workspace path must be relative")
    resolved_root = root.resolve(strict=False)
    if root.exists() and root.is_symlink():
        raise ValueError("workspace root must not be a symlink")

    candidate = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ValueError("fixed workspace path must not traverse symlinks")
    try:
        candidate.resolve(strict=False).relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("fixed workspace path escaped workspace") from exc
    return candidate


def _read_json_object_bounded(path: Path) -> dict[str, Any]:
    if not _regular_file(path):
        raise ValueError("required fixed artifact is unavailable")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError("required fixed artifact is unavailable") from exc
    if size > MAX_RESULT_BYTES:
        raise ValueError("required fixed artifact exceeds size limit")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("required fixed artifact is unreadable") from exc
    if len(raw) > MAX_RESULT_BYTES:
        raise ValueError("required fixed artifact exceeds size limit")
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("required fixed artifact is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("required fixed artifact must be a JSON object")
    return payload


def _json_stdout(stdout: str) -> dict[str, Any] | None:
    """Parse trusted structured output without projecting it into evidence."""

    encoded = stdout.encode("utf-8", errors="replace")
    if len(encoded) > MAX_RESULT_BYTES:
        return None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _mcp_requests(root: Path) -> str:
    workspace = str(root.resolve(strict=False))
    requests = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ctoa-full-validation", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "ctoai_engine_brain_brief",
                "arguments": {"workspace": workspace},
            },
        },
    )
    encoded_requests = (
        json.dumps(item, separators=(",", ":")) for item in requests
    )
    return "\n".join(encoded_requests) + "\n"


def _trusted_command(
    spec: ValidationSpec, root: Path
) -> tuple[list[str], Path, str | None]:
    """Build a command only from the immutable registry.

    The returned input is used only by the fixed JSON-RPC handshake entry.
    """

    python = process_safety.resolve_python()
    if spec.kind == "python_non_e2e":
        return (
            [
                python,
                "-m",
                "pytest",
                "tests",
                "--ignore=tests/e2e",
                "-m",
                "not workspace_state",
                "-q",
            ],
            root,
            None,
        )
    if spec.kind == "web_lint":
        return (
            [process_safety.resolve_executable("npm"), "run", "lint"],
            root / "web",
            None,
        )
    if spec.kind == "web_tests":
        return (
            [process_safety.resolve_executable("npm"), "test"],
            root / "web",
            None,
        )
    if spec.kind == "diff_check":
        return ([process_safety.resolve_git(), "diff", "--check"], root, None)
    if spec.kind == "brain_refresh":
        return ([python, "scripts/ops/engine_brain_index.py"], root, None)
    if spec.kind == "brain_doctor":
        return ([python, "scripts/ops/engine_brain_doctor.py"], root, None)
    if spec.kind == "brain_pack_all":
        return (
            [python, "scripts/ops/engine_brain_pack.py", "--profile", "all"],
            root,
            None,
        )

    plugin_script_by_kind = {
        "p6_plugin_self_check": "ctoai_engine_brain_self_check.py",
        "p6_plugin_mcp": "ctoai_engine_brain_mcp.py",
        "p7_operator_brief": "ctoai_engine_brain_brief.py",
    }
    script_name = plugin_script_by_kind.get(spec.kind)
    if script_name:
        plugin_script = PLUGIN_ROOT / "scripts" / script_name
        if not _regular_file(plugin_script):
            raise process_safety.ExecutableUnavailableError(
                "required trusted plugin script is unavailable"
            )
        if spec.kind == "p6_plugin_self_check":
            return (
                [python, str(plugin_script), "--workspace", str(root)],
                root,
                None,
            )
        if spec.kind == "p6_plugin_mcp":
            return ([python, str(plugin_script)], PLUGIN_ROOT, _mcp_requests(root))
        return (
            [
                python,
                str(plugin_script),
                "--workspace",
                str(root),
                "--format",
                "json",
            ],
            root,
            None,
        )
    raise ValueError("unknown fixed validation registry entry")


def execute_validation_entry(spec: ValidationSpec, root: Path) -> ExecutionResult:
    """Run a single immutable registry entry without exposing its output."""

    if spec.kind == "p7_generated_brief":
        try:
            payload = _read_json_object_bounded(
                _fixed_workspace_path(root, Path("AI/generated/P7_OPERATOR_BRIEF.json"))
            )
        except ValueError:
            return ExecutionResult(returncode=1)
        return ExecutionResult(returncode=0, stdout=json.dumps(payload))

    try:
        command, cwd, input_text = _trusted_command(spec, root)
        completed = process_safety.run_trusted(
            command,
            cwd=str(cwd),
            input=input_text,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            encoding="utf-8",
            errors="replace",
        )
    except process_safety.ProcessTimeoutExpired:
        return ExecutionResult(returncode=124, timed_out=True)
    except (process_safety.ExecutableUnavailableError, OSError, ValueError):
        return ExecutionResult(returncode=127)
    return ExecutionResult(
        returncode=int(completed.returncode),
        stdout=str(completed.stdout or ""),
        stderr=str(completed.stderr or ""),
    )


def _mcp_handshake_ok(stdout: str) -> tuple[bool, str]:
    encoded = stdout.encode("utf-8", errors="replace")
    if len(encoded) > MAX_RESULT_BYTES:
        return False, "mcp_result_exceeds_size_limit"
    responses: dict[int, dict[str, Any]] = {}
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return False, "invalid_mcp_response"
        if not isinstance(payload, dict):
            return False, "invalid_mcp_response"
        message_id = payload.get("id")
        if isinstance(message_id, int):
            responses[message_id] = payload
    initialized = responses.get(1, {}).get("result")
    listed = responses.get(2, {}).get("result")
    called = responses.get(3, {}).get("result")
    if (
        not isinstance(initialized, dict)
        or not isinstance(listed, dict)
        or not isinstance(called, dict)
    ):
        return False, "incomplete_mcp_handshake"
    server = initialized.get("serverInfo")
    if not isinstance(server, dict) or not str(server.get("name") or "").strip():
        return False, "invalid_mcp_initialize"
    tools = listed.get("tools")
    if not isinstance(tools, list):
        return False, "invalid_mcp_tools_response"
    tool_names: set[str] = set()
    for item in tools:
        if not isinstance(item, dict):
            return False, "invalid_mcp_tools_response"
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or name in tool_names:
            return False, "invalid_mcp_tools_response"
        tool_names.add(name)
    if not MCP_REQUIRED_TOOLS.issubset(tool_names):
        return False, "mcp_required_tools_missing"
    if tool_names - MCP_REQUIRED_TOOLS:
        return False, "mcp_forbidden_tools_present"
    content = called.get("content")
    if called.get("isError") is True or not isinstance(content, list) or not content:
        return False, "mcp_brief_unavailable"
    first = content[0] if isinstance(content[0], dict) else {}
    text = first.get("text") if isinstance(first, dict) else None
    brief = _json_stdout(text) if isinstance(text, str) else None
    if brief is None or not isinstance(brief.get("status"), str):
        return False, "mcp_brief_invalid"
    return True, f"initialize=ready; tools={len(tool_names)}; brief=responded"


def _classify_execution(
    spec: ValidationSpec, result: ExecutionResult
) -> tuple[str, str]:
    """Map private output to small, fixed vocabulary evidence."""

    if result.timed_out:
        return "failed", "timeout"
    if result.returncode != 0:
        return "failed", "nonzero_exit"

    if spec.kind in {"python_non_e2e", "web_lint", "web_tests", "diff_check"}:
        return "passed", "completed"

    if spec.kind == "p6_plugin_mcp":
        ok, summary = _mcp_handshake_ok(result.stdout)
        return ("passed" if ok else "failed"), summary

    payload = _json_stdout(result.stdout)
    if payload is None:
        return "failed", "invalid_structured_result"

    if spec.kind == "brain_refresh":
        guards_ready = (
            payload.get("doc_sync_status") == "passed"
            and payload.get("secret_guardrail_status") == "passed"
        )
        return (
            ("passed", "generated_guardrails_verified")
            if guards_ready
            else ("failed", "generated_guardrails_not_ready")
        )
    if spec.kind == "brain_doctor":
        overall = str(payload.get("overall_status") or "")
        if overall == "ok":
            return "passed", "environment_doctor_ok"
        if overall == "warn":
            return "warn", "environment_doctor_warn"
        return "failed", "environment_doctor_failed"
    if spec.kind == "brain_pack_all":
        try:
            included_count = int(payload.get("included_count") or 0)
        except (TypeError, ValueError):
            included_count = 0
        valid_pack = payload.get("profile") == "all" and included_count > 0
        return (
            ("passed", "all_profile_pack_generated")
            if valid_pack
            else ("failed", "all_profile_pack_invalid")
        )
    if spec.kind == "p6_plugin_self_check":
        return (
            ("passed", "plugin_self_check_ready")
            if payload.get("status") == "ready"
            else ("failed", "plugin_self_check_not_ready")
        )
    if spec.kind == "p7_operator_brief":
        hard_blockers = payload.get("hard_blockers")
        ready = payload.get("status") == "ready" and hard_blockers == []
        return (
            ("passed", "operator_brief_ready")
            if ready
            else ("failed", "operator_brief_not_ready")
        )
    if spec.kind == "p7_generated_brief":
        hard_blockers = payload.get("hard_blockers")
        ready = payload.get("status") == "ready" and hard_blockers == []
        return (
            ("passed", "generated_operator_brief_ready")
            if ready
            else ("failed", "generated_operator_brief_not_ready")
        )
    return "failed", "unknown_registry_entry"


Executor = Callable[[ValidationSpec, Path], ExecutionResult]


def build_dry_run_payload() -> dict[str, Any]:
    """Return a non-mutating registry description without command details."""

    return {
        "schema_version": 2,
        "status": "dry_run",
        "summary": {
            "command_count": len(VALIDATION_REGISTRY),
            "passed": 0,
            "warn": 0,
            "failed": 0,
            "skipped": len(VALIDATION_REGISTRY),
            "propagation": "not_run",
        },
        "commands": [
            {"id": spec.identifier, "status": "not_run"}
            for spec in VALIDATION_REGISTRY
        ],
    }


def run_confirmed_validation(
    root: Path, executor: Executor = execute_validation_entry
) -> dict[str, Any]:
    """Execute every fixed registry entry and return bounded public evidence."""

    commands: list[dict[str, Any]] = []
    for spec in VALIDATION_REGISTRY:
        started = time.monotonic()
        try:
            result = executor(spec, root)
            status, summary = _classify_execution(spec, result)
        except Exception:  # noqa: BLE001 - evidence must fail closed and stay redacted.
            status, summary = "failed", "execution_unavailable"
        duration_seconds = max(0.0, time.monotonic() - started)
        commands.append(
            {
                "id": spec.identifier,
                "status": status,
                "summary": summary,
                "duration": f"{duration_seconds:.2f}s",
            }
        )

    status_counts = {
        status: sum(1 for item in commands if item["status"] == status)
        for status in ("passed", "warn", "failed")
    }
    status = "passed" if status_counts["failed"] == 0 else "failed"
    return {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "status": status,
        "summary": {
            "command_count": len(commands),
            **status_counts,
            "skipped": 0,
            "propagation": "passed" if status == "passed" else "blocked",
        },
        "commands": commands,
    }


def write_evidence(root: Path, payload: dict[str, Any]) -> Path:
    """Write the sole bounded artifact after confirmed execution only."""

    path = _fixed_workspace_path(root, OUTPUT_RELATIVE_PATH)
    encoded = (json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_EVIDENCE_BYTES:
        raise ValueError("bounded validation evidence exceeds size limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ValueError("validation evidence path must not be a symlink")
    path.write_bytes(encoded)
    return path


def _valid_reason(value: str) -> bool:
    return bool(value.strip()) and (
        len(value.encode("utf-8", errors="ignore")) <= MAX_REASON_BYTES
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the fixed CTOAi full-workspace validation registry."
    )
    parser.add_argument("--dry-run", choices=("true", "false"), required=True)
    parser.add_argument("--confirmation")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)

    if not _valid_reason(args.reason):
        parser.error("reason must be non-empty and at most 512 bytes")
    if args.dry_run == "false" and args.confirmation != CONFIRMATION:
        parser.error("confirmed validation requires the exact confirmation text")
    if args.dry_run == "true":
        print(json.dumps(build_dry_run_payload(), separators=(",", ":")))
        return 0

    payload = run_confirmed_validation(ROOT.resolve(strict=False))
    write_evidence(ROOT.resolve(strict=False), payload)
    print(json.dumps(payload, separators=(",", ":")))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
