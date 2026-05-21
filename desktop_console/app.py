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


def _default_profile_urls() -> dict[str, str]:
    return {
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
        self.geometry("1320x860")
        self.minsize(1120, 740)

        self._configure_styles()

        self.settings = _load_settings()
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

        self.show_login(preset_url=self.settings.base_url)

        if self.settings.check_updates_on_startup:
            self.after(900, lambda: self.check_for_updates(manual=False))

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        palette = {
            "bg": "#edf2f8",
            "surface": "#ffffff",
            "hero": "#0f4c81",
            "hero_text": "#ffffff",
            "hero_soft": "#dcecff",
            "text": "#15253a",
            "muted": "#52627a",
            "metric": "#f4f8fc",
            "status": "#dfe7f2",
            "accent": "#1f76cc",
            "accent_active": "#185f9f",
        }
        self._palette = palette
        self.configure(bg=palette["bg"])

        style.configure("Root.TFrame", background=palette["bg"])
        style.configure("Shell.TFrame", background=palette["bg"])

        style.configure("Card.TFrame", background=palette["surface"], relief="solid", borderwidth=1)
        style.configure("Surface.TFrame", background=palette["surface"])
        style.configure("Hero.TFrame", background=palette["hero"], relief="solid", borderwidth=1)

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
            "Field.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9, "bold"),
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

        style.configure("Primary.TButton", padding=(14, 8), font=("Segoe UI Semibold", 10))
        style.map(
            "Primary.TButton",
            background=[("active", palette["accent_active"]), ("!disabled", palette["accent"])],
            foreground=[("!disabled", "#ffffff")],
        )

        style.configure(
            "Surface.TCheckbutton",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 9),
        )

        style.configure("Dashboard.TNotebook", background=palette["bg"], borderwidth=0)
        style.configure("Dashboard.TNotebook.Tab", padding=(16, 8), font=("Segoe UI Semibold", 10))
        style.map(
            "Dashboard.TNotebook.Tab",
            background=[("selected", palette["surface"]), ("active", "#e7eff8")],
            foreground=[("selected", palette["text"]), ("active", palette["text"])],
        )

        style.configure("StatusBar.TFrame", background=palette["status"], relief="flat")
        style.configure(
            "StatusBar.TLabel",
            background=palette["status"],
            foreground="#344a63",
            font=("Segoe UI", 9),
        )
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

    def show_dashboard(self) -> None:
        self._mount(DashboardFrame(self))

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
        super().__init__(app, padding=8, style="Root.TFrame")
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=5)
        shell.columnconfigure(1, weight=6)
        shell.rowconfigure(0, weight=1)

        hero = ttk.Frame(shell, style="Hero.TFrame", padding=(26, 24))
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        ttk.Label(hero, text="CTOA Control Room", style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            hero,
            text="Secure sign-in to live telemetry, agent orchestration and owner guardrails.",
            style="HeroBody.TLabel",
            justify="left",
            wraplength=360,
        ).pack(anchor="w", pady=(8, 12))
        ttk.Label(hero, text="- Local, stage i prod profiles in one place", style="HeroBody.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(hero, text="- Instant API reachability check before login", style="HeroBody.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(hero, text="- Built-in updater for release rollout", style="HeroBody.TLabel").pack(anchor="w", pady=(4, 0))

        card = ttk.Frame(shell, style="Card.TFrame", padding=(24, 22))
        card.grid(row=0, column=1, sticky="nsew")

        ttk.Label(card, text="Sign In", style="Headline.TLabel").pack(anchor="w")
        ttk.Label(
            card,
            text="Log in to access live dashboard and agent operations.",
            style="Subhead.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        form = ttk.Frame(card, style="Surface.TFrame")
        form.pack(anchor="w", fill="x")

        self.profile_var = tk.StringVar(value=app.settings.endpoint_profile)
        self.base_url = tk.StringVar(value=preset_url)
        self.username = tk.StringVar(value=preset_username)
        self.password = tk.StringVar(value="")
        self.show_password = tk.BooleanVar(value=False)

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

        base_entry = _labeled_entry(form, "API Base URL", self.base_url, row=1)
        user_entry = _labeled_entry(form, "Username", self.username, row=2)
        pass_entry = _labeled_entry(form, "Password", self.password, row=3, show="*")

        ttk.Checkbutton(
            form,
            text="Show password",
            style="Surface.TCheckbutton",
            variable=self.show_password,
            command=lambda: _toggle_password_entry(form, reveal=self.show_password.get(), row=3),
        ).grid(row=4, column=1, sticky="w", pady=(2, 4), padx=(8, 0))

        hint = "Local API: http://127.0.0.1:8787  |  VPS API: http(s)://<vps-host-or-domain>:8787"
        ttk.Label(card, text=hint, style="Subhead.TLabel", wraplength=560, justify="left").pack(anchor="w", pady=(6, 12))

        primary_actions = ttk.Frame(card, style="Surface.TFrame")
        primary_actions.pack(anchor="w")
        ttk.Button(primary_actions, text="Login", style="Primary.TButton", command=self._login).pack(side="left")
        ttk.Button(primary_actions, text="Create Account", command=self._open_register).pack(side="left", padx=(10, 0))

        utility_actions = ttk.Frame(card, style="Surface.TFrame")
        utility_actions.pack(anchor="w", pady=(10, 0))
        ttk.Button(utility_actions, text="Ping API", command=self._ping_api).pack(side="left")
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

        _labeled_entry(form, "Local API URL", self.local_url, row=1)
        _labeled_entry(form, "Stage API URL", self.stage_url, row=2)
        _labeled_entry(form, "Prod API URL", self.prod_url, row=3)

        actions = ttk.Frame(card, style="Surface.TFrame")
        actions.pack(anchor="w", pady=(14, 0))

        ttk.Button(actions, text="Save Profiles", style="Primary.TButton", command=self._save_profiles).pack(side="left")
        ttk.Button(actions, text="Apply Selected", command=self._apply_selected).pack(side="left", padx=(10, 0))
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
        _save_settings(self.app.settings)
        self.app.set_status("Endpoint profiles saved")
        messagebox.showinfo("Saved", "Endpoint profile configuration saved.")

    def _apply_selected(self) -> None:
        local_url, stage_url, prod_url = self._normalized_values()
        self.app.update_profile_urls(local_url=local_url, stage_url=stage_url, prod_url=prod_url)
        selected = self.active_profile.get().strip().lower()

        try:
            applied_url = self.app.apply_endpoint_profile(selected)
        except Exception as exc:
            messagebox.showerror("Apply profile failed", str(exc))
            return

        messagebox.showinfo("Profile applied", f"Active API Base URL: {applied_url}")
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
            payload = tester.health()
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
        super().__init__(app, padding=8, style="Root.TFrame")
        self.app = app
        self._refresh_job: str | None = None

        self.refresh_seconds = tk.IntVar(value=_normalize_refresh_seconds(self.app.settings.refresh_seconds))
        self.auto_refresh = tk.BooleanVar(value=self.app.settings.auto_refresh)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        shell = ttk.Frame(self, style="Shell.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)

        header_card = ttk.Frame(shell, style="Card.TFrame", padding=(18, 16))
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

        tools_actions = ttk.Frame(controls, style="Surface.TFrame")
        tools_actions.pack(anchor="e", pady=(8, 0))
        ttk.Button(
            tools_actions,
            text="Endpoint Profiles",
            command=lambda: self.app.show_endpoint_config(return_to="dashboard"),
        ).pack(side="left")
        ttk.Button(
            tools_actions,
            text="Check updates",
            command=lambda: self.app.check_for_updates(manual=True),
        ).pack(side="left", padx=(10, 0))
        ttk.Button(tools_actions, text="Install update", command=self.app.prompt_update_install).pack(side="left", padx=(8, 0))

        metrics = ttk.Frame(shell, style="Shell.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(12, 10))
        self.metric_vars: dict[str, tk.StringVar] = {}
        metric_names = [
            "Pipeline status",
            "Success rate (24h)",
            "Error budget",
            "Average quality",
            "Degraded sections",
            "Services",
        ]
        for idx, name in enumerate(metric_names):
            row_idx, col_idx = divmod(idx, 3)
            card = ttk.Frame(metrics, style="MetricCard.TFrame", padding=10)
            card.grid(
                row=row_idx,
                column=col_idx,
                sticky="nsew",
                padx=(0 if col_idx == 0 else 8, 0),
                pady=(0 if row_idx == 0 else 8, 0),
            )
            metrics.columnconfigure(col_idx, weight=1)
            ttk.Label(card, text=name, style="MetricName.TLabel").pack(anchor="w")
            var = tk.StringVar(value="-")
            self.metric_vars[name] = var
            ttk.Label(card, textvariable=var, style="MetricValue.TLabel").pack(anchor="w", pady=(4, 0))

        action_row = ttk.Frame(shell, style="Shell.TFrame")
        action_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.admin_button = ttk.Button(action_row, text="Open Admin Console", command=self.app.show_admin_console)
        self.admin_button.pack(side="left")
        ttk.Button(action_row, text="Logout", command=self.app.logout).pack(side="left", padx=(8, 0))

        self.notebook = ttk.Notebook(shell, style="Dashboard.TNotebook")
        self.notebook.grid(row=3, column=0, sticky="nsew")

        overview_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=10)
        agents_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=10)
        raw_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=10)

        self.notebook.add(overview_tab, text="Overview")
        self.notebook.add(agents_tab, text="Agents")
        self.notebook.add(raw_tab, text="Raw JSON")

        code_bg = "#f7fbff"
        code_fg = "#1c2c40"

        self.overview_box = ScrolledText(overview_tab, wrap="word", font=("Consolas", 10), height=20)
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

        self._load_remote_profile()
        self._sync_role_controls()
        self.refresh()
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

    def _sync_role_controls(self) -> None:
        role = self.app.auth.role if self.app.auth else "operator"
        state = "normal" if role == "owner" else "disabled"
        self.admin_button.configure(state=state)
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
        self.metric_vars["Services"].set(" | ".join(services))

        status_message = str(dashboard_payload.get("status_message", ""))
        top_reason = dashboard_payload.get("dominant_signal") if isinstance(dashboard_payload, dict) else None
        overview = {
            "status_message": status_message,
            "dominant_signal": top_reason,
            "slo_summary": slo_summary,
            "timeline_summary": timeline_summary,
            "query_diagnostics": dashboard_payload.get("query_diagnostics", {}),
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

        left = ttk.Frame(workbench, style="Surface.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Allowed presets", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.preset_list = tk.Listbox(left, width=52, height=26, relief="solid", borderwidth=1)
        self.preset_list.grid(row=1, column=0, sticky="nsew")
        self.preset_list.bind("<<ListboxSelect>>", self._on_preset_selected)

        right = ttk.Frame(workbench, style="Surface.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        ttk.Label(right, text="Result output", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.output_box = ScrolledText(right, wrap="word", font=("Consolas", 10), height=26)
        self.output_box.grid(row=1, column=0, sticky="nsew")
        self.output_box.configure(background="#f7fbff", foreground="#1c2c40", insertbackground="#1c2c40", relief="flat", borderwidth=0)

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




