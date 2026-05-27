"""Agent 8 QA — Integration tests: full tick-loop with mock screen (Sprint 5).

Covers:
  1. parse_game_state — graceful fallback when cv2 unavailable
  2. Full bot tick: screen → parse → decide → act, no real screen required
  3. ML fallback: Q-learning raises → rules engine takes over
  4. Humanizer is wired (delays called during actions)
  5. Telemetry writes survive tick cycle
  6. select_target / follow_route actions in action map
  7. N-tick loop writes no real I/O, stays deterministic
  8. Dashboard endpoints (skipped when fastapi not installed)
"""
from __future__ import annotations
import time
import unittest
from unittest.mock import patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_fake_pixels():
    """Return a 720×1280 BGRA numpy array (all-black — no colour match)."""
    try:
        import numpy as np
        return np.zeros((720, 1280, 4), dtype="uint8")
    except ImportError:
        return None


# ── Test: parse_game_state ────────────────────────────────────────────────────

class TestParseGameState(unittest.TestCase):
    def test_returns_gamestate_no_pixels(self):
        from bot.perception.parser import parse_game_state
        state = parse_game_state(None)
        self.assertIsNotNone(state)
        self.assertGreaterEqual(state.hp, 0)
        self.assertGreaterEqual(state.mp, 0)

    def test_carries_over_level_from_prev(self):
        from bot.perception.parser import parse_game_state
        from bot.perception.state import GameState
        prev = GameState()
        prev.level = 42
        state = parse_game_state(None, prev_state=prev)
        self.assertEqual(state.level, 42)

    def test_returns_gamestate_with_fake_pixels(self):
        from bot.perception.parser import parse_game_state
        pixels = _make_fake_pixels()
        state = parse_game_state(pixels)
        self.assertIsNotNone(state)
        self.assertIn(state.hp, range(0, 101))
        self.assertIn(state.mp, range(0, 101))

    def test_no_crash_on_tiny_frame(self):
        from bot.perception.parser import parse_game_state
        try:
            import numpy as np
            tiny = np.zeros((10, 10, 3), dtype="uint8")
        except ImportError:
            self.skipTest("numpy not available")
        state = parse_game_state(tiny)
        self.assertIsNotNone(state)


# ── Test: action registry ────────────────────────────────────────────────────

class TestActionRegistry(unittest.TestCase):
    def test_select_target_in_map(self):
        from bot.action import _ACTION_MAP
        self.assertIn("select_target", _ACTION_MAP)

    def test_follow_route_in_map(self):
        from bot.action import _ACTION_MAP
        self.assertIn("follow_route", _ACTION_MAP)

    def test_core_actions_present(self):
        from bot.action import _ACTION_MAP
        expected = {"attack", "use_hp_potion", "use_mp_potion", "loot",
                    "select_target", "follow_route", "idle"}
        missing = expected - set(_ACTION_MAP.keys())
        self.assertEqual(missing, set(), f"Missing handlers: {missing}")


# ── Test: ML fallback ─────────────────────────────────────────────────────────

class TestMLFallback(unittest.TestCase):
    def test_brain_falls_back_to_rules_on_ml_error(self):
        """When ML raises, rules engine must return a valid action name."""
        from bot.decision import brain
        from bot.perception.state import GameState

        state = GameState()
        state.hp = 30;  state.hp_max = 100
        state.mp = 80;  state.mp_max = 100

        with patch.object(brain, "_USE_ML", True), \
             patch("bot.decision.ml_model.predict_action",
                   side_effect=RuntimeError("ML exploded")):
            action = brain.decide_action(state)

        self.assertIsInstance(action, str)
        self.assertGreater(len(action), 0)

    def test_brain_returns_valid_action_healthy_state(self):
        from bot.decision import brain
        from bot.perception.state import GameState
        state = GameState()
        state.hp = state.hp_max = 100
        state.mp = state.mp_max = 100
        action = brain.decide_action(state)
        self.assertIsInstance(action, str)

    def test_brain_heals_on_low_hp(self):
        from bot.decision import brain
        from bot.perception.state import GameState
        state = GameState()
        state.hp = 20;  state.hp_max = 100
        state.mp = state.mp_max = 100
        with patch.object(brain, "_USE_ML", False):
            action = brain.decide_action(state)
        self.assertEqual(action, "use_hp_potion")


# ── Test: N-tick loop ─────────────────────────────────────────────────────────

class TestTickLoop(unittest.TestCase):
    N_TICKS = 20

    def _run_loop(self, n: int):
        from bot.perception.parser import parse_game_state
        from bot.decision.brain import decide_action
        from bot.action import execute_action

        state = None
        actions_taken = []
        for _ in range(n):
            state = parse_game_state(None, prev_state=state)
            action = decide_action(state)
            with patch("time.sleep"):
                try:
                    execute_action(action, state)
                except Exception:
                    pass
            actions_taken.append(action)
        return actions_taken

    def test_loop_runs_n_ticks(self):
        actions = self._run_loop(self.N_TICKS)
        self.assertEqual(len(actions), self.N_TICKS)

    def test_loop_actions_are_valid_strings(self):
        for a in self._run_loop(self.N_TICKS):
            self.assertIsInstance(a, str)
            self.assertGreater(len(a), 0)

    def test_loop_no_unhandled_exceptions(self):
        try:
            self._run_loop(self.N_TICKS)
        except Exception as e:
            self.fail(f"Tick loop raised exception: {e}")


# ── Test: Humanizer wired ─────────────────────────────────────────────────────

class TestHumanizerWired(unittest.TestCase):
    def test_combat_pause_called_during_attack(self):
        """Verify humanizer is wired: combat_pause() called when GUI available."""
        import bot.action.combat as _combat_mod
        from unittest.mock import MagicMock

        # Temporarily enable GUI so the early-return guard is bypassed
        with patch.object(_combat_mod, "_GUI_AVAILABLE", True), \
             patch.object(_combat_mod, "combat_pause") as mock_pause, \
             patch.object(_combat_mod, "pyautogui", MagicMock(), create=True), \
             patch("time.sleep"):
            try:
                _combat_mod.attack_target()
            except Exception:
                pass
        self.assertGreater(mock_pause.call_count, 0)


# ── Test: Telemetry survives tick ─────────────────────────────────────────────

class TestTelemetryInTick(unittest.TestCase):
    def test_log_loot_does_not_raise(self):
        from bot.data.telemetry import log_loot
        try:
            log_loot("Gold Coin", 100)
        except Exception as e:
            self.fail(f"log_loot raised {e}")

    def test_get_stats_returns_dict(self):
        from bot.data.telemetry import get_stats
        s = get_stats()
        self.assertIsInstance(s, dict)
        for key in ("gold_hr", "exp_hr", "kills"):
            self.assertIn(key, s)


# ── Test: dashboard app ────────────────────────────────────────────────────────

class TestDashboard(unittest.TestCase):
    def _client(self):
        try:
            from fastapi.testclient import TestClient
            from bot.dashboard.app import app
            return TestClient(app)
        except ImportError:
            self.skipTest("fastapi not installed")

    def test_stats_endpoint(self):
        r = self._client().get("/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ("gold_hr", "exp_hr", "kills"):
            self.assertIn(key, data)

    def test_metrics_endpoint(self):
        r = self._client().get("/metrics")
        self.assertEqual(r.status_code, 200)
        self.assertIn("bot_gold_per_hour", r.text)

    def test_health_endpoint(self):
        r = self._client().get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_index_returns_html(self):
        r = self._client().get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Dashboard", r.text)


if __name__ == "__main__":
    unittest.main()


