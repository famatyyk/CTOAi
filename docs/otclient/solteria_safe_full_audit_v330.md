# Solteria Safe v3.3.0 full audit

## Decision

Safe v3.2.0 was a selective safety repair. v3.3.0 is the first candidate from
the broader control-to-runtime audit requested after the live defects were
reported. The live Solteria client remains unchanged until a separate explicit
promotion approval.

The implementation is clean-room and compatibility-driven. The encrypted
KingsVale module was treated only as an opaque behavioural reference. No
decryption, embedded server code, character data, or copied proprietary module
is present in the seven-file package.

## Proven client profile

- Target: Solteria derived OTCv8 client.
- Proven UI path: programmatic `g_ui.createWidget`, imported OTUI styles,
  `UIItem`, `CheckBox`, `HeadlessWindow`, modules and mods.
- Native skin inputs: Solteria's own `/images/ui/window_headless`,
  `/images/ui/item`, native buttons and checkbox state images.
- Behavioural reference: the supplied KingsVale video and visible Helper
  layout. The encrypted files were not used as executable or source input.

## Control-to-runtime matrix

| Surface | Persistent state | Runtime consumer | Dispatch / outcome | v3.3 evidence |
|---|---|---|---|---|
| Healing spell checkbox and spell button | `healing.spell_slots[]` | `runHealing` | guarded `g_game.talk` | checkbox now gates the same slot list consumed at runtime |
| Potion item slots | `healing.potion_rules[]` | `runHealing` | item on local player | accepts backpack and actionbar drag shapes |
| Friend healing | `friend_rules[]` | `runHealing` | named heal spell | vocation-gated for Monk, Sorcerer and Druid |
| Mana training | `tools.mana_training_*` | `runTools` | item on local player | item selector and threshold are connected |
| Exercise training | `tools.exercise_*` | `runTools` | item on nearest visible exercise-dummy creature or map item | native tile/item scan; no player/self fallback |
| Haste and buff | `tools.haste_*`, `tools.buff[]` | `runTools` | PZ-guarded spell dispatch | buff spell is now selectable in UI |
| Food, gold, ammo | tool item ids and enables | `runTools` | plain inventory item use | no incorrect self-target dispatch |
| Amulet and ring slots | equipment rules | `runTools` | plain inventory item use at HP/MP threshold | item and enable controls share runtime state |
| Shooter spells | selected shooter profile | `runCombat` | PZ-guarded spell dispatch | creature count, mana, priority and combat context enforced |
| Shooter runes | selected shooter profile | `runCombat` | rune on current monster target | no longer used on the player |
| Auto target | target rules and mode | `runCombat` | attack/follow/cancel | NPC/player exclusion, chase, timeout and idempotence enforced |
| Legacy rotation | compatibility-only profile fields | none in the three-page Safe runtime | no dispatch | hidden legacy rotation can no longer cast spells |
| Legacy conditions/support/timers | compatibility-only profile fields | none in the three-page Safe runtime | no dispatch | hidden modules are disabled at boot and skipped by the think loop |
| Global enable | runtime-only arm state | think loop | all modules gated | imported profiles and boot never restore armed state |

## Item assignment contract

Item slots are `selectable`, `editable`, virtual and focusable. Drop parsing
supports the observed OTC variants: numeric `currentDragThing`, a dragged
thing exposing `getId`, direct `getItemId`, nested `getItem():getId`, nested
`item:getItemId`, and actionbar `cache.itemId`. Invalid or empty drops fail
closed and do not alter configuration.

## Compatibility-only fields

The KingsVale JSON adapter retains fields such as `autoChangeProfile` and
locked-target identifiers to preserve import/export shape. They are not
presented as implemented automation when Safe has no proven local semantic for
them. Imported `helperEnabled` is always discarded and Safe stays disarmed.

## Verification boundary

Executable Lua tests cover item drops, checkbox state, healing gating, rune
target dispatch, ordinary item dispatch, exercise dummy selection, NPC/PZ
guards, targeting idempotence, presets and safe boot. Static release checks bind
those behaviours to the staged seven-file manifest.

## Sandbox acceptance

The final seven-file v3.3.0 package was copied by hash into the isolated
`SolteriaCodexTest` client and tested in the real client on both available
vocations. The live client was not modified.

- Elite Knight: Healing, Tools and KVShooter render within the native client
  layout. Actionbar-to-item-slot drag works and survives a client restart.
- Sorcerer: the expected two spell slots, two potion slots and Friend Healing
  section render correctly; Tools and KVShooter also fit without clipping.
- Visible checkboxes change persistent state. Safe still boots and loads
  disarmed, and the test profiles were returned to an all-visible-actions-off
  state after the run.
- Arming Safe with every visible action disabled produced no spell, item use or
  target action. This proved that compatibility-only legacy modules no longer
  dispatch invisibly.
- The server reports the nearby NPC `Adam Malysz` as a monster-like creature
  (`isNpc=false`, type `1`, icon `7`, id in the `0x80000000` range). The NPC
  classifier now also uses the server id/icon signals. A fresh seven-second
  Auto Target run neither attacked the NPC nor emitted the prior `hi` spam.

The first runtime probe incorrectly reported `PZ=false` because it trusted only
the narrow player/game boolean family. A client screenshot showed the native
`You are within a protection zone` message and invalidated that result. The
resolver now combines game/player methods, player state bit `16384`, tile
methods, `Tile:getFlags`, `Tile:hasFlag` and the protection-zone bit `1`.
The repeated sandbox snapshot resolved `PZ=true` from
`player:getStates:16384`. With Auto Haste enabled, `PZ Cast` disabled and Safe
armed for over five seconds, mana remained at `72/750` and no spell was sent.
The in-world PZ guard is therefore accepted. Promotion to live still requires
a separate explicit approval.

The follow-up evidence review found that the first Exercise Training runtime
only inspected spectators. Solteria proves `g_map.getTiles`, `Tile:getItems` and
item names/tooltips in its native API, so v3.3.0 now also scans nearby map items
and passes the actual item `Thing` to `useInventoryItemWith`. The fixture uses a
nearby item dummy and a farther creature dummy to prove the map item is chosen.
The family snapshot also found three nearby map-item dummies with id `28559`.
The Exercise catalog now covers public/training and house dummy ids
`5787-5788` and `28558-28565`, plus normal, durable and lasting exercise weapon
families (`28552-28557`, `35279-35290`, `44066`, `50294`). Classification uses
ID first and name/description/tooltip as a compatibility fallback. An in-world
charge consumption test is no longer dependent on a successful drag from Store
Inbox: when Exercise Training is enabled with an empty slot, Safe scans open
containers and selects a vocation-compatible family (Knight sword/axe/club,
Paladin bow, Sorcerer/Druid rod/wand, Monk wraps). The user approved spending
one charge for the final runtime check.
