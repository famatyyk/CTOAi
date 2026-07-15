# CTOAi Three Development Plans

Basis: full workspace audit with `45487` inventoried files and `1382` git-tracked files.

## Plan 1: Helper-First Productization

Goal: turn the OTClient/Solteria Helper into a safe, repeatable product lane before broad expansion.

Product split: Helper remains the primary full platform and owns P8-P16. CTOA Safe is a separate compact movable panel with fixed module labels and deep editing only inside supported modules. Safe has no CaveBot, movement/routes, generic Settings, arbitrary Lua, or authority to satisfy a Helper gate.

### 0-30 Days

- Keep `scripts/lua/otclient/` canonical and keep live Solteria protected.
- S0 source and staging are complete in candidate `v2.4.0`: the neutral chooser is the only CTOA autoload, requires a new Helper/Safe choice after every login, rejects direct project startup, and terminates the selected project on logout. Safe contains only its `.otmod`, explicit loader, and self-contained project; copied Helper runtime files, CaveBot, and generic Settings are absent.
- Keep S0 operational acceptance pending until a fresh sandbox Safe selection plus ENABLE smoke passes without a client crash and the separately approved, manifest-bound promotion is verified. Staging evidence cannot claim the live crash fixed.
- Require `PrepareDev`, `ValidateDev`, `SmokePreflight`, in-world `SmokeAttachAll`, and explicit live approval.
- Expand `otclient_helper_profile_audit.py` from text checks toward schema-backed migration validation.
- Keep Control Center Helper status read-only and backed by runtime artifacts.
- Current Helper phase state: P8, P9, P10, and P11 are `operational_acceptance_complete`; P12 execute-once review is `closed_with_deferred_heal_friend_lane`. Conditions and Equipment are separately accepted, terminally disarmed, zero-retry, and grant no downstream authority. Heal Friend plan `964ff8f0c178c7b646a565380e96846a8b29780eb02a734a259713d9ccf023b3` is `closed_blocked_no_compatible_vocation`: its approved sandbox session reached a fresh ED-only blocked preflight, then `p12_heal_friend_no_compatible_vocation_closure.json` expired the approval because only sorcerer and knight are available. Attempt count is 0, execution approval and reuse are forbidden, and no cast, retry, downstream authority, or live promotion occurred. P13 Runtime Evidence And Machine-Readable Roadmap State is `runtime_evidence_ready`: its fixed seven-entry ledger, SHA-pinned schema registry, freshness/tamper validation, atomic generator, sanitized audit trail, read-only Control Center surface, and release-evidence consumer are implemented and tested. Exact confirmation `refresh roadmap state` authorized the fixed JSON/Markdown outputs and their hash-bound confirmed audit record. No runtime executor, MCP write tool, live authority, or P12 Heal Friend reopening is introduced. Keep BackgroundNoScreen as the default routine evidence lane with no mouse/keyboard input, focus, screenshots, client launch/stop, or live-client writes.
- P14 Independent Runner And Release Automation is active as `foundation_in_progress`: signed artifact-only request/result schemas, tracked-source package manifest derivation, clean-checkout/revision binding, deterministic manifest rollback replay, Windows CI, Release Evidence, and a read-only Control Center card are implemented. A real second-machine/VM result, isolated visual/in-world suite, canary, and actual rollback rehearsal remain required; no promotion, runtime/live authority, or additional MCP tool exists.
- Keep the post-Recovery runtime sequence fixed: Conditions paralyze-only gate, then Equipment ring-only rollback gate, then Heal Friend exact-whitelist gate. Require action-bound predecessor traces and current `RuntimeModuleGatesSandboxSmoke` evidence; Combat and CaveBot remain `deferred_high_risk` and may receive passive refactor work only.

### 31-60 Days

- Split `ctoa_native_helper.lua` only along stable boundaries: config/schema, profile persistence, UI, runtime loops, diagnostics.
- Preserve `ctoa_project_loader.lua` as the only public root loader; keep `ctoa_native_helper.lua` reachable only through an authorized Helper selection.
- Add stable diagnostics export coverage for HP/MP, movement, combat, magic, container/loot, UI/resources.

### 61-90 Days

- Keep visual acceptance explicit, but move `SmokeAttachAll` screenshots to a separate runner/VM or user-provided review so routine Codex work never takes over the user's only screen.
- Block `releasable_to_live=true` unless staged package hashes match full in-world evidence.
- Package Helper release notes and evidence as one reviewable artifact.

## Plan 2: Control Center And Evidence Platform

Goal: make Control Center the operator cockpit for status, evidence, safe commands, and release confidence.

### 0-30 Days

- Normalize evidence paths through `controlCenterEvidenceConfig.ts` and `.env.example`.
- Add tests for every evidence payload shape before adding UI panels.
- Keep Control Center markdown report reads physically size-bounded with file-handle reads of at most `max + 1` bytes, symlink rejection before `open`, `finally` cleanup, and no full-file `readFile` path.
- Keep Control Center release-evidence drilldown metadata bounded too; title extraction must not full-read large markdown artifacts.
- Keep Control Center configured JSON and action-audit reads physically bounded, symlink-rejecting, and fail-closed before any browser-visible evidence payload is built.
- Keep release evidence pack generation on the same bounded, symlink-rejecting local-read contract for configured JSON, action-audit JSONL, release markdown discovery, and Helper dev status.
- Keep Control Center API base URLs origin-only: reject path components, path separators, credentials, query strings, fragments, and non-local HTTP before proxy or browser API calls.
- Keep panels read-only unless actions are explicitly risk-modeled and audited.
- Keep API public registration fail-closed in production; privileged account creation must always require an authenticated owner token.
- Keep production Intel launch targets protected from localhost/private/internal URLs unless `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true` is explicitly set.
- Keep Intel client-sync write paths confined to `CTOA_CLIENT_SCRIPTS_DIR` and validate target/autoloader/init settings before copying files.
- Keep the static security scan lane active: Bandit high and medium severity must remain zero, discovery TLS must verify by default, remote template sources must stay on public HTTP(S) hosts, and insecure legacy opt-ins must be explicit.
- Keep operator script inputs fail-closed before network calls or child processes: runtime smoke base URLs and LAB003 base URLs stay on loopback HTTP(S), generic alert webhooks must be HTTP(S), Discord-native alert webhooks must stay on allowlisted Discord webhook URLs, Azure Activity listener binds default to loopback and requires `CTOA_AZURE_INGEST_SECRET` for non-loopback hosts, LAB003 child PowerShell launches use the current `$PSHOME` executable, GS reset API URLs/timing values are validated before shutdown or health probes, and direct GS API validator probes stay loopback-only before `urlopen`.

### 31-60 Days

- Add release-evidence drilldowns for Helper, repo hygiene, API cost, action audit, and VPS parity.
- Surface `background_status.json` as a read-only Helper tile with heartbeat freshness, immutable parity, runtime state, and zero action controls.
- Add stale-artifact detection: manifest age, package hash mismatch with Helper dev-lane path containment, missing smoke, missing action audit.
- Add one operator-safe `next` recommendation surface that never bypasses gates.

### 61-90 Days

- Turn evidence pack generation into a release prerequisite.
- Add dashboard-level comparison between last released evidence and current runtime evidence.
- Add CI checks for evidence schemas and docs links.

## Plan 3: Engine Brain And CTOAi Platform

Goal: make `AI/` the local, secret-safe planning/context layer and evolve it into a reusable CTOAi/Codex capability.

### 0-30 Days

- Keep `AI/FEATURE_ROADMAP.md`, `AI/ENGINE_BRAIN_STATUS.md`, and `AI/generated/*` fresh after workflow changes.
- Use `ctoa.ps1 brain refresh`, `brain doctor`, and `brain pack` as the operator workflow.
- Add this full workspace audit as a recurring Engine Brain input.

### 31-60 Days

- Generate ownership maps from inventory: path owner, source/runtime/vendor category, validation gate.
- Add stale-doc detection between README, docs index, CLI docs, and command dictionary.
- Add local-only secret guardrails for AI packs and generated context.

### 61-90 Days

- Convert the stabilized Engine Brain workflow into a Codex skill or CTOAi plugin.
- Add repo context packs that can target Helper, Control Center, infra, or security lanes.
- Gate plugin design through `AI/generated/P6_CODEX_INTEGRATION_READINESS.md`, generated by `brain refresh` from current local evidence.
- Generate `AI/generated/P7_OPERATOR_WORKFLOW.md` as the read-only P7 risk gate before adding plugin actions.
- Generate `AI/generated/P7_ACTION_READINESS.md` as the audited safe-write candidate gate before enabling plugin write tools.
- Generate `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md` as the primary safe-write tool contract and require enabled safe-write MCP tools to match audited evidence/reporting actions.
- Generate `AI/generated/P7_OPERATOR_BRIEF.md` as the read-only daily operator handoff for Control Center and release evidence.
- Keep the local `ctoai-engine-brain` plugin bounded to `ctoai_engine_brain_status`, `ctoai_engine_brain_self_check`, `ctoai_engine_brain_brief`, plus audited `ctoai_evidence_pack_refresh` and `ctoai_api_cost_refresh` safe-write tools.
- Keep deploy/live actions out of the plugin MCP surface; only dry-run-first evidence/reporting refreshes may write, and they must append Control Center action-audit evidence.
- Prepare a plugin-style operator surface for audit, release evidence, and roadmap generation.
- Keep `AI/P8_P16_EXECUTION_ROADMAP.md` as the post-P7 execution contract: P8 background observability, P9-P11 independent low-risk shadow/replay lanes, P12 execute-once sandbox review, P13 evidence/roadmap state, P14 independent runner, and P15-P16 design-only Combat/CaveBot twins.
