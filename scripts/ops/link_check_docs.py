#!/usr/bin/env python3
"""Simple markdown link checker for local repository links."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

def is_ignored(link: str) -> bool:
    if link.startswith("http://") or link.startswith("https://"):
        return True
    if link.startswith("mailto:"):
        return True
    if link.startswith("#"):
        return True
    return False

def normalize_target(link: str) -> str:
    return link.split("#", 1)[0].strip()

def main() -> int:
    failures: list[str] = []
    files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]

    for md in files:
        text = md.read_text(encoding="utf-8", errors="ignore")
        for raw in MD_LINK_RE.findall(text):
            if is_ignored(raw):
                continue
            target = normalize_target(raw)
            if not target:
                continue
            abs_target = (md.parent / target).resolve()
            if not abs_target.exists():
                rel_md = md.relative_to(ROOT).as_posix()
                failures.append(f"{rel_md} -> {raw}")

    if failures:
        print("Broken markdown links found:")
        for item in failures:
            print(f" - {item}")
        return 1

    print("Markdown link check passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
