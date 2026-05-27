# CTOA Sprint Governance Framework

**Document Updated:** 2026-05-25T00:00:00+00:00

## Overview

This document standardizes sprint execution, approval gates,
and rollover procedures for the CTOA AI Toolkit.

## Sprint Lifecycle

### Release-Train Short Sprint Mode (3-Day Window)

For active release-train micro-sprints (for example Sprint-058), use this compressed cadence:

- Day 1: kickoff + scope lock + doc reference sync
- Day 2: run non-interactive Wave-1 chain and publish artifacts
- Day 3: finalize approvals/handoff or carry unresolved items forward

This mode keeps the canonical state flow unchanged and only compresses schedule length.

### Phase 1: Planning & Kickoff (Day 1)

- Create new backlog file: `workflows/backlog-sprint-NNN.yaml`
- Create Sprint documentation: `SPRINT-NNN.md`
- Create sprint progress snapshot: `SPRINT-NNN-PROGRESS.md`
- Wire validator, local task, and CI gate entries for the sprint
- Update README.md with active sprint status and current release train
- Git commit: "chore: kickoff Sprint-NNN"

### Phase 2: Execution (Days 2-13)

- Run the Wave-1 chain for the sprint: tests, validator, launch gate, state sync dry-run, state sync, repo hygiene, core guard, progress refresh, wave summary
- AI agents execute tasks and generate deliverables
- State transitions: NEW -> IN_PROGRESS -> IN_QA -> IN_CI_GATE -> WAITING_APPROVAL
- Evidence-first approvals: no task moves to RELEASED without the validator and release evidence pack

### Phase 3: Closure & Validation (Day 14)

- Final approval of all remaining tasks
- Generate final report: 100% completion check plus evidence pack verification
- Update sprint documentation with closure timestamp and handoff notes
- Backup previous sprint state: `task-state-sprint-NNN-closed.yaml`

### Phase 4: Rollover & Next Planning

- Switch backlog: update `CTOA_BACKLOG_FILE` env var on VPS
- Refresh `runtime/task-state.yaml` through `sprint_state_sync.py`
- Refresh progress and wave summary artifacts for the new backlog
- Restart systemd timers: `sudo systemctl restart ctoa-runner.timer`
- Verify new backlog loads and state re-initializes
- Update README.md roadmap with next sprint or archive note

## Approval Gates

### Release Policy

All tasks require manual approval before transitioning to RELEASED state.

**Gate Conditions:**

1. Task must be in `WAITING_APPROVAL` status
2. All deliverables must exist and be valid
3. Wave-1 evidence pack must be complete (`tests`, validator, launch gate, state sync, repo hygiene, core guard, wave summary)
4. No blocking issues reported
5. Definition of Done checklist verified

**Approval Command:**

```bash
CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-NNN.yaml \
  python3 runner/runner.py approve --task CTOA-NNN
```

### Sprint Close Gate

Sprint cannot be marked CLOSED until:

1. All tasks in the current backlog are in RELEASED status
2. No tasks in WAITING_APPROVAL or earlier states
3. Final report shows 100% progress
4. Sprint documentation updated with closure timestamp and release evidence links

### Wave Quality Gates (Training-Aware)

Gate intent:

- **Wave-1:** automated quality and evidence completeness
- **Wave-2:** manual release approval with accountability

**Wave-1 PASS requires:**

1. Validator/test chain passes or has documented non-blocking exception
2. No critical regression flags
3. Evidence pack is complete: output artifacts, validator/test results, baseline delta (quality/cost/latency), state sync evidence, repo hygiene and core guard results, risk note + fallback path

**Wave-2 PASS requires:**

1. Owner/reviewer sign-off on release fitness
2. Decision log record with timestamp and rationale
3. Confirmation that promotion criteria are met for any skill update

### PR Quality Gate Requirement (CTOA-208)

Default promotion path to `main` is pull-request based.
Required status checks for merge:

1. `PR Quality Report`
2. `CTOA Pipeline`

Direct pushes to `main` are reserved for documented incident recovery only.

### Bypass Exception Protocol (DEFCON 1-2 only)

1. STRATEGOS/owner records explicit decision note with timestamp.
2. Include reason, impacted scope, and rollback path in sprint evidence.
3. Run local test + sprint validator evidence before bypass push.
4. Open backfill PR within 24h to restore auditable review trail.

Canonical definitions:

- [Enhanced Agent/Prompt Definitive](./AGENT_PROMPT_DEFINITIVE.md)
- [Agent Training Masterplan](./AGENT_TRAINING_MASTERPLAN.md)

## Backlog Rollover Procedure

**Pre-Rollover:**

1. Final sprint report: 100% completion
2. Backup current state: `cp task-state.yaml task-state-sprint-NNN-closed.yaml`
3. Refresh progress and summary artifacts
4. Verify git working directory clean: `git status`
5. Commit final sprint documentation

**Rollover Steps:**

1. Update VPS environment:
  `echo 'CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-MMM.yaml' >> /opt/ctoa/.env`
2. Pull latest backlog: `cd /opt/ctoa && git pull origin main`
3. Verify backlog file exists: `test -f workflows/backlog-sprint-MMM.yaml`
4. Dry-run state sync: `python scripts/ops/sprint_state_sync.py --backlog workflows/backlog-sprint-MMM.yaml --state runtime/task-state.yaml --dry-run`
5. Apply state sync: `python scripts/ops/sprint_state_sync.py --backlog workflows/backlog-sprint-MMM.yaml --state runtime/task-state.yaml`
6. Refresh progress diagram: `python scripts/ops/project_progress_diagram.py --backlog workflows/backlog-sprint-MMM.yaml --state runtime/task-state.yaml --output docs/history/sprints/SPRINT-MMM-PROGRESS.md --project-name Sprint-MMM`
7. Verify state reset and NEW tasks loaded: `python3 runner/runner.py report`

**Validation:**

- Check `task-state.yaml` has new `backlog_id`
- All old tasks should be gone
- All new tasks (CTOA-XXX) in state
- `last_tick_at` recently updated
- Progress snapshot and wave summary reflect the new backlog

**Resume Operations:**

1. Restart VPS timers: `sudo systemctl restart ctoa-runner.timer ctoa-report.timer`
2. Enable agents: existing systemd service will auto-invoke with `--agents` flag
3. Monitor live status: GitHub Issue #1

## Task State Machine

```text
NEW
  -> IN_PROGRESS (planner or wave kickoff)
IN_PROGRESS
  -> IN_QA (task complete)
IN_QA
  -> IN_CI_GATE (quality gate pass)
IN_CI_GATE
  -> WAITING_APPROVAL (release evidence complete)
WAITING_APPROVAL
  -> RELEASED (manual approve --task CTOA-NNN)
RELEASED

BLOCKED (manual: block_task with reason)
  -> IN_PROGRESS (manual unblock_task)
IN_PROGRESS (resume)
```

## Agent Execution Policy

Agents are automatically invoked when tasks transition to IN_PROGRESS:

- Track A agents: Documentation (runbooks, checklists)
- Track B agents: KPI Automation (metrics, reports)
- Track C agents: Reliability (drift detection, health checks)
- Track D agents: Governance (procedures, templates)

**Agent Output:**

- All deliverables written to workspace
- Execution logged in task history
- Failed agents must be manually addressed (blocking issue)
- Successful agents update task state automatically
- Release evidence and summary artifacts must remain auditable

## Metrics & Reporting

### Weekly Report

- Generated every Sunday via `ctoa-report.timer`
- Published to GitHub Topic #1
- Includes:
  - Sprint progress percentage
  - Task status distribution
  - Approval lead-time metrics
  - Wave-1 evidence completeness
  - State sync and repo hygiene status
  - Top blockers (if any)
  - Health trend data

### Sprint Report

- Generated at sprint close
- Final counts (Released/Total)
- Timeline (Start/End/Duration)
- Agent execution summary
- Blockers and escalations (if any)
- Wave-1/Wave-2 pass ratio
- Release evidence links and validation summary
- Training-event and promotion summary

## Escalation & Issue Management

### Critical Issues (DEFCON 1-2)

- Immediate escalation to user
- Hold sprint pending decision
- Document decision and rationale
- Resume after decision documented

### Standard Issues

- Logged as BLOCKED task
- Assigned to responsible track
- Scheduled for next sprint if unresolved

### Release Blockers

- No task can be RELEASED if BLOCKED
- Block reason must be documented
- Resolution required before approval

## Template: Sprint Governance Review

**Every 3 Days - Sprint Health Check:**

```text
- How many tasks are RELEASED? (should be 25%-50%-75%-100%)
- Any tasks stuck in IN_QA or IN_CI_GATE? (check for automation failures)
- Agents executing successfully? (check runner logs)
- Any escalations or blockers? (document and decide)
```

## Documentation Governance Checklist

### Definition of Ready (DoR)

- Terms align with the canonical glossary (Agent, Prompt Forge, Tool Advisor, Wave-1/Wave-2)
- Target KPI and promotion criteria are explicit
- Required evidence sources are identified

### Definition of Done (DoD)

- Linked docs are synchronized and non-conflicting
- Gate impact is documented (Wave-1/Wave-2)
- Validation checklist links are current

### Sprint Audit Cadence

- Run one documentation consistency audit at sprint closure
- Remove stale/duplicated instructions in favor of canonical links
- Record audit result in sprint report/release pack

## References

- [SPRINT-007.md](./history/sprints/SPRINT-007.md) Ă˘â‚¬â€ť Historical sprint example
- [runner.py](../runner/runner.py) Ă˘â‚¬â€ť Task orchestration engine
- [orchestrator.py](../runner/agents/orchestrator.py) Ă˘â‚¬â€ť Agent orchestration entrypoint
- [README.md](../README.md) Ă˘â‚¬â€ť Project roadmap
- [Enhanced Agent/Prompt Definitive](./AGENT_PROMPT_DEFINITIVE.md)
- [Agent Training Masterplan](./AGENT_TRAINING_MASTERPLAN.md)
- [Validation Checklist](./VALIDATION_CHECKLIST.md)
