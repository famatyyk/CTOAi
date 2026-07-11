# Solteria Helper v2.2.0 — vocation profiles and combat decisions

## Scope

Version 2.2.0 adds profession-aware profile routing and fixes three runtime
decision defects reported after v2.1.1a: profile changes not reaching a real
filesystem path, unreachable targets being held, and EK single-target spells
being selected for large monster packs.

## Profiles

- Supported profile families: Elite Knight, Master Sorcerer, Elder Druid and
  Royal Paladin, including their base-vocation IDs.
- Vocation is detected after `onGameStart` through guarded player/vocation API
  probes. Unknown APIs retain the safe EK fallback and never arm runtime.
- Each profession has Healing, Targeting, Magic Shooter and CaveBot surfaces.
- Profile writes map resource paths to the installed `mods/ctoa_otclient`
  filesystem path. Module visibility and vocation metadata are exported.

## EK combat policy

- A target requiring melee reachability is rejected when `findPath` returns no
  route; the current invalid target is cleared and normal retarget delay applies.
- At three or more adjacent monsters, single-target `exori ico`,
  `exori gran ico` and `exori hur` are ineligible. The helper waits for an AoE
  spell instead of wasting the global action lock.
- With one or two adjacent monsters, auto stance selects `utito tempo` and Full
  Attack. With four or more, it selects `utamo tempo` and Full Defense. Exactly
  three monsters leaves stance unchanged.

## Safety and promotion

Safe boot remains default-off. Vocation detection and profile loading never arm
runtime. Live promotion requires a fresh dev validation, static gates,
SmokePreflight, sandbox attach evidence, ReadyCheck and explicit approved
promotion through the official wrapper.
