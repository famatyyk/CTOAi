# Tibia Control Center And Helper P0 Plan

## Objective

Build the next Helper and Control Center modules around a shared operational
contract before adding assisted actions. Control Center must show source
freshness, parser failures, unknown client builds, protocol gaps, and safe
fallback state from real local evidence only.

## Implemented Foundation

- Added the shared web contract in `web/src/lib/tibiaOperationalState.ts`.
- Added local-first API surfaces:
  - `GET /api/sources`
  - `GET /api/updates/latest`
  - `GET /api/diffs/:surface`
  - `GET /api/clients`
  - `GET /api/clients/:id/capabilities`
  - `GET /api/events`
  - `POST /api/config/validate-dry-run`
- Wired `/api/control-center` to include the same operational source and client
  state even when the backend probe is unavailable.
- The initial contract reports explicit P0 states instead of fallback metrics:
  `source_blocked`, `stale_snapshot`, `unknown_build`, and
  `pending_protocol_source`.

## P0-A Source Inventory And Snapshot Archive

Implemented:

- `scripts/ops/tibia_source_collector.py` is a bounded, HTTPS-only,
  Tibia.com-allowlisted collector for `news`, `library`, `character_trade`,
  and `community_test`.
- Each attempt has a unique raw HTML file and sibling JSON metadata under
  `runtime/tibia_source_archive/<source_kind>/`; the collector never replaces
  a historical capture.
- `source-index.json` is an atomically replaced current view, while
  `update-ledger.jsonl` is append-only. The raw file and individual metadata
  JSON are the durable evidence.
- Metadata contains `RawSnapshot` fields (`source_kind`, `fetched_at`, `url`,
  `content_hash`, `blocked_reason`) plus parser status, normalized records,
  and detected changes.
- `news` is the first fixture-backed parser. It accepts only explicit News
  archive links and marks unparseable HTML as `parser_broken`; Library,
  Character Trade, and Community/Test remain `pending_fixture` until their
  parsers and fixtures exist.
- The Control Center API reads a valid local archive through
  `CTOA_TIBIA_SOURCE_ARCHIVE_DIR` (default
  `runtime/tibia_source_archive`). If absent or malformed, it falls back to
  explicit blocked/stale contract states rather than claiming freshness.

Operator examples:

```powershell
# Fixture-first: no external request.
.\.venv\Scripts\python.exe scripts\ops\tibia_source_collector.py news --input-html path\to\news.html

# Bounded live attempt. A Cloudflare/HTTP block is still archived as evidence.
.\.venv\Scripts\python.exe scripts\ops\tibia_source_collector.py news
```

Acceptance now enforced by tests:

- A blocked fetch produces `source_blocked` and preserves both raw body and
  metadata.
- A failed fetch remains `stale_snapshot`; it never becomes `fresh` merely
  because the API rendered the inventory.
- Parser failures become `parser_broken` without deleting the raw snapshot.
- A second valid News snapshot emits `added`, `changed`, and `removed` ledger
  events against the prior successful parse.

## P0-B Shared Domain Model

Next implementation slice:

- Reuse the TypeScript contract names in helper docs and future Lua capability
  reporter output.
- Keep normalized records behind adapter boundaries:
  `SourceCollector.fetch`, `SourceParser.parse`, and `ClientAdapter.detect`.
- Add contract tests that compare API response keys against the documented
  `RawSnapshot`, `UpdateEvent`, `ClientCapabilities`, and `TelemetryEvent`
  shapes.

Acceptance:

- API, Control Center, and Helper evidence use the same state names.
- New source kinds cannot be added without tests for status and freshness.

## P0-C Helper Heartbeat And Capability Reporter

Next implementation slice:

- Add a passive Helper capability module that reports client family, build id,
  supported modules, protocol status, profile schema, and heartbeat timestamp.
- Unknown builds must report `unknown_build`, `pending_protocol_source`, and
  `safe_fallback = true`.
- Keep runtime actions gated; heartbeat and capability reporting must not arm
  combat, cavebot movement, healing, timers, runes, or scripting.

Acceptance:

- Sandbox known-build smoke and unknown-build fixture both produce capability
  reports.
- Unknown build keeps the Helper UI available but leaves runtime bridges
  blocked.

## P0-D Control Center Operational State

Next implementation slice:

- Render source rows, client capability rows, latest update events, and parser
  errors from the P0 API contract.
- Add visual states for `source_blocked`, `parser_broken`, `unknown_build`,
  `pending_protocol_source`, and `stale_snapshot`.
- Keep all counts tied to API payloads or local files; no generated progress
  values or pretend freshness.

Acceptance:

- `/api/control-center` and the Control Center UI expose identical P0 state.
- Backend outage still shows local source/client state and a sanitized backend
  probe error.
- Control Center never converts blocked/stale/pending state to live/ready.

## P1 Queue

- Weapon proficiency surface and local banner.
- Boss difficulty surface.
- Monk/virtues surface.
- Compatibility profiling per OTClient fork.
- Protocol probe pack and replay fixtures, marked `pending_protocol_source`
  until real captures exist.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_otclient_helper_zerobot_shell.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action ModuleStaticGates
cd web
npm test -- tibiaOperationalState route.test.ts
npm run lint -- --quiet
```
