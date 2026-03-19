# Next-Cycle Candidate: Routing Micro-Experiment Charter

## Status
- State: deferred
- Start window: next cycle only
- Lane rule: this is a new candidate, not a reactivation of `EXP-002`

## Candidate Header
- Candidate ID: `EXP-NEXT-ROUTING-MICRO-001`
- Owner: `pm-roadmap`
- Reviewers: `tool-advisor`, `qa-safety`
- Timebox: 1 day (setup + replay + decision)

## Fresh Hypothesis
- If we apply a narrow routing rule set only to low-risk documentation and planning tasks,
- then retry rate will decrease by at least 15 percent against baseline,
- without reducing output quality or increasing operator load.

## Baseline (Required Before Start)
- Baseline routing profile: current stable routing from post-EXP week state.
- Task sample: 20 tasks minimum, same category mix for baseline and challenger.
- Baseline metrics to capture:
	- retry count per task
	- first-pass completion rate
	- cycle time
	- operator interventions per task
	- QA quality score

## Challenger Scope
- Allowed task domains:
	- docs consolidation
	- experiment memo drafting
	- scorecard and evidence collation
- Excluded domains:
	- auth/security policy mutations
	- production deployment changes
	- role/permission logic changes

## Continuation Gates
1. Day-2 complexity budget gate:
	 - stop if rule count or routing branches exceed the pre-set micro budget.
2. Retry-reduction gate:
	 - continue only if retry reduction is measurable and repeatable across two replay slices.
3. Safety gate:
	 - stop immediately on any QA safety regression.

## Decision Thresholds
- Promote candidate only if all conditions are met:
	- retry reduction >= 15 percent
	- no quality regression
	- no increase in operator load
	- reproducibility confirmed in replay
- Otherwise: `hold` or `kill`.

## Carry-Over Lessons From EXP-002
1. Complexity budget must be explicit before Day 2.
2. Retry reduction must be measurable and repeatable, not anecdotal.

## Evidence Pack Required
- One completed daily scorecard.
- One decision memo with baseline vs challenger table.
- One rollback note.
- QA and owner signoff.
