"""Generate the sandbox smoke queue for the Solteria OTClient helper."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
DEFAULT_JSON = DEV_DIR / "sandbox_smoke_queue.json"
DEFAULT_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_sandbox_smoke_queue.md"
SMOKE_ENV_SCRIPT = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"
SMOKE_SCRIPT = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1"


@dataclass(frozen=True)
class SmokeQueueStep:
    order: int
    step_id: str
    label: str
    status: str
    command: str
    evidence: str
    reason: str


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_status(release_gate: dict[str, Any], name: str) -> tuple[str, str, str]:
    for gate in release_gate.get("gates", []):
        if gate.get("name") == name:
            return str(gate.get("status", "missing")), str(gate.get("evidence", "")), str(gate.get("reason", ""))
    return "missing", "", "gate not found"


def _fresh_status(status: str) -> str:
    if status == "passed":
        return "passed"
    if status in {"pending", "blocked", "missing"}:
        return "required"
    return status or "required"


def _valid_attach_tabs(script_path: Path = SMOKE_ENV_SCRIPT) -> set[str]:
    if not script_path.is_file():
        return set()
    source = script_path.read_text(encoding="utf-8")
    match = re.search(
        r'\[ValidateSet\((?P<values>"overview".*?)\)\]\s*\n\s*\[string\]\$Tab',
        source,
        flags=re.DOTALL,
    )
    if not match:
        return set()
    return set(re.findall(r'"([^"]+)"', match.group("values")))


def _attach_tab(command: str) -> str:
    match = re.search(r"(?:^|\s)-Tab\s+([A-Za-z0-9_]+)(?:\s|$)", command)
    return match.group(1) if match else ""


def _static_module_steps(
    goal_status: dict[str, Any],
    valid_tabs: set[str],
) -> tuple[list[SmokeQueueStep], list[dict[str, str]]]:
    module_audit = goal_status.get("module_audit") or {}
    summary = module_audit.get("static_gate_summary") or []
    steps: list[SmokeQueueStep] = []
    static_only: list[dict[str, str]] = []
    for item in summary:
        module = str(item.get("module", "")).strip()
        if not module:
            continue
        attach_command = str(item.get("attach_command") or "").strip()
        attach_tab = _attach_tab(attach_command)
        if not attach_command:
            static_only.append(
                {
                    "module": module,
                    "status": str(item.get("status", "unknown")),
                    "report_path": str(item.get("report_path", "")),
                    "reason": "No dedicated UI tab; covered by static gate report and grouped module attach context.",
                }
            )
            continue
        if attach_tab and attach_tab not in valid_tabs:
            static_only.append(
                {
                    "module": module,
                    "status": str(item.get("status", "unknown")),
                    "report_path": str(item.get("report_path", "")),
                    "reason": f"Invalid attach tab `{attach_tab}`; covered by static gate report and grouped module attach context.",
                }
            )
            continue
        steps.append(
            SmokeQueueStep(
                order=0,
                step_id=f"attach_{module}",
                label=f"Attach module tab: {module}",
                status="queued",
                command=attach_command,
                evidence="runtime\\solteria_helper_dev\\module_attach_smoke.json",
                reason=f"Static gate is {item.get('status', 'unknown')}; in-world tab evidence is still required.",
            )
        )
    return steps, static_only


def build_queue(dev_dir: Path = DEV_DIR) -> dict[str, Any]:
    manifest = read_json(dev_dir / "manifest.json")
    release_gate = read_json(dev_dir / "release_gate.json")
    smoke_status = read_json(dev_dir / "smoke_status.json")
    goal_status = read_json(dev_dir / "goal_status.json")

    preflight_status, preflight_evidence, preflight_reason = _gate_status(release_gate, "SmokePreflight")
    static_status, static_evidence, static_reason = _gate_status(release_gate, "ModuleStaticGates")
    module_attach_status, module_attach_evidence, module_attach_reason = _gate_status(release_gate, "ModuleAttachSmoke")
    smoke_all_status, smoke_all_evidence, smoke_all_reason = _gate_status(release_gate, "SmokeAttachAll")
    live_status, live_evidence, live_reason = _gate_status(release_gate, "live_approval")
    smoke_runtime_status = str(smoke_status.get("status", "missing"))

    steps = [
        SmokeQueueStep(
            1,
            "local_ready",
            "Refresh local package and static gates",
            "passed" if goal_status.get("status") in {"blocked", "passed"} and preflight_status == "passed" else "required",
            f"{SMOKE_SCRIPT} -Action LocalReady",
            str(dev_dir / "local_ready.json"),
            "Local package, SmokePreflight, ModuleStaticGates, and GoalStatus should be current before attach.",
        ),
        SmokeQueueStep(
            2,
            "launch_sandbox",
            "Launch sandbox client and enter test character",
            "required" if smoke_runtime_status != "running" else "passed",
            f"{SMOKE_SCRIPT} -Action Launch",
            str(dev_dir / "smoke_status.json"),
            str(smoke_status.get("next_action") or "Sandbox client must be running in-world before attach smoke."),
        ),
        SmokeQueueStep(
            3,
            "ready_check",
            "Confirm helper is attached in-world",
            "required" if smoke_runtime_status != "running" else "queued",
            f"{SMOKE_SCRIPT} -Action ReadyCheck",
            str(dev_dir / "ready_check.json"),
            "Run after the sandbox character is in-world; character-select screens are not enough.",
        ),
        SmokeQueueStep(
            4,
            "module_attach_group",
            "Capture grouped prototype module tab evidence",
            _fresh_status(module_attach_status),
            f"{SMOKE_SCRIPT} -Action SmokeAttachModules",
            module_attach_evidence,
            module_attach_reason or "Prototype module tabs need grouped in-world evidence.",
        ),
    ]

    module_steps, static_only_modules = _static_module_steps(goal_status, _valid_attach_tabs())
    for index, step in enumerate(module_steps, start=5):
        steps.append(
            SmokeQueueStep(
                index,
                step.step_id,
                step.label,
                step.status if module_attach_status != "passed" else "passed",
                step.command,
                step.evidence,
                step.reason,
            )
        )

    next_order = 5 + len(module_steps)
    steps.extend(
        [
            SmokeQueueStep(
                next_order,
                "smoke_attach_all",
                "Capture full in-world helper acceptance",
                _fresh_status(smoke_all_status),
                f"{SMOKE_SCRIPT} -Action SmokeAttachAll",
                smoke_all_evidence,
                smoke_all_reason or "Fresh full attach report is required for the current manifest.",
            ),
            SmokeQueueStep(
                next_order + 1,
                "promote_live_approval",
                "Promote only after explicit live approval",
                _fresh_status(live_status),
                f"{SMOKE_SCRIPT} -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport <fresh-smokeattachall-json>",
                live_evidence,
                live_reason or "Live promotion remains gated by explicit approval.",
            ),
        ]
    )

    queue_status = "ready_for_operator" if preflight_status == "passed" and static_status == "passed" else "refresh_required"
    if module_attach_status == "passed" and smoke_all_status == "passed" and live_status == "passed":
        queue_status = "passed"

    return {
        "schema_version": 1,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "status": queue_status,
        "helper_version": manifest.get("helper_version", ""),
        "manifest_created_at": manifest.get("created_at", ""),
        "runtime_status": smoke_runtime_status,
        "release_gate_status": release_gate.get("status", "missing"),
        "preflight_status": preflight_status,
        "module_static_gates_status": static_status,
        "module_attach_status": module_attach_status,
        "smoke_attach_all_status": smoke_all_status,
        "live_approval_status": live_status,
        "next_action": next((step.label for step in steps if step.status in {"required", "queued", "blocked"}), "none"),
        "steps": [asdict(step) for step in steps],
        "static_only_modules": static_only_modules,
        "live_safety": "This queue is read-only planning evidence; it does not launch, attach to, promote, stop, or overwrite any client.",
        "source_evidence": {
            "manifest": str(dev_dir / "manifest.json"),
            "release_gate": str(dev_dir / "release_gate.json"),
            "smoke_status": str(dev_dir / "smoke_status.json"),
            "goal_status": str(dev_dir / "goal_status.json"),
            "preflight": preflight_evidence,
            "static_gates": static_evidence or static_reason,
        },
    }


def render_markdown(queue: dict[str, Any]) -> str:
    lines = [
        "# Solteria Helper Sandbox Smoke Queue",
        "",
        "## Decision",
        "",
        f"- Status: `{queue['status']}`",
        f"- Helper version: `{queue['helper_version']}`",
        f"- Runtime status: `{queue['runtime_status']}`",
        f"- Release gate: `{queue['release_gate_status']}`",
        f"- Next action: {queue['next_action']}",
        "- Live safety: read-only plan; live promotion still requires `-ApproveLiveDeploy`.",
        "",
        "## Queue",
        "",
        "| Order | Step | Status | Command | Evidence | Reason |",
        "|---:|---|---:|---|---|---|",
    ]
    for step in queue["steps"]:
        lines.append(
            f"| {step['order']} | `{step['step_id']}` / {step['label']} | `{step['status']}` | `{step['command']}` | `{step['evidence']}` | {step['reason']} |"
        )
    static_only = queue.get("static_only_modules") or []
    if static_only:
        lines.extend(
            [
                "",
                "## Static-Only Modules",
                "",
                "| Module | Status | Evidence | Reason |",
                "|---|---:|---|---|",
            ]
        )
        for item in static_only:
            lines.append(
                f"| `{item['module']}` | `{item['status']}` | `{item['report_path']}` | {item['reason']} |"
            )
    lines.extend(
        [
            "",
            "## Operator Rule",
            "",
            "Run this queue from top to bottom. If any attach step reports character-select, offline helper, stale manifest, or failed screenshot evidence, stop and refresh `LocalReady` before continuing.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{id(text)}.tmp")
    try:
        tmp.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Solteria Helper sandbox smoke queue")
    parser.add_argument("--dev-dir", type=Path, default=DEV_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()

    queue = build_queue(args.dev_dir.resolve())
    write_text_atomic(args.json_out, json.dumps(queue, indent=2))
    write_text_atomic(args.plan_out, render_markdown(queue))
    print(f"[solteria-helper-sandbox-smoke-queue] JSON: {args.json_out}")
    print(f"[solteria-helper-sandbox-smoke-queue] Plan: {args.plan_out}")
    print(f"[solteria-helper-sandbox-smoke-queue] Status: {queue['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
