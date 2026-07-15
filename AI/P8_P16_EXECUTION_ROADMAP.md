# CTOAi P8-P16 Execution Roadmap

Canonical snapshot (2026-07-14): Helper source/live is `v2.4.1`; Safe source
candidate is `v2.9.0`, last verified live Safe is `v2.8.0`, and chooser is
`2.1.0`. P8 operational acceptance completed on 2026-07-14: exactly one live
process, a fresh `v2.4.1` heartbeat newer than that process, trusted manifest
pin, `62/62` live hash parity, and unchanged process/screenshot invariants.
Repository validation for this snapshot passed with `1694 passed, 46 skipped`
outside e2e; web validation passed `147/147` tests and lint.

P9 promotion update (2026-07-14): the Helper release boundary was separated
from Safe, the fresh sandbox chain passed `4/4`, `16/16`, and `19/19`, and the
explicitly approved official promotion verified `59/59` Helper/chooser files.
The manifest contains zero `mods/ctoa_safe` entries. GoalStatus is complete and
the release gate is passed. The running live process was not restarted, so the
canonical P9 observation still waits for a normal client reload and fresh
Helper heartbeat.

The normal reload is now complete and `otbg` is `ready`. Canonical live `otp9`
accepts the fork-proven `player_states` source after synchronizing the Python
sanitizer, replay, and Recovery contracts (`186 passed, 2 skipped`). The current
real decision is a valid fail-closed `hold`, blocked only by
`protection_zone_inside` and `condition_absent`; scenario replay passes. No P9
acceptance receipt may be issued until a fresh passive sample observes the test
character outside PZ with paralyze present and all remaining guards ready.

That sample was captured on 2026-07-14 by a bounded passive monitor that invoked
the canonical wrapper immediately after the short-lived state appeared. P9 now
reports `shadow_plan_ready_for_operator_review`; the operational trace is
`shadow_plan_ready` with decision `would_plan_paralyze_recovery`, no blockers,
Recovery trace/proof `ready`, scenario pack `passed`, and report SHA-256
`65776a653981f9681b799faf29ce085fc63435d60284fb3c3849381acff075a4`.
Dispatch, runtime, execute-once, promotion, and intrusive-action fields remain
false/empty. The separate `otp9accept` receipt still requires exact operator
confirmation and has not been created.

P9 acceptance completed on 2026-07-14. The persisted receipt is `accepted`,
`acceptance_granted=true`, and binds canonical report SHA-256
`795c2d4b1a130376335035d144be1cff609fe51ed826a75f46530571579ce0df`;
the independently recomputed canonical hash matches. All runtime, dispatch,
execute-once, promotion, and intrusive-action fields remain false/empty. P10 is
now the active phase. Its first dependency preflight confirms the P9 report and
receipt are ready and hash-bound, but remains blocked by the missing local
operator exact-ID override, stale/blocked Equipment preview, unknown Equipment
PZ source, and no equipped ring. No item movement was performed.

The operator then supplied ring IDs `3096 -> 3097`. Passive inventory evidence
confirmed equipped ring `3096` and candidate `3097`; `10325` was an item ID in
another container, not a container handle. Runtime container handles are
session-scoped: the live observation used `container_id=1`, `slot_index=1`,
while the approved P10 sandbox resolved the same candidate at
`container_id=2`, `slot_index=1`. The sandbox chain passed module attach `4/4`,
full attach `16/16`, and runtime gates `19/19`, with all action flags false.
Equipment uses the fork-proven `player_states` PZ fallback across Lua, Python
validators, and JSON Schemas. `otp10autoplan` now refreshes the fixed passive
preview, accepts only the equipped and candidate item IDs, and binds
container/slot from exactly one fresh operational match in the same process;
missing or duplicate matches fail closed. The passive planning preview allows
`10000 ms` solely for the complete official-wrapper transport chain, while the operational
snapshot/replay boundary remains `6000 ms`. Targeted P10 validation passed
`187 passed, 5 skipped`. The separately approved Helper promotion then passed
the official release gate with independent `59/59` stage/live SHA-256 parity,
zero mismatches, and zero Safe files in the Helper manifest. Backup:
`runtime/solteria_helper_dev/live_backup_20260714-211806`. The active live
process was not restarted, so a normal client reload and fresh passive preview
are still required. No profile or item change was performed.

P10 operational acceptance completed on 2026-07-15. A fresh passive snapshot
bound equipped ring `3096` to candidate `3097` at session-local
`container_id=2`, `slot_index=1`; replay returned
`shadow_plan_ready_for_operator_review`, and the separately confirmed receipt
is `accepted`. Its acceptance basis SHA-256 is
`b6d08795b7f7352da96dd250aab98f17a8bb8b3e093689e7fe836636e5acf9e7`.
The scenario pack passed `30/30`, targeted acceptance validation passed
`44/44`, and runtime, dispatch, execute-once, promotion, item movement, and
intrusive-action fields remained false/empty.

P11 operational shadow acceptance completed on 2026-07-15. The fixed sandbox
adapter observed the exact allowlisted party target `268435471 / amir to moja
dziwka` at `53%` HP, distance `0`, on the same floor and visible, while the
local player `268435472 / el cvvel` remained excluded as self. The persisted
profile is `shadow_only`, uses retry budget `0`, and has canonical SHA-256
`c499ef6bfb059705f670c8ed8f239e00765463a6869934582718116b88bb4c00`.
Replay returned `would_plan_sio` without casting. The accepted receipt is
`heal-friend-shadow-acceptance-82535ea97fd19483`, binds canonical report
SHA-256 `b6d5f8e53c7e7354445ab9b134b4b04a7bda984df93c477ed2cbb2a57d575ed8`,
and has acceptance-basis SHA-256
`82535ea97fd19483f704451972f21cc56405c82cc0749f26724bce51cd774358`.
Runtime, dispatch, execute-once, promotion, cast, talk, and intrusive-action
fields remained false/empty. P12 is the next phase and still requires separate
per-lane execute-once reviews; P11 acceptance grants no P12 action authority.

Status: P8, P9, P10, and P11 are `operational_acceptance_complete`. P12 execute-once
review is `closed_with_deferred_heal_friend_lane`.
Current accepted-lane marker: Conditions and Equipment lanes are `operational_acceptance_complete`.
Heal Friend is `closed_blocked_no_compatible_vocation`. Equipment completed through separately approved
Registry v1 plan `d041db806c6417b018c6ae390e3d384ccec9bead2a77e498a582093bf7c823e0`:
accepted receipt `p12-equipment-bdf7027cf48c438d` records one attempt, zero
retry, `killed_and_disarmed`, and no downstream or live authority.
Historical evidence follows: P9's
first real passive trace remained fail-closed on `protection_zone_unknown` and
`condition_unknown`. The repo-only adapter candidate now uses the fork-proven
`player:getStates()` bitmask plus fork-proven `getSpeed()`/`getBaseSpeed()`
fallback and passed the approved in-world sandbox
session on 2026-07-14: module attach `4/4`, full attach `16/16`, and runtime
module gates `19/19`, with runtime continuously disarmed. The real sandbox
observation reported `protection_zone=inside` from `player_states`, paralyze
`absent`, and cooldown `ready`, with every execution flag false. Operational
`otp9` remains blocked until this adapter is promoted through a separately
approved Helper live release and a fresh live observation is collected; the
strict observer correctly rejected an attempted mixed live/sandbox evidence
path as `capability_explicit_path_mismatch`. The passive
P10 implementation was promoted only after its separate
v2.3.3 sandbox and explicit live gate passed. The promoted v2.3.4 hardening lane
adds cross-fork/no-focus startup and cross-consumer P10 receipt enforcement.
The v2.3.5 candidate adds the missing passive Recovery trace/proof producer,
safe local P10 capture override, exact slot binding, and P10.1 consumer closure;
it does not change operational acceptance. P9 is `offline_implementation_complete`; its
operational acceptance no longer depends on P8, but still lacks a reviewable
real Conditions trace. Canonical
Recovery predecessor trace/proof can now be produced passively, but the data-only P9 acceptance boundary is
implemented, but current evidence cannot create an accepted receipt. P10 now has
its own operational input and receipt boundary, but remains blocked. The live-promoted v2.3.6
lane adds only the fixture P11 exact-target replay and passive Helper scan
boundary; it does not change P8-P10 operational acceptance.
The live-promoted v2.3.7 lane expands P10 fixture coverage to 30 exact mutations and
closes time-override, scenario-path, nested-schema, and consumer-parity gaps;
it still cannot create operational acceptance or execute an item action.
The live-promoted v2.3.8 lane closes Helper safe-boot lifecycle bypasses and
loads Lua profiles/preferences with no OTClient or filesystem authority. Its
promotion is package hardening only and does not alter P8-P10 acceptance state.

## Operating Contract

The one-screen constraint is a product requirement, not an operator preference.
Routine Codex work must use `BackgroundNoScreen`: no mouse or keyboard input,
window focus, screenshots, client launch/stop, sandbox UI, or writes inside the
live client. Passive reads may consume bounded, sanitized heartbeat, log, process,
manifest, and hash evidence. Writes are confined to repo-local `runtime/` evidence.

Visual acceptance is not silently removed. UI-layout work waits for a separate
runner/VM or an explicit user-provided visual review. Live promotion remains a
separate, explicit wrapper action and never follows from background evidence.

## Product Topology: Helper Mainline And CTOA Safe

The Helper remains the main CTOAi OTClient project and owns the P8-P16 sequence.
It is the full operator platform: evidence and acceptance gates, profiles,
advanced configuration, Conditions, Equipment, Heal Friend, Combat and CaveBot
design/replay lanes, Control Center integration, and future sandbox bridges.
CTOA Safe does not replace the Helper and must not reduce or redirect the
Helper roadmap.

CTOA Safe is a secondary, deliberately constrained product lane. Its purpose is
to provide a compact, movable, minimalist in-client panel for the small set of
automations an operator wants close at hand. The visible module labels and their
order are product-owned and fixed; each supported module may expose a broad,
purpose-built editor without turning the panel into another full Helper.

CTOA Safe target scope:

- compact movable window, low visual footprint, fixed module labels, and one
  explicit master arm/disarm control;
- editable healing thresholds, spells, potions, cooldowns, and hotkey bindings;
- editable ordered combat spell rotations, per-entry conditions and cooldowns;
- editable Exeta rotations, including spell order, intervals, and minimum nearby
  creature conditions;
- narrowly scoped Conditions and Timer editing where it preserves the same
  compact interaction model;
- local, versioned, schema-validated presets with safe defaults, atomic saves,
  bounded values, and explicit import/export suitable for moving the same setup
  between supported clients;
- safe boot: loading the mod or a preset never arms runtime automation.

CTOA Safe permanent exclusions:

- no CaveBot, waypoint editor, route runner, movement automation, or hidden
  CaveBot compatibility switch;
- no generic Settings module or open-ended settings screen;
- no scripting console, arbitrary Lua editor, plugin marketplace, Control Center
  cockpit, or duplication of the Helper's evidence/acceptance platform;
- no automatic migration of a full Helper profile into executable Safe behavior.

The current `mods/ctoa_safe` prototype is an input to this lane, not the final
scope contract. Copied Helper surfaces that conflict with these boundaries,
especially CaveBot and generic profile/settings machinery, must be removed or
reduced before CTOA Safe is considered product-ready.

### CTOA Safe Delivery Lane

1. **S0 — Scope freeze and reduction:** define the fixed label set, remove
   CaveBot and generic Settings surfaces, inventory copied Helper dependencies,
   and keep only code required by the compact product.
2. **S1 — Editable rotations:** complete ordered spell and Exeta rotation editors
   with add/remove/reorder, per-entry validation, bounded timing/condition fields,
   and deterministic runtime selection.
3. **S2 — Mobile preset contract:** move editable data to a non-executable,
   versioned schema; provide atomic save, named presets, explicit import/export,
   migration, validation, and fail-closed recovery from malformed data.
4. **S3 — Minimal UI acceptance:** verify the fixed-label compact layout,
   movable-window persistence, keyboard-only access, clear armed state, and no
   accidental growth into Helper-style navigation. Visual acceptance follows the
   separate runner/VM or explicit user-review rule above.
5. **S4 — Separate package and release gate:** give Safe its own manifest,
   sandbox checks, evidence, versioning, and explicit promotion action. Safe
   acceptance must never satisfy or bypass a Helper P8-P16 gate.

S4 implementation status (2026-07-14): `complete_for_v2.8.0`; the separate
`v2.9.0` candidate requires a new sandbox and release cycle.
`scripts/windows/solteria_safe_release.ps1` now validates and promotes exactly
the three Safe files with an explicit approval switch, timestamped backup,
content-bound manifest, source/live SHA-256 parity, and unchanged live-process
proof. Safe `v2.8.0` was promoted 3/3 to the live Solteria tree; backup:
`runtime/solteria_safe_release/live_backup_20260713-015729`. PID 17988 remained
unchanged. The later sandbox visual report passed 10/10 for v2.8.0. File parity
and Safe acceptance remain independent from every Helper gate.

Safe implementation may progress alongside passive/offline Helper work, but
Helper milestones have priority when both lanes compete for the same runtime,
release, or validation work. Reusable schema, persistence, and guard utilities
may be shared only when their product policies remain separate and tests prove
that Safe exclusions cannot be re-enabled through shared Helper configuration.

S0 implementation status: `complete`. Package `v2.4.0` introduced the exclusive
per-login project loader documented in
`docs/otclient/CTOA_EXCLUSIVE_PROJECT_LOADER_V1.md`. Only the neutral chooser
autoloads; Helper and Safe reject direct startup, terminate on logout, and cannot
run together. The staged Safe tree has no copied Helper runtime files, CaveBot,
or generic Settings surface. The later v2.8.0 sandbox selection/ENABLE and
separately approved promotion provide operational crash closure.

The staged Safe `v2.0.1` hardening additionally replaces the invalid
zero-argument spectator query reached after ENABLE with the fork-proven bounded
center-position signature. Lua fixture evidence covers the exact native call
shape, but operational crash closure still requires the sandbox smoke above.

S1/S2 implementation update (2026-07-13): Safe `v2.8.0` exposes fixed
Healing, Combat, Conditions, Support, and Timer labels. Healing, Targeting,
Spell Rotation, and Support use purpose-built ordered list editors with
add/remove/edit/reorder operations and selection-to-form hydration. Their data
is bounded and persisted through the dedicated `ctoa-safe-profile-v2` JSON
contract; runtime-only timestamps are stripped during export. Support remains
default-off and Safe remains globally disarmed at boot. Target dispatch is
idempotent: an already attacked creature is not attacked again every tick.
The Healing editor now has independently configurable HP and mana thresholds,
bounded randomization, hotkey fallback, and drag-and-drop item slots. Support
rules are typed as spell or item and may trigger always, on HP, or on mana with
a randomized threshold range. Combat rotation entries use one compact
`require monster count` checkbox, a minimum count, and an explicit per-spell
distance. Editor close controls are inset from the content edge and primary
panel labels use a larger font scale. These changes do not alter safe boot,
module exclusions, or Helper gate ownership.

S1/S2/S3 candidate update (2026-07-14): repo-only Safe `v2.9.0` replaces the
remaining text-only Exeta configuration with an ordered editor and per-entry
monster/cooldown fields. `ctoa-safe-profile-v3` stores up to 12 named presets,
migrates v2 once, rejects unknown v3 fields, uses atomic save with retained
backup, and provides fixed-path import/export without arm state or runtime
timestamps. Restored geometry is clamped and Ctrl+Tab/Ctrl+Shift+Tab/Ctrl+E/
Ctrl+Space provide bounded keyboard navigation. S1/S2 implementation is
complete in source; S3 and the next S4 release remain pending sandbox visual
and explicit live approval.

### Cross-Fork OTS Connection Profile Lane

The planned OTC/OTCv8/OTC Brasil/fork connection layer is a separate platform
lane, not a Safe runtime module. Its contract is documented in
`docs/otclient/CTOA_ENCRYPTED_SERVER_PROFILE_DESIGN.md`: one normalized,
UI-friendly server profile; fork capability adapters; OS-keystore-backed local
secrets; authenticated encrypted profile envelopes; certificate/public-key
pinning where supported; and an explicit connect action. No password, token,
private key, or decrypted profile may enter Git, Engine Brain packs, logs, or
generated evidence. Implementation starts with passive capability discovery
and import/export validation before any login/connect adapter is enabled. The
public portable subset is schema-closed by
`schemas/otclient-server-profile.schema.json`; unknown adapters, unpinned keys,
and plaintext secret fields fail validation.
The first passive implementation is now present in
`scripts/ops/otclient_fork_capability_detector.py`. It identifies the available
source checkout as `redemption-mehah`, reports only proven file/API
capabilities, does not inspect profiles or credentials, and makes no connection.
Protected live packages without public fork markers remain `unknown` rather
than inheriting a guessed adapter.

The primary Helper continues independently as `v2.4.1`. Its guarded targeting
path applies the same idempotent-current-target rule without broadening any
P8-P16 permission or acceptance boundary. P8-P11 operational acceptance states
remain unchanged.

Safe `v2.8.0` operational acceptance update (2026-07-13): sandbox visual
acceptance passed for Healing item slots and HP/mana randomization, Support
`ITEM + MANA` drag-and-drop and JSON persistence, Combat monster-count/distance
controls, readable labels, and in-bounds editor close buttons. The test item
`23375` was assigned and persisted while Safe and Support remained disarmed.
Helper attach evidence passed 4/4 modules and 16/16 full tabs; runtime module
gates passed 19/19. The official wrapper promoted the current manifest to live
with backup `runtime/solteria_helper_dev/live_backup_20260713-021234`; repo,
stage, and live Safe hashes match. Release gate and GoalStatus both report
complete with no blockers.

Client feature extraction is also complete for the two requested shortcuts:
`Ctrl+Y` maps to `game_shaders` (Map/Outfit/Mount/Text), while the dynamic
registry proves `Ctrl+Shift+C` maps to `Debug / Toggle Chromium Color Test`
from `/webview_color_demo/webview_color_demo.lua:108`. Both complete module
trees are preserved under `C:/Users/zycie/Desktop/shader map outfit etc`.

## Phase Sequence

### P8 — BackgroundNoScreen Foundation

Objective: make routine Helper validation non-intrusive while the user plays.

State: `operational_acceptance_complete` since 2026-07-14. Acceptance proved an
official promotion-bound trusted pin, a fresh capability heartbeat, and full
producer/consumer parity for the no-action contract together.

Deliverables:

- bounded shared parsers for the current helper session, API probe, runtime state,
  and capability heartbeat;
- deterministic passive reporter path under the client work directory;
- `BackgroundStatus` wrapper action and `ctoa.ps1 otbg` shortcut;
- inherited, non-downgradable `BackgroundNoScreen` operator mode with a positive
  action allowlist and guards around GUI/input/screenshot/start-stop/live-write
  primitives;
- sanitized `background_status.json`, release-evidence summary, and read-only
  Control Center tile;
- mutable profile drift separated from immutable package-code parity.
- strict pin provenance classification plus read-only diagnostic parity that
  cannot create, repair, rebind, or accept a trust anchor.

Done gates:

- no client process or screenshot-count change during collection;
- immutable live files match a manifest pinned by an official promotion record
  and remain unchanged during the observation; the observer never creates or
  repairs that trust anchor itself;
- readiness requires exactly one canonical live process plus an online,
  5-second heartbeat newer than that process; missing safety fields, an
  untrusted promotion pin, or cross-client evidence fail closed;
- any drift in a Lua vocation profile is reported separately but still blocks
  parity because the current profile format is executable; it cannot become a
  non-blocking data change until persistence moves to a non-executable format;
- missing, stale, malformed, oversized, symlinked, or unsafe capability evidence
  never claims readiness;
- the report is advisory-only with `promotion_allowed=false`,
  `dispatch_allowed=false`, and an empty intrusive-action ledger;
- Python, Lua, PowerShell, web, release-evidence, doc-sync, and secret-guardrail
  tests pass.

Historical pre-acceptance evidence was `legacy_or_unbound_attestation`: all 58
manifest entries were safe to inspect, 57 matched, and one executable profile
drifted. It remained diagnostic-only and was not rebound into trust. Final P8
acceptance used a new official promotion-bound pin, one fresh `v2.4.1`
heartbeat newer than the canonical process, `62/62` live hash parity, and full
no-action consumer parity while process and screenshot invariants stayed
unchanged.

### P9 — Conditions Shadow Observation And Replay

Objective: validate only `plan_paralyze_recovery` from passive observations before
any execute-once design.

State: `operational_acceptance_complete` since 2026-07-14. Canonical contract:
`docs/otclient/P9_CONDITIONS_SHADOW_REPLAY_DESIGN.md`.

Acceptance dependencies were explicitly accepted P8 operational acceptance,
including its trusted promotion pin, fresh heartbeat, and full consumer-parity
proofs; a real current Conditions observation; and canonical ready, hash-bound
Recovery trace/proof reviewed inside P9 acceptance. Those dependencies passed
together before the accepted receipt was written. Offline/staging replay still
cannot claim runtime readiness or independently unlock a downstream phase.

Deliverables: sanitized Conditions observation schema, freshness/PZ tri-state,
action-bound trace replay, deterministic positive and negative scenario pack, and
read-only Control Center evidence. Before profile drift can be accepted as data,
profile persistence must gain a non-executable, schema-validated representation.

Implemented evidence: strict profile/observation/P8/Recovery/trace/report schemas,
the existing-heartbeat passive producer, bounded sanitizer, 44-case deterministic
fixture pack, canonical passive Recovery pair producer, `ctoa.ps1 otp9`,
`ctoa.ps1 otp9accept`, atomic runtime report, Release Evidence summary,
read-only Control Center tile, and a separate strict data-only operator acceptance
schema/preflight. Its writer revalidates fresh canonical evidence, hashes,
no-action invariants, reparse safety, and exact confirmation before an atomic
receipt write. The persisted receipt is `accepted` and binds the independently
recomputed canonical report SHA-256. All action, dispatch, execute-once,
promotion, and intrusive-action fields remain disabled or empty.

Done gates: stale/offline/dead/PZ/wrong-condition/wrong-spell/cooldown/retry cases
fail closed; replay parity is deterministic; runtime and dispatch remain false;
an accepted receipt requires a fresh real trace, canonical raw P8 and Recovery
inputs, exact `accept P9 conditions shadow` confirmation, and separate downstream
review.

### P10 — Equipment Ring-Only Shadow And Rollback Replay

Objective: validate one ring-swap plan and its rollback without touching inventory.

Dependencies: explicitly reviewed action-bound P9 trace plus its validated
data-only acceptance receipt. Neither artifact authorizes runtime dispatch.
Those dependencies and the separate P10 operational evidence are accepted.
State: `operational_acceptance_complete` since 2026-07-15; neither receipt
authorizes runtime dispatch.

Deliverables: a sanitized passive adapter observation, operator-configured exact
item/slot/container capture profile, canonical snapshot producer, zero-retry
plan, rollback simulation, tamper detection, raw-report-bound P9 receipt, and a
30-case negative scenario pack. `ctoa.ps1 otp10` produces the snapshot and runs
the operational replay; `ctoa.ps1 otp10accept` is the separate hash-bound exact-
confirmation receipt boundary. Real IDs are confined to the fixed ignored
`.ctoa-local/otclient` override; the tracked template is permanently unconfigured.
Release Evidence, P7, and Control Center expose
replay and acceptance separately. Neither command dispatches or promotes.

Done gates: ambiguous inventory, revision drift, missing slot, wrong IDs, missing
rollback, stale evidence, PZ, fixture provenance, noncanonical paths, or a P9
receipt/raw-report mismatch block readiness; no amulet or rotation scope. P11
eligibility requires both a strict fresh operational blocker-free P10 report and
its matching accepted non-fixture receipt. Both passed before P11 acceptance;
the P10 receipt still grants no execute-once authority.

### P11 — Heal Friend Exact-Whitelist Shadow And Replay

Objective: validate one `exura sio` decision without casting.

Dependencies: accepted P9 and P10 traces.

Deliverables: persisted whitelist revision, stable creature ID/name, real party-ID
membership, fresh HP/range/floor/visibility evidence, and deterministic replay.

Current status: `operational_acceptance_complete`. The fixed synthetic profile
and observation remain as deterministic regression fixtures, while the real
sandbox producer, exact-target local profile, operational replay, and separate
hash-bound acceptance receipt are complete.
The reviewed Vithrax/vBot spectator/Sio pattern has been capability-mapped into
the Helper without copying its macro or action paths. The passive scan now
requires one configured stable ID plus canonical name, party membership,
visibility, same floor, range, and valid HP; ranking and fallback were removed.
`HealFriendNoTargetSmoke` passes, the static runtime gate passes `9/9`, and the
final focused P11 validation passed `34 passed, 1 skipped` before acceptance;
the acceptance validator then passed `17 passed, 1 skipped`. The operational
receipt remains explicitly ineligible for runtime readiness or P12 without a
new, separate execute-once review.

Done gates: self/spoofed/changed/stale/non-party/out-of-range/PZ/cooldown cases fail
closed; whitelist mutation, ranking, multi-target healing, and dispatch remain out.

### P12 — Execute-Once Sandbox Acceptance

Objective: introduce separate, manually approved sandbox bridges in the order
Conditions, Equipment, Heal Friend.

Dependencies: complete P9-P11 shadow packs and a separate per-lane review.

Done gates for each lane: exactly one bounded action, current domain evidence,
operator confirmation, result trace, immediate KILL/disarm, zero automatic retry,
and no implication of live promotion. A lane cannot inherit another lane's approval.

Historical Conditions preparation evidence (2026-07-15): the separate execute-once bridge,
session-approval contract, execution-approval contract, and terminal receipt
validator and the sandbox-only command transport are implemented. Focused
validation passed `93/93`; `ValidateDev`
passed `154/154`; `SmokePreflight`, `ModuleContract` (`32/32`), and
`ModuleStaticGates` (`39/39`) passed against the current manifest. The current
hash-bound plan is
`ce7f011bea67fcd75f0004557e91279f5cc58ddfa820311ce83adceb618aca07`
with no blockers. Its state is `ready_for_sandbox_session_approval`, attempt
count `0`, runtime/dispatch/execute-once/live-promotion flags false, and no
intrusive actions. No sandbox package sync, cast, or live promotion has occurred
under P12.

The Conditions sandbox session was separately approved on 2026-07-15 as
`p12-conditions-session-7932a9fab7954713`, bound to the plan and accepted P9
receipt. The stale sandbox process was replaced through the official wrapper;
the new sandbox boot reached and executed the neutral chooser loader while the
live process remained unchanged. Execution approval is still false, attempt
count remains zero, and the operator must select CTOA Helper and enter the
sandbox character before attach/readiness evidence can be collected.

The refreshed in-world session then passed `ReadyCheck`, Conditions attach,
`SmokeAttachModules` `4/4`, `SmokeAttachAll` `16/16`, and
`RuntimeModuleGatesSandboxSmoke` `19/19`, all against manifest SHA-256
`79465eb48ef484f5994451a193e833d31f7c9e00e064cea4b341500a917b1923`.
The current execution preflight is `waiting_for_paralyze`: the guarded heartbeat
is fresh, online/alive/outside-PZ, cooldown-ready, runtime-disarmed and no-action,
but `condition_state=absent`. The attempt remains unconsumed and execution
approval remains false until a fresh observation reports paralyze present.

The next bounded observation reported paralyze `present` with a 789 ms heartbeat
age and no blockers, so the Conditions lane reached
`ready_for_execution_approval`. The official wrapper now repeats this preflight
after execution approval and immediately before command delivery; if the
condition expires, it sends no command and leaves attempt count zero.

Before command delivery, the operator corrected the exact EK recovery spell:
the canonical EK profile and live capability both prove vocation `ek` and
`ctoa_ek_profile.healing.spell = "exura ico"`. No command had been sent and
attempt count remained zero. The former `exura` plan
`ce7f011bea67fcd75f0004557e91279f5cc58ddfa820311ce83adceb618aca07`
and its approvals are superseded and cannot authorize the corrected action.
The new plan binds vocation `ek`, the EK profile hash, action
`cast_exura_ico`, spell `exura ico`, and accepted P9 condition evidence; its
SHA-256 is
`93a99ec795c93641017eac3a8fe258c324a581e0d8aeb279fa8ba3bb950ce17f`.
Focused tests passed `27/27`, `ValidateDev` passed `154/154`, and current
static gates passed `39/39`. A new plan-bound sandbox session approval and
fresh in-world evidence are required before execution can be reconsidered.

The corrected EK session was approved as
`p12-conditions-session-709b17c7269d4ede`. Sandbox PID `27324` loaded the
`exura ico` module with stage/sandbox SHA-256 parity while live PID `29352`
remained unchanged. The corrected manifest then passed `ReadyCheck`, module
attach `4/4`, full attach `16/16`, and runtime gates `19/19`. Current execution
preflight remains blocked without consuming an attempt because paralyze is
absent and the game cooldown group is active; runtime is still disarmed and no
command has been delivered.

Final Conditions acceptance (2026-07-15): the first approved command was held
before the executor because the old observer reported `paralyze_not_present`;
its trace proved `result=not_called` and terminal `killed_and_disarmed`. Review
found two fail-closed defects: a rejected guard consumed the attempt counter,
and boolean `false` values were serialized as empty strings. The bridge now
increments `attempt_count` only immediately before a real executor call and
preserves boolean terminal fields. The condition adapter and direct P12 guard
also share the fork-proven speed fallback because this client can visibly show
paralysis without setting state bit `32`. Regression tests passed `14/14`, full
`ValidateDev` passed `154/154`, module attach passed `4/4`, full attach passed
`16/16`, and runtime gates passed `19/19` against manifest SHA-256
`81d6ced724ac99ee3e3a91e336f4506d7218c882c7addcd5a12620453cb80e71`.

The replacement plan
`67c27a26797b0b01e4f8dfccec4e02b0e5f454ca6818434709e4b55850f49810`
was separately approved for session and execution. The official wrapper made
exactly one executor call for `cast_exura_ico`; trace result was `success`,
attempt count `1`, retry scheduled `false`, and terminal state
`killed_and_disarmed`. Receipt `p12-conditions-78a8b689653640af` is `accepted`
with no blockers and grants no downstream authority. The sandbox runtime remains
disarmed, only the sandbox client process is running, and live was untouched.
That Conditions receipt granted no Equipment authority; the subsequent separate
Equipment lane and its result are recorded below.

First Equipment execute-once result (2026-07-15): plan
`f129ccaefd6b9c0ca9b6d7bdba69addc6c8cd20c4233c196aa625daceea9432f`
was separately approved for the sandbox session and execution. The official
wrapper dispatched exactly one request to move source item `3097` from dynamic
`container_id=3`, `slot_index=1` onto the ring slot occupied by `3096`.
The terminal log proves `attempt=1`, `result=requested`, `retry=false`, and
`final=killed_and_disarmed`; no retry occurred and only sandbox PID `21124`
was running. The original postcondition was incorrect for this server because
ring IDs transform across the equipment boundary: the passive reporter briefly
observed equipped `3099`, then the ring slot became empty, while source slot
`3/1` contained transformed rollback item `3093`. Reconciled receipt
`p12-equipment-4716714ecc674b47` is therefore correctly `rejected`; it grants
no acceptance or downstream authority. A replacement Equipment attempt must
use separately reviewed backpack/equipped ID pairs (`3097 -> 3099` and
`3096 -> 3093`), a fresh prepared inventory state, and new plan-bound session
and execution approvals. The consumed attempt must never be replayed.

Equipment Family Registry v1 is now the corrective design boundary. It models
`3093/3096` as one ring family and `3097/3099` as another, with separate
inventory, equipped, and returned states. The Helper UI exposes disabled-by-
default family checkboxes instead of editable numeric IDs; selecting a family
does not arm runtime or authorize an item move. Unknown ID transitions produce
only a passive `review_required` proposal. The registry is slot-generic for
future amulets, but P12 execution remains strictly ring-only and a new registry-
bound plan plus two new approvals are required before another attempt.

Fresh Registry v1 sandbox evidence (2026-07-15): official `SmokePreflight`
passed for the 62-file manifest, stage/sandbox registry SHA-256 matched at
`c9061af7927e0863de637b7e5db7924401162a178f392f3394cdedf161cab8a6`,
and sandbox PID `8484` remained runtime-disarmed. The Equipment view visibly
showed separate `Primary ring` and `Secondary ring` checkboxes, both OFF, with
no raw-ID input or layout overlap. Module attach passed `4/4`, full in-world
attach passed `16/16`, and runtime module gates passed `19/19`. No family was
enabled and no equipment action, retry, or live promotion occurred.

Final Equipment acceptance (2026-07-15): Registry v1 plan
`d041db806c6417b018c6ae390e3d384ccec9bead2a77e498a582093bf7c823e0`
was separately approved for session and execution after current manifest-bound
attach/runtime gates, fresh sandbox capability, and prepared inventory evidence
passed. The official wrapper made exactly one request to move `3097` onto the
ring slot. The terminal observation verified equipped `3099` and transformed
rollback item `3093` in source container `2`, slot `1`. Attempt count was `1`,
retry remained `false`, and final state was `killed_and_disarmed`. Receipt
`p12-equipment-bdf7027cf48c438d` is `accepted`, grants no downstream authority,
and did not touch a live client. The earlier rejected attempt remains immutable
historical evidence and cannot be replayed. P12 Heal Friend plan
`964ff8f0c178c7b646a565380e96846a8b29780eb02a734a259713d9ccf023b3`
is now `closed_blocked_no_compatible_vocation`. Its bridge is present in the
63-file manifest, attach/runtime evidence passes `4/4`, `16/16`, and `19/19`,
and the plan binds ED plus the exact accepted P11 target policy. The sandbox
session was approved, then a fresh preflight stopped on the single
`vocation_must_be_ed` blocker. Because the operator has only sorcerer and knight,
`p12_heal_friend_no_compatible_vocation_closure.json` expires that approval and
forbids execution or reuse. Attempt count remains `0`, retry false, final state
`disarmed`, no cast occurred, and no downstream or live authority exists.
The earlier phrase "P12 Heal Friend is now the next" and historical marker P12
is `in_progress`, plus `plan_ready_for_sandbox_session_approval`,
`ready_for_sandbox_session_approval`, and Heal Friend `not_started` are
superseded and retained only for compatibility with older read-only cockpit checks.

### P13 — Runtime Evidence And Machine-Readable Roadmap State

Objective: make P8-P12 state replayable and drift-resistant.

Status: `runtime_evidence_ready`. The terminal no-action
Heal Friend closure is represented as the seventh immutable ledger entry without
reopening P12 or introducing an executor. Schemas, generator, dry-run audit,
read-only Control Center consumption, release-evidence phase state, and tests are
complete. The exact confirmed fixed-output refresh is audit-bound and P13 grants
no runtime, live, MCP-write, or reopened P12 authority.

Deliverables: bounded decision/result ledger, SHA-pinned versioned schema registry,
artifact freshness and tamper status, read-only Control Center cards, and generated
`ROADMAP_STATE.json/md`.

Done gates: atomic writes, path confinement, symlink rejection, redaction, stable
schema tests, pack parity, and an audited dry-run contract. Enabling another MCP
safe-write tool requires a separate review; the P7 tool count does not grow here.

### P14 — Independent Runner And Release Automation

Objective: move visual and in-world regression work away from the user's only screen.

Status: `foundation_in_progress`. The v1 signed artifact-only request/result
contract, tracked-source Helper manifest derivation, clean-checkout/revision binding,
tamper/path-confinement tests, deterministic manifest rollback replay, and clean
Windows CI job are implemented. This foundation launches no client, uses no operator
workstation focus/input, grants no promotion/live authority, and adds no MCP tool.
P14 remains open until a real second machine/VM returns matching signed evidence and
completes isolated visual/in-world plus actual canary/rollback rehearsals.

Deliverables: second-machine/VM runner contract, artifact-only handoff, CI schema and
replay checks, signed manifest/evidence bundle, canary/rollback evidence, and explicit
promotion approval outside plugin MCP actions.

Done gates: no operator workstation focus/input dependency, reproducible clean-runner
evidence, immutable artifact provenance, and tested rollback.

### P15 — Combat Design-Only Digital Twin

Objective: model monster-only combat risks without an attack executor.

Dependencies: P8-P14 complete and a new formal risk review.

Scope: target identity, player/NPC/PZ guards, spell/rune budgets, cooldowns, kill
switch, deterministic replay, and adversarial scenarios. `g_game.attack`, rune use,
and live dispatch remain forbidden in this phase.

### P16 — CaveBot Design-Only Digital Twin

Objective: model movement/path/retry/stuck behavior independently of Combat.

Dependencies: P15 review complete; a separate movement risk review.

Scope: route provenance, floor/PZ transitions, reachability, retry budgets, stuck
detection, and kill switch. `autoWalk` and live movement remain forbidden.

## Beyond P16

Only accepted low-risk lanes may enter an explicit live-canary program. Combat and
CaveBot require separate canaries and must never be opened by a generic static gate.
TFS/protocol indexing remains read-only until real source is supplied. Multi-client
or hosted operation starts only after provenance, tenancy, secrets, rollback, and
operator-authorization models have their own evidence-backed phase.

## Commit And Release Boundaries

1. P8 implementation ships as one reviewable background-observability bundle;
   operational acceptance remains separate and fail-closed until its three
   required proofs pass together.
2. P9, P10, and P11 remain separate commits/PRs and cannot share acceptance evidence.
3. P12 uses one bridge commit and one acceptance record per lane.
4. P13/P14 are platform work and do not smuggle runtime executors into evidence code.
5. P15/P16 remain design/replay only until new user approval and new gates exist.
