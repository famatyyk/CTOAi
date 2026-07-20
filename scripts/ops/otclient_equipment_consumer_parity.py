#!/usr/bin/env python3
"""Validate cross-consumer parity for the six P10 operator artifacts.

The gate is repo-only.  It reads fixed JSON artifacts, their JSON Schemas, and
the Python/Web consumer source contracts.  It never starts or controls an
OTClient process, changes eligibility, accepts evidence, dispatches an action,
or writes live-client files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any
import uuid

from jsonschema import Draft202012Validator

try:
    from . import otclient_conditions_shadow_replay as documents
except ImportError:  # pragma: no cover - direct script execution
    import otclient_conditions_shadow_replay as documents


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
DEFAULT_OUTPUT = DEFAULT_DEV_DIR / "equipment_consumer_parity.json"
DEFAULT_PYTHON_CONSUMER = ROOT / "scripts" / "ops" / "release_evidence_pack.py"
DEFAULT_WEB_CONSUMER = ROOT / "web" / "src" / "lib" / "controlCenterEvidence.ts"
PARITY_SCHEMA_VERSION = "ctoa.equipment-consumer-parity.v1"
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024

FALSE_NO_ACTION_FIELDS = (
    "runtime_actions",
    "dispatch_allowed",
    "executes_plan",
    "execute_once_allowed",
    "promotion_allowed",
    "live_file_writes",
)


@dataclass(frozen=True)
class ArtifactSpec:
    artifact_id: str
    filename: str
    schema_filename: str
    schema_version: str
    ready_status: str
    no_action: dict[str, object]
    eligibility: dict[str, object]


ARTIFACT_SPECS = (
    ArtifactSpec(
        artifact_id="capture_profile_doctor",
        filename="equipment_capture_profile_doctor.json",
        schema_filename="equipment-capture-profile-doctor.schema.json",
        schema_version="ctoa.equipment-capture-profile-doctor.v1",
        ready_status="ready",
        no_action={
            "no_action_contract": True,
            "runtime_actions": False,
            "live_file_writes": False,
        },
        eligibility={"runtime_readiness_claimed": False},
    ),
    ArtifactSpec(
        artifact_id="observation_preview",
        filename="equipment_observation_preview.json",
        schema_filename="equipment-observation-preview.schema.json",
        schema_version="ctoa.equipment-observation-preview.v1",
        ready_status="preview_ready",
        no_action={
            "runtime_actions": False,
            "dispatch_allowed": False,
            "executes_plan": False,
            "execute_once_allowed": False,
            "promotion_allowed": False,
            "intrusive_actions_performed": [],
        },
        eligibility={},
    ),
    ArtifactSpec(
        artifact_id="dependency_preflight",
        filename="equipment_dependency_preflight.json",
        schema_filename="equipment-dependency-preflight.schema.json",
        schema_version="ctoa.equipment-dependency-preflight.v1",
        ready_status="passed",
        no_action={
            **{name: False for name in FALSE_NO_ACTION_FIELDS},
            "repo_report_write_only": True,
            "intrusive_actions_performed": [],
        },
        eligibility={
            "eligibility_changed": False,
            "eligibility_state": "unchanged",
            "operational_readiness_claimed": False,
        },
    ),
    ArtifactSpec(
        artifact_id="candidate_catalog",
        filename="equipment_candidate_catalog.json",
        schema_filename="equipment-candidate-catalog.schema.json",
        schema_version="ctoa.equipment-candidate-catalog.v1",
        ready_status="catalog_ready",
        no_action={
            "runtime_actions": False,
            "dispatch_allowed": False,
            "executes_plan": False,
            "execute_once_allowed": False,
            "promotion_allowed": False,
            "intrusive_actions_performed": [],
            "selection_policy": "none",
            "recommendation": None,
        },
        eligibility={},
    ),
    ArtifactSpec(
        artifact_id="capture_profile_change_plan",
        filename="equipment_capture_profile_change_plan.json",
        schema_filename="equipment-capture-profile-change-plan.schema.json",
        schema_version="ctoa.equipment-capture-profile-change-plan.v1",
        ready_status="plan_generated",
        no_action={
            **{name: False for name in FALSE_NO_ACTION_FIELDS},
            "repo_report_write_only": True,
            "profile_write_performed": False,
            "intrusive_actions_performed": [],
        },
        eligibility={
            "eligibility_changed": False,
            "acceptance_granted": False,
            "runtime_readiness_claimed": False,
        },
    ),
    ArtifactSpec(
        artifact_id="operator_readiness",
        filename="equipment_operator_readiness.json",
        schema_filename="equipment-operator-readiness.schema.json",
        schema_version="ctoa.equipment-operator-readiness.v1",
        ready_status="operator_inputs_ready",
        no_action={
            **{name: False for name in FALSE_NO_ACTION_FIELDS},
            "repo_report_write_only": True,
            "intrusive_actions_performed": [],
        },
        eligibility={
            "eligibility_changed": False,
            "eligibility_state": "unchanged",
            "operational_readiness_claimed": False,
        },
    ),
)

SPEC_BY_ID = {spec.artifact_id: spec for spec in ARTIFACT_SPECS}

PYTHON_ARTIFACT_KEYS = tuple(f"equipment_{spec.artifact_id}" for spec in ARTIFACT_SPECS)
WEB_ARTIFACT_KEYS = (
    "equipmentCaptureProfileDoctor",
    "equipmentObservationPreview",
    "equipmentDependencyPreflight",
    "equipmentCandidateCatalog",
    "equipmentCaptureProfileChangePlan",
    "equipmentOperatorReadiness",
)
PYTHON_PROJECTION_FIELDS = (
    "status",
    "reported_status",
    "blockers",
    "sha256",
    "contract_valid",
    "fresh",
    "ready",
    "age_ms",
    "runtime_actions",
    "dispatch_allowed",
    "execute_once_allowed",
    "executes_plan",
    "promotion_allowed",
    "live_file_writes",
    "intrusive_actions_performed",
    "eligibility_changed",
    "eligibility_state",
    "operational_readiness_claimed",
    "operator_inputs_ready",
)
WEB_PROJECTION_FIELDS = (
    "status",
    "blockers",
    "sha256",
    "contractValid",
    "fresh",
    "ready",
    "ageMs",
    "runtimeActions",
    "dispatchAllowed",
    "executeOnceAllowed",
    "executesPlan",
    "promotionAllowed",
    "liveFileWrites",
    "intrusiveActionsPerformed",
    "eligibilityChanged",
    "eligibilityState",
    "operationalReadinessClaimed",
    "operatorInputsReady",
)


class DuplicateKeyError(ValueError):
    """Raised when a JSON object repeats a key."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _read_json(path: Path) -> tuple[str, dict[str, Any] | None]:
    if path.is_symlink():
        return "symlink_rejected", None
    if not path.is_file():
        return "missing", None
    try:
        if path.stat().st_size > MAX_ARTIFACT_BYTES:
            return "oversize", None
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except DuplicateKeyError:
        return "duplicate_keys", None
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return "malformed", None
    if not isinstance(payload, dict):
        return "not_object", None
    return "loaded", payload


def _schema_errors(schema_path: Path, payload: dict[str, Any]) -> list[str]:
    status, schema = _read_json(schema_path)
    if status != "loaded" or schema is None:
        return [f"schema_{status}"]
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(payload),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    except Exception as exc:  # pragma: no cover - invalid schema dependency path
        return [f"schema_validator_error:{type(exc).__name__}"]
    rendered: list[str] = []
    for error in errors[:20]:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{location}:{error.validator}")
    if len(errors) > 20:
        rendered.append(f"+{len(errors) - 20}_more")
    return rendered


def _field_divergences(
    payload: dict[str, Any], expected: dict[str, object], prefix: str
) -> list[str]:
    return [
        f"{prefix}.{name}"
        for name, value in expected.items()
        if payload.get(name) != value
    ]


def _lookup(payload: dict[str, Any], *path: str) -> Any:
    value: Any = payload
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _record_binding(
    divergences: dict[str, list[str]],
    payloads: dict[str, dict[str, Any]],
    hashes: dict[str, str],
    *,
    consumer: str,
    path: tuple[str, ...],
    source: str,
    label: str,
) -> None:
    payload = payloads.get(consumer)
    expected = hashes.get(source)
    if payload is None or expected is None or _lookup(payload, *path) != expected:
        divergences.setdefault(consumer, []).append(f"hash:{label}")


def _artifact_chain_divergences(
    payloads: dict[str, dict[str, Any]], hashes: dict[str, str]
) -> dict[str, list[str]]:
    divergences: dict[str, list[str]] = {}

    for consumer, path, source, label in (
        (
            "dependency_preflight",
            ("input_sha256", "capture_doctor"),
            "capture_profile_doctor",
            "dependency.capture_doctor",
        ),
        (
            "dependency_preflight",
            ("input_sha256", "observation_preview"),
            "observation_preview",
            "dependency.observation_preview",
        ),
        (
            "candidate_catalog",
            ("preview_sha256",),
            "observation_preview",
            "catalog.observation_preview",
        ),
        (
            "capture_profile_change_plan",
            ("input_sha256", "capture_doctor"),
            "capture_profile_doctor",
            "change_plan.capture_doctor",
        ),
        (
            "capture_profile_change_plan",
            ("input_sha256", "observation_preview"),
            "observation_preview",
            "change_plan.observation_preview",
        ),
        (
            "operator_readiness",
            ("input_sha256", "capture_doctor"),
            "capture_profile_doctor",
            "readiness.capture_doctor",
        ),
        (
            "operator_readiness",
            ("input_sha256", "observation_preview"),
            "observation_preview",
            "readiness.observation_preview",
        ),
        (
            "operator_readiness",
            ("input_sha256", "dependency_preflight"),
            "dependency_preflight",
            "readiness.dependency_preflight",
        ),
        (
            "operator_readiness",
            ("input_sha256", "candidate_catalog"),
            "candidate_catalog",
            "readiness.candidate_catalog",
        ),
        (
            "operator_readiness",
            ("input_sha256", "change_plan"),
            "capture_profile_change_plan",
            "readiness.change_plan",
        ),
    ):
        _record_binding(
            divergences,
            payloads,
            hashes,
            consumer=consumer,
            path=path,
            source=source,
            label=label,
        )

    preview = payloads.get("observation_preview")
    catalog = payloads.get("candidate_catalog")
    if preview is not None and catalog is not None:
        if catalog.get("preview_status") != preview.get("status"):
            divergences.setdefault("candidate_catalog", []).append(
                "status:observation_preview"
            )
        if catalog.get("preview_blockers") != preview.get("blockers"):
            divergences.setdefault("candidate_catalog", []).append(
                "blockers:observation_preview"
            )

    dependency = payloads.get("dependency_preflight")
    if dependency is not None:
        dependency_inputs = dependency.get("inputs")
        upstream = dependency.get("upstream_blockers")
        for source_id, key in (
            ("capture_profile_doctor", "capture_doctor"),
            ("observation_preview", "observation_preview"),
        ):
            source_payload = payloads.get(source_id)
            summary = (
                dependency_inputs.get(key)
                if isinstance(dependency_inputs, dict)
                else None
            )
            if source_payload is None or not isinstance(summary, dict):
                divergences.setdefault("dependency_preflight", []).append(
                    f"summary:{key}"
                )
                continue
            expected_ready = (
                source_payload.get("status") == SPEC_BY_ID[source_id].ready_status
            )
            if summary.get("ready") is not expected_ready:
                divergences.setdefault("dependency_preflight", []).append(
                    f"status:{key}"
                )
            if summary.get("schema_version") != source_payload.get("schema_version"):
                divergences.setdefault("dependency_preflight", []).append(
                    f"schema:{key}"
                )
            source_blockers = source_payload.get("blockers")
            copied_blockers = upstream.get(key) if isinstance(upstream, dict) else None
            if copied_blockers != source_blockers:
                divergences.setdefault("dependency_preflight", []).append(
                    f"blockers:{key}"
                )

    readiness = payloads.get("operator_readiness")
    if readiness is not None:
        summaries = readiness.get("inputs")
        for source_id, key in (
            ("capture_profile_doctor", "capture_doctor"),
            ("observation_preview", "observation_preview"),
            ("dependency_preflight", "dependency_preflight"),
            ("candidate_catalog", "candidate_catalog"),
            ("capture_profile_change_plan", "change_plan"),
        ):
            source_payload = payloads.get(source_id)
            summary = summaries.get(key) if isinstance(summaries, dict) else None
            if source_payload is None or not isinstance(summary, dict):
                divergences.setdefault("operator_readiness", []).append(
                    f"summary:{key}"
                )
                continue
            expected_ready = (
                source_payload.get("status") == SPEC_BY_ID[source_id].ready_status
            )
            if summary.get("ready") is not expected_ready:
                divergences.setdefault("operator_readiness", []).append(f"status:{key}")
            if summary.get("schema_version") != source_payload.get("schema_version"):
                divergences.setdefault("operator_readiness", []).append(f"schema:{key}")
            if summary.get("upstream_blockers") != source_payload.get("blockers"):
                divergences.setdefault("operator_readiness", []).append(
                    f"blockers:{key}"
                )

    return {name: sorted(set(items)) for name, items in divergences.items() if items}


def _consumer_source_check(
    path: Path, *, artifact_tokens: tuple[str, ...], projection_fields: tuple[str, ...]
) -> dict[str, Any]:
    try:
        source = path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeError):
        source = ""
    missing_artifacts = [token for token in artifact_tokens if token not in source]
    missing_fields = [token for token in projection_fields if token not in source]
    marker_present = PARITY_SCHEMA_VERSION in source
    return {
        "path": str(path),
        "marker_present": marker_present,
        "artifact_tokens_present": len(artifact_tokens) - len(missing_artifacts),
        "artifact_tokens_expected": len(artifact_tokens),
        "missing_artifact_tokens": missing_artifacts,
        "projection_fields_present": len(projection_fields) - len(missing_fields),
        "projection_fields_expected": len(projection_fields),
        "missing_projection_fields": missing_fields,
        "contract_valid": bool(
            source and marker_present and not missing_artifacts and not missing_fields
        ),
    }


def build_report(
    dev_dir: Path = DEFAULT_DEV_DIR,
    *,
    python_consumer: Path = DEFAULT_PYTHON_CONSUMER,
    web_consumer: Path = DEFAULT_WEB_CONSUMER,
) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    blockers: list[str] = []

    for spec in ARTIFACT_SPECS:
        path = dev_dir / spec.filename
        schema_path = ROOT / "schemas" / spec.schema_filename
        load_status, payload = _read_json(path)
        divergences: list[str] = []
        schema_errors: list[str] = []
        canonical_sha256: str | None = None
        status_value: str | None = None
        source_blockers: list[str] = []
        status_blocker_parity = False
        no_action_valid = False
        eligibility_valid = False

        if payload is None:
            divergences.append(f"load:{load_status}")
        else:
            payloads[spec.artifact_id] = payload
            canonical_sha256 = documents.canonical_sha256(payload)
            hashes[spec.artifact_id] = canonical_sha256
            schema_errors = _schema_errors(schema_path, payload)
            if payload.get("schema_version") != spec.schema_version:
                divergences.append("schema_version")
            status_value = (
                payload.get("status")
                if isinstance(payload.get("status"), str)
                else None
            )
            raw_blockers = payload.get("blockers")
            if isinstance(raw_blockers, list) and all(
                isinstance(item, str) for item in raw_blockers
            ):
                source_blockers = list(raw_blockers)
            else:
                divergences.append("blockers_shape")
            ready = status_value == spec.ready_status
            status_blocker_parity = ready == (len(source_blockers) == 0)
            if not status_blocker_parity:
                divergences.append("status_blockers")
            no_action_fields = _field_divergences(payload, spec.no_action, "no_action")
            eligibility_fields = _field_divergences(
                payload, spec.eligibility, "eligibility"
            )
            divergences.extend(no_action_fields)
            divergences.extend(eligibility_fields)
            no_action_valid = not no_action_fields
            eligibility_valid = not eligibility_fields
            if schema_errors:
                divergences.append("schema_contract")

        artifacts[spec.artifact_id] = {
            "filename": spec.filename,
            "path": str(path),
            "schema_path": str(schema_path),
            "load_status": load_status,
            "schema_version": payload.get("schema_version") if payload else None,
            "expected_schema_version": spec.schema_version,
            "status": status_value,
            "ready_status": spec.ready_status,
            "blockers": source_blockers,
            "sha256": canonical_sha256,
            "schema_valid": not schema_errors and payload is not None,
            "schema_errors": schema_errors,
            "status_blocker_parity": status_blocker_parity,
            "no_action_valid": no_action_valid,
            "eligibility_valid": eligibility_valid,
            "hash_bindings_valid": True,
            "divergences": sorted(set(divergences)),
        }

    chain_divergences = _artifact_chain_divergences(payloads, hashes)
    for artifact_id, items in chain_divergences.items():
        row = artifacts[artifact_id]
        row["hash_bindings_valid"] = not any(item.startswith("hash:") for item in items)
        row["divergences"] = sorted(set([*row["divergences"], *items]))

    python_check = _consumer_source_check(
        python_consumer,
        artifact_tokens=PYTHON_ARTIFACT_KEYS,
        projection_fields=PYTHON_PROJECTION_FIELDS,
    )
    web_check = _consumer_source_check(
        web_consumer,
        artifact_tokens=WEB_ARTIFACT_KEYS,
        projection_fields=WEB_PROJECTION_FIELDS,
    )

    for artifact_id, row in artifacts.items():
        if row["divergences"]:
            blockers.append(f"artifact_divergence:{artifact_id}")
    if not python_check["contract_valid"]:
        blockers.append("python_consumer_contract_divergence")
    if not web_check["contract_valid"]:
        blockers.append("web_consumer_contract_divergence")

    status_parity = all(row["status_blocker_parity"] for row in artifacts.values())
    blockers_parity = not any(
        item.startswith("blockers:")
        for items in chain_divergences.values()
        for item in items
    )
    hash_parity = not any(
        item.startswith("hash:")
        for items in chain_divergences.values()
        for item in items
    )
    no_action_parity = all(row["no_action_valid"] for row in artifacts.values())
    eligibility_parity = all(row["eligibility_valid"] for row in artifacts.values())
    schemas_valid = all(row["schema_valid"] for row in artifacts.values())
    consumer_contracts_valid = (
        python_check["contract_valid"] and web_check["contract_valid"]
    )

    return {
        "schema_version": PARITY_SCHEMA_VERSION,
        "status": "passed" if not blockers else "blocked",
        "artifact_count": len(ARTIFACT_SPECS),
        "artifacts": artifacts,
        "consumer_contracts": {"python": python_check, "web": web_check},
        "checks": {
            "schemas_valid": schemas_valid,
            "status_parity": status_parity,
            "blockers_parity": blockers_parity,
            "hash_parity": hash_parity,
            "no_action_parity": no_action_parity,
            "eligibility_parity": eligibility_parity,
            "consumer_contracts_valid": consumer_contracts_valid,
        },
        "blockers": blockers,
        "eligibility_changed": False,
        "eligibility_state": "unchanged",
        "operational_readiness_claimed": False,
        "runtime_actions": False,
        "dispatch_allowed": False,
        "executes_plan": False,
        "execute_once_allowed": False,
        "promotion_allowed": False,
        "live_file_writes": False,
        "intrusive_actions_performed": [],
        "live_safety": (
            "EquipmentConsumerParity reads fixed repo artifacts, schemas, and consumer source contracts only; "
            "it does not launch or control OTClient, mutate eligibility, accept evidence, dispatch actions, "
            "or write live-client files."
        ),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev-dir", type=Path, default=DEFAULT_DEV_DIR)
    parser.add_argument("--python-consumer", type=Path, default=DEFAULT_PYTHON_CONSUMER)
    parser.add_argument("--web-consumer", type=Path, default=DEFAULT_WEB_CONSUMER)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--allow-blocked", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dev_dir = args.dev_dir.resolve()
    output = args.output.resolve() if args.output else dev_dir / DEFAULT_OUTPUT.name
    report = build_report(
        dev_dir,
        python_consumer=args.python_consumer.resolve(),
        web_consumer=args.web_consumer.resolve(),
    )
    if not args.no_write:
        write_json_atomic(output, report)
        print(f"P10 consumer parity report: {output}")
    print(f"P10 consumer parity: {report['status']}")
    if report["blockers"]:
        print("P10 consumer parity blockers: " + ", ".join(report["blockers"]))
    return 0 if report["status"] == "passed" or args.allow_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
