---
name: ci-hotfix-workflow
description: 'Diagnose and stabilize failing CI, PR quality, build gates, validator failures, and post-merge regressions in CTOAi. Use for CI hotfixes, broken Wave-1 chains, gate remediation, and minimal-risk validation before merge.'
argument-hint: 'Branch, PR, failing task, or CI symptom'
user-invocable: true
disable-model-invocation: false
---

# CI Hotfix Workflow

## When To Use
- A pull request is red because a validator, quality gate, or build step failed.
- A post-merge or post-rebase regression broke the standard CTOA validation chain.
- You need the smallest safe fix to get CI green again without refactoring unrelated code.
- You need a compact summary of failure cause, fix scope, residual risk, and validation evidence.

## Workflow
1. Identify the failing gate precisely.
   - Prefer the exact failing task, validator, or test over broad repo-wide guesses.
   - Map the failure back to the relevant area: `runner/`, `policies/`, `workflows/`, `scripts/ops/`, or CI workflow files.

2. Reproduce with the narrowest reliable command.
   - Prefer workspace tasks from `.vscode/tasks.json`.
   - Use the smallest matching chain first: failing sprint validator, `CTOA: Run All Tests`, `CTOA: Check Update Gate`, or `CTOA: Launch Pack`.

3. Fix the root cause with minimal scope.
   - Preserve governance semantics and existing task flows.
   - Avoid opportunistic refactors while stabilizing CI.
   - Keep fixes auditable and deterministic.

4. Re-run the relevant validation chain.
   - Verify the specific failing check.
   - Then verify the nearest user-facing gate or Wave-1 chain if needed.

5. Summarize outcome for PR review.
   - State the concrete failure.
   - State the fix.
   - State what was revalidated.
   - Call out remaining risks or untested areas.

## CTOAi-Specific Rules
- Prefer task-first validation using `.vscode/tasks.json` before improvising custom command sequences.
- Preserve canonical status semantics: `NEW -> IN_PROGRESS -> IN_QA -> IN_CI_GATE -> WAITING_APPROVAL -> RELEASED|BLOCKED`.
- If protected files changed intentionally, include `python scripts/ops/core_guard.py --check` and update manifest only when required.
- For PowerShell and VPS-related CI failures, reuse `scripts/ops/ctoa-vps.ps1` helpers instead of inventing new remote command patterns.
- Treat `runtime/` as evidence/state, not a place for permanent source fixes.

## Output Format
- `Failure:` exact failing check or symptom
- `Root cause:` smallest verified cause
- `Fix applied:` minimal change made
- `Validation:` commands or tasks rerun
- `Risk:` remaining uncertainty, if any

## References
- [Workspace Instructions](../../copilot-instructions.md)
- [Runner Governance Instructions](../../instructions/runner-governance.instructions.md)
- [Ops PowerShell Safety](../../instructions/ops-powershell-safety.instructions.md)
- [Architecture](../../../docs/ARCHITECTURE.md)
- [Core Guardrails](../../../docs/CORE_GUARDRAILS.md)
- [Sprint Governance](../../../docs/SPRINT_GOVERNANCE.md)