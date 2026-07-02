"""Macro studio overlay for composing key sequences and cooldown-based macros.

Run:
  python -m bot.overlay.macro_overlay
"""
from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox

from runner.hybrid_bot.command_executor import CommandExecutor

_BG = "#0f172a"
_PANEL = "#111827"
_PANEL_2 = "#1f2937"
_FG = "#e5e7eb"
_MUTED = "#94a3b8"
_ACCENT = "#38bdf8"
_GOOD = "#22c55e"
_WARN = "#f59e0b"
_BAD = "#ef4444"

_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _ROOT / "config" / "bot_macro_pad.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_config() -> dict:
    return {
        "version": 1,
        "updated_at": _now_iso(),
        "quick_presets": [
            {
                "name": "Kamil Full Rota",
                "group": "kamil",
                "cooldown_ms": 2800,
                "steps": "key f2; wait 110; key f3; wait 110; key f4; wait 110; key f5",
            },
            {
                "name": "Kamil Opener",
                "group": "kamil",
                "cooldown_ms": 2200,
                "steps": "key f2; wait 110; key f3; wait 110; key f4",
            },
            {
                "name": "Kamil Burst",
                "group": "kamil",
                "cooldown_ms": 1800,
                "steps": "key f2; wait 110; key f3",
            },
            {
                "name": "Kamil Heal",
                "group": "kamil",
                "cooldown_ms": 1200,
                "steps": "key f1",
            },
        ],
        "macros": [
            {
                "id": "macro-1",
                "name": "Heal chain",
                "trigger": "F1",
                "group": "heal",
                "cooldown_ms": 2200,
                "primary": "key f1; wait 90; key f2",
                "fallback": "key f3",
            },
            {
                "id": "macro-2",
                "name": "Burst combo",
                "trigger": "F2",
                "group": "burst",
                "cooldown_ms": 3000,
                "primary": "say exori gran; wait 120; key f5",
                "fallback": "say exori",
            },
            {
                "id": "macro-3",
                "name": "Potion chain",
                "trigger": "F3",
                "group": "potion",
                "cooldown_ms": 1200,
                "primary": "key f1; wait 70; key f2; wait 70; key f4",
                "fallback": "key f4",
            },
        ],
    }


def _ensure_defaults(data: dict) -> dict:
    if not isinstance(data, dict):
        return _default_config()

    defaults = _default_config()
    if not isinstance(data.get("quick_presets"), list) or not data.get("quick_presets"):
        data["quick_presets"] = defaults["quick_presets"]
    if not isinstance(data.get("macros"), list) or not data.get("macros"):
        data["macros"] = defaults["macros"]
    return data


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = _default_config()
        _CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload

    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return _ensure_defaults(data)


def _save_config(data: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now_iso()
    _CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_macro(entry: dict, index: int) -> dict:
    macro = dict(entry) if isinstance(entry, dict) else {}
    macro.setdefault("id", f"macro-{index + 1}")
    macro.setdefault("name", f"Macro {index + 1}")
    macro.setdefault("trigger", f"F{index + 1}")
    macro.setdefault("group", "")
    macro.setdefault("cooldown_ms", 1500)
    macro.setdefault("primary", "")
    macro.setdefault("fallback", "")
    macro.setdefault("notes", "")
    return macro


def _normalize_preset(entry: dict, index: int) -> dict:
    preset = dict(entry) if isinstance(entry, dict) else {}
    preset.setdefault("id", f"preset-{index + 1}")
    preset.setdefault("name", f"Preset {index + 1}")
    preset.setdefault("group", "preset")
    preset.setdefault("cooldown_ms", 1500)
    preset.setdefault("steps", "")
    return preset


def _pretty_age(remaining: float) -> str:
    if remaining <= 0:
        return "READY"
    if remaining < 1:
        return "<1s"
    return f"{remaining:.1f}s"


def _parse_steps(text: str) -> list[str]:
    steps: list[str] = []
    for raw in text.split(";"):
        step = raw.strip()
        if step:
            steps.append(step)
    return steps


def _normalize_step(step: str) -> str:
    text = step.strip()
    if not text:
        return text
    if " " not in text and "+" not in text:
        return f"key {text}"
    return text


class MacroOverlayApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CTOA Macro Studio")
        self.root.geometry("980x560+80+70")
        self.root.configure(bg=_BG)
        self.root.minsize(920, 520)

        self._data = _load_config()
        self._presets = [_normalize_preset(p, i) for i, p in enumerate(self._data.get("quick_presets", []))]
        self._macros = [_normalize_macro(m, i) for i, m in enumerate(self._data.get("macros", []))]
        self._last_fire: dict[str, float] = {}
        self._selected_index = 0
        self._command_executor = CommandExecutor()
        self._fire_lock = threading.Lock()
        self._test_mode = tk.BooleanVar(value=False)

        outer = tk.Frame(root, bg=_BG, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=_BG)
        header.pack(fill="x")
        tk.Label(header, text="Macro Studio", fg=_FG, bg=_BG, font=("Consolas", 16, "bold")).pack(anchor="w")
        tk.Label(
            header,
            text="Jedno klikniecie = sekwencja krokow. Group = wspolny cooldown dla wariantow.",
            fg=_MUTED,
            bg=_BG,
            font=("Consolas", 9),
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(outer, bg=_BG)
        body.pack(fill="both", expand=True, pady=(12, 0))

        left = tk.Frame(body, bg=_PANEL, bd=1, relief="solid", padx=8, pady=8)
        left.pack(side="left", fill="y")
        right = tk.Frame(body, bg=_PANEL, bd=1, relief="solid", padx=10, pady=10)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        tk.Label(left, text="Slots", fg=_FG, bg=_PANEL, font=("Consolas", 11, "bold")).pack(anchor="w")
        self.slot_list = tk.Listbox(
            left,
            height=18,
            width=26,
            bg=_PANEL_2,
            fg=_FG,
            selectbackground=_ACCENT,
            selectforeground="#081120",
            highlightthickness=0,
            relief="flat",
            activestyle="none",
            font=("Consolas", 10),
        )
        self.slot_list.pack(fill="y", expand=False, pady=(8, 8))
        self.slot_list.bind("<<ListboxSelect>>", self._on_select)

        presets = tk.LabelFrame(left, text="Quick Presets", bg=_PANEL, fg=_FG, padx=6, pady=6)
        presets.pack(fill="x", pady=(0, 8))
        self._build_presets(presets)

        btn_row = tk.Frame(left, bg=_PANEL)
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="New", command=self._new_macro, width=7).pack(side="left")
        tk.Button(btn_row, text="Dup", command=self._duplicate_macro, width=7).pack(side="left", padx=(6, 0))
        tk.Button(btn_row, text="Del", command=self._delete_macro, width=7).pack(side="left", padx=(6, 0))

        self.status = tk.StringVar(value="Ready")
        tk.Label(left, textvariable=self.status, fg=_MUTED, bg=_PANEL, font=("Consolas", 9)).pack(anchor="w", pady=(10, 0))

        self.name_var = tk.StringVar()
        self.trigger_var = tk.StringVar()
        self.group_var = tk.StringVar()
        self.cooldown_var = tk.StringVar()
        self.primary_var = tk.StringVar()
        self.fallback_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.preview_var = tk.StringVar(value="Preview: --")
        self.timer_var = tk.StringVar(value="Cooldown: --")

        self._build_editor(right)
        self._build_help(right)
        self._refresh_list()
        self._load_selected(0)
        self._tick()

    def _build_editor(self, parent: tk.Widget) -> None:
        title = tk.Label(parent, text="Editor", fg=_FG, bg=_PANEL, font=("Consolas", 13, "bold"))
        title.pack(anchor="w")

        grid = tk.Frame(parent, bg=_PANEL)
        grid.pack(fill="x", pady=(10, 0))

        self._field(grid, "Name", self.name_var, 0, 0, 36)
        self._field(grid, "Trigger", self.trigger_var, 0, 1, 14)
        self._field(grid, "Group", self.group_var, 1, 0, 20)
        self._field(grid, "CD ms", self.cooldown_var, 1, 1, 14)
        self._field(grid, "Notes", self.notes_var, 2, 0, 56, colspan=2)
        self._field(grid, "Primary", self.primary_var, 3, 0, 56, colspan=2)
        self._field(grid, "Fallback", self.fallback_var, 4, 0, 56, colspan=2)

        meta = tk.Frame(parent, bg=_PANEL)
        meta.pack(fill="x", pady=(10, 0))
        tk.Label(meta, textvariable=self.preview_var, fg=_GOOD, bg=_PANEL, font=("Consolas", 9)).pack(anchor="w")
        tk.Label(meta, textvariable=self.timer_var, fg=_WARN, bg=_PANEL, font=("Consolas", 9)).pack(anchor="w")
        tk.Label(
            meta,
            text="Syntax: key f1; wait 120; combo ctrl+shift+l; say exura",
            fg=_MUTED,
            bg=_PANEL,
            font=("Consolas", 9),
        ).pack(anchor="w", pady=(2, 0))

        log_box = tk.LabelFrame(parent, text="Log", bg=_PANEL, fg=_FG, padx=8, pady=8)
        log_box.pack(fill="both", expand=True, pady=(12, 0))
        self.log_text = tk.Text(
            log_box,
            height=8,
            bg=_PANEL_2,
            fg=_FG,
            insertbackground=_FG,
            relief="flat",
            wrap="word",
            font=("Consolas", 9),
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

        actions = tk.Frame(parent, bg=_PANEL)
        actions.pack(fill="x", pady=(12, 0))
        tk.Button(actions, text="Save Slot", command=self._save_current, width=14).pack(side="left")
        tk.Button(actions, text="Fire Now", command=self._fire_current, width=14).pack(side="left", padx=(8, 0))
        tk.Button(actions, text="Reset CD", command=self._reset_current_cd, width=14).pack(side="left", padx=(8, 0))
        tk.Button(actions, text="Reload", command=self._reload, width=14).pack(side="left", padx=(8, 0))
        tk.Checkbutton(
            actions,
            text="Test mode",
            variable=self._test_mode,
            fg=_FG,
            bg=_PANEL,
            selectcolor=_PANEL,
            activebackground=_PANEL,
            activeforeground=_FG,
            bd=0,
            highlightthickness=0,
            font=("Consolas", 9),
        ).pack(side="right")

    def _build_help(self, parent: tk.Widget) -> None:
        help_box = tk.LabelFrame(parent, text="CD logic", bg=_PANEL, fg=_FG, padx=8, pady=8)
        help_box.pack(fill="x", pady=(12, 0))
        lines = [
            "• primary = normal sekwencja",
            "• fallback = gdy slot ma wspolny CD albo chcesz awaryjny wariant",
            "• group = wspolny cooldown dla kilku slotow",
            "• trigger to etykieta, nie globalny hook",
        ]
        for line in lines:
            tk.Label(help_box, text=line, fg=_MUTED, bg=_PANEL, font=("Consolas", 9)).pack(anchor="w")

    def _build_presets(self, parent: tk.Widget) -> None:
        if not self._presets:
            tk.Label(parent, text="No presets", fg=_MUTED, bg=_PANEL, font=("Consolas", 9)).pack(anchor="w")
            return

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        for idx, preset in enumerate(self._presets):
            label = str(preset.get("name", "Preset"))
            steps = str(preset.get("steps", "")).strip()
            cooldown_ms = int(preset.get("cooldown_ms", 0) or 0)
            group = str(preset.get("group", "")).strip() or str(preset.get("id", "")).strip()
            tk.Button(
                parent,
                text=label,
                width=12,
                command=lambda s=steps, g=group, cd=cooldown_ms, name=label: self._fire_preset(name, g, cd, s),
            ).grid(row=idx // 2, column=idx % 2, sticky="ew", padx=3, pady=3)

    def _field(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        row: int,
        col: int,
        width: int,
        *,
        colspan: int = 1,
    ) -> None:
        wrap = tk.Frame(parent, bg=_PANEL)
        wrap.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=(0, 10), pady=(0, 8))
        wrap.grid_columnconfigure(0, weight=1)
        tk.Label(wrap, text=label, fg=_MUTED, bg=_PANEL, font=("Consolas", 9)).pack(anchor="w")
        tk.Entry(wrap, textvariable=variable, width=width, bg=_PANEL_2, fg=_FG, insertbackground=_FG, relief="flat").pack(fill="x")

    def _refresh_list(self) -> None:
        self.slot_list.delete(0, tk.END)
        for idx, macro in enumerate(self._macros):
            cooldown = int(macro.get("cooldown_ms", 0) or 0)
            self.slot_list.insert(tk.END, f"{idx + 1}. {macro.get('name', 'Macro')} [{cooldown}ms]")
        if self._macros:
            self.slot_list.selection_clear(0, tk.END)
            self.slot_list.selection_set(self._selected_index)
            self.slot_list.activate(self._selected_index)

    def _selected_macro(self) -> dict:
        if not self._macros:
            self._macros.append(_normalize_macro({}, 0))
        self._selected_index = max(0, min(self._selected_index, len(self._macros) - 1))
        return self._macros[self._selected_index]

    def _load_selected(self, index: int) -> None:
        if not self._macros:
            return
        self._selected_index = max(0, min(index, len(self._macros) - 1))
        macro = self._macros[self._selected_index]
        self.name_var.set(str(macro.get("name", "")))
        self.trigger_var.set(str(macro.get("trigger", "")))
        self.group_var.set(str(macro.get("group", "")))
        self.cooldown_var.set(str(int(macro.get("cooldown_ms", 0) or 0)))
        self.primary_var.set(str(macro.get("primary", "")))
        self.fallback_var.set(str(macro.get("fallback", "")))
        self.notes_var.set(str(macro.get("notes", "")))
        self._update_preview()
        self._refresh_timer()
        self._refresh_list()

    def _on_select(self, _event=None) -> None:
        selection = self.slot_list.curselection()
        if not selection:
            return
        self._load_selected(int(selection[0]))

    def _update_preview(self) -> None:
        primary = self.primary_var.get().strip()
        steps = _parse_steps(primary)
        if steps:
            self.preview_var.set(f"Preview: {' -> '.join(steps[:4])}")
        else:
            self.preview_var.set("Preview: --")

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _refresh_timer(self) -> None:
        macro = self._selected_macro()
        group = str(macro.get("group", "")).strip() or str(macro.get("id", "")).strip()
        cooldown_ms = int(macro.get("cooldown_ms", 0) or 0)
        last = self._last_fire.get(group, 0.0)
        elapsed_ms = max(0.0, (time.monotonic() - last) * 1000.0)
        remaining_ms = max(0.0, cooldown_ms - elapsed_ms)
        self.timer_var.set(f"Cooldown: {_pretty_age(remaining_ms / 1000.0)} ({group or 'solo'})")

    def _collect_macro(self) -> dict:
        cooldown_text = self.cooldown_var.get().strip() or "0"
        try:
            cooldown_ms = max(0, int(cooldown_text))
        except ValueError:
            raise ValueError("CD ms must be an integer")

        macro = dict(self._selected_macro())
        macro.update(
            {
                "name": self.name_var.get().strip() or "Macro",
                "trigger": self.trigger_var.get().strip() or "F1",
                "group": self.group_var.get().strip(),
                "cooldown_ms": cooldown_ms,
                "primary": self.primary_var.get().strip(),
                "fallback": self.fallback_var.get().strip(),
                "notes": self.notes_var.get().strip(),
            }
        )
        return macro

    def _save_current(self) -> None:
        try:
            macro = self._collect_macro()
        except ValueError as exc:
            messagebox.showerror("Invalid macro", str(exc))
            return

        self._macros[self._selected_index] = macro
        self._data["macros"] = self._macros
        _save_config(self._data)
        self.status.set(f"Saved {macro['name']}")
        self._refresh_list()
        self._update_preview()
        self._refresh_timer()

    def _run_steps(self, steps: list[str]) -> None:
        for step in steps:
            normalized = _normalize_step(step)
            if not normalized:
                continue
            if normalized.startswith("wait "):
                try:
                    delay_ms = max(0, int(float(normalized.split(" ", 1)[1].strip())))
                except ValueError:
                    raise ValueError(f"Invalid wait step: {normalized}")
                time.sleep(delay_ms / 1000.0)
                continue
            if not self._command_executor.execute(normalized):
                raise RuntimeError(f"Command failed: {normalized}")

    def _preview_steps(self, label: str, steps: str) -> None:
        parsed = _parse_steps(steps)
        if not parsed:
            raise RuntimeError("No steps defined")
        rendered = " -> ".join(_normalize_step(step) for step in parsed)
        self._append_log(f"{label}: {rendered}")

    def _fire_preset(self, name: str, group: str, cooldown_ms: int, steps: str) -> None:
        now = time.monotonic()
        last = self._last_fire.get(group, 0.0)
        if cooldown_ms > 0 and (now - last) * 1000.0 < cooldown_ms:
            self.status.set(f"{name} on cooldown")
            self._append_log(f"{name}: cooldown active")
            return

        if self._test_mode.get():
            try:
                self._preview_steps(name, steps)
                self._last_fire[group] = time.monotonic()
                self.status.set(f"Previewed {name}")
                self._refresh_timer()
            except Exception as exc:
                self.status.set(f"Preview failed: {exc}")
                self._append_log(f"{name}: preview failed: {exc}")
            return

        def worker() -> None:
            message = ""
            with self._fire_lock:
                try:
                    self._run_steps(_parse_steps(steps))
                    self._last_fire[group] = time.monotonic()
                    message = f"Fired {name}"
                except Exception as exc:
                    message = f"Fire failed: {exc}"
                finally:
                    self.root.after(0, lambda msg=message: self.status.set(msg))
                    self.root.after(0, self._refresh_timer)

        threading.Thread(target=worker, daemon=True).start()

    def _fire_macro(self, macro: dict, *, force: bool = False) -> str:
        group = str(macro.get("group", "")).strip() or str(macro.get("id", "")).strip()
        cooldown_ms = int(macro.get("cooldown_ms", 0) or 0)
        now = time.monotonic()
        last = self._last_fire.get(group, 0.0)
        elapsed_ms = (now - last) * 1000.0
        ready = elapsed_ms >= cooldown_ms

        sequence_key = "primary"
        if not ready and str(macro.get("fallback", "")).strip():
            sequence_key = "fallback"
        elif not ready and not force:
            raise RuntimeError(f"Cooldown active for {group or macro.get('id')}")

        sequence = str(macro.get(sequence_key, "")).strip()
        if not sequence:
            raise RuntimeError(f"No {sequence_key} sequence defined")

        if self._test_mode.get():
            self._preview_steps(str(macro.get("name", "Macro")), sequence)
            self._last_fire[group] = time.monotonic()
            return f"Previewed {macro.get('name', 'Macro')} ({sequence_key})"

        self._run_steps(_parse_steps(sequence))
        self._last_fire[group] = time.monotonic()
        return f"Fired {macro.get('name', 'Macro')} ({sequence_key})"

    def _fire_current(self) -> None:
        macro = self._collect_macro()

        def worker() -> None:
            message = ""
            with self._fire_lock:
                try:
                    message = self._fire_macro(macro)
                except Exception as exc:
                    message = f"Fire failed: {exc}"
                finally:
                    self.root.after(0, lambda msg=message: self.status.set(msg))
                    self.root.after(0, self._refresh_timer)

        threading.Thread(target=worker, daemon=True).start()

    def _reset_current_cd(self) -> None:
        macro = self._selected_macro()
        group = str(macro.get("group", "")).strip() or str(macro.get("id", "")).strip()
        self._last_fire.pop(group, None)
        self.status.set(f"Reset CD for {group}")
        self._refresh_timer()

    def _new_macro(self) -> None:
        self._macros.append(_normalize_macro({}, len(self._macros)))
        self._selected_index = len(self._macros) - 1
        self._load_selected(self._selected_index)
        self.status.set("Created new macro slot")

    def _duplicate_macro(self) -> None:
        macro = dict(self._selected_macro())
        macro["id"] = f"{macro.get('id', 'macro')}-copy"
        macro["name"] = f"{macro.get('name', 'Macro')} Copy"
        self._macros.insert(self._selected_index + 1, macro)
        self._selected_index += 1
        self._load_selected(self._selected_index)
        self.status.set("Duplicated macro slot")

    def _delete_macro(self) -> None:
        if len(self._macros) <= 1:
            messagebox.showinfo("Keep one slot", "Zostawiamy przynajmniej jeden slot.")
            return
        self._macros.pop(self._selected_index)
        self._selected_index = max(0, self._selected_index - 1)
        self._data["macros"] = self._macros
        _save_config(self._data)
        self._load_selected(self._selected_index)
        self.status.set("Deleted macro slot")

    def _reload(self) -> None:
        self._data = _load_config()
        self._presets = [_normalize_preset(p, i) for i, p in enumerate(self._data.get("quick_presets", []))]
        self._macros = [_normalize_macro(m, i) for i, m in enumerate(self._data.get("macros", []))]
        self._selected_index = min(self._selected_index, max(0, len(self._macros) - 1))
        self._load_selected(self._selected_index)
        self.status.set("Reloaded macro config")
        self._append_log("Reloaded macro config")

    def _tick(self) -> None:
        self._update_preview()
        self._refresh_timer()
        self.root.after(250, self._tick)


def run() -> None:
    root = tk.Tk()
    app = MacroOverlayApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
