"""AGENT 8: Integration test — bot loop runs N ticks without crashing."""
import time
from unittest.mock import patch
from bot.perception.state import GameState
from bot.decision.brain import decide_action
from bot.action import execute_action
from bot.data.telemetry import set_session


def test_bot_loop_10_ticks():
    """Simulate 10 bot ticks with mocked screen capture."""
    set_session(0)  # dummy session id for test
    dummy_state = GameState(hp=100, hp_max=100, mp=100, mp_max=100, target_id=None)

    with patch("bot.perception.screen.capture_region_pixels", return_value=None), \
         patch("bot.perception.parser.parse_game_state", return_value=dummy_state), \
         patch("bot.data.telemetry.log_event"):

        for _ in range(10):
            pixels = None
            state  = dummy_state
            action = decide_action(state)
            result = execute_action(action)
            assert action in ("find_monster", "attack", "flee_to_depot",
                              "use_hp_potion", "use_mp_potion", "loot",
                              "go_to_depot", "idle")
            assert result in ("ok", "unknown_action") or result.startswith("error:")
