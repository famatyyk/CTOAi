# CTOAi

CTOAi is an AI operations platform built around a guarded Control Center, an
OTClient Helper, and a compatibility adapter layer. The public repository is
currently a transition-stage monorepo. Product boundaries are documented and
the sanitized repositories will be extracted through explicit allowlists.

## Current state

The repository is useful, but it is not a single release artifact. The current
Control Center and Helper work continue on dedicated branches and require
independent evidence before release. P14 is not marked ready without a signed,
independent acceptance report.

The public tree must contain source and documentation only. Local runtime state,
raw evidence, credentials, databases, logs, generated cache, and private Engine
Brain material stay outside the public product surface.

## Product map

| Product | Current source surface | Future repository |
| --- | --- | --- |
| Control Center | `web/src/app/control-center`, `web/src/app/api/control-center`, shared web components | `CTOAi-Control-Center` |
| OTClient Helper | `scripts/lua/otclient`, Helper tests, OTUI assets and contracts | `CTOAi-Helper` |
| Adapter layer | observation adapter, fork capability detection, compatibility schemas and tests | `CTOAi-Adapter` |
| Engine Brain and operations | `AI`, `scripts/ops`, `deploy`, `runtime`, private evidence and internal data | private repository/storage |

The adapter is currently co-located with the Helper for compatibility. It is a
separate ownership boundary and will be extracted before either product is
declared independently releasable.

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

## License

MIT (the historical public repository license). Internal/private assets are
not covered by a public export unless they pass the explicit publication gate.
