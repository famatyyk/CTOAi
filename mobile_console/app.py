#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import json
import time
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
AUTO_TRAINER_DIR = Path(os.environ.get("CTOA_TRAINING_REPORT_DIR", str(ROOT / "runtime" / "training-reports")))
GENERATED_DIR = Path(os.environ.get("CTOA_GENERATED_DIR", "/opt/ctoa/generated"))

app = FastAPI(title="CTOA Mobile Console", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    timeout: int = Field(default=20, ge=1, le=120)
    cwd: Optional[str] = None


class ServerRegisterRequest(BaseModel):
    url: str = Field(min_length=8, max_length=512)


class IntelMissionRequest(BaseModel):
    urls: list[str] = Field(default_factory=list, max_length=25)
    force_rescout: bool = False
    trigger_now: bool = True


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
        "systemctl status ctoa-mythibia-news-api.service --no-pager -l",
        "systemctl status ctoa-mythibia-news-watcher.timer --no-pager -l",
        "tail -n 80 /opt/ctoa/logs/runner.log",
        "tail -n 80 /opt/ctoa/logs/health-live.log",
        "tail -n 80 /opt/ctoa/logs/mythibia-news-api.log",
        "tail -n 80 /opt/ctoa/logs/mythibia-news-watcher.log",
        "cd /opt/ctoa; CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-004.yaml python3 runner/runner.py report",
        "cd /opt/ctoa; python3 runner/drift_checker.py",
        "df -h",
    ]


def _require_token(x_ctoa_token: Optional[str] = Header(default=None)) -> None:
    expected = _mobile_token()
    if x_ctoa_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _token_valid(x_ctoa_token: Optional[str]) -> bool:
    return bool(x_ctoa_token) and x_ctoa_token == _mobile_token()


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


@app.get("/api/auth/auto-check")
def auth_auto_check(x_ctoa_token: Optional[str] = Header(default=None)) -> dict:
    valid = _token_valid(x_ctoa_token)
    payload = {
        "ok": valid,
        "token_present": bool(x_ctoa_token),
        "token_valid": valid,
        "full_access": _full_access() if valid else False,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if valid:
        timer = _run("systemctl is-active ctoa-agents-orchestrator.timer", timeout=5)
        payload["orchestrator_timer"] = timer["stdout"].strip() or "unknown"
    else:
        payload["hint"] = "Zapisz aktualny CTOA_MOBILE_TOKEN i sprobuj ponownie"
    return payload


@app.get("/api/presets")
def presets(_: None = Depends(_require_token)) -> dict:
    return {"commands": _allowed_commands()}


@app.get("/api/status")
def status(_: None = Depends(_require_token)) -> dict:
    checks = {
        "runner_timer": "systemctl is-active ctoa-runner.timer",
        "report_timer": "systemctl is-active ctoa-report.timer",
        "health_service": "systemctl is-active ctoa-health-live.service",
        "mythibia_watcher_timer": "systemctl is-active ctoa-mythibia-news-watcher.timer",
        "mythibia_api_service": "systemctl is-active ctoa-mythibia-news-api.service",
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

    lab_status = _run(
        "python3 - << 'PY'\nimport yaml\nfrom pathlib import Path\np=Path('/opt/ctoa/labs/tasks/mythibia-projects.yaml')\nif not p.exists():\n print('LAB_TASKS_MISSING')\n raise SystemExit(0)\nd=yaml.safe_load(p.read_text(encoding='utf-8')) or {}\nt=d.get('tasks',[]) or []\ncounts={}\nfor x in t:\n s=x.get('status','UNKNOWN')\n counts[s]=counts.get(s,0)+1\nprint({'counts':counts,'tasks':[(x.get('id'),x.get('status')) for x in t]})\nPY",
        timeout=20,
    )

    mythibia_health = _run(
        "python3 - << 'PY'\nimport json\nfrom urllib.request import urlopen\nfrom urllib.error import URLError, HTTPError\nurl='http://127.0.0.1:8890/health'\nout={'ok': False, 'url': url}\ntry:\n with urlopen(url, timeout=5) as r:\n  body=r.read().decode('utf-8')\n  out['status']=r.status\n  out['body']=json.loads(body)\n  out['ok']=True\nexcept HTTPError as e:\n out['error']=f'http_{e.code}'\nexcept URLError as e:\n out['error']=str(e.reason)\nexcept Exception as e:\n out['error']=str(e)\nprint(out)\nPY",
        timeout=10,
    )

    return {
        "services": out,
        "disk": disk,
        "report": report,
        "lab": lab_status,
        "mythibia_api_health": mythibia_health,
    }


@app.get("/api/logs")
def logs(
    target: str = Query(
        default="runner",
        pattern="^(runner|health|report|mythibia_api|mythibia_watcher"
                "|agent_orchestrator|agent_scout|agent_brain|agent_generator"
                "|agent_validator|agent_publisher)$",
    ),
    lines: int = Query(default=120, ge=10, le=500),
    _: None = Depends(_require_token),
) -> dict:
    mapping = {
        "runner":            "/opt/ctoa/logs/runner.log",
        "health":            "/opt/ctoa/logs/health-live.log",
        "report":            "/opt/ctoa/logs/runner.log",
        "mythibia_api":      "/opt/ctoa/logs/mythibia-news-api.log",
        "mythibia_watcher":  "/opt/ctoa/logs/mythibia-news-watcher.log",
        "agent_orchestrator": "/opt/ctoa/logs/agents-orchestrator.log",
        "agent_scout":       "/opt/ctoa/logs/agents-orchestrator.log",
        "agent_brain":       "/opt/ctoa/logs/agents-orchestrator.log",
        "agent_generator":   "/opt/ctoa/logs/agents-orchestrator.log",
        "agent_validator":   "/opt/ctoa/logs/agents-orchestrator.log",
        "agent_publisher":   "/opt/ctoa/logs/agents-orchestrator.log",
    }
    path = mapping[target]
    cmd = f"tail -n {lines} {path} 2>/dev/null || echo '(log not found)'"
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


# ── Server registration ──────────────────────────────────────────────────────

def _validate_url(url: str) -> str:
    """Normalise and basic-validate a game server URL."""
    url = url.strip().rstrip("/")
    if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url, re.IGNORECASE):
        raise HTTPException(status_code=422, detail="Invalid URL format. Must start with http:// or https://")
    return url


def _db_exec(sql: str, params: tuple = ()) -> dict:
    """Run a SQL statement via psql CLI (no psycopg2 needed on the mobile console host)."""
    dsn = (
        f"postgresql://{os.getenv('DB_USER','ctoa')}:{os.getenv('DB_PASSWORD','')}"
        f"@{os.getenv('DB_HOST','127.0.0.1')}:{os.getenv('DB_PORT','5432')}"
        f"/{os.getenv('DB_NAME','ctoa')}"
    )
    # Build parameterised SQL by simple positional substitution (values are quoted)
    def quote(v: object) -> str:
        if v is None:
            return "NULL"
        return "'" + str(v).replace("'", "''") + "'"

    # Replace %s placeholders sequentially
    filled = sql
    for p in params:
        filled = filled.replace("%s", quote(p), 1)

    cmd = f"psql {dsn} -t -A -c {json.dumps(filled)}"
    return _run(cmd, timeout=15)


@app.post("/api/server/register")
def server_register(
    req: ServerRegisterRequest,
    request: Request,
    _: None = Depends(_require_token),
) -> dict:
    url = _validate_url(req.url)

    # Insert into DB (idempotent)
    res = _db_exec(
        "INSERT INTO servers (url, status) VALUES (%s, 'NEW') "
        "ON CONFLICT (url) DO UPDATE SET status='NEW', updated_at=now() "
        "RETURNING id, status",
        (url,),
    )
    if res["code"] != 0:
        raise HTTPException(status_code=503, detail=f"DB error: {res['stderr'][:200]}")

    # Trigger one-shot orchestrator run (background)
    _run(
        "systemctl start ctoa-agents-orchestrator.service",
        timeout=5,
    )

    _audit(request, f"server_register:{url}", 0)
    return {"ok": True, "url": url, "db": res["stdout"].strip()}


def _default_intel_urls() -> list[str]:
    env_urls = os.getenv("CTOA_INTEL_DEFAULT_URLS", "").strip()
    if env_urls:
        return [u.strip() for u in env_urls.split(",") if u.strip()]
    return [
        "https://tibiantis.online",
        "https://otland.net",
    ]


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower().split("//")[-1])[:40]


def _sync_mythibia_to_client(source_dir: Path) -> dict:
    enabled = os.getenv("CTOA_CLIENT_SYNC_ENABLED", "false").lower() == "true"
    if not enabled:
        return {
            "enabled": False,
            "ok": False,
            "detail": "CTOA_CLIENT_SYNC_ENABLED=false",
        }

    client_scripts = os.getenv("CTOA_CLIENT_SCRIPTS_DIR", "").strip()
    if not client_scripts:
        return {
            "enabled": True,
            "ok": False,
            "detail": "Missing CTOA_CLIENT_SCRIPTS_DIR",
        }

    if not source_dir.exists():
        return {
            "enabled": True,
            "ok": False,
            "detail": f"Source dir not found: {source_dir}",
        }

    try:
        client_root = Path(client_scripts)
        target_dir = client_root / "mythibia_online"
        target_dir.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        for src in sorted(source_dir.glob("*.lua")):
            dst = target_dir / src.name
            shutil.copy2(src, dst)
            copied.append(src.name)

        autoload_name = os.getenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_mythibia_autoload.lua").strip()
        autoload_path = client_root / autoload_name

        target_posix = target_dir.as_posix()
        lines = [
            "-- CTOA auto-generated mythibia autoloader",
            f"local BASE = \"{target_posix}\"",
            "",
        ]
        for name in copied:
            lines.append(f"dofile(BASE .. \"/{name}\")")
        autoload_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        init_file = os.getenv("CTOA_CLIENT_INIT_FILE", "").strip()
        init_updated = False
        if init_file:
            init_path = Path(init_file)
            if init_path.exists():
                include_line = f'dofile("{autoload_path.as_posix()}")'
                body = init_path.read_text(encoding="utf-8", errors="replace")
                if include_line not in body:
                    if not body.endswith("\n"):
                        body += "\n"
                    body += include_line + "\n"
                    init_path.write_text(body, encoding="utf-8")
                    init_updated = True

        return {
            "enabled": True,
            "ok": True,
            "target_dir": str(target_dir),
            "autoload": str(autoload_path),
            "copied_files": copied,
            "copied_count": len(copied),
            "init_updated": init_updated,
        }
    except Exception as exc:
        return {
            "enabled": True,
            "ok": False,
            "detail": str(exc),
        }


@app.post("/api/agents/intel/launch")
def launch_intel_mission(
    req: IntelMissionRequest,
    request: Request,
    _: None = Depends(_require_token),
) -> dict:
    urls = req.urls or _default_intel_urls()
    sanitized: list[str] = []
    for raw in urls[:25]:
        sanitized.append(_validate_url(raw))

    seeded = 0
    for url in sanitized:
        if req.force_rescout:
            sql = (
                "INSERT INTO servers (url, status) VALUES (%s, 'NEW') "
                "ON CONFLICT (url) DO UPDATE SET status='NEW', updated_at=now()"
            )
        else:
            sql = (
                "INSERT INTO servers (url, status) VALUES (%s, 'NEW') "
                "ON CONFLICT (url) DO NOTHING"
            )
        res = _db_exec(sql, (url,))
        if res["code"] != 0:
            raise HTTPException(status_code=503, detail=f"DB error while seeding {url}: {res['stderr'][:200]}")
        seeded += 1

    trigger = {"code": 0, "stdout": "skipped", "stderr": ""}
    if req.trigger_now:
        trigger = _run("systemctl start --no-block ctoa-agents-orchestrator.service", timeout=8)

    _audit(request, f"intel_launch:{len(sanitized)}", int(trigger.get("code", 0)))
    return {
        "ok": True,
        "seeded_urls": sanitized,
        "seeded_count": seeded,
        "triggered": req.trigger_now,
        "trigger_result": {
            "code": trigger.get("code", -1),
            "stdout": (trigger.get("stdout", "") or "").strip(),
            "stderr": (trigger.get("stderr", "") or "").strip(),
        },
    }


@app.get("/api/agents/intel/report")
def intel_report(_: None = Depends(_require_token)) -> dict:
    servers_res = _db_exec(
        "SELECT status, COUNT(*) FROM servers GROUP BY status ORDER BY status"
    )
    runs_res = _db_exec(
        "SELECT agent, status, finished_at FROM agent_runs ORDER BY id DESC LIMIT 20"
    )
    quality_res = _db_exec(
        "SELECT dt, modules_generated, programs_generated, avg_quality, launcher_day "
        "FROM daily_stats ORDER BY dt DESC LIMIT 3"
    )
    failures_res = _db_exec(
        "SELECT task_id, template, quality_score, test_log "
        "FROM modules WHERE status='FAILED' ORDER BY validated_at DESC NULLS LAST LIMIT 8"
    )

    def parse_rows(raw: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for line in raw.strip().splitlines():
            if line.strip():
                rows.append(line.split("|"))
        return rows

    quality_rows = parse_rows(quality_res.get("stdout", ""))
    trainer_actions: list[str] = []
    if quality_rows:
        latest = quality_rows[0]
        try:
            avg_q = float(latest[3])
        except Exception:
            avg_q = 0.0
        if avg_q < 85:
            trainer_actions.append("Podnies rygor promptu: edge-cases + negative tests + output contract")
            trainer_actions.append("Zwieksz nacisk na walidowalnosc i deterministyczne API modulow")
        elif avg_q < 92:
            trainer_actions.append("Dostrajać prompty pod stabilnosc i redukcje TODO/FIXME")
        else:
            trainer_actions.append("Tryb elite: utrzymanie jakosci i optymalizacja kosztu tokenow")
    else:
        trainer_actions.append("Brak danych quality: uruchom misje intel i pipeline walidacji")

    return {
        "ok": True,
        "servers": parse_rows(servers_res.get("stdout", "")),
        "recent_runs": parse_rows(runs_res.get("stdout", "")),
        "quality": quality_rows,
        "failed_modules": parse_rows(failures_res.get("stdout", "")),
        "trainer_actions": trainer_actions,
    }


@app.get("/api/agents/auto-trainer/latest")
def auto_trainer_latest(_: None = Depends(_require_token)) -> dict:
    latest_md = AUTO_TRAINER_DIR / "latest.md"
    latest_json = AUTO_TRAINER_DIR / "latest.json"

    if not latest_md.exists() and not latest_json.exists():
        return {
            "ok": False,
            "exists": False,
            "detail": "Auto-trainer report not found",
            "path": str(AUTO_TRAINER_DIR),
        }

    md_text = ""
    if latest_md.exists():
        md_text = latest_md.read_text(encoding="utf-8", errors="replace")
        if len(md_text) > 50000:
            md_text = md_text[:50000] + "\n\n... [truncated]"

    js_payload: dict = {}
    if latest_json.exists():
        try:
            js_payload = json.loads(latest_json.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            js_payload = {"parse_error": str(exc)}

    latest_mtime = None
    if latest_md.exists():
        latest_mtime = datetime.fromtimestamp(latest_md.stat().st_mtime, tz=timezone.utc).isoformat()

    return {
        "ok": True,
        "exists": True,
        "updated_at": latest_mtime,
        "markdown": md_text,
        "json": js_payload,
    }


@app.post("/api/agents/mythibia/run")
def mythibia_one_click(request: Request, _: None = Depends(_require_token)) -> dict:
    mythibia_url = "https://mythibia.online"
    res = _db_exec(
        "INSERT INTO servers (url, status) VALUES (%s, 'NEW') "
        "ON CONFLICT (url) DO UPDATE SET status='NEW', updated_at=now() "
        "RETURNING id, status",
        (mythibia_url,),
    )
    if res["code"] != 0:
        raise HTTPException(status_code=503, detail=f"DB error: {res['stderr'][:200]}")

    trig = _run("systemctl start --no-block ctoa-agents-orchestrator.service", timeout=8)
    if trig["code"] != 0:
        raise HTTPException(status_code=503, detail=f"Orchestrator error: {trig['stderr'][:200]}")

    # Give systemd one-shot a moment to produce outputs.
    time.sleep(3)

    slug = _slug(mythibia_url)
    out_dir = GENERATED_DIR / slug
    files: list[dict] = []
    if out_dir.exists():
        for p in sorted(out_dir.glob("*.lua"), key=lambda x: x.stat().st_mtime, reverse=True)[:40]:
            files.append(
                {
                    "name": p.name,
                    "updated_at": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "size": p.stat().st_size,
                }
            )

    srv_state = _db_exec(
        "SELECT id, url, status, game_type, coalesce(scout_error,'') "
        "FROM servers WHERE url=%s ORDER BY id DESC LIMIT 1",
        (mythibia_url,),
    )

    sync = _sync_mythibia_to_client(out_dir)

    _audit(request, "mythibia_one_click", 0)
    return {
        "ok": True,
        "url": mythibia_url,
        "generated_dir": str(out_dir),
        "files": files,
        "files_count": len(files),
        "server_state": srv_state.get("stdout", "").strip(),
        "client_sync": sync,
    }


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard(_: None = Depends(_require_token)) -> dict:
    servers_res = _db_exec(
        "SELECT id, url, status, created_at FROM servers ORDER BY id DESC LIMIT 20",
    )
    modules_res = _db_exec(
        "SELECT status, COUNT(*) AS n FROM modules GROUP BY status ORDER BY status",
    )
    stats_res = _db_exec(
        "SELECT dt, modules_generated, programs_generated, avg_quality, launcher_day "
        "FROM daily_stats ORDER BY dt DESC LIMIT 7",
    )
    top_res = _db_exec(
        "SELECT task_id, output_file, quality_score, status "
        "FROM modules WHERE quality_score IS NOT NULL ORDER BY quality_score DESC LIMIT 10",
    )

    def parse_rows(raw: str) -> list[list[str]]:
        rows = []
        for line in raw.strip().splitlines():
            if line.strip():
                rows.append(line.split("|"))
        return rows

    return {
        "servers":  parse_rows(servers_res.get("stdout", "")),
        "modules":  parse_rows(modules_res.get("stdout", "")),
        "stats":    parse_rows(stats_res.get("stdout", "")),
        "top":      parse_rows(top_res.get("stdout", "")),
        "ok":       servers_res["code"] == 0,
    }


@app.get("/api/agents/status")
def agents_status(_: None = Depends(_require_token)) -> dict:
    units = {
        "orchestrator": "ctoa-agents-orchestrator.service",
        "orchestrator_timer": "ctoa-agents-orchestrator.timer",
        "db": "ctoa-db",  # docker container
    }
    out: dict[str, str] = {}
    for key, unit in units.items():
        if key == "db":
            res = _run("docker inspect --format '{{.State.Status}}' ctoa-db 2>/dev/null || echo missing", timeout=5)
            out[key] = res["stdout"].strip() or "unknown"
        else:
            res = _run(f"systemctl is-active {unit}", timeout=5)
            out[key] = res["stdout"].strip() or "unknown"

    # Last agent run times from DB
    last_runs = _db_exec(
        "SELECT agent, status, finished_at FROM agent_runs ORDER BY id DESC LIMIT 12",
    )
    out["last_runs_raw"] = last_runs.get("stdout", "")
    return out

