#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import json
import time
import hmac
import secrets
import bcrypt
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "mobile_console" / "static"
LIVE_DASHBOARD_HTML = ROOT / "docs" / "site" / "live-dashboard.html"
AUDIT_LOG = ROOT / "logs" / "mobile-console-audit.log"
AUTO_TRAINER_DIR = Path(os.environ.get("CTOA_TRAINING_REPORT_DIR", str(ROOT / "runtime" / "training-reports")))
GENERATED_DIR = Path(os.environ.get("CTOA_GENERATED_DIR", "/opt/ctoa/generated"))
GENERATED_MANIFESTS_DIR = GENERATED_DIR / "manifests"
ADMIN_SETTINGS_FILE = Path(os.environ.get("CTOA_ADMIN_SETTINGS_FILE", str(ROOT / "runtime" / "admin-panel-settings.json")))
IDEA_PARKING_FILE = Path(os.environ.get("CTOA_IDEA_PARKING_FILE", str(ROOT / "runtime" / "idea-parking.json")))


def _is_production_env() -> bool:
    return os.getenv("CTOA_ENV", "").strip().lower() in {"prod", "production"}

app = FastAPI(title="CTOA Mobile Console", version="1.0.0")

cors_origins = [o.strip() for o in os.getenv("CTOA_CORS_ORIGINS", "*").split(",") if o.strip()]
if _is_production_env() and (not cors_origins or "*" in cors_origins):
    raise RuntimeError(
        "Refusing to start in production with wildcard CORS. "
        "Set CTOA_CORS_ORIGINS to explicit origins, e.g. https://twoja-domena.pl"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class AdminSettingsPayload(BaseModel):
    stealthMode: bool = True
    showPrices: bool = False
    heroNote: str = Field(default="", max_length=500)


class IdeaCreatePayload(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class LiveDashboardProfilePayload(BaseModel):
    api_base: str = Field(default="", max_length=256)
    refresh_seconds: int = Field(default=10, ge=5, le=120)


class RegisterAccountPayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(default="operator", pattern="^(operator|owner)$")


class ChangePasswordPayload(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class ChangeRolePayload(BaseModel):
    role: str = Field(pattern="^(operator|owner)$")


ROLE_WEIGHT = {"operator": 1, "owner": 2}
SESSION_TTL_SECONDS = int(os.getenv("CTOA_SESSION_TTL_SECONDS", "1800"))
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSIONS_LOCK = Lock()
_ADMIN_SETTINGS_LOCK = Lock()
_IDEA_PARKING_LOCK = Lock()
_USER_PROFILES_LOCK = Lock()
_USER_PROFILES_TABLE_READY = False
_ACCOUNTS_TABLE_READY = False


def _default_admin_settings() -> dict[str, Any]:
    return {
        "stealthMode": True,
        "showPrices": False,
        "heroNote": "",
    }


def _normalize_admin_settings(payload: dict[str, Any]) -> dict[str, Any]:
    default = _default_admin_settings()
    data = {**default, **(payload or {})}
    data["stealthMode"] = bool(data.get("stealthMode", default["stealthMode"]))
    data["showPrices"] = bool(data.get("showPrices", default["showPrices"]))
    hero = str(data.get("heroNote", default["heroNote"]))
    data["heroNote"] = hero[:500]
    return data


def _read_admin_settings() -> dict[str, Any]:
    with _ADMIN_SETTINGS_LOCK:
        if not ADMIN_SETTINGS_FILE.exists():
            return _default_admin_settings()
        try:
            payload = json.loads(ADMIN_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return _default_admin_settings()
        return _normalize_admin_settings(payload)


def _write_admin_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = _normalize_admin_settings(payload)
    with _ADMIN_SETTINGS_LOCK:
        ADMIN_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ADMIN_SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data


def _normalize_idea_item(payload: dict[str, Any], fallback_author: str = "") -> dict[str, Any] | None:
    text = str((payload or {}).get("text", "")).strip()
    if not text:
        return None

    raw_id = str((payload or {}).get("id", "")).strip()
    idea_id = raw_id[:80] if raw_id else secrets.token_hex(8)

    created_at = str((payload or {}).get("createdAt", "")).strip()
    if not created_at:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    author = str((payload or {}).get("author", fallback_author)).strip().lower()[:64]

    return {
        "id": idea_id,
        "text": text[:500],
        "createdAt": created_at,
        "author": author,
    }


def _read_idea_parking() -> list[dict[str, Any]]:
    with _IDEA_PARKING_LOCK:
        if not IDEA_PARKING_FILE.exists():
            return []
        try:
            payload = json.loads(IDEA_PARKING_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

        if not isinstance(payload, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            parsed = _normalize_idea_item(item)
            if parsed:
                normalized.append(parsed)
        return normalized


def _write_idea_parking(ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in ideas:
        if not isinstance(item, dict):
            continue
        parsed = _normalize_idea_item(item)
        if parsed:
            normalized.append(parsed)

    normalized = normalized[:1000]
    with _IDEA_PARKING_LOCK:
        IDEA_PARKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        IDEA_PARKING_FILE.write_text(json.dumps(normalized, ensure_ascii=True, indent=2), encoding="utf-8")
    return normalized


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


def _normalize_user(username: str) -> str:
    return username.strip().lower()


def _admin_credentials() -> dict[str, dict[str, str]]:
    owner_user = _normalize_user(os.getenv("CTOA_OWNER_USER", "CTO"))
    operator_user = _normalize_user(os.getenv("CTOA_OPERATOR_USER", "ctoa-bot"))
    owner_pass = os.getenv("CTOA_OWNER_PASSWORD", "asdzxc12")
    operator_pass = os.getenv("CTOA_OPERATOR_PASSWORD", "")

    creds = {
        owner_user: {"role": "owner", "password": owner_pass},
    }
    if operator_pass:
        creds[operator_user] = {"role": "operator", "password": operator_pass}
    return creds


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    auth = authorization.strip()
    if not auth.lower().startswith("bearer "):
        return ""
    return auth[7:].strip()


def _create_session(username: str, role: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    with _SESSIONS_LOCK:
        _SESSIONS[token] = {
            "username": username,
            "role": role,
            "expires_at": expires_at,
        }
    return token, expires_at


def _get_session(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(token)
        if not session:
            return None
        if int(session.get("expires_at", 0)) <= int(time.time()):
            _SESSIONS.pop(token, None)
            return None
        return dict(session)


def _delete_session(token: str) -> None:
    if not token:
        return
    with _SESSIONS_LOCK:
        _SESSIONS.pop(token, None)


def _try_auth_context(
    x_ctoa_token: Optional[str] = None,
    authorization: Optional[str] = None,
    x_ctoa_session: Optional[str] = None,
) -> dict[str, Any] | None:
    # Backward-compatible owner auth using static token.
    expected = _mobile_token()
    if x_ctoa_token and hmac.compare_digest(x_ctoa_token, expected):
        return {
            "username": os.getenv("CTOA_OWNER_USER", "CTO"),
            "role": "owner",
            "auth_mode": "legacy_token",
            "session_token": None,
        }

    session_token = x_ctoa_session or _extract_bearer(authorization)
    session = _get_session(session_token)
    if session:
        return {
            "username": session["username"],
            "role": session["role"],
            "auth_mode": "session",
            "session_token": session_token,
        }

    return None


def _token_valid(
    x_ctoa_token: Optional[str],
    authorization: Optional[str],
    x_ctoa_session: Optional[str],
) -> bool:
    return _try_auth_context(x_ctoa_token=x_ctoa_token, authorization=authorization, x_ctoa_session=x_ctoa_session) is not None


def require_operator(
    x_ctoa_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_ctoa_session: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    ctx = _try_auth_context(x_ctoa_token=x_ctoa_token, authorization=authorization, x_ctoa_session=x_ctoa_session)
    if not ctx:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return ctx


def require_owner(ctx: dict[str, Any] = Depends(require_operator)) -> dict[str, Any]:
    role = str(ctx.get("role", "operator"))
    if ROLE_WEIGHT.get(role, 0) < ROLE_WEIGHT["owner"]:
        raise HTTPException(status_code=403, detail="Owner role required")
    return ctx


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


@app.get("/live-dashboard")
def live_dashboard() -> FileResponse:
    """Serve the login-based live dashboard (username/password auth)."""
    return FileResponse(str(LIVE_DASHBOARD_HTML))


@app.get("/api/health")
def health(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    return {"ok": True, "full_access": _full_access(), "role": ctx["role"], "username": ctx["username"]}


@app.post("/api/auth/login")
def auth_login(req: AuthLoginRequest, request: Request) -> dict:
    username = _normalize_user(req.username)

    # 1. Try env-based credentials (owner/operator hardcoded — backward compat).
    creds = _admin_credentials()
    account = creds.get(username)
    matched_role: str | None = None

    if account and hmac.compare_digest(req.password, account["password"]):
        matched_role = account["role"]
    else:
        # 2. Try DB-backed account.
        try:
            db_account = _db_get_account(username)
        except Exception:
            db_account = None

        if db_account and _verify_password(req.password, db_account["password_hash"]):
            matched_role = db_account["role"]

    if matched_role is None:
        _audit(request, f"auth_login:{username}", 401)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token, expires_at = _create_session(username=username, role=matched_role)

    # Best-effort profile bootstrap so each authenticated user has a DB profile.
    try:
        _load_live_dashboard_profile(username=username, role=matched_role)
    except Exception:
        pass

    _audit(request, f"auth_login:{username}", 0)
    return {
        "ok": True,
        "token": token,
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        "role": matched_role,
        "username": username,
    }


@app.get("/api/auth/me")
def auth_me(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    return {
        "ok": True,
        "username": ctx["username"],
        "role": ctx["role"],
        "auth_mode": ctx["auth_mode"],
    }


@app.post("/api/auth/logout")
def auth_logout(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    token = str(ctx.get("session_token") or "")
    if token:
        _delete_session(token)
    return {"ok": True}


# ── User account management ──────────────────────────────────────────────────

@app.post("/api/users/register")
def register_account(
    req: RegisterAccountPayload,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    username = _normalize_user(req.username)

    # Prevent overwriting env-based accounts.
    env_creds = _admin_credentials()
    if username in env_creds:
        raise HTTPException(status_code=409, detail="Username reserved by system configuration")

    try:
        result = _db_create_account(
            username=username,
            password=req.password,
            role=req.role,
            created_by=str(ctx.get("username", "")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _audit(request, f"account_register:{username}:role={req.role}", 0)
    return {"ok": True, "account": result}


@app.get("/api/users")
def list_accounts(
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    try:
        db_accounts = _db_list_accounts()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Also surface env-based accounts so the owner sees the full picture.
    env_creds = _admin_credentials()
    env_entries = [
        {"username": u, "role": v["role"], "active": True,
         "created_by": "env", "created_at": None, "updated_at": None, "source": "env"}
        for u, v in env_creds.items()
    ]

    db_usernames = {a["username"] for a in db_accounts}
    for entry in env_entries:
        entry["source"] = "env"
        db_accounts_with_source = [
            {**a, "source": "db"} for a in db_accounts
        ]

    combined = db_accounts_with_source + [
        e for e in env_entries if e["username"] not in db_usernames
    ]

    return {"ok": True, "accounts": combined, "count": len(combined)}


@app.put("/api/users/{username}/password")
def change_password(
    username: str,
    req: ChangePasswordPayload,
    request: Request,
    ctx: dict[str, Any] = Depends(require_operator),
) -> dict:
    caller = str(ctx.get("username", ""))
    caller_role = str(ctx.get("role", "operator"))
    target = _normalize_user(username)

    # Only owner can change someone else's password.
    if target != caller and ROLE_WEIGHT.get(caller_role, 0) < ROLE_WEIGHT["owner"]:
        raise HTTPException(status_code=403, detail="Cannot change another user's password")

    env_creds = _admin_credentials()
    if target in env_creds:
        raise HTTPException(status_code=409, detail="Cannot change password of an env-configured account via API")

    try:
        _db_update_password(username=target, password=req.password)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _audit(request, f"account_password_change:{target}:by={caller}", 0)
    return {"ok": True, "username": target}


@app.put("/api/users/{username}/role")
def change_role(
    username: str,
    req: ChangeRolePayload,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    target = _normalize_user(username)
    caller = str(ctx.get("username", ""))

    env_creds = _admin_credentials()
    if target in env_creds:
        raise HTTPException(status_code=409, detail="Cannot change role of an env-configured account via API")

    try:
        _db_update_role(username=target, role=req.role)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _audit(request, f"account_role_change:{target}:role={req.role}:by={caller}", 0)
    return {"ok": True, "username": target, "role": req.role}


@app.delete("/api/users/{username}")
def deactivate_account(
    username: str,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    target = _normalize_user(username)
    caller = str(ctx.get("username", ""))

    if target == caller:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    env_creds = _admin_credentials()
    if target in env_creds:
        raise HTTPException(status_code=409, detail="Cannot deactivate an env-configured account via API")

    try:
        _db_deactivate_account(username=target)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _audit(request, f"account_deactivate:{target}:by={caller}", 0)
    return {"ok": True, "username": target, "active": False}


@app.get("/api/auth/auto-check")
def auth_auto_check(
    x_ctoa_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_ctoa_session: Optional[str] = Header(default=None),
) -> dict:
    ctx = _try_auth_context(x_ctoa_token=x_ctoa_token, authorization=authorization, x_ctoa_session=x_ctoa_session)
    valid = ctx is not None
    payload = {
        "ok": valid,
        "token_present": bool(x_ctoa_token or authorization or x_ctoa_session),
        "token_valid": valid,
        "full_access": _full_access() if valid else False,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if ctx:
        payload["username"] = ctx["username"]
        payload["role"] = ctx["role"]
        payload["auth_mode"] = ctx["auth_mode"]
    if valid:
        timer = _run("systemctl is-active ctoa-agents-orchestrator.timer", timeout=5)
        payload["orchestrator_timer"] = timer["stdout"].strip() or "unknown"
    else:
        payload["hint"] = "Uzyj loginu /api/auth/login i przeslij Authorization: Bearer <token>"
    return payload


@app.get("/api/presets")
def presets(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    return {"commands": _allowed_commands(), "role": ctx["role"]}


@app.get("/api/status")
def status(_: dict[str, Any] = Depends(require_operator)) -> dict:
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


@app.get("/api/admin/settings")
def get_admin_settings(_: dict[str, Any] = Depends(require_operator)) -> dict:
    return {
        "ok": True,
        "settings": _read_admin_settings(),
        "path": str(ADMIN_SETTINGS_FILE),
    }


@app.put("/api/admin/settings")
def put_admin_settings(
    req: AdminSettingsPayload,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    saved = _write_admin_settings(req.model_dump())
    _audit(request, f"admin_settings_save:{ctx.get('username','unknown')}", 0)
    return {
        "ok": True,
        "settings": saved,
        "saved_by": ctx.get("username"),
        "saved_role": ctx.get("role"),
    }


@app.get("/api/ideas")
def get_ideas(_: dict[str, Any] = Depends(require_operator)) -> dict:
    ideas = _read_idea_parking()
    return {
        "ok": True,
        "ideas": ideas,
        "count": len(ideas),
        "path": str(IDEA_PARKING_FILE),
    }


@app.post("/api/ideas")
def post_idea(
    req: IdeaCreatePayload,
    request: Request,
    ctx: dict[str, Any] = Depends(require_operator),
) -> dict:
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Idea text cannot be empty")

    ideas = _read_idea_parking()
    idea = _normalize_idea_item(
        {
            "id": secrets.token_hex(8),
            "text": text,
            "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "author": ctx.get("username", ""),
        }
    )
    if not idea:
        raise HTTPException(status_code=422, detail="Invalid idea payload")

    ideas.insert(0, idea)
    saved = _write_idea_parking(ideas)
    _audit(request, f"idea_add:{ctx.get('username', 'unknown')}", 0)
    return {
        "ok": True,
        "idea": idea,
        "count": len(saved),
    }


@app.delete("/api/ideas/{idea_id}")
def delete_idea(
    idea_id: str,
    request: Request,
    ctx: dict[str, Any] = Depends(require_operator),
) -> dict:
    idea_id = idea_id.strip()
    if not idea_id:
        raise HTTPException(status_code=422, detail="idea_id is required")

    ideas = _read_idea_parking()
    remaining = [item for item in ideas if str(item.get("id", "")) != idea_id]
    deleted = len(ideas) - len(remaining)
    if deleted <= 0:
        raise HTTPException(status_code=404, detail="Idea not found")

    saved = _write_idea_parking(remaining)
    _audit(request, f"idea_delete:{ctx.get('username', 'unknown')}:{idea_id}", 0)
    return {
        "ok": True,
        "deleted": deleted,
        "count": len(saved),
    }


@app.delete("/api/ideas")
def clear_ideas(
    request: Request,
    ctx: dict[str, Any] = Depends(require_operator),
) -> dict:
    _write_idea_parking([])
    _audit(request, f"idea_clear_all:{ctx.get('username', 'unknown')}", 0)
    return {
        "ok": True,
        "count": 0,
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
    _: dict[str, Any] = Depends(require_operator),
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
def command(req: CommandRequest, request: Request, _: dict[str, Any] = Depends(require_owner)) -> dict:
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


# ── Bcrypt account helpers ───────────────────────────────────────────────────

def _hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_password(plaintext: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode(), hashed.encode())
    except Exception:
        return False


def _ensure_accounts_table() -> None:
    global _ACCOUNTS_TABLE_READY
    if _ACCOUNTS_TABLE_READY:
        return
    res = _db_exec(
        "CREATE TABLE IF NOT EXISTS accounts ("
        "id SERIAL PRIMARY KEY, "
        "username TEXT NOT NULL UNIQUE, "
        "password_hash TEXT NOT NULL, "
        "role TEXT NOT NULL DEFAULT 'operator', "
        "active BOOL NOT NULL DEFAULT TRUE, "
        "created_by TEXT, "
        "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        ")"
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error ensuring accounts table: {res.get('stderr','')[:200]}")
    _ACCOUNTS_TABLE_READY = True


def _db_get_account(username: str) -> dict[str, Any] | None:
    _ensure_accounts_table()
    res = _db_exec(
        "SELECT username, password_hash, role, active FROM accounts WHERE username=%s AND active=TRUE LIMIT 1",
        (username,),
    )
    if res.get("code", 1) != 0:
        return None
    row = (res.get("stdout", "") or "").strip()
    if not row:
        return None
    parts = row.split("|", 3)
    if len(parts) < 4:
        return None
    return {
        "username": parts[0],
        "password_hash": parts[1],
        "role": parts[2],
        "active": parts[3].strip() == "t",
    }


def _db_create_account(
    username: str, password: str, role: str, created_by: str
) -> dict[str, Any]:
    _ensure_accounts_table()
    password_hash = _hash_password(password)
    res = _db_exec(
        "INSERT INTO accounts (username, password_hash, role, created_by) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (username) DO NOTHING RETURNING id",
        (username, password_hash, role, created_by),
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error creating account: {res.get('stderr','')[:200]}")
    if not (res.get("stdout", "") or "").strip():
        raise ValueError(f"Account '{username}' already exists")
    return {"username": username, "role": role, "created_by": created_by}


def _db_list_accounts() -> list[dict[str, Any]]:
    _ensure_accounts_table()
    res = _db_exec(
        "SELECT username, role, active, created_by, created_at, updated_at "
        "FROM accounts ORDER BY created_at DESC"
    )
    if res.get("code", 1) != 0:
        return []
    rows = []
    for line in (res.get("stdout", "") or "").strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 5)
        rows.append({
            "username": parts[0] if len(parts) > 0 else "",
            "role": parts[1] if len(parts) > 1 else "",
            "active": (parts[2] if len(parts) > 2 else "f").strip() == "t",
            "created_by": parts[3] if len(parts) > 3 else "",
            "created_at": parts[4] if len(parts) > 4 else "",
            "updated_at": parts[5] if len(parts) > 5 else "",
        })
    return rows


def _db_update_password(username: str, password: str) -> None:
    _ensure_accounts_table()
    password_hash = _hash_password(password)
    res = _db_exec(
        "UPDATE accounts SET password_hash=%s, updated_at=now() WHERE username=%s",
        (password_hash, username),
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error updating password: {res.get('stderr','')[:200]}")


def _db_update_role(username: str, role: str) -> None:
    _ensure_accounts_table()
    res = _db_exec(
        "UPDATE accounts SET role=%s, updated_at=now() WHERE username=%s",
        (role, username),
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error updating role: {res.get('stderr','')[:200]}")


def _db_deactivate_account(username: str) -> None:
    _ensure_accounts_table()
    res = _db_exec(
        "UPDATE accounts SET active=FALSE, updated_at=now() WHERE username=%s",
        (username,),
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error deactivating account: {res.get('stderr','')[:200]}")


def _default_live_dashboard_profile() -> dict[str, Any]:
    return {
        "api_base": "",
        "refresh_seconds": 10,
    }


def _normalize_live_dashboard_profile(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    default = _default_live_dashboard_profile()

    raw_api_base = str(data.get("api_base", default["api_base"])).strip().rstrip("/")
    if raw_api_base and not re.match(r"^https?://", raw_api_base, re.IGNORECASE):
        raw_api_base = ""

    try:
        refresh_seconds = int(data.get("refresh_seconds", default["refresh_seconds"]))
    except Exception:
        refresh_seconds = default["refresh_seconds"]
    refresh_seconds = max(5, min(120, refresh_seconds))

    return {
        "api_base": raw_api_base,
        "refresh_seconds": refresh_seconds,
    }


def _ensure_user_profiles_table() -> None:
    global _USER_PROFILES_TABLE_READY
    with _USER_PROFILES_LOCK:
        if _USER_PROFILES_TABLE_READY:
            return

        res = _db_exec(
            "CREATE TABLE IF NOT EXISTS user_profiles ("
            "username TEXT PRIMARY KEY, "
            "role TEXT NOT NULL, "
            "profile_json JSONB NOT NULL DEFAULT '{}'::jsonb, "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        )
        if res.get("code", 1) != 0:
            raise RuntimeError(f"DB error while ensuring user_profiles: {res.get('stderr', '')[:200]}")

        _USER_PROFILES_TABLE_READY = True


def _save_live_dashboard_profile(username: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_user_profiles_table()
    normalized = _normalize_live_dashboard_profile(payload)
    profile_json = json.dumps(normalized, ensure_ascii=True)

    res = _db_exec(
        "INSERT INTO user_profiles (username, role, profile_json) VALUES (%s, %s, %s::jsonb) "
        "ON CONFLICT (username) DO UPDATE SET "
        "role=EXCLUDED.role, profile_json=EXCLUDED.profile_json, updated_at=now() "
        "RETURNING updated_at",
        (username, role, profile_json),
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error while saving user profile: {res.get('stderr', '')[:200]}")

    return normalized


def _load_live_dashboard_profile(username: str, role: str) -> dict[str, Any]:
    _ensure_user_profiles_table()
    res = _db_exec(
        "SELECT role, profile_json::text, created_at, updated_at "
        "FROM user_profiles WHERE username=%s LIMIT 1",
        (username,),
    )
    if res.get("code", 1) != 0:
        raise RuntimeError(f"DB error while loading user profile: {res.get('stderr', '')[:200]}")

    row = (res.get("stdout", "") or "").strip()
    if not row:
        profile = _save_live_dashboard_profile(username=username, role=role, payload=_default_live_dashboard_profile())
        return {
            "username": username,
            "role": role,
            "profile": profile,
            "created_at": None,
            "updated_at": None,
        }

    parts = row.split("|", 3)
    stored_role = parts[0] if len(parts) > 0 and parts[0] else role
    profile_raw = parts[1] if len(parts) > 1 else "{}"
    created_at = parts[2] if len(parts) > 2 else None
    updated_at = parts[3] if len(parts) > 3 else None

    try:
        profile_data = json.loads(profile_raw)
    except Exception:
        profile_data = {}

    profile = _normalize_live_dashboard_profile(profile_data)
    if profile != profile_data:
        profile = _save_live_dashboard_profile(username=username, role=stored_role, payload=profile)

    return {
        "username": username,
        "role": stored_role,
        "profile": profile,
        "created_at": created_at,
        "updated_at": updated_at,
    }


@app.get("/api/live-dashboard/profile")
def get_live_dashboard_profile(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    try:
        profile = _load_live_dashboard_profile(
            username=str(ctx.get("username", "")).strip().lower(),
            role=str(ctx.get("role", "operator")),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "ok": True,
        **profile,
    }


@app.put("/api/live-dashboard/profile")
def put_live_dashboard_profile(
    req: LiveDashboardProfilePayload,
    ctx: dict[str, Any] = Depends(require_operator),
) -> dict:
    username = str(ctx.get("username", "")).strip().lower()
    role = str(ctx.get("role", "operator"))
    payload = req.model_dump()

    try:
        profile = _save_live_dashboard_profile(username=username, role=role, payload=payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "ok": True,
        "username": username,
        "role": role,
        "profile": profile,
    }


@app.post("/api/server/register")
def server_register(
    req: ServerRegisterRequest,
    request: Request,
    _: dict[str, Any] = Depends(require_owner),
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


def _latest_manifest_payload() -> dict[str, Any] | None:
    latest_file = GENERATED_MANIFESTS_DIR / "latest.json"
    if not latest_file.exists():
        return None
    try:
        latest = json.loads(latest_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    manifest_path = Path(str(latest.get("manifest_path", "")).strip())
    if not manifest_path.exists():
        candidate = GENERATED_MANIFESTS_DIR / str(latest.get("run_id", "")) / "manifest.json"
        if candidate.exists():
            manifest_path = candidate
        else:
            return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return {
        "run_id": latest.get("run_id") or manifest.get("run_id"),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
    }


def _scan_generated_files(limit: int) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not GENERATED_DIR.exists():
        return files

    for p in GENERATED_DIR.rglob("*.lua"):
        try:
            st = p.stat()
        except Exception:
            continue
        files.append(
            {
                "output_path": str(p),
                "output_file": p.name,
                "server_slug": p.parent.name,
                "generated_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                "size": int(st.st_size),
            }
        )
    files.sort(key=lambda item: str(item.get("generated_at", "")), reverse=True)
    return files[:limit]


@app.post("/api/agents/intel/launch")
def launch_intel_mission(
    req: IntelMissionRequest,
    request: Request,
    _: dict[str, Any] = Depends(require_owner),
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
def intel_report(_: dict[str, Any] = Depends(require_operator)) -> dict:
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
def auto_trainer_latest(_: dict[str, Any] = Depends(require_operator)) -> dict:
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
def mythibia_one_click(request: Request, _: dict[str, Any] = Depends(require_owner)) -> dict:
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


@app.get("/api/agents/generated/latest")
def latest_generated_modules(
    limit: int = Query(default=20, ge=1, le=200),
    _: dict[str, Any] = Depends(require_operator),
) -> dict:
    manifest_payload = _latest_manifest_payload()
    if manifest_payload:
        manifest = manifest_payload["manifest"]
        generated = manifest.get("generated") if isinstance(manifest, dict) else []
        items: list[dict[str, Any]] = []
        if isinstance(generated, list):
            for entry in generated[:limit]:
                if not isinstance(entry, dict):
                    continue
                item = {
                    "task_id": entry.get("task_id"),
                    "server_id": entry.get("server_id"),
                    "template": entry.get("template"),
                    "output_file": entry.get("output_file"),
                    "output_path": entry.get("output_path"),
                    "queued_at": entry.get("queued_at"),
                    "generated_at": entry.get("generated_at"),
                }
                items.append(item)

        return {
            "ok": True,
            "source": "manifest",
            "run_id": manifest_payload.get("run_id"),
            "manifest_path": manifest_payload.get("manifest_path"),
            "count": len(items),
            "items": items,
        }

    scanned = _scan_generated_files(limit=limit)
    return {
        "ok": True,
        "source": "scan",
        "run_id": None,
        "manifest_path": None,
        "count": len(scanned),
        "items": scanned,
    }


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard(_: dict[str, Any] = Depends(require_operator)) -> dict:
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
def agents_status(_: dict[str, Any] = Depends(require_operator)) -> dict:
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

