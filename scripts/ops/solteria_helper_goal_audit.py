#!/usr/bin/env python3
"""Build a single Solteria Helper goal audit from current release artifacts."""

from __future__ import annotations

import argparse
import html
import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_development_plan.md"
DEFAULT_DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"


@dataclass(frozen=True)
class AuditItem:
    name: str
    status: str
    evidence: str
    note: str = ""


@dataclass(frozen=True)
class GoalAudit:
    name: str
    status: str
    complete: bool
    items: list[AuditItem]
    blockers: list[str]
    next_action: str
    next_command: str


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _exists_item(name: str, path: Path) -> AuditItem:
    return AuditItem(name=name, status="passed" if path.exists() else "missing", evidence=str(path))


def _roadmap_items(plan_path: Path, validation_status: str, gate: dict, gate_path: Path) -> list[AuditItem]:
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    validated = validation_status == "passed"
    phase_expectations = {
        "P0_development_lane": "### P0: Development Lane",
        "P1_runtime_observability": "### P1: Runtime Observability",
        "P2_healing_and_mana": "### P2: Healing And Mana",
        "P3_cavebot": "### P3: CaveBot",
        "P4_combat_and_magic": "### P4: Combat And Magic",
    }
    items: list[AuditItem] = []
    for name, heading in phase_expectations.items():
        status = "passed" if validated and heading in plan_text else "blocked"
        note = "covered by current ValidateDev evidence" if status == "passed" else "missing plan heading or validation"
        items.append(AuditItem(name=name, status=status, evidence=str(plan_path), note=note))
    p5_status = "passed" if gate.get("releasable_to_live") is True else "blocked"
    items.append(
        AuditItem(
            name="P5_packaging_and_release",
            status=p5_status,
            evidence=str(gate_path),
            note=gate.get("next_action", ""),
        )
    )
    return items


def build_audit(plan_path: Path = DEFAULT_PLAN, dev_dir: Path = DEFAULT_DEV_DIR) -> GoalAudit:
    validation_path = dev_dir / "validation.json"
    preflight_path = dev_dir / "smoke_preflight.json"
    status_path = dev_dir / "smoke_status.json"
    ready_check_path = dev_dir / "ready_check.json"
    gate_path = dev_dir / "release_gate.json"
    readiness_path = dev_dir / "release_readiness.json"
    module_audit_path = dev_dir / "module_audit.json"
    module_static_gates_path = dev_dir / "module_static_gates.json"
    module_attach_smoke_path = dev_dir / "module_attach_smoke.json"
    manifest_path = dev_dir / "manifest.json"

    manifest = _load_json(manifest_path)
    helper_version = manifest.get("helper_version") or "v1.1b"
    zip_path = dev_dir / f"ctoa_otclient_{helper_version}.zip"
    validation = _load_json(validation_path)
    preflight = _load_json(preflight_path)
    gate = _load_json(gate_path)
    smoke_status = _load_json(status_path)
    ready_check = _load_json(ready_check_path)
    module_audit = _load_json(module_audit_path)
    module_static_gates = _load_json(module_static_gates_path)
    module_attach_smoke = _load_json(module_attach_smoke_path)

    items = [
        _exists_item("development_plan", plan_path),
        _exists_item("manifest", manifest_path),
        _exists_item("changelog", dev_dir / "CHANGELOG.md"),
        AuditItem("validation", "passed" if validation.get("status") == "passed" else "blocked", str(validation_path)),
        _exists_item("release_readiness", readiness_path),
        _exists_item("zip", zip_path),
        AuditItem("smoke_preflight", "passed" if preflight.get("status") == "passed" else "blocked", str(preflight_path)),
        AuditItem("smoke_status", smoke_status.get("status") or "missing", str(status_path), smoke_status.get("next_action", "")),
        AuditItem("ready_check", ready_check.get("status") or "missing", str(ready_check_path), ready_check.get("next_action", "")),
        AuditItem(
            "module_static_gates",
            "passed" if module_static_gates.get("status") == "passed" else "blocked",
            str(module_static_gates_path),
            f"{module_static_gates.get('passed_count', 0)}/{module_static_gates.get('gate_count', 0)} static gates passed",
        ),
        AuditItem(
            "module_attach_smoke",
            "passed" if module_attach_smoke.get("status") == "passed" else "blocked",
            str(module_attach_smoke_path),
            f"{module_attach_smoke.get('passed_count', 0)}/{module_attach_smoke.get('module_count', 0)} module attach tabs passed",
        ),
        AuditItem("release_gate", gate.get("status") or "missing", str(gate_path), gate.get("next_action", "")),
        AuditItem(
            "module_audit",
            module_audit.get("status") or "missing",
            str(module_audit_path),
            module_audit.get("next_phase", "Run otclient_helper_module_audit.py before adding new modules."),
        ),
    ]
    items.extend(_roadmap_items(plan_path, validation.get("status", ""), gate, gate_path))
    blockers = [
        f"{gate_item.get('name')}: {gate_item.get('reason')}"
        for gate_item in gate.get("gates", [])
        if gate_item.get("status") != "passed"
    ]
    complete = gate.get("releasable_to_live") is True and not blockers
    next_command = (
        str(gate.get("next_command") or "")
        if gate.get("status") == "passed"
        else gate.get("next_command") or smoke_status.get("next_command") or ""
    )
    return GoalAudit(
        name="solteria-helper-goal-audit",
        status="complete" if complete else "blocked",
        complete=complete,
        items=items,
        blockers=blockers,
        next_action=gate.get("next_action") or smoke_status.get("next_action") or "Run ValidateDev.",
        next_command=next_command,
    )


def _status_tone(status: str) -> str:
    normalized = status.lower()
    if normalized in {"passed", "complete", "ready", "promoted", "releasable"}:
        return "good"
    if normalized in {"blocked", "missing", "failed", "parser_broken"} or normalized.startswith("blocked"):
        return "bad"
    return "warn"


def _label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()


def _render_status_badge(status: str) -> str:
    return f'<span class="badge {_status_tone(status)}">{html.escape(_label(status))}</span>'


def _render_item_rows(items: list[AuditItem]) -> str:
    rows: list[str] = []
    for item in items:
        note = item.note or "No additional operator note."
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(_label(item.name))}</strong></td>"
            f"<td>{_render_status_badge(item.status)}</td>"
            f"<td>{html.escape(note)}</td>"
            f"<td class=\"evidence\">{html.escape(item.evidence)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_html(audit: GoalAudit) -> str:
    """Render a standalone, read-only operator dashboard from the audit payload."""

    roadmap = [item for item in audit.items if item.name.startswith("P")]
    evidence_items = [item for item in audit.items if not item.name.startswith("P")]
    passed_count = sum(item.status == "passed" for item in audit.items)
    attention_count = len(audit.items) - passed_count
    roadmap_passed = sum(item.status == "passed" for item in roadmap)
    blockers = "".join(f"<li>{html.escape(blocker)}</li>" for blocker in audit.blockers) or "<li>No active blockers.</li>"
    command = html.escape(audit.next_command or "No command is required for the current audit state.")

    roadmap_cards = "\n".join(
        "<article class=\"phase\">"
        f"<span>{html.escape(item.name.split('_', 1)[0])}</span>"
        f"<strong>{html.escape(_label(item.name.split('_', 1)[-1]))}</strong>"
        f"{_render_status_badge(item.status)}"
        "</article>"
        for item in roadmap
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solteria Helper — Goal Audit</title>
<style>
:root {{ color-scheme: dark; --bg:#101416; --panel:#192024; --panel-2:#212a2f; --line:#344047; --text:#f0f4f5; --muted:#9aa8ae; --gold:#d7b36a; --good:#6ac48d; --warn:#e4b85e; --bad:#ef7373; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-width:320px; background:radial-gradient(circle at top right,#263338 0,transparent 30%),var(--bg); color:var(--text); font:15px/1.5 Inter,Segoe UI,Arial,sans-serif; }}
main {{ width:min(1180px,calc(100% - 32px)); margin:32px auto 48px; }}
header {{ display:flex; gap:24px; justify-content:space-between; align-items:flex-start; padding:28px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(135deg,#202a2f,#151b1f); }}
h1 {{ margin:0 0 5px; font-size:clamp(25px,4vw,38px); letter-spacing:-.035em; }}
h2 {{ margin:0; font-size:18px; }}
p {{ margin:0; }}
.eyebrow {{ color:var(--gold); font-size:12px; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }}
.status {{ min-width:185px; padding:13px 16px; border-radius:12px; text-align:center; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }}
.status.good {{ background:rgba(106,196,141,.15); color:var(--good); border:1px solid rgba(106,196,141,.45); }}
.status.warn {{ background:rgba(228,184,94,.15); color:var(--warn); border:1px solid rgba(228,184,94,.45); }}
.status.bad {{ background:rgba(239,115,115,.15); color:var(--bad); border:1px solid rgba(239,115,115,.45); }}
.metrics {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:18px 0; }}
.metric,.panel {{ border:1px solid var(--line); border-radius:14px; background:rgba(25,32,36,.93); }}
.metric {{ padding:18px; }} .metric span {{ display:block; color:var(--muted); font-size:13px; }} .metric strong {{ display:block; margin-top:2px; font-size:28px; }}
.panel {{ padding:22px; margin-top:18px; }}
.next {{ border-color:#7a663b; background:linear-gradient(135deg,rgba(102,81,38,.28),rgba(25,32,36,.98)); }}
.next-action {{ margin-top:14px; font-size:18px; font-weight:700; }}
code {{ display:block; max-width:100%; overflow:auto; padding:13px; border:1px solid #3c494d; border-radius:9px; background:#0e1315; color:#b9e3c6; white-space:pre-wrap; word-break:break-word; }}
.roadmap {{ display:grid; grid-template-columns:repeat(6,minmax(120px,1fr)); gap:10px; margin-top:15px; overflow-x:auto; }}
.phase {{ min-height:132px; padding:15px; border:1px solid var(--line); border-radius:12px; background:var(--panel-2); display:flex; flex-direction:column; gap:9px; }}
.phase span {{ color:var(--gold); font-size:13px; font-weight:800; }} .phase strong {{ min-height:44px; font-size:14px; }}
.badge {{ display:inline-block; width:max-content; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:800; white-space:nowrap; }}
.badge.good {{ color:var(--good); background:rgba(106,196,141,.14); }} .badge.warn {{ color:var(--warn); background:rgba(228,184,94,.14); }} .badge.bad {{ color:var(--bad); background:rgba(239,115,115,.14); }}
ul {{ margin:14px 0 0; padding-left:22px; }} li+li {{ margin-top:8px; }}
table {{ width:100%; margin-top:15px; border-collapse:collapse; font-size:13px; }} th,td {{ padding:11px 10px; border-top:1px solid var(--line); vertical-align:top; text-align:left; }} th {{ color:var(--muted); font-size:11px; letter-spacing:.08em; text-transform:uppercase; }} .evidence {{ max-width:260px; color:var(--muted); overflow-wrap:anywhere; }}
footer {{ margin-top:18px; color:var(--muted); font-size:12px; text-align:center; }}
@media (max-width:720px) {{ main {{ width:min(100% - 20px,1180px); margin-top:10px; }} header {{ padding:21px; flex-direction:column; }} .status {{ width:100%; }} .metrics {{ grid-template-columns:1fr; }} .roadmap {{ grid-template-columns:repeat(6,150px); }} table {{ min-width:760px; }} .table-wrap {{ overflow:auto; }} }}
</style>
</head>
<body>
<main>
  <header>
    <div>
      <p class="eyebrow">Read-only release routing</p>
      <h1>Solteria Helper Goal Audit</h1>
      <p>Current evidence, release blockers, and exactly one safe next action.</p>
    </div>
    <div class="status {_status_tone(audit.status)}">{html.escape(audit.status)}</div>
  </header>

  <section class="metrics" aria-label="Audit summary">
    <article class="metric"><span>Verified checks</span><strong>{passed_count}/{len(audit.items)}</strong></article>
    <article class="metric"><span>Needs attention</span><strong>{attention_count}</strong></article>
    <article class="metric"><span>Roadmap complete</span><strong>{roadmap_passed}/{len(roadmap)}</strong></article>
  </section>

  <section class="panel next">
    <p class="eyebrow">Do this next</p>
    <p class="next-action">{html.escape(audit.next_action)}</p>
    <code id="next-command">{command}</code>
  </section>

  <section class="panel">
    <p class="eyebrow">Delivery roadmap</p>
    <h2>P0–P5 status</h2>
    <div class="roadmap">{roadmap_cards}</div>
  </section>

  <section class="panel">
    <p class="eyebrow">Release gate</p>
    <h2>Active blockers</h2>
    <ul>{blockers}</ul>
  </section>

  <section class="panel">
    <p class="eyebrow">Evidence inventory</p>
    <h2>Audit checks</h2>
    <div class="table-wrap"><table><thead><tr><th>Check</th><th>Status</th><th>Operator note</th><th>Evidence</th></tr></thead><tbody>{_render_item_rows(evidence_items)}</tbody></table></div>
  </section>
  <footer>Generated locally from release evidence. This dashboard is read-only and never launches, stops, or promotes a client.</footer>
</main>
</body>
</html>
"""


def render_terminal_dashboard(audit: GoalAudit) -> str:
    """Return a compact dashboard for PowerShell and CI logs without ANSI dependencies."""

    roadmap = [item for item in audit.items if item.name.startswith("P")]
    passed_count = sum(item.status == "passed" for item in audit.items)
    lines = [
        "",
        "SOLTERIA HELPER  |  GOAL AUDIT",
        f"STATE: {_label(audit.status)}  |  verified: {passed_count}/{len(audit.items)}  |  blockers: {len(audit.blockers)}",
        "-" * 72,
        "ROADMAP: " + "  ".join(f"{item.name.split('_', 1)[0]}={item.status}" for item in roadmap),
        f"NEXT: {audit.next_action}",
    ]
    if audit.next_command:
        lines.append(f"COMMAND: {audit.next_command}")
    if audit.blockers:
        lines.append("BLOCKERS:")
        lines.extend(f"  - {blocker}" for blocker in audit.blockers)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--dev-dir", type=Path, default=DEFAULT_DEV_DIR)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--html-out", type=Path, default=None, help="Write a standalone read-only audit dashboard to this path.")
    parser.add_argument("--no-html", action="store_true", help="Do not write the default goal_audit.html dashboard.")
    parser.add_argument("--allow-blocked", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_audit(args.plan.resolve(), args.dev_dir.resolve())
    out = args.json_out or args.dev_dir / "goal_audit.json"
    write_json_atomic(out, asdict(audit))
    dashboard = None if args.no_html else args.html_out or args.dev_dir / "goal_audit.html"
    if dashboard is not None:
        write_text_atomic(dashboard, render_html(audit))
    print(render_terminal_dashboard(audit))
    print(f"[solteria-helper-goal-audit] JSON: {out}")
    if dashboard is not None:
        print(f"[solteria-helper-goal-audit] Dashboard: {dashboard}")
    print(f"[solteria-helper-goal-audit] Status: {audit.status}")
    print(f"[solteria-helper-goal-audit] Next: {audit.next_action}")
    if audit.next_command:
        print(f"[solteria-helper-goal-audit] Next command: {audit.next_command}")
    return 0 if audit.complete or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
