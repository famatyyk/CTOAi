#!/usr/bin/env python3
"""Evaluate real passive P11 evidence without casting or granting acceptance."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from . import otclient_conditions_shadow_acceptance as p9_acceptance
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_capture_profile_apply as local_reader
    from . import otclient_equipment_observation_preview as writer
    from . import otclient_equipment_shadow_acceptance as p10_acceptance
    from . import otclient_equipment_shadow_replay as p10_replay
    from . import otclient_heal_friend_observation as observation
    from . import otclient_heal_friend_profile_change_plan as profile_plan
    from . import otclient_heal_friend_shadow_replay as replay
else:  # pragma: no cover
    import otclient_conditions_shadow_acceptance as p9_acceptance
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_capture_profile_apply as local_reader
    import otclient_equipment_observation_preview as writer
    import otclient_equipment_shadow_acceptance as p10_acceptance
    import otclient_equipment_shadow_replay as p10_replay
    import otclient_heal_friend_observation as observation
    import otclient_heal_friend_profile_change_plan as profile_plan
    import otclient_heal_friend_shadow_replay as replay


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = profile_plan.DEV_DIR
OUTPUT = DEV_DIR / "heal_friend_shadow_replay.json"
MAX_BYTES = 512 * 1024


def observation_document(producer: documents.InputDocument) -> documents.InputDocument:
    payload = producer.payload
    if not (
        producer.status == "loaded"
        and isinstance(payload, dict)
        and payload.get("schema_version") == "ctoa.heal-friend-observation-producer.v1"
        and payload.get("status") == "observation_ready"
        and payload.get("blockers") == []
        and isinstance(payload.get("observation"), dict)
        and payload.get("observation_sha256")
        == documents.canonical_sha256(payload["observation"])
        and all(payload.get(field) is False for field in replay.FALSE_FLAGS)
        and payload.get("intrusive_actions_performed") == []
    ):
        return documents.InputDocument(None, "malformed", documents.ZERO_SHA256)
    return documents.document_from_payload(payload["observation"])


def build_report(docs: replay.FixtureDocuments, evaluated_at: int) -> dict[str, Any]:
    trace = replay.evaluate_shadow(docs, evaluated_at, source="operational")
    ready = trace["status"] == "shadow_plan_ready" and trace["blockers"] == []
    return {
        "schema_version": replay.REPORT_SCHEMA,
        "generated_at_unix_ms": evaluated_at,
        "mode": replay.MODE,
        "source": "operational",
        "status": "passed" if ready else "blocked",
        "fixture_only": False,
        "operational_acceptance_status": (
            "shadow_plan_ready_for_operator_review"
            if ready
            else "operational_acceptance_blocked"
        ),
        "operational_producer_present": True,
        "acceptance_receipt_written": False,
        "operational_readiness_claimed": False,
        "runtime_readiness_claimed": False,
        "operational_trace": trace,
        **{field: False for field in replay.FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def canonical_documents() -> replay.FixtureDocuments:
    producer = documents.read_document(observation.OUTPUT, MAX_BYTES)
    return replay.FixtureDocuments(
        profile=local_reader._strict_local_document(observation.PROFILE),  # noqa: SLF001
        observation=observation_document(producer),
        p9_report=documents.read_document(documents.DEFAULT_OUTPUT, MAX_BYTES),
        p9_receipt=documents.read_document(p9_acceptance.DEFAULT_OUTPUT, MAX_BYTES),
        p10_report=documents.read_document(p10_replay.DEFAULT_OUTPUT, MAX_BYTES),
        p10_receipt=documents.read_document(p10_acceptance.DEFAULT_OUTPUT, MAX_BYTES),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(canonical_documents(), int(time.time() * 1000))
    writer._write_atomic(OUTPUT, OUTPUT, report)  # noqa: SLF001
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" or args.allow_blocked else 1


if __name__ == "__main__":
    sys.exit(main())
