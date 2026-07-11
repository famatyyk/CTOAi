# Vbot 5.0 To CTOAi Helper Execution Plan

## Decision

The useful Vbot pattern is its split between domain logic, profile/UI state, and
an execution router. CTOAi must adapt that separation, not copy Vbot runtime
actions. CTOAi already has stronger safe-boot, policy, evidence, and release
gates; those remain authoritative.

The inspected Vbot snapshot contains 117 files and about 25,850 text lines. Its
main `vBot` lane contains 71 files and about 19,303 lines. The snapshot also
contains newer domain files (`00_core_helper_domain.lua`, attack pattern/UI/router
splits, and `storage_schema.lua`) that are not listed in `_Loader.lua`. Because
`AttackBot.lua` requires those domains, its manual loader graph can fail before
the module starts. CTOAi will avoid that failure mode with one validated boot
manifest.

## Non-negotiable boundaries

- Keep `helper-ui-only` and safe runtime defaults.
- Never import Vbot network update checks, arbitrary scripts, automatic combat,
  movement, casting, item use, or storage writes as boot behavior.
- All runtime actions continue through CTOAi runtime policy, dispatch guard,
  explicit arming, sandbox evidence, and live approval.
- Keep the untracked official Windows wrapper in the Helper/Solteria commit
  bundle. Do not mix runtime artifacts, logs, caches, or unrelated repo lanes.
- Treat Vbot as a behavioral reference only; implement CTOAi-native contracts.

## Execution order

1. **Validated boot graph** — move support-module order and dependency metadata
   into `ctoa_helper_modules.lua`; make the loader bootstrap that registry and
   fail closed before loading the main helper if the graph is invalid or a
   required module is missing.
2. **Domain contracts** — standardize observation, planning, summary, and
   contract surfaces for healing, combat, cavebot, loot, conditions, equipment,
   heal-friend, timer, and scripting lanes.
3. **Profile migration layer** — extend the existing profile schema with named
   schema versions and bounded migrations inspired by Vbot's separated profile
   files, while preserving CTOAi key order and safe defaults.
4. **Decision pipeline** — keep the Vbot-style domain/UI/router separation but
   route plans through `planner -> runtime_policy -> dispatch_guard -> bounded
   queue -> adapter`, with no direct domain execution.
5. **Operator surface** — expose module phase, dependency health, readiness,
   blockers, and the selected plan without enabling actions from display code.
6. **Evidence and promotion** — extend static contracts, run targeted pytest,
   `ValidateDev`, `ModuleStaticGates`, sandbox attach smokes, then require an
   explicit approved live promotion in a separate operation.

## Point 1 acceptance criteria

- One support-module manifest owns ordering, phases, and dependencies.
- The loader contains only the registry bootstrap, consumes a defensive copy of
  the manifest, validates it, and refuses to load the main helper on failure.
- Existing module-contract and loader-shell tests pass.
- Safe boot behavior and runtime action permissions do not change.
- No live client mutation occurs during implementation or static validation.

## Commit bundle

Point 1 belongs to `helper-solteria` and includes only the loader, module
registry, contract validator/tests, this plan, related generated Helper docs,
and the official wrapper when the complete bundle is intentionally staged.

## Point 2 progress

`ctoa_helper_domain_contract.lua` defines the shared
`ctoa-helper-domain-v1` protocol. It catalogs all nine lanes and provides
defensive observation, plan, and summary envelopes. Plan envelopes always leave
`dispatch_allowed` and `executes_plan` false; later runtime wiring must still go
through the existing policy and dispatch guard.

The planner is the compatibility boundary: it leaves every domain's existing
call signature unchanged, then attaches the canonical observation envelope and
normalizes the returned plan. `Planner.summaryEnvelope` produces the same
protocol for operator summaries. This keeps module behavior stable while all
nine lanes expose a consistent downstream contract.

## Point 3 progress

Profiles now declare `ctoa-helper-profile-v1`. Unversioned profiles receive a
bounded in-memory migration before merge; missing sections come from current
defaults and all runtime-sensitive flags are reset to safe values. Invalid or
future profile versions fail closed and are not merged. The builder, serializer
key order, JSON schema, profile audit, and persistence export carry the same
version identifier.

## Point 4 progress

`ctoa_helper_decision_pipeline.lua` now coordinates the real passive flow:
planner collection and ranking, action risk classification, runtime-policy gate
evaluation, dispatch-guard review, bounded decision queue, readiness, decision
trace, and an adapter handoff. A ready handoff means `review_ready`, never
execution: the coordinator always returns `dispatch_allowed = false`, does not
invoke adapters, and performs no OTClient action.

## Point 5 progress

The Engine panel now has live read-only `Boot` and `Pipeline` rows. Boot status
summarizes manifest phases, loaded/total modules, missing modules, and broken
dependencies from the actual loader state. Pipeline status shows the latest
adapter handoff, action, guard state, and unique blocker count. The UI formats
these values only and cannot change gates or dispatch an action.
