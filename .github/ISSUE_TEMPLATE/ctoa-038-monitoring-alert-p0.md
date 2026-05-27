---
name: "CTOA-038 Monitoring Alert P0"
about: "Escalate any non-passing workflow, gate, test, or deployment signal on main."
title: "[ALERT][P0][CTOAi/main] "
labels: ["alert", "p0", "monitoring", "main"]
assignees: []
---

## Detected
- Time UTC:
- Source event:
- Severity: P0

## Failure Signal
- Workflow or check name:
- Conclusion:
- Branch: main
- Commit SHA:
- Run URL:

## Impact
- Required process did not pass.
- Treat pipeline state as BLOCKED until recovery.

## Required Actions
1. Find root cause.
2. Prepare and push fix.
3. Rerun failed checks.
4. Update owner and ETA in this issue.

## Closure Criteria
- Two consecutive successful reruns for the same workflow and branch.
- No active blocked signal for this alert.
