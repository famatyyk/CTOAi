#!/usr/bin/env python3
"""Publisher Agent – Launcher Day.

Criteria (any one triggers):
  - modules_generated >= CTOA_DAILY_MODULE_LIMIT  (default 50)
  - programs_generated >= CTOA_DAILY_PROGRAM_LIMIT (default 5)
    AND avg_quality >= CTOA_MIN_QUALITY (default 90)

On trigger:
  1. Zip all VALIDATED outputs into /opt/ctoa/releases/launcher-YYYYMMDD.zip
  2. Commit release manifest to git
  3. Create GitHub release via `gh` CLI (if available)
  4. Mark daily_stats.launcher_day = TRUE
  5. Write LAUNCHER_DAY.md summary

Run: python3 -m runner.agents.publisher_agent
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [publisher] %(levelname)s %(message)s",
)
log = logging.getLogger("publisher")

DAILY_MODULE_LIMIT  = int(os.environ.get("CTOA_DAILY_MODULE_LIMIT",  "50"))
DAILY_PROGRAM_LIMIT = int(os.environ.get("CTOA_DAILY_PROGRAM_LIMIT", "5"))
MIN_QUALITY         = int(os.environ.get("CTOA_MIN_QUALITY",          "90"))

REPO_DIR      = Path(os.environ.get("CTOA_REPO_DIR",    "/opt/ctoa"))
RELEASES_DIR  = Path(os.environ.get("CTOA_RELEASES_DIR", "/opt/ctoa/releases"))
GENERATED_DIR = Path(os.environ.get("CTOA_GENERATED_DIR", "/opt/ctoa/generated"))


def _criteria_met(today_str: str) -> tuple[bool, str]:
    row = db.query_one(
        "SELECT modules_generated, programs_generated, avg_quality, launcher_day "
        "FROM daily_stats WHERE dt=%s",
        (today_str,),
    )
    if not row:
        return False, "no stats yet"
    if row["launcher_day"]:
        return False, "already launched today"

    modules_ok  = row["modules_generated"] >= DAILY_MODULE_LIMIT
    programs_ok = (
        row["programs_generated"] >= DAILY_PROGRAM_LIMIT
        and (row["avg_quality"] or 0) >= MIN_QUALITY
    )
    if modules_ok:
        return True, f"module limit reached ({row['modules_generated']}/{DAILY_MODULE_LIMIT})"
    if programs_ok:
        return True, (
            f"program limit reached ({row['programs_generated']}/{DAILY_PROGRAM_LIMIT}) "
            f"@ avg quality {row['avg_quality']:.1f}"
        )
    return False, (
        f"not yet: {row['modules_generated']} modules, "
        f"{row['programs_generated']} programs @ {row['avg_quality']:.1f} quality"
    )


def _collect_validated() -> list[dict]:
    return db.query_all(
        "SELECT task_id, output_path, quality_score FROM modules "
        "WHERE status='VALIDATED' AND output_path IS NOT NULL ORDER BY quality_score DESC"
    )


def _create_zip(today_str: str, mods: list[dict]) -> Path:
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RELEASES_DIR / f"launcher-{today_str}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for mod in mods:
            p = Path(mod["output_path"])
            if p.exists():
                arcname = f"modules/{p.parent.name}/{p.name}"
                zf.write(p, arcname)
    return zip_path


def _write_manifest(today_str: str, mods: list[dict], zip_path: Path) -> Path:
    manifest = RELEASES_DIR / f"launcher-{today_str}-manifest.md"
    lines = [
        f"# CTOA Launcher Day — {today_str}",
        "",
        f"**Released:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Modules:** {len(mods)}",
        f"**ZIP:** `{zip_path.name}`",
        "",
        "## Modules",
        "",
        "| Task ID | File | Quality |",
        "|---------|------|---------|",
    ]
    for m in mods:
        fname = Path(m["output_path"]).name if m["output_path"] else "?"
        lines.append(f"| {m['task_id']} | `{fname}` | {m['quality_score'] or 0}% |")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _git_commit_release(manifest_path: Path, tag: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(REPO_DIR), "add", str(manifest_path)], check=True, timeout=30)
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "commit", "-m", f"release: launcher-day {tag}"],
            check=True, timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "tag", tag],
            check=True, timeout=10,
        )
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "push", "origin", "main", "--tags"],
            check=True, timeout=60,
        )
        return True
    except subprocess.SubprocessError as exc:
        log.warning("git commit/push skipped: %s", exc)
        return False


def _gh_release(tag: str, zip_path: Path, manifest_path: Path) -> bool:
    if not shutil.which("gh"):
        log.info("gh CLI not found – skipping GitHub release")
        return False
    try:
        subprocess.run(
            [
                "gh", "release", "create", tag,
                str(zip_path),
                "--title", f"CTOA Launcher Day {tag}",
                "--notes-file", str(manifest_path),
                "--repo", "famatyyk/CTOAi",
            ],
            check=True, timeout=120,
        )
        log.info("GitHub release %s created", tag)
        return True
    except subprocess.SubprocessError as exc:
        log.warning("gh release failed: %s", exc)
        return False


def run_once() -> None:
    today_str = date.today().isoformat()
    should_launch, reason = _criteria_met(today_str)

    if not should_launch:
        log.info("Launcher day not triggered: %s", reason)
        return

    log.info("🚀 LAUNCHER DAY triggered: %s", reason)
    mods = _collect_validated()
    if not mods:
        log.warning("No VALIDATED modules to package – aborting")
        return

    tag = f"launcher-{today_str}"
    zip_path     = _create_zip(today_str, mods)
    manifest_path = _write_manifest(today_str, mods, zip_path)

    # Mark all released modules
    db.execute(
        "UPDATE modules SET status='RELEASED' WHERE status='VALIDATED'",
    )

    # Mark launcher day
    db.execute(
        "UPDATE daily_stats SET launcher_day=TRUE, released_at=now() WHERE dt=%s",
        (today_str,),
    )

    # Git + GitHub
    _git_commit_release(manifest_path, tag)
    _gh_release(tag, zip_path, manifest_path)

    db.log_run("publisher_agent", "ok", f"launcher day {tag}: {len(mods)} modules")
    log.info("Launcher Day complete: %d modules packaged → %s", len(mods), zip_path)


if __name__ == "__main__":
    run_once()
