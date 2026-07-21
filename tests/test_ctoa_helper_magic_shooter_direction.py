from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMBAT_RUNTIME = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_combat_runtime.lua"
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"


def test_exori_min_selects_best_facing_and_beats_exori_for_two_aligned_mobs(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    if not lua:
        pytest.skip("Lua interpreter is required for Magic Shooter validation")

    scenario = tmp_path / "magic_shooter_direction.lua"
    scenario.write_text(
        """
local runtime = dofile(arg[1])
local scan = {
  adjacent = 3,
  facing_direction = 0,
  directional_hits = {[0] = 1, [1] = 2, [2] = 0, [3] = 1},
}
local rows = runtime.rotationSpellRows({
  {words = "exori", min_nearby = 2, cooldown_ms = 4000},
  {words = "exori min", min_nearby = 2, cooldown_ms = 4000, directional = true},
}, {scan = scan, rotation_scan_range = 1, last_spell_casts = {}})
assert(rows[2].mob_count == 2)
assert(rows[2].turn_direction == 1)
assert(rows[2].directional == true)
local selected = runtime.rotationSpell(rows, {
  now_ms = 5000,
  action_lock_until_ms = 0,
  last_attack_spell_ms = 0,
  rotation_interval_ms = 1050,
})
assert(selected.words == "exori min")
assert(selected.turn_direction == 1)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(scenario), str(COMBAT_RUNTIME)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_magic_shooter_turns_before_directional_cast() -> None:
    source = HELPER.read_text(encoding="utf-8")
    turn_at = source.index("g_game.turn(desiredDirection)")
    cast_at = source.index('if descriptor.kind == "spell" and descriptor.words ~= "" then sent = castSpell(descriptor.words) end')
    assert turn_at < cast_at
    assert "Rotation blocked: turn API unavailable" in source
