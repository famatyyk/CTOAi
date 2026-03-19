# Current Priority Map - 2026-03-19

## Purpose
This document is the single control view after a high-change day.
It defines what is active, what is frozen, what matters most, and what can run in parallel.

## Executive Summary
- Primary lane: secure and stabilize the website + mobile console control surface.
- Secondary lane: monitor published `EXP-001` outcome and keep release artifacts auditable.
- Controlled lane: experiment week is closed; next candidate is deferred to the next cycle.
- Frozen lane: `EXP-002` stays archived unless explicitly reopened.
- Support lane: CI guardrails are implemented and verified; no urgent new work unless regressions appear.

## Priority Levels

### P0 - Immediate Control And Safety
- Done:
  - owner/operator flows validated against the real backend on VPS
  - production env owner/operator credentials confirmed
  - owner-only endpoints reject operator actions with `403`
  - site can save/load admin settings through backend storage

### P1 - Product Surface Stabilization
- Finish website polish only where it improves usability directly.
- Keep current menu atlas positions for this sprint; dedicated extracted icons are not worth the churn right now.
- Parking Pomyslow is backend-backed with local fallback.
- Done:
  - mobile-device QA pass completed (Samsung Note 10+ class checks)
  - owner/operator touch workflows validated
  - no release-blocking mobile regressions found

### P2 - Release And Promotion Preparation
- `EXP-001` promotion path is complete and retained after monitoring (`T+1h`, `T+6h`, `T+24h`).
- Preserve evidence links, approvals, and rollback notes as audit-ready artifacts.
- Keep CI summaries and response guardrail regressions green.

### P3 - Deferred / Do Not Chase Now
- Do not reopen `EXP-002`.
- Do not start new visual rabbit holes unless they block usability.
- Do not broaden scope into unrelated tooling or new product surfaces.

## Current Project Lanes

### 1. Website + Admin UX
Status: active
Goal: role-aware public/admin site with backend-backed settings and usable visual identity.
Current state:
- local site is working
- Enter login bug fixed
- backend login/session integration exists
- menu sprites are stable enough for current sprint; extraction work deferred
- Parking Pomyslow syncs through backend when API session is active

### 2. Mobile Console API / Backend Security
Status: validated
Goal: owner/operator auth, role gates, backend settings persistence, production-safe CORS.
Current state:
- session login endpoints exist
- owner-only gates exist on mutating actions
- admin settings GET/PUT exists
- prod startup guard blocks wildcard CORS
- VPS validation passed for owner login, owner write, and operator `403` guard

### 3. CI / Guardrails
Status: monitor only
Goal: prevent bad response patterns and keep summaries visible in push/PR flows.
Current state:
- implemented
- tested
- verified in real push and pull_request runs
Action: no new feature work unless a regression appears

### 4. Experiments
Status: constrained
Goal: maintain decision clarity, not open-ended exploration.
Current state:
- `EXP-001` = published and stable
- `EXP-002` = archived
Action: do not open a new candidate in this cycle; open next only in the next cycle with a fresh hypothesis and baseline

### 5. VPS Observability / Runbooks
Status: healthy support lane
Goal: know where outputs, logs, runs, and artifacts live.
Current state:
- VPS output runbook exists
- mobile console docs link to it
Action: use as operational reference, no urgent new build work

## Freeze List
- Freeze new experiment starts in this cycle.
- Freeze broad site redesign ideas.
- Freeze low-value cosmetic iteration unless tied to clarity or trust.
- Freeze non-essential backend expansion unless it directly supports release-readiness.

## What To Do Next

### Next 1
Maintain release evidence and monitoring closure artifacts for `EXP-001`.

Success means:
- evidence bundle remains complete and linked
- approvals remain traceable (`qa-safety`, `ci-publisher`, `queen-ctoa`)
- rollback note remains attached and explicit
- no post-release regression signal

### Next 2
Carry forward 1-2 lessons from `EXP-002` as a deferred micro-experiment brief.

Reason:
- preserve archive value without reactivating the old lane
- keep experiment capacity focused on next-cycle decisions only

### Next 3
Open a new candidate only in the next cycle, with a clean hypothesis and explicit baseline.

## Parallelizable Work

### Safe To Run In Parallel
- promotion evidence collation
- approval collection and gate pre-check
- documentation cleanup and runbook refinement

### Should Stay Serial
- auth/security policy changes
- role permission changes
- release-lane decisions for `EXP-001`

## Recommended Delegation Model
- Agent A: release evidence audit and link integrity check
- Agent B: CI guardrail monitoring and regression triage only
- Agent C: docs consolidation, backlog carry-over, and next-cycle experiment brief prep

## Stop Conditions
- If owner/operator behavior is inconsistent, stop visual work and fix auth first.
- If prod env is not configured, stop release thinking and fix deployment config first.
- If CI guardrails regress, pause surface work and restore trust in the pipeline.

## Working Rule For Tomorrow
- One primary lane at a time.
- Maximum one secondary lane.
- Everything else is either frozen, delegated, or explicitly parked.

## Tomorrow Morning

### First 90 Minutes
1. Check VPS env configuration for production safety.
2. Validate owner login on real backend.
3. Validate operator login on real backend.
4. Confirm owner can save admin settings and read them back.
5. Confirm operator gets blocked from owner-only actions.
6. Record pass/fail in one short QA note before touching any new feature.

### Definition Of A Good Morning
- no auth ambiguity
- no role ambiguity
- no CORS ambiguity
- one written QA result confirming what works and what does not

## Delegate To Agents

### Agent A - VPS QA
Scope:
- closed
Deliverable:
- short checklist with pass/fail and blockers only

### Agent B - UI Assets
Scope:
- keep current atlas approach unless device QA shows a readability issue
Deliverable:
- clear recommendation only

### Agent C - Docs / Control Surface
Scope:
- tighten docs so auth, env, and site/backend flow are easy to recover later
- keep one operational index of the important runbooks and control docs
Deliverable:
- updated control docs with no duplicated stale guidance

## Remove From Head For Now
- new experiments
- reopening `EXP-002`
- broad redesign ideas for the site
- non-essential animation or styling tweaks
- new backend capability outside auth, settings, and validation
- anything that does not improve control, trust, or deployment readiness

## Week Closure Snapshot
- Experiment week status: closed.
- `EXP-001`: published and stable after checkpointed monitoring.
- `EXP-002`: archived with lessons moved to deferred backlog candidate.
- New experiment candidate: explicitly postponed to the next cycle.

## Decision Gate After Tomorrow Morning
- VPS QA passed and mobile QA passed: proceed with `EXP-001` promotion prep and gate review.