from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_recovery_runtime.lua"


def test_recovery_jitter_stays_bounded_and_affects_rotation_thresholds(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for recovery-jitter validation"
    probe = tmp_path / "recovery_jitter_probe.lua"
    probe.write_text(
        """
local recovery = dofile(arg[1])
for nonce = 0, 50 do
  local threshold, offset = recovery.jitterThreshold(62, 3, nonce)
  assert(threshold >= 59 and threshold <= 65)
  assert(offset >= -3 and offset <= 3)
end
local unchanged, zero = recovery.jitterThreshold(45, 0, 99)
assert(unchanged == 45 and zero == 0)
local healing = {
  threshold_jitter_percent = 3,
  spell = "basic",
  critical_spell = "critical",
  spell_rotation = {
    {threshold = 80, spell = "light"},
    {threshold = 50, spell = "strong"},
  },
}
local first = recovery.selectHealingSpell(healing, 49, 10)
local second = recovery.selectHealingSpell(healing, 49, 11)
assert(first ~= nil and second ~= nil)
assert(recovery.contract().owns_threshold_jitter == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(RECOVERY)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
