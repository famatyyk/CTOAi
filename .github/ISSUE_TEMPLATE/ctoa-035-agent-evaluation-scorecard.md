---
name: "CTOA-035 Agent Evaluation Scorecard"
about: "Create a lightweight scorecard used to judge experiments consistently."
title: "CTOA-035: Agent Evaluation Scorecard"
labels: ["backlog", "experiment", "evaluation"]
assignees: []
---

## Objective
Introduce a lightweight, repeatable scorecard for evaluating agent experiments with evidence instead of intuition.

## Problem Statement
- Experiment decisions become noisy without a shared evaluation structure.
- The team needs a common scorecard for quality, speed, cost, and reproducibility.

## Deliverables
- Daily scorecard template
- Scoring rubric
- Baseline task sample guidance
- Decision thresholds for go, hold, and kill

## Scope
In scope:
- Quality metrics
- Cycle time and operator load
- Failure rate and reproducibility
- Cost awareness

Out of scope:
- Building a full metrics warehouse
- Long-term trend dashboards

## Dependencies
- [docs/experiments/daily-experiment-scorecard.md](docs/experiments/daily-experiment-scorecard.md)
- [docs/experiments/decision-memo-template.md](docs/experiments/decision-memo-template.md)

## Acceptance Criteria
- Every experiment can be scored on the same rubric.
- Baseline and challenger can be compared directly.
- Final decisions can reference scorecard evidence.

## Risks
- Scorecard being too heavy to use daily.
- Scorecard being too light to support decisions.

## Proposed Owners
- Lead: `evaluator`
- Review: `qa-safety`, `pm-roadmap`

## Definition of Done
- Scorecard is documented.
- Thresholds and examples are ready for daily use.
