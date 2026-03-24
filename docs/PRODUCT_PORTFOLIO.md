# CTOA Product Portfolio

This file is the canonical map of what is considered a product in this repository.

## Product 1: CTOA Control Plane

- Purpose: secure operations panel + VPS command/control.
- Primary paths:
  - `mobile_console/`
  - `scripts/ops/ctoa-vps.ps1`
  - `deploy/vps/systemd/`
  - `docs/MOBILE_CONSOLE.md`
- Public API highlights:
  - `POST /api/agents/execution/run` (preferred)
  - `POST /api/agents/mythibia/run` (legacy alias)

## Product 2: CTOA Agent Execution Engine

- Purpose: orchestrate agents, generate outputs, run quality checks.
- Primary paths:
  - `runner/`
  - `agents/`
  - `prompts/`
  - `scoring/`
  - `schemas/`

## Product 3: CTOA Release Governance

- Purpose: sprint evidence, validator gates, release approvals.
- Primary paths:
  - `workflows/`
  - `policies/`
  - `runtime/experiments/`
  - `scripts/ops/sprint*_validate.py`

  ## Packaging Tiers

  Public client distribution uses three tiers:

  - Core: runtime engine, prompts, governance, schemas, bootstrap/update gate
  - Pro: Core plus customer-facing console/control-plane surface
  - Studio: internal-only overlay, private operations, lab/research and raw assets

  Canonical tier definitions:

  - `product/packages/core.manifest.json`
  - `product/packages/pro.manifest.json`
  - `product/packages/studio.manifest.json`

  Client distribution reference:

  - `docs/CLIENT_DISTRIBUTION_MODEL.md`

## Legacy/Lab/Research Tracks (not product-facing)

These tracks are valid for internal R&D but should not dominate the public product narrative:

- reverse-engineering and unpacking helpers
- temporary decrypt/decompile outputs
- ad-hoc local experiment artifacts/logs

Examples currently present:

- top-level one-off scripts (`analyze_enc3.py`, `bulk_xxtea_decrypt.py`, `generate_key_candidates.py`, `hunt.py`)
- unpack/decompile data trees (`decompiled_lua*/`, `decrypted_xxtea/`, `readable_pack/`)

## Naming Migration Policy

External product naming should use neutral CTOA wording:

- "Agent Execution" instead of domain-specific labels in public-facing docs/endpoints.
- Legacy aliases remain temporarily for backward compatibility.

Migration status:

- Preferred endpoint enabled: `POST /api/agents/execution/run`
- Legacy alias retained: `POST /api/agents/mythibia/run`

## Definition of Product-Ready in Public Repo

A component is product-ready when all are true:

1. It has owner, purpose, and docs in this file.
2. It has at least one validation path (test/task/health check).
3. It does not expose secrets or local-only data dumps.
4. It is not a one-off forensic helper without product path.
