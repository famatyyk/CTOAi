---
description: "Check CTOA Wave-1 readiness for a sprint by running the standard validation chain and summarizing blockers, evidence, and next action. Use for sprint QA gates, release readiness triage, or pre-approval checks."
name: "CTOA Sprint Wave-1 Readiness"
argument-hint: "Sprint number or task label, for example: Sprint-040"
agent: "agent"
---
Assess Wave-1 readiness for the provided sprint or validation target in this repository.

Use the repo conventions from [.github/copilot-instructions.md](../copilot-instructions.md), with special attention to [runner governance instructions](../instructions/runner-governance.instructions.md) when governance or gate semantics are involved.

Workflow:
- Identify the most relevant task chain in [.vscode/tasks.json](../../.vscode/tasks.json). Prefer the existing `CTOA: Sprint-XXX Wave-1 Run` task when it matches the requested sprint.
- If no direct Wave-1 task exists, use the canonical sequence: `CTOA: Run All Tests`, matching `CTOA: Sprint-XXX Validate ...`, then `CTOA: Launch Pack`.
- Run the minimum necessary commands/tasks to determine readiness.
- Do not modify code unless the user explicitly asks for a fix.
- If a check fails, isolate the failing step and summarize the blocker precisely.
- If core or governance files are implicated, call out whether [scripts/ops/core_guard.py](../../scripts/ops/core_guard.py) verification is relevant.

Return format:
- `Verdict:` PASS, FAIL, or BLOCKED
- `Executed:` the tasks or commands actually used
- `Blockers:` concrete failing checks, if any
- `Evidence:` artifact paths, task names, or logs that support the verdict
- `Next action:` the shortest practical next step