# CTOA Client Distribution Model

This document defines how private CTOA source surfaces are packaged for approved
clients without publishing the canonical repository or its Git history.

## Product Tiers

### Core

Audience:

- approved self-hosted customers
- approved technical customers
- developer customers receiving a controlled toolkit export

Includes:

- agent runtime and prompts
- scoring and schemas
- bootstrap and update gate
- release governance and validated workflows
- customer-safe documentation and configuration templates

Excludes:

- premium UX/admin surfaces
- private operations automation
- internal studio tooling
- raw data and training assets

### Pro

Audience:

- commercial customers consuming higher-value packaged experiences
- customers receiving sealed capabilities without access to training internals

Includes everything from Core, plus:

- mobile console packageable surface
- selected dashboard/control plane capabilities
- sealed capability packs approved for customer use
- customer-safe support docs and packaging metadata

Excludes:

- private VPS automation secrets and internal-only ops flows
- studio training and evaluation pipeline internals

### Studio

Audience:

- internal CTOA team only

Includes:

- private overlays
- internal operations tooling
- private telemetry and tenant ops data
- training/eval/fine-tuning assets
- raw research, reverse-engineering and private lab trees

Studio assets must not define the public product narrative or leak into customer packages.

## Surface Rules

### Allowed in Core

- `agents/`
- `prompts/`
- `runner/`
- `scoring/`
- `schemas/`
- `policies/`
- `workflows/`
- `tests/` relevant to exported product behavior
- `scripts/ops/` export-safe setup, validation, and release scripts
- `config/`
- `product/`

### Allowed in Pro

- everything in Core
- `mobile_console/`
- selected deployment templates and release packaging metadata

### Studio-only

- reverse-engineering helpers
- decrypted/decompiled trees
- raw forensic reports
- private infrastructure overlays
- customer-specific or internal datasets
- internal-only runtime storage

## Cleanup Priority for Controlled Distribution

1. Keep Studio-only raw artifact trees out of every export.
2. Move one-off research tools under clearly archived/internal paths or private storage.
3. Reduce top-level clutter so only product paths remain obvious.
4. Keep package manifests current so every path has an explicit distribution tier.

## Distribution Contract

Customer clone flow:

1. receive an approved, sanitized package without repository history
2. pass mandatory update gate
3. run bootstrap to create local config/state
4. launch only the tier they are licensed/configured for

## Enforcement

Package manifests under `product/packages/` define which private source paths may
enter Core or Pro exports and which remain Studio-only.

Repo hygiene and public-exposure audits enforce those boundaries before any
external delivery.
