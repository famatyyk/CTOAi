# Solteria Helper Supplemental Refactor Plan

## Current State

- Static helper pack: `passed`.
- Module static gates: `passed (31/31)`.
- Local ready: `ready_for_sandbox`.
- Sandbox queue: `ready_for_operator`.
- Helper shell budget: `needs_extraction`, `4222` lines and `165` functions.
- Live status: not ready for live promotion.

The current refactor keeps runtime execution in the guarded helper shell. Passive
policy, planning, summary, and UI responsibilities should continue moving into
named modules with static contracts before any runtime bridge is expanded.

## Completed In Current Slice

- Runtime policy now owns protection-zone policy metadata and the final PZ
  decision.
- The native helper shell now collects guarded OTClient observations and asks
  `CTOA_HELPER_RUNTIME_POLICY.protectionZoneDecision(...)` for the block result.
- Module contract now records runtime-policy ownership for PZ policy and PZ
  decision.
- Helper shell PZ logic is smaller while still failing closed when the policy
  module is unavailable or errors.
- Profile persistence now owns passive profile export grouping through
  `ProfilePersistence.exportProfile(...)`; the shell keeps save execution,
  autosave scheduling, and fallback-only profile assembly.
- Targeting now owns passive creature-type decisions through
  `Targeting.creatureTypeDecision(...)`; the shell keeps guarded OTClient
  method reads and attack execution.
- Timer runtime now owns passive timer dispatch/status decisions through
  `TimerRuntime.dispatch(...)`; the shell keeps guarded `castSpell(...)`,
  `last_timer_ms`, and runtime execution.
- Static smoke checks now require the new timer dispatch contract and the
  combat adapter's current `adapter_text` handoff rather than stale shell-only
  suffix strings.
- Cavebot runtime now owns passive adapter summary, movement capability
  normalization, and movement probe snapshot normalization through
  `CavebotRuntime.adapterSummary(...)`,
  `CavebotRuntime.movementCapability(...)`, and
  `CavebotRuntime.probeSnapshot(...)`.
- Cavebot runtime now owns the passive adapter summary-to-status pipeline
  through `CavebotRuntime.adapterStatusSummary(...)`; the native shell still
  supplies guarded online/PZ/route context and only fits the returned status for
  UI display.
- Cavebot runtime now owns the full passive movement probe report assembly
  through `CavebotRuntime.probeReport(...)`; the native shell still reads
  guarded OTClient movement APIs and only sends the report text to status.
- The native helper shell still performs guarded OTClient reads, `findPath`, and
  `autoWalk`, but no longer builds cavebot adapter-summary callbacks inside the
  runtime loop.
- Route now owns passive CaveBot editor state and delete-confirm request
  metadata through `Route.uiState(...)` and `Route.deleteRequest(...)`; the
  native shell still renders widgets and executes guarded modal confirmation.
- Combat runtime now owns passive spell cooldown/readiness row normalization
  through `CombatRuntime.spellReadiness(...)`; the shell still performs guarded
  creature scanning and spell mob-count observation, while attack/cast execution
  remains in the guarded helper runtime.
- Combat runtime now owns passive combat adapter summary assembly through
  `CombatRuntime.adapterSummary(...)`; the shell passes guarded online/PZ/target
  observations and only fits the returned text for UI display.
- Combat runtime now owns passive decision-state summary shaping through
  `CombatRuntime.decisionStateSummary(...)`; the native shell still reads
  guarded online/PZ/rune state and performs the final UI text fitting, while
  attack, cast, rune, and exeta execution remain shell-owned.
- Diagnostics now owns central API probe status/detail text assembly through
  `Diagnostics.apiProbeText(...)`; the shell still performs guarded OTClient API
  reads, retry scheduling, snapshot recording, and UI refresh.
- Diagnostics now owns passive API/magic probe deferred-retry decisions through
  `Diagnostics.probeDeferredPlan(...)`; the shell still owns `delay(...)`,
  startup retry scheduling, guarded OTClient reads, snapshot recording, and UI
  refresh.
- Diagnostics now owns passive diagnostics snapshot UI row descriptors through
  `Diagnostics.snapshotUiRows(...)`; the shell still owns widget existence
  checks, `fitText(...)`, and `setText(...)`.
- Cavebot runtime now owns passive movement-reset trace text through
  `CavebotRuntime.traceText("movement_reset", ...)`; the shell still resets
  retry/stuck state and only emits the module-owned status message.
- Cavebot runtime now owns the movement probe report handoff through
  `CavebotRuntime.probeReport(...)`; the shell no longer orchestrates separate
  `probeSnapshot` and `probeSummary` calls.
- Cavebot runtime now owns path-result status text through
  `CavebotRuntime.pathText(...)`; the shell still performs the guarded
  `g_map.findPath` read and only passes the passive result snapshot with
  fallback `n/a`.
- Cavebot runtime now owns passive movement status/trace prose for walk
  attempts, test walks, retry-budget blocks, and walk-failed blocks through
  `CavebotRuntime.statusText(...)` and `CavebotRuntime.traceText(...)`; the
  native shell still mutates retry state and performs guarded `player:autoWalk`.
- Cavebot runtime now owns passive walking-status assembly through
  `CavebotRuntime.walkingStatus(...)`; the native shell still resolves the
  current route label/retry snapshot and performs guarded `player:autoWalk`.
- Diagnostics now owns passive smoke-command parsing, tab/subtab target
  normalization, and smoke status text through
  `Diagnostics.parseSmokeCommandText(...)`,
  `Diagnostics.smokeCommandTarget(...)`, and
  `Diagnostics.smokeTabStatusText(...)`; the native shell still reads/removes
  the command file, focuses widgets, and executes the guarded smoke action.
- Route now owns passive CaveBot editor action dispatch through
  `Route.editorAction(...)`; the native shell still reads the player position,
  preserves the delete confirmation modal, marks profiles dirty only from the
  route-owned result, and never moves/pathfinds from the route module.
- Combat runtime now owns passive rotation spell selection through
  `CombatRuntime.rotationSpell(...)`; the native shell still observes nearby
  monsters, builds spell rows from guarded scan results, and keeps all
  `castSpell(...)` execution inside the guarded helper runtime.
- Combat runtime now owns passive offensive action status text through
  `CombatRuntime.actionStatusText(...)`; the native shell still enforces PZ,
  action-lock, recovery-gap, cast, and rune execution guards.
- Combat runtime now owns passive targeting status text through
  `CombatRuntime.targetingStatusText(...)`; the native shell still performs
  guarded target scanning, target clearing, chase mode, and `g_game.attack`.
- Combat runtime now owns passive next-action label formatting through
  `CombatRuntime.nextActionText(...)`; the native shell still computes the
  guarded action and fallback wait reason.
- The native helper shell now calls diagnostics, route, combat runtime, and
  cavebot runtime adapters through one shared guarded `moduleValue(...)`
  invoker, reducing repeated `pcall` scaffolding while keeping all guarded
  scans, file command handling, widget rendering, modal confirmation,
  profile-dirty marking, `autoWalk`, `findPath`, casts, rune use, and attacks
  shell-owned.
- Combat decision-state and adapter-summary handoffs now rely only on the
  shared `moduleValue(externalCombatRuntime, ...)` guard; the shell no longer
  carries duplicate `externalCombatRuntime.*` preflight branches for those
  passive text paths.
- Combat runtime now owns passive rotation spell row normalization through
  `CombatRuntime.rotationSpellRows(...)`; the native shell still supplies only
  guarded scan snapshots and last-cast state, while spell selection, readiness
  rows, and target/status prose remain behind
  `moduleValue(externalCombatRuntime, ...)`.
- Module contract and static smoke now require `CombatRuntime.targetingStatusText(...)`
  and `owns_targeting_status_text = true`, matching the existing shell handoff
  for blocked/no-target/friendly-summon/auto-target runtime status text.
- Diagnostics now owns passive smoke-command status text through
  `Diagnostics.smokeCommandStatusText(...)`; the native shell still reads and
  removes the smoke command file, switches helper tabs, and executes only the
  existing guarded probe/action paths.
- The native helper shell now calls smoke-command parsing, target selection,
  and status text directly through `moduleValue(externalDiagnostics, ...)`,
  removing the remaining local smoke-command wrapper functions while keeping
  tab switching, command-file removal, probe execution, export, and cavebot
  action dispatch shell-owned.
- The native helper shell now calls diagnostics formatter/probe/export helpers
  through the shared `moduleValue(externalDiagnostics, ...)` invoker while
  keeping OTClient reads, file command handling, and smoke execution
  shell-owned.
- The native helper shell now calls cavebot runtime adapter summary and movement
  probe report helpers directly through
  `moduleValue(externalCavebotRuntime, ...)`, removing extra shell wrapper
  functions while keeping `autoWalk`, `findPath`, retry mutation, and status
  emission shell-owned.
- The native helper shell now calls cavebot adapter status text directly through
  `moduleValue(externalCavebotRuntime, "adapterStatusText", ...)`, removing
  the last adapter-status wrapper while keeping status display and all movement
  execution in the guarded shell.
- Cavebot movement capability now keeps only the guarded `player:canWalk(true)`
  read in the shell; `CavebotRuntime.movementCapability(...)` owns the passive
  capability decision, and the shell fallback is reduced to a minimal
  module-unavailable path.
- Cavebot movement blocked-reason fallback now reuses the same online/player/
  position/PZ context passed to `CavebotRuntime.movementBlockedReason(...)`,
  avoiding repeated shell-side state checks while keeping movement execution
  and `autoWalk` guarded in the native shell.
- Cavebot runtime now owns passive adapter status text through
  `CavebotRuntime.adapterStatusText(...)`; the native shell still resolves the
  active route target, gathers guarded route context, mutates retry state, and
  executes only the existing guarded `player:autoWalk(...)` path.
- The native helper shell now calls cavebot path-result and walking-status
  adapters directly through `moduleValue(externalCavebotRuntime, ...)`,
  removing the remaining one-off shell wrappers for those passive cavebot texts
  while keeping `g_map.findPath`, route label resolution, retry mutation, and
  `player:autoWalk(...)` shell-owned.
- The native helper shell now calls combat adapter summary directly through
  `moduleValue(externalCombatRuntime, "adapterSummary", ...)`, removing the one-off
  `combatRuntimeAdapterSummary(...)` wrapper while keeping guarded online/PZ
  observation, target presence, text fitting, creature scans, casts, rune use,
  and attacks shell-owned.
- Loot runtime now owns passive adapter summary assembly through
  `LootRuntime.adapterSummary(...)`; the native shell no longer carries the
  `lootRuntimeAdapterSummary(...)` wrapper or a one-off
  `pcall(externalLootRuntime.adapterSummary, ...)` branch and only passes
  guarded online/PZ context plus container-count probe data for diagnostics
  text through `moduleValue(externalLootRuntime, "adapterSummary", ...)`.
- Cavebot runtime now owns passive retry-budget decisions through
  `CavebotRuntime.retryDecision(...)`; the native shell still mutates
  `cavebot_movement_enabled` and retry counters, emits module-owned status and
  trace text, and keeps every guarded `player:autoWalk(...)` call shell-owned.
- Cavebot runtime now owns the passive "no player position" waypoint-editor
  status through `CavebotRuntime.statusText("no_player_position")`; the native
  shell still performs the guarded local-player position read and refuses to add
  a waypoint when no position is available.
- Diagnostics now owns passive smoke-command file existence probing through
  `Diagnostics.smokeCommandExists(...)`; the native shell still chooses the
  smoke command path, reads/parses the command, deletes the command file, and
  executes every smoke action in guarded shell code.
- Profile persistence now owns the full profile export field grouping through
  `ProfilePersistence.exportProfile(...)`; the native shell keeps only a
  minimal module-unavailable fallback plus the guarded save execution path.
- Profile persistence also owns the UI preferences export shape through
  `ProfilePersistence.exportUiPrefs(...)`; the native shell keeps the guarded
  save path, serializer call, and minimal module-unavailable fallback.
- Profile persistence now owns passive UI preferences normalization through
  `ProfilePersistence.uiPrefsPlan(...)`; the native shell still owns
  `dofile(...)`, guarded config/helper mutation, status emission, and the
  selected `Helper.ui_path`.
- Diagnostics now owns movement API probe deferral decisions through the shared
  `Diagnostics.probeDeferredPlan(...)`; the native shell still owns delayed
  scheduling, guarded movement/API reads, path probing, and status emission.
- The profile schema, profile persistence, and hotkey shell adapters now reuse
  the generic `moduleValue(...)` protected invoker instead of carrying separate
  per-domain `pcall(...)` branches.
- Diagnostics formatter/counting bridge calls now share one
  `diagnosticsText(...)` shell adapter, and unused shell-only `apiText`,
  `valueText`, `boolText`, `posText`, `tableCount`, and `firstTableValue`
  wrappers were removed; the diagnostics module still owns the passive text,
  table-count, and first-value decisions.
- Operator summary, scripting policy snapshot, modal request/status, and
  targeting score/best-candidate handoffs now reuse the shared
  `moduleValue(...)` guarded invoker instead of one-off `pcall(...)` branches;
  the shell still owns UI rendering, modal confirmation execution, guarded
  creature scans, target choice fallback, and all attack/cast execution.
- Cavebot status and trace formatting now share one
  `cavebotRuntimeText(...)` bridge into `CavebotRuntime.statusText(...)` and
  `CavebotRuntime.traceText(...)`, replacing separate shell wrappers while
  keeping `g_map.findPath`, retry mutation, and every `player:autoWalk(...)`
  call in the guarded native shell.
- Combat action and targeting status formatting now share one
  `combatRuntimeText(...)` bridge into `CombatRuntime.actionStatusText(...)`
  and `CombatRuntime.targetingStatusText(...)`, replacing separate shell
  wrappers while keeping guarded target scans, spell casts, rune actionbar use,
  action locks, and `g_game.attack(...)` execution in the native shell.
- HUD start/disarmed/runtime text and passive position lookup now route through
  direct `moduleValue(externalHud, ...)` calls instead of per-HUD `pcall(...)`
  wrappers or a shell-owned HUD text bridge; `ctoa_helper_hud.lua` still owns
  passive text and geometry defaults, while the shell keeps widget creation,
  movement, visibility, and all OTClient UI calls.
- Protection-zone policy resolution and final PZ decision now use the shared
  `moduleValue(externalRuntimePolicy, ...)` bridge instead of two local
  runtime-policy `pcall(...)` wrappers; the shell still performs guarded
  `g_game` / `g_map` observation because the policy module remains passive and
  does not call OTClient globals.
- The native shell no longer carries a duplicate protection-zone policy fallback
  table; if `ctoa_helper_runtime_policy.lua` is unavailable, PZ-sensitive
  runtime gates now fail closed by treating the player as protected instead of
  reconstructing policy metadata in the shell.
- Module registry summary/readiness shell calls now use the shared
  `moduleValue(externalModules, ...)` bridge for lane enabled/runtime text,
  registry summary, short labels, and readiness rows; `ctoa_helper_modules.lua`
  stays the owner of registry/readiness semantics while the native helper keeps
  only overview widget wiring.
- Operator summary calls now share one table-driven bridge map for
  title/domain/profile/UI summaries; `ctoa_helper_operator_summary.lua` owns
  summary formatting plus `bridgeText(...)` fallback dispatch, while the shell
  keeps only context assembly, widget refresh calls, and guarded module
  invocation through `moduleValue(...)`.
- Profile label callbacks now share one table-driven `profileLabelText(...)`
  bridge into `ctoa_helper_profile_schema.lua` for spell, potion, rune,
  priority, and theme labels; the UI-facing callback names remain stable while
  duplicate shell wrapper functions are removed.
- Recovery runtime now owns passive vitals normalization, healing spell
  selection, recovery action-gap planning, and recovery status text through
  `ctoa_helper_recovery_runtime.lua`; the native shell still performs guarded
  player API reads, actionbar potion sends, spell casts, cooldown mutation, and
  UI/status emission.
- UI now owns passive metric-card geometry and metric text update planning
  through `Ui.metricCardGeometry(...)` and `Ui.metricTextPlan(...)`; the native
  shell still creates widgets, assigns sections, and calls guarded OTClient UI
  APIs, while the unused placeholder-module shell helper has been removed.
- The native shell no longer carries the obsolete toggle-button registry path
  (`setToggleText`, `addToggleButton`, and `Helper.toggles`); current row
  toggles remain owned by the guarded UI row builders and profile/UI adapters.
- UI now owns active panel renderers for `healing`, `heal_friend`,
  `conditions`, `equipment`, and `scripting`; the native shell passes guarded
  callbacks/config context and keeps runtime execution, OTClient API calls, and
  arming decisions in the shell.
- UI now owns operator-summary refresh and setting-row builders
  (`Ui.refreshOperatorSummaries`, `Ui.addSettingRow`,
  `Ui.addToggleSettingRow`); the native shell remains the source of summary
  data and dirty/sync callbacks but no longer manually updates each summary
  widget or lays out setting rows.
- The native shell no longer carries dead coming-soon tab configuration or
  one-shot UI wrapper functions for section bodies, sidebar profile card, and
  overview rendering; active tabs remain bound directly and overview rendering
  delegates to the UI module inline.
- The native shell also removed the remaining one-shot table/toggle row wrapper
  names; panel renderers now receive inline guarded context callbacks, and the
  UI module contract no longer exposes unused inactive/disabled nav styles.
- Profile schema now owns one more passive text bridge (`onOffLabel`) and the
  native shell consumes schema option lists and profile labels directly from
  the module instead of carrying local profile option/list/label adapters.
- UI builder delegation is leaner: tab, subtab, and action-button styling now
  calls `CTOA_HELPER_UI` directly through `styleUi(...)`; the shell no longer
  carries local style wrapper functions for those controls.
- Muted/accent sidebar and section labels now use `addLabel(...)` plus direct
  UI style calls instead of named shell wrappers, leaving the UI module as the
  styling owner while preserving the same rendered labels.
- Priority badges follow the same pattern: panel renderers receive an inline
  guarded context callback, so the shell no longer carries a named
  `addPriorityBadge(...)` wrapper.
- Footer and summary strips now follow the same renderer-context pattern. The
  shell no longer carries named `addFooterStrip(...)` or `addSummaryStrip(...)`
  wrappers, while panel renderers still receive guarded callbacks with the same
  widget styling and section registration.
- Table headers now use the renderer context directly as well: the shell no
  longer carries a named `addTableHeader(...)` wrapper, and batch table headers
  call the same guarded context callback.
- Section bands and subtab buttons now use renderer-context callbacks instead
  of named shell wrappers. `addSectionScaffold(...)` remains shell-owned because
  it creates the guarded OTClient body container, while section header and
  subtab widget composition no longer add shell function pressure.
- Diagnostics text formatting now bypasses shell forwarding wrappers. The shell
  calls `ctoa_helper_diagnostics.lua` through `moduleValue(...)` for boolean,
  position, API snapshot, feature flag, movement, magic/loot, and export-buffer
  text; the smoke commands and runtime sampling remain guarded shell-owned.
- Operator summary bridge calls now bypass the last shell-owned dispatch
  wrapper. `ctoa_helper_operator_summary.lua` owns `bridgeText(...)` fallback
  dispatch, while the shell still owns context assembly and widget refresh
  calls.
- Heal Friend fallback status text now uses the shared
  `moduleValue(externalHealFriend, "statusText", ...)` adapter. The shell no
  longer has a one-off `externalHealFriend.statusText` pcall branch, while
  observation scans and all runtime execution gates remain shell-owned.
- Scripting policy snapshot no longer has a named shell wrapper. The scripting
  panel renderer receives a guarded callback that calls
  `ctoa_helper_scripting.lua` through `moduleValue(...)`, while the module
  still owns passive policy text and blocked unsafe-state wording.
- Module registry overview data now bypasses four shell wrappers
  (`moduleLaneEnabled`, `moduleLaneRuntimeText`, `moduleRegistrySummaryText`,
  and `moduleReadinessRowText`). Overview refresh calls
  `ctoa_helper_modules.lua` through `moduleValue(...)` directly for registry
  summary and readiness rows, while the UI module still owns rendering.
- Profile step rows no longer use the single-call `profileSchemaNumber(...)`
  shell wrapper. The row adapter calls `ProfileSchema.stepValue(...)` through
  `profileSchemaValue(...)` directly and keeps the same numeric fallback.
- Protection-zone state checks no longer use the single-call `pcallWithArg(...)`
  wrapper. `hasAnyState(...)` keeps the same guarded `pcall` behavior inline,
  returning false on unavailable methods or protected-call failures.
- Actionbar slot display text no longer has a shell-owned
  `actionbarSlotText(...)` wrapper. Runtime potion/rune status and operator
  summaries call `ctoa_helper_hotkeys.lua` through `moduleValue(...)` or pass
  the module formatter directly, while `sendActionbarSlot(...)` remains the
  guarded shell-owned execution path.
- Hotkey display and module forwarding now bypass the shell-owned
  `hotkeyValue(...)` and `hotkeyDisplayText(...)` wrappers. The helper shell
  still keeps guarded hotkey bind fallback logic, while passive normalize,
  display, and binding decisions are owned by `ctoa_helper_hotkeys.lua`.
- Modal confirmation flow no longer uses shell-owned `modalValue(...)` or
  `modalStatusText(...)` wrappers. The shell calls `ctoa_helper_modal.lua`
  directly through `moduleValue(...)` for request, pending, and status text,
  while cavebot delete execution and confirmation fallback remain shell-owned.
- HUD runtime/start/disarmed text no longer uses the shell-owned
  `hudText(...)` wrapper. The shell calls `ctoa_helper_hud.lua` directly
  through `moduleValue(...)`, while HUD widget creation, positioning, and
  visibility remain shell-owned and guarded.
- Profile schema text formatting no longer uses the shell-owned
  `profileSchemaText(...)` wrapper. On/off labels, autosave labels, rotation
  preset labels, and rotation summary now call `ProfileSchema` directly through
  `profileSchemaValue(...)` with local fallbacks at each use site.
- Profile number formatting no longer keeps a shell-owned `profileNumberText`
  alias. UI renderer contexts receive `tostring` directly for passive numeric
  display text.
- Profile field geometry now reuses `profileSchemaTable("fieldGeometry", ...)`
  directly from the UI row adapter instead of unpacking and rebuilding the same
  table in the shell; `ctoa_helper_profile_schema.lua` remains the passive
  geometry owner while OTClient widget construction stays shell-owned.
- The obsolete shell-owned `profileFieldGeometry(...)` wrapper is removed; the
  static profile-schema gate now requires direct UI/profile row delegation.
- Operator-summary panel setup no longer carries per-domain
  `*SummaryText = function()` wrappers. Initial panel summary text is captured
  as a string snapshot during `rebuildUi(...)`, while
  `refreshOperatorSummaries(...)` still refreshes live widgets through
  `ctoa_helper_operator_summary.lua` and the shared guarded `moduleValue(...)`
  bridge.

## Non-Negotiable Gates

- Do not promote live until sandbox `SmokeAttachModules`, fresh
  `SmokeAttachAll`, release gate, and explicit
  `PromoteLiveCtoa -ApproveLiveDeploy` are current.
- Do not enable combat, movement, rune casting, timer, healing, loot, or eval at
  loader initialization.
- Keep external bot sources as references only until provenance, license, secret
  scan, import gate, and mapped module gates pass.
- Keep vBot-derived implementation claims blocked until a reviewed source tree
  or archive is present in this checkout.

## Next Work Order

| Order | Workstream | Goal | First action | Required gate |
|---:|---|---|---|---|
| 1 | `runtime_cavebot` | Continue reducing cavebot runtime shell pressure without moving movement execution. | Move remaining movement preflight/status labels into cavebot runtime adapters; keep `autoWalk` and `findPath` shell-owned. | CavebotRuntimeStaticSmoke, RouteStaticSmoke, sandbox cavebot attach evidence. |
| 2 | `runtime_combat` | Keep attack/cast guarded while extracting remaining passive readiness labels. | Move remaining combat wait/decision-state input shaping into combat runtime/targeting adapters; keep creature scans and casts shell-owned. | CombatRuntimeStaticSmoke, TargetingStaticSmoke, sandbox hunting and hunting_magic attach evidence. |
| 3 | `diagnostics_smoke` | Keep smoke evidence formatting module-owned. | Move any remaining smoke report/static result labels into diagnostics helpers; keep smoke command execution shell-owned. | Diagnostics contract checks, ModuleStaticGates, LocalReady. |
| 4 | `ui_builder` | Reduce shell-only UI builder pressure before adding new tabs. | Continue moving repeated section, row, and metric metadata into passive UI descriptor tables; metric-card geometry/text planning is already module-owned. | UI preview, ModuleStaticGates, no layout overlap evidence. |
| 5 | `runtime_recovery` | Prepare healing/recovery metadata without enabling new actions. | Continue mirroring potion/spell blocked-reason labels in passive recovery metadata; vitals, spell selection, status text, and action-gap planning are already module-owned. | Safe-boot false-key coverage, recovery targeted tests, sandbox evidence. |
| 6 | `sandbox_runtime_review` | Decide whether any passive plan can become a guarded dispatcher input. | Run Launch, ReadyCheck, SmokeAttachModules, SmokeAttachAll for the current manifest. | Release gate current and live promotion still explicit. |

## Operator Sequence

1. Run `ValidateDev` after source changes so manifest, ZIP hash, smoke preflight,
   and release-readiness evidence are synchronized.
2. Run `ModuleStaticGates` and `LocalReady`.
3. Launch the sandbox client and enter a test character.
4. Run `SmokeAttachModules`, then `SmokeAttachAll`.
5. Only after those pass, review runtime bridge candidates.
6. Use the official live wrapper only when the release gate is current and the
   user explicitly approves live deployment.
