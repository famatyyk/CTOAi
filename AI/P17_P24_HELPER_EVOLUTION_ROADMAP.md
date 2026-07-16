# CTOAi Helper P17-P24 Evolution Roadmap

This roadmap extends the Helper beyond the design-only P15/P16 twins. It does
not change the current machine-readable P13/P14 evidence state and grants no
runtime or live authority. Static P17 work may proceed while P14 independent
runner evidence remains open; runtime acceptance still depends on P14.

The machine-readable companion is `AI/P17_P24_HELPER_EVOLUTION_ROADMAP.json`.
The measured baseline and audit evidence are recorded in
`docs/otclient/HELPER_SIMPLIFICATION_AUDIT_2026-07-16.md`.

## Direction

Helper remains the primary product. Safe remains a separate, smaller product.
The useful lesson from Safe is the action/condition separation and editable
rule model, not permission to copy Safe runtime or bypass Helper gates.

The order is deliberate: simplify ownership first, introduce one typed rule
model second, then rebuild targeting/spells and the UI on that model. Adding
more branches to `ctoa_native_helper.lua` before P17/P18 is rejected.

## P17 — Helper Simplification And Ownership

Remove proven dead paths, consolidate duplicated UI, assign one owner per
domain, and extend the module audit with reachability/ownership checks. Initial
targets are the duplicate HUD settings, unused `hasAttackTarget` and
`countMonsters` locals, fallback logic already owned by extracted modules, and
the initial 4404-line/130-function shell ceiling. The first reachability cut
removed those two unused locals. P17.3 then removed the Tools/HUD controls and
made Engine the single HUD configuration owner. A legacy `hud` smoke subtab is
only a redirect to Engine; it no longer renders or persists a second surface.
The resulting native shell has 4384 lines and 128 functions.

P17.5 removed three redundant Targeting fallbacks from the shell: creature-name
normalization, ignored-name matching and a second candidate-ranking loop. The
required `ctoa_helper_targeting.lua` module now owns these decisions; missing or
invalid module output fails closed. The shell is now 4353 lines/128 functions.

## P18 — Declarative Action And Condition Engine

Separate what to do from when to do it. Actions include spell, rune, item,
equipment, stance and target selection. Conditions include HP, mana, monster
count, range, PZ and observed active states, with `<`, `<=`, `=`, `!=`, `>=`,
`>`, AND/OR, cooldown, hysteresis and bounded randomization.

The passive foundation now exists in `ctoa_helper_rule_engine.lua`. It validates
and evaluates typed rules without OTClient globals, profile mutation or action
dispatch. It is in the guarded support-module boot graph, but no targeting,
spell or equipment runtime consumes it yet.

## P19 — Configurable Targeting And Magic Shooter

Replace embedded name lists and three fixed EK spell controls with ordered,
editable target/action rules. Mandatory NPC/player/summon/PZ/dummy guards stay
outside user-overridable scoring.

P19.1 opens the first previously hard-coded policy in the native Helper UI.
`Ignored names` and `Priority order` are editable `TextEdit` fields with
autosave. The passive Targeting owner normalizes, deduplicates, preserves order,
limits the policy to 32 entries of 64 characters, and allows an empty list.
Changing these fields grants no runtime authority and does not make mandatory
NPC/player/summon/PZ guards configurable. The shell is 4366 lines/128 functions;
the temporary line increase is UI wiring and does not satisfy the remaining P17
shell budget gate.

P19.2 removes the three fixed EK controls from Magic Shooter. `Spell Rules` is
now an ordered profile-data editor: an operator can add, remove and move rules,
edit arbitrary spell words, enable a rule, choose whether monster count applies,
and set minimum/maximum mobs, scan range, cooldown and directional behavior.
The separate `Runtime` subtab owns rotation/rune activation and remains guarded
by the existing safe-boot path. Rules are sanitized to 16 entries and 64 spell
characters; every editor decision explicitly reports `runtime_actions=false`
and `dispatch_allowed=false`. Existing rotation presets migrate through the same
sanitizer, while the serializer preserves all new rule fields. The shell is now
4397 lines/128 functions and remains inside the temporary 4500/130 ceiling.

P19.3 completes the configurable combat surface. `Target Rules` is an ordered
list with arbitrary name/wildcard matching, HP, distance, visible-monster
count, numeric priority and `inherit/follow/stand` chase policy. Mandatory
friendly-summon, NPC/player, reachability and PZ guards remain outside these
rules. Candidate counts come from the already bounded target scan; the UI does
not perform its own scan.

`Actions` is now a second ordered editor for arbitrary `rune` and `stance`
rules. Each row owns its text, hotkey/mode, monster-count range, cooldown,
target requirement and PvP-safe flag and supports add/remove/reorder. Runtime
master switches remain on the separate Runtime subtab, so profile editing does
not arm a feature. Legacy scalar fields may still be read during profile
migration, but no longer drive a second stance-selection branch. The shell was
4424 lines/128 functions at the P19 gate and the 208-widget preview had no
layout issue.

## P20 — Spell State Registry And Anti-Spam

Resolve active haste, shield, buff and stance state through proven client APIs
and bounded adapters. Unknown state is explicit. Auto Haste must not cast only
because a timer expired.

P20.1 is complete at the static/runtime-contract boundary. The passive registry
now owns bounded `spell_state_families`, resolves proven `PlayerStates` flags,
emits fresh/active/inactive/unknown evidence and produces deterministic
decisions. Haste and strengthened states fail closed when unknown or stale.
Spells without a proven distinct client flag can use only an explicit bounded
cooldown fallback stored in profile data. Ordered stance rules reference a
`state_id`; an active state blocks selection before dispatch. Vocation spell
families live in EK/MS/ED/RP profile data rather than vocation branches.

P17.6 removed the second scalar stance-selection algorithm and moved combat
dispatch descriptors plus success bookkeeping into the passive combat owner.
The native shell retains the guarded OTClient calls but no longer duplicates
per-action timestamp/state mutation. It is back at the 4404-line ratchet and
128 functions. The module audit intentionally remains `needs_simplification`
until the product target of fewer than 4000 lines and 110 functions is met.

P17.7 removed the 100-line `moduleValue` fallback hub that reimplemented pieces
of Profile, Hotkeys, Modal, Route, Targeting, CaveBot, Recovery, Combat and UI
inside the shell. Required modules are now authoritative and an unavailable or
malformed owner returns no decision instead of silently switching algorithms.
Profile and UI saves also serialize and validate their payload before opening
the destination file, preventing a missing owner from truncating a profile.
The shell is now 4320 lines/128 functions; the P17 product target remains open.

P17.8 moved safe object/global API calls plus smoke-command path, read and
removal into the passive diagnostics owner. Smoke input is now read through a
4097-byte sentinel and rejected above the 4096-byte contract before parsing.
The native shell only requests the operation and applies the command; it no
longer owns duplicate diagnostics IO helpers. The shell is now 4247 lines/121
functions, with real-Lua coverage for the extracted API and bounded IO paths.

P17.9 closes the strict P17 product gate. UI now owns the style/layout tables,
the observation adapter owns guarded native reads, Diagnostics owns its
controller and passive API probe lifecycle, Route owns editor bindings, and
CaveBot Runtime owns movement capability plus transient state reset. The shell
retains guarded `autoWalk` dispatch and orchestration boundaries, but no longer
duplicates those passive contracts. The authoritative audit reports `ready` at
3719 lines/100 functions with no dead-local, duplicate-surface or rigid-behavior
finding. P17 is complete; runtime authority remains unchanged and default-off.

P18.1 closes the declarative engine phase without granting runtime authority.
Rule and ordered rule-set schemas are versioned, bounded to 32 entries and
migrated deterministically. Legacy rules are disabled during migration;
unknown, invalid and future versions fail closed. Profile migration delegates
the `tools.automation` section to the rule engine, persistence keeps the
versioned data, and replay tests prove that a current profile stays stable.
The native shell is 3721 lines/100 functions and safe boot remains default-off.

## P21 — Profile Schema V2 And Vocation Packs

Move defaults, migrations and vocation differences into one typed schema plus
data-only packs. Preserve custom-server spell editing and never persist runtime
arming or transient cooldown state.

## P22 — Native Unified Operator UX

Expose one settings location per concern, native scroll containment, reusable
rule rows/editors and clear disabled/blocked/stale/active feedback. HUD belongs
to one surface rather than Tools and Engine simultaneously.

P22.1 is complete. The former ambiguous `Engine`/`Settings` pair is now one
visible `Settings` surface for hotkey, appearance and HUD, plus a separate
`Profile` surface for healing, module visibility and presets. Target, spell and
combat-action editors use one native selector/navigation/action chrome while
retaining their specialized fields and action-free profile mutations. The
690x560 preview contains 208 widgets with zero layout issues; 92 focused tests,
61 Lua syntax checks and the module audit are green. The broad workspace run
passes 1933 tests, skips 49 and retains 20 out-of-slice failures in the existing
P13/P6-P7, Equipment evidence, deleted Control Center boundary, P13 design and
Safe-version expectations. P22.2 remains responsible
for distinct disabled/blocked/stale/active feedback and explicit overflow
containment proof before the full phase can close.

P22.2 completes the phase. One passive UI contract normalizes `disabled`,
`blocked`, `stale` and `active` with blocker-first precedence and four distinct
visual roles. Decision-pipeline evidence becomes stale after 5000 ms without a
refresh, Settings and the runtime badge use the same state vocabulary, and the
passive HUD prints the normalized state beside its decision. Module status now
counts stale lanes separately.

The detected OTCv8 target proves programmatic widgets but does not prove a safe
scroll-container alias. Ordered target, spell and action rules therefore use a
single-row, bounded previous/next navigation contract rather than an unproven
OTUI widget. Lists remain capped at 16 and navigation clamps to `0` for empty or
`1..count` otherwise. Default and compact previews each render 208 widgets in
690x560 with zero containment issues. Real Lua, 112 focused tests, all 61 Lua
syntax checks and the module audit pass without new runtime authority. The
Helper/OTClient regression passes 792 tests, skips 13 and retains only the six
known out-of-slice failures: four Equipment evidence expectations, the
intentionally stale P14 stage manifest and the deleted Control Center evidence
component boundary. The native shell remains below its product gate at 3576
lines/102 functions.

## P23 — Shared Contracts Without Project Coupling

Helper and Safe share a bounded condition vocabulary and parity evidence. They
do not share evaluator files, loaders, mutable runtime state, acceptance
receipts or promotion authority.

P23.1 is complete. A machine-readable inventory classifies nine boundaries:
one pure numeric/combinator vocabulary is `share`, three product-specific
representations or lifecycles are `adapt`, and five loader/runtime/UI/evidence
areas are `reject`. Helper keeps
profile v1 and Safe keeps profile v3. Neither loader, mutable state nor
acceptance receipt crosses the project boundary.

Ten deterministic fixture cases prove parity for six numeric operators, AND/
OR, HP/mana/monster metric mapping and one-shot bounded randomization. The Safe-side
adapter lives only under `tests/fixtures/lua`; placing it inside
`mods/ctoa_safe` was correctly rejected by the existing three-file runtime and
seven-file release-manifest gates. It is not loaded or called by Safe. The
fixture explicitly keeps runtime, dispatch, operational acceptance and
promotion false. The integrated boundary suite passes 51 tests; the separately
known Safe release assertion still expects 3.3.0 although the source and
validated manifest are 3.4.0.

P23.2 is complete with the reviewed `no_shared_runtime_core` decision. Helper
randomizes through an injected per-evaluation offset and supports eight
conditions plus hysteresis/cooldown/extended metrics. Safe supports four
conditions and retains `_effective_value` until the owning action succeeds.
Those are product semantics, not accidental duplication. Each evaluator stays
local; no loader, runtime file, schema, mutable state, manifest or evidence gate
is shared. The machine-readable decision is
`AI/P23_2_CONDITION_CORE_DECISION.json`.

## P24 — Replay, Canary And Rollback Program

Bind the simplified Helper to independent-runner replay, bounded sandbox
gameplay canaries and tested rollback. Live promotion always remains a separate
explicit approval.

P24.1 is complete as a static, action-free planning and replay slice. Six
P18-P23 replay lanes name both their proven scope and their limits. Four
sandbox canaries define preconditions, actions, observations, abort conditions
and rollback; none has been executed or authorized. The focused replay suite
passes 61 tests and the sandbox queue/release-gate suite passes 47.

P14 remains `externally_verified_stale`: the matching Windows runner is online
and an earlier signed run passed, but it does not match the current revision,
the four acceptance capabilities are unproven, environment review protection
is incomplete, and the local stage manifest differs from tracked Helper source.
The strict P14 suite passes 31, skips one and correctly retains one stale-stage
failure. P24.2 must refresh stage and current-revision independent evidence;
P24.1 grants no runtime, canary or promotion authority.

## Immediate Work Order

1. P17.1: ownership/reachability audit and contract — complete.
2. P17.2: remove the two proven dead locals — complete.
3. P17.3: keep one canonical HUD configuration surface — complete; Engine owns
   HUD preferences and the old smoke target redirects there.
4. P17.4: design the P18 schema and evaluator without dispatch wiring —
   complete; real-Lua behavior and passive module-contract tests pass.
5. P17.5: remove duplicate Targeting fallbacks — complete; required-module
   output is authoritative and missing output fails closed.
6. P19.1: expose bounded ignored/priority target-name editing — complete;
   native fields autosave and the Targeting module owns sanitation/order.
7. P19.2: replace the three fixed EK Magic Shooter rows with an editable,
   ordered spell-rule list — complete; profile-data editing is bounded,
   autosaved and separated from the runtime-gated controls.
8. P19.3: open ordered target conditions plus rune/stance action rows —
   complete; both editors are bounded, autosaved and action-free.
9. P20.1: introduce an observed spell-state registry and remove timer-only
   Auto Haste decisions without weakening safe boot — complete; state families,
   deterministic transitions and bounded unknown fallback are covered.
10. P17.6: remove the duplicate scalar stance path and centralize combat
    descriptors/success bookkeeping — complete; shell ratchet restored to
    4404 lines/128 functions.
11. P17.7: continue shell extraction toward the 4000/110 product target without
    adding runtime authority — complete; the duplicate `moduleValue` fallback
    hub is gone and missing owners fail closed.
12. P17.8: reduce function ownership pressure, starting with diagnostics/smoke
    — complete; diagnostics now owns API guards and bounded smoke IO.
13. P17.9: extract remaining CaveBot, diagnostics, UI and observation ownership
    — complete; the shell is 3719/100 and the module audit reports `ready`.
14. P18.1: promote the existing data-only rule-engine foundation into a
    versioned, bounded and deterministic schema/profile migration slice —
    complete; legacy input is disabled, future input fails closed and no new
    runtime authority is wired.
15. P21.1: inventory and consolidate vocation profile data before schema growth
    — complete; the existing vocation owner now rejects executable, mismatched,
    oversized or runtime-armed packs, while MS/ED/RP store only vocation deltas
    plus explicit safe flags. Replay preserves custom spell data and stays off.
16. P21.2: move the remaining canonical shared default tree out of the native
    shell and into profile-schema ownership — complete; the schema returns a
    defensive deep copy, missing/invalid ownership fails closed, and the shell
    drops 180 lines without profile behavior drift. A gratuitous v2 is avoided.
17. P22.1: audit and unify Settings, HUD and rule-editor interaction surfaces —
    complete; Settings owns hotkey/appearance/HUD, Profile owns profile data,
    and all three ordered rule editors share one interaction chrome.
18. P22.2: make disabled/blocked/stale/active feedback visibly distinct and
    prove contained navigation in default and compact layouts — complete;
    four visual roles, bounded single-row navigation and both previews pass.
19. P23.1: inventory pure Helper/Safe contracts, classify each as share/adapt/
    reject and prove that loaders, mutable runtime state and acceptance evidence
    stay separate — complete; nine boundaries and ten real-Lua parity cases are
    recorded without changing either product runtime.
20. P23.2: decide whether the reviewed pure condition subset becomes one
    canonical core with product-local adapters or remains explicitly separate;
    preserve both release manifests and safe boot — complete; runtime sharing
    is explicitly rejected while numeric semantics retain parity coverage.
21. P24.1: bind the P18-P23 contracts to an independent replay matrix and
    specify bounded sandbox canaries with explicit rollback — complete; six
    replay lanes and four unexecuted canaries are machine-readable.
22. P24.2: refresh the official stage, obtain a signed current-revision Windows
    runner result and prepare an action-free acceptance request for visual,
    in-world, canary and rollback capabilities — next.
