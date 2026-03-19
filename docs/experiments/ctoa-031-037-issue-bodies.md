# CTOA-031..037 Issue Bodies

Use these sections as ready-to-publish issue bodies for GitHub issues CTOA-031 through CTOA-037.

## CTOA-031: Experiment Charter and Guardrails

### Objective
Define the bounded experiment lane and the operating rules that keep experimentation safe and measurable.

### Problem Statement
- Experiments can be launched, but not yet under one clear operating charter.
- We need hard constraints for hypothesis, scoring, rollback, and promotion.

### Deliverables
- Experiment charter
- Allowed experiment categories
- Stop conditions and rollback rules
- Daily review protocol
- Promotion evidence requirements

### Dependencies
- docs/operating-model.md
- docs/SPRINT_GOVERNANCE.md
- docs/experiments/decision-memo-template.md
- docs/experiments/daily-experiment-scorecard.md

### Acceptance Criteria
- Every experiment includes: hypothesis, owner, timebox, metric, rollback path.
- Experiment lane is explicitly separated from release lane.
- Every experiment ends with promote, hold, or kill.
- Promotion requires green CI, QA signoff, owner approval, and written evidence.

### Risks
- Too much policy overhead.
- Experiments bypassing release safety constraints.

### Owners
- Lead: queen-ctoa
- Review: pm-roadmap, qa-safety, ci-publisher

---

## CTOA-032: Agent Capability Matrix and Routing Map

### Objective
Create one ownership matrix for all 10 agents across experiment work.

### Problem Statement
- Without explicit mapping, experiment ownership can overlap and produce duplicate work.

### Deliverables
- Capability matrix (10 agents)
- Primary and secondary roles
- Routing map by experiment type
- Escalation and handoff rules

### Dependencies
- agents/ctoa-agents.yaml
- agents/definitions.py
- docs/experiments/agent-experiment-week-plan.md

### Acceptance Criteria
- Each experiment type has lead and reviewer agents.
- No task category is left without owner mapping.
- Handoff rules are documented for planning, implementation, QA, and release.

### Risks
- Role overlap creating queue contention.

### Owners
- Lead: pm-roadmap
- Review: queen-ctoa, tool-advisor, qa-safety

---

## CTOA-033: BRAVE(R) Experiment Packs

### Objective
Standardize prompt experiments with a reusable baseline vs challenger format.

### Problem Statement
- Prompt improvements are too easy to run ad hoc and hard to compare over time.

### Deliverables
- 3 to 5 experiment pack templates
- Baseline vs challenger structure
- Prompt evaluation rubric
- Failure mode checklist

### Dependencies
- prompts/braver-library.yaml
- docs/experiments/daily-experiment-scorecard.md
- docs/experiments/decision-memo-template.md

### Acceptance Criteria
- At least 3 reusable prompt experiment packs exist.
- Each pack supports baseline vs challenger scoring.
- Output is measurable on quality, operator load, and reproducibility.

### Risks
- Prompt churn without measurable gain.

### Owners
- Lead: prompt-forge
- Review: qa-safety, evaluator

---

## CTOA-034: Tool Advisor Sandbox Tuning

### Objective
Tune tool-routing scoring in a sandbox and evaluate gains against baseline routing.

### Problem Statement
- Current routing can be improved, but changes need bounded testing with rollback.

### Deliverables
- Candidate scoring changes
- Before/after routing comparison
- Regression notes for high-risk tasks
- Final recommendation memo

### Dependencies
- scoring/tool-advisor-rules.yaml
- docs/experiments/daily-experiment-scorecard.md
- docs/experiments/decision-memo-template.md

### Acceptance Criteria
- At least one candidate scoring update shows measurable improvement.
- No high-risk safety regressions.
- Rollback path documented.

### Risks
- Overfitting to too small task sample.

### Owners
- Lead: tool-advisor
- Review: bot-architect, qa-safety, optimizer

---

## CTOA-035: Agent Evaluation Scorecard

### Objective
Adopt one lightweight scorecard that all experiments must use.

### Problem Statement
- Decisions drift toward intuition without a standard scorecard.

### Deliverables
- Daily scorecard template
- Scoring rubric
- Baseline task sample guidance
- Go, hold, kill thresholds

### Dependencies
- docs/experiments/daily-experiment-scorecard.md
- docs/experiments/decision-memo-template.md

### Acceptance Criteria
- Every active experiment is evaluated on one shared rubric.
- Baseline and challenger can be compared directly.
- Final decision references scorecard evidence.

### Risks
- Scorecard too heavy for daily cadence.

### Owners
- Lead: evaluator
- Review: qa-safety, pm-roadmap

---

## CTOA-036: Daily Experiment Review Loop

### Objective
Run a strict daily review that forces continue, kill, or promote decisions.

### Problem Statement
- Experiments lose signal when they do not get daily decision pressure.

### Deliverables
- Daily review format
- Experiment state labels
- Decision journal structure
- Stale cleanup policy

### Dependencies
- docs/experiments/daily-experiment-scorecard.md
- docs/experiments/decision-memo-template.md
- docs/experiments/agent-experiment-week-plan.md

### Acceptance Criteria
- Every running experiment gets daily state update.
- Every daily review ends with concrete decision.
- Experiments with no signal after 48h are killed or rescoped.

### Risks
- Review loop turns into status-only ritual.

### Owners
- Lead: queen-ctoa
- Review: pm-roadmap, qa-safety, ci-publisher

---

## CTOA-037: Promotion Gate for Winning Experiments

### Objective
Define how proven experiments enter production safely.

### Problem Statement
- Winning experiments need a repeatable promotion path through CI, QA, and approval.

### Deliverables
- Promotion checklist
- Evidence bundle format
- Adoption threshold
- Rollback readiness rules

### Dependencies
- docs/experiments/decision-memo-template.md
- docs/VALIDATION_CHECKLIST.md
- docs/SPRINT_GOVERNANCE.md

### Acceptance Criteria
- Promotion requires baseline comparison, scorecard evidence, green CI, QA signoff, owner approval.
- Promoted changes are small, reversible, and documented.
- Rollback is defined before promotion.

### Risks
- Promoting interesting work instead of proven work.

### Owners
- Lead: ci-publisher
- Review: queen-ctoa, qa-safety, pm-roadmap
