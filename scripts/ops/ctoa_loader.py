#!/usr/bin/env python3
"""CTOA Live Target Loader CLI.

This script is intended to be packaged as a Windows EXE (PyInstaller)
and used by operators to quickly:
- list live targets,
- run source -> target sync,
- open a specific target directory,
- export a target manifest to JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
LIVE_SOURCE = Path(os.environ.get("CTOA_LIVE_TARGETS_DIR", str(ROOT / "runtime" / "live-targets")))
LIVE_TARGET = Path(os.environ.get("CTOA_BOT_LIVE_ROOT", str(ROOT / "runtime" / "bot-live")))
SYNC_SCRIPT = ROOT / "scripts" / "ops" / "sync-live-targets.py"


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _target_candidates(name: str) -> list[str]:
    raw = (name or "").strip()
    if not raw:
        return []

    candidates: list[str] = []

    def add(value: str) -> None:
        v = value.strip()
        if v and v not in candidates:
            candidates.append(v)

    normalized_path = raw.replace("\\", "/")
    add(normalized_path)
    if "/" in normalized_path:
        add(normalized_path.split("/")[0])

    parse_input = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(parse_input)
    host = (parsed.netloc or "").strip().lower()
    scheme = (parsed.scheme or "https").strip().lower()
    if host:
        host_slug = _slugify(host)
        add(f"{scheme}-{host_slug}")
        add(f"https-{host_slug}")
        add(host_slug)

    add(_slugify(raw))
    return candidates


def _resolve_target_dir(root: Path, name: str) -> Path | None:
    root = Path(root)
    for candidate in _target_candidates(name):
        probe = root / candidate
        if probe.exists() and probe.is_dir():
            return probe

    host_like = _slugify((name or "").replace("\\", "/").split("/")[0])
    if host_like and root.exists():
        matches = [d for d in root.iterdir() if d.is_dir() and host_like in d.name.lower()]
        if len(matches) == 1:
            return matches[0]

    return None


def _list_targets(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not root.exists():
        return items
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        manifest = d / "live-manifest.json"
        data: dict[str, Any] = {}
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                data = {}
        items.append(
            {
                "name": d.name,
                "path": str(d),
                "has_manifest": manifest.exists(),
                "url": data.get("url", ""),
                "status": data.get("status", ""),
            }
        )
    return items


def _sync_with_output(source: Path, target: Path) -> tuple[int, str, str]:
    if not SYNC_SCRIPT.exists():
        err = json.dumps({"ok": False, "error": f"missing sync script: {SYNC_SCRIPT}"}, ensure_ascii=True)
        return 2, "", err

    cmd = [
        sys.executable,
        str(SYNC_SCRIPT),
        "--source",
        str(source),
        "--target",
        str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", check=False)
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _sync(source: Path, target: Path) -> int:
    code, stdout, stderr = _sync_with_output(source, target)
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CTOA loader helper")
    parser.add_argument("--source", default=str(LIVE_SOURCE), help="Live source directory")
    parser.add_argument("--target", default=str(LIVE_TARGET), help="Live target directory")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List targets")
    sub.add_parser("sync", help="Sync source -> target")

    p_open = sub.add_parser("open", help="Open target directory in Explorer")
    p_open.add_argument("name", help="Target directory name")

    p_export = sub.add_parser("export", help="Export target manifest")
    p_export.add_argument("name", help="Target directory name")
    p_export.add_argument("--out", required=True, help="Output JSON path")
    return parser


def _run_cli(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    source = Path(args.source)
    target = Path(args.target)

    if args.command == "list":
        data = {"ok": True, "source": str(source), "target": str(target), "items": _list_targets(target)}
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return 0

    if args.command == "sync":
        return _sync(source, target)

    if args.command == "open":
        return _open_target_dir(target, args.name)

    if args.command == "export":
        return _export_manifest(target, args.name, Path(args.out))

    return 1


def _launch_gui() -> int:
    root = tk.Tk()
    root.title("CTOA Loader")
    root.geometry("920x620")

    source_var = tk.StringVar(value=str(LIVE_SOURCE))
    target_var = tk.StringVar(value=str(LIVE_TARGET))
    name_var = tk.StringVar()
    out_var = tk.StringVar(value=str(ROOT / "runtime" / "exports" / "live-manifest.json"))

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Source directory:").grid(row=0, column=0, sticky="w")
    source_entry = ttk.Entry(frame, textvariable=source_var, width=90)
    source_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
    ttk.Button(
        frame,
        text="Browse",
        command=lambda: source_var.set(filedialog.askdirectory() or source_var.get()),
    ).grid(row=1, column=1, sticky="ew")

    ttk.Label(frame, text="Target directory:").grid(row=2, column=0, sticky="w", pady=(8, 0))
    target_entry = ttk.Entry(frame, textvariable=target_var, width=90)
    target_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8))
    ttk.Button(
        frame,
        text="Browse",
        command=lambda: target_var.set(filedialog.askdirectory() or target_var.get()),
    ).grid(row=3, column=1, sticky="ew")

    ttk.Label(frame, text="Target name (for Open/Export):").grid(row=4, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(frame, textvariable=name_var, width=50).grid(row=5, column=0, sticky="w")

    ttk.Label(frame, text="Export file path:").grid(row=6, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(frame, textvariable=out_var, width=90).grid(row=7, column=0, sticky="ew", padx=(0, 8))
    ttk.Button(
        frame,
        text="Save as",
        command=lambda: out_var.set(
            filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            or out_var.get()
        ),
    ).grid(row=7, column=1, sticky="ew")

    output = tk.Text(frame, height=20, wrap="word")
    output.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(10, 0))

    def write_output(text: str) -> None:
        output.insert("end", text + "\n")
        output.see("end")

    def list_targets() -> None:
        target = Path(target_var.get())
        data = {"ok": True, "source": source_var.get(), "target": target_var.get(), "items": _list_targets(target)}
        write_output(json.dumps(data, ensure_ascii=True, indent=2))

    def sync_targets() -> None:
        source = Path(source_var.get())
        target = Path(target_var.get())
        write_output("[sync] started...")
        code, stdout, stderr = _sync_with_output(source, target)
        if stdout:
            write_output(stdout)
        if stderr:
            write_output(stderr)
        if code == 0:
            write_output("[sync] finished: ok")
            messagebox.showinfo("CTOA Loader", "Sync completed.")
        else:
            write_output(f"[sync] finished: error ({code})")
            messagebox.showerror("CTOA Loader", f"Sync failed (exit code {code}).")

    def open_target() -> None:
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("CTOA Loader", "Provide target name first.")
            return
        target = _resolve_target_dir(Path(target_var.get()), name)
        if target is None:
            messagebox.showerror("CTOA Loader", f"Target not found: {name}")
            return
        os.startfile(str(target))  # type: ignore[attr-defined]
        write_output(json.dumps({"ok": True, "opened": str(target)}, ensure_ascii=True))

    def export_manifest() -> None:
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("CTOA Loader", "Provide target name first.")
            return
        target = Path(target_var.get())
        out_path = Path(out_var.get())
        code = _export_manifest(target, name, out_path)
        if code == 0:
            write_output(json.dumps({"ok": True, "target": name, "export": str(out_path)}, ensure_ascii=True))
            messagebox.showinfo("CTOA Loader", f"Manifest exported to:\n{out_path}")
        else:
            write_output(json.dumps({"ok": False, "target": name, "export": str(out_path)}, ensure_ascii=True))
            messagebox.showerror("CTOA Loader", "Export failed. Check output log.")

    buttons = ttk.Frame(frame)
    buttons.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ttk.Button(buttons, text="List", command=list_targets).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Sync", command=sync_targets).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Open", command=open_target).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Export", command=export_manifest).pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Clear Log", command=lambda: output.delete("1.0", "end")).pack(side="left")

    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(9, weight=1)

    root.mainloop()
    return 0


def _open_target_dir(root: Path, name: str) -> int:
    target = _resolve_target_dir(root, name)
    if target is None:
        print(json.dumps({"ok": False, "error": f"target not found: {name}"}, ensure_ascii=True))
        return 1
    try:
        os.startfile(str(target))  # type: ignore[attr-defined]
        print(json.dumps({"ok": True, "opened": str(target)}, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True))
        return 1


def _export_manifest(root: Path, name: str, out_path: Path) -> int:
    target = _resolve_target_dir(root, name)
    if target is None:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"target not found: {name}",
                    "candidates": _target_candidates(name),
                },
                ensure_ascii=True,
            )
        )
        return 1

    manifest = target / "live-manifest.json"
    if not manifest.exists():
        print(json.dumps({"ok": False, "error": f"manifest not found: {manifest}"}, ensure_ascii=True))
        return 1

    payload = manifest.read_text(encoding="utf-8", errors="replace")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "target": name, "export": str(out_path)}, ensure_ascii=True))
    return 0


def main() -> int:
    # No arguments -> GUI mode for double-click usage.
    if len(sys.argv) == 1:
        return _launch_gui()
    return _run_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
