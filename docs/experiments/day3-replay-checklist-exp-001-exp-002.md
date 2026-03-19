# Day 3 Replay Checklist - EXP-001 and EXP-002

Use this checklist during Day 3 execution.

## Common Replay Controls
- [ ] Same task sample family as Day 2, with expanded volume.
- [ ] Fixed evaluator roles per run.
- [ ] Run IDs and timestamps captured.
- [ ] No mixed variable changes across baseline and challenger.
- [ ] QA review attached to every replay batch.

## EXP-001 Prompt Quality Lift (Replay)

### Replay Setup
- [ ] Day 2 challenger prompt retained as candidate baseline.
- [ ] Expanded sample set selected.
- [ ] Quality rubric fixed before run.

### Replay Execution
- [ ] Run batch 1 executed.
- [ ] Run batch 2 executed.
- [ ] Cost, quality, operator load recorded.

### Replay Validation
- [ ] Quality gain still present.
- [ ] Safety confidence unchanged or improved.
- [ ] Reproducibility confirmed.

### Day 3 Decision Gate
- [ ] Promote candidate if stable gain persists.
- [ ] Hold if signal weakens.
- [ ] Kill if regression appears.

## EXP-002 Tool Routing Efficiency (Rescoped Replay)

### Rescope Setup
- [ ] Complexity-heavy routing branch removed.
- [ ] New variant documented.
- [ ] Same baseline retained for comparison.

### Replay Execution
- [ ] Retry metrics captured.
- [ ] Cycle-time metrics captured.
- [ ] Quality and safety deltas captured.

### Replay Validation
- [ ] Retry or cycle-time gain is consistent.
- [ ] No quality drift.
- [ ] Complexity budget passes architecture review.

### Day 3 Decision Gate
- [ ] Go if gains hold without regressions.
- [ ] Hold if partial signal persists.
- [ ] Kill if tradeoff remains unfavorable.
