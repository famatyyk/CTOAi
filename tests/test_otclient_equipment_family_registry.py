from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "scripts/lua/otclient/ctoa_helper_equipment_family_registry.lua"
MODULES = ROOT / "scripts/lua/otclient/ctoa_helper_modules.lua"
HELPER = ROOT / "scripts/lua/otclient/ctoa_native_helper.lua"
UI = ROOT / "scripts/lua/otclient/ctoa_helper_ui.lua"
SCHEMA = ROOT / "scripts/lua/otclient/ctoa_helper_profile_schema.lua"
PERSISTENCE = ROOT / "scripts/lua/otclient/ctoa_helper_profile_persistence.lua"
WRAPPER = ROOT / "scripts/windows/solteria_helper_test_env.ps1"


def test_registry_is_packaged_profile_bound_and_checkbox_driven() -> None:
    registry = REGISTRY.read_text(encoding="utf-8")
    modules = MODULES.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")
    persistence = PERSISTENCE.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert 'SCHEMA = "ctoa.equipment-family-registry.v1"' in registry
    assert 'key = "ring_primary"' in registry
    assert "inventory_ids = {3093}" in registry
    assert "equipped_ids = {3096}" in registry
    assert 'key = "ring_secondary"' in registry
    assert "inventory_ids = {3097}" in registry
    assert "equipped_ids = {3099}" in registry
    assert "unknown_transitions_require_approval = true" in registry
    assert "runtime_actions = false" in registry
    assert "moves_items = false" in registry
    assert "ctoa_helper_equipment_family_registry.lua" in modules
    assert "ctoa_helper_equipment_family_registry.lua" in wrapper
    assert 'rawget(_G, "CTOA_HELPER_EQUIPMENT_FAMILY_REGISTRY")' in helper
    assert "equipment_family_rows" in helper
    assert "set_equipment_family_enabled" in helper
    assert 'id = "ctoaEquipmentFamily" .. tostring(index)' in ui
    assert "equipment.family_enabled[key] == true" in ui
    assert '"family_enabled"' in schema
    assert 'family_enabled = {"ring_primary", "ring_secondary"}' in schema
    assert '"family_enabled"' in persistence


@pytest.mark.skipif(shutil.which("lua") is None, reason="Lua runtime unavailable")
def test_registry_matches_states_and_requires_review_for_unknown_transition(
    tmp_path: Path,
) -> None:
    probe = tmp_path / "registry_probe.lua"
    probe.write_text(
        r"""
local registry=dofile(arg[1])
local ok,blockers=registry.validate(); assert(ok and #blockers==0)
local primary=registry.match("ring",3096); assert(primary.family.key=="ring_primary" and primary.state=="equipped")
local returned=registry.match("ring",3093); assert(returned.family.key=="ring_primary")
local secondary=registry.match("ring",3097); assert(secondary.family.key=="ring_secondary")
local active=registry.match("ring",3099); assert(active.family.key=="ring_secondary" and active.state=="equipped")
local cfg={family_enabled={ring_primary=false,ring_secondary=false},ring_swap=false}
assert(registry.setEnabled(cfg,"ring_secondary",true)==true and cfg.ring_swap==true)
local selected=registry.enabledFamily(cfg,"ring"); assert(selected.key=="ring_secondary")
local known=registry.proposeTransition({slot="ring",before_equipped_id=3096,candidate_inventory_id=3097,after_equipped_id=3099,returned_inventory_id=3093})
assert(known.status=="known_transition" and known.transition_known==true and known.operator_approval_required==false)
local unknown=registry.proposeTransition({slot="ring",before_equipped_id=3096,candidate_inventory_id=4000,after_equipped_id=4001,returned_inventory_id=3093})
assert(unknown.status=="review_required" and unknown.operator_approval_required==true and unknown.dispatch_allowed==false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [shutil.which("lua"), str(probe), str(REGISTRY)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
