---
name: "CTOA-033 BRAVE(R) Experiment Packs"
about: "Create repeatable prompt experiment packs for baseline vs challenger tests."
title: "CTOA-033: BRAVE(R) Experiment Packs"
labels: ["backlog", "experiment", "prompting"]
assignees: []
---

## Objective
Standardize prompt experiments so that prompt changes are measured instead of improvised.

## Problem Statement
- Prompt changes currently risk becoming ad hoc.
- We need a reusable pattern for baseline vs challenger comparisons.

## Deliverables
- 3 to 5 experiment pack templates
- Baseline vs challenger structure
- Prompt-specific evaluation rubric
- Failure mode checklist

## Scope
In scope:
- Prompt experiments for planning, coding, review, and analysis tasks
- Reusable test structure

Out of scope:
- Model provider changes
- Full evaluation infrastructure rollout

## Dependencies
- [prompts/braver-library.yaml](prompts/braver-library.yaml)
- [docs/experiments/daily-experiment-scorecard.md](docs/experiments/daily-experiment-scorecard.md)
- [docs/experiments/decision-memo-template.md](docs/experiments/decision-memo-template.md)

## Acceptance Criteria
- At least 3 prompt pack templates exist.
- Each template supports baseline vs challenger comparisons.
- Each result can be scored on quality, operator load, and reproducibility.

## Risks
- Prompt churn without measurable gains.
- Optimizing for style rather than outcome quality.

## Proposed Owners
- Lead: `prompt-forge`
- Review: `qa-safety`, `evaluator`

## Definition of Done
- Packs are documented and trial-ready.
- First pilot experiment can use them without inventing new structure.
