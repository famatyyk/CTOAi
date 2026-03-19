---
name: "CTOA-037 Promotion Gate for Winning Experiments"
about: "Define how a winning experiment becomes a production-ready candidate."
title: "CTOA-037: Promotion Gate for Winning Experiments"
labels: ["backlog", "experiment", "release"]
assignees: []
---

## Objective
Define the promotion path that turns proven experiments into safe production candidates.

## Problem Statement
- Winning experiments need a consistent path to adoption.
- Promotion must not bypass QA, CI, documentation, or owner approval.

## Deliverables
- Promotion checklist
- Evidence bundle format
- Adoption threshold
- Rollback readiness rules

## Scope
In scope:
- Promotion criteria
- Required evidence
- QA and CI gates
- Rollback preparation

Out of scope:
- Automatic deployment of experiments
- Replacing manual owner approval

## Dependencies
- [docs/experiments/decision-memo-template.md](docs/experiments/decision-memo-template.md)
- [docs/VALIDATION_CHECKLIST.md](docs/VALIDATION_CHECKLIST.md)
- [docs/SPRINT_GOVERNANCE.md](docs/SPRINT_GOVERNANCE.md)

## Acceptance Criteria
- Promotion requires baseline comparison, scorecard evidence, green CI, QA signoff, and owner approval.
- Promoted changes are small, reversible, and documented.
- Failed promotions can be rolled back cleanly.

## Risks
- Promoting work that is interesting but not proven.
- Letting release pressure bypass experiment evidence.

## Proposed Owners
- Lead: `ci-publisher`
- Review: `queen-ctoa`, `qa-safety`, `pm-roadmap`

## Definition of Done
- Promotion gate is documented.
- Winning experiments can enter the release lane through a repeatable process.
