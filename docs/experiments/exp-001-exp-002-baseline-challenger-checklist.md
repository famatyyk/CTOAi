# Baseline/Challenger Checklist - EXP-001 and EXP-002

Use this checklist before recording Day 2 outcomes.

## Common Preconditions
- [ ] Scope is unchanged from Day 1 `go` decision.
- [ ] Same task sample is used for baseline and challenger.
- [ ] Same reviewers are assigned for baseline and challenger.
- [ ] Scorecard fields are ready.
- [ ] Rollback path exists if challenger fails.

## EXP-001 Prompt Quality Lift

### Baseline Setup
- [ ] Baseline prompt pack selected from current BRAVE(R) flow.
- [ ] Baseline task set locked (planning + coding samples).
- [ ] Baseline output quality criteria frozen.
- [ ] Baseline run log captured.

### Challenger Setup
- [ ] Challenger prompt variant documented.
- [ ] Only prompt variable changed; tools and task set unchanged.
- [ ] Challenger run log captured.

### Comparison Checks
- [ ] Quality score compared (baseline vs challenger).
- [ ] Correctness score compared.
- [ ] Operator correction effort compared.
- [ ] Failure and safety notes reviewed by `qa-safety`.
- [ ] Reproducibility checked with at least one replay.

### Decision Gate
- [ ] `go` if quality improves and no risk regression.
- [ ] `hold` if signal is weak or inconclusive.
- [ ] `kill` if quality drops or safety risk increases.

## EXP-002 Tool Routing Efficiency

### Baseline Setup
- [ ] Baseline routing/scoring settings captured.
- [ ] Baseline task sample locked.
- [ ] Baseline retries and cycle-time logged.

### Challenger Setup
- [ ] Challenger routing variant documented.
- [ ] Only routing/scoring variable changed.
- [ ] Challenger retries and cycle-time logged.

### Comparison Checks
- [ ] Retry count compared.
- [ ] Cycle-time compared.
- [ ] Output quality compared.
- [ ] Architecture complexity reviewed by `bot-architect`.
- [ ] Safety risk reviewed by `qa-safety`.

### Decision Gate
- [ ] `go` if retries/cycle-time improve with no quality or safety regression.
- [ ] `hold` if gains are minor or unstable.
- [ ] `kill` if complexity and risk increase without clear gain.
