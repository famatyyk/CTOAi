# CTOAi

CTOAi is an AI operations platform built around a guarded Control Center, an
OTClient Helper, and a compatibility adapter layer. This repository remains the
transition-stage source and private operations boundary; sanitized, history-free
product exports are now published separately through explicit allowlists.

## Current state

The repository is useful, but it is not a single release artifact. The
published product repositories are independent source surfaces, while this
monorepo retains transition history and private Engine Brain integration.
Control Center and Helper releases still require independent evidence. P14 is
not marked ready without a signed, independent acceptance report.

The public tree must contain source and documentation only. Local runtime state,
raw evidence, credentials, databases, logs, generated cache, and private Engine
Brain material stay outside the public product surface.

## Product map

| Product | Current source surface | Published repository |
| --- | --- | --- |
| Control Center | `web/src/app/control-center`, `web/src/app/api/control-center`, shared web components | [`famatyyk/CTOAi-Control-Center`](https://github.com/famatyyk/CTOAi-Control-Center) |
| OTClient Helper | `scripts/lua/otclient`, Helper tests, OTUI assets and contracts | [`famatyyk/CTOAi-Helper`](https://github.com/famatyyk/CTOAi-Helper) |
| Adapter layer | observation adapter, fork capability detection, compatibility schemas and tests | [`famatyyk/CTOAi-Adapter`](https://github.com/famatyyk/CTOAi-Adapter) |
| Engine Brain and operations | `AI`, `scripts/ops`, `deploy`, `runtime`, private evidence and internal data | private repository/storage |

The adapter remains co-located in the transition monorepo for compatibility,
but its public export is already a separate ownership boundary. The published
repositories are sanitized snapshots and do not include monorepo history.

## Repository layout

- `web/` — canonical Control Center UI and read-only operations API.
- `scripts/lua/otclient/` — OTClient Helper runtime, UI and module contracts.
- `schemas/` — versioned contracts shared by products.
- `tests/` — validation and replay coverage; product-specific tests move with
  their owning repository during extraction.
- `docs/` — architecture, runbooks, evidence policy and migration decisions.
- `AI/`, `runtime/`, `deploy/`, `data/` — internal or operational material that
  must be reviewed before any public export.
- `config/repository-boundaries.json` — machine-readable export boundary.
- `scripts/ops/repository_export.py` — deterministic dry-run-first exporter for
  the three public product repositories.

## Public/private rules

Do not commit `.env` files, auth stores, logs, databases, raw runtime evidence,
private infrastructure mappings, generated caches, or unredacted Engine Brain
packs. Use the [public/private architecture](docs/PRODUCT_PUBLIC_PRIVATE_ARCHITECTURE.md)
and [repository split plan](docs/REPOSITORY_SPLIT_PLAN.md) as the publication
contract.

## Local development

```powershell
python -m pytest tests/ --ignore=tests/e2e -q
cd web; npm run lint; npm test
python scripts/ops/ctoa_full_workspace_validation.py --workspace .
```

Use `ctoa_control_central` for a compact read-only workspace status. Evidence
files belong in local ignored storage and are not a substitute for a signed
release report.

## Documentation

- [Repository split plan](docs/REPOSITORY_SPLIT_PLAN.md)
- [Repository boundary manifest](config/repository-boundaries.json)
- [Repository schema](docs/REPO_SCHEMA.md)
- [Product portfolio](docs/PRODUCT_PORTFOLIO.md)
- [Foundation cleanup](docs/CTOAI_FOUNDATION_CLEANUP.md)
- [Public/private architecture](docs/PRODUCT_PUBLIC_PRIVATE_ARCHITECTURE.md)
- [Repository hygiene policy](docs/REPO_HYGIENE_POLICY.md)
- [OTClient Helper documentation](scripts/lua/otclient/README.md)

The local exporter can be inspected without writing files:

```powershell
python scripts/ops/repository_export.py --all --dry-run
```

## License

MIT (the historical public repository license). Internal/private assets are
not covered by a public export unless they pass the explicit publication gate.
