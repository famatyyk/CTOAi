---
description: "Use when editing runner orchestration, CI gate policy, sprint workflows, approval states, task status transitions, or release governance rules. Covers state-machine safety, deterministic evidence, validators, and atomic runtime updates."
name: "Runner Governance Guidelines"
applyTo:
  - "runner/**"
  - "policies/**"
  - "workflows/**"
---
# Runner Governance Guidelines

- Preserve the canonical status flow: `NEW -> IN_PROGRESS -> IN_QA -> IN_CI_GATE -> WAITING_APPROVAL -> RELEASED|BLOCKED`.
- Do not change transition semantics, approval meaning, or gate ordering unless the task explicitly requires it.
- Keep runner and governance changes deterministic and auditable; avoid hidden side effects, implicit fallbacks, or non-repeatable gate decisions.
- Preserve existing atomic write patterns for runtime state and evidence files.
- Keep boundaries clear: orchestration in `runner/`, policy contracts in `policies/`, sprint/backlog definitions in `workflows/`.
- If execution semantics change, update the narrowest relevant tests and validators rather than refactoring unrelated modules.
- Prefer workspace tasks from `.vscode/tasks.json` for validation, especially `CTOA: Run All Tests`, the relevant `CTOA: Sprint-XXX Validate ...`, and `CTOA: Launch Pack`.
- If protected assets are intentionally changed, verify `python scripts/ops/core_guard.py --check` and update the manifest with `python scripts/ops/core_guard.py --update` in the same change set.
- Link to the canonical docs instead of restating process detail: `docs/ARCHITECTURE.md`, `docs/SPRINT_GOVERNANCE.md`, `docs/CORE_GUARDRAILS.md`, and `docs/VALIDATION_CHECKLIST.md`.