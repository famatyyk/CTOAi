# CTOAi Security Hardening Note - 2026-07-06

## Scope

Practical repo-wide hardening wave focused on auth bootstrap, production startup
guards, command execution scan results, and release evidence correctness.

## Completed

- API production startup now fails closed when `CTOA_CORS_ORIGINS` is wildcard
  or missing.
- API production startup still requires a non-default `CTOA_JWT_SECRET`.
- API production startup now also runs a lightweight pre-import guard in
  `api/startup_guard.py`, so wildcard CORS, default JWT secrets, and production
  API self-registration without `CTOA_API_SELF_REGISTER_CODE` fail before
  heavier API dependencies are imported.
- API auth store bootstrap no longer seeds known default accounts in production;
  production must provision `CTOA_AUTH_STORE_FILE` ahead of startup.
- API auth store bootstrap now fails closed by default outside production too;
  local seed accounts require explicit `CTOA_ALLOW_SEED_ACCOUNTS=true` and
  `CTOA_SEED_*_PASSWORD` env vars.
- API auth-store and runner state artifact writes now avoid predictable sibling
  `*.tmp` paths. Auth JSON, runner YAML state, and runner execution-summary JSON
  use hidden PID/UUID temp files in the target directory, `fsync` before
  `replace`, and `finally` cleanup for partial temp artifacts. API auth-store
  reads now use a byte cap, reject symlinked or invalid existing stores, and
  fail closed instead of seeding over a bad store.
- Health Metrics latest snapshot writes now follow the same state-artifact
  contract. `runner/health_metrics.py` writes `health-latest.json` through a
  hidden PID/UUID temp file with `fsync`, atomic `replace`, and cleanup, so a
  symlinked latest snapshot is replaced instead of writing through it.
- Desktop Console settings now follow the same state-artifact contract.
  `desktop_console/app.py` reads `desktop-settings.json` through a byte cap,
  rejects symlinked settings, and fails closed to defaults for oversized,
  invalid, or non-object JSON; writes use a hidden PID/UUID temp file with
  `fsync`, atomic `replace`, and cleanup, so a symlinked settings path is
  replaced instead of writing through it.
- Mobile Console local operator state now follows the same state-artifact
  contract. Admin settings and idea parking JSON reads are byte-bounded and
  fail closed to defaults for oversized or invalid state, while writes use
  hidden PID/UUID temp files with `fsync`, atomic `replace`, and cleanup so
  symlinked state paths are replaced instead of written through.
- Product bootstrap local state now follows the same state-artifact contract.
  `scripts/ops/ctoa_product_bootstrap.py` writes `.ctoa-local/user-config.json`
  and `.ctoa-local/bootstrap-state.json` through hidden PID/UUID temp files
  with `fsync`, atomic `replace`, and cleanup so update-gate state is not left
  partially written and symlinked JSON state is replaced instead of written
  through.
- Product update gate local state reads now fail closed. `ctoa_update_gate.py`
  reads `.ctoa-local/bootstrap-state.json` through a byte cap, rejects symlinked
  state before reading through it, and returns stable `invalid_bootstrap_state`
  reason codes for malformed JSON, oversized state, unreadable state, and
  invalid version/schema values instead of raising parser tracebacks or echoing
  state contents.
- Helper/release-gate and sprint runtime state writes now follow the same
  non-predictable temp-file rule. Helper profile audit, Helper goal audit,
  Helper release gate, Solteria Helper PowerShell test-env report writes, and
  `sprint_state_sync.py` use PID+UUID/GUID temp names with cleanup instead of
  PID-only or fixed suffix temp paths.
- Bot client runtime profile config no longer silently swallows broad config
  load/coercion exceptions. Invalid or unreadable profile config records a
  non-secret diagnostic code, numeric coercion catches concrete errors, and
  profile saves use hidden PID/UUID temp files with `fsync`, atomic `replace`,
  and cleanup.
- API public member self-registration now defaults off in production and requires
  `CTOA_API_SELF_REGISTER_ENABLED=true` plus `CTOA_API_SELF_REGISTER_CODE`.
- API `/api/auth/register` no longer treats an empty auth store as permission to
  create the first `owner` or `operator`; privileged account creation always
  requires an authenticated owner token.
- Control Center local seed-login no longer embeds seed passwords in the Next
  route and requires localhost, non-production runtime,
  `CTOA_ENABLE_LOCAL_SEED_LOGIN=true`, and `CTOA_SEED_*_PASSWORD` env vars.
- Web `ctoa_token` cookie writes now use a shared `authCookies.ts` helper.
  Cookies remain `httpOnly`, `sameSite=lax`, and repo-scoped to `/`, and they
  gain the `Secure` flag automatically when `NODE_ENV=production`.
- `/api/auth` proxy responses now strip token-like backend fields recursively
  before returning JSON to the browser. Login/register/accept-invite still set
  the httpOnly `ctoa_token` cookie from the original backend token, but response
  bodies no longer expose `token`, `access_token`, `refresh_token`, nested
  token fields, token/password strings, or Windows/POSIX local paths.
- `authProxySanitizer.ts` centralizes that contract, and local
  `/api/auth/seed-login` now uses it too. Seed-login keeps backend-token
  extraction only for the httpOnly cookie while stripping nested token-like
  fields and sanitizing backend detail strings before browser JSON responses.
- Control Center action audit persistence now redacts common secret forms from
  `reason` and `output_preview` before writing
  `runtime/control-center/action-audit.jsonl`; the evidence drilldown remains
  sanitized as a second read-side guard.
- Control Center evidence and ops drilldowns now use the same shared redaction
  helper as audit persistence, so legacy or hand-written action-audit JSONL
  entries with token/password/Bearer/provider-token forms, including quoted
  JSON-like token/password/API-key fields, are sanitized before read-only panels
  return them.
- Control Center action-audit drilldown now reads oversized
  `runtime/control-center/action-audit.jsonl` files through a bounded, redacted
  tail sample instead of full-file `readFile`; the UI reports
  `truncated/sourceBytes/sampledBytes` and a `warn` state before sign-off.
- Control Center chat persistence and exports now use the shared redaction
  helper too. `localStorage` chat snapshots, transcript downloads, markdown
  exports, JSON chat logs, quality issues, and publication notes redact Bearer,
  provider-token, token/password/API-key, and quoted JSON-like secret fields
  before durable storage or export.
- Control Center evidence read endpoints now require operator-or-owner access
  before collecting local runtime evidence or reading markdown reports. This
  covers evidence JSON, ops detail payloads, release-evidence markdown, and API
  cost markdown so anonymous/member sessions cannot read local paths or action
  audit metadata.
- Control Center evidence and ops payloads now keep browser-visible file paths
  display-safe: repo-local paths are relative, and external absolute paths are
  collapsed to `[external]/name` before they reach the UI.
- Control Center Helper package hash checks now resolve `release_readiness.json`
  ZIP paths only inside the configured Helper dev lane. External absolute or
  escaping package paths fail closed as missing hash evidence instead of forcing
  Control Center to hash an arbitrary local file.
- `release_evidence_pack.py` now follows the same local evidence read discipline
  as Control Center: configured JSON reads are byte-bounded and symlink
  rejecting, action-audit JSONL is counted from a bounded tail sample, release
  markdown discovery ignores symlinked files, and symlinked Helper dev
  directories fail closed to missing Helper status.
- `ctoa_full_workspace_audit.py` now uses `lstat`/regular-file checks and skips
  symlinked files before size accounting or SHA256 hashing. This keeps the
  50k+ file workspace inventory from following repo-local symlinks into
  external local content. Its report now includes an audit-integrity gate for
  non-regular entry accounting, bounded hash counts, and sensitive-name file
  hash omission, and a validation-evidence gate backed by local runtime command
  evidence for Python tests, web lint/tests, diff check, and Engine Brain
  refresh/doctor/pack.
- Control Center release-evidence drilldown metadata now reads markdown titles
  through a small bounded prefix reader. Oversized or unsafe markdown falls back
  to the file name instead of loading the full evidence artifact for a heading.
- Control Center release-evidence and API-cost markdown report endpoints now
  run the same browser-visible sanitizer before returning text, so markdown
  responses redact token/password forms and collapse Windows or POSIX absolute
  local paths too, while preserving normal `/api/...` route text.
- Control Center release-evidence and API-cost markdown report endpoints now
  read configured report files through a physically bounded file-handle read:
  at most `max + 1` bytes are loaded, handles close in `finally`, and
  symlinked configured report files are rejected before `open`, while oversized
  markdown returns `413`. This keeps a bad env/path choice from making the
  route load a linked or very large local artifact into memory.
- Control Center configured JSON evidence reads now use a bounded file-handle
  reader too. Repo hygiene, API cost, Helper, Engine Brain, and runtime evidence
  JSON reject symlinked or oversized configured files and fail closed to
  missing/default status without exposing target contents.
- Control Center action-audit reads now share a bounded tail reader across
  Evidence and Ops. Symlinked audit paths are rejected before `open`, oversized
  logs surface a tail-limited `warn`, and Ops `recentActions` no longer performs
  a separate full-file read.
- Backend `/api/release-evidence` now applies the same evidence-response
  discipline for configured JSON: bounded reads, display-safe `evidence_path`,
  recursive token/password/API-key redaction, local absolute path collapse, and
  symlink rejection before `stat/open`, plus stable oversized/invalid/read-error
  messages that do not echo raw exceptions or file contents.
- FastAPI HTTP audit JSONL persistence now redacts token/password/API-key/Bearer
  forms and local absolute paths from `actor`, `ip`, `ua`, request path, and
  nested `meta` before writing `CTOA_AUDIT_LOG_FILE`, reducing leakage from
  spoofed headers such as `User-Agent` or `X-Forwarded-For`.
- Control Center action result output now runs through the same browser-visible
  sanitizer before `/api/control-center/actions` returns it to the UI. Successful
  stdout/stderr and local execution failure messages redact token/password
  forms and collapse Windows or POSIX absolute local paths before display or
  audit preview.
- `/api/control-center/actions` route-level error JSON now uses the same
  sanitizer for generic and authorization errors, so exception messages cannot
  echo token-like action IDs, Bearer values, or Windows/POSIX local paths to the
  browser.
- `/api/control-center` backend probe summaries and
  `/api/control-center/legacy` backend fetch details now also use the shared
  browser-visible sanitizer, so fallback status payloads redact token/password
  forms and collapse Windows/POSIX local paths before JSON responses.
- Control Center Python-backed actions now resolve only `CTOA_PYTHON_BIN` as an
  absolute existing executable or the repo-local `.venv` Python. They no longer
  fall back to PATH-only `python`/`python3`, and missing trusted Python is
  recorded as an audited failed action.
- Control Center action execution now resolves the workspace root correctly
  from either repo-root or `web/` working directories. Explicit
  `CTOA_WORKSPACE_ROOT` overrides must be absolute existing directories, and
  allowlisted action scripts must stay under that workspace root and exist
  before `execFile` is allowed to run.
- Control Center action script resolution now also checks real paths, so a
  repo-local symlinked parent or junction cannot point an allowlisted script
  path outside the workspace before `execFile`.
- Control Center action catalog reads now return only actions allowed for the
  current viewer role. Anonymous and member viewers no longer receive local
  `commandSummary` metadata, and the client action panel defensively renders no
  actions until a viewer role is available.
- Control Center action POST requests now fail closed on cross-site request
  signals before auth resolution or action execution. The route rejects
  mismatched `Origin`, cross-site `Sec-Fetch-Site`, and mismatched `Referer`
  headers so an existing `ctoa_token` cookie cannot be used to trigger local
  actions from another site.
- The same same-origin request guard now lives in `requestOriginGuard.ts` and
  also protects `/api/auth` POST forwarding before rate-limit, body parsing, or
  backend fetch. Cross-site `invite`, `setRole`, login/logout, and registration
  wrapper requests fail closed at the Next route boundary.
- The shared same-origin guard also protects `/api/chat` and local
  `/api/auth/seed-login` before rate-limit, body parsing, cookie/token
  forwarding, or backend fetch, preventing explicit cross-site prompts or local
  seed-login attempts.
- Web API base URL config now fails closed: `VPS_API_URL` and
  `NEXT_PUBLIC_API_URL` must be absolute HTTP(S) URLs, must not include
  credentials, path components, path separators, query strings, or fragments,
  and must use HTTPS for non-local hosts before Control Center proxy routes or
  browser API calls use them.
- Web proxy route rate limits now share the explicit proxy-header trust model:
  `/api/auth` and `/api/chat` ignore `X-Forwarded-For` and `X-Real-IP` by
  default, and use those headers only when `CTOA_TRUST_PROXY_HEADERS=true` with
  syntactically valid IP values.
- Desktop Console API and Control Center URLs now use the same fail-closed URL
  contract before settings, login, or browser launch use them: local HTTP is
  allowed, but remote hosts require HTTPS and URLs with credentials,
  query strings, or fragments are rejected without echoing rejected values.
- Desktop updater downloads now keep initial release asset URLs pinned to
  trusted GitHub HTTPS hosts and safe `.exe` asset names, while allowing signed
  query strings only on the final trusted GitHub asset CDN redirect that
  `requests` follows before writing the update file. Update downloads now also
  enforce a maximum size and write to a `.download` temp file that is atomically
  moved into place only after the full stream succeeds; oversized or failed
  streams clean up the partial temp file.
- `/api/chat` no longer forwards arbitrary client JSON fields to the backend
  chat API. The proxy now builds a strict payload from normalized messages plus
  allowlisted `model`, `route_mode`, and bounded `temperature`; debug routing,
  token-like fields, `max_tokens`, and other unrecognized fields are dropped.
- Backend chat route diagnostics are now operator-only: `/api/chat` and
  `/v1/chat/completions` require `owner` or `operator` before honoring
  `debug_route`, and returned route metadata is allowlisted so backend URLs,
  fallback backend URLs, and key-like values are not exposed to normal chat
  clients. Router stdout logs now use the same sanitized route view instead of
  dumping internal backend URLs into host logs.
- The API dev JWT fallback name now uses an explicit non-secret placeholder so
  production still rejects unset/default `CTOA_JWT_SECRET` while Bandit does not
  classify the local placeholder as a hardcoded secret.
- Public docs/site JS and runtime smoke scripts no longer carry legacy default
  login passwords.
- Public docs/site JS now normalizes API base URLs with the browser `URL`
  parser, rejects credentials/path/query/hash components, requires HTTPS for
  non-local API origins, avoids dynamic `innerHTML`, and keeps local fallback
  admin passwords in session storage instead of persistent `localStorage`.
- Public docs/site live dashboard now uses the same API-base guardrail pattern,
  keeps auth tokens session-scoped, removes dynamic `innerHTML` and inline
  handlers, and renders account/status/latest/server payloads with DOM nodes and
  `textContent`.
- Mobile console DB fallback execution no longer places `DB_PASSWORD` in local
  `psql` or `docker exec` command argv; password transfer uses environment
  handling instead.
- `runner/agents/db.py` no longer constructs a text DSN containing
  `password=...`; the agent connection pool receives DB connection fields as
  keyword arguments so secrets are not assembled into a loggable connection
  string. Agent-run DB write failure logs now sanitize `password=...`,
  `PGPASSWORD=...`, and PostgreSQL URL password forms before exception text is
  emitted.
- Mobile console command audit now redacts common secret forms from command
  strings before writing `logs/mobile-console-audit.log`, covering Bearer
  tokens, common provider tokens, `token=...`/`password=...` forms, and common
  long `--token`/`--password` style CLI options.
- Mobile console command execution now also redacts operator-facing stdout and
  stderr before returning command/status/log output to the UI. Safe-mode
  `/api/command` presets, full-access command output, runner report status
  output, and log tails are sliced and redacted for Bearer, provider-token,
  token/password, and `PGPASSWORD` forms without changing DB fallback stdout
  parsing. The `/api/logs` fallback path now reads only a bounded tail from the
  end of local log files and rejects symlinked logs before reading.
- Mobile console audit records now include actor accountability metadata:
  `actor`, `actor_role`, `auth_mode`, and `auth_transport`. The audit helper
  does not persist session tokens or CSRF tokens.
- Legacy mobile and desktop Intel guarded writes now require owner auth,
  `confirm=true`, and a non-empty audit reason before DB writes, orchestrator
  triggers, or client sync can run. Missing confirmation is audited before any
  runtime side effect.
- Mobile console cookie-authenticated mutations now have focused CSRF
  regression coverage: cookie-only POST/PUT/DELETE-style requests require
  `X-CSRF-Token`, while bearer/header-authenticated operator calls continue to
  work without a CSRF header.
- Legacy mobile console dashboard rendering no longer uses dynamic
  `innerHTML` in `mobile_console/static/app.js`; API payloads are rendered with
  DOM nodes and `textContent`, with
  `tests/test_mobile_console_static_xss_security.py` guarding against XSS-prone
  HTML-string regressions.
- Public docs-site owner reset now clears session-scoped admin auth data in
  addition to persistent local state: backend API token/user/role, admin session,
  and session-scoped local fallback admin passwords are removed before the reset
  flow rebuilds default public state.
- Mobile console generated-artifact APIs now return public artifact paths for
  manifest and Lua output references. `/api/agents/generated/latest` and SLO
  manifest observations no longer expose local absolute `GENERATED_DIR`,
  temp-directory, or unknown runtime paths to the dashboard JSON. Generated
  `latest.json` and run `manifest.json` reads now use a byte-capped,
  symlink-rejecting loader and fail closed to scan/default responses for
  oversized or invalid manifests.
- Mobile Console local metadata JSON reads now go through a byte-capped,
  symlink-rejecting loader. Command dictionary, product manifest, and product
  user config reads fail closed to defaults for oversized, invalid, symlinked,
  or non-object JSON before operator API responses are built.
- Mobile console file metadata responses now also use display-safe paths:
  admin settings, idea parking, auto-trainer report status, local disk probes,
  one-click generated directories, and client-sync result paths return public
  artifact names or repo-relative paths instead of absolute local host paths.
- Mobile console auto-trainer report reads are now physically bounded:
  `/api/agents/auto-trainer/latest` reads `latest.md` and `latest.json` through
  byte caps, reports markdown truncation, rejects oversized JSON with a stable
  status, and avoids returning raw parser exception text.
- Desktop Console updater downloads are now fail-closed around release assets:
  repository IDs must stay in `owner/repo` form, Windows assets must be safe
  `.exe` filenames without path separators, download URLs and final redirects
  must stay on trusted GitHub HTTPS hosts, and release-note URLs are sanitized
  before browser launch.
- Desktop Console no longer auto-runs downloaded update executables from the
  GUI; it downloads the package and asks the operator to verify/run it
  explicitly from Windows.
- Desktop Console update streams are size-bounded, written through a temporary
  `.download` file, cleaned up on failure, and moved into place only after a
  complete stream.
- The pre-commit Bandit scope now includes `desktop_console` alongside
  `runner`, `mobile_console`, and `scripts`, with a static contract test
  guarding that coverage.
- Mobile console safe-mode presets now execute through backend-owned
  `argv/cwd/env` specifications instead of raw command text. Legacy preset
  strings remain visible in `/api/presets`, but the backend no longer relies on
  `cd ...; ENV=... command` pseudo-shell text for allowlisted execution.
- Mobile console `/api/command` no longer treats legacy
  `CTOA_MOBILE_FULL_ACCESS=true` as permission to execute arbitrary command
  text over HTTP. The endpoint always routes through backend-owned presets and
  rejects non-preset command text.
- Mobile console health/auto-check status now reports `command_mode=presets`
  and never reports `full_access=true`; the legacy mobile UI no longer renders
  a full-command box, and the desktop admin console uses a readonly preset
  field backed by `/api/presets`.
- Mobile console server/intel target URLs now reject embedded credentials,
  query strings, fragments, backslashes, and decoded `.`/`..` path traversal
  before URLs are written to DB rows, audits, or dashboard responses.
- Mobile console local runtime proxy base URLs now fail closed before local
  proxy calls. `CTOA_API_BASE_URL` and `CTOA_INTEL_API_BASE_URL` must target
  `localhost`, `127.0.0.1`, `[::1]`, or `host.docker.internal`, and must not
  include credentials, query strings, fragments, backslashes, or decoded
  traversal before `/api/intel/*` or `/api/dashboard/release-evidence` can call
  `urlopen`. Invalid values return a generic `[invalid-local-runtime-api]`
  marker instead of echoing raw secret-bearing env URLs. Runtime proxy
  `URLError` and generic exception text is now redacted before browser JSON
  receives `error` fields, covering token/password forms from local backend
  failures.
- Mobile console local runtime proxy paths now fail closed before the validated
  base URL is joined. `_intel_api_proxy` and `_ctoa_api_proxy` accept only
  relative `/api/...` paths without query strings, fragments, empty segments,
  traversal, backslashes, or encoded separators; invalid paths return
  `[invalid-local-runtime-path]` without echoing secret-bearing path text.
- VPS agent-output runbook no longer documents `psql` DSNs that place
  `${DB_PASSWORD}` in command argv.
- Mobile console production startup defaults self-registration off and requires
  `CTOA_SELF_REGISTER_CODE` when self-registration is explicitly enabled.
- Mobile console self-registration now creates only `member` accounts, and
  `require_operator` enforces that operator endpoints require `operator` or
  `owner`. Members can authenticate for `/api/auth/me`, but cannot access
  operator command/status surfaces until an owner promotes them.
- Mobile console Intel target validation now rejects localhost, private IPs,
  link-local/metadata IPs, `.local` names, and single-label internal hosts in
  production unless `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true` is explicitly set.
- Mobile console Intel client sync now confines target, autoloader, and init-file
  writes to `CTOA_CLIENT_SCRIPTS_DIR` and validates paths before copying files.
  Init-file updates now reject symlinked or oversized init files before copying
  generated Lua, and autoloader/init writes use hidden PID/UUID temp files with
  `fsync` plus atomic replace. Generated Lua copies now reject symlinked or
  oversized sources, reject existing destination symlinks, and write through the
  same atomic temp-file path.
- Mobile console DB-backed account changes now revoke existing in-memory
  sessions for the affected user after password change, role change, or
  deactivation, so stale owner/operator tokens cannot keep old privileges.
- Bot DQL reward shaping no longer rewards `loot` in healthy no-target states,
  and the 1000-tick stress test now isolates local runtime Q-table state so CI
  does not inherit stale learned action dominance.
- OTClient Helper release evidence now reports durable live promotion as
  `status=promoted` when `live_promotion.json` and the passed release gate match.
- Passed Helper release gates no longer inherit stale `next_command` values from
  older goal-status artifacts.
- Training notebook package install no longer uses `shell=True`.
- Training supply-chain scan is now clean. The Kaggle fine-tune notebook
  requires `CTOA_TRAINING_MODEL_REVISION` to be an immutable 40-character
  Hugging Face commit SHA before `from_pretrained()` downloads, defaults
  `trust_remote_code` off unless `CTOA_TRAINING_TRUST_REMOTE_CODE=true`, and
  fails explicitly when no `.jsonl` dataset is mounted. The Colab Unsloth
  notebook now requires the same pinned model revision and remote-code opt-in.
  The GitHub dataset collector validates GitHub API/raw HTTPS hosts, allowlisted
  API query strings, repo identifiers, branches, decoded raw paths, and decoded
  dataset filenames before any `urlopen` or file write, rejects encoded
  traversal/backslashes, and no longer silently swallows download failures.
  `build_dataset.py` now uses deterministic non-security sampling and reports
  file read/build errors instead of `except/pass`.
- BRAVE prompt rendering no longer fails on incomplete evaluation/operator
  context. Missing template variables now render as `[UNKNOWN]`, so prompt,
  scoring, and eval workflows can continue with visible gaps instead of
  crashing on `KeyError`.
- Repo-local dev security tooling is available through `requirements-dev.txt`
  and the local `.venv`; the pre-commit Bandit scope now writes
  `runtime\security\bandit-precommit.json`.
- Bot low-severity static-scan findings are now cleared and folded into the
  pre-commit Bandit scope. Runtime jitter/Q-learning exploration uses
  `bot/safety/nonsecurity_random.py`, prior silent best-effort UI/OS exception
  paths now log concrete diagnostics, and `status_overlay.py` starts bot and
  macro-pad processes through `runner.process_safety`.
- Hybrid bot template cache/source handling is now bounded. Template names and
  types reject traversal, path separators, Windows-unsafe filename characters,
  and realpath escapes before cache reads/writes. Remote template source URLs
  now use the public-discovery URL guard plus stricter no-query/no-fragment
  checks, rejecting credentials, localhost/private/link-local or internal hosts,
  query strings, fragments, backslashes, and decoded traversal before
  `urlopen`; failed loads no longer echo raw source URLs.
- Hybrid bot metrics and profiler file outputs are now bounded to the selected
  metrics output directory. CSV/JSONL output names reject absolute paths,
  drive-style paths, `..`, backslashes, control characters,
  Windows-unsafe filename characters, unsupported extensions, realpath escapes,
  and existing output symlinks before read/write.
- Generator agent module output is now bounded to the generated-artifact tree.
  Queue-provided `output_file` values must stay under
  `CTOA_GENERATED_DIR/<server-slug>/`, reject absolute paths, drive-style paths,
  `..`, backslashes, control characters, Windows-unsafe filename characters, and
  output symlinks, and fail before writing generated Lua or updating module DB
  status.
- Generator agent manifest writes are now bounded by the same generated-artifact
  guard. Symlinked `<server-slug>` directories, `generated/manifests`, and
  `generated/manifests/latest.json` are rejected before per-run manifests or
  latest manifest pointers can be written outside `CTOA_GENERATED_DIR`.
- Generated manifest reads now use the same containment model:
  `runner/generator_validator_samples.py`, `runner/weekly_report.py`, and
  Mobile Console `_latest_manifest_payload` reject `latest.json`
  `manifest_path` values that resolve outside the configured
  `generated/manifests` directory before loading JSON or returning summaries.
- Generated manifest enumeration now uses the same containment model too.
  Mobile Console execution trend/SLO metrics, `nightly_stability.py`, and
  `night-report.py` skip symlinked run directories whose resolved
  `manifest.json` escapes `generated/manifests`.
- `night-report.py` now reads orchestrator logs through a bounded tail sample
  instead of full-file `read_text()`. The markdown report includes
  sampled/source byte counts and marks truncation as a tail sample, preventing
  large runtime logs from being fully loaded during evidence generation.
- Agent executor fallback deliverable writes are now bounded to safe
  repo-relative paths. Track A-D generic outputs reject absolute paths,
  drive-style paths, `..`, backslashes, control characters, Windows-unsafe
  filename characters, realpath escapes, and existing output symlinks before
  any file write.
- Non-security SHA1 fingerprints in OTMM assembly utilities now use
  `usedforsecurity=False`, removing the previous Bandit high-severity findings.
- `ctoa_helper_ui_preview.py` no longer evaluates extracted Lua expressions
  with Python `eval`; it uses a small AST numeric-expression evaluator.
- Catalog, scout, and ingest discovery agents now validate probed URLs through
  `runner.http_safety.require_public_discovery_url`, keeping public `http://`
  and `https://` discovery working while rejecting loopback, private,
  link-local/metadata, reserved, single-label, and internal-host targets plus
  credentials, fragments, token query parameters, backslashes, and decoded path
  traversal before `urlopen`. They still use verified TLS by default. Insecure
  TLS is available only through explicit legacy opt-ins:
  `CTOA_CATALOG_ALLOW_INSECURE_SSL`, `CTOA_SCOUT_ALLOW_INSECURE_SSL`, and
  `CTOA_INGEST_ALLOW_INSECURE_SSL`.
- Shared `runner.http_safety.require_http_url` now protects generic runner
  webhooks, template downloads, GS API validation, and other generic HTTP calls
  before `urlopen`.
- Phase-5 attention notification webhooks now use
  `runner.http_safety.require_notify_webhook_url` instead of a generic HTTP URL
  check. Slack and Discord destinations must use HTTPS, match allowlisted
  webhook hosts and path prefixes, and reject credentials, query strings,
  fragments, backslashes, empty/traversal segments, or encoded path separators
  before `urlopen`; rejected values return a stable `invalid_webhook_url`
  detail without echoing the URL.
- Token-bearing GitHub API wrappers now use
  `runner.http_safety.require_github_api_url`, which pins requests to
  `https://api.github.com/repos/{owner}/{repo}/...`, requires non-empty
  owner/repo path segments, and rejects credentials, fragments, traversal,
  encoded path separators, and token query parameters before any
  `Authorization: Bearer` header is sent. This covers runner live issue
  publishing, daily/weekly issue comments, issue/status sync, close-on-gate,
  health dashboard publishing, and the CI executive report fetcher.
- `runner.http_safety.require_github_repository` now validates
  `GITHUB_REPOSITORY`, `CTOA_REPO_OWNER`, and `CTOA_REPO_NAME`-derived inputs
  before those runner/ops publishers build GitHub API URLs. Repo IDs must be
  literal `owner/repo` values without empty segments, traversal, encoded
  separators, or unsupported characters.
- Runtime smoke now uses `runner.http_safety.require_loopback_http_url` for
  `CTOA_RUNTIME_SMOKE_BASE` and per-request URLs, so login credentials and
  bearer tokens stay on `127.0.0.1`, `localhost`, or `[::1]` without
  credentials, query strings, fragments, backslashes, or traversal.
- LLM/model backend routing now validates endpoints before prompts or provider
  keys are sent. Local model HTTP is limited to loopback and
  `host.docker.internal`; remote model backends require explicit opt-in and
  HTTPS; Azure provider endpoints require HTTPS and allowlisted Azure service
  hosts before `FOUNDRY_API_KEY` is passed to the SDK.
- `scripts/ops/azure_activity_alerts.py` now keeps generic webhook routing on
  `runner.http_safety.require_http_url`, while Discord-native delivery uses
  `runner.http_safety.require_discord_webhook_url` before `urlopen`. Discord
  payloads require HTTPS Discord webhook hosts and `/api/webhooks/...` paths,
  reject credentials/query/fragment/traversal/backslash/encoded separators, and
  no longer fall back to arbitrary generic webhook destinations.
- Azure Activity webhook listener startup now fails closed before binding a
  non-loopback host unless `CTOA_AZURE_INGEST_SECRET` is set.
  `scripts/ops/azure-alerts-runner.ps1` defaults listener mode to
  `127.0.0.1`, validates public exposure before starting Python, and keeps the
  ingest secret in the environment instead of adding it to child process argv.
- Runtime smoke checks no longer use Python `assert`, so checks are not removed
  by optimized bytecode.
- Engine Brain Docker bind auditing now detects unspecified bind addresses with
  `ipaddress` instead of broad-bind string literals.
- `runner.process_safety` now centralizes trusted subprocess execution and
  executable resolution. Publisher and validator agents use it for Git, gh,
  luac, and Python checks instead of relying on partial executable names.
- Git-backed ops scripts for full workspace audit, bridge replacement readiness,
  and runtime path guard now resolve Git through `CTOA_GIT_BIN`, PATH, or the
  standard Windows Git install path before execution.
- Bridge replacement readiness now catches only file read/decode errors while
  scanning tracked files instead of broadly swallowing all exceptions.
- Health metrics, service drift checks, and queue worker subprocess calls now
  resolve fixed executables before execution. Optional disk cleanup resolves
  `bash` through `CTOA_BASH_BIN`/PATH and runs through `runner.process_safety`.
- Queue worker startup logs now redact Redis URL credentials and query strings
  before displaying `CTOA_REDIS_URL`. Invalid queue payload JSON now becomes
  `action=unknown` without copying raw payload text into job metadata or
  results.
- Mobile console command execution now resolves command executables in the
  central `_run_argv` path before launching. The same subprocess guard now
  covers Windows tasklist probing for orchestrator state.
- Repo hygiene audit and Phase-5 nightly sync now use `runner.process_safety`
  for Git/SSH/SCP-style command execution instead of direct `subprocess.run`.
- `ctoa_loader.py` shell sync and file-opening paths now resolve trusted
  executables before launch instead of relying on direct subprocess or OS shell
  dispatch.
- `engine_brain_doctor.py` now resolves probed commands through
  `runner.process_safety` and returns stable unavailable/timeout statuses.
- Smoke/validator/nightly ops wrappers now resolve Python and command
  executables before launch through `runner.process_safety`.
- Sprint validators `028` and `041` through `070` now run focused regression
  checks through `runner.process_safety` instead of direct `subprocess.run`.
- `runner.process_safety` now also exposes `start_trusted` for trusted
  long-running process launches, and absolute executable path resolution is
  validated before launch.
- Rosetta bundle generation, KingsVale first-hit attach tooling, and the x64dbg
  ENC3 dynamic pass now resolve external tools and launch through
  `runner.process_safety`.
- `activation_agent.py` now runs its live-target sync hook through
  `runner.process_safety`, and its sync-report parsing no longer silently
  swallows broad exceptions.
- `runner/agents/executor.py` now emits a hardened `runner/drift_checker.py`
  generator output: generated drift checks resolve `systemctl` through
  `runner.process_safety`, run through `run_trusted`, and catch concrete
  execution/resolution errors. The same pass fixed runbook/checklist timestamp
  replacement so those generator paths no longer reference an undefined
  `governance` variable.
- `scripts/ops/sync-live-targets.py` now validates source/target roots and
  target child paths before replacing live target directories. It rejects target
  roots inside the source root, unsafe target names, symlinked source/target
  content, and destinations that resolve outside the live target root before
  `shutil.rmtree`.
- `scripts/ops/ctoa_loader.py` now resolves operator-supplied live target names
  through safe path parts only. `open` and `export` skip traversal candidates,
  absolute/drive-rooted candidates, and symlinked target directories so target
  lookup cannot escape the configured live target root. Manifest reads now also
  reject symlinked `live-manifest.json` files, list unsafe manifests as absent,
  and refuse symlinked export output paths before writing.
- `scripts/ops/ctoa-root-action.sh` no longer writes dashboard health output to
  a predictable `/tmp/ctoa-health.out` path from the root wrapper. It creates a
  private temp file with `mktemp`, passes that path to `curl -o`, reads it by
  variable, and removes it through an EXIT trap.
- `deploy/vps/wrappers/ctoa-root-action.sh` now uses the same private
  dashboard-health temp-file pattern before install to
  `/opt/ctoa/scripts/ops/ctoa-root-action.sh`; `healthcheck-one-shot` and
  `dashboard-snapshot` both call the guarded `PrintDashboardHealth` helper.
- `scripts/ops/gs-reset.sh` now validates env-provided API URLs and numeric
  wait/retry settings before service shutdown or health probes. The reset flow
  accepts only local HTTP(S) API endpoints on `127.0.0.1`, `localhost`, or
  `[::1]` without credentials, query strings, or fragments, and rejects
  non-positive retry/wait values before reaching `curl`.
- `scripts/ops/gs-api-validator.py` now independently enforces the same local
  API boundary for direct validator runs. `fetch_json` rejects non-loopback,
  credential-bearing, query, fragment, backslash, and traversal URLs before
  `urlopen`; `API_BASE_URL` must be a loopback origin without a path; rejected
  URLs use stable log text instead of echoing raw env values.
- `runner/agents/executor.py` no longer imports `subprocess`; the remaining
  subprocess examples there are generated documentation/script text only.
- `scripts/ops/sync-mythibia-client.ps1` now keeps the experimental unsafe
  runtime bootstrap behind a second explicit
  `CTOA_ALLOW_UNSAFE_RUNTIME_BOOTSTRAP=true` approval, resolves bootstrap paths
  under `ClientRoot`, and removes unsafe artifacts with `-LiteralPath`.
- `scripts/windows/install-ctoa-vscode-extensions.ps1` now uses
  separator-aware target containment for extension mirrors and uses
  `-LiteralPath` for recursive replacement of existing extension directories.
- VS Code Mobile Console debug/run configuration is now local-only and
  secret-free. `.vscode/launch.json` and the paired `.vscode/tasks.json` bind
  Mobile Console to `127.0.0.1`, reference `CTOA_*` environment variables
  instead of committed passwords/tokens, and require the shared Mobile Console
  env preflight before launch.
- Operator-facing Mobile Console launch guidance is local-only too:
  `.\ctoa.ps1 up`, `docs/MOBILE_CONSOLE.md`, and Desktop Console connection
  error hints use `uvicorn mobile_console.app:app --host 127.0.0.1 --port 8787`
  instead of `0.0.0.0`.
- `scripts/ops/watch-mythibia-client-sync.ps1` now runs under strict mode and
  rotates logs with literal paths plus archive path containment before removing
  old archives.
- `scripts/ops/orchestrator-loop.ps1` no longer launches a hidden inline
  `-EncodedCommand` that embeds DB environment values. It delegates to
  `scripts/ops/orchestrator-loop-worker.ps1`, passes `DB_PASSWORD` through the
  inherited process environment, verifies PID ownership through the worker
  command line before `Stop-Process`, and uses `-LiteralPath` for PID/log
  access.
- Windows scheduled-task installers now share
  `scripts/ops/windows-task-guard.ps1`: CTOAi task and Run-key names must stay
  in the `CTOA-*` namespace, repo scripts are resolved with separator-aware
  containment, watcher log paths stay under `%LOCALAPPDATA%\CTOA\logs`, and the
  HKCU Run fallback uses literal registry paths.
- `scripts/ops/run-hidden.vbs` now accepts only existing `.ps1` targets under
  the current repo root before launching hidden PowerShell, so the helper cannot
  be reused as a generic hidden launcher for arbitrary paths.
- PowerShell launchers now reject unsafe operator inputs before process launch:
  `ctoa.ps1 cc` and `scripts/windows/open-control-center.ps1` accept only
  HTTP(S) URLs, reject embedded credentials/query/fragment components without
  echoing rejected values, reject raw or decoded backslashes and decoded
  `.`/`..` path traversal, and require HTTPS for non-local hosts before probing
  or opening Control Center;
  `launch_kamil_client_macro_studio.ps1` requires an absolute existing `.exe`
  client path and a safe bot profile name; `watch-mythibia-client-sync.ps1`
  requires its sync script path to resolve to a repo-local `.ps1`. `ctoa.ps1`
  also uses explicit `Start-Process -FilePath` for Control Center and generated
  Helper preview/mockup HTML files.
- Solteria Helper sandbox operations now use a separator-aware
  `%LOCALAPPDATA%` containment guard and reject `SandboxClient` values that
  equal or sit inside `SourceClient`, preventing manual smoke/status/stop
  commands from aliasing the live Solteria client.
- LAB003 operator scripts now fail closed before network calls or child
  processes. `lab003_mobile_proxy_smoke.ps1`, `lab003_shift_guard.ps1`, and
  `lab003_shift_smoke_webhook.ps1` accept only local loopback HTTP(S) API base
  origins without credentials, paths, query strings, or fragments. Alert
  webhooks must be HTTPS unless loopback HTTP and cannot include credentials or
  fragments. `lab003_validate_bundle.ps1` is restored as the documented bundle
  target, and LAB003 child launches resolve the current `$PSHOME` PowerShell
  executable instead of PATH-only `powershell`.
- Bot VPS bootstrap no longer executes Docker's remote installer through
  `curl | sh`. `scripts/ops/bot/bootstrap_vps.sh` installs Docker from distro
  packages, requires root plus an existing validated `BOT_VPS_USER`, keeps the
  deploy directory under `/opt`, and leaves Grafana port `3000` closed unless
  `BOT_ALLOW_PUBLIC_GRAFANA=true` is explicitly set.
- Bot VPS deploy now validates SSH/rsync inputs before use:
  `scripts/ops/bot/deploy.sh` rejects unsafe remote users, unsafe host strings,
  and deploy directories outside `/opt`; uses `ssh --` and `scp --`; creates the
  remote directory with a quoted path; and passes `BOT_DEPLOY_DIR` into the
  remote build script as an argument instead of interpolating it in the heredoc.
- `scripts/ops/ctoa-vps.ps1 WriteGithubPat` no longer embeds the GitHub PAT in
  an SSH command string or base64-encoded remote script. The action validates
  the token shape, writes a local temp env file, copies it to a randomized
  remote temp path with `scp`, merges it into `/opt/ctoa/.env` with
  `install -m 600`, and removes both local and remote temp files.
- `scripts/ops/ctoa-vps.ps1` now installs the root-action wrapper through a
  randomized `/tmp/ctoa-root-action-<guid>.sh` remote temp path with cleanup,
  and the generated tiered-reseed installer updates `/opt/ctoa/.env` through
  `mktemp /opt/ctoa/.env.XXXXXX` instead of predictable `.env.tmp` paths.
- `deploy/vps/rotate-mobile-token.sh` no longer writes the new Mobile Console
  token to predictable `/tmp/ctoa_new_mobile_token`, `/opt/ctoa/.env.tmp`, or
  history `.tmp` paths. Token, `.env`, and history temp files now come from
  `mktemp`, cleanup runs on exit, and the secrets directory plus token file use
  root-only permissions.
- `scripts/ops/ctoa-vps.ps1` now validates `CTOA_VPS_USER` and `CTOA_VPS_HOST`
  before composing SSH/SCP targets. Remote users must match the lowercase
  system-user pattern, and hosts must be valid IPv4, DNS labels, or bracketed
  IPv6. The guard rejects empty values, leading/trailing whitespace, unbracketed
  IPv6, invalid DNS labels, path separators, shell metacharacters, and other
  unsupported target syntax. SSH key lookup now uses literal path resolution and
  requires an existing key file.
- `scripts/ops/ctoa-vps.ps1 EnsureGsEnvKeys` no longer embeds
  `OPENAI_API_KEY` or `GITHUB_PAT` in placeholder-expanded remote scripts. The
  action validates secret values for `.env` transfer, writes a local temp env
  file, copies it with `scp`, performs missing/empty-only remote upserts from
  that temp file, and removes local plus remote temp files.
- `scripts/ops/ctoa-vps.ps1` now uses shared validation helpers for remaining
  operator-provided remote-script inputs: server URLs and URL lists, server
  status filters, systemd service names, GS source refs, reseed timer values,
  and remote SQL string literals. The affected actions now cover
  `ShowScoutDetails`, `WatchScoutingUntilSettled`, `RegisterServer`,
  `RegisterServerList`, `MythibiaBurst`, `HealService`,
  `InstallTieredReseedTimers`, `InstallGsReset`, and
  `InstallGsResetFromBranch`.
- `scripts/ops/ctoa-vps.ps1 Resolve-ServerUrl` now emits a generic invalid URL
  fallback warning instead of echoing the rejected value, so credential-bearing
  or token-like bad inputs are not copied into operator logs.
- The generated `/opt/ctoa/scripts/ops/reseed-tier.sh` now revalidates
  runtime values read back from `/opt/ctoa/.env`: tier URLs must remain
  HTTP(S), short, whitespace-free, and free of shell/SQL metacharacters; stale
  error age values must be integers between 1 and 720; and SQL lookups/updates
  use a controlled `sql_literal` helper instead of `WHERE url='$url'`.
- Broad exception-control residuals in the pre-commit Bandit scope were reduced
  to zero: depack/parsing utilities now catch typed read/decode/zlib failures,
  runner/mobile fallback paths now record diagnostics, and x64dbg capture
  helpers preserve breakpoint/cleanup errors in evidence instead of silently
  swallowing them.
- Bandit scan coverage was restored for legacy ENC3/runtime tooling:
  `capture_runtime_loader_transform_live.py`, `depack_top_candidates.py`, and
  `triage_entropy_carves.py` now compile under the repo Python. The live
  capture tool marks non-security SHA1 fingerprints with
  `usedforsecurity=False` and records breakpoint/cleanup probe failures in
  structured diagnostics instead of silently passing.
- Local Docker runtime exposure now matches the hardened compose defaults:
  `docker compose up -d --remove-orphans api postgres` removed stale
  broad-binding orphan containers and left `ctoa-api` bound to
  `127.0.0.1:8001` with `ctoa-postgres` internal-only.
- Web supply-chain audit is currently clean. `web/package.json` pins
  `postcss` to `8.5.16` and uses an npm override so Next's transitive PostCSS
  dependency dedupes to the patched version, clearing
  `GHSA-qx2v-qp2m-jg93` from `npm audit`.
- Web dependency security now has a static regression guard:
  `tests/test_web_dependency_security.py` verifies the PostCSS pin/override and
  rejects a vulnerable nested `next/node_modules/postcss` lockfile tree.

## Validation

- `.\.venv\Scripts\python.exe -m pytest tests\test_azure_activity_listener_security.py tests\test_azure_activity_alerts.py -q`
  - 11 passed
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 881 passed, 13 skipped
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\azure_activity_webhook_listener.py tests\test_azure_activity_listener_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\azure_activity_webhook_listener.py tests\test_azure_activity_listener_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check scripts\ops\azure_activity_webhook_listener.py tests\test_azure_activity_listener_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_vscode_workspace_security.py tests\test_tasks_json_hygiene.py -q`
  - 5 passed
- `.\.venv\Scripts\python.exe -m py_compile tests\test_vscode_workspace_security.py tests\test_tasks_json_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check tests\test_vscode_workspace_security.py tests\test_tasks_json_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check tests\test_vscode_workspace_security.py tests\test_tasks_json_hygiene.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 857 passed, 13 skipped
- `.\.venv\Scripts\python.exe -m pytest tests\test_powershell_launcher_security.py -q`
  - 8 passed
- `.\.venv\Scripts\python.exe -m py_compile tests\test_powershell_launcher_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check tests\test_powershell_launcher_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check tests\test_powershell_launcher_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 854 passed, 13 skipped
- `npm test -- chatTranscript`
  - 5 passed
- `npm test -- chatTranscript src/app/api/auth/seed-login/route.test.ts`
  - 10 passed
- `npx eslint src/lib/chatTranscript.ts src/components/ControlCenterChatPanel.tsx src/lib/__tests__/chatTranscript.test.ts src/app/api/auth/seed-login/route.test.ts`
  - passed
- `npx tsc --noEmit --pretty false`
  - passed
- `npm test`
  - 90 passed across 21 web test files
- `npm run lint`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_hybrid_bot_file_safety.py -q`
  - 13 passed, 1 skipped
- `.\.venv\Scripts\python.exe -m py_compile runner\hybrid_bot\file_safety.py runner\hybrid_bot\metrics.py runner\hybrid_bot\performance_profiler.py tests\test_hybrid_bot_file_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check runner\hybrid_bot\file_safety.py runner\hybrid_bot\metrics.py runner\hybrid_bot\performance_profiler.py tests\test_hybrid_bot_file_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check runner\hybrid_bot\file_safety.py runner\hybrid_bot\metrics.py runner\hybrid_bot\performance_profiler.py tests\test_hybrid_bot_file_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit -r runner\hybrid_bot -f json -o runtime\security\bandit-hybrid-bot-file-safety.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`, `nosec=0`
- `.\.venv\Scripts\python.exe -m bandit -r api agents bot desktop_console mobile_console runner scoring scripts training prompts -f json -o runtime\security\bandit-broad-current.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=26`, `nosec=1`
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 851 passed, 10 skipped
- `.\.venv\Scripts\python.exe -m pytest tests\test_executor_deliverable_security.py -q`
  - 9 passed, 1 skipped
- `.\.venv\Scripts\python.exe -m py_compile runner\agents\executor.py tests\test_executor_deliverable_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check runner\agents\executor.py tests\test_executor_deliverable_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check runner\agents\executor.py tests\test_executor_deliverable_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\agents\executor.py -f json -o runtime\security\bandit-executor-agent.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`, `nosec=0`
- `.\.venv\Scripts\python.exe -m bandit -r api agents bot desktop_console mobile_console runner scoring scripts training prompts -f json -o runtime\security\bandit-broad-current.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=26`, `nosec=1`
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 834 passed, 9 skipped
- `.\.venv\Scripts\python.exe -m pytest tests\test_generator_agent_output_security.py -q`
  - 7 passed, 3 skipped; covers generated output containment and manifest
    symlink guardrails
- `.\.venv\Scripts\python.exe -m py_compile runner\agents\generator_agent.py tests\test_generator_agent_output_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check runner\agents\generator_agent.py tests\test_generator_agent_output_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check runner\agents\generator_agent.py tests\test_generator_agent_output_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\agents\generator_agent.py -f json -o runtime\security\bandit-generator-agent.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m bandit -r runner\agents -f json -o runtime\security\bandit-runner-agents.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m bandit -r api agents bot desktop_console mobile_console runner scoring scripts training prompts -f json -o runtime\security\bandit-broad-current.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=26`
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 824 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m pytest tests\test_template_library_security.py tests\test_integration_simple.py::TestTemplateLibrary -q`
  - 15 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_template_library_security.py tests\test_integration_simple.py::TestTemplateLibrary tests\test_agent_http_security.py -q`
  - 119 passed after remote template source SSRF guard hardening
- `.\.venv\Scripts\python.exe -m py_compile runner\hybrid_bot\template_library.py tests\test_template_library_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\hybrid_bot\template_library.py tests\test_template_library_security.py tests\test_agent_http_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check runner\hybrid_bot\template_library.py tests\test_template_library_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check runner\hybrid_bot\template_library.py tests\test_template_library_security.py tests\test_agent_http_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check runner\hybrid_bot\template_library.py tests\test_template_library_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\hybrid_bot\template_library.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`
- `.\.venv\Scripts\python.exe -m bandit -r runner\hybrid_bot -f json -o runtime\security\bandit-hybrid-template-library.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`
- `.\.venv\Scripts\python.exe -m bandit -r api agents bot desktop_console mobile_console runner scoring scripts training prompts -f json -o runtime\security\bandit-broad-current.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=26`
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 824 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_framework.py tests\test_api_cost_optimizer_agent.py -q`
  - 17 passed
- `.\.venv\Scripts\python.exe -m py_compile prompts\braver_templates.py tests\test_agent_framework.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check prompts\braver_templates.py tests\test_agent_framework.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check prompts\braver_templates.py tests\test_agent_framework.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit -r prompts scoring evals -f json -o runtime\security\bandit-prompts-scoring-evals.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m py_compile training\scripts\collect_github.py training\scripts\build_dataset.py tests\test_training_supply_chain_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check training\scripts\collect_github.py training\scripts\build_dataset.py tests\test_training_supply_chain_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check training\scripts\collect_github.py training\scripts\build_dataset.py tests\test_training_supply_chain_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_training_supply_chain_security.py -q`
  - 7 passed
- `.\.venv\Scripts\python.exe -m bandit -r training -f json -o runtime\security\bandit-training.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=5`
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 824 passed, 8 skipped
- `git diff --check`
  - No whitespace errors; line-ending warnings only.
- `.\.venv\Scripts\python.exe -m pytest tests\test_phase5_nightly_sync.py tests\test_phase5_nightly_sync_more.py tests\test_agent_http_security.py -q`
  - 110 passed
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py scripts\ops\phase5_nightly_sync.py tests\test_agent_http_security.py tests\test_phase5_nightly_sync_more.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py scripts\ops\phase5_nightly_sync.py tests\test_agent_http_security.py tests\test_phase5_nightly_sync.py tests\test_phase5_nightly_sync_more.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py scripts\ops\phase5_nightly_sync.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`
- `.\.venv\Scripts\python.exe scripts\ops\ctoa_full_workspace_audit.py`
  - refreshed `runtime\audits\ctoai-full-workspace-audit.json`,
    `docs\audits\CTOAI_FULL_WORKSPACE_AUDIT_2026-07-06.md`, and
    `docs\roadmaps\CTOAI_THREE_DEVELOPMENT_PLANS_2026-07-06.md`
- `.\ctoa.ps1 brain refresh`
  - `doc_sync_status=passed`
  - `secret_guardrail_status=passed`
- `.\ctoa.ps1 brain doctor`
  - `overall_status=warn`, `fail=0`, `docker.status=ok`,
    `running_broad=0`, `configured_broad=0`
- `.\ctoa.ps1 brain pack security`
  - 13 sections included, 3 generated indexes truncated
- `.\.venv\Scripts\python.exe -m py_compile training\kaggle-notebook\ctoa_finetune.py training\scripts\collect_github.py training\scripts\build_dataset.py tests\test_training_supply_chain_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check training\kaggle-notebook\ctoa_finetune.py training\scripts\collect_github.py training\scripts\build_dataset.py tests\test_training_supply_chain_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff format --check training\kaggle-notebook\ctoa_finetune.py training\scripts\collect_github.py training\scripts\build_dataset.py tests\test_training_supply_chain_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_training_supply_chain_security.py -q`
  - 6 passed
- `.\.venv\Scripts\python.exe -m bandit -r training -f json -o runtime\security\bandit-training-after.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=5`
- `.\.venv\Scripts\python.exe -m bandit -r bot training scoring agents -f json -o runtime\security\bandit-bot-training-after.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=6`
- `.\.venv\Scripts\python.exe -m pytest tests\test_static_security_scan_contract.py tests\unit\bot\test_humanizer.py tests\unit\bot\test_safety.py tests\unit\bot\test_sprint6.py tests\unit\bot\test_ml_model.py tests\unit\bot\test_decision.py tests\unit\bot\test_movement_follow.py -q`
  - 58 passed
- `.\.venv\Scripts\python.exe -m bandit -r bot -f json -o runtime\security\bandit-bot-after.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=21`
- `python -m pytest tests\test_security_hardening.py tests\test_release_evidence_pack.py -q`
  - 16 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py -q`
  - 15 passed, 1 skipped; covers backend `/api/release-evidence` path/secret
    redaction plus oversized and symlinked evidence rejection
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py tests\test_release_evidence_pack.py tests\test_api_auth_registration_security.py tests\test_api_chat_safety.py -q`
  - 57 passed; covers API security, release-evidence pack, auth registration,
    chat safety, and HTTP audit redaction together
- `.\.venv\Scripts\python.exe -m pytest tests\test_api_auth_registration_security.py tests\test_security_hardening.py -q`
  - 21 passed; covers FastAPI HTTP audit redaction for spoofed headers plus
    core API security hardening checks
- `.\.venv\Scripts\python.exe -m ruff check api\main.py tests\test_security_hardening.py tests\test_api_auth_registration_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile api\main.py tests\test_security_hardening.py tests\test_api_auth_registration_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit api\main.py -f json`
  - `results=0`, `errors=0`, no low/medium/high findings
- `python -m pytest tests\test_api_auth_registration_security.py -q`
  - 5 passed
- `python -m pytest tests\test_api_auth_registration_security.py tests\test_security_hardening.py tests\test_api_chat_safety.py -q`
  - 43 passed
- `python -m pytest tests\test_security_hardening.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_user_accounts_api.py -q`
  - 26 passed
- `python -m pytest tests\test_mobile_console_user_accounts_api.py -q`
  - 15 passed
- `python -m pytest tests\test_mobile_console_user_accounts_api.py tests\test_security_hardening.py tests\test_mobile_console_capability_gate.py -q`
  - 30 passed
- `python -m pytest tests\test_security_hardening.py tests\test_mobile_console_db_exec_security.py -q`
  - 15 passed
- `python -m pytest tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_db_exec_security.py tests\test_security_hardening.py -q`
  - 17 passed
- `python -m pytest tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_command_execution_security.py -q`
  - 5 passed
- `python -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_db_exec_security.py -q`
  - 7 passed
- `python -m pytest tests\test_mobile_console_static_xss_security.py -q`
  - 2 passed
- `node --check mobile_console\static\app.js`
  - passed
- `node --test tests\js\dashboard_helpers.test.js`
  - 2 passed
- `python -m pytest tests\test_mobile_console_capability_gate.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_command_execution_security.py -q`
  - 33 passed
- `python -m pytest tests\test_mobile_console_csrf_security.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_ideas_api.py -q`
  - 11 passed
- `python -m pytest tests\test_mobile_console_csrf_security.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_live_dashboard_profile_api.py -q`
  - 52 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 63 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py -q`
  - 22 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 69 passed
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 798 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 804 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console -f json -o runtime\security\bandit-mobile-console.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `python -m py_compile mobile_console\app.py`
  - passed
- `python -m pytest tests\ --ignore=tests\e2e -q`
  - 700 passed, 3 skipped
- `python -m pytest tests\test_mobile_console_capability_gate.py tests\test_mobile_console_api_contract_snapshot.py -q`
  - 4 passed
- `python -m pytest tests\unit\bot\test_ml_model.py tests\integration\bot\test_stress.py -q`
  - 26 passed
- `python -m pytest tests\test_engine_brain_pack.py::test_engine_brain_pack_supports_helper_profile -q`
  - 1 passed
- `python -m pytest tests\test_security_hardening.py tests\test_mobile_console_db_exec_security.py -q`
  - 14 passed
- `python -m pytest tests\test_mobile_console_url_validation_security.py -q`
  - 10 passed
- `python -m pytest tests\test_mobile_console_client_sync_security.py -q`
  - 5 passed
- `python -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_db_exec_security.py tests\test_security_hardening.py -q`
  - 29 passed
- `python -m pytest tests\test_security_hardening.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_url_validation_security.py -q`
  - 24 passed
- `python -m pytest tests\test_mobile_console_capability_gate.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_live_dashboard_profile_api.py -q`
  - 16 passed
- `python -m pytest tests\test_mobile_console_capability_gate.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_user_accounts_api.py -q`
  - 29 passed
- `python -m pytest tests\test_agent_http_security.py tests\test_ctoa_helper_ui_preview_security.py tests\test_static_security_scan_contract.py tests\test_mobile_console_url_validation_security.py -q`
  - 25 passed
- `python -m pytest tests\test_ctoa_loader_process_safety.py tests\test_engine_brain_doctor.py tests\test_process_safety.py -q`
  - 11 passed
- `python -m pytest tests\test_ctoa_loader_process_safety.py -q`
  - 7 passed, 4 skipped
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\ctoa_loader.py -f json -o runtime\security\bandit-ctoa-loader.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `python -m pytest tests\test_sync_live_targets_security.py tests\test_ctoa_loader_process_safety.py tests\test_ops_process_safety.py::test_activation_agent_sync_hook_uses_resolved_python -q`
  - 11 passed, 5 skipped
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\sync-live-targets.py -f json -o runtime\security\bandit-sync-live-targets.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `python -m pytest tests\test_ops_process_safety.py tests\test_nightly_stability_artifact.py tests\test_sprint029_ci_evidence.py tests\test_sprint029_nightly_trend.py -q`
  - 8 passed
- `python -m pytest tests\test_ops_process_safety.py tests\test_sprint041_validate.py tests\test_sprint042_validate.py tests\test_sprint067_validate.py tests\test_sprint070_validate.py tests\test_sprint_validator_contracts.py -q`
  - 26 passed
- `python -m pytest tests\test_process_safety.py tests\test_ops_process_safety.py tests\test_runner_imports.py -q`
  - 16 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_ops_process_safety.py tests\test_process_safety.py -q`
  - 17 passed
- `.\.venv\Scripts\python.exe -m ruff check runner\agents\executor.py runner\drift_checker.py tests\test_ops_process_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\agents\executor.py runner\drift_checker.py tests\test_ops_process_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit -r api agents bot desktop_console mobile_console runner scoring scripts training -f json -o runtime\security\bandit-broad-python.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=26`
- `.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt -f json -o runtime\security\pip-audit.json`
  - no known vulnerabilities found
- `npm audit --json` in `web\`
  - 0 total vulnerabilities across 584 dependencies
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=21`
  - `B105=0`, `B110=0`, `B112=0`, `B404=0`, `B603=0`, `B607=0`
- `.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt -f json`
  - `vulns=0`
- `npm audit --json` in `web\`
  - `info=0`, `low=0`, `moderate=0`, `high=0`, `critical=0`, `total=0`
- `python -m pytest tests\test_docs_site_security.py tests\test_web_dependency_security.py -q`
  - 10 passed
- `node --check docs\site\script.js`
  - passed
- `node -e "... vm.Script(... docs/site/live-dashboard.html inline scripts ...)"`
  - 1 inline script parsed
- `python -m pytest tests\test_ctoa_root_action_security.py tests\test_suite.py::TestVPSConnectivity::test_ctoa_root_action_supports_phase5_guardrail_actions -q`
  - 3 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_vps_root_action_wrapper_security.py tests\test_ctoa_root_action_security.py tests\test_ctoa_vps_secret_handling.py -q`
  - 17 passed
- Git Bash parser check for `scripts\ops\ctoa-root-action.sh`
  - passed
- Git Bash parser check for `deploy/vps/wrappers/ctoa-root-action.sh`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_gs_reset_security.py -q`
  - 2 passed
- Git Bash parser check for `scripts\ops\gs-reset.sh`
  - passed
- Local Git Bash smoke for `gs-reset.sh` URL and integer validators
  - passed; accepted local API URLs and positive integers, rejected unsafe
    schemes, remote hosts, credentials, query/fragment components, paths in
    `API_BASE_URL`, and non-positive/non-integer wait or retry values.
- `.\.venv\Scripts\python.exe -m pytest tests\test_gs_api_validator_security.py tests\test_gs_reset_security.py tests\test_agent_http_security.py -q`
  - 103 passed
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\gs-api-validator.py tests\test_gs_api_validator_security.py tests\test_gs_reset_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\gs-api-validator.py tests\test_gs_api_validator_security.py tests\test_gs_reset_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\gs-api-validator.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`
- Direct `gs-api-validator.py` smoke with remote `API_BASE_URL` and
  `API_HEALTH_URL`
  - returned exit code `3` after rejecting unsafe local API URLs before network
    access
- Git Bash parser check for every `scripts\**\*.sh` file
  - passed
- `python -m pytest tests\test_health_metrics_process_safety.py tests\test_agent_http_security.py tests\test_process_safety.py tests\test_ops_process_safety.py -q`
  - 25 passed
- `python -m pytest tests\test_azure_activity_alerts.py tests\test_phase5_nightly_sync.py tests\test_agent_http_security.py -q`
  - 26 passed
- `python -m py_compile scripts\ops\azure_activity_alerts.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_azure_activity_alerts.py tests\test_agent_http_security.py -q`
  - 107 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_azure_activity_listener_security.py tests\test_phase5_nightly_sync_more.py tests\test_phase5_nightly_sync.py -q`
  - 30 passed
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py scripts\ops\azure_activity_alerts.py tests\test_agent_http_security.py tests\test_azure_activity_alerts.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py scripts\ops\azure_activity_alerts.py tests\test_agent_http_security.py tests\test_azure_activity_alerts.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py scripts\ops\azure_activity_alerts.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`
- `python -m pytest tests\test_runner_agent_db_security.py tests\test_mobile_console_db_exec_security.py tests\test_process_safety.py -q`
  - 11 passed
- `python -m py_compile runner\agents\db.py`
  - passed
- `python -m pytest tests\test_mythibia_sync_security.py -q`
  - 3 passed
- PowerShell parser check for `scripts\ops\sync-mythibia-client.ps1`
  - passed
- `python -m pytest tests\test_vscode_extension_installer_security.py -q`
  - 2 passed
- PowerShell parser check for `scripts\windows\install-ctoa-vscode-extensions.ps1`
  - passed
- `python -m pytest tests\test_mythibia_watcher_security.py -q`
  - 3 passed
- PowerShell parser check for `scripts\ops\watch-mythibia-client-sync.ps1`
  - passed
- `python -m pytest tests\test_orchestrator_loop_security.py -q`
  - 4 passed
- PowerShell parser check for `scripts\ops\orchestrator-loop.ps1` and
  `scripts\ops\orchestrator-loop-worker.ps1`
  - passed
- `.\scripts\ops\orchestrator-loop.ps1 -Action status`
  - passed; reported stopped without launching a background process
- `python -m py_compile scripts\ops\capture_runtime_loader_transform_live.py scripts\ops\depack_top_candidates.py scripts\ops\triage_entropy_carves.py`
  - passed
- `python -m pytest tests\test_static_security_scan_contract.py tests\test_orchestrator_loop_security.py -q`
  - 6 passed
- `python -m pytest tests\test_windows_task_autostart_security.py -q`
  - 5 passed
- PowerShell parser check for `scripts\ops\windows-task-guard.ps1` and all
  changed scheduled-task install/remove scripts
  - passed
- PowerShell guard smoke for `Assert-CtoaTaskName`, `Assert-CtoaRunKeyName`,
  and `Assert-CtoaStartTime`
  - passed
- `cscript.exe //NoLogo scripts\ops\run-hidden.vbs scripts\ops\run-hidden.vbs`
  - passed; rejected non-PS1 target with exit code 2
- `python -m pytest tests\test_windows_task_autostart_security.py tests\test_mythibia_watcher_security.py tests\test_static_security_scan_contract.py -q`
  - 10 passed
- `python -m pytest tests\test_powershell_launcher_security.py tests\test_mythibia_watcher_security.py tests\test_vps_python_parity.py::test_control_center_launcher_uses_repo_local_python -q`
  - 10 passed
- `python -m pytest tests\test_powershell_launcher_security.py tests\test_vps_python_parity.py -q`
  - 11 passed
- PowerShell parser check for `ctoa.ps1`,
  `scripts\windows\open-control-center.ps1`,
  `scripts\ops\launch_kamil_client_macro_studio.ps1`, and
  `scripts\ops\watch-mythibia-client-sync.ps1`
  - passed
- Negative launcher smoke for `file://` Control Center URLs, non-local HTTP
  Control Center URLs, unsafe profile overrides, relative client paths, and
  out-of-repo watcher sync scripts
  - passed
- `python -m pytest tests\test_bot_vps_bootstrap_security.py -q`
  - 4 passed
- `C:\Program Files\Git\bin\bash.exe -n scripts/ops/bot/bootstrap_vps.sh`
  - passed
- `python -m pytest tests\test_bot_vps_deploy_security.py tests\test_bot_vps_bootstrap_security.py -q`
  - 8 passed
- `C:\Program Files\Git\bin\bash.exe -n scripts/ops/bot/deploy.sh`
  - passed
- Negative deploy smoke for unsafe host, unsafe user, and out-of-`/opt`
  `BOT_DEPLOY_DIR`
  - passed
- `npm test`
  - 70 passed
- `npm test -- config`
  - 7 passed
- `npm test -- --run src/lib/__tests__/config.test.ts`
  - 9 passed; covers fail-closed web API base URL origin-only parsing,
    including rejection of path components and path separators without echoing
    rejected values
- `npm test`
  - 105 passed across 24 web test files after the API base URL origin-only
    guard
- `npx eslint src/lib/config.ts src/lib/__tests__/config.test.ts`
  - passed
- `npx tsc --noEmit --pretty false`
  - passed
- `npm test -- chat/route normalizeMessages`
  - 6 passed
- `npm test -- authCookies auth/route seed-login chat/route requestOriginGuard`
  - 17 passed
- `npm test -- controlCenterActions`
  - 16 passed; covers trusted Python, workspace/script containment, and
    symlinked-parent realpath escape rejection
- `npm test -- control-center/actions controlCenterActions`
  - 18 passed
- `npm test -- controlCenterActions controlCenterEvidence controlCenterOps`
  - 20 passed; covers shared action-audit redaction across persistence,
    evidence drilldown, ops detail payloads, and quoted JSON-like secret fields
- `npm test -- src/lib/__tests__/controlCenterEvidenceAccess.test.ts src/app/api/control-center/evidence/route.test.ts src/app/api/control-center/actions/route.test.ts src/lib/__tests__/controlCenterActions.test.ts src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts`
  - 32 passed; covers operator-gated evidence reads before runtime evidence
    collection or markdown file reads
- `npm test -- --run src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts src/app/api/control-center/evidence/route.test.ts src/app/api/control-center/actions/route.test.ts`
  - 20 passed; covers Control Center release-evidence drilldown,
    runtime-vs-tracked comparison, sanitized action-audit drilldown, ops
    propagation, route access, and action route guard behavior
- `npx eslint src/lib/controlCenterEvidence.ts src/lib/controlCenterOps.ts src/components/ControlCenterEvidencePanel.tsx src/components/ControlCenterDetailPanels.tsx src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts src/app/api/control-center/evidence/route.test.ts src/app/api/control-center/actions/route.test.ts`
  - passed
- `npx tsc --noEmit --pretty false`
  - passed
- `npm test`
  - 105 passed across 24 web test files after the Control Center
    release-evidence/action-audit drilldown pass
- `npm test -- controlCenterEvidence.test.ts`
  - 4 passed; covers bounded, redacted action-audit tail sampling for oversized
    JSONL logs
- `npx eslint src/lib/controlCenterEvidence.ts src/components/ControlCenterEvidencePanel.tsx src/lib/__tests__/controlCenterEvidence.test.ts`
  - passed
- `npx tsc --noEmit`
  - passed
- `npm test`
  - 106 passed across 24 web test files after bounded action-audit drilldown
    sampling
- `npm test -- src/lib/__tests__/controlCenterDisplayPath.test.ts src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts src/app/api/control-center/evidence/route.test.ts`
  - 13 passed; covers display-safe Control Center evidence paths for repo-local
    and external absolute paths
- `npm test -- src/lib/__tests__/controlCenterMarkdownReport.test.ts src/lib/__tests__/controlCenterDisplayPath.test.ts src/app/api/control-center/evidence/route.test.ts`
  - 13 passed; covers markdown report secret redaction and display-safe
    Control Center evidence paths before browser response
- `npm test -- --run src/app/api/control-center/evidence/route.test.ts src/lib/__tests__/controlCenterMarkdownReport.test.ts`
  - 15 passed; covers symlinked configured markdown report rejection before
    `open`, bounded markdown report reads, oversized report `413` responses, no
    file opens after access denial, and file-handle cleanup after bounded reads
- `npm test -- --run src/lib/__tests__/controlCenterEvidence.test.ts src/lib/__tests__/controlCenterOps.test.ts`
  - 11 passed; covers bounded release markdown title extraction, bounded
    configured JSON evidence reads, Helper package hash path containment,
    oversized and symlinked JSON fail-closed behavior, symlinked action-audit
    rejection before tail sampling, and Ops `recentActions` using the shared
    bounded reader
- `.\.venv\Scripts\python.exe -m pytest tests\test_release_evidence_pack.py -q`
  - 5 passed, 3 skipped; covers release evidence pack bounded configured JSON
    reads, symlinked JSON/action-audit/markdown rejection, and symlinked Helper
    dev directory fail-closed behavior
- `.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_full_workspace_audit.py -q`
  - 4 passed, 1 skipped; covers full workspace audit skipping symlinked files
    before stat/hash evidence collection plus audit/validation gate reporting
- `npm test`
  - 103 passed across 24 web test files after the bounded markdown report
    read guard
- `npx eslint src/app/api/control-center/evidence/report/route.ts src/app/api/control-center/evidence/api-cost-report/route.ts src/app/api/control-center/evidence/route.test.ts src/lib/controlCenterMarkdownReportFile.ts src/lib/controlCenterMarkdownReport.ts`
  - passed
- `npx tsc --noEmit --pretty false`
  - passed
- `npm test`
  - 82 passed
- `npm test`
  - 86 passed
- `npm test -- controlCenterEvidence`
  - 3 passed
- `npm test -- controlCenterAuth`
  - 3 passed
- `npm run lint`
  - passed
- `npm run build`
  - passed
- `npm audit --json`
  - 0 vulnerabilities
- `npm test -- seed-login`
  - 4 passed
- `python -m pytest tests\test_otclient_helper_zerobot_shell.py tests\test_solteria_helper_release_gate.py tests\test_solteria_helper_goal_audit.py -q`
  - 60 passed
- PowerShell parser check for `scripts\windows\solteria_helper_test_env.ps1`
  - passed
- `python -m pytest tests\test_otclient_helper_zerobot_shell.py tests\test_powershell_launcher_security.py -q`
  - 40 passed; covers Helper sandbox path guard and launcher input contracts
- Negative `SmokeStatus` smoke with `SandboxClient == SourceClient`
  - passed; script rejects the live/source client alias before process attach
- `python -m pytest tests\test_otclient_helper_zerobot_shell.py tests\test_solteria_helper_release_gate.py tests\test_solteria_helper_goal_audit.py -q`
  - 61 passed
- `python -m pytest tests\test_mobile_console_display_path_security.py -q`
  - 4 passed; covers display-safe mobile-console file metadata paths and
    generic client-sync error detail redaction
- `python -m pytest tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_client_sync_security.py -q`
  - 14 passed
- `python -m pytest tests\test_mobile_console*.py -q`
  - 73 passed
- `python -m pytest tests\test_desktop_console_url_security.py -q`
  - 19 passed
- `python -m pytest tests\test_desktop_console_url_security.py tests\test_static_security_scan_contract.py -q`
  - 22 passed
- `python -m py_compile desktop_console\api_client.py desktop_console\app.py desktop_console\update_client.py tests\test_desktop_console_url_security.py tests\test_static_security_scan_contract.py`
  - passed
- `python -m pytest tests\ --ignore=tests\e2e -q`
  - 740 passed, 8 skipped
- `python -m pytest tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py tests\test_issue_sync.py tests\test_status_sync.py -q`
  - 27 passed
- `python -m pytest tests\ --ignore=tests\e2e -q`
  - 754 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py runner\runner.py runner\daily_insights.py runner\weekly_report.py runner\issue_sync.py runner\status_sync.py runner\close_on_gate.py runner\health_metrics.py scripts\ops\ci_executive_report.py -f json -o runtime\security\bandit-github-api-guard.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=7`
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py tests\test_issue_sync.py tests\test_status_sync.py tests\test_health_metrics_process_safety.py -q`
  - 125 passed, 1 skipped after adding shared GitHub repository ID validation
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py runner\runner.py runner\daily_insights.py runner\weekly_report.py runner\issue_sync.py runner\status_sync.py runner\close_on_gate.py runner\health_metrics.py scripts\ops\ci_executive_report.py tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py runner\runner.py runner\daily_insights.py runner\weekly_report.py runner\issue_sync.py runner\status_sync.py runner\close_on_gate.py runner\health_metrics.py scripts\ops\ci_executive_report.py tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py`
  - passed
- `python -m pytest tests\test_ctoa_full_workspace_audit.py tests\test_agent_http_security.py tests\test_security_hardening.py::test_runtime_smoke_keeps_credentials_on_loopback_api -q`
  - 34 passed
- `python -m pytest tests\ --ignore=tests\e2e -q`
  - 773 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py scripts\ops\runtime_smoke_e2e_8001.py scripts\ops\ctoa_full_workspace_audit.py -f json -o runtime\security\bandit-runtime-smoke-guard.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=1`
- `.\.venv\Scripts\python.exe -m bandit -r desktop_console -f json -o runtime\security\bandit-desktop-console.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=21`
- PowerShell parser check for `scripts\ops\ctoa-vps.ps1`
  - passed
- `python -m pytest tests\test_ctoa_vps_secret_handling.py -q`
  - 15 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_vps_secret_handling.py tests\test_vps_python_parity.py -q`
  - 21 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_vps_mobile_token_rotation_security.py -q`
  - 3 passed
- Git Bash parser check for `deploy/vps/rotate-mobile-token.sh`
  - passed
- `python -m pytest tests\test_api_chat_safety.py -q`
  - 31 passed
- `python -m pytest tests\test_api_chat_safety.py tests\test_api_auth_registration_security.py tests\test_security_hardening.py -q`
  - 48 passed
- `.\.venv\Scripts\python.exe -m bandit -r api -f json -o runtime\security\bandit-api.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `python -m py_compile api\main.py`
  - passed
- Local Git Bash smoke for generated `reseed-tier.sh` URL/hour/sql helpers
  - passed; accepted valid HTTP(S) URLs and age values, rejected unsafe schemes,
    whitespace, shell substitution, apostrophes, out-of-range ages, and invalid
    ages.
- AST smoke for `Assert-EnvSecretValue` extracted from
  `scripts\ops\ctoa-vps.ps1`
  - passed; accepted a safe token value and rejected empty, newline,
    whitespace, shell substitution, and backtick forms.
- AST smoke for `Assert-VpsUser` and `Assert-VpsHost` extracted from
  `scripts\ops\ctoa-vps.ps1`
  - passed; accepted valid lowercase user, IPv4, DNS, and bracketed IPv6, and
    rejected uppercase user, whitespace, invalid DNS labels, unbracketed IPv6,
    and shell metacharacters.
- AST smoke for VPS operator input validators extracted from
  `scripts\ops\ctoa-vps.ps1`
  - passed; accepted valid HTTP(S) URL lists, SQL literals, systemd service
    names, GS source refs, integer ranges, and UTC timer values, and rejected
    credentials, fragments, shell substitution, whitespace URLs, invalid service
    names, option-like refs, dotdot refs, invalid integers, and invalid times.
- `python -m pytest tests\test_vps_python_parity.py tests\test_suite.py::TestVPSConnectivity tests\test_ctoa_vps_secret_handling.py -q`
  - 29 passed
- `python scripts\ops\release_evidence_pack.py --json-out runtime\evidence\latest.json --md-out runtime\evidence\latest.md`
  - Helper evidence reports `status=promoted`, `live_promoted=true`, and empty
    `next_command`.
- `python -m pytest tests\test_lab003_operator_url_security.py -q`
  - 7 passed
- PowerShell parser check for `scripts\ops\lab003_shift_guard.ps1`,
  `scripts\ops\lab003_shift_smoke_webhook.ps1`,
  `scripts\ops\lab003_mobile_proxy_smoke.ps1`, and
  `scripts\ops\lab003_validate_bundle.ps1`
  - passed
- `.\ctoa.ps1 brain refresh`
  - `doc_sync_status=passed`
  - `secret_guardrail_status=passed`
- `.\ctoa.ps1 brain doctor`
  - `overall_status=warn`, `fail=0`, `docker.status=ok`,
    `running_broad=0`, `configured_broad=0`
- `.\ctoa.ps1 brain pack security`
  - 13 sections included, 2 generated indexes truncated
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py tests\test_llm_provider_url_security.py tests\test_api_chat_safety.py -q`
  - 86 passed
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 797 passed, 8 skipped
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py runner\llm_providers\local_model.py runner\llm_providers\azure_foundry.py api\main.py -f json -o runtime\security\bandit-llm-provider-url-guard.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m bandit -r runner mobile_console scripts desktop_console bot -f json -o runtime\security\bandit-precommit.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py -q`
  - 69 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_agent_http_security.py tests\test_health_metrics_process_safety.py tests\test_issue_sync.py tests\test_status_sync.py -q`
  - 76 passed
- `.\.venv\Scripts\python.exe -m ruff check runner\http_safety.py runner\agents\catalog_agent.py runner\agents\scout_agent.py runner\agents\ingest_agent.py tests\test_agent_http_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\http_safety.py runner\agents\catalog_agent.py runner\agents\scout_agent.py runner\agents\ingest_agent.py tests\test_agent_http_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\http_safety.py runner\agents\catalog_agent.py runner\agents\scout_agent.py runner\agents\ingest_agent.py -f json -o runtime\security\bandit-discovery-url-guard.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py -q`
  - 34 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 81 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 6 passed; covers structured preset execution, secret-redacted command
    output/audit, safe rejection of non-preset command text, and legacy
    `CTOA_MOBILE_FULL_ACCESS=true` not enabling arbitrary `/api/command`
    execution
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_static_xss_security.py tests\test_desktop_console_url_security.py -q`
  - 28 passed; covers preset-only command status, legacy mobile UI without a
    full-command box, and desktop admin console preset-only behavior
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 82 passed after the legacy full-access command closure
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 84 passed after preset-only UI/status alignment
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_guarded_agent_actions_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py -q`
  - 11 passed; covers owner-only confirmation/audit reasons for legacy Intel
    launch and one-click execution plus command redaction regressions
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_capability_gate.py tests\test_mobile_console_user_accounts_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_static_xss_security.py tests\test_mobile_console_live_dashboard_profile_api.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_db_exec_security.py tests\test_mobile_console_csrf_security.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py tests\test_mobile_console_guarded_agent_actions_security.py -q`
  - 89 passed after guarded Intel write confirmation
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py tests\test_api_auth_registration_security.py -q`
  - 20 passed after adding the lightweight API startup guard and stable
    subprocess timeouts for security import checks
- `.\.venv\Scripts\python.exe -m pytest tests\test_api_auth_registration_security.py tests\test_security_hardening.py -q`
  - 23 passed after making FastAPI proxy-header trust explicit. Default API
    rate limiting and HTTP audit IPs now ignore spoofed `X-Forwarded-For`
    headers unless `CTOA_TRUST_PROXY_HEADERS=true`; the trusted mode accepts
    only the first syntactically valid forwarded IP.
- `.\.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py tests\test_release_evidence_pack.py tests\test_api_auth_registration_security.py tests\test_api_chat_safety.py -q`
  - 59 passed after API release-evidence, HTTP audit redaction, chat safety,
    and proxy-header trust regression coverage.
- `npm test` from `web\`
  - 109 passed after web proxy route rate-limit identity stopped trusting
    `X-Forwarded-For`/`X-Real-IP` unless `CTOA_TRUST_PROXY_HEADERS=true`
- `npm run lint` from `web\`
  - passed after web rate-limit proxy-header trust hardening
- `npx tsc --noEmit` from `web\`
  - passed after web rate-limit proxy-header trust hardening
- `.\.venv\Scripts\python.exe -m pytest tests\test_generated_manifest_safety.py tests\test_mobile_console_generated_latest_api.py -q`
  - 12 passed, 2 skipped after generated-manifest read-side containment hardening
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_generated_latest_api.py tests\test_generator_agent_output_security.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_display_path_security.py -q`
  - 29 passed, 4 skipped after checking the Mobile Console/generator surface
- `.\.venv\Scripts\python.exe -m ruff check runner\generated_manifest_safety.py mobile_console\app.py scripts\ops\nightly_stability.py scripts\ops\night-report.py tests\test_generated_manifest_safety.py tests\test_mobile_console_generated_latest_api.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\generated_manifest_safety.py mobile_console\app.py scripts\ops\nightly_stability.py scripts\ops\night-report.py tests\test_generated_manifest_safety.py tests\test_mobile_console_generated_latest_api.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\generated_manifest_safety.py mobile_console\app.py scripts\ops\nightly_stability.py scripts\ops\night-report.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_night_report_security.py -q`
  - 2 passed after bounded night-report log sampling
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\night-report.py tests\test_night_report_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\night-report.py tests\test_night_report_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\night-report.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_health_metrics_process_safety.py -q`
  - 3 passed, 1 skipped after Health Metrics latest snapshot atomic-write
    hardening
- `.\.venv\Scripts\python.exe -m ruff check runner\health_metrics.py tests\test_health_metrics_process_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile runner\health_metrics.py tests\test_health_metrics_process_safety.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit runner\health_metrics.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_desktop_console_url_security.py -q`
  - 24 passed, 2 skipped after Desktop Console settings atomic-write and
    bounded-read hardening
- `.\.venv\Scripts\python.exe -m ruff check desktop_console\app.py tests\test_desktop_console_url_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile desktop_console\app.py tests\test_desktop_console_url_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit desktop_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_ideas_api.py tests\test_mobile_console_display_path_security.py -q`
  - 12 passed, 1 skipped after Mobile Console local state bounded-read and
    atomic-write hardening
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_display_path_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_ideas_api.py tests\test_mobile_console_display_path_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_update_gate.py tests\test_ctoa_product_bootstrap.py -q`
  - 8 passed, 2 skipped after product bootstrap atomic-write and update-gate
    bounded-read hardening
- `.\.venv\Scripts\python.exe -m ruff check scripts\ops\ctoa_update_gate.py tests\test_ctoa_update_gate.py scripts\ops\ctoa_product_bootstrap.py tests\test_ctoa_product_bootstrap.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\ctoa_update_gate.py tests\test_ctoa_update_gate.py scripts\ops\ctoa_product_bootstrap.py tests\test_ctoa_product_bootstrap.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit scripts\ops\ctoa_product_bootstrap.py scripts\ops\ctoa_update_gate.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_display_path_security.py tests\test_mobile_console_generated_latest_api.py -q`
  - 15 passed after auto-trainer report bounded-read hardening
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_display_path_security.py tests\test_mobile_console_generated_latest_api.py tests\test_mobile_console_api_contract_snapshot.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py -q`
  - 51 passed after checking the broader Mobile Console file/proxy surface
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_command_execution_security.py -q`
  - 6 passed, 1 skipped after Mobile Console log-tail fallback bounded-read
    hardening
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_command_execution_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_generated_latest_api.py -q`
  - 11 passed, 2 skipped after Mobile Console local metadata JSON and
    generated-manifest bounded-read hardening
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_generated_latest_api.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_generated_latest_api.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_client_sync_security.py -q`
  - 7 passed, 3 skipped after Mobile Console client-sync init-file and Lua-copy
    bounded-read/atomic-write hardening
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_client_sync_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_client_sync_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m pytest tests\ --ignore=tests\e2e -q`
  - 927 passed, 13 skipped
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_command_audit_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_static_xss_security.py tests\test_desktop_console_url_security.py desktop_console\app.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py desktop_console\app.py tests\test_mobile_console_command_execution_security.py tests\test_mobile_console_static_xss_security.py tests\test_desktop_console_url_security.py`
  - passed
- `node --check mobile_console\static\app.js`
  - passed
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console desktop_console -f json -o runtime\security\bandit-mobile-desktop-command-preset-only.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`,
    `SEVERITY.MEDIUM=0`, `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console desktop_console -f json -o runtime\security\bandit-mobile-desktop-guarded-actions.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`,
    `SEVERITY.MEDIUM=0`, `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m bandit -r api mobile_console desktop_console -f json -o runtime\security\bandit-api-mobile-desktop-guarded-actions.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`,
    `SEVERITY.MEDIUM=0`, `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m pytest tests\test_api_auth_registration_security.py tests\test_security_hardening.py tests\test_atomic_state_writes_security.py -q`
  - 28 passed, 1 skipped after API auth-store bounded-read hardening
- `.\.venv\Scripts\python.exe -m ruff check api\main.py tests\test_api_auth_registration_security.py tests\test_security_hardening.py tests\test_atomic_state_writes_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile api\main.py tests\test_api_auth_registration_security.py tests\test_security_hardening.py tests\test_atomic_state_writes_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit api\main.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_intel_proxy_api.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit -r mobile_console -f json -o runtime\security\bandit-mobile-console-runtime-api-base.json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py -q`
  - 43 passed after adding local runtime proxy path validation
- `.\.venv\Scripts\python.exe -m ruff check mobile_console\app.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m bandit mobile_console\app.py -f json`
  - `results=0`, `errors=0`, `SEVERITY.HIGH=0`, `SEVERITY.MEDIUM=0`,
    `SEVERITY.LOW=0`, `skipped_tests=3`
- `.\.venv\Scripts\python.exe -m pytest tests\test_powershell_launcher_security.py tests\test_vscode_workspace_security.py tests\test_docker_bind_defaults.py -q`
  - 16 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_desktop_console_url_security.py tests\test_powershell_launcher_security.py -q`
  - 29 passed
- `.\.venv\Scripts\python.exe -m py_compile desktop_console\app.py tests\test_powershell_launcher_security.py`
  - passed
- PowerShell parser check for `ctoa.ps1`
  - passed
- `npm test -- control-center/actions controlCenterActions`
  - 25 passed
- `npm test -- control-center/actions controlCenterActions control-center/route control-center/legacy controlCenterEvidence controlCenterOps`
  - 34 passed
- `python -m pytest tests\test_engine_brain_doctor.py tests\test_docker_bind_defaults.py -q`
  - 8 passed
- `Invoke-WebRequest http://127.0.0.1:8001/health`
  - 200
- `git diff --check`
  - No whitespace errors; line-ending warnings only.
- `.\.venv\Scripts\python.exe -m pytest tests\test_atomic_state_writes_security.py tests\test_security_hardening.py tests\test_runner_execution_summary.py tests\test_runner_backlog_selection.py -q`
  - 24 passed
- `.\.venv\Scripts\python.exe -m py_compile api\main.py runner\runner.py tests\test_atomic_state_writes_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_profile_audit.py tests\test_solteria_helper_goal_audit.py tests\test_solteria_helper_release_gate.py tests\test_sprint_state_sync.py -q`
  - 37 passed
- `.\.venv\Scripts\python.exe -m py_compile scripts\ops\otclient_helper_profile_audit.py scripts\ops\solteria_helper_goal_audit.py scripts\ops\solteria_helper_release_gate.py scripts\ops\sprint_state_sync.py`
  - passed
- PowerShell parser check for `scripts\windows\solteria_helper_test_env.ps1`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\unit\bot\test_runtime_profile_security.py tests\unit\bot\test_spell_rotation.py tests\test_powershell_launcher_security.py -q`
  - 18 passed
- `.\.venv\Scripts\python.exe -m py_compile bot\config\runtime_profile.py tests\unit\bot\test_runtime_profile_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_runner_agent_db_security.py tests\test_mobile_console_db_exec_security.py tests\test_process_safety.py -q`
  - 12 passed
- `.\.venv\Scripts\python.exe -m py_compile runner\agents\db.py tests\test_runner_agent_db_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_queue_worker_security.py tests\test_process_safety.py tests\test_runner_imports.py -q`
  - 12 passed
- `.\.venv\Scripts\python.exe -m py_compile runner\queue_worker.py tests\test_queue_worker_security.py`
  - passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_mobile_console_intel_proxy_api.py tests\test_mobile_console_url_validation_security.py tests\test_mobile_console_command_execution_security.py -q`
  - 40 passed
- `.\.venv\Scripts\python.exe -m py_compile mobile_console\app.py tests\test_mobile_console_intel_proxy_api.py`
  - passed

Note: run full pytest separately from web builds on Windows. Engine Brain tests
write `AI/generated/*`, and concurrent build/test work can collide on generated
artifact writes.

## Remaining Follow-Up

- Keep Docker runtime exposure at `running_broad=0` and `configured_broad=0`
  after future compose, profile, or local service changes.
- Keep the pre-commit Bandit scope at zero findings. Future broad exception
  handling should either catch concrete failure types or write structured
  diagnostics when best-effort cleanup/probing cannot fail the workflow.
- Continue reviewing remaining mobile console high-risk surfaces and Control
  Center action catalog before enabling broader guarded actions.
- Keep release evidence and Control Center semantics aligned whenever Helper
  release-gate fields change.
