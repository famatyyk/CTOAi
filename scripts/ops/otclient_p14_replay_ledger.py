#!/usr/bin/env python3
"""Build opaque, one-time P14 guest-evidence reservation records.

The protected GitHub workflow verifies the signed guest evidence first and then
uses the record emitted here to create one closed, repository-local ledger issue.
The immutable title commitment is derived from the repository and guest run ID,
not from a secret, and intentionally never exposes either raw value in GitHub.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts.ops import otclient_p14_guest_evidence as guest_evidence
except ModuleNotFoundError:  # Direct script execution from scripts/ops.
    import otclient_p14_guest_evidence as guest_evidence


LEDGER_SCHEMA_VERSION = "ctoa.p14-guest-run-claim.v1"
LEDGER_DOMAIN = b"CTOAi-P14-guest-run-ledger/v1\x00"
ISSUE_TITLE_PREFIX = "P14 guest evidence consumed v1: "
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"
)
RUN_ID_RE = re.compile(r"^[a-f0-9]{16}$")
POSITIVE_INT_RE = re.compile(r"^[1-9][0-9]{0,19}$")


class ReplayLedgerError(ValueError):
    """Raised when a one-time P14 guest evidence claim is not safe to reserve."""


def _require_repository(value: str) -> str:
    if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
        raise ReplayLedgerError("github_repository_invalid")
    return value.lower()


def _require_run_id(value: str) -> str:
    if not isinstance(value, str) or not RUN_ID_RE.fullmatch(value):
        raise ReplayLedgerError("guest_run_id_invalid")
    return value


def _require_positive_int(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not POSITIVE_INT_RE.fullmatch(value):
        raise ReplayLedgerError(f"{label}_invalid")
    return value


def _hash_parts(label: str, *values: str) -> str:
    digest = hashlib.sha256()
    digest.update(LEDGER_DOMAIN)
    digest.update(label.encode("ascii"))
    digest.update(b"\x00")
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _load_envelope(path: Path) -> dict[str, Any]:
    """Load a bounded strict envelope and reject malformed shape before a claim."""

    envelope = guest_evidence.load_strict_json_file(path)
    # The cryptographic verification happens in the preceding protected workflow
    # step.  Shape validation here makes the claim's immutable digest unambiguous.
    return guest_evidence.validate_envelope_shape(envelope)


def build_claim(
    *,
    repository: str,
    run_id: str,
    envelope: dict[str, Any],
    workflow_run_id: str,
    workflow_run_attempt: str,
) -> dict[str, str]:
    """Create a stable, secret-minimized ledger claim for one guest run ID."""

    normalized_repository = _require_repository(repository)
    _require_run_id(run_id)
    _require_positive_int(workflow_run_id, label="workflow_run_id")
    _require_positive_int(workflow_run_attempt, label="workflow_run_attempt")
    envelope = guest_evidence.validate_envelope_shape(envelope)

    envelope_sha256 = guest_evidence.raw_sha256(
        guest_evidence.canonical_json_bytes(envelope)
    )
    run_commitment = _hash_parts("guest-run", normalized_repository, run_id)
    issue_title = f"{ISSUE_TITLE_PREFIX}{run_commitment}"
    issue_body = "\n".join(
        (
            "<!-- ctoa-p14-guest-run-ledger:v1 -->",
            "",
            "Automated protected P14 guest-evidence reservation. This record is",
            "durable audit evidence: do not delete, reopen, or repurpose it.",
            "A failed protected run remains consumed; create a fresh isolated guest",
            "run instead of retrying this one.",
            "",
            f"- claim SHA-256: `{run_commitment}`",
            f"- envelope SHA-256: `{envelope_sha256}`",
            f"- guest evidence key ID: `{envelope['key_id']}`",
            f"- workflow run: `{workflow_run_id}.{workflow_run_attempt}`",
        )
    )
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "claim_id": f"p14-guest-run-{run_commitment[:16]}",
        "repository": normalized_repository,
        "run_commitment_sha256": run_commitment,
        "envelope_sha256": envelope_sha256,
        "issue_title": issue_title,
        "issue_body": issue_body,
    }


def _write_json_atomic(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = guest_evidence.canonical_json_bytes(payload) + b"\n"
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def _prepare(args: argparse.Namespace) -> int:
    envelope = _load_envelope(Path(args.envelope))
    claim = build_claim(
        repository=args.repository,
        run_id=args.run_id,
        envelope=envelope,
        workflow_run_id=args.workflow_run_id,
        workflow_run_attempt=args.workflow_run_attempt,
    )
    _write_json_atomic(Path(args.output), claim)
    print(
        json.dumps(
            {
                "schema_version": 1,
                "action": "p14-guest-run-ledger-prepare",
                "status": "prepared",
                "claim_id": claim["claim_id"],
                "run_commitment_sha256": claim["run_commitment_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare", help="Build an opaque GitHub issue reservation record."
    )
    prepare.add_argument("--repository", required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--envelope", required=True)
    prepare.add_argument("--workflow-run-id", required=True)
    prepare.add_argument("--workflow-run-attempt", required=True)
    prepare.add_argument("--output", required=True)
    prepare.set_defaults(handler=_prepare)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        return int(args.handler(args))
    except (ReplayLedgerError, guest_evidence.GuestEvidenceError, OSError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "blocked",
                    "blockers": [str(exc)],
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
