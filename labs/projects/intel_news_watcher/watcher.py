from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


def _detect_repo_root() -> Path:
    for candidate in [BASE_DIR, *BASE_DIR.parents]:
        if (candidate / "labs" / "tasks" / "intel-projects.yaml").exists():
            return candidate
    if len(BASE_DIR.parents) >= 3:
        return BASE_DIR.parents[2]
    return Path.cwd()


REPO_ROOT = _detect_repo_root()

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labs.projects.intel_news_scraper import scraper  # noqa: E402

TASK_ID = "LAB-002"
TASKS_FILE = REPO_ROOT / "labs" / "tasks" / "intel-projects.yaml"
RUNTIME_DIR = BASE_DIR / "runtime"
ARCHIVE_DIR = RUNTIME_DIR / "archive"
STATE_FILE = RUNTIME_DIR / "state.json"
LATEST_DIFF_FILE = RUNTIME_DIR / "latest_diff.json"


def _normalize_url(value: str) -> str:
    return value.strip().lower()


def _coerce_items(raw_items: Any) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        return []

    items: list[dict[str, str]] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        url = str(entry.get("url", "")).strip()
        if not url:
            continue
        items.append({"title": title or url, "url": url})
    return items


def _read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _resolve_target_url() -> str:
    env_url = os.getenv("CTOA_INTEL_NEWS_URL", "").strip()
    if env_url:
        return env_url

    if not TASKS_FILE.exists():
        return scraper.DEFAULT_URL

    in_lab_block = False
    for raw_line in TASKS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("- id:"):
            in_lab_block = stripped.split(":", 1)[1].strip() == TASK_ID
            continue

        if in_lab_block and stripped.startswith("target_url:"):
            value = stripped.split(":", 1)[1].strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if value:
                return value

    return scraper.DEFAULT_URL


def _diff_items(previous_items: list[dict[str, str]], current_items: list[dict[str, str]]) -> dict[str, Any]:
    previous_urls = {_normalize_url(item["url"]) for item in previous_items if item.get("url")}
    current_urls = {_normalize_url(item["url"]) for item in current_items if item.get("url")}

    new_items = [
        item
        for item in current_items
        if item.get("url") and _normalize_url(item["url"]) not in previous_urls
    ]

    removed_items = [
        item
        for item in previous_items
        if item.get("url") and _normalize_url(item["url"]) not in current_urls
    ]

    return {
        "new_count": len(new_items),
        "removed_count": len(removed_items),
        "new_items": new_items,
        "removed_items": removed_items,
    }


def run_once(url: str | None = None, max_items: int = 25, timeout: int = 20) -> dict[str, Any]:
    requested_url = (url or _resolve_target_url()).strip() or scraper.DEFAULT_URL

    previous_state = _read_json(STATE_FILE, default={})
    previous_items = _coerce_items(previous_state.get("items", []))

    snapshot = scraper.run_once(url=requested_url, max_items=max_items, timeout=timeout)
    current_items = _coerce_items(snapshot.get("items", []))

    previous_digest = str(previous_state.get("digest", ""))
    current_digest = str(snapshot.get("digest", ""))
    diff = _diff_items(previous_items, current_items)

    generated_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "generated_at": generated_at,
        "task_id": TASK_ID,
        "requested_url": snapshot.get("requested_url", requested_url),
        "source_url": snapshot.get("source_url", requested_url),
        "previous_count": len(previous_items),
        "current_count": len(current_items),
        "previous_digest": previous_digest,
        "current_digest": current_digest,
        "digest_changed": previous_digest != current_digest,
        **diff,
    }

    _write_json(LATEST_DIFF_FILE, report)

    archive_name = f"diff_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    _write_json(ARCHIVE_DIR / archive_name, report)

    next_state = {
        "updated_at": generated_at,
        "digest": current_digest,
        "items": current_items,
        "requested_url": report["requested_url"],
        "source_url": report["source_url"],
    }
    _write_json(STATE_FILE, next_state)

    print(
        "intel_news_watcher: "
        f"checked={report['current_count']} new={report['new_count']} "
        f"removed={report['removed_count']} source={report['source_url']}"
    )

    for item in report["new_items"]:
        print(f"NEW | {item['title']} | {item['url']}")

    for item in report["removed_items"]:
        print(f"REMOVED | {item['title']} | {item['url']}")

    return report


def run_forever(
    interval_seconds: int = 300,
    url: str | None = None,
    max_items: int = 25,
    timeout: int = 20,
) -> None:
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be >= 1")

    print(
        f"intel_news_watcher: daemon started interval={interval_seconds}s "
        f"task={TASK_ID}"
    )

    while True:
        try:
            run_once(url=url, max_items=max_items, timeout=timeout)
        except Exception as exc:
            print(f"intel_news_watcher: ERROR {exc}")
        time.sleep(interval_seconds)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch Intel news and emit diff entries")
    parser.add_argument("--url", default=None, help="Optional source URL override")
    parser.add_argument("--max-items", type=int, default=25, help="Maximum scraped records")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--interval", type=int, default=300, help="Daemon loop interval in seconds")
    parser.add_argument("--daemon", action="store_true", help="Run continuous watcher loop")
    parser.add_argument("--print-json", action="store_true", help="Print watcher report as JSON")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()

    if args.daemon:
        run_forever(
            interval_seconds=args.interval,
            url=args.url,
            max_items=args.max_items,
            timeout=args.timeout,
        )
        return 0

    report = run_once(url=args.url, max_items=args.max_items, timeout=args.timeout)
    if args.print_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

