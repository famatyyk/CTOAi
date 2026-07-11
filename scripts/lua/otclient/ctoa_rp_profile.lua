-- Default Royal Paladin profile. Runtime remains safe-boot disabled.
return {
    schema_version = "ctoa-helper-profile-v1", vocation = "rp", name = "CTOAI RP profile",
    enabled = false, safe_boot_runtime_disabled = true, tick_ms = 500,
    modules = {overview=true, healing=true, heal_friend=false, conditions=false, targeting=true, magic=true, cavebot=true, equipment=false, helper=true, scripting=false, settings=true, engine=true},
    healing = {
        spell_enabled=true, potion_enabled=true, spell_threshold=82, potion_threshold=58,
        threshold_jitter_percent=3, spell="exura gran san", critical_spell="exura gran san",
        spell_rotation={{threshold=82,spell="exura san"},{threshold=48,spell="exura gran san"}},
        potion_mode="Actionbar", potion_hotkey="F1", potion_actionbar_slot="F1",
        mana_potion_enabled=true, mana_potion_threshold=50, mana_potion_hotkey="F2", mana_potion_actionbar_slot="F2",
        mana_potion_cooldown_ms=1000, cooldown_ms=1000,
    },
    heal_friend = {enabled=false, runtime_enabled=false, observe_party=true, friend_whitelist={}, require_whitelist=true},
    conditions = {enabled=false, runtime_enabled=false, observe_states=true},
    equipment = {enabled=false, runtime_enabled=false, observe_slots=true},
    scripting = {enabled=false, runtime_enabled=false, allow_user_snippets=false, allow_runtime_eval=false, policy_mode="deny_all"},
    tools = {
        auto_attack=false, chase=true, pause_in_pz=true, hold_target=false, require_reachable_target=false,
        auto_haste=false, timer_enabled=false,
        attack_range=7, target_timeout_ms=6000, unreachable_timeout_ms=1200, retarget_delay_ms=200,
        spell_rotation=false, magic_priority="rotation", rotation_interval_ms=1050, rotation_scan_range=3,
        rotation_spells={
            {words="exevo mas san",min_nearby=3,cooldown_ms=4000,scan_range=3},
            {words="exori gran con",min_nearby=1,max_nearby=2,cooldown_ms=2000,scan_range=7},
            {words="exori san",min_nearby=1,max_nearby=2,cooldown_ms=2000,scan_range=7},
        },
        auto_exeta=false, rune_enabled=false, rune_hotkey="F5", rune_actionbar_slot="F5",
        cavebot_enabled=false, cavebot_movement_enabled=false, cavebot_waypoints={},
        feature_flags={diagnostics=true,experimental_cavebot=false,experimental_loot=false,experimental_combat=false},
    },
    hud = {enabled=true,x=22,y=170},
}
