"""Desktop GUI entrypoint for CTOA operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import re
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser

try:
    from desktop_console.api_client import ApiError, AuthContext, CtoaApiClient
    from desktop_console.update_client import GitHubReleaseUpdater, UpdateInfo
    from desktop_console.version import APP_NAME, APP_VERSION
except ImportError:
    from api_client import ApiError, AuthContext, CtoaApiClient
    from update_client import GitHubReleaseUpdater, UpdateInfo
    from version import APP_NAME, APP_VERSION


DEFAULT_API_BASE = "http://127.0.0.1:8787"
SETTINGS_FILE = Path(os.getenv("APPDATA", str(Path.home()))) / "CTOA" / "desktop-settings.json"
UPDATE_DOWNLOAD_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "CTOA" / "updates"
PROFILE_CHOICES = ("local", "stage", "prod")
THEME_CHOICES = ("arcane_night", "steel_ops", "classic_parchment")
THEME_LABELS = {
    "arcane_night": "Arcane Night (Dark)",
    "steel_ops": "Steel Ops",
    "classic_parchment": "Classic Tibia Parchment",
}
THEME_PALETTES = {
    "arcane_night": {
        "bg": "#0f1424",
        "surface": "#151d31",
        "hero": "#22345b",
        "hero_deep": "#182542",
        "hero_text": "#f2f6ff",
        "hero_soft": "#c8d5ef",
        "text": "#e9f0ff",
        "muted": "#98a5c1",
        "metric": "#1a243b",
        "status": "#11192d",
        "accent": "#4ea3ff",
        "accent_active": "#2f87e6",
        "ok": "#4ed9a1",
        "warn": "#efc25e",
        "bad": "#ff788a",
        "rail": "#111a2d",
        "step": "#1e2c4a",
        "code_bg": "#101a2c",
        "code_fg": "#d9e7ff",
        "insight_bg": "#16253f",
        "input_bg": "#101a2c",
        "input_fg": "#edf3ff",
        "banner_good_bg": "#173b2d",
        "banner_good_fg": "#81f0c5",
        "banner_warn_bg": "#47361b",
        "banner_warn_fg": "#ffd480",
        "banner_bad_bg": "#4b1d26",
        "banner_bad_fg": "#ff9dad",
    },
    "steel_ops": {
        "bg": "#141a22",
        "surface": "#1b242f",
        "hero": "#2a3a50",
        "hero_deep": "#1d2a3c",
        "hero_text": "#edf4fc",
        "hero_soft": "#c5d3e3",
        "text": "#e5edf7",
        "muted": "#9aa9ba",
        "metric": "#202b37",
        "status": "#17202a",
        "accent": "#4c9bc7",
        "accent_active": "#3e82aa",
        "ok": "#56ce96",
        "warn": "#d9b45a",
        "bad": "#ea8080",
        "rail": "#17212b",
        "step": "#253244",
        "code_bg": "#15202a",
        "code_fg": "#d8e3ef",
        "insight_bg": "#1e2d3d",
        "input_bg": "#111a23",
        "input_fg": "#eaf2fa",
        "banner_good_bg": "#183b32",
        "banner_good_fg": "#8ae5be",
        "banner_warn_bg": "#4a3a22",
        "banner_warn_fg": "#ffd893",
        "banner_bad_bg": "#48252c",
        "banner_bad_fg": "#ffacac",
    },
    "classic_parchment": {
        "bg": "#efe7d6",
        "surface": "#f8f1e2",
        "hero": "#6b4f2a",
        "hero_deep": "#523d20",
        "hero_text": "#fff6e3",
        "hero_soft": "#f6e0b7",
        "text": "#352718",
        "muted": "#6f5a40",
        "metric": "#f3e7cf",
        "status": "#e8dbc0",
        "accent": "#9b5f2a",
        "accent_active": "#7c4a1f",
        "ok": "#3f7a43",
        "warn": "#9b6a14",
        "bad": "#9a2f2f",
        "rail": "#e2d5ba",
        "step": "#f1e4cb",
        "code_bg": "#f6ecda",
        "code_fg": "#3c2f1d",
        "insight_bg": "#efe2c8",
        "input_bg": "#fff8eb",
        "input_fg": "#352718",
        "banner_good_bg": "#dff1df",
        "banner_good_fg": "#28562a",
        "banner_warn_bg": "#f8e9cf",
        "banner_warn_fg": "#7d560e",
        "banner_bad_bg": "#f8dbdb",
        "banner_bad_fg": "#7e2323",
    },
}


def _theme_label(theme_name: str) -> str:
    key = str(theme_name or "").strip().lower()
    if key not in THEME_CHOICES:
        key = "arcane_night"
    return THEME_LABELS[key]


def _theme_from_choice(value: object) -> str:
    lowered = str(value or "").strip().lower()
    if lowered in THEME_CHOICES:
        return lowered
    for key, label in THEME_LABELS.items():
        if label.lower() == lowered:
            return key
    return "arcane_night"


def _default_profile_urls() -> dict[str, str]:    return {
        "local": DEFAULT_API_BASE,
        "stage": str(os.getenv("CTOA_STAGE_API_BASE", "")).strip(),
        "prod": str(os.getenv("CTOA_PROD_API_BASE", "")).strip(),
    }


@dataclass(slots=True)
class DesktopSettings:
    base_url: str = DEFAULT_API_BASE
    username: str = ""
    refresh_seconds: int = 20
    auto_refresh: bool = True
    check_updates_on_startup: bool = True
    endpoint_profile: str = "local"
    onboarding_completed: bool = False
    theme_name: str = "arcane_night"
    profile_urls: dict[str, str] = field(default_factory=_default_profile_urls)


def _safe_normalize_url(raw_url: object) -> str:
    value = str(raw_url or "").strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.IGNORECASE):
        value = f"http://{value}"
    return value.rstrip("/")


def _load_settings() -> DesktopSettings:
    defaults = _default_profile_urls()
    if not SETTINGS_FILE.exists():
        return DesktopSettings(profile_urls=defaults)

    try:
        payload = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DesktopSettings(profile_urls=defaults)

    loaded_profiles = payload.get("profile_urls") if isinstance(payload, dict) else {}
    profile_urls = dict(defaults)
    if isinstance(loaded_profiles, dict):
        for key in PROFILE_CHOICES:
            candidate = _safe_normalize_url(loaded_profiles.get(key, profile_urls.get(key, "")))
            if key == "local" and not candidate:
                candidate = DEFAULT_API_BASE
            profile_urls[key] = candidate

    endpoint_profile = str(payload.get("endpoint_profile", "local")).strip().lower()
    if endpoint_profile not in PROFILE_CHOICES:
        endpoint_profile = "local"

    theme_name = _theme_from_choice(payload.get("theme_name", "arcane_night"))

    configured_base = _safe_normalize_url(payload.get("base_url", ""))
    base_url = configured_base or profile_urls.get(endpoint_profile) or profile_urls["local"]

    refresh_seconds = _normalize_refresh_seconds(payload.get("refresh_seconds", 20))
    return DesktopSettings(
        base_url=base_url,
        username=str(payload.get("username") or ""),
        refresh_seconds=refresh_seconds,
        auto_refresh=bool(payload.get("auto_refresh", True)),
        check_updates_on_startup=bool(payload.get("check_updates_on_startup", True)),
        endpoint_profile=endpoint_profile,
        onboarding_completed=bool(payload.get("onboarding_completed", False)),
        theme_name=theme_name,
        profile_urls=profile_urls,
    )


def _save_settings(settings: DesktopSettings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=True), encoding="utf-8")


def _normalize_refresh_seconds(value: object) -> int:
    try:
        parsed = int(value)
    except Exception:
        return 20
    if parsed < 5:
        return 5
    if parsed > 300:
        return 300
    return parsed


def _friendly_api_error(exc: Exception, base_url: str) -> str:
    text = str(exc)
    lowered = text.lower()

    if "invalid credentials" in lowered or "401" in lowered:
        return "Login failed: invalid username or password."

    if "owner role required" in lowered or "403" in lowered:
        return "Access denied: this action requires owner role."

    network_markers = [
        "failed to establish a new connection",
        "connection refused",
        "max retries exceeded",
        "name or service not known",
        "network error while calling",
    ]
    if any(marker in lowered for marker in network_markers):
        return (
            "Cannot connect to API.\n\n"
            f"Current API Base URL: {base_url}\n\n"
            "If backend runs locally, start it with:\n"
            "python -m uvicorn mobile_console.app:app --host 0.0.0.0 --port 8787\n\n"
            "If backend runs on VPS, use your VPS domain/IP URL instead of 127.0.0.1."
        )

    return text


class CtoaDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1360x900")
        self.minsize(1160, 760)

        self.settings = _load_settings()
        self._configure_styles(theme_name=self.settings.theme_name)

        effective_base = _safe_normalize_url(self.settings.base_url) or self._resolve_profile_url(
            self.settings.endpoint_profile,
            fallback=self.settings.base_url,
        )
        self.settings.base_url = effective_base
        self.api = CtoaApiClient(effective_base)
        self.auth: AuthContext | None = None

        self._frame: ttk.Frame | None = None
        self._content = ttk.Frame(self, style="Root.TFrame")
        self._content.pack(fill="both", expand=True, padx=14, pady=(12, 0))

        self.status_var = tk.StringVar(value="Ready")
        self.update_var = tk.StringVar(value=f"Version {APP_VERSION}")
        status_bar = ttk.Frame(self, style="StatusBar.TFrame")
        status_bar.pack(side="bottom", fill="x", padx=14, pady=(0, 10))
        ttk.Label(status_bar, textvariable=self.status_var, style="StatusBar.TLabel").pack(side="left", padx=8, pady=4)
        ttk.Label(status_bar, textvariable=self.update_var, style="StatusBar.TLabel").pack(side="right", padx=8, pady=4)

        self.updater = GitHubReleaseUpdater()
        self.pending_update: UpdateInfo | None = None
        self._update_check_running = False

        self._bind_shortcuts()
        self.show_login(preset_url=self.settings.base_url)

        if self.settings.check_updates_on_startup:
            self.after(900, lambda: self.check_for_updates(manual=False))

    def _configure_styles(self, theme_name: str | None = None) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        selected_theme = _theme_from_choice(theme_name or self.settings.theme_name)
        palette = dict(THEME_PALETTES.get(selected_theme, THEME_PALETTES["arcane_night"]))
        self.settings.theme_name = selected_theme
        self._palette = palette
        self._current_theme = selected_theme
        self.configure(bg=palette["bg"])

        style.configure("Root.TFrame", background=palette["bg"])
        style.configure("Shell.TFrame", background=palette["bg"])
        style.configure("Card.TFrame", background=palette["surface"], relief="solid", borderwidth=1)
        style.configure("Surface.TFrame", background=palette["surface"])
        style.configure("Hero.TFrame", background=palette["hero"], relief="solid", borderwidth=1)
        style.configure("NavRail.TFrame", background=palette["rail"], relief="solid", borderwidth=1)
        style.configure("StepCard.TFrame", background=palette["step"], relief="solid", borderwidth=1)

        style.configure(
            "Headline.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Bahnschrift SemiBold", 23),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=palette["surface"],
            foreground=palette["text"],
            font=("Bahnschrift SemiBold", 18),
        )
        style.configure(
            "Subhead.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Meta.TLabel",
            background=palette["bg"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Hint.TLabel",
            background=palette["rail"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Field.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "StepTitle.TLabel",
            background=palette["step"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "StepBody.TLabel",
            background=palette["step"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )

        style.configure(
            "HeroTitle.TLabel",
            background=palette["hero"],
            foreground=palette["hero_text"],
            font=("Bahnschrift SemiBold", 27),
        )
        style.configure(
            "HeroBody.TLabel",
            background=palette["hero"],
            foreground=palette["hero_soft"],
            font=("Segoe UI", 10),
        )

        style.configure("MetricCard.TFrame", background=palette["metric"], relief="solid", borderwidth=1)
        style.configure(
            "MetricName.TLabel",
            background=palette["metric"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "MetricValue.TLabel",
            background=palette["metric"],
            foreground=palette["text"],
            font=("Segoe UI Semibold", 13),
        )
        style.configure(
            "MetricValueGood.TLabel",
            background=palette["metric"],
            foreground=palette["ok"],
            font=("Segoe UI Semibold", 13),
        )
        style.configure(
            "MetricValueWarn.TLabel",
            background=palette["metric"],
            foreground=palette["warn"],
            font=("Segoe UI Semibold", 13),
        )
        style.configure(
            "MetricValueBad.TLabel",
            background=palette["metric"],
            foreground=palette["bad"],
            font=("Segoe UI Semibold", 13),
        )

        style.configure(
            "BannerGood.TLabel",
            background=palette["banner_good_bg"],
            foreground=palette["banner_good_fg"],
            font=("Segoe UI Semibold", 10),
            padding=(10, 8),
        )
        style.configure(
            "BannerWarn.TLabel",
            background=palette["banner_warn_bg"],
            foreground=palette["banner_warn_fg"],
            font=("Segoe UI Semibold", 10),
            padding=(10, 8),
        )
        style.configure(
            "BannerBad.TLabel",
            background=palette["banner_bad_bg"],
            foreground=palette["banner_bad_fg"],
            font=("Segoe UI Semibold", 10),
            padding=(10, 8),
        )

        style.configure(
            "Primary.TButton",
            padding=(14, 8),
            font=("Segoe UI Semibold", 10),
            foreground="#ffffff",
            background=palette["accent"],
            borderwidth=0,
            focusthickness=1,
            focuscolor=palette["accent_active"],
        )
        style.map(
            "Primary.TButton",
            background=[("pressed", palette["accent_active"]), ("active", palette["accent_active"]), ("!disabled", palette["accent"])],
            foreground=[("!disabled", "#ffffff")],
        )

        style.configure(
            "NavButton.TButton",
            padding=(12, 8),
            font=("Segoe UI Semibold", 10),
            anchor="w",
        )

        style.configure(
            "Surface.TCheckbutton",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )

        style.configure(
            "TEntry",
            fieldbackground=palette["input_bg"],
            foreground=palette["input_fg"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=palette["input_bg"],
            foreground=palette["input_fg"],
            arrowsize=14,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["input_bg"])],
            foreground=[("readonly", palette["input_fg"])],
            selectbackground=[("readonly", palette["input_bg"])],
            selectforeground=[("readonly", palette["input_fg"])],
        )

        self.option_add("*TCombobox*Listbox*Background", palette["input_bg"])
        self.option_add("*TCombobox*Listbox*Foreground", palette["input_fg"])

        style.configure("Dashboard.TNotebook", background=palette["bg"], borderwidth=0)
        style.configure("Dashboard.TNotebook.Tab", padding=(16, 8), font=("Segoe UI Semibold", 10))
        style.map(
            "Dashboard.TNotebook.Tab",
            background=[("selected", palette["surface"]), ("active", palette["metric"])],
            foreground=[("selected", palette["text"]), ("active", palette["text"])],
        )

        style.configure("StatusBar.TFrame", background=palette["status"], relief="flat")
        style.configure(
            "StatusBar.TLabel",
            background=palette["status"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )

    def set_theme(self, theme_choice: object, rerender: bool = True) -> str:
        theme_name = _theme_from_choice(theme_choice)
        self.settings.theme_name = theme_name
        _save_settings(self.settings)
        self._configure_styles(theme_name=theme_name)
        self.set_status(f"Theme switched to {_theme_label(theme_name)}")
        if rerender:
            self._rerender_active_frame()
        return theme_name

    def _rerender_active_frame(self) -> None:
        frame = self._frame
        if frame is None:
            return

        frame_name = frame.__class__.__name__
        if frame_name == "DashboardFrame":
            self.show_dashboard(trigger_onboarding=False)
            return
        if frame_name == "LoginFrame":
            self.show_login(self.api.base_url)
            return
        if frame_name == "RegisterFrame":
            self.show_register(self.api.base_url)
            return
        if frame_name == "EndpointConfigFrame":
            return_to = getattr(frame, "return_to", "login")
            self.show_endpoint_config(return_to=return_to)
            return
        if frame_name == "AdminConsoleFrame":
            self.show_admin_console()
            return
        self.show_login(self.api.base_url)
    def _bind_shortcuts(self) -> None:
        for sequence, callback in (
            ("<F5>", self._shortcut_refresh),
            ("<Control-r>", self._shortcut_refresh),
            ("<Control-R>", self._shortcut_refresh),
            ("<Control-1>", lambda: self._shortcut_tab(0)),
            ("<Control-2>", lambda: self._shortcut_tab(1)),
            ("<Control-3>", lambda: self._shortcut_tab(2)),
            ("<Control-e>", self._shortcut_profiles),
            ("<Control-E>", self._shortcut_profiles),
            ("<Control-h>", self._shortcut_onboarding),
            ("<Control-H>", self._shortcut_onboarding),
            ("<Control-q>", self._shortcut_logout),
            ("<Control-Q>", self._shortcut_logout),
            ("<Control-Shift-A>", self._shortcut_admin),
            ("<Control-Shift-a>", self._shortcut_admin),
            ("<Control-t>", self._shortcut_cycle_theme),
            ("<Control-T>", self._shortcut_cycle_theme),
        ):
            self.bind_all(sequence, lambda _event, cb=callback: self._execute_shortcut(cb))

    def _execute_shortcut(self, callback: object) -> str:
        try:
            if callable(callback):
                callback()
        except Exception:
            pass
        return "break"

    def _active_dashboard(self) -> object | None:
        frame = self._frame
        if frame is None:
            return None
        if frame.__class__.__name__ != "DashboardFrame":
            return None
        return frame

    def _shortcut_refresh(self) -> None:
        dashboard = self._active_dashboard()
        if dashboard and hasattr(dashboard, "refresh"):
            dashboard.refresh()

    def _shortcut_tab(self, index: int) -> None:
        dashboard = self._active_dashboard()
        if dashboard and hasattr(dashboard, "go_tab"):
            dashboard.go_tab(index)

    def _shortcut_profiles(self) -> None:
        dashboard = self._active_dashboard()
        if dashboard is not None:
            self.show_endpoint_config(return_to="dashboard")
            return
        frame = self._frame
        if frame and frame.__class__.__name__ == "LoginFrame":
            self.show_endpoint_config(return_to="login")

    def _shortcut_onboarding(self) -> None:
        origin = "dashboard" if self._active_dashboard() is not None else "login"
        self.show_onboarding(origin=origin)

    def _shortcut_logout(self) -> None:
        dashboard = self._active_dashboard()
        if dashboard is not None:
            self.logout()

    def _shortcut_admin(self) -> None:
        if self._active_dashboard() is not None:
            self.show_admin_console()

    def _shortcut_cycle_theme(self) -> None:
        current = _theme_from_choice(self.settings.theme_name)
        try:
            idx = THEME_CHOICES.index(current)
        except ValueError:
            idx = 0
        next_theme = THEME_CHOICES[(idx + 1) % len(THEME_CHOICES)]
        self.set_theme(next_theme, rerender=True)

    def _resolve_return_target(self, origin: str) -> str:
        value = str(origin or "").strip().lower()
        if value in {"dashboard", "register", "endpoint", "login"}:
            return value
        return "login"

    def _resolve_profile_url(self, profile: str, fallback: str = "") -> str:
        key = profile if profile in PROFILE_CHOICES else "local"
        candidate = _safe_normalize_url(self.settings.profile_urls.get(key, ""))
        if candidate:
            return candidate
        safe_fallback = _safe_normalize_url(fallback)
        if safe_fallback:
            return safe_fallback
        return DEFAULT_API_BASE if key == "local" else ""

    def _match_profile_for_url(self, url: str) -> str:
        normalized = _safe_normalize_url(url)
        if not normalized:
            return self.settings.endpoint_profile
        for profile in PROFILE_CHOICES:
            profile_url = _safe_normalize_url(self.settings.profile_urls.get(profile, ""))
            if profile_url and profile_url == normalized:
                return profile
        return self.settings.endpoint_profile

    def set_status(self, text: str) -> None:
        self.status_var.set(str(text))

    def show_login(self, preset_url: str = "") -> None:
        self._mount(
            LoginFrame(
                self,
                preset_url=preset_url or self.settings.base_url or self.api.base_url,
                preset_username=self.settings.username,
            )
        )

    def show_register(self, preset_url: str = "") -> None:
        self._mount(RegisterFrame(self, preset_url=preset_url or self.settings.base_url or self.api.base_url))

    def show_dashboard(self, trigger_onboarding: bool = True) -> None:
        self._mount(DashboardFrame(self))
        if trigger_onboarding and not self.settings.onboarding_completed:
            self.after(140, lambda: self.show_onboarding(origin="dashboard"))

    def show_onboarding(self, origin: str = "dashboard") -> None:
        target = self._resolve_return_target(origin)
        try:
            OnboardingDialog(self, return_to=target)
        except Exception:
            messagebox.showinfo(
                "Quick onboarding",
                "1) Ustaw endpoint profile\n2) Sprawdz Ping API\n3) Zaloguj i uzyj Ctrl+1/2/3 + F5",
            )

    def show_admin_console(self) -> None:
        if not self.auth or self.auth.role != "owner":
            messagebox.showwarning("Access denied", "Admin console is available only for owner role.")
            return
        self._mount(AdminConsoleFrame(self))

    def show_endpoint_config(self, return_to: str = "login") -> None:
        self._mount(EndpointConfigFrame(self, return_to=return_to))

    def update_profile_urls(self, local_url: str, stage_url: str, prod_url: str) -> None:
        self.settings.profile_urls["local"] = _safe_normalize_url(local_url) or DEFAULT_API_BASE
        self.settings.profile_urls["stage"] = _safe_normalize_url(stage_url)
        self.settings.profile_urls["prod"] = _safe_normalize_url(prod_url)
        _save_settings(self.settings)

    def apply_endpoint_profile(self, profile: str) -> str:
        selected = str(profile or "").strip().lower()
        if selected not in PROFILE_CHOICES:
            raise ApiError("Unknown profile")

        endpoint = self._resolve_profile_url(selected, fallback=self.settings.base_url)
        if not endpoint:
            raise ApiError(f"Profile '{selected}' has no configured API URL")

        self.api.set_base_url(endpoint)
        self.settings.endpoint_profile = selected
        self.settings.base_url = self.api.base_url
        _save_settings(self.settings)
        self.set_status(f"Using profile '{selected}' -> {self.api.base_url}")
        return self.api.base_url

    def login(self, base_url: str, username: str, password: str) -> None:
        self.api.set_base_url(base_url)
        self.auth = self.api.login(username=username, password=password)

        self.settings.base_url = self.api.base_url
        self.settings.username = username
        self.settings.endpoint_profile = self._match_profile_for_url(self.api.base_url)
        _save_settings(self.settings)

    def register(self, base_url: str, username: str, password: str, registration_code: str) -> None:
        self.api.set_base_url(base_url)
        self.api.register(username=username, password=password, registration_code=registration_code)

        self.settings.base_url = self.api.base_url
        self.settings.username = username
        self.settings.endpoint_profile = self._match_profile_for_url(self.api.base_url)
        _save_settings(self.settings)

    def logout(self) -> None:
        try:
            self.api.logout()
        except Exception:
            pass
        self.auth = None
        self.set_status("Logged out")
        self.show_login(preset_url=self.settings.base_url)

    def check_for_updates(self, manual: bool) -> None:
        if self._update_check_running:
            if manual:
                messagebox.showinfo("Updates", "Update check is already in progress.")
            return

        self._update_check_running = True
        self.set_status("Checking updates...")

        def worker() -> None:
            info: UpdateInfo | None = None
            error: Exception | None = None
            try:
                info = self.updater.check_for_update(APP_VERSION)
            except Exception as exc:
                error = exc
            self.after(0, lambda: self._finish_update_check(info=info, error=error, manual=manual))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update_check(self, info: UpdateInfo | None, error: Exception | None, manual: bool) -> None:
        self._update_check_running = False

        if error is not None:
            self.update_var.set(f"Version {APP_VERSION} | update check failed")
            self.set_status("Update check failed")
            if manual:
                messagebox.showerror("Update check failed", str(error))
            return

        if info is None:
            self.update_var.set(f"Version {APP_VERSION}")
            self.set_status("No update metadata available")
            return

        if info.update_available:
            self.pending_update = info
            self.update_var.set(f"Update available: {info.latest_version}")
            self.set_status(f"Update {info.latest_version} is available")
            if manual:
                self.prompt_update_install()
            return

        self.pending_update = None
        self.update_var.set(f"Version {APP_VERSION} is up to date")
        self.set_status("Application is up to date")
        if manual:
            messagebox.showinfo("Updates", f"You already run latest version ({APP_VERSION}).")

    def prompt_update_install(self) -> None:
        info = self.pending_update
        if info is None:
            messagebox.showinfo("Updates", "No pending update available.")
            return

        if not info.download_url:
            messagebox.showinfo(
                "Update available",
                (
                    f"Version {info.latest_version} is available, but no Windows EXE asset was found.\n"
                    "Release page will be opened in your browser."
                ),
            )
            if info.release_notes_url:
                webbrowser.open(info.release_notes_url)
            return

        if not messagebox.askyesno(
            "Update available",
            (
                f"Version {info.latest_version} is available.\n\n"
                "Do you want to download update now?"
            ),
        ):
            return

        self.download_update()

    def download_update(self) -> None:
        info = self.pending_update
        if info is None:
            messagebox.showinfo("Updates", "No pending update available.")
            return

        self.set_status("Downloading update package...")

        def worker() -> None:
            path: Path | None = None
            error: Exception | None = None
            try:
                path = self.updater.download_update(info, UPDATE_DOWNLOAD_DIR)
            except Exception as exc:
                error = exc
            self.after(0, lambda: self._finish_update_download(path=path, error=error))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update_download(self, path: Path | None, error: Exception | None) -> None:
        if error is not None:
            self.set_status("Update download failed")
            messagebox.showerror("Update download failed", str(error))
            return

        if path is None:
            self.set_status("Update download failed")
            messagebox.showerror("Update download failed", "No update file was created.")
            return

        self.set_status(f"Update downloaded: {path}")
        if messagebox.askyesno(
            "Update ready",
            (
                f"Update package downloaded to:\n{path}\n\n"
                "Run downloaded executable now?"
            ),
        ):
            try:
                os.startfile(str(path))
            except OSError as exc:
                messagebox.showerror("Launch failed", str(exc))

    def _mount(self, frame: ttk.Frame) -> None:
        if self._frame is not None:
            self._frame.destroy()
        self._frame = frame
        self._frame.pack(in_=self._content, fill="both", expand=True)


class LoginFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp, preset_url: str, preset_username: str) -> None:
        super().__init__(app, padding=10, style="Root.TFrame")
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=11)
        shell.columnconfigure(1, weight=9)
        shell.rowconfigure(0, weight=1)

        hero = ttk.Frame(shell, style="Hero.TFrame", padding=(24, 22))
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        hero.columnconfigure(0, weight=1)

        ttk.Label(hero, text="CTOA Mission Control", style="HeroTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            hero,
            text="Przejdz przez onboarding i uruchom dashboard z pelna kontrola pipeline.",
            style="HeroBody.TLabel",
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 10))

        self.hero_canvas = tk.Canvas(hero, height=220, highlightthickness=0, bd=0, relief="flat")
        self.hero_canvas.grid(row=2, column=0, sticky="ew", pady=(2, 12))
        self.hero_canvas.bind("<Configure>", lambda event: _draw_thematic_banner(self.hero_canvas, event.width, event.height, self.app._palette))

        steps = ttk.Frame(hero, style="Hero.TFrame")
        steps.grid(row=3, column=0, sticky="ew")
        steps.columnconfigure(0, weight=1)
        for idx, (title, body) in enumerate(
            (
                ("Krok 1: Endpoint", "Wybierz profil local, stage lub prod i ustaw API URL."),
                ("Krok 2: Polaczenie", "Uzyj Ping API przed logowaniem, aby sprawdzic lacznosc."),
                ("Krok 3: Operacje", "Po loginie przejdz do dashboardu i uzyj Ctrl+1/2/3, F5."),
            )
        ):
            card = ttk.Frame(steps, style="StepCard.TFrame", padding=(10, 8))
            card.grid(row=idx, column=0, sticky="ew", pady=(0 if idx == 0 else 6, 0))
            ttk.Label(card, text=title, style="StepTitle.TLabel").pack(anchor="w")
            ttk.Label(card, text=body, style="StepBody.TLabel", wraplength=440, justify="left").pack(anchor="w", pady=(2, 0))

        card = ttk.Frame(shell, style="Card.TFrame", padding=(24, 22))
        card.grid(row=0, column=1, sticky="nsew")

        ttk.Label(card, text="Sign In", style="Headline.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Wejscie do live dashboard, agent missions i admin guardrails.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        form = ttk.Frame(card, style="Surface.TFrame")
        form.pack(anchor="w", fill="x")

        self.profile_var = tk.StringVar(value=app.settings.endpoint_profile)
        self.base_url = tk.StringVar(value=preset_url)
        self.username = tk.StringVar(value=preset_username)
        self.password = tk.StringVar(value="")
        self.show_password = tk.BooleanVar(value=False)
        self.theme_choice = tk.StringVar(value=_theme_label(app.settings.theme_name))

        profile_row = ttk.Frame(form, style="Surface.TFrame")
        profile_row.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 4))
        ttk.Label(profile_row, text="Endpoint Profile", style="Field.TLabel").pack(side="left")
        profile_combo = ttk.Combobox(
            profile_row,
            textvariable=self.profile_var,
            values=list(PROFILE_CHOICES),
            state="readonly",
            width=14,
        )
        profile_combo.pack(side="left", padx=(10, 0))
        profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        theme_row = ttk.Frame(form, style="Surface.TFrame")
        theme_row.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 6))
        ttk.Label(theme_row, text="Theme", style="Field.TLabel").pack(side="left")
        theme_combo = ttk.Combobox(
            theme_row,
            textvariable=self.theme_choice,
            values=[THEME_LABELS[key] for key in THEME_CHOICES],
            state="readonly",
            width=28,
        )
        theme_combo.pack(side="left", padx=(10, 0))
        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)

        base_entry = _labeled_entry(form, "API Base URL", self.base_url, row=2)
        user_entry = _labeled_entry(form, "Username", self.username, row=3)
        pass_entry = _labeled_entry(form, "Password", self.password, row=4, show="*")

        ttk.Checkbutton(
            form,
            text="Show password",
            style="Surface.TCheckbutton",
            variable=self.show_password,
            command=lambda: _toggle_password_entry(form, reveal=self.show_password.get(), row=4),
        ).grid(row=5, column=1, sticky="w", pady=(2, 4), padx=(8, 0))

        hint = "Local API: http://127.0.0.1:8787  |  VPS API: http(s)://<host-or-domain>:8787"
        ttk.Label(card, text=hint, style="Subhead.TLabel", wraplength=520, justify="left").pack(anchor="w", pady=(6, 10))

        shortcuts = ttk.Frame(card, style="StepCard.TFrame", padding=(10, 8))
        shortcuts.pack(fill="x", pady=(0, 10))
        ttk.Label(shortcuts, text="Szybkie skroty", style="StepTitle.TLabel").pack(anchor="w")
        ttk.Label(
            shortcuts,
            text="Ctrl+H: onboarding  |  Ctrl+E: endpoint profiles  |  Ctrl+T: next theme  |  Enter: login",
            style="StepBody.TLabel",
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        primary_actions = ttk.Frame(card, style="Surface.TFrame")
        primary_actions.pack(anchor="w")
        ttk.Button(primary_actions, text="Login", style="Primary.TButton", command=self._login).pack(side="left")
        ttk.Button(primary_actions, text="Create Account", command=self._open_register).pack(side="left", padx=(10, 0))

        utility_actions = ttk.Frame(card, style="Surface.TFrame")
        utility_actions.pack(anchor="w", pady=(10, 0))
        ttk.Button(utility_actions, text="Guided Onboarding", command=lambda: self.app.show_onboarding(origin="login")).pack(side="left")
        ttk.Button(utility_actions, text="Ping API", command=self._ping_api).pack(side="left", padx=(10, 0))
        ttk.Button(utility_actions, text="Endpoint Profiles", command=self._open_endpoint_profiles).pack(side="left", padx=(10, 0))
        ttk.Button(utility_actions, text="Check Updates", command=lambda: self.app.check_for_updates(manual=True)).pack(side="left", padx=(10, 0))

        for entry in (base_entry, user_entry, pass_entry):
            entry.bind("<Return>", self._on_enter)
    def _on_enter(self, _: object) -> None:
        self._login()

    def _on_profile_selected(self, _: object) -> None:
        profile = self.profile_var.get().strip().lower()
        if profile not in PROFILE_CHOICES:
            return
        url = self.app.settings.profile_urls.get(profile, "")
        if url:
            self.base_url.set(url)

    def _on_theme_selected(self, _: object) -> None:
        self._persist_profile_choice()
        selected_theme = _theme_from_choice(self.theme_choice.get())
        self.app.set_theme(selected_theme, rerender=True)

    def _persist_profile_choice(self) -> None:
        profile = self.profile_var.get().strip().lower()
        if profile in PROFILE_CHOICES:
            self.app.settings.endpoint_profile = profile
            if self.base_url.get().strip():
                self.app.settings.profile_urls[profile] = _safe_normalize_url(self.base_url.get())
        self.app.settings.base_url = _safe_normalize_url(self.base_url.get())
        _save_settings(self.app.settings)

    def _open_endpoint_profiles(self) -> None:
        self._persist_profile_choice()
        self.app.show_endpoint_config(return_to="login")

    def _ping_api(self) -> None:
        self._persist_profile_choice()
        try:
            self.app.api.set_base_url(self.base_url.get())
            payload = self.app.api.auth_auto_check()
        except Exception as exc:
            messagebox.showerror("API check failed", _friendly_api_error(exc, self.base_url.get()))
            return
        self.app.set_status("API reachable")
        messagebox.showinfo("API reachable", json.dumps(payload, indent=2, ensure_ascii=True))

    def _login(self) -> None:
        if not self.username.get().strip() or not self.password.get().strip():
            messagebox.showerror("Missing data", "Username and password are required.")
            return

        self._persist_profile_choice()

        try:
            self.app.login(
                base_url=self.base_url.get(),
                username=self.username.get().strip(),
                password=self.password.get(),
            )
        except Exception as exc:
            messagebox.showerror("Login failed", _friendly_api_error(exc, self.base_url.get()))
            return

        self.app.set_status("Login successful")
        self.app.show_dashboard()

    def _open_register(self) -> None:
        self._persist_profile_choice()
        self.app.show_register(preset_url=self.base_url.get())


class RegisterFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp, preset_url: str) -> None:
        super().__init__(app, padding=8, style="Root.TFrame")
        self.app = app

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.pack(fill="both", expand=True)

        card = ttk.Frame(shell, style="Card.TFrame", padding=(24, 22))
        card.pack(fill="x", anchor="n")

        ttk.Label(card, text="Create Account", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Self-registration creates operator role account.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        form = ttk.Frame(card, style="Surface.TFrame")
        form.pack(anchor="w", fill="x")

        self.base_url = tk.StringVar(value=preset_url)
        self.username = tk.StringVar(value="")
        self.password = tk.StringVar(value="")
        self.password_confirm = tk.StringVar(value="")
        self.registration_code = tk.StringVar(value="")

        _labeled_entry(form, "API Base URL", self.base_url, row=0)
        _labeled_entry(form, "Username", self.username, row=1)
        _labeled_entry(form, "Password", self.password, row=2, show="*")
        _labeled_entry(form, "Confirm Password", self.password_confirm, row=3, show="*")
        _labeled_entry(form, "Registration Code (optional)", self.registration_code, row=4)

        actions = ttk.Frame(card, style="Surface.TFrame")
        actions.pack(anchor="w", pady=(14, 0))
        ttk.Button(actions, text="Create Account", style="Primary.TButton", command=self._register).pack(side="left")
        ttk.Button(actions, text="Endpoint Profiles", command=self._open_endpoint_profiles).pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Back to Login", command=lambda: self.app.show_login(self.base_url.get())).pack(side="left", padx=(10, 0))
    def _open_endpoint_profiles(self) -> None:
        self.app.settings.base_url = _safe_normalize_url(self.base_url.get())
        _save_settings(self.app.settings)
        self.app.show_endpoint_config(return_to="register")

    def _register(self) -> None:
        username = self.username.get().strip()
        password = self.password.get()
        password_confirm = self.password_confirm.get()

        if not username:
            messagebox.showerror("Missing data", "Username is required.")
            return
        if len(password) < 8:
            messagebox.showerror("Weak password", "Password must have at least 8 characters.")
            return
        if password != password_confirm:
            messagebox.showerror("Password mismatch", "Passwords must match.")
            return

        try:
            self.app.register(
                base_url=self.base_url.get(),
                username=username,
                password=password,
                registration_code=self.registration_code.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Registration failed", _friendly_api_error(exc, self.base_url.get()))
            return

        messagebox.showinfo("Account created", "Account created successfully. You can now sign in.")
        self.app.set_status("Account created")
        self.app.show_login(self.base_url.get())


class EndpointConfigFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp, return_to: str) -> None:
        super().__init__(app, padding=8, style="Root.TFrame")
        self.app = app
        self.return_to = return_to

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.pack(fill="both", expand=True)

        card = ttk.Frame(shell, style="Card.TFrame", padding=(24, 22))
        card.pack(fill="x", anchor="n")

        ttk.Label(card, text="Endpoint Profiles", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Configure local/stage/prod API endpoints and switch active profile.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        form = ttk.Frame(card, style="Surface.TFrame")
        form.pack(anchor="w", fill="x")

        self.active_profile = tk.StringVar(value=self.app.settings.endpoint_profile)
        self.local_url = tk.StringVar(value=self.app.settings.profile_urls.get("local", DEFAULT_API_BASE))
        self.stage_url = tk.StringVar(value=self.app.settings.profile_urls.get("stage", ""))
        self.prod_url = tk.StringVar(value=self.app.settings.profile_urls.get("prod", ""))
        self.theme_choice = tk.StringVar(value=_theme_label(self.app.settings.theme_name))

        profile_row = ttk.Frame(form, style="Surface.TFrame")
        profile_row.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 4))
        ttk.Label(profile_row, text="Active profile", style="Field.TLabel").pack(side="left")
        profile_combo = ttk.Combobox(
            profile_row,
            textvariable=self.active_profile,
            values=list(PROFILE_CHOICES),
            state="readonly",
            width=14,
        )
        profile_combo.pack(side="left", padx=(10, 0))

        theme_row = ttk.Frame(form, style="Surface.TFrame")
        theme_row.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 4))
        ttk.Label(theme_row, text="Theme", style="Field.TLabel").pack(side="left")
        theme_combo = ttk.Combobox(
            theme_row,
            textvariable=self.theme_choice,
            values=[THEME_LABELS[key] for key in THEME_CHOICES],
            state="readonly",
            width=28,
        )
        theme_combo.pack(side="left", padx=(10, 0))

        _labeled_entry(form, "Local API URL", self.local_url, row=2)
        _labeled_entry(form, "Stage API URL", self.stage_url, row=3)
        _labeled_entry(form, "Prod API URL", self.prod_url, row=4)

        actions = ttk.Frame(card, style="Surface.TFrame")
        actions.pack(anchor="w", pady=(14, 0))

        ttk.Button(actions, text="Save Profiles", style="Primary.TButton", command=self._save_profiles).pack(side="left")
        ttk.Button(actions, text="Apply Selected", command=self._apply_selected).pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Apply Theme", command=self._apply_theme).pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Ping Selected", command=self._ping_selected).pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Back", command=self._go_back).pack(side="left", padx=(10, 0))
    def _normalized_values(self) -> tuple[str, str, str]:
        local_url = _safe_normalize_url(self.local_url.get())
        stage_url = _safe_normalize_url(self.stage_url.get())
        prod_url = _safe_normalize_url(self.prod_url.get())
        if not local_url:
            local_url = DEFAULT_API_BASE
        return local_url, stage_url, prod_url

    def _save_profiles(self) -> None:
        local_url, stage_url, prod_url = self._normalized_values()
        self.app.update_profile_urls(local_url=local_url, stage_url=stage_url, prod_url=prod_url)

        self.app.settings.endpoint_profile = self.active_profile.get().strip().lower()
        self.app.settings.base_url = self.app._resolve_profile_url(self.app.settings.endpoint_profile, fallback=local_url)
        self.app.settings.theme_name = _theme_from_choice(self.theme_choice.get())
        _save_settings(self.app.settings)

        self.app.set_theme(self.app.settings.theme_name, rerender=False)
        self.app.set_status("Endpoint profiles and theme saved")
        messagebox.showinfo("Saved", "Endpoint profile configuration and theme were saved.")

    def _apply_theme(self) -> None:
        selected_theme = _theme_from_choice(self.theme_choice.get())
        self.app.set_theme(selected_theme, rerender=False)
        self.app.set_status(f"Theme preview: {_theme_label(selected_theme)}")
        messagebox.showinfo("Theme applied", f"Active theme: {_theme_label(selected_theme)}")
    def _apply_selected(self) -> None:
        local_url, stage_url, prod_url = self._normalized_values()
        self.app.update_profile_urls(local_url=local_url, stage_url=stage_url, prod_url=prod_url)
        selected = self.active_profile.get().strip().lower()
        selected_theme = _theme_from_choice(self.theme_choice.get())

        try:
            applied_url = self.app.apply_endpoint_profile(selected)
        except Exception as exc:
            messagebox.showerror("Apply profile failed", str(exc))
            return

        self.app.set_theme(selected_theme, rerender=False)
        messagebox.showinfo("Profile applied", f"Active API Base URL: {applied_url}\nTheme: {_theme_label(selected_theme)}")
        self._go_back()

    def _ping_selected(self) -> None:
        local_url, stage_url, prod_url = self._normalized_values()
        selected = self.active_profile.get().strip().lower()

        candidate_map = {
            "local": local_url,
            "stage": stage_url,
            "prod": prod_url,
        }
        target_url = candidate_map.get(selected, "")
        if not target_url:
            messagebox.showerror("Ping failed", f"Profile '{selected}' has no configured URL.")
            return

        tester = CtoaApiClient(target_url)
        try:
            payload = tester.auth_auto_check()
        except Exception as exc:
            messagebox.showerror("Ping failed", _friendly_api_error(exc, target_url))
            return

        self.app.set_status(f"Profile '{selected}' API reachable")
        messagebox.showinfo("Ping OK", json.dumps(payload, indent=2, ensure_ascii=True))

    def _go_back(self) -> None:
        if self.return_to == "dashboard" and self.app.auth is not None:
            self.app.show_dashboard()
        elif self.return_to == "register":
            self.app.show_register(self.app.settings.base_url)
        else:
            self.app.show_login(self.app.settings.base_url)


class DashboardFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp) -> None:
        super().__init__(app, padding=10, style="Root.TFrame")
        self.app = app
        self._refresh_job: str | None = None

        self.refresh_seconds = tk.IntVar(value=_normalize_refresh_seconds(self.app.settings.refresh_seconds))
        self.auto_refresh = tk.BooleanVar(value=self.app.settings.auto_refresh)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        nav = ttk.Frame(shell, style="NavRail.TFrame", padding=(12, 12))
        nav.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        ttk.Label(nav, text="Mission Nav", style="Field.TLabel").pack(anchor="w", pady=(0, 8))

        self.nav_tab_buttons: list[ttk.Button] = []
        for idx, title in enumerate(("Overview", "Agents", "Raw JSON")):
            button = ttk.Button(nav, text=title, style="NavButton.TButton", command=lambda i=idx: self.go_tab(i))
            button.pack(fill="x", pady=(0 if idx == 0 else 6, 0))
            self.nav_tab_buttons.append(button)

        ttk.Separator(nav, orient="horizontal").pack(fill="x", pady=10)
        self.nav_admin_button = ttk.Button(
            nav,
            text="Admin Console",
            style="NavButton.TButton",
            command=self.app.show_admin_console,
        )
        self.nav_admin_button.pack(fill="x")
        ttk.Button(
            nav,
            text="Endpoint Profiles",
            style="NavButton.TButton",
            command=lambda: self.app.show_endpoint_config(return_to="dashboard"),
        ).pack(fill="x", pady=(6, 0))
        ttk.Button(
            nav,
            text="Guided Onboarding",
            style="NavButton.TButton",
            command=lambda: self.app.show_onboarding(origin="dashboard"),
        ).pack(fill="x", pady=(6, 0))
        ttk.Button(nav, text="Logout", style="NavButton.TButton", command=self.app.logout).pack(fill="x", pady=(6, 0))

        ttk.Separator(nav, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(
            nav,
            text="Skroty\nF5 lub Ctrl+R: refresh\nCtrl+1/2/3: taby\nCtrl+E: endpoint\nCtrl+Shift+A: admin\nCtrl+H: onboarding\nCtrl+T: kolejny motyw",
            style="Hint.TLabel",
            justify="left",
        ).pack(anchor="w")

        main = ttk.Frame(shell, style="Shell.TFrame")
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

        header_card = ttk.Frame(main, style="Card.TFrame", padding=(18, 16))
        header_card.grid(row=0, column=0, sticky="ew")
        header_card.columnconfigure(0, weight=1)

        left_meta = ttk.Frame(header_card, style="Surface.TFrame")
        left_meta.grid(row=0, column=0, sticky="w")

        ttk.Label(left_meta, text="Live Dashboard", style="SectionTitle.TLabel").pack(anchor="w")
        self.identity_label = ttk.Label(left_meta, text="User: - | Role: - | Auth: -", style="Subhead.TLabel")
        self.identity_label.pack(anchor="w", pady=(4, 0))
        self.refresh_meta_label = ttk.Label(left_meta, text="Last refresh: never", style="Subhead.TLabel")
        self.refresh_meta_label.pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(header_card, style="Surface.TFrame")
        controls.grid(row=0, column=1, sticky="e")

        quick_actions = ttk.Frame(controls, style="Surface.TFrame")
        quick_actions.pack(anchor="e")
        ttk.Button(quick_actions, text="Refresh now", style="Primary.TButton", command=self.refresh).pack(side="left")
        ttk.Checkbutton(
            quick_actions,
            text="Auto refresh",
            style="Surface.TCheckbutton",
            variable=self.auto_refresh,
            command=self._on_refresh_pref_changed,
        ).pack(side="left", padx=(10, 0))

        self.interval_combo = ttk.Combobox(
            quick_actions,
            width=5,
            values=["5", "10", "20", "30", "60", "120"],
            state="readonly",
        )
        self.interval_combo.set(str(self.refresh_seconds.get()))
        self.interval_combo.pack(side="left", padx=(8, 0))
        self.interval_combo.bind("<<ComboboxSelected>>", lambda _: self._on_refresh_pref_changed())
        ttk.Label(quick_actions, text="sec", style="Subhead.TLabel").pack(side="left", padx=(4, 0))

        ttk.Label(quick_actions, text="Theme", style="Subhead.TLabel").pack(side="left", padx=(10, 0))
        self.theme_choice = tk.StringVar(value=_theme_label(self.app.settings.theme_name))
        self.theme_combo = ttk.Combobox(
            quick_actions,
            textvariable=self.theme_choice,
            values=[THEME_LABELS[key] for key in THEME_CHOICES],
            state="readonly",
            width=24,
        )
        self.theme_combo.pack(side="left", padx=(8, 0))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)

        tools_actions = ttk.Frame(controls, style="Surface.TFrame")
        tools_actions.pack(anchor="e", pady=(8, 0))
        ttk.Button(tools_actions, text="Check updates", command=lambda: self.app.check_for_updates(manual=True)).pack(side="left")
        ttk.Button(tools_actions, text="Install update", command=self.app.prompt_update_install).pack(side="left", padx=(8, 0))

        self.health_banner_var = tk.StringVar(value="Waiting for first refresh...")
        self.health_banner_label = ttk.Label(main, textvariable=self.health_banner_var, style="BannerWarn.TLabel")
        self.health_banner_label.grid(row=1, column=0, sticky="ew", pady=(10, 10))

        metrics = ttk.Frame(main, style="Shell.TFrame")
        metrics.grid(row=2, column=0, sticky="ew")
        metrics.columnconfigure(0, weight=1)
        metrics.columnconfigure(1, weight=1)
        metrics.columnconfigure(2, weight=1)
        metrics.columnconfigure(3, weight=1)
        metrics.columnconfigure(4, weight=1)
        metrics.columnconfigure(5, weight=1)

        self.metric_vars: dict[str, tk.StringVar] = {}
        self.metric_labels: dict[str, ttk.Label] = {}
        metric_names = [
            "Pipeline status",
            "Success rate (24h)",
            "Error budget",
            "Average quality",
            "Degraded sections",
            "Services",
        ]
        for idx, name in enumerate(metric_names):
            card = ttk.Frame(metrics, style="MetricCard.TFrame", padding=10)
            card.grid(
                row=0 if idx < 3 else 1,
                column=idx if idx < 3 else idx - 3,
                columnspan=2 if idx in (2, 5) else 1,
                sticky="nsew",
                padx=(0 if idx % 3 == 0 else 8, 0),
                pady=(0 if idx < 3 else 8, 0),
            )
            ttk.Label(card, text=name, style="MetricName.TLabel").pack(anchor="w")
            value_var = tk.StringVar(value="-")
            self.metric_vars[name] = value_var
            value_label = ttk.Label(card, textvariable=value_var, style="MetricValue.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.metric_labels[name] = value_label

        action_row = ttk.Frame(main, style="Shell.TFrame")
        action_row.grid(row=3, column=0, sticky="ew", pady=(8, 8))
        self.admin_button = ttk.Button(action_row, text="Open Admin Console", command=self.app.show_admin_console)
        self.admin_button.pack(side="left")
        ttk.Button(action_row, text="Guided Onboarding", command=lambda: self.app.show_onboarding(origin="dashboard")).pack(side="left", padx=(8, 0))
        ttk.Button(action_row, text="Logout", command=self.app.logout).pack(side="left", padx=(8, 0))

        self.notebook = ttk.Notebook(main, style="Dashboard.TNotebook")
        self.notebook.grid(row=4, column=0, sticky="nsew")

        overview_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=10)
        agents_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=10)
        raw_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=10)

        self.notebook.add(overview_tab, text="Overview")
        self.notebook.add(agents_tab, text="Agents")
        self.notebook.add(raw_tab, text="Raw JSON")
        self.notebook.bind("<<NotebookTabChanged>>", lambda _: self._sync_nav_buttons())

        palette = self.app._palette
        code_bg = palette.get("code_bg", "#f7fbff")
        code_fg = palette.get("code_fg", "#1c2c40")
        insight_bg = palette.get("insight_bg", code_bg)

        self.insight_box = ScrolledText(overview_tab, wrap="word", font=("Segoe UI", 10), height=6)
        self.insight_box.pack(fill="x", pady=(0, 8))
        self.insight_box.configure(background=insight_bg, foreground=code_fg, insertbackground=code_fg, relief="flat", borderwidth=0)

        self.overview_box = ScrolledText(overview_tab, wrap="word", font=("Consolas", 10), height=17)
        self.overview_box.pack(fill="both", expand=True)
        self.overview_box.configure(background=code_bg, foreground=code_fg, insertbackground=code_fg, relief="flat", borderwidth=0)

        agents_controls = ttk.Frame(agents_tab, style="Surface.TFrame")
        agents_controls.pack(fill="x", pady=(0, 8))
        self.launch_agent_button = ttk.Button(agents_controls, text="Run One-Click Agent", style="Primary.TButton", command=self._run_one_click_agent)
        self.launch_agent_button.pack(side="left")
        self.intel_button = ttk.Button(agents_controls, text="Launch Intel Mission", command=self._launch_intel)
        self.intel_button.pack(side="left", padx=(8, 0))

        self.agents_box = ScrolledText(agents_tab, wrap="word", font=("Consolas", 10), height=20)
        self.agents_box.pack(fill="both", expand=True)
        self.agents_box.configure(background=code_bg, foreground=code_fg, insertbackground=code_fg, relief="flat", borderwidth=0)

        self.raw_box = ScrolledText(raw_tab, wrap="word", font=("Consolas", 10), height=20)
        self.raw_box.pack(fill="both", expand=True)
        self.raw_box.configure(background=code_bg, foreground=code_fg, insertbackground=code_fg, relief="flat", borderwidth=0)

        self._sync_nav_buttons()
        self._load_remote_profile()
        self._sync_role_controls()
        self.refresh()

    def go_tab(self, index: int) -> None:
        tabs = self.notebook.tabs()
        if not tabs:
            return
        safe_index = max(0, min(int(index), len(tabs) - 1))
        self.notebook.select(safe_index)
        self._sync_nav_buttons()

    def _sync_nav_buttons(self) -> None:
        try:
            selected = self.notebook.index(self.notebook.select())
        except Exception:
            selected = 0
        for idx, button in enumerate(self.nav_tab_buttons):
            button.configure(state="disabled" if idx == selected else "normal")
    def destroy(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None
        super().destroy()

    def _load_remote_profile(self) -> None:
        try:
            payload = self.app.api.live_profile()
        except ApiError:
            return

        profile = payload.get("profile") if isinstance(payload, dict) else None
        if not isinstance(profile, dict):
            return

        refresh_seconds = _normalize_refresh_seconds(profile.get("refresh_seconds", self.refresh_seconds.get()))
        self.refresh_seconds.set(refresh_seconds)
        self.interval_combo.set(str(refresh_seconds))

    def _on_refresh_pref_changed(self) -> None:
        self.refresh_seconds.set(_normalize_refresh_seconds(self.interval_combo.get()))
        self.interval_combo.set(str(self.refresh_seconds.get()))

        self.app.settings.refresh_seconds = self.refresh_seconds.get()
        self.app.settings.auto_refresh = self.auto_refresh.get()
        _save_settings(self.app.settings)

        try:
            self.app.api.save_live_profile(
                api_base=self.app.api.base_url,
                refresh_seconds=self.refresh_seconds.get(),
            )
        except ApiError:
            pass

        self._schedule_next_refresh()

    def _on_theme_selected(self, _: object) -> None:
        self._persist_profile_choice()
        selected_theme = _theme_from_choice(self.theme_choice.get())
        self.app.set_theme(selected_theme, rerender=True)

    def _sync_role_controls(self) -> None:
        role = self.app.auth.role if self.app.auth else "operator"
        state = "normal" if role == "owner" else "disabled"
        self.admin_button.configure(state=state)
        self.nav_admin_button.configure(state=state)
        self.launch_agent_button.configure(state=state)
        self.intel_button.configure(state=state)

    def _schedule_next_refresh(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

        if not self.auto_refresh.get():
            return

        delay = max(5, self.refresh_seconds.get()) * 1000
        self._refresh_job = self.after(delay, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self._refresh_job = None
        self.refresh()

    def refresh(self) -> None:
        try:
            me = self.app.api.me()
            self.app.auth = me
        except Exception as exc:
            messagebox.showerror("Session error", _friendly_api_error(exc, self.app.api.base_url))
            self._schedule_next_refresh()
            return

        self.identity_label.configure(text=f"User: {me.username} | Role: {me.role} | Auth: {me.auth_mode}")
        self._sync_role_controls()

        payloads: dict[str, dict] = {}
        errors: list[str] = []

        for name, loader in (
            ("status", self.app.api.status),
            ("dashboard", self.app.api.dashboard),
            ("agents_status", self.app.api.agents_status),
            ("intel_report", self.app.api.intel_report),
        ):
            try:
                payloads[name] = loader()
            except Exception as exc:
                payloads[name] = {}
                errors.append(f"{name}: {_friendly_api_error(exc, self.app.api.base_url)}")

        dashboard_payload = payloads.get("dashboard", {})
        agents_payload = payloads.get("agents_status", {})
        intel_payload = payloads.get("intel_report", {})

        status_text = str(dashboard_payload.get("status") or payloads.get("status", {}).get("status") or "unknown")
        status_lower = status_text.lower()
        self.metric_vars["Pipeline status"].set(status_text)

        slo_summary = dashboard_payload.get("slo_summary", {}) if isinstance(dashboard_payload, dict) else {}
        success_rate = float(slo_summary.get("success_rate_24h", 0.0) or 0.0)
        self.metric_vars["Success rate (24h)"].set(f"{success_rate * 100:.1f}%")

        error_budget = slo_summary.get("error_budget_remaining", "-")
        self.metric_vars["Error budget"].set(str(error_budget))

        timeline_summary = dashboard_payload.get("timeline_summary", {}) if isinstance(dashboard_payload, dict) else {}
        avg_quality = timeline_summary.get("avg_quality", "-")
        self.metric_vars["Average quality"].set(str(avg_quality))

        degraded_sections = dashboard_payload.get("summary", {}).get("degraded_sections", []) if isinstance(dashboard_payload, dict) else []
        self.metric_vars["Degraded sections"].set(", ".join(str(item) for item in degraded_sections) if degraded_sections else "none")

        services = []
        for key in ("orchestrator", "orchestrator_timer", "db"):
            value = str(agents_payload.get(key, "unknown")) if isinstance(agents_payload, dict) else "unknown"
            services.append(f"{key}={value}")
        services_text = " | ".join(services)
        self.metric_vars["Services"].set(services_text)

        status_message = str(dashboard_payload.get("status_message", ""))
        top_reason = dashboard_payload.get("dominant_signal") if isinstance(dashboard_payload, dict) else None

        critical_markers = ("critical", "error", "missing", "failed")
        has_critical = any(marker in status_lower for marker in critical_markers) or any(
            "missing" in part.lower() or "error" in part.lower() for part in services
        )
        has_warning = bool(degraded_sections) or "degraded" in status_lower

        if has_critical or errors:
            self.health_banner_var.set("Critical state detected. Investigate services/errors before running automation.")
            self.health_banner_label.configure(style="BannerBad.TLabel")
            self.metric_labels["Pipeline status"].configure(style="MetricValueBad.TLabel")
        elif has_warning:
            self.health_banner_var.set("System is operational with degraded signals. Continue with caution.")
            self.health_banner_label.configure(style="BannerWarn.TLabel")
            self.metric_labels["Pipeline status"].configure(style="MetricValueWarn.TLabel")
        else:
            self.health_banner_var.set("System healthy. Pipeline and services are within expected range.")
            self.health_banner_label.configure(style="BannerGood.TLabel")
            self.metric_labels["Pipeline status"].configure(style="MetricValueGood.TLabel")

        if success_rate >= 0.95:
            self.metric_labels["Success rate (24h)"].configure(style="MetricValueGood.TLabel")
        elif success_rate >= 0.85:
            self.metric_labels["Success rate (24h)"].configure(style="MetricValueWarn.TLabel")
        else:
            self.metric_labels["Success rate (24h)"].configure(style="MetricValueBad.TLabel")

        try:
            error_budget_num = float(error_budget)
        except Exception:
            error_budget_num = -1.0
        if error_budget_num >= 3:
            self.metric_labels["Error budget"].configure(style="MetricValueGood.TLabel")
        elif error_budget_num >= 1:
            self.metric_labels["Error budget"].configure(style="MetricValueWarn.TLabel")
        else:
            self.metric_labels["Error budget"].configure(style="MetricValueBad.TLabel")

        try:
            avg_quality_num = float(avg_quality)
        except Exception:
            avg_quality_num = 0.0
        if avg_quality_num >= 0.8:
            self.metric_labels["Average quality"].configure(style="MetricValueGood.TLabel")
        elif avg_quality_num >= 0.5:
            self.metric_labels["Average quality"].configure(style="MetricValueWarn.TLabel")
        else:
            self.metric_labels["Average quality"].configure(style="MetricValueBad.TLabel")

        self.metric_labels["Degraded sections"].configure(
            style="MetricValueWarn.TLabel" if degraded_sections else "MetricValueGood.TLabel"
        )
        self.metric_labels["Services"].configure(
            style="MetricValueBad.TLabel" if has_critical else "MetricValueWarn.TLabel" if has_warning else "MetricValueGood.TLabel"
        )

        query_diagnostics = dashboard_payload.get("query_diagnostics", {}) if isinstance(dashboard_payload, dict) else {}
        failing_queries = []
        if isinstance(query_diagnostics, dict):
            for key, value in query_diagnostics.items():
                status = str(value.get("status", "")) if isinstance(value, dict) else ""
                if status and status != "ok":
                    failing_queries.append(f"{key}:{status}")

        insight_lines = [
            f"Status: {status_text}",
            f"Message: {status_message or '-'}",
            f"Dominant signal: {top_reason or 'none'}",
            f"Success rate 24h: {success_rate * 100:.1f}%",
            f"Services: {services_text}",
        ]
        if failing_queries:
            insight_lines.append("Diagnostics: " + ", ".join(failing_queries))
        if errors:
            insight_lines.append("API errors: " + " | ".join(errors))

        self.insight_box.configure(state="normal")
        self.insight_box.delete("1.0", tk.END)
        self.insight_box.insert(tk.END, "\n".join(insight_lines))
        self.insight_box.configure(state="disabled")

        overview = {
            "status_message": status_message,
            "dominant_signal": top_reason,
            "slo_summary": slo_summary,
            "timeline_summary": timeline_summary,
            "query_diagnostics": query_diagnostics,
            "errors": errors,
        }

        self._write_json(self.overview_box, overview)
        self._write_json(self.agents_box, {"agents_status": agents_payload, "intel_report": intel_payload})
        self._write_json(self.raw_box, payloads)

        now_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.refresh_meta_label.configure(text=f"Last refresh: {now_label}")

        if errors:
            self.app.set_status("Dashboard updated with partial errors")
        else:
            self.app.set_status("Dashboard updated")

        self._schedule_next_refresh()
    def _run_one_click_agent(self) -> None:
        try:
            payload = self.app.api.run_agents_one_click()
        except Exception as exc:
            messagebox.showerror("Agent run failed", _friendly_api_error(exc, self.app.api.base_url))
            return

        self._write_json(self.agents_box, {"run_agents_one_click": payload})
        self.app.set_status("One-click agent run triggered")
        self.refresh()

    def _launch_intel(self) -> None:
        raw_url = simpledialog.askstring(
            "Launch Intel Mission",
            "Optional seed URL (leave empty to use backend defaults):",
            parent=self,
        )
        urls = [raw_url.strip()] if raw_url and raw_url.strip() else []

        try:
            payload = self.app.api.launch_intel_mission(urls=urls, force_rescout=False, trigger_now=True)
        except Exception as exc:
            messagebox.showerror("Intel launch failed", _friendly_api_error(exc, self.app.api.base_url))
            return

        self._write_json(self.agents_box, {"launch_intel": payload})
        self.app.set_status("Intel mission launched")
        self.refresh()

    @staticmethod
    def _write_json(widget: ScrolledText, payload: object) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, json.dumps(payload, indent=2, ensure_ascii=True))
        widget.configure(state="disabled")


class OnboardingDialog(tk.Toplevel):
    def __init__(self, app: CtoaDesktopApp, return_to: str) -> None:
        super().__init__(app)
        self.app = app
        self.return_to = app._resolve_return_target(return_to)

        self.title("CTOA Guided Onboarding")
        self.geometry("760x560")
        self.minsize(700, 500)
        self.transient(app)
        self.configure(bg=app._palette.get("bg", "#eef3fa"))

        self.protocol("WM_DELETE_WINDOW", self._close)

        shell = ttk.Frame(self, style="Root.TFrame", padding=12)
        shell.pack(fill="both", expand=True)

        card = ttk.Frame(shell, style="Card.TFrame", padding=(20, 18))
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Guided Onboarding", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Krotka trasa: polaczenie API, konto, dashboard i skroty operacyjne.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        steps_wrap = ttk.Frame(card, style="Surface.TFrame")
        steps_wrap.pack(fill="both", expand=True)
        steps_wrap.columnconfigure(0, weight=1)
        steps_wrap.columnconfigure(1, weight=1)

        step_one = ttk.Frame(steps_wrap, style="StepCard.TFrame", padding=(12, 10))
        step_one.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        ttk.Label(step_one, text="1. Ustaw endpoint", style="StepTitle.TLabel").pack(anchor="w")
        ttk.Label(
            step_one,
            text="Skonfiguruj local, stage i prod. Po zmianie wykonaj Ping API.",
            style="StepBody.TLabel",
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(3, 8))
        ttk.Button(step_one, text="Open Endpoint Profiles", command=self._open_profiles).pack(anchor="w")

        step_two = ttk.Frame(steps_wrap, style="StepCard.TFrame", padding=(12, 10))
        step_two.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        ttk.Label(step_two, text="2. Konto i autoryzacja", style="StepTitle.TLabel").pack(anchor="w")
        ttk.Label(
            step_two,
            text="Jesli nie masz konta, utworz operatora i zaloguj sie przez ekran Sign In.",
            style="StepBody.TLabel",
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(3, 8))
        ttk.Button(step_two, text="Create Account", command=self._open_register).pack(anchor="w")

        step_three = ttk.Frame(steps_wrap, style="StepCard.TFrame", padding=(12, 10))
        step_three.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 8))
        ttk.Label(step_three, text="3. Dashboard hierarchy", style="StepTitle.TLabel").pack(anchor="w")
        ttk.Label(
            step_three,
            text="Najpierw health banner, potem karty metryk, dopiero potem szczegolowy JSON.",
            style="StepBody.TLabel",
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(3, 8))
        ttk.Button(step_three, text="Go to Dashboard", command=self._open_dashboard).pack(anchor="w")

        step_four = ttk.Frame(steps_wrap, style="StepCard.TFrame", padding=(12, 10))
        step_four.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 8))
        ttk.Label(step_four, text="4. Skroty klawiaturowe", style="StepTitle.TLabel").pack(anchor="w")
        ttk.Label(
            step_four,
            text="F5/Ctrl+R refresh | Ctrl+1/2/3 taby | Ctrl+E endpoint | Ctrl+Shift+A admin | Ctrl+Q logout | Ctrl+T theme",
            style="StepBody.TLabel",
            wraplength=300,
            justify="left",
        ).pack(anchor="w", pady=(3, 8))
        ttk.Button(step_four, text="Mark Onboarding Complete", style="Primary.TButton", command=self._complete).pack(anchor="w")

        footer = ttk.Frame(card, style="Surface.TFrame")
        footer.pack(fill="x", pady=(4, 0))
        ttk.Button(footer, text="Close", command=self._close).pack(side="right")

        self.grab_set()
        self.focus_set()

    def _complete(self) -> None:
        self.app.settings.onboarding_completed = True
        _save_settings(self.app.settings)
        self.app.set_status("Onboarding marked as completed")
        self._close()

    def _open_profiles(self) -> None:
        self._close()
        back_target = "dashboard" if self.app.auth else "login"
        self.app.show_endpoint_config(return_to=back_target)

    def _open_register(self) -> None:
        self._close()
        self.app.show_register(self.app.settings.base_url)

    def _open_dashboard(self) -> None:
        self._close()
        if self.app.auth is not None:
            self.app.show_dashboard()
        else:
            self.app.show_login(self.app.settings.base_url)

    def _close(self) -> None:
        if self.winfo_exists():
            self.destroy()

class AdminConsoleFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp) -> None:
        super().__init__(app, padding=8, style="Root.TFrame")
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell, style="Card.TFrame", padding=(18, 16))
        header.grid(row=0, column=0, sticky="ew")

        ttk.Label(header, text="Admin Console", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Owner account only. Executes /api/command under backend guardrails.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        self.command_var = tk.StringVar(value="")

        row = ttk.Frame(header, style="Surface.TFrame")
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Command", style="Field.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=self.command_var, width=90).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(row, text="Run", style="Primary.TButton", command=self.run_command).pack(side="left")

        actions = ttk.Frame(header, style="Surface.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Load Presets", command=self.load_presets).pack(side="left")
        ttk.Button(actions, text="Back to Dashboard", command=self.app.show_dashboard).pack(side="left", padx=(10, 0))

        workbench = ttk.Frame(shell, style="Card.TFrame", padding=(14, 14))
        workbench.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        workbench.columnconfigure(0, weight=2)
        workbench.columnconfigure(1, weight=3)
        workbench.rowconfigure(0, weight=1)

        palette = self.app._palette
        code_bg = palette.get("code_bg", "#f7fbff")
        code_fg = palette.get("code_fg", "#1c2c40")

        left = ttk.Frame(workbench, style="Surface.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Allowed presets", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.preset_list = tk.Listbox(
            left,
            width=52,
            height=26,
            relief="solid",
            borderwidth=1,
            background=code_bg,
            foreground=code_fg,
            selectbackground=palette.get("accent", "#1f76cc"),
            selectforeground=palette.get("hero_text", "#ffffff"),
            activestyle="none",
        )
        self.preset_list.grid(row=1, column=0, sticky="nsew")
        self.preset_list.bind("<<ListboxSelect>>", self._on_preset_selected)

        right = ttk.Frame(workbench, style="Surface.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="Result output", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.output_box = ScrolledText(right, wrap="word", font=("Consolas", 10), height=26)
        self.output_box.grid(row=1, column=0, sticky="nsew")
        self.output_box.configure(background=code_bg, foreground=code_fg, insertbackground=code_fg, relief="flat", borderwidth=0)

        self._enforce_owner_guard()
        self.load_presets()
    def _enforce_owner_guard(self) -> None:
        role = self.app.auth.role if self.app.auth else "operator"
        if role == "owner":
            return
        self.command_var.set("")
        self.output_box.insert(tk.END, "Access denied: owner role required.\n")

    def load_presets(self) -> None:
        try:
            presets = self.app.api.presets()
        except Exception as exc:
            messagebox.showerror("Load presets failed", _friendly_api_error(exc, self.app.api.base_url))
            return

        self.preset_list.delete(0, tk.END)
        for cmd in presets:
            self.preset_list.insert(tk.END, cmd)

    def _on_preset_selected(self, _: object) -> None:
        selected = self.preset_list.curselection()
        if not selected:
            return
        value = self.preset_list.get(selected[0])
        self.command_var.set(value)

    def run_command(self) -> None:
        if not self.command_var.get().strip():
            messagebox.showwarning("No command", "Pick or type a command first.")
            return

        try:
            result = self.app.api.run_command(self.command_var.get().strip())
        except Exception as exc:
            messagebox.showerror("Command failed", _friendly_api_error(exc, self.app.api.base_url))
            return

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, json.dumps(result, indent=2, ensure_ascii=True))
        self.output_box.configure(state="disabled")


def _draw_thematic_banner(
    canvas: tk.Canvas,
    width: int,
    height: int,
    palette: dict[str, str] | None = None,
) -> None:
    safe_w = max(180, int(width or 0))
    safe_h = max(100, int(height or 0))
    p = palette or THEME_PALETTES["arcane_night"]

    canvas.configure(background=p.get("hero", "#22345b"))
    canvas.delete("all")

    layers = [
        p.get("hero_deep", "#182542"),
        p.get("hero", "#22345b"),
        p.get("accent_active", "#2f87e6"),
        p.get("accent", "#4ea3ff"),
        p.get("hero_soft", "#c8d5ef"),
    ]
    stripe_h = max(1, safe_h // len(layers))
    for idx, color in enumerate(layers):
        y0 = idx * stripe_h
        y1 = safe_h if idx == len(layers) - 1 else (idx + 1) * stripe_h
        canvas.create_rectangle(0, y0, safe_w, y1, fill=color, outline="")

    moon_x = int(safe_w * 0.82)
    moon_y = int(safe_h * 0.26)
    moon_r = max(16, min(32, safe_h // 6))
    canvas.create_oval(
        moon_x - moon_r,
        moon_y - moon_r,
        moon_x + moon_r,
        moon_y + moon_r,
        fill=p.get("hero_text", "#f2f6ff"),
        outline="",
    )
    canvas.create_oval(
        moon_x - moon_r + 10,
        moon_y - moon_r + 2,
        moon_x + moon_r + 10,
        moon_y + moon_r + 2,
        fill=p.get("hero", "#22345b"),
        outline="",
    )

    ridge_base = int(safe_h * 0.66)
    ridge_a = p.get("hero_deep", "#182542")
    ridge_b = p.get("hero", "#22345b")
    for idx in range(6):
        x0 = int((safe_w / 6) * idx) - 24
        x1 = x0 + int(safe_w / 4)
        peak = ridge_base - (24 + (idx % 3) * 14)
        fill = ridge_a if idx % 2 == 0 else ridge_b
        canvas.create_polygon(x0, safe_h, x1, safe_h, (x0 + x1) // 2, peak, fill=fill, outline="")

    path_points = [
        (int(safe_w * 0.18), safe_h),
        (int(safe_w * 0.32), int(safe_h * 0.78)),
        (int(safe_w * 0.46), int(safe_h * 0.72)),
        (int(safe_w * 0.62), int(safe_h * 0.66)),
        (int(safe_w * 0.78), int(safe_h * 0.6)),
    ]
    for idx in range(len(path_points) - 1):
        x0, y0 = path_points[idx]
        x1, y1 = path_points[idx + 1]
        canvas.create_line(
            x0,
            y0,
            x1,
            y1,
            fill=p.get("warn", "#efc25e"),
            width=3,
            capstyle=tk.ROUND,
        )

    rune_color = p.get("hero_text", "#f2f6ff")
    for idx in range(4):
        cx = int(safe_w * (0.14 + idx * 0.2))
        cy = int(safe_h * 0.28)
        r = 12
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=rune_color, width=2)
        canvas.create_line(cx - 6, cy, cx + 6, cy, fill=rune_color, width=2)
        canvas.create_line(cx, cy - 6, cx, cy + 6, fill=rune_color, width=2)

def _labeled_entry(parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, show: str = "") -> ttk.Entry:
    ttk.Label(parent, text=label, style="Field.TLabel").grid(row=row, column=0, sticky="w", pady=4)
    entry = ttk.Entry(parent, textvariable=variable, width=62, show=show)
    entry.grid(row=row, column=1, sticky="we", pady=4, padx=(8, 0))
    parent.columnconfigure(1, weight=1)
    return entry


def _toggle_password_entry(form: ttk.Frame, reveal: bool, row: int) -> None:
    for child in form.winfo_children():
        if isinstance(child, ttk.Entry):
            info = child.grid_info()
            if int(info.get("row", -1)) == row:
                child.configure(show="" if reveal else "*")


def main() -> None:
    app = CtoaDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()













































