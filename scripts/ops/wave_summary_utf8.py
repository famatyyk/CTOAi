"""Generate compact UTF-8 Wave summary artifacts for sprint evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data if isinstance(data, dict) else {}


def _state_release_counts(state: dict[str, Any], backlog: dict[str, Any], expected_backlog_id: str) -> tuple[int, int, str]:
    state_backlog_id = str(state.get("backlog_id", "unknown"))
    total = len([task for task in (backlog.get("tasks") or []) if isinstance(task, dict)])
    released = sum(
        1
        for task in (state.get("tasks") or [])
        if isinstance(task, dict) and str(task.get("status", "")) == "RELEASED"
    )

    if state_backlog_id != expected_backlog_id:
        return released, total, f"mismatch:{state_backlog_id}"
    return released, total, "aligned"


def generate_summary(
    sprint_id: str,
    validation_json: Path,
    output: Path,
    repo_hygiene_json: Path,
    state_yaml: Path,
    backlog_yaml: Path,
) -> Path:
    validation = _load_json(validation_json)
    hygiene = _load_json(repo_hygiene_json)
    state = _load_yaml(state_yaml)
    backlog = _load_yaml(backlog_yaml)

    val_status = str(validation.get("status", "UNKNOWN"))
    val_summary = str(validation.get("summary", "n/a"))
    hygiene_status = str(hygiene.get("status", "UNKNOWN"))

    released, total, state_alignment = _state_release_counts(
        state=state,
        backlog=backlog,
        expected_backlog_id=f"sprint-{sprint_id}",
    )

    lines = [
        f"sprint: {sprint_id}",
        f"generated_at: {_now_iso()}",
        f"validation_status: {val_status}",
        f"validation_summary: {val_summary}",
        f"repo_hygiene_status: {hygiene_status}",
        f"runtime_release: {released}/{total}",
        f"runtime_alignment: {state_alignment}",
        f"validation_artifact: {validation_json.as_posix()}",
        f"repo_hygiene_artifact: {repo_hygiene_json.as_posix()}",
        f"state_source: {state_yaml.as_posix()}",
        f"backlog_source: {backlog_yaml.as_posix()}",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate compact UTF-8 Wave summary")
    parser.add_argument("--sprint-id", required=True, help="Sprint numeric id, e.g. 054")
    parser.add_argument("--validation-json", required=True, help="Path to sprint validation artifact")
    parser.add_argument("--output", required=True, help="Output summary text path")
    parser.add_argument(
        "--repo-hygiene-json",
        default="runtime/repo-hygiene/latest.json",
        help="Path to repo hygiene artifact",
    )
    parser.add_argument(
        "--state-yaml",
        default="runtime/task-state.yaml",
        help="Path to runtime task-state yaml",
    )
    parser.add_argument(
        "--backlog-yaml",
        required=True,
        help="Path to sprint backlog yaml",
    )
    args = parser.parse_args()

    output_path = generate_summary(
        sprint_id=args.sprint_id,
        validation_json=Path(args.validation_json),
        output=Path(args.output),
        repo_hygiene_json=Path(args.repo_hygiene_json),
        state_yaml=Path(args.state_yaml),
        backlog_yaml=Path(args.backlog_yaml),
    )

    print(f"[wave_summary_utf8] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
