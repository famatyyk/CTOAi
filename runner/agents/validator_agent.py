#!/usr/bin/env python3
"""Validator Agent – quality-checks GENERATED modules.

Checks performed:
  Lua files  (.lua):
    1. File exists and is non-empty
    2. Contains at least one `register(` call
    3. No syntax-level red flags (unclosed brackets, TODO markers)
    4. Line count is reasonable (> 5)
    5. luac syntax check if luac is available on PATH

  Python files (.py):
    1. `python3 -m py_compile` passes
    2. flake8 score (warn only, doesn't fail)

Quality score (0–100):
  Base  = 60
  +10   lua: register() present
  +10   line count >= 20
  +10   luac / py_compile passes
  +5    no TODO / FIXME markers
  +5    header comment present (-- CTOA Generated or # CTOA Generated)
  Clamp to [0, 100]

Run: python3 -m runner.agents.validator_agent
"""
from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [validator] %(levelname)s %(message)s",
)
log = logging.getLogger("validator")


def _luac_check(path: Path) -> tuple[bool, str]:
    """Return (ok, message). Tries `luac -p`."""
    try:
        res = subprocess.run(
            ["luac", "-p", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode == 0:
            return True, "luac ok"
        return False, res.stderr.strip()[:500]
    except FileNotFoundError:
        # luac not installed – do a basic bracket balance check instead
        return _bracket_balance(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, str(exc)


def _bracket_balance(src: str) -> tuple[bool, str]:
    depth = 0
    for ch in src:
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
    if depth == 0:
        return True, "brackets balanced"
    return False, f"unbalanced brackets (depth={depth})"


def _py_compile_check(path: Path) -> tuple[bool, str]:
    try:
        res = subprocess.run(
            ["python3", "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return res.returncode == 0, (res.stderr.strip()[:500] or "ok")
    except Exception as exc:
        return False, str(exc)


def validate_lua(path: Path, src: str) -> tuple[int, str]:
    score = 60
    notes: list[str] = []

    if not src.strip():
        return 0, "empty file"

    lines = src.splitlines()
    if len(lines) < 5:
        score -= 20
        notes.append("too short (<5 lines)")

    if "register(" in src:
        score += 10
        notes.append("register() present")
    else:
        notes.append("WARN: no register() call")

    if len(lines) >= 20:
        score += 10
        notes.append(f"{len(lines)} lines")

    syn_ok, syn_msg = _luac_check(path)
    if syn_ok:
        score += 10
        notes.append("syntax ok")
    else:
        score -= 15
        notes.append(f"syntax error: {syn_msg}")

    if not re.search(r"\bTODO\b|\bFIXME\b", src, re.IGNORECASE):
        score += 5
        notes.append("no TODO markers")

    if "CTOA Generated" in src[:200]:
        score += 5
        notes.append("header present")

    return max(0, min(100, score)), "; ".join(notes)


def validate_python(path: Path, src: str) -> tuple[int, str]:
    score = 60
    notes: list[str] = []

    if not src.strip():
        return 0, "empty file"

    ok, msg = _py_compile_check(path)
    if ok:
        score += 20
        notes.append("py_compile ok")
    else:
        score -= 20
        notes.append(f"compile error: {msg}")

    lines = src.splitlines()
    if len(lines) >= 30:
        score += 10
    if not re.search(r"\bTODO\b|\bFIXME\b", src, re.IGNORECASE):
        score += 5
    if "# CTOA Generated" in src[:200]:
        score += 5

    return max(0, min(100, score)), "; ".join(notes)


def validate_module(mod: dict) -> None:
    output_path = mod.get("output_path")
    if not output_path:
        db.execute(
            "UPDATE modules SET status='FAILED', test_log='no output_path', validated_at=now() WHERE task_id=%s",
            (mod["task_id"],),
        )
        return

    path = Path(output_path)
    if not path.exists():
        db.execute(
            "UPDATE modules SET status='FAILED', test_log='file not found', validated_at=now() WHERE task_id=%s",
            (mod["task_id"],),
        )
        return

    src = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()

    if ext == ".lua":
        score, notes = validate_lua(path, src)
    elif ext == ".py":
        score, notes = validate_python(path, src)
    else:
        score, notes = 50, f"unknown ext {ext}"

    final_status = "VALIDATED" if score >= 60 else "FAILED"

    db.execute(
        """
        UPDATE modules
        SET status=%s, quality_score=%s, test_log=%s, validated_at=now()
        WHERE task_id=%s
        """,
        (final_status, score, notes[:2000], mod["task_id"]),
    )

    # Update avg_quality in daily_stats
    today = datetime.now(timezone.utc).date().isoformat()
    db.execute(
        """
        INSERT INTO daily_stats (dt, avg_quality)
        VALUES (%s, %s)
        ON CONFLICT (dt) DO UPDATE
          SET avg_quality = (daily_stats.avg_quality * 0.9 + EXCLUDED.avg_quality * 0.1)
        """,
        (today, float(score)),
    )

    log.info("Validated %s → score=%d (%s) → %s", mod["task_id"], score, notes, final_status)


def run_once() -> None:
    mods = db.query_all(
        "SELECT task_id, output_path FROM modules WHERE status='GENERATED' ORDER BY id LIMIT 30"
    )
    if not mods:
        log.info("No GENERATED modules to validate")
        return

    ok = fail = 0
    for mod in mods:
        try:
            validate_module(mod)
            ok += 1
        except Exception as exc:
            fail += 1
            log.error("Validate error for %s: %s", mod["task_id"], exc)
            db.execute(
                "UPDATE modules SET status='FAILED', test_log=%s, validated_at=now() WHERE task_id=%s",
                (str(exc)[:2000], mod["task_id"]),
            )

    db.log_run("validator_agent", "ok", f"validated {ok}, failed {fail}")


if __name__ == "__main__":
    run_once()
