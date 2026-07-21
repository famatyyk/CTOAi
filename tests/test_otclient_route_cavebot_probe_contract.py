from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
OTCLIENT = ROOT / "scripts" / "lua" / "otclient"
ROUTE = OTCLIENT / "ctoa_helper_route.lua"
CAVEBOT = OTCLIENT / "ctoa_helper_cavebot_runtime.lua"
HELPER = OTCLIENT / "ctoa_native_helper.lua"


def test_probe_metadata_and_formatting_live_only_in_passive_adapters() -> None:
    route = ROUTE.read_text(encoding="utf-8")
    cavebot = CAVEBOT.read_text(encoding="utf-8")

    for function_name in ("positionText", "probeTarget", "probeMetadata"):
        assert f"function Route.{function_name}" in route
    for token in (
        'schema_version = "ctoa.route-probe-metadata.v1"',
        "owns_position_text = true",
        "owns_probe_target = true",
        "owns_probe_metadata = true",
        "probe_mutates_route = false",
        "probe_changes_arming = false",
    ):
        assert token in route

    for function_name in (
        "movementCapability",
        "probeMetadata",
        "probeSnapshot",
        "probeSummary",
        "probeReport",
        "pathText",
    ):
        assert f"function CavebotRuntime.{function_name}" in cavebot
    for token in (
        'schema_version = "ctoa.cavebot-probe-metadata.v1"',
        'schema_version = "ctoa.cavebot-probe-report.v1"',
        "owns_probe_metadata = true",
        "probe_executes_movement = false",
        "probe_mutates_route = false",
        "probe_changes_arming = false",
        "runtime_actions = false",
        "movement_executed = false",
        "route_mutated = false",
        "arming_changed = false",
    ):
        assert token in cavebot

    route_probe = route[
        route.index("function Route.positionText") : route.index("function Route.add")
    ]
    cavebot_probe = cavebot[
        cavebot.index("function CavebotRuntime.probeMetadata") : cavebot.index(
            "function CavebotRuntime.movementBlockedReason"
        )
    ]
    for forbidden in (
        "autoWalk",
        "findPath",
        "g_game",
        "g_map",
        "table.remove",
        "cavebot_waypoints =",
        "cavebot_index =",
        "runtime_session_armed",
    ):
        assert forbidden not in route_probe
        assert forbidden not in cavebot_probe


def test_route_and_cavebot_probe_contract_is_normalized_and_non_mutating(
    tmp_path: Path,
) -> None:
    lua = shutil.which("lua")
    if not lua:
        pytest.skip("Lua interpreter is required for passive adapter contract")
    probe = tmp_path / "route_cavebot_probe_contract.lua"
    probe.write_text(
        r"""
local route = dofile(arg[1])
local cavebot = dofile(arg[2])

local tools = {
  cavebot_index = 2,
  cavebot_waypoints = {
    {x = 100, y = 200, z = 7, label = "start"},
    {x = 104, y = 203, z = 7, label = "hunt"},
  },
}
local metadata = route.probeMetadata(tools, {x = 101, y = 201, z = 7})
assert(metadata.schema_version == "ctoa.route-probe-metadata.v1")
assert(metadata.mode == "passive")
assert(metadata.waypoint_count == 2 and metadata.selected_index == 2)
assert(metadata.label == "hunt" and metadata.target_text == "104,203,7")
assert(metadata.current_text == "101,201,7" and metadata.distance == 3)
assert(metadata.same_floor == true and metadata.target_valid == true)
assert(metadata.runtime_actions == false and metadata.movement_executed == false)
assert(metadata.route_mutated == false and metadata.arming_changed == false)
assert(tools.cavebot_index == 2 and #tools.cavebot_waypoints == 2)

tools.cavebot_index = 99
local clamped = route.probeTarget(tools)
assert(clamped.selected_index == 2 and clamped.label == "hunt")
assert(tools.cavebot_index == 99)
local empty = route.probeMetadata({}, {x = 1, y = 2, z = 7})
assert(empty.route_empty == true and empty.has_waypoint == false)
assert(empty.target == nil and empty.target_text == "nil")

local report = cavebot.probeReport({
  reason = "manual",
  api = {
    game_walk = true,
    game_auto_walk = false,
    game_force_walk = true,
    player_auto_walk = true,
    player_stop_auto_walk = false,
  },
  player_can_sample = {available = true, ok = true, value = true},
  route_metadata = metadata,
  path_sample = {available = true, ok = true, dirs_count = 3, result = "ok"},
})
assert(report.schema_version == "ctoa.cavebot-probe-report.v1")
assert(report.mode == "passive_probe")
assert(report.metadata.schema_version == "ctoa.cavebot-probe-metadata.v1")
assert(report.metadata.api.game_walk == true)
assert(report.metadata.api.game_auto_walk == false)
assert(report.metadata.can_walk.available == true and report.metadata.can_walk.can_move == true)
assert(report.metadata.route.selected_index == 2 and report.metadata.route.waypoint_count == 2)
assert(report.metadata.path.text == "dirs=3 result=ok")
assert(string.find(report.text, "route=2/2", 1, true) ~= nil)
assert(string.find(report.text, "label=hunt", 1, true) ~= nil)
assert(report.runtime_actions == false and report.movement_executed == false)
assert(report.route_mutated == false and report.arming_changed == false)
assert(#report.intrusive_actions_performed == 0)

local forged = cavebot.probeReport({
  schema_version = "ctoa.cavebot-probe-metadata.v1",
  reason = "forged",
  runtime_actions = true,
  movement_executed = true,
  route_mutated = true,
  arming_changed = true,
})
assert(forged.metadata.runtime_actions == false)
assert(forged.metadata.movement_executed == false)
assert(forged.metadata.route_mutated == false)
assert(forged.metadata.arming_changed == false)

local routeContract = route.contract()
local cavebotContract = cavebot.contract()
assert(routeContract.owns_probe_metadata == true and routeContract.probe_mutates_route == false)
assert(cavebotContract.owns_probe_metadata == true and cavebotContract.probe_executes_movement == false)
assert(cavebotContract.probe_mutates_route == false and cavebotContract.probe_changes_arming == false)
""",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [lua, str(probe), str(ROUTE), str(CAVEBOT)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_guarded_shell_still_owns_movement_mutation_and_arming_boundaries() -> None:
    source = HELPER.read_text(encoding="utf-8")

    probe = source[
        source.index("function runMovementApiProbe") : source.index(
            "function runMagicApiProbe"
        )
    ]
    assert 'moduleValue(externalRoute, "probeMetadata", tools, current)' in probe
    assert 'moduleValue(externalCavebotRuntime, "probeReport"' in probe
    assert 'safeCall(player, "canWalk", true)' in probe
    assert "return g_map.findPath(current, target, 200, 0)" in probe
    assert "function cavebotMovementCapabilitySample" not in source
    assert "function movementPathProbeSample" not in source
    assert "function movementPathProbeText" not in source
    for moved_out in (
        "tools.cavebot_waypoints",
        "tools.cavebot_index",
        'moduleValue(externalDiagnostics, "boolText"',
        'moduleValue(externalDiagnostics, "posText"',
        "movementPathProbeText(current, target)",
        "player:autoWalk",
        'moduleValue(externalRoute, "editorAction"',
        "requestRuntimeSessionArm",
    ):
        assert moved_out not in probe

    assert "function autoWalkTo(pos)" in source
    assert "return player:autoWalk(pos, retry)" in source
    assert "function applyCavebotEditorAction(action, options)" in source
    assert 'moduleValue(externalRoute, "editorAction"' in source
    assert "function requestRuntimeSessionArm(reason)" in source
    assert "Helper.runtime_session_armed = true" in source
    assert 'moduleValue(externalDiagnostics, "vocationProbeText"' in source
    assert 'moduleValue(externalTimerRuntime, "probeSummary", plan)' in source
