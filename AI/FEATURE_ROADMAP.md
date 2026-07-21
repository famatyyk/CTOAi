# Feature Roadmap

## Current State

- Canonical product snapshot (2026-07-14): Helper source and last verified live
  package are `v2.4.1`; Safe source candidate is `v2.9.0`, while the last
  separately verified live Safe package remains `v2.8.0`. Neutral chooser is
  `2.1.0`. Historical version paragraphs below are release history, not current
  version declarations.
- Current phase state (2026-07-15): P8, P9, P10, and P11 are `operational_acceptance_complete`.
  Their accepted receipts remain independent
  and grant no P12 action authority.
- P12 execute-once review is `closed_with_deferred_heal_friend_lane`. P12
  Conditions is `operational_acceptance_complete`:
  exactly one approved sandbox executor call
  succeeded, the trace ended `killed_and_disarmed`, retry remained false, and
  the accepted receipt grants no downstream authority.
- P12 Equipment is `operational_acceptance_complete`. Registry v1 plan
  `d041db806c6417b018c6ae390e3d384ccec9bead2a77e498a582093bf7c823e0`
  was separately approved and made exactly one `3097 -> 3099` sandbox executor
  request. Receipt `p12-equipment-bdf7027cf48c438d` is `accepted`; retry stayed
  false, transformed rollback item `3093` returned to the source slot, terminal
  state was `killed_and_disarmed`, and no downstream or live authority was
  granted. The earlier rejected attempt remains historical and cannot be replayed.
- P12 Heal Friend is `closed_blocked_no_compatible_vocation`. Plan
  `964ff8f0c178c7b646a565380e96846a8b29780eb02a734a259713d9ccf023b3`
  remains immutable and binds the accepted P11 shadow receipt, accepted P12
  Equipment predecessor, exact target identity and whitelist revision, ED-only
  vocation, HP `<= 70`, range `<= 7`, zero retry, and terminal KILL/disarm.
  The current 63-file manifest has `39/39` static gates, `4/4` module attach,
  `16/16` full attach, and `19/19` runtime gates. The separately approved
  sandbox session reached a fresh preflight whose only blocker was
  `vocation_must_be_ed`; the operator has only sorcerer and knight characters.
  `p12_heal_friend_no_compatible_vocation_closure.json` therefore expires that
  session approval, forbids its reuse and any execution approval, and records
  attempt count `0`, retry false, final state `disarmed`, no cast, and no
  downstream or live authority. No Conditions or Equipment authority was inherited.
  Fixture success is never reported as runtime readiness.
  Historical compatibility marker: P12 is `in_progress`. P12 Heal Friend is
  `plan_ready_for_sandbox_session_approval`, `ready_for_sandbox_session_approval`,
  and P12 Heal Friend is `not_started` are superseded and retained only for
  older read-only cockpit checks; none describes the current state.
- P13 is `runtime_evidence_ready`. The fixed seven-entry
  decision/result ledger, versioned schema registry with independent v1/schema
  SHA-256 pins, freshness/tamper checks,
  atomic `ROADMAP_STATE.json/md` generator, sanitized dry-run/success/failure
  audit contract, read-only Control Center panel, and release-evidence phase
  consumer are implemented and tested. The exact confirmation
  `refresh roadmap state` authorized the fixed-output refresh; generated JSON
  and Markdown now carry the terminal ledger, while the confirmed safe-write
  audit binds their raw hashes independently from freshness and tamper status.
  P13 adds no runtime executor, MCP write tool, live authority, or inherited
  permission, and it does not reopen the closed P12 Heal Friend lane.
- P14 is active with status `foundation_ready_operational_hardening_required`.
  Its v1 request/result
  schemas, HMAC-SHA256 artifact-only handoff, tracked-source 63-file manifest,
  clean-checkout/revision binding, tamper/path tests, deterministic manifest
  rollback replay, Windows CI contract job, Release Evidence phase state, and
  read-only Control Center card and bounded external preflight are implemented.
  The current bounded status source is
  `runtime/control-center/p14-runner-preflight.json`. It records an online
  GitHub-hosted Windows runner, configured required review, and disabled
  administrator bypass. The current source branch is not allowed by the
  protected-environment branch policy, and the signed replay is stale and targets
  an older revision. P14 therefore remains fail-closed on those external blockers
  plus the unproven visual/in-world, canary, and rollback capabilities; promotion,
  runtime, live, and MCP-write authority remain unclaimed and P15 stays closed.
- The post-P16 continuation is now explicit in
  `AI/P17_P24_HELPER_EVOLUTION_ROADMAP.md` and its machine-readable JSON
  companion. P17 static ownership/reachability work may proceed during P14;
  runtime acceptance remains gated. The measured baseline is 4404 lines and
  130 functions in `ctoa_native_helper.lua`, duplicate HUD configuration exists
  in Tools and Engine, targeting/magic configuration is incomplete, and Auto
  Haste lacks active-state evidence. P17-P24 address simplification, typed
  action/condition rules, configurable targeting/shooter, spell anti-spam,
  schema migration, unified UX, pure Helper/Safe contracts, and canary/rollback.
- The accepted shadow-gate dependency order remains **Conditions runtime safety gate**,
  then **Equipment runtime safety gate**, then **Heal Friend runtime safety gate**.
  P9-P11 acceptance is complete, but this order still governs the independent
  P12 execute-once lanes and grants no inherited action authority.

- Engine Brain Plan 3 is operational and maintained as the secret-safe context
  foundation; roadmap work now consumes its generated evidence.
- Product direction is now explicitly split: the full OTClient/Solteria Helper
  remains the primary P8-P16 project, while `mods/ctoa_safe` is a secondary
  minimalist, movable client panel with fixed module labels and broad editing
  inside its supported lanes. Safe may provide editable healing, spell and Exeta
  rotations, Conditions, Timer, and portable data-only presets, but permanently
  excludes CaveBot, route/movement automation, generic Settings, arbitrary Lua,
  and any path that satisfies or bypasses a Helper acceptance gate. The delivery
  contract is S0 scope reduction, S1 rotation editors, S2 mobile preset schema,
  S3 compact UI acceptance, and S4 separate package/release evidence.
- S0 is repo- and stage-complete in candidate package `v2.4.0`: a single neutral
  loader is the only CTOA autoload, asks after every login, activates exactly one
  of Helper or Safe, and tears it down on logout. Direct Helper/Safe initialization
  is rejected without the matching selection. Safe now has only three project
  files, fixed Healing/Combat/Conditions/Timer labels, forced safe boot, and no
  copied Helper runtime, CaveBot, or generic Settings surface. Operational crash
  closure remains unclaimed until fresh sandbox selection plus Safe ENABLE smoke
  and the separately approved promotion gate pass.
- Safe `v2.0.1` closes the ENABLE-only zero-argument spectator query found during
  crash-path review. It now uses the fork-native bounded center-position API and
  guarded fallback; an executable Lua fixture verifies the exact arguments.
  This strengthens the staged candidate but does not replace in-world crash proof.
- Safe `v2.8.0` advances S1/S2 with a fixed Support label below Conditions,
  module-specific ordered editors for Healing, Targeting, Spell Rotation, and
  Support, selection-to-form editing, bounded JSON persistence, and export-time
  removal of runtime timestamps. Healing includes HP/mana percentage controls,
  bounded randomization, and drag-and-drop item slots with hotkey fallback.
  Support accepts spell or item rules triggered always, by HP, or by mana.
  Combat rules include a compact monster-count checkbox and per-spell distance.
  Support is default-off and has no CaveBot, movement, Settings, scripting, or
  Helper-profile compatibility path.
- Safe `v2.8.0` is live-promoted after sandbox visual acceptance, real item
  drag/drop and JSON persistence proof, Helper attach coverage 4/4 and 16/16,
  runtime module gates 19/19, and exact repo/stage/live hash parity. Backup:
  `runtime/solteria_helper_dev/live_backup_20260713-021234`.
- Safe `v2.9.0` is the next repo-only candidate. It completes the ordered Exeta
  editor with per-entry monster count and cooldown, introduces strict
  `ctoa-safe-profile-v3` named preset libraries with v2 migration and explicit
  fixed-path import/export, keeps `.bak` recovery, excludes runtime arm state,
  clamps restored window geometry, and adds bounded keyboard navigation. It is
  not staged, visually accepted, or live-promoted yet.
- Add a separate cross-fork OTS Connection Profile lane for OTC, OTCv8,
  OTC Brasil, and derived clients. Keep the UI normalized while fork adapters
  map protocol/client differences. Store only authenticated encrypted envelopes;
  keep key material in the OS credential store, pin server identity when the
  fork supports it, redact logs/evidence, and require an explicit Connect action.
  Begin with passive capability discovery and validated profile import/export;
  do not place this surface inside Safe or couple it to Helper runtime arming.
  The public profile contract is now schema-closed in
  `schemas/otclient-server-profile.schema.json`; secrets are represented only by
  an OS-vault reference and unknown adapters or missing public-key pins fail.
  A bounded passive detector now identifies the source checkout as
  `redemption-mehah` and records proven UIItem/action-bar/keybind/shader/HTML
  capabilities without reading credentials or connecting. A protected live
  tree with no public markers remains explicitly `unknown`.
- Safe S4 now has an independent three-file release lane documented in
  `docs/otclient/solteria_safe_release.md`. Safe `v2.8.0` is live-promoted with
  3/3 source/live SHA-256 parity and backup
  `runtime/solteria_safe_release/live_backup_20260713-015729`; the running client
  PID remained unchanged. Activation and visual/runtime acceptance are pending
  a normal reload, so this evidence does not satisfy any Helper release gate.
- Helper `v2.4.1` hardens guarded auto-targeting so the currently attacked safe
  creature is not redispatched every retarget interval. This is an idempotency
  fix only and does not alter P8-P16 eligibility, runtime gates, or safe boot.
- Helper `v2.3.6` is live-promoted with 58/58 verified files and
  `launch_after_promote=false`; backup: `live_backup_20260712-121859`.
  It adds the passive P10 observation, canonical snapshot producer, operational
  replay, and separate acceptance receipt contract.
  The already-running live client still reports the prior capability version;
  P8 correctly returns `capability_version_mismatch` until the user performs a
  normal client restart. Promotion did not force-close or restart that session.
  Vocation-profile drift after play is tracked separately, but remains blocking
  because the current Lua profile is executable rather than data-only.
- Helper `v2.3.6` adds a passive exact-single-target
  Heal Friend scan boundary and a fixture-only P11 replay that passes 55/55
  deterministic cases under mandatory `--no-write`. P11 operational acceptance
  remains `not_started`: there is no operational producer, receipt, dispatch,
  Control Center unlock, cast, talk, execute-once, or runtime-readiness claim.
- Helper `v2.3.7` is live-promoted with 58/58 verified files,
  `launch_after_promote=false`, and backup `live_backup_20260712-150157`.
  It hardens P10 with a fixed 30-case
  corpus, scenario-pack SHA binding, current-wall-clock operational evaluation,
  strict nested schemas and Release Evidence/Control Center coverage parity.
  Privileged smoke commands now fail closed while runtime is disabled, while
  passive tab/probe smoke remains available for sandbox evidence.
- Helper `v2.3.8` is live-promoted with 58/58 stage/live SHA-256 matches,
  `launch_after_promote=false`; the latest content-bound P10 operator-tooling
  promotion backup is `live_backup_20260712-163259`.
  It closes safe-boot lifecycle bypasses across init, terminate, profile reload,
  external disable/enable, and the persisted Recovery Bridge arm. Profile and
  UI-preference Lua now execute in an empty data-only environment rather than
  inheriting OTClient or filesystem authority. The current-manifest sandbox
  evidence passed ModuleAttachSmoke 4/4, SmokeAttachAll 16/16, and runtime
  module gates 19/19 before promotion.
- Helper `v2.3.9` is live-promoted with backup
  `live_backup_20260712-185148`, 58/58 stage/live SHA-256 matches, and
  `launch_after_promote=false`. The main Lua shell was reduced from 160 to the
  enforced 130-function budget (4308 lines) by moving pure profile/input,
  route/target/cavebot, recovery/combat, registry, and UI metadata into existing
  support modules. Lifecycle, arming, OTClient API access, and final action
  guards remain shell-owned. The in-world smoke caught and fixed a missing
  Profile renderer visibility callback before promotion.
- Helper `v2.3.10` is live-promoted with backup
  `live_backup_20260712-192857`. It moves vocation/timer and route/cavebot probe
  presentation into passive adapters, adds schema-owned export descriptors for
  all six generated profile sections, and centralizes initial operator-summary
  collection. Native reads, route mutation, arming, movement, and dispatch stay
  in the guarded shell, now at 4298 lines and 129 named functions. Sandbox QA
  caught and fixed a nil UI-preference write and an unsafe generic wrapper around
  native `g_map.findPath`; the proven direct guarded `pcall` boundary is retained.
  Final evidence passed 1666 Python tests, ValidateDev 127/127, static gates
  39/39, attach 4/4 and 16/16, and runtime gates 19/19.
- P10 operator evidence now has strict read-only parity across its six producer
  artifacts, Python Release Evidence, and the web Control Center. A dedicated
  `ctoa.equipment-consumer-parity.v1` gate validates fixed paths, schemas,
  canonical hashes/bindings, copied status/blockers, freshness, unchanged
  eligibility, and all no-action fields. Control Center exposes only read-only
  summaries and evidence links; no write or action endpoint was added.
- P10 now has one fixed repo-only refresh entry point, `ctoa.ps1 otp10refresh`.
  It runs doctor, preview, dependency preflight, catalog, a no-ID change plan,
  readiness, and strict consumer parity in order. Producer blockers are allowed
  as data, but parity must pass; the command accepts no IDs, confirmation,
  acceptance, replay, client action, or `.ctoa-local` write path. Successful
  runs persist one UUID-bound anti-mix envelope with seven ordered canonical
  hashes; failed runs abort only their matching pending journal. The completed
  batch passed 1657 Python tests, 147 web tests, ValidateDev 127/127, static
  gates 39/39, sandbox attach 4/4 and 16/16, and runtime gates 19/19.
- P10 now exposes `ctoa.ps1 otp10doctor`: a schema-closed no-action preflight
  for the fixed ignored capture profile. It reports exact missing IDs,
  confirmation, validity, and identity-collision blockers, writes only bounded
  runtime evidence, and is enforced by ValidateDev without treating a blocked
  operational profile as fixture failure or runtime permission.
- The next P10 operator batch adds three fail-closed boundaries: exclusive
  zero-ID `otp10doctor init` with no overwrite path, bounded `otp10preview` for
  sanitized ring/container/slot evidence, and `otp10preflight` for the complete
  P8/P9/doctor/preview dependency chain. Preflight never changes eligibility and
  all three remain repo/runtime-evidence only. The content-bound release cycle
  passed 1585 tests, ValidateDev, 39/39 static gates, 4/4 module attach, 16/16
  full attach, and 19/19 runtime gates before the latest live promotion.
- P10 profile preparation now also has `otp10plan`: a strict hash-bound,
  data-only plan/diff over the fixed doctor and observation preview. It requires
  four exact IDs plus an exact planning confirmation, writes only repo runtime
  evidence, never reads or writes `.ctoa-local`, and grants no acceptance,
  readiness, eligibility, dispatch, execution, or promotion.
- The latest P10 operator batch adds `otp10catalog` with no selection or
  recommendation policy, `otp10plan` as a write-free exact-ID review artifact,
  and `otp10ready` as an ordered blocker/next-action explanation. ValidateDev
  enforces all three no-action contracts. The content-bound cycle passed 1612
  tests, 39/39 static gates, 4/4 module attach, 16/16 full attach, and 19/19
  runtime gates before promotion; operational readiness remains unclaimed.
- The v2.3.5 package retains the v2.3.4 loader hardening and adds a canonical
  passive Recovery trace/proof producer, `otp9accept`, a fixed ignored local P10
  profile override, exact container-slot binding, and P10.1 consumer closure.
  Release Evidence and Control Center now require the bound P10 report itself to
  be fresh, operational, non-fixture, blocker-free, rollback-ready, and scenario-
  complete before P11 predecessor eligibility can become true.
- The v2.3.4 package fixed lowercase OTML autoload metadata,
  cross-fork console enums, idempotent loader teardown/reload, and hidden
  no-focus startup. It also seals P10 receipt eligibility consistently across
  Python, JSON Schema, Release Evidence, and Control Center, and hardens passive
  snapshot/replay writes. It does not accept P10 or enable P11/runtime actions.
- P8 `BackgroundNoScreen` is `operational_acceptance_complete`. Its final
  acceptance used the official promotion-bound trusted pin, one fresh
  capability heartbeat newer than the canonical process, `62/62` live hash
  parity, and full producer/consumer no-action parity. The earlier
  `legacy_or_unbound_attestation` evidence remains historical and was never
  rebound into trust by the observer.
- The sandbox smoke chain is content-bound: `ModuleAttachSmoke` 4/4,
  `SmokeAttachAll` 16/16, and `RuntimeModuleGatesSandboxSmoke` must carry the
  current dev manifest SHA-256. Legacy reports remain blocked; a newer file
  timestamp alone is not evidence of freshness.
- P9 Conditions is `operational_acceptance_complete`. Its accepted data-only
  receipt binds fresh real Conditions evidence plus canonical P8 and Recovery
  predecessors; dispatch, execute-once, promotion, and runtime readiness remain
  false.
- P10 Equipment shadow/replay is `operational_acceptance_complete`. Its accepted
  receipt binds the exact ring/container/slot observation and the P9 receipt;
  it authorizes no item movement. The later P12 Equipment execute-once lane was
  completed through its own separate Registry v1 authority boundary.
- P11 Heal Friend shadow/replay is `operational_acceptance_complete`. It retains
  exactly one stable allowlisted party identity and no ranking, fallback,
  multi-target, cast, talk, dispatch, or promotion path.
- P6 is ready for plugin design and the six bounded P7 safe-write refresh tools
  are enabled with audit coverage.
- The next static Helper slice keeps the UI shell passive: Diagnostics owns
  snapshot text values and the UI adapter owns diagnostic widget updates;
  `ctoa_native_helper.lua` retains only guarded orchestration and runtime
  probing.

## Now

1. **P12 Heal Friend exact-whitelist boundary** — owner: Helper Runtime +
   Evidence; status: `plan_ready_for_sandbox_session_approval`; risk:
   `execute_once_sandbox`. Its lane-specific plan is bound to the persisted
   exact whitelist and current manifest gates. Next it requires the exact
   sandbox-session approval; later, on ED, a fresh stable party-target window,
   independent execution approval, one terminal trace, and its own receipt.
2. **P12 Conditions accepted boundary** — owner: Helper Runtime + Evidence;
   status: `operational_acceptance_complete`. Its one terminal trace and receipt
   stay immutable, killed/disarmed, zero-retry, sandbox-only, and grant no
   authority to Equipment, Heal Friend, live promotion, or automatic execution.
3. **P12 Equipment accepted boundary** — owner: Helper Runtime + Evidence;
   status: `operational_acceptance_complete`. Registry v1 receipt
   `p12-equipment-bdf7027cf48c438d` stays immutable: one attempt, zero retry,
   killed/disarmed, sandbox-only, and no authority for Heal Friend or live
   promotion.

## Next

- Request only the exact sandbox-session confirmation for plan
  `964ff8f0c178c7b646a565380e96846a8b29780eb02a734a259713d9ccf023b3`.
- Switch the sandbox to ED and wait for the approved target to be a visible,
  same-floor party member within seven tiles at or below 70% HP. The current EK
  character and missing approved target keep execution fail-closed.
- Request execution approval later and independently; permit at most one
  terminal attempt, zero retry, immediate KILL/disarm, and no live promotion.
- P13 adds decision/result replay and machine-readable roadmap state; P14 moves
  visual acceptance to a separate runner/VM.
- Add sandbox-to-live promotion visibility without implicit promotion.
- Index a supplied TFS fork and protocol sources; do not infer missing server
  behavior.
- Generate roadmap status from manifests and evidence to reduce manual drift.
- **Roadmap state refresh** is enabled end-to-end as the sixth bounded
  `safe_write` capability. Its native dry-run separates P13 platform health
  from pending P14 sandbox evidence, exact confirmation writes only the fixed
  roadmap JSON/Markdown artifacts, and active external P14 recovery still
  outranks routine roadmap maintenance.
- Keep Combat and CaveBot explicitly `deferred_high_risk` until all three safer
  lanes have independent acceptance evidence and a new review opens P15/P16.

## Guardrails And Maintenance

The priority sections below retain the complete durable security, evidence, and
runtime maintenance contract. They are invariants, not simultaneous active
feature work.

## Default Horizon: 90 Days, Helper First

- Stabilize and productize the OTClient/Solteria Helper before broader CTOAi
  expansion.
- Treat CTOA Safe as a bounded companion lane, never as a replacement or fork of
  the full Helper roadmap. Shared utilities must preserve separate policies and
  prove that Safe exclusions cannot be restored through Helper configuration.
- Reduce the current `mods/ctoa_safe` prototype before product acceptance:
  remove CaveBot and generic Settings/profile surfaces, freeze the visible label
  set and order, then implement validated ordered spell/Exeta editors and
  non-executable portable presets with safe boot default-off.
- Keep `scripts/lua/otclient/` as the canonical Helper source tree; generated
  ZIPs stay under `runtime\solteria_helper_dev\` or release staging.
- Preserve safe boot defaults: runtime disarmed, combat/offensive/movement
  actions off unless explicitly enabled.
- Treat the live Solteria client as protected. Development uses
  `runtime\solteria_helper_dev` and the sandbox client first.
- Treat the user's single game screen as protected too. Routine agent work uses
  `BackgroundNoScreen`, bounded passive reads, and repo-local evidence only.
  Screenshot/focus/input/start-stop actions require an explicitly interactive
  session or a separate runner; they are not fallback behavior.
- Keep helper sandbox path validation strict: `SandboxClient` must stay under
  `%LOCALAPPDATA%`, use separator-aware containment, and must not equal or sit
  inside `SourceClient`.
- Required gates before live promotion: `PrepareDev`, `ValidateDev`,
  `SmokePreflight`, in-world `SmokeAttachAll`, then explicit live approval via
  `PromoteLiveCtoa -ApproveLiveDeploy`.
- A post-promotion live client launch is not implicit. Operators must add
  `-LaunchAfterPromote`; the wrapper may launch a missing live client but must
  never stop or restart an existing live client.
- Current Helper `v2.4.1` is live-promoted. Its promotion report verified the
  current manifest
  staged/live SHA-256 matches; release gate and GoalStatus passed. Runtime module
  acceptance remains fail-closed and separate from package promotion.
- Helper P6 Module Lane is repo- and sandbox-complete: Healing/Recovery, Combat,
  CaveBot, Loot, Timer, Heal Friend, Conditions, Equipment, and Scripting are
  all `static_gated` by dedicated reports, current ModuleStaticGates and
  ReadyCheck, and newer in-world tab evidence. Runtime stayed disarmed.
- The completion evidence is passive: Combat has no active target; CaveBot only
  reports movement capabilities and retry/PZ/offline/empty-route guards; Timer
  returns `hold_timer_disabled`; and Loot returns
  `hold_feature_flag_disabled` with zero planned items. No attack, movement,
  sio, condition recovery, equipment swap, loot move/open/use, timer cast,
  eval, or snippet runtime was enabled. The next functional phase requires a
  separate runtime-bridge review after the completed v2.2.1 stabilization.

## P0: Make This Brain Usable In Daily Codex Work

- Keep this `AI/` folder current when OTClient, Lua generator, API, or Control
  Center contracts change.
- Add a lightweight script that refreshes Lua/API/class inventories into
  markdown or JSON.
- Add this folder to the handoff checklist for large CTOAi tasks.
- Add `AI/generated/` for generated file tree and symbol maps.
- Add `.\ctoa.ps1 brain refresh` as the one-command local Engine Brain updater.
- Keep `scripts/ops/ctoa_full_workspace_audit.py` available for full-file
  inventory and roadmap refresh work. The audit must use `lstat`/regular-file
  checks and skip symlinked files before size accounting or SHA256 hashing, so a
  repo-local symlink cannot pull external local content into inventory evidence.
  It should also publish an audit-integrity gate with non-regular entry
  accounting, bounded hash counts, and proof that sensitive-name files were not
  hashed, plus a validation-evidence gate backed by local runtime command
  evidence for Python tests, web lint/tests, diff check, and Engine Brain
  refresh/doctor/pack.
- Generate `AI/generated/OWNERSHIP_MAP.md`, `AI/generated/DOC_SYNC.md`, and
  `AI/generated/SECRET_GUARDRAIL.md` during `brain refresh`.
- Keep Engine Brain indexing tolerant of volatile generated directories such as
  `web/.next/*`; excluded directories should be pruned before traversal.
- Use `brain pack control-central` for the minimal daily operator handoff. Use
  `all|helper|control-center|infra|security` only when the active task needs the
  broader scoped context; never append file-tree or symbol-map summaries to the
  `control-central` profile.
- Keep the local Codex skill `ctoa-engine-brain` aligned with the operator
  shortcuts, generated artifacts, and secret-safe context rules.
- Restore or replace the missing environment doctor with checks for Git, Docker,
  VPN/WARP, Vercel, VS Code/Codex extension, GitHub, and local update gate.
- Keep Docker compose bind defaults on loopback and require explicit env opt-in
  for LAN/VPN exposure.
- After compose/profile changes, recreate stale local containers when needed and
  require Engine Brain doctor to show `running_broad=0` and
  `configured_broad=0` before treating runtime exposure as clean.
- Keep production startup guardrails strict: API must use explicit
  `CTOA_CORS_ORIGINS`, a non-default `CTOA_JWT_SECRET`, and a pre-provisioned
  `CTOA_AUTH_STORE_FILE`; mobile console self-registration stays off by default
  in production and requires `CTOA_SELF_REGISTER_CODE` when explicitly enabled.
- Keep default account seeding and local seed-login fail-closed: seed accounts
  require explicit `CTOA_ALLOW_SEED_ACCOUNTS=true`, and Control Center local
  seed-login requires `CTOA_ENABLE_LOCAL_SEED_LOGIN=true` plus
  `CTOA_SEED_*_PASSWORD` env vars that are not stored in the repo.
- Keep web `ctoa_token` cookies centralized and production-safe: all writers
  should use `authCookies.ts`, stay `httpOnly` and `sameSite=lax`, and set
  `Secure` automatically in production.
- Keep `/api/auth` proxy responses browser-safe: backend `token`,
  `access_token`, `refresh_token`, nested token-like fields, and token/password
  strings must not be returned in JSON bodies. Cookie auth should still use the
  original backend token through the centralized httpOnly `ctoa_token` writer.
- Keep local `/api/auth/seed-login` on the same shared auth proxy sanitizer as
  `/api/auth`; it may extract the original backend token for the httpOnly
  cookie, but browser-visible JSON must never expose nested token-like backend
  fields or unsanitized backend detail strings.
- Keep public docs/site admin helpers constrained: API base URLs must be parsed
  and normalized, HTTP must remain local/private-dev only, local fallback admin
  passwords must not persist in `localStorage`, owner reset must clear
  session-scoped API tokens and local fallback admin passwords too, and
  `tests/test_docs_site_security.py` must reject dynamic HTML regressions.
- Keep public docs/site live dashboard constrained the same way: API base URLs
  must use the URL guardrail, tokens must stay session-scoped, dynamic
  `innerHTML` and inline handlers must stay out of the inline dashboard script.
- Keep mobile-console DB-backed account mutations privilege-safe: password
  changes, role changes, and deactivation must revoke existing sessions for the
  affected user so stale tokens cannot retain old owner/operator privileges.
- Keep mobile-console self-registration least-privilege: public/self-register
  paths may create only `member`, and operator endpoints must enforce
  `operator` or `owner` role rather than accepting any authenticated session.
- Keep API public registration fail-closed in production:
  `CTOA_API_SELF_REGISTER_ENABLED=true` requires
  `CTOA_API_SELF_REGISTER_CODE`, and `/api/auth/register` must never create
  `owner` or `operator` without an authenticated owner token.
- Keep backend chat routing diagnostics operator-only: `/api/chat` and
  `/v1/chat/completions` may expose `debug_route` metadata only to `owner` or
  `operator`, and the returned route object must stay allowlisted without
  backend URLs, fallback backend URLs, keys, or internal endpoint values. Router
  stdout logs must use the same sanitized route view.
- Keep Control Center chat persistence and exports secret-safe: localStorage
  snapshots, transcript downloads, markdown exports, and JSON chat logs must
  redact Bearer/provider tokens, token/password/API-key forms, quoted
  JSON-like secret fields, and quality/publication-note secrets before they are
  stored or exported.
- Keep dev auth placeholders static-scan clean while preserving production
  fail-closed behavior: production must continue rejecting unset/default
  `CTOA_JWT_SECRET`.
- Keep database CLI fallbacks secret-safe: `DB_PASSWORD` must not be placed in
  `psql` or `docker exec` command argv.
- Keep runner agent database connections secret-safe too: do not assemble
  `DB_PASSWORD` into text DSN strings that can be copied into exception or log
  paths, and redact secret-bearing DB exception messages before logging
  `agent_runs` write failures.
- Keep mobile-console command audit secret-safe: `/api/command` audit records
  must redact Bearer tokens, common provider tokens, token/password assignments,
  and common long token/password CLI options before writing
  `logs/mobile-console-audit.log`.
- Keep mobile-console operator command output secret-safe too: stdout/stderr
  returned from `/api/command`, status report helpers, and log tails should be
  sliced and redacted for Bearer, provider-token, token/password, and
  `PGPASSWORD` forms before the UI receives them. Local log-tail fallbacks must
  read from the end through a byte cap and reject symlinked log files before any
  UI response, while DB fallback stdout used for parsing stays unmodified.
- Keep mobile-console audit accountable without leaking credentials: audit
  records should include actor, role, auth mode, and auth transport, but never
  session tokens or CSRF tokens.
- Keep mobile-console cookie-authenticated mutations CSRF-protected with
  regression coverage: cookie-only unsafe methods require `X-CSRF-Token`, while
  bearer/header-authenticated operator calls stay header-authenticated.
- Keep mobile-console generated-artifact responses secret-safe:
  `/api/agents/generated/latest`, manifest summaries, and SLO observations
  should expose public artifact paths rather than local absolute
  `GENERATED_DIR`, temp-directory, or unknown runtime paths. Generated
  `latest.json` and run `manifest.json` reads should be byte-capped,
  symlink-rejecting, and fail closed to scan/default responses when oversized
  or invalid.
- Keep mobile-console local metadata JSON reads bounded too: command
  dictionary, product manifest, and product user config reads should reject
  symlinked files and oversized/non-object JSON before driving operator API
  responses.
- Keep mobile-console file metadata responses display-safe too: admin settings,
  idea parking, auto-trainer report status, disk probes, one-click generated
  directories, and client-sync result paths should expose public artifact names
  or repo-relative paths instead of absolute local host paths.
- Keep mobile-console auto-trainer report reads physically bounded:
  `/api/agents/auto-trainer/latest` should read markdown and JSON through
  byte caps, return stable parse/oversize states, and avoid echoing raw parser
  exception text.
- Keep legacy mobile-console dashboard rendering DOM-safe: API payloads in
  `mobile_console/static/app.js` must use `createElement`/`textContent`, and
  `tests/test_mobile_console_static_xss_security.py` must reject dynamic
  `innerHTML` regressions.
- Keep mobile-console preset execution structured: safe-mode `/api/command`
  presets must run through backend-owned `argv/cwd/env` specs, not raw
  pseudo-shell snippets.
- Keep legacy mobile-console full-access closed: `CTOA_MOBILE_FULL_ACCESS=true`
  must not re-enable arbitrary command text execution through `/api/command`;
  the endpoint should accept only backend-owned presets.
- Keep legacy mobile/desktop operator UIs aligned with that contract: status
  payloads should report `command_mode=presets`, the mobile legacy UI should
  not render a full-command box, and the desktop admin console should run only
  presets loaded from `/api/presets`.
- Keep legacy mobile/desktop Intel guarded writes behind explicit
  confirmation: `/api/agents/intel/launch`, `/api/agents/execution/run`, and
  `/api/agents/intel/run` should require owner auth plus `confirm=true` and a
  non-empty audit `reason` before DB writes, orchestrator triggers, or client
  sync can run.
- Keep mobile-console Intel target validation fail-closed in production:
  localhost, private IPs, link-local/metadata IPs, `.local` names, and
  single-label internal hosts require explicit
  `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true`.
- Keep mobile-console server/intel target URLs free of secret-bearing or
  ambiguous components before DB/audit/UI use: reject embedded credentials,
  query strings, fragments, backslashes, and decoded `.`/`..` traversal.
- Keep mobile-console local runtime proxy base URLs fail-closed:
  `CTOA_API_BASE_URL` and `CTOA_INTEL_API_BASE_URL` must target local runtime
  API hosts only (`localhost`, `127.0.0.1`, `[::1]`, or
  `host.docker.internal`) and must reject embedded credentials, query strings,
  fragments, backslashes, and decoded traversal before `/api/intel/*` or
  `/api/dashboard/release-evidence` can call `urlopen`. Runtime proxy paths
  must stay as relative `/api/...` paths without query strings, fragments,
  empty segments, traversal, backslashes, or encoded separators. Runtime proxy
  error text returned to browsers must use the shared redactor so URL/open
  failures cannot echo token/password forms.
- Keep Intel client-sync writes confined to `CTOA_CLIENT_SCRIPTS_DIR`; target
  slug, autoloader, and init-file settings must be validated before any copy.
  Init-file updates should reject symlinked or oversized files, fail fast before
  copying generated Lua, and write through hidden PID/UUID temp files with
  `fsync` plus atomic replace. Generated Lua copies should reject symlinked or
  oversized sources, reject existing destination symlinks, and write through the
  same atomic temp-file path.
- Keep repo-local static security scanning available through
  `requirements-dev.txt`; the pre-commit Bandit scope
  `runner mobile_console scripts desktop_console bot` must stay at
  `SEVERITY.HIGH=0` and `SEVERITY.MEDIUM=0`, and should remain at `results=0`
  and `errors=0` after each security or operator-script change.
- Keep `training/` supply-chain clean: Hugging Face `from_pretrained()` calls
  in scripts and notebooks must use an immutable
  `CTOA_TRAINING_MODEL_REVISION` commit SHA, remote model code must stay opt-in,
  GitHub dataset collectors must validate API/raw HTTPS hosts, allowlisted query
  strings, decoded URL paths, decoded dataset filenames, and backslashes before
  `urlopen` or file writes, and Bandit should report zero findings for both
  `training` and the broader `bot training scoring agents` slice.
- Keep prompt/eval/scoring workflows tolerant of partial operator context:
  BRAVE template rendering should surface missing variables as `[UNKNOWN]`
  instead of raising, and the prompt/scoring/evals Bandit slice should stay at
  zero findings.
- Keep bot runtime static-scan clean too: behavioral jitter and Q-learning
  exploration should use the centralized random helper, best-effort OS/UI
  probes should log concrete failures instead of silent `except/pass`, overlay
  subprocess launches should stay behind `runner.process_safety`, and hybrid
  bot template cache/source handling should reject path traversal, unsafe
  filename components, secret-bearing URLs, localhost/private/link-local or
  internal remote template hosts, and ambiguous remote template source paths
  before disk writes or `urlopen`.
- Keep bot client runtime profile handling diagnostic and atomic:
  `bot/config/runtime_profile.py` should not use broad `except Exception` for
  config load or numeric coercion, invalid profile JSON should expose a
  non-secret diagnostic code, and profile saves should use hidden PID/UUID temp
  files with `fsync`, `replace`, and cleanup.
- Keep Desktop Console updater guarded: release repos must stay in `owner/repo`
  form, Windows assets must be safe `.exe` filenames without path separators,
  update URLs/final redirects must stay on trusted GitHub HTTPS hosts, signed
  query strings are allowed only on final trusted GitHub asset CDN redirects,
  downloads must stay size-bounded and use temp-file cleanup plus atomic final
  replacement, and the desktop client must not auto-run downloaded update
  executables.
- Keep dependency audits clean: `pip-audit -r requirements.txt` and
  `npm audit --json` in `web\` should report zero vulnerabilities. Keep the
  web `postcss` pin/override unless Next ships a dependency path that no longer
  pulls vulnerable PostCSS. Keep `tests/test_web_dependency_security.py` as the
  regression guard for the PostCSS pin/override and lockfile tree.
- Keep non-security hashes explicit with `usedforsecurity=False`, prohibit
  Python `eval` in preview/parser tooling, and keep discovery agents on
  verified TLS by default. Insecure discovery TLS must remain explicit
  per-agent env opt-in only.
- Keep catalog/scout/ingest discovery requests behind
  `runner.http_safety.require_public_discovery_url`: public `http://` and
  `https://` targets are allowed, but loopback/private/link-local/metadata IPs,
  single-label or internal hostnames, embedded credentials, fragments, token
  query parameters, backslashes, and decoded path traversal must be rejected
  before `urlopen`.
- Keep runner HTTP callers behind `runner.http_safety.require_http_url` before
  generic network calls; token-bearing GitHub API wrappers and health/CI
  publishing must validate `GITHUB_REPOSITORY`/owner-name inputs through
  `runner.http_safety.require_github_repository` and use
  `runner.http_safety.require_github_api_url` so Bearer tokens are sent only to
  `https://api.github.com/repos/{owner}/{repo}/...` with non-empty owner/repo
  segments and without credentials, fragments, traversal, encoded path
  separators, or token query parameters.
- Keep Phase-5 attention notification webhooks behind
  `runner.http_safety.require_notify_webhook_url`: URLs must use HTTPS, target
  allowlisted Slack or Discord webhook hosts, and omit credentials, query
  strings, fragments, backslashes, empty/traversal segments, or encoded path
  separators before any `urlopen` call.
- Keep local runtime smoke URLs behind
  `runner.http_safety.require_loopback_http_url`; smoke credentials and bearer
  tokens must stay on `127.0.0.1`, `localhost`, or `[::1]` without credentials,
  query strings, fragments, backslashes, or traversal.
- Keep API auth-store and runner state artifact writes non-predictable:
  `api/main.py` auth JSON, `runner/runner.py` YAML state, and runner execution
  summary JSON, `runner/health_metrics.py` latest health snapshot JSON, and
  `desktop_console/app.py` operator settings JSON, plus Mobile Console admin
  settings and idea parking JSON, and `.ctoa-local/user-config.json` plus
  `.ctoa-local/bootstrap-state.json` from `ctoa_product_bootstrap.py` should use
  hidden PID/UUID temp files in the target directory, `fsync` before `replace`,
  cleanup in `finally`, and no `path.suffix + ".tmp"` sibling names. Desktop
  Console settings reads and Mobile Console local JSON reads should stay
  byte-bounded and fail closed to defaults for oversized, invalid, or symlinked
  state. API auth-store reads should stay byte-bounded, reject symlinked or
  invalid existing stores, and fail closed instead of seeding over a bad store.
  `ctoa_update_gate.py` should read
  `.ctoa-local/bootstrap-state.json` through a byte cap, reject symlinked state,
  and return a stable `invalid_bootstrap_state` status for malformed local
  launch state.
- Keep Helper/release-gate and sprint runtime state JSON/YAML writes on the
  same non-predictable temp-file contract. Helper profile audit, Helper goal
  audit, Helper release gate, Solteria Helper PowerShell test-env reports, and
  `sprint_state_sync.py` must use PID+UUID/GUID temp names with cleanup rather
  than PID-only or fixed suffix temp files.
- Keep LLM/model backend URLs behind shared fail-closed guards before prompts
  or provider keys are sent: local model HTTP is allowed only for loopback and
  `host.docker.internal`, remote model backends require explicit opt-in plus
  HTTPS, and Azure provider endpoints must be HTTPS hosts under the allowed
  Azure service domains with no credentials, query strings, fragments,
  backslashes, or traversal.
- Keep `scripts/ops` webhook senders behind route-specific guardrails. Generic
  Azure activity webhooks must be HTTP(S), Azure `discord_webhook` destinations
  must be allowlisted Discord webhook URLs, and Phase-5 notification webhooks
  must be allowlisted Slack or Discord URLs before any `urlopen` call.
- Keep Azure Activity webhook listener startup fail-closed: listener mode
  defaults to `127.0.0.1`, and any non-loopback bind requires
  `CTOA_AZURE_INGEST_SECRET` before the server starts.
- Keep trusted subprocess calls behind `runner.process_safety` where practical:
  resolve Git through `CTOA_GIT_BIN`/PATH/Windows Git fallback, resolve optional
  tools before use, avoid partial executable names in agent and ops code, and
  keep destructive sync helpers bounded to validated child paths under their
  target roots. Live-target open/export resolvers must also reject traversal,
  absolute, drive-rooted, and symlink-escape candidates, and manifest/export
  file handling must reject symlink traps before reading or writing evidence.
  Generator agents that write module artifacts must keep queue-provided output
  paths under `CTOA_GENERATED_DIR/<server-slug>/` and reject absolute paths,
  drive-style paths, traversal, backslashes, unsafe filename characters, and
  output symlinks before writing files or updating DB status. Generator
  manifest writes under `generated/manifests` must use the same containment and
  symlink-trap guard before writing per-run or latest manifest JSON.
  Read-side consumers of `generated/manifests/latest.json` must also reject
  `manifest_path` values that resolve outside the configured manifests
  directory before loading JSON or returning manifest summaries. Consumers that
  enumerate `generated/manifests/*/manifest.json` must use the same resolved
  containment check and skip symlinked run directories that escape the
  manifests root before trend, SLO, or night-report evidence is built.
  Night activity reports must also read logs through a bounded tail sample and
  expose sampled/source byte counts when the source log is truncated.
  Hybrid bot metrics/profiler exports must keep CSV/JSONL files under the
  selected metrics output directory and reject traversal, absolute paths,
  drive-style paths, backslashes, unsafe filename characters, control
  characters, unsupported extensions, realpath escapes, and symlink outputs.
  Track agents and generic deliverable writers must keep fallback deliverables
  under the repo root and reject absolute paths, drive-style paths, traversal,
  backslashes, unsafe filename characters, control characters, realpath escapes,
  and existing output symlinks before writing.
  Queue worker startup logs must display redacted Redis URLs, and invalid queue
  JSON payloads must not be copied into job metadata or result records.
  Generators that write executable helper scripts must emit the same guardrails
  so regenerated artifacts do not drift back to direct
  `subprocess`/PATH-only calls.
- Keep Control Center action execution on trusted executable resolution:
  Python-backed actions must use `CTOA_PYTHON_BIN` as an absolute existing path
  or the repo-local `.venv` Python, with audited failure when neither is
  available. Action workspace roots must resolve from repo-root or `web/` cwd
  without climbing above the repo, explicit `CTOA_WORKSPACE_ROOT` overrides must
  be absolute existing directories, and allowlisted scripts must remain inside
  that workspace. The action catalog read path must also be role-scoped so
  unauthenticated/member sessions cannot enumerate local command summaries.
  Cookie-authenticated action POST routes must reject explicit cross-site
  request signals before auth lookup or execution, and auth wrapper POST routes
  that forward invite, role, login, logout, or registration actions must use
  the same guard. Apply the same rule to chat and local seed-login proxy routes
  before rate-limit, body parsing, cookie/token forwarding, or backend fetch.
  Chat proxy payloads must be built from an explicit allowlist instead of
  spreading arbitrary client JSON into backend model requests.
- Keep web proxy route rate limits fail-closed on client identity:
  `/api/auth` and `/api/chat` must ignore `X-Forwarded-For` and `X-Real-IP`
  unless `CTOA_TRUST_PROXY_HEADERS=true`; trusted mode should accept only
  syntactically valid IP values and otherwise fall back to `unknown`.
- Keep Control Center API base URL config fail-closed: `VPS_API_URL` and
  `NEXT_PUBLIC_API_URL` must parse as absolute HTTP(S), must not include
  credentials, path components, path separators, query strings, or fragments,
  and must require HTTPS for non-local hosts before any proxy route or browser
  API call uses them.
- Keep Desktop Console API and Control Center URL handling on the same
  fail-closed contract before login, settings persistence, or browser launch:
  local HTTP is allowed, remote hosts require HTTPS, and URLs with credentials,
  query strings, or fragments must be rejected without echoing rejected values.
- Keep health/drift/worker subprocess surfaces on fixed executable resolution;
  optional cleanup hooks must use explicit tool resolvers instead of raw shell
  names.
- Keep mobile-console operator command execution and ops sync scripts on the
  same resolver path before launching external tools.
- Keep operator wrappers such as `ctoa_loader.py`, `engine_brain_doctor.py`,
  smoke checks, validator preflight, and nightly stability on
  `runner.process_safety`; new wrappers should resolve Python, Git, file
  openers, and optional tools before launch.
- Keep legacy Mythibia unsafe runtime bootstrap paths gated: the plaintext
  bootstrap must require `-UnsafeRuntimeBootstrap` plus
  `CTOA_ALLOW_UNSAFE_RUNTIME_BOOTSTRAP=true`, and bootstrap writes/removals
  must stay under the resolved client root.
- Keep local PowerShell installers and watchers separator-aware before
  recursive writes or cleanup: containment checks must include a path separator
  boundary and use `-LiteralPath` for replacement/removal operations. Scheduled
  task and Run-key names should stay under the `CTOA-*` namespace, watcher logs
  should remain under `%LOCALAPPDATA%\CTOA\logs`, and hidden runners should
  accept only existing repo-local `.ps1` targets.
- Keep VS Code workspace launch/task configs local-only and secret-free:
  Mobile Console launchers must bind to `127.0.0.1`, reference `CTOA_*`
  environment variables instead of committed passwords/tokens, and run the
  shared env preflight before starting.
- Keep operator Mobile Console launch guidance local-only too: `.\ctoa.ps1 up`,
  `docs/MOBILE_CONSOLE.md`, and Desktop Console connection-error hints should
  recommend `uvicorn mobile_console.app:app --host 127.0.0.1 --port 8787`, not
  `0.0.0.0`.
- Keep PowerShell background launchers secret-safe: avoid hidden
  `-EncodedCommand` wrappers that embed environment values, pass secrets through
  inherited process environment, and verify PID ownership before force-stopping
  long-running workers.
- Keep operator-facing PowerShell launchers input-validated before
  `Start-Process`: URL openers must reject unsafe protocols and embedded
  credentials, query strings, fragments, raw/decoded backslashes, and decoded
  `.`/`..` path traversal without echoing rejected values; client launchers
  should require absolute existing `.exe` paths plus safe
  profile names, and watcher loop scripts should execute only repo-local `.ps1`
  targets.
- Keep LAB003 operator smoke scripts on the same URL and process guardrails:
  mobile proxy and shift guard `BaseUrl` values must stay local loopback
  HTTP(S) origins, alert webhooks must be HTTPS unless explicitly loopback HTTP,
  webhook URLs must not include credentials or fragments, and child PowerShell
  launches must use the current `$PSHOME` executable rather than PATH-only
  `powershell`.
- Keep VPS/bootstrap scripts supply-chain-safe: do not pipe remote installer
  downloads into shells as root, prefer distro packages or pinned artifacts,
  validate target users, host strings, and deployment directories, avoid
  interpolating untrusted deploy paths into remote heredocs, and keep public
  ports closed unless explicitly enabled. Root wrappers, including deploy-time
  wrapper copies, must use private temporary files from `mktemp` plus cleanup
  traps instead of predictable `/tmp` paths. Mobile token rotation should
  follow the same rule for generated token, `.env`, and history temp files,
  with root-only secret permissions. `ctoa-vps.ps1` remote install/update
  flows should use randomized remote temp paths for copied wrappers and
  generated `.env` updates.
- Keep SSH/SCP target construction input-safe: env-provided remote users and
  hosts must be validated before command launch. Remote users should follow a
  lowercase system-user pattern; hosts should be restricted to valid IPv4, DNS
  labels, or bracketed IPv6; and SSH key paths must be resolved as literal
  existing files.
- Keep remote-script operator inputs on shared validators: URLs and URL lists,
  SQL literals, service names, status filters, git refs, timer values, and
  similar heredoc/placeholder inputs should not rely on one-off string
  replacement or ad hoc quoting.
- Keep local GS reset operator inputs fail-closed before service shutdown or
  health probes: `API_HEALTH_URL` and `API_BASE_URL` must stay local HTTP(S)
  URLs on `127.0.0.1`, `localhost`, or `[::1]` without credentials, query
  strings, fragments, or `API_BASE_URL` path components, and retry/wait values
  must be positive integers. Direct `gs-api-validator.py` runs must enforce the
  same loopback-only API URL contract before `urlopen`, not only rely on
  `gs-reset.sh`.
- Keep remote secret writes command-line-safe: operator actions must not embed
  PATs, passwords, or tokens in SSH command strings, base64-encoded remote
  scripts, or shell `echo` fragments. Use validated temp files, stdin, or other
  non-argv transfer paths, then clean up local and remote secret-bearing temp
  files.
- Keep sprint validators on the same `runner.process_safety` path for focused
  regression tests, including older validator scripts that are mostly
  historical CI evidence gates.
- Keep the pre-commit Bandit scope at zero subprocess audit findings
  (`B404`, `B603`, `B607`) by routing long-running launches through
  `process_safety.start_trusted` and one-shot commands through
  `process_safety.run_trusted`.
- Keep broad exception-control findings closed: prefer concrete exception
  types for parse/read/decode/zlib paths, and record structured diagnostics for
  best-effort cleanup, breakpoint, or probe failures instead of silently
  swallowing them.
- Keep bot ML regression tests isolated from local runtime state: stress tests
  must not load persisted `runtime/state/qtable_*.json`, and reward shaping
  must not reinforce `loot` in healthy no-target states.

## P1: OTClient Source Normalization

- Keep the expanded `scripts/lua/otclient/` folder canonical.
- Keep generated ZIPs under `runtime\solteria_helper_dev\` or release staging,
  not beside source files.
- Add Lua syntax validation for every OTClient source file.
- Add helper smoke instructions for each main tab/subtab.
- Keep `docs/otclient/helper_redesign.md` as the active UI rebuild brief and
  update it after each Helper layout pass.

## P2: OTClient Helper Hardening

- Execute `docs/otclient/ctoai_runtime_2_execution_plan.md` in order. P0 now
  provides a passive runtime module registry, isolated event bus, and budgeted
  scheduler; all tasks remain disabled by default and runtime actions remain
  behind the existing policy and dispatch guards.
- Continue P1 with the passive `ctoa.combat-observation.v1` adapter. It may
  normalize and publish targeting/combat observations, but it must not call
  attack, walk, cast, talk, item-use, or keypress APIs.
- Runtime 2 P2 now exposes additive `ctoa.runtime-core.v1` status through Helper
  diagnostics, bounded exports, and client capability reports. Preserve the
  disabled/deferred/failed counters and `runtime_actions=false` invariant.
- Runtime 2 P3 now includes disabled-by-default combat/targeting and
  recovery/healing observers. Continue next with cavebot/pathing, then loot and
  equipment; require observer-only tests before any executor design.
- Runtime 2 P3 observer migration is complete repo-side across combat,
  recovery, cavebot, loot, and equipment. Preserve the five-registered/zero-
  enabled safe-boot invariant until P4 evidence authorizes executor design.
- Keep Runtime 2 P4 blocked while Helper evidence freshness is unresolved and
  in-world ModuleAttachSmoke/SmokeAttachAll plus current live approval are
  missing. Passing local static gates alone must not authorize an executor.
- Use the official `GoalStatus` action after SmokePreflight and
  ModuleStaticGates so release-gate freshness is regenerated before goal audit.
- Keep the seven Runtime 2 files in every test-env package, manifest, sync, and
  enable/disable list; package coverage tests must fail when one is omitted.
- Keep smoke-command paths in one filesystem domain: virtual resource paths may
  be probed with `g_resources`, while `io.open` must consume the resolved host
  work-directory path. Preserve regression coverage for virtual UI prefs.
- Split `ctoa_native_helper.lua` into smaller modules if the target client
  supports module-local `dofile` cleanly.
- Maintain `schemas/otclient-helper-config.schema.json` as the machine-readable
  config schema for `HELPER_CONFIG`.
- Keep `scripts/ops/otclient_helper_profile_audit.py` in `ValidateDev` so old
  `ctoa_ek_profile.lua` files cannot silently arm unsafe runtime behavior.
- Add explicit UI smoke states for hunting, tools, profile, and UI tabs.
- Keep the Helper redesign Phase 3 summary strips current for Healing, Hunting
  Targeting, Hunting Magic, Tools Helper, Profile, and UI.
- Keep the release gate strict: in-world `SmokeAttachAll` evidence must carry a
  SHA-256 binding to the current dev manifest before it can satisfy visual
  acceptance; mtime is only a legacy-staleness signal.
- Treat the Phase 3 summary implementation as visually accepted for the current
  dev manifest after `SmokeAttachAll` run `20260706-1025`; future Helper UI
  changes must rerun in-world `SmokeAttachAll`.
- Keep `SmokeStatus` and `ReadyCheck` evidence readable during blocked sandbox
  states; missing-window and Select Character/modal-helper-offline blockers
  should produce JSON with the next safe operator command.
- Keep the release gate next-command logic tied to current sandbox evidence:
  `Launch` for not-running, `ReadyCheck` for readiness blockers, and
  `SmokeAttachAll` only after `ready_check.json` reports `ready`.

## P3: Generator Quality Upgrade

- Align generic generated Lua templates with OTClient-native capabilities where
  an adapter exists.
- Add stronger Lua validation beyond bracket balance when `luac` is missing.
- Add negative tests for unsafe runtime activation.
- Add quality scoring for cooldowns, bounded retries, and guard checks.

## P4: TFS Fork Index

Blocked until TFS source is available.

Once available:

- Index C++ classes and ownership boundaries.
- Index protocol packets and extended opcodes.
- Index Lua script interface and callback names.
- Write server-side rulebook entries based on actual code.
- Add packet/event flow diagrams.

## P5: End-To-End Evidence

- Connect generated module manifests to release evidence.
- Keep the Control Center read-only Helper status panel backed by
  `runtime\solteria_helper_dev` artifacts.
- Keep the Control Center read-only Engine Brain status panel backed by
  `AI/generated/manifest.json`, `ENGINE_BRAIN_PACK.json`, `DOC_SYNC.json`, and
  `SECRET_GUARDRAIL.json`.
- Keep the Control Center artifact freshness panel read-only and backed by
  manifest age, ZIP SHA256 comparison, smoke evidence, live-promotion evidence,
  and action audit traces. Helper ZIP SHA256 comparison must resolve package
  paths inside the configured Helper dev lane only; external or escaping
  `release_readiness.json` package paths should fail closed as missing evidence.
- Keep release evidence packs reporting OTClient Helper package validation and
  release gate state when Helper files change.
- Keep release evidence packs reporting the generated P7 operator brief status,
  decision, blockers, warnings, and next safe command from
  `AI/generated/P7_OPERATOR_BRIEF.json`.
- Keep release evidence packs aligned with Control Center Helper semantics:
  durable `live_promotion.json` evidence must report `status=promoted` and must
  not leak stale next-command guidance after the release gate has passed.
- Keep `scripts/ops/release_evidence_pack.py` on the same local evidence read
  contract as Control Center: configured JSON reads are byte-bounded and
  symlink-rejecting, action-audit JSONL is counted from a bounded tail sample,
  release markdown discovery ignores symlinked files, and a symlinked Helper dev
  directory fails closed to missing Helper status.
- Keep Control Center release-evidence and action-audit drilldowns read-only:
  release markdowns should show latest tracked files and sprint coverage, while
  action audit should show sanitized metadata rather than raw command output.
- Keep release-evidence drilldown metadata reads bounded too. Markdown title
  extraction should read only a small capped prefix, reject symlinked or
  oversized files, and fall back to the file name instead of full-file reads.
- Keep those drilldowns visible in both the dedicated Evidence tab and the
  Overview/Local Status ops detail panels through `/api/control-center/ops`.
- Keep Control Center evidence read endpoints operator-gated. Anonymous users
  and `member` sessions must not receive runtime evidence JSON, ops detail
  payloads, release-evidence markdown, API cost markdown, local filesystem paths,
  or action-audit metadata.
- Keep browser-visible Control Center evidence paths display-safe: repo-local
  paths may be shown relative to the repo, while external absolute paths should
  be collapsed to `[external]/name` instead of exposing user profile, temp, live
  client, or custom runtime parent directories.
- Keep browser-visible Control Center markdown reports on the same sanitizer:
  release-evidence and API-cost markdown endpoints must redact token/password
  forms and collapse Windows or POSIX absolute local paths before returning
  text to the browser, while preserving normal UI/API route text like
  `/api/control-center/actions`.
- Keep Control Center markdown report reads physically size-bounded. Release-
  evidence and API-cost markdown endpoints should read at most `max + 1` bytes,
  close file handles in `finally`, reject symlinked configured report files
  before `open`, and reject oversized configured files without full-file
  `readFile`.
- Keep Control Center configured JSON evidence reads physically size-bounded
  too. Repo hygiene, API cost, Helper, Engine Brain, and runtime evidence JSON
  should reject symlinked or oversized configured files and fail closed to
  missing/default status without exposing target contents.
- Keep backend `/api/release-evidence` on the same browser-safe evidence
  contract: read configured JSON with a size bound, return display-safe
  `evidence_path`, recursively redact token/password/API-key fields and local
  absolute paths from the evidence payload, reject symlinked configured
  evidence before `stat/open`, and reject oversized evidence without echoing
  file contents or exception text.
- Keep FastAPI HTTP audit logs secret-safe too. `CTOA_AUDIT_LOG_FILE` records
  should redact token/password/API-key/Bearer forms and collapse local absolute
  paths in `actor`, `ip`, `ua`, request path, and nested `meta` before JSONL
  persistence.
- Keep FastAPI proxy header trust explicit. `X-Forwarded-For` must not drive
  audit IPs or rate-limit buckets unless `CTOA_TRUST_PROXY_HEADERS=true`; when
  enabled, only the first syntactically valid IP from the header is accepted.
- Keep browser-visible Control Center action results on that same sanitizer:
  stdout/stderr and local execution failure messages returned from
  `/api/control-center/actions` must redact token/password forms and collapse
  Windows or POSIX absolute local paths before the UI or audit preview can
  display them.
- Keep `/api/control-center/actions` route-level error JSON on the same
  sanitizer too. Unknown-action, authorization, malformed, or internal action
  errors must not echo token-like input or local host paths back to the browser.
- Keep `/api/control-center` and `/api/control-center/legacy` fallback status
  payloads on that same browser-visible sanitizer. Backend probe/fetch failures
  must not expose token/password forms or Windows/POSIX local paths in JSON
  summaries/details.
- Keep Control Center action-audit persistence secret-safe too: action `reason`
  and `output_preview` fields must be redacted before writing
  `runtime/control-center/action-audit.jsonl`, not only when rendered back
  through the evidence drilldown.
- Keep Control Center action-audit read paths on the same shared redaction
  helper as persistence. Evidence and ops drilldowns must sanitize legacy or
  hand-written JSONL records before displaying `reason`, `output_preview`,
  action metadata, or count keys. Redaction must cover Bearer/provider-token
  forms, unquoted `key=value` secrets, and quoted JSON-like
  token/password/API-key fields.
- Keep Control Center action-audit drilldown physically bounded too. Oversized
  `runtime/control-center/action-audit.jsonl` files should be read as a
  redacted tail sample, symlinked audit paths should be rejected before `open`,
  and Evidence/Ops should share the same bounded reader while reporting
  `truncated/sourceBytes/sampledBytes` and surfacing a `warn` state until
  retention is reviewed.
- Keep Control Center action execution fail-closed: action runners must not
  invoke PATH-only `python`/`python3`; missing trusted Python should be visible
  as an audited failed action.
- Keep allowlisted Control Center action scripts on realpath containment:
  repo-relative script paths must not escape the workspace through symlinked
  parents or junctions, and direct script symlinks should be rejected before
  `execFile`.
- Keep the runtime-vs-tracked release evidence comparison visible in Control
  Center so `runtime/evidence/latest.json` and `latest.md` can be checked
  against the newest tracked release-evidence markdown before sign-off.
- Keep durable live-promotion evidence in the Helper release gate: after
  promotion, `live_promotion.json` must contain approval evidence, be newer
  than the current manifest, and match live client file hashes to the staged
  manifest. If `-LaunchAfterPromote` is used, the report must also record the
  explicit launch result without treating launch as a release-gate bypass.
- Surface that same durable live-promotion evidence in Control Center as a
  read-only status card and artifact health check; do not add deploy actions
  that bypass `PromoteLiveCtoa -ApproveLiveDeploy`.
- Add Control Center tests for new evidence cards before expanding operator
  actions.
- Add local smoke launcher for OTClient helper packaging.
- Add screenshots or log evidence for helper UI load tests.

## P6: Codex Integration

- Add nested `AGENTS.md` under `AI/` and `scripts/lua/`.
- Keep Plan 3 Engine Brain artifacts in the portable `brain pack` before
  converting the workflow into a Codex skill.
- Keep scoped context profiles stable after exposing them through the local
  `ctoa-engine-brain` skill.
- Generate `AI/generated/P6_CODEX_INTEGRATION_READINESS.md` during
  `brain refresh` as the read-only gate for plugin design. It must verify the
  local skill, scoped packs, Control Center evidence contracts, release evidence
  tooling, full workspace validation evidence, doc sync, and secret guardrails
  before reporting `ready_for_plugin_design`.
- Keep the local `ctoai-engine-brain` plugin centered on the read-only
  `ctoai_control_central` entrypoint. Its compact default must unify `brain`,
  `control-center`, `plugin-management`, and `sites`, measure payload reduction,
  and expose full drilldown only for a selected lane. Retain the four direct
  status/brief/cockpit tools as compatibility drilldowns. Keep write authority
  bounded to audited repo-hygiene, API-cost, evidence-pack, Engine Brain, and
  P7 cockpit-smoke refreshes. Its
  plugin manifest, MCP config/server, operator skill, and personal marketplace
  entry must be detected by P6 readiness before moving beyond plugin design.
  After cachebuster/reinstall, P6 readiness should also detect the installed
  Codex cache version.
- Keep the plugin-owned `scripts/ctoai_engine_brain_status.py` smoke script
  read-only and secret-safe. It should summarize manifest, P6 readiness, pack,
  doctor, audit, and validation status without reading `.env`, logs, databases,
  or live client state.
- Keep the plugin-owned `scripts/ctoai_engine_brain_mcp.py` server bounded.
  Its MCP tools should expose only `ctoai_control_central`, `ctoai_engine_brain_status`,
  `ctoai_engine_brain_self_check`, `ctoai_engine_brain_brief`,
  `ctoai_control_center_cockpit`, `ctoai_repo_hygiene_refresh`,
  `ctoai_api_cost_refresh`, `ctoai_evidence_pack_refresh`,
  `ctoai_engine_brain_refresh`, and `ctoai_p7_cockpit_smoke_refresh`, backed by
  generated evidence, plugin install checks, action-audit evidence, runtime
  Control Center cockpit state, and read-only operator handoff.
- Keep the plugin-owned `scripts/ctoai_engine_brain_brief.py` as the P7 daily
  operator entrypoint. It should return decision, warnings, P6/validation
  status, and the next safe command without running deploy/live actions.
- Generate `AI/generated/P7_OPERATOR_WORKFLOW.md` and `.json` during
  `brain refresh` as the P7 risk gate. It must report `read_only_ready`,
  list the four read-only plugin MCP tools plus the explicitly audited
  safe-write refresh tools, and keep `guarded_write`, `dangerous`, and
  `forbidden_ui` action classes blocked.
- Generate `AI/generated/P7_ACTION_READINESS.md` and `.json` during
  `brain refresh` as the bridge from read-only P7 to bounded `safe_write`
  tools. It must list Control Center `safe_write` candidates, count sanitized
  `runtime/control-center/action-audit.jsonl` evidence, and distinguish
  expected bounded MCP write tools from unexpected write tools.
- Generate `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md` and `.json` during
  `brain refresh` as the primary `safe_write` MCP contract. It keeps
  `evidence-pack-refresh` / `ctoai_evidence_pack_refresh` as the primary
  design, allows `repo-hygiene-refresh` / `ctoai_repo_hygiene_refresh` and
  `api-cost-refresh` / `ctoai_api_cost_refresh` plus
  `engine-brain-refresh` / `ctoai_engine_brain_refresh` and
  `p7-cockpit-smoke-refresh` / `ctoai_p7_cockpit_smoke_refresh` as additional bounded
  evidence/context refreshes, and requires Control Center audit parity.
- Generate `AI/generated/P7_OPERATOR_BRIEF.md` and `.json` during
  `brain refresh` so Control Center and release evidence can consume the P7
  operator decision, workflow gate, action-readiness summary, and safe-write
  tool design without loading the plugin MCP server.
- Keep P6 readiness strict about that P7 Control Center contract: `brain
  refresh` must fail plugin-design readiness if Control Center config, evidence
  payloads, ops payloads, or Evidence UI stop consuming
  `AI/generated/P7_OPERATOR_BRIEF.json`.
- Keep Control Center Evidence surfacing a read-only P6 plugin handoff from
  `AI/generated/P6_CODEX_INTEGRATION_READINESS.json`, including installed cache
  version, marketplace status, MCP contract counts, and the fresh-thread
  verification step for the installed plugin tool layer.
- Keep P6 handoff blocking plugin MCP startup regressions: `.mcp.json` must use
  an absolute runnable `ctoai_engine_brain_mcp.py` path, and validation must
  distinguish fresh-session tool discovery from noninteractive approval-free
  execution.
- Keep `scripts/ops/control_center_p6_plugin_handoff_smoke.py` as the read-only
  P6 plugin handoff acceptance gate. It must write
  `runtime/control-center/p6-plugin-handoff-smoke.json`, validate plugin
  manifest/cache version parity, P6 readiness, P7 operator workflow policy,
  P7 cockpit smoke, and P7 dry-run smoke before fresh-thread MCP verification.
- Surface `runtime/control-center/p6-plugin-handoff-smoke.json` in Control
  Center Evidence and Ops as the visible P6 plugin handoff smoke: smoke status,
  check counts, current-thread discovery state, fresh-thread verification
  status, recommended tool order, and source link.
- Surface the same P6 plugin handoff smoke in the local `ctoai-engine-brain`
  plugin status, operator brief, Control Center cockpit, self-check, and MCP
  safe-write preflight. P6 readiness must block plugin-design readiness if the
  plugin source stops reporting `p6_plugin_handoff_smoke`.
- Keep Control Center Evidence and Ops drilldowns surfacing the generated P7
  action-readiness fields from `AI/generated/P7_OPERATOR_BRIEF.json`: action
  readiness status, audited candidate count, MCP write-tool count, and next
  safe command.
- Keep Control Center Evidence and Ops drilldowns surfacing the generated P7
  safe-write design fields from `AI/generated/P7_OPERATOR_BRIEF.json`: design
  status, selected action, proposed MCP tool, MCP enabled flag, and next safe
  command.
- Keep Control Center Engine Brain cockpit cards correlating all enabled P7
  safe-write actions with `runtime/control-center/action-audit.jsonl`,
  including latest matching audit ids, risk classes, dry-run/confirmed modes,
  authorization results, and sanitized summaries.
- Keep the P7 cockpit summary read-only and generated from
  `AI/generated/P7_OPERATOR_BRIEF.json`: enabled safe-write MCP tool count,
  ready audit count, and per-tool audit status list must stay visible in
  Control Center Evidence and Ops drilldowns. P6 readiness must block plugin
  design if this cockpit summary or enabled-tool audit list disappears from the
  Control Center payload, Ops summary, Evidence UI, or detail UI.
- Keep `scripts/ops/control_center_p7_cockpit_smoke.py` as the repeatable
  read-only P7 cockpit acceptance gate. It must validate the generated P7
  operator brief, workflow, action readiness, safe-write design, release
  evidence pack, and `runtime/control-center/action-audit.jsonl` together
  before P6/P7 handoff is considered operator-ready.
- Surface `runtime/control-center/p7-cockpit-smoke.json` in Control Center
  Evidence and Ops as read-only P7 smoke status, including check counts,
  safe-write audit counts, artifact health, and source links.
- Surface `runtime/control-center/p7-cockpit-smoke.json` through the local
  `ctoai-engine-brain` plugin cockpit, self-check, and safe-write preflight.
  Missing smoke remains a warning to avoid refresh bootstrap loops; present
  non-ready smoke is a plugin cockpit blocker.
- Keep `scripts/ops/control_center_p7_safe_write_dry_run_smoke.py` as the
  operator smoke for the six bounded P7 safe-write MCP tools. It must call
  `ctoai_repo_hygiene_refresh`, `ctoai_api_cost_refresh`,
  `ctoai_evidence_pack_refresh`, `ctoai_engine_brain_refresh`, and
  `ctoai_p7_cockpit_smoke_refresh`, and `ctoai_roadmap_state_refresh` with
  `dry_run=true`, verify the plugin stdio payloads, and prove matching
  `runtime/control-center/action-audit.jsonl`
  records before a new plugin action is designed.
- Treat P7 safe-write dry-run smoke as operator-ready only when it reports
  `dry_run_ready_count=6`, `preflight_ready_count=6`, and
  `bootstrap_allowed_count=0`. The explicit bootstrap allowance is only a
  temporary self-stale P7 audit/smoke recovery path, not the normal cockpit
  acceptance state.
- Surface `runtime/control-center/p7-safe-write-dry-run-smoke.json` in Control
  Center Evidence and Ops as read-only P7 dry-run smoke status, including check
  counts, dry-run tool readiness, per-tool audit/preflight/bootstrap status,
  artifact health, operator-next gating, and source links.
- Keep Control Center artifact health aligned with the same P7 dry-run smoke
  acceptance rule: a bootstrap-only or partial-preflight smoke report must be a
  blocking mismatch, not a passed artifact.
- Once all six enabled P7 safe-write tools have current dry-run/preflight
  evidence, let the generated operator recommendation advance to the selected
  confirmed evidence refresh only:
  `ctoai_evidence_pack_refresh dry_run=false confirm='refresh evidence pack'`.
  Do not expose confirmed deploy/live/client actions through this path.
- After a confirmed `evidence-pack-refresh` audit record exists, move the
  generated P7 handoff to `review_confirmed_safe_write_evidence`: review
  `runtime/control-center/action-audit.jsonl` and `runtime/evidence/latest.json`
  before designing the next plugin action. Do not keep recommending the same
  confirmed refresh in a loop.
- Keep `scripts/ops/control_center_p7_evidence_review.py` as the read-only
  review gate for that confirmed evidence. It must validate the confirmed
  `dry_run=false` evidence-pack audit, release evidence, P7 cockpit smoke, P7
  dry-run smoke, and P6 handoff smoke before the generated P7 handoff advances
  to `design_next_p7_plugin_action`.
- Surface `runtime/control-center/p7-safe-write-dry-run-smoke.json` through the
  local `ctoai-engine-brain` plugin cockpit, operator brief, self-check, and
  safe-write MCP preflight. Missing dry-run smoke remains a warning to avoid
  bootstrap loops; present non-ready dry-run smoke is a plugin cockpit blocker.
- Keep the plugin `ctoai_control_center_cockpit` payload aligned with Control
  Center drilldowns: release evidence should expose status, sprint/file
  coverage, recent markdown titles, and source paths; action audit should expose
  a bounded, redacted tail sample with risk/action counts, invalid-line counts,
  source/sample byte counts, and recent sanitized records. P6 readiness must
  block if those read-only drilldown markers disappear from the plugin source.
- Keep the plugin `ctoai_control_center_cockpit` payload exposing a read-only
  `operator_next` recommendation that mirrors the Control Center operator-safe
  next step, prefers audited P7 dry-run safe-write refreshes, and suppresses
  guarded live-promotion commands. P6 readiness must block if the plugin source
  loses the `operator_next` contract or its guarded-command filter.
- Keep the plugin P7 cockpit smoke contract under regression coverage. P6
  readiness must block if tests stop checking the MCP tool schema, forbidden
  deploy/live/promote tool-name fragments, cockpit smoke fields, or safe-write
  preflight smoke status.
- Expose one read-only `operatorNext` recommendation in Control Center Evidence
  and Ops. It must be derived from existing Engine Brain, P7 smoke, action
  audit, and artifact-health gates; it must prefer audited P7 dry-run
  safe-write refreshes when P6/P7 are ready; and it must not expose guarded
  live-promotion commands as a top-level command.
- Keep a dedicated read-only `P7 operator brief` card in Control Center
  Evidence backed by `AI/generated/P7_OPERATOR_BRIEF.json`. It must show the
  generated cockpit handoff, P7 smoke status, P7 dry-run smoke status,
  release-evidence coverage, action-audit counts, and recommended tool order
  without exposing guarded live-promotion commands.
- Keep the plugin cockpit and operator brief exposing read-only
  `roadmap_generation` status from `AI/FEATURE_ROADMAP.md`,
  `AI/ENGINE_BRAIN_STATUS.md`,
  `docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md`, and
  `AI/generated/DOC_SYNC.json` before expanding plugin actions.
- Keep the CTOAi plugin bounded to one compact Control Central entrypoint, four
  compatibility read-only status/cockpit drilldowns, plus
  `ctoai_repo_hygiene_refresh`, `ctoai_api_cost_refresh`,
  `ctoai_evidence_pack_refresh`, `ctoai_engine_brain_refresh`, and
  `ctoai_p7_cockpit_smoke_refresh`, plus `ctoai_roadmap_state_refresh`.
  The default read-only tool is `ctoai_control_central`; the full cockpit
  drilldown remains `ctoai_control_center_cockpit`. All safe-write tools must default to
  dry-run, require `ctoai_control_center_cockpit` preflight status `ready`,
  write `runtime/control-center/action-audit.jsonl`, and reject non-dry-run
  calls unless the explicit confirmation text is supplied.
- Expand the CTOAi plugin beyond these six safe-write MCP tools only after the
  next action has risk model coverage, audit logging, Control Center evidence
  gates, and targeted MCP tests.
- Evaluate Repomix MCP mode for secret-safe full-repo context packs.
