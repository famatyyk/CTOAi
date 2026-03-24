# CTOA Product Architecture: Public vs Private

This document defines which parts of CTOA are public product surface and which must remain private studio/operations assets.

## Product Goal

Ship a reusable CTOA Toolkit that any customer can clone and configure for their own environment, without receiving CTOA internal credentials, internal infrastructure details, or training pipelines.

## Product Layers

### 1. Public Core: CTOA Toolkit

Public distribution includes:

- product code and UX surfaces
- agent runtime definitions usable by customers
- prompt updates intended for public delivery
- workflow specs, validators, release governance contracts
- bootstrap/configuration wizard
- mandatory update gate before launch
- local configuration template and setup guidance

Primary public paths:

- `agents/`
- `prompts/`
- `runner/`
- `scoring/`
- `schemas/`
- `mobile_console/`
- `workflows/`
- `policies/`
- `scripts/ops/ctoa_product_bootstrap.py`
- `scripts/ops/ctoa_update_gate.py`
- `product/`

### 2. Private Studio Overlay: CTOA Studio

Private studio assets remain outside public distribution.

Private-only scope includes:

- real secrets, PATs, API keys, SSH keys, internal hostnames
- internal VPS topology and privileged automation
- raw telemetry, raw datasets, training corpora, prompt lab experiments
- internal-only dashboards or privileged mobile console features
- agent training, fine-tuning, evaluation, and optimization pipelines
- customer-specific tenant operations data

Private assets belong in a separate private repository, private storage, or sealed deployment environment.

### 3. Sealed Capability Packs

Customer-facing product tiers may include sealed agents and sealed workflows.

Allowed for customers:

- use the trained agents
- configure their own environment and data sources
- receive prompt/runtime updates that CTOA publishes

Not allowed for customers:

- retrain CTOA-provided agents
- modify internal training logic
- access private evaluation datasets or optimization loops

## Public/Private Boundaries

### Public Repo Rules

Public repo may contain:

- sanitized examples
- config templates
- schemas and migrations
- public product documentation
- release packs for public versions

Public repo must not contain:

- real `.env` files
- production credentials
- internal-only customer data
- internal experiment outputs
- private infrastructure mappings
- training source datasets

### Local User State

Customer-specific state is created only at bootstrap time and stored in ignored local paths.

Artifacts created locally:

- `.ctoa-local/user-config.json`
- `.ctoa-local/bootstrap-state.json`
- `.ctoa-local/toolkit-state.db`

These files must never be committed.

## Launch Lifecycle

Every product launch follows this sequence:

1. Clone or update repository.
2. Run mandatory update gate.
3. If toolkit version is outdated or bootstrap schema changed, launch is blocked.
4. Run bootstrap/configuration flow.
5. Bootstrap writes local JSON config and local SQLite registration.
6. Product launch continues only when update gate passes.

## Release Policy

Public release train ships:

- toolkit runtime updates
- prompt updates approved for public use
- sealed capability packs
- compatibility updates for config/bootstrap schema

Private studio release train ships separately:

- internal dashboards
- training updates
- private ops tooling
- internal telemetry pipelines

## Immediate Productization Roadmap

### Phase 1: Foundation

- public/private architecture defined
- tracked product manifest added
- bootstrap script writes local config and local DB state
- update gate enforced before launch

### Phase 2: Repo Cleanup

- move private/internal artifacts out of product surface
- reduce top-level one-off scripts
- archive or migrate legacy/research trees

### Phase 3: Distribution

- package public toolkit by tier
- add signed release/update manifest
- add installer/bootstrap UX for non-technical customers

## Design Constraint

CTOA Toolkit should feel like a product studio platform, not a dump of mixed internal assets. Public product code stays reusable, configurable, and auditable. Private CTOA intelligence, training, and operations remain sealed.