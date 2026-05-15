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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "evidence" / "vps-worktree-hygiene"
DEFAULT_REMOTE_DIR = "/opt/ctoa/runtime/evidence/worktree-hygiene/phase5-drycheck"
DEFAULT_CHECKLIST_SCRIPT = ROOT / "scripts" / "ops" / "phase5_nightly_checklist.py"
DEFAULT_CHECKLIST_OUTPUT = DEFAULT_EVIDENCE_DIR / "phase5-nightly-checklist.md"
DEFAULT_CHECKLIST_JSON = ROOT / "runtime" / "ci-artifacts" / "phase5-nightly-checklist.json"
DEFAULT_MORNING_BRIEF_OUT = DEFAULT_EVIDENCE_DIR / "phase5-morning-brief.md"
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

    parser.add_argument("--target-runs", type=int, default=3)
    parser.add_argument("--nightly-hour", type=int, default=2)
    parser.add_argument("--nightly-minute", type=int, default=20)
    parser.add_argument("--window-minutes", type=int, default=45)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--sync-all", action="store_true", help="Re-copy all remote snapshots even if local copy exists")
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

    return checklist_rc


if __name__ == "__main__":
    raise SystemExit(main())