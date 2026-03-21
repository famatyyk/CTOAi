#!/usr/bin/env python3
"""
hunt.py — CTOA Autonomous Hunt Loop

Wczytuje konfigurację z config/character.yaml i uruchamia pełny auto-loop.

Użycie:
    python hunt.py                                    # domyślna konfiguracja
    python hunt.py --config config/character.yaml    # własna konfiguracja
    python hunt.py --dry-run                          # sprawdź config bez uruchamiania bota
    python hunt.py --manual                           # tryb manualny (Easybot-style)

Skróty klawiszowe podczas polowania:
    CTRL+P — pauza / wznowienie
    CTRL+Q — zatrzymanie i raport końcowy
    CTRL+H — ręczny heal
    CTRL+A — toggle auto-attack
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML nie jest zainstalowany. Uruchom: pip install pyyaml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(level_str: str, log_file: Optional[str]) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        handlers=handlers,
    )


log = logging.getLogger("hunt")

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = Path("config/character.yaml")


def load_config(path: Path) -> dict:
    if not path.exists():
        log.error(f"Brak pliku konfiguracji: {path}")
        log.error("Stwórz plik config/character.yaml lub podaj ścieżkę przez --config")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Walidacja kluczowych pól
    required = [("character", "level"), ("hunting", "location"), ("spells", "heal")]
    for section, key in required:
        if section not in cfg or key not in cfg.get(section, {}):
            log.error(f"Brak wymaganego pola w konfiguracji: [{section}].{key}")
            sys.exit(1)

    return cfg


def cfg_get(cfg: dict, *keys, default=None):
    """Bezpieczny dostęp do zagnieżdżonego klucza."""
    val = cfg
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return val


# ---------------------------------------------------------------------------
# Session stats tracker
# ---------------------------------------------------------------------------

class SessionStats:
    def __init__(self):
        self.start_time = datetime.now()
        self.ticks = 0
        self.heals_cast = 0
        self.attacks_sent = 0
        self.creatures_killed = 0
        self.loot_collected = 0
        self.deaths = 0
        self.paused_sec = 0.0
        self._pause_start: Optional[float] = None

    def pause(self):
        if self._pause_start is None:
            self._pause_start = time.time()

    def resume(self):
        if self._pause_start is not None:
            self.paused_sec += time.time() - self._pause_start
            self._pause_start = None

    @property
    def elapsed(self) -> timedelta:
        return datetime.now() - self.start_time

    @property
    def active_sec(self) -> float:
        return max(1.0, self.elapsed.total_seconds() - self.paused_sec)

    def report(self) -> str:
        elapsed_str = str(self.elapsed).split(".")[0]
        xp_h = int(self.creatures_killed * 200 * 3600 / self.active_sec)
        lines = [
            "",
            "=" * 60,
            "  RAPORT SESJI POLOWANIA",
            "=" * 60,
            f"  Czas aktywny : {elapsed_str}",
            f"  Ticków bota  : {self.ticks}",
            f"  Heale        : {self.heals_cast}",
            f"  Ataki        : {self.attacks_sent}",
            f"  Zabicia      : {self.creatures_killed}",
            f"  Loot         : {self.loot_collected}x",
            f"  Zgony        : {self.deaths}",
            f"  XP/h (szac.) : ~{xp_h:,}",
            "=" * 60,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# HealingController — korzysta z config spell
# ---------------------------------------------------------------------------

class HealingController:
    def __init__(self, heal_spell: str, heal_threshold: float, crit_threshold: float, use_potion: bool, potion_key: str):
        self.heal_spell = heal_spell
        self.heal_threshold = heal_threshold / 100.0
        self.crit_threshold = crit_threshold / 100.0
        self.use_potion = use_potion
        self.potion_key = potion_key
        self._last_heal = 0.0
        self._cooldown = 1.0

    def should_heal(self, hp_pct: float) -> bool:
        return hp_pct < self.heal_threshold and (time.time() - self._last_heal) > self._cooldown

    def is_critical(self, hp_pct: float) -> bool:
        return hp_pct < self.crit_threshold

    def get_heal_command(self) -> str:
        if self.use_potion:
            return self.potion_key
        return f"say {self.heal_spell}"

    def record_heal(self):
        self._last_heal = time.time()


# ---------------------------------------------------------------------------
# Anti-idle heartbeat
# ---------------------------------------------------------------------------

class AntiIdle:
    def __init__(self, interval_sec: int):
        self._interval = interval_sec
        self._last = time.time()

    def should_send(self) -> bool:
        return time.time() - self._last > self._interval

    def record(self):
        self._last = time.time()


# ---------------------------------------------------------------------------
# Main hunt loop
# ---------------------------------------------------------------------------

async def hunt_loop(cfg: dict, stats: SessionStats, stop_event: asyncio.Event, pause_event: asyncio.Event) -> None:
    """Główna pętla polowania."""
    from runner.hybrid_bot.bot_runner import BotConfig, HybridBotRunner
    from runner.hybrid_bot.screenshot_provider import ScreenshotProvider
    from runner.hybrid_bot.command_executor import CommandExecutor
    from runner.hybrid_bot.gameplay_engine import GameplayEngine, GameplayMode

    char = cfg.get("character", {})
    hunt = cfg.get("hunting", {})
    spells = cfg.get("spells", {})
    health = cfg.get("health", {})
    safety = cfg.get("safety", {})
    anti_idle_cfg = cfg.get("safety", {})

    # Healing controller
    healer = HealingController(
        heal_spell=spells.get("heal", "exura"),
        heal_threshold=health.get("heal_threshold", 60),
        crit_threshold=health.get("critical_threshold", 25),
        use_potion=health.get("use_potion", False),
        potion_key=health.get("potion_key", "F1"),
    )

    anti_idle = AntiIdle(safety.get("anti_idle_interval_sec", 600)) if safety.get("anti_idle", True) else None

    # Bot config
    tick_ms = cfg_get(cfg, "client", "tick_ms", default=100)
    bot_config = BotConfig(
        player_level=char.get("level", 50),
        use_llm=False,
        max_health_before_heal=health.get("heal_threshold", 60.0),
        critical_health=health.get("critical_threshold", 25.0),
        update_interval_ms=tick_ms,
        metrics_dir=Path(cfg_get(cfg, "logging", "metrics_dir", default="metrics")),
    )

    window_title = cfg_get(cfg, "client", "window_title", default="Tibia")
    screenshot_provider = ScreenshotProvider(window_title=window_title)
    command_executor = CommandExecutor()

    bot = HybridBotRunner(
        config=bot_config,
        screenshot_provider=screenshot_provider,
        command_executor=command_executor,
    )

    location = hunt.get("location", "Unknown")
    duration_min = hunt.get("duration_min", 0)
    deadline = time.time() + duration_min * 60 if duration_min > 0 else None

    # Set waypoints
    waypoints = hunt.get("waypoints", [])
    if waypoints:
        bot.set_waypoints([tuple(wp) for wp in waypoints])

    bot.start_hunting_location(location)

    log.info(f"[HUNT] START — {char.get('name', '?')} lvl {char.get('level')} | {location}")
    log.info(f"[HUNT] Spell: {spells.get('heal', 'exura')} przy {health.get('heal_threshold', 60)}% HP")
    if duration_min:
        log.info(f"[HUNT] Czas: {duration_min} min")
    else:
        log.info("[HUNT] Czas: bez limitu (CTRL+Q aby zatrzymać)")
    log.info("[HUNT] Pauza: CTRL+P | Stop: CTRL+Q")
    log.info("-" * 60)

    # Cast buffs at start
    for buff in spells.get("buffs", []):
        bname = buff.get("name", "")
        if bname:
            log.info(f"[BUFF] {bname}")
            command_executor.execute(f"say {bname}")
            await asyncio.sleep(0.5)

    last_status_print = time.time()

    while not stop_event.is_set():
        # Check deadline
        if deadline and time.time() > deadline:
            log.info("[HUNT] Limit czasu minął — kończę polowanie.")
            break

        # Pause check
        if pause_event.is_set():
            stats.pause()
            await asyncio.sleep(0.5)
            continue
        else:
            stats.resume()

        # Bot tick
        try:
            player_state = bot._get_player_state() if hasattr(bot, "_get_player_state") else {}
        except Exception:
            player_state = {}

        hp_pct = player_state.get("hp_percent", 100.0)

        # --- Healing ---
        if healer.is_critical(hp_pct / 100.0 if hp_pct > 1 else hp_pct):
            flee_dir_map = {"north": "numpad 8", "south": "numpad 2", "east": "numpad 6", "west": "numpad 4"}
            flee_cmd = flee_dir_map.get(safety.get("flee_direction", "west"), "numpad 4")
            log.warning(f"[CRIT] HP {hp_pct:.0f}% — uciekam! ({flee_cmd})")
            command_executor.execute(flee_cmd)
            await asyncio.sleep(0.3)

        if healer.should_heal(hp_pct / 100.0 if hp_pct > 1 else hp_pct):
            heal_cmd = healer.get_heal_command()
            log.info(f"[HEAL] {heal_cmd} (HP: {hp_pct:.0f}%)")
            command_executor.execute(heal_cmd)
            healer.record_heal()
            stats.heals_cast += 1

        # --- Bot tick ---
        try:
            await bot._tick()
        except Exception as e:
            log.debug(f"Tick error: {e}")

        # --- Anti-idle ---
        if anti_idle and anti_idle.should_send():
            command_executor.execute("numpad 8")
            await asyncio.sleep(0.1)
            command_executor.execute("numpad 2")
            anti_idle.record()
            log.debug("[ANTI-IDLE] ruch wysłany")

        stats.ticks += 1

        # --- Status print co 30s ---
        if time.time() - last_status_print > 30:
            elapsed_str = str(stats.elapsed).split(".")[0]
            log.info(
                f"[STATUS] {elapsed_str} | heale: {stats.heals_cast} | "
                f"ataki: {stats.attacks_sent} | HP: {hp_pct:.0f}%"
            )
            last_status_print = time.time()

        await asyncio.sleep(tick_ms / 1000.0)

    bot.stop()
    log.info("[HUNT] Bot zatrzymany.")


# ---------------------------------------------------------------------------
# Keyboard hook (pause/stop)
# ---------------------------------------------------------------------------

def _setup_hotkeys(stop_event: asyncio.Event, pause_event: asyncio.Event, loop: asyncio.AbstractEventLoop) -> None:
    """Rejestruje globalne skróty klawiszowe CTRL+Q / CTRL+P."""
    try:
        from pynput import keyboard

        paused = [False]

        def on_press(key):
            try:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                    return
            except AttributeError:
                pass

        pressed = set()

        def on_press(key):
            pressed.add(key)
            ctrl = keyboard.Key.ctrl_l in pressed or keyboard.Key.ctrl_r in pressed

            if ctrl:
                try:
                    ch = key.char.lower() if hasattr(key, "char") and key.char else None
                    if ch == "q":
                        log.info("[HOTKEY] CTRL+Q — zatrzymuję bota...")
                        loop.call_soon_threadsafe(stop_event.set)
                    elif ch == "p":
                        if paused[0]:
                            log.info("[HOTKEY] CTRL+P — wznawianie...")
                            loop.call_soon_threadsafe(pause_event.clear)
                            paused[0] = False
                        else:
                            log.info("[HOTKEY] CTRL+P — pauza...")
                            loop.call_soon_threadsafe(pause_event.set)
                            paused[0] = True
                except Exception:
                    pass

        def on_release(key):
            pressed.discard(key)

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()

    except ImportError:
        log.warning("[HOTKEY] pynput niedostępny — skróty CTRL+Q/P nie działają. Użyj CTRL+C.")


# ---------------------------------------------------------------------------
# Dry-run validator
# ---------------------------------------------------------------------------

def dry_run(cfg: dict) -> None:
    char = cfg.get("character", {})
    hunt = cfg.get("hunting", {})
    spells = cfg.get("spells", {})
    health = cfg.get("health", {})
    safety = cfg.get("safety", {})

    print()
    print("=" * 60)
    print("  CTOA BOT — WERYFIKACJA KONFIGURACJI")
    print("=" * 60)
    print(f"  Postać    : {char.get('name', '?')} [{char.get('vocation', '?')}] lvl {char.get('level', '?')}")
    print(f"  Klient    : {cfg_get(cfg, 'client', 'window_title', default='Tibia')}")
    print()
    print(f"  Lokacja   : {hunt.get('location', '?')}")
    duration = hunt.get('duration_min', 0)
    print(f"  Czas      : {'bez limitu' if not duration else str(duration) + ' min'}")
    targets = hunt.get("targets", [])
    print(f"  Stwory    : {', '.join(t['name'] for t in targets) if targets else '(brak — random)'}")
    print()
    print(f"  Heal spell: {spells.get('heal', '?')} przy {health.get('heal_threshold', 60)}% HP")
    attack = spells.get("attack", "")
    print(f"  Atak spell: {attack if attack else '(melee)'}")
    buffs = spells.get("buffs", [])
    print(f"  Buffy     : {', '.join(b['name'] for b in buffs) if buffs else '(brak)'}")
    print()
    print(f"  Flee przy : {health.get('critical_threshold', 25)}% HP")
    print(f"  Anti-idle : {'Tak' if safety.get('anti_idle', True) else 'Nie'}")
    print()

    whitelist = cfg_get(cfg, "hunting", "loot", "whitelist", default=[])
    print(f"  Loot WL   : {', '.join(whitelist[:5])}{'...' if len(whitelist) > 5 else ''}")
    print()
    print("  [OK] Konfiguracja poprawna. Uruchom bez --dry-run aby zacząć.")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="CTOA Bot — Autonomiczne polowanie",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python hunt.py                               # domyślna konfiguracja
  python hunt.py --config config/character.yaml
  python hunt.py --dry-run                     # weryfikacja bez uruchamiania
  python hunt.py --manual                      # tryb manualny (Easybot)
  python hunt.py --duration 30                 # override czasu (minuty)
        """,
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Ścieżka do pliku konfiguracji")
    parser.add_argument("--dry-run", action="store_true", help="Sprawdź konfigurację bez uruchamiania bota")
    parser.add_argument("--manual", action="store_true", help="Tryb manualny (interaktywny jak Easybot)")
    parser.add_argument("--duration", type=int, default=None, help="Override czasu polowania (minuty)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    # Setup logging
    log_cfg = cfg.get("logging", {})
    _setup_logging(log_cfg.get("level", "INFO"), log_cfg.get("log_file"))

    if args.dry_run:
        dry_run(cfg)
        return 0

    if args.duration is not None:
        cfg.setdefault("hunting", {})["duration_min"] = args.duration

    if args.manual:
        # Tryb manualny — Easybot style
        log.info("[MODE] Tryb manualny — użyj strzałek i CTRL+H/A/Q")
        from runner.hybrid_bot.command_executor import CommandExecutor
        from runner.hybrid_bot.interactive_mode import InteractiveMode
        executor = CommandExecutor()
        interactive = InteractiveMode(executor.execute)
        asyncio.run(interactive.run())
        return 0

    # Autonomous mode
    print()
    print("=" * 60)
    print("  CTOA BOT — AUTONOMICZNE POLOWANIE")
    print("=" * 60)
    print(f"  Konfiguracja: {args.config}")
    print(f"  Postać: {cfg_get(cfg, 'character', 'name')} lvl {cfg_get(cfg, 'character', 'level')}")
    print(f"  Lokacja: {cfg_get(cfg, 'hunting', 'location')}")
    print()
    print("  Skróty: CTRL+P = pauza | CTRL+Q = stop")
    print("=" * 60)
    print()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop_event = asyncio.Event()
    pause_event = asyncio.Event()

    # SIGINT (CTRL+C) → stop gracefully
    def _sigint_handler(sig, frame):
        log.info("[SIGINT] CTRL+C — zatrzymuję bota...")
        loop.call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGINT, _sigint_handler)

    _setup_hotkeys(stop_event, pause_event, loop)

    stats = SessionStats()

    try:
        loop.run_until_complete(hunt_loop(cfg, stats, stop_event, pause_event))
    except Exception as e:
        log.error(f"Błąd krytyczny: {e}", exc_info=True)
    finally:
        loop.close()

    # --- Raport końcowy ---
    print(stats.report())

    if log_cfg.get("session_report", True):
        report_path = Path(log_cfg.get("log_file", "logs/hunt.log")).parent / "session_report.json"
        report_data = {
            "session_start": stats.start_time.isoformat(),
            "elapsed_sec": stats.elapsed.total_seconds(),
            "heals": stats.heals_cast,
            "attacks": stats.attacks_sent,
            "kills": stats.creatures_killed,
            "loot": stats.loot_collected,
            "deaths": stats.deaths,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False))
        log.info(f"[REPORT] Zapisano: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
