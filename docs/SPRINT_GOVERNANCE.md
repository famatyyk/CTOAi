# CTOA Sprint Governance Framework

**Document Updated:** 2026-03-12T20:05:12+00:00

## Overview

This document standardizes sprint execution, approval gates, and rollover procedures for the CTOA AI Toolkit.

## Sprint Lifecycle

### Phase 1: Planning & Kickoff (Day 1)
- Create new backlog file: `workflows/backlog-sprint-NNN.yaml`
- Create Sprint documentation: `SPRINT-NNN.md`
- Update README.md with active sprint status
- Git commit: "chore: kickoff Sprint-NNN"

### Phase 2: Execution (Days 2-13)
- Daily tick cycles via `runner.py tick --agents`
- AI agents execute tasks and generate deliverables
- State transitions: NEW → IN_PROGRESS → IN_QA → IN_CI_GATE → WAITING_APPROVAL
- Wave-based approvals (typically 3 tasks per wave, ~25% increment)

### Phase 3: Closure & Validation (Day 14)
- Final approval of all remaining tasks
- Generate final report: 100% completion check
- Update sprint documentation with closure timestamp
- Backup previous sprint state: `task-state-sprint-NNN-closed.yaml`

### Phase 4: Rollover & Next Planning
- Switch backlog: update `CTOA_BACKLOG_FILE` env var on VPS
- Restart systemd timers: `sudo systemctl restart ctoa-runner.timer`
- Verify new backlog loads and state re-initializes
- Update README.md roadmap with next sprint

## Approval Gates

### Release Policy
All tasks require manual approval before transitioning to RELEASED state.

**Gate Conditions:**
1. Task must be in `WAITING_APPROVAL` status
2. All deliverables must exist and be valid
3. No blocking issues reported
4. Definition of Done checklist verified

**Approval Command:**
```bash
CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-NNN.yaml \
  python3 runner/runner.py approve --task CTOA-NNN
```

### Sprint Close Gate
Sprint cannot be marked CLOSED until:
1. All tasks (10/10) are in RELEASED status
2. No tasks in WAITING_APPROVAL or earlier states
3. Final report shows 100% progress
4. Sprint documentation updated with closure timestamp

## Backlog Rollover Procedure

**Pre-Rollover:**
1. Final sprint report: 100% completion
2. Backup current state: `cp task-state.yaml task-state-sprint-NNN-closed.yaml`
3. Verify git working directory clean: `git status`
4. Commit final sprint documentation

**Rollover Steps:**
1. Update VPS environment: `echo 'CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-MMM.yaml' >> /opt/ctoa/.env`
2. Pull latest backlog: `cd /opt/ctoa && git pull origin main`
3. Verify backlog file exists: `test -f workflows/backlog-sprint-MMM.yaml`
4. Control tick (no agents): `python3 runner/runner.py tick`
5. Verify state reset and NEW tasks loaded: `python3 runner/runner.py report`

**Validation:**
- Check `task-state.yaml` has new `backlog_id`
- All old tasks should be gone
- All new tasks (CTOA-XXX) in state
- `last_tick_at` recently updated

**Resume Operations:**
1. Restart VPS timers: `sudo systemctl restart ctoa-runner.timer ctoa-report.timer`
2. Enable agents: existing systemd service will auto-invoke with `--agents` flag
3. Monitor live status: GitHub Issue #1

## Task State Machine

```
NEW
  ↓ (tick: scheduled_by_planner)
IN_PROGRESS (2 ticks)
  ↓ (auto transition)
IN_QA (1 tick)
  ↓ (auto transition)
IN_CI_GATE (1 tick)
  ↓ (auto transition)
WAITING_APPROVAL
  ↓ (manual: approve --task CTOA-NNN)
RELEASED

BLOCKED (manual: block_task with reason)
  ↓ (manual: unblock_task)
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

## Metrics & Reporting

### Weekly Report
- Generated every Sunday via `ctoa-report.timer`
- Published to GitHub Topic #1
- Includes:
  - Sprint progress percentage
  - Task status distribution
  - Approval lead-time metrics
  - Top blockers (if any)
  - Health trend data

### Sprint Report
- Generated at sprint close
- Final counts (Released/Total)
- Timeline (Start/End/Duration)
- Agent execution summary
- Blockers and escalations (if any)

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
```
- How many tasks are RELEASED? (should be 25%-50%-75%-100%)
- Any tasks stuck in IN_QA or IN_CI_GATE? (check for automation failures)
- Agents executing successfully? (check runner logs)
- Any escalations or blockers? (document and decide)
```

## References

- [SPRINT-007.md](SPRINT-007.md) — Current sprint plan
- [runner.py](runner/runner.py) — Task orchestration engine
- [agents.py](runner/agents.py) — AI agent executors
- [README.md](README.md) — Project roadmap

