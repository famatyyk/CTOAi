#!/usr/bin/env python3
"""Ingest a Tibia.com HTML snapshot into the local Control Center archive."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.tibia_sources import (  # noqa: E402
    HttpTibiaCollector,
    LinkRecordParser,
    SOURCE_DEFINITIONS,
    SnapshotArchive,
    collected_from_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sorted(SOURCE_DEFINITIONS), required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", type=Path, help="Approved local raw HTML snapshot")
    mode.add_argument("--fetch", action="store_true", help="Fetch the allowlisted official source URL")
    parser.add_argument("--url", help="Allowlisted official URL override")
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=ROOT / "runtime" / "tibia_source_archive",
    )
    parser.add_argument("--no-parse", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input:
        collected = collected_from_file(args.source, args.input, url=args.url)
    else:
        collected = HttpTibiaCollector().fetch(args.source, cursor=args.url)
    archive = SnapshotArchive(args.archive_root)
    parser = None if args.no_parse else LinkRecordParser(archive.root)
    snapshot, events = archive.ingest(collected, parser=parser)
    print(
        json.dumps(
            {
                "status": "source_blocked" if snapshot.blocked_reason else "archived",
                "snapshot": asdict(snapshot),
                "events": [asdict(event) for event in events],
                "inventory_path": str(archive.inventory_path),
                "source_index_path": str(archive.index_path),
                "events_path": str(archive.events_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
