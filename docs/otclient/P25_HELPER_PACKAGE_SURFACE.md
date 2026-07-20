# P25 Helper Package Surface

## Decision

The official CTOAi Helper distribution contains only the neutral chooser,
Helper loader, boot-manifest modules, vocation data, and the canonical native
composition shell. Three older standalone runtimes remain local source
references and are not distributable Helper files:

- `ctoa_native_combat.lua`
- `ctoa_native_heal.lua`
- `ctoa_native_loot.lua`

They duplicate domains now owned by the Helper targeting, combat/recovery/loot
runtime, observer, policy, and guarded bridge modules. The Helper loader never
loads these standalone files.

## Boundaries

- `Get-DevPackageFiles`, stage creation, ZIP creation, sandbox sync, signed P14
  source manifests, and live promotion exclude the three files.
- Sandbox sync and live legacy cleanup remove old enabled and `.disabled`
  copies so a previous package cannot silently preserve them.
- Source files are retained for local comparison only and carry an explicit
  `LOCAL SOURCE ONLY` marker.
- No Safe source, release manifest, runtime state, or live client is changed.
- Runtime remains safe-booted and default-off.

## Canonical inventory

P25.2 removes four repeated active-module arrays from the Windows operator
wrapper. Stage creation, sandbox sync, live enablement and UI-only enablement
now derive their filenames from `Get-DevPackageFiles` through
`Get-DevModuleFileNames`. The legacy cleanup list remains separate because it
describes files that must be removed, never files that may be distributed.

## Next slices

- P26: split UI composition primitives from rule-editor presentation without
  changing the proven OTCv8 widget surface.
- P27: add portable rule preset import/export with strict schema validation and
  no runtime arming.
- P28: execute the independent sandbox replay/canary/rollback acceptance once
  the external P14 Windows runner and protected environment are current.
