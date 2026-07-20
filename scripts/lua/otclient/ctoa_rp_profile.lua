-- Royal Paladin vocation delta. Shared defaults belong to ctoa_native_helper.lua.
-- Runtime remains safe-boot disabled; only vocation differences live here.
return {
    schema_version = "ctoa-helper-profile-v1",
    vocation = "rp",
    name = "CTOAI RP profile",
    enabled = false,
    safe_boot_runtime_disabled = true,
    tick_ms = 500,
    healing = {
        spell_threshold = 82,
        potion_threshold = 58,
        spell = "exura gran san",
        critical_spell = "exura gran san",
        spell_rotation = {
            {threshold = 82, spell = "exura san"},
            {threshold = 48, spell = "exura gran san"},
        },
        mana_potion_threshold = 50,
    },
    tools = {
        auto_attack = false,
        require_reachable_target = false,
        auto_haste = false,
        spell_state_families = {
            {id = "haste", flag_names = {"Haste"}, spells = {"utani hur"}, max_age_ms = 1500, unknown_policy = "block", fallback_cooldown_ms = 30000},
        },
        spell_rotation = false,
        rotation_scan_range = 3,
        rotation_spells = {
            {words = "exevo mas san", min_nearby = 3, cooldown_ms = 4000, scan_range = 3},
            {words = "exori gran con", min_nearby = 1, max_nearby = 2, cooldown_ms = 2000, scan_range = 7},
            {words = "exori san", min_nearby = 1, max_nearby = 2, cooldown_ms = 2000, scan_range = 7},
        },
        auto_exeta = false,
        rune_enabled = false,
        cavebot_enabled = false,
        cavebot_movement_enabled = false,
        timer_enabled = false,
        feature_flags = {
            diagnostics = true,
            experimental_cavebot = false,
            experimental_loot = false,
            experimental_combat = false,
        },
    },
    hud = {enabled = true, x = 22, y = 170},
}
