# Solteria Safe release lane

CTOA Safe has a release lane independent from the full Helper package:

Current state: `v3.1.0` is the live package. `v3.3.0` is the local full-audit
candidate. In addition to the v3.2 safety repairs, it fixes actionbar/backpack
item assignment, healing checkbox dispatch, rune targeting, plain equipment
use, target timeout/chase/count constraints, buff selection and the native
Solteria skin. It still requires separately approved `Promote` before replacing
live.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_safe_release.ps1 -Action Validate
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_safe_release.ps1 -Action Package
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_safe_release.ps1 -Action Status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_safe_release.ps1 -Action Promote -ApproveLiveDeploy
```

The release contains exactly:

- `mods/ctoa_safe/ctoa_safe.otmod`
- `mods/ctoa_safe/ctoa_safe_loader.lua`
- `mods/ctoa_safe/ctoa_safe_helper.lua`
- `mods/ctoa_safe/styles/helper.otui`
- `mods/ctoa_safe/styles/spell.otui`
- `mods/ctoa_safe/styles/siolist.otui`
- `mods/ctoa_safe/styles/shooterPreset.otui`

`Validate` builds `runtime/solteria_safe_release/latest`, runs executable Safe
tests, enforces safe boot, the three-page UI contract and product exclusions,
and writes a content-bound seven-file manifest. It never changes the live client.

`Package` repeats validation and creates `ctoa-safe-3.3.0-minimal.zip`. The
archive contains only the seven runtime files. Local source history, tests,
recordings, character data, `helper.json` samples and the encrypted reference
module are deliberately excluded.

`Promote` requires the explicit approval switch, rejects source changes after
validation, creates a timestamped backup, copies only the seven Safe files and
requires live SHA-256 parity. It records the live process set before and after;
it does not stop, restart or launch the client. An already loaded Lua instance
continues in memory until a normal client/session reload.

Safe v3 exposes a `kingsvale-helper-json-v1` compatibility adapter for the
observable `helper.json` contract. Import copies sanitized settings into the
local Safe profile but always discards `helperEnabled` runtime state and leaves
Safe disarmed. This is the intentional security boundary of the clean-room
implementation.

This lane does not satisfy, bypass or rewrite Helper P8-P16 evidence. Changes to
the chooser, neutral boot loader or Helper must use the full official package
and its own sandbox/release gates.
