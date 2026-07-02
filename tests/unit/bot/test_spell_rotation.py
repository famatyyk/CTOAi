"""Unit tests for profession and level aware spell rotation."""

import json


def test_spell_rotation_respects_level_and_cooldown(monkeypatch, tmp_path):
    from bot.action import spell_rotation as sr

    cfg = {
        "default_profession": "knight",
        "profiles": [],
        "rotations": {
            "knight": [
                {"key": "f5", "min_level": 8, "cooldown_ms": 1000},
                {"key": "f6", "min_level": 20, "cooldown_ms": 1000},
            ]
        },
    }
    cfg_path = tmp_path / "spell_rotation.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    monkeypatch.setattr(sr, "_CONFIG_PATH", cfg_path)
    monkeypatch.setattr(sr, "_CONFIG_CACHE", None)
    monkeypatch.setattr(sr, "_CONFIG_MTIME", -1.0)
    monkeypatch.setattr(sr, "_last_cast_ts", {})
    monkeypatch.setattr(sr, "_rotation_index", {})

    monkeypatch.setattr(sr, "is_available", lambda: True)
    pressed = []
    monkeypatch.setattr(sr, "press", lambda key: pressed.append(key))

    t = {"value": 100.0}
    monkeypatch.setattr(sr.time, "monotonic", lambda: t["value"])

    assert sr.cast_rotation_spell(10, "knight") == "f5"
    assert sr.cast_rotation_spell(10, "knight") is None

    t["value"] = 101.2
    assert sr.cast_rotation_spell(25, "knight") == "f6"

    t["value"] = 102.5
    assert sr.cast_rotation_spell(25, "knight") == "f5"
    assert pressed == ["f5", "f6", "f5"]


def test_spell_rotation_no_backend_noop(monkeypatch):
    from bot.action import spell_rotation as sr

    monkeypatch.setattr(sr, "is_available", lambda: False)
    assert sr.cast_rotation_spell(20, "knight") is None


def test_detect_profession_from_profile_window_title(monkeypatch):
    from bot.action import spell_rotation as sr

    monkeypatch.setenv("BOT_PROFESSION", "")
    monkeypatch.setenv("BOT_WINDOW_TITLE_ACTIVE", "")
    monkeypatch.setattr(sr, "_active_window_title_lower", lambda: "kingsvale - loyalty pasanot")

    cfg = {
        "default_profession": "knight",
        "profiles": [
            {
                "window_title_contains": "pasanot",
                "profession": "druid",
                "min_level": 1,
                "max_level": 9999,
            }
        ],
        "rotations": {},
    }

    assert sr._detect_profession(30, cfg) == "druid"


def test_detect_profession_from_promoted_keyword(monkeypatch):
    from bot.action import spell_rotation as sr

    monkeypatch.setenv("BOT_PROFESSION", "")
    monkeypatch.setenv("BOT_WINDOW_TITLE_ACTIVE", "")
    monkeypatch.setattr(sr, "_active_window_title_lower", lambda: "you are an elder druid")

    cfg = {
        "default_profession": "knight",
        "profiles": [],
        "rotations": {},
    }

    assert sr._detect_profession(30, cfg) == "druid"


def test_detect_profession_from_client_profile_override(monkeypatch):
    from bot.action import spell_rotation as sr

    monkeypatch.setenv("BOT_PROFESSION", "")
    monkeypatch.setenv("BOT_WINDOW_TITLE_ACTIVE", "")
    monkeypatch.setenv("BOT_CLIENT_PROFILE", "kamil_client")

    cfg = {
        "default_profession": "druid",
        "profiles": [],
        "client_profiles": {
            "kamil_client": {
                "default_profession": "monk",
            }
        },
        "rotations": {},
    }

    merged = sr._merge_rotation_config(cfg)
    assert sr._detect_profession(30, merged) == "monk"


def test_spell_rotation_uses_kamil_client_monk_profile(monkeypatch, tmp_path):
    from bot.action import spell_rotation as sr

    cfg = {
        "default_profession": "druid",
        "profiles": [],
        "client_profiles": {
            "kamil_client": {
                "default_profession": "monk",
                "rotations": {
                    "monk": [
                        {"key": "f2", "min_level": 8, "cooldown_ms": 1000},
                    ]
                },
            }
        },
        "rotations": {
            "druid": [],
        },
    }
    cfg_path = tmp_path / "spell_rotation.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    monkeypatch.setattr(sr, "_CONFIG_PATH", cfg_path)
    monkeypatch.setattr(sr, "_CONFIG_CACHE", None)
    monkeypatch.setattr(sr, "_CONFIG_MTIME", -1.0)
    monkeypatch.setattr(sr, "_last_cast_ts", {})
    monkeypatch.setattr(sr, "_rotation_index", {})

    monkeypatch.setenv("BOT_PROFESSION", "")
    monkeypatch.setenv("BOT_WINDOW_TITLE_ACTIVE", "")
    monkeypatch.setenv("BOT_CLIENT_PROFILE", "kamil_client")

    monkeypatch.setattr(sr, "is_available", lambda: True)
    pressed = []
    monkeypatch.setattr(sr, "press", lambda key: pressed.append(key))
    monkeypatch.setattr(sr.time, "monotonic", lambda: 100.0)

    assert sr.cast_rotation_spell(20) == "f2"
    assert pressed == ["f2"]
