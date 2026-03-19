---
name: "CTOA-032 Agent Capability Matrix and Routing Map"
about: "Map the 10 agents to experiment roles, ownership, and handoffs."
title: "CTOA-032: Agent Capability Matrix and Routing Map"
labels: ["backlog", "experiment", "agents"]
assignees: []
---

## Objective
Create a practical routing map that defines which agent leads, reviews, and escalates each experiment type.

## Problem Statement
- The repo has 10 active agents, but experiment ownership can become ambiguous.
- We need clear handoffs between planning, implementation, QA, and release.

## Deliverables
- Capability matrix for all 10 agents
- Primary and secondary roles
- Experiment routing map
- Escalation and handoff rules

## Scope
In scope:
- Ownership matrix
- Lead and reviewer mapping
- Escalation paths

Out of scope:
- Changing the base 10-agent roster
- Rewriting agent prompt packs

## Dependencies
- [agents/ctoa-agents.yaml](agents/ctoa-agents.yaml)
- [agents/definitions.py](agents/definitions.py)
- [docs/experiments/agent-experiment-week-plan.md](docs/experiments/agent-experiment-week-plan.md)

## Acceptance Criteria
- Every experiment type has a lead agent and a reviewer agent.
- No task category is left without clear ownership.
- Handoff rules are documented for prompt, tooling, implementation, QA, and release.

## Risks
- Role overlap causing duplicate work.
- Overly rigid mapping that blocks useful cross-agent collaboration.

## Proposed Owners
- Lead: `pm-roadmap`
- Review: `queen-ctoa`, `tool-advisor`, `qa-safety`

## Definition of Done
- Matrix is documented and approved.
- Routing rules are ready for use in the next experiment week.
