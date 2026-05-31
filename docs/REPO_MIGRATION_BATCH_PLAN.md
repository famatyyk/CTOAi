# Repo Migration Batch Plan

Findings: 37 top-level directories reviewed
Batches: 6
Date: 2026-05-31
Owner: STRATEGOS

## Approval And Execution Tracking

Status: Approved as source-of-truth for repo split execution.
Tracking issues:
- B0: #133 - Governance Freeze and Mapping
- B1: #134 - Core Surface Stabilization
- B2: #135 - Studio Extraction First (priority start)
- B3: #136 - Pro Extraction
- B4: #137 - Data and Evidence Segregation
- B5: #138 - Cutover and Enforcement

## Objective

Split this monorepo into clear product surfaces with deterministic ownership:
- Core (public runtime/governance toolkit)
- Pro (commercial console/deploy surface)
- Studio (internal/private research and operations)

Execution policy:
1. Freeze architecture future enhancements as backlog.
2. Complete repository split and boundary hardening first.
3. Resume feature-scale enhancements only after split closure criteria pass.

## Target Repository Model

1. `ctoa-core` (public): runner, governance, prompts, scoring, tests, docs, workflows.
2. `ctoa-pro` (private/commercial): mobile console and customer deployment package.
3. `ctoa-studio` (private/internal): labs, archived/internal artifacts, internal releases.

## Boundary Source Of Truth

- [product/packages/core.manifest.json](../product/packages/core.manifest.json)
- [product/packages/pro.manifest.json](../product/packages/pro.manifest.json)
- [product/packages/studio.manifest.json](../product/packages/studio.manifest.json)
- [docs/REPO_HYGIENE_POLICY.md](./REPO_HYGIENE_POLICY.md)

## Inventory And Proposed Ownership

| Path | Current role | Target package | Action | Risk |
|---|---|---|---|---|
| agents | Agent definitions/prompts | Core | Keep | Low |
| runner | Execution runtime | Core | Keep | Low |
| prompts | Prompt engine/templates | Core | Keep | Low |
| scoring | Tool/policy/risk engine | Core | Keep | Low |
| core | Guardrails/contracts | Core | Keep | Low |
| policies | Governance policies | Core | Keep | Low |
| workflows | Sprint/backlog contracts | Core | Keep | Low |
| scripts/ops | Ops validators/audits | Core | Keep, tighten scope | Medium |
| tests | Validation suite | Core | Keep | Low |
| docs | Product and governance docs | Core | Keep, split docs by package | Medium |
| schemas | Data contracts | Core | Keep | Low |
| tools | Utility modules | Core | Keep | Low |
| training | Prompt/training assets | Core | Keep | Medium |
| product | Package manifests/meta | Core | Keep (authoritative) | Low |
| mobile_console | Customer-facing console | Pro | Move to Pro repo | Medium |
| deploy | Deployment scripts/systemd | Pro | Move Pro-facing subset; keep core-safe ops in Core | High |
| releases | Mixed evidence + release artifacts | Split | Separate public evidence vs private release payloads | High |
| desktop_console | Local console app | Pro | Evaluate merge with mobile_console or move to Pro | Medium |
| labs | Experiments/internal tooling | Studio | Move to Studio repo | High |
| archived | Historical/internal/runtime dumps | Studio | Move to Studio repo | High |
| evals | Evaluation scenarios | Core (allowlisted) | Keep with governance labels | Medium |
| backups | Backup artifacts | Studio | Move to private storage/repo | High |
| logs | Runtime logs | Runtime-only | Keep ignored, do not version | Low |
| runtime | Transient evidence/state | Runtime-only | Keep ignored, promote only required evidence | Medium |
| data | Mixed datasets/snapshots | Split | Classify public fixtures vs private/internal data | High |
| bot | Bot runtime modules | Core | Keep with API boundary review | Medium |
| build | Build outputs | Runtime-only | Keep ignored | Low |
| dist | Build artifacts | Runtime-only | Keep ignored | Low |
| config | Runtime configuration templates | Core | Keep | Low |
| alembic | DB migration config | Core | Keep | Low |
| .devcontainer | Dev environment | Core | Keep | Low |
| .github | CI/CD workflows | Core | Keep, add package-specific gates | Medium |
| .vscode | Local tasks | Core | Keep, add per-package task groups | Medium |
| .foundry | Tooling metadata | Core (allowlisted) | Keep | Low |
| .ctoa-local | Local state | Runtime-only | Ensure ignored/non-release | Medium |
| __pycache__, .pytest_cache, .venv* | Local caches/envs | Runtime-only | Ignore | Low |

## Batch Execution Plan

### B0 - Governance Freeze And Mapping (Day 0-1)

Scope:
- Freeze Future Enhancements as backlog in architecture docs.
- Confirm manifest boundaries and CODEOWNERS draft.
- Build path ownership table (this document) and approve it.

Done when:
- Future enhancements section explicitly marked frozen.
- Ownership table approved by project owner.

### B1 - Core Surface Stabilization (Day 1-3)

Scope:
- Keep Core directories in place, remove ambiguity in naming and docs.
- Add CI matrix for package-aware checks: Core, Pro, Studio lint/contract checks.
- Ensure runtime-only paths remain ignored.

Done when:
- Core validate task passes.
- Repo hygiene audit reports no critical public/private violations.

### B2 - Studio Extraction First (Day 3-6)

Scope:
- Move `labs`, `archived`, private `backups`, and private `releases` payloads to `ctoa-studio`.
- Replace moved content with minimal references and interfaces.

Done when:
- No Studio-private artifacts remain in public Core surface.
- Studio repo bootstraps with independent README and CI sanity checks.

### B3 - Pro Extraction (Day 6-9)

Scope:
- Move `mobile_console`, Pro-specific `deploy`, Pro release loader payloads, and related app surfaces to `ctoa-pro`.
- Keep compatibility wrappers in Core only if needed.

Done when:
- Pro package builds/tests run from `ctoa-pro` independently.
- Core CI no longer depends on Pro runtime paths.

### B4 - Data And Evidence Segregation (Day 9-11)

Scope:
- Classify `data` into public fixtures vs private corpora.
- Promote required governance evidence to tracked locations.
- Keep runtime/debug outputs out of tracked history.

Done when:
- Evidence references resolve to tracked canonical paths.
- No sign-off-critical artifact remains runtime-only.

### B5 - Cutover And Enforcement (Day 11-14)

Scope:
- Finalize docs links for 3-repo topology.
- Turn on fail gates for hygiene and package boundary checks.
- Publish migration closure report and next-sprint entry criteria.

Done when:
- All package-specific validation gates are green.
- Architecture docs and runbooks reference split topology.

## CI And Task Updates Required

1. Add package-aware tasks:
- `CTOA: Validate Core Package`
- `CTOA: Validate Pro Package`
- `CTOA: Validate Studio Package`
- `CTOA: Repo Split Boundary Check`

2. Add CI checks:
- path ownership validation against package manifests
- forbidden path leakage checks (Studio/private into Core)
- evidence promotion and reference integrity check

3. Add ownership controls:
- CODEOWNERS for Core/Pro/Studio paths
- required reviewers for cross-package changes

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Cross-package dependency hidden in imports | Build failures after split | Run import graph checks before each extraction batch |
| Private artifacts accidentally kept in public repo | Security/compliance risk | Enforce hygiene fail gate and manual review in B2/B4 |
| CI gates become too slow/fragile during transition | Delivery slowdown | Stage gates gradually and cache test layers |
| Docs drift from actual path ownership | Operational confusion | Treat this plan as source-of-truth and update per batch |

## Immediate Next Actions (This Week)

1. Approve this plan as migration source-of-truth.
2. Create `ctoa-studio` repository and execute B2 first.
3. Add package-aware CI stubs and boundary-check task in current repo.
4. Open migration tracking issue per batch (B0-B5) with owner and deadline.

## Closure Criteria For Unfreezing Future Enhancements

Unfreeze deferred architecture enhancements only when all conditions pass:
1. B0-B5 marked complete.
2. Core/Pro/Studio ownership enforced in CI.
3. No critical findings in hygiene audit for two consecutive sprint waves.

