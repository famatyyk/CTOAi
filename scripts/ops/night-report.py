#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write CTOA night activity report")
    parser.add_argument("--log-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--window-hours", type=int, default=12)
    parser.add_argument("--manifest-dir", default="")
    return parser.parse_args()


def parse_ts(line: str) -> datetime | None:
    m = re.search(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2})\]", line)
    if m:
        try:
            return datetime.fromisoformat(m.group(1))
        except ValueError:
            return None

    m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})", line)
    if not m:
        return None
    try:
        ts = datetime.strptime(f"{m.group(1)}.{m.group(2)}", "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None
    return ts.astimezone()


def resolve_manifest_dir(cli_value: str) -> Path | None:
    candidates: list[Path] = []
    if cli_value:
        candidates.append(Path(cli_value))

    env_value = os.getenv("CTOA_GENERATOR_MANIFEST_DIR", "").strip()
    if env_value:
        candidates.append(Path(env_value))

    generated_env = os.getenv("CTOA_GENERATED_DIR", "").strip()
    if generated_env:
        candidates.append(Path(generated_env) / "manifests")

    candidates.extend([
        ROOT / "generated" / "manifests",
        ROOT / "runtime" / "generated" / "manifests",
        Path("/opt/ctoa/generated/manifests"),
    ])

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def collect_manifest_stats(manifest_dir: Path | None, window_start: datetime) -> dict[str, Any]:
    stats = {
        "generated": 0,
        "generator_failed": 0,
        "manifests_seen": 0,
        "manifest_dir": str(manifest_dir) if manifest_dir else "",
    }
    if manifest_dir is None or not manifest_dir.exists():
        return stats

    for manifest_path in manifest_dir.glob("*/manifest.json"):
        try:
            modified = datetime.fromtimestamp(manifest_path.stat().st_mtime, tz=timezone.utc).astimezone()
        except OSError:
            continue
        if modified < window_start:
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        generated = payload.get("generated") if isinstance(payload, dict) else []
        failed = payload.get("failed") if isinstance(payload, dict) else []
        stats["generated"] += len(generated) if isinstance(generated, list) else 0
        stats["generator_failed"] += len(failed) if isinstance(failed, list) else 0
        stats["manifests_seen"] += 1

    return stats


def build_report(log_file: Path, manifest_dir: Path | None, window_hours: int) -> str:
    now = datetime.now().astimezone()
    window_start = now - timedelta(hours=window_hours)

    tick_count = 0
    queued_total = 0
    queued_last = 0
    validated_ok = 0
    validated_failed = 0
    last_errors: list[str] = []
    recent_lines = 0

    if log_file.exists():
        for raw_line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
            ts = parse_ts(raw_line)
            if ts is not None and ts < window_start:
                continue
            recent_lines += 1

            if "LOOP_TICK start" in raw_line:
                tick_count += 1

            match = re.search(r"Server #\d+: (\d+) tasks queued", raw_line)
            if match:
                value = int(match.group(1))
                queued_total += value
                queued_last = value

            if "Validated " in raw_line and raw_line.rstrip().endswith("VALIDATED"):
                validated_ok += 1
            elif "Validated " in raw_line and raw_line.rstrip().endswith("FAILED"):
                validated_failed += 1
            elif "Validate error for " in raw_line:
                validated_failed += 1

            lowered = raw_line.lower()
            if " error " in lowered or lowered.startswith("error") or "traceback" in lowered or "exception" in lowered:
                last_errors.append(raw_line.strip())

    manifest_stats = collect_manifest_stats(manifest_dir, window_start)
    last_errors = last_errors[-10:]

    lines = [
        "# CTOA Night Report",
        "",
        f"- Generated at: {now.replace(microsecond=0).isoformat()}",
        f"- Window: last {window_hours}h",
        f"- Source log: {log_file}",
        f"- Manifest dir: {manifest_stats['manifest_dir'] or '-'}",
        "",
        "## Activity",
        f"- Loop ticks: {tick_count}",
        f"- Recent log lines in window: {recent_lines}",
        f"- Tasks queued total: {queued_total}",
        f"- Tasks queued last observed: {queued_last}",
        f"- Modules generated: {manifest_stats['generated']}",
        f"- Generator failures: {manifest_stats['generator_failed']}",
        f"- Modules validated OK: {validated_ok}",
        f"- Modules validated FAILED: {validated_failed}",
        f"- Generator manifests seen: {manifest_stats['manifests_seen']}",
        "",
        "## Last Errors",
    ]

    if last_errors:
        lines.extend(f"- {line}" for line in last_errors)
    else:
        lines.append("- No recent errors detected in the selected window.")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    log_file = Path(args.log_file)
    report_file = Path(args.report_file)
    manifest_dir = resolve_manifest_dir(args.manifest_dir)
    report = build_report(log_file=log_file, manifest_dir=manifest_dir, window_hours=max(1, args.window_hours))
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report, encoding="utf-8")
    print(f"[night-report] wrote {report_file}")


if __name__ == "__main__":
    main()