# B2 Studio Extraction Prep (Phase-1)

Execution tracker: #135
Date: 2026-05-31
Status: IN_PROGRESS

## Goal

Start B2 by defining the first extraction wave for Studio-private surfaces with minimal risk to Core runtime.

## Candidate Move Set (Phase-1)

1. archived
2. labs
3. backups

Rationale:
- These paths are internal/experimental or historical artifact surfaces.
- They have highest public/private leakage risk if kept in Core repo.
- They have lowest direct coupling to Core execution path (`runner`, `scoring`, `prompts`, `workflows`).

## Conditional/Phase-2 Paths (After Dependency Verification)

1. releases (split public evidence from private payloads)
2. data (split public fixtures from private corpora)
3. evals (keep allowlisted in Core unless private-only subsets appear)

## Dependency Checks Before Move

1. Search imports/references from Core runtime to `archived`, `labs`, `backups`.
2. Verify CI/workflow scripts do not consume Studio paths directly.
3. Add compatibility stubs or doc references if any path is referenced.

## Execution Checklist

- [x] B2 issue created (#135)
- [x] Prep document created
- [ ] Reference scan completed (`scripts`, `runner`, `workflows`, `tests`)
- [ ] Final move list approved
- [ ] First extraction PR opened

## Exit Criteria For Phase-1

1. `archived`, `labs`, `backups` removed from Core repo or replaced with thin references.
2. No broken imports/tasks/CI references to moved paths.
3. Hygiene and package-boundary checks pass.
