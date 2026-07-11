#!/usr/bin/env python3
"""Generate a budget-focused decomposition plan for the OTClient helper shell."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import uuid


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
DEFAULT_JSON_OUT = ROOT / "runtime" / "solteria_helper_dev" / "helper_shell_budget_plan.json"
DEFAULT_PLAN_OUT = ROOT / "docs" / "otclient" / "solteria_helper_shell_budget_plan.md"

HELPER_LINE_BUDGET = 4500
HELPER_FUNCTION_BUDGET = 130
HARD_LINE_CEILING = 6200
HARD_FUNCTION_CEILING = 700


DOMAIN_RULES = [
    ("ui_builder", ("Widget", "Section", "Row", "Tab", "rebuildUi", "style", "bindClick", "create")),
    ("profile_persistence", ("Profile", "Prefs", "exportProfile", "loadProfile", "Save", "Dirty", "migration")),
    ("runtime_combat", ("Combat", "Target", "Monster", "Offensive", "Rotation", "Rune", "Haste", "Exeta")),
    ("runtime_cavebot", ("Cavebot", "Waypoint", "Route", "Walk", "Movement")),
    ("runtime_recovery", ("Heal", "Mana", "Potion", "Vitals", "Recovery")),
    ("observer_modules", ("HealFriend", "Conditions", "Equipment", "Scripting")),
    ("diagnostics_smoke", ("Smoke", "Diagnostics", "Api", "Probe", "Log", "Status")),
    ("operator_summary", ("Summary", "Operator", "Title")),
    ("input_contracts", ("Hotkey", "Modal", "Confirm")),
]

NEXT_EXTRACTION_GUIDANCE = {
    "ui_builder": "Move repeated section/row builder metadata into passive UI descriptor tables before adding new tabs.",
    "profile_persistence": "Move profile dirty-reason metadata and save/export field grouping into profile schema helpers.",
    "runtime_combat": "Keep execution guarded; move remaining decision text and readiness summaries into combat/runtime adapters.",
    "runtime_cavebot": "Keep autoWalk guarded; move remaining cavebot editor text and waypoint button state into route/cavebot adapters.",
    "runtime_recovery": "Mirror remaining recovery decision labels in passive healing metadata before changing potion/spell runtime.",
    "observer_modules": "Keep observers read-only; move any tab-only status text into their module summaries.",
    "diagnostics_smoke": "Keep smoke commands in the shell, but move static evidence formatting into diagnostics helpers.",
    "operator_summary": "Move remaining operator-facing prose into ctoa_helper_operator_summary.lua.",
    "input_contracts": "Expand fixture coverage before accepting new shortcuts or destructive commands.",
}


@dataclass(frozen=True)
class FunctionSpan:
    name: str
    kind: str
    start_line: int
    end_line: int
    line_count: int
    domain: str


@dataclass(frozen=True)
class DomainBudget:
    domain: str
    function_count: int
    line_count: int
    largest_functions: list[FunctionSpan]
    next_action: str


@dataclass(frozen=True)
class ShellBudgetPlan:
    name: str
    created_at: str
    status: str
    helper_path: str
    helper_line_count: int
    helper_function_count: int
    helper_line_budget: int
    helper_function_budget: int
    hard_line_ceiling: int
    hard_function_ceiling: int
    over_line_budget_by: int
    over_function_budget_by: int
    under_hard_ceiling: bool
    top_domains: list[DomainBudget]
    next_extraction_domains: list[str]
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


def classify_function(name: str) -> str:
    lower = name.lower()
    for domain, tokens in DOMAIN_RULES:
        if any(token.lower() in lower for token in tokens):
            return domain
    return "shell_misc"


def strip_lua_literals(line: str) -> str:
    result = []
    index = 0
    quote = ""
    while index < len(line):
        char = line[index]
        next_char = line[index + 1] if index + 1 < len(line) else ""
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
            continue
        if char == "-" and next_char == "-":
            break
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        result.append(char)
        index += 1
    return "".join(result)


def lua_block_delta(line: str) -> int:
    clean = strip_lua_literals(line)
    opens = len(re.findall(r"\b(function|if|for|while|repeat)\b", clean))
    closes = len(re.findall(r"\b(end|until)\b", clean))
    return opens - closes


def find_function_end(lines: list[str], start_index: int) -> int:
    depth = 1
    for index in range(start_index + 1, len(lines)):
        depth += lua_block_delta(lines[index])
        if depth <= 0:
            return index + 1
    return len(lines)


def parse_function_spans(source: str) -> list[FunctionSpan]:
    lines = source.splitlines()
    pattern = re.compile(r"^\s*(?P<kind>local\s+function|function)\s+(?P<name>[A-Za-z0-9_:.]+)")
    spans: list[FunctionSpan] = []
    for index, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            start = index + 1
            end = find_function_end(lines, index)
            name = match.group("name")
            spans.append(
                FunctionSpan(
                    name=name,
                    kind=match.group("kind"),
                    start_line=start,
                    end_line=end,
                    line_count=max(1, end - start + 1),
                domain=classify_function(name),
            )
        )
    return spans


def build_plan(helper_path: Path = DEFAULT_HELPER) -> ShellBudgetPlan:
    source = helper_path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    spans = parse_function_spans(source)
    domains: dict[str, list[FunctionSpan]] = {}
    for span in spans:
        domains.setdefault(span.domain, []).append(span)

    domain_budgets = [
        DomainBudget(
            domain=domain,
            function_count=len(items),
            line_count=sum(item.line_count for item in items),
            largest_functions=sorted(items, key=lambda item: item.line_count, reverse=True)[:5],
            next_action=NEXT_EXTRACTION_GUIDANCE.get(domain, "Keep this shell-only unless a named module owns the contract."),
        )
        for domain, items in domains.items()
    ]
    top_domains = sorted(domain_budgets, key=lambda item: (item.line_count, item.function_count), reverse=True)
    candidate_domains = [
        item.domain
        for item in top_domains
        if item.domain not in {"shell_misc"} and item.line_count >= 150
    ][:5]
    over_line = max(0, line_count - HELPER_LINE_BUDGET)
    over_functions = max(0, len(spans) - HELPER_FUNCTION_BUDGET)
    under_hard = line_count <= HARD_LINE_CEILING and len(spans) <= HARD_FUNCTION_CEILING
    status = "needs_extraction" if over_line or over_functions else "within_budget"
    return ShellBudgetPlan(
        name="otclient-helper-shell-budget-plan",
        created_at=datetime.now().replace(microsecond=0).isoformat(),
        status=status,
        helper_path=str(helper_path),
        helper_line_count=line_count,
        helper_function_count=len(spans),
        helper_line_budget=HELPER_LINE_BUDGET,
        helper_function_budget=HELPER_FUNCTION_BUDGET,
        hard_line_ceiling=HARD_LINE_CEILING,
        hard_function_ceiling=HARD_FUNCTION_CEILING,
        over_line_budget_by=over_line,
        over_function_budget_by=over_functions,
        under_hard_ceiling=under_hard,
        top_domains=top_domains,
        next_extraction_domains=candidate_domains,
        next_action=(
            "Extract the highest-line non-runtime text/metadata domain first, keep execution in guarded shell, then rerun ModuleStaticGates."
            if status == "needs_extraction"
            else "Keep budgets guarded before adding new modules."
        ),
        live_safety="ShellBudgetPlan is repo-only static analysis; it does not launch, stop, attach to, promote, bind keys, execute plans, cast, talk, walk, use items, attack, or overwrite any client.",
    )


def render_markdown(plan: ShellBudgetPlan) -> str:
    lines = [
        "# Solteria Helper Shell Budget Plan",
        "",
        f"- Status: `{plan.status}`",
        f"- Helper lines: `{plan.helper_line_count}` / `{plan.helper_line_budget}`",
        f"- Helper functions: `{plan.helper_function_count}` / `{plan.helper_function_budget}`",
        f"- Over line budget by: `{plan.over_line_budget_by}`",
        f"- Over function budget by: `{plan.over_function_budget_by}`",
        f"- Under hard ceiling: `{str(plan.under_hard_ceiling).lower()}`",
        f"- Next action: {plan.next_action}",
        "",
        "## Rule",
        "",
        "Use this plan to choose the next extraction from measured shell pressure. Runtime execution remains in guarded shell paths until sandbox `SmokeAttachModules`, fresh `SmokeAttachAll`, and explicit live approval exist.",
        "",
        "## Top Domains",
        "",
        "| Domain | Functions | Lines | Next action |",
        "|---|---:|---:|---|",
    ]
    for item in plan.top_domains:
        lines.append(
            f"| `{item.domain}` | `{item.function_count}` | `{item.line_count}` | {item.next_action} |"
        )
    lines.extend(["", "## Largest Functions", "", "| Domain | Function | Lines | Span |", "|---|---|---:|---|"])
    for domain in plan.top_domains[:6]:
        for function in domain.largest_functions:
            lines.append(
                f"| `{domain.domain}` | `{function.name}` | `{function.line_count}` | `{function.start_line}-{function.end_line}` |"
            )
    lines.extend(
        [
            "",
            "## Next Extraction Domains",
            "",
        ]
    )
    for index, domain in enumerate(plan.next_extraction_domains, start=1):
        lines.append(f"{index}. `{domain}`")
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\ops\\otclient_helper_shell_budget_plan.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action HelperShellBudgetPlanStaticSmoke",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, default=DEFAULT_HELPER)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN_OUT)
    parser.add_argument("--no-plan-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(args.helper.resolve())
    write_json_atomic(args.json_out.resolve(), asdict(plan))
    if not args.no_plan_write:
        write_text_atomic(args.plan_out.resolve(), render_markdown(plan))
    print(f"[otclient-helper-shell-budget-plan] JSON: {args.json_out}")
    if not args.no_plan_write:
        print(f"[otclient-helper-shell-budget-plan] Plan: {args.plan_out}")
    print(
        "[otclient-helper-shell-budget-plan] Status: "
        f"{plan.status}; lines={plan.helper_line_count}; functions={plan.helper_function_count}"
    )
    return 0 if plan.under_hard_ceiling else 1


if __name__ == "__main__":
    raise SystemExit(main())
