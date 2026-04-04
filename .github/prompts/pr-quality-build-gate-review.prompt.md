---
description: "Review a CTOAi branch or PR for quality-gate and build-gate risk. Use for CI hotfixes, PR stabilization, failing validation chains, and pre-merge review on branches such as fix/ci-post-merge-green."
name: "CTOA PR Quality Build Gate Review"
argument-hint: "Branch name, PR number, or failing gate summary"
agent: "agent"
---
Review the current CTOAi branch or the provided PR target with a code-review mindset focused on PR quality and build-gate risk.

Use findings-first output. Prioritize real regressions, gate failures, missing validation, and risky assumptions over style commentary.

Workflow:
- Inspect current changes and identify files most likely to affect CI, Wave-1, governance, tests, or launch gating.
- Reproduce the narrowest relevant failing or risky validation path using existing workspace tasks where possible.
- If the branch appears to be a CI hotfix, verify the smallest path to green before suggesting broader cleanup.
- Treat review as risk analysis first: bugs, build failures, validator drift, missing artifacts, broken task chains, and protected-file implications.
- Keep summaries brief after the findings.

Return format:
- `Findings:` ordered by severity, each with file path and concrete risk
- `Validation checked:` tasks, tests, or commands actually run
- `Residual risk:` what remains unverified or fragile
- `Merge view:` ready, not ready, or conditionally ready

References:
- [.github/copilot-instructions.md](../copilot-instructions.md)
- [runner governance instructions](../instructions/runner-governance.instructions.md)
- [ops PowerShell safety](../instructions/ops-powershell-safety.instructions.md)
- [ci-hotfix-workflow skill](../skills/ci-hotfix-workflow/SKILL.md)