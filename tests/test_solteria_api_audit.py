from pathlib import Path

from scripts.ops.solteria_api_audit import parse_meta, render_markdown


def test_parse_meta_extracts_global_functions_and_methods(tmp_path: Path):
    meta = tmp_path / "meta.lua"
    meta.write_text(
        "\n".join(
            [
                "---@class g_game",
                "g_game = {}",
                "---@param direction integer",
                "---@param isKeyDown? boolean false",
                "---@return boolean",
                "function g_game.walk(direction, isKeyDown) end",
                "",
                "---@class LocalPlayer : Player",
                "LocalPlayer = {}",
                "---@param destination Position | string",
                "---@param retry? boolean false",
                "---@return boolean",
                "function LocalPlayer:autoWalk(destination, retry) end",
                "",
                "---@param fromPos Position | string",
                "---@param toPos Position | string",
                "---@return integer",
                "function getDirectionFromPos(fromPos, toPos) end",
            ]
        ),
        encoding="utf-8",
    )

    report = parse_meta(meta)

    assert report["function_count"] == 3
    assert report["class_count"] == 3
    g_game = report["namespaces"]["g_game"]
    local_player = report["namespaces"]["LocalPlayer"]
    globals_ = report["namespaces"]["_G"]
    assert g_game[0]["full_name"] == "g_game.walk"
    assert g_game[0]["params"][0] == {"name": "direction", "type": "integer"}
    assert g_game[0]["returns"] == ["boolean"]
    assert local_player[0]["full_name"] == "LocalPlayer:autoWalk"
    assert globals_[0]["full_name"] == "getDirectionFromPos"


def test_render_markdown_includes_high_value_api(tmp_path: Path):
    meta = tmp_path / "meta.lua"
    meta.write_text(
        "\n".join(
            [
                "---@class g_map",
                "g_map = {}",
                "---@param start Position | string",
                "---@param goal Position | string",
                "---@return integer[], integer",
                "function g_map.findPath(start, goal, maxComplexity, flags) end",
            ]
        ),
        encoding="utf-8",
    )
    parsed = parse_meta(meta)
    markdown = render_markdown(
        {
            "client_path": "C:/client",
            "meta": parsed,
            "archives": [],
            "binary_keyword_hits": {},
        }
    )

    assert "### g_map" in markdown
    assert "`g_map.findPath(start, goal, maxComplexity, flags)`" in markdown
