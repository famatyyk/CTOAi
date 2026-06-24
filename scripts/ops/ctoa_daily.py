#!/usr/bin/env python3
"""CTOAi daily loop: preflight + smoke tests + AI plan + markdown report."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.llm_providers import get_provider
from scripts.ops import ctoa_env_doctor
from scripts.ops.git_exec import run_git


@dataclass
class DailyResult:
    ts: str
    doctor: dict[str, Any]
    git_status: str
    smoke_cmd: list[str]
    smoke_exit: int
    smoke_stdout: str
    smoke_stderr: str
    plan_text: str


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_tokens(tokens: list[str]) -> list[str]:
    safe: list[str] = []
    for token in tokens:
        if not token or len(token) > 240:
            raise ValueError(f"Unsupported token: {token!r}")
        if any(ch in token for ch in [";", "&", "|", "`"]):
            raise ValueError(f"Unsupported token: {token!r}")
        safe.append(token)
    return safe


def run_smoke(smoke_args: str) -> tuple[list[str], int, str, str]:
    tokens = shlex.split(smoke_args.strip()) if smoke_args.strip() else ["tests/test_suite.py", "-q"]
    safe_tokens = _sanitize_tokens(tokens)
    cmd = [sys.executable, "-m", "pytest", *safe_tokens]
    res = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return cmd, res.returncode, res.stdout.strip(), res.stderr.strip()


def git_status_short() -> str:
    out = run_git(["status", "-sb"], cwd=ROOT, check=False).stdout
    return (out or "").strip()


def build_plan_prompt(doctor: dict[str, Any], git_status: str, smoke_exit: int, smoke_stdout: str, smoke_stderr: str) -> str:
    doctor_json = json.dumps(doctor, ensure_ascii=False)
    smoke_tail = "\n".join((smoke_stdout or "").splitlines()[-20:])
    stderr_tail = "\n".join((smoke_stderr or "").splitlines()[-20:])
    return (
        "Create a decision-complete daily execution plan for this repo.\n"
        "Output sections: Summary, Top Priorities (max 5), Risks, Next Actions (numbered).\n"
        "Be concrete and concise.\n\n"
        f"Doctor report JSON:\n{doctor_json}\n\n"
        f"Git status:\n{git_status}\n\n"
        f"Smoke test exit: {smoke_exit}\n"
        f"Smoke test output (tail):\n{smoke_tail}\n\n"
        f"Smoke stderr (tail):\n{stderr_tail}\n"
    )


def generate_plan(doctor: dict[str, Any], git_status: str, smoke_exit: int, smoke_stdout: str, smoke_stderr: str, *, mode: str = "ops") -> str:
    try:
        provider = get_provider()
    except Exception as exc:
        return f"LLM unavailable: {exc}\nFallback: fix FAIL checks, ensure smoke tests pass, then continue with highest-risk module."

    if not provider.health():
        return "LLM health check failed. Fallback: resolve preflight FAIL checks and rerun smoke tests."

    mode_preamble = {
        "ops": "You are CTO operations lead. Prioritize reliability and delivery safety.",
        "architect": "You are software architect. Prioritize design integrity and migration safety.",
        "reviewer": "You are reviewer. Prioritize defects, regressions, and tests.",
    }.get(mode, "You are CTO assistant.")

    try:
        return provider.complete(
            system_prompt=mode_preamble,
            user_prompt=build_plan_prompt(doctor, git_status, smoke_exit, smoke_stdout, smoke_stderr),
            temperature=0.1,
            max_tokens=1200,
        )
    except Exception as exc:
        return f"LLM plan generation failed: {exc}\nFallback: review doctor+smoke output and execute top 3 risk-reduction actions."


def render_report(res: DailyResult) -> str:
    smoke_excerpt = "\n".join(res.smoke_stdout.splitlines()[-30:]) if res.smoke_stdout else "(no stdout)"
    stderr_excerpt = "\n".join(res.smoke_stderr.splitlines()[-20:]) if res.smoke_stderr else "(no stderr)"
    doctor_status = res.doctor.get("status", "UNKNOWN")
    return (
        f"# CTOAi Daily Report ({res.ts[:10]})\n\n"
        f"- Generated at: `{res.ts}`\n"
        f"- Doctor status: `{doctor_status}`\n"
        f"- Smoke exit: `{res.smoke_exit}`\n"
        f"- Smoke command: `{' '.join(res.smoke_cmd)}`\n\n"
        "## Git Status\n\n"
        "```text\n"
        f"{res.git_status or '(clean)'}\n"
        "```\n\n"
        "## Doctor Checks\n\n"
        "```json\n"
        f"{json.dumps(res.doctor, indent=2, ensure_ascii=False)}\n"
        "```\n\n"
        "## Smoke Output (tail)\n\n"
        "```text\n"
        f"{smoke_excerpt}\n"
        "```\n\n"
        "## Smoke Stderr (tail)\n\n"
        "```text\n"
        f"{stderr_excerpt}\n"
        "```\n\n"
        "## AI Daily Plan\n\n"
        f"{res.plan_text}\n"
    )


def save_report(text: str, *, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    path = out_dir / f"{date_str}.md"
    path.write_text(text, encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CTOAi daily local loop")
    parser.add_argument("--smoke", default="tests/test_suite.py -q", help="Pytest args for smoke test")
    parser.add_argument("--mode", default="ops", choices=["ops", "architect", "reviewer"])
    parser.add_argument("--out-dir", default=str(ROOT / ".ctoa-local" / "daily"))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on doctor FAIL or smoke failure")
    parser.add_argument("--print-report", action="store_true", help="Print full markdown report to stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ts = now_iso()
    doctor = ctoa_env_doctor.run_doctor(ctoa_env_doctor.DEFAULT_ORIGIN)
    status = git_status_short()
    cmd, smoke_exit, smoke_out, smoke_err = run_smoke(args.smoke)
    plan = generate_plan(doctor, status, smoke_exit, smoke_out, smoke_err, mode=args.mode)

    result = DailyResult(
        ts=ts,
        doctor=doctor,
        git_status=status,
        smoke_cmd=cmd,
        smoke_exit=smoke_exit,
        smoke_stdout=smoke_out,
        smoke_stderr=smoke_err,
        plan_text=plan,
    )
    report = render_report(result)
    report_path = save_report(report, out_dir=Path(args.out_dir).resolve())

    print("[ctoa-daily] Done")
    print(f"[ctoa-daily] Report: {report_path}")
    print(f"[ctoa-daily] Doctor: {doctor.get('status', 'UNKNOWN')} | Smoke exit: {smoke_exit}")
    if args.print_report:
        print("\n" + report)

    if args.strict and (doctor.get("status") == "FAIL" or smoke_exit != 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

