"""AGENT 9 / AGENT 3: FastAPI dashboard — live bot stats.

Endpoints:
  GET /          — HTML status page
  GET /stats     — JSON: gold/hr, exp/hr, kills, session_hours
  GET /metrics   — Prometheus text format
  GET /health    — liveness probe

Run: uvicorn bot.dashboard.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations
import time
from pathlib import Path

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, PlainTextResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

from bot.data.telemetry import get_stats
from bot.data.db import get_session_stats, get_connection

_START_TIME = time.time()

if _FASTAPI_AVAILABLE:
    app = FastAPI(title="Tibia Bot Dashboard", version="1.0.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "uptime_s": int(time.time() - _START_TIME)}

    @app.get("/stats")
    def stats():
        """Return live session stats as JSON."""
        s = get_stats()
        return {
            "gold_hr":       s.get("gold_hr", 0),
            "exp_hr":        s.get("exp_hr", 0),
            "kills":         s.get("kills", 0),
            "session_hours": s.get("session_hours", 0),
            "uptime_s":      int(time.time() - _START_TIME),
        }

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics():
        """Prometheus exposition format — scraped by prometheus.yml."""
        s = get_stats()
        lines = [
            "# HELP bot_gold_per_hour Estimated gold earned per hour",
            "# TYPE bot_gold_per_hour gauge",
            f'bot_gold_per_hour {s.get("gold_hr", 0)}',
            "# HELP bot_exp_per_hour Estimated experience per hour",
            "# TYPE bot_exp_per_hour gauge",
            f'bot_exp_per_hour {s.get("exp_hr", 0)}',
            "# HELP bot_kills_total Total kills this session",
            "# TYPE bot_kills_total gauge",
            f'bot_kills_total {s.get("kills", 0)}',
            "# HELP bot_session_hours Session duration in hours",
            "# TYPE bot_session_hours gauge",
            f'bot_session_hours {s.get("session_hours", 0)}',
            "# HELP bot_uptime_seconds Bot process uptime in seconds",
            "# TYPE bot_uptime_seconds gauge",
            f'bot_uptime_seconds {int(time.time() - _START_TIME)}',
        ]
        return "\n".join(lines) + "\n"

    @app.get("/", response_class=HTMLResponse)
    def index():
        """Simple HTML status dashboard — no JS framework needed."""
        s = get_stats()
        uptime_h = (time.time() - _START_TIME) / 3600
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="10">
  <title>Tibia Bot Dashboard</title>
  <style>
    body {{ font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 2rem; }}
    h1   {{ color: #ffd700; }}
    .card {{ background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
             padding: 1rem; margin: 0.5rem 0; display: inline-block; min-width: 180px; }}
    .val  {{ font-size: 2rem; color: #e94560; font-weight: bold; }}
    .lbl  {{ font-size: 0.8rem; color: #a0a0a0; }}
    .grid {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 1rem; }}
  </style>
</head>
<body>
  <h1>🎖️ Tibia Bot — Live Dashboard</h1>
  <p style="color:#888">Auto-refreshes every 10s | <a href="/stats" style="color:#ffd700">/stats JSON</a> | <a href="/metrics" style="color:#ffd700">/metrics Prometheus</a></p>
  <div class="grid">
    <div class="card"><div class="val">{s.get('gold_hr', 0):,}</div><div class="lbl">Gold / hour</div></div>
    <div class="card"><div class="val">{s.get('exp_hr', 0):,}</div><div class="lbl">Exp / hour</div></div>
    <div class="card"><div class="val">{s.get('kills', 0)}</div><div class="lbl">Kills this session</div></div>
    <div class="card"><div class="val">{s.get('session_hours', 0):.2f}h</div><div class="lbl">Session time</div></div>
    <div class="card"><div class="val">{uptime_h:.2f}h</div><div class="lbl">Dashboard uptime</div></div>
  </div>
  <p style="margin-top:2rem; color:#555; font-size:0.75rem">AGENT 9 DevOps Master + AGENT 3 Data Engineer — Sprint 5</p>
</body>
</html>"""
        return html
