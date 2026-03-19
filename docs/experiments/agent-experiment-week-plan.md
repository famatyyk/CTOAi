# 7-Day Agent Experiment Week Plan

This plan uses the active 10-agent roster from [agents/ctoa-agents.yaml](agents/ctoa-agents.yaml). The goal is to run a bounded experiment week without weakening the delivery lane.

## Week Rules
1. Maximum 2 active experiments at the same time.
2. Every experiment must have a baseline and scorecard.
3. Every day ends with a go, hold, or kill decision.
4. Nothing moves into the release lane without green CI and owner approval.

## Agent Roster
1. `queen-ctoa`
2. `pm-roadmap`
3. `prompt-forge`
4. `tool-advisor`
5. `mmo-intel`
6. `lua-scripter`
7. `bot-architect`
8. `builder-engine`
9. `qa-safety`
10. `ci-publisher`

## Day 1: Frame and Baseline
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Open experiment lane and define daily decision cadence | Decision frame |
| `pm-roadmap` | Choose 3 candidate experiments and rank them | Experiment shortlist |
| `prompt-forge` | Capture baseline prompts for planning and coding tasks | Baseline prompt set |
| `tool-advisor` | Capture current tool routing baseline | Routing baseline |
| `mmo-intel` | Provide external context and domain risk inputs | Domain risk brief |
| `lua-scripter` | Identify Lua-specific experiment opportunities | Candidate task list |
| `bot-architect` | Identify architecture-sensitive change zones | Architecture constraint note |
| `builder-engine` | Prepare isolated implementation path for experiments | Sandbox implementation plan |
| `qa-safety` | Define validation checks and failure thresholds | QA guardrail note |
| `ci-publisher` | Confirm release lane boundaries and promotion blockers | Release gate checklist |

## Day 2: Ownership and Routing
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Approve top 2 experiments for execution | Go list |
| `pm-roadmap` | Map owners and deadlines | Assignment matrix |
| `prompt-forge` | Draft challenger prompt variants | Prompt variant set |
| `tool-advisor` | Draft challenger routing variants | Tool routing variants |
| `mmo-intel` | Validate experiment relevance against live domain needs | Relevance brief |
| `lua-scripter` | Select code-oriented test cases | Lua task pack |
| `bot-architect` | Review routing impact on system complexity | Architecture review |
| `builder-engine` | Prepare implementation hooks for experiments | Execution setup |
| `qa-safety` | Prepare baseline validation suite | Validation baseline |
| `ci-publisher` | Define what evidence is required for promotion | Evidence gate |

## Day 3: Prompt Experiment Run
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Keep scope tight and reject side quests | Scope decisions |
| `pm-roadmap` | Track experiment state and blockers | Daily board update |
| `prompt-forge` | Run baseline vs challenger prompt tests | Prompt test report |
| `tool-advisor` | Observe tool usage impact from prompt changes | Tool usage notes |
| `mmo-intel` | Judge domain adequacy of outputs | Domain quality note |
| `lua-scripter` | Review code quality from prompt variants | Code quality review |
| `bot-architect` | Review structure and maintainability | Architecture delta note |
| `builder-engine` | Reproduce generated implementation path | Reproducibility note |
| `qa-safety` | Score failures and risk regressions | Safety score |
| `ci-publisher` | Flag anything that cannot be promoted even if it looks good | Promotion blockers |

## Day 4: Tool Routing Experiment Run
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Decide whether experiment 2 continues unchanged | Continue or rescope |
| `pm-roadmap` | Compare expected vs actual effort | Effort delta note |
| `prompt-forge` | Hold prompts stable to isolate routing change | Prompt freeze note |
| `tool-advisor` | Run routing comparison | Routing comparison report |
| `mmo-intel` | Identify domain blind spots introduced by routing | Blind spot note |
| `lua-scripter` | Check whether routing helps or hurts task output | Task outcome note |
| `bot-architect` | Evaluate complexity and coupling risk | Coupling risk note |
| `builder-engine` | Measure implementation overhead | Overhead report |
| `qa-safety` | Score risk and error patterns | QA delta report |
| `ci-publisher` | Check what would survive release gates | Release readiness note |

## Day 5: Hard Cut Review
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Force go, hold, or kill decision on each experiment | Decision log |
| `pm-roadmap` | Remove weak experiments from the active queue | Updated backlog |
| `prompt-forge` | Summarize winning or losing prompt patterns | Prompt lessons |
| `tool-advisor` | Summarize winning or losing routing patterns | Routing lessons |
| `mmo-intel` | Note domain-specific constraints for next round | Domain constraints |
| `lua-scripter` | Flag code paths worth promoting | Promotion candidates |
| `bot-architect` | Identify which changes are safe to absorb | Architecture go or no-go |
| `builder-engine` | Package the strongest candidate changes | Candidate implementation bundle |
| `qa-safety` | Decide if any candidate is too risky to continue | QA kill list |
| `ci-publisher` | Decide which candidate can enter promotion prep | Promotion shortlist |

## Day 6: Harden Winners
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Confirm winner scope for hardening | Harden scope |
| `pm-roadmap` | Lock next-day decision target | Final review agenda |
| `prompt-forge` | Stabilize prompt assets for the winner | Stable prompt package |
| `tool-advisor` | Lock any routing changes selected | Stable routing package |
| `mmo-intel` | Verify winner still matches live domain needs | Final relevance check |
| `lua-scripter` | Re-run code-oriented checks | Code verification note |
| `bot-architect` | Check maintainability and rollback simplicity | Maintainability note |
| `builder-engine` | Prepare minimal promotable change set | Promotion-ready patch set |
| `qa-safety` | Re-run validation and confirm reproducibility | Final QA report |
| `ci-publisher` | Confirm required evidence is complete | Release evidence bundle |

## Day 7: Promotion Decision
| Agent | Assignment | Output |
|-------|------------|--------|
| `queen-ctoa` | Make final promote or defer decision | Final decision memo |
| `pm-roadmap` | Convert winners into next backlog candidates | Backlog update |
| `prompt-forge` | Archive usable prompt deltas | Prompt archive |
| `tool-advisor` | Archive usable routing deltas | Routing archive |
| `mmo-intel` | Capture domain lessons | Domain learning note |
| `lua-scripter` | Prepare handoff notes for implementation | Implementation handoff |
| `bot-architect` | Confirm long-term fit | Fit assessment |
| `builder-engine` | Prepare the smallest safe adoption slice | Adoption slice |
| `qa-safety` | Provide final pass or fail recommendation | Final QA gate |
| `ci-publisher` | Confirm release-lane readiness and owner approval path | Promotion gate status |

## End-of-Week Outputs
1. One final decision memo per experiment.
2. One completed scorecard per day per active experiment.
3. A kill list with reasons.
4. A shortlist of 1 or 2 promotable winners.

## Final Week Wrap-Up (2026-03-20)
- Status: experiment week closed.
- `EXP-001`: promoted and retained after monitoring window closure (`T+1h`, `T+6h`, `T+24h`) with stable outcome.
- `EXP-002`: archived; lane stays closed.

### Backlog Carry-Over From EXP-002
1. Add strict complexity-budget gate before Day 2 in any routing experiment.
2. Require measurable and repeatable retry reduction as a continuation gate.

### Next-Cycle Opening Rule
- Do not open a new experiment candidate in this cycle.
- Open the next candidate only in the next cycle, with a fresh hypothesis and explicit baseline.