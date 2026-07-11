# CTOAi Runtime 2 Execution Plan

## Decision

CTOAi Runtime 2 will adapt the lightweight event-driven execution model observed in the reviewed vBot 5.0 source without importing its global-state architecture wholesale. CTOAi remains the policy, planning, evidence, and operator layer. OTClient Lua remains the low-latency observation and execution layer.

Runtime actions remain disabled by default. Existing `ctoa_helper_runtime_policy.lua` and `ctoa_helper_dispatch_guard.lua` contracts remain authoritative for future execution.

## Target Flow

1. OTClient adapters collect bounded observations.
2. Domain observers publish normalized events.
3. Passive planners produce candidate plans.
4. Runtime policy and dispatch guard classify each plan.
5. A future executor may act only after sandbox, manifest, smoke, and live-approval gates pass.
6. Bounded telemetry reports results to the Helper and Control Center surfaces.

## Migration Principles

- Adapt behavior and domain boundaries; do not copy unreviewed external code.
- Keep OTClient globals behind guarded adapters.
- Keep UI, observation, planning, policy, and execution separate.
- Use one budgeted scheduler instead of adding independent high-frequency loops.
- New tasks are passive and disabled by default.
- A scheduler overrun defers work; it never expands the tick budget.
- A failed task receives bounded backoff and cannot stop other domains.
- Capability reports must distinguish registered, enabled, healthy, deferred, and failed states.

## Execution Sequence

### P0 — Runtime Core

- Add a runtime module registry separate from the descriptive Helper lane registry.
- Add a synchronous, failure-isolated event bus.
- Add a budgeted cooperative scheduler with per-task interval and failure backoff.
- Expose passive snapshots and counters for diagnostics.
- Keep every task disabled by default.

Evidence: static contract tests, scheduler behavior tests, loader wiring, safe-boot assertions.

### P1 — Passive Combat/Targeting Adapter

- Normalize target, spectator, protection-zone, cooldown, and latency observations.
- Publish observation events without calling attack, talk, use, walk, or cast APIs.
- Feed the existing passive combat planner and decision trace.
- Report plan and guard status through existing capability telemetry.

Evidence: fixture-based observation tests, no-action static scan, malformed-API fallbacks.

### P2 — Tick Budget and Telemetry Integration

- Route the first observer through Runtime Core.
- Add deferred-task, execution-time, failure, and backoff counters.
- Surface a compact scheduler snapshot in Helper diagnostics and the client reporter.

Evidence: deterministic clock tests and bounded diagnostic snapshot tests.

### P3 — Domain Migration

Migrate in order: targeting/combat, recovery/healing, cavebot/pathing, loot, equipment. Each domain must pass observer-only tests before an executor is designed.

### P4 — Guarded Executor

Design an executor only after current sandbox attach, SmokeAttachAll, manifest, release-gate, and explicit live-approval evidence is present. The executor must consume only dispatch-guard-approved plans and must add action-specific cooldown and protection-zone checks.

## Current Status

- P0 implementation: complete repo-side; registry, event bus, budgeted scheduler,
  Lua behavior probe, loader wiring, and safe-default tests pass.
- P1 implementation: complete repo-side with a normalized passive
  combat/targeting observer and guarded OTClient snapshot provider. Loader
  attachment registers the observer task disabled by default.
- P2 implementation: complete repo-side. Runtime Core status now reaches Helper
  diagnostics, bounded diagnostic exports, and the additive `runtime_core`
  section of the v1 capability report with disabled/deferred/failed counters.
- P3 implementation: complete repo-side for targeting/combat, recovery/healing,
  cavebot/pathing, loot, and equipment observers. All five are attached to
  guarded OTClient providers; Runtime Core reports five registered tasks and
  zero enabled tasks after safe boot.
- P4: blocked by current evidence. The latest goal audit verifies 14/19 checks
  after the official `GoalStatus` refresh and now reports only the genuine
  in-world ModuleAttachSmoke, SmokeAttachAll, and live-approval blockers. The
  earlier static freshness mismatch came from running the goal audit without
  first regenerating `release_gate.json` through `GoalStatus`.
- The sandbox packaging contract now includes Runtime Core, all five observers,
  and the guarded OTClient observation adapter in runtime sync, dev manifest,
  stage construction, and enable/disable lists. A full PrepareDev/ValidateDev
  rebuild passes 114 tests; the sandbox must log in and rerun attach smoke.
- The smoke-command resolver now converts virtual `/ctoa_ui_prefs.lua` state to
  the real sandbox work-directory `ctoa_smoke_command.lua` path before `io.open`.
  This fixes the repeated `Smoke command failed: nil` loop caused by mixing the
  resource filesystem with the host filesystem. The rebuilt sandbox is waiting
  at saved-credential login before the in-world verification can run.
- Runtime action enablement: prohibited until P4 evidence is complete.
