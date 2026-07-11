# vBot Import Review

## Decision

- Status: `source_required`.
- No vBot source tree or reviewed local archive is present in this checkout.
- Do not claim vBot-derived implementation until source provenance, license
  notes, secret scan, and module mapping are recorded here.
- External bot projects may be used as capability checklists and naming
  references only. Do not directly copy code into CTOAi helper modules without
  explicit source and license review.

## Intake Requirements

A valid vBot or vBot-like source handoff must include:

1. Source path or archive name.
2. Origin URL or owner-provided provenance note.
3. License text or explicit permission note.
4. SHA256 for the archive or source snapshot.
5. Secret scan result for tokens, accounts, server IPs, and local runtime state.
6. File inventory grouped by capability: healing, targeting, cavebot, looting,
   HUD, hotkeys, conditions, equipment, scripting, and diagnostics.
7. Risk notes for every runtime action path: movement, attack, spell cast, rune,
   item use, chat/talk, filesystem write, and profile migration.

Use the checked intake command before reviewing code manually:

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_external_bot_intake.py <source-path-or-zip> --origin "<origin-or-owner-note>" --license-note "<license-or-permission-note>"
```

The generated report is an intake gate, not an import approval. Any warnings
for movement, attack, spell cast, item use, keyboard binding, filesystem write,
or dynamic code still need mapping into passive CTOAi helper modules first.
The report must include `import_gate`, and `import_gate.runtime_import_allowed`
must stay `false` until the matching CTOAi module gates and sandbox evidence
prove the behavior.

## Import Gate Contract

The intake gate converts external bot findings into a CTOAi decision:

- `source_required`: no source was provided, so no import work can claim vBot
  behavior.
- `review_required`: source exists, but provenance, license, secret, or review
  blockers remain.
- `capability_mapping_only`: source can be reviewed as a checklist, but runtime
  import is still blocked.

`import_gate.direct_copy_allowed` is always `false`. Detected runtime actions
must appear in `runtime_gate_mapping` and point at existing CTOAi gates such as
`combat_runtime`, `cavebot_runtime`, `loot_runtime`, `hotkeys`,
`profile_schema`, or `scripting`.

## Mapping Policy

Map external bot behavior into existing CTOAi helper domains instead of adding
new runtime shortcuts:

| External capability | CTOAi target | Import rule |
|---|---|---|
| HUD text/overlay helpers | `ctoa_helper_hud.lua` | Keep passive text/position formatting only. |
| Hotkey parsing/manager | `ctoa_helper_hotkeys.lua` | Keep parser/display helpers only; binding stays in helper shell. |
| Confirmation modals | `ctoa_helper_modal.lua` | Keep request/expiry/status lifecycle only; execution stays guarded. |
| Cavebot route editor | `ctoa_helper_route.lua` | Keep waypoint labels and mutations only; `autoWalk` stays gated in helper shell. |
| Target selection/scoring | `ctoa_helper_targeting.lua` | Keep score and ignored-name rules only; `g_game.attack` stays guarded in helper shell. |
| Heal friend/sio | `ctoa_helper_heal_friend.lua` | Observer and whitelist first; no cast until sandbox whitelist smoke exists. |
| Conditions | `ctoa_helper_conditions.lua` | Read-only state observer first; no recovery action until condition smoke exists. |
| Equipment | `ctoa_helper_equipment.lua` | Read-only slot observer first; no item move/use until inventory smoke exists. |
| Scripting/macros | `ctoa_helper_scripting.lua` | Deny-all policy shell first; no eval/snippets without security review. |

## Required Evidence Before Import

Before any external logic changes runtime behavior:

1. Add or update a named helper module file.
2. Add package copy coverage in `scripts/windows/solteria_helper_test_env.ps1`.
3. Add static contracts in `tests/test_otclient_helper_zerobot_shell.py`.
4. Update `scripts/lua/otclient/README.md`.
5. Regenerate `docs/otclient/solteria_helper_next_modules_plan.md`.
6. Run `ValidateDev`, `SmokePreflight`, and `ModuleStaticGates`.
7. Run `SmokeAttachModules` and fresh `SmokeAttachAll` after sandbox character
   is in-world.
8. Keep `PromoteLiveCtoa` behind `-ApproveLiveDeploy`.

## Current Source Review

No vBot source is available in the repository as of this review. The current
safe basis is:

- `docs/otclient/zerobot_reference.md` as a local capability/API reference.
- CTOAi helper modules already extracted into passive domains.
- Runtime gates from `scripts/windows/solteria_helper_test_env.ps1`.

## Next Operator Step

If a vBot archive is provided, place it outside runtime client state, record its
path and hash here, run `scripts/ops/otclient_external_bot_intake.py`, then
review it as a capability checklist. Keep all imported behavior passive until
its matching CTOAi module gate and sandbox evidence pass.
