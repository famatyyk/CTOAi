---
name: "CTOA-036 Daily Experiment Review Loop"
about: "Create the daily review loop that forces continue, kill, or promote decisions."
title: "CTOA-036: Daily Experiment Review Loop"
labels: ["backlog", "experiment", "operations"]
assignees: []
---

## Objective
Build a disciplined daily loop that keeps experiment work bounded, visible, and decisive.

## Problem Statement
- Experiments decay into background noise without daily decisions.
- The team needs a small operating loop with clear state transitions.

## Deliverables
- Daily review format
- Experiment state labels
- Decision journal structure
- Rules for stale experiment cleanup

## Scope
In scope:
- Daily review cadence
- Continue, kill, promote outcomes
- State transitions

Out of scope:
- Replacing sprint ceremonies
- Adding large governance overhead

## Dependencies
- [docs/experiments/daily-experiment-scorecard.md](docs/experiments/daily-experiment-scorecard.md)
- [docs/experiments/decision-memo-template.md](docs/experiments/decision-memo-template.md)
- [docs/experiments/agent-experiment-week-plan.md](docs/experiments/agent-experiment-week-plan.md)

## Acceptance Criteria
- Every running experiment gets a daily status.
- Each review ends in a concrete decision.
- Stale experiments older than 48 hours are killed or rescoped.

## Risks
- Review loop turning into status theater.
- Too many concurrent experiments diluting signal quality.

## Proposed Owners
- Lead: `queen-ctoa`
- Review: `pm-roadmap`, `qa-safety`, `ci-publisher`

## Definition of Done
- Loop is documented and ready to run.
- Decision states are standardized.
