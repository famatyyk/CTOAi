# Technical Debt

## Documentation Debt

- TFS fork is not indexed.
- Packet/opcode index is empty pending source.
- Lua API inventory is manually summarized, not generated.
- `schemas/otclient-helper-config.schema.json` exists, but there is still no
  generated map from each `HELPER_CONFIG` key to its UI control.

## Code Organization Debt

- `ctoa_native_helper.lua` is a monolith containing config, theme, layout, UI
  builders, runtime toggles, profile persistence, HUD, smoke support, and manager
  registration.
- Generated generic Lua modules and OTClient-native modules are not clearly
  separated by compatibility target in docs.
- OTClient packaging source of truth is now the expanded
  `scripts/lua/otclient/` folder; generated ZIP artifacts must stay out of the
  source tree.

## Validation Debt

- Lua syntax validation depends on whether `luac` exists.
- OTClient UI smoke is manual and log-based.
- No automated screenshot/pixel smoke for the OTClient helper panel.
- Packet/protocol behavior has no tests without TFS/client protocol source.

## Runtime Debt

- Native API guard patterns are repeated and should become helper utilities if
  the client supports clean module splitting.
- Profile save/load should eventually parse and validate against the schema
  directly inside the Helper; current protection is the repo-side
  `otclient_helper_profile_audit.py` gate.
- Combat/probe logs need clear rate-limit contracts to avoid noisy logs.

## Product Debt

- Control Center now surfaces latest Helper package status; generated Lua
  validation score remains future work.
- Release evidence now includes OTClient package checks; keep broadening it when
  Helper package artifacts grow.
- Operator docs should include one Windows-native install/smoke path for the
  helper package.
