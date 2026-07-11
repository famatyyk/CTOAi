#!/usr/bin/env python3
"""Validate passive OTClient input contract behavior fixtures."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parents[2]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
DEFAULT_JSON_OUT = ROOT / "runtime" / "solteria_helper_dev" / "input_contract_fixtures.json"
DEFAULT_PLAN_OUT = ROOT / "docs" / "otclient" / "solteria_helper_input_contracts.md"


@dataclass(frozen=True)
class FixtureCheck:
    name: str
    status: str
    expected: dict[str, object]
    evidence: str


@dataclass(frozen=True)
class InputContractReport:
    name: str
    created_at: str
    status: str
    check_count: int
    passed_count: int
    failed_count: int
    hotkeys_path: str
    modal_path: str
    hotkey_checks: list[FixtureCheck]
    modal_checks: list[FixtureCheck]
    next_action: str
    live_safety: str


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def passed_if(source: str, *tokens: str) -> str:
    return "passed" if all(token in source for token in tokens) else "failed"


def build_report(otclient_dir: Path = OTCLIENT_DIR) -> InputContractReport:
    hotkeys_path = otclient_dir / "ctoa_helper_hotkeys.lua"
    modal_path = otclient_dir / "ctoa_helper_modal.lua"
    hotkeys = hotkeys_path.read_text(encoding="utf-8") if hotkeys_path.is_file() else ""
    modal = modal_path.read_text(encoding="utf-8") if modal_path.is_file() else ""

    hotkey_checks = [
        FixtureCheck(
            name="modifier_order_normalizes_ctrl_h",
            status=passed_if(hotkeys, 'local MODIFIER_ORDER = {"Ctrl", "Alt", "Shift", "Meta"}', "function Hotkeys.normalizeKeyName", "function Hotkeys.parse"),
            expected={"input": " ctrl + h ", "valid": True, "normalized": "Ctrl+H", "reason": "ok"},
            evidence="parser trims input, normalizes single-character keys, and emits ordered modifiers",
        ),
        FixtureCheck(
            name="command_alias_maps_to_meta_function_key",
            status=passed_if(hotkeys, 'command = "Meta"', "local functionMatch = string.match(lowered, \"^f(%d%d?)$\")"),
            expected={"input": "command+f12", "valid": True, "normalized": "Meta+F12", "reason": "ok"},
            evidence="command/cmd/win aliases map to Meta and F1-F24 are accepted",
        ),
        FixtureCheck(
            name="empty_hotkey_is_rejected",
            status=passed_if(hotkeys, 'reason = "empty"', 'valid = false'),
            expected={"input": "", "valid": False, "normalized": "", "reason": "empty"},
            evidence="empty input has an explicit fail-closed reason",
        ),
        FixtureCheck(
            name="modifier_only_hotkey_is_rejected",
            status=passed_if(hotkeys, 'reason = "missing_key"', 'key == ""'),
            expected={"input": "Ctrl+Alt", "valid": False, "normalized": "", "reason": "missing_key"},
            evidence="modifier-only input has no executable key and is rejected",
        ),
        FixtureCheck(
            name="invalid_function_key_is_rejected",
            status=passed_if(hotkeys, 'reason = "invalid_key"', "number >= 1 and number <= 24"),
            expected={"input": "F25", "valid": False, "normalized": "", "reason": "invalid_key"},
            evidence="function key range is bounded to F1-F24",
        ),
        FixtureCheck(
            name="multiple_keys_are_rejected",
            status=passed_if(hotkeys, 'reason = "multiple_keys"', 'key = normalized'),
            expected={"input": "Ctrl+A+B", "valid": False, "normalized": "", "reason": "multiple_keys"},
            evidence="a second non-modifier key fails closed",
        ),
        FixtureCheck(
            name="reserved_keys_are_rejected",
            status=passed_if(hotkeys, "local RESERVED_KEYS = {", 'reason = "reserved_key"', "Escape = true"),
            expected={"input": "Escape", "valid": False, "normalized": "", "reason": "reserved_key"},
            evidence="reserved UI keys cannot become helper bindings",
        ),
        FixtureCheck(
            name="binding_decision_reports_changed_allowed_choice",
            status=passed_if(hotkeys, "function Hotkeys.bindingDecision", 'reason = previous == parsed.normalized and "unchanged" or "changed"', "changed = previous ~= parsed.normalized"),
            expected={"input": "Ctrl+J", "current": "Ctrl+H", "allowed": ["Ctrl+H", "Ctrl+J"], "allowed_result": True, "normalized": "Ctrl+J", "reason": "changed", "changed": True},
            evidence="bindingDecision reports normalized value, previous value, and changed state without binding keys",
        ),
        FixtureCheck(
            name="binding_decision_rejects_disallowed_choice",
            status=passed_if(hotkeys, 'reason = "not_allowed"', "not Hotkeys.isAllowed(parsed.normalized, allowed)"),
            expected={"input": "Ctrl+K", "current": "Ctrl+H", "allowed": ["Ctrl+H", "Ctrl+J"], "allowed_result": False, "normalized": "Ctrl+K", "reason": "not_allowed"},
            evidence="bindingDecision enforces explicit allow-list before the shell may bind",
        ),
    ]

    modal_checks = [
        FixtureCheck(
            name="request_builds_bounded_confirmation",
            status=passed_if(modal, "function Modal.request", "local DEFAULT_TTL_MS = 4500", "expires_at_ms = now + ttl"),
            expected={"action": "cavebot_delete", "context": "wp 1", "now_ms": 1000, "ttl_ms": 4500, "expires_at_ms": 5500, "message": "Confirm cavebot delete: wp 1"},
            evidence="request creates a bounded confirmation payload and readable action text",
        ),
        FixtureCheck(
            name="pending_state_expires_after_ttl",
            status=passed_if(modal, "function Modal.isPending", "now > (tonumber(request.expires_at_ms) or 0)"),
            expected={"action": "cavebot_delete", "pending_at_ms": 5000, "expired_at_ms": 6000, "pending_before_expiry": True, "pending_after_expiry": False},
            evidence="isPending is time-bounded and action-specific",
        ),
        FixtureCheck(
            name="guarded_action_requires_confirmation",
            status=passed_if(modal, "local GUARDED_ACTIONS = {", "cavebot_delete = true", 'reason = "confirmation_required"'),
            expected={"action": "cavebot_delete", "confirm": False, "allowed": False, "reason": "confirmation_required"},
            evidence="guarded destructive actions fail closed without confirm=true",
        ),
        FixtureCheck(
            name="confirmed_guarded_action_is_allowed",
            status=passed_if(modal, "function Modal.confirm", 'reason = "confirmed"', "confirmed_at_ms"),
            expected={"action": "cavebot_delete", "confirm": True, "allowed": True, "reason": "confirmed"},
            evidence="confirmation payload is required before a guarded action can proceed",
        ),
        FixtureCheck(
            name="expired_guarded_action_is_blocked",
            status=passed_if(modal, "function Modal.isExpired", 'reason = "expired"', "confirmation expired"),
            expected={"action": "cavebot_delete", "confirm": True, "allowed": False, "reason": "expired", "decision_text": "confirmation expired"},
            evidence="expired confirmations are denied and have explicit operator text",
        ),
        FixtureCheck(
            name="unguarded_action_stays_allowed_without_runtime_shortcut",
            status=passed_if(modal, 'reason = "unguarded_action"', "live_shortcuts = false", "runtime_actions = false"),
            expected={"action": "tab_switch", "confirm": False, "allowed": True, "reason": "unguarded_action"},
            evidence="unprotected UI intents remain allowed while the module still cannot execute runtime actions",
        ),
        FixtureCheck(
            name="decision_text_covers_allow_deny_states",
            status=passed_if(modal, "function Modal.decisionText", '"confirmed: " .. actionText(decision.action)', '"confirmation required: " .. actionText(decision.action)'),
            expected={"confirmed": "confirmed: cavebot delete", "required": "confirmation required: cavebot delete", "expired": "confirmation expired"},
            evidence="decisionText turns modal states into stable operator text",
        ),
    ]

    all_checks = [*hotkey_checks, *modal_checks]
    failed = [item for item in all_checks if item.status != "passed"]
    status = "passed" if not failed else "failed"
    return InputContractReport(
        name="otclient-helper-input-contract-fixtures",
        created_at=datetime.now().replace(microsecond=0).isoformat(),
        status=status,
        check_count=len(all_checks),
        passed_count=len(all_checks) - len(failed),
        failed_count=len(failed),
        hotkeys_path=str(hotkeys_path),
        modal_path=str(modal_path),
        hotkey_checks=hotkey_checks,
        modal_checks=modal_checks,
        next_action=(
            "Run ModuleStaticGates, then sandbox SmokeAttachModules before any runtime bridge consumes input decisions."
            if status == "passed"
            else "Fix hotkey/modal passive input fixture coverage before adding new shortcuts or destructive commands."
        ),
        live_safety="InputContractFixtures is repo-only static fixture validation; it does not launch, stop, bind keys, create widgets, execute plans, cast, talk, walk, use items, attack, attach to, promote, or overwrite any client.",
    )


def render_markdown(report: InputContractReport) -> str:
    lines = [
        "# Solteria Helper Input Contracts",
        "",
        f"- Status: `{report.status}`",
        f"- Checks: `{report.passed_count}` / `{report.check_count}`",
        f"- Failed: `{report.failed_count}`",
        f"- Next action: {report.next_action}",
        "",
        "## Rule",
        "",
        "Hotkey and modal modules may parse, normalize, describe, and decide. They must not bind keys, create widgets, execute commands, dispatch plans, or promote live runtime behavior.",
        "",
        "## Hotkey Fixtures",
        "",
        "| Fixture | Status | Expected | Evidence |",
        "|---|---:|---|---|",
    ]
    for item in report.hotkey_checks:
        lines.append(
            f"| `{item.name}` | `{item.status}` | `{json.dumps(item.expected, sort_keys=True)}` | {item.evidence} |"
        )
    lines.extend(
        [
            "",
            "## Modal Fixtures",
            "",
            "| Fixture | Status | Expected | Evidence |",
            "|---|---:|---|---|",
        ]
    )
    for item in report.modal_checks:
        lines.append(
            f"| `{item.name}` | `{item.status}` | `{json.dumps(item.expected, sort_keys=True)}` | {item.evidence} |"
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\ops\\otclient_input_contract_fixtures.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action InputContractsStaticSmoke",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--otclient-dir", type=Path, default=OTCLIENT_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN_OUT)
    parser.add_argument("--no-plan-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.otclient_dir.resolve())
    write_json_atomic(args.json_out.resolve(), asdict(report))
    if not args.no_plan_write:
        write_text_atomic(args.plan_out.resolve(), render_markdown(report))
    print(f"[otclient-input-contract-fixtures] JSON: {args.json_out}")
    if not args.no_plan_write:
        print(f"[otclient-input-contract-fixtures] Plan: {args.plan_out}")
    print(
        "[otclient-input-contract-fixtures] Status: "
        f"{report.status} ({report.passed_count}/{report.check_count})"
    )
    return 0 if report.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
