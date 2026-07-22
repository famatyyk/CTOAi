# Engine Brain Status

Snapshot date: 2026-07-07 Europe/Warsaw

Current P7 Control Center contract: seven bounded `safe_write` capabilities
are registered for local evidence/context maintenance only: repo hygiene, API
cost, evidence pack, Engine Brain, P7 cockpit smoke, adaptive roadmap state,
and fixed full-workspace validation. The seventh action,
`full-workspace-validation-refresh` /
`ctoai_full_workspace_validation_refresh`, has a native dry-run, actor-bound
proof, exact confirmation `refresh full workspace validation`, bounded public
projection, and sanitized audit evidence. It does not grant deploy, live
client, promotion, or runtime authority.

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
  the 1000-tick stress test isolates local runtime Q-table state so test results
  are not driven by stale learned action dominance from `runtime/state`.
- Bot client runtime profile config now reports non-secret diagnostic codes for
  unreadable, invalid JSON, or invalid-shape profile config instead of silently
  swallowing broad exceptions. Profile saves now use the same hidden PID/UUID
  temp-file, `fsync`, `replace`, and cleanup pattern used by other local state
  writers.
- `release_evidence_pack.py` now mirrors Control Center Helper semantics for
  durable live promotion: `live_promotion.json` can produce `status=promoted`,
  and passed release gates no longer inherit stale next-command guidance from
  older goal-status artifacts.
- `release_evidence_pack.py` now also mirrors Control Center local-read
  guardrails: configured JSON artifacts are byte-bounded and symlink-rejecting,
  action-audit JSONL is counted from a bounded tail sample, release markdown
  discovery ignores symlinked files, and symlinked Helper dev directories fail
  closed to missing Helper status.
- Repo-local security scan tooling is available through `requirements-dev.txt`
  and the local `.venv`; the Bandit pre-commit scope now produces
  `runtime\security\bandit-precommit.json`.
- Training supply-chain hardening is complete for the current slice:
  `ctoa_finetune.py` requires a pinned 40-character
  `CTOA_TRAINING_MODEL_REVISION` before Hugging Face downloads and defaults
  remote model code off; `finetune_colab.ipynb` now carries the same pinned
  revision and remote-code opt-in contract for Unsloth loads; `collect_github.py`
  validates GitHub API/raw HTTPS URLs, allowlisted API query strings, repo
  identifiers, branches, decoded raw paths, and decoded dataset filenames before
  `urlopen` or file writes, rejecting encoded traversal and backslashes;
  `build_dataset.py` uses deterministic non-security sampling and reports file
  build failures.
  `runtime\security\bandit-training-after.json` and
  `runtime\security\bandit-bot-training-after.json` both report zero findings.
  The latest targeted continuation also writes
  `runtime\security\bandit-training.json` with zero findings.
- BRAVE prompt rendering now tolerates incomplete evaluation/operator context:
  missing template variables render as `[UNKNOWN]` instead of raising
  `KeyError`. The prompt/scoring/evals slice writes
  `runtime\security\bandit-prompts-scoring-evals.json` with zero findings.
- Bot runtime low-severity Bandit findings are now cleared and locked into the
  pre-commit scan scope. Behavioral randomness is centralized in
  `bot/safety/nonsecurity_random.py`, silent best-effort exception handlers now
  record diagnostics, and `status_overlay.py` launches bot and macro-pad
  processes through `runner.process_safety`.
- Hybrid bot template cache handling now rejects unsafe template names,
  path separators, Windows-unsafe filename characters, and cache realpath
  escapes before reading or writing template PNGs. Remote template source URLs
  now use `runner.http_safety.require_public_discovery_url` plus stricter
  no-query/no-fragment checks, rejecting credentials, localhost/private/
  link-local or internal hosts, query strings, fragments, backslashes, and
  decoded traversal before `urlopen`; failures no longer echo raw source URLs.
- Hybrid bot metrics and profiler file outputs now keep generated CSV/JSONL
  artifacts under the selected metrics output directory. Relative output names
  reject absolute paths, drive-style paths, `..`, backslashes, control
  characters, Windows-unsafe filename characters, realpath escapes, unsupported
  extensions, and existing output symlinks before read/write.
- Generator agent module output paths now stay under
  `CTOA_GENERATED_DIR/<server-slug>/`. Queue-provided `output_file` values
  reject absolute paths, drive-style paths, `..`, backslashes, control
  characters, Windows-unsafe filename characters, and output symlinks before
  generated Lua is written or module DB status is updated.
- Generator agent manifest writes now use the same generated-artifact
  containment guard. Symlinked `<server-slug>` directories,
  `generated/manifests`, or `generated/manifests/latest.json` are rejected
  before generated Lua, per-run manifests, or latest manifest pointers can be
  written outside `CTOA_GENERATED_DIR`.
- Generated manifest reads now share a read-side containment helper.
  `runner/generator_validator_samples.py`, `runner/weekly_report.py`, and
  Mobile Console `_latest_manifest_payload` reject `latest.json`
  `manifest_path` values that resolve outside the configured
  `generated/manifests` directory, and public summaries use display-safe
  generated manifest paths.
- Generated manifest enumeration now uses that same helper. Mobile Console
  execution trend/SLO metrics plus `nightly_stability.py` and `night-report.py`
  skip symlinked run directories whose resolved `manifest.json` escapes
  `generated/manifests`.
- `night-report.py` now reads orchestrator logs through a bounded tail sample
  instead of full-file `read_text()`, and the markdown report includes
  sampled/source byte counts plus a tail-sample marker when truncation occurs.
- Agent executor generic deliverable writes now require safe repo-relative
  paths. Track A-D fallback deliverables reject absolute paths, drive-style
  paths, `..`, backslashes, control characters, Windows-unsafe filename
  characters, root escapes, and existing output symlinks before writing.
- Bandit high-severity findings are currently cleared for the pre-commit scope:
  SHA1-only fingerprints are marked with `usedforsecurity=False`, the Helper UI
  preview script no longer uses Python `eval`, and catalog/scout/ingest agents
  validate HTTP(S) URLs while using verified TLS by default.
- Catalog, scout, and ingest discovery fetches now use
  `runner.http_safety.require_public_discovery_url`, which keeps public
  `http://` and `https://` discovery working while rejecting loopback, private,
  link-local/metadata, reserved, single-label, and internal-host targets plus
  credentials, fragments, token query parameters, backslashes, and decoded path
  traversal before `urlopen`.
- Bandit medium-severity findings are currently cleared for the pre-commit
  scope: runner webhook/template/smoke `urlopen` call sites now pass through
  `runner.http_safety.require_http_url`, token-bearing GitHub API callers now
  use `runner.http_safety.require_github_api_url`, runtime smoke checks no
  longer use `assert`, and Docker bind auditing uses `ipaddress` for
  unspecified bind detection.
- `runner.http_safety.require_github_api_url` now also requires non-empty
  `/repos/{owner}/{repo}` path segments and rejects encoded path separators
  after URL decoding, closing off ambiguous repo path construction before any
  token-bearing GitHub API request is created.
- `runner.http_safety.require_github_repository` now validates
  `GITHUB_REPOSITORY`, `CTOA_REPO_OWNER`, and `CTOA_REPO_NAME`-derived inputs
  before runner live issue publishing, daily/weekly reports, issue/status sync,
  close-on-gate, health dashboard publishing, or CI executive reporting build
  token-bearing GitHub API URLs. Repo IDs must be literal `owner/repo` values
  without empty segments, traversal, encoded separators, or unsupported
  characters.
- `runner/health_metrics.py` now applies the same GitHub API URL guardrail
  before its requests-backed GitHub issue comment publish path.
- `scripts/ops/runtime_smoke_e2e_8001.py` now validates
  `CTOA_RUNTIME_SMOKE_BASE` through `runner.http_safety.require_loopback_http_url`
  before sending login credentials or bearer tokens. Runtime smoke targets must
  stay on `127.0.0.1`, `localhost`, or `[::1]` without credentials, query
  strings, fragments, backslashes, or traversal.
- LLM/model backend URLs now fail closed before prompts or provider keys are
  sent. `runner.http_safety.require_model_backend_url` allows local HTTP only
  for loopback and `host.docker.internal`, requires explicit opt-in plus HTTPS
  for remote model backends, and rejects credentials, query strings, fragments,
  backslashes, and traversal. Azure provider endpoints now pass through
  `runner.http_safety.require_azure_service_url`, which requires HTTPS and
  allowlisted Azure service hosts before `FOUNDRY_API_KEY` is handed to the SDK.
- `scripts/ops/azure_activity_alerts.py` now keeps generic webhooks on
  `runner.http_safety.require_http_url`, while Discord-native alert delivery
  uses `runner.http_safety.require_discord_webhook_url` before `urlopen`.
  Discord payloads cannot fall back to arbitrary generic webhook hosts.
- Azure Activity webhook listener startup now fails closed before binding a
  non-loopback host unless `CTOA_AZURE_INGEST_SECRET` is set. The
  PowerShell runner defaults listener mode to `127.0.0.1` and keeps the ingest
  secret in the environment instead of putting it on the child process command
  line.
- `runner.process_safety` now centralizes trusted subprocess execution and
  executable resolution. Publisher and validator agents use it for Git, gh,
  luac, and Python checks, while Git-backed ops scripts use the same Git
  resolver path.
- Health metrics, service drift checks, and queue worker subprocess calls now
  resolve fixed executables through `runner.process_safety`; optional disk
  cleanup resolves `bash` via `CTOA_BASH_BIN`/PATH before execution.
- Queue worker startup logging now redacts Redis URL credentials and query
  strings before emitting `CTOA_REDIS_URL`, and invalid queue JSON payloads are
  reduced to `action=unknown` without copying raw payload text into job
  metadata.
- Mobile console command execution, repo hygiene audit, and Phase-5 nightly sync
  now use the same subprocess guardrail path before launching external tools.
- `ctoa_loader.py`, `engine_brain_doctor.py`, `smoke_must_pass.py`,
  `run_validator_with_preflight.py`, and `nightly_stability.py` now resolve
  external executables through `runner.process_safety` instead of launching
  direct partial command names.
- Sprint validators `028` and `041` through `070` now use
  `runner.process_safety` for focused regression test subprocesses, removing
  the repeated direct `subprocess.run` pattern from those operator gates.
- `runner.process_safety.start_trusted` now covers trusted long-running process
  launches. Rosetta bundle generation, KingsVale first-hit attach tooling, and
  the x64dbg ENC3 dynamic pass use the shared resolver/launcher path.
  `activation_agent.py` now runs its live-target sync hook through
  `runner.process_safety`, and `runner/agents/executor.py` no longer imports
  `subprocess` at runtime.
- `runner/agents/executor.py` now also generates `runner/drift_checker.py` with
  the same `runner.process_safety` systemctl resolver/run path, preventing the
  generator from overwriting the hardened drift checker with a direct
  `subprocess.run(["systemctl", ...])` version. Its runbook/checklist
  generators now replace timestamp placeholders on the correct document
  variables and write UTF-8 explicitly.
- `scripts/ops/sync-live-targets.py` now validates source/target roots before
  replacing live target directories. It rejects target roots inside the source
  root, unsafe target directory names, symlinked source/target content, and any
  destination path that resolves outside the live target root before calling
  `shutil.rmtree`.
- `scripts/ops/ctoa_loader.py` now resolves operator-supplied live target names
  through safe path parts only. `open` and `export` skip traversal candidates,
  absolute/drive-rooted candidates, and symlinked target directories so target
  lookup cannot escape the configured live target root. Manifest reads now also
  reject symlinked `live-manifest.json` files, list unsafe manifests as absent,
  and refuse symlinked export output paths before writing.
- `scripts/ops/ctoa-root-action.sh` no longer writes dashboard health output to
  a predictable `/tmp/ctoa-health.out` path while running as a root wrapper.
  The one-shot health check uses `mktemp` under `${TMPDIR:-/tmp}` and removes
  the private output file via an EXIT trap.
- `deploy/vps/wrappers/ctoa-root-action.sh` now uses the same private
  dashboard-health temp-file pattern before it is installed to
  `/opt/ctoa/scripts/ops/ctoa-root-action.sh`; both `healthcheck-one-shot` and
  `dashboard-snapshot` share the guarded `PrintDashboardHealth` helper.
- `scripts/ops/gs-reset.sh` now validates env-provided API URLs and timing
  values before any shutdown phase or `curl` health probe. `API_HEALTH_URL` and
  `API_BASE_URL` must resolve to local HTTP(S) endpoints on `127.0.0.1`,
  `localhost`, or `[::1]` without credentials, query strings, or fragments, and
  `API_CHECK_RETRIES` plus `GS_TIMEOUT_WAIT` must be positive integers.
- `scripts/ops/gs-api-validator.py` now enforces the same local API boundary on
  direct validator runs. Health and module probes use
  `runner.http_safety.require_loopback_http_url`, `API_BASE_URL` must be a
  loopback origin without credentials, path, query, or fragment, and rejected
  URLs are logged without echoing raw env values.
- `scripts/ops/sync-mythibia-client.ps1` keeps the experimental unsafe runtime
  bootstrap behind both `-UnsafeRuntimeBootstrap` and
  `CTOA_ALLOW_UNSAFE_RUNTIME_BOOTSTRAP=true`, resolves bootstrap paths under
  `ClientRoot`, and removes unsafe artifacts with `-LiteralPath`.
- `scripts/windows/install-ctoa-vscode-extensions.ps1` now uses
  separator-aware target containment and `-LiteralPath` when replacing mirrored
  VS Code extension directories.
- VS Code Mobile Console debug/run configs now stay local-only and secret-free:
  `.vscode/launch.json` and the paired `.vscode/tasks.json` bind Mobile
  Console to `127.0.0.1`, use `CTOA_*` env references instead of committed
  passwords/tokens, and require the shared Mobile Console env preflight before
  launch.
- Operator-facing Mobile Console launch guidance is local-only too:
  `.\ctoa.ps1 up`, `docs/MOBILE_CONSOLE.md`, and Desktop Console connection
  error hints use `uvicorn mobile_console.app:app --host 127.0.0.1 --port 8787`
  instead of `0.0.0.0`.
- `scripts/ops/watch-mythibia-client-sync.ps1` now runs under strict mode and
  rotates watcher logs with literal paths plus archive containment before
  deleting old archive files.
- `scripts/ops/orchestrator-loop.ps1` now delegates long-running loop work to
  `scripts/ops/orchestrator-loop-worker.ps1` instead of a hidden
  `-EncodedCommand`. `DB_PASSWORD` is inherited through the child process
  environment, PID ownership is checked against the worker command line before
  stopping, and PID/log access uses literal paths.
- Scheduled-task installers and removers now share
  `scripts/ops/windows-task-guard.ps1`: CTOAi task names and HKCU Run-key names
  are constrained to `CTOA-*`, repo script targets use separator-aware
  containment, watcher logs are confined to `%LOCALAPPDATA%\CTOA\logs`, and
  Run-key cleanup uses literal registry paths. `run-hidden.vbs` now rejects
  non-PS1 and out-of-repo targets before launching hidden PowerShell.
- Operator-facing PowerShell launchers now reject unsafe inputs before process
  launch: `ctoa.ps1 cc` and `open-control-center.ps1` allow only HTTP(S),
  block URL credentials/query/fragment components without echoing rejected
  values, reject raw or decoded backslashes and decoded `.`/`..` path traversal,
  and require HTTPS for non-local hosts before probing or opening Control
  Center; the Kamil client launcher requires an absolute existing
  `.exe` and a safe bot profile name; the Mythibia watcher loop
  requires its sync script to resolve to a repo-local `.ps1`. `ctoa.ps1` uses
  explicit `Start-Process -FilePath` for Control Center and generated Helper
  preview/mockup HTML files.
- LAB003 operator smoke scripts now validate network targets before credentials,
  env transfer, child processes, or `Invoke-RestMethod`: mobile proxy and shift
  guard base URLs must be local loopback HTTP(S) origins, alert webhooks must be
  HTTPS unless loopback HTTP, and webhook URLs cannot include credentials or
  fragments. `lab003_validate_bundle.ps1` is restored as the documented bundle
  entrypoint, and LAB003 child launches use the current `$PSHOME` PowerShell
  executable instead of PATH-only `powershell`.
- Bot VPS bootstrap no longer executes Docker's remote installer via
  `curl | sh`. `scripts/ops/bot/bootstrap_vps.sh` installs Docker from distro
  packages, requires root plus a validated existing `BOT_VPS_USER`, confines the
  deploy directory to `/opt`, and keeps Grafana port `3000` closed unless
  `BOT_ALLOW_PUBLIC_GRAFANA=true` is explicitly set.
- Bot VPS deploy now validates SSH/rsync inputs before use:
  `scripts/ops/bot/deploy.sh` rejects unsafe remote users, unsafe host strings,
  and deploy directories outside `/opt`; uses `ssh --` and `scp --`; creates the
  remote directory with a quoted path; and passes `BOT_DEPLOY_DIR` into the
  remote build script as an argument instead of interpolating it in the heredoc.
- `scripts/ops/ctoa-vps.ps1 WriteGithubPat` now keeps the GitHub PAT out of
  SSH command strings and base64-encoded remote scripts. The action validates
  token shape, transfers a temp env file with `scp`, merges it into
  `/opt/ctoa/.env` with `install -m 600`, and removes local plus remote temp
  files.
- `scripts/ops/ctoa-vps.ps1` now installs the root-action wrapper through a
  randomized `/tmp/ctoa-root-action-<guid>.sh` remote temp path with remote
  cleanup, and the generated tiered-reseed installer updates `/opt/ctoa/.env`
  through `mktemp /opt/ctoa/.env.XXXXXX` instead of predictable `.env.tmp`
  paths.
- `deploy/vps/rotate-mobile-token.sh` no longer writes the new Mobile Console
  token to a predictable `/tmp/ctoa_new_mobile_token` path. Token, `.env`, and
  history temp files now come from `mktemp`, use a cleanup trap, and keep the
  secrets directory plus token file on root-only permissions.
- `scripts/ops/ctoa-vps.ps1` now validates `CTOA_VPS_USER` and `CTOA_VPS_HOST`
  before building SSH/SCP targets. Users must match the lowercase system-user
  pattern, hosts must be valid IPv4, DNS labels, or bracketed IPv6, and the
  guard rejects whitespace, invalid labels, unbracketed IPv6, path separators,
  and shell metacharacters. `CTOA_VPS_KEY_PATH` resolves as a literal existing
  key file.
- `scripts/ops/ctoa-vps.ps1 EnsureGsEnvKeys` now keeps `OPENAI_API_KEY` and
  optional `GITHUB_PAT` out of placeholder-expanded remote scripts. The action
  validates `.env`-safe secret values, transfers them through a temp env file
  with `scp`, performs missing/empty-only upserts remotely, and cleans up local
  plus remote temp files.
- `scripts/ops/ctoa-vps.ps1` now uses shared validators for remaining
  operator-provided remote-script inputs: server URLs and URL lists, server
  status filters, systemd service names, GS source refs, reseed timer values,
  and remote SQL string literals. `ShowScoutDetails`,
  `WatchScoutingUntilSettled`, `RegisterServer`, `RegisterServerList`,
  `MythibiaBurst`, `HealService`, `InstallTieredReseedTimers`,
  `InstallGsReset`, and `InstallGsResetFromBranch` no longer rely on ad hoc
  quoting for those values.
- `scripts/ops/ctoa-vps.ps1 Resolve-ServerUrl` now reports invalid fallback
  URLs without echoing the rejected value, so credentials or token-like strings
  in bad operator input are not written to warnings/logs.
- The generated `/opt/ctoa/scripts/ops/reseed-tier.sh` now revalidates runtime
  values loaded from `/opt/ctoa/.env`: tier URLs must stay HTTP(S), short,
  whitespace-free, and free of shell/SQL metacharacters; stale error age values
  must be integers between 1 and 720; and server URL SQL lookups/updates use a
  controlled `sql_literal` helper instead of `WHERE url='$url'`.
- The pre-commit Bandit scope is now clear. Depack/parsing utilities catch
  concrete read/decode/zlib failures, runner/mobile best-effort fallbacks record
  diagnostics, and x64dbg capture helpers preserve cleanup/breakpoint errors in
  evidence instead of silently swallowing broad exceptions.
- Bandit scan coverage is also clear: legacy ENC3/runtime tools that previously
  failed AST parsing now compile, non-security SHA1 fingerprints in
  `capture_runtime_loader_transform_live.py` use `usedforsecurity=False`, and
  its best-effort breakpoint/cleanup failures are recorded in structured
  diagnostics instead of silent `pass`/`continue` handlers.
- Dependency audits are currently clean. `pip-audit -r requirements.txt` reports
  zero vulnerabilities, and `npm audit --json` in `web\` reports zero
  vulnerabilities after pinning `postcss` to `8.5.16` and adding an npm override
  so Next's transitive PostCSS dependency dedupes to the patched version.
- `tests/test_web_dependency_security.py` now guards the PostCSS pin/override
  and rejects a vulnerable nested `next/node_modules/postcss` lockfile tree.
- Public docs/site admin helpers now normalize API base URLs through `URL`,
  reject credentials/path/query/hash components, require HTTPS outside local
  dev hosts, avoid dynamic `innerHTML`, and keep local fallback admin passwords
  out of persistent `localStorage`.
- Public docs/site live dashboard now follows the same guardrails: URL-normalized
  API base, session-scoped auth tokens, no dynamic `innerHTML`, no inline
  handlers, and DOM/text rendering for dashboard payloads.
- Legacy mobile console dashboard rendering now avoids dynamic `innerHTML` in
  `mobile_console/static/app.js`; dashboard API payloads render through DOM
  nodes and `textContent`, with a static XSS regression test.
- Local Docker runtime exposure was reconciled with the hardened compose
  defaults: `docker compose up -d --remove-orphans api postgres` removed stale
  broad-binding orphan containers, leaving only `ctoa-api` on
  `127.0.0.1:8001` and internal-only `ctoa-postgres`.

## Current Evidence Highlights

- Docker is running with CTOAi containers active and no running or configured
  broad binds.
- Cloudflare WARP is connected and healthy.
- Vercel CLI is installed and linked to project `ctoa-web`.
- GitHub auth works through `gh`; repo has 6 open PRs and recent workflow runs
  listed as successful.
- VS Code has `openai.chatgpt@26.623.101652` active, with older OpenAI
  extension directories still present.
- `scripts/ops/ctoa_update_gate.py` passes and reports launch allowed.
- `tests/test_engine_brain_index.py` passes.
- `tests/test_engine_brain_doctor.py` passes.
- `tests/test_engine_brain_pack.py` passes.
- `tests/test_otclient_helper_profile_audit.py` passes.
- `.\.venv\Scripts\python.exe -m pytest tests\test_release_evidence_pack.py
  -q` passes with 5 tests and 3 skipped symlink-platform cases after release
  evidence pack bounded/symlink-safe local-read hardening.
- `tests/test_security_hardening.py` passes with production CORS/JWT/auth-store
  seeding guards, mobile console self-registration guards, and cookie/CSRF
  coverage.
- `tests/test_atomic_state_writes_security.py` covers API auth-store and runner
  state artifact writes so they use hidden PID/UUID temp files, keep `fsync`,
  clean up temp artifacts, and reject the old `path.suffix + ".tmp"` contract.
- `.\.venv\Scripts\python.exe -m pytest tests\test_api_auth_registration_security.py tests\test_security_hardening.py tests\test_atomic_state_writes_security.py -q`
  passes with 28 tests and 1 skipped symlink-platform case after API
  auth-store bounded-read hardening.
- `.\.venv\Scripts\python.exe -m pytest tests\test_atomic_state_writes_security.py tests\test_security_hardening.py tests\test_runner_execution_summary.py tests\test_runner_backlog_selection.py -q`
  passes with 24 tests.
- `.\.venv\Scripts\python.exe -m py_compile api\main.py runner\runner.py tests\test_atomic_state_writes_security.py`
  passes.
- `.\.venv\Scripts\python.exe -m pytest tests\test_health_metrics_process_safety.py -q`
  passes with 3 tests and 1 skipped symlink-platform case after Health Metrics
  latest snapshot atomic-write hardening.
- `.\.venv\Scripts\python.exe -m ruff check runner\health_metrics.py tests\test_health_metrics_process_safety.py`
  passes after Health Metrics latest snapshot atomic-write hardening.
- `.\.venv\Scripts\python.exe -m py_compile runner\health_metrics.py tests\test_health_metrics_process_safety.py`
  passes after Health Metrics latest snapshot atomic-write hardening.
- `.\.venv\Scripts\python.exe -m bandit runner\health_metrics.py -f json`
  reports `results=0` and `errors=0`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_desktop_console_url_security.py -q`
  passes with 24 tests and 2 skipped symlink-platform cases after Desktop
  Console settings atomic-write and bounded-read hardening.
- `.\.venv\Scripts\python.exe -m ruff check desktop_console\app.py tests\test_desktop_console_url_security.py`
  passes after Desktop Console settings atomic-write and bounded-read
  hardening.
- `.\.venv\Scripts\python.exe -m py_compile desktop_console\app.py tests\test_desktop_console_url_security.py`
  passes after Desktop Console settings atomic-write and bounded-read
  hardening.
- `.\.venv\Scripts\python.exe -m bandit desktop_console\app.py -f json`
  reports `results=0` and `errors=0`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_ideas_api.py tests\test_mobile_console_display_path_security.py -q`
  passes with 12 tests and 1 skipped symlink-platform case after Mobile
  Console local state bounded-read and atomic-write hardening.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_display_path_security.py`
  passes after Mobile Console local state hardening.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_display_path_security.py`
  passes after Mobile Console local state hardening.
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  reports `results=0`, `errors=0`, and `skipped_tests=3`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_update_gate.py tests\test_ctoa_product_bootstrap.py -q`
  passes with 8 tests and 2 skipped symlink-platform cases after product
  bootstrap atomic-write and update-gate bounded-read hardening.
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\ctoa_update_gate.py tests\test_ctoa_update_gate.py scripts\ops\ctoa_product_bootstrap.py tests\test_ctoa_product_bootstrap.py`
  passes after product bootstrap/update-gate local state hardening.
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\ctoa_update_gate.py tests\test_ctoa_update_gate.py scripts\ops\ctoa_product_bootstrap.py tests\test_ctoa_product_bootstrap.py`
  passes after product bootstrap/update-gate local state hardening.
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\ctoa_product_bootstrap.py scripts\ops\ctoa_update_gate.py -f json`
  reports `results=0`, `errors=0`, and `skipped_tests=0`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_profile_audit.py tests\test_solteria_helper_goal_audit.py tests\test_solteria_helper_release_gate.py tests\test_sprint_state_sync.py -q`
  passes with 37 tests after extending Helper/release-gate and sprint state
  atomic-write contracts.
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\otclient_helper_profile_audit.py scripts\ops\solteria_helper_goal_audit.py scripts\ops\solteria_helper_release_gate.py scripts\ops\sprint_state_sync.py`
  passes.
- PowerShell parser check for `scripts\windows\solteria_helper_test_env.ps1`
  passes after the GUID-temp `Write-JsonAtomic` change.
- `.\.venv\Scripts\python.exe -m pytest tests\unit\bot\test_runtime_profile_security.py tests\unit\bot\test_spell_rotation.py tests\test_powershell_launcher_security.py -q`
  passes with 18 tests after adding runtime-profile config diagnostics and
  atomic save coverage.
- `.\.venv\Scripts\python.exe -m py_compile bot\config\runtime_profile.py tests\unit\bot\test_runtime_profile_security.py`
  passes.
- `tests/test_mobile_console_user_accounts_api.py` passes with 15 tests covering
  account-session revocation plus member-only self-registration.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py -q`
  passes with 6 tests and 1 skipped symlink-platform case after Mobile Console
  log-tail fallback bounded-read hardening.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py`
  passes after Mobile Console log-tail fallback bounded-read hardening.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_command_execution_security.py`
  passes after Mobile Console log-tail fallback bounded-read hardening.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_generated_latest_api.py -q`
  passes with 11 tests and 2 skipped symlink-platform cases after Mobile
  Console local metadata JSON and generated-manifest bounded-read hardening.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_generated_latest_api.py`
  passes after Mobile Console local metadata JSON and generated-manifest
  bounded-read hardening.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_generated_latest_api.py`
  passes after Mobile Console local metadata JSON and generated-manifest
  bounded-read hardening.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py -q`
  passes with 7 tests and 3 skipped symlink-platform cases after Mobile Console
  client-sync init-file and Lua-copy bounded-read/atomic-write hardening.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_client_sync_security.py`
  passes after Mobile Console client-sync init-file and Lua-copy hardening.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_client_sync_security.py`
  passes after Mobile Console client-sync init-file and Lua-copy hardening.
- `python -m pytest tests\test_mobile_console_user_accounts_api.py tests\test_security_hardening.py tests\test_mobile_console_capability_gate.py -q`
  passes with 30 tests, including member-only self-registration and operator
  role enforcement.
- `tests/unit/bot/test_ml_model.py` and `tests/integration/bot/test_stress.py`
  pass with no-target loot reward and deterministic stress-loop coverage.
- `.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_full_workspace_audit.py
  -q` passes with 4 tests and 1 skipped symlink-platform case after full
  workspace audit symlink-safe stat/hash hardening and audit-integrity gate
  reporting.
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  passes with 1040 tests and 32 skipped cases after adding the full workspace
  audit validation-evidence gate and updating the client-sync display-path
  regression to patch the current atomic writer.
- `.\.venv\Scripts\python.exe -m pytest tests\test_engine_brain_index.py
  tests\test_engine_brain_pack.py -q` passes with 10 tests after adding the P7
  operator workflow gate to `brain refresh`, Engine Brain packs, and plugin
  read-only contract checks.
- `codex plugin add ctoai-engine-brain@personal` succeeds after applying a
  Codex cachebuster to the local plugin manifest, and `codex plugin list`
  reports `ctoai-engine-brain@personal` as `installed, enabled` at
  `0.1.0+codex.20260707043706`.
- `python C:\Users\zycie\plugins\ctoai-engine-brain\scripts\ctoai_engine_brain_status.py --workspace C:\Users\zycie\CTOAi`
  reports `status=ready` with no hard blockers after the plugin status-script
  pass.
- `.\.venv\Scripts\python.exe -m pytest tests\test_engine_brain_index.py
  tests\test_engine_brain_pack.py tests\test_ctoa_full_workspace_audit.py -q`
  passes with 13 tests and 1 skipped case after adding the read-only P7
  operator brief and MCP brief coverage.
- `python C:\Users\zycie\.codex\plugins\cache\personal\ctoai-engine-brain\0.1.0+codex.20260707043706\scripts\ctoai_engine_brain_mcp.py`
  passes a JSON-RPC smoke covering initialize, tools/list, and
  `ctoai_engine_brain_brief`; for that historical cache version the tool list was
  `ctoai_engine_brain_status`, `ctoai_engine_brain_self_check`, and
  `ctoai_engine_brain_brief`.
- `python C:\Users\zycie\.codex\plugins\cache\personal\ctoai-engine-brain\0.1.0+codex.20260707043706\scripts\ctoai_engine_brain_brief.py --workspace C:\Users\zycie\CTOAi --format json`
  reports `decision=ready_for_p7_operator_workflow`, `status=ready`, no hard
  blockers, and `operator_workflow.status=read_only_ready`.
- `AI/generated/P6_CODEX_INTEGRATION_READINESS.md` reports
  `ready_for_plugin_design` with passed checks including plugin brief script,
  MCP config, MCP server, installed cache, P7 operator workflow contracts, and
  P7 operator brief validation evidence.
- `AI/generated/P7_OPERATOR_WORKFLOW.md` reports `read_only_ready` with three
  allowed read-only MCP tools and all write/deploy/live action classes blocked.
- `AI/generated/P7_OPERATOR_BRIEF.md` reports
  `decision=ready_for_p7_operator_workflow`, `status=ready`, and no hard
  blockers after the generated-brief pass.
- `web` `npm run lint` passes after the full workspace audit validation wave.
- `web` `npm test` passes with 24 test files and 117 tests after the full
  workspace audit validation wave.
- `tests/test_engine_brain_index.py` covers ownership map, doc sync, and secret
  guardrail generation.
- `tests/test_engine_brain_pack.py` covers inclusion of the new generated
  Engine Brain artifacts in the portable pack.
- `.\ctoa.ps1 brain pack helper` passes and emits a helper-scoped portable
  context pack.
- `ctoa-engine-brain` skill validation passes.
- `web` Control Center evidence tests cover Engine Brain status and next
  context command.
- `web` Control Center evidence tests cover artifact freshness checks and real
  Helper ZIP SHA256 comparison.
- `web` Control Center evidence tests cover durable Helper live-promotion
  evidence from `runtime\solteria_helper_dev\live_promotion.json`.
- `web` Control Center evidence tests cover release-evidence drilldown and
  sanitized action-audit drilldown payloads, including legacy audit JSONL
  entries whose `reason` or `output_preview` fields contain token/password
  assignments. They also cover oversized action-audit JSONL handling through a
  redacted bounded tail sample.
- `web` Control Center evidence tests cover runtime-vs-tracked release evidence
  comparison payloads.
- `web` Control Center ops tests cover release/action drilldown propagation and
  redaction of fallback recent action previews.
- `tests/test_runner_agent_db_security.py` covers runner agent DB connection
  setup so it does not pass a `dsn` string containing `password=...`.
- `tests/test_runner_agent_db_security.py` also covers agent-run DB error log
  redaction for `password=...` and PostgreSQL URL password forms.
- `tests/test_security_hardening.py` covers backend `/api/release-evidence`
  sanitization for local paths, token/password/API-key fields, and oversized
  evidence files.
- `tests/test_api_auth_registration_security.py` covers FastAPI HTTP audit log
  redaction for spoofed `User-Agent` and `X-Forwarded-For` values containing
  token/password/API-key/Bearer forms and local absolute paths.
- `tests/test_mobile_console_intel_proxy_api.py` covers local runtime proxy
  error redaction so URL/open exceptions containing `token=...` or
  `password=...` do not leak through Intel or CTOA proxy JSON.
- `tests/test_mythibia_sync_security.py` covers the Mythibia unsafe runtime
  bootstrap approval/path-containment contract.
- `tests/test_template_library_security.py` covers hybrid bot template cache
  path containment and remote template source SSRF/secret URL rejection before
  `urlopen`.
- `tests/test_vscode_extension_installer_security.py` covers VS Code extension
  mirror path containment and recursive replacement guardrails.
- `tests/test_mythibia_watcher_security.py` covers Mythibia watcher log
  rotation literal paths and archive containment.
- `tests/test_orchestrator_loop_security.py` covers the orchestrator loop
  launcher/worker split, removal of `EncodedCommand`, inherited secret
  transfer, PID owner verification, and literal-path PID/log handling.
- `tests/test_queue_worker_security.py` covers Redis URL credential/query
  redaction, invalid JSON raw-payload dropping, and absence of broad
  `except Exception` in queue worker parsing.
- `tests/test_windows_task_autostart_security.py` covers the scheduled-task
  guard module, `CTOA-*` namespace enforcement, watcher HKCU Run fallback
  containment, guarded repo child paths, and `run-hidden.vbs` repo-only PS1
  target validation.
- `tests/test_powershell_launcher_security.py` covers Control Center URL
  protocol/credential guards, Kamil launcher `.exe`/profile validation, and
  repo-local Python use for Macro Studio.
- `tests/test_bot_vps_bootstrap_security.py` covers bot VPS bootstrap
  supply-chain hardening: no remote installer pipe-to-shell, validated local
  deploy user, `/opt` deploy-dir confinement, and Grafana closed by default.
- `tests/test_bot_vps_deploy_security.py` covers bot VPS deploy hardening:
  validated SSH user/host/deploy-dir, end-of-options for SSH/SCP, guarded rsync
  target handling, and remote build script argument passing instead of heredoc
  path interpolation.
- `web` Control Center action tests cover role gates and audit redaction before
  action records are persisted.
- `web` Control Center action tests cover trusted Python resolution for
  configured absolute paths, repo-local `.venv`, relative-path rejection, and
  audited failure when no trusted Python is available.
- `web` Control Center action tests now also cover repo-root vs `web/`
  workspace root resolution, absolute existing `CTOA_WORKSPACE_ROOT`
  requirements, allowlisted script containment, and audited failure when a
  configured action script is missing.
- `web` Control Center action tests cover browser-visible action result
  sanitization, including successful stdout, trusted-Python failure messages,
  missing-script failure messages, token/password forms, and absolute live
  client paths.
- `web` Control Center markdown/action-output tests cover POSIX absolute local
  path redaction for repo-local and external paths while preserving normal
  `/api/...` route text.
- `web` Control Center markdown report tests cover symlinked configured report
  rejection before `open`, bounded reads, oversized report `413`, access-gated
  no-open behavior, and file-handle cleanup.
- `web` Control Center action route tests cover sanitized generic and
  authorization error JSON for token-like input plus Windows/POSIX local paths.
- `web` Control Center action route tests cover role-scoped action catalog GET
  responses, including no local command summary exposure for unauthenticated
  viewers and no owner-only command metadata exposure to operators.
- `web` Control Center snapshot and legacy route tests cover sanitized backend
  probe/fetch error summaries before JSON responses are returned to the
  browser.
- `web` Control Center action route tests cover same-origin action POST
  validation and cross-site rejection before auth lookup or action execution.
- `web` same-origin guard and `/api/auth` route tests cover shared cross-site
  rejection before backend forwarding for cookie-authenticated auth wrapper
  actions.
- `web` chat and seed-login route tests cover shared cross-site rejection before
  backend chat forwarding or local seed-login backend login forwarding.
- `web` auth route tests cover stripping backend `token`, `access_token`,
  `refresh_token`, and nested token-like fields from browser-visible JSON while
  still setting the httpOnly `ctoa_token` cookie from the original backend
  response.
- `web` auth proxy sanitizer and seed-login tests cover the shared
  cookie-token extraction vs browser-visible payload split, including nested
  token-like fields and Windows/POSIX local path redaction.
- `web` config tests cover fail-closed `VPS_API_URL` and
  `NEXT_PUBLIC_API_URL` parsing for scheme, embedded credentials, query/fragment
  components, and non-local HTTP.
- `web` `rateLimit.test.ts` covers fail-closed proxy-header trust for
  `/api/auth` and `/api/chat` rate-limit identity: default requests ignore
  `X-Forwarded-For`/`X-Real-IP`, trusted mode accepts only syntactically valid
  IP values, and invalid trusted values fall back to `unknown`.
- `tests/test_desktop_console_url_security.py` covers Desktop Console API and
  Control Center URL parsing for local HTTP, remote HTTPS, unsafe schemes,
  embedded credentials, query/fragment components, and non-local HTTP.
- Desktop Console updater downloads are guarded: release repository IDs must be
  `owner/repo`, selected Windows assets must be safe `.exe` filenames without
  path separators, update URLs and final redirects must stay on trusted GitHub
  HTTPS hosts, release-note URLs are sanitized before browser launch, and the
  GUI no longer auto-runs downloaded update executables. Update streams are
  size-bounded, written through a temporary `.download` file, cleaned up on
  failure, and moved into place only after a complete stream.
- The pre-commit Bandit scope now covers `desktop_console` in addition to
  `runner`, `mobile_console`, and `scripts`, with a static test preventing the
  operator desktop surface from dropping out of the scan.
- `web` chat route tests cover the backend payload allowlist, including dropping
  debug, token-like, `quality_retry`, and `max_tokens` fields from client JSON.
- `web` auth cookie tests cover centralized `ctoa_token` options and production
  `Secure` cookie behavior for login/logout-style writes.
- `web` `vitest run controlCenterEvidence` passes with Helper status coverage.
- `web` `npm test -- controlCenterActions` passes with 16 tests after adding
  realpath containment for allowlisted Control Center action scripts and a
  symlinked-parent escape regression test.
- `web` `npm test -- control-center/actions controlCenterActions` passes with
  25 tests after adding role-scoped action catalog GET coverage.
- `web` `npm test -- control-center/actions controlCenterActions control-center/route control-center/legacy controlCenterEvidence controlCenterOps`
  passes with 34 tests after checking the action catalog change against the
  broader Control Center evidence/ops surface.
- `web` `npm test` passes with 70 tests after the Control Center action
  realpath guard pass.
- `web` `npm test -- src/lib/__tests__/controlCenterActions.test.ts
  src/lib/__tests__/controlCenterEvidence.test.ts
  src/lib/__tests__/controlCenterOps.test.ts` passes with 20 tests after
  extending Control Center audit redaction to quoted JSON-like secret fields.
- `web` `npm test` passes with 70 tests after the quoted action-audit redaction
  pass.
- `web` `npm test -- src/lib/__tests__/controlCenterEvidenceAccess.test.ts
  src/app/api/control-center/evidence/route.test.ts
  src/app/api/control-center/actions/route.test.ts
  src/lib/__tests__/controlCenterActions.test.ts
  src/lib/__tests__/controlCenterEvidence.test.ts
  src/lib/__tests__/controlCenterOps.test.ts` passes with 32 tests after
  operator-gating Control Center evidence reads before local file collection.
- `web` `npm test -- --run src/lib/__tests__/controlCenterEvidence.test.ts
  src/lib/__tests__/controlCenterOps.test.ts
  src/app/api/control-center/evidence/route.test.ts
  src/app/api/control-center/actions/route.test.ts` passes with 20 tests for
  the Control Center release-evidence/action-audit drilldown surface.
- `web` targeted ESLint and `npx tsc --noEmit --pretty false` pass for the
  Control Center evidence, ops, action, and route-test files.
- `web` `npm test` passes with 105 tests across 24 files after the Control
  Center evidence/action drilldown pass.
- `web` `npm test -- controlCenterEvidence.test.ts` passes with 4 tests and
  covers bounded, redacted action-audit tail sampling for oversized JSONL logs.
- `web` `npm test` passes with 106 tests across 24 files after bounded
  action-audit drilldown sampling.
- `web` `npm test -- --run src/lib/__tests__/controlCenterEvidence.test.ts
  src/lib/__tests__/controlCenterOps.test.ts` passes with 11 tests after
  bounding release markdown title extraction, configured JSON evidence reads,
  containing Helper package hash paths to the Helper dev lane, and
  symlink-rejecting action audit tail sampling across Evidence and Ops.
- `web` `npm test -- --run src/lib/__tests__/controlCenterMarkdownReport.test.ts
  src/app/api/control-center/evidence/route.test.ts` passes with 15 tests after
  Control Center markdown report symlink rejection and bounded-read coverage.
- `web` `npm test` passes with 109 tests across 24 files after web proxy route
  rate-limit identity stopped trusting `X-Forwarded-For`/`X-Real-IP` unless
  `CTOA_TRUST_PROXY_HEADERS=true`.
- `web` `npm run lint` and `npx tsc --noEmit` pass after the web rate-limit
  proxy-header trust hardening.
- `.\.venv\Scripts\python.exe -m pytest tests\test_generated_manifest_safety.py
  tests\test_mobile_console_generated_latest_api.py -q` passes with 12 passed
  and 2 skipped after generated-manifest read-side containment hardening.
- `.\.venv\Scripts\python.exe -m pytest
  tests\test_mobile_console_generated_latest_api.py
  tests\test_generator_agent_output_security.py
  tests\test_mobile_console_api_contract_snapshot.py
  tests\test_mobile_console_intel_proxy_api.py
  tests\test_mobile_console_display_path_security.py -q` passes with 29 passed
  and 4 skipped after checking the Mobile Console/generator surface.
- `.\.venv\Scripts\python.exe -m ruff check
  runner\generated_manifest_safety.py mobile_console\app.py
  scripts\ops\nightly_stability.py scripts\ops\night-report.py
  tests\test_generated_manifest_safety.py
  tests\test_mobile_console_generated_latest_api.py` passes after manifest
  enumeration hardening.
- `.\.venv\Scripts\python.exe -m py_compile
  runner\generated_manifest_safety.py mobile_console\app.py
  scripts\ops\nightly_stability.py scripts\ops\night-report.py
  tests\test_generated_manifest_safety.py
  tests\test_mobile_console_generated_latest_api.py` passes after manifest
  enumeration hardening.
- `.\.venv\Scripts\python.exe -m bandit
  runner\generated_manifest_safety.py mobile_console\app.py
  scripts\ops\nightly_stability.py scripts\ops\night-report.py -f json`
  reports `results=0` and `errors=0`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_night_report_security.py -q`
  passes with 2 tests after bounded night-report log sampling.
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\night-report.py
  tests\test_night_report_security.py` passes after bounded night-report log
  sampling.
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\night-report.py
  tests\test_night_report_security.py` passes after bounded night-report log
  sampling.
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\night-report.py -f json`
  reports `results=0` and `errors=0`.
- `.\.venv\Scripts\python.exe -m pytest
  tests\test_mobile_console_display_path_security.py
  tests\test_mobile_console_generated_latest_api.py -q` passes with 15 tests
  after auto-trainer report bounded-read hardening.
- `.\.venv\Scripts\python.exe -m pytest
  tests\test_mobile_console_display_path_security.py
  tests\test_mobile_console_generated_latest_api.py
  tests\test_mobile_console_api_contract_snapshot.py
  tests\test_mobile_console_intel_proxy_api.py
  tests\test_mobile_console_url_validation_security.py -q` passes with 51 tests
  after checking the broader Mobile Console file/proxy surface.
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py -q`
  passes with 15 tests and 1 skipped platform symlink case after backend
  `/api/release-evidence` bounded-read, symlink rejection, and redaction
  hardening.
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py
  tests\test_release_evidence_pack.py tests\test_api_auth_registration_security.py
  tests\test_api_chat_safety.py -q` passes with 59 tests after API
  release-evidence, HTTP audit redaction, and proxy-header trust hardening.
- `.\.venv\Scripts\python.exe -m pytest
  tests\test_api_auth_registration_security.py tests\test_security_hardening.py
  -q` passes with 21 tests after FastAPI HTTP audit JSONL redaction.
- `.\.venv\Scripts\python.exe -m pytest
  tests\test_api_auth_registration_security.py tests\test_security_hardening.py
  -q` passes with 23 tests after FastAPI proxy-header trust and rate-limit
  spoofing regression coverage.
- `.\.venv\Scripts\python.exe -m ruff check api\main.py
  tests\test_security_hardening.py tests\test_api_auth_registration_security.py`
  passes.
- `.\.venv\Scripts\python.exe -m py_compile api\main.py
  tests\test_security_hardening.py tests\test_api_auth_registration_security.py`
  passes.
- `.\.venv\Scripts\python.exe -m bandit api\main.py -f json` reports
  `results=0`, `errors=0`, and no low/medium/high findings.
- `web` `npm test` passes with 79 tests after the Control Center evidence read
  access gate pass.
- `web` `npm run lint` and `npm run build` pass after shared
  action-audit read/write redaction, trusted Python action execution,
  workspace/script realpath containment, shared same-origin POST checks across
  actions, auth, chat, and local seed-login, fail-closed API base URL config
  parsing, production-safe web auth cookie settings, and strict chat proxy
  payload construction.
- Full workspace audit inventory currently covers 34,323 files, including `.git`
  internals, local runtime state, vendor/cache files, tracked source, untracked
  source candidates, and local sensitive/env files without copying secret
  contents.
- `AI/generated/DOC_SYNC.md` reports `passed`.
- `AI/generated/SECRET_GUARDRAIL.md` reports `passed` with zero exact sensitive
  path hits across generated Engine Brain context files.
- `.\ctoa.ps1 brain refresh` passes.
- `.\ctoa.ps1 brain doctor` passes with `overall_status: warn`, no failed
  checks, `docker.status=ok`, `running_broad=0`, and `configured_broad=0`.
- `.\ctoa.ps1 brain pack` passes.
- Solteria loaded Helper `v1.1b` at `2026-07-06 01:58:45`.
- Fresh `API probe` reports `online=yes`, `localPlayer=yes`, HP/MP values,
  `player.autoWalk=yes`, `g_map.findPath=yes`, combat APIs, magic APIs,
  UI/resources APIs, and container/loot APIs.
- Fresh `Magic API probe` reports `talk=yes`, `useInventoryItemWith=yes`, and
  `findItemInContainers=yes`.
- `python scripts\ops\ctoa_helper_ui_preview.py` passes for the redesigned
  helper shell with Phase 3 summaries and no layout issues.
- `python -m pytest tests\test_agent_http_security.py tests\test_ctoa_helper_ui_preview_security.py tests\test_static_security_scan_contract.py tests\test_mobile_console_url_validation_security.py -q`
  passes with 25 tests.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py -q`
  passes with 22 tests after tightening mobile-console server/intel target URL
  validation.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py -q`
  passes with 34 tests after adding local runtime API base guards for
  `CTOA_API_BASE_URL` and `CTOA_INTEL_API_BASE_URL`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py -q`
  passes with 43 tests after adding local runtime proxy path validation.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py`
  passes after local runtime proxy path validation.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py`
  passes after local runtime proxy path validation.
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  reports `results=0`, `errors=0`, and `skipped_tests=3`.
- `python -m pytest tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_db_exec_security.py tests\test_security_hardening.py -q`
  passes with 17 tests.
- `python -m pytest tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_command_execution_security.py -q`
  passes with 4 tests.
- `python -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_db_exec_security.py -q`
  passes with 7 tests.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 5 tests after adding operator-facing command stdout/stderr
  redaction.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 6 tests after closing legacy `CTOA_MOBILE_FULL_ACCESS=true`
  arbitrary command execution through `/api/command`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_static_xss_security.py tests\test_desktop_console_url_security.py -q`
  passes with 28 tests after aligning mobile status, legacy mobile UI, and
  desktop admin console with preset-only command execution.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 69 mobile-console security/regression tests.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 81 mobile-console security/regression tests.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 82 mobile-console security/regression tests after the legacy
  full-access command closure.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 84 mobile-console security/regression tests after the preset-only
  UI/status alignment.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_guarded_agent_actions_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  passes with 11 tests after adding owner-only confirmation and audit reasons
  for legacy Intel launch and one-click execution.
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_guarded_agent_actions_security.py -q`
  passes with 89 mobile-console security/regression tests after guarded Intel
  write confirmation.
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py tests\test_api_auth_registration_security.py -q`
  passes with 20 tests after adding the lightweight API startup guard and
  stable subprocess timeouts for security import checks.
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  passes with 927 tests and 13 skipped tests after the guarded Intel write and
  API startup guard pass.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py`
  passes after the legacy full-access command closure.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py`
  passes after the legacy full-access command closure.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_static_xss_security.py tests\test_desktop_console_url_security.py desktop_console\app.py`
  passes after the preset-only UI/status alignment.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py desktop_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_static_xss_security.py tests\test_desktop_console_url_security.py`
  passes after the preset-only UI/status alignment.
- `node --check mobile_console\static\app.js`
  passes after removing the legacy full-command box handler.
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console desktop_console -f json -o runtime\security\bandit-mobile-desktop-command-preset-only.json`
  reports `results=0`, `errors=0`, `SEVERITY.HIGH=0`,
  `SEVERITY.MEDIUM=0`, `SEVERITY.LOW=0`, and `skipped_tests=3`.
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console desktop_console -f json -o runtime\security\bandit-mobile-desktop-guarded-actions.json`
  reports `results=0`, `errors=0`, `SEVERITY.HIGH=0`,
  `SEVERITY.MEDIUM=0`, `SEVERITY.LOW=0`, and `skipped_tests=3`.
- `.\.venv\Scripts\python.exe -m bandit -r api mobile_console desktop_console -f json -o runtime\security\bandit-api-mobile-desktop-guarded-actions.json`
  reports `results=0`, `errors=0`, `SEVERITY.HIGH=0`,
  `SEVERITY.MEDIUM=0`, `SEVERITY.LOW=0`, and `skipped_tests=3`.
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py`
  passes after the local runtime API base guard pass.
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py`
  passes after the local runtime API base guard pass.
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  passes with 804 tests and 8 skipped tests after the mobile-console URL
  validation pass.
- `python -m pytest tests\test_mobile_console_static_xss_security.py -q`
  passes with 2 tests covering legacy mobile console DOM-safe dashboard
  rendering.
- `node --check mobile_console\static\app.js` passes.
- `node --test tests\js\dashboard_helpers.test.js` passes with 2 tests.
- `python -m pytest tests\test_mobile_console_capability_gate.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_command_execution_security.py -q`
  passes with 33 tests.
- `python -m pytest tests\test_mobile_console_csrf_security.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_ideas_api.py -q`
  passes with 11 tests covering cookie CSRF and public generated-artifact paths.
- `python -m pytest tests\test_mobile_console_csrf_security.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_live_dashboard_profile_api.py -q`
  passes with 52 mobile-console security/regression tests.
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console -f json -o runtime\security\bandit-mobile-console.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console -f json -o runtime\security\bandit-mobile-console-runtime-api-base.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=3`.
- `python -m py_compile mobile_console\app.py` passes.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 700 tests and
  3 skipped tests after the mobile-console generated-artifact path redaction
  and CSRF regression coverage pass.
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, `skipped_tests=21`, and zero
  `B105`/`B110`/`B112`/`B404`/`B603`/`B607` findings.
- `.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt -f json`
  reports zero vulnerable Python dependencies.
- `npm audit --json` in `web\` reports zero vulnerabilities after the PostCSS
  pin/override.
- `python -m pytest tests\test_docs_site_security.py tests\test_web_dependency_security.py -q`
  passes with 10 tests covering public docs/site URL, storage, owner reset,
  dynamic HTML, live-dashboard guardrails, and the PostCSS dependency pin.
- `node --check docs\site\script.js` passes.
- `node -e "... vm.Script(... docs/site/live-dashboard.html inline scripts ...)"`
  parses the live-dashboard inline script successfully.
- `python -m pytest tests\test_ctoa_root_action_security.py tests\test_suite.py::TestVPSConnectivity::test_ctoa_root_action_supports_phase5_guardrail_actions -q`
  passes with 3 tests covering the root action allowlist and private temp-file
  dashboard health output.
- `.\.venv\Scripts\python.exe -m pytest tests\test_vps_root_action_wrapper_security.py tests\test_ctoa_root_action_security.py tests\test_ctoa_vps_secret_handling.py -q`
  passes with 17 tests covering private temp-file dashboard health output in
  both source and deploy root-action wrappers plus VPS secret handling.
- Git Bash `bash -n scripts\ops\ctoa-root-action.sh` passes.
- Git Bash `bash -n deploy/vps/wrappers/ctoa-root-action.sh` passes.
- Git Bash `bash -n` over every `scripts\**\*.sh` file passes.
- `python -m pytest tests\test_health_metrics_process_safety.py tests\test_agent_http_security.py tests\test_process_safety.py tests\test_ops_process_safety.py -q`
  passes with 25 tests covering process safety and health publish URL
  validation.
- `python -m pytest tests\test_sync_live_targets_security.py tests\test_ctoa_loader_process_safety.py tests\test_ops_process_safety.py::test_activation_agent_sync_hook_uses_resolved_python -q`
  passes with 11 tests and 5 skipped symlink-platform cases, covering
  live-target sync child-path, destructive replace, and loader open/export
  traversal, manifest symlink, and export symlink guardrails.
- `python -m pytest tests\test_ctoa_loader_process_safety.py -q` passes with
  7 tests and 4 skipped symlink-platform cases, covering live target
  open/export traversal, manifest symlink, list-target manifest, and export
  symlink guardrails.
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\ctoa_loader.py -f json -o runtime\security\bandit-ctoa-loader.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\sync-live-targets.py -f json -o runtime\security\bandit-sync-live-targets.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `python -m pytest tests\test_azure_activity_alerts.py tests\test_phase5_nightly_sync.py tests\test_agent_http_security.py -q`
  passes with 26 tests covering Azure and Phase-5 webhook URL guardrails.
- `.\.venv\Scripts\python.exe -m pytest tests\test_phase5_nightly_sync.py tests\test_phase5_nightly_sync_more.py tests\test_agent_http_security.py -q`
  passes with 110 tests after the Phase-5 Slack/Discord webhook allowlist
  hardening.
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py scripts\ops\phase5_nightly_sync.py tests\test_agent_http_security.py tests\test_phase5_nightly_sync_more.py`
  passes after the Phase-5 webhook allowlist hardening.
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py scripts\ops\phase5_nightly_sync.py tests\test_agent_http_security.py tests\test_phase5_nightly_sync.py tests\test_phase5_nightly_sync_more.py`
  passes after the Phase-5 webhook allowlist hardening.
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py scripts\ops\phase5_nightly_sync.py -f json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=1`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_azure_activity_alerts.py tests\test_agent_http_security.py -q`
  passes with 107 tests after adding the Discord-only Azure alert webhook
  guard.
- `.\.venv\Scripts\python.exe -m pytest tests\test_azure_activity_listener_security.py tests\test_phase5_nightly_sync_more.py tests\test_phase5_nightly_sync.py -q`
  passes with 30 tests after rechecking shared webhook consumers.
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py scripts\ops\azure_activity_alerts.py tests\test_agent_http_security.py tests\test_azure_activity_alerts.py`
  passes after the Azure Discord webhook guard.
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py scripts\ops\azure_activity_alerts.py tests\test_agent_http_security.py tests\test_azure_activity_alerts.py`
  passes after the Azure Discord webhook guard.
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py scripts\ops\azure_activity_alerts.py -f json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=1`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_azure_activity_listener_security.py tests\test_azure_activity_alerts.py -q`
  passes with 11 tests covering Azure Activity listener loopback defaults,
  non-loopback ingest-secret enforcement, runner guardrails, and docs.
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  passes with 881 tests and 13 skipped tests after the Azure Activity listener
  exposure guard.
- `python -m py_compile scripts\ops\azure_activity_alerts.py` passes.
- `.\.venv\Scripts\python.exe -m pytest tests\test_gs_api_validator_security.py tests\test_gs_reset_security.py tests\test_agent_http_security.py -q`
  passes with 103 tests after the direct GS API validator loopback guard.
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\gs-api-validator.py tests\test_gs_api_validator_security.py tests\test_gs_reset_security.py`
  passes after the direct GS API validator loopback guard.
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\gs-api-validator.py tests\test_gs_api_validator_security.py tests\test_gs_reset_security.py`
  passes after the direct GS API validator loopback guard.
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\gs-api-validator.py -f json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=1`.
- Direct CLI smoke with remote `API_BASE_URL`/`API_HEALTH_URL`, one retry, and
  one-second timeout returns exit code `3` after rejecting unsafe local API URLs
  before network access.
- `python -m pytest tests\test_otclient_helper_zerobot_shell.py -q` passes
  with 34 tests, including the redesign layout and summary contracts.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 643 tests and
  3 skipped tests after the latest health publish URL-guard hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 659 tests and
  3 skipped tests after the latest PowerShell orchestrator-loop hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 660 tests and
  3 skipped tests after the latest Bandit scan-coverage hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 665 tests and
  3 skipped tests after the latest Windows scheduled-task autostart hardening
  pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 669 tests and
  3 skipped tests after the latest PowerShell launcher input-validation pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 673 tests and
  3 skipped tests after the latest bot VPS bootstrap supply-chain hardening
  pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 677 tests and
  3 skipped tests after the latest bot VPS deploy input-hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 681 tests and
  3 skipped tests after the latest `ctoa-vps.ps1 WriteGithubPat` secret-transfer
  hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 683 tests and
  3 skipped tests after the latest `ctoa-vps.ps1` SSH/SCP target-validation
  hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 685 tests and
  3 skipped tests after the latest `ctoa-vps.ps1 EnsureGsEnvKeys`
  secret-transfer hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 688 tests and
  3 skipped tests after the latest `ctoa-vps.ps1` operator-input validation
  hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 689 tests and
  3 skipped tests after the latest generated `reseed-tier.sh` runtime
  URL/hour/SQL-literal hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 694 tests and
  3 skipped tests after the latest `Resolve-ServerUrl` rejected-value warning
  redaction pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 694 tests and
  3 skipped tests after the backend chat debug-route role gate and route
  metadata sanitization pass.
- `python -m pytest tests\test_api_chat_safety.py -q` passes with 31 tests,
  including debug-route role-gate, sanitized-route response, and sanitized
  router-log coverage.
- `python -m pytest tests\test_api_chat_safety.py tests\test_api_auth_registration_security.py tests\test_security_hardening.py -q`
  passes with 48 tests.
- `.\.venv\Scripts\python.exe -m bandit -r api -f json -o runtime\security\bandit-api.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `python -m py_compile api\main.py` passes.
- `python -m pytest tests\test_powershell_launcher_security.py tests\test_vps_python_parity.py -q`
  passes with 11 tests after the latest `ctoa.ps1 cc` URL-guard and explicit
  `Start-Process -FilePath` hardening pass.
- `npm test -- --run src/lib/__tests__/config.test.ts` passes with 9 tests
  after the latest web API base URL origin-only hardening pass.
- `npm test` passes with 105 tests after the latest web API base URL
  origin-only hardening pass.
- `npm test`, `npm run lint`, and `npm run build` pass after the latest web API
  base URL config hardening pass; full web tests report 69 passed.
- `npm audit --json` reports zero vulnerabilities after the latest web API base
  URL config hardening pass.
- `python -m pytest tests\test_desktop_console_url_security.py -q` passes with
  19 tests after the latest Desktop Console URL and updater hardening pass.
- `python -m pytest tests\test_desktop_console_url_security.py tests\test_static_security_scan_contract.py -q`
  passes with 22 tests, including the expanded pre-commit Bandit scope
  contract.
- `python -m py_compile desktop_console\api_client.py desktop_console\app.py desktop_console\update_client.py tests\test_desktop_console_url_security.py tests\test_static_security_scan_contract.py`
  passes after the latest Desktop Console URL and updater hardening pass.
- `.\.venv\Scripts\python.exe -m pytest tests\test_powershell_launcher_security.py tests\test_vscode_workspace_security.py tests\test_docker_bind_defaults.py -q`
  passes with 16 tests after keeping `.\ctoa.ps1 up`, Mobile Console docs, and
  Desktop Console hints on loopback.
- `.\.venv\Scripts\python.exe -m pytest tests\test_desktop_console_url_security.py tests\test_powershell_launcher_security.py -q`
  passes with 29 tests.
- `.\.venv\Scripts\python.exe -m py_compile desktop_console\app.py tests\test_powershell_launcher_security.py`
  passes after the Mobile Console loopback guidance pass.
- PowerShell parser check for `ctoa.ps1` passes after changing `Invoke-Up` to
  `127.0.0.1`.
- `.\.venv\Scripts\python.exe -m bandit -r desktop_console -f json -o runtime\security\bandit-desktop-console.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=21`.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 698 tests and
  3 skipped tests after the latest web API base URL config hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 709 tests and
  3 skipped tests after the latest Desktop Console URL hardening pass.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 740 tests and
  8 skipped tests after the latest Desktop updater signed-redirect,
  max-download-size, atomic temp-file, backend router-log sanitization, and
  PowerShell Control Center URL-guard, training GitHub API query allowlist, and
  bot/training Bandit cleanup plus live-target sync/open/export child-path,
  manifest symlink, and export symlink guard pass.
- `python -m pytest tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py tests\test_issue_sync.py tests\test_status_sync.py -q`
  passes with 27 tests after adding the shared GitHub API URL guard for
  token-bearing runner and ops requests.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 754 tests and
  8 skipped tests after pinning token-bearing GitHub API requests to
  `https://api.github.com/repos/...` with credentials, fragments, traversal,
  and token query parameters rejected.
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py runner\runner.py runner\daily_insights.py runner\weekly_report.py runner\issue_sync.py runner\status_sync.py runner\close_on_gate.py runner\health_metrics.py scripts\ops\ci_executive_report.py -f json -o runtime\security\bandit-github-api-guard.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=7`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py tests\test_issue_sync.py tests\test_status_sync.py tests\test_health_metrics_process_safety.py -q`
  passes with 125 tests and 1 skipped symlink-platform case after adding shared
  GitHub repository ID validation to token-bearing runner/ops call sites.
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py runner\runner.py runner\daily_insights.py runner\weekly_report.py runner\issue_sync.py runner\status_sync.py runner\close_on_gate.py runner\health_metrics.py scripts\ops\ci_executive_report.py tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py`
  passes after adding shared GitHub repository ID validation.
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py runner\runner.py runner\daily_insights.py runner\weekly_report.py runner\issue_sync.py runner\status_sync.py runner\close_on_gate.py runner\health_metrics.py scripts\ops\ci_executive_report.py tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py`
  passes after adding shared GitHub repository ID validation.
- `python -m pytest tests\test_ctoa_full_workspace_audit.py tests\test_agent_http_security.py tests\test_security_hardening.py::test_runtime_smoke_keeps_credentials_on_loopback_api -q`
  passes with 34 tests after adding the shared loopback-only runtime smoke URL
  guard and making the generated roadmap keep that policy.
- `python -m pytest tests\ --ignore=tests\e2e -q` passes with 773 tests and
  8 skipped tests after keeping runtime smoke credentials and bearer tokens on
  local API targets only.
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py scripts\ops\runtime_smoke_e2e_8001.py scripts\ops\ctoa_full_workspace_audit.py -f json -o runtime\security\bandit-runtime-smoke-guard.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=1`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py tests\test_llm_provider_url_security.py tests\test_api_chat_safety.py -q`
  passes with 86 tests after adding fail-closed URL guards for local model,
  Azure provider, and API chat backend routing.
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  passes with 797 tests and 8 skipped tests after the LLM/model backend URL
  guard pass.
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py runner\llm_providers\local_model.py runner\llm_providers\azure_foundry.py api\main.py -f json -o runtime\security\bandit-llm-provider-url-guard.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=0`.
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py -q`
  passes with 69 tests after adding public discovery URL SSRF/secret guard
  coverage and a static contract for catalog/scout/ingest.
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py tests\test_issue_sync.py tests\test_status_sync.py -q`
  passes with 76 tests after rechecking shared runner HTTP guard consumers.
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py runner\agents\catalog_agent.py runner\agents\scout_agent.py runner\agents\ingest_agent.py -f json -o runtime\security\bandit-discovery-url-guard.json`
  reports `results=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
  `SEVERITY.LOW=0`, `errors=0`, and `skipped_tests=3`.
- `python -m pytest tests\test_ctoa_vps_secret_handling.py -q` passes with 15
  tests covering PAT validation, non-argv transfer, remote `.env` merge,
  temp-file cleanup, VPS user/host validation, literal SSH key path resolution,
  GS env secret transfer contracts, and shared validation for remote SQL,
  URL/list, service, git-ref, reseed timer inputs, generated reseed runtime
  guards, root-wrapper remote temp cleanup, private generated `.env` updates,
  and rejected URL warning redaction.
- `.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_vps_secret_handling.py tests\test_vps_python_parity.py -q`
  passes with 21 VPS operator/parity tests after the `ctoa-vps.ps1` remote temp
  hardening pass.
- `.\.venv\Scripts\python.exe -m pytest tests\test_vps_mobile_token_rotation_security.py -q`
  passes with 3 tests covering private temp files and root-only Mobile Console
  token rotation permissions.
- Git Bash `bash -n deploy/vps/rotate-mobile-token.sh` passes after the Mobile
  Console token rotation temp-file hardening pass.
- AST smoke for `Assert-EnvSecretValue` passes after extracting the function
  from `scripts\ops\ctoa-vps.ps1`; it accepts a safe token value and rejects
  empty, newline, whitespace, shell substitution, and backtick forms.
- AST smoke for `Assert-VpsUser` and `Assert-VpsHost` passes after extracting
  the functions from `scripts\ops\ctoa-vps.ps1`; it accepts valid lowercase
  user, IPv4, DNS, and bracketed IPv6 values, and rejects uppercase user,
  whitespace, invalid DNS labels, unbracketed IPv6, and shell metacharacters.
- AST smoke for VPS operator input validators passes after extracting the
  functions from `scripts\ops\ctoa-vps.ps1`; it accepts valid HTTP(S) URL
  lists, SQL literals, systemd service names, GS source refs, integer ranges,
  and UTC timer values, and rejects credentials, fragments, shell substitution,
  whitespace URLs, invalid service names, option-like refs, dotdot refs, invalid
  integers, and invalid times.
- Local Git Bash smoke for generated `reseed-tier.sh` helpers passes; it accepts
  valid HTTP(S) URLs and age values, and rejects unsafe schemes, whitespace,
  shell substitution, apostrophes, out-of-range ages, and invalid ages.
- `python -m pytest tests\test_vps_python_parity.py tests\test_suite.py::TestVPSConnectivity tests\test_ctoa_vps_secret_handling.py -q`
  passes with 29 tests.
- `ValidateDev` passes after the redesign and refreshes the dev package under
  `runtime\solteria_helper_dev`; live Solteria remains untouched.
- `SmokePreflight` passes for the refreshed Helper dev manifest.
- `SmokeStatus` now writes stable atomic JSON with simple sandbox process
  summaries, and `ReadyCheck` writes `ready_check.json` for missing-window or
  Select Character/modal-helper-offline blocker states.
- `solteria_helper_test_env.ps1` now enforces a separator-aware sandbox path
  guard before sandbox setup, launch, status, process attach, and stop flows.
  `SandboxClient` must stay under `%LOCALAPPDATA%` and must not equal or live
  under `SourceClient`, so a manually supplied sandbox path cannot alias the
  live Solteria client.
- The Helper release gate now consumes `smoke_status.json` and
  `ready_check.json` when `SmokeAttachAll` is blocked, so the next safe command
  progresses from `Launch` to `ReadyCheck` to `SmokeAttachAll` based on current
  sandbox evidence.
- Sandbox launch/ReadyCheck was attempted after the Phase 3 pass; the Helper
  rendered behind the Select Character modal until a test character was entered.
- In-world `SmokeAttachAll` then passed for run `20260706-1025`: coverage
  `16/16`, `modal_limited=false`, `acceptance_status=ready_for_visual_review`,
  and all expected view screenshots exist.
- `solteria_helper_release_gate.py` now blocks stale `SmokeAttachAll` evidence
  when the in-world smoke report is older than the current Helper dev manifest.
- `PromoteLiveCtoa -ApproveLiveDeploy` completed at `2026-07-06T11:06:46` for
  Helper `v1.1b`; live backup evidence is under
  `runtime\solteria_helper_dev\live_backup_20260706-110646`.
- `solteria_helper_release_gate.py` now accepts durable
  `live_promotion.json` evidence only when it contains the approval switch,
  is newer than the current manifest, and the live client files match the
  current manifest hashes.
- `GoalStatus` now reports P0-P5 passed, `release_gate=passed`,
  `releasable_to_live=True`, and next action
  `Live promotion is complete for the current staged package.`

## Current Risks
- Worktree is dirty with unrelated pre-existing local changes.
- Old OpenAI extension directories may contribute to stale VS Code extension
  state if command routing breaks.
- The old `ctoa_env_doctor.py` path is replaced by
  `scripts/ops/engine_brain_doctor.py`; historical references may still exist in
  older docs/memory.
- TFS source and packet/protocol sources are not present.
- Future Helper source, profile, package, or UI changes must rerun
  `ValidateDev`, `SmokePreflight`, in-world `SmokeAttachAll`, and
  `PromoteLiveCtoa -ApproveLiveDeploy` before being treated as live-promoted.
- The pre-commit Bandit scope is clear today, but broader manual security
  review is still open outside that scanner surface, especially remaining
  mobile console high-risk endpoints, Control Center action catalog, and
  runtime deployment exposure.

## Not Complete Yet

The full objective is not complete yet. Remaining work:

- Repomix remains optional; local `engine_brain_pack.py` is the primary
  secret-safe packer for now.
- Keep Docker runtime exposure checked after compose or profile changes; current
  local runtime has `running_broad=0` and `configured_broad=0`.
- Plan 2 has started with read-only evidence surfacing and stale-artifact
  detection; broader cockpit command gating, schema checks, and visual
  regression coverage remain next.
- If the user provides TFS source, index classes, packet flow, Lua interface, and
  architecture rules.
