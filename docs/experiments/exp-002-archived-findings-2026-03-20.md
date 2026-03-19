# EXP-002 Archived Findings - 2026-03-20

## Experiment
- ID: `EXP-002`
- Name: Tool Routing Efficiency
- Final outcome: `kill`

## Why It Was Closed
The rescoped routing replay removed architecture complexity concerns, but the experiment still failed to produce a strong enough efficiency gain to justify continued investment.

## Final Findings
1. What improved
- Complexity budget improved after removing the heavy routing branch.
- QA safety confidence improved after rescope.

2. What did not improve enough
- Retry count showed no durable reduction.
- Cycle-time gain stayed flat rather than improving.
- Output quality did not move above baseline in a meaningful way.

3. Decision rationale
- The tradeoff shifted from `too complex` to `not valuable enough`.
- Continuing the lane would consume experiment capacity without strong expected lift.

## Lessons Learned
1. Routing experiments need a complexity budget before Day 2, not after.
2. Retry reduction must be measurable and repeatable to justify continued work.
3. Simplification alone is not enough; the experiment still needs a material upside.

## Reuse Guidance
This experiment should not be reopened in its current form. It may be reconsidered later only if:
- a new routing hypothesis exists,
- the task sample changes materially,
- expected gain is stronger than neutral,
- experiment capacity is available.

## Archive Status
- Owner closing lane: `pm-roadmap`
- Findings owner: `tool-advisor`
- Future state: archived for reference, not active backlog
