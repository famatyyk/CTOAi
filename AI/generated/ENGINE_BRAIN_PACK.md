# CTOAi Engine Brain Pack

Generated at: `2026-07-11T12:51:30+00:00`
Repo root: `C:\Users\zycie\CTOAi`
Profile: `helper`

This pack is curated and secret-safe. It excludes `.env*`, auth stores,
runtime data, logs, local databases, tokens, credentials, and generated
dependency folders. It is intended as a portable context artifact for
Codex or another code assistant.

## Included Sources


## `AI/README.md`

```markdown
# CTOAi Engine Brain

This folder is the Codex working context for the current CTOAi + OTClient lane.
It is intentionally split into small files so a model can load only the slice
needed for a task instead of relying on one long prompt.

## Load Order

1. `SYSTEM_PROMPT.md`
2. `PROJECT_CONTEXT.md`
3. `ENGINE_MEMORY.md`
4. `RULEBOOK.md`
5. The relevant index file for the task
6. The relevant persona from `SPECIALIZED_PROMPTS.md`
7. `TASK_TEMPLATE.md`

## Source Snapshot

- CTOAi repo root: `C:/Users/zycie/CTOAi`
- OTClient source tree: `scripts/lua/otclient/`
- Expanded inspection source used for this package: `.tmp/otclient_ai_source/otclient`
- Current limitation: no TFS fork source tree was included in the workspace, so
  TFS engine classes, packet handlers, and server-side protocol flow are marked
  as pending source rather than inferred.

## Files

- `SYSTEM_PROMPT.md`: primary Codex behavior for this project.
- `PROJECT_CONTEXT.md`: repo architecture and integration map.
- `ENGINE_MEMORY.md`: stable facts, decisions, and current state.
- `RULEBOOK.md`: project-specific engineering rules.
- `ARCHITECTURE_INDEX.md`: subsystem map and data flow.
- `API_INDEX.md`: CTOAi HTTP/API and local model surfaces.
- `LUA_INDEX.md`: Lua runtime modules and helper APIs.
- `OTCLIENT_INDEX.md`: OTClient native module map.
- `PACKET_INDEX.md`: protocol/packet status and known gaps.
- `CLASS_INDEX.md`: important Python/Lua classes and tables.
- `FEATURE_ROADMAP.md`: next implementation lanes.
- `KNOWN_BUGS.md`: known risks and suspected defects.
- `TECH_DEBT.md`: cleanup backlog.
- `SPECIALIZED_PROMPTS.md`: project-aware task personas.
- `TASK_TEMPLATE.md`: reusable task intake and delivery template.
- `OPERATIONS_AUDIT.md`: current Docker/VPN/Vercel/GitHub/extension/local gate evidence.
- `CODEX_CAPABILITY_MAP.md`: Codex surfaces and external context tools to use next.
- `ENGINE_BRAIN_STATUS.md`: completion status, risks, and remaining work.
- `generated/FILE_TREE.md`: generated secret-safe file inventory.
- `generated/SYMBOL_MAP.md`: generated lightweight symbol map.
- `generated/manifest.json`: generated index metadata.
- `generated/ENV_DOCTOR.md`: generated local operations audit summary.
- `generated/ENV_DOCTOR.json`: generated local operations audit data.
- `generated/ENGINE_BRAIN_PACK.md`: generated portable secret-safe context pack.
- `generated/ENGINE_BRAIN_PACK.json`: generated context pack manifest.
```


## `AI/ENGINE_BRAIN_STATUS.md`

```markdown
# Engine Brain Status

Snapshot date: 2026-07-07 Europe/Warsaw

## Completed In This Brain

- Root prompt pack created under `AI/`.
- Project context summarized for CTOAi, OTClient Lua, API, and hybrid bot.
- OTClient helper source tree inspected and indexed.
- Lua and API surfaces indexed at a practical level.
- Packet/TFS sections marked as pending source rather than inferred.
- Operations audit added for Docker, VPN, Vercel, VS Code extension, GitHub, and
  local CTOAi gate.
- Codex capability map added for AGENTS.md, skills, MCP, hooks, plugins, and
  external context tooling.
- Generated file tree, symbol map, and manifest added under `AI/generated/`.
- `.\ctoa.ps1 brain refresh` added as the one-command local index refresh.
- `.\ctoa.ps1 brain doctor` added as the one-command local operations audit.
- `.\ctoa.ps1 brain pack` added as the one-command portable context packer.
- Nested `AGENTS.md` added for `AI/` and `scripts/lua/`.
- Docker compose defaults hardened to loopback through `CTOA_BIND_HOST`,
  `CTOA_BOT_DASHBOARD_BIND_HOST`, and `CTOA_MONITOR_BIND_HOST`.
- OTClient Helper `v2.1.1a` is live with current 49-file SHA-256 parity and
  fresh `Initialized successfully v2.1.1a` boot evidence. The stabilization
  patch passed its production gate:
  Graphite uses an amber accent, adaptive sidebar geometry and button/state
  roles are UI-owned, shell pressure is bounded to 4350 lines / 158 functions,
  the 20-shot theme matrix, 32/32 module gates, 16/16 attach smoke, and singleton
  relog evidence pass, and runtime remains disarmed.
- Helper P6 Module Lane is repo- and sandbox-complete. Its evidence-aware module audit promotes
  passive lanes only when the dedicated smoke, current module gates, ReadyCheck,
  and a newer in-world tab screenshot all exist. Heal Friend, Conditions,
  Equipment, and Scripting now meet that `static_gated` contract while every
  corresponding runtime action remains unavailable. Healing/Recovery also has
  a fail-closed sandbox vitals gate: it rejected an armed runtime, then passed
  only after clean safe boot produced bounded real HP/MP evidence and a newer
  Healing-tab attachment and promoted the recovery lane before Combat review.
- Helper P6 evidence now passes 9/9 lanes as `static_gated`. Combat reports no
  active target; CaveBot proves movement capability plus retry/PZ/offline/empty
  route guards without walking; Timer returns `hold_timer_disabled`; and Loot
  returns `hold_feature_flag_disabled`, zero planned items, and a read-only
  container capability sample. Every report has newer in-world tab evidence and
  runtime remains disarmed. The next functional step is a separately reviewed
  runtime bridge after the completed v2.1.1a stabilization.
- CTOAi Runtime 2 execution has started from the reviewed vBot architecture:
  `ctoa_helper_runtime_core.lua` now provides a passive runtime registry,
  failure-isolated event bus, and 4 ms budgeted cooperative scheduler with
  disabled-by-default tasks and bounded failure backoff.
- The first P1 slice, `ctoa_helper_combat_observer.lua`, normalizes and publishes
  `ctoa.combat-observation.v1` snapshots while remaining detached from OTClient
  action APIs and disabled after loader attachment.
- P1 is now wired through `ctoa_helper_otclient_observation_adapter.lua`, which
  performs guarded read-only target, spectator, protection-zone, cooldown, and
  latency reads. Its Runtime Core task remains disabled by default.
- Runtime 2 P2 is complete repo-side: `ctoa.runtime-core.v1` status is included
  in Helper diagnostics, bounded diagnostic samples, and the additive
  `runtime_core` capability-report section, including disabled, deferred, and
  failed task counters.
- Runtime 2 P3 has started with passive combat/targeting and recovery/healing
  observers. The recovery provider reads guarded HP, mana, percentage, PZ, and
  state APIs; both observer tasks remain disabled after loader attachment.
- Runtime 2 P3 is complete repo-side across combat, recovery, cavebot, loot,
  and equipment observation domains. Guarded providers expose only read state;
  the verified safe-boot snapshot contains five registered tasks, zero enabled
  tasks, and no executed tick work.
- Runtime 2 P4 executor work remains outside the v2.1.1a stabilization scope.
  The v2.1.1a Helper goal and release gate completed with a fresh manifest,
  static gates, theme matrix, in-world attach, relog evidence, and separately
  approved live promotion.
- Runtime 2 packaging now carries Runtime Core, five observers, and the guarded
  observation adapter through all five test-env package/sync/manifest lists.
  PrepareDev and ValidateDev rebuild the stage successfully with 117 tests;
  current attach and release evidence is complete.
- Sandbox attach diagnosis found and fixed a virtual/filesystem path mismatch:
  Helper derived `/ctoa_smoke_command.lua` from virtual UI prefs and then passed
  it to `io.open`, producing repeated `Smoke command failed: nil`. It now uses
  the real work-directory command file; the rebuilt package again passes 114
  tests; subsequent attach, relog, and live-promotion evidence completed.
- Helper-first 90-day plan adopted: Helper P0-P2 remain the active priority
  before broader CTOAi expansion.
- `schemas/otclient-helper-config.schema.json` added as the machine-readable
  `HELPER_CONFIG` safety schema.
- `scripts/ops/otclient_helper_profile_audit.py` added and wired into
  `ValidateDev` as the profile migration safety gate.
- Control Center evidence now includes a read-only OTClient Helper status
  surface backed by `runtime\solteria_helper_dev` artifacts.
- Release evidence packs now include OTClient Helper validation, package hash,
  release gate state, blockers, and next safe command.
- Release evidence packs now include the generated P7 operator brief status,
  decision, blocker/warning counts, and next safe command from
  `AI/generated/P7_OPERATOR_BRIEF.json`.
- Full workspace audit added through `scripts/ops/ctoa_full_workspace_audit.py`,
  with JSON inventory in `runtime/audits/` and durable docs in `docs/audits/`
  plus `docs/roadmaps/`. The inventory now uses `lstat`/regular-file checks and
  skips symlinked files before size accounting or SHA256 hashing, so repo-local
  symlinks cannot pull external local content into audit evidence. The audit
  also publishes an integrity gate with non-regular entry accounting, bounded
  hash counts, and proof that sensitive-name files were inventoried without
  content hashes. It now also consumes
  `runtime/audits/ctoai-full-workspace-validation.json` and reports a
  validation-evidence gate for Python, web, diff, and Engine Brain command
  evidence.
- Plan 3 first implementation wave completed: `brain refresh` now generates
  `OWNERSHIP_MAP`, `DOC_SYNC`, and `SECRET_GUARDRAIL` artifacts from the full
  workspace audit and canonical docs.
- Engine Brain indexing now prunes excluded volatile directories before
  traversal and tolerates disappearing build paths such as `web/.next/*`.
- `brain pack` now supports context profiles: `all`, `helper`,
  `control-center`, `infra`, and `security`.
- Local Codex skill `ctoa-engine-brain` added under
  `C:\Users\zycie\.codex\skills\ctoa-engine-brain` and validated with the
  skill creator quick validator.
- P6 Codex Integration has started as a read-only readiness gate rather than a
  deploy/action shortcut. `brain refresh` now generates
  `AI/generated/P6_CODEX_INTEGRATION_READINESS.md` and `.json`, checking the
  local Engine Brain skill, AGENTS.md coverage, Control Center evidence
  contracts, release evidence tooling, full workspace validation evidence,
  doc sync, and secret guardrails before reporting plugin-design readiness.
- Local plugin scaffold `ctoai-engine-brain` now exists under the user's local
  plugin workspace with a read-only operator skill, MCP config/server, and a
  personal marketplace entry. P6 readiness checks the plugin manifest, MCP
  config/server, operator skill, and marketplace source/policy before reporting
  readiness.
- The local plugin was cachebusted and installed from the personal marketplace
  through `codex plugin add ctoai-engine-brain@personal`; `codex plugin list`
  reports it as `installed, enabled`. P6 readiness now checks the installed
  Codex cache manifest version too.
- The local plugin now includes read-only smoke script
  `scripts/ctoai_engine_brain_status.py`, which summarizes manifest, P6
  readiness, pack, doctor, audit, and validation status without reading secrets,
  logs, databases, or live client state.
- The local plugin now includes read-only Control Center cockpit script
  `scripts/ctoai_control_center_cockpit.py`, exposed through MCP as
  `ctoai_control_center_cockpit`. It summarizes `runtime/evidence/latest.json`,
  tracked release-evidence markdown drilldown,
  `AI/generated/P7_OPERATOR_BRIEF.json`, P7 cockpit smoke evidence, and bounded
  Control Center action-audit drilldown status without running refresh, deploy,
  or live-client actions.
- The local plugin now includes read-only MCP server
  `scripts/ctoai_engine_brain_mcp.py`. It exposes four read-only tools
  (`ctoai_engine_brain_status`, `ctoai_engine_brain_self_check`,
  `ctoai_engine_brain_brief`, `ctoai_control_center_cockpit`) plus five
  dry-run-first safe-write refresh tools for repo hygiene, API cost, evidence
  pack, Engine Brain context, and P7 cockpit smoke workflows. Deploy/live actions remain blocked.
- The local plugin now includes read-only operator brief script
  `scripts/ctoai_engine_brain_brief.py`. It reports
  `decision=ready_for_p7_operator_workflow`, `status=ready`, and
  `hard_blockers=[]` from generated Engine Brain and validation evidence.
- `brain refresh` now generates `AI/generated/P7_OPERATOR_BRIEF.md` and
  `AI/generated/P7_OPERATOR_BRIEF.json`, giving Control Center and release
  evidence a read-only P7 operator decision artifact that does not require the
  plugin MCP server to be loaded.
- `brain refresh` now also generates `AI/generated/P7_OPERATOR_WORKFLOW.md` and
  `AI/generated/P7_OPERATOR_WORKFLOW.json` as the P7 risk gate. It reports
  the allowed read-only cockpit/status tools, the five audited safe-write
  refresh tools, and blocked `guarded_write`, `dangerous`, and
  `forbidden_ui` action classes.
- `brain refresh` now generates `AI/generated/P7_ACTION_READINESS.md` and
  `AI/generated/P7_ACTION_READINESS.json` as the action-expansion gate. It
  reports five Control Center `safe_write` candidates, five audited
  candidates, and now allows five bounded MCP write tools:
  `ctoai_repo_hygiene_refresh`, `ctoai_api_cost_refresh`,
  `ctoai_evidence_pack_refresh`, `ctoai_engine_brain_refresh`, and
  `ctoai_p7_cockpit_smoke_refresh`.
- `brain refresh` now generates `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md`
  and `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.json` as the first
  `safe_write` MCP contract. It keeps `evidence-pack-refresh` /
  `ctoai_evidence_pack_refresh` as the primary design contract, allows
  `repo-hygiene-refresh` / `ctoai_repo_hygiene_refresh` and
  `api-cost-refresh` / `ctoai_api_cost_refresh` plus
  `engine-brain-refresh` / `ctoai_engine_brain_refresh` and
  `p7-cockpit-smoke-refresh` / `ctoai_p7_cockpit_smoke_refresh` as additional bounded
  evidence/context refreshes, and keeps every deploy/live action blocked.
- The local `ctoai-engine-brain` plugin now exposes
  `ctoai_repo_hygiene_refresh`, `ctoai_api_cost_refresh`,
  `ctoai_evidence_pack_refresh`, `ctoai_engine_brain_refresh`, and
  `ctoai_p7_cockpit_smoke_refresh` as bounded
  safe-write MCP tools. All default
  to dry-run, require a read-only `ctoai_control_center_cockpit` preflight with
  status `ready`, write Control Center-compatible
  `runtime/control-center/action-audit.jsonl` records, and require explicit
  confirmation before non-dry-run execution.
- Control Center Evidence now surfaces the generated P7 action-readiness fields
  from `AI/generated/P7_OPERATOR_BRIEF.json` in the Engine Brain cockpit card:
  readiness status, audited candidate ratio, MCP write-tool count, action
  readiness decision, and next safe command. The Overview/Local Status Engine
  Brain detail panel mirrors the same read-only action-gate state.
- Control Center Evidence and Ops drilldowns now also surface the generated P7
  safe-write design from `AI/generated/P7_OPERATOR_BRIEF.json`: design status,
  selected action, proposed MCP tool, MCP enabled flag, and next safe command.
- Control Center now correlates all enabled P7 safe-write actions with the
  bounded `runtime/control-center/action-audit.jsonl` tail sample, exposing
  latest matching audit ids, risk classes, dry-run/confirmed modes,
  authorization results, and sanitized summaries in the Engine Brain cockpit
  card.
- Control Center Evidence and Ops now derive a read-only P7 cockpit summary
  from `AI/generated/P7_OPERATOR_BRIEF.json`, including enabled safe-write MCP
  tool count, ready audit count, and the per-tool audit status list. Current
  cockpit state is five enabled tools and five ready audit traces.
- P6 readiness now checks the P7 Control Center contract directly. It blocks
  plugin-design readiness if Control Center config, evidence payloads, ops
  payloads, Evidence UI, or detail UI stop consuming
  `AI/generated/P7_OPERATOR_BRIEF.json`, including the read-only P7 cockpit
  summary and enabled-tool audit status list.
- `scripts/ops/control_center_p7_cockpit_smoke.py` is now the repeatable
  read-only P7 cockpit smoke gate. It validates generated P7 workflow files,
  release evidence, and `runtime/control-center/action-audit.jsonl` together,
  and P6 readiness tracks both the script and its regression tests.
- Control Center Evidence and Ops now surface
  `runtime/control-center/p7-cockpit-smoke.json` as read-only P7 smoke status,
  including check counts, safe-write audit counts, artifact health, and source
  links.
- The local `ctoai-engine-brain` plugin cockpit, self-check, and safe-write
  preflight now also surface `runtime/control-center/p7-cockpit-smoke.json`.
  Installed cache checks report `p7_cockpit_smoke status=ready`, `14/14`
  checks, `5/5` safe-write audits, and roadmap generation readiness `ready`.
- `scripts/ops/control_center_p7_safe_write_dry_run_smoke.py` now exercises all
  five bounded P7 safe-write MCP tools with `dry_run=true` against the local
  plugin stdio server and verifies matching Control Center action-audit records.
  P6 readiness tracks both the smoke script and its regression tests before any
  broader plugin action expansion.
- P7 safe-write dry-run smoke now separates normal cockpit preflight from the
  explicit self-stale bootstrap allowance: operator-ready evidence requires
  `dry_run_ready_count=5`, `preflight_ready_count=5`, and
  `bootstrap_allowed_count=0`; bootstrap remains limited to stale P7
  audit/smoke recovery and is not the final acceptance state.
- Control Center artifact health now uses the same P7 dry-run smoke acceptance
  rule, so a bootstrap-only or partial-preflight report blocks operator handoff
  instead of appearing as a passed artifact.
- P7 action readiness now advances the generated `next_safe_command` after all
  five enabled safe-write tools have dry-run/preflight evidence. The only
  confirmed recommendation in this lane is the selected evidence refresh:
  `ctoai_evidence_pack_refresh` with `dry_run=false` and
  `confirm='refresh evidence pack'`; deploy/live/client actions remain blocked.
- The selected confirmed evidence refresh was executed through the
  `ctoai-engine-brain` plugin MCP path with exact confirmation. P7 action
  readiness now recognizes the confirmed `evidence-pack-refresh` audit evidence
  and advances to `review_confirmed_safe_write_evidence`, so Control Center and
  the plugin cockpit recommend reviewing `runtime/control-center/action-audit.jsonl`
  and `runtime/evidence/latest.json` before any next plugin action is designed.
- `scripts/ops/control_center_p7_evidence_review.py` now performs that
  read-only review as a concrete gate. It writes
  `runtime/control-center/p7-evidence-review.json` and `.md`, validates the
  confirmed `dry_run=false` evidence-pack audit, release evidence, P7 cockpit
  smoke, P7 dry-run smoke, and P6 handoff smoke, and lets
  `P7_ACTION_READINESS` advance to `design_next_p7_plugin_action` only when
  the review is ready.
- Control Center Evidence and Ops now surface
  `runtime/control-center/p7-safe-write-dry-run-smoke.json` as read-only P7
  dry-run smoke status, including check counts, dry-run tool readiness,
  per-tool audit/preflight/bootstrap status, artifact health, operator-next
  gating, and source links.
- The local `ctoai-engine-brain` plugin cockpit, operator brief, self-check,
  and safe-write MCP preflight now also surface
  `runtime/control-center/p7-safe-write-dry-run-smoke.json`. The plugin was
  reinstalled as `0.1.0+codex.20260708000418`; installed cache checks report
  `p7_safe_write_dry_run_smoke status=ready`, `12/12` checks, `5/5`
  dry-run safe-write tools, `5/5` preflight-ready tools, and `0` bootstrap-only
  tools.
- Control Center Evidence now surfaces a read-only P6 plugin handoff card from
  `AI/generated/P6_CODEX_INTEGRATION_READINESS.json`, including marketplace
  status, installed cache version, P6 check counts, MCP contract counts, and the
  explicit fresh-thread verification requirement for `ctoai_engine_brain_brief`
  and `ctoai_control_center_cockpit`.
- `scripts/ops/control_center_p6_plugin_handoff_smoke.py` now writes
  `runtime/control-center/p6-plugin-handoff-smoke.json` and `.md` as the final
  read-only P6 plugin handoff smoke. It validates P6 readiness, marketplace and
  installed-cache evidence, plugin manifest version parity, P7 operator
  workflow policy, P7 operator brief readiness, P7 cockpit smoke, and P7
  safe-write dry-run smoke before fresh-thread plugin verification.
- Control Center Evidence and Ops now surface that P6 handoff smoke inside the
  existing P6 plugin card/detail: smoke status, check counts, current-thread
  discovery state, fresh-thread verification status, recommended tool order,
  and source link.
- The local `ctoai-engine-brain` plugin was reinstalled as
  `0.1.0+codex.20260708000418`. Its status, operator brief, Control Center
  cockpit, self-check, and MCP safe-write preflight now also surface
  `runtime/control-center/p6-plugin-handoff-smoke.json` as a read-only P6
  handoff gate before broader P6/P7 action expansion.
- P6 handoff now guards the plugin MCP startup path itself:
  `.mcp.json` must point at the absolute runnable
  `C:/Users/zycie/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py`
  script so fresh Codex sessions do not try to start the server from the CTOAi
  repo working directory.
- Fresh `codex exec` visibility smoke attempted the read-only
  `ctoai_engine_brain_brief` MCP tool against server `ctoai-engine-brain`,
  proving new-session discovery. Noninteractive approval cancelled the tool
  call, so direct MCP protocol smoke was also run; it listed `9` tools and
  returned `ready` for brief, cockpit, and self-check with P6 smoke `17/17`.
- The plugin `ctoai_control_center_cockpit` payload now mirrors the practical
  Control Center drilldown: release evidence status, sprint/file coverage,
  latest markdown titles, bounded action-audit tail sampling, risk/action
  counts, invalid-line counts, source/sample byte counts, and sanitized recent
  action records. It also returns a read-only `operator_next` recommendation
  that mirrors the Control Center operator-safe next step and suppresses
  guarded live-promotion commands. P6 readiness blocks if the plugin cockpit
  loses those drilldown or operator-next markers.
- P6 readiness now also tracks the plugin P7 cockpit smoke contract regression
  in `tests/test_engine_brain_index.py`, including MCP tool schema, forbidden
  tool-name fragments, cockpit smoke payload fields, and safe-write preflight
  smoke status.
- Control Center Evidence and Ops now expose one read-only `operatorNext`
  surface. It selects the next operator-safe step from current Engine Brain,
  P7 smoke, action-audit, and evidence gates, prefers P7 dry-run safe-write
  refreshes when P6/P7 are ready, and suppresses guarded live-promotion
  commands from the top-level recommendation.
- Control Center Evidence now also exposes a dedicated read-only `P7 operator
  brief` card backed by `AI/generated/P7_OPERATOR_BRIEF.json`. The card
  surfaces the generated cockpit handoff status, P7 smoke counts, P7 dry-run
  smoke status, release evidence coverage, action-audit record counts, and
  recommended read-only plugin tool order without exposing live-promotion
  commands.
- The local plugin cockpit and operator brief now include a read-only
  plugin-style operator surface for roadmap generation status. It checks
  `AI/FEATURE_ROADMAP.md`, this status file,
  `docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md`, and
  `AI/generated/DOC_SYNC.json` before treating further plugin-action expansion
  as roadmap-aligned.
- Control Center evidence now includes a read-only Engine Brain status surface
  backed by `AI/generated/manifest.json`, `ENGINE_BRAIN_PACK.json`,
  `DOC_SYNC.json`, and `SECRET_GUARDRAIL.json`.
- Control Center evidence now includes read-only stale-artifact detection for
  Helper manifest age, Helper ZIP hash mismatch, missing smoke evidence, and
  missing Control Center action audit records. Helper package hash checks now
  resolve `release_readiness.json` ZIP paths only inside the configured Helper
  dev lane, so an unsafe runtime JSON path cannot force Control Center to hash
  an arbitrary local file.
- Control Center evidence now surfaces read-only Helper live-promotion evidence
  from `live_promotion.json`, including promoted status, live client path,
  backup path, and a freshness check that stays separate from live deploy
  actions.
- Control Center evidence now includes read-only drilldowns for tracked
  release-evidence markdown and sanitized action-audit JSONL metadata. The
  release-evidence drilldown extracts markdown titles through a small bounded
  prefix reader and falls back to the file name for oversized or unsafe files.
  The action-audit drilldown reports action, target, risk, actor role,
  authorization, dry-run and result summaries without exposing raw
  `output_preview` command text. Oversized action-audit JSONL files are read
  through a bounded tail sample instead of a full-file read, and symlinked audit
  paths are rejected before `open`; the payload reports `truncated`, source
  bytes, sampled bytes, and a `warn` state before release sign-off.
- Control Center configured JSON evidence reads now use a bounded file-handle
  reader and reject symlinked or oversized configured files before parsing.
  Repo hygiene, API cost, Helper, Engine Brain, and runtime evidence JSON fail
  closed to missing/default status instead of following unsafe paths.
- Control Center ops now carries the same release-evidence and action-audit
  drilldowns into Overview and Local Status detail panels. The legacy
  `recentActions` fallback now uses the shared bounded action-audit reader and
  is redacted before the `/api/control-center/ops` payload is returned.
- Control Center evidence read endpoints now require operator-or-owner access
  before collecting runtime evidence or reading local markdown files. This
  protects `/api/control-center/evidence`, `/api/control-center/ops`,
  `/api/control-center/evidence/report`, and
  `/api/control-center/evidence/api-cost-report` from anonymous/member reads.
- Backend `/api/release-evidence` now follows the same browser-safe evidence
  discipline for its configured JSON file: bounded read, display-safe
  `evidence_path`, recursive token/password/API-key redaction, local absolute
  path collapse, symlink rejection before `stat/open`, and stable error
  messages without raw exception text.
- FastAPI HTTP audit JSONL persistence now redacts token/password/API-key/Bearer
  forms and local absolute paths from `actor`, `ip`, `ua`, request path, and
  nested `meta` before writing `CTOA_AUDIT_LOG_FILE`.
- FastAPI rate-limit identity now ignores `X-Forwarded-For` unless
  `CTOA_TRUST_PROXY_HEADERS=true`. When proxy headers are explicitly trusted,
  only the first syntactically valid forwarded IP is used for audit IPs and
  rate-limit buckets, preventing spoofed header rotation from bypassing read
  limits in default local/API deployments.
- Control Center evidence and ops payloads now display repo-local paths as
  repo-relative strings and external absolute paths as `[external]/name`,
  keeping user profile, temp, live-client, and custom runtime parent
  directories out of browser-visible JSON.
- Control Center markdown report endpoints now apply the same browser-visible
  redaction and display-path rules before returning release evidence or API
  cost markdown through `/api/control-center/evidence/report` and
  `/api/control-center/evidence/api-cost-report`. The shared sanitizer now
  handles Windows and POSIX absolute local paths while leaving UI/API routes
  such as `/api/control-center/actions` intact.
- Control Center markdown report reads are now physically bounded. Release-
  evidence and API-cost markdown endpoints read at most `max + 1` bytes through
  a file handle, reject symlinked configured report files before `open`, close
  the handle in `finally`, and return `413` for oversized configured report
  files, so an env/path mistake cannot force the route to load a linked or very
  large local artifact into memory.
- Control Center action execution now applies the same browser-visible
  sanitizer to action results before returning stdout/stderr or local failure
  messages to the UI. Returned action output and persisted audit previews both
  redact token/password forms and collapse Windows or POSIX absolute local
  paths.
- `/api/control-center/actions` now also sanitizes generic and authorization
  error JSON before returning it to the browser, so rejected/unknown action
  errors cannot echo token-like input or local host paths from exception
  messages.
- `/api/control-center` backend probe summaries and
  `/api/control-center/legacy` backend fetch details now use the same
  browser-visible sanitizer before JSON responses, keeping token/password forms
  and Windows/POSIX local paths out of fallback Control Center status payloads.
- Control Center action execution now redacts common secret forms from audit
  `reason` and `output_preview` fields before appending
  `runtime/control-center/action-audit.jsonl`, so the persisted runtime audit
  and the read-side drilldown both avoid copying tokens or passwords.
- Control Center evidence, ops detail panels, and action audit persistence now
  share the same redaction helper. This keeps legacy or hand-written
  `runtime/control-center/action-audit.jsonl` records with `token=...`,
  `password=...`, quoted JSON-like token/password/API-key fields, Bearer,
  GitHub, OpenAI, GitLab, or `PGPASSWORD` forms from leaking through read-only
  evidence drilldowns or `/api/control-center/ops`.
- Control Center chat transcripts, markdown exports, JSON chat logs, and
  `localStorage` persistence now use the same redaction helper before storing
  or exporting messages. Bearer, provider-token, token/password/API-key,
  quoted JSON-like secret fields, and quality/publication-note secrets are
  replaced with `[redacted]` while the current in-memory chat view remains
  unchanged.
- Control Center local Python-backed actions now resolve only
  `CTOA_PYTHON_BIN` as an absolute existing executable or the repo-local
  `.venv` Python. Missing trusted Python is recorded as an audited action
  failure instead of falling back to PATH-only `python`/`python3`.
- Control Center action execution now derives the workspace root safely from
  either repo-root or `web/` working directories. Explicit
  `CTOA_WORKSPACE_ROOT` overrides must be absolute existing directories, and
  allowlisted action scripts must resolve inside that workspace and exist before
  `execFile` runs.
- Control Center action script resolution now uses `realpath` containment.
  Repo-relative allowlisted scripts must still resolve inside the real
  workspace root after following parent symlinks or junctions, and direct
  script symlinks are rejected before `execFile`.
- Control Center action catalog reads are now role-scoped. Anonymous or member
  viewers no longer receive local action `commandSummary` metadata, and the
  client action panel defensively renders no actions until a viewer role is
  available.
- Control Center action POST requests now reject cross-site action triggers
  before auth lookup or execution by validating explicit `Origin`, cross-site
  `Sec-Fetch-Site`, and fallback `Referer` signals against the request origin.
- `web/src/lib/requestOriginGuard.ts` centralizes that same-origin check, and
  `/api/auth` POST now uses it before rate-limit, body parsing, or backend
  forwarding, so cookie-authenticated invite/setRole/logout-style wrapper calls
  cannot be explicitly cross-site triggered.
- `/api/chat` and local `/api/auth/seed-login` now use the same guard before
  rate-limit, body parsing, cookie/token forwarding, or backend fetch, preventing
  explicit cross-site chat prompts and local seed-login attempts.
- `/api/auth` proxy responses now strip token-like backend fields recursively
  and sanitize string values before browser JSON is returned. Login, register,
  accept-invite, invite, role-change, and GET proxy responses keep httpOnly
  cookie auth while avoiding token/password or local-path echoes in response
  bodies.
- `authProxySanitizer.ts` now centralizes that auth proxy contract, and local
  `/api/auth/seed-login` uses it too. Seed-login still extracts the backend
  token for the httpOnly cookie, but nested token-like fields and backend
  detail strings are removed or sanitized before browser JSON is returned.
- Web API base URL config now fails closed before proxy or browser API calls:
  `VPS_API_URL` and `NEXT_PUBLIC_API_URL` must be absolute HTTP(S) URLs, must
  not include credentials, path components, path separators, query strings, or
  fragments, and must use HTTPS for non-local hosts.
- Web proxy route rate-limit identity now mirrors the FastAPI proxy-header
  contract. `/api/auth` and `/api/chat` ignore `X-Forwarded-For` and
  `X-Real-IP` unless `CTOA_TRUST_PROXY_HEADERS=true`; trusted mode accepts
  only syntactically valid IP values, otherwise the limiter key falls back to
  `unknown`.
- Desktop Console API and Control Center URLs now use the same fail-closed URL
  contract before settings, login, or browser launch use them: local HTTP is
  allowed, remote hosts require HTTPS, and credentials/query/fragment
  components are rejected without echoing rejected values.
- Desktop updater downloads now keep initial release asset URLs pinned to
  trusted GitHub HTTPS hosts and safe `.exe` asset names, while allowing signed
  query strings only on the final trusted GitHub asset CDN redirect before the
  update file is written. Downloads also enforce a maximum size and use a
  `.download` temp file that is atomically moved into place only after the full
  stream succeeds; oversized or failed streams clean up the partial temp file.
- Phase-5 attention notification posting now validates Slack and Discord
  webhook URLs with `runner.http_safety.require_notify_webhook_url` before
  `urlopen`. The guard requires HTTPS, allowlisted Slack/Discord hosts, strict
  webhook path prefixes, and rejects credentials, query strings, fragments,
  backslashes, traversal, empty segments, and encoded path separators without
  echoing rejected URLs.
- `/api/chat` now builds a strict backend payload from normalized messages plus
  allowlisted `model`, `route_mode`, and bounded `temperature`. It drops
  arbitrary client JSON fields such as `debug_route`, `quality_retry`,
  `max_tokens`, token-like values, and other unrecognized keys before backend
  forwarding.
- Backend `/api/chat` and `/v1/chat/completions` now keep `debug_route`
  operator-only by requiring `owner` or `operator` before route diagnostics are
  generated, and they return only allowlisted route metadata without backend
  URLs, fallback backend URLs, or key-like values. Router stdout logging now
  uses the same sanitized route view instead of dumping internal backend URLs.
- The API dev JWT fallback uses an explicit non-secret placeholder name. The
  production guard still rejects unset/default `CTOA_JWT_SECRET`, while the API
  Bandit scan remains clean of hardcoded-secret placeholder findings.
- Control Center evidence now includes a read-only dashboard comparison between
  current runtime evidence (`runtime/evidence/latest.json` and `latest.md`) and
  the newest tracked release-evidence markdown.
- OTClient Helper redesign Phase 1/2 started from
  `docs/otclient/helper_redesign.md`: narrower module rail, wider active
  workspace, single operator header, quieter row/control styling, and a
  regression contract for the layout treatment.
- OTClient Helper redesign Phase 3 implemented repo-side: summary strips now
  cover Healing, Hunting Targeting, Hunting Magic, Tools Helper, Profile, and
  UI, with live title/autosave refresh wiring and a regression contract for
  summary wiring.
- OTClient Helper P5 live promotion completed for the historical `v1.1b` staged
  package after strict release-gate approval. Promotion created a live CTOA
  backup, copied staged files, and recorded durable `live_promotion.json`
  evidence without stopping, restarting, or launching the live Solteria client
  by default. A post-promotion launch must be explicit through
  `-LaunchAfterPromote`, and the wrapper only starts the live executable when
  it is not already running.
- Production API startup now rejects wildcard CORS, default JWT secrets, and
  automatic default auth-account seeding. Production mobile console startup now
  defaults self-registration off and requires `CTOA_SELF_REGISTER_CODE` if
  self-registration is explicitly enabled.
- `api/startup_guard.py` now performs lightweight production fail-fast checks
  for wildcard CORS, default JWT secrets, and production API self-registration
  without an invite code before importing heavier API dependencies.
- Default API auth-account seeding is now opt-in even outside production via
  `CTOA_ALLOW_SEED_ACCOUNTS=true`. Control Center local seed-login no longer
  embeds seed passwords and only runs on localhost when
  `CTOA_ENABLE_LOCAL_SEED_LOGIN=true` plus `CTOA_SEED_*_PASSWORD` env vars are
  set.
- Web `ctoa_token` cookie writes now go through `authCookies.ts`, keeping
  `httpOnly`, `sameSite=lax`, `/` path scope, and adding `Secure`
  automatically under `NODE_ENV=production`. Server routes read the token name
  through the same shared constant.
- API public member self-registration now defaults off in production, requires
  `CTOA_API_SELF_REGISTER_ENABLED=true` plus `CTOA_API_SELF_REGISTER_CODE`, and
  `/api/auth/register` no longer creates `owner` or `operator` accounts without
  an authenticated owner token when the auth store is empty.
- API auth-store and runner state artifact writes now avoid predictable sibling
  `*.tmp` paths. `api/main.py` and `runner/runner.py` use hidden PID/UUID temp
  files in the target directory, `fsync` before `replace`, and cleanup in
  `finally` for auth JSON, scheduler YAML state, and execution-summary JSON.
  API auth-store reads now use a byte cap, reject symlinked or invalid existing
  stores, and fail closed instead of seeding over a bad store.
- Health Metrics latest snapshots now follow the same state-artifact write
  discipline. `runner/health_metrics.py` writes `health-latest.json` through a
  hidden PID/UUID temp file with `fsync`, atomic `replace`, and cleanup, so a
  symlinked latest snapshot is replaced instead of writing through it.
- Desktop Console settings now follow the same state-artifact write discipline.
  `desktop_console/app.py` saves `desktop-settings.json` through a hidden
  PID/UUID temp file with `fsync`, atomic `replace`, and cleanup, preventing
  partial writes and replacing a symlinked settings path instead of writing
  through it. Settings reads now use a byte cap, reject symlinked settings, and
  fail closed to defaults for oversized, invalid, or non-object JSON.
- Mobile Console local operator state now follows the same state-artifact
  contract. Admin settings and idea parking JSON are read through byte caps and
  invalid/oversized state fails closed to defaults; writes use hidden PID/UUID
  temp files with `fsync`, atomic `replace`, and cleanup so symlinked state
  paths are replaced instead of written through.
- Product bootstrap local state now follows the same state-artifact contract.
  `scripts/ops/ctoa_product_bootstrap.py` writes
  `.ctoa-local/user-config.json` and `.ctoa-local/bootstrap-state.json` through
  hidden PID/UUID temp files with `fsync`, atomic `replace`, and cleanup, so
  update-gate state cannot be left partially written and symlinked JSON state
  is replaced instead of written through.
- Product update gate local state reads now fail closed. `ctoa_update_gate.py`
  reads `.ctoa-local/bootstrap-state.json` through a byte cap, rejects symlinked
  state before reading through it, and returns stable `invalid_bootstrap_state`
  reason codes for malformed JSON, oversized state, unreadable state, and
  invalid version/schema values instead of raising parser tracebacks or echoing
  state contents.
- Helper/release-gate and sprint state writers now follow the same
  non-predictable temp-file contract. `otclient_helper_profile_audit.py`,
  `solteria_helper_goal_audit.py`, `solteria_helper_release_gate.py`, and
  `sprint_state_sync.py` use PID/UUID temp names with cleanup; the Solteria
  Helper PowerShell test-env `Write-JsonAtomic` uses PID/GUID temp names with
  cleanup after `Move-Item`.
- Mobile console DB fallback execution no longer passes `DB_PASSWORD` in local
  `psql` or `docker exec` argv; fallbacks now pass it through process
  environment handling.
- Runner agent DB pooling no longer assembles `DB_PASSWORD` into a text DSN;
  `runner/agents/db.py` passes connection fields to psycopg2 as keyword
  arguments instead. Agent-run write failure logs now sanitize
  `password=...`, `PGPASSWORD=...`, and PostgreSQL URL password forms before
  emitting exception text.
- Mobile console command audit now redacts common secret forms from `/api/command`
  command strings before writing `logs/mobile-console-audit.log`, covering
  Bearer tokens, common provider tokens, token/password assignments, and common
  long token/password CLI options.
- Mobile console command execution now redacts returned stdout/stderr for
  operator-facing command/status/log paths before sending them back to the UI.
  This covers safe-mode `/api/command` presets, full-access command output,
  runner report status output, and local log tails without changing DB fallback
  stdout parsing. The `/api/logs` fallback path now reads only a bounded tail
  from the end of local log files and rejects symlinked logs before reading.
- Mobile console audit records now include actor accountability fields
  (`actor`, `actor_role`, `auth_mode`, `auth_transport`) while avoiding session
  token or CSRF token persistence.
- Mobile console cookie-authenticated mutations now have direct CSRF regression
  coverage: cookie-only unsafe methods require `X-CSRF-Token`, while
  bearer/header-authenticated operator calls remain usable without CSRF.
- Mobile console generated-artifact APIs now return public artifact paths
  instead of local absolute paths. `/api/agents/generated/latest` and SLO
  manifest observations redact `GENERATED_DIR`, temp-directory, and unknown
  runtime path prefixes before JSON is returned to dashboard clients. Generated
  `latest.json` and run `manifest.json` reads now use a byte-capped,
  symlink-rejecting loader and fail closed to scan/default responses for
  oversized or invalid manifests.
- Mobile Console local metadata JSON reads now go through a byte-capped,
  symlink-rejecting loader. Command dictionary, product manifest, and product
  user config reads fail closed to defaults for oversized, invalid, symlinked,
  or non-object JSON before operator API responses are built.
- Mobile console file metadata responses now reuse the same display-safe path
  helper for admin settings, idea parking, auto-trainer report status, disk
  probes, one-click generated directories, and client-sync result paths, so
  operator JSON avoids exposing absolute local host directories.
- Mobile console auto-trainer report reads are now physically bounded.
  `/api/agents/auto-trainer/latest` reads `latest.md` and `latest.json` through
  byte caps, reports markdown truncation, rejects oversized JSON reports with a
  stable status, and no longer returns raw JSON parser exception text.
- Mobile console safe-mode presets now execute through backend-owned
  `argv/cwd/env` specs instead of raw pseudo-shell snippets. Legacy preset
  strings remain visible through `/api/presets`, but allowlisted execution no
  longer depends on interpreting `cd ...; ENV=... command` text.
- Mobile console `/api/command` no longer executes arbitrary command text when
  legacy `CTOA_MOBILE_FULL_ACCESS=true` is set. The endpoint always routes
  through backend-owned presets and rejects non-preset command text.
- Mobile console health/auto-check status now reports `command_mode=presets`
  and never reports `full_access=true`; the legacy mobile UI no longer renders
  a full-command box, and the desktop admin console uses a readonly
  preset-selected command field.
- Legacy mobile and desktop Intel guarded writes now require owner auth,
  `confirm=true`, and a non-empty audit reason before DB writes, orchestrator
  triggers, or client sync can run. Denied attempts are audited, and audit
  reasons reuse the secret redactor.
- Mobile console Intel URL validation now blocks localhost, private IPs,
  link-local/metadata IPs, `.local` names, and single-label internal hosts in
  production unless `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true` is explicitly set.
- Mobile console server/intel target URLs now also reject embedded credentials,
  query strings, fragments, backslashes, and decoded `.`/`..` path traversal
  before URLs are written to DB rows, audits, or dashboard responses.
- Mobile console local runtime API proxy bases now fail closed. `CTOA_API_BASE_URL`
  and `CTOA_INTEL_API_BASE_URL` must target `localhost`, `127.0.0.1`, `[::1]`,
  or `host.docker.internal`, and must not include credentials, query strings,
  fragments, backslashes, or decoded traversal before `/api/intel/*` or
  `/api/dashboard/release-evidence` can call `urlopen`. Invalid values return a
  generic `[invalid-local-runtime-api]` marker instead of echoing the raw env
  URL. Runtime proxy `URLError` and generic exception text is now routed through
  the shared redactor before browser JSON receives `error` fields.
- Mobile console local runtime proxy paths now fail closed too. `_intel_api_proxy`
  and `_ctoa_api_proxy` accept only relative `/api/...` paths without query
  strings, fragments, empty segments, traversal, backslashes, or encoded
  separators before joining a validated local base URL and calling `urlopen`.
  Invalid paths return `[invalid-local-runtime-path]` without echoing
  secret-bearing path text.
- Mobile console Intel client-sync writes are now confined to
  `CTOA_CLIENT_SCRIPTS_DIR`; target, autoloader, and init-file paths are
  validated before files are copied. Init-file updates now reject symlinked or
  oversized init files before copying generated Lua, and autoloader/init writes
  use hidden PID/UUID temp files with `fsync` plus atomic replace. Generated Lua
  copies now reject symlinked or oversized sources, reject existing destination
  symlinks, and write through the same atomic temp-file path.
- Public docs-site admin reset now clears session-scoped auth state as well as
  persistent local state: backend API token/user/role, local fallback admin
  session, and session-scoped local fallback admin passwords are removed during
  owner reset.
- Mobile console DB-backed account changes now revoke active in-memory sessions
  for the affected user after password changes, role changes, or deactivation,
  preventing stale owner/operator tokens from retaining old privileges.
- Mobile console self-registration now creates only `member` accounts, and
  `require_operator` enforces that operator endpoints require `operator` or
  `owner` instead of accepting any authenticated session. Members can
  authenticate for `/api/auth/me`, but cannot access command/status operator
  surfaces until an owner promotes them.
- Bot DQL reward shaping now penalizes `loot` in healthy no-target states, and
  the 1000-tick stress test isolates local runtime Q-table state so test

[truncated]
```


## `AI/FEATURE_ROADMAP.md`

```markdown
# Feature Roadmap

## Current State

- Engine Brain Plan 3 is operational and maintained as the secret-safe context
  foundation; roadmap work now consumes its generated evidence.
- Helper `v2.1.1a` is live-promoted, while all new runtime bridge work remains
  sandbox-first and does not imply another live promotion.
- P6 is ready for plugin design and the five bounded P7 safe-write refresh tools
  are enabled with audit coverage.

## Now

1. **Helper Runtime Bridge v1** — owner: Helper Runtime; status: `sandbox`;
   risk: `runtime_recovery`. Deliver one `plan_heal` execution boundary with
   dry-run default, session arming, cooldown, retry budget, kill switch, and
   decision/guard/action/result trace. Definition of done: repo tests, packaged
   boot graph, sandbox attach, and in-world evidence all pass. Contract:
   `docs/otclient/HELPER_RUNTIME_BRIDGE_V1.md`.
2. **Capability freshness and drift** — owner: Control Center; status: `gated`;
   expose stale Helper/evidence timestamps without adding a write action.
3. **Next P7 action design** — owner: Engine Brain; status: `planned`; select
   exactly one action only after risk model, audit logging, Control Center gate,
   dry-run behavior, and targeted MCP tests exist. Deploy/live actions remain
   excluded.

## Next

- Add operator session arming and a visible kill switch after the bridge sandbox
  contract passes.
- Add decision-trace replay and bounded runtime evidence export.
- Add sandbox-to-live promotion visibility without implicit promotion.
- Index a supplied TFS fork and protocol sources; do not infer missing server
  behavior.
- Generate roadmap status from manifests and evidence to reduce manual drift.

## Guardrails And Maintenance

The priority sections below retain the complete durable security, evidence, and
runtime maintenance contract. They are invariants, not simultaneous active
feature work.

## Default Horizon: 90 Days, Helper First

- Stabilize and productize the OTClient/Solteria Helper before broader CTOAi
  expansion.
- Keep `scripts/lua/otclient/` as the canonical Helper source tree; generated
  ZIPs stay under `runtime\solteria_helper_dev\` or release staging.
- Preserve safe boot defaults: runtime disarmed, combat/offensive/movement
  actions off unless explicitly enabled.
- Treat the live Solteria client as protected. Development uses
  `runtime\solteria_helper_dev` and the sandbox client first.
- Keep helper sandbox path validation strict: `SandboxClient` must stay under
  `%LOCALAPPDATA%`, use separator-aware containment, and must not equal or sit
  inside `SourceClient`.
- Required gates before live promotion: `PrepareDev`, `ValidateDev`,
  `SmokePreflight`, in-world `SmokeAttachAll`, then explicit live approval via
  `PromoteLiveCtoa -ApproveLiveDeploy`.
- A post-promotion live client launch is not implicit. Operators must add
  `-LaunchAfterPromote`; the wrapper may launch a missing live client but must
  never stop or restart an existing live client.
- Current Helper `v2.1.1a` is live-promoted with 49-file SHA-256 parity and
  fresh `Initialized successfully v2.1.1a` boot evidence. Its production gate
  passed after UI stabilization, shell-budget reduction, a 20-shot theme
  matrix, 32/32 module static gates, 16/16 in-world attach coverage, and
  singleton relog evidence; runtime remained disarmed.
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
  separate runtime-bridge review after the completed v2.1.1a stabilization.

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
- Use `brain pack all|helper|control-center|infra|security` for scoped context
  packs.
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
- Keep the release gate strict: in-world `SmokeAttachAll` evidence must be
  newer than the current dev manifest before it can satisfy visual acceptance.
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
  that bypass `PromoteLiveCtoa -ApproveLiveDeploy

[truncated]
```


## `AI/LUA_INDEX.md`

```markdown
# Lua Index

## Standalone Lua Modules

Source folder: `scripts/lua/`

- `auto_heal.lua`: `AutoHeal.shouldCast`, `AutoHeal.nextAction`.
- `event_logger.lua`: JSONL event shaping through `EventLogger`.
- `loot_filter.lua`: allow/deny loot decision helpers.
- `pathing_helper.lua`: route normalization, next waypoint, blocked retry.
- `supply_manager.lua`: supply threshold checks and refill action.
- `target_priority.lua`: target scoring and priority selection.
- `safety_interrupt.lua`: critical-state interrupt action.
- `telemetry_exporter.lua`: JSONL telemetry serialization.
- `ctoa_hotkey_status.lua`: periodic hotkey status file/log emission.
- `ctoa_path_probe.lua`: runtime path probe.
- `module_reporter.lua`: periodic module status log.
- `proximity_watch.lua`: player proximity alert.
- `status_beacon.lua`: HP/mana status beacon.
- `emergency_heal.lua`: simple emergency heal loop.

Standalone modules often assume a generic runtime API such as `Player`, `Game`,
`Creature`, and `register("onThink", ...)`. Keep these separate from OTClient
native modules unless an adapter layer is written.

## OTClient Native Lua Modules

Source tree: `scripts/lua/otclient/`

- `ctoa_otclient_loader.lua`
- `ctoa_native_helper.lua`
- `ctoa_native_combat.lua`
- `ctoa_native_heal.lua`
- `ctoa_native_loot.lua`
- `ctoa_ek_profile.lua`

Native modules use OTClient globals:

- `g_game`
- `g_map`
- `g_ui`
- `g_keyboard`
- `g_resources`
- `g_clock`
- `connect`
- `cycleEvent`
- `scheduleEvent`
- `addEvent`
- `removeEvent`

## Helper Config Areas

`HELPER_CONFIG` in `ctoa_native_helper.lua` owns:

- global enable state
- safe boot runtime disable flag
- helper hotkey
- auto hide
- window position
- theme preset
- compact mode
- healing settings
- combat/targeting settings
- tools settings
- cavebot waypoints and movement
- HUD preferences
- smoke tab/subtab state

## Profile Files

`ctoa_ek_profile.lua` is generated by `scripts/ops/ctoa_otprofile_builder.py`.
The helper loads profile candidates from user/module paths and merges them into
`HELPER_CONFIG`.

Profile saves are ordered by:

- `PROFILE_KEY_ORDER`
- `UI_PREFS_KEY_ORDER`
- `HEALING_KEY_ORDER`
- `TOOLS_KEY_ORDER`
- `HUD_KEY_ORDER`
- `ROTATION_KEY_ORDER`
- `HEAL_SPELL_KEY_ORDER`
- `WAYPOINT_KEY_ORDER`

Preserve this order when changing profile persistence.

## Hook Patterns

- Generic scripts: `register("onThink", onThink)`.
- OTClient events: `connect(LocalPlayer, {...})`,
  `connect(Creature, {...})`, `connect(Container, {...})`,
  `connect(Map, {...})`, `connect(g_game, {...})`.
- Periodic OTClient loops: `cycleEvent(onThink, interval_ms)`.

## Validation

Minimum checks:

- Syntax parse with `luac -p` when available.
- Fallback bracket/sanity checks when `luac` is not available.
- Manual OTClient load smoke for helper/UI/hotkey work.
- Fresh `ctoa_local.log` lines for loader/helper changes.
```


## `AI/OTCLIENT_INDEX.md`

```markdown
# OTClient Index

## Package Contents

`scripts/lua/otclient/` contains the canonical helper source files:

- `ctoa_otclient.otmod`
- `ctoa_otclient_loader.lua`
- `ctoa_native_helper.lua`
- `ctoa_native_combat.lua`
- `ctoa_native_heal.lua`
- `ctoa_native_loot.lua`
- `ctoa_ek_profile.lua`
- `README.md`

## Module Definition

`ctoa_otclient.otmod`:

- name: `ctoa_otclient`
- description: `CTOA OTClient helper and native automation modules`
- version: `1.1b`
- `autoLoad: true`
- `autoLoadPriority: 1000`
- script: `ctoa_otclient_loader`

## Loader

`ctoa_otclient_loader.lua`:

- Creates/reuses `_G.CTOA_OTCLIENT`.
- Version: `1.1b`.
- Main helper module: `ctoa_native_helper.lua`.
- Load delay: `1500 ms`.
- Resolves helper from resource/workdir candidate paths.
- Connects to `g_game.onGameStart` and `g_game.onGameEnd`.
- Schedules helper load through `scheduleEvent` or `addEvent` fallback.
- Logs through game console when available.
- Runtime modules are skipped by loader; helper UI is loaded first.

## Helper

`ctoa_native_helper.lua`:

- Owns `HELPER_CONFIG`, `Helper`, UI style/theme/layout tables, widgets, and
  runtime state.
- Loads `ctoa_ek_profile.lua` from candidate user/module paths.
- Applies safe boot by disabling runtime action modules unless profile opts out.
- Builds helper window, tabs, settings rows, tools panels, HUD, and profile UI.
- Binds helper hotkey, default `Ctrl+J`.
- Uses `cycleEvent(onThink, HELPER_CONFIG.tick_ms)`.
- Exposes:
  - `Helper.showTab(tab)`
  - `Helper.onThink(self)`
  - `Helper.reloadProfile()`
  - `Helper.runMovementApiProbe()`
  - `Helper.runMagicApiProbe()`
  - `Helper.runApiProbe()`
  - `Helper.setEnabled(enabled)`
- Current helper version: `v1.1b`.
- API v1.1b adds a central safe API registry probe for core, player/vitals,
  movement/pathing, combat, magic/runes, UI/resources, and container/loot APIs.
- Magic v1.1b keeps the safe API probe, versioned HUD/footer text, and a Magic
  tab `Rune box` actionbar selector.
- Ensures `_G.CTOA_Manager` exists and registers module `helper`.

## Combat

`ctoa_native_combat.lua`:

- Config: `DEFAULT_COMBAT_CONFIG`.
- Runtime state: `Combat`.
- Guards offline, disabled, PZ, no local player, invalid targets.
- Finds targets through `g_map.getSpectatorsInRange` or
  `g_map.getCreaturesInRange`.
- Scores by priority names, distance, and validity.
- Uses `g_game.attack(target)` and optional `g_game.follow(target)`.
- Clears with `cancelAttack`, `stopAttack`, `attack(nil)`, `follow(nil)` where
  available.
- Uses `cycleEvent(onThink, 100)`.
- Connects `Creature.onDeath`.

## Heal

`ctoa_native_heal.lua`:

- Config: `HEAL_SETTINGS`.
- Cooldown: `HEAL_COOLDOWN = 1000`.
- Uses `g_game.talk(spell)` for heal/mana spells.
- Connects `LocalPlayer.onHealthChanged` and `LocalPlayer.onManaChanged`.

## Loot

`ctoa_native_loot.lua`:

- Config: `LOOT_CONFIG`.
- Uses `VALUABLE_LOOT` item id map.
- Connects `Container.onOpen` and `Map.onItemAppear`.
- Scans container/item events and moves valuable items when supported.

## Profile

`ctoa_ek_profile.lua`:

- Generated by `scripts/ops/ctoa_otprofile_builder.py`.
- Default hotkey: `Ctrl+J`.
- Potion hotkey: `F1`.
- Mana potion hotkey: `F2`.
- Rune hotkey: `F5`.
- Contains healing, combat, tools, rune, and profile settings for EK use.

## Manual Smoke

1. Put package files under the OTClient module/user directory.
2. Ensure loader is called by OTClient module autoload or `init.lua`.
3. Start OTClient.
4. Confirm `[CTOA-OTC]` or helper log line appears.
5. Toggle helper with configured hotkey.
6. Confirm runtime remains disabled in safe boot unless explicitly enabled.
7. Check fresh `ctoa_local.log` lines.
```


## `docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md`

```markdown
# CTOAi Three Development Plans

Basis: full workspace audit with `42168` inventoried files and `1329` git-tracked files.

## Plan 1: Helper-First Productization

Goal: turn the OTClient/Solteria Helper into a safe, repeatable product lane before broad expansion.

### 0-30 Days

- Keep `scripts/lua/otclient/` canonical and keep live Solteria protected.
- Require `PrepareDev`, `ValidateDev`, `SmokePreflight`, in-world `SmokeAttachAll`, and explicit live approval.
- Expand `otclient_helper_profile_audit.py` from text checks toward schema-backed migration validation.
- Keep Control Center Helper status read-only and backed by runtime artifacts.

### 31-60 Days

- Split `ctoa_native_helper.lua` only along stable boundaries: config/schema, profile persistence, UI, runtime loops, diagnostics.
- Preserve `ctoa_native_helper.lua` as the public loader entrypoint.
- Add stable diagnostics export coverage for HP/MP, movement, combat, magic, container/loot, UI/resources.

### 61-90 Days

- Make `SmokeAttachAll` the final visual acceptance source with full in-world screenshots.
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
```


## `docs/otclient/solteria_helper_development_plan.md`

```markdown
# Solteria Helper Development Plan

## Objective

Build new Helper features in an isolated lane first, then promote them to the
live Solteria client only after static validation, sandbox smoke, and log
evidence pass.

## Non-Interference Rule

The active play client under:

```text
C:\Users\zycie\AppData\Local\Solteria\client
```

must not be restarted, stopped, or overwritten during normal development work.
Development work uses:

```text
runtime\solteria_helper_dev
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client
```

Sandbox operations must keep `SandboxClient` under `%LOCALAPPDATA%` with
separator-aware path containment, and `SandboxClient` must not equal or sit
inside `SourceClient`. This prevents manual smoke/status/stop commands from
aliasing the live Solteria client.

Use `PrepareDev` and `ValidateDev` first. Use live copy only when the user
explicitly asks to deploy to the active play client.

## Environment Commands

Prepare a package and manifest without launching a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PrepareDev
```

Run static validation without touching the live client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ValidateDev
```

Prepare the sandbox client without touching the live client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Setup
```

Verify sandbox files match the staged dev package without launching a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
```

Inspect sandbox smoke readiness without launching or stopping a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeStatus
```

Refresh and print the full development goal status without launching or stopping
a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action GoalStatus
```

Only the sandbox client should be launched for interactive smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch
```

## Promotion Gates

1. `PrepareDev` writes a fresh package under `runtime\solteria_helper_dev`.
2. `PrepareDev` writes `manifest.json`, `CHANGELOG.md`, `validation.json`, and
   a versioned ZIP without touching the live client.
3. `ValidateDev` passes helper/API/report tests, static UI preview, and API
   catalog refresh.
4. `SmokePreflight` verifies sandbox files match the staged dev package.
5. Sandbox launch loads the Helper and writes fresh `ctoa_local.log` evidence.
6. `SmokeAttachAll` passes after a sandbox test character is in-world.
7. Only then copy to the active client with
   `PromoteLiveCtoa -ApproveLiveDeploy`.

## Feature Roadmap

### P0: Development Lane

- Keep `PrepareDev` and `ValidateDev` green.
- Keep package manifest evidence current.
  Status: the release gate verifies every staged file listed in
  `manifest.json` still exists under `latest` and matches its SHA256.
- Keep `CHANGELOG.md` and `validation.json` attached to every dev package.
- Never use active play-client restart as the first validation step.

### P1: Runtime Observability

- Add an in-client diagnostics tab that renders the last API probe snapshot.
  Status: `Tools / Diag` added in source; validate through `ValidateDev`.
- Add bounded log export for HP/MP, movement, combat, magic, and container APIs.
  Status: bounded diagnostics buffer and `ctoa_diag_export.lua` export added in
  source; validate through `ValidateDev`.
- Add feature flags for experimental modules.
  Status: profile-backed flags added for diagnostics, cavebot, loot, and combat.

### P2: Healing And Mana

- Use real `LocalPlayer:getHealth/getMaxHealth/getMana/getMaxMana` reads first.
  Status: `readPlayerVitals()` added in source; percent APIs are fallback only.
- Keep spell rotation by HP thresholds.
- Keep potion/rune selection actionbar-compatible: choose item/actionbar slot in
  the same model as the client actionbar assignment flow.
  Status: HP/MP/rune box selectors remain actionbar-slot backed, and runtime
  item actions resolve `*_actionbar_slot` before legacy hotkey fields.

### P3: CaveBot

- Keep movement disabled separately from route editing.
- Route editor first: add/current/delete/reorder waypoints without movement.
  Status: add/delete/select/reorder controls added; editor functions only mutate
  route/profile state and do not call movement APIs.
- Movement execution only through `LocalPlayer:autoWalk(destination, retry)`.
- Add stuck detection, retry budget, and PZ/offline guards before looped movement.
  Status: movement runtime now checks offline/PZ/player-position guards, tracks
  same-position retries, passes the retry flag into `LocalPlayer:autoWalk`, and
  disables movement after the retry budget is reached while keeping the edited
  route intact.

### P4: Combat And Magic

- Keep monster-only targeting guards.
  Status: targeting clears non-monster/unsafe targets and retargets only
  monster candidates inside configured range.
- Add visible decision state for spell rotation, exeta, rune, and target lock.
  Status: magic footer and HUD render the next action with target, action-lock,
  exeta cooldown, and rune readiness/cooldown state.
- Keep all offensive actions rate-limited and PZ-aware.
  Status: offensive action execution rechecks PZ/runtime block, action lock, and
  recovery gap before casting exeta, rotation spells, or rune actions.

### P5: Packaging And Release

- Build a versioned zip from canonical source files.
  Status: `PrepareDev` stages canonical OTClient files and creates
  `ctoa_otclient_<version>.zip` with SHA256 manifest evidence. The release gate
  verifies the ZIP exists and its SHA256 matches `release_readiness.json`.
- Generate a changelog from manifest + validation evidence.
  Status: `ValidateDev` refreshes `CHANGELOG.md`, `validation.json`, and
  `release_readiness.json` after tests, UI preview, and API audit pass. It also
  writes `release_gate.json`, which stays `blocked` until `SmokePreflight`
  passes, in-world `SmokeAttachAll` evidence exists, and live
  approval/promotion evidence exists. The gate auto-discovers only
  `solteria-helper-smokeall-inworld-*.json` reports, ignores modal-limited
  coverage reports, and verifies that the report contains every expected helper
  view with an existing screenshot file.
- Promote to live only with explicit approval and fresh backup.
  Status: live promotion is a separate `PromoteLiveCtoa` action that refuses to
  run without `-ApproveLiveDeploy`, checks the existing strict `release_gate`
  for the current staged package without regenerating the manifest, then writes
  a fresh `live_backup_<timestamp>` with `backup_manifest.json`, copies staged
  files without stopping, restarting, or launching the live client by default,
  and records `live_promotion.json` as durable post-promotion evidence. A live
  client launch after promotion is available only through the explicit
  `-LaunchAfterPromote` switch; it starts the live executable when it is not
  already running and never restarts an existing live client.
- Prepare sandbox smoke without interfering with live play.
  Status: `SmokePreflight` uses the latest staged package, creates one only
  when it is missing, runs sandbox setup, verifies staged package hashes against
  sandbox files, writes the current manifest fingerprint into
  `smoke_preflight.json`, and does not launch, stop, or overwrite the live
  client. The release gate blocks stale preflight evidence after a new manifest
  is generated.
- Inspect sandbox smoke state without changing client state.
  Status: `SmokeStatus` writes `smoke_status.json` from existing sandbox
  process/log state and does not launch, stop, or overwrite any client. It also
  rejects a `SandboxClient` path that aliases `SourceClient`.
- Inspect full goal state without changing client state.
  Status: `GoalStatus` refreshes `release_gate.json` and `goal_audit.json`,
  writes `goal_status.json`, prints P0-P5 status and the next command when a
  next gate exists, and does not launch, stop, or overwrite any client.

### P6: Module Lane And New Features

- Keep the generated module workplan current before adding new helper behavior.
  Status: `scripts/ops/otclient_helper_module_audit.py` writes
  `runtime/solteria_helper_dev/module_audit.json` and
  `docs/otclient/solteria_helper_module_workplan.md`.
- Treat the 5k-line helper as a module host, not as the default place for new
  behavior. New features must enter through a named lane with profile keys,
  safe boot defaults, tests, sandbox smoke evidence, and release-gate evidence.
- Extract or isolate shared domains before extending runtime behavior:
  recovery/vitals, target guards, actionbar actions, diagnostics, and module
  registry.
- Convert placeholders in order: Heal Friend, Conditions diagnostics,
  Equipment safe swaps, then Scripting policy shell.
- Do not implement arbitrary scripting or live-client actions until the risk
  model, audit logging, Control Center evidence, and targeted tests exist.
  Status: this remains a planning lane; runtime enablement is blocked until the
  module-specific gates in `solteria_helper_module_workplan.md` pass.

### P7: Next Module Design Queue

- Keep the supplemental next-module plan current after the extraction map is
  complete.
  Status: `scripts/ops/otclient_helper_next_modules_plan.py` writes
  `runtime/solteria_helper_dev/next_modules_plan.json` and
  `docs/otclient/solteria_helper_next_modules_plan.md`.
- Treat local ZeroBot material as a capability/API reference, not as a visual
  or runtime copy target.
- Treat vBot or other external bot logic as `source_required` until the actual
  source/archive is present, reviewed for provenance, and mapped into CTOAi
  safe-boot gates.
- Build the next functions in this order unless sandbox evidence changes the
  priority: HUD overlay domain, hotkey normalization, confirmation modal
  lifecycle, route engine split, target scorer split, then external vBot import
  review.
```


## `docs/otclient/HELPER_RUNTIME_BRIDGE_V1.md`

```markdown
# Helper Runtime Bridge v1

## Outcome

Enable one bounded Healing/Recovery action in the sandbox without changing the
Helper safe-boot contract. The bridge connects passive decisions to an injected
executor; it does not call OTClient globals directly and does not authorize live
promotion.

## Scope

- Action: `plan_heal` / `cast_heal` only.
- Environment: sandbox only.
- Boot state: disarmed and dry-run.
- Arm gate: explicit operator confirmation, runtime enablement, and a non-empty
  session identifier.
- Runtime guards: online client, living player, client readiness, protection
  zone exclusion, cooldown, armed-session match, and active kill switch.
- Failure policy: bounded consecutive failures activate the kill switch.
- Trace: `decision -> guard -> action -> result` using
  `ctoa.recovery-bridge-trace.v1`.

## Acceptance Evidence

1. Real-Lua tests prove dry-run never invokes the executor.
2. Execution requires an explicitly armed matching sandbox session.
3. Cooldown and PZ guards fail closed.
4. Retry-budget exhaustion disarms the bridge and activates its kill switch.
5. The packaged boot graph includes the bridge after policy and dispatch guard.
6. No direct `g_game`, cast, item-use, movement, or live-promotion call exists.
7. Sandbox attach and in-world evidence are required before adding a native
   executor adapter or expanding beyond Healing/Recovery.

## Deliberate Boundary

This phase supplies the execution boundary and injected-executor contract. The
native OTClient executor adapter, operator UI arming control, live promotion,
Combat, CaveBot, Equipment, Conditions, and Heal Friend remain outside v1 until
the sandbox acceptance evidence is complete.
```


## `docs/otclient/solteria_helper_test_env.md`

```markdown
# Solteria Helper Test Environment

This sandbox runs a separate Solteria client from:

```text
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client
```

It keeps mutable CTOA files, logs, and UI preferences separate from the normal play client:

```text
C:\Users\zycie\AppData\Local\Solteria\client
```

Large data folders/packages are linked to avoid duplicating the full client. The executable files are copied, not hardlinked, so the sandbox can run next to the normal client.

## Commands

Prepare a development package and manifest without launching, stopping, or
overwriting the live play client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PrepareDev
```

Run static validation for the current development package without touching the
live play client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ValidateDev
```

Prepare sandbox files:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Setup -Tab healing
```

Verify sandbox files match the staged dev package without launching a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
```

`SmokePreflight` uses the latest staged package and only creates a fresh one
when the staged package is missing, so it does not reset a freshly passed
`ValidateDev` report.

Inspect current sandbox smoke readiness without launching or stopping a client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeStatus
```

`SmokeStatus` writes `next_action` and `next_command` into
`runtime\solteria_helper_dev\smoke_status.json` so the next safe operator step
is explicit. The report is written atomically and uses simple process summaries
so a blocked or closed sandbox does not leave a partial JSON file.

Refresh the full development goal status without launching or stopping a
client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action GoalStatus
```

`GoalStatus` refreshes `release_gate.json` and `goal_audit.json`, writes
`runtime\solteria_helper_dev\goal_status.json`, and prints P0-P5 status,
current blockers, and the next safe command when a next gate still exists. It
does not launch, stop, or overwrite any client.

Emergency-disable CTOA modules in the normal live Solteria client when login is
unstable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action DisableLiveCtoa
```

Re-enable them after testing:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action EnableLiveCtoa
```

Launch the sandbox manually:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch -Tab healing
```

Capture the current sandbox window without restarting or changing helper tabs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Snapshot
```

Check whether the sandbox is ready for in-world attach smoke:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck
```

`ReadyCheck` writes `runtime\solteria_helper_dev\ready_check.json` for both
success and blocker states. If the sandbox window is missing, or if the Select
Character modal/helper-offline state blocks tab switching, the JSON records the
status, latest smoke marker, screenshot path when available, and next safe
command.

Verify real HP/MP observation while the sandbox runtime is disarmed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HealingVitalsSmoke
```

This writes `runtime\solteria_helper_dev\healing_vitals_smoke.json`. It reads
only the sandbox `ctoa_local.log`, requires a real bounded HP/mana API sample,
and fails closed unless the latest runtime state is disarmed. It never casts,
uses potions, arms runtime, launches a client, or touches the live client. After
it passes, capture newer visual evidence with `SmokeAttach -Tab healing`.

Verify the passive Combat/PZ/NPC safety lane with a fresh manual API probe:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action CombatSafetySmoke
```

This writes `runtime\solteria_helper_dev\combat_safety_smoke.json`. It combines
the targeting and combat-runtime static reports with a fresh read-only sandbox
probe, requires no active target, and requires runtime to be disarmed before and
throughout the probe. It does not attack, follow, cast, use runes/items, or touch
the live client. After it passes, refresh Hunting and Hunting/Magic evidence
with `SmokeAttachAll`.

Verify the CaveBot planner without walking or pathfinding:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action CavebotSafetySmoke
```

Verify one passive Timer planning tick while Timer and runtime remain disabled:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action TimerSafetySmoke
```

Verify read-only container capabilities while experimental Loot remains off:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LootSafetySmoke
```

These reports require current static gates and disarmed runtime. CaveBot records
capabilities and route guards only, Timer must return `hold_timer_disabled`,
and Loot must return `hold_feature_flag_disabled` with zero planned items.
Refresh their evidence with `SmokeAttach -Tab cavebot`,
`SmokeAttach -Tab tools_timer`, and `SmokeAttach -Tab tools_diag`.

Run the static Heal Friend no-target contract before enabling any sio path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action HealFriendNoTargetSmoke
```

This writes `runtime\solteria_helper_dev\heal_friend_no_target_smoke.json` and
checks the read-only observer, safe boot profile defaults, whitelist guard, and
absence of `castSpell`, actionbar sends, and `g_game.talk` in the Heal Friend
observer slice. It does not launch, stop, or overwrite any client.

Run the static Conditions observer contract before enabling any condition
recovery action:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ConditionsObserverSmoke
```

This writes `runtime\solteria_helper_dev\conditions_observer_smoke.json` and
checks the read-only state/API observer, safe boot profile defaults, and absence
of `castSpell`, actionbar sends, and `g_game.talk` in the Conditions observer
slice. It does not launch, stop, or overwrite any client.

Run the static Equipment observer contract before enabling any ring, amulet, or
weapon swap path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action EquipmentObserverSmoke
```

This writes `runtime\solteria_helper_dev\equipment_observer_smoke.json` and
checks the read-only inventory slot/API observer, safe boot profile defaults,
and absence of `castSpell`, actionbar sends, `g_game.talk`, `g_game.move`,
`moveTo`, item use, or inventory-use calls in the Equipment observer slice. It
does not launch, stop, move gear, use items, or overwrite any client.

Run the static Scripting policy contract before enabling any command model,
snippet, or runtime eval path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ScriptingPolicySmoke
```

This writes `runtime\solteria_helper_dev\scripting_policy_smoke.json` and
checks the deny-all profile defaults, forced-off runtime flags, blocked unsafe
status text, and absence of `loadstring`, `dofile`, `require`, runtime calls,
talk, casts, or actionbar sends in the Scripting policy slice. It does not
launch, stop, evaluate snippets, run files, talk, cast, or overwrite any client.

Run every static prototype-module gate with one command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
```

This writes `runtime\solteria_helper_dev\module_static_gates.json` after running
`HealFriendNoTargetSmoke`, `ConditionsObserverSmoke`,
`EquipmentObserverSmoke`, and `ScriptingPolicySmoke`. It is repo-only evidence:
it does not launch, stop, attach to, promote, or overwrite any client.

Run the complete local readiness pipeline before opening the sandbox client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LocalReady
```

This runs `ValidateDev`, `SmokePreflight`, `ModuleStaticGates`, `GoalStatus`,
and `SmokeQueue` in order, then writes
`runtime\solteria_helper_dev\local_ready.json`. A
`ready_for_sandbox` result means local packaging, static validation, staged
sandbox files, and prototype-module static gates are current; it still does not
launch, stop, attach to, promote, or overwrite any live client.

Run a UI smoke and capture a screenshot from the sandbox window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab healing
```

Run all ZeroBot-like helper tabs/subtabs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAll -DismissDialogs
```

Covered views:

```text
overview, healing, heal_friend, conditions, hunting, hunting_magic,
cavebot, equipment, tools, tools_pvp, tools_hud, tools_timer,
tools_diag, scripting, profile, ui
```

Build a machine-readable coverage report from the screenshots:

```powershell
python scripts\ops\ctoa_helper_smoke_report.py --run-id 20260705-035
```

Expected result:

```text
Coverage: 16/16
```

The report includes a `ZeroBot Mapping` section that maps every captured view
to the expected ZeroBot-like module surface. If the report says
`blocked_by_character_modal`, it is only a routing/screenshot proof, not final
in-world visual acceptance.

The reporter also writes an HTML visual review gallery next to the JSON/MD
artifacts. Open `solteria-helper-smokeall-coverage-<run-id>.html` for a compact
contact sheet of every ZeroBot-like view.

## Post-login Attach Smoke

Use this when the sandbox client is already running and a character is inside
the game world. This avoids restarting the client and avoids the Select
Character modal covering the helper.

1. Launch the sandbox:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch
```

2. Log in with a test character.
3. Optionally confirm the sandbox is in-world:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck
```

4. Switch a helper tab without restarting the client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_pvp
```

Run every view in the already-logged-in client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll
```

`SmokeAttachModules` is the focused in-world gate for the prototype module tabs:
`heal_friend`, `conditions`, `equipment`, and `scripting`. It writes
`runtime/solteria_helper_dev/module_attach_smoke.json` and routes to
`SmokeAttachAll` only when all four module tabs capture successfully.

Use a stable run id when you want repeatable artifact names:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll -RunId 20260705-0430
```

`SmokeAttachAll` automatically builds an in-world coverage report with:

```powershell
python scripts\ops\ctoa_helper_smoke_report.py --run-id <run-id> --prefix solteria-helper-attach --in-world
```

Attach smoke writes `ctoa_smoke_command.lua`; the helper consumes it during
runtime, switches tabs, logs `Smoke tab visible: <tab>/<subtab>`, captures a
screenshot, and then generates the coverage report.

Attach smoke requires a fresh `Smoke tab visible: ...` marker written after the
command file is created. If the client is still on `Select Character`, attach
smoke fails with an instruction to enter the character first instead of
accepting an old log marker.

If the client is stopped at the character list, the `Select Character` modal can cover the helper. This is expected and means the screenshot is only a partial runtime proof. You can attempt to dismiss startup dialogs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab overview -DismissDialogs
```

Stop only the sandbox client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Stop
```

## Tab Persistence

The smoke writes `ctoa_ui_prefs.lua` with:

```lua
active_tab = "healing"
```

The helper loads it through `ctoa_native_helper.lua`, switches to that tab on `buildUi()`, and exposes:

```lua
CTOA_Helper.showTab("healing")
```

Use this for targeted screenshots:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab ui
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab hunting
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab hunting_magic
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Smoke -Tab tools_pvp
```

## Logs And Screenshots

Sandbox logs:

```text
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client\otclient.log
C:\Users\zycie\AppData\Local\SolteriaCodexTest\client\ctoa_local.log
```

Screenshots:

```text
runtime\otclient_ui_preview\solteria-helper-testenv-<tab>-<timestamp>.png
```

Development package artifacts:

```text
runtime\solteria_helper_dev\manifest.json
runtime\solteria_helper_dev\CHANGELOG.md
runtime\solteria_helper_dev\validation.json
runtime\solteria_helper_dev\release_readiness.json
runtime\solteria_helper_dev\release_gate.json
runtime\solteria_helper_dev\goal_audit.json
runtime\solteria_helper_dev\goal_status.json
runtime\solteria_helper_dev\smoke_preflight.json
runtime\solteria_helper_dev\smoke_status.json
runtime\solteria_helper_dev\ready_check.json
runtime\solteria_helper_dev\live_promotion.json
runtime\solteria_helper_dev\live_backup_<timestamp>\backup_manifest.json
runtime\solteria_helper_dev\latest\
runtime\solteria_helper_dev\ctoa_otclient_<version>.zip
```

`manifest.json` contains the staged file list with SHA256 hashes and a snapshot
of any running Solteria process. The release gate verifies those staged file
hashes against `latest` before promotion. `validation.json` is `pending` after
`PrepareDev` and becomes `passed` only after `ValidateDev` completes all gates.
`release_readiness.json` keeps the promotion gates explicit: static validation
can pass while sandbox launch, `SmokeAttachModules`, `SmokeAttachAll`, and live approval remain
pending.
`release_gate.json` is the strict audit result. It remains `blocked` until
`smoke_preflight.json` is `passed`, fresh `SmokeAttachModules` evidence exists,
a complete in-world SmokeAttachAll report is present, and explicit live approval
or durable `live_promotion.json` evidence is present. It also writes
`next_action` and `next_command` for the next safe gate step. The preflight
report includes the current manifest fingerprint, so the gate blocks stale
preflight evidence after a new package is generated. The gate also verifies the
versioned ZIP SHA256 against `release_readiness.json` before allowing
promotion. After promotion, `live_promotion.json` must be newer than the current
manifest and the live client files must match the current manifest hashes before
`live_approval` remains `passed`.
When `ModuleAttachSmoke` or `SmokeAttachAll` is the active blocker, the gate reads
`smoke_status.json` and `ready_check.json` to choose the next safe command:
`Launch` when the sandbox is not running, `ReadyCheck` when the sandbox needs an
in-world readiness check, `SmokeAttachModules` first after `ReadyCheck` reports
`ready`, and `SmokeAttachAll` only after module attach evidence has passed. A
fresh `SmokeStatus` blocker such as `not_running`,
`character_modal`, or `helper_log_missing` takes precedence over older
`ready_check.json` evidence.
`goal_audit.json` summarizes the full development plan state and repeats the
current blockers plus the next command from the release gate when one exists.
It also lists the P0-P5 roadmap phases so the remaining incomplete phase is
visible. `goal_audit.html` is generated from that same audit as a local,
read-only dashboard with the release state, next command, roadmap, blockers,
and evidence inventory; its path is included in `goal_status.json`.
`goal_status.json` is the operator-facing read-only summary generated by
`GoalStatus`: it repeats the audit/gate state, P0-P5 roadmap statuses, live
process snapshot, blockers, and next safe command when one exists. It refreshes
`SmokeStatus` first, so the next command reflects the current sandbox process,
window, helper log, and character-modal state before release-gate routing runs.
`GOAL_HANDOFF.md` is generated from the same status payload as a one-screen
operator checklist with current state, P0-P5 roadmap, blockers, next safe
command, module workplan summary, and the live-promotion completion rule. When
`runtime\solteria_helper_dev\module_audit.json` exists, `GoalStatus` also adds
module status, modularization pressure, registry coverage, and each lane's next
step to both `goal_status.json` and `GOAL_HANDOFF.md`. The module audit also
selects `next_module_id` and `next_module_action`, so the handoff separates the
next safe smoke command from the next helper-module development move. When
`heal_friend_no_target_smoke.json` is `passed`, `GoalStatus` advances the
module recommendation to grouped in-world `SmokeAttachModules` evidence and
adds `next_module_command`: `HealFriendNoTargetSmoke` before static evidence,
`Launch` or `ReadyCheck` while the sandbox is not ready, and
`SmokeAttachModules` once `ReadyCheck` reports `ready`.
The same prototype-gate pattern is now available for `conditions` through
`ConditionsObserverSmoke`, with in-world visual acceptance captured later by
`SmokeAttach -Tab conditions`.
`EquipmentObserverSmoke` applies the same rule to `equipment`; it only accepts
read-only inventory observation and leaves ring/amulet/weapon swaps blocked
until sandbox evidence exists.
`ScriptingPolicySmoke` applies the same rule to `scripting`; it only accepts a
deny-all policy shell and leaves snippets, eval, and command execution blocked.
`GoalStatus` aggregates these prototype gates as `static_gate_summary` in
`goal_status.json` and as a `Static gates: passed/total` block in
`GOAL_HANDOFF.md`, so the operator can see which local module gates are ready
before starting sandbox attach smoke. `ModuleStaticGates` refreshes all four
prototype gate reports and writes `module_static_gates.json`; run `GoalStatus`
after it to route the next release step. The release gate also requires a fresh
passed `module_static_gates.json` and a fresh passed
`module_attach_smoke.json` before it routes to final in-world `SmokeAttachAll`,
so new prototype-module risk cannot be skipped during packaging.
`LocalReady` wraps the local half of this flow and should be the first command
when the operator wants one current handoff before opening the sandbox client.
`release_gate.json`, `goal_audit.json`, `goal_status.json`, and
`GOAL_HANDOFF.md` are written atomically, so readers do not observe partial
outputs while `GoalStatus` refreshes the audit.
Neither action copies files into the live play client.

Generate the read-only sandbox smoke queue after `LocalReady` when the release
gate is waiting on attach evidence:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeQueue
.\.venv\Scripts\python.exe scripts\ops\solteria_helper_sandbox_smoke_queue.py
```

This writes `runtime\solteria_helper_dev\sandbox_smoke_queue.json` and
`docs\otclient\solteria_helper_sandbox_smoke_queue.md` from the current
manifest, release gate, smoke status, and goal status. It only plans the
operator sequence; it does not launch, attach to, promote, stop, or overwrite
any client.

You can run the gate audit directly:

```powershell
python scripts\ops\solteria_helper_release_gate.py --dev-dir runtime\solteria_helper_dev --allow-blocked
```

If `--smoke-report` is not provided, the gate looks for the latest
`runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-*.json` report.
It intentionally ignores modal-limited `solteria-helper-smokeall-coverage-*.json`
reports. An in-world report must include every expected helper view and each
listed screenshot file must exist on disk.

Live promotion is intentionally separate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action BackupLiveCtoa
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy
```

`PromoteLiveCtoa` refuses to run without `-ApproveLiveDeploy`, then checks the
existing strict release gate for the current staged package with approval. It
does not run `ValidateDev`, run `SmokePreflight`, regenerate the manifest, or
change the staged package after in-world `SmokeAttachAll` has passed. It will
still refuse to copy files until `SmokePreflight` and in-world `SmokeAttachAll`
are passed. After the gate passes, it writes a fresh
`live_backup_<timestamp>\backup_manifest.json`, copies staged files into the
live client without stopping, restarting, or launching it by default, and
records `live_promotion.json` as durable post-promotion evidence.

If the operator wants the live client opened immediately after a successful
promotion, make that explicit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -LaunchAfterPromote
```

`-LaunchAfterPromote` starts `SourceClient\solteria-client.exe` only when that
exact live client is not already running. It records `launched`,
`already_running`, or `failed` in `live_promotion.json`; it never stops or
restarts the live client.

If needed, pass a specific in-world smoke report:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-<run-id>.json
```

The Helper can also export its bounded runtime diagnostics buffer from the
sandbox/live module directory as:

```text
ctoa_diag_export.lua
```

Use the smoke command action `diag_export` or the in-client
`CTOA_Helper.exportDiagnostics()` entrypoint after the sandbox Helper has
collected samples. The export contains only bounded passive snapshots for
HP/MP, movement, combat, magic, and container APIs.

## Test Account

For live in-game UI/runtime checks, use a separate low-risk test character in the sandbox. Keep the main play client logged in normally. The sandbox should be used for:

- helper UI screenshots,
- tab persistence checks,
- combat/healing log validation,
- PZ/NPC/targeting regression tests,
- actionbar potion/rune behavior checks.

Full visual acceptance for all tabs requires the sandbox to enter the game world with a separate test character. Before login, the character selection modal is above helper widgets and can obscure screenshots even when `CTOA_Helper.showTab("<tab>")` succeeds.

Static geometry/layout acceptance is covered by:

```powershell
python scripts\ops\ctoa_helper_ui_preview.py
```

Expected result:

```text
issues: none
```

Regression tests for the ZeroBot-like shell contract:

```powershell
python -m pytest tests\test_otclient_helper_zerobot_shell.py -q
```

Expected result:

```text
4 passed
```

## PZ / NPC Targeting Regression

The helper combat runtime must not attack NPCs or run offensive actions in PZ.
Use this after changing targeting, magic shooter, rune shooter, or auto exeta.

Live/sandbox steps:

1. Enter the game world with a test character.
2. Stand in PZ or near an NPC such as `Taskmaster Liora`.
3. Keep `Targeting` enabled for 30-60 seconds.
4. Inspect `ctoa_local.log`.

Passing log pattern:

```text
[CTOA-OTC-COMBAT] Combat paused: no valid monster target
```

Failing log pattern:

```text
[CTOA-OTC-COMBAT] Auto target: Taskmaster Liora
```

If a bad target still appears, inspect the probe line. It logs the client-side
creature methods used by the guard:

```text
[CTOA-OTC-COMBAT] Target probe: <name> id=<id> reason=<reason> isNpc=<...> isMonster=<...> isPlayer=<...> isAttackable=<...> canBeAttacked=<...> isTargetable=<...>
```

Current guard behavior:

- `pause_in_pz=true` blocks targeting, rune shooter, spell rotation, and auto exeta.
- NPC/player/ignored names are rejected before attack.
- Unknown creature types are treated as non-monsters.
- The helper HUD and combat module share the same valid-target rules.
```


## `docs/otclient/solteria_helper_module_workplan.md`

```markdown
# Solteria Helper Module Workplan

## Current Decision

- Status: `ready`
- Helper lines: `4349`
- Helper functions: `159`
- Helper line budget: `4500`
- Helper function budget: `130`
- Helper budget status: `over_budget`
- Helper shell target: UI composition, profile persistence, and guarded dispatch only; registry/domain logic belongs in helper modules/adapters.
- Modularization pressure: `medium`
- Placeholder modules: `0`
- Implemented modules: `31`
- Prototype modules: `0`
- Registry coverage: `9` / `9`
- Next extraction: `none`
- Next supplemental split: `none`
- Next phase: P6-module-lane: keep the main helper as UI composition shell; move runtime adapters behind static contracts and sandbox gates.
- Next module action: `` - Keep module gates current before adding new runtime actions.

## Operating Rule

New behavior must enter through a named module lane with profile keys, safe boot defaults, static tests, sandbox smoke evidence, and release-gate evidence. Do not add broad runtime logic directly to the main helper without updating this workplan and the module audit.

The helper Overview must expose module readiness from `ctoa_helper_modules.lua` so operators can see implemented, prototype, armed, gated, and experimental lanes without enabling runtime actions.

## Module Lanes

| Module | Status | Target | Next step | Gate |
|---|---:|---|---|---|
| `healing` / Healing and recovery | `static_gated` | `ctoa_native_heal.lua` | Keep runtime logic mirrored in standalone passive recovery module and add sandbox HP/MP log smoke. | ValidateDev plus in-world HP/MP sandbox log evidence. |
| `combat` / Targeting and magic shooter | `static_gated` | `ctoa_native_combat.lua` | Extract shared target scoring/guards into a reusable helper runtime domain before adding more attacks. | PZ/NPC regression log plus SmokeAttachAll hunting and hunting_magic views. |
| `cavebot` / CaveBot route and movement | `static_gated` | `ctoa_native_helper.lua` | Split route editing from movement execution into separate domain blocks before adding waypoint actions. | Route editor static tests plus sandbox autoWalk retry-budget evidence. |
| `loot` / Loot scanner | `static_gated` | `ctoa_native_loot.lua` | Promote loot from experimental flag only after in-world container scan evidence exists. | ValidateDev plus bounded ctoa_local.log loot scan evidence in sandbox. |
| `timer` / Timer action | `static_gated` | `ctoa_native_helper.lua` | Keep timer as a small bounded action; do not add arbitrary scripting through timer message. | Static contract and sandbox log evidence for one timer tick. |
| `heal_friend` / Heal Friend | `static_gated` | `ctoa_helper_heal_friend.lua` | Run HealFriendNoTargetSmoke, then capture grouped in-world SmokeAttachModules evidence before any sio cast path. | No runtime sio cast until whitelist UI, profile persistence, HealFriendNoTargetSmoke, ModuleStaticGates, and ModuleAttachSmoke evidence exist. |
| `conditions` / Conditions | `static_gated` | `ctoa_helper_conditions.lua` | Run ConditionsObserverSmoke, then capture grouped in-world SmokeAttachModules state evidence before any recovery action. | No condition recovery action until API probe evidence, passive plan contract, ConditionsObserverSmoke, ModuleStaticGates, and ModuleAttachSmoke pass. |
| `equipment` / Equipment | `static_gated` | `ctoa_helper_equipment.lua` | Run EquipmentObserverSmoke, then capture grouped in-world SmokeAttachModules inventory evidence before any swap path. | No runtime swap before inventory API probe output, passive plan contract, profile persistence, EquipmentObserverSmoke, ModuleStaticGates, and ModuleAttachSmoke. |
| `scripting` / Scripting | `static_gated` | `ctoa_helper_scripting.lua` | Run ScriptingPolicySmoke, then capture grouped in-world SmokeAttachModules policy shell evidence; keep eval and user snippets blocked. | No user snippet execution until passive plan contract, security review, denylist tests, audit logging, ScriptingPolicySmoke, ModuleStaticGates, and ModuleAttachSmoke pass. |

## Extraction Map

| Order | Domain | Target | Status | Gate |
|---:|---|---|---:|---|
| 1 | `module_registry` / MODULE_LANES, module lane lookup, readiness text | `ctoa_helper_modules.lua` | `extracted` | Registry parity test plus Overview readiness smoke. |
| 2 | `diagnostics` / log helpers, API probes, status snapshots, module evidence formatting | `ctoa_helper_diagnostics.lua` | `extracted` | ValidateDev, UI preview, and no secret/runtime path leakage in generated evidence. |
| 3 | `heal_friend` / heal friend profile defaults, whitelist matching, observer sampling, UI summary | `ctoa_helper_heal_friend.lua` | `extracted` | HealFriendNoTargetSmoke, ModuleStaticGates, and ModuleAttachSmoke before any sio runtime arm. |
| 4 | `conditions` / condition state API probes, read-only observer rows, passive recovery planner, profile defaults | `ctoa_helper_conditions.lua` | `extracted` | ConditionsObserverSmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke before any recovery action. |
| 5 | `equipment` / inventory slot probes, passive ring/amulet swap planner, read-only UI summary | `ctoa_helper_equipment.lua` | `extracted` | EquipmentObserverSmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke before any use/move action. |
| 6 | `scripting` / policy shell, deny-all snippet planner, audit metadata | `ctoa_helper_scripting.lua` | `extracted` | ScriptingPolicySmoke, passive plan contract, ModuleStaticGates, and ModuleAttachSmoke; eval remains blocked. |

## Supplemental Refactor Plan

This is the next wave after the passive helper modules are contracted. It exists because the main helper is still over budget and should become a composition shell instead of absorbing more runtime logic.

| Order | Split | Target | Status | Gate |
|---:|---|---|---:|---|
| 1 | `combat_runtime_adapter` / combat arming, monster scan adapter, attack/cast execution guards | `ctoa_helper_combat_runtime.lua` | `extracted` | Combat runtime static contract, target scorer contract, monster-only regressions, PZ/NPC smoke, SmokeAttachAll hunting tabs. |
| 2 | `cavebot_runtime_adapter` / movement execution, path probe, retry budget, PZ/offline movement guards | `ctoa_helper_cavebot_runtime.lua` | `extracted` | Route contract, cavebot static tests, in-world retry-budget evidence, SmokeAttachAll cavebot tab. |
| 3 | `loot_runtime_adapter` / corpse/container scan orchestration, item move bounds, capacity guard | `ctoa_helper_loot_runtime.lua` | `extracted` | Container API probe, experimental_loot remains false by default, bounded sandbox loot log evidence. |
| 4 | `timer_runtime_adapter` / bounded timer message/cast action, interval guard, action lock | `ctoa_helper_timer_runtime.lua` | `extracted` | Static no-eval contract, one-tick sandbox log evidence, no scripting bridge. |
| 5 | `profile_schema_adapter` / profile defaults, migration keys, rotation preset metadata, profile dirty reasons, profile UI persistence | `ctoa_helper_profile_schema.lua` | `extracted` | Profile audit, schema snapshot, safe migration and rotation-summary tests, no key-order churn. |
| 6 | `operator_summary_bridge` / operator title, domain summary text, profile/UI summary bridge, and no-widget text composition | `ctoa_helper_operator_summary.lua` | `extracted` | OperatorSummary static contract, profile schema and domain summary parity, ModuleStaticGates, UI preview, and sandbox SmokeAttachModules before any runtime bridge can consume summaries. |
| 7 | `planner_coordinator` / passive plan collection, ranking, summary, and no-execution contract | `ctoa_helper_planner.lua` | `extracted` | Planner static contract, module planner regressions, ModuleStaticGates, and sandbox SmokeAttachModules before any runtime dispatcher wiring. |
| 8 | `runtime_policy_guard` / shared runtime gate evaluation, manifest freshness, sandbox smoke, and live approval policy | `ctoa_helper_runtime_policy.lua` | `extracted` | RuntimePolicy static contract, ModuleStaticGates, current manifest, ModuleAttachSmoke, SmokeAttachAll, and explicit live approval before any dispatcher executes a plan. |
| 9 | `dispatch_guard_coordinator` / ranked plan classification, runtime policy handoff, and dispatch allow/deny reasons | `ctoa_helper_dispatch_guard.lua` | `extracted` | DispatchGuard static contract, RuntimePolicy ready decision, sandbox attach evidence, and explicit live approval before any dispatcher bridge is wired. |
| 10 | `plan_queue_coordinator` / bounded guarded-decision queue, review summaries, and no-execution handoff state | `ctoa_helper_plan_queue.lua` | `extracted` | PlanQueue static contract, DispatchGuard decision evidence, bounded queue tests, sandbox attach evidence, and explicit live approval before queued plans can feed any dispatcher bridge. |
| 11 | `runtime_readiness_status` / component readiness, gate readiness, queued-plan review status, and no-execution runtime bridge summary | `ctoa_helper_runtime_readiness.lua` | `extracted` | RuntimeReadiness static contract, required component/gate coverage, current manifest, sandbox attach evidence, SmokeAttachAll, and explicit live approval before any runtime bridge is considered ready. |
| 12 | `module_status_board` / module readiness rows, status counts, blocker summary, and no-execution evidence board | `ctoa_helper_module_status.lua` | `extracted` | ModuleStatus static contract, module contract coverage, ModuleStaticGates, sandbox attach evidence, and explicit live approval before status can support runtime enablement. |
| 13 | `action_catalog_policy` / runtime action capability names, domain mapping, risk class, required gates, and no-execution dispatch metadata | `ctoa_helper_action_catalog.lua` | `extracted` | ActionCatalog static contract, action risk coverage, RuntimePolicy gate parity, ModuleStaticGates, sandbox attach evidence, and explicit live approval before any action can be dispatched. |
| 14 | `decision_trace_review` / plan/policy/guard/queue decision traces, missing gate summaries, and no-write review metadata | `ctoa_helper_decision_trace.lua` | `extracted` | DecisionTrace static contract, policy/guard reason coverage, bounded queue trace, ModuleStaticGates, sandbox attach evidence, and explicit live approval before any trace informs runtime dispatch. |
| 15 | `sandbox_handoff_checklist` / operator sandbox smoke checklist, required runtime gates, next-step summary, and no-launch/no-promote handoff metadata | `ctoa_helper_sandbox_handoff.lua` | `extracted` | SandboxHandoff static contract, Launch/ReadyCheck/SmokeAttachModules/SmokeAttachAll/ApproveLiveDeploy sequence coverage, ModuleStaticGates, and explicit live approval before live promotion. |
| 16 | `feature_flag_matrix` / safe false runtime flags, feature domains, required gates, and no-toggle profile audit metadata | `ctoa_helper_feature_flags.lua` | `extracted` | FeatureFlags static contract, safe-default coverage, profile audit parity, ModuleStaticGates, SmokeAttachAll, and explicit live approval before runtime flags can be enabled. |

## P6 Module Lane

1. Freeze the current helper UI contract with `ValidateDev`, `ctoa_helper_ui_preview.py`, and `SmokePreflight`.
2. Extract domains in the `Extraction Map` order and keep the main helper as the UI composition shell.
3. Execute the `Supplemental Refactor Plan` one adapter at a time; adapter files may plan or dispatch guarded actions only after static contracts exist.
4. Convert prototype modules in order: Heal Friend observation, Conditions diagnostics, Equipment safe swaps, Scripting policy shell.
5. For each module, add profile schema keys, safe boot defaults, tests, README/docs, `ModuleStaticGates`, and `SmokeAttachModules` before runtime enablement.
6. Keep live promotion separate and require `PromoteLiveCtoa -ApproveLiveDeploy` after in-world `SmokeAttachAll` evidence.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_module_audit.py --json-out runtime\solteria_helper_dev\module_audit.json
.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_module_audit.py tests\test_otclient_helper_zerobot_shell.py tests\test_otclient_helper_profile_audit.py tests\test_ctoa_helper_smoke_report.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ValidateDev
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokePreflight
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules
```
```


## `docs/otclient/solteria_helper_module_contract.md`

```markdown
# Solteria Helper Module Contract

- Status: `passed`
- Expected modules: `32`
- Passed modules: `32`
- Failed modules: `0`
- Registry lanes: `9` / `9`
- Forbidden passive hits: `0`
- Next action: Run ModuleStaticGates, then sandbox SmokeAttachModules.

## Rule

Passive helper modules may observe, format, plan, or expose UI state. They must not cast spells, use items, walk, execute snippets, or load arbitrary files. Runtime actions stay in the guarded native helper domains and still require sandbox evidence.

## Modules

| Module | File | Status | Loader | Registry | Global | Return | Missing functions | Forbidden |
|---|---|---:|---:|---:|---:|---:|---|---|
| `modules` | `ctoa_helper_modules.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `domain_contract` | `ctoa_helper_domain_contract.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `ui` | `ctoa_helper_ui.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `diagnostics` | `ctoa_helper_diagnostics.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `hotkeys` | `ctoa_helper_hotkeys.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `modal` | `ctoa_helper_modal.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `route` | `ctoa_helper_route.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `targeting` | `ctoa_helper_targeting.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `combat_runtime` | `ctoa_helper_combat_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `cavebot_runtime` | `ctoa_helper_cavebot_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `loot_runtime` | `ctoa_helper_loot_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `timer_runtime` | `ctoa_helper_timer_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `recovery_runtime` | `ctoa_helper_recovery_runtime.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `profile_schema` | `ctoa_helper_profile_schema.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `profile_persistence` | `ctoa_helper_profile_persistence.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `operator_summary` | `ctoa_helper_operator_summary.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `planner` | `ctoa_helper_planner.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `runtime_policy` | `ctoa_helper_runtime_policy.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `dispatch_guard` | `ctoa_helper_dispatch_guard.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `plan_queue` | `ctoa_helper_plan_queue.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `runtime_readiness` | `ctoa_helper_runtime_readiness.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `module_status` | `ctoa_helper_module_status.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `action_catalog` | `ctoa_helper_action_catalog.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `decision_trace` | `ctoa_helper_decision_trace.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `decision_pipeline` | `ctoa_helper_decision_pipeline.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `sandbox_handoff` | `ctoa_helper_sandbox_handoff.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `feature_flags` | `ctoa_helper_feature_flags.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `hud` | `ctoa_helper_hud.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `conditions` | `ctoa_helper_conditions.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `equipment` | `ctoa_helper_equipment.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `scripting` | `ctoa_helper_scripting.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |
| `heal_friend` | `ctoa_helper_heal_friend.lua` | `passed` | `yes` | `yes` | `yes` | `yes` | none | none |

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_helper_module_contract.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
```
```


## `docs/otclient/solteria_helper_next_modules_plan.md`

```markdown
# Solteria Helper Next Modules Plan

## Decision

- Status: `ready_for_sandbox_then_next_module_design`
- Current extraction map: complete.
- Budget priority source: `runtime\solteria_helper_dev\helper_shell_budget_plan.json`.
- Budget top non-shell domain: `runtime_cavebot`.
- Budget next extraction domains: `runtime_cavebot, runtime_combat, diagnostics_smoke, ui_builder, profile_persistence`.
- Runtime evidence: in-world `SmokeAttachModules` and fresh `SmokeAttachAll` are current for v2.1.1a; runtime execution remains blocked by module-specific action gates and explicit live approval.
- External vBot source: `source_required`; do not claim vBot-derived implementation until source/provenance is present.

## Source Policy

- ZeroBot reference: `docs/otclient/zerobot_reference.md`
- vBot: `source_required`
- External bot intake: `scripts/ops/otclient_external_bot_intake.py`
- External bot import gate: import_gate.runtime_import_allowed must remain false until mapped module gates and sandbox evidence pass
- Rule: Use external bots as capability checklists and naming references only; no direct copy without provenance review; keep CTOAi safe boot, gates, and tests.

## Prerequisites

- Run SmokeAttachModules after sandbox character is in-world.
- Run SmokeAttachAll for the current dev manifest before enabling runtime actions.
- Keep PromoteLiveCtoa behind -ApproveLiveDeploy.

## Candidate Modules

| Order | Module | Status | Source basis | Target | First slice | Gate | Blocked until |
|---:|---|---:|---|---|---|---|---|
| 0 | `ui_primitives` / Guarded UI primitives split | `static_gated` | Current UI composition shell plus passive UI adapter; corrected budget keeps it below cavebot/combat pressure | `ctoa_helper_ui.lua` | Move text fitting, widget styling, checkbox state helpers, visibility helpers, guarded createWidget wrapper, nav/subtab style functions, button/card style descriptors, metric row styling, setting/profile/vector row styling, section/table/strip styling, priority badge styling, label styling, window chrome styling, toggle/checkbox/sidebar-card styling, overview avatar/equipment styling, control-name styling, row geometry, and tab metadata behind CTOA_HELPER_UI. | ModuleContract, UI preview, HelperShellBudgetPlanStaticSmoke, ModuleStaticGates, and current LocalReady. | Further UI builder extraction waits for sandbox SmokeAttachModules so visual regressions can be checked in-world. |
| 1 | `hud` / HUD overlay domain | `static_gated` | ZeroBot HUD wrapper reference plus current Tools/HUD controls | `ctoa_helper_hud.lua` | Extract HUD state formatting and visibility/draggable summary without adding new overlay actions. | HUD static contract, UI preview, ModuleStaticGates, and in-world SmokeAttach -Tab tools_hud. | Current sandbox SmokeAttachModules and fresh SmokeAttachAll evidence exist. |
| 2 | `hotkeys` / Hotkey normalization domain | `static_gated` | ZeroBot hotkeymanager reference plus current Ctrl+H binding | `ctoa_helper_hotkeys.lua` | Add parser/normalizer tests for modifier strings; keep runtime binding unchanged. | Parser unit tests, safe boot check, UI preview, and no automatic new key bindings during loader init. | HUD extraction has tests and sandbox attach evidence. |
| 3 | `modal_confirm` / Confirmation modal domain | `static_gated` | ZeroBot custom modal wrapper reference plus helper profile/reset workflows | `ctoa_helper_modal.lua` | Create a passive modal lifecycle wrapper for destructive helper commands; no live-client action shortcuts. | Static lifecycle tests, UI preview, no PromoteLiveCtoa bypass, and explicit approval path retained. | Hotkey parser is isolated and profile commands remain guarded. |
| 4 | `route_engine` / Cavebot route engine split | `static_gated` | Route engine is static-gated; current shell budget now points remaining runtime pressure at combat/cavebot adapters | `ctoa_helper_route.lua` | Move route labels, waypoint mutation, active target advancement, and retry-budget status into a domain module; keep autoWalk gated. | Route editor static tests, SmokeAttach -Tab cavebot, PZ/offline guard evidence, and no movement at loader init. | Sandbox SmokeAttachModules proves current cavebot tab state in-world. |
| 5 | `target_scorer` / Combat target scorer split | `static_gated` | Current monster-only target guards plus bot decision scoring concepts | `ctoa_helper_targeting.lua` | Extract candidate scoring and ignored-name checks; keep attack/cast execution in existing guarded runtime. | Monster-only regression tests, PZ/NPC smoke evidence, and SmokeAttachAll hunting/hunting_magic screenshots. | Route engine extraction is stable and combat runtime evidence is fresh. |
| 6 | `combat_runtime` / Combat runtime planner split | `static_gated` | Current guarded combat runtime plus target scorer and passive adapter plan | `ctoa_helper_combat_runtime.lua` | Keep passive combat planning, wait-reason text, decision-state text, and cooldown text in the runtime adapter; keep attack, cast, rune, and exeta execution in guarded helper runtime. | Combat runtime static contract, SmokeAttach -Tab hunting_magic, PZ/offline/target-required plan evidence, and no loader-time combat actions. | Target scorer static gate is stable and sandbox combat tabs have fresh attach evidence. |
| 7 | `cavebot_runtime` / Cavebot runtime planner split | `static_gated` | Current guarded autoWalk retry loop plus route engine and passive cavebot adapter plan | `ctoa_helper_cavebot_runtime.lua` | Keep passive cavebot planning, movement decision text, movement blocked-reason/status/trace/path result text, and movement API probe summary text in the runtime adapter; keep autoWalk/findPath execution in guarded helper runtime. | Cavebot runtime static contract, SmokeAttach -Tab cavebot, PZ/offline/empty-route/retry plan evidence, and no loader-time movement. | Route engine static gate is stable and sandbox cavebot tab has fresh attach evidence. |
| 8 | `loot_runtime` / Loot runtime planner split | `static_gated` | Current loot feature flag, API probe, and passive loot adapter plan | `ctoa_helper_loot_runtime.lua` | Use a passive loot runtime planner for diagnostics text; keep container scan/open/move/use behavior outside loader init and guarded by feature flags. | Loot runtime static contract, SmokeAttach -Tab tools_diag, feature-flag/offline/container plan evidence, and no loader-time loot actions. | Experimental loot stays feature-flagged and sandbox diagnostics have fresh attach evidence. |
| 9 | `timer_runtime` / Timer runtime planner split | `static_gated` | Current guarded timer loop plus passive timer adapter plan | `ctoa_helper_timer_runtime.lua` | Use a passive timer runtime planner for timer decision/status text; keep talk/cast execution in the guarded helper runtime. | Timer runtime static contract, SmokeAttach -Tab tools_timer, disabled/PZ/offline/message plan evidence, and no loader-time timer actions. | Timer remains disabled by default and sandbox tools timer tab has fresh attach evidence. |
| 10 | `profile_schema` / Profile schema, persistence policy, rotation metadata, and migration metadata | `static_gated` | Current EK profile defaults plus passive profile schema adapter plan | `ctoa_helper_profile_schema.lua + ctoa_helper_profile_persistence.lua` | Use passive profile schema metadata for required sections, safe false keys, rotation preset labels/summaries, migration readiness, load candidate lists, save path policy, generated save headers, load/save status text, and autosave metadata; keep file reads/writes in existing guarded profile audit/persistence shell paths. | Profile schema static contract, profile audit parity, safe-boot false-key coverage, rotation-summary coverage, key-order preservation, and no loader-time profile writes. | Profile audit and ModuleStaticGates stay current for the staged helper manifest. |
| 11 | `vbot_import` / External vBot/vBot-like import lane | `source_required` | source_required: no vBot source is present in this checkout | `docs/otclient/vbot_import_review.md` | If a vBot source tree is provided, run otclient_external_bot_intake.py and require its import_gate before capability mapping; no direct copy without license/source notes. | Intake import_gate, source provenance note, secret scan, license/provenance review, runtime_gate_mapping, and mapping into existing module gates. | User provides the actual vBot source or a reviewed local archive. |

## Supplemental Execution Plan

P6 evidence progression: `healing_recovery` is now `static_gated` from
`RecoveryRuntimeStaticSmoke`, bounded real-player `HealingVitalsSmoke`, current
module gates, a disarmed sandbox, and a newer Healing-tab attachment. Spell and
potion execution remains in the guarded helper runtime. The evidence-aware
module audit now advances the next prototype lane to `combat`.

`combat`, `cavebot`, `timer`, and `loot` are now also `static_gated`.
Combat reports no active target; CaveBot proves capability and route guards
without walking or pathfinding; Timer returns `hold_timer_disabled`; and Loot
returns `hold_feature_flag_disabled` with zero planned items. Each dedicated
report has current module gates, ReadyCheck, a newer in-world screenshot, and
disarmed-runtime proof. The evidence-aware audit now reports all nine module
lanes `static_gated`; no runtime bridge is enabled by this completion.

| Order | Workstream | Status | Current slice | Next slice | Gate |
|---:|---|---:|---|---|---|
| 0 | `ui_primitives` | `in_progress_static_gated` | ctoa_helper_ui.lua owns text fit, widget style, checkbox state, visibility, guarded createWidget, nav/subtab style, button/card style, metric row/value style, setting/profile/vector row style, section/table/header strip style, priority badge style, label style, window chrome style, toggle/checkbox/sidebar-card style, overview avatar/equipment slot style, control-name style primitives, setting/profile/vector/section row geometry, sidebar/subtab metadata, section scaffold metadata, subtab content offsets, tools table-header metadata, CaveBot action/choice metadata, interactive profile/vector row builders, the passive Hunting targeting/magic panel renderer, the passive CaveBot editor renderer, the passive Tools helper/PvP/HUD/timer/diag panel renderer, the passive Settings/Profile renderer, and the passive Engine/HUD/layout renderer; helper shell now delegates all direct styleWidget calls, row geometry, tab metadata, repeated body/header scaffolding, subtab button creation, cavebot waypoint editor composition/action metadata, tools table headers, hunting targeting/magic composition, tools helper/PvP/HUD/timer/diag composition, profile/settings composition, Engine/HUD/layout composition, and profile cycle/step/vector row construction through UI functions with guarded shell adapters. | Extract remaining runtime probe summaries into passive runtime adapters while keeping value getters/setters, route mutation, and runtime arming in guarded shell adapters. | ModuleContract, UI preview, HelperShellBudgetPlanStaticSmoke, ModuleStaticGates, current LocalReady, then SmokeAttachModules for in-world visual evidence. |
| 1 | `target_scorer` | `in_progress_static_gated` | Targeting owns bestCandidate ranking; helper now builds OTClient candidate snapshots and delegates best-target choice to ctoa_helper_targeting.lua. | Move the remaining PZ/NPC reason summaries into targeting/combat runtime adapters before adding any new combat feature. | TargetingStaticSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach hunting and hunting_magic tabs in sandbox before runtime enablement. |
| 2 | `route_engine` | `in_progress_static_gated` | Route labels, waypoint mutation, active target advancement, retry status, progress state, retryBlocked, selected summary, passive CaveBot editor panel, cavebot runtime decision text, movement blocked-reason/status/trace/path result text, and movement API probe summary text are module/UI-owned. | Move the next cavebot route/probe metadata slice into route/cavebot runtime adapters while keeping movement execution in guarded runtime. | RouteStaticSmoke, ModuleStaticGates, current LocalReady, then SmokeAttach cavebot tab in sandbox. |
| 3 | `heal_friend_observer` | `static_gated` | ctoa_helper_heal_friend.lua owns whitelist matching, visible-player scan, observer updates, runtime plan, status text, decision text, and summary text; fresh HealFriendNoTargetSmoke and in-world attach evidence are recorded. | Keep sio execution unavailable; next review is whitelist persistence and an explicit runtime bridge design. | Current HealFriendNoTargetSmoke, ModuleStaticGates, LocalReady, SmokeAttach heal_friend, SmokeAttachAll, and live approval before any sio runtime bridge. |
| 4 | `conditions_observer` | `static_gated` | ctoa_helper_conditions.lua owns condition flag text, state snapshots, API probe text, observer sampling, passive recovery plan, and summary text; fresh observer and in-world attach evidence are recorded. | Keep condition recovery actions unavailable until a separate guarded runtime bridge is designed and approved. | Current ConditionsObserverSmoke, ModuleStaticGates, LocalReady, SmokeAttach conditions, SmokeAttachAll, and live approval before any condition recovery bridge. |
| 5 | `equipment_observer` | `static_gated` | ctoa_helper_equipment.lua owns slot text, equipment snapshots, inventory API probe text, observer sampling, passive swap plan, and summary text; fresh inventory observer and attach evidence are recorded. | Keep ring/amulet swaps unavailable until a bounded swap bridge and rollback policy are designed and approved. | Current EquipmentObserverSmoke, ModuleStaticGates, LocalReady, SmokeAttach equipment, SmokeAttachAll, and live approval before any equipment bridge. |
| 6 | `scripting_policy` | `static_gated` | ctoa_helper_scripting.lua owns policy snapshots, deny-all planning, and summary text; fresh deny-all policy and attach evidence are recorded. | Keep snippets, eval and arbitrary file execution blocked; no runtime scripting bridge belongs to this phase. | Current ScriptingPolicySmoke, ModuleStaticGates, LocalReady, SmokeAttach scripting, SmokeAttachAll, security review, audit logging, and live approval. |
| 7 | `operator_summary_bridge` | `in_progress_static_gated` | ctoa_helper_operator_summary.lua owns title/domain/profile/UI summary composition; helper shell now only passes local context and renders returned text. | Move any remaining operator-facing summary branches into the module before adding new runtime features, keeping summaries passive and widget-free. | Operator summary static contract, OperatorSummaryStaticSmoke, ModuleStaticGates, UI preview, current LocalReady, then SmokeAttachModules in sandbox before summaries can inform runtime bridge decisions. |
| 8 | `input_contracts` | `in_progress_static_gated` | ctoa_helper_hotkeys.lua owns passive binding decisions, ctoa_helper_modal.lua owns passive confirmation decision text, and otclient_input_contract_fixtures.py now records behavior fixtures for parser and modal states. | Expand fixture cases whenever a new keyboard shortcut, destructive helper action, or external bot command mapping is proposed; keep actual binding and execution inside guarded helper shell paths. | InputContractsStaticSmoke, HotkeysStaticSmoke, ModalStaticSmoke, ModuleStaticGates, current LocalReady, and no loader-time key binding beyond the existing guarded helper toggle. |
| 9 | `profile_persistence` | `in_progress_static_gated` | ctoa_helper_profile_schema.lua owns key order, serializer, labels, summaries, and schema metadata; ctoa_helper_profile_persistence.lua now owns passive load candidates, save path fallback policy, generated save headers, load/save status text, and autosave delay metadata. The helper shell still owns every dofile, io.open, dirty flag mutation, and save execution path. | Move profile export field grouping into schema/persistence descriptors once profile audit parity has fixtures for every generated section; keep actual profile writes in guarded shell paths. | Profile schema contract, ProfileSchemaStaticSmoke, module contract, profile audit parity, HelperShellBudgetPlanStaticSmoke, ModuleStaticGates, and current LocalReady. |
| 10 | `runtime_bridge_review` | `awaiting_live_approval` | All nine module lanes, runtime policy, dispatch guard, queue, readiness, action catalog, decision trace, sandbox handoff, ModuleAttachSmoke, and SmokeAttachAll are static-gated with fresh sandbox evidence. | Keep runtime passive through v2.1.1a; after explicit live promotion, open a separate bounded bridge review. | No runtime bridge until explicit PromoteLiveCtoa -ApproveLiveDeploy and a new reviewed action-specific plan. |

## Operator Sequence

1. Preserve the completed 9/9 sandbox evidence set for the current package.
2. Keep the new module as passive/read-only unless its gate explicitly allows runtime action.
3. Add profile keys, safe boot defaults, module registry entry, package copy, README note, static smoke, and release-gate evidence for every new module.
4. Promote a module from `contracted` to `static_gated` only after its dedicated static smoke is included in `ModuleStaticGates`.
5. Maintain the supplemental status-board lane (`ctoa_helper_module_status.lua`) so module readiness, blockers, and static-only modules remain visible before any runtime bridge work.
6. Maintain the supplemental action-catalog lane (`ctoa_helper_action_catalog.lua`) so future features declare action names, risk class, and required gates before any dispatcher can consume them.
7. Maintain the supplemental decision-trace lane (`ctoa_helper_decision_trace.lua`) so runtime policy and dispatch guard reasons are visible before any queued plan is reviewed.
8. Maintain the supplemental sandbox-handoff lane (`ctoa_helper_sandbox_handoff.lua`) so Launch, ReadyCheck, SmokeAttachModules, SmokeAttachAll, and PromoteLiveCtoa approval remain one explicit operator sequence.
9. Maintain the supplemental feature-flag lane (`ctoa_helper_feature_flags.lua`) so every future feature declares default disabled state, domain, and required gate before runtime code can consume it.
10. Only then consider runtime enablement, and only in sandbox first.
```


## `docs/otclient/ctoai_runtime_2_execution_plan.md`

```markdown
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
```


## `docs/otclient/solteria_helper_supplemental_refactor_plan.md`

```markdown
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
```


## `docs/otclient/solteria_helper_sandbox_smoke_queue.md`

```markdown
# Solteria Helper Sandbox Smoke Queue

## Decision

- Status: `passed`
- Helper version: `v2.0.0`
- Runtime status: `ready_for_readycheck`
- Release gate: `passed`
- Next action: Refresh local package and static gates
- Live safety: read-only plan; live promotion still requires `-ApproveLiveDeploy`.

## Queue

| Order | Step | Status | Command | Evidence | Reason |
|---:|---|---:|---|---|---|
| 1 | `local_ready` / Refresh local package and static gates | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action LocalReady` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\local_ready.json` | Local package, SmokePreflight, ModuleStaticGates, and GoalStatus should be current before attach. |
| 2 | `launch_sandbox` / Launch sandbox client and enter test character | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action Launch` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\smoke_status.json` | Run ReadyCheck, then SmokeAttachModules when the test character is in-world. |
| 3 | `ready_check` / Confirm helper is attached in-world | `required` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ReadyCheck` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\ready_check.json` | Run after the sandbox character is in-world; character-select screens are not enough. |
| 4 | `module_attach_group` / Capture grouped prototype module tab evidence | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachModules` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\module_attach_smoke.json` | Prototype module tabs need grouped in-world evidence. |
| 5 | `attach_heal_friend` / Attach module tab: heal_friend | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab heal_friend` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 6 | `attach_conditions` / Attach module tab: conditions | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab conditions` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 7 | `attach_equipment` / Attach module tab: equipment | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab equipment` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 8 | `attach_scripting` / Attach module tab: scripting | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab scripting` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 9 | `attach_hud` / Attach module tab: hud | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_hud` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 10 | `attach_route` / Attach module tab: route | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 11 | `attach_targeting` / Attach module tab: targeting | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 12 | `attach_combat_runtime` / Attach module tab: combat_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab hunting_magic` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 13 | `attach_cavebot_runtime` / Attach module tab: cavebot_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab cavebot` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 14 | `attach_loot_runtime` / Attach module tab: loot_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_diag` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 15 | `attach_timer_runtime` / Attach module tab: timer_runtime | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttach -Tab tools_timer` | `runtime\solteria_helper_dev\module_attach_smoke.json` | Static gate is passed; in-world tab evidence is still required. |
| 16 | `smoke_attach_all` / Capture full in-world helper acceptance | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action SmokeAttachAll` | `C:\Users\zycie\CTOAi\runtime\otclient_ui_preview\solteria-helper-smokeall-inworld-20260711-0131.json` | Fresh full attach report is required for the current manifest. |
| 17 | `promote_live_approval` / Promote only after explicit live approval | `passed` | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport <fresh-smokeattachall-json>` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\live_promotion.json` | Live promotion remains gated by explicit approval. |

## Static-Only Modules

| Module | Status | Evidence | Reason |
|---|---:|---|---|
| `planner` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\planner_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `runtime_policy` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\runtime_policy_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `dispatch_guard` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\dispatch_guard_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `plan_queue` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\plan_queue_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `runtime_readiness` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\runtime_readiness_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `module_status` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\module_status_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `action_catalog` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\action_catalog_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `decision_trace` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\decision_trace_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `sandbox_handoff` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\sandbox_handoff_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `feature_flags` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\feature_flags_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `hotkeys` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\hotkeys_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `modal` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\modal_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `input_contracts` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\input_contract_fixtures.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `profile_schema` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\profile_schema_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `operator_summary` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\operator_summary_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `external_bot_import_gate` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\external_bot_import_gate_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `helper_shell_budget` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\helper_shell_budget_static_smoke.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |
| `helper_shell_budget_plan` | `passed` | `C:\Users\zycie\CTOAi\runtime\solteria_helper_dev\helper_shell_budget_plan.json` | No dedicated UI tab; covered by static gate report and grouped module attach context. |

## Operator Rule

Run this queue from top to bottom. If any attach step reports character-select, offline helper, stale manifest, or failed screenshot evidence, stop and refresh `LocalReady` before continuing.
```


## `docs/otclient/zerobot_reference.md`

```markdown
# ZeroBot / ZeroLauncher Reference

## Purpose

This note captures what is actually useful from the local `ZeroLauncher` package for CTOAi OTClient work.

Source inspected:

- `C:\Users\zycie\Downloads\ZeroLauncher (1).zip`
- `C:\Users\zycie\Downloads\ZeroLauncher`
- `C:\Users\zycie\Downloads\ZeroLauncher\data\core.zip`

This is not product documentation. It is a binary launcher package with a Lua runtime layer and client patch metadata.

## What The Package Contains

Top-level package contents:

- `ZeroBot.exe`
- `ZeroBotLauncher.exe`
- `ZeroBotLauncher64.exe`
- `data/core.zip`
- `data/sounds.zip`
- `data/ZeroBot-*.dll`
- `versions.txt`
- `patch_addresses.txt`
- `version_addresses.txt`

Practical reading:

- the package is useful for behavior and API patterns
- the package is not useful as a clean visual reference for the current helper panel
- the package does not provide a ready-made OTClient UI skin we should copy

## Lua Runtime Inventory

The main technical value sits in `data/core.zip`.

Relevant files:

- `hud.lua`
- `custom_modal_window.lua`
- `hotkeymanager.lua`
- `game.lua`
- `player.lua`
- `inventory.lua`
- `map.lua`
- `spells.lua`
- `cavebot.lua`
- `engine.lua`

These files describe the wrapper layer ZeroBot exposes to scripts.

## Useful Capabilities To Reuse Conceptually

### HUD wrapper

`hud.lua` exposes a structured HUD object with:

- creation of text, item, spell-icon, and outfit HUD nodes
- explicit `setPos`, `show`, `hide`, `setDraggable`
- visual controls such as `setColor`, `setFontSize`, `setScale`, `setOpacity`, `setZIndex`
- click callbacks with `setCallback`

Why this matters for CTOAi:

- our helper already has HUD behavior, but the ZeroBot wrapper is cleaner as an API surface
- it suggests separating panel UI from overlay HUD concerns
- it confirms that HUD state should be treated as a first-class subsystem, not just a couple of booleans in a larger panel

### Custom modal wrapper

`custom_modal_window.lua` exposes:

- modal creation
- caption and description setters
- button creation
- click callback registration
- explicit destroy lifecycle

Why this matters for CTOAi:

- confirms a good pattern for confirmation UI
- useful later if we want profile import/export confirmation, reset actions, or runtime warnings
- this is a logic/API reference, not a visual reference

### Hotkey parsing

`hotkeymanager.lua` exposes:

- string-to-keycode mapping
- parsing for combinations like `Ctrl+H`
- a normalization point for keyboard modifiers

Why this matters for CTOAi:

- our helper already binds hotkeys, but this file is a good reference if we later want stricter parsing or validation
- it suggests keeping hotkey parsing isolated from panel layout logic

### Runtime domain modules

The package also has focused runtime modules such as:

- player state
- map access
- inventory access
- cavebot orchestration
- spell helpers

Why this matters for CTOAi:

- these files are useful for capability mapping and naming conventions
- they are not a reason to change the current helper UI layout directly

## What Is Not Worth Copying

Do not copy from ZeroLauncher:

- launcher aesthetics inferred from the binaries
- old-school bot UX conventions with dense technical labeling everywhere
- modal-heavy workflows as the default interaction model
- version patch tables and address metadata
- opaque monolithic wrappers without a clean separation between domain state and presentation

## Direct Comparison With Current CTOAi Helper

Current CTOAi helper implementation:

- [ctoa_native_helper.lua](../../scripts/lua/otclient/ctoa_native_helper.lua)

Current CTOAi helper strengths:

- runtime/profile/UI prefs are already separated conceptually
- helper supports profile save/load and UI prefs persistence
- helper has explicit sections for healing, tools, profile, and UI
- helper already exposes HUD toggles and window placement

Current CTOAi helper weaknesses:

- layout is widget-heavy and visually noisy
- too many bordered boxes compete for attention
- labels, values, and controls do not produce a clear visual hierarchy
- the panel reads like a debug tool rather than a polished in-client operator surface

## Recommended Use Of ZeroLauncher Material

Use ZeroLauncher as:

- an API reference
- a behavior reference
- a capability checklist

Do not use ZeroLauncher as:

- the visual blueprint for the helper panel
- the design language for spacing, typography, or control composition

## Actionable Follow-Up

The right next step is not reverse-engineering more binaries. The right next step is rebuilding the helper panel around a quieter information architecture.

Companion design note:

- [helper_redesign.md](helper_redesign.md)
```


## `docs/otclient/vbot_import_review.md`

```markdown
# vBot Import Review

## Decision

- Status: `source_required`.
- No vBot source tree or reviewed local archive is present in this checkout.
- Do not claim vBot-derived implementation until source provenance, license
  notes, secret scan, and module mapping are recorded here.
- External bot projects may be used as capability checklists and naming
  references only. Do not directly copy code into CTOAi helper modules without
  explicit source and license review.

## Intake Requirements

A valid vBot or vBot-like source handoff must include:

1. Source path or archive name.
2. Origin URL or owner-provided provenance note.
3. License text or explicit permission note.
4. SHA256 for the archive or source snapshot.
5. Secret scan result for tokens, accounts, server IPs, and local runtime state.
6. File inventory grouped by capability: healing, targeting, cavebot, looting,
   HUD, hotkeys, conditions, equipment, scripting, and diagnostics.
7. Risk notes for every runtime action path: movement, attack, spell cast, rune,
   item use, chat/talk, filesystem write, and profile migration.

Use the checked intake command before reviewing code manually:

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_external_bot_intake.py <source-path-or-zip> --origin "<origin-or-owner-note>" --license-note "<license-or-permission-note>"
```

The generated report is an intake gate, not an import approval. Any warnings
for movement, attack, spell cast, item use, keyboard binding, filesystem write,
or dynamic code still need mapping into passive CTOAi helper modules first.
The report must include `import_gate`, and `import_gate.runtime_import_allowed`
must stay `false` until the matching CTOAi module gates and sandbox evidence
prove the behavior.

## Import Gate Contract

The intake gate converts external bot findings into a CTOAi decision:

- `source_required`: no source was provided, so no import work can claim vBot
  behavior.
- `review_required`: source exists, but provenance, license, secret, or review
  blockers remain.
- `capability_mapping_only`: source can be reviewed as a checklist, but runtime
  import is still blocked.

`import_gate.direct_copy_allowed` is always `false`. Detected runtime actions
must appear in `runtime_gate_mapping` and point at existing CTOAi gates such as
`combat_runtime`, `cavebot_runtime`, `loot_runtime`, `hotkeys`,
`profile_schema`, or `scripting`.

## Mapping Policy

Map external bot behavior into existing CTOAi helper domains instead of adding
new runtime shortcuts:

| External capability | CTOAi target | Import rule |
|---|---|---|
| HUD text/overlay helpers | `ctoa_helper_hud.lua` | Keep passive text/position formatting only. |
| Hotkey parsing/manager | `ctoa_helper_hotkeys.lua` | Keep parser/display helpers only; binding stays in helper shell. |
| Confirmation modals | `ctoa_helper_modal.lua` | Keep request/expiry/status lifecycle only; execution stays guarded. |
| Cavebot route editor | `ctoa_helper_route.lua` | Keep waypoint labels and mutations only; `autoWalk` stays gated in helper shell. |
| Target selection/scoring | `ctoa_helper_targeting.lua` | Keep score and ignored-name rules only; `g_game.attack` stays guarded in helper shell. |
| Heal friend/sio | `ctoa_helper_heal_friend.lua` | Observer and whitelist first; no cast until sandbox whitelist smoke exists. |
| Conditions | `ctoa_helper_conditions.lua` | Read-only state observer first; no recovery action until condition smoke exists. |
| Equipment | `ctoa_helper_equipment.lua` | Read-only slot observer first; no item move/use until inventory smoke exists. |
| Scripting/macros | `ctoa_helper_scripting.lua` | Deny-all policy shell first; no eval/snippets without security review. |

## Required Evidence Before Import

Before any external logic changes runtime behavior:

1. Add or update a named helper module file.
2. Add package copy coverage in `scripts/windows/solteria_helper_test_env.ps1`.
3. Add static contracts in `tests/test_otclient_helper_zerobot_shell.py`.
4. Update `scripts/lua/otclient/README.md`.
5. Regenerate `docs/otclient/solteria_helper_next_modules_plan.md`.
6. Run `ValidateDev`, `SmokePreflight`, and `ModuleStaticGates`.
7. Run `SmokeAttachModules` and fresh `SmokeAttachAll` after sandbox character
   is in-world.
8. Keep `PromoteLiveCtoa` behind `-ApproveLiveDeploy`.

## Current Source Review

No vBot source is available in the repository as of this review. The current
safe basis is:

- `docs/otclient/zerobot_reference.md` as a local capability/API reference.
- CTOAi helper modules already extracted into passive domains.
- Runtime gates from `scripts/windows/solteria_helper_test_env.ps1`.

## Next Operator Step

If a vBot archive is provided, place it outside runtime client state, record its
path and hash here, run `scripts/ops/otclient_external_bot_intake.py`, then
review it as a capability checklist. Keep all imported behavior passive until
its matching CTOAi module gate and sandbox evidence pass.
```


## `scripts/ops/otclient_external_bot_intake.py`

```python
"""Inspect external OTClient bot sources before CTOAi helper import."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "runtime" / "solteria_helper_dev" / "external_bot_intake.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "otclient" / "vbot_import_intake.md"

TEXT_SUFFIXES = {
    ".lua",
    ".otui",
    ".otmod",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".md",
    ".cfg",
    ".conf",
    ".ini",
}
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.txt", "notice", "notice.txt"}
MAX_SCAN_BYTES = 512_000

CAPABILITY_PATTERNS = {
    "healing": re.compile(r"\b(heal|sio|uh|mana|health|hp|mp)\b", re.IGNORECASE),
    "targeting": re.compile(r"\b(target|attack|monster|creature|priority)\b", re.IGNORECASE),
    "cavebot": re.compile(r"\b(cavebot|waypoint|walk|route|path|label)\b", re.IGNORECASE),
    "looting": re.compile(r"\b(loot|container|corpse|pickup)\b", re.IGNORECASE),
    "hud": re.compile(r"\b(hud|overlay|label|widget|panel)\b", re.IGNORECASE),
    "hotkeys": re.compile(r"\b(hotkey|bindKey|keyboard|shortcut)\b", re.IGNORECASE),
    "conditions": re.compile(r"\b(condition|haste|paralyze|poison|burn|curse)\b", re.IGNORECASE),
    "equipment": re.compile(r"\b(equip|slot|ring|amulet|weapon|armor)\b", re.IGNORECASE),
    "scripting": re.compile(r"\b(macro|script|eval|loadstring|scheduleEvent|cycleEvent)\b", re.IGNORECASE),
    "diagnostics": re.compile(r"\b(log|debug|trace|diagnostic|export)\b", re.IGNORECASE),
}

RUNTIME_ACTION_PATTERNS = {
    "movement": re.compile(r"\b(autoWalk|walk|findPath|goto|moveTo)\b"),
    "attack": re.compile(r"\b(g_game\.attack|attack\(|setTarget)\b"),
    "spell_cast": re.compile(r"\b(say|talk|cast|exori|exura|utani|utevo|exeta)\b", re.IGNORECASE),
    "rune_or_item_use": re.compile(r"\b(useInventoryItem|useWith|g_game\.use|useItem|useRune)\b"),
    "item_move": re.compile(r"\b(moveItem|g_game\.move|moveToParentContainer)\b"),
    "keyboard_binding": re.compile(r"\b(bindKey|g_keyboard|pressKey)\b"),
    "filesystem_write": re.compile(r"\b(io\.open|writefile|save|g_resources\.writeFileContents)\b"),
    "dynamic_code": re.compile(r"\b(loadstring|dofile|require|assert\(load)\b"),
}

SECRET_PATTERNS = {
    "token_like": re.compile(r"(?i)\b(token|secret|api[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "password_like": re.compile(r"(?i)\b(pass|password)\b\s*[:=]\s*['\"]?[^'\"\s]{6,}"),
    "bearer": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-.]{20,}"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

CAPABILITY_TARGETS = {
    "healing": "ctoa_helper_heal_friend.lua",
    "targeting": "ctoa_helper_targeting.lua",
    "cavebot": "ctoa_helper_route.lua",
    "looting": "ctoa_helper_loot_runtime.lua",
    "hud": "ctoa_helper_hud.lua",
    "hotkeys": "ctoa_helper_hotkeys.lua",
    "conditions": "ctoa_helper_conditions.lua",
    "equipment": "ctoa_helper_equipment.lua",
    "scripting": "ctoa_helper_scripting.lua",
    "diagnostics": "ctoa_helper_diagnostics.lua",
}

RUNTIME_ACTION_GATES = {
    "movement": "cavebot_runtime",
    "attack": "combat_runtime",
    "spell_cast": "combat_runtime",
    "rune_or_item_use": "combat_runtime",
    "item_move": "loot_runtime",
    "keyboard_binding": "hotkeys",
    "filesystem_write": "profile_schema",
    "dynamic_code": "scripting",
}


@dataclass(frozen=True)
class SourceFileReport:
    path: str
    bytes: int
    sha256: str
    capabilities: list[str]
    runtime_actions: list[str]
    secret_hits: list[str]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_limited(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_SCAN_BYTES + 1)


def _is_text_candidate(path: str) -> bool:
    return Path(path).suffix.lower() in TEXT_SUFFIXES or Path(path).name.lower() in LICENSE_NAMES


def _decode(data: bytes) -> str:
    return data[:MAX_SCAN_BYTES].decode("utf-8", errors="replace")


def _matches(patterns: dict[str, re.Pattern[str]], haystack: str) -> list[str]:
    return [name for name, pattern in patterns.items() if pattern.search(haystack)]


def _directory_snapshot_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = file_path.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _zip_text_entries(path: Path) -> Iterable[tuple[str, bytes]]:
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not _is_text_candidate(info.filename):
                continue
            with archive.open(info) as handle:
                yield info.filename, handle.read(MAX_SCAN_BYTES + 1)


def _directory_text_entries(path: Path) -> Iterable[tuple[str, bytes]]:
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        rel = file_path.relative_to(path).as_posix()
        if _is_text_candidate(rel):
            yield rel, _read_limited(file_path)


def _source_entries(path: Path) -> Iterable[tuple[str, bytes]]:
    if path.is_dir():
        return _directory_text_entries(path)
    if zipfile.is_zipfile(path):
        return _zip_text_entries(path)
    if _is_text_candidate(path.name):
        return [(path.name, _read_limited(path))]
    return []


def _source_sha256(path: Path) -> str:
    if path.is_dir():
        return _directory_snapshot_sha256(path)
    return _sha256_bytes(path.read_bytes())


def inspect_source_file(name: str, data: bytes) -> SourceFileReport:
    text = _decode(data)
    haystack = f"{name}\n{text}"
    return SourceFileReport(
        path=name,
        bytes=len(data),
        sha256=_sha256_bytes(data),
        capabilities=_matches(CAPABILITY_PATTERNS, haystack),
        runtime_actions=_matches(RUNTIME_ACTION_PATTERNS, haystack),
        secret_hits=_matches(SECRET_PATTERNS, haystack),
    )


def build_import_gate(report: dict) -> dict:
    """Convert intake findings into an explicit CTOAi import decision."""
    if report.get("status") == "source_missing":
        decision = "source_required"
    elif report.get("blockers"):
        decision = "review_required"
    else:
        decision = "capability_mapping_only"

    capability_mapping = {}
    for capability, paths in report.get("capability_inventory", {}).items():
        if paths:
            capability_mapping[capability] = {
                "target_module": CAPABILITY_TARGETS.get(capability, "manual_review_required"),
                "source_files": sorted(paths),
                "import_rule": "map concepts only; no direct code copy; runtime behavior remains gated",
            }

    runtime_gate_mapping = {}
    for action, paths in report.get("runtime_action_inventory", {}).items():
        if paths:
            runtime_gate_mapping[action] = {
                "required_gate": RUNTIME_ACTION_GATES.get(action, "manual_review_required"),
                "source_files": sorted(paths),
                "allowed_now": False,
            }

    blockers = list(report.get("blockers") or [])
    if decision == "capability_mapping_only" and runtime_gate_mapping:
        blockers.append("runtime actions detected; map as passive module plans before any execution path")

    return {
        "decision": decision,
        "runtime_import_allowed": False,
        "direct_copy_allowed": False,
        "capability_mapping": capability_mapping,
        "runtime_gate_mapping": runtime_gate_mapping,
        "blockers": blockers,
        "next_action": (
            "Provide vBot source with origin and license notes."
            if decision == "source_required"
            else "Resolve provenance, license, secret, and review blockers."
            if decision == "review_required"
            else "Map detected capabilities into CTOAi passive module contracts and sandbox gates."
        ),
    }


def build_report(source: Path, *, origin: str = "", license_note: str = "") -> dict:
    source = source.expanduser()
    generated_at = datetime.now().replace(microsecond=0).isoformat()
    if not source.exists():
        report = {
            "schema_version": 1,
            "generated_at": generated_at,
            "source": str(source),
            "status": "source_missing",
            "blockers": ["source path does not exist"],
            "warnings": [],
            "source_sha256": "",
            "origin": origin,
            "license_note": license_note,
            "files": [],
            "capability_inventory": {},
            "runtime_action_inventory": {},
            "secret_scan_status": "not_run",
        }
        report["import_gate"] = build_import_gate(report)
        return report

    files = [inspect_source_file(name, data) for name, data in _source_entries(source)]
    capability_inventory = {
        capability: sorted(report.path for report in files if capability in report.capabilities)
        for capability in CAPABILITY_PATTERNS
    }
    runtime_action_inventory = {
        action: sorted(report.path for report in files if action in report.runtime_actions)
        for action in RUNTIME_ACTION_PATTERNS
    }
    secret_files = sorted(report.path for report in files if report.secret_hits)
    license_files = sorted(report.path for report in files if Path(report.path).name.lower() in LICENSE_NAMES)

    blockers: list[str] = []
    warnings: list[str] = []
    if not origin:
        blockers.append("origin/provenance note missing")
    if not license_note and not license_files:
        blockers.append("license note or license file missing")
    if secret_files:
        blockers.append("secret-like values require review")
    if not files:
        blockers.append("no scan-compatible text files found")
    for action, action_files in runtime_action_inventory.items():
        if action_files:
            warnings.append(f"runtime action path detected: {action}")

    status = "ready_for_capability_mapping" if not blockers else "review_required"
    report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": str(source),
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "source_sha256": _source_sha256(source),
        "origin": origin,
        "license_note": license_note,
        "license_files": license_files,
        "files": [asdict(report) for report in files],
        "capability_inventory": capability_inventory,
        "runtime_action_inventory": runtime_action_inventory,
        "secret_scan_status": "needs_review" if secret_files else "passed",
        "secret_files": secret_files,
    }
    report["import_gate"] = build_import_gate(report)
    return report


def render_markdown(report: dict) -> str:
    lines = [
        "# External Bot Intake Report",
        "",
        "## Decision",
        "",
        f"- Status: `{report['status']}`",
        f"- Source: `{report['source']}`",
        f"- Source SHA256: `{report['source_sha256'] or 'missing'}`",
        f"- Secret scan: `{report['secret_scan_status']}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = report.get("blockers") or ["none"]
    lines.extend(f"- {item}" for item in blockers)
    lines.extend(["", "## Runtime Action Warnings", ""])
    warnings = report.get("warnings") or ["none"]
    lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "## Capability Inventory", ""])
    for capability, paths in report.get("capability_inventory", {}).items():
        value = ", ".join(paths[:20]) if paths else "none"
        suffix = " ..." if len(paths) > 20 else ""
        lines.append(f"- `{capability}`: {value}{suffix}")
    gate = report.get("import_gate", {})
    lines.extend(
        [
            "",
            "## CTOAi Import Gate",
            "",
            f"- Decision: `{gate.get('decision', 'unknown')}`",
            f"- Runtime import allowed: `{str(gate.get('runtime_import_allowed', False)).lower()}`",
            f"- Direct copy allowed: `{str(gate.get('direct_copy_allowed', False)).lower()}`",
            f"- Next action: {gate.get('next_action', 'Review source before import.')}",
            "",
            "## Runtime Gate Mapping",
            "",
        ]
    )
    runtime_gate_mapping = gate.get("runtime_gate_mapping") or {}
    if runtime_gate_mapping:
        for action, item in runtime_gate_mapping.items():
            lines.append(
                f"- `{action}` -> `{item['required_gate']}`: {', '.join(item['source_files'][:20])}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Import Rule", ""])
    lines.append(
        "Use this report as a capability checklist only. Runtime behavior must still be mapped into passive CTOAi helper modules and proven by sandbox smoke before live promotion."
    )
    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{id(text)}.tmp")
    try:
        tmp.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect external OTClient bot sources before helper import")
    parser.add_argument("source", type=Path)
    parser.add_argument("--origin", default="", help="Origin URL or owner-provided provenance note")
    parser.add_argument("--license-note", default="", help="License text reference or explicit permission note")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-out", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(args.source, origin=args.origin, license_note=args.license_note)
    write_text_atomic(args.json_out, json.dumps(report, indent=2))
    write_text_atomic(args.markdown_out, render_markdown(report))
    print(f"[otclient-external-bot-intake] JSON: {args.json_out}")
    print(f"[otclient-external-bot-intake] Markdown: {args.markdown_out}")
    print(f"[otclient-external-bot-intake] Status: {report['status']}")
    return 0 if report["status"] != "source_missing" else 2


if __name__ == "__main__":
    raise SystemExit(main())
```


## `scripts/ops/otclient_helper_module_contract.py`

```python
#!/usr/bin/env python3
"""Validate OTClient helper passive module contracts before sandbox attach."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OTCLIENT_DIR = ROOT / "scripts" / "lua" / "otclient"
DEFAULT_LOADER = OTCLIENT_DIR / "ctoa_otclient_loader.lua"
DEFAULT_REGISTRY = OTCLIENT_DIR / "ctoa_helper_modules.lua"
DEFAULT_JSON_OUT = ROOT / "runtime" / "solteria_helper_dev" / "module_contract.json"
DEFAULT_PLAN_OUT = ROOT / "docs" / "otclient" / "solteria_helper_module_contract.md"

PASSIVE_MODULES = [
    {
        "id": "modules",
        "loader_name": "ctoa_helper_modules",
        "file": "ctoa_helper_modules.lua",
        "global": "CTOA_HELPER_MODULES",
        "lane_id": "",
        "required_functions": [
            "getModuleLanes",
            "getShortLabels",
            "getSupportModules",
            "validateSupportModules",
            "bootSnapshot",
            "bootSummary",
            "laneEnabled",
            "laneRuntimeText",
            "registrySummary",
            "readinessTag",
            "readinessRow",
            "contract",
        ],
    },
    {
        "id": "domain_contract",
        "loader_name": "ctoa_helper_domain_contract",
        "file": "ctoa_helper_domain_contract.lua",
        "global": "CTOA_HELPER_DOMAIN_CONTRACT",
        "lane_id": "",
        "required_functions": [
            "schemaVersion",
            "lanes",
            "lane",
            "observationEnvelope",
            "planEnvelope",
            "summaryEnvelope",
            "validateEnvelope",
            "contract",
        ],
    },
    {
        "id": "ui",
        "loader_name": "ctoa_helper_ui",
        "file": "ctoa_helper_ui.lua",
        "global": "CTOA_HELPER_UI",
        "lane_id": "",
        "required_functions": [
            "shortText",
            "configureLayout",
            "fitText",
            "setWidgetText",
            "styleWidget",
            "setWidgetChecked",
            "getWidgetChecked",
            "showWidget",
            "createWidget",
            "styleTabState",
            "styleSubtabState",
            "styleMiniButton",
            "styleActionButton",
            "styleRuleCard",
            "styleMetricRow",
            "styleMetricLabel",
            "styleMetricValue",
            "styleSettingState",
            "styleProfileField",
            "styleVectorRow",
            "styleSectionBody",
            "styleTableHeader",
            "styleTableHeaderLabel",
            "styleFooterStrip",
            "styleFooterStripLabel",
            "styleSummaryStrip",
            "styleSummaryStripLabel",
            "styleSectionBandTitle",
            "styleSectionBandSubtitle",
            "styleSectionBandDivider",
            "stylePriorityBadge",
            "styleLabel",
            "styleWindowRoot",
            "styleWindowFrame",
            "styleWindowTitleLabel",
            "styleToggleButton",
            "styleCheckBox",
            "styleSidebarCard",
            "styleOverviewAvatarFrame",
            "styleOverviewAvatar",
            "styleOverviewAvatarName",
            "styleOverviewHpBar",
            "styleOverviewEquipSlot",
            "styleControlName",
            "settingRowGeometry",
            "metricCardGeometry",
            "metricTextPlan",
            "profileFieldGeometry",
            "vectorStepGeometry",
            "addSettingRow",
            "addToggleSettingRow",
            "addProfileCycleRow",
            "addProfileStepRow",
            "addVectorStepRow",
            "sectionBodyGeometry",
            "sidebarTabs",
            "huntingSubtabs",
            "subtabContentY",
            "toolsSubtabs",
            "toolsTableHeaders",
            "cavebotDelayChoices",
            "cavebotReachChoices",
            "msText",
            "cavebotActionSpecs",
            "refreshOperatorSummaries",
            "renderConditionsPanel",
            "renderEquipmentPanel",
            "renderCavebotPanel",
            "renderEnginePanel",
            "renderHealingPanel",
            "renderHealFriendPanel",
            "renderHuntingPanel",
            "renderProfilePanel",
            "renderScriptingPanel",
            "renderToolsPanel",
            "contract",
        ],
    },
    {
        "id": "diagnostics",
        "loader_name": "ctoa_helper_diagnostics",
        "file": "ctoa_helper_diagnostics.lua",
        "global": "CTOA_HELPER_DIAGNOSTICS",
        "lane_id": "",
        "required_functions": [
            "boolText",
            "posText",
            "hasApi",
            "apiText",
            "valueText",
            "apiSnapshotText",
            "apiProbeSnapshot",
            "apiProbeText",
            "magicApiProbeText",
            "featureFlagsText",
            "bufferText",
            "movementText",
            "magicLootText",
            "tableCount",
            "firstTableValue",
            "parseSmokeCommandText",
            "smokeCommandTarget",
            "smokeTabStatusText",
            "smokeCommandStatusText",
            "recordSnapshot",
            "exportBuffer",
            "contract",
        ],
    },
    {
        "id": "hotkeys",
        "loader_name": "ctoa_helper_hotkeys",
        "file": "ctoa_helper_hotkeys.lua",
        "global": "CTOA_HELPER_HOTKEYS",
        "lane_id": "",
        "required_functions": ["normalizeKeyName", "parse", "normalize", "isAllowed", "bindingDecision", "display", "contract"],
    },
    {
        "id": "modal",
        "loader_name": "ctoa_helper_modal",
        "file": "ctoa_helper_modal.lua",
        "global": "CTOA_HELPER_MODAL",
        "lane_id": "",
        "required_functions": ["request", "confirm", "cancel", "isExpired", "decision", "decisionText", "contract"],
    },
    {
        "id": "route",
        "loader_name": "ctoa_helper_route",
        "file": "ctoa_helper_route.lua",
        "global": "CTOA_HELPER_ROUTE",
        "lane_id": "",
        "required_functions": ["position", "label", "add", "clear", "select", "delete", "move", "editorAction", "retryBlocked", "progress", "activeTarget", "selectedSummary", "stats", "uiState", "deleteRequest", "contract"],
    },
    {
        "id": "targeting",
        "loader_name": "ctoa_helper_targeting",
        "file": "ctoa_helper_targeting.lua",
        "global": "CTOA_HELPER_TARGETING",
        "lane_id": "",
        "required_functions": ["normalizedName", "isIgnoredName", "hasBlockingNpcIcon", "creatureTypeDecision", "priorityRank", "scoreCandidate", "bestCandidate", "decision", "summary", "configSummary", "contract"],
    },
    {
        "id": "combat_runtime",
        "loader_name": "ctoa_helper_combat_runtime",
        "file": "ctoa_helper_combat_runtime.lua",
        "global": "CTOA_HELPER_COMBAT_RUNTIME",
        "lane_id": "",
        "required_functions": ["plan", "summary", "adapterSummary", "magicSummary", "msLeftText", "runeReady", "rotationSpellRows", "spellReadiness", "rotationSpell", "offensiveAction", "actionStatusText", "targetingStatusText", "nextActionText", "waitReason", "decisionState", "contract"],
    },
    {
        "id": "cavebot_runtime",
        "loader_name": "ctoa_helper_cavebot_runtime",
        "file": "ctoa_helper_cavebot_runtime.lua",
        "global": "CTOA_HELPER_CAVEBOT_RUNTIME",
        "lane_id": "",
        "required_functions": [
            "plan",
            "summary",
            "decisionText",
            "adapterSummary",
            "adapterStatusText",
            "movementCapability",
            "probeSnapshot",
            "probeSummary",
            "probeReport",
            "pathText",
            "movementBlockedReason",
            "walkPreflight",
            "testWalkPlan",
            "walkingStatus",
            "retryDecision",
            "statusText",
            "traceText",
            "contract",
        ],
    },
    {
        "id": "loot_runtime",
        "loader_name": "ctoa_helper_loot_runtime",
        "file": "ctoa_helper_loot_runtime.lua",
        "global": "CTOA_HELPER_LOOT_RUNTIME",
        "lane_id": "",
        "required_functions": ["plan", "summary", "adapterSummary", "contract"],
    },
    {
        "id": "timer_runtime",
        "loader_name": "ctoa_helper_timer_runtime",
        "file": "ctoa_helper_timer_runtime.lua",
        "global": "CTOA_HELPER_TIMER_RUNTIME",
        "lane_id": "",
        "required_functions": ["plan", "summary", "dispatch", "contract"],
    },
    {
        "id": "recovery_runtime",
        "loader_name": "ctoa_helper_recovery_runtime",
        "file": "ctoa_helper_recovery_runtime.lua",
        "global": "CTOA_HELPER_RECOVERY_RUNTIME",
        "lane_id": "",
        "required_functions": ["normalizeVitals", "selectHealingSpell", "potionStatusText", "spellStatusText", "actionGap", "summary", "contract"],
    },
    {
        "id": "profile_schema",
        "loader_name": "ctoa_helper_profile_schema",
        "file": "ctoa_helper_profile_schema.lua",
        "global": "CTOA_HELPER_PROFILE_SCHEMA",
        "lane_id": "",
        "required_functions": [
            "requiredSections",
            "sectionOrder",
            "safeFalseKeys",
            "optionList",
            "rotationPresets",
            "keyOrder",
            "valueIndex",
            "cycleValue",
            "fieldGeometry",
            "stepValue",
            "currentVersion",
            "currentSchema",
            "profileVersion",
            "migrationPlan",
            "migrate",
            "summary",
            "profileSchemaSuffix",
            "rotationPresetIds",
            "rotationPresetLabel",
            "rotationSummary",
            "spellLabel",
            "potionLabel",
            "runeLabel",
            "healFriendPriorityLabel",
            "magicPriorityLabel",
            "themePresetLabel",
            "onOffLabel",
            "autosaveLabel",
            "titleSummary",
            "healingSummary",
            "profileSummary",
            "contract",
        ],
    },
    {
        "id": "profile_persistence",
        "loader_name": "ctoa_helper_profile_persistence",
        "file": "ctoa_helper_profile_persistence.lua",
        "global": "CTOA_HELPER_PROFILE_PERSISTENCE",
        "lane_id": "",
        "required_functions": [
            "profileCandidates",
            "uiPrefsCandidates",
            "saveDefaults",
            "resolveSavePath",
            "fallbackSavePath",
            "saveText",
            "loadSuccessText",
            "loadFailureText",
            "dirtyState",
            "exportProfile",
            "contract",
        ],
    },
    {
        "id": "operator_summary",
        "loader_name": "ctoa_helper_operator_summary",
        "file": "ctoa_helper_operator_summary.lua",
        "global": "CTOA_HELPER_OPERATOR_SUMMARY",
        "lane_id": "",
        "required_functions": [
            "title",
            "healing",
            "healFriend",
            "conditions",
            "equipment",
            "scripting",
            "targeting",
            "magic",
            "tools",
            "profile",
            "ui",
            "bridgeText",
            "contract",
        ],
    },
    {
        "id": "planner",
        "loader_name": "ctoa_helper_planner",
        "file": "ctoa_helper_planner.lua",
        "global": "CTOA_HELPER_PLANNER",
        "lane_id": "",
        "required_functions": ["collect", "best", "summary", "summaryEnvelope", "contract"],
    },
    {
        "id": "runtime_policy",
        "loader_name": "ctoa_helper_runtime_policy",
        "file": "ctoa_helper_runtime_policy.lua",
        "global": "CTOA_HELPER_RUNTIME_POLICY",
        "lane_id": "",
        "required_functions": ["requiredGates", "protectionZonePolicy", "resolvedProtectionZonePolicy", "protectionZoneDecision", "snapshot", "decision", "summary", "contract"],
    },
    {
        "id": "dispatch_guard",
        "loader_name": "ctoa_helper_dispatch_guard",
        "file": "ctoa_helper_dispatch_guard.lua",
        "global": "CTOA_HELPER_DISPATCH_GUARD",
        "lane_id": "",
        "required_functions": ["classify", "decision", "summary", "contract"],
    },
    {
        "id": "plan_queue",
        "loader_name": "ctoa_helper_plan_queue",
        "file": "ctoa_helper_plan_queue.lua",
        "global": "CTOA_HELPER_PLAN_QUEUE",
        "lane_id": "",
        "required_functions": ["normalize", "enqueue", "trim", "summary", "contract"],
    },
    {
        "id": "runtime_readiness",
        "loader_name": "ctoa_helper_runtime_readiness",
        "file": "ctoa_helper_runtime_readiness.lua",
        "global": "CTOA_HELPER_RUNTIME_READINESS",
        "lane_id": "",
        "required_functions": ["requiredComponents", "requiredGates", "snapshot", "decision", "summary", "contract"],
    },
    {
        "id": "module_status",
        "loader_name": "ctoa_helper_module_status",
        "file": "ctoa_helper_module_status.lua",
        "global": "CTOA_HELPER_MODULE_STATUS",
        "lane_id": "",
        "required_functions": ["defaultOrder", "normalize", "snapshot", "summary", "contract"],
    },
    {
        "id": "action_catalog",
        "loader_name": "ctoa_helper_action_catalog",
        "file": "ctoa_helper_action_catalog.lua",
        "global": "CTOA_HELPER_ACTION_CATALOG",
        "lane_id": "",
        "required_functions": ["requiredGates", "all", "domains", "byAction", "classify", "summary", "contract"],
    },
    {
        "id": "decision_trace",
        "loader_name": "ctoa_helper_decision_trace",
        "file": "ctoa_helper_decision_trace.lua",
        "global": "CTOA_HELPER_DECISION_TRACE",
        "lane_id": "",
        "required_functions": ["record", "queue", "summary", "contract"],
    },
    {
        "id": "decision_pipeline",
        "loader_name": "ctoa_helper_decision_pipeline",
        "file": "ctoa_helper_decision_pipeline.lua",
        "global": "CTOA_HELPER_DECISION_PIPELINE",
        "lane_id": "",
        "required_functions": ["components", "evaluate", "summary", "blockers", "contract"],
    },
    {
        "id": "sandbox_handoff",
        "loader_name": "ctoa_helper_sandbox_handoff",
        "file": "ctoa_helper_sandbox_handoff.lua",
        "global": "CTOA_HELPER_SANDBOX_HANDOFF",
        "lane_id": "",
        "required_functions": ["steps", "snapshot", "next", "summary", "contract"],
    },
    {
        "id": "feature_flags",
        "loader_name": "ctoa_helper_feature_flags",
        "file": "ctoa_helper_feature_flags.lua",
        "global": "CTOA_HELPER_FEATURE_FLAGS",
        "lane_id": "",
        "required_functions": ["all", "safeFalseKeys", "byKey", "audit", "summary", "toolsSummary", "contract"],
    },
    {
        "id": "hud",
        "loader_name": "ctoa_helper_hud",
        "file": "ctoa_helper_hud.lua",
        "global": "CTOA_HELPER_HUD",
        "lane_id": "",
        "required_functions": [
            "startText",
            "disarmedText",
            "position",
            "state",
            "visibilityText",
            "runtimeText",
            "uiSummary",
            "operatorSummary",
            "contract",
        ],
    },
    {
        "id": "conditions",
        "loader_name": "ctoa_helper_conditions",
        "file": "ctoa_helper_conditions.lua",
        "global": "CTOA_HELPER_CONDITIONS",
        "lane_id": "conditions",
        "required_functions": ["flagText", "snapshot", "apiProbe", "observe", "plan", "summary", "contract"],
    },
    {
        "id": "equipment",
        "loader_name": "ctoa_helper_equipment",
        "file": "ctoa_helper_equipment.lua",
        "global": "CTOA_HELPER_EQUIPMENT",
        "lane_id": "equipment",
        "required_functions": ["slotText", "snapshot", "apiProbe", "observe", "plan", "summary", "contract"],
    },
    {
        "id": "scripting",
        "loader_name": "ctoa_helper_scripting",
        "file": "ctoa_helper_scripting.lua",
        "global": "CTOA_HELPER_SCRIPTING",
        "lane_id": "scripting",
        "required_functions": ["policySnapshot", "plan", "summary", "contract"],
    },
    {
        "id": "heal_friend",
        "loader_name": "ctoa_helper_heal_friend",
        "file": "ctoa_helper_heal_friend.lua",
        "global": "CTOA_HELPER_HEAL_FRIEND",
        "lane_id": "heal_friend",
        "required_functions": ["whitelistContainsName", "scan", "observe", "plan", "statusText", "decisionText", "summary", "contract"],
    },
]

FORBIDDEN_PASSIVE_PATTERNS = {
    "spell_cast": re.compile(r"\bcastSpell\s*\(|\bg_game\.talk\s*\(|\bsay\s*\("),
    "item_use": re.compile(
        r"\bg_game\.use(?:InventoryItem|InventoryItemWith)?\s*\(|\buseWith\s*\("
    ),
    "movement": re.compile(r"\bautoWalk\s*\(|\bg_game\.walk\s*\("),
    "snippet_eval": re.compile(r"\bloadstring\s*\(|\bload\s*\(|\bdofile\s*\("),
}

REQUIRED_LANES = {
    "healing",
    "combat",
    "cavebot",
    "loot",
    "timer",
    "heal_friend",
    "conditions",
    "equipment",
    "scripting",
}


@dataclass(frozen=True)
class ModuleContractItem:
    id: str
    file: str
    status: str
    loader_present: bool
    registry_present: bool
    global_present: bool
    return_present: bool
    missing_functions: list[str]
    forbidden_hits: list[str]


@dataclass(frozen=True)
class ModuleContractReport:
    name: str
    created_at: str
    status: str
    loader_path: str
    registry_path: str
    expected_module_count: int
    check_count: int
    passed_count: int
    failed_count: int
    registry_lane_count: int
    registry_missing: list[str]
    loader_missing: list[str]
    forbidden_count: int
    modules: list[ModuleContractItem]
    next_action: str
    live_safety: str


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def parse_loader_modules(loader_text: str) -> dict[str, str]:
    return {
        match.group("name"): match.group("file")
        for match in re.finditer(
            r'\{name\s*=\s*"(?P<name>[^"]+)",\s*file\s*=\s*"(?P<file>[^"]+)"[^}]*\}',
            loader_text,
        )
    }


def parse_registry_lanes(registry_text: str) -> set[str]:
    return set(re.findall(r'id\s*=\s*"([^"]+)"', registry_text))


def forbidden_hits(source: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in FORBIDDEN_PASSIVE_PATTERNS.items():
        if pattern.search(source):
            hits.append(name)
    return hits


def missing_functions(source: str, module_global: str, required: list[str]) -> list[str]:
    local_name = module_global.removeprefix("CTOA_HELPER_").title().replace("_", "")
    if module_global == "CTOA_HELPER_MODULES":
        local_name = "Registry"
    return [
        function_name
        for function_name in required
        if f"function {local_name}.{function_name}" not in source
    ]


def build_report(
    otclient_dir: Path = OTCLIENT_DIR,
    loader_path: Path = DEFAULT_LOADER,
    registry_path: Path = DEFAULT_REGISTRY,
) -> ModuleContractReport:
    loader_text = loader_path.read_text(encoding="utf-8")
    registry_text = registry_path.read_text(encoding="utf-8")
    # The loader owns the registry bootstrap; the registry owns the ordered
    # support-module graph. Validate both sources as one boot contract.
    loader_modules = parse_loader_modules(loader_text + "\n" + registry_text)
    registry_lanes = parse_registry_lanes(registry_text)
    registry_missing = sorted(REQUIRED_LANES - registry_lanes)
    modules: list[ModuleContractItem] = []

    for expected in PASSIVE_MODULES:
        source_path = otclient_dir / str(expected["file"])
        source = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
        loader_present = loader_modules.get(str(expected["loader_name"])) == expected["file"]
        lane_id = str(expected["lane_id"])
        registry_present = not lane_id or lane_id in registry_lanes
        global_name = str(expected["global"])
        global_present = (
            f'rawget(_G, "{global_name}")' in source
            and f"_G.{global_name}" in source
        )
        return_present = f"return {global_name.removeprefix('CTOA_HELPER_').title().replace('_', '')}" in source
        if expected["id"] == "modules":
            return_present = "return Registry" in source
        forbidden = forbidden_hits(source)
        missing_required = missing_functions(
            source,
            global_name,
            [str(item) for item in expected.get("required_functions", [])],
        )
        status = (
            "passed"
            if source_path.is_file()
            and loader_present
            and registry_present
            and global_present
            and return_present
            and not missing_required
            and not forbidden
            else "failed"
        )
        modules.append(
            ModuleContractItem(
                id=str(expected["id"]),
                file=str(expected["file"]),
                status=status,
                loader_present=loader_present,
                registry_present=registry_present,
                global_present=global_present,
                return_present=return_present,
                missing_functions=missing_required,
                forbidden_hits=forbidden,
            )
        )

    failed = [item for item in modules if item.status != "passed"]
    loader_missing = sorted(
        str(item["loader_name"])
        for item in PASSIVE_MODULES
        if loader_modules.get(str(item["loader_name"])) != item["file"]
    )
    forbidden_count = sum(len(item.forbidden_hits) for item in modules)
    status = "passed" if not failed and not registry_missing else "failed"
    return ModuleContractReport(
        name="otclient-helper-module-contract",
        created_at=datetime.now().replace(microsecond=0).isoformat(),
        status=status,
        loader_path=str(loader_path),
        registry_path=str(registry_path),
        expected_module_count=len(PASSIVE_MODULES),
        check_count=len(PASSIVE_MODULES),
        passed_count=sum(1 for item in modules if item.status == "passed"),
        failed_count=len(failed),
        registry_lane_count=len(registry_lanes & REQUIRED_LANES),
        registry_missing=registry_missing,
        loader_missing=loader_missing,
        forbidden_count=forbidden_count,
        modules=modules,
        next_action=(
            "Run ModuleStaticGates, then sandbox SmokeAttachModules."
            if status == "passed"
            else "Fix loader, registry, passive globals, or forbidden passive module actions before sandbox attach."
        ),
        live_safety=(
            "ModuleContract is repo-only static analysis; it does not launch, stop, attach to, promote, or overwrite any client."
        ),
    )


def render_markdown(report: ModuleContractReport) -> str:
    lines = [
        "# Solteria Helper Module Contract",
        "",
        f"- Status: `{report.status}`",
        f"- Expected modules: `{report.expected_module_count}`",
        f"- Passed modules: `{report.passed_count}`",
        f"- Failed modules: `{report.failed_count}`",
        f"- Registry lanes: `{report.registry_lane_count}` / `{len(REQUIRED_LANES)}`",
        f"- Forbidden passive hits: `{report.forbidden_count}`",
        f"- Next action: {report.next_action}",
        "",
        "## Rule",
        "",
        "Passive helper modules may observe, format, plan, or expose UI state. They must not cast spells, use items, walk, execute snippets, or load arbitrary files. Runtime actions stay in the guarded native helper domains and still require sandbox evidence.",
        "",
        "## Modules",
        "",
        "| Module | File | Status | Loader | Registry | Global | Return | Missing functions | Forbidden |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in report.modules:
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | `{}` | {} | {} |".format(
                item.id,
                item.file,
                item.status,
                "yes" if item.loader_present else "no",
                "yes" if item.registry_present else "no",
                "yes" if item.global_present else "no",
                "yes" if item.return_present else "no",
                ", ".join(item.missing_functions) if item.missing_functions else "none",
                ", ".join(item.forbidden_hits) if item.forbidden_hits else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\ops\\otclient_helper_module_contract.py",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1 -Action ModuleStaticGates",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--otclient-dir", type=Path, default=OTCLIENT_DIR)
    parser.add_argument("--loader", type=Path, default=DEFAULT_LOADER)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN_OUT)
    parser.add_argument("--no-plan-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.otclient_dir.resolve(),
        args.loader.resolve(),
        args.registry.resolve(),
    )
    write_json_atomic(args.json_out.resolve(), asdict(report))
    if not args.no_plan_write:
        write_text_atomic(args.plan_out.resolve(), render_markdown(report))
    print(f"[otclient-helper-module-contract] JSON: {args.json_out}")
    if not args.no_plan_write:
        print(f"[otclient-helper-module-contract] Plan: {args.plan_out}")
    print(
        "[otclient-helper-module-contract] Status: "
        f"{report.status} ({report.passed_count}/{report.expected_module_count})"
    )
    return 0 if report.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```


## `scripts/ops/solteria_helper_sandbox_smoke_queue.py`

```python
"""Generate the sandbox smoke queue for the Solteria OTClient helper."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEV_DIR = ROOT / "runtime" / "solteria_helper_dev"
DEFAULT_JSON = DEV_DIR / "sandbox_smoke_queue.json"
DEFAULT_PLAN = ROOT / "docs" / "otclient" / "solteria_helper_sandbox_smoke_queue.md"
SMOKE_ENV_SCRIPT = ROOT / "scripts" / "windows" / "solteria_helper_test_env.ps1"
SMOKE_SCRIPT = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows\\solteria_helper_test_env.ps1"


@dataclass(frozen=True)
class SmokeQueueStep:
    order: int
    step_id: str
    label: str
    status: str
    command: str
    evidence: str
    reason: str


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_status(release_gate: dict[str, Any], name: str) -> tuple[str, str, str]:
    for gate in release_gate.get("gates", []):
        if gate.get("name") == name:
            return str(gate.get("status", "missing")), str(gate.get("evidence", "")), str(gate.get("reason", ""))
    return "missing", "", "gate not found"


def _fresh_status(status: str) -> str:
    if status == "passed":
        return "passed"
    if status in {"pending", "blocked", "missing"}:
        return "required"
    return status or "required"


def _valid_attach_tabs(script_path: Path = SMOKE_ENV_SCRIPT) -> set[str]:
    if not script_path.is_file():
        return set()
    source = script_path.read_text(encoding="utf-8")
    match = re.search(
        r'\[ValidateSet\((?P<values>"overview".*?)\)\]\s*\n\s*\[string\]\$Tab',
        source,
        flags=re.DOTALL,
    )
    if not match:
        return set()
    return set(re.findall(r'"([^"]+)"', match.group("values")))


def _attach_tab(command: str) -> str:
    match = re.search(r"(?:^|\s)-Tab\s+([A-Za-z0-9_]+)(?:\s|$)", command)
    return match.group(1) if match else ""


def _static_module_steps(
    goal_status: dict[str, Any],
    valid_tabs: set[str],
) -> tuple[list[SmokeQueueStep], list[dict[str, str]]]:
    module_audit = goal_status.get("module_audit") or {}
    summary = module_audit.get("static_gate_summary") or []
    steps: list[SmokeQueueStep] = []
    static_only: list[dict[str, str]] = []
    for item in summary:
        module = str(item.get("module", "")).strip()
        if not module:
            continue
        attach_command = str(item.get("attach_command") or "").strip()
        attach_tab = _attach_tab(attach_command)
        if not attach_command:
            static_only.append(
                {
                    "module": module,
                    "status": str(item.get("status", "unknown")),
                    "report_path": str(item.get("report_path", "")),
                    "reason": "No dedicated UI tab; covered by static gate report and grouped module attach context.",
                }
            )
            continue
        if attach_tab and attach_tab not in valid_tabs:
            static_only.append(
                {
                    "module": module,
                    "status": str(item.get("status", "unknown")),
                    "report_path": str(item.get("report_path", "")),
                    "reason": f"Invalid attach tab `{attach_tab}`; covered by static gate report and grouped module attach context.",
                }
            )
            continue
        steps.append(
            SmokeQueueStep(
                order=0,
                step_id=f"attach_{module}",
                label=f"Attach module tab: {module}",
                status="queued",
                command=attach_command,
                evidence="runtime\\solteria_helper_dev\\module_attach_smoke.json",
                reason=f"Static gate is {item.get('status', 'unknown')}; in-world tab evidence is still required.",
            )
        )
    return steps, static_only


def build_queue(dev_dir: Path = DEV_DIR) -> dict[str, Any]:
    manifest = read_json(dev_dir / "manifest.json")
    release_gate = read_json(dev_dir / "release_gate.json")
    smoke_status = read_json(dev_dir / "smoke_status.json")
    goal_status = read_json(dev_dir / "goal_status.json")

    preflight_status, preflight_evidence, preflight_reason = _gate_status(release_gate, "SmokePreflight")
    static_status, static_evidence, static_reason = _gate_status(release_gate, "ModuleStaticGates")
    module_attach_status, module_attach_evidence, module_attach_reason = _gate_status(release_gate, "ModuleAttachSmoke")
    smoke_all_status, smoke_all_evidence, smoke_all_reason = _gate_status(release_gate, "SmokeAttachAll")
    live_status, live_evidence, live_reason = _gate_status(release_gate, "live_approval")
    smoke_runtime_status = str(smoke_status.get("status", "missing"))

    steps = [
        SmokeQueueStep(
            1,
            "local_ready",
            "Refresh local package and static gates",
            "passed" if goal_status.get("status") in {"blocked", "passed"} and preflight_status == "passed" else "required",
            f"{SMOKE_SCRIPT} -Action LocalReady",
            str(dev_dir / "local_ready.json"),
            "Local package, SmokePreflight, ModuleStaticGates, and GoalStatus should be current before attach.",
        ),
        SmokeQueueStep(
            2,
            "launch_sandbox",
            "Launch sandbox client and enter test character",
            "required" if smoke_runtime_status != "running" else "passed",
            f"{SMOKE_SCRIPT} -Action Launch",
            str(dev_dir / "smoke_status.json"),
            str(smoke_status.get("next_action") or "Sandbox client must be running in-world before attach smoke."),
        ),
        SmokeQueueStep(
            3,
            "ready_check",
            "Confirm helper is attached in-world",
            "required" if smoke_runtime_status != "running" else "queued",
            f"{SMOKE_SCRIPT} -Action ReadyCheck",
            str(dev_dir / "ready_check.json"),
            "Run after the sandbox character is in-world; character-select screens are not enough.",
        ),
        SmokeQueueStep(
            4,
            "module_attach_group",
            "Capture grouped prototype module tab evidence",
            _fresh_status(module_attach_status),
            f"{SMOKE_SCRIPT} -Action SmokeAttachModules",
            module_attach_evidence,
            module_attach_reason or "Prototype module tabs need grouped in-world evidence.",
        ),
    ]

    module_steps, static_only_modules = _static_module_steps(goal_status, _valid_attach_tabs())
    for index, step in enumerate(module_steps, start=5):
        steps.append(
            SmokeQueueStep(
                index,
                step.step_id,
                step.label,
                step.status if module_attach_status != "passed" else "passed",
                step.command,
                step.evidence,
                step.reason,
            )
        )

    next_order = 5 + len(module_steps)
    steps.extend(
        [
            SmokeQueueStep(
                next_order,
                "smoke_attach_all",
                "Capture full in-world helper acceptance",
                _fresh_status(smoke_all_status),
                f"{SMOKE_SCRIPT} -Action SmokeAttachAll",
                smoke_all_evidence,
                smoke_all_reason or "Fresh full attach report is required for the current manifest.",
            ),
            SmokeQueueStep(
                next_order + 1,
                "promote_live_approval",
                "Promote only after explicit live approval",
                _fresh_status(live_status),
                f"{SMOKE_SCRIPT} -Action PromoteLiveCtoa -ApproveLiveDeploy -SmokeReport <fresh-smokeattachall-json>",
                live_evidence,
                live_reason or "Live promotion remains gated by explicit approval.",
            ),
        ]
    )

    queue_status = "ready_for_operator" if preflight_status == "passed" and static_status == "passed" else "refresh_required"
    if module_attach_status == "passed" and smoke_all_status == "passed" and live_status == "passed":
        queue_status = "passed"

    return {
        "schema_version": 1,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "status": queue_status,
        "helper_version": manifest.get("helper_version", ""),
        "manifest_created_at": manifest.get("created_at", ""),
        "runtime_status": smoke_runtime_status,
        "release_gate_status": release_gate.get("status", "missing"),
        "preflight_status": preflight_status,
        "module_static_gates_status": static_status,
        "module_attach_status": module_attach_status,
        "smoke_attach_all_status": smoke_all_status,
        "live_approval_status": live_status,
        "next_action": next((step.label for step in steps if step.status in {"required", "queued", "blocked"}), "none"),
        "steps": [asdict(step) for step in steps],
        "static_only_modules": static_only_modules,
        "live_safety": "This queue is read-only planning evidence; it does not launch, attach to, promote, stop, or overwrite any client.",
        "source_evidence": {
            "manifest": str(dev_dir / "manifest.json"),
            "release_gate": str(dev_dir / "release_gate.json"),
            "smoke_status": str(dev_dir / "smoke_status.json"),
            "goal_status": str(dev_dir / "goal_status.json"),
            "preflight": preflight_evidence,
            "static_gates": static_evidence or static_reason,
        },
    }


def render_markdown(queue: dict[str, Any]) -> str:
    lines = [
        "# Solteria Helper Sandbox Smoke Queue",
        "",
        "## Decision",
        "",
        f"- Status: `{queue['status']}`",
        f"- Helper version: `{queue['helper_version']}`",
        f"- Runtime status: `{queue['runtime_status']}`",
        f"- Release gate: `{queue['release_gate_status']}`",
        f"- Next action: {queue['next_action']}",
        "- Live safety: read-only plan; live promotion still requires `-ApproveLiveDeploy`.",
        "",
        "## Queue",
        "",
        "| Order | Step | Status | Command | Evidence | Reason |",
        "|---:|---|---:|---|---|---|",
    ]
    for step in queue["steps"]:
        lines.append(
            f"| {step['order']} | `{step['step_id']}` / {step['label']} | `{step['status']}` | `{step['command']}` | `{step['evidence']}` | {step['reason']} |"
        )
    static_only = queue.get("static_only_modules") or []
    if static_only:
        lines.extend(
            [
                "",
                "## Static-Only Modules",
                "",
                "| Module | Status | Evidence | Reason |",
                "|---|---:|---|---|",
            ]
        )
        for item in static_only:
            lines.append(
                f"| `{item['module']}` | `{item['status']}` | `{item['report_path']}` | {item['reason']} |"
            )
    lines.extend(
        [
            "",
            "## Operator Rule",
            "",
            "Run this queue from top to bottom. If any attach step reports character-select, offline helper, stale manifest, or failed screenshot evidence, stop and refresh `LocalReady` before continuing.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{id(text)}.tmp")
    try:
        tmp.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Solteria Helper sandbox smoke queue")
    parser.add_argument("--dev-dir", type=Path, default=DEV_DIR)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--plan-out", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()

    queue = build_queue(args.dev_dir.resolve())
    write_text_atomic(args.json_out, json.dumps(queue, indent=2))
    write_text_atomic(args.plan_out, render_markdown(queue))
    print(f"[solteria-helper-sandbox-smoke-queue] JSON: {args.json_out}")
    print(f"[solteria-helper-sandbox-smoke-queue] Plan: {args.plan_out}")
    print(f"[solteria-helper-sandbox-smoke-queue] Status: {queue['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```


## `scripts/lua/AGENTS.md`

```markdown
# Lua And OTClient Instructions

This folder contains standalone CTOAi Lua modules and the OTClient helper
package/source.

## Rules

- Keep standalone runtime scripts and OTClient-native scripts separate unless an
  adapter is explicitly added.
- For OTClient files, guard native globals such as `g_game`, `g_map`, `g_ui`,
  `g_keyboard`, `g_resources`, and `g_clock`.
- Preserve safe boot defaults. Do not enable combat, cavebot movement, rune
  casting, auto haste, exeta, timer, or healing during loader initialization.
- Use `connect(...)` for supported OTClient events and `cycleEvent` for bounded
  loops.
- Use `scheduleEvent` for delayed boot work; `addEvent` is only a fallback.
- Keep cooldowns, bounded retries, and explicit early exits in `onThink` logic.
- Preserve profile/UI key order when changing helper persistence.

## Validation

Run the narrowest available check:

```powershell
.\ctoa.ps1 brain refresh
.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_zerobot_shell.py tests\test_ctoa_helper_smoke_report.py -q
```

For manual OTClient UI changes, also load the helper in the client and verify
fresh `ctoa_local.log` lines plus safe boot state.
```


## `AI/generated/manifest.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-11T12:51:23+00:00",
  "root": "C:\\Users\\zycie\\CTOAi",
  "file_count": 1236,
  "outputs": {
    "file_tree": "AI\\generated\\FILE_TREE.md",
    "symbol_map": "AI\\generated\\SYMBOL_MAP.md",
    "ownership_map": "AI\\generated\\OWNERSHIP_MAP.md",
    "ownership_json": "AI\\generated\\OWNERSHIP_MAP.json",
    "doc_sync": "AI\\generated\\DOC_SYNC.md",
    "doc_sync_json": "AI\\generated\\DOC_SYNC.json",
    "secret_guardrail": "AI\\generated\\SECRET_GUARDRAIL.md",
    "secret_guardrail_json": "AI\\generated\\SECRET_GUARDRAIL.json",
    "p6_readiness": "AI\\generated\\P6_CODEX_INTEGRATION_READINESS.md",
    "p6_readiness_json": "AI\\generated\\P6_CODEX_INTEGRATION_READINESS.json",
    "p7_operator_workflow": "AI\\generated\\P7_OPERATOR_WORKFLOW.md",
    "p7_operator_workflow_json": "AI\\generated\\P7_OPERATOR_WORKFLOW.json",
    "p7_action_readiness": "AI\\generated\\P7_ACTION_READINESS.md",
    "p7_action_readiness_json": "AI\\generated\\P7_ACTION_READINESS.json",
    "p7_safe_write_tool_design": "AI\\generated\\P7_SAFE_WRITE_TOOL_DESIGN.md",
    "p7_safe_write_tool_design_json": "AI\\generated\\P7_SAFE_WRITE_TOOL_DESIGN.json",
    "p7_operator_brief": "AI\\generated\\P7_OPERATOR_BRIEF.md",
    "p7_operator_brief_json": "AI\\generated\\P7_OPERATOR_BRIEF.json"
  },
  "doc_sync_status": "passed",
  "secret_guardrail_status": "passed",
  "p6_readiness_status": "ready_for_plugin_design",
  "p7_operator_workflow_status": "safe_write_ready",
  "p7_action_readiness_status": "safe_write_tools_enabled",
  "p7_safe_write_tool_design_status": "implemented",
  "p7_operator_brief_status": "ready",
  "excluded_dirs": [
    ".git",
    ".hg",
    ".next",
    ".pytest_cache",
    ".svn",
    ".tmp",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "logs",
    "node_modules",
    "runtime"
  ],
  "excluded_file_patterns": [
    ".env-",
    ".env.",
    "credential",
    "password",
    "secret",
    "token"
  ]
}
```


## `AI/generated/ENV_DOCTOR.md`

```markdown
# Engine Brain Environment Doctor

Generated at: `2026-07-11T12:47:45+00:00`
Overall status: `warn`

| Check | Status | Key evidence |
|---|---|---|
| `git` | `ok` | branch=codex/post-merge-engine-brain-sync; dirty=25; path=C:\Program Files\Git\cmd\git.EXE |
| `docker` | `ok` | containers=2; running_broad=0; configured_broad=0 |
| `vpn` | `ok` | warp_connected=True |
| `vercel` | `ok` | version=54.10.3; project=ctoa-web |
| `vscode` | `warn` | openai=['openai.chatgpt@26.623.141536']; old_dirs=2 |
| `github` | `warn` | open_prs=6; dirty_prs=5; failed_runs=0 |
| `update_gate` | `ok` | gate=ok; product=CTOA Toolkit; version=1.1.1 |

## GitHub Dirty PRs

- `#184` [WIP] Fix CTOA VPS Global Save Cycle failure - https://github.com/famatyyk/CTOAi/pull/184
- `#160` test(copilot-instructions): expand conformance coverage to all seven sections - https://github.com/famatyyk/CTOAi/pull/160
- `#157` feat: add /analyze-prompt Copilot slash command - https://github.com/famatyyk/CTOAi/pull/157
- `#153` docs: add alternative LLM model recommendations to copilot instructions and .env.example - https://github.com/famatyyk/CTOAi/pull/153
- `#152` Enable workspace-level Python trace logging in VS Code - https://github.com/famatyyk/CTOAi/pull/152
```


## `AI/generated/OWNERSHIP_MAP.md`

```markdown
# Engine Brain Ownership Map

Generated at: `2026-07-11T12:51:23+00:00`
Source audit: `runtime\audits\ctoai-full-workspace-audit.json`
Status: `ready`

| Path | Owner | Validation gate | Files | Categories |
|---|---|---|---:|---|
| `.ctoa-local` | Local/uncategorized | `manual review` | 9 | runtime_or_local_state:9 |
| `.devcontainer` | Local/uncategorized | `manual review` | 2 | tracked_source:2 |
| `.dockerignore` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.env.example` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.foundry` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.git` | Local/uncategorized | `manual review` | 792 | git_internal:792 |
| `.gitattributes` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.github` | Local/uncategorized | `manual review` | 41 | tracked_source:41 |
| `.gitignore` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.gitmodules` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.luarc.json` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.pre-commit-config.yaml` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `.pytest_cache` | Local/uncategorized | `manual review` | 5 | vendor_or_cache:5 |
| `.ruff_cache` | Local/uncategorized | `manual review` | 17 | untracked_local:17 |
| `.tmp` | Local/uncategorized | `manual review` | 105 | runtime_or_local_state:105 |
| `.venv` | Local/uncategorized | `manual review` | 4543 | vendor_or_cache:4543 |
| `.vscode` | Local/uncategorized | `manual review` | 4 | tracked_source:4 |
| `AGENTS.md` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `AI` | Engine Brain | `brain refresh; brain pack` | 45 | tracked_source:45 |
| `CHANGELOG.md` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `Dockerfile` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `Dockerfile.api` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `Dockerfile.bot` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `README.md` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `__pycache__` | Local/uncategorized | `manual review` | 4 | vendor_or_cache:4 |
| `_local_archive` | Local/uncategorized | `manual review` | 111 | runtime_or_local_state:111 |
| `agent.yaml` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `agents` | Agent governance | `pytest tests/ --ignore=tests/e2e` | 32 | tracked_source:30, untracked_source_candidate:2 |
| `alembic` | Local/uncategorized | `manual review` | 6 | tracked_source:4, untracked_local:2 |
| `alembic.ini` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `api` | API runtime | `pytest tests/ --ignore=tests/e2e` | 9 | tracked_source:3, untracked_source_candidate:6 |
| `bot` | Bot runtime | `pytest tests/ --ignore=tests/e2e` | 144 | tracked_source:43, untracked_source_candidate:101 |
| `config` | Local/uncategorized | `manual review` | 6 | local_secret_or_sensitive:1, tracked_source:5 |
| `conftest.py` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `core` | Local/uncategorized | `manual review` | 3 | tracked_source:3 |
| `ctoa-vps.ps1` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `ctoa.ps1` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `ctoa_local.log` | Local/uncategorized | `manual review` | 1 | untracked_local:1 |
| `ctoa_ui_prefs.lua` | Local/uncategorized | `manual review` | 1 | untracked_local:1 |
| `data` | Local/uncategorized | `manual review` | 5 | runtime_or_local_state:5 |
| `deploy` | VPS/deploy | `engine_brain_doctor; deployment smoke` | 43 | tracked_source:43 |
| `desktop_console` | Local/uncategorized | `manual review` | 16 | tracked_source:6, untracked_source_candidate:10 |
| `docker` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `docker-compose.yml` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `docs` | Documentation | `doc sync guard` | 313 | tracked_source:307, untracked_source_candidate:6 |
| `evals` | Local/uncategorized | `manual review` | 6 | tracked_source:6 |
| `logs` | Local/uncategorized | `manual review` | 3 | runtime_or_local_state:3 |
| `metrics` | Local/uncategorized | `manual review` | 4 | runtime_or_local_state:4 |
| `mobile_console` | Mobile console | `pytest tests/ --ignore=tests/e2e` | 20 | tracked_source:9, untracked_source_candidate:11 |
| `node_modules` | Local/uncategorized | `manual review` | 1 | vendor_or_cache:1 |
| `policies` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `product` | Local/uncategorized | `manual review` | 4 | tracked_source:4 |
| `prompts` | Local/uncategorized | `manual review` | 6 | tracked_source:4, untracked_source_candidate:2 |
| `releases` | Release evidence | `release_evidence_pack.py` | 36 | tracked_source:36 |
| `requirements-bot.txt` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `requirements-dev.txt` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `requirements.txt` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `runner` | Runner runtime | `pytest tests/ --ignore=tests/e2e` | 154 | tracked_source:57, untracked_source_candidate:97 |
| `runtime` | Local/uncategorized | `manual review` | 2292 | runtime_or_local_state:2292 |
| `runtime_context.py` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `schemas` | Contracts | `schema consumers and pytest` | 6 | tracked_source:6 |
| `scoring` | Local/uncategorized | `manual review` | 5 | tracked_source:3, untracked_source_candidate:2 |
| `scripts` | Operator automation | `pytest targeted script tests` | 436 | tracked_source:260, untracked_source_candidate:176 |
| `src` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `tests` | Regression suite | `pytest tests/ --ignore=tests/e2e` | 507 | local_secret_or_sensitive:2, tracked_source:182, untracked_source_candidate:323 |
| `training` | Local/uncategorized | `manual review` | 8 | tracked_source:5, untracked_source_candidate:3 |
| `up` | Local/uncategorized | `manual review` | 1 | tracked_source:1 |
| `web` | Control Center | `cd web; npm run lint; npm test` | 32304 | local_secret_or_sensitive:2, tracked_source:98, untracked_source_candidate:5419, vendor_or_cache:26785 |
| `workflows` | Sprint workflows | `sprint validators` | 89 | tracked_source:89 |
```


## `AI/generated/DOC_SYNC.md`

```markdown
# Engine Brain Doc Sync

Generated at: `2026-07-11T12:51:23+00:00`
Status: `passed`

| Check | Path | Status | Missing |
|---|---|---|---|
| `brain_cli_docs` | `docs/CTOA_CLI.md` | `passed` | - |
| `otclient_cli_docs` | `docs/CTOA_CLI.md` | `passed` | - |
| `command_dictionary_brain` | `schemas/ctoa-command-dictionary.json` | `passed` | - |
| `command_dictionary_otclient` | `schemas/ctoa-command-dictionary.json` | `passed` | - |
| `docs_index_plan3_artifacts` | `docs/INDEX.md` | `passed` | - |
| `roadmap_plan3` | `docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md` | `passed` | - |
```


## `AI/generated/SECRET_GUARDRAIL.md`

```markdown
# Engine Brain Secret Guardrail

Generated at: `2026-07-11T12:51:23+00:00`
Status: `passed`
Sensitive/local env path count in audit: `7`

Generated Engine Brain context must not include exact local sensitive/env paths or secret contents.

| Generated path | Exact sensitive path hits |
|---|---:|
| `AI\generated\FILE_TREE.md` | 0 |
| `AI\generated\SYMBOL_MAP.md` | 0 |
| `AI\generated\OWNERSHIP_MAP.md` | 0 |
| `AI\generated\OWNERSHIP_MAP.json` | 0 |
| `AI\generated\DOC_SYNC.md` | 0 |
| `AI\generated\DOC_SYNC.json` | 0 |
```


## `AI/generated/P6_CODEX_INTEGRATION_READINESS.md`

```markdown
# P6 Codex Integration Readiness

Generated at: `2026-07-11T12:51:23+00:00`
Status: `ready_for_plugin_design`

P6 allows only four read-only status/cockpit tools plus audited repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke safe-write refreshes. Do not add deploy/live shortcuts or bypass Control Center evidence gates.

Recommended next: Operate the plugin as four read-only status/cockpit tools plus audited repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke safe-write refreshes.

| Check | Status | Evidence |
|---|---|---|
| `ai_agents_instruction` | `passed` | AI/AGENTS.md |
| `lua_agents_instruction` | `passed` | scripts/lua/AGENTS.md |
| `engine_brain_skill_source` | `passed` | codex_home/skills/ctoa-engine-brain/SKILL.md |
| `ctoai_plugin_manifest` | `passed` | home/plugins/ctoai-engine-brain/.codex-plugin/plugin.json |
| `ctoai_plugin_brief_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_mcp_config` | `passed` | home/plugins/ctoai-engine-brain/.mcp.json |
| `ctoai_plugin_mcp_absolute_script` | `passed` | absolute MCP script path is runnable |
| `ctoai_plugin_mcp_server` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_operator_skill` | `passed` | home/plugins/ctoai-engine-brain/skills/ctoai-engine-brain-operator/SKILL.md |
| `ctoai_plugin_status_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_control_center_cockpit_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_self_check_script` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_p7_workflow_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p7_workflow_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_operator_brief_cockpit_handoff_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_control_center_cockpit_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_control_center_cockpit_drilldown_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_control_center_cockpit_self_check_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_p7_action_readiness_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p7_action_readiness_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_p7_safe_write_design_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p7_safe_write_design_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_repo_hygiene_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_evidence_pack_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_api_cost_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_engine_brain_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_p7_cockpit_smoke_refresh_mcp_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_mcp.py |
| `ctoai_plugin_p6_handoff_smoke_status_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_status.py |
| `ctoai_plugin_p6_handoff_smoke_cockpit_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_control_center_cockpit.py |
| `ctoai_plugin_p6_handoff_smoke_brief_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_brief.py |
| `ctoai_plugin_p6_handoff_smoke_self_check_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_bounded_write_policy_contract` | `passed` | home/plugins/ctoai-engine-brain/scripts/ctoai_engine_brain_self_check.py |
| `ctoai_plugin_p7_cockpit_smoke_contract_tests` | `passed` | tests/test_engine_brain_index.py |
| `ctoai_plugin_marketplace_entry` | `passed` | personal marketplace entry |
| `ctoai_plugin_installed_cache` | `passed` | installed personal cache version 0.1.0+codex.20260708000418 |
| `control_center_evidence_contract` | `passed` | web/src/lib/controlCenterEvidence.ts |
| `control_center_evidence_tests` | `passed` | web/src/lib/__tests__/controlCenterEvidence.test.ts |
| `control_center_p7_cockpit_smoke_script` | `passed` | scripts/ops/control_center_p7_cockpit_smoke.py |
| `control_center_p7_cockpit_smoke_tests` | `passed` | tests/test_control_center_p7_cockpit_smoke.py |
| `control_center_p7_safe_write_dry_run_smoke_script` | `passed` | scripts/ops/control_center_p7_safe_write_dry_run_smoke.py |
| `control_center_p7_safe_write_dry_run_smoke_tests` | `passed` | tests/test_control_center_p7_safe_write_dry_run_smoke.py |
| `control_center_p7_evidence_review_script` | `passed` | scripts/ops/control_center_p7_evidence_review.py |
| `control_center_p7_evidence_review_tests` | `passed` | tests/test_control_center_p7_evidence_review.py |
| `control_center_p6_plugin_handoff_smoke_script` | `passed` | scripts/ops/control_center_p6_plugin_handoff_smoke.py |
| `control_center_p6_plugin_handoff_smoke_tests` | `passed` | tests/test_control_center_p6_plugin_handoff_smoke.py |
| `control_center_safe_write_action_catalog` | `passed` | web/src/lib/controlCenterActions.ts |
| `control_center_p7_operator_brief_config` | `passed` | web/src/lib/controlCenterEvidenceConfig.ts |
| `control_center_p7_operator_brief_payload` | `passed` | web/src/lib/controlCenterEvidence.ts |
| `control_center_p7_operator_brief_ops` | `passed` | web/src/lib/controlCenterOps.ts |
| `control_center_p7_operator_brief_ui` | `passed` | web/src/components/ControlCenterEvidencePanel.tsx |
| `control_center_p7_operator_brief_detail_ui` | `passed` | web/src/components/ControlCenterDetailPanels.tsx |
| `release_evidence_pack` | `passed` | scripts/ops/release_evidence_pack.py |
| `release_evidence_p7_operator_brief` | `passed` | scripts/ops/release_evidence_pack.py |
| `full_workspace_validation_evidence` | `passed` | runtime\audits\ctoai-full-workspace-validation.json |
| `engine_brain_generated_context` | `passed` | doc_sync_status=passed; secret_guardrail_status=passed |
```


## `AI/generated/P7_OPERATOR_WORKFLOW.md`

```markdown
# P7 Operator Workflow

Generated at: `2026-07-11T12:51:23+00:00`
Status: `safe_write_ready`
Decision: `allow_bounded_safe_write_tools`

P7 operator workflow allows five audited safe_write evidence/context refresh tools. Deploy/live actions stay blocked.

Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Next safe command: Use ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh with dry_run=true before any confirmed refresh.

## Allowed MCP Tools

| Tool | Risk | Purpose |
|---|---|---|
| `ctoai_engine_brain_status` | `read_only` | Summarize generated Engine Brain, validation, doctor, and pack status. |
| `ctoai_engine_brain_self_check` | `read_only` | Verify plugin install state and generated workspace evidence. |
| `ctoai_engine_brain_brief` | `read_only` | Return the generated P7 operator decision and next safe command. |
| `ctoai_control_center_cockpit` | `read_only` | Return read-only Control Center runtime evidence, P7 cockpit, and action-audit status. |
| `ctoai_repo_hygiene_refresh` | `safe_write` | Dry-run-first refresh of repo hygiene evidence with Control Center-compatible audit logging. |
| `ctoai_api_cost_refresh` | `safe_write` | Dry-run-first refresh of API cost evidence with Control Center-compatible audit logging. |
| `ctoai_evidence_pack_refresh` | `safe_write` | Dry-run-first refresh of release evidence with Control Center-compatible audit logging. |
| `ctoai_engine_brain_refresh` | `safe_write` | Dry-run-first refresh of Engine Brain generated context with Control Center-compatible audit logging. |
| `ctoai_p7_cockpit_smoke_refresh` | `safe_write` | Dry-run-first refresh of P7 cockpit smoke evidence with Control Center-compatible audit logging. |

## Blocked Action Classes

| Risk class | Blocked until |
|---|---|
| `guarded_write` | Risk metadata, confirmation modal, operator/owner role gate, and audit evidence exist. |
| `dangerous` | Owner-only typed confirmation, dry-run path, rollback evidence, and audit review exist. |
| `forbidden_ui` | Never expose through plugin or Control Center UI. |

## Gates Before Actions

- Every plugin tool must have a stable risk class from docs/CTOAI_COMMAND_RISK_MODEL.md.
- Every write-capable tool must be represented in Control Center action audit before enablement.
- Only ctoai_repo_hygiene_refresh, ctoai_api_cost_refresh, ctoai_evidence_pack_refresh, ctoai_engine_brain_refresh, and ctoai_p7_cockpit_smoke_refresh may be exposed as safe_write in this wave.
- Every safe-write MCP tool must default to dry-run and append runtime/control-center/action-audit.jsonl.
- No tool may bypass PromoteLiveCtoa -ApproveLiveDeploy for Solteria Helper live promotion.
- No tool may read .env, logs, databases, runtime client state, or private Solteria client data into generated context.
- P6 readiness, P7 operator brief, release evidence pack, doc sync, and secret guardrail must all be current.
```


## `AI/generated/P7_ACTION_READINESS.md`

```markdown
# P7 Action Readiness

Generated at: `2026-07-11T12:51:23+00:00`
Status: `safe_write_tools_enabled`
Decision: `monitor_enabled_safe_write_tools`

P7 action readiness is evidence-only. MCP write tools stay disabled until every candidate has audit evidence and explicit enablement.

Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Action audit: `runtime\control-center\action-audit.jsonl` with `122` records.
MCP write tools: `5`
Next safe command: Design the next P7 plugin action only after risk model coverage, audit logging, Control Center gates, and targeted MCP tests exist; keep deploy/live actions outside the plugin surface.

## Safe Write Candidates

| Action | Source | Risk model | Audit | MCP allowed | Missing gates |
|---|---:|---:|---:|---:|---|
| `repo-hygiene-refresh` | `True` | `True` | `True` | `True` | `none` |
| `api-cost-refresh` | `True` | `True` | `True` | `True` | `none` |
| `evidence-pack-refresh` | `True` | `True` | `True` | `True` | `none` |
| `engine-brain-refresh` | `True` | `True` | `True` | `True` | `none` |
| `p7-cockpit-smoke-refresh` | `True` | `True` | `True` | `True` | `none` |
```


## `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md`

```markdown
# P7 Safe Write Tool Design

Generated at: `2026-07-11T12:51:23+00:00`
Status: `implemented`
Decision: `ready_for_dry_run_operation`

Primary safe-write MCP design remains evidence-pack refresh; repo hygiene, API cost, and Engine Brain refreshes are allowed as additional bounded evidence/context tools. Deploy/live actions remain blocked.

Mode: `dry_run_first`
MCP enabled: `True`
Selected action: `evidence-pack-refresh`
Proposed MCP tool: `ctoai_evidence_pack_refresh`
Risk class: `safe_write`
Control Center source: `web/src/lib/controlCenterActions.ts`
Risk model: `docs/CTOAI_COMMAND_RISK_MODEL.md`
Audit sink: `runtime/control-center/action-audit.jsonl`
Blocked reasons: `none`
Next safe command: Run ctoai_evidence_pack_refresh with dry_run=true and verify runtime/control-center/action-audit.jsonl before confirmed execution.

## Implementation Contract

- Reuse Control Center action semantics for evidence-pack-refresh or an equivalent audited runner.
- Default to dry-run before any write and expose the dry-run result in the MCP response.
- Append a sanitized action audit record before returning.
- Accept no arbitrary command, path, shell, live-deploy, or Solteria Helper promotion arguments.
- Do not read .env, logs, databases, runtime client state, or private client data into AI/generated context.
- Keep live, deploy, guarded_write, dangerous, and forbidden_ui actions out of this tool.
- Keep MCP tool listing read-only until implementation tests and audit parity pass in a later turn.

## Required Tests

- MCP tools/list still exposes only read-only tools while this design artifact is design-only.
- Dry-run call returns planned evidence-pack refresh output without mutating release artifacts.
- Real execution requires explicit safe_write intent and appends a sanitized action audit record.
- Denied or malformed arguments return blocked status without running a command.
- Release evidence and Control Center panels show the tool status without secret leakage.
```


## `AI/generated/P7_OPERATOR_BRIEF.md`

```markdown
# P7 Operator Brief

Generated at: `2026-07-11T12:51:23+00:00`
Decision: `ready_for_p7_operator_workflow`
Status: `ready`

Generated operator brief. Only audited repo-hygiene, API-cost, evidence-pack, Engine Brain, and P7 cockpit-smoke safe_write tools are allowed; deploy/live actions remain blocked.

Next safe command: Design the next P7 plugin action only after risk model coverage, audit logging, Control Center gates, and targeted MCP tests exist; keep deploy/live actions outside the plugin surface.

## Evidence

- P6 readiness: `ready_for_plugin_design` with `55` checks.
- P7 workflow: `safe_write_ready` with `9` MCP tools and `5` safe-write tools.
- P7 action readiness: `safe_write_tools_enabled` with `5/5` audited candidates and `5` MCP write tools.
- P7 safe-write design: `implemented` for `ctoai_evidence_pack_refresh` with MCP enabled `True`.
- P7 cockpit handoff: `ready`; smoke `14/14`; safe-write audits `5/5`; release files `35`; action audit records `122`.
- OTClient helper: `promoted`; release gate `passed`; module contract `passed` (30/30); sandbox queue `passed`; runtime `ready_for_readycheck`; first step `local_ready`.
- Roadmap generation: `ready`; docs `3/3`; doc sync `passed`.
- Validation evidence: `16` commands from `2026-07-07T04:15:56+00:00`.
- Hard blockers: `none`.
- Warnings: `brain_doctor`, `diff_check`.
```


## `AI/generated/FILE_TREE.md`

```markdown
# Engine Brain File Tree

Generated at: `2026-07-11T12:51:23+00:00`

Excluded: `.env*`, secrets/tokens/credentials, `.git`, `.venv`,
`node_modules`, `runtime`, `logs`, `data`, `.tmp`, build outputs.

| Path | Bytes |
|---|---:|
| `.ctoa-local/bootstrap-state.json` | 383 |
| `.ctoa-local/daily/2026-06-23.md` | 3915 |
| `.ctoa-local/user-config.json` | 461 |
| `.devcontainer/devcontainer-lock.json` | 1265 |
| `.devcontainer/devcontainer.json` | 1526 |
| `.foundry/.deployment.json` | 114 |
| `.github/ci-smoke-check.txt` | 38 |
| `.github/copilot-instructions.md` | 5576 |
| `.github/dependabot.yml` | 467 |
| `.github/instructions/ops-powershell-safety.instructions.md` | 1889 |
| `.github/instructions/runner-governance.instructions.md` | 1744 |
| `.github/ISSUE_TEMPLATE/config.yml` | 475 |
| `.github/ISSUE_TEMPLATE/ctoa-031-experiment-charter.md` | 1949 |
| `.github/ISSUE_TEMPLATE/ctoa-032-agent-capability-matrix.md` | 1640 |
| `.github/ISSUE_TEMPLATE/ctoa-033-braver-experiment-packs.md` | 1617 |
| `.github/ISSUE_TEMPLATE/ctoa-034-tool-advisor-sandbox-tuning.md` | 1574 |
| `.github/ISSUE_TEMPLATE/ctoa-035-agent-evaluation-scorecard.md` | 1555 |
| `.github/ISSUE_TEMPLATE/ctoa-036-daily-experiment-review-loop.md` | 1612 |
| `.github/ISSUE_TEMPLATE/ctoa-037-promotion-gate.md` | 1621 |
| `.github/ISSUE_TEMPLATE/ctoa-038-monitoring-alert-p0.md` | 740 |
| `.github/prompts/pr-quality-build-gate-review.prompt.md` | 1729 |
| `.github/prompts/sprint-wave1-readiness.prompt.md` | 1680 |
| `.github/PULL_REQUEST_TEMPLATE/template.md` | 245 |
| `.github/skills/ci-hotfix-workflow/SKILL.md` | 3039 |
| `.github/workflows/browser-e2e-smoke.yml` | 1158 |
| `.github/workflows/cd_bot.yml` | 7124 |
| `.github/workflows/ctoa-approval-watchdog.yml` | 3519 |
| `.github/workflows/ctoa-ci-executive-weekly.yml` | 1068 |
| `.github/workflows/ctoa-close-on-gate.yml` | 887 |
| `.github/workflows/ctoa-copilot-ci.yml` | 9288 |
| `.github/workflows/ctoa-daily-ci-health.yml` | 4820 |
| `.github/workflows/ctoa-daily-insights.yml` | 941 |
| `.github/workflows/ctoa-issue-sync.yml` | 687 |
| `.github/workflows/ctoa-monitoring-alerts.yml` | 14232 |
| `.github/workflows/ctoa-pipeline.yml` | 30466 |
| `.github/workflows/ctoa-runtime-smoke-e2e-8001.yml` | 2546 |
| `.github/workflows/ctoa-smoke-must-pass.yml` | 949 |
| `.github/workflows/ctoa-status-sync.yml` | 980 |
| `.github/workflows/ctoa-vps-hygiene-weekly.yml` | 3891 |
| `.github/workflows/ctoa-weekly-report.yml` | 750 |
| `.github/workflows/docker-build.yml` | 3569 |
| `.github/workflows/main_ctoai.yml` | 3256 |
| `.github/workflows/pr_quality.yml` | 1985 |
| `.github/workflows/site-pages.yml` | 1537 |
| `.github/workflows/vps-authorize-ctoa-key.yml` | 4091 |
| `.github/workflows/vps-gs-cycle.yml` | 10161 |
| `.github/workflows/vps-stack-deploy.yml` | 8480 |
| `.luarc.json` | 268 |
| `.pre-commit-config.yaml` | 784 |
| `.vscode/extensions.json` | 155 |
| `.vscode/launch.json` | 2063 |
| `.vscode/settings.json` | 1277 |
| `.vscode/tasks.json` | 114679 |
| `agent.yaml` | 80 |
| `AGENTS.md` | 2819 |
| `agents/AGENT10_DOCUMENTATION_SAGE.md` | 2620 |
| `agents/agent10_documentation_sage.yaml` | 2253 |
| `agents/AGENT2_CORE_ARCHITECT.md` | 2164 |
| `agents/agent2_core_architect.yaml` | 2010 |
| `agents/AGENT3_DATA_ENGINEER.md` | 1470 |
| `agents/agent3_data_engineer.yaml` | 1882 |
| `agents/AGENT4_ML_BRAIN.md` | 1403 |
| `agents/agent4_ml_brain.yaml` | 1725 |
| `agents/AGENT5_SECURITY_GUARDIAN.md` | 1566 |
| `agents/agent5_security_guardian.yaml` | 1619 |
| `agents/AGENT6_GAME_LOGIC_EXPERT.md` | 2294 |
| `agents/agent6_game_logic_expert.yaml` | 1846 |
| `agents/AGENT7_CODE_SMITH.md` | 1806 |
| `agents/agent7_code_smith.yaml` | 1875 |
| `agents/AGENT8_QA_TERMINATOR.md` | 1413 |
| `agents/agent8_qa_terminator.yaml` | 1706 |
| `agents/AGENT9_DEVOPS_MASTER.md` | 1450 |
| `agents/agent9_devops_master.yaml` | 1993 |
| `agents/ctoa-agents.yaml` | 10819 |
| `agents/definitions.py` | 5911 |
| `agents/STRATEGOS.md` | 2276 |
| `agents/strategos_agent.yaml` | 2500 |
| `agents/toolkit/ctoai_foundry_agent/__init__.py` | 44 |
| `agents/toolkit/ctoai_foundry_agent/app.py` | 8044 |
| `agents/toolkit/ctoai_foundry_agent/README.md` | 1641 |
| `agents/toolkit/ctoai_foundry_agent/requirements.txt` | 143 |
| `agents/toolkit/editable_agents.json` | 2105 |
| `agents/toolkit/README.md` | 647 |
| `AI/AGENTS.md` | 1000 |
| `AI/API_INDEX.md` | 3125 |
| `AI/ARCHITECTURE_INDEX.md` | 2492 |
| `AI/CHECKPOINT_2026-07-07.md` | 3788 |
| `AI/CHECKPOINT_2026-07-08.md` | 10285 |
| `AI/CLASS_INDEX.md` | 1815 |
| `AI/CODEX_CAPABILITY_MAP.md` | 5237 |
| `AI/ENGINE_BRAIN_STATUS.md` | 132303 |
| `AI/ENGINE_MEMORY.md` | 2971 |
| `AI/FEATURE_ROADMAP.md` | 58116 |
| `AI/generated/DOC_SYNC.json` | 1019 |
| `AI/generated/DOC_SYNC.md` | 609 |
| `AI/generated/ENGINE_BRAIN_PACK.json` | 5583 |
| `AI/generated/ENGINE_BRAIN_PACK.md` | 412228 |
| `AI/generated/ENV_DOCTOR.json` | 7626 |
| `AI/generated/ENV_DOCTOR.md` | 1266 |
| `AI/generated/FILE_TREE.md` | 68543 |
| `AI/generated/manifest.json` | 2062 |
| `AI/generated/OWNERSHIP_MAP.json` | 16930 |
| `AI/generated/OWNERSHIP_MAP.md` | 6577 |
| `AI/generated/P6_CODEX_INTEGRATION_READINESS.json` | 11010 |
| `AI/generated/P6_CODEX_INTEGRATION_READINESS.md` | 6915 |
| `AI/generated/P7_ACTION_READINESS.json` | 4870 |
| `AI/generated/P7_ACTION_READINESS.md` | 1142 |
| `AI/generated/P7_OPERATOR_BRIEF.json` | 6464 |
| `AI/generated/P7_OPERATOR_BRIEF.md` | 1373 |
| `AI/generated/P7_OPERATOR_WORKFLOW.json` | 4690 |
| `AI/generated/P7_OPERATOR_WORKFLOW.md` | 3015 |
| `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.json` | 2705 |
| `AI/generated/P7_SAFE_WRITE_TOOL_DESIGN.md` | 2024 |
| `AI/generated/SYMBOL_MAP.md` | 261913 |
| `AI/KNOWN_BUGS.md` | 1384 |
| `AI/LUA_INDEX.md` | 2874 |
| `AI/OPERATIONS_AUDIT.md` | 5139 |
| `AI/OTCLIENT_INDEX.md` | 3675 |
| `AI/PACKET_INDEX.md` | 1405 |
| `AI/PROJECT_CONTEXT.md` | 3648 |
| `AI/README.md` | 2439 |
| `AI/RULEBOOK.md` | 4666 |
| `AI/SPECIALIZED_PROMPTS.md` | 2904 |
| `AI/SYSTEM_PROMPT.md` | 2486 |
| `AI/TASK_TEMPLATE.md` | 1156 |
| `AI/TECH_DEBT.md` | 1803 |
| `alembic/env.py` | 1412 |
| `alembic/versions/20260521_0001_sprint0_baseline.py` | 445 |
| `api/__init__.py` | 2 |
| `api/main.py` | 54986 |
| `api/startup_guard.py` | 1328 |
| `bot/__init__.py` | 1 |
| `bot/action/__init__.py` | 2631 |
| `bot/action/combat.py` | 1677 |
| `bot/action/input_backend.py` | 3022 |
| `bot/action/loot.py` | 315 |
| `bot/action/movement.py` | 2988 |
| `bot/action/spell_rotation.py` | 6741 |
| `bot/config/__init__.py` | 42 |
| `bot/config/runtime_profile.py` | 5961 |
| `bot/connection/__init__.py` | 1 |
| `bot/connection/ots_config.py` | 2579 |
| `bot/dashboard/__init__.py` | 1 |
| `bot/dashboard/app.py` | 6627 |
| `bot/decision/__init__.py` | 1 |
| `bot/decision/brain.py` | 2266 |
| `bot/decision/hunt_strategy.py` | 2683 |
| `bot/decision/ml_model.py` | 7980 |
| `bot/decision/rules.py` | 2199 |
| `bot/infra/docker-compose.yml` | 848 |
| `bot/infra/grafana/dashboards/tibia_bot.json` | 4684 |
| `bot/infra/grafana/provisioning/dashboards/default.yaml` | 175 |
| `bot/infra/grafana/provisioning/datasources/prometheus.yaml` | 159 |
| `bot/infra/prometheus.yml` | 159 |
| `bot/main.py` | 8297 |
| `bot/overlay/__init__.py` | 0 |
| `bot/overlay/macro_overlay.py` | 23823 |
| `bot/overlay/status_overlay.py` | 20975 |
| `bot/perception/__init__.py` | 1 |
| `bot/perception/memory_reader.py` | 8646 |
| `bot/perception/parser.py` | 15541 |
| `bot/perception/screen.py` | 1708 |
| `bot/perception/state.py` | 1124 |
| `bot/perception/window.py` | 10438 |
| `bot/safety/__init__.py` | 1 |
| `bot/safety/humanizer.py` | 4457 |
| `bot/safety/nonsecurity_random.py` | 951 |
| `bot/safety/scheduler.py` | 6918 |
| `bot/safety/session.py` | 1777 |
| `CHANGELOG.md` | 14700 |
| `config/bot_macro_pad.json` | 1487 |
| `config/bot_spell_rotation.json` | 2749 |
| `config/client_profiles.json` | 2161 |
| `config/ctoa-user-config.template.json` | 400 |
| `config/rosetta-presets.json` | 19137 |
| `conftest.py` | 121 |
| `core/protected-files.txt` | 222 |
| `core/runtime-freeze-policy.json` | 301 |
| `ctoa-vps.ps1` | 547 |
| `ctoa.ps1` | 30025 |
| `ctoa_ui_prefs.lua` | 397 |
| `deploy/local/observability/grafana/provisioning/datasources/datasources.yml` | 224 |
| `deploy/local/observability/loki-config.yml` | 539 |
| `deploy/local/observability/prometheus.yml` | 274 |
| `deploy/local/observability/promtail-config.yml` | 349 |
| `deploy/vps/docker-compose.yml` | 819 |
| `deploy/vps/runbook-wrapper-map.md` | 1128 |
| `deploy/vps/SETUP.md` | 10270 |
| `desktop_console/__init__.py` | 154 |
| `desktop_console/api_client.py` | 6829 |
| `desktop_console/app.py` | 90357 |
| `desktop_console/README.md` | 3955 |
| `desktop_console/update_client.py` | 8610 |
| `desktop_console/version.py` | 136 |
| `docker-compose.yml` | 1800 |
| `docs/adr/ADR-001-shared-clock-hybrid-modules.md` | 1201 |
| `docs/AGENT_PROMPT_DEFINITIVE.md` | 4201 |
| `docs/AGENT_TRAINING_MASTERPLAN.md` | 3605 |
| `docs/ARCHITECTURE.md` | 21905 |
| `docs/audits/CTOAI_FULL_WORKSPACE_AUDIT_2026-07-06.md` | 7040 |
| `docs/audits/CTOAI_SECURITY_HARDENING_2026-07-06.md` | 114540 |
| `docs/audits/CTOAI_WORKTREE_EXECUTION_PLAN_2026-07-11.md` | 8548 |
| `docs/audits/CTOAI_WORKTREE_TRIAGE_2026-07-09.md` | 6985 |
| `docs/azure-activity-log-validation-checklist.md` | 555 |
| `docs/azure-alerts-automation-setup.md` | 4007 |
| `docs/BUSINESS_STRATEGY.md` | 5029 |
| `docs/CLIENT_DISTRIBUTION_MODEL.md` | 2928 |
| `docs/COMMUNITY_ENGAGEMENT_PLAN.md` | 15939 |
| `docs/CORE_GUARDRAILS.md` | 1090 |
| `docs/CTOA_CLI.md` | 3810 |
| `docs/CTOAI_COMMAND_RISK_MODEL.md` | 10206 |
| `docs/CTOAI_CONTROL_CENTER_PHASE1.md` | 9084 |
| `docs/CTOAI_FOUNDATION_CLEANUP.md` | 7779 |
| `docs/CTOAI_LEGACY_FEATURE_INVENTORY.md` | 8857 |
| `docs/CTOAI_SURFACE_CONSOLIDATION.md` | 3282 |
| `docs/DEPLOYMENT.md` | 6848 |
| `docs/evidence/azure-activity-log-manual-validation-2026-05-23.md` | 584 |
| `docs/evidence/vps-worktree-hygiene/ctoa-237-20260515T135557Z/preupdate-gate-20260515T135557Z.txt` | 1132 |
| `docs/evidence/vps-worktree-hygiene/ctoa-237-20260515T135557Z/preupdate-status-20260515T135557Z.txt` | 709 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/branch.txt` | 5 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/classification.md` | 3065 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/diff-stat.txt` | 373 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/head.txt` | 41 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/status-full.txt` | 1196 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/status-porcelain.txt` | 951 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/status-short.txt` | 709 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/summary.md` | 224 |
| `docs/evidence/vps-worktree-hygiene/phase1-20260515T130807Z/untracked.txt` | 693 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/branch.txt` | 5 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/changed-paths.txt` | 879 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/head.txt` | 8 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/post-status-porcelain.txt` | 0 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/status-porcelain.txt` | 951 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/status-short.txt` | 709 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/summary.md` | 602 |
| `docs/evidence/vps-worktree-hygiene/phase2-20260515T140911Z/untracked.txt` | 693 |
| `docs/evidence/vps-worktree-hygiene/phase3-20260515T141636Z/fetch-output.txt` | 132 |
| `docs/evidence/vps-worktree-hygiene/phase3-20260515T141636Z/pull-output.txt` | 12749 |
| `docs/evidence/vps-worktree-hygiene/phase3-20260515T141636Z/status-after.txt` | 0 |
| `docs/evidence/vps-worktree-hygiene/phase3-20260515T141636Z/status-before.txt` | 0 |
| `docs/evidence/vps-worktree-hygiene/phase3-20260515T141636Z/summary.md` | 296 |
| `docs/evidence/vps-worktree-hygiene/phase4-exec-20260515T143536Z/format-patch.resume.stdout.txt` | 563 |
| `docs/evidence/vps-worktree-hygiene/phase4-exec-20260515T143536Z/resume-main-status.txt` | 0 |
| `docs/evidence/vps-worktree-hygiene/phase4-exec-20260515T143536Z/summary.json` | 3267 |
| `docs/evidence/vps-worktree-hygiene/phase4-exec-20260515T143536Z/summary.md` | 954 |
| `docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/grouped-paths.json` | 422 |
| `docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/stash-list.txt` | 52 |
| `docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/stash-top-name-status.txt` | 198 |
| `docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/stash-top-stat.txt` | 372 |
| `docs/evidence/vps-worktree-hygiene/phase4-readiness-20260515T141731Z/summary.md` | 277 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260515T185948Z/cron-install.out.txt` | 231 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260515T185948Z/remote-head.txt` | 11 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260515T185948Z/remote-latest-path.txt` | 80 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260515T185948Z/report.txt` | 295 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260515T185948Z/status-porcelain.txt` | 0 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260515T185948Z/summary.md` | 157 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260516T022001Z/report.txt` | 295 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260516T022001Z/status-porcelain.txt` | 0 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260516T022001Z/summary.md` | 157 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260517T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260517T022001Z/status-porcelain.txt` | 54 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260517T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260518T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260518T022001Z/status-porcelain.txt` | 108 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260518T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260519T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260519T022001Z/status-porcelain.txt` | 162 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260519T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260520T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260520T022001Z/status-porcelain.txt` | 216 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260520T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260521T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260521T022001Z/status-porcelain.txt` | 270 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260521T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260522T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260522T022001Z/status-porcelain.txt` | 554 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260522T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260523T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260523T022001Z/status-porcelain.txt` | 608 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260523T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260524T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260524T022001Z/status-porcelain.txt` | 662 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260524T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260525T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260525T022001Z/status-porcelain.txt` | 751 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260525T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260526T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260526T022001Z/status-porcelain.txt` | 805 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260526T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260527T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260527T022001Z/status-porcelain.txt` | 859 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260527T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260528T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260528T022001Z/status-porcelain.txt` | 913 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260528T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260529T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260529T022001Z/status-porcelain.txt` | 967 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260529T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260530T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260530T022001Z/status-porcelain.txt` | 1021 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260530T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260531T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260531T022001Z/status-porcelain.txt` | 1075 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260531T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260601T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260601T022001Z/status-porcelain.txt` | 1129 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260601T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260602T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260602T022001Z/status-porcelain.txt` | 1183 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260602T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260603T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260603T022001Z/status-porcelain.txt` | 1237 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260603T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260604T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260604T022001Z/status-porcelain.txt` | 1291 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260604T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260605T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260605T022001Z/status-porcelain.txt` | 1345 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260605T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260606T022002Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260606T022002Z/status-porcelain.txt` | 1399 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260606T022002Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260607T022002Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260607T022002Z/status-porcelain.txt` | 1453 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260607T022002Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260608T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260608T022001Z/status-porcelain.txt` | 1507 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260608T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260609T022001Z/report.txt` | 465 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260609T022001Z/status-porcelain.txt` | 23 |
| `docs/evidence/vps-worktree-hygiene/phase5-drycheck-20260609T022001Z/summary.md` | 174 |
| `docs/evidence/vps-worktree-hygiene/phase5-morning-brief.md` | 342 |
| `docs/evidence/vps-worktree-hygiene/phase5-nightly-checklist.md` | 1454 |
| `docs/evidence/vps-worktree-hygiene/README.md` | 5847 |
| `docs/examples/azure-activity-log-samples.json` | 2059 |
| `docs/experiments/agent-experiment-week-plan.md` | 7880 |
| `docs/experiments/ci-executive-weekly-template.md` | 984 |
| `docs/experiments/ci-remediation-plan-7d.md` | 2182 |
| `docs/experiments/ctoa-031-037-issue-bodies.md` | 6217 |
| `docs/experiments/daily-experiment-scorecard.md` | 1309 |
| `docs/experiments/day1-2026-03-19-execution.md` | 3736 |
| `docs/experiments/day1-go-hold-kill-2026-03-19.yaml` | 1308 |
| `docs/experiments/day2-assignment-matrix-2026-03-19.md` | 2269 |
| `docs/experiments/day2-end-of-day-decision-memo-2026-03-19.md` | 5612 |
| `docs/experiments/day2-scorecard-dry-run-2026-03-19.md` | 2109 |
| `docs/experiments/day3-assignment-matrix-2026-03-20.md` | 1811 |
| `docs/experiments/day3-end-of-day-decision-memo-2026-03-20.md` | 3632 |
| `docs/experiments/day3-go-hold-kill-2026-03-20.yaml` | 1305 |
| `docs/experiments/day3-replay-checklist-exp-001-exp-002.md` | 1583 |
| `docs/experiments/day3-run-sheet-2026-03-20-0900-1000.md` | 3762 |
| `docs/experiments/day4-assignment-matrix-2026-03-21.md` | 1686 |
| `docs/experiments/day4-end-of-day-decision-memo-2026-03-21.md` | 1481 |
| `docs/experiments/day4-run-sheet-2026-03-21-0900-1000.md` | 3335 |
| `docs/experiments/decision-memo-template.md` | 1325 |
| `docs/experiments/exp-001-exp-002-baseline-challenger-checklist.md` | 2022 |
| `docs/experiments/exp-001-promotion-prep-2026-03-20.md` | 3647 |
| `docs/experiments/exp-001-promotion-release-run-sheet-2026-03-20.md` | 3602 |
| `docs/experiments/exp-002-archived-findings-2026-03-20.md` | 1524 |
| `docs/experiments/exp-next-cycle-routing-micro-hypothesis.md` | 2077 |
| `docs/gs-ops-README.md` | 5665 |
| `docs/history/ARCHIVED_CURRENT_PRIORITY_MAP_2026-03-19.md` | 872 |
| `docs/history/sprints/SPRINT-002.md` | 2357 |
| `docs/history/sprints/SPRINT-003.md` | 3386 |
| `docs/history/sprints/SPRINT-004.md` | 4441 |
| `docs/history/sprints/SPRINT-005.md` | 4382 |
| `docs/history/sprints/SPRINT-006.md` | 4265 |
| `docs/history/sprints/SPRINT-007.md` | 2307 |
| `docs/history/sprints/SPRINT-040.md` | 1038 |
| `docs/history/sprints/SPRINT-042.md` | 5143 |
| `docs/history/sprints/SPRINT-043.md` | 112 |
| `docs/history/sprints/SPRINT-044.md` | 112 |
| `docs/history/sprints/SPRINT-045-PROGRESS.md` | 854 |
| `docs/history/sprints/SPRINT-045.md` | 5558 |
| `docs/history/sprints/SPRINT-046-PROGRESS.md` | 917 |
| `docs/history/sprints/SPRINT-046.md` | 8252 |
| `docs/history/sprints/SPRINT-047-PROGRESS.md` | 915 |
| `docs/history/sprints/SPRINT-047.md` | 5181 |
| `docs/history/sprints/SPRINT-048-PROGRESS.md` | 915 |
| `docs/history/sprints/SPRINT-048.md` | 3674 |
| `docs/history/sprints/SPRINT-049-HANDOFF-CTOA-256.md` | 1285 |
| `docs/history/sprints/SPRINT-049-PROGRESS.md` | 2440 |
| `docs/history/sprints/SPRINT-049.md` | 3859 |
| `docs/history/sprints/SPRINT-050-PROGRESS.md` | 3959 |
| `docs/history/sprints/SPRINT-050.md` | 3295 |
| `docs/history/sprints/SPRINT-051-PROGRESS.md` | 3407 |
| `docs/history/sprints/SPRINT-051.md` | 3238 |
| `docs/history/sprints/SPRINT-052-PROGRESS.md` | 3796 |
| `docs/history/sprints/SPRINT-052.md` | 3228 |
| `docs/history/sprints/SPRINT-053-PROGRESS.md` | 3599 |
| `docs/history/sprints/SPRINT-053.md` | 3215 |
| `docs/history/sprints/SPRINT-054-PROGRESS.md` | 3629 |
| `docs/history/sprints/SPRINT-054.md` | 3215 |
| `docs/history/sprints/SPRINT-055-PROGRESS.md` | 2706 |
| `docs/history/sprints/SPRINT-055.md` | 3197 |
| `docs/history/sprints/SPRINT-056-PROGRESS.md` | 985 |
| `docs/history/sprints/SPRINT-056.md` | 3165 |
| `docs/history/sprints/SPRINT-057-PROGRESS.md` | 985 |
| `docs/history/sprints/SPRINT-057.md` | 2872 |
| `docs/history/sprints/SPRINT-058-PROGRESS.md` | 1171 |
| `docs/history/sprints/SPRINT-058.md` | 2877 |
| `docs/history/sprints/SPRINT-059-PR-EXECUTIVE.md` | 1316 |
| `docs/history/sprints/SPRINT-059-PROGRESS.md` | 1171 |
| `docs/history/sprints/SPRINT-059.md` | 1883 |
| `docs/history/sprints/SPRINT-060-PROGRESS.md` | 985 |
| `docs/history/sprints/SPRINT-060.md` | 1888 |
| `docs/history/sprints/SPRINT-061-PROGRESS.md` | 985 |
| `docs/history/sprints/SPRINT-061.md` | 1388 |
| `docs/history/sprints/SPRINT-062-PROGRESS.md` | 985 |
| `docs/history/sprints/SPRINT-062.md` | 2142 |
| `docs/history/sprints/SPRINT-063-PROGRESS.md` | 830 |
| `docs/history/sprints/SPRINT-063.md` | 1320 |
| `docs/history/sprints/SPRINT-064-PROGRESS.md` | 830 |
| `docs/history/sprints/SPRINT-064.md` | 1309 |
| `docs/history/sprints/SPRINT-065-PROGRESS.md` | 830 |
| `docs/history/sprints/SPRINT-065.md` | 1317 |
| `docs/history/sprints/SPRINT-066-PROGRESS.md` | 825 |
| `docs/history/sprints/SPRINT-066.md` | 1604 |
| `docs/history/sprints/SPRINT-067-PROGRESS.md` | 826 |
| `docs/history/sprints/SPRINT-067.md` | 1882 |
| `docs/history/sprints/SPRINT-068-PROGRESS.md` | 902 |
| `docs/history/sprints/SPRINT-068.md` | 1918 |
| `docs/history/sprints/SPRINT-069-PROGRESS.md` | 942 |
| `docs/history/sprints/SPRINT-069.md` | 1316 |
| `docs/history/sprints/SPRINT_007_AGENT_EXECUTION_REPORT.md` | 4393 |
| `docs/HYBRID_BOT_IMPLEMENTATION.md` | 12154 |
| `docs/INDEX.md` | 3421 |
| `docs/INFRASTRUCTURE_CANONICAL.md` | 2069 |
| `docs/INFRASTRUCTURE_DECISION_LOG.md` | 2450 |
| `docs/ISSUE_TRIAGE.md` | 1784 |
| `docs/LAB003_10H_WORK_SHIFT_PLAN.md` | 2605 |
| `docs/LOCAL_SETUP.md` | 7359 |
| `docs/loot-target-spec.md` | 507 |
| `docs/MARKET_ANALYSIS_2025.md` | 4947 |
| `docs/MOBILE_CONSOLE.md` | 5749 |
| `docs/operating-model.md` | 454 |
| `docs/otclient/ctoai_runtime_2_execution_plan.md` | 5250 |
| `docs/otclient/helper_redesign.md` | 7979 |
| `docs/otclient/HELPER_RUNTIME_BRIDGE_V1.md` | 1694 |
| `docs/otclient/solteria_helper_development_plan.md` | 10365 |
| `docs/otclient/solteria_helper_input_contracts.md` | 4430 |
| `docs/otclient/solteria_helper_module_contract.md` | 4360 |
| `docs/otclient/solteria_helper_module_workplan.md` | 12759 |
| `docs/otclient/solteria_helper_next_modules_plan.md` | 18281 |
| `docs/otclient/solteria_helper_sandbox_smoke_queue.md` | 10222 |
| `docs/otclient/solteria_helper_shell_budget_plan.md` | 4261 |
| `docs/otclient/solteria_helper_supplemental_refactor_plan.md` | 27770 |
| `docs/otclient/solteria_helper_test_env.md` | 26202 |
| `docs/otclient/SOLTERIA_HELPER_V2_1_1_STYLE_MODERNIZATION_PLAN_2026-07-11.md` | 7950 |
| `docs/otclient/SOLTERIA_HELPER_V2_1_1A_STABILIZATION_REFACTOR_PLAN_2026-07-11.md` | 2206 |
| `docs/otclient/SOLTERIA_HELPER_V2_1_UX_PLAN_2026-07-11.md` | 1797 |
| `docs/otclient/SOLTERIA_HELPER_V2_2_0_VOCATION_COMBAT_PLAN_2026-07-11.md` | 1741 |
| `docs/otclient/SOLTERIA_HELPER_V2_EXECUTION_PLAN_2026-07-11.md` | 3394 |
| `docs/otclient/tibia_control_center_helper_p0_plan.md` | 5553 |
| `docs/otclient/VBOT_5_ARCHITECTURE_EXECUTION_PLAN_2026-07-11.md` | 5431 |
| `docs/otclient/vbot_import_review.md` | 4989 |
| `docs/otclient/zerobot_reference.md` | 4707 |
| `docs/OTCLIENT_INTEGRATION.md` | 13068 |
| `docs/OTCLIENT_QUICKSTART.md` | 2776 |
| `docs/paper_extracted.txt` | 35869 |
| `docs/pathing-spec.md` | 485 |
| `docs/POST_GA_DELIVERY_TRAIN_BASELINE.md` | 1733 |
| `docs/POST_GA_DELIVERY_TRAIN_CANDIDATE.yaml` | 496 |
| `docs/PRODUCT_PORTFOLIO.md` | 2894 |
| `docs/PRODUCT_PUBLIC_PRIVATE_ARCHITECTURE.md` | 4229 |
| `docs/PRODUCTIZATION_TRACK_C.md` | 4674 |
| `docs/README_BOT.md` | 14155 |
| `docs/README_INVENTORY.md` | 2172 |
| `docs/REALTIME_MODULE_CREATION.md` | 3229 |
| `docs/REPO_HYGIENE_POLICY.md` | 4830 |
| `docs/REPO_SCHEMA.md` | 10994 |
| `docs/ROADMAP_V0.2.0_TO_V1.0.0.md` | 878 |
| `docs/roadmaps/CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md` | 6578 |
| `docs/runbook-althea-enc3-reverseeng.md` | 3502 |
| `docs/runbook-azure-activity-log-interpretation.md` | 2855 |
| `docs/runbook-disk-emergency.md` | 2223 |
| `docs/runbook-enc3-reverseeng.md` | 13429 |
| `docs/runbook-phase5-alerts-incident.md` | 2514 |
| `docs/runbook-vps-agent-outputs.md` | 5948 |
| `docs/runbook-vps-mobile-console.md` | 2576 |
| `docs/site/assets/opentibia/ATTRIBUTION.md` | 614 |
| `docs/site/script.js` | 38292 |
| `docs/SPRINT_GOVERNANCE.md` | 9642 |
| `docs/STRATEGOS_DESKTOP_WEB_REBUILD_PLAN.md` | 2361 |
| `docs/targeting-rules.md` | 236 |
| `docs/telemetry-schema.md` | 197 |
| `docs/VALIDATION_CHECKLIST.md` | 9492 |
| `evals/prompt-variants/azure-activity-baseline.md` | 315 |
| `evals/prompt-variants/azure-activity-fact-first.md` | 1138 |
| `evals/prompt-variants/azure-activity-strict-evidence.md` | 441 |
| `evals/README-azure-agent-eval-dataset.md` | 763 |
| `evals/runs/README.md` | 1177 |
| `mobile_console/__init__.py` | 0 |
| `mobile_console/app.py` | 121249 |
| `mobile_console/services/__init__.py` | 212 |
| `mobile_console/services/admin_settings_service.py` | 604 |
| `mobile_console/services/ideas_service.py` | 1685 |
| `mobile_console/static/app.js` | 30184 |
| `mobile_console/static/dashboard_helpers.js` | 938 |
| `policies/ci-gate-policy.yaml` | 566 |
| `product/ctoa-toolkit.manifest.json` | 325 |
| `product/packages/core.manifest.json` | 680 |
| `product/packages/pro.manifest.json` | 445 |
| `product/packages/studio.manifest.json` | 371 |
| `prompts/braver-library.yaml` | 3632 |
| `prompts/braver_templates.py` | 5238 |
| `prompts/design-infra-playbook.yaml` | 1014 |
| `prompts/mmo-lua-pack.yaml` | 4062 |
| `README.md` | 5711 |
| `releases/evidence/release-validation-dashboardsnapshot-2026-05-24.md` | 921 |
| `releases/evidence/sprint-050/CTOA-260.md` | 578 |
| `releases/evidence/sprint-050/CTOA-261.md` | 609 |
| `releases/evidence/sprint-050/CTOA-262.md` | 553 |
| `releases/evidence/sprint-050/CTOA-263.md` | 1076 |
| `releases/evidence/sprint-051/CTOA-266.md` | 676 |
| `releases/evidence/sprint-051/CTOA-267.md` | 640 |
| `releases/evidence/sprint-051/CTOA-268.md` | 553 |
| `releases/evidence/sprint-051/CTOA-269.md` | 994 |
| `releases/evidence/sprint-052/CTOA-272.md` | 575 |
| `releases/evidence/sprint-052/CTOA-273.md` | 580 |
| `releases/evidence/sprint-052/CTOA-274.md` | 558 |
| `releases/evidence/sprint-052/CTOA-275.md` | 936 |
| `releases/evidence/sprint-053/CTOA-278.md` | 516 |
| `releases/evidence/sprint-053/CTOA-279.md` | 564 |
| `releases/evidence/sprint-053/CTOA-280.md` | 771 |
| `releases/evidence/sprint-053/CTOA-281.md` | 897 |
| `releases/evidence/sprint-054/CTOA-282.md` | 432 |
| `releases/evidence/sprint-054/CTOA-283.md` | 508 |
| `releases/evidence/sprint-054/CTOA-284.md` | 509 |
| `releases/evidence/sprint-054/CTOA-285.md` | 538 |
| `releases/evidence/sprint-054/CTOA-286.md` | 778 |
| `releases/evidence/sprint-054/CTOA-287.md` | 854 |
| `releases/evidence/sprint-055/CTOA-288.md` | 432 |
| `releases/evidence/sprint-055/CTOA-289.md` | 508 |
| `releases/evidence/sprint-055/CTOA-290.md` | 529 |
| `releases/evidence/sprint-055/CTOA-291.md` | 529 |
| `releases/evidence/sprint-055/CTOA-292.md` | 778 |
| `releases/evidence/sprint-055/CTOA-293.md` | 883 |
| `releases/evidence/sprint-056/CTOA-294.md` | 432 |
| `releases/evidence/sprint-056/CTOA-295.md` | 508 |
| `releases/evidence/sprint-056/CTOA-296.md` | 505 |
| `releases/evidence/sprint-056/CTOA-297.md` | 514 |
| `releases/evidence/sprint-056/CTOA-298.md` | 778 |
| `releases/evidence/sprint-056/CTOA-299.md` | 838 |
| `releases/v1.1.1-release-notes.md` | 2210 |
| `requirements-bot.txt` | 525 |
| `requirements-dev.txt` | 126 |
| `requirements.txt` | 550 |
| `runner/__init__.py` | 112 |
| `runner/agents/__init__.py` | 256 |
| `runner/agents/activation_agent.py` | 9427 |
| `runner/agents/brain_v2.py` | 10487 |
| `runner/agents/catalog_agent.py` | 15656 |
| `runner/agents/db.py` | 3581 |
| `runner/agents/executor.py` | 28127 |
| `runner/agents/generator_agent.py` | 35621 |
| `runner/agents/ingest_agent.py` | 8582 |
| `runner/agents/orchestrator.py` | 2709 |
| `runner/agents/publisher_agent.py` | 6801 |
| `runner/agents/routing.py` | 500 |
| `runner/agents/scout_agent.py` | 12207 |
| `runner/agents/validator_agent.py` | 6552 |
| `runner/alert_rules.py` | 3097 |
| `runner/close_on_gate.py` | 3595 |
| `runner/daily_insights.py` | 6334 |
| `runner/drift_checker.py` | 2444 |
| `runner/generated_manifest_safety.py` | 3281 |
| `runner/generator_validator_samples.py` | 5979 |
| `runner/health_metrics.py` | 21276 |
| `runner/health_trend.py` | 4412 |
| `runner/http_safety.py` | 10943 |
| `runner/hybrid_bot/__init__.py` | 1008 |
| `runner/hybrid_bot/bot_runner.py` | 14245 |
| `runner/hybrid_bot/cli.py` | 7611 |
| `runner/hybrid_bot/clock.py` | 250 |
| `runner/hybrid_bot/command_executor.py` | 14571 |
| `runner/hybrid_bot/file_safety.py` | 2070 |
| `runner/hybrid_bot/gameplay_engine.py` | 11632 |
| `runner/hybrid_bot/INTEGRATION_COMPLETE.md` | 14231 |
| `runner/hybrid_bot/interactive_mode.py` | 11148 |
| `runner/hybrid_bot/metrics.py` | 15053 |
| `runner/hybrid_bot/pathfinding.py` | 11395 |
| `runner/hybrid_bot/performance_profiler.py` | 8328 |
| `runner/hybrid_bot/prompt_logic.py` | 11668 |
| `runner/hybrid_bot/README.md` | 15326 |
| `runner/hybrid_bot/screenshot_provider.py` | 8349 |
| `runner/hybrid_bot/state_manager.py` | 10822 |
| `runner/hybrid_bot/template_library.py` | 15009 |
| `runner/hybrid_bot/vision_layer.py` | 14219 |
| `runner/issue_sync.py` | 6474 |
| `runner/llm_providers/__init__.py` | 1760 |
| `runner/llm_providers/azure_foundry.py` | 1949 |
| `runner/llm_providers/local_model.py` | 1927 |
| `runner/mythibia_local_brain.py` | 11506 |
| `runner/pipeline/__init__.py` | 170 |
| `runner/pipeline/scheduler.py` | 589 |
| `runner/process_safety.py` | 2977 |
| `runner/queue_worker.py` | 4368 |
| `runner/requirements.txt` | 54 |
| `runner/response_guardrails.py` | 2491 |
| `runner/runner.py` | 20638 |
| `runner/status_sync.py` | 9396 |
| `runner/tibia_sources.py` | 25210 |
| `runner/weekly_report.py` | 8409 |
| `runtime_context.py` | 2934 |
| `schemas/ci-gate-policy.schema.json` | 1426 |
| `schemas/ctoa-command-dictionary.json` | 3196 |
| `schemas/intel-projects.schema.json` | 1136 |
| `schemas/mobile_console_api_contract.snapshot.json` | 8456 |
| `schemas/otclient-helper-config.schema.json` | 4451 |
| `schemas/release-artifact.schema.json` | 1190 |
| `scoring/tibia-tool-matrix.yaml` | 1508 |
| `scoring/tool-advisor-rules.yaml` | 1083 |
| `scoring/tool_advisor.py` | 4485 |
| `scripts/analyze_pdf.py` | 1903 |
| `scripts/calibrate_colors.py` | 6188 |
| `scripts/calibrate_memory.py` | 9545 |
| `scripts/enc3_analyze.py` | 4200 |
| `scripts/enc3_disasm.py` | 3072 |
| `scripts/enc3_format.py` | 2063 |
| `scripts/enc3_header.py` | 1183 |
| `scripts/enc3_recover_func.py` | 5451 |
| `scripts/enc3_xref_scan.py` | 985 |
| `scripts/enc3_xref_scan_rva.py` | 2374 |
| `scripts/example_strategos_local_ai.py` | 6635 |
| `scripts/lua/AGENTS.md` | 1183 |
| `scripts/lua/auto_heal.lua` | 1760 |
| `scripts/lua/ctoa_hotkey_status.lua` | 1535 |
| `scripts/lua/ctoa_path_probe.lua` | 1248 |
| `scripts/lua/emergency_heal.lua` | 460 |
| `scripts/lua/event_logger.lua` | 2180 |
| `scripts/lua/loot_filter.lua` | 1538 |
| `scripts/lua/module_reporter.lua` | 1112 |
| `scripts/lua/otclient/ctoa_ed_profile.lua` | 2453 |
| `scripts/lua/otclient/ctoa_ek_profile.lua` | 7703 |
| `scripts/lua/otclient/ctoa_helper_action_catalog.lua` | 6472 |
| `scripts/lua/otclient/ctoa_helper_cavebot_observer.lua` | 3342 |
| `scripts/lua/otclient/ctoa_helper_cavebot_runtime.lua` | 15629 |
| `scripts/lua/otclient/ctoa_helper_client_reporter.lua` | 8294 |
| `scripts/lua/otclient/ctoa_helper_combat_observer.lua` | 5193 |
| `scripts/lua/otclient/ctoa_helper_combat_runtime.lua` | 17810 |
| `scripts/lua/otclient/ctoa_helper_conditions.lua` | 7172 |
| `scripts/lua/otclient/ctoa_helper_decision_pipeline.lua` | 6154 |
| `scripts/lua/otclient/ctoa_helper_decision_trace.lua` | 3937 |
| `scripts/lua/otclient/ctoa_helper_diagnostics.lua` | 19073 |
| `scripts/lua/otclient/ctoa_helper_dispatch_guard.lua` | 4041 |
| `scripts/lua/otclient/ctoa_helper_domain_contract.lua` | 5152 |
| `scripts/lua/otclient/ctoa_helper_equipment.lua` | 6160 |
| `scripts/lua/otclient/ctoa_helper_equipment_observer.lua` | 3333 |
| `scripts/lua/otclient/ctoa_helper_feature_flags.lua` | 6778 |
| `scripts/lua/otclient/ctoa_helper_heal_friend.lua` | 7450 |
| `scripts/lua/otclient/ctoa_helper_hotkeys.lua` | 5811 |
| `scripts/lua/otclient/ctoa_helper_hud.lua` | 3845 |
| `scripts/lua/otclient/ctoa_helper_loot_observer.lua` | 3083 |
| `scripts/lua/otclient/ctoa_helper_loot_runtime.lua` | 4304 |
| `scripts/lua/otclient/ctoa_helper_modal.lua` | 5112 |
| `scripts/lua/otclient/ctoa_helper_module_status.lua` | 4669 |
| `scripts/lua/otclient/ctoa_helper_modules.lua` | 15761 |
| `scripts/lua/otclient/ctoa_helper_operator_summary.lua` | 5532 |
| `scripts/lua/otclient/ctoa_helper_otclient_observation_adapter.lua` | 11308 |
| `scripts/lua/otclient/ctoa_helper_plan_queue.lua` | 2684 |
| `scripts/lua/otclient/ctoa_helper_planner.lua` | 5062 |
| `scripts/lua/otclient/ctoa_helper_profile_persistence.lua` | 14272 |
| `scripts/lua/otclient/ctoa_helper_profile_schema.lua` | 25417 |
| `scripts/lua/otclient/ctoa_helper_recovery_bridge.lua` | 5889 |
| `scripts/lua/otclient/ctoa_helper_recovery_observer.lua` | 4249 |
| `scripts/lua/otclient/ctoa_helper_recovery_runtime.lua` | 4956 |
| `scripts/lua/otclient/ctoa_helper_route.lua` | 10784 |
| `scripts/lua/otclient/ctoa_helper_runtime_core.lua` | 10804 |
| `scripts/lua/otclient/ctoa_helper_runtime_policy.lua` | 7685 |
| `scripts/lua/otclient/ctoa_helper_runtime_readiness.lua` | 3844 |
| `scripts/lua/otclient/ctoa_helper_sandbox_handoff.lua` | 4120 |
| `scripts/lua/otclient/ctoa_helper_scripting.lua` | 2946 |
| `scripts/lua/otclient/ctoa_helper_targeting.lua` | 8172 |
| `scripts/lua/otclient/ctoa_helper_timer_runtime.lua` | 4056 |
| `scripts/lua/otclient/ctoa_helper_ui.lua` | 93266 |
| `scripts/lua/otclient/ctoa_helper_vocation_profiles.lua` | 3881 |
| `scripts/lua/otclient/ctoa_ms_profile.lua` | 2412 |
| `scripts/lua/otclient/ctoa_native_combat.lua` | 18058 |
| `scripts/lua/otclient/ctoa_native_heal.lua` | 9644 |
| `scripts/lua/otclient/ctoa_native_helper.lua` | 180090 |
| `scripts/lua/otclient/ctoa_native_loot.lua` | 11632 |
| `scripts/lua/otclient/ctoa_otclient.otmod` | 253 |
| `scripts/lua/otclient/ctoa_otclient_loader.lua` | 7548 |
| `scripts/lua/otclient/ctoa_rp_profile.lua` | 2424 |
| `scripts/lua/otclient/README.md` | 25123 |
| `scripts/lua/pathing_helper.lua` | 1361 |
| `scripts/lua/proximity_watch.lua` | 797 |
| `scripts/lua/safety_interrupt.lua` | 359 |
| `scripts/lua/status_beacon.lua` | 475 |
| `scripts/lua/supply_manager.lua` | 1155 |
| `scripts/lua/target_priority.lua` | 1955 |
| `scripts/lua/telemetry_exporter.lua` | 399 |
| `scripts/ops/aggregate_agent_eval.py` | 2402 |
| `scripts/ops/analyze-enc3.ps1` | 3809 |
| `scripts/ops/api_cost_report.py` | 19017 |
| `scripts/ops/assemble_by_handle_offset.py` | 6315 |
| `scripts/ops/assemble_io_dense_stream.py` | 1817 |
| `scripts/ops/assemble_overlap_graph_variants.py` | 11610 |
| `scripts/ops/assemble_window_aware_variants.py` | 5674 |
| `scripts/ops/auto_trainer.py` | 7488 |
| `scripts/ops/azure-alerts-runner.ps1` | 4953 |
| `scripts/ops/azure_activity_alerts.py` | 15878 |
| `scripts/ops/azure_activity_webhook_listener.py` | 5693 |
| `scripts/ops/bootstrap_sprints_029_040.py` | 16837 |
| `scripts/ops/bridge_replacement_readiness.py` | 3669 |
| `scripts/ops/build-loader.ps1` | 556 |
| `scripts/ops/capture_io_dense_live.py` | 12151 |
| `scripts/ops/capture_loader_exec_aggressive.py` | 10262 |
| `scripts/ops/capture_loader_exec_aggressive_live.py` | 10343 |
| `scripts/ops/capture_loader_exec_burst.py` | 10993 |
| `scripts/ops/capture_ntreadfile_stream.py` | 9444 |
| `scripts/ops/capture_post_transform_mapview.py` | 6564 |
| `scripts/ops/capture_post_transform_protect.py` | 6399 |
| `scripts/ops/capture_runtime_crypto_decompress_live.py` | 14260 |
| `scripts/ops/capture_runtime_loader_transform_live.py` | 41844 |
| `scripts/ops/ci_executive_report.py` | 10673 |
| `scripts/ops/client_profile_router.py` | 885 |
| `scripts/ops/compare_eval_summaries.py` | 3647 |
| `scripts/ops/control_center_p6_plugin_handoff_smoke.py` | 21273 |
| `scripts/ops/control_center_p7_cockpit_smoke.py` | 19947 |
| `scripts/ops/control_center_p7_evidence_review.py` | 15745 |
| `scripts/ops/control_center_p7_safe_write_dry_run_smoke.py` | 17838 |
| `scripts/ops/core_guard.py` | 3960 |
| `scripts/ops/ctoa-vps.ps1` | 92112 |
| `scripts/ops/ctoa_env_doctor.py` | 6218 |
| `scripts/ops/ctoa_full_workspace_audit.py` | 30604 |
| `scripts/ops/ctoa_helper_smoke_report.py` | 10065 |
| `scripts/ops/ctoa_helper_ui_mockup_v4.py` | 6281 |
| `scripts/ops/ctoa_helper_ui_preview.py` | 58270 |
| `scripts/ops/ctoa_loader.py` | 16230 |
| `scripts/ops/ctoa_otprofile_builder.py` | 15867 |
| `scripts/ops/ctoa_product_bootstrap.py` | 7977 |
| `scripts/ops/ctoa_tibia_source_ingest.py` | 2209 |
| `scripts/ops/ctoa_update_gate.py` | 4419 |
| `scripts/ops/depack_anchor_windows.py` | 9656 |
| `scripts/ops/depack_io_assembled_focused.py` | 3260 |
| `scripts/ops/depack_stream_compare.py` | 2780 |
| `scripts/ops/depack_stream_focused.py` | 4554 |
| `scripts/ops/depack_top_candidates.py` | 10352 |
| `scripts/ops/depack_window_aware_focused.py` | 8002 |
| `scripts/ops/engine_brain_doctor.py` | 19184 |
| `scripts/ops/engine_brain_index.py` | 112932 |
| `scripts/ops/engine_brain_pack.py` | 9020 |
| `scripts/ops/evidence_retention.py` | 2057 |
| `scripts/ops/git_exec.py` | 2142 |
| `scripts/ops/gs-api-validator.py` | 6610 |
| `scripts/ops/install-mythibia-autosync-task.ps1` | 1666 |
| `scripts/ops/install-mythibia-watchdog-task.ps1` | 1594 |
| `scripts/ops/install-mythibia-watcher-task.ps1` | 2664 |
| `scripts/ops/install-phase5-morning-sync-task.ps1` | 1359 |
| `scripts/ops/kv_attach_first_hit.py` | 2374 |
| `scripts/ops/kv_first_hit_from_live_session.py` | 17152 |
| `scripts/ops/kv_raw_init_probe.py` | 643 |
| `scripts/ops/kv_smoke_diag.py` | 857 |
| `scripts/ops/kv_smoke_min.py` | 434 |
| `scripts/ops/lab003_mobile_proxy_smoke.ps1` | 4695 |
| `scripts/ops/lab003_shift_guard.ps1` | 8887 |
| `scripts/ops/lab003_shift_smoke_webhook.ps1` | 5375 |
| `scripts/ops/lab003_validate_bundle.ps1` | 3687 |
| `scripts/ops/launch_kamil_client_macro_studio.ps1` | 3766 |
| `scripts/ops/link_check_docs.py` | 1438 |
| `scripts/ops/night-report.py` | 8009 |
| `scripts/ops/nightly_stability.py` | 11554 |
| `scripts/ops/orchestrator-loop-worker.ps1` | 2613 |
| `scripts/ops/orchestrator-loop.ps1` | 6161 |
| `scripts/ops/otclient_external_bot_intake.py` | 14940 |
| `scripts/ops/otclient_helper_module_audit.py` | 32156 |
| `scripts/ops/otclient_helper_module_contract.py` | 27457 |
| `scripts/ops/otclient_helper_next_modules_plan.py` | 29072 |
| `scripts/ops/otclient_helper_profile_audit.py` | 5236 |
| `scripts/ops/otclient_helper_shell_budget_plan.py` | 12627 |
| `scripts/ops/otclient_input_contract_fixtures.py` | 13415 |
| `scripts/ops/phase5_nightly_checklist.py` | 10720 |
| `scripts/ops/phase5_nightly_sync.py` | 24770 |
| `scripts/ops/project_progress_diagram.py` | 6516 |
| `scripts/ops/queue_enqueue_job.py` | 1142 |
| `scripts/ops/release_evidence_pack.py` | 35872 |
| `scripts/ops/remove-mythibia-autosync-task.ps1` | 460 |
| `scripts/ops/remove-mythibia-watcher-task.ps1` | 819 |
| `scripts/ops/remove-phase5-morning-sync-task.ps1` | 415 |
| `scripts/ops/repo_hygiene_audit.py` | 8244 |
| `scripts/ops/repo_hygiene_migration_plan.py` | 7540 |
| `scripts/ops/rosetta_bundle.py` | 7981 |
| `scripts/ops/run-ghidra-enc3-analysis.ps1` | 1142 |
| `scripts/ops/run-ghidra-enc3-context.ps1` | 1184 |
| `scripts/ops/run-phase5-morning-sync.ps1` | 1246 |
| `scripts/ops/run-x64dbg-enc3-dynamic-pass.py` | 10370 |
| `scripts/ops/run_validator_with_preflight.py` | 1451 |
| `scripts/ops/runtime_path_guard.py` | 2780 |
| `scripts/ops/runtime_smoke_e2e_8001.py` | 1965 |
| `scripts/ops/smoke_must_pass.py` | 2644 |
| `scripts/ops/solteria_api_audit.py` | 9873 |
| `scripts/ops/solteria_helper_goal_audit.py` | 17499 |
| `scripts/ops/solteria_helper_release_gate.py` | 22463 |
| `scripts/ops/solteria_helper_sandbox_smoke_queue.py` | 12790 |
| `scripts/ops/sprint027_validate.py` | 8791 |
| `scripts/ops/sprint028_validate.py` | 11765 |
| `scripts/ops/sprint029_validate.py` | 5367 |
| `scripts/ops/sprint030_validate.py

[truncated]
```


## `AI/generated/SYMBOL_MAP.md`

```markdown
# Engine Brain Symbol Map

Generated at: `2026-07-11T12:51:23+00:00`

This is a lightweight map for navigation, not a full source dump.

## `agents/definitions.py`

- L24: def _normalize_agent(agent)
- L39: def _read_registry_payload(registry_path)
- L46: def _load_registry(registry_path)
- L58: def validate_registry_consistency(registry_path)
- L103: def get_agent_config(agent_id)
- L108: def list_agents()
- L113: def get_agents_for_task(task_id)
- L122: def _load_toolkit_registry(registry_path)
- L134: def list_toolkit_agents(registry_path)
- L139: def get_toolkit_agent_config(agent_id, registry_path)
- L144: class APICostOptimizerAgent
- L147: def __init__(self)
- L164: def score_action_risk(self, tool_name, payload)
- L172: def registry_config(self)

## `agents/toolkit/ctoai_foundry_agent/app.py`

- L31: class IncidentInput
- L39: class AgentResponse
- L49: class CTOAIFoundryRouter
- L52: def __init__(self)
- L73: def _append_evidence(self, kind, payload)
- L83: def _chat(self, model, prompt)
- L103: def triage(self, incident)
- L126: def finalize(self, incident, triage)
- L171: def invoke(self, incident)
- L181: def health()
- L186: def invoke(payload)
- L190: def run_cli()
- L203: def main()

## `alembic/env.py`

- L15: def _db_url()
- L29: def run_migrations_offline()
- L37: def run_migrations_online()

## `alembic/versions/20260521_0001_sprint0_baseline.py`

- L20: def upgrade()
- L25: def downgrade()

## `api/main.py`

- L32: def _env_bool(name, default)
- L39: def _env_int(name, default)
- L49: def _is_production_env()
- L57: def _is_weak_secret(secret)
- L85: def _backend_kind(url)
- L134: def _api_self_register_enabled()
- L138: def _api_self_register_code()
- L142: def _validate_api_security_config()
- L217: def _safety_telemetry_snapshot()
- L235: def _sanitize_assistant_content(content)
- L254: def _friendly_model_error(exc)
- L291: class Message
- L296: class ChatRequest
- L306: class OpenAIChatRequest
- L316: class RegisterRequest
- L324: class LoginRequest
- L329: class BootstrapRequest
- L335: class InviteRequest
- L340: class AcceptInviteRequest
- L344: class RoleUpdateRequest
- L348: def _estimate_chars(messages)
- L352: def _is_complex(messages)
- L357: def _low_quality(content, user_chars)
- L369: def _utc_now_iso()
- L373: def _atomic_write_json(path, payload)
- L408: def _display_path(path_value)
- L431: def _redact_release_evidence_text(value)
- L445: def _public_release_evidence_value(value, key)
- L462: def _public_audit_value(value, key)
- L479: def _read_release_evidence_payload(path)
- L495: def _hash_password(password)
- L499: def _verify_password(password, hashed)
- L506: def _sanitize_username(username)
- L515: def _seed_password(env_name)
- L522: def _seed_accounts()
- L555: def _default_account_seed_blocked()
- L559: def _read_auth_store_payload(path)
- L578: def _load_auth_store()
- L620: def _save_auth_store(store)
- L624: def _append_activity(store)
- L647: def _b64url_encode(data)
- L651: def _b64url_decode(data)
- L656: def _jwt_encode(payload)
- L667: def _jwt_decode(token)
- L692: def _issue_token(user)
- L703: def _extract_bearer(authorization)
- L716: def _first_forwarded_ip(value)
- L726: def _client_ip_from_request(request)
- L736: def _rate_limit_group(path)
- L746: def _rate_limit_for_group(group)
- L754: def _consume_rate_limit(ip, group, now_ts)
- L799: def _audit_actor_from_request(request)
- L813: def _append_audit_http(request, status, actor, meta)
- L839: async def security_middleware(request, call_next)
- L881: def _current_user(authorization)
- L904: def _require_roles(user, allowed)
- L909: def _select_models(req)
- L982: async def _call_model(model_name, backend_url, backend_key, messages, temperature, max_tokens)
- L1016: async def _execute_chat(req)
- L1104: def _safe_chat_route_info(route_info)
- L1120: def _require_chat_debug_route_user(user)
- L1130: def health()
- L1135: def status()
- L1156: def bootstrap(req)
- L1204: def register(req, authorization)
- L1270: def login(req)
- L1294: def me(authorization)
- L1300: def create_invite(req, authorization)
- L1337: def accept_invite(req, authorization)
- L1385: def community_members(authorization)
- L1405: def set_member_role(username, req, authorization)
- L1446: def community_feed(authorization)
- L1455: def community_invites(authorization)
- L1466: def release_evidence()
- L1547: async def chat(req, authorization)
- L1566: async def chat_completions(req, authorization)
- L1608: async def safety_metrics(authorization)
- L1622: async def safety_telemetry(authorization)
- L1631: async def safety_status()

## `api/startup_guard.py`

- L7: def _env_bool(name, default)
- L14: def _is_production_env()
- L18: def validate_early_security_config()

## `bot/action/__init__.py`

- L18: def set_current_state(state)
- L22: def _select_target()
- L32: def _attack_with_rotation()
- L38: def _follow_route()
- L63: def execute_action(action)

## `bot/action/combat.py`

- L24: def _can_act()
- L28: def attack_target()
- L36: def use_hp_potion()
- L43: def use_strong_hp_potion()
- L50: def use_mp_potion()
- L57: def use_antidote()

## `bot/action/input_backend.py`

- L24: def _noop_press(_key)
- L28: def _noop_click(_x, _y)
- L38: def _load_pydirectinput()
- L54: def _load_pyautogui()
- L79: def is_available()
- L83: def backend_name()
- L87: def _is_tibia_active_window()
- L104: def _can_dispatch_input()
- L112: def press(key)
- L118: def click(x, y)

## `bot/action/loot.py`

- L9: def loot_corpse()

## `bot/action/movement.py`

- L19: def _auto_follow_key()
- L23: def _auto_follow_interval_ms()
- L27: def _auto_follow_stuck_ms()
- L31: def _auto_follow_refresh_ms()
- L35: def walk_to(x, y)
- L46: def idle_move()
- L55: def _state_position_tuple(state)
- L72: def auto_follow(state)

## `bot/action/spell_rotation.py`

- L36: def _default_config()
- L51: def _load_config()
- L75: def _active_client_profile_lower()
- L79: def _merge_rotation_config(cfg)
- L113: def _active_window_title_lower()
- L129: def _detect_profession(level, cfg)
- L163: def cast_rotation_spell(level, profession_override)

## `bot/config/runtime_profile.py`

- L28: def _set_config_error(code, message, exc)
- L37: def last_config_error()
- L41: def _load_config()
- L93: def active_profile_name()
- L101: def _profile_values()
- L118: def _raw_value(key, default)
- L125: def get_str(key, default)
- L132: def get_int(key, default)
- L140: def get_float(key, default)
- L148: def get_bool(key, default)
- L160: def get_list(key, default)
- L175: def config_path()
- L179: def reload_config()
- L186: def _write_json_atomic(path, payload)
- L203: def save_profile_values(profile, updates)

## `bot/connection/ots_config.py`

- L11: def _env(key, default)
- L16: class OTSConfig
- L38: def is_configured(self)
- L41: def summary(self)
- L49: def _parse_region(s)
- L60: def get_config()
- L69: def _load_dotenv()

## `bot/dashboard/app.py`

- L42: def health()
- L46: def scheduler_status()
- L56: def stats()
- L71: def metrics()
- L103: def index()

## `bot/decision/brain.py`

- L19: def decide_action(state)

## `bot/decision/hunt_strategy.py`

- L21: def best_target_from_nearby(state)
- L42: def get_active_route(level, max_risk)
- L49: def get_potion_thresholds()
- L62: def next_waypoint(level)

## `bot/decision/ml_model.py`

- L76: def _load()
- L110: def save_qtable()
- L128: def _epsilon()
- L134: def _state_key(state)
- L144: def _row(table, key)
- L150: def predict_action(state)
- L172: def update_q(state, action, reward, next_state)
- L212: def compute_reward(prev_state, action, result, curr_state)

## `bot/decision/rules.py`

- L24: def _auto_follow_enabled()
- L29: class Rule
- L51: def evaluate_rules(state)

## `bot/main.py`

- L43: def _manual_action(state)
- L51: def _record_loop_telemetry(tick, elapsed_ms, stage, ok, details)
- L62: def run()
- L76: def _shutdown(sig, frame)
- L86: def _print_stats()

## `bot/overlay/macro_overlay.py`

- L32: def _now_iso()
- L36: def _default_config()
- L98: def _ensure_defaults(data)
- L110: def _load_config()
- L124: def _save_config(data)
- L130: def _normalize_macro(entry, index)
- L143: def _normalize_preset(entry, index)
- L153: def _pretty_age(remaining)
- L161: def _parse_steps(text)
- L170: def _normalize_step(step)
- L179: class MacroOverlayApp
- L180: def __init__(self, root)
- L264: def _build_editor(self, parent)
- L326: def _build_help(self, parent)
- L338: def _build_presets(self, parent)
- L357: def _field(self, parent, label, variable, row, col, width)
- L374: def _refresh_list(self)
- L384: def _selected_macro(self)
- L390: def _load_selected(self, index)
- L406: def _on_select(self, _event)
- L412: def _update_preview(self)
- L420: def _append_log(self, message)
- L427: def _refresh_timer(self)
- L436: def _collect_macro(self)
- L457: def _save_current(self)
- L472: def _run_steps(self, steps)
- L487: def _preview_steps(self, label, steps)
- L494: def _fire_preset(self, name, group, cooldown_ms, steps)
- L513: def worker()
- L528: def _fire_macro(self, macro)
- L555: def _fire_current(self)
- L558: def worker()
- L571: def _reset_current_cd(self)
- L578: def _new_macro(self)
- L584: def _duplicate_macro(self)
- L593: def _delete_macro(self)
- L604: def _reload(self)
- L613: def _tick(self)
- L619: def run()

## `bot/overlay/status_overlay.py`

- L41: class RailSwitch
- L44: def __init__(self, master)
- L69: def set_state(self, enabled)
- L73: def _on_click(self, _event)
- L78: def _draw(self)
- L122: class OverlayApp
- L123: def __init__(self, root)
- L382: def refresh(self)
- L412: def _toggle_pin(self)
- L415: def _set_alpha(self, value)
- L421: def _start_drag(self, event)
- L425: def _drag(self, event)
- L430: def _reload_config(self)
- L440: def _render_module_row(self, parent, label, key, enabled)
- L457: def _paint_module_switch(self, key, enabled)
- L463: def _module_auto_follow(self)
- L466: def _module_spell_rotation(self)
- L469: def _module_focus_guard(self)
- L472: def _sync_module_buttons(self)
- L481: def _toggle_module(self, key, desired_state)
- L494: def _save_follow_key(self)
- L504: def _save_follow_timing(self)
- L527: def _start_bot(self)
- L552: def _stop_bot(self)
- L569: def _open_macro_pad(self)
- L589: def _refresh_diagnostics(self)
- L609: def _on_close(self)
- L613: def _read_state(self)
- L623: def run()

## `bot/perception/memory_reader.py`

- L65: class _PROCESSENTRY32
- L81: class TibiaMemoryReader
- L84: def __init__(self, process_name)
- L91: def attach(self)
- L114: def detach(self)
- L124: def read_position(self)
- L133: def read_hp(self)
- L141: def read_mp(self)
- L149: def read_level(self)
- L152: def read_exp(self)
- L155: def read_all(self)
- L167: def _find_pid(self)
- L195: def _read_bytes(self, address, size)
- L210: def _read_int32(self, address)
- L216: def _read_int64(self, address)
- L227: def get_reader()

## `bot/perception/parser.py`

- L68: def _parse_region(raw)
- L78: def _scale_region(region, frame)
- L103: def _load_calibration()
- L145: def _bgr_range(mean_bgr, tolerance)
- L182: def _rescale_from_pct(pct, max_value)
- L186: def _stabilize_resource_value(current, current_max, prev, prev_max)
- L209: def _bar_percentage(frame, region, low, high)
- L239: def _has_target(frame, region)
- L247: def _target_hp_pct(frame, region)
- L254: def _template_target_match(frame)
- L273: def _ocr_reader()
- L285: def _ocr_extract_ratios(frame)
- L318: def reload_calibration()
- L336: def parse_game_state(screenshot_pixels, prev_state)

## `bot/perception/screen.py`

- L18: def _capture_window_pixels()
- L27: def capture_screen(region)
- L40: def capture_region_pixels(region)

## `bot/perception/state.py`

- L7: class Position
- L14: class GameState
- L31: def hp_pct(self)
- L35: def mp_pct(self)
- L38: def is_low_hp(self, threshold)
- L41: def is_low_mp(self, threshold)

## `bot/perception/window.py`

- L40: def _window_title_patterns()
- L45: def _active_window_title_hint()
- L58: class _BITMAPINFOHEADER
- L74: class _BITMAPINFO
- L82: class WindowHandle
- L88: def width(self)
- L92: def height(self)
- L96: def left(self)
- L100: def top(self)
- L104: def find_tibia_window()
- L115: def _enum_cb(hwnd, _lParam)
- L193: def capture_window(handle)
- L283: def bring_to_front(handle)

## `bot/safety/humanizer.py`

- L25: def human_delay(min_ms, max_ms)
- L33: def reaction_delay()
- L38: def combat_pause()
- L56: def think_pause()
- L64: def loot_delay()
- L69: def potion_delay()
- L79: def bezier_path(start, end, steps)
- L94: def misclick_jitter(x, y)
- L99: def move_mouse_human(start, end)
- L119: def random_afk_twitch()

## `bot/safety/nonsecurity_random.py`

- L18: def random()
- L22: def randint(left, right)
- L26: def uniform(left, right)
- L30: def gauss(mean, sigma)
- L34: def choice(items)
- L38: def shuffle(items)

## `bot/safety/scheduler.py`

- L33: def _env_int(key, default)
- L40: class SessionScheduler
- L43: def __init__(self, active_start, active_end, session_min_h, session_max_h, break_min_m, break_max_m)
- L68: def should_run(self)
- L100: def tick(self)
- L107: def session_elapsed_s(self)
- L113: def status(self)
- L134: def _in_active_window(self, dt)
- L144: def _plan_session(self)
- L166: def _start_break(self)
- L186: def get_scheduler()

## `bot/safety/session.py`

- L23: class SessionManager
- L24: def __init__(self)
- L33: def is_active(self)
- L47: def stop(self)
- L50: def _take_break(self)
- L59: def _is_night()

## `ctoa.ps1`

- L20: function Get-CliVpsHost
- L31: function Get-PythonExe
- L39: function Resolve-ControlCenterUrl
- L91: function Invoke-FromRoot
- L111: function Invoke-FromRootCapture
- L141: function Get-CommandDictionary
- L168: function Show-Help
- L248: function Get-GitExe
- L262: function Get-NpmExe
- L273: function Get-WorktreeSummary
- L295: function Show-Next
- L318: function Open-ControlCenter
- L373: function Resolve-Sprint
- L387: function Invoke-ValidateSprint
- L407: function Invoke-Nightly
- L424: function Invoke-Up
- L438: function Invoke-Test
- L449: function Invoke-Doctor
- L462: function Invoke-DevProfile
- L467: function Invoke-OpsProfile
- L472: function Invoke-ProdProfile
- L482: function Invoke-VpsAction
- L522: function Invoke-VpsActionCapture
- L570: function Invoke-RunnerCommand
- L582: function Invoke-ReportCommand
- L595: function Invoke-MobileCommand
- L607: function Invoke-LogsCommand
- L621: function Invoke-StatusSnapshot
- L701: function Invoke-DashboardSnapshot
- L705: function Invoke-ReportNow
- L709: function Invoke-OtProfileBuilder
- L723: function Invoke-OtHelperPreview
- L733: function Invoke-OtHelperMockup
- L743: function Invoke-OtHelperDeploy
- L764: function Invoke-OtTestLoop
- L779: function Invoke-EngineBrain
- L810: function Get-ValueOrDefault
- L822: function Show-Menu

## `ctoa_ui_prefs.lua`

- L13: lua hud

## `docs/site/script.js`

- L21: symbol createIdeaId
- L28: symbol encodeSecret
- L32: symbol nowTs
- L36: symbol isPrivateIpv4Host
- L49: symbol isLocalDevHost
- L54: symbol normalizeApiBase
- L79: symbol inferSameOriginApiBase
- L86: symbol getApiBase
- L91: symbol setApiBase
- L100: symbol syncApiBaseInputs
- L112: symbol getApiToken
- L116: symbol setApiSession
- L134: symbol getConsoleUrl
- L145: symbol apiRequest
- L178: symbol loadJson
- L191: symbol saveJson
- L195: symbol loadSessionJson
- L208: symbol saveSessionJson
- L212: symbol canUseIdeasBackend
- L216: symbol loadIdeas
- L220: symbol saveIdeas
- L226: symbol refreshIdeasFromBackend
- L236: symbol addIdea
- L267: symbol removeIdea
- L278: symbol clearIdeas
- L287: symbol formatDate
- L298: symbol updateIdeaCount
- L315: symbol downloadJsonFile
- L327: symbol renderIdeas
- L386: symbol setupIdeaForm
- L435: symbol getDefaultAdminState
- L443: symbol loadAdminState
- L448: symbol saveAdminState
- L452: symbol loadAdminStateFromBackend
- L470: symbol getAdminUsers
- L480: symbol saveAdminUsers
- L485: symbol getUserRecord
- L491: symbol isAdminLocked
- L496: symbol getLockSecondsLeft
- L501: symbol resetAuthFailures
- L506: symbol markAuthFailure
- L516: symbol isAdminLoggedIn
- L528: symbol getAdminSession
- L535: symbol isOwnerSession
- L540: symbol setAdminLoggedIn
- L552: symbol clearAdminSessionState
- L558: symbol applyAdminState
- L607: symbol setupAdminDrawerHover
- L654: symbol showAuthModal
- L672: symbol setupAdminAuth
- L975: symbol setupMenuPanels
- L1200: symbol setupDecks

## `mobile_console/app.py`

- L48: def generate_latest()
- L98: def _is_production_env()
- L106: def _is_windows_host()
- L108: def _command_exists(name)
- L112: def _read_orchestrator_loop_pid()
- L122: def _windows_orchestrator_state()
- L136: def _service_is_active(unit)
- L150: def _disk_probe()
- L171: def _lab_tasks_probe()
- L189: def _require_http_url(url)
- L196: def _require_local_runtime_api_base_url(url, label)
- L218: def _require_local_runtime_proxy_path(path, label)
- L243: def _private_intel_targets_allowed()
- L252: def _is_private_or_local_intel_host(hostname)
- L269: def _safe_proxy_error(exc)
- L273: def _intel_api_health_probe()
- L306: def _intel_api_proxy(path, timeout)
- L363: def _ctoa_api_proxy(path, timeout)
- L412: def _load_json_file(path)
- L429: def _is_production_env()
- L433: def _read_generated_manifest_json(path)
- L450: def _atomic_local_state_temp_path(path)
- L454: def _remove_local_state_temp(path)
- L461: def _atomic_write_local_json(path, payload)
- L475: def _atomic_write_text(path, text)
- L488: def _atomic_write_bytes(path, data)
- L501: def _read_local_json_bounded(path, max_bytes)
- L515: def _read_text_bounded(path, max_bytes)
- L527: def _read_tail_text_bounded(path, lines, max_bytes)
- L543: def _read_json_bounded(path, max_bytes)
- L558: def _normalize_package_tier(value)
- L565: def _is_windows_host()
- L573: def _prom_get_or_create_counter(name, documentation, labels)
- L586: def _prom_get_or_create_histogram(name, documentation, labels)
- L626: async def enforce_mobile_console_capability(request, call_next)
- L642: async def collect_http_metrics(request, call_next)
- L663: class CommandRequest
- L669: class ServerRegisterRequest
- L673: class IntelMissionRequest
- L681: class GuardedActionRequest
- L686: class QueueJobRequest
- L689: class AuthLoginRequest
- L694: class AdminSettingsPayload
- L700: class IdeaCreatePayload
- L704: class LiveDashboardProfilePayload
- L709: class RegisterAccountPayload
- L715: class SelfRegisterPayload
- L721: class ChangePasswordPayload
- L725: class ChangeRolePayload
- L747: def _default_admin_settings()
- L755: def _normalize_admin_settings(payload)
- L765: def _read_admin_settings()
- L775: def _write_admin_settings(payload)
- L782: def _normalize_idea_item(payload, fallback_author)
- L804: def _read_idea_parking()
- L823: def _write_idea_parking(ideas)
- L848: def _mobile_token()
- L853: def _full_access()
- L857: def _self_register_enabled()
- L866: def _self_register_code()
- L870: def _session_cookie_secure()
- L879: def _safe_command_specs()
- L924: def _allowed_commands()
- L928: def _normalize_user(username)
- L932: def _admin_credentials()
- L946: def _validate_security_config()
- L976: def _extract_bearer(authorization)
- L985: def _create_session(username, role)
- L999: def _get_session(token)
- L1012: def _delete_session(token)
- L1019: def _delete_sessions_for_user(username)
- L1031: def _try_auth_context(x_ctoa_token, authorization, x_ctoa_session, ctoa_session)
- L1065: def _token_valid(x_ctoa_token, authorization, x_ctoa_session, ctoa_session)
- L1079: def _csrf_required(request, ctx)
- L1087: def _verify_csrf(request, ctx, x_csrf_token)
- L1096: def require_authenticated(request, x_ctoa_token, authorization, x_ctoa_session, x_csrf_token, ctoa_session)
- L1116: def require_operator(ctx)
- L1123: def require_owner(ctx)
- L1130: def _slice_command_output(value)
- L1134: def _redact_audit_text(value, max_length)
- ... 92 more symbols omitted

## `mobile_console/services/admin_settings_service.py`

- L6: class AdminSettingsService
- L9: def __init__(self, read_settings, write_settings)
- L17: def get(self)
- L20: def save(self, payload)

## `mobile_console/services/ideas_service.py`

- L8: class IdeasService
- L11: def __init__(self, read_items, write_items, normalize_item)
- L21: def list_items(self)
- L24: def add(self, text, author)
- L41: def delete(self, idea_id)
- L50: def clear(self)

## `mobile_console/static/app.js`

- L14: symbol getToken
- L18: symbol getSessionToken
- L22: symbol setToken
- L26: symbol api
- L49: symbol refreshOwnerUi
- L65: symbol applyRoleState
- L73: symbol setRoleBadge
- L142: symbol checkAuthAuto
- L397: symbol clearElement
- L403: symbol createTextElement
- L412: symbol appendText
- L416: symbol safeStatusKey
- L421: symbol createStatusBadge
- L441: symbol createEmptyTrend
- L445: symbol renderReasonGroup
- L463: symbol renderTimeline
- L493: symbol bindTrendToggles
- L506: symbol statusClassFromSeverity
- L513: symbol appendEmptyTableRow
- L523: symbol renderTrendBars
- L554: symbol createTrendToggle
- L564: symbol appendReasonGroup
- L572: symbol renderTrendSummary
- L634: symbol renderDashboardStatusContext
- L850: symbol fetchAgentLog

## `mobile_console/static/dashboard_helpers.js`

- L2: symbol escapeHtml
- L11: symbol badgeStatus

## `prompts/braver_templates.py`

- L11: class _SafeFormatDict
- L12: def __missing__(self, key)
- L138: def get_template(template_type)
- L143: def normalize_component_name(component)
- L148: def render_template(template_type, component)
- L155: def get_all_components()

## `runner/agents/activation_agent.py`

- L43: def _slug(value)
- L47: def _targets()
- L75: def _write_json(path, payload)
- L80: def _write_text(path, text)
- L85: def _persist_manifest(server_id, manifest)
- L92: def _run_sync_hook()
- L127: def _character_plan(server_slug)
- L142: def _bot_profile(server, signal, target_dir)
- L161: def _deploy_script(server_slug)
- L173: def _bootstrap_lua(server_name, bot_profile_path)
- L189: def run_once()

## `runner/agents/brain_v2.py`

- L89: def _get_daily_counts()
- L104: def _existing_task_ids(server_id)
- L112: def _available_data_types(server_id)
- L120: def plan_for_server(server_id)
- L167: def run_once()

## `runner/agents/catalog_agent.py`

- L110: def _catalog_profile()
- L118: def _parse_window_hours(window, fallback_start, fallback_end)
- L135: def _hour_in_window(hour, start, end)
- L141: def _source_allowed_now(source_url, profile)
- L170: def _source_priority(source_url)
- L178: def _default_sources()
- L185: def _fetch_text(url)
- L213: def _is_candidate_url(url)
- L232: def _extract_candidates(source_url, body)
- L260: def _count_players_hint(text)
- L274: def _score_candidate(source_url, context)
- L320: def _upsert_server(url)
- L336: def _write_signal(server_id, source_url, score, tags, pop_hint, context, detail)
- L364: def _enrich_existing_servers()
- L444: def run_once()

## `runner/agents/db.py`

- L39: class DbConnectConfig
- L48: def _connect_config()
- L62: def _sanitize_db_error(exc)
- L72: def get_pool()
- L82: def get_conn()
- L96: def query_one(sql, params)
- L104: def query_all(sql, params)
- L111: def execute(sql, params)
- L117: def log_run(agent, status, message)

## `runner/agents/executor.py`

- L40: def now_iso()
- L44: def _safe_repo_relative_path(path_str)
- L71: def write_deliverable(path_str, title, body)
- L83: def get_llm_provider()
- L95: def invoke_llm_for_task(task_id, prompt, context)
- L123: class TrackAAgent
- L133: def execute(task_id, deliverables)
- L173: def create_runbook_disk_emergency()
- L285: def create_validation_checklist()
- L418: def create_consistency_report()
- L451: class TrackBAgent
- L461: def execute(task_id, deliverables)
- L487: def enhance_weekly_report()
- L493: class TrackCAgent
- L503: def execute(task_id, deliverables)
- L537: def create_drift_checker()
- L642: class TrackDAgent
- L652: def execute(task_id, deliverables)
- L678: def create_sprint_governance()
- L861: def execute_agent_for_task(task)

## `runner/agents/generator_agent.py`

- L36: def _now_iso()
- L40: def _safe_output_path(base_dir, output_file)
- L70: def _safe_output_dir(base_dir, relative_dir)
- L76: def _write_run_manifest(run_started_at, generated, failed)
- L117: def _server_ctx(server_id)
- L152: def _safe_lua_string(s)
- L157: def _render(template_id, ctx)
- L168: def _tpl_auto_heal(ctx)
- L192: def _tpl_auto_reconnect(ctx)
- L215: def _tpl_loot_filter(ctx)
- L251: def _tpl_cavebot_pathing(ctx)
- L280: def _tpl_target_selector(ctx)
- L305: def _tpl_anti_stuck(ctx)
- L333: def _tpl_alarmy(ctx)
- L370: def _tpl_healer_profiles(ctx)
- L404: def _tpl_flee_logic(ctx)
- L435: def _tpl_target_blacklist(ctx)
- L460: def _tpl_auto_resupply(ctx)
- L489: def _tpl_server_blacklist(ctx)
- L516: def _tpl_server_loot_map(ctx)
- L543: def _tpl_highscore_scout(ctx)
- L568: def _tpl_server_stats(ctx)
- L590: def _tpl_player_tracker(ctx)
- L620: def _tpl_hunt_orchestrator(ctx)
- L710: def _tpl_economy_bot(ctx)
- L749: def _tpl_pvp_guard(ctx)
- L778: def _tpl_depot_manager(ctx)
- L804: def _tpl_gold_tracker(ctx)
- L827: def _tpl_bank_automation(ctx)
- L854: def _tpl_human_delay(ctx)
- L878: def _tpl_break_scheduler(ctx)
- L913: def _tpl_login_randomizer(ctx)
- L940: def _tpl_rune_maker(ctx)
- L963: def _tpl_combo_spells(ctx)
- L990: def _tpl_area_spell_ctrl(ctx)
- L1026: def _tpl_exp_tracker(ctx)
- L1050: def _tpl_session_log(ctx)
- L1075: def _tpl_respawn_optimizer(ctx)
- L1146: def _slug(url)
- L1153: def generate_module(mod)
- L1220: def run_once()

## `runner/agents/ingest_agent.py`

- L36: def _fetch_json(url)
- L64: def _normalise_monsters(data)
- L81: def _normalise_items(data)
- L98: def _normalise_players(data)
- L114: def _normalise_highscores(data)
- L131: def _normalise_server_info(data)
- L157: def _detect_type(path)
- L165: def ingest_server(server_id, base_url)
- L219: def run_once()

## `runner/agents/orchestrator.py`

- L42: def run_pipeline()

## `runner/agents/publisher_agent.py`

- L44: def _criteria_met(today_str)
- L73: def _collect_validated()
- L80: def _create_zip(today_str, mods)
- L92: def _write_manifest(today_str, mods, zip_path)
- L113: def _git_commit_release(manifest_path, tag)
- L135: def _gh_release(tag, zip_path, manifest_path)
- L159: def run_once()

## `runner/agents/routing.py`

- L6: def select_track(domain)

## `runner/agents/scout_agent.py`

- L157: def _fetch(url)
- L198: def _safe_slug(url)
- L202: def _dedupe_paths(paths)
- L213: def _infer_profile(base_url)
- L221: def _force_generic_hosts()
- L226: def _probe_paths(server_id, base_url, paths, source, probed, deadline)
- L273: def scout_server(server_id, base_url)
- L379: def run_once()

## `runner/agents/validator_agent.py`

- L44: def _luac_check(path)
- L64: def _bracket_balance(src)
- L76: def _py_compile_check(path)
- L90: def validate_lua(path, src)
- L131: def validate_python(path, src)
- L157: def validate_module(mod)
- L210: def run_once()

## `runner/alert_rules.py`

- L104: def check_generation_failed_spike(reason_counts, max_fails)

## `runner/close_on_gate.py`

- L14: def github_api(method, url, token, payload)
- L36: def parse_waiting_task_ids(issue_body)
- L58: def main()

## `runner/daily_insights.py`

- L22: def parse_iso(ts)
- L31: def load_yaml(path)
- L41: def github_api(method, url, token, payload)
- L63: def build_daily_comment(backlog, state)
- L148: def comment_daily_insight(comment_body)
- L178: def main()

## `runner/drift_checker.py`

- L28: def now_iso()
- L32: def check_service_status(service)
- L65: def main()

## `runner/generated_manifest_safety.py`

- L9: def _is_relative_to(path, root)
- L17: def resolve_latest_manifest_path(manifests_dir, latest_payload)
- L50: def iter_safe_manifest_files(manifests_dir)
- L95: def public_manifest_path(manifest_path, manifests_dir)

## `runner/generator_validator_samples.py`

- L28: def now_iso()
- L32: def load_latest_manifest(manifests_dir)
- L58: def build_generator_sample(latest_manifest)
- L98: def build_validator_sample(latest_manifest)
- L136: def write_json(path, payload)
- L141: def write_markdown(path, generator_payload, validator_payload)
- L161: def main()

## `runner/health_metrics.py`

- L33: def now_iso()
- L37: def _atomic_temp_path(path)
- L41: def _remove_temp_path(path)
- L48: def _atomic_write_json(path, payload)
- L62: def _read_proc_stat_totals()
- L74: def read_cpu_percent(sample_seconds)
- L117: def read_memory_percent()
- L164: def read_disk_percent(path)
- L171: def read_uptime_human()
- L192: def read_load_average()
- L199: def check_processes(processes_to_check)
- L229: def _run_tool(name, args)
- L251: def collect_metrics()
- L320: def check_thresholds(metrics)
- L340: def format_health_dashboard(metrics, alerts)
- L394: def publish_to_github(dashboard_md)
- L424: def persist_snapshot(metrics, alerts)
- L432: def print_live_line(metrics, alerts)
- L444: def maybe_run_disk_cleanup(metrics, now_ts, enabled, threshold, cooldown_seconds, command, last_run_ts)
- L499: def run_once(publish)
- L512: def run_watch(interval, samples, publish, cpu_sustain, disk_auto_cleanup, disk_cleanup_threshold, disk_cleanup_cooldown, disk_cleanup_cmd)
- L569: def build_parser()
- L620: def main()

## `runner/health_trend.py`

- L15: def parse_iso(ts)
- L22: def read_rows(path)
- L39: def avg(values)
- L45: def summarize_window(rows, since)
- L100: def print_window(label, summary)
- L115: def main()

## `runner/http_safety.py`

- L46: def env_enabled(name)
- L50: def require_http_url(url)
- L58: def require_github_repository(repo)
- L75: def require_github_api_url(url)
- L107: def require_loopback_http_url(url)
- L125: def _reject_token_query(parsed, label)
- L131: def _is_ip_literal(host)
- L139: def _reject_private_discovery_host(host, label)
- L163: def require_public_discovery_url(url)
- L179: def _reject_url_secret_parts(parsed, label)
- L191: def require_model_backend_url(url)
- L205: def require_azure_service_url(url)
- L217: def _require_strict_path_parts(parsed, label)
- L232: def require_notify_webhook_url(url)
- L250: def require_discord_webhook_url(url)
- L264: def discovery_ssl_context(insecure_env_name)

## `runner/hybrid_bot/bot_runner.py`

- L36: class BotConfig
- L49: class ActionExecutor
- L52: def __init__(self, send_command)
- L61: def execute(self, action, parameters)
- L105: class HybridBotRunner
- L123: def __init__(self, config, screenshot_provider, command_executor)
- L144: def command_callback(cmd)
- L172: async def run(self)
- L189: async def _tick(self)
- L266: def _capture_frame(self)
- L276: def _collect_perception(self, frame)
- L287: def _apply_state_updates(self, position, health, creatures)
- L312: def _decide_and_execute(self)
- L319: def _emit_tick_telemetry(self, decision)
- L327: def stop(self)
- L335: def set_waypoints(self, waypoints)
- L341: def start_hunting_location(self, name)
- L348: def _print_final_report(self)
- L363: def get_status(self)

## `runner/hybrid_bot/cli.py`

- L37: async def cmd_run(args)
- L74: def cmd_benchmark(args)
- L115: def cmd_export(args)
- L129: def main()

## `runner/hybrid_bot/clock.py`

- L8: def utc_now()

## `runner/hybrid_bot/command_executor.py`

- L27: class _FallbackKey
- L36: class _FallbackButton
- L48: class CommandExecutor
- L74: def __init__(self, base_delay_ms, typing_delay_ms, enable_delays)
- L101: def execute(self, command)
- L181: async def execute_async(self, command)
- L187: def _type_spell(self, spell_name)
- L197: def _press_key(self, key)
- L219: def _press_named_key(self, key_name)
- L226: def _press_combo(self, combo)
- L249: def _resolve_key(self, key_name)
- L278: def _attack_target(self)
- L300: def _wait(self)
- L305: def _reconnect(self)
- L324: def _apply_delay(self)
- L333: def set_delaying(self, enable)
- L338: def get_stats(self)
- L349: class BatchCommandExecutor
- L361: def __init__(self, executor)
- L366: def add(self, command, duration_ms)
- L376: async def execute(self)
- L395: def clear(self)

## `runner/hybrid_bot/file_safety.py`

- L10: def resolve_output_dir(output_dir)
- L19: def safe_child_path(base_dir, relative_path)

## `runner/hybrid_bot/gameplay_engine.py`

- L27: class GameplayMode
- L35: class CombatStats
- L45: def dps(self)
- L50: def increment_kill(self, xp_gain, loot_value)
- L57: class CombatEngine
- L60: def __init__(self, player_level)
- L72: def _build_priority_queue(self)
- L82: def choose_target(self, visible_creatures)
- L129: def should_flee(self, health_percent, critical_threshold)
- L134: class MovementEngine
- L137: def __init__(self, max_distance_before_recall)
- L150: def set_home(self, x, y, z)
- L155: def set_hunting_path(self, waypoints)
- L161: def get_next_waypoint(self, current_x, current_y)
- L179: def should_recall_home(self, current_x, current_y)
- L191: class LootEngine
- L194: def __init__(self, max_backpack_items, skip_items)
- L210: def should_pickup_loot(self, item_name)
- L223: def should_drop_loot(self, backpack_items)
- L228: class HealingEngine
- L231: def __init__(self)
- L241: def should_cast_heal(self, health_percent, heal_threshold)
- L252: def should_cast_buff(self, buff_name)
- L259: def record_heal(self)
- L263: def record_buff(self, buff_name)
- L268: class GameplayEngine
- L275: def __init__(self, mode, player_level)
- L296: def make_decision(self, player_state, visible_creatures, time_delta)
- L344: def set_mode(self, mode)
- L349: def get_stats(self)

## `runner/hybrid_bot/interactive_mode.py`

- L31: class InteractiveCommand
- L52: class InteractiveState
- L59: def update_activity(self)
- L64: class KeyboardListener
- L71: def __init__(self)
- L76: async def start(self, command_queue)
- L88: def on_key_press(key)
- L106: def _map_key_to_command(self, key)
- L142: def stop(self)
- L151: class InteractiveMode
- L158: def __init__(self, command_executor, screenshot_callback)
- L184: async def run(self)
- L212: async def _handle_command(self, command)
- L279: async def _periodic_update(self)
- L284: def _print_status(self)
- L301: def _print_session_stats(self)

## `runner/hybrid_bot/metrics.py`

- L29: class MetricsSnapshot
- L58: class SessionMetrics
- L77: def __post_init__(self)
- L82: class MetricsCollector
- L92: def __init__(self, output_dir, snapshot_interval_seconds, disable_file_output)
- L136: def record_snapshot(self, location, duration_seconds, xp_gained, monsters_killed, loot_value_gold, supplies_cost_gold, player_health_percent, player_level, distance_traveled_sqm, notes)
- L195: def _append_snapshot_to_file(self, snapshot)
- L204: def _append_event_to_file(self, event)
- L214: def load_snapshots_from_file(self, filepath)
- L234: def record_event(self, name, duration_ms, ok, error, details)
- L256: def get_session_summary(self)
- L293: def get_location_stats(self, location)
- L314: def print_session_report(self)
- L350: def export_metrics_csv(self, output_file)
- L377: def compare_with_manual_metrics(bot_metrics, manual_xp_per_hour, manual_balance_per_hour)

## `runner/hybrid_bot/pathfinding.py`

- L24: class SQMType
- L38: class Coordinate
- L44: def distance_to(self, other)
- L50: class PathNode
- L58: def __post_init__(self)
- L61: def __lt__(self, other)
- L64: def __hash__(self)
- L67: def __eq__(self, other)
- L74: class PathSegment
- L83: class Pathfinder
- L95: def __init__(self, player_level, sqm_cost_map, base_movement_ms)
- L120: def find_path(self, start, goal, sqm_terrain, max_iterations)
- L207: def _get_neighbors(self, pos)
- L225: def _is_valid_position(self, pos)
- L230: def _calculate_move_cost(self, sqm_type)
- L236: def _reconstruct_path(self, node, sqm_terrain)
- L263: def estimate_travel_time_ms(self, segments)
- L268: class WaypointBuffer
- L276: def __init__(self, waypoints)
- L281: def get_current_waypoint(self)
- L287: def advance(self)
- L294: def reset(self)
- L298: def distance_to_current(self, pos)
- L308: def generate_terrain_map(map_data)

## `runner/hybrid_bot/performance_profiler.py`

- L28: class TimingSnapshot
- L39: def to_dict(self)
- L52: class PerformanceStats
- L82: def update(self, snapshot)
- L116: def print_report(self)
- L144: class PerformanceProfiler
- L162: def __init__(self, output_dir)
- L176: class TimingContext
- L179: def __init__(self, profiler, timer_name)
- L184: def __enter__(self)
- L188: def __exit__(self, exc_type, exc_val, exc_tb)
- L206: def measure(self, timer_name)
- L218: def record_snapshot(self)
- L225: def get_stats(self)
- L229: def export_to_json(self, filename)
- L245: def print_report(self)

## `runner/hybrid_bot/prompt_logic.py`

- L25: class Action
- L40: class GameState
- L58: class Decision
- L67: class PromptLogic
- L79: def __init__(self, use_llm, model_name)
- L102: def decide_action_heuristic(self, state)
- L169: def decide_action_with_llm(self, state)
- L208: def make_decision(self, state)
- L228: def _build_state_prompt(self, state)
- L253: def _get_system_prompt(self)
- L275: def _parse_llm_response(self, response)
- L300: def prompt_training_mode(level, current_xp_percent)
- L309: def prompt_hunting_profit(balance_per_hour)
- L318: def prompt_resource_management(supplies_cost, loot_value)

## `runner/hybrid_bot/screenshot_provider.py`

- L36: class ScreenshotProvider
- L46: def __init__(self, window_title, monitor_index, use_mss, game_window_bounds)
- L73: def _initialize_capture_method(self)
- L92: def capture(self)
- L111: def _capture_mss(self)
- L142: def _capture_pil(self)
- L163: def get_bounds(self)
- L179: def set_bounds(self, bounds)
- L184: def close(self)
- L193: def find_tibia_window()

## `runner/hybrid_bot/state_manager.py`

- L26: class PlayerState
- L41: def position(self)
- L45: def is_alive(self)
- L49: def is_critical(self)
- L54: class TargetState
- L64: def position(self)
- L68: def is_valid(self)
- L73: class LocationMetrics
- L83: def elapsed_minutes(self)
- L87: def xp_per_hour(self)
- L92: def balance_per_hour(self)
- L98: def supplies_per_hour(self)
- L103: class StateManager
- L114: def __init__(self, initial_level)
- L129: def update_player_state(self, x, y, z, hp_percent, mp_percent, is_poisoned, is_paralyzed)
- L148: def update_target(self, name, x, y, distance, is_engaged, health_percent)
- L165: def clear_target(self)
- L169: def update_inventory(self, items)
- L175: def start_location(self, name)
- L187: def record_monster_kill(self, xp_gain, loot_value)
- L194: def record_supply_cost(self, cost)
- L200: def should_heal(self)
- L204: def is_critical_health(self)
- L208: def should_rotate_location(self)
- L218: def is_inventory_full(self, capacity_percent_threshold)
- L228: def snapshot(self)
- L252: def print_summary(self)
- L276: def get_location_history(self)

## `runner/hybrid_bot/template_library.py`

- L38: def _safe_template_component(value, label)
- L52: def _require_template_source_url(url)
- L68: class Template
- L80: class TemplateLibrary
- L93: def __init__(self, cache_dir, server_url, use_cache)
- L123: def load_creatures(self, creature_names)
- L146: def _load_creature(self, name)
- L183: def load_minimap_sections(self, world_bounds, section_size)
- L230: def _cache_file(self, tpl_type, name)
- L241: def _load_from_disk(self, path, tpl_type, name)
- L277: def _load_from_server(self, url, tpl_type, name)
- L321: def save_template(self, template)
- L334: def get_creature(self, name)
- L338: def get_minimap_section(self, x, y, z)
- L343: def get_all_creatures(self)
- L349: def get_stats(self)
- L366: def print_stats(self)
- L401: def create_default_library(cache_dir)

## `runner/hybrid_bot/vision_layer.py`

- L29: def _vision_deps_available()
- L34: class GPSPosition
- L43: class HealthState
- L51: class Creature
- L65: class VisionLayer
- L75: def __init__(self, templates_dir)
- L92: def _load_templates(self)
- L112: def detect_position_from_minimap(self, minimap_screenshot)
- L169: def detect_health_from_healthbar(self, healthbar_region)
- L226: def detect_creatures_from_sprites(self, game_screen, creature_db)
- L285: def detect_engagement_from_target_window(self, target_window)
- L318: def extract_healthbar_region(game_screen, ui_layout)
- L345: def extract_minimap_region(game_screen, ui_layout)
- L366: def extract_target_window(game_screen, ui_layout)

## `runner/issue_sync.py`

- L20: def github_api(method, url, token, payload)
- L42: def load_backlog()
- L50: def make_issue_title(task)
- L54: def make_issue_body(backlog_id, task)
- L84: def list_open_issues(base, token)
- L101: def group_backlog_issues_by_task_id(open_issues)
- L116: def split_primary_and_duplicates(issues_by_task_id)
- L133: def main()

## `runner/llm_providers/__init__.py`

- L11: class LLMProvider
- L15: def complete(self, system_prompt, user_prompt, temperature, max_tokens)
- L26: def health(self)
- L31: def get_provider()

## `runner/llm_providers/azure_foundry.py`

- L19: class AzureFoundryProvider
- L22: def __init__(self)
- L39: def health(self)
- L43: def complete(self, system_prompt, user_prompt, temperature, max_tokens)

## `runner/llm_providers/local_model.py`

- L15: class LocalModelProvider
- L18: def __init__(self)
- L30: def health(self)
- L40: def complete(self, system_prompt, user_prompt, temperature, max_tokens)

## `runner/mythibia_local_brain.py`

- L98: def now_iso()
- L102: def ensure_queue()
- L129: def render(template_name)
- L148: def generate()

## `runner/pipeline/scheduler.py`

- L6: def count_active_tasks(tasks, active_states)
- L10: def build_new_task_candidates(tasks, priority_rank)

## `runner/process_safety.py`

- L18: class ExecutableUnavailableError
- L27: def _resolve_candidate(value)
- L42: def resolve_executable(name)
- L75: def resolve_git()
- L81: def resolve_python()
- L90: def run_trusted(command)
- L97: def start_trusted(command)

## `runner/queue_worker.py`

- L29: def _redis_url_for_log(raw_url)
- L55: def _parse_job_payload(payload_raw)
- L65: def _setup_logging()
- L77: def _run_action(action)
- L100: def main()

## `runner/response_guardrails.py`

- L29: def validate_response(text)
- L51: def is_response_compliant(text)
- L55: def validate_operational_structure(text)
- L68: def is_operational_structure_compliant(text)

## `runner/runner.py`

- L33: def _default_ci_artifacts_dir(root)
- L71: def now_iso()
- L75: def _atomic_temp_path(path)
- L79: def _remove_temp_path(path)
- L86: def load_yaml(path)
- L94: def save_yaml(path, payload)
- L107: def save_json(path, payload)
- L123: def load_backlog()
- L129: def init_state(backlog)
- L161: def load_state(backlog)
- L201: def status_rank(status)
- L208: def priority_rank(priority)
- L213: def transition_task(task, new_status, reason)
- L233: def tick(backlog, state, invoke_agents)
- L279: def approve_task(state, task_id)
- L294: def execute_task_agent(task, backlog)
- L322: def estimate_next_approval_eta_hours(tasks)
- L341: def build_execution_summary(backlog, state)
- L391: def build_report(backlog, state)
- L501: def github_api(method, url, token, payload)
- L523: def upsert_live_issue(markdown)
- L561: def main()

## `runner/status_sync.py`

- L32: def parse_iso(ts)
- L41: def load_state()
- L51: def github_api(method, url, token, payload)
- L73: def ensure_status_labels(base, token)
- L92: def task_map(state)
- L104: def backlog_issue_map(open_issues)
- L115: def list_open_issues(base, token)
- L132: def desired_status_label(task)
- L137: def normalize_alert_mode(value)
- L144: def sync_status_labels(base, token, tasks, issues)
- L175: def build_sla_alert(tasks, issues, threshold_hours, alert_mode)
- L241: def update_live_issue_sla_section(base, token, live_issue_number, body)
- L276: def main()

## `runner/tibia_sources.py`

- L65: def utc_now()
- L70: class CollectedSource
- L81: class RawSnapshot
- L95: class NormalizedRecord
- L102: class UpdateEvent
- L112: class SourceCollector
- L113: def fetch(self, source_kind, cursor)
- L117: class SourceParser
- L118: def parse(self, snapshot)
- L122: class ClientAdapter
- L123: def detect(self)
- L127: class HttpTibiaCollector
- L130: def __init__(self)
- L133: def fetch(self, source_kind, cursor)
- L138: def _fetch(self, source_kind, url)
- L213: class _AnchorParser
- L214: def __init__(self)
- L220: def handle_starttag(self, tag, attrs)
- L229: def handle_data(self, data)
- L233: def handle_endtag(self, tag)
- L243: class LinkRecordParser
- L246: def __init__(self, archive_root)
- L249: def parse(self, snapshot)
- L275: class SnapshotArchive
- L276: def __init__(self, root)
- L285: def ingest(self, collected, parser)
- L357: def _record_diff_events(self, previous, current, records)
- L413: def _records_for(self, snapshot)
- L442: def latest(self, source_kind)
- L450: def _diff_events(self, previous, current)
- L492: def _append_events(self, events)
- L502: def _write_inventory(self)
- L587: def _latest_parser_error(self, source_kind)
- L595: def _recent_events(self, limit)
- L611: def source_definition(source_kind)
- L618: def collected_from_file(source_kind, path)
- L634: def _validate_source_url(url)
- L642: def _blocked_reason(status_code,

[truncated]
```
