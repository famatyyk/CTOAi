#!/usr/bin/env python3
"""Explain fixed P10 operator inputs without changing eligibility.

The report consumes only existing repo-local P10 artifacts.  It never invokes
their producers, accepts a receipt, reads an OTClient installation, or performs
an item/runtime/live action.  Missing optional-next-stage artifacts are explicit
fail-closed blockers, not reasons to infer readiness from earlier evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from . import otclient_conditions_shadow_replay as documents
    from . import otclient_equipment_candidate_catalog as candidate_catalog
    from . import otclient_equipment_capture_profile_change_plan as change_plan
    from . import otclient_equipment_dependency_preflight as dependency_preflight
    from . import otclient_equipment_observation_preview as observation_preview
else:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_replay as documents
    import otclient_equipment_candidate_catalog as candidate_catalog
    import otclient_equipment_capture_profile_change_plan as change_plan
    import otclient_equipment_dependency_preflight as dependency_preflight
    import otclient_equipment_observation_preview as observation_preview


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
DEFAULT_DOCTOR = DEV_DIR / "equipment_capture_profile_doctor.json"
DEFAULT_PREVIEW = DEV_DIR / "equipment_observation_preview.json"
DEFAULT_DEPENDENCY_PREFLIGHT = DEV_DIR / "equipment_dependency_preflight.json"
DEFAULT_CANDIDATE_CATALOG = DEV_DIR / "equipment_candidate_catalog.json"
DEFAULT_CHANGE_PLAN = DEV_DIR / "equipment_capture_profile_change_plan.json"
DEFAULT_OUTPUT = DEV_DIR / "equipment_operator_readiness.json"

SCHEMA = "ctoa.equipment-operator-readiness.v1"
MODE = "repo_only_operator_explain"
CHANGE_PLAN_SCHEMA = change_plan.SCHEMA
MAX_INPUT_BYTES = 512 * 1024
MAX_FRESH_AGE_MS = observation_preview.MAX_AGE_MS
FALSE_FLAGS = dependency_preflight.FALSE_FLAGS

SOURCES = (
    "capture_doctor",
    "observation_preview",
    "dependency_preflight",
    "candidate_catalog",
    "change_plan",
)
CATEGORIES = ("missing", "invalid", "stale", "upstream")
BLOCKER_ORDER = tuple(
    f"{source}_{category}" for source in SOURCES for category in CATEGORIES
)
BLOCKER_RANK = {name: index for index, name in enumerate(BLOCKER_ORDER)}

EXPECTED_SCHEMAS = {
    "capture_doctor": "ctoa.equipment-capture-profile-doctor.v1",
    "observation_preview": observation_preview.SCHEMA,
    "dependency_preflight": dependency_preflight.SCHEMA,
    "candidate_catalog": candidate_catalog.SCHEMA,
    "change_plan": CHANGE_PLAN_SCHEMA,
}

PATHS = {
    "capture_doctor": DEFAULT_DOCTOR,
    "observation_preview": DEFAULT_PREVIEW,
    "dependency_preflight": DEFAULT_DEPENDENCY_PREFLIGHT,
    "candidate_catalog": DEFAULT_CANDIDATE_CATALOG,
    "change_plan": DEFAULT_CHANGE_PLAN,
}

COMMANDS = {
    "capture_doctor": ".\\ctoa.ps1 otp10doctor",
    "observation_preview": ".\\ctoa.ps1 otp10preview",
    "dependency_preflight": ".\\ctoa.ps1 otp10preflight",
    "candidate_catalog": ".\\ctoa.ps1 otp10catalog",
    "change_plan": ".\\ctoa.ps1 otp10plan",
}

DEPENDENCY_KEYS = {
    "schema_version",
    "mode",
    "evaluated_at_unix_ms",
    "status",
    "dependencies_satisfied",
    "inputs",
    "input_sha256",
    "canonical_input_sha256",
    "checks",
    "upstream_blockers",
    "blockers",
    "decision_sha256",
    "eligibility_changed",
    "eligibility_state",
    "operational_readiness_claimed",
    "operator_review_required",
    "repo_report_write_only",
    "live_file_writes",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}

CATALOG_KEYS = {
    "schema_version",
    "generated_at_unix_ms",
    "status",
    "source",
    "preview_sha256",
    "preview_status",
    "preview_blockers",
    "selection_policy",
    "recommendation",
    "ring",
    "groups",
    "summary",
    "blockers",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}

CHANGE_PLAN_KEYS = {
    "schema_version",
    "generated_at_unix_ms",
    "status",
    "mode",
    "sources",
    "input_status",
    "input_sha256",
    "input_binding_sha256",
    "requested_identifiers",
    "operator_confirmation",
    "checks",
    "observation_age_ms",
    "blockers",
    "plan",
    "plan_sha256",
    "explanation",
    "operator_review_required",
    "acceptance_granted",
    "runtime_readiness_claimed",
    "eligibility_changed",
    "profile_write_performed",
    "repo_report_write_only",
    "live_file_writes",
    "interaction_contract",
    *FALSE_FLAGS,
    "intrusive_actions_performed",
}


@dataclass(frozen=True)
class ArtifactState:
    source: str
    document: documents.InputDocument
    valid: bool
    ready: bool
    fresh: bool
    age_ms: int | None
    upstream_blockers: list[str]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _safe(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return bool(
        all(payload.get(key) is False for key in FALSE_FLAGS)
        and payload.get("intrusive_actions_performed") == []
    )


def _ordered(values: Iterable[str]) -> list[str]:
    unique = set(values)
    unknown = unique - set(BLOCKER_RANK)
    if unknown:
        raise ValueError(f"unknown readiness blockers: {sorted(unknown)}")
    return sorted(unique, key=BLOCKER_RANK.__getitem__)


def read_artifacts() -> dict[str, documents.InputDocument]:
    return {
        source: documents.read_document(path, MAX_INPUT_BYTES)
        for source, path in PATHS.items()
    }


def _dependency_contract_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != DEPENDENCY_KEYS:
        return False
    blockers = payload.get("blockers")
    checks = payload.get("checks")
    input_hashes = payload.get("input_sha256")
    if not (
        payload.get("schema_version") == dependency_preflight.SCHEMA
        and payload.get("mode") == dependency_preflight.MODE
        and _is_int(payload.get("evaluated_at_unix_ms"))
        and payload["evaluated_at_unix_ms"] > 0
        and payload.get("status") in {"passed", "blocked"}
        and isinstance(payload.get("dependencies_satisfied"), bool)
        and isinstance(payload.get("inputs"), dict)
        and isinstance(input_hashes, dict)
        and set(input_hashes) == set(dependency_preflight.INPUT_NAMES)
        and all(_is_sha(value) for value in input_hashes.values())
        and _is_sha(payload.get("canonical_input_sha256"))
        and isinstance(checks, dict)
        and checks
        and all(isinstance(value, bool) for value in checks.values())
        and isinstance(payload.get("upstream_blockers"), dict)
        and isinstance(blockers, list)
        and blockers == dependency_preflight._ordered(blockers)  # noqa: SLF001
        and _is_sha(payload.get("decision_sha256"))
        and payload.get("eligibility_changed") is False
        and payload.get("eligibility_state") == "unchanged"
        and payload.get("operational_readiness_claimed") is False
        and payload.get("operator_review_required") is True
        and payload.get("repo_report_write_only") is True
        and payload.get("live_file_writes") is False
        and _safe(payload)
    ):
        return False
    basis = {
        "schema_version": payload["schema_version"],
        "status": payload["status"],
        "dependencies_satisfied": payload["dependencies_satisfied"],
        "checks": checks,
        "blockers": blockers,
        "input_sha256": input_hashes,
        "canonical_input_sha256": payload["canonical_input_sha256"],
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }
    if payload["decision_sha256"] != documents.canonical_sha256(basis):
        return False
    return bool(
        (
            payload["status"] == "passed"
            and payload["dependencies_satisfied"] is True
            and blockers == []
            and all(checks.values())
        )
        or (
            payload["status"] == "blocked"
            and payload["dependencies_satisfied"] is False
            and len(blockers) > 0
        )
    )


def _catalog_contract_valid(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != CATALOG_KEYS:
        return False
    blockers = payload.get("blockers")
    groups = payload.get("groups")
    summary = payload.get("summary")
    return bool(
        payload.get("schema_version") == candidate_catalog.SCHEMA
        and _is_int(payload.get("generated_at_unix_ms"))
        and payload["generated_at_unix_ms"] > 0
        and payload.get("status") in {"catalog_ready", "blocked"}
        and payload.get("source") == "equipment_observation_preview"
        and _is_sha(payload.get("preview_sha256"))
        and payload.get("preview_status") in {"preview_ready", "blocked", None}
        and isinstance(payload.get("preview_blockers"), list)
        and payload.get("selection_policy") == "none"
        and payload.get("recommendation") is None
        and isinstance(groups, list)
        and len(groups) <= 256
        and isinstance(summary, dict)
        and isinstance(blockers, list)
        and blockers == candidate_catalog._ordered(blockers)  # noqa: SLF001
        and _safe(payload)
        and (
            (payload["status"] == "catalog_ready" and blockers == [])
            or (payload["status"] == "blocked" and len(blockers) > 0)
        )
    )


def _change_plan_contract_valid(payload: Any) -> bool:
    """Validate the stable no-action surface while the producer owns details."""

    if not isinstance(payload, dict) or set(payload) != CHANGE_PLAN_KEYS:
        return False
    blockers = payload.get("blockers")
    try:
        blockers_valid = (
            isinstance(blockers, list) and blockers == change_plan._ordered(blockers)  # noqa: SLF001
        )
    except ValueError:
        blockers_valid = False
    plan = payload.get("plan")
    plan_sha = payload.get("plan_sha256")
    return bool(
        payload.get("schema_version") == CHANGE_PLAN_SCHEMA
        and _is_int(payload.get("generated_at_unix_ms"))
        and payload["generated_at_unix_ms"] > 0
        and payload.get("status") in {"plan_generated", "blocked"}
        and payload.get("mode") == change_plan.MODE
        and blockers_valid
        and _is_sha(payload.get("input_binding_sha256"))
        and isinstance(payload.get("checks"), dict)
        and payload.get("operator_review_required") is True
        and payload.get("acceptance_granted") is False
        and payload.get("eligibility_changed") is False
        and payload.get("runtime_readiness_claimed") is False
        and payload.get("profile_write_performed") is False
        and payload.get("repo_report_write_only") is True
        and payload.get("live_file_writes") is False
        and payload.get("interaction_contract") == change_plan.INTERACTION_CONTRACT
        and _safe(payload)
        and (
            (
                payload["status"] == "plan_generated"
                and blockers == []
                and isinstance(plan, dict)
                and plan_sha == documents.canonical_sha256(plan)
            )
            or (
                payload["status"] == "blocked"
                and len(blockers) > 0
                and plan is None
                and plan_sha is None
            )
        )
    )


def _state(
    source: str,
    document: documents.InputDocument,
    *,
    now_ms: int,
    preview_document: documents.InputDocument,
) -> ArtifactState:
    payload = document.payload
    valid = ready = fresh = False
    age_ms: int | None = None
    upstream: list[str] = []
    if document.status != "loaded" or not isinstance(payload, dict):
        return ArtifactState(source, document, False, False, False, None, [])

    if source == "capture_doctor":
        valid = dependency_preflight._doctor_contract_valid(payload)  # noqa: SLF001
        ready = bool(
            valid
            and payload.get("status") == "ready"
            and payload.get("source") == "local_operator_override"
            and payload.get("blockers") == []
        )
        # The doctor schema has no timestamp. Structural validity is current;
        # a valid blocked doctor is an upstream/configuration state, not stale.
        fresh = valid
    elif source == "observation_preview":
        try:
            valid = dependency_preflight._preview_contract_valid(payload)  # noqa: SLF001
        except ValueError:
            valid = False
        freshness = payload.get("freshness")
        observed_at = (
            freshness.get("observed_at_unix_ms")
            if isinstance(freshness, dict)
            else None
        )
        if _is_int(observed_at):
            age_ms = now_ms - observed_at
            fresh = 0 <= age_ms <= MAX_FRESH_AGE_MS
        ready = bool(
            valid
            and fresh
            and payload.get("status") == "preview_ready"
            and payload.get("blockers") == []
        )
    elif source == "dependency_preflight":
        valid = _dependency_contract_valid(payload)
        evaluated_at = payload.get("evaluated_at_unix_ms")
        if _is_int(evaluated_at):
            age_ms = now_ms - evaluated_at
            fresh = 0 <= age_ms <= MAX_FRESH_AGE_MS
        ready = bool(
            valid
            and fresh
            and payload.get("status") == "passed"
            and payload.get("dependencies_satisfied") is True
            and payload.get("blockers") == []
        )
    elif source == "candidate_catalog":
        valid = _catalog_contract_valid(payload)
        generated_at = payload.get("generated_at_unix_ms")
        if _is_int(generated_at):
            age_ms = now_ms - generated_at
            fresh = 0 <= age_ms <= MAX_FRESH_AGE_MS
        ready = bool(
            valid
            and fresh
            and payload.get("status") == "catalog_ready"
            and payload.get("blockers") == []
            and preview_document.status == "loaded"
            and payload.get("preview_sha256") == preview_document.sha256
        )
    else:
        valid = _change_plan_contract_valid(payload)
        generated_at = payload.get("generated_at_unix_ms")
        if _is_int(generated_at):
            age_ms = now_ms - generated_at
            fresh = 0 <= age_ms <= MAX_FRESH_AGE_MS
        ready = bool(
            valid
            and fresh
            and payload.get("status") == "plan_generated"
            and payload.get("blockers") == []
        )
    raw_blockers = payload.get("blockers")
    if isinstance(raw_blockers, list):
        upstream = [str(item) for item in raw_blockers]
    return ArtifactState(source, document, valid, ready, fresh, age_ms, upstream)


def _category(state: ArtifactState) -> str | None:
    if state.document.status == "missing":
        return "missing"
    if state.document.status != "loaded" or not state.valid:
        return "invalid"
    if not state.fresh:
        return "stale"
    if not state.ready:
        return "upstream"
    return None


def _instruction(source: str, category: str) -> str:
    labels = {
        "capture_doctor": "fixed capture-profile doctor",
        "observation_preview": "passive Equipment observation preview",
        "dependency_preflight": "P8/P9 to P10 dependency preflight",
        "candidate_catalog": "passive candidate catalog",
        "change_plan": "data-only capture-profile change plan",
    }
    verbs = {
        "missing": "Generate",
        "invalid": "Regenerate",
        "stale": "Refresh",
        "upstream": "Resolve its listed upstream blockers, then regenerate",
    }
    return (
        f"{verbs[category]} the {labels[source]} through its fixed repo-only command."
    )


def evaluate_readiness(
    artifacts: dict[str, documents.InputDocument], *, generated_at_unix_ms: int
) -> dict[str, Any]:
    if not _is_int(generated_at_unix_ms) or generated_at_unix_ms <= 0:
        raise ValueError("generated_at_unix_ms must be a positive integer")
    if set(artifacts) != set(SOURCES):
        raise ValueError("operator readiness requires exactly the five fixed artifacts")

    states = {
        source: _state(
            source,
            artifacts[source],
            now_ms=generated_at_unix_ms,
            preview_document=artifacts["observation_preview"],
        )
        for source in SOURCES
    }
    blockers: list[str] = []
    details: list[dict[str, Any]] = []
    for source in SOURCES:
        state = states[source]
        category = _category(state)
        if category is None:
            continue
        code = f"{source}_{category}"
        blockers.append(code)
        details.append(
            {
                "code": code,
                "category": category,
                "source": source,
                "upstream_blockers": state.upstream_blockers,
            }
        )
    ordered = _ordered(blockers)
    details.sort(key=lambda item: BLOCKER_RANK[item["code"]])

    # Explain upstream P8/P9 remediation before regenerating the dependency report.
    next_actions: list[dict[str, Any]] = []
    dependency_upstream = states["dependency_preflight"].upstream_blockers
    if any(
        item.startswith(("p8_report_", "p9_report_")) for item in dependency_upstream
    ):
        next_actions.append(
            {
                "order": 0,
                "source": "p9_chain",
                "category": "upstream",
                "command": ".\\ctoa.ps1 otp9",
                "instruction": "Refresh bounded P8 evidence and recompute the no-action P9 report.",
                "changes_eligibility": False,
                "action_scope": "passive_or_repo_only",
            }
        )
    if any(item.startswith("p9_receipt_") for item in dependency_upstream):
        next_actions.append(
            {
                "order": 0,
                "source": "p9_chain",
                "category": "upstream",
                "command": '.\\ctoa.ps1 otp9accept "accept P9 conditions shadow"',
                "instruction": "Review and accept only the current non-fixture P9 report through its separate receipt boundary.",
                "changes_eligibility": False,
                "action_scope": "repo_only_review",
            }
        )
    for source in SOURCES:
        category = _category(states[source])
        if category is None:
            continue
        next_actions.append(
            {
                "order": 0,
                "source": source,
                "category": category,
                "command": COMMANDS[source],
                "instruction": _instruction(source, category),
                "changes_eligibility": False,
                "action_scope": "passive_or_repo_only",
            }
        )
    for index, action in enumerate(next_actions, start=1):
        action["order"] = index

    counts = {
        category: sum(detail["category"] == category for detail in details)
        for category in CATEGORIES
    }
    counts["total"] = len(details)
    ready = not ordered and all(state.ready for state in states.values())
    input_summaries = {
        source: {
            "path": PATHS[source].relative_to(ROOT).as_posix(),
            "load_status": states[source].document.status,
            "schema_version": (
                states[source].document.payload.get("schema_version")
                if isinstance(states[source].document.payload, dict)
                and isinstance(
                    states[source].document.payload.get("schema_version"), str
                )
                else None
            ),
            "expected_schema_version": EXPECTED_SCHEMAS[source],
            "sha256": states[source].document.sha256,
            "valid": states[source].valid,
            "ready": states[source].ready,
            "fresh": states[source].fresh,
            "age_ms": states[source].age_ms,
            "upstream_blockers": states[source].upstream_blockers,
        }
        for source in SOURCES
    }
    input_sha256 = {source: states[source].document.sha256 for source in SOURCES}
    canonical_input_sha256 = documents.canonical_sha256(
        {
            "schema_version": "ctoa.equipment-operator-readiness-input.v1",
            "generated_at_unix_ms": generated_at_unix_ms,
            "input_sha256": input_sha256,
        }
    )
    return {
        "schema_version": SCHEMA,
        "mode": MODE,
        "generated_at_unix_ms": generated_at_unix_ms,
        "status": "operator_inputs_ready" if ready else "blocked",
        "operator_inputs_ready": ready,
        "inputs": input_summaries,
        "input_sha256": input_sha256,
        "canonical_input_sha256": canonical_input_sha256,
        "blocker_counts": counts,
        "blockers": ordered,
        "blocker_details": details,
        "next_actions": next_actions,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        "operator_review_required": True,
        "repo_report_write_only": True,
        "live_file_writes": False,
        **{key: False for key in FALSE_FLAGS},
        "intrusive_actions_performed": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="return success after emitting a structurally blocked report",
    )
    args = parser.parse_args(argv)
    report = evaluate_readiness(
        read_artifacts(), generated_at_unix_ms=int(time.time() * 1000)
    )
    if not args.no_write:
        observation_preview._write_atomic(  # noqa: SLF001
            DEFAULT_OUTPUT, DEFAULT_OUTPUT, report
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"P10 operator readiness: {report['status']}", file=sys.stderr)
    return 0 if report["status"] == "operator_inputs_ready" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
