# Day 1 Execution - 2026-03-19

## Objective
Start the experiment lane with bounded scope, baseline evidence, and a first hard `go/hold/kill` package.

## Day 1 Outputs
1. Experiment lane activated under Sprint-007 without changing release-lane policy.
2. Baseline captured from current repo and automation state.
3. Three experiment candidates defined.
4. First `go/hold/kill` decisions recorded.
5. Day 2 ownership map prepared for all 10 agents.

## Baseline Snapshot
- Repository: `famatyyk/CTOAi`
- Branch: `main`
- Latest experiment-docs commit: `9ffa1b8`
- CI pipeline status: green (`CTOA Pipeline` success)
- GitHub Pages: active
- Site build: `v2026.03.19-j`
- Local caveat: independent uncommitted `README.md` change remains outside this lane.

## Candidate Experiments
### EXP-001 Prompt Quality Lift
- Goal: improve output quality and reduce operator correction loops through BRAVE(R) challenger packs.
- Scope: planning and coding tasks only.
- Owner group: `prompt-forge`, `qa-safety`, `evaluator`.

### EXP-002 Tool Routing Efficiency
- Goal: improve tool selection quality and reduce retries using sandbox scoring variants.
- Scope: routing logic and recommendation comparison only.
- Owner group: `tool-advisor`, `bot-architect`, `optimizer`, `qa-safety`.

### EXP-003 Landing Telemetry and UX Signal
- Goal: capture reliable interaction metrics from public page and test one CTA variant.
- Scope: `docs/site` telemetry and event export only.
- Owner group: `builder-engine`, `mmo-intel`, `ci-publisher`.

## Day 1 Decision Pack
## GO
### EXP-001 Prompt Quality Lift
- Why go:
  - High expected signal with low blast radius.
  - Existing templates and scorecard are already in repo.
  - Direct impact on agent productivity and quality.
- Day 2 action:
  - Build baseline and challenger prompt set.
  - Lock evaluation criteria and sample task set.

### EXP-002 Tool Routing Efficiency
- Why go:
  - Direct alignment with `CTOA-034` and current tool-advisor architecture.
  - Strong chance to lower retries and operator overhead.
  - Can run fully in sandbox with rollback by config.
- Day 2 action:
  - Prepare ranking variants.
  - Run before/after against representative task sample.

## HOLD
### EXP-003 Landing Telemetry and UX Signal
- Why hold:
  - Needs KPI alignment to avoid collecting vanity metrics.
  - Should start only after scorecard and decision cadence are proven on EXP-001/002.
  - Potentially mixes product experiment with operations experiments too early.
- Hold condition:
  - Re-evaluate on Day 5 after first hard-cut review.
- Unhold trigger:
  - Clear KPI definition and owner confirmation from `pm-roadmap` + `queen-ctoa`.

## KILL
- None on Day 1.
- Rule: any experiment with no measurable signal after 48 hours enters `kill or rescope`.

## Day 2 Work Allocation (10 Agents)
1. `queen-ctoa`: approve final Day 2 scope and enforce max 2 active experiments.
2. `pm-roadmap`: publish assignment matrix and deadlines for EXP-001 and EXP-002.
3. `prompt-forge`: prepare baseline and challenger prompt packs for EXP-001.
4. `tool-advisor`: prepare sandbox scoring variants for EXP-002.
5. `mmo-intel`: provide domain risk and relevance brief for both experiments.
6. `lua-scripter`: define code-focused validation cases for prompt output quality.
7. `bot-architect`: review routing-change complexity and integration risk.
8. `builder-engine`: prepare isolated execution path for experiment runs.
9. `qa-safety`: lock validation checks, failure thresholds, and acceptance gates.
10. `ci-publisher`: define promotion evidence package and release-lane blockers.

## Exit Criteria for Day 1
- `go/hold/kill` decisions documented.
- Day 2 owners assigned.
- No release-lane policy changes introduced.
