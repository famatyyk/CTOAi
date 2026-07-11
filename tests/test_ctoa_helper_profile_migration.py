from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_schema.lua"
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
PERSISTENCE = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_persistence.lua"
BUILDER = ROOT / "scripts" / "ops" / "ctoa_otprofile_builder.py"


def test_profile_version_is_preserved_across_build_load_and_export():
    schema = SCHEMA.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    persistence = PERSISTENCE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")

    assert 'local CURRENT_PROFILE_SCHEMA = "ctoa-helper-profile-v1"' in schema
    assert 'schema_version = "ctoa-helper-profile-v1"' in helper
    assert 'moduleValue(externalProfileSchema, "migrate", profile, HELPER_CONFIG)' in helper
    assert 'status("Profile blocked: " .. tostring(reason))' in helper
    assert 'schema_version = cfg.schema_version or "ctoa-helper-profile-v1"' in persistence
    assert '"schema_version": "ctoa-helper-profile-v1"' in builder


def test_versioned_profile_migration_is_safe_and_future_versions_fail_closed(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for profile migration validation"
    probe = tmp_path / "profile_migration_probe.lua"
    probe.write_text(
        """
local schema = dofile(arg[1])
local defaults = {
  schema_version = "ctoa-helper-profile-v1",
  name = "default",
  enabled = false,
  safe_boot_runtime_disabled = true,
  tick_ms = 500,
  healing = {},
  heal_friend = {},
  conditions = {},
  equipment = {},
  scripting = {},
  tools = {feature_flags = {}},
  hud = {},
}

local migrated, plan = schema.migrate({
  name = "legacy",
  enabled = true,
  safe_boot_runtime_disabled = false,
  tools = {
    auto_attack = true,
    cavebot_movement_enabled = true,
    feature_flags = {experimental_combat = true},
  },
  scripting = {enabled = true, allow_runtime_eval = true},
}, defaults)

assert(migrated ~= nil)
assert(plan.allowed == true and plan.reason == "migration_required")
assert(plan.source_version == 0 and plan.target_version == 1)
assert(migrated.schema_version == "ctoa-helper-profile-v1")
assert(migrated.name == "legacy")
assert(migrated.enabled == false)
assert(migrated.safe_boot_runtime_disabled == true)
assert(migrated.tools.auto_attack == false)
assert(migrated.tools.cavebot_movement_enabled == false)
assert(migrated.tools.feature_flags.experimental_combat == false)
assert(migrated.scripting.enabled == false)
assert(migrated.scripting.allow_runtime_eval == false)
assert(migrated.healing ~= nil and migrated.hud ~= nil)

local future, futurePlan = schema.migrate({schema_version = "ctoa-helper-profile-v2"}, defaults)
assert(future == nil)
assert(futurePlan.allowed == false and futurePlan.reason == "future_schema_version")

local invalid, invalidPlan = schema.migrate({schema_version = "other-v1"}, defaults)
assert(invalid == nil)
assert(invalidPlan.allowed == false and invalidPlan.reason == "invalid_schema_version")

local order = schema.keyOrder("profile")
assert(order[1] == "schema_version")
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SCHEMA)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
