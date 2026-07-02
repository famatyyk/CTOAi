# CTOAi Documentation Index

This is the routing map for repository documentation. Use it before adding a new
document or deciding which older document should drive implementation.

## Canonical

These documents define the current shape of the repo and should be updated when
the system changes:

- [README](../README.md): current repo entry point and visible operating status.
- [Changelog](../CHANGELOG.md): release history only, not current operating truth.
- [Repo Schema](REPO_SCHEMA.md): current repository map and ownership contract.
- [Foundation Cleanup](CTOAI_FOUNDATION_CLEANUP.md): canonical surface cleanup plan.
- [Product Portfolio](PRODUCT_PORTFOLIO.md): product ownership and product-ready definition.
- [Repo Hygiene Policy](REPO_HYGIENE_POLICY.md): public repo hygiene and evidence placement rules.
- [Infrastructure Canonical](INFRASTRUCTURE_CANONICAL.md): production infrastructure source of truth.
- [Sprint Governance](SPRINT_GOVERNANCE.md): sprint lifecycle, gates, and approval flow.
- [Validation Checklist](VALIDATION_CHECKLIST.md): deployment and runtime validation checklist.
- [README Inventory](README_INVENTORY.md): README cleanup guardrail and classification map.

## Active Working Docs

These documents are still useful for implementation, but they should defer to the
canonical docs above when there is a conflict:

- [Control Center Phase 1](CTOAI_CONTROL_CENTER_PHASE1.md): implementation history and next Control Center ideas.
- [Local Setup](LOCAL_SETUP.md): local bootstrap and operator setup.
- [Deployment](DEPLOYMENT.md): deployment procedures and rollback notes.
- [Mobile Console](MOBILE_CONSOLE.md): legacy/API compatibility and mobile console operations.
- [Architecture](ARCHITECTURE.md): deeper architecture notes.
- [CTOA CLI](CTOA_CLI.md): command-line operator surface.
- [Product Public/Private Architecture](PRODUCT_PUBLIC_PRIVATE_ARCHITECTURE.md): product boundary rationale.
- [Repo Cleanup Waves](REPO_CLEANUP_WAVES.md): cleanup wave contract and execution record.

## Historical Snapshots

These are retained for traceability. Do not treat their status tables as current
unless README and the active sprint docs confirm the same state.

- [Roadmap v0.2.0 to v1.0.0](ROADMAP_V0.2.0_TO_V1.0.0.md)
- [Productization Track C](PRODUCTIZATION_TRACK_C.md)
- [Sprint History](history/sprints/)
- [Experiments](experiments/)

## Evidence

Evidence proves past decisions and release state. It is usually append-only and
should be linked from sprint or release docs rather than rewritten.

- [Tracked release evidence](../releases/evidence/)
- [Docs evidence](evidence/)
- [Eval runs](../evals/runs/)

## Decision Rules

1. If docs disagree, prefer `README.md` for current status.
2. Prefer `docs/REPO_SCHEMA.md` for ownership and canonical surfaces.
3. Prefer `docs/INFRASTRUCTURE_CANONICAL.md` for VPS, deploy, and production values.
4. Treat `docs/ROADMAP_V0.2.0_TO_V1.0.0.md` and `docs/PRODUCTIZATION_TRACK_C.md` as historical snapshots.
5. Add new docs only when they introduce a durable contract, runbook, or evidence artifact.
