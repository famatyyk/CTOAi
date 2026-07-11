# Known Bugs and Risks

## Confirmed From Current Source Shape

- Packet/protocol documentation is incomplete because TFS/client protocol source
  is not present.
- OTClient native API availability varies by fork; any unguarded `g_*` or class
  method call can fail on a custom client.
- `ctoa_native_helper.lua` is very large, so unrelated UI/runtime changes can
  accidentally affect profile save, tabs, hotkeys, or safe boot behavior.
- Generic Lua modules in `scripts/lua/` and OTClient native modules use different
  runtime APIs; mixing them without an adapter can break at load time.
- Validator fallback without `luac` is weaker than true Lua syntax validation.

## Suspected Areas To Check Before Editing

- Hotkey rebinding and old binding cleanup.
- Profile save order and partial write behavior.
- Safe boot defaults after profile merge; repo-side profile audit now blocks
  unsafe generated/migrated defaults before `ValidateDev`.
- Cavebot movement enable flags and test-walk behavior.
- Combat target clearing in PZ/offline/invalid target states.
- UI smoke tab/subtab persistence.
- `ctoa_local.log` path behavior in custom OTClient user directories.

## Not Yet Verified

- Full OTClient manual smoke on the current local client.
- TFS packet flow.
- Server-side Lua callback compatibility.
- Whether the ZIP or expanded folder should be treated as canonical source.
