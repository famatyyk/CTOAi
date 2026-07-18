# CTOAi repository split plan

Status: approved working plan, 2026-07-18.

## Why this exists

CTOAi grew as one workspace containing product code, operational automation,
Engine Brain outputs, client integration, raw evidence and historical work.
That shape is useful for exploration but unsafe as a long-term publication and
release boundary. The goal is to separate ownership without losing history,
contracts or reproducibility.

This is a boundary plan first. It does not move files blindly and it does not
make P14 or the Helper release-ready by declaration.

## Target repositories

### `CTOAi-Control-Center`

Owns the operator cockpit and its read-only projection layer:

- `web/src/app/control-center/`
- `web/src/app/api/control-center/`
- Control Center components and client libraries
- public-safe UI contracts and focused tests
- Control Center documentation and packaging metadata

It does not own OTClient Lua, raw evidence, VPS credentials, deploy scripts or
private Engine Brain output.

### `CTOAi-Helper`

Owns the OTClient-side product:

- `scripts/lua/otclient/` Helper modules and loader
- `mods/ctoa_safe/` Helper module packaging
- Helper-specific tests, fixtures and user documentation
- versioned profile and UI contracts required by the client

It does not own Control Center UI, private runtime evidence, VPS automation or
unredacted internal roadmaps.

### `CTOAi-Adapter`

Owns compatibility and observation boundaries:

- `ctoa_helper_otclient_observation_adapter.lua`
- fork capability detection and compatibility probes
- observation/conditions schemas and adapter fixtures
- adapter tests and replay contracts

The adapter must remain data-first: it observes and normalizes client state. It
does not contain Control Center presentation or Helper product policy.

### Private Engine Brain and operations

Remain outside public product repositories:

- `AI/` generated packs and internal decision state
- `runtime/` evidence, client captures, logs and audit trails
- `scripts/ops/`, `deploy/`, VPS mappings and operational credentials
- local databases, raw datasets and private training/evaluation material

Private storage may later live on the dedicated server. It must not be copied
into a public export as a convenience.

## Migration sequence

1. **Freeze and snapshot.** Preserve current dirty worktrees, stashes and
   historical branches before changing ownership.
2. **Declare boundaries.** Keep the monorepo paths stable and add explicit
   ownership/allowlist manifests. No mass move or `git add -A`.
3. **Reduce coupling.** Move shared contracts to versioned schemas; replace
   imports that reach across product boundaries with adapter interfaces.
4. **Build sanitized exports.** Generate each repository from an allowlist and
   run secret, runtime, database and path-leak checks. Start history-free so
   old private commits cannot leak through the new public history.
5. **Validate independently.** Each export gets its own tests, package smoke,
   docs and release evidence. Control Center, Helper and Adapter cannot be
   declared ready based only on monorepo tests.
6. **Publish draft PRs.** Review one repository map/README PR first, then one
   extraction PR per product. Keep the current monorepo as an archival source
   until parity is proven.
7. **Archive and operate.** Mark the monorepo as historical, retain bundles
   and signed evidence, and move large private runtime data to the dedicated
   server with retention rules.

## Branch and worktree policy

- `main` is the public baseline and receives only scoped PRs.
- Product work uses `codex/cc-*`, `codex/helper-*` and `codex/adapter-*`.
- Evidence/replay work uses a separate branch and never mixes with README or
  packaging changes.
- Generated `AI/generated/*` changes are reviewed as generated output, not
  silently bundled with product source.
- A worktree may be removed only after its status is clean and its branch or
  detached commit has an archive bundle or an accepted PR.
- Remote branches are not deleted as part of local cleanup without an explicit
  owner decision.

## Publication gate

Before a path enters any public repository, verify:

- owner and destination repository are declared;
- no `.env`, token, auth store, database, log, raw evidence or private path is
  present;
- tests and package smoke are scoped to that product;
- contracts are versioned and imports do not cross the boundary accidentally;
- README and release status do not claim readiness that evidence has not proven.

## Dedicated server plan

The server is a storage and execution boundary, not a replacement for source
control. Move raw runtime evidence, build caches and large replay assets there;
keep the laptop checkout small and reproducible. Source repositories remain
sanitized, and server synchronization uses explicit manifests with retention
and backup checks.
