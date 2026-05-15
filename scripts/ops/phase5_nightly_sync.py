#!/usr/bin/env python3
"""One-command Phase-5 nightly monitoring: pull VPS evidence + regenerate checklist + print short status."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "evidence" / "vps-worktree-hygiene"
DEFAULT_REMOTE_DIR = "/opt/ctoa/runtime/evidence/worktree-hygiene/phase5-drycheck"
DEFAULT_CHECKLIST_SCRIPT = ROOT / "scripts" / "ops" / "phase5_nightly_checklist.py"
DEFAULT_CHECKLIST_OUTPUT = DEFAULT_EVIDENCE_DIR / "phase5-nightly-checklist.md"
DEFAULT_CHECKLIST_JSON = ROOT / "runtime" / "ci-artifacts" / "phase5-nightly-checklist.json"
DEFAULT_MORNING_BRIEF_OUT = DEFAULT_EVIDENCE_DIR / "phase5-morning-brief.md"
DEFAULT_NOTIFY_ENV_FILE = ROOT / ".ctoa-local" / "phase5-notify.env"
DEFAULT_STEP9_PLAN_PATH = ROOT / "docs" / "VPS_WORKTREE_HYGIENE_PLAN.md"
DEFAULT_STEP9_CLOSURE_EVIDENCE_OUT = DEFAULT_EVIDENCE_DIR / "phase5-step9-closure.md"
DEFAULT_EVIDENCE_README_PATH = DEFAULT_EVIDENCE_DIR / "README.md"
LOCAL_PREFIX = "phase5-drycheck-"
TIMESTAMP_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")


def _default_key_path() -> Path:
    key_env = os.getenv("CTOA_VPS_KEY_PATH", "").strip()
    if key_env:
        return Path(key_env).expanduser()

    user_profile = os.getenv("USERPROFILE", "").strip()
    if user_profile:
        return Path(user_profile) / ".ssh" / "ctoa_vps_auto_ed25519"

    return Path(".ssh/ctoa_vps_auto_ed25519")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Phase-5 dry-check evidence and regenerate nightly checklist")
    parser.add_argument("--host", default="116.202.96.250")
    parser.add_argument("--user", default="ctoa-admin")
    parser.add_argument("--key-path", default=str(_default_key_path()))
    parser.add_argument("--ssh-timeout", type=int, default=20)

    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--local-evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))

    parser.add_argument("--checklist-script", default=str(DEFAULT_CHECKLIST_SCRIPT))
    parser.add_argument("--checklist-output", default=str(DEFAULT_CHECKLIST_OUTPUT))
    parser.add_argument("--checklist-json-out", default=str(DEFAULT_CHECKLIST_JSON))
    parser.add_argument("--morning-brief-out", default=str(DEFAULT_MORNING_BRIEF_OUT))
    parser.add_argument("--notify-env-file", default=str(DEFAULT_NOTIFY_ENV_FILE))

    parser.add_argument("--target-runs", type=int, default=3)
    parser.add_argument("--nightly-hour", type=int, default=2)
    parser.add_argument("--nightly-minute", type=int, default=20)
    parser.add_argument("--window-minutes", type=int, default=45)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--auto-close-step9", action="store_true")
    parser.add_argument("--sync-all", action="store_true", help="Re-copy all remote snapshots even if local copy exists")

    parser.add_argument("--discord-webhook-url", default=os.getenv("CTOA_DISCORD_WEBHOOK_URL", ""))
    parser.add_argument("--slack-webhook-url", default=os.getenv("CTOA_SLACK_WEBHOOK_URL", ""))

    parser.add_argument("--step9-plan-path", default=str(DEFAULT_STEP9_PLAN_PATH))
    parser.add_argument("--step9-closure-evidence-out", default=str(DEFAULT_STEP9_CLOSURE_EVIDENCE_OUT))
    parser.add_argument("--step9-evidence-readme-path", default=str(DEFAULT_EVIDENCE_README_PATH))

    return parser.parse_args()


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\nstdout={stdout}\nstderr={stderr}"
        )
    return result


def _ssh_base(key_path: Path, timeout: int) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={timeout}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-i",
        str(key_path),
    ]


def _scp_base(key_path: Path, timeout: int) -> list[str]:
    return [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={timeout}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-i",
        str(key_path),
    ]


def parse_remote_timestamps(raw: str) -> list[str]:
    values: set[str] = set()
    for line in raw.splitlines():
        value = line.strip()
        if TIMESTAMP_PATTERN.match(value):
            values.add(value)
    return sorted(values)


def list_remote_timestamps(host: str, user: str, key_path: Path, timeout: int, remote_dir: str) -> list[str]:
    remote_cmd = (
        "set -e; "
        f"if [ -d {shlex.quote(remote_dir)} ]; then "
        f"find {shlex.quote(remote_dir)} -mindepth 1 -maxdepth 1 -type d -printf '%f\\n' | sort; "
        "fi"
    )
    cmd = _ssh_base(key_path, timeout) + [f"{user}@{host}", remote_cmd]
    result = _run(cmd, check=True)
    return parse_remote_timestamps(result.stdout)


def _local_snapshot_dir(local_evidence_dir: Path, timestamp: str) -> Path:
    return local_evidence_dir / f"{LOCAL_PREFIX}{timestamp}"


def should_sync_snapshot(local_snapshot_dir: Path, sync_all: bool) -> bool:
    if sync_all:
        return True
    required = [
        local_snapshot_dir / "summary.md",
        local_snapshot_dir / "report.txt",
        local_snapshot_dir / "status-porcelain.txt",
    ]
    return not all(path.exists() for path in required)


def sync_snapshot(
    host: str,
    user: str,
    key_path: Path,
    timeout: int,
    remote_dir: str,
    local_evidence_dir: Path,
    timestamp: str,
) -> Path:
    local_snapshot_dir = _local_snapshot_dir(local_evidence_dir, timestamp)
    local_snapshot_dir.mkdir(parents=True, exist_ok=True)

    scp_base = _scp_base(key_path, timeout)
    for filename in ("summary.md", "report.txt", "status-porcelain.txt"):
        remote = f"{user}@{host}:{remote_dir}/{timestamp}/{filename}"
        local = str(local_snapshot_dir / filename)
        _run(scp_base + [remote, local], check=True)

    return local_snapshot_dir


def run_checklist(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(Path(args.checklist_script).resolve()),
        "--evidence-dir",
        str(Path(args.local_evidence_dir).resolve()),
        "--output",
        str(Path(args.checklist_output).resolve()),
        "--json-out",
        str(Path(args.checklist_json_out).resolve()),
        "--target-runs",
        str(args.target_runs),
        "--nightly-hour",
        str(args.nightly_hour),
        "--nightly-minute",
        str(args.nightly_minute),
        "--window-minutes",
        str(args.window_minutes),
    ]
    if args.require_complete:
        cmd.append("--require-complete")

    result = _run(cmd, check=False)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def load_checklist_payload(json_path: Path) -> dict[str, Any]:
    if not json_path.exists():
        return {}
    return json.loads(json_path.read_text(encoding="utf-8"))


def render_short_status(payload: dict[str, Any], pulled_new: int, skipped_existing: int) -> str:
    status = payload.get("overall_status", "UNKNOWN")
    selected = payload.get("selected_nightly_runs", "?")
    target = payload.get("target_runs", "?")
    pending = payload.get("pending_runs", "?")
    alerts = payload.get("alerts_count", "?")
    return (
        "[phase5-nightly-sync] "
        f"status={status} nightly_runs={selected}/{target} pending={pending} alerts={alerts} "
        f"pulled_new={pulled_new} skipped_existing={skipped_existing}"
    )


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_notify_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_webhook_urls(discord_cli: str, slack_cli: str, notify_env_file: Path) -> tuple[str, str, str]:
    discord = discord_cli.strip()
    slack = slack_cli.strip()
    source = "cli"

    if discord and slack:
        return discord, slack, source

    env_values = load_notify_env_file(notify_env_file)

    if not discord:
        discord = str(env_values.get("CTOA_DISCORD_WEBHOOK_URL", "")).strip()
    if not slack:
        slack = str(env_values.get("CTOA_SLACK_WEBHOOK_URL", "")).strip()

    if discord or slack:
        source = "notify_env_file"
    elif discord_cli.strip() or slack_cli.strip():
        source = "cli_partial"
    else:
        source = "none"

    return discord, slack, source


def render_notify_source_status(source: str, env_file: Path, discord_set: bool, slack_set: bool) -> str:
    return (
        "[phase5-notify-config] "
        f"source={source} env_file={env_file} discord_set={discord_set} slack_set={slack_set}"
    )


def build_morning_brief(payload: dict[str, Any], pulled_new: int, skipped_existing: int) -> dict[str, Any]:
    selected = _as_int(payload.get("selected_nightly_runs"), 0)
    target = _as_int(payload.get("target_runs"), 3)
    pending = _as_int(payload.get("pending_runs"), max(0, target - selected))
    alerts = _as_int(payload.get("alerts_count"), 0)
    checklist_status = str(payload.get("overall_status", "UNKNOWN"))

    if alerts > 0:
        verdict = "ATTENTION"
        reason = "alerts_detected"
    elif pending > 0:
        verdict = "ATTENTION"
        reason = "nightly_runs_pending"
    else:
        verdict = "PASS"
        reason = "three_nightly_runs_verified"

    return {
        "generated_utc": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "verdict": verdict,
        "reason": reason,
        "checklist_status": checklist_status,
        "nightly_runs": f"{selected}/{target}",
        "pending": pending,
        "alerts": alerts,
        "pulled_new": pulled_new,
        "skipped_existing": skipped_existing,
    }


def render_morning_brief_markdown(brief: dict[str, Any]) -> str:
    lines = [
        "# Phase-5 Morning Brief",
        "",
        f"generated_utc: {brief['generated_utc']}",
        f"verdict: {brief['verdict']}",
        f"reason: {brief['reason']}",
        "",
        "## KPI Snapshot",
        "",
        f"- checklist_status: {brief['checklist_status']}",
        f"- nightly_runs: {brief['nightly_runs']}",
        f"- pending: {brief['pending']}",
        f"- alerts: {brief['alerts']}",
        f"- pulled_new: {brief['pulled_new']}",
        f"- skipped_existing: {brief['skipped_existing']}",
        "",
        "## Sprint Log Paste",
        "",
        (
            "- Phase-5 morning check: "
            f"{brief['verdict']} (runs={brief['nightly_runs']}, pending={brief['pending']}, alerts={brief['alerts']}, "
            f"checklist={brief['checklist_status']})"
        ),
    ]
    return "\n".join(lines) + "\n"


def write_morning_brief(path: Path, brief: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_morning_brief_markdown(brief), encoding="utf-8")


def render_morning_brief_status(path: Path, brief: dict[str, Any]) -> str:
    return (
        "[phase5-morning-brief] "
        f"verdict={brief['verdict']} runs={brief['nightly_runs']} pending={brief['pending']} alerts={brief['alerts']} "
        f"output={path}"
    )


def _post_json(url: str, payload: dict[str, Any], timeout_sec: int = 12) -> tuple[bool, str]:
    if not url.strip():
        return False, "missing_url"

    data = json.dumps(payload).encode("utf-8")
    request = urlrequest.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urlrequest.urlopen(request, timeout=timeout_sec) as response:
            status_code = int(getattr(response, "status", 200))
        if 200 <= status_code < 300:
            return True, f"http_{status_code}"
        return False, f"http_{status_code}"
    except urlerror.HTTPError as exc:
        return False, f"http_{exc.code}"
    except Exception as exc:
        return False, exc.__class__.__name__


def build_attention_message(brief: dict[str, Any]) -> str:
    return (
        "[CTOA][Phase-5] ATTENTION "
        f"runs={brief.get('nightly_runs', '?')} pending={brief.get('pending', '?')} "
        f"alerts={brief.get('alerts', '?')} checklist={brief.get('checklist_status', 'UNKNOWN')} "
        f"reason={brief.get('reason', 'unspecified')}"
    )


def send_attention_notifications(
    brief: dict[str, Any],
    discord_webhook_url: str,
    slack_webhook_url: str,
    post_json=_post_json,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "verdict": brief.get("verdict", "UNKNOWN"),
        "reason": "",
        "results": {
            "discord": {"state": "skipped", "detail": "not_applicable"},
            "slack": {"state": "skipped", "detail": "not_applicable"},
        },
    }

    if brief.get("verdict") != "ATTENTION":
        result["reason"] = "verdict_not_attention"
        return result

    message = build_attention_message(brief)
    attempted = 0
    delivered = 0

    if discord_webhook_url.strip():
        attempted += 1
        ok, detail = post_json(discord_webhook_url.strip(), {"content": message})
        result["results"]["discord"] = {"state": "sent" if ok else "failed", "detail": detail}
        if ok:
            delivered += 1
    else:
        result["results"]["discord"] = {"state": "skipped", "detail": "missing_webhook"}

    if slack_webhook_url.strip():
        attempted += 1
        ok, detail = post_json(slack_webhook_url.strip(), {"text": message})
        result["results"]["slack"] = {"state": "sent" if ok else "failed", "detail": detail}
        if ok:
            delivered += 1
    else:
        result["results"]["slack"] = {"state": "skipped", "detail": "missing_webhook"}

    if attempted == 0:
        result["reason"] = "no_channels_configured"
    elif delivered == 0:
        result["reason"] = "delivery_failed"
    else:
        result["reason"] = "sent"

    return result


def render_attention_notify_status(notification_result: dict[str, Any]) -> str:
    discord_state = notification_result.get("results", {}).get("discord", {}).get("state", "unknown")
    slack_state = notification_result.get("results", {}).get("slack", {}).get("state", "unknown")
    return (
        "[phase5-attention-notify] "
        f"verdict={notification_result.get('verdict', 'UNKNOWN')} "
        f"reason={notification_result.get('reason', 'unknown')} "
        f"discord={discord_state} slack={slack_state}"
    )


def is_step9_ready(payload: dict[str, Any]) -> bool:
    selected = _as_int(payload.get("selected_nightly_runs"), 0)
    target = _as_int(payload.get("target_runs"), 3)
    pending = _as_int(payload.get("pending_runs"), max(0, target - selected))
    alerts = _as_int(payload.get("alerts_count"), 0)
    return selected >= target and pending == 0 and alerts == 0


def render_step9_closure_markdown(brief: dict[str, Any], payload: dict[str, Any], plan_path: Path) -> str:
    lines = [
        "# Phase 5 Step-9 Closure Evidence",
        "",
        f"generated_utc: {brief.get('generated_utc', datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ'))}",
        "closure_status: DONE",
        "closure_trigger: automated by scripts/ops/phase5_nightly_sync.py",
        f"plan_path: {plan_path}",
        f"checklist_status: {payload.get('overall_status', 'UNKNOWN')}",
        f"nightly_runs: {payload.get('selected_nightly_runs', '?')}/{payload.get('target_runs', '?')}",
        f"pending_runs: {payload.get('pending_runs', '?')}",
        f"alerts_count: {payload.get('alerts_count', '?')}",
        "",
        "Criteria met: 3/3 nightly runs collected and alerts=0.",
    ]
    return "\n".join(lines) + "\n"


def write_step9_closure_evidence(path: Path, brief: dict[str, Any], payload: dict[str, Any], plan_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_step9_closure_markdown(brief, payload, plan_path), encoding="utf-8")


def mark_step9_done_in_plan(plan_path: Path, done_utc: str, evidence_rel_path: str) -> dict[str, Any]:
    if not plan_path.exists():
        return {"updated": False, "already_done": False, "error": "plan_missing"}

    lines = plan_path.read_text(encoding="utf-8").splitlines()
    updated = False
    already_done = False

    for index, line in enumerate(lines):
        if line.startswith("9. [x] Monitor first 3 nightly dry-check runs and alert on any non-empty porcelain status."):
            already_done = True
            break
        if line.startswith("9. [ ] Monitor first 3 nightly dry-check runs and alert on any non-empty porcelain status."):
            lines[index] = (
                "9. [x] Monitor first 3 nightly dry-check runs and alert on any non-empty porcelain status. "
                f"(DONE: {done_utc}; automated closure via scripts/ops/phase5_nightly_sync.py; evidence: {evidence_rel_path})"
            )
            updated = True
            break

    if updated:
        plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"updated": True, "already_done": False, "error": ""}

    if already_done:
        return {"updated": False, "already_done": True, "error": ""}

    return {"updated": False, "already_done": False, "error": "step9_line_not_found"}


def update_step9_closure_in_readme(readme_path: Path, done_utc: str) -> bool:
    if not readme_path.exists():
        return False

    content = readme_path.read_text(encoding="utf-8")
    header = "## Phase 5 Step-9 Closure"
    block = (
        "\n## Phase 5 Step-9 Closure\n\n"
        "- status: DONE\n"
        f"- done_utc: {done_utc}\n"
        "- evidence: phase5-step9-closure.md\n"
    )

    if header not in content:
        readme_path.write_text(content.rstrip("\n") + block + "\n", encoding="utf-8")
        return True

    updated_content = re.sub(r"(- done_utc:\s*).*$", rf"\1{done_utc}", content, count=1, flags=re.MULTILINE)
    if updated_content != content:
        readme_path.write_text(updated_content, encoding="utf-8")
        return True
    return False


def auto_close_step9_if_ready(
    payload: dict[str, Any],
    brief: dict[str, Any],
    plan_path: Path,
    closure_evidence_path: Path,
    evidence_readme_path: Path,
) -> dict[str, Any]:
    if not is_step9_ready(payload):
        return {"ready": False, "ok": True, "plan": "not_ready", "readme": "not_ready", "evidence": "not_ready"}

    done_utc = str(brief.get("generated_utc") or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    write_step9_closure_evidence(closure_evidence_path, brief, payload, plan_path)

    try:
        evidence_rel_path = closure_evidence_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        evidence_rel_path = str(closure_evidence_path)

    plan_result = mark_step9_done_in_plan(plan_path, done_utc=done_utc, evidence_rel_path=evidence_rel_path)
    if plan_result.get("error"):
        return {
            "ready": True,
            "ok": False,
            "plan": f"error:{plan_result['error']}",
            "readme": "skipped",
            "evidence": "written",
        }

    readme_updated = update_step9_closure_in_readme(evidence_readme_path, done_utc=done_utc)
    return {
        "ready": True,
        "ok": True,
        "plan": "updated" if plan_result.get("updated") else "already_done",
        "readme": "updated" if readme_updated else "unchanged",
        "evidence": "written",
    }


def render_step9_close_status(result: dict[str, Any]) -> str:
    return (
        "[phase5-step9-close] "
        f"ready={result.get('ready', False)} ok={result.get('ok', False)} "
        f"plan={result.get('plan', 'unknown')} readme={result.get('readme', 'unknown')} "
        f"evidence={result.get('evidence', 'unknown')}"
    )


def main() -> int:
    args = parse_args()

    key_path = Path(args.key_path).expanduser().resolve()
    if not key_path.exists():
        print(f"[phase5-nightly-sync] SSH key not found: {key_path}", file=sys.stderr)
        return 3

    local_evidence_dir = Path(args.local_evidence_dir).resolve()
    local_evidence_dir.mkdir(parents=True, exist_ok=True)

    try:
        remote_timestamps = list_remote_timestamps(
            host=args.host,
            user=args.user,
            key_path=key_path,
            timeout=args.ssh_timeout,
            remote_dir=args.remote_dir,
        )
    except RuntimeError as exc:
        print(f"[phase5-nightly-sync] Failed to list remote snapshots: {exc}", file=sys.stderr)
        return 4

    pulled_new = 0
    skipped_existing = 0

    for timestamp in remote_timestamps:
        local_snapshot_dir = _local_snapshot_dir(local_evidence_dir, timestamp)
        if not should_sync_snapshot(local_snapshot_dir, sync_all=args.sync_all):
            skipped_existing += 1
            continue
        try:
            sync_snapshot(
                host=args.host,
                user=args.user,
                key_path=key_path,
                timeout=args.ssh_timeout,
                remote_dir=args.remote_dir,
                local_evidence_dir=local_evidence_dir,
                timestamp=timestamp,
            )
            pulled_new += 1
        except RuntimeError as exc:
            print(f"[phase5-nightly-sync] Failed to sync snapshot {timestamp}: {exc}", file=sys.stderr)
            return 5

    checklist_rc = run_checklist(args)
    checklist_payload = load_checklist_payload(Path(args.checklist_json_out).resolve())

    short_status = render_short_status(checklist_payload, pulled_new=pulled_new, skipped_existing=skipped_existing)
    print(short_status)

    morning_brief = build_morning_brief(checklist_payload, pulled_new=pulled_new, skipped_existing=skipped_existing)
    morning_brief_path = Path(args.morning_brief_out).resolve()
    write_morning_brief(morning_brief_path, morning_brief)
    print(render_morning_brief_status(morning_brief_path, morning_brief))

    notify_env_file = Path(args.notify_env_file).expanduser().resolve()
    discord_webhook_url, slack_webhook_url, notify_source = resolve_webhook_urls(
        args.discord_webhook_url,
        args.slack_webhook_url,
        notify_env_file,
    )
    print(
        render_notify_source_status(
            notify_source,
            notify_env_file,
            discord_set=bool(discord_webhook_url),
            slack_set=bool(slack_webhook_url),
        )
    )

    notification_result = send_attention_notifications(
        morning_brief,
        discord_webhook_url=discord_webhook_url,
        slack_webhook_url=slack_webhook_url,
    )
    print(render_attention_notify_status(notification_result))

    if args.auto_close_step9:
        close_result = auto_close_step9_if_ready(
            checklist_payload,
            morning_brief,
            plan_path=Path(args.step9_plan_path).resolve(),
            closure_evidence_path=Path(args.step9_closure_evidence_out).resolve(),
            evidence_readme_path=Path(args.step9_evidence_readme_path).resolve(),
        )
        print(render_step9_close_status(close_result))
        if not close_result.get("ok", False):
            return 6

    return checklist_rc


if __name__ == "__main__":
    raise SystemExit(main())