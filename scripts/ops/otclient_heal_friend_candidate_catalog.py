#!/usr/bin/env python3
"""Catalog bounded passive P11 party candidates without selecting a target."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_observation_preview as writer
    from .otclient_headless_evidence import load_json_bounded, summarize_capability
else:  # pragma: no cover
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_observation_preview as writer
    from otclient_headless_evidence import load_json_bounded, summarize_capability


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
DEFAULT_BACKGROUND = DEV_DIR / "background_status.json"
DEFAULT_OUTPUT = DEV_DIR / "heal_friend_candidate_catalog.json"
SCHEMA = "ctoa.heal-friend-candidate-catalog.v1"
MAX_BACKGROUND_BYTES = 256 * 1024
MAX_AGE_MS = 10_000
EXPECTED_HELPER_VERSION = "v2.4.1"
FALSE_FLAGS = (
    "dispatch_allowed",
    "runtime_actions",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "casts",
    "talks",
)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def build_catalog(
    background: documents.InputDocument,
    now_unix_ms: int,
    *,
    source: str = "background_status",
) -> dict[str, Any]:
    blockers: list[str] = []
    payload = background.payload
    capability = payload.get("capability") if isinstance(payload, dict) else None
    scan = capability.get("heal_friend_scan") if isinstance(capability, dict) else None
    if background.status != "loaded" or not isinstance(payload, dict):
        blockers.append("background_missing_or_invalid")
    elif payload.get("status") != "ready":
        blockers.append("background_not_ready")
    if not isinstance(capability, dict):
        blockers.append("capability_missing")
    else:
        if capability.get("fresh") is not True:
            blockers.append("capability_not_fresh")
        if capability.get("contract_valid") is not True:
            blockers.append("capability_contract_invalid")
        if capability.get("version_match") is not True:
            blockers.append("helper_version_mismatch")
    candidates: list[dict[str, Any]] = []
    observed_at = None
    age_ms = None
    if (
        not isinstance(scan, dict)
        or scan.get("status") != "valid"
        or scan.get("valid") is not True
    ):
        blockers.append("heal_friend_scan_missing_or_invalid")
    else:
        observed_at = scan.get("observed_at_unix_ms")
        age_ms = now_unix_ms - observed_at if _is_int(observed_at) else None
        if not _is_int(age_ms) or age_ms < 0:
            blockers.append("heal_friend_scan_future_or_invalid")
        elif age_ms > MAX_AGE_MS:
            blockers.append("heal_friend_scan_stale")
        if scan.get("scan_complete") is not True:
            blockers.append("heal_friend_scan_incomplete")
        if scan.get("producer_source") != "otclient_guarded_adapter":
            blockers.append("heal_friend_scan_source_invalid")
        if any(scan.get(field) is not False for field in FALSE_FLAGS):
            blockers.append("unsafe_contract")
        raw_candidates = scan.get("candidates")
        if isinstance(raw_candidates, list):
            candidates = [
                dict(item) for item in raw_candidates if isinstance(item, dict)
            ]
        if not candidates:
            blockers.append("party_candidates_empty")
    return {
        "schema_version": SCHEMA,
        "generated_at_unix_ms": now_unix_ms,
        "status": "catalog_ready" if not blockers else "blocked",
        "source": source,
        "background_sha256": background.sha256,
        "observed_at_unix_ms": observed_at,
        "age_ms": age_ms,
        "max_age_ms": MAX_AGE_MS,
        "selection_policy": "none",
        "recommendation": None,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "blockers": blockers,
        **{field: False for field in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def sandbox_capability_path(local_app_data: str | None = None) -> Path:
    root = (
        local_app_data
        if local_app_data is not None
        else os.environ.get("LOCALAPPDATA", "")
    )
    if not root:
        raise ValueError("LOCALAPPDATA is required for sandbox catalog mode")
    return (
        Path(root)
        / "SolteriaCodexTest"
        / "client"
        / "mods"
        / "ctoa_otclient"
        / "ctoa_client_capabilities.json"
    )


def build_sandbox_catalog(
    capability_path: Path,
    *,
    now_unix_ms: int,
    process_start_unix_ms: int,
) -> dict[str, Any]:
    payload, load_status = load_json_bounded(capability_path)
    capability = summarize_capability(
        payload,
        load_status,
        now_unix_ms,
        process_start_unix_ms=process_start_unix_ms,
        expected_helper_version=EXPECTED_HELPER_VERSION,
    )
    background = documents.document_from_payload(
        {
            "status": "ready" if capability.get("fresh") is True else "blocked",
            "capability": capability,
        }
    )
    report = build_catalog(
        background,
        now_unix_ms,
        source="sandbox_capability",
    )
    report["capability_report"] = str(capability_path)
    report["capability_status"] = capability.get("status")
    report["heartbeat_after_process_start"] = (
        capability.get("heartbeat_after_process_start") is True
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true")
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Read only the fixed SolteriaCodexTest capability heartbeat.",
    )
    parser.add_argument("--process-start-unix-ms", type=int)
    args = parser.parse_args(argv)
    now_unix_ms = int(time.time() * 1000)
    if args.sandbox:
        if not args.process_start_unix_ms or args.process_start_unix_ms <= 0:
            parser.error("--sandbox requires a positive --process-start-unix-ms")
        report = build_sandbox_catalog(
            sandbox_capability_path(),
            now_unix_ms=now_unix_ms,
            process_start_unix_ms=args.process_start_unix_ms,
        )
    else:
        if args.process_start_unix_ms is not None:
            parser.error("--process-start-unix-ms is valid only with --sandbox")
        report = build_catalog(
            documents.read_document(DEFAULT_BACKGROUND, MAX_BACKGROUND_BYTES),
            now_unix_ms,
        )
    if not args.no_write:
        writer._write_atomic(DEFAULT_OUTPUT, DEFAULT_OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "catalog_ready" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
