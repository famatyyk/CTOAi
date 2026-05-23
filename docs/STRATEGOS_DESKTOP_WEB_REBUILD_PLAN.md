# Strategos Program Plan: Windows EXE + Web Rebuild

## Mission
Build a professional Windows executable and rebuild the web experience under one delivery lane.

## Product Scope
1. Windows desktop app with login and account creation.
2. Live dashboard for all authenticated users.
3. Admin console restricted to owner account only.
4. Web redesign with new design system and media pipeline.
5. Prompt/tool stack for text, image, and UX generation.

## Strategic phases
### Phase 1 - Foundation (now)
1. Add self-registration endpoint to API.
2. Deliver desktop GUI shell with role-gated admin console.
3. Add build script for EXE packaging.
4. Extend agent roster with design+infrastructure lead.

### Phase 2 - Productization
1. Persist desktop settings and profile sync.
2. Integrate telemetry and audit trail in desktop actions.
3. Introduce signed build and release channel.
4. Add regression and smoke tests for desktop auth flow.

### Phase 3 - Website rebuild
1. Establish design language and component inventory.
2. Rebuild pages with conversion-focused IA.
3. Prepare visual assets and copy blocks.
4. Wire publishing and monitoring into CI gate.

## Agent orchestration
1. queen-ctoa: overall decisions, risk gating, sprint goals.
2. pm-roadmap: roadmap breakdown, delivery sequencing.
3. prompt-forge: prompts for copy, UX, and automation assistants.
4. tool-advisor: tool ranking for design/image/text generators.
5. design-infra-lead: design system, UI assets, deployment blueprint.
6. builder-engine: desktop and web implementation.
7. qa-safety: quality and security validation.
8. ci-publisher: release gate and publish control.
9. documenter: runbooks, release notes, onboarding docs.
10. mmo-intel + bot-architect + lua-scripter: domain integration for project-specific workflows.

## Risks and controls
1. Open registration abuse -> optional registration code and API rate limiting.
2. Owner console misuse -> strict role gate and command allowlist mode.
3. Build drift -> pinned build script and release checklist.
4. Scope overload -> phase gates with go/no-go decisions.

## Immediate next backlog items
1. Desktop app auto-refresh and resilient reconnect flow.
2. Owner-managed user administration screen in desktop app.
3. Visual redesign sprint for docs/site and live dashboard.
4. Toolchain pack for media generation and design QA.
