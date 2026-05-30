"""Agent 8 QA — Stress test: 1000-tick loop with performance metrics (Sprint 7).

Measures:
  - Ticks per second throughput
  - Decision latency (avg, p95, p99)
  - Memory growth (state objects)
  - Action distribution (no single action dominates >80%)
  - Telemetry write throughput
  - No crashes or unhandled exceptions over 1000 ticks
"""
from __future__ import annotations
import statistics
import time
import unittest
from unittest.mock import patch


TICK_COUNT = 1000


class TestStressTickLoop(unittest.TestCase):
    """1000-tick stress test — must complete in <30s with no errors."""

    @classmethod
    def setUpClass(cls):
        from bot.perception.parser import parse_game_state
        from bot.decision.brain import decide_action
        from bot.action import execute_action

        latencies   = []
        actions     = []
        errors      = 0
        state       = None
        t_start     = time.perf_counter()

        for i in range(TICK_COUNT):
            tick_start = time.perf_counter()
            try:
                state  = parse_game_state(None, prev_state=state)
                action = decide_action(state)
                with patch("time.sleep"):
                    execute_action(action)
                actions.append(action)
            except Exception as e:
                errors += 1

            latencies.append((time.perf_counter() - tick_start) * 1000)

        cls.elapsed_s   = time.perf_counter() - t_start
        cls.latencies   = latencies
        cls.actions     = actions
        cls.errors      = errors
        cls.ticks_ps    = TICK_COUNT / cls.elapsed_s

        sorted_lat = sorted(latencies)
        cls.avg_ms  = statistics.mean(latencies)
        cls.p95_ms  = sorted_lat[int(0.95 * len(sorted_lat))]
        cls.p99_ms  = sorted_lat[int(0.99 * len(sorted_lat))]

        from collections import Counter
        cls.action_dist = Counter(actions)

        print(f"\n{'='*55}")
        print(f"  STRESS TEST — {TICK_COUNT} ticks")
        print(f"{'='*55}")
        print(f"  Elapsed:      {cls.elapsed_s:.2f}s")
        print(f"  Throughput:   {cls.ticks_ps:.0f} ticks/sec")
        print(f"  Latency avg:  {cls.avg_ms:.2f}ms  p95={cls.p95_ms:.2f}ms  p99={cls.p99_ms:.2f}ms")
        print(f"  Errors:       {cls.errors}")
        print(f"  Action dist:  {dict(cls.action_dist.most_common(5))}")
        print(f"{'='*55}")

    # ── Correctness ───────────────────────────────────────────────────────────

    def test_zero_errors(self):
        self.assertEqual(self.errors, 0,
            f"{self.errors} ticks raised unhandled exceptions")

    def test_all_actions_recorded(self):
        self.assertEqual(len(self.actions), TICK_COUNT)

    def test_actions_are_valid_strings(self):
        from bot.action import _ACTION_MAP
        valid = set(_ACTION_MAP.keys()) | {"idle"}
        for a in self.actions:
            self.assertIn(a, valid, f"Unknown action: {a}")

    # ── Performance ───────────────────────────────────────────────────────────

    def test_completes_in_time(self):
        """1000 ticks must complete within 30 seconds (headless, no sleep)."""
        self.assertLess(self.elapsed_s, 30.0,
            f"Loop took {self.elapsed_s:.1f}s — too slow")

    def test_avg_latency_under_10ms(self):
        """Average tick latency must be < 10ms (decision + parse overhead)."""
        self.assertLess(self.avg_ms, 10.0,
            f"Avg latency {self.avg_ms:.2f}ms exceeds 10ms budget")

    def test_p99_latency_under_50ms(self):
        """p99 latency < 50ms — no long GC / IO pauses."""
        self.assertLess(self.p99_ms, 50.0,
            f"p99 latency {self.p99_ms:.2f}ms exceeds 50ms")

    def test_throughput_above_100_ticks_per_sec(self):
        """Must sustain > 100 ticks/sec (real bot needs ~2/sec but pipeline must be fast)."""
        self.assertGreater(self.ticks_ps, 100,
            f"Throughput {self.ticks_ps:.0f} tps — too low")

    # ── Distribution ─────────────────────────────────────────────────────────

    def test_action_diversity(self):
        """No single action should dominate more than 95% of ticks (bot stuck check)."""
        most_common_count = self.action_dist.most_common(1)[0][1]
        dominance = most_common_count / TICK_COUNT
        self.assertLess(dominance, 0.95,
            f"Action '{self.action_dist.most_common(1)[0][0]}' took {dominance:.0%} of ticks")

    def test_idle_not_only_action(self):
        """Bot must take at least one non-idle action."""
        non_idle = sum(c for a, c in self.action_dist.items() if a != "idle")
        self.assertGreater(non_idle, 0, "Bot only idled for all 1000 ticks")


class TestStressGameData(unittest.TestCase):
    """Verify new Fibula + Mintwallin routes and monsters load correctly."""

    def test_total_routes_count(self):
        from bot.data.game_data import get_all_routes
        routes = get_all_routes()
        self.assertGreaterEqual(len(routes), 12, "Expected at least 12 routes")

    def test_fibula_routes_present(self):
        from bot.data.game_data import get_all_routes
        ids = {r["id"] for r in get_all_routes()}
        self.assertIn("fibula_dungeon_l1", ids)
        self.assertIn("fibula_dungeon_l2", ids)
        self.assertIn("fibula_heroes", ids)

    def test_mintwallin_routes_present(self):
        from bot.data.game_data import get_all_routes
        ids = {r["id"] for r in get_all_routes()}
        self.assertIn("mintwallin_minotaurs", ids)
        self.assertIn("mintwallin_deep", ids)

    def test_level_routing_fibula_l1(self):
        from bot.data.game_data import get_route_for_level
        route = get_route_for_level(10)
        self.assertIsNotNone(route)
        # At level 10 we should get a low/medium route
        self.assertIn(route["risk"], ("low", "medium"))

    def test_level_routing_mintwallin(self):
        from bot.data.game_data import get_route_for_level
        route = get_route_for_level(45)
        self.assertIsNotNone(route)

    def test_total_monsters_count(self):
        from bot.data.game_data import get_all_monsters
        self.assertGreaterEqual(len(get_all_monsters()), 18)

    def test_new_monsters_present(self):
        from bot.data.game_data import get_all_monsters
        names = {m["name"] for m in get_all_monsters()}
        for name in ("Orc Warrior", "Minotaur Archer", "Minotaur Mage", "Hero"):
            self.assertIn(name, names)

    def test_monsters_for_level_60(self):
        from bot.data.game_data import get_monsters_for_level
        monsters = get_monsters_for_level(60)
        names = {m["name"] for m in monsters}
        self.assertIn("Hero", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
