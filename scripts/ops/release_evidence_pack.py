"""Build and persist standardized release evidence packs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_filename(value: str) -> str:
    text = str(value or "").strip().lower()
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text) or "unknown"


def build_release_evidence_pack(
    *,
    backlog_id: str,
    backlog_path: Path,
    state_path: Path,
    released_count: int,
    total_tasks: int,
    reason: str,
    mode: str = "wave1",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    completion_rate = (released_count / total_tasks) if total_tasks else 0.0
    pack_notes = list(notes or [])
    if not pack_notes and released_count == total_tasks:
        pack_notes.append("All backlog tasks synchronized to RELEASED.")

    return {
        "schema_version": "ctoa.release_evidence_pack.v1",
        "generated_at": _now_iso(),
        "backlog_id": backlog_id,
        "mode": mode,
        "reason": reason,
        "release": {
            "released_count": released_count,
            "total_tasks": total_tasks,
            "completion_rate": round(completion_rate, 4),
            "status": "complete" if released_count >= total_tasks else "partial",
        },
        "paths": {
            "backlog": str(backlog_path),
            "state": str(state_path),
        },
        "notes": pack_notes,
    }


def write_release_evidence_pack(output_dir: Path, pack: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    backlog_id = _safe_filename(str(pack.get("backlog_id", "unknown")))
    json_path = output_dir / f"{backlog_id}-release-evidence-pack.json"
    md_path = output_dir / f"{backlog_id}-release-evidence-pack.md"

    json_path.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    release = pack.get("release", {}) if isinstance(pack.get("release"), dict) else {}
    release_count = release.get("released_count", 0)
    total_tasks = release.get("total_tasks", 0)
    completion_rate = release.get("completion_rate", 0.0)
    notes = pack.get("notes", []) if isinstance(pack.get("notes"), list) else []

    md_lines = [
        f"# Release Evidence Pack: {pack.get('backlog_id', 'unknown')}",
        "",
        f"- generated_at: {pack.get('generated_at', '')}",
        f"- mode: {pack.get('mode', 'wave1')}",
        f"- reason: {pack.get('reason', '')}",
        f"- release_count: {release_count}/{total_tasks}",
        f"- completion_rate: {completion_rate}",
        f"- backlog_path: {pack.get('paths', {}).get('backlog', '')}",
        f"- state_path: {pack.get('paths', {}).get('state', '')}",
        "",
        "## Notes",
    ]
    if notes:
        md_lines.extend([f"- {note}" for note in notes])
    else:
        md_lines.append("- none")
    md_lines.append("")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return json_path, md_path
