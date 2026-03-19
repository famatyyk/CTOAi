# Current Priority Map - 2026-03-19

## Purpose
This document is the single control view after a high-change day.
It defines what is active, what is frozen, what matters most, and what can run in parallel.

## Executive Summary
- Primary lane: secure and stabilize the website + mobile console control surface.
- Secondary lane: validate the new auth, role, and backend settings flow on VPS.
- Controlled lane: experiments remain documented, but only `EXP-001` is promotion-prep relevant.
- Frozen lane: `EXP-002` stays archived unless explicitly reopened.
- Support lane: CI guardrails are implemented and verified; no urgent new work unless regressions appear.

## Priority Levels

### P0 - Immediate Control And Safety
- Verify owner/operator flows against the real backend on VPS.
- Confirm production env values are correct:
  - `CTOA_ENV=prod`
  - `CTOA_CORS_ORIGINS=<explicit origins only>`
  - `CTOA_OWNER_PASSWORD`
  - `CTOA_OPERATOR_PASSWORD`
- Validate that owner-only endpoints reject operator actions.
- Confirm the site can save/load admin settings through backend storage.

### P1 - Product Surface Stabilization
- Finish website polish only where it improves usability directly.
- Replace current menu sprite compromises with dedicated cleaned icons if needed.
- Decide whether Parking Pomyslow remains local-only or becomes backend-backed.
- Run one mobile-device QA pass for layout, drawer behavior, and admin workflow.

### P2 - Release And Promotion Preparation
- Keep `EXP-001` as the only experiment lane eligible for promotion prep.
- Package promotion evidence, QA criteria, and release-lane gate state.
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
- menu sprites are improved but still not final-quality UI assets

### 2. Mobile Console API / Backend Security
Status: active
Goal: owner/operator auth, role gates, backend settings persistence, production-safe CORS.
Current state:
- session login endpoints exist
- owner-only gates exist on mutating actions
- admin settings GET/PUT exists
- prod startup guard blocks wildcard CORS

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
- `EXP-001` = promotion candidate / prep lane
- `EXP-002` = archived
Action: do not split focus here until P0 and P1 are stable

### 5. VPS Observability / Runbooks
Status: healthy support lane
Goal: know where outputs, logs, runs, and artifacts live.
Current state:
- VPS output runbook exists
- mobile console docs link to it
Action: use as operational reference, no urgent new build work

## Freeze List
- Freeze new experiments.
- Freeze broad site redesign ideas.
- Freeze low-value cosmetic iteration unless tied to clarity or trust.
- Freeze non-essential backend expansion until auth validation is complete.

## What To Do Next

### Next 1
Run VPS validation for owner/operator flows end-to-end.

Success means:
- owner can log in, save settings, sync, and use protected actions
- operator can log in, read state, but is blocked from owner-only actions
- site and backend agree on saved settings

### Next 2
Make the asset decision for menu icons.

Choose one:
- keep current improved atlas positions for now
- or cut 4 dedicated icons from the sprite pack for cleaner UI

### Next 3
Decide storage model for Parking Pomyslow.

Choose one:
- local-only for private ideation
- backend-backed for multi-device continuity

## Parallelizable Work

### Safe To Run In Parallel
- VPS QA checklist execution
- icon extraction / asset cleanup
- documentation cleanup and runbook refinement

### Should Stay Serial
- auth/security policy changes
- role permission changes
- release-lane decisions for `EXP-001`

## Recommended Delegation Model
- Agent A: VPS QA and role validation
- Agent B: asset cleanup and dedicated icon extraction
- Agent C: docs consolidation and operational checklist maintenance

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
- execute owner/operator validation
- verify protected endpoints
- verify backend settings persistence
Deliverable:
- short checklist with pass/fail and blockers only

### Agent B - UI Assets
Scope:
- extract or prepare 4 dedicated menu icons from the sprite pack
- remove atlas compromise if possible
- keep attribution intact
Deliverable:
- final icon files or a clear recommendation to keep current atlas approach

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

## Decision Gate After Tomorrow Morning
- If VPS QA passes: continue with Parking Pomyslow storage decision.
- If VPS QA fails: stop product expansion and fix auth/deploy gaps only.
- If VPS QA is mixed: freeze visuals and finish backend clarity first.