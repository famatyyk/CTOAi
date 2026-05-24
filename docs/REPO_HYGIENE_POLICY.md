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

## Approved Top-Level Exceptions

The following entries are explicitly classified as product-relevant and remain allowlisted:

- `.foundry` (Foundry workspace/project metadata used by tooling)
- `agent.yaml` (root agent/runtime configuration contract)
- `evals/` (evaluation scenarios and quality comparison inputs)

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

## Sprint-050 Evidence Promotion Rules

Use these rules to decide when runtime outputs must be promoted from ignored locations to tracked evidence paths.

### Promote To Tracked Paths (Required)

- Validation artifacts used for sprint sign-off decisions (for example sprint validate JSON reports)
- Wave execution transcripts that prove gate outcomes (tests, validate, launch)
- Approval closure evidence that demonstrates transitions from `WAITING_APPROVAL` to `RELEASED`
- Any artifact cited as authoritative in release notes or sprint handoff documents

### Keep In Runtime Only (Default)

- Debug-level intermediate files that are not referenced by sign-off docs
- High-volume operational logs without release or governance impact
- Local experimentation outputs that do not affect acceptance criteria

### Canonical Promotion Targets

- `releases/evidence/sprint-XXX/` for release-significant snapshots and sign-off attachments
- `docs/history/sprints/SPRINT-XXX-PROGRESS.md` for concise, human-readable evidence summaries
- `runtime/experiments/sprint-XXX/CTOA-YYY.md` for scoped operator notes before promotion

### Promotion Workflow

1. Identify candidate artifacts in `runtime/ci-artifacts/` and `runtime/experiments/`.
2. Classify each artifact as required or runtime-only using the rules above.
3. Copy required artifacts to `releases/evidence/sprint-XXX/` and keep file names stable.
4. Update sprint progress and sign-off docs with relative links to promoted paths.
5. Re-run hygiene audit and ensure no sign-off-critical evidence remains runtime-only.

## Sprint-051 Tracked Evidence Continuity Addendum

Apply this continuity contract to every Sprint-051 sign-off-critical artifact.

### Required Continuity Set

- Wave gate artifacts: validation JSON and wave run transcript
- Governance closure artifacts: approval/state sync notes and sign-off memo
- Handoff artifact: Sprint-052 recommendation memo cited by Sprint-051 sign-off

### Canonical Sprint-051 Targets

- `releases/evidence/sprint-051/CTOA-266.md`
- `releases/evidence/sprint-051/CTOA-267.md`
- `releases/evidence/sprint-051/CTOA-268.md`
- `releases/evidence/sprint-051/CTOA-269.md`
- `docs/history/sprints/SPRINT-051-PROGRESS.md`
- `docs/history/sprints/SPRINT-051.md`

### Continuity Check

Before sign-off, ensure every artifact referenced in `SPRINT-051-PROGRESS.md` resolves to a tracked repository path.
