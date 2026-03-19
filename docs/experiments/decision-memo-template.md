# Decision Memo Template

Use this template at the end of every experiment cycle, or when an experiment needs a hard go, hold, or kill decision.

## Header
- Experiment ID:
- Experiment title:
- Date:
- Owner:
- Reviewer:
- Related issue:
- Related branch or PR:

## Hypothesis
- If we change:
- We expect:
- Metric expected to improve:
- Expected lift:

## Baseline
- Current method or prompt:
- Current owner workflow:
- Baseline evidence:
- Known pain points:

## Challenger
- What changed:
- What stayed fixed:
- Why this is a valid comparison:

## Evidence Summary
| Metric | Baseline | Challenger | Delta | Notes |
|--------|----------|------------|-------|-------|
| Quality |  |  |  |  |
| Cycle time |  |  |  |  |
| Operator load |  |  |  |  |
| Failure rate |  |  |  |  |
| Reproducibility |  |  |  |  |
| Cost |  |  |  |  |

## What We Learned
- Strong signals:
- Weak signals:
- Unexpected behavior:
- Failure modes found:

## Risk Review
- Safety impact:
- Delivery impact:
- Coordination overhead:
- Rollback complexity:

## Decision
- Final decision: `promote` / `hold` / `kill`
- Why:
- Conditions required before promotion:
- If hold, next checkpoint:
- If kill, what should be preserved for future reference:

## Approval Block
- QA signoff:
- CI status:
- Owner approval:
- Promotion allowed: `yes` / `no`
