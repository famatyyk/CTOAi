#!/usr/bin/env python3
import os
import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "mobile_console" / "static"
AUDIT_LOG = ROOT / "logs" / "mobile-console-audit.log"

app = FastAPI(title="CTOA Mobile Console", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    timeout: int = Field(default=20, ge=1, le=120)
    cwd: Optional[str] = None


def _mobile_token() -> str:
    token = os.getenv("CTOA_MOBILE_TOKEN", "")
    if not token:
        raise RuntimeError("Missing CTOA_MOBILE_TOKEN")
    return token


def _full_access() -> bool:
    return os.getenv("CTOA_MOBILE_FULL_ACCESS", "false").lower() == "true"


def _allowed_commands() -> List[str]:
    return [
        "systemctl status ctoa-runner.timer --no-pager -l",
        "systemctl status ctoa-report.timer --no-pager -l",
        "systemctl status ctoa-health-live.service --no-pager -l",
        "tail -n 80 /opt/ctoa/logs/runner.log",
        "tail -n 80 /opt/ctoa/logs/health-live.log",
        "cd /opt/ctoa; CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-004.yaml python3 runner/runner.py report",
        "cd /opt/ctoa; python3 runner/drift_checker.py",
        "df -h",
    ]


def _require_token(x_ctoa_token: Optional[str] = Header(default=None)) -> None:
    expected = _mobile_token()
    if x_ctoa_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _run(cmd: str, timeout: int = 20, cwd: Optional[str] = None) -> dict:
    proc = subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
    )
    return {
        "code": proc.returncode,
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-20000:],
    }


def _audit(request: Request, command: str, code: int) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "ip": request.client.host if request.client else "unknown",
        "path": request.url.path,
        "command": command,
        "code": code,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
def health(_: None = Depends(_require_token)) -> dict:
    return {"ok": True, "full_access": _full_access()}


@app.get("/api/presets")
def presets(_: None = Depends(_require_token)) -> dict:
    return {"commands": _allowed_commands()}


@app.get("/api/status")
def status(_: None = Depends(_require_token)) -> dict:
    checks = {
        "runner_timer": "systemctl is-active ctoa-runner.timer",
        "report_timer": "systemctl is-active ctoa-report.timer",
        "health_service": "systemctl is-active ctoa-health-live.service",
    }
    out = {}
    for key, cmd in checks.items():
        res = _run(cmd, timeout=10)
        out[key] = (res["stdout"].strip() or res["stderr"].strip() or "unknown")

    disk = _run("df -h /", timeout=10)
    report = _run(
        "cd /opt/ctoa; CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-004.yaml python3 runner/runner.py report",
        timeout=20,
    )

    return {
        "services": out,
        "disk": disk,
        "report": report,
    }


@app.get("/api/logs")
def logs(
    target: str = Query(default="runner", pattern="^(runner|health|report)$"),
    lines: int = Query(default=120, ge=10, le=500),
    _: None = Depends(_require_token),
) -> dict:
    mapping = {
        "runner": "/opt/ctoa/logs/runner.log",
        "health": "/opt/ctoa/logs/health-live.log",
        "report": "/opt/ctoa/logs/runner.log",
    }
    path = mapping[target]
    cmd = f"tail -n {lines} {path}"
    return _run(cmd, timeout=10)


@app.post("/api/command")
def command(req: CommandRequest, request: Request, _: None = Depends(_require_token)) -> dict:
    cmd = req.command.strip()

    if not _full_access():
        allowed = _allowed_commands()
        if cmd not in allowed:
            raise HTTPException(
                status_code=403,
                detail="Command not allowed in safe mode. Use one of /api/presets or enable full access.",
            )

    result = _run(cmd, timeout=req.timeout, cwd=req.cwd)
    _audit(request, cmd, int(result.get("code", -1)))
    return result
