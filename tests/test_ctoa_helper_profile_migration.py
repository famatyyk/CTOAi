from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_schema.lua"
HELPER = ROOT / "scripts" / "lua" / "otclient" / "ctoa_native_helper.lua"
PERSISTENCE = (
    ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_profile_persistence.lua"
)
HOTKEYS = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_hotkeys.lua"
MODAL = ROOT / "scripts" / "lua" / "otclient" / "ctoa_helper_modal.lua"
BUILDER = ROOT / "scripts" / "ops" / "ctoa_otprofile_builder.py"


def test_profile_version_is_preserved_across_build_load_and_export():
    schema = SCHEMA.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    persistence = PERSISTENCE.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")

    assert 'local CURRENT_PROFILE_SCHEMA = "ctoa-helper-profile-v1"' in schema
    assert 'schema_version = "ctoa-helper-profile-v1"' in helper
    assert (
        'moduleValue(externalProfileSchema, "migrate", profile, HELPER_CONFIG)'
        in helper
    )
    assert 'status("Profile blocked: " .. tostring(reason))' in helper
    assert (
        'schema_version = cfg.schema_version or "ctoa-helper-profile-v1"' in persistence
    )
    assert '"schema_version": "ctoa-helper-profile-v1"' in builder


def test_versioned_profile_migration_is_safe_and_future_versions_fail_closed(
    tmp_path: Path,
):
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


def test_extracted_profile_and_input_helpers_execute_in_support_modules(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for support-module validation"
    probe = tmp_path / "profile_input_extraction_probe.lua"
    probe.write_text(
        r"""
local schema = dofile(arg[1])
local persistence = dofile(arg[2])
local hotkeys = dofile(arg[3])
local modal = dofile(arg[4])

assert(schema.displayProfileName("monk route") == "EK monk profile")
assert(schema.displayProfileName("CTOAI EK: test") == "CTOAI EK profile")
assert(schema.displayProfileName("long profile", function() return "short" end) == "short")
assert(schema.profileSchemaValue("onOffLabel", "fallback", true) == "ON")
assert(schema.profileSchemaValue("missing", "fallback") == "fallback")
local options = schema.profileSchemaTable("optionList", {}, "hotkey")
assert(type(options) == "table" and options[1] == "F1")
local tableFallback = {fallback = true}
assert(schema.profileSchemaTable("onOffLabel", tableFallback, true) == tableFallback)
local merged = schema.mergeTable({tools = {enabled = false}}, {tools = {enabled = true}})
assert(merged.tools.enabled == true)
assert(string.find(schema.serializeLua({enabled = false}, "profile"), "enabled = false", 1, true))

assert(persistence.profilePersistenceValue("loadSuccessText", "fallback", "profile", "EK") == "Profile loaded: EK")
local candidates = persistence.profilePersistenceTable("profileCandidates", {})
assert(type(candidates) == "table" and #candidates > 0)
local exported = persistence.exportProfile({schema_version = "ctoa-helper-profile-v1", tools = {}}, "EK")
assert(exported.name == "EK" and exported.schema_version == "ctoa-helper-profile-v1")
local prefs = persistence.exportUiPrefs({hotkey = "Ctrl+H", hud = {}}, {active_tab = "tools"})
assert(prefs.hotkey == "Ctrl+H" and prefs.active_tab == "tools")

assert(hotkeys.normalizeHelperHotkey(" ctrl + j ") == "Ctrl+J")
local decision = hotkeys.hotkeyBindingDecision("Ctrl+J", "Ctrl+H", {"Ctrl+J"})
assert(decision.allowed == true and decision.changed == true)
assert(hotkeys.resolveActionbarSlot("F2", "F3") == "F2")
assert(hotkeys.resolveActionbarSlot(nil, "F3") == "F3")
assert(hotkeys.resolveActionbarSlot(nil, nil) == nil)

local request = modal.modalRequest("cavebot_delete", "waypoint 2", 4500, 100)
assert(request.action == "cavebot_delete")
assert(request.requested_at_ms == 100 and request.expires_at_ms == 4600)
assert(schema.contract().runtime_actions == false)
assert(persistence.contract().writes_profile == false)
assert(hotkeys.contract().binds_keys == false)
assert(modal.contract().runtime_actions == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SCHEMA), str(PERSISTENCE), str(HOTKEYS), str(MODAL)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_profile_export_descriptors_cover_every_generated_section_with_fixture_parity(tmp_path: Path):
    lua = shutil.which("lua")
    assert lua, "Lua interpreter is required for profile descriptor validation"
    probe = tmp_path / "profile_export_descriptor_probe.lua"
    probe.write_text(
        r"""
local schema = dofile(arg[1])
local persistence = dofile(arg[2])
local schemaDescriptors = schema.profileExportDescriptors()
local persistenceDescriptors = persistence.profileExportDescriptors()
assert(#schemaDescriptors == 6 and #persistenceDescriptors == #schemaDescriptors)

local config = {schema_version = "ctoa-helper-profile-v1", modules = {overview = true}}
for index, descriptor in ipairs(schemaDescriptors) do
  assert(descriptor.id == descriptor.source and descriptor.id == descriptor.output)
  assert(descriptor.generated == true and #descriptor.fields > 0)
  assert(persistenceDescriptors[index].id == descriptor.id)
  config[descriptor.source] = {}
  for fieldIndex, field in ipairs(descriptor.fields) do
    config[descriptor.source][field] = descriptor.id .. ":" .. tostring(fieldIndex)
  end
end

local exported = persistence.exportProfile(config, "descriptor fixture")
for _, descriptor in ipairs(schemaDescriptors) do
  local section = exported[descriptor.output]
  assert(type(section) == "table")
  local count = 0
  for _, field in ipairs(descriptor.fields) do
    count = count + 1
    assert(section[field] == config[descriptor.source][field])
  end
  local actual = 0
  for _ in pairs(section) do actual = actual + 1 end
  assert(actual == count)
end
assert(schema.contract().owns_profile_export_descriptors == true)
assert(persistence.contract().owns_profile_export_descriptors == true)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(SCHEMA), str(PERSISTENCE)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_profile_descriptor_modules_keep_loader_and_write_ownership_outside():
    for source_path in (SCHEMA, PERSISTENCE):
        source = source_path.read_text(encoding="utf-8")
        assert "io.write" not in source
        assert "io.open" not in source
        assert "dofile(" not in source


def test_profile_and_ui_pref_writes_fail_closed_to_string_payloads():
    source = HELPER.read_text(encoding="utf-8")
    assert 'if type(profileSaveText) ~= "string"' in source
    assert 'if type(uiPrefsSaveText) ~= "string"' in source
    assert "file:write(profileSaveText)" in source
    assert "file:write(uiPrefsSaveText)" in source
