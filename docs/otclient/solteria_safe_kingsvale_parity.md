# CTOA Safe v3.1 KingsVale parity contract

## Vocation-specific surface

Safe derives the visible layout from a fixed, local vocation contract:

| Vocation | Healing spells | Potions | Friend Healing | Auto Exeta |
| --- | ---: | ---: | --- | --- |
| Knight (`ek`) | 3 | 3 | hidden and runtime-denied | visible |
| Monk (`monk`) | 3 | 3 | visible | visible |
| Paladin (`rp`) | 3 | 3 | hidden and runtime-denied | visible |
| Sorcerer (`ms`) | 2 | 2 | visible | hidden and runtime-denied |
| Druid (`ed`) | 3 | 3 | visible | hidden and runtime-denied |

The Monk numeric vocation ID is intentionally not guessed. Safe recognizes a
runtime/string value containing `monk`; unknown server-specific spell IDs remain
importable through `helper.json`, resolve through the client's `SpellInfo` table
when available, and can also be assigned with explicit spell words.

This is a clean-room compatibility implementation. The observable sources are
the user-provided demonstration recording, the plaintext `helper.json` runtime
contract and its local history, and the public OTClient API exposed by the
target fork. The encrypted reference Lua, OTMod and OTUI payloads are not
decrypted, copied, embedded or distributed.

## Product boundary

- Full Safe source, tests, validation evidence and documentation remain local.
- The friend package contains seven runtime files under `mods/ctoa_safe` only.
- Character data, recordings, reference binaries and Helper project files are excluded.
- Importing `helper.json` always leaves `CTOA_SAFE.config.enabled=false` and the runtime disarmed.

## UI contract

| Reference surface | Safe v3 surface | Runtime behavior |
| --- | --- | --- |
| Healing | `csTabhealing` | Three spell slots, three potion slots, two Sio and two Gran Sio rows |
| Tools | `csTabtools` | Training, haste/PZ cast, exercise, gold, food, two amulets, two rings, buff, utamo, ammo and reconnect |
| KVShooter | `csTabshooter` | Named presets, six spell rows, two rune rows, mana/creature/priority controls, target/shooter/hold switches and hotkeys |
| Spell assignment modal | `csSpellSelector` | Vocation-aware healing/aggressive catalog, search, learnt-only control, parameter field and OK/Apply/Cancel |
| Status/footer | `csStatus`, `csSetKey`, `csFooterClose` | Explicit arm/disarm, selected hotkey and close control |

## `helper.json` field coverage

All 30 top-level keys observed across 27 local snapshots are accepted and
sanitized. Persistent settings are mapped into the Safe profile. The two
session fields are intentionally normalized:

- `helperEnabled` exports as `false` and never arms Safe.
- `currentLockedTargetId` exports as `0` and is never restored across sessions.

`autoReconnect` is guarded and only calls the target fork's existing
`modules.client_entergame.doLogin` function while Safe is explicitly armed.
Spell IDs are preserved. Safe resolves their words from a runtime spell catalog
when the fork exposes one; otherwise the operator assigns the spell through the
included selector. This is the remaining server-data dependency because the
reference spell catalog is encrypted.

## Verification

```powershell
lua -e "assert(loadfile('mods/ctoa_safe/ctoa_safe_helper.lua'))"
.\.venv\Scripts\python.exe -m pytest tests\test_ctoa_exclusive_project_loader.py tests\test_solteria_safe_release.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_safe_release.ps1 -Action Package
```

The release gate also rejects embedded reference paths, requires default-off
safe boot, verifies the seven-file manifest and checks that the ZIP contains no
other files.

## Sandbox visual acceptance

On 2026-07-15 the seven-file candidate was synchronized to the isolated
`SolteriaCodexTest` client with 7/7 SHA-256 parity and opened on a Sorcerer:

- the title resolved the vocation as `[MS]` through `LocalPlayer:getVocation()`;
- Healing, Tools and KVShooter rendered inside the compact window;
- the aggressive spell selector rendered the Sorcerer catalog and all modal controls;
- the earlier v3.0 acceptance remained `Ready v3.0.0` and the Enable action was not used;
- no spell, item, movement, target or attack action was executed;
- the sandbox process was stopped after inspection and the live client stayed untouched.
