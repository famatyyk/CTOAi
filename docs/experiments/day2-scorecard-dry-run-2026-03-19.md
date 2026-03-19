# Day 2 Scorecard Dry Run - 2026-03-19

This is a sample filled scorecard to standardize how Day 2 evidence should be reported.

## Experiment Metadata
- Experiment ID: `EXP-001`
- Title: Prompt Quality Lift
- Date: 2026-03-19
- Owner: `prompt-forge`
- Reviewer: `qa-safety`
- Status: `running`

## Daily Snapshot
| Dimension | Score 1-5 | Evidence | Notes |
|-----------|-----------|----------|-------|
| Output quality | 4 | Challenger produced clearer task decomposition on 4/5 samples | Stronger structure, fewer missing steps |
| Task correctness | 4 | 5/5 outputs executable with minor edits | No critical correctness regressions |
| Cycle time | 3 | Similar average completion time | Neutral impact on speed |
| Operator load | 4 | Fewer manual rewrites in challenger runs | Estimated 20% lower correction overhead |
| Failure rate | 3 | 1 weak output in both baseline and challenger | No net change |
| Reproducibility | 4 | Replay consistency high across 2 runs | Stable behavior |
| Cost efficiency | 3 | Token usage slightly higher in challenger | Acceptable if quality gains persist |
| Safety confidence | 4 | No new unsafe patterns detected | QA signoff still required for promotion |

## Baseline vs Challenger
| Check | Baseline | Challenger | Winner | Notes |
|-------|----------|------------|--------|-------|
| Better result quality | Medium | High | Challenger | Better structure and clarity |
| Faster completion | Medium | Medium | Tie | No meaningful speed change |
| Lower operator effort | Medium | High | Challenger | Fewer correction loops |
| Lower failure risk | Medium | Medium | Tie | Same failure profile |
| Easier to repeat | Medium | High | Challenger | More stable formatting and flow |

## Daily Decision
- Continue: `yes`
- Promote candidate: `no`
- Kill candidate: `no`
- Why: Signal is positive but requires Day 3 replay and QA confirmation before promotion eligibility.

## Next Action
- What happens next: run second replay batch and collect comparative evidence on a wider sample.
- Who owns it: `prompt-forge` with `qa-safety` review.
- Deadline: Day 3 checkpoint.
