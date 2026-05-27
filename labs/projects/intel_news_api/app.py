from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI

BASE_DIR = Path(__file__).resolve().parent
WATCHER_RUNTIME_DIR = BASE_DIR.parent / "intel_news_watcher" / "runtime"
STATE_FILE = WATCHER_RUNTIME_DIR / "state.json"
DIFF_FILE = WATCHER_RUNTIME_DIR / "latest_diff.json"

app = FastAPI(title="CTOA Intel News API", version="0.1.0")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if path.exists():
        stat = path.stat()
        info["bytes"] = stat.st_size
        info["modified_at"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return info


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, str(exc)

    if not isinstance(raw, dict):
        return None, "payload is not a JSON object"

    return raw, None


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _load_state() -> dict[str, Any]:
    payload, error = _load_json(STATE_FILE)
    return {
        "available": payload is not None,
        "error": error,
        "file": _file_info(STATE_FILE),
        "data": payload or {},
    }


def _load_diff() -> dict[str, Any]:
    payload, error = _load_json(DIFF_FILE)
    return {
        "available": payload is not None,
        "error": error,
        "file": _file_info(DIFF_FILE),
        "data": payload or {},
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "ctoa-intel-news-api",
        "task_id": "LAB-003",
        "generated_at": _utc_now_iso(),
        "endpoints": [
            "/health",
            "/api/intel/status",
            "/api/intel/state",
            "/api/intel/diff",
        ],
    }


@app.get("/health")
def health() -> dict[str, Any]:
    state = _load_state()
    diff = _load_diff()
    return {
        "ok": True,
        "generated_at": _utc_now_iso(),
        "runtime_dir": str(WATCHER_RUNTIME_DIR),
        "state": {
            "available": state["available"],
            "error": state["error"],
            "file": state["file"],
        },
        "diff": {
            "available": diff["available"],
            "error": diff["error"],
            "file": diff["file"],
        },
    }


@app.get("/api/intel/state")
def api_state() -> dict[str, Any]:
    state = _load_state()
    return {
        "task_id": "LAB-003",
        "generated_at": _utc_now_iso(),
        **state,
    }


@app.get("/api/intel/diff")
def api_diff() -> dict[str, Any]:
    diff = _load_diff()
    return {
        "task_id": "LAB-003",
        "generated_at": _utc_now_iso(),
        **diff,
    }


@app.get("/status")
@app.get("/api/intel/status")
def api_status() -> dict[str, Any]:
    state = _load_state()
    diff = _load_diff()

    state_data = state["data"]
    diff_data = diff["data"]

    state_items = state_data.get("items", [])
    state_count = len(state_items) if isinstance(state_items, list) else 0

    return {
        "task_id": "LAB-003",
        "generated_at": _utc_now_iso(),
        "watcher": {
            "state_available": state["available"],
            "diff_available": diff["available"],
            "source_url": diff_data.get("source_url") or state_data.get("source_url"),
            "requested_url": diff_data.get("requested_url") or state_data.get("requested_url"),
            "current_count": _as_int(diff_data.get("current_count"), state_count),
            "new_count": _as_int(diff_data.get("new_count"), 0),
            "removed_count": _as_int(diff_data.get("removed_count"), 0),
            "digest_changed": _as_bool(diff_data.get("digest_changed"), False),
            "last_updated": diff_data.get("generated_at") or state_data.get("updated_at"),
        },
        "state": {
            "error": state["error"],
            "file": state["file"],
        },
        "diff": {
            "error": diff["error"],
            "file": diff["file"],
        },
    }
