from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_URL = "https://tibiantis.online/news"
BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
ARCHIVE_DIR = RUNTIME_DIR / "archive"
LATEST_FILE = RUNTIME_DIR / "latest.json"

FALLBACK_PATHS = (
    "/index.php?subtopic=latestnews",
    "/?subtopic=latestnews",
    "/index.php?subtopic=newsarchive",
)


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._active_href: str | None = None
        self._parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = None
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value.strip()
                break
        self._active_href = href
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._active_href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._active_href is None:
            return
        title = " ".join(part.strip() for part in self._parts if part.strip())
        if title:
            self.anchors.append((title, self._active_href))
        self._active_href = None
        self._parts = []


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _candidate_urls(requested_url: str) -> list[str]:
    candidates = [requested_url]
    parsed = urlparse(requested_url)
    if not parsed.scheme or not parsed.netloc:
        return candidates

    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in FALLBACK_PATHS:
        candidate = urljoin(base, path)
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _extract_comment_entries(html: str, source_url: str, max_items: int) -> list[dict[str, str]]:
    pattern = re.compile(
        r"<small>\s*(?P<meta>[^<]*\d{4}[^<]*)\s*<a\s+href=['\"](?P<href>[^'\"]*page=viewtopic[^'\"]+)['\"][^>]*>\s*Comment\s*\(\d+\)\s*</a>\s*</small>",
        flags=re.IGNORECASE,
    )

    extracted: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for match in pattern.finditer(html):
        href = match.group("href").strip()
        resolved_url = urljoin(source_url, href)
        key = resolved_url.lower()
        if key in seen_urls:
            continue

        seen_urls.add(key)
        meta = _normalize_whitespace(unescape(match.group("meta")))
        extracted.append(
            {
                "title": f"News update ({meta})",
                "url": resolved_url,
            }
        )

        if len(extracted) >= max_items:
            break

    return extracted


def parse_news_items(html: str, source_url: str, max_items: int = 25) -> list[dict[str, str]]:
    parser = _AnchorParser()
    parser.feed(html)

    results: list[NewsItem] = []
    seen: set[tuple[str, str]] = set()

    ignored_titles = {
        "news",
        "rules",
        "menu link",
        "account lost?",
        "archived news",
        "check full changelog...",
    }

    for title_raw, href_raw in parser.anchors:
        title = _normalize_whitespace(unescape(title_raw))
        href = href_raw.strip()

        if len(title) < 12:
            continue
        if title.lower() in ignored_titles:
            continue
        if href.startswith(("javascript:", "mailto:", "#")):
            continue

        resolved_url = urljoin(source_url, href)
        lowered_url = resolved_url.lower()
        lowered_title = title.lower()

        has_news_signal = (
            "news" in lowered_url
            or "latest" in lowered_url
            or "news" in lowered_title
            or "latest" in lowered_title
            or "page=viewtopic" in lowered_url
        )
        if not has_news_signal:
            continue

        dedupe_key = (title.lower(), resolved_url.lower())
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        results.append(NewsItem(title=title, url=resolved_url))

        if len(results) >= max_items:
            break

    parsed_items = [{"title": item.title, "url": item.url} for item in results]

    if len(parsed_items) < max_items:
        fallback_items = _extract_comment_entries(
            html=html,
            source_url=source_url,
            max_items=max_items,
        )
        seen_urls = {item["url"].lower() for item in parsed_items}
        for item in fallback_items:
            key = item["url"].lower()
            if key in seen_urls:
                continue
            parsed_items.append(item)
            seen_urls.add(key)
            if len(parsed_items) >= max_items:
                break

    return parsed_items[:max_items]


def fetch_news_html(url: str, timeout: int = 20) -> tuple[str, str]:
    headers = {
        "User-Agent": "CTOA-IntelNewsScraper/1.0 (+https://github.com/famatyyk/CTOAi)",
        "Accept": "text/html,application/xhtml+xml",
    }

    errors: list[str] = []
    for candidate in _candidate_urls(url):
        try:
            response = requests.get(candidate, headers=headers, timeout=timeout, allow_redirects=True)
        except requests.RequestException as exc:
            errors.append(f"{candidate} => {exc}")
            continue

        if response.status_code >= 400:
            errors.append(f"{candidate} => HTTP {response.status_code}")
            continue

        return response.text, response.url

    joined = "; ".join(errors) if errors else "no candidate URLs"
    raise RuntimeError(f"Failed to fetch news HTML: {joined}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def run_once(url: str = DEFAULT_URL, max_items: int = 25, timeout: int = 20) -> dict[str, Any]:
    html, effective_url = fetch_news_html(url=url, timeout=timeout)
    items = parse_news_items(html=html, source_url=effective_url, max_items=max_items)

    generated_at = datetime.now(timezone.utc).isoformat()
    digest_source = json.dumps(items, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()

    snapshot: dict[str, Any] = {
        "generated_at": generated_at,
        "requested_url": url,
        "source_url": effective_url,
        "count": len(items),
        "digest": digest,
        "items": items,
    }

    _write_json(LATEST_FILE, snapshot)

    archive_name = f"news_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    _write_json(ARCHIVE_DIR / archive_name, snapshot)

    return snapshot


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape latest Intel news links")
    parser.add_argument("--url", default=DEFAULT_URL, help="Source news URL")
    parser.add_argument("--max-items", type=int, default=25, help="Maximum number of records in output")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--print", action="store_true", dest="print_json", help="Print JSON snapshot")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    snapshot = run_once(url=args.url, max_items=args.max_items, timeout=args.timeout)
    if args.print_json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print(
            "intel_news_scraper: captured "
            f"{snapshot['count']} items from {snapshot['source_url']} "
            f"(requested: {snapshot['requested_url']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
