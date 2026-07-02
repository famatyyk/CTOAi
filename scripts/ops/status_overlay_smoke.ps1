param(
    [int]$DurationMs = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing repo-local Python at $python. Create the virtual environment with: python -m venv .venv"
}

& $python -c @"
import tkinter as tk
from bot.overlay.status_overlay import OverlayApp

root = tk.Tk()
app = OverlayApp(root)
app.refresh()
root.after($DurationMs, root.destroy)
root.after(200, lambda: print('status-overlay-smoke-ok'))
root.mainloop()
"@ | Out-Host
