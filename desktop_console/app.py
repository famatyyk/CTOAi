"""Desktop GUI entrypoint for CTOA operations."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

try:
    from desktop_console.api_client import ApiError, AuthContext, CtoaApiClient
except ImportError:
    from api_client import ApiError, AuthContext, CtoaApiClient


class CtoaDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CTOA Desktop Console")
        self.geometry("1120x760")
        self.minsize(960, 680)

        self.api = CtoaApiClient("http://127.0.0.1:8787")
        self.auth: AuthContext | None = None
        self._frame: ttk.Frame | None = None

        self.show_login()

    def show_login(self, preset_url: str = "") -> None:
        self._mount(LoginFrame(self, preset_url=preset_url or self.api.base_url))

    def show_register(self, preset_url: str = "") -> None:
        self._mount(RegisterFrame(self, preset_url=preset_url or self.api.base_url))

    def show_dashboard(self) -> None:
        self._mount(DashboardFrame(self))

    def show_admin_console(self) -> None:
        if not self.auth or self.auth.role != "owner":
            messagebox.showwarning("Access denied", "Admin console is available only for owner role.")
            return
        self._mount(AdminConsoleFrame(self))

    def login(self, base_url: str, username: str, password: str) -> None:
        self.api.set_base_url(base_url)
        self.auth = self.api.login(username=username, password=password)

    def register(self, base_url: str, username: str, password: str, registration_code: str) -> None:
        self.api.set_base_url(base_url)
        self.api.register(username=username, password=password, registration_code=registration_code)

    def logout(self) -> None:
        try:
            self.api.logout()
        except Exception:
            pass
        self.auth = None
        self.show_login()

    def _mount(self, frame: ttk.Frame) -> None:
        if self._frame is not None:
            self._frame.destroy()
        self._frame = frame
        self._frame.pack(fill="both", expand=True)


class LoginFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp, preset_url: str) -> None:
        super().__init__(app, padding=20)
        self.app = app

        ttk.Label(self, text="CTOA Windows Client", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="Log in to access live dashboard and operations.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(self)
        form.pack(anchor="w", fill="x")

        self.base_url = tk.StringVar(value=preset_url)
        self.username = tk.StringVar(value="")
        self.password = tk.StringVar(value="")

        _labeled_entry(form, "API Base URL", self.base_url, row=0)
        _labeled_entry(form, "Username", self.username, row=1)
        _labeled_entry(form, "Password", self.password, row=2, show="*")

        actions = ttk.Frame(self)
        actions.pack(anchor="w", pady=(16, 0))
        ttk.Button(actions, text="Login", command=self._login).pack(side="left")
        ttk.Button(actions, text="Create Account", command=self._open_register).pack(side="left", padx=(12, 0))

    def _login(self) -> None:
        if not self.username.get().strip() or not self.password.get().strip():
            messagebox.showerror("Missing data", "Username and password are required.")
            return
        try:
            self.app.login(
                base_url=self.base_url.get(),
                username=self.username.get().strip(),
                password=self.password.get(),
            )
        except ApiError as exc:
            messagebox.showerror("Login failed", str(exc))
            return
        self.app.show_dashboard()

    def _open_register(self) -> None:
        self.app.show_register(preset_url=self.base_url.get())


class RegisterFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp, preset_url: str) -> None:
        super().__init__(app, padding=20)
        self.app = app

        ttk.Label(self, text="Create Account", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="New users are registered as operator role.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(self)
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

        actions = ttk.Frame(self)
        actions.pack(anchor="w", pady=(16, 0))
        ttk.Button(actions, text="Create Account", command=self._register).pack(side="left")
        ttk.Button(actions, text="Back to Login", command=lambda: self.app.show_login(self.base_url.get())).pack(
            side="left", padx=(12, 0)
        )

    def _register(self) -> None:
        username = self.username.get().strip()
        if not username:
            messagebox.showerror("Missing data", "Username is required.")
            return
        if self.password.get() != self.password_confirm.get():
            messagebox.showerror("Password mismatch", "Passwords must match.")
            return
        try:
            self.app.register(
                base_url=self.base_url.get(),
                username=username,
                password=self.password.get(),
                registration_code=self.registration_code.get().strip(),
            )
        except ApiError as exc:
            messagebox.showerror("Registration failed", str(exc))
            return

        messagebox.showinfo("Account created", "Account created successfully. You can now sign in.")
        self.app.show_login(self.base_url.get())


class DashboardFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp) -> None:
        super().__init__(app, padding=20)
        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x")

        ttk.Label(header, text="Live Dashboard", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Button(header, text="Refresh", command=self.refresh).pack(side="right")

        user = app.auth.username if app.auth else "unknown"
        role = app.auth.role if app.auth else "unknown"

        self.identity_label = ttk.Label(self, text=f"User: {user} | Role: {role}", font=("Segoe UI", 10))
        self.identity_label.pack(anchor="w", pady=(8, 12))

        actions = ttk.Frame(self)
        actions.pack(anchor="w", pady=(0, 12))
        self.admin_button = ttk.Button(actions, text="Open Admin Console", command=self.app.show_admin_console)
        self.admin_button.pack(side="left")
        ttk.Button(actions, text="Logout", command=self.app.logout).pack(side="left", padx=(12, 0))

        self.status_box = ScrolledText(self, wrap="word", font=("Consolas", 10), height=28)
        self.status_box.pack(fill="both", expand=True)

        self._sync_role_controls()
        self.refresh()

    def _sync_role_controls(self) -> None:
        role = self.app.auth.role if self.app.auth else "operator"
        state = "normal" if role == "owner" else "disabled"
        self.admin_button.configure(state=state)

    def refresh(self) -> None:
        try:
            me = self.app.api.me()
            self.app.auth = me
            status_payload = self.app.api.status()
        except ApiError as exc:
            messagebox.showerror("Dashboard refresh failed", str(exc))
            return

        self.identity_label.configure(text=f"User: {me.username} | Role: {me.role} | Auth: {me.auth_mode}")
        self._sync_role_controls()

        self.status_box.configure(state="normal")
        self.status_box.delete("1.0", tk.END)
        self.status_box.insert(tk.END, json.dumps(status_payload, indent=2, ensure_ascii=True))
        self.status_box.configure(state="disabled")


class AdminConsoleFrame(ttk.Frame):
    def __init__(self, app: CtoaDesktopApp) -> None:
        super().__init__(app, padding=20)
        self.app = app

        ttk.Label(self, text="Admin Console", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            self,
            text="Owner account only. Executes /api/command under backend guardrails.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 12))

        self.command_var = tk.StringVar(value="")

        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Command").pack(side="left")
        ttk.Entry(row, textvariable=self.command_var, width=110).pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(row, text="Run", command=self.run_command).pack(side="left")

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Load Presets", command=self.load_presets).pack(side="left")
        ttk.Button(actions, text="Back to Dashboard", command=self.app.show_dashboard).pack(side="left", padx=(10, 0))

        split = ttk.Frame(self)
        split.pack(fill="both", expand=True)

        left = ttk.Frame(split)
        left.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(left, text="Allowed presets").pack(anchor="w")
        self.preset_list = tk.Listbox(left, width=52, height=26)
        self.preset_list.pack(fill="y", expand=True)
        self.preset_list.bind("<<ListboxSelect>>", self._on_preset_selected)

        right = ttk.Frame(split)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Result output").pack(anchor="w")
        self.output_box = ScrolledText(right, wrap="word", font=("Consolas", 10), height=26)
        self.output_box.pack(fill="both", expand=True)

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
        except ApiError as exc:
            messagebox.showerror("Load presets failed", str(exc))
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
        except ApiError as exc:
            messagebox.showerror("Command failed", str(exc))
            return

        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, json.dumps(result, indent=2, ensure_ascii=True))
        self.output_box.configure(state="disabled")


def _labeled_entry(parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, show: str = "") -> None:
    ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
    ttk.Entry(parent, textvariable=variable, width=80, show=show).grid(row=row, column=1, sticky="we", pady=4, padx=(8, 0))
    parent.columnconfigure(1, weight=1)


def main() -> None:
    app = CtoaDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
