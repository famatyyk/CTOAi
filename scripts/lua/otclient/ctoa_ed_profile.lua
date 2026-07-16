-- Elder Druid vocation delta. Shared defaults belong to ctoa_native_helper.lua.
-- Runtime remains safe-boot disabled; only vocation differences live here.
return {
    schema_version = "ctoa-helper-profile-v1",
    vocation = "ed",
    name = "CTOAI ED profile",
    enabled = false,
    safe_boot_runtime_disabled = true,
    tick_ms = 500,
    modules = {heal_friend = true},
    healing = {
        spell_threshold = 82,
        potion_threshold = 55,
        spell = "exura vita",
        critical_spell = "exura vita",
        spell_rotation = {
            {threshold = 82, spell = "exura gran"},
            {threshold = 48, spell = "exura vita"},
        },
        mana_potion_threshold = 72,
    },
    tools = {
        auto_attack = false,
        chase = false,
        require_reachable_target = false,
        auto_haste = false,
        haste_spell = "utani gran hur",
        spell_state_families = {
            {id = "haste", flag_names = {"Haste"}, spells = {"utani hur", "utani gran hur"}, max_age_ms = 1500, unknown_policy = "block", fallback_cooldown_ms = 30000},
            {id = "mana_shield", flag_names = {"ManaShield", "NewManaShield"}, spells = {"utamo vita"}, max_age_ms = 1500, unknown_policy = "block", fallback_cooldown_ms = 30000},
        },
        target_timeout_ms = 5000,
        spell_rotation = false,
        rotation_scan_range = 3,
        rotation_spells = {
            {words = "exevo gran mas frigo", min_nearby = 3, cooldown_ms = 8000, scan_range = 3},
            {words = "exevo frigo hur", min_nearby = 2, cooldown_ms = 4000, scan_range = 3},
            {words = "exori gran frigo", min_nearby = 1, max_nearby = 2, cooldown_ms = 2000, scan_range = 3},
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
