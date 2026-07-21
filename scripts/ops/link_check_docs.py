#!/usr/bin/env python3
"""Check local links in repository-owned Markdown documentation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

# Runtime evidence and dependency trees are not repository documentation.  Apart
# from making the check slow, scanning those trees reports links owned by third
# parties or links to intentionally ephemeral artifacts.
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".tmp",
        ".venv",
        "__pycache__",
        "build",
        "data",
        "dist",
        "logs",
        "node_modules",
        "outputs",
        "runtime",
        "vendor",
    }
)


def iter_markdown_files(root: Path) -> Iterable[Path]:
    """Yield repository-owned Markdown files in stable order."""
    for path in sorted(root.rglob("*.md")):
        relative_parts = path.relative_to(root).parts[:-1]
        if any(part in EXCLUDED_DIRS for part in relative_parts):
            continue
        yield path


def is_ignored(link: str) -> bool:
    stripped = link.strip()
    if not stripped or stripped.startswith("#"):
        return True
    return bool(urlsplit(stripped).scheme)


def normalize_target(link: str) -> str:
    target = link.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        # Markdown permits an optional title after the destination.
        target = target.split(maxsplit=1)[0]
    return unquote(target.split("#", 1)[0].strip())


def find_broken_links(root: Path, files: Iterable[Path] | None = None) -> list[str]:
    """Return broken local links as stable ``source -> target`` strings."""
    failures: list[str] = []
    markdown_files = files if files is not None else iter_markdown_files(root)

    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8", errors="ignore")
        for raw in MD_LINK_RE.findall(text):
            if is_ignored(raw):
                continue
            target = normalize_target(raw)
            if not target:
                continue
            absolute_target = (markdown_file.parent / target).resolve()
            if not absolute_target.exists():
                relative_source = markdown_file.relative_to(root).as_posix()
                failures.append(f"{relative_source} -> {raw}")

    return failures


def main() -> int:
    failures = find_broken_links(ROOT)

    if failures:
        print("Broken markdown links found:")
        for item in failures:
            print(f" - {item}")
        return 1

    print("Markdown link check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
