from __future__ import annotations
import sys
import unittest
from unittest.mock import patch
import numpy as np


def _make_frame(w=800, h=600):
    f = np.zeros((h, w, 3), dtype=np.uint8)
    f[0:10, 0:140] = (0, 0, 200)
    f[12:22, 0:140] = (200, 0, 0)
    f[50:60, 640:650] = (200, 200, 200)
    return f


TICKS = 50


class TestBotE2EHeadless(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frame = _make_frame()
        from bot.perception.parser import parse_game_state
        from bot.decision.brain import decide_action
        from bot.action import execute_action
        actions, errors, state = [], [], None
        with patch("time.sleep"):
            for _ in range(TICKS):
                try:
                    state = parse_game_state(frame, prev_state=state)
                    action = decide_action(state)
                    execute_action(action)
                    actions.append(action)
                except Exception as exc:
                    errors.append(str(exc))
        cls.actions, cls.errors, cls.final_state = actions, errors, state

    def test_no_errors(self):
        self.assertEqual(self.errors, [])

    def test_all_ticks_produced_action(self):
        self.assertEqual(len(self.actions), TICKS)

    def test_actions_are_strings(self):
        for a in self.actions:
            self.assertIsInstance(a, str)

    def test_state_has_hp_mp(self):
        s = self.final_state
        self.assertIsNotNone(s)
        self.assertGreaterEqual(s.hp_pct, 0.0)
        self.assertLessEqual(s.hp_pct, 1.0)

    def test_not_all_idle(self):
        self.assertGreater(sum(1 for a in self.actions if a != "idle"), 0)


class TestOTSConfig(unittest.TestCase):

    def _reset(self):
        import os, bot.connection.ots_config as m
        for k in ("OTS_HOST", "OTS_PORT", "OTS_ACCOUNT", "OTS_CHARACTER"):
            os.environ.pop(k, None)
        m._config = None

    setUp = tearDown = _reset

    def test_defaults(self):
        import bot.connection.ots_config as m
        cfg = m.get_config()
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertEqual(cfg.port, 7171)

    def test_env_override(self):
        import os, bot.connection.ots_config as m
        os.environ["OTS_HOST"] = "10.0.0.1"
        os.environ["OTS_PORT"] = "7172"
        os.environ["OTS_ACCOUNT"] = "acc"
        os.environ["OTS_CHARACTER"] = "Knight"
        cfg = m.get_config()
        self.assertEqual(cfg.host, "10.0.0.1")
        self.assertTrue(cfg.is_configured())

    def test_summary_not_configured(self):
        import bot.connection.ots_config as m
        self.assertIn("NO", m.get_config().summary())


class TestWindowModule(unittest.TestCase):

    def test_find_returns_none_or_handle(self):
        from bot.perception.window import find_tibia_window, WindowHandle
        result = find_tibia_window()
        # Returns None if Tibia is not running, WindowHandle if it is
        self.assertTrue(result is None or isinstance(result, WindowHandle))

    def test_capture_without_mss_returns_none(self):
        with patch.dict(sys.modules, {"mss": None}):
            from importlib import reload
            import bot.perception.window as wm
            reload(wm)
            self.assertIsNone(wm.capture_window(None))
            reload(wm)


if __name__ == "__main__":
    unittest.main()

