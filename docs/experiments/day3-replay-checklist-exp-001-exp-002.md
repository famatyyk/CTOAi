# Day 3 Replay Checklist - EXP-001 and EXP-002

Use this checklist during Day 3 execution.

## Common Replay Controls
- [x] Same task sample family as Day 2, with expanded volume.
- [x] Fixed evaluator roles per run.
- [x] Run IDs and timestamps captured.
- [x] No mixed variable changes across baseline and challenger.
- [x] QA review attached to every replay batch.

## EXP-001 Prompt Quality Lift (Replay)

### Replay Setup
- [x] Day 2 challenger prompt retained as candidate baseline.
- [x] Expanded sample set selected.
- [x] Quality rubric fixed before run.

### Replay Execution
- [x] Run batch 1 executed.
- [x] Run batch 2 executed.
- [x] Cost, quality, operator load recorded.

### Replay Validation
- [x] Quality gain still present.
- [x] Safety confidence unchanged or improved.
- [x] Reproducibility confirmed.

### Day 3 Decision Gate
- [x] Promote candidate if stable gain persists.
- [ ] Hold if signal weakens.
- [ ] Kill if regression appears.

## EXP-002 Tool Routing Efficiency (Rescoped Replay)

### Rescope Setup
- [x] Complexity-heavy routing branch removed.
- [x] New variant documented.
- [x] Same baseline retained for comparison.

### Replay Execution
- [x] Retry metrics captured.
- [x] Cycle-time metrics captured.
- [x] Quality and safety deltas captured.

### Replay Validation
- [ ] Retry or cycle-time gain is consistent.
- [ ] No quality drift.
- [x] Complexity budget passes architecture review.

### Day 3 Decision Gate
- [ ] Go if gains hold without regressions.
- [ ] Hold if partial signal persists.
- [x] Kill if tradeoff remains unfavorable.
