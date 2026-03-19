---
name: "CTOA-031 Experiment Charter and Guardrails"
about: "Define the bounded experimentation lane, rules, and stop conditions."
title: "CTOA-031: Experiment Charter and Guardrails"
labels: ["backlog", "experiment", "governance"]
assignees: []
---

## Objective
Define the operating rules for running bounded agent experiments without weakening the delivery lane.

## Problem Statement
- Experiments are currently possible, but not formally separated from production delivery.
- The repo needs clear rules for hypothesis, evidence, kill criteria, and promotion.

## Deliverables
- Experiment charter
- Allowed experiment categories
- Stop conditions and rollback rules
- Daily review protocol
- Evidence requirements for promotion

## Scope
In scope:
- Experiment governance
- Approval boundaries
- Kill or continue logic
- Required measurements

Out of scope:
- Implementing a new agent runner
- Reworking CI release flow
- Broad process redesign outside the experiment lane

## Dependencies
- [docs/operating-model.md](docs/operating-model.md)
- [docs/SPRINT_GOVERNANCE.md](docs/SPRINT_GOVERNANCE.md)
- [docs/experiments/decision-memo-template.md](docs/experiments/decision-memo-template.md)
- [docs/experiments/daily-experiment-scorecard.md](docs/experiments/daily-experiment-scorecard.md)

## Acceptance Criteria
- Every experiment must declare hypothesis, owner, timebox, metric, and rollback path.
- The experiment lane is explicitly separated from the release lane.
- Every experiment ends with one of: promote, hold, kill.
- Promotion requires evidence, green CI, QA signoff, and owner approval.

## Risks
- Overdesigning policy and slowing execution.
- Letting experiments bypass existing safety and approval gates.

## Proposed Owners
- Lead: `queen-ctoa`
- Review: `pm-roadmap`, `qa-safety`, `ci-publisher`

## Definition of Done
- Charter is merged.
- Review loop is documented.
- Promotion and kill rules are visible to all agents.
