# Solteria Helper v2 Execution Plan

## Outcome

Release `v2.0.0` as a complete, fail-closed Helper package whose validated
manifest, ZIP, sandbox installation, and live installation contain the same
required module graph. Preserve UI-only safe boot and keep all runtime actions
disarmed by default.

## Incident driving v2

The v1.1b stage contained `ctoa_helper_client_reporter.lua`, but
`Get-DevPackageFiles` omitted it. Sandbox synchronization copied the module by
a separate list, while live promotion copied only `Get-DevPackageFiles`.
Consequently the release gate could pass and the live loader could still fail
closed on the missing required reporter.

The sandbox also exposed a stale-hardlink failure mode after the source client
updated its protocol packages. The wrapper now compares source and sandbox
content before reusing those links.

## v2 invariants

1. The validated boot manifest remains authoritative for required runtime
   modules and fails closed when any required module is unavailable.
2. Every required packaged module must be represented by the development file
   contract and copied into `mods/ctoa_otclient`.
3. Promotion must verify SHA-256 equality for every staged and live package
   file before reporting success.
4. The release and goal audits must derive the versioned ZIP name from the
   current manifest, never from a hard-coded historical version.
5. Profiles remain on `ctoa-helper-profile-v1`; Helper application version and
   profile schema version evolve independently.
6. Safe boot remains `helper-ui-only`, runtime stays disarmed, and live writes
   continue to require explicit approval and a fresh backup.

## Execution order

### V2.1 Package completeness

- Add the client reporter to the promotion package contract.
- Add regression coverage tying the required reporter to the package list.
- Verify the staged manifest contains it at the module path.

### V2.2 Promotion verification

- After copying, verify every file in `Get-DevPackageFiles` exists live.
- Compare stage and live SHA-256 values.
- Record the verified file count and verification mode in
  `live_promotion.json`.

### V2.3 Version migration

- Set Helper, loader, and `.otmod` versions to `v2.0.0` / `2.0.0`.
- Produce `ctoa_otclient_v2.0.0.zip` and a manifest carrying `v2.0.0`.
- Keep the profile schema at v1 because no persisted profile contract is
  broken by this release.

### V2.4 Validation and rollout

- Run targeted regression tests and the complete Helper static suite.
- Run `ValidateDev`, `ModuleStaticGates`, and `SmokePreflight`.
- Rebuild the sandbox, enter a test character, then pass `ReadyCheck`,
  `SmokeAttachModules`, and `SmokeAttachAll` for the v2 manifest.
- Promote only through `PromoteLiveCtoa -ApproveLiveDeploy`, then verify the
  live reporter, promotion hashes, release gate, and goal audit.

## Acceptance criteria

- The live loader reaches `Initialization complete` with no missing required
  support module.
- The manifest and live client both contain
  `mods/ctoa_otclient/ctoa_helper_client_reporter.lua` with identical SHA-256.
- Static and in-world gates are fresh for the v2 manifest and pass.
- `live_promotion.json` reports `stage_live_sha256_match` and the full verified
  package-file count.
- No unrelated worktree files are staged or committed; the official wrapper
  remains part of the Helper/Solteria change bundle.
