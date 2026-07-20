# Helper Simplification Audit — 2026-07-16

## Outcome

The Helper is feature-rich but its current `ready` module-audit result is too
coarse for the next development wave. It proves extracted modules and gates,
but it does not prove single ownership, reachability, configurable behavior or
spell-state correctness.

## Measured Baseline

- `ctoa_native_helper.lua`: 4404 lines and 130 functions according to the
  canonical module audit, exactly at its 130-function budget and close to the
  4500-line budget; modularization pressure is `medium`.
- `ctoa_helper_ui.lua`: approximately 1922 lines and 90 function definitions.
- Confirmed single-reference local candidates in the native shell:
  `hasAttackTarget` and `countMonsters`.
- The existing audit reports `ready` despite the issues below, so its contract
  needs ownership and reachability checks rather than a larger numeric budget.

## Confirmed Duplication And Rigidity

1. HUD settings are rendered twice from the same profile fields:
   `Tools > HUD` (`ctoaToolsHudEnabled`, `ctoaToolsHudPos`) and `Engine`
   (`ctoaUiHudEnabled`, `ctoaUiHudPos`). Engine becomes the intended owner;
   Tools should link to status/diagnostics rather than repeat configuration.
2. Targeting stores embedded `ignored_names` and `priority_names`, but Hunting
   exposes only toggles and scalar range/timeout preferences. There is no list
   editor or ordered target-rule model.
3. Magic Shooter exposes fixed EK rows for `exori gran`, `exori`, and
   `exori min`. The runtime has broader rotation data, but the UI cannot add,
   remove, reorder or fully configure arbitrary spell/rune/stance actions.
4. Auto Haste dispatches when its interval elapses and does not check a proven
   active Haste condition. This explains repeated casting while haste is still
   active.
5. The native shell still coordinates UI adapters, fallbacks, profile bridges,
   target guards, combat planning and dispatch. Extracted modules exist, but
   fallback ownership remains distributed and can drift.

## Decisions

- Do not solve these issues by adding more vocation-specific branches.
- Do not make mandatory safety guards user-disableable.
- Introduce one typed action/condition model before rebuilding Targeting and
  Magic Shooter UI.
- Treat active spell conditions as evidence with freshness/unknown states, not
  as a timer assumption.
- Preserve Helper/Safe separation. Shared work may contain pure schemas and
  evaluators only; no shared mutable runtime or acceptance authority.

## First Safe Refactor Slice

P17.1 established this audit and the machine-readable P17-P24 contract. The
first P17.2 edit removed the two proven dead locals, reducing the canonical
audit result from 4404 lines/130 functions to 4380 lines/128 functions. P17.3
removed the Tools/HUD tab, header, controls and footer. Engine now owns the only
HUD preference controls; the legacy `hud` smoke subtab redirects to Engine and
does not create a second configuration surface. The redirect leaves the native
shell at 4384 lines/128 functions. A contract test rejects reintroduction of
the old Tools/HUD widget IDs. The next slice identifies redundant fallbacks
already owned by extracted modules.
Runtime behavior, sandbox arming and live files remain out of scope for these
static slices.

## P17.4 Rule Foundation

`ctoa_helper_rule_engine.lua` is the first shared Helper rule contract. It
supports typed HP, mana, monster-count, distance, PZ and active-condition
metrics; all six comparison operators; AND/OR; cooldown; hysteresis; and
bounded injected randomization. Sanitization copies scalar action parameters
and never stores transient thresholds in the profile. Evaluation always emits
`dispatch_allowed = false` and `executes_action = false`. The module is present
in the guarded boot graph and sandbox package, but no gameplay lane consumes it
until the remaining P17 ownership work and P18 adapter migrations are reviewed.

## P17.5 Targeting Ownership Cut

The native shell no longer duplicates `ctoa_helper_targeting.lua` behavior for
creature-name normalization, ignored-name matching or best-candidate ranking.
The module is required by the validated boot graph, so unavailable/invalid
module output now fails closed instead of silently switching algorithms. This
cut reduces the shell to 4353 lines/128 functions while preserving mandatory
NPC/player/summon/PZ guards.

## P19.1 Editable Target Name Policy

The Hunting/Targeting surface now exposes native `TextEdit` fields for ignored
names and ordered priority names. `ctoa_helper_targeting.lua` owns parsing,
normalization, deduplication, order preservation and the bounded 32-entry / 64
character policy. Empty input intentionally clears the selected list. Edits use
the existing profile autosave path; profile schema and persistence already own
both fields.

This resolves the audit finding
`target_name_policy_without_rule_editor`. Mandatory NPC, player, summon,
unattackable, unreachable and PZ guards remain outside the editable name policy.
The module remains passive: it neither scans creatures nor attacks or casts.
The remaining confirmed rigid findings are the fixed EK Magic Shooter rows and
Auto Haste without active-state evidence.

## P19.2 Editable Magic Shooter Rules

The three vocation-specific `exori gran`, `exori` and `exori min` controls are
no longer rendered. Magic Shooter now has a generic ordered spell-rule editor
with add, remove, up and down actions; arbitrary spell words; enabled,
monster-count and directional toggles; and bounded minimum mobs, maximum mobs,
scan range and cooldown values. A separate Runtime subtab retains the guarded
rotation, rune and Exeta controls.

The passive combat owner sanitizes at most 16 rules with 64-character spell
words and returns data-only editor decisions (`runtime_actions=false`,
`dispatch_allowed=false`). Existing presets use the same replacement path and
profile serialization preserves every editable field. The native shell is
4397 lines/128 functions, the generated 172-widget preview has no layout issue,
and the module audit now reports only Auto Haste without active-state evidence
as a confirmed rigid behavior. No live client or runtime arming was changed.

## P19.3 Ordered Target And Combat Actions

Target selection now consumes a bounded ordered `target_rules` list. Rules can
match an arbitrary name fragment or every monster and constrain HP, distance
and visible-monster count. They provide explicit numeric priority and a per-rule
`inherit`, `follow` or `stand` chase policy. Mandatory creature-type,
friendly-summon, reachability and PZ guards run before editable scoring.

Rune and stance configuration now uses a bounded ordered
`combat_action_rules` list rather than two fixed stance branches and one fixed
rune. Rows support arbitrary server text/hotkeys, count ranges, cooldown,
stance mode, target/PvP guards, add/remove and reorder. Editor decisions remain
action-free and global runtime switches remain separate. Profile serialization
preserves both new rule families. The shell is 4424 lines/128 functions and the
208-widget preview reports no overflow or overlap. P19 is complete; Auto Haste
state evidence is the next confirmed rigid lane.

## P20.1 Spell State Registry And Anti-Spam

The former Haste-only probe is now a bounded, data-driven spell-state registry.
Profiles declare at most 16 state families with proven client flag names,
editable spell words, evidence freshness, and either fail-closed or explicitly
bounded unknown-state policy. The registry observes only the local player's
state bitmask and never casts, talks, scans creatures, or grants dispatch
authority.

Haste and `PartyBuff`/strengthened decisions block while their proven state is
active and also block stale or unknown evidence. `utamo tempo` has no distinct
flag proven in the inspected client, so its family documents an explicit
30-second unknown-state fallback instead of pretending that timer state is
observation. Ordered stance rules reference these family IDs. Deterministic
replay covers active -> inactive, unknown fallback, fallback cooldown, and
repeat evaluation.

The duplicate scalar stance-selection branch was removed. The passive combat
owner now provides dispatch descriptors and records successful transient
timestamps/state; the native shell still owns the guarded OTClient calls. The
shell returned to 4404 lines/128 functions. With rigid behavior findings now
empty, the audit still reports `needs_simplification` because the P17 product
target remains below 4000 lines and 110 functions.

## P17.7 Required Module Ownership

`moduleValue` previously contained a second implementation for profile names,
schema/persistence values, hotkeys, modal requests, route distance, NPC and
summon guards, target scoring, CaveBot retry state, Recovery gaps, spell
selection, module lanes and UI context merging. Those fallbacks were reachable
only when a named owner was missing or malformed, which made failure behavior
different from normal behavior and allowed the copies to drift.

The bridge now invokes the named module or returns `nil`. Required owners are
loaded by the validated support-module graph, and missing output is handled by
the caller's existing blocked/disabled path. Profile and UI persistence gained
an additional fail-closed boundary: export and serialization complete before
the destination file is opened, so missing ownership cannot truncate a valid
profile with fallback data. This cut removes 84 net shell lines, leaving
4320 lines/128 functions with zero dead-local, duplicate-surface or rigid
behavior findings. The audit remains `needs_simplification` because the P17
4000/110 product target is intentionally stricter than the temporary ceiling.

## P17.8 Diagnostics And Smoke IO Ownership

The native shell previously retained seven named diagnostics helpers: three
safe API-call guards plus smoke-command path selection, export-path selection,
bounded-file removal and command-file reading. The diagnostics module already
owned the parser, status text, snapshots and exports, so splitting IO between
both files created an artificial second owner.

Diagnostics now owns safe object/global calls and the full passive smoke-file
boundary. It reads one sentinel byte beyond the 4096-byte limit and rejects an
oversized command before parsing, then exposes bounded path/read/remove
capabilities in its module contract. Export path selection is also resolved by
the diagnostics export owner. Real-Lua probes cover method calling, global
calling, relative OTClient path derivation, command parsing, removal and the
oversize rejection. This removes 73 shell lines and seven shell functions,
leaving 4247 lines/121 functions. P17 remains open for the CaveBot extraction
needed to reach the strict 4000/110 product gate.

## P17.9 Strict Product Gate Closure

The final ownership pass moved static layout/style tables into the UI owner,
guarded native reads into the OTClient observation adapter, the snapshot/export
and passive API-probe lifecycle into Diagnostics, editor bindings into Route,
and movement capability/reset state into CaveBot Runtime. The shell still owns
the deliberately guarded `autoWalk` calls and the runtime gate that precedes
them; no extracted module gained gameplay authority.

The native shell is now 3719 lines/100 named functions, below the strict
4000/110 gate. The module audit reports `ready` with no dead local, duplicate
surface or rigid behavior finding. HUD configuration still has one canonical
Engine surface, loader startup remains `helper-ui-only`, and all runtime actions
remain default-off. These results close P17 and make the next bounded slice
P18.1: schema/migration hardening of the existing data-only rule engine.

## P18.1 Versioned Rule And Profile Migration

The passive rule engine now owns v1 migrations for individual rules and
ordered rule sets. Sets are capped at 32 entries, preserve order, disable
legacy entries during upgrade and reject invalid or future schemas. Profile
migration delegates `tools.automation` to that owner and blocks the whole
profile if rule migration cannot be proved; persistence exports the versioned
section unchanged. Real-Lua probes cover replay, overflow, invalid-child and
future-version paths. The shell remains below the strict product gate at
3721 lines/100 functions and no runtime or live authority was added.

## P21.1 Data-Only Vocation Delta Packs

The existing vocation router now validates every loaded profile before schema
migration. Validation is bounded to depth 12 and 4096 nodes, rejects functions,
cycles, non-data values, wrong vocation, invalid schema, unsafe startup flags
and route/profile mismatches. MS, ED and RP are delta packs over the canonical
Helper defaults rather than three copies of the full EK configuration; this
removes 1416 tracked bytes while retaining editable vocation spell lists.
Real-Lua replay proves inherited defaults, vocation overrides and runtime-off
state. The native shell is 3727 lines/100 functions and remains within budget.

## P21.2 Canonical Default Ownership

`ctoa_helper_profile_schema.lua` is now the single owner of the canonical
profile defaults and migrations. `defaultProfile()` returns a defensive deep
copy; the native shell has no duplicate default tree and fails closed with an
explicit boot blocker when the owner is missing, throws, or returns invalid
data. Real-Lua tests cover mutation isolation, schema replay and both blocker
paths. This removes 180 shell lines, leaving 3547 lines/100 functions. P21 is
complete without inventing profile schema v2 where v1 remains sufficient.

## P22.1 Unified Settings And Rule Editor Interaction

The visible ownership ambiguity is removed without changing internal section
IDs or runtime gates. `Settings` is now the sole operator surface for the
Helper hotkey, appearance, HUD visibility and HUD position. `Profile` owns
healing defaults, module visibility and persistence. HUD rendering remains a
passive state projection and does not gain a second configuration surface.

Target, spell and combat-action rule editors now share one
`Ui.addRuleEditorChrome` builder for previous/next selection and
add/remove/reorder actions. Specialized fields and their existing bounded,
action-free mutations stay in the domain editors. The supported 690x560
preview renders 208 widgets with no containment issue. Focused UI/module tests
pass 92/92, all 61 OTClient Lua files parse, the module audit remains `ready`,
and the native shell remains 3547 lines/100 functions. The full workspace suite
passes 1933 tests, skips 49 and reports 20 pre-existing out-of-slice failures
across P13/P6-P7 evidence state, Equipment evidence, a deleted Control Center
boundary, P13 design text and the already promoted Safe version expectation.
P22 stays in progress
until P22.2 proves distinct disabled/blocked/stale/active feedback and explicit
overflow behavior in default and compact layouts.

## P22.2 Four-State Feedback And Contained Navigation

The operator UI now has one passive state vocabulary: `disabled`, `blocked`,
`stale` and `active`. Blocked state wins over stale, stale wins over active,
and an inactive lane resolves to disabled. Each state has a distinct semantic
color and border role. Settings boot/pipeline rows, the main runtime badge and
the passive HUD consume this vocabulary; a decision-pipeline snapshot older
than 5000 ms is visibly stale instead of looking active. Module status counts
stale lanes separately from blocked and missing lanes.

The current high-confidence OTCv8 capability profile proves programmatic
widgets but not a native scroll-container alias. Rule overflow therefore uses
the compatible single-row previous/next model, bounded to empty index `0` or
`1..count` for the existing 16-entry cap. Default and compact previews each
contain 208 widgets in 690x560 with zero issues. Real-Lua state, visual-role,
navigation, HUD and module-status probes pass; the focused suite is 112/112,
all 61 Lua files parse, and the module audit is `ready`. The shell is still
within its strict product gate at 3576 lines/102 functions. The broader
Helper/OTClient run passes 792, skips 13 and retains six known out-of-slice
failures: four Equipment evidence expectations, the stale P14 stage manifest
and the removed Control Center evidence component boundary. P22 is complete and
opens the static, action-free P23.1 boundary inventory.

## P23.1 Helper / Safe Contract Boundary Inventory

Nine product boundaries are classified in the machine-readable P23 inventory:
the numeric operator/combinator vocabulary is shareable; metric names,
randomization lifecycle and extended Helper features require adapters; profile
persistence, loaders, mutable runtime,
UI/HUD, plus acceptance/promotion evidence are rejected from sharing. Helper
retains profile v1; Safe retains profile v3; neither product can satisfy the
other's acceptance gate.

Ten deterministic real-Lua cases prove the shared subset across all six
numeric operators, AND/OR, mapped HP/mana/monster metrics and one-shot bounded
randomization. The Safe-side implementation is a fixture-only adapter under
`tests/fixtures/lua`. An attempted placement in `mods/ctoa_safe` was rejected by
the existing three-file runtime boundary, so it was removed rather than
weakening the release contract. Safe loader/runtime files and its seven-file
release manifest remain unchanged. Operational acceptance and promotion stay
false. The integrated boundary suite passes 51 tests. One pre-existing release
test still expects Safe 3.3.0 while the source and validated manifest are
3.4.0; it is not changed by this slice.

## P23.2 Product-local Condition Core Decision

The reviewed decision is `no_shared_runtime_core`. Helper owns a pure,
versioned evaluator with eight-condition capacity, per-evaluation injected
random offsets, hysteresis, cooldown and extended metrics. Safe owns a
four-condition profile-v3 evaluator whose randomized `_effective_value` is
cached until a successful action resets it. The P23.1 fixture therefore proves
one-shot numeric semantics, not identical runtime lifecycle.

Sharing a runtime file would either erase those product differences or couple
Safe's independent package to a Helper-owned module. P23.2 instead preserves
both product-local evaluators and shares only the six operator names, AND/OR
truth tables, metric mapping documentation and passive parity cases. No loader,
mutable state, profile schema, release manifest, acceptance evidence, sandbox
root or live root changed. The machine-readable decision is
`AI/P23_2_CONDITION_CORE_DECISION.json`. P23 is complete; P24.1 is next.

## P24.1 Replay And Canary Matrix

Six replay lanes now bind P18-P23 to concrete test files and explicitly list
what each evidence level cannot prove. The integrated replay set passes 61
tests. Four sandbox-only canaries cover safe-boot profile migration, passive
NPC/player/dummy target rejection, PZ plus anti-spam spell state, and package
rollback. They are specified but not executed; only the spell-state canary may
ever dispatch, is capped at one allowlisted cast, and requires a separate
session approval.

The current P14 preflight is not accepted. Its runner is online and a previous
signed run exists, but the revision is stale, visual/in-world/canary/rollback
acceptance is missing, required environment review is absent, and admin bypass
is enabled. The local official stage is also stale; the first strict manifest
mismatch is `mods/ctoa_otclient/ctoa_helper_hud.lua`. The P14 contract suite
passes 31, skips one and correctly retains that one mismatch failure. Sandbox
queue and release-gate contracts pass 47. P24.2 must refresh those external and
stage proofs before any canary can run.
