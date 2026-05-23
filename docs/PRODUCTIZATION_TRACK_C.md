# CTOA Track C — Productization Plan

**Track:** C — Productization
**Sprint:** Sprint-040 / Sprint-041
**Status:** ACTIVE
**Updated:** 2026-05-10

---

## Objective

Prepare CTOA AI Toolkit for structured public distribution through clearly
defined packaging tiers, clean public/private surface hygiene, and a
documented operator UX and release cadence.

---

## Packaging Tiers

CTOA is distributed in three tiers. Canonical manifests live under
`product/packages/`.

### Core (public, self-hosted)

- Target: self-hosted operators, technical integrators, developer customers.
- Includes: agent runtime, prompts, scoring, schemas, bootstrap/update gate,
  release governance, validated workflows, public documentation.
- Excludes: mobile console, private ops automation, studio tooling, raw training
  assets.
- Manifest: `product/packages/core.manifest.json`

### Pro (commercial)

- Target: commercial customers receiving packaged, higher-value experiences.
- Includes everything in Core, plus: mobile console surface, selected dashboard
  and control-plane capabilities.
- Manifest: `product/packages/pro.manifest.json`

### Studio (internal only)

- Target: internal R&D, reverse-engineering lab, private ops overlays.
- Includes everything in Pro, plus: raw assets, training internals, private VPS
  automation, lab/research tracks.
- Manifest: `product/packages/studio.manifest.json`

Reference: `docs/CLIENT_DISTRIBUTION_MODEL.md`

---

## Public/Private Surface Hygiene Rules

1. **No studio paths in Core or Pro exports.** Paths matching
   `archived/runtime/private-storage/**`, `decompiled_lua/**`,
   `artifacts/**` are always excluded from public tiers.
2. **No credentials or tokens** in any committed file under public tier paths.
3. **API endpoints** listed in `docs/PRODUCT_PORTFOLIO.md` are the only ones
   considered stable public API. All others are internal and may break without
   notice.
4. **Documentation** in `docs/` that references internal VPS hostnames, database
   credentials, or private service endpoints must be annotated with
   `<!-- internal -->` or moved to `docs/internal/`.
5. **`REPO_HYGIENE_POLICY.md`** is the canonical reference for hygiene rules.
   Update it whenever a new category of sensitive content is identified.

---

## Operator UX and Release Cadence

### How Operators Adopt a New CTOA Version

1. Check `CHANGELOG.md` for breaking changes in the target version.
2. Run `python scripts/ops/ctoa_update_gate.py` — this verifies the current
   installation against the target baseline and reports go/no-go.
3. If go: pull the new tag or archive and replace the installation.
4. Verify core integrity post-install:
   ```
   python scripts/ops/core_guard.py --check
   ```
5. Run the test suite:
   ```
   python -m pytest tests/ --ignore=tests/e2e -q
   ```
6. Confirm the update gate passes again:
   ```
   python scripts/ops/ctoa_update_gate.py
   ```

### Release Cadence

| Phase | Frequency | Owner |
|-------|-----------|-------|
| Sprint delivery | ~2 weeks | STRATEGOS + agents |
| Wave-1 automated gate | Per sprint close | CI (ctoa-pipeline.yml) |
| Wave-2 manual sign-off | Per sprint close | STRATEGOS |
| Baseline promotion | After Wave-2 pass | STRATEGOS |
| Public tier packaging | Per minor release | DevOps |

### Version Numbering

- **Patch** (`x.y.Z`): bug fixes, evidence hardening, documentation corrections.
- **Minor** (`x.Y.0`): new features, new sprint deliverables, tier additions.
- **Major** (`X.0.0`): breaking API changes, governance policy overhauls.

Current release: **v1.13.0** (Sprint-040 closed).
Next planned: **v1.14.0** (Sprint-041, Track C delivery).

---

## Delivery Checklist (per release)

- [ ] All sprint tasks in `RELEASED` state in the backlog YAML
- [ ] `CHANGELOG.md` entry written and reviewed
- [ ] `runtime/experiments/sprint-NNN/` release pack created
- [ ] `docs/POST_GA_DELIVERY_TRAIN_CANDIDATE.yaml` `status` updated to `released`
- [ ] `docs/POST_GA_DELIVERY_TRAIN_BASELINE.md` baseline tag updated
- [ ] README Command Center table updated
- [ ] `python scripts/ops/core_guard.py --check` → PASSED
- [ ] `python -m pytest tests/ --ignore=tests/e2e -q` → all pass

---

## References

- `docs/ROADMAP_V0.2.0_TO_V1.0.0.md` — canonical roadmap
- `docs/CLIENT_DISTRIBUTION_MODEL.md` — tier distribution rules
- `docs/REPO_HYGIENE_POLICY.md` — hygiene policy
- `product/packages/` — tier manifests
- `docs/PRODUCT_PORTFOLIO.md` — product map and API registry
