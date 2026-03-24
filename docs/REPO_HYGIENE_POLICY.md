# Repo Hygiene Policy (Public Product Repo)

Goal: keep this repository focused on public CTOA products, while moving internal drafts, forensic artifacts, and raw dumps outside the product surface.

## Core Rules

1. Public repo stores product code, product docs, validated workflows, and release evidence.
2. Raw research artifacts and local forensic outputs must not be committed by default.
3. Secrets/tokens are forbidden in history, files, and command snippets.
4. New top-level files require explicit product relevance.

## Data Placement Strategy

- Product metadata and state:
  - use Postgres/runtime DB tables and compact JSON summaries.
- Large/raw artifacts:
  - store in object storage or private lab repo.
- Local transient outputs:
  - keep in ignored folders (`runtime/`, `logs/`, private lab paths).

## Naming and API Exposure

- Public naming uses CTOA-neutral product terms.
- Domain-specific legacy names can remain only as compatibility aliases.
- New APIs/scripts must use neutral naming by default.

## Cleanup Workflow

1. Identify non-product files via hygiene audit script.
2. Classify each finding: keep product / move to private lab / archive.
3. Move artifacts to private storage and keep only references/metadata.
4. Update docs and tasks to point to product paths only.

## Immediate Focus Areas

- reduce top-level one-off script clutter
- isolate reverse-engineering helpers under clearly marked internal path
- keep README and docs centered on active products

## Enforcement

Run:

```bash
python scripts/ops/repo_hygiene_audit.py --json-out runtime/repo-hygiene/latest.json
```

Fail CI mode:

```bash
python scripts/ops/repo_hygiene_audit.py --fail-on-findings --json-out runtime/repo-hygiene/latest.json
```

## Package Awareness

Repo hygiene is package-aware:

- Core: public-safe toolkit runtime and governance surface
- Pro: public commercial add-ons such as console/control-plane surfaces
- Studio: internal/private overlays that must not remain in public customer distribution

Package manifests live under `product/packages/` and should be updated before major cleanup waves.
