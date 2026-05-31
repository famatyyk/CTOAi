# Sprint-067 Plan - 3 Day Execution Window

Status: IN_PROGRESS
Theme: Sprint-067 AI-layer consolidation + prompt/runtime governance
Window: 2026-06-16 -> 2026-06-18
Backlog: workflows/backlog-sprint-067.yaml
Flow: workflows/sprint-067-delivery-flow.yaml

## Sprint Mission

Sprint-067 turns the recent AI-layer fixes into a governed baseline:
- one canonical agent registry,
- one runtime prompt contract without reasoning-labelled execution sections,
- clear documentation of which prompt surfaces are live, canonical, or workflow-specific.

## Task Matrix

| Task ID | Title | Owner | Support | Exit Signal |
| --- | --- | --- | --- | --- |
| CTOA-332 | Canonical AI registry and runtime contract consolidation | strategos | core-architect, code-smith | one registry feeds runtime and tests |
| CTOA-333 | BRAVE prompt runtime alignment | prompt-forge | code-smith, qa-terminator | prompt runtime uses analysis-oriented sections with passing guardrails |
| CTOA-334 | Prompt surface and governance boundary documentation | documentation-sage | strategos | docs distinguish canonical, live, and workflow-specific surfaces |

## KPI Contract

- Architecture KPI: runtime AI registry has a single source of truth with automated consistency validation.
- Runtime KPI: BRAVE prompt components stay guardrail-compliant without reasoning-labelled runtime sections.
- Governance KPI: docs remove ambiguity about which prompt and instruction layers actually control execution.

## Definition of Done

- Agent registry duplication is removed from runtime code paths.
- BRAVE runtime components use non-reasoning execution section names with legacy compatibility where required.
- Guardrail and agent framework regression tests pass.
- Docs explain canonical vs live prompt surfaces without conflicting guidance.
- Sprint has validator, progress doc, and evidence chain like prior sprints.
