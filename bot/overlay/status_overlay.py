"""Simple always-on-top status overlay for bot live state.

Run:
  python -m bot.overlay.status_overlay
"""

from __future__ import annotations

import json
import logging
import os
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from bot.config.runtime_profile import (
    active_profile_name,
    config_path,
    get_bool,
    get_int,
    get_str,
    reload_config,
    save_profile_values,
)
from bot.runtime.live_state import get_live_state_path
from runner import process_safety

logger = logging.getLogger(__name__)

_BG = "#111827"
_FG = "#E5E7EB"
_ACCENT_HP = "#22C55E"
_ACCENT_MP = "#3B82F6"
_ACCENT_TARGET = "#EF4444"
_ACCENT_STALE = "#F59E0B"
_ACCENT_LIVE = "#10B981"
_STALE_AFTER_SEC = 2.5


class RailSwitch(tk.Canvas):
    """Compact red/green rail switch with moving knob."""

    def __init__(
        self,
        master: tk.Widget,
        *,
        initial: bool,
        command,
        width: int = 58,
        height: int = 24,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=_BG,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self._width = width
        self._height = height
        self._command = command
        self._state = bool(initial)
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def set_state(self, enabled: bool) -> None:
        self._state = bool(enabled)
        self._draw()

    def _on_click(self, _event=None) -> None:
        self._state = not self._state
        self._draw()
        self._command(self._state)

    def _draw(self) -> None:
        self.delete("all")
        pad = 2
        h = self._height - 2 * pad
        radius = h / 2
        left = pad
        top = pad
        right = self._width - pad
        bottom = self._height - pad

        rail_color = "#16A34A" if self._state else "#B91C1C"
        rail_active = "#15803D" if self._state else "#991B1B"

        self.create_oval(
            left, top, left + 2 * radius, bottom, fill=rail_color, outline=rail_active
        )
        self.create_rectangle(
            left + radius,
            top,
            right - radius,
            bottom,
            fill=rail_color,
            outline=rail_active,
        )
        self.create_oval(
            right - 2 * radius, top, right, bottom, fill=rail_color, outline=rail_active
        )

        knob_d = h - 4
        knob_y = top + 2
        if self._state:
            knob_x = right - knob_d - 2
        else:
            knob_x = left + 2
        self.create_oval(
            knob_x,
            knob_y,
            knob_x + knob_d,
            knob_y + knob_d,
            fill="#F9FAFB",
            outline="#D1D5DB",
        )


class OverlayApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.state_path: Path = get_live_state_path()
        self._project_root = Path(__file__).resolve().parents[2]
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._update_ms = get_int("BOT_OVERLAY_REFRESH_MS", 250)
        self._bot_proc: process_safety.TrustedProcess | None = None
        self._last_state_ts = 0.0
        self._module_switches: dict[str, RailSwitch] = {}

        self.root.title("CTOAi Overlay")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg=_BG)
        self.root.geometry("450x500+18+42")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        frame = tk.Frame(root, bg=_BG, padx=12, pady=10)
        frame.pack(fill="both", expand=True)

        header = tk.Frame(frame, bg=_BG)
        header.pack(fill="x", pady=(0, 8))

        self.status = tk.StringVar(value="STATUS: WAITING")
        self.status_label = tk.Label(
            header,
            textvariable=self.status,
            fg=_ACCENT_STALE,
            bg=_BG,
            font=("Consolas", 10, "bold"),
        )
        self.status_label.pack(side="left")

        self.pin = tk.BooleanVar(value=True)
        tk.Checkbutton(
            header,
            text="PIN",
            variable=self.pin,
            command=self._toggle_pin,
            fg=_FG,
            bg=_BG,
            selectcolor=_BG,
            activebackground=_BG,
            activeforeground=_FG,
            font=("Consolas", 9),
            bd=0,
            highlightthickness=0,
        ).pack(side="right")

        title = tk.Label(
            frame,
            text="CTOAi Overlay",
            fg="#D1D5DB",
            bg=_BG,
            font=("Consolas", 11, "bold"),
        )
        title.pack(anchor="w", pady=(0, 6))

        # Drag overlay by clicking the title/header.
        for drag_src in (header, title, self.status_label):
            drag_src.bind("<ButtonPress-1>", self._start_drag)
            drag_src.bind("<B1-Motion>", self._drag)

        self.hp = tk.StringVar(value="HP: --")
        self.mp = tk.StringVar(value="MP: --")
        self.target = tk.StringVar(value="Target: --")
        self.action = tk.StringVar(value="Action: --")
        self.tick = tk.StringVar(value="Tick: -- ms")

        tk.Label(
            frame,
            textvariable=self.hp,
            fg=_ACCENT_HP,
            bg=_BG,
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            textvariable=self.mp,
            fg=_ACCENT_MP,
            bg=_BG,
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            textvariable=self.target,
            fg=_ACCENT_TARGET,
            bg=_BG,
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame, textvariable=self.action, fg=_FG, bg=_BG, font=("Consolas", 11)
        ).pack(anchor="w", pady=(8, 0))
        tk.Label(
            frame, textvariable=self.tick, fg="#9CA3AF", bg=_BG, font=("Consolas", 10)
        ).pack(anchor="w")

        controls = tk.Frame(frame, bg=_BG)
        controls.pack(fill="x", pady=(10, 0))

        self.bot_status = tk.StringVar(value="Bot: STOPPED")
        tk.Label(
            controls,
            textvariable=self.bot_status,
            fg="#9CA3AF",
            bg=_BG,
            font=("Consolas", 10),
        ).pack(anchor="w")

        control_row = tk.Frame(controls, bg=_BG)
        control_row.pack(fill="x", pady=(6, 0))
        tk.Button(
            control_row, text="Start Bot", command=self._start_bot, width=12
        ).pack(side="left")
        tk.Button(control_row, text="Stop Bot", command=self._stop_bot, width=12).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(
            control_row, text="Reload Config", command=self._reload_config, width=12
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            control_row, text="Macro Pad", command=self._open_macro_pad, width=12
        ).pack(side="left", padx=(8, 0))

        modules = tk.LabelFrame(frame, text="Modules", bg=_BG, fg=_FG, padx=8, pady=5)
        modules.pack(fill="x", pady=(10, 0))

        self._render_module_row(
            modules, "Auto Follow", "BOT_AUTO_FOLLOW", self._module_auto_follow()
        )
        self._render_module_row(
            modules,
            "Spell Rotation",
            "BOT_SPELL_ROTATION_ENABLED",
            self._module_spell_rotation(),
        )
        self._render_module_row(
            modules,
            "Input Focus Guard",
            "BOT_INPUT_ONLY_WHEN_TIBIA_ACTIVE",
            self._module_focus_guard(),
        )

        quick = tk.Frame(modules, bg=_BG)
        quick.pack(fill="x", pady=(6, 0))
        tk.Label(quick, text="Follow Key", fg=_FG, bg=_BG, font=("Consolas", 9)).pack(
            side="left"
        )
        self.var_follow_key = tk.StringVar(value=get_str("BOT_FOLLOW_KEY", "f12"))
        tk.Entry(quick, textvariable=self.var_follow_key, width=8).pack(
            side="left", padx=(6, 0)
        )
        tk.Button(quick, text="Save Key", command=self._save_follow_key, width=10).pack(
            side="left", padx=(8, 0)
        )

        timings = tk.Frame(modules, bg=_BG)
        timings.pack(fill="x", pady=(5, 0))
        self.var_follow_interval = tk.StringVar(
            value=str(get_int("BOT_AUTO_FOLLOW_INTERVAL_MS", 1200))
        )
        self.var_follow_stuck = tk.StringVar(
            value=str(get_int("BOT_AUTO_FOLLOW_STUCK_MS", 900))
        )
        self.var_follow_refresh = tk.StringVar(
            value=str(get_int("BOT_AUTO_FOLLOW_REFRESH_MS", 5000))
        )
        tk.Label(timings, text="I", fg=_FG, bg=_BG, font=("Consolas", 9)).pack(
            side="left"
        )
        tk.Entry(timings, textvariable=self.var_follow_interval, width=6).pack(
            side="left", padx=(3, 8)
        )
        tk.Label(timings, text="S", fg=_FG, bg=_BG, font=("Consolas", 9)).pack(
            side="left"
        )
        tk.Entry(timings, textvariable=self.var_follow_stuck, width=6).pack(
            side="left", padx=(3, 8)
        )
        tk.Label(timings, text="R", fg=_FG, bg=_BG, font=("Consolas", 9)).pack(
            side="left"
        )
        tk.Entry(timings, textvariable=self.var_follow_refresh, width=6).pack(
            side="left", padx=(3, 8)
        )
        tk.Button(
            timings, text="Save Timings", command=self._save_follow_timing, width=12
        ).pack(side="left")

        diag = tk.LabelFrame(frame, text="Diagnostics", bg=_BG, fg=_FG, padx=8, pady=6)
        diag.pack(fill="x", pady=(10, 0))

        self.diag_profile = tk.StringVar(value="Profile: --")
        self.diag_config = tk.StringVar(value="Config: --")
        self.diag_freshness = tk.StringVar(value="Freshness: --")
        self.diag_mode = tk.StringVar(value="Mode: --")
        self.diag_process = tk.StringVar(value="Process: --")

        tk.Label(
            diag,
            textvariable=self.diag_profile,
            fg="#9CA3AF",
            bg=_BG,
            font=("Consolas", 9),
        ).pack(anchor="w")
        tk.Label(
            diag,
            textvariable=self.diag_config,
            fg="#9CA3AF",
            bg=_BG,
            font=("Consolas", 9),
        ).pack(anchor="w")
        tk.Label(
            diag,
            textvariable=self.diag_freshness,
            fg="#9CA3AF",
            bg=_BG,
            font=("Consolas", 9),
        ).pack(anchor="w")
        tk.Label(
            diag,
            textvariable=self.diag_mode,
            fg="#9CA3AF",
            bg=_BG,
            font=("Consolas", 9),
        ).pack(anchor="w")
        tk.Label(
            diag,
            textvariable=self.diag_process,
            fg="#9CA3AF",
            bg=_BG,
            font=("Consolas", 9),
        ).pack(anchor="w")

        alpha_row = tk.Frame(frame, bg=_BG)
        alpha_row.pack(fill="x", pady=(8, 0))
        tk.Label(
            alpha_row, text="Opacity", fg="#9CA3AF", bg=_BG, font=("Consolas", 9)
        ).pack(side="left")
        alpha_scale = tk.Scale(
            alpha_row,
            from_=45,
            to=100,
            orient="horizontal",
            showvalue=False,
            resolution=1,
            length=150,
            command=self._set_alpha,
            fg=_FG,
            bg=_BG,
            troughcolor="#374151",
            highlightthickness=0,
            bd=0,
        )
        alpha_scale.set(90)
        alpha_scale.pack(side="right")

    def refresh(self) -> None:
        data = self._read_state()
        stale = True
        if data is not None:
            hp = float(data.get("hp_pct", 0.0))
            mp = float(data.get("mp_pct", 0.0))
            target = int(data.get("target_hp_pct", 0))
            action = str(data.get("action", "idle"))
            result = str(data.get("action_result", "ok"))
            tick_ms = int(data.get("tick_ms", 0))
            ts = float(data.get("timestamp", 0.0) or 0.0)
            self._last_state_ts = ts
            stale = (time.time() - ts) > _STALE_AFTER_SEC if ts > 0.0 else True

            self.hp.set(f"HP: {hp:5.1f}%")
            self.mp.set(f"MP: {mp:5.1f}%")
            self.target.set(f"Target: {target:3d}%")
            self.action.set(f"Action: {action} ({result})")
            self.tick.set(f"Tick: {tick_ms} ms")

        if stale:
            self.status.set("STATUS: STALE")
            self.status_label.configure(fg=_ACCENT_STALE)
        else:
            self.status.set("STATUS: LIVE")
            self.status_label.configure(fg=_ACCENT_LIVE)

        self._refresh_diagnostics()
        self.root.after(self._update_ms, self.refresh)

    def _toggle_pin(self) -> None:
        self.root.attributes("-topmost", bool(self.pin.get()))

    def _set_alpha(self, value: str) -> None:
        try:
            self.root.attributes("-alpha", max(0.45, min(1.0, int(value) / 100.0)))
        except Exception:
            return

    def _start_drag(self, event) -> None:
        self._drag_offset_x = event.x_root - self.root.winfo_x()
        self._drag_offset_y = event.y_root - self.root.winfo_y()

    def _drag(self, event) -> None:
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    def _reload_config(self) -> None:
        reload_config()
        self._update_ms = get_int("BOT_OVERLAY_REFRESH_MS", 250)
        self.var_follow_key.set(get_str("BOT_FOLLOW_KEY", "f12"))
        self.var_follow_interval.set(str(get_int("BOT_AUTO_FOLLOW_INTERVAL_MS", 1200)))
        self.var_follow_stuck.set(str(get_int("BOT_AUTO_FOLLOW_STUCK_MS", 900)))
        self.var_follow_refresh.set(str(get_int("BOT_AUTO_FOLLOW_REFRESH_MS", 5000)))
        self._sync_module_buttons()
        self._refresh_diagnostics()

    def _render_module_row(
        self, parent: tk.Widget, label: str, key: str, enabled: bool
    ) -> None:
        row = tk.Frame(parent, bg=_BG)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, fg=_FG, bg=_BG, font=("Consolas", 10, "bold")).pack(
            side="left"
        )
        sw = RailSwitch(
            row,
            initial=enabled,
            command=lambda state, k=key: self._toggle_module(k, state),
        )
        sw.pack(side="right")
        self._module_switches[key] = sw
        self._paint_module_switch(key, enabled)

    def _paint_module_switch(self, key: str, enabled: bool) -> None:
        sw = self._module_switches.get(key)
        if not sw:
            return
        sw.set_state(enabled)

    def _module_auto_follow(self) -> bool:
        return get_bool("BOT_AUTO_FOLLOW", False)

    def _module_spell_rotation(self) -> bool:
        return get_bool("BOT_SPELL_ROTATION_ENABLED", True)

    def _module_focus_guard(self) -> bool:
        return get_bool("BOT_INPUT_ONLY_WHEN_TIBIA_ACTIVE", True)

    def _sync_module_buttons(self) -> None:
        self._paint_module_switch("BOT_AUTO_FOLLOW", self._module_auto_follow())
        self._paint_module_switch(
            "BOT_SPELL_ROTATION_ENABLED", self._module_spell_rotation()
        )
        self._paint_module_switch(
            "BOT_INPUT_ONLY_WHEN_TIBIA_ACTIVE", self._module_focus_guard()
        )

    def _toggle_module(self, key: str, desired_state: bool) -> None:
        profile = active_profile_name()
        try:
            value = bool(desired_state)

            save_profile_values(profile, {key: value})
            reload_config()
            self._sync_module_buttons()
            self.bot_status.set(f"Bot: module saved ({key})")
        except Exception as exc:
            self._sync_module_buttons()
            messagebox.showerror("Save Failed", str(exc))

    def _save_follow_key(self) -> None:
        profile = active_profile_name()
        value = self.var_follow_key.get().strip().lower() or "f12"
        try:
            save_profile_values(profile, {"BOT_FOLLOW_KEY": value})
            reload_config()
            self.bot_status.set("Bot: follow key saved")
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))

    def _save_follow_timing(self) -> None:
        profile = active_profile_name()
        try:
            updates = {
                "BOT_AUTO_FOLLOW_INTERVAL_MS": int(
                    self.var_follow_interval.get().strip()
                ),
                "BOT_AUTO_FOLLOW_STUCK_MS": int(self.var_follow_stuck.get().strip()),
                "BOT_AUTO_FOLLOW_REFRESH_MS": int(
                    self.var_follow_refresh.get().strip()
                ),
            }
        except ValueError:
            messagebox.showerror("Invalid Settings", "I/S/R values must be integers.")
            return

        try:
            save_profile_values(profile, updates)
            reload_config()
            self.bot_status.set("Bot: follow timings saved")
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))

    def _start_bot(self) -> None:
        if self._bot_proc is not None and self._bot_proc.poll() is None:
            self.bot_status.set(f"Bot: RUNNING (pid={self._bot_proc.pid})")
            return

        try:
            creation_flags = (
                process_safety.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            )
            python_bin = process_safety.resolve_python()
            self._bot_proc = process_safety.start_trusted(
                [python_bin, "-m", "bot.main"],
                cwd=str(self._project_root),
                env=os.environ.copy(),
                creationflags=creation_flags,
            )
            self.bot_status.set(f"Bot: RUNNING (pid={self._bot_proc.pid})")
        except (
            OSError,
            process_safety.ExecutableUnavailableError,
            process_safety.ProcessExecutionError,
        ) as exc:
            self.bot_status.set("Bot: START FAILED")
            messagebox.showerror("Start Bot", str(exc))

    def _stop_bot(self) -> None:
        if self._bot_proc is None or self._bot_proc.poll() is not None:
            self.bot_status.set("Bot: STOPPED")
            return

        try:
            self._bot_proc.terminate()
            self._bot_proc.wait(timeout=3)
        except process_safety.ProcessTimeoutExpired:
            try:
                self._bot_proc.kill()
            except OSError as exc:
                logger.warning("bot process kill failed: %s", exc)
        except (OSError, process_safety.ProcessExecutionError) as exc:
            logger.warning("bot process stop failed: %s", exc)
        self.bot_status.set("Bot: STOPPED")

    def _open_macro_pad(self) -> None:
        creation_flags = (
            process_safety.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        )

        try:
            process_safety.start_trusted(
                [process_safety.resolve_python(), "-m", "bot.overlay.macro_overlay"],
                cwd=str(self._project_root),
                env=os.environ.copy(),
                creationflags=creation_flags,
            )
            self.bot_status.set("Bot: macro pad opened")
        except (
            OSError,
            process_safety.ExecutableUnavailableError,
            process_safety.ProcessExecutionError,
        ) as exc:
            messagebox.showerror("Macro Pad", str(exc))

    def _refresh_diagnostics(self) -> None:
        self.diag_profile.set(f"Profile: {active_profile_name()}")
        self.diag_config.set(f"Config: {config_path()}")
        self.diag_mode.set(
            f"Mode: {get_str('BOT_ACTION_MODE', 'full').strip().lower() or 'full'}"
        )

        if self._last_state_ts > 0.0:
            age = max(0.0, time.time() - self._last_state_ts)
            self.diag_freshness.set(f"Freshness: {age:.1f}s ago")
        else:
            self.diag_freshness.set("Freshness: no live state yet")

        if self._bot_proc is not None and self._bot_proc.poll() is None:
            process_line = f"Process: bot.main running (pid={self._bot_proc.pid})"
        else:
            process_line = "Process: bot.main stopped"
        self.diag_process.set(process_line)
        self.bot_status.set(process_line.replace("Process: ", "Bot: "))

    def _on_close(self) -> None:
        self._stop_bot()
        self.root.destroy()

    def _read_state(self) -> dict | None:
        try:
            if not self.state_path.exists():
                return None
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.debug("overlay live-state read failed: %s", exc)
            return None


def run() -> None:
    root = tk.Tk()
    app = OverlayApp(root)
    app.refresh()
    root.mainloop()


if __name__ == "__main__":
    run()
