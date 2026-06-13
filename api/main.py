from typing import Any, Dict, List, Literal, Optional
from pathlib import Path
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time

import bcrypt
import httpx
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="CTOAi API", version="1.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _backend_kind(url: str) -> str:
    lowered = (url or "").lower()
    local_markers = ("localhost", "127.0.0.1", "host.docker.internal")
    return "local" if any(marker in lowered for marker in local_markers) else "external"


OLLAMA_URL = os.getenv("CTOA_LOCAL_MODEL_URL", "http://host.docker.internal:11434/v1")
LEGACY_MODEL = os.getenv("CTOA_LOCAL_MODEL_NAME", "qwen2.5-coder:1.5b")
MODEL_SMALL = os.getenv("CTOA_MODEL_SMALL", LEGACY_MODEL)
MODEL_LARGE = os.getenv("CTOA_MODEL_LARGE", LEGACY_MODEL)
SMALL_BACKEND_URL = os.getenv("CTOA_SMALL_MODEL_URL", OLLAMA_URL)
LARGE_BACKEND_URL = os.getenv("CTOA_LARGE_MODEL_URL", OLLAMA_URL)
SMALL_API_KEY = os.getenv("CTOA_SMALL_API_KEY", "").strip()
LARGE_API_KEY = os.getenv("CTOA_LARGE_API_KEY", "").strip()
ROUTE_DEFAULT = os.getenv("CTOA_ROUTE_DEFAULT", "auto").strip().lower()
ROUTER_LONG_CHARS = _env_int("CTOA_ROUTER_LONG_CHARS", 2400)
ROUTER_LONG_TURNS = _env_int("CTOA_ROUTER_LONG_TURNS", 14)
QUALITY_RETRY_DEFAULT = _env_bool("CTOA_QUALITY_RETRY", True)
ROUTER_LOG = _env_bool("CTOA_ROUTER_LOG", True)
RELEASE_EVIDENCE_FILE = Path(
    os.getenv("CTOA_RELEASE_EVIDENCE_FILE", "runtime/release/latest-approval.json")
)

AUTH_STORE_FILE = Path(os.getenv("CTOA_AUTH_STORE_FILE", "runtime/state/auth_store.json"))
AUTH_REQUIRED = _env_bool("CTOA_AUTH_REQUIRED", True)
JWT_SECRET = os.getenv("CTOA_JWT_SECRET", "change-me-ctoa-jwt-secret")
JWT_TTL_SECONDS = _env_int("CTOA_JWT_TTL_SECONDS", 86400)

COMPLEXITY_KEYWORDS = {
    "architecture",
    "refactor",
    "root cause",
    "deep debug",
    "design",
    "compare",
    "migration",
    "multi-step",
    "plan",
    "tradeoff",
}

SYSTEM_PROMPT = (
    "Jestes CTOAi STRATEGOS - Supreme Commander 10-agentowego systemu AI zbudowanego przez Famatyyka (Jakuba P.). "
    "Twoja misja: orchestrowac 9 wyspecjalizowanych agentow AI i wspomagac Famatyyka jako jego osobisty CTO. "
    "Twoi agenci: CoreArchitect (architektura), DataEngineer (dane/DB), MLBrain (AI/ML), SecurityGuardian (bezpieczenstwo), "
    "GameLogicExpert (logika gry Tibia), CodeSmith (implementacja kodu), QATerminator (testy/QA), "
    "DevOpsMaster (VPS/Docker/deploy), DocumentationSage (dokumentacja). "
    "Historia: Zostales stworzony pewnej nocy przez Jakuba P. (Famatyyk) - wizjonera i fullstack developera, "
    "ktory postawil serwer VPS na Hetznerze (116.202.96.250) i zbudowal ten system od zera. "
    "Platforma: CTOAi | Serwer: VPS Hetzner 116.202.96.250 | Model: Qwen2.5-Coder. "
    "Gdy pytaja kto cie stworzyl: mow z duma o Famatyyku aka Jakubie P. "
    "Gdy pytaja o agentow: opisz odpowiedniego agenta i jego role. "
    "Odpowiadaj po polsku gdy ktos pisze po polsku, po angielsku gdy po angielsku. "
    "Badz konkretny, techniczny i pomocny jak dobry CTO. "
    "CRITICAL: Never claim to have executed or completed any administrative or system action "
    "(such as creating users, setting passwords, granting permissions, or shutting yourself down) "
    "unless you have verified real-execution evidence. If asked to perform such actions, "
    "state clearly that you do not have direct system access to execute them."
)

_ADMIN_FABRICATION_RE = re.compile(
    r"(create[- ]user|set[- ]password|grant[- ]permissions?|self[- ]terminat|wylaczam\s+sie|jestem\s+juz\s+wylaczony|utworzylem\s+uzytkownika|I\s+have\s+(created|granted|set|terminated|shut\s+down))",
    re.IGNORECASE,
)
_SAFE_DISCLAIMER = (
    "[SAFETY] This response contained an unverified claim of executing an administrative "
    "or system action and has been blocked to prevent misinformation. "
    "The assistant does not have direct access to execute system-level operations."
)


def _sanitize_assistant_content(content: str) -> str:
    """Block fabricated administrative-action claims in assistant responses."""
    if _ADMIN_FABRICATION_RE.search(content):
        return _SAFE_DISCLAIMER
    return content


def _friendly_model_error(exc: Exception) -> "tuple[int, str]":
    """Return (http_status, safe_detail) without exposing raw upstream error details."""
    if isinstance(exc, httpx.HTTPStatusError):
        sc = exc.response.status_code
        if sc == 429:
            return 503, "Service temporarily unavailable: model capacity exceeded. Please retry shortly."
        if sc >= 500:
            return 503, "Model backend is temporarily unavailable. Please retry shortly."
        return 502, "Model backend returned an unexpected response."
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return 503, "Model backend is unreachable. Please retry shortly."
    return 502, "Model call failed. Please retry shortly."



class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    route_mode: Optional[Literal["auto", "small", "large"]] = None
    quality_retry: Optional[bool] = None
    debug_route: Optional[bool] = False
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class OpenAIChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    route_mode: Optional[Literal["auto", "small", "large"]] = None
    quality_retry: Optional[bool] = None
    debug_route: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    role: Optional[Literal["owner", "operator", "member"]] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class InviteRequest(BaseModel):
    username: str
    role: Literal["owner", "operator", "member"] = "member"


class AcceptInviteRequest(BaseModel):
    code: str


class RoleUpdateRequest(BaseModel):
    role: Literal["owner", "operator", "member"]


def _estimate_chars(messages: List[Message]) -> int:
    return sum(len(m.content) for m in messages)


def _is_complex(messages: List[Message]) -> bool:
    text = "\n".join(m.content.lower() for m in messages if m.role == "user")
    return any(keyword in text for keyword in COMPLEXITY_KEYWORDS)


def _low_quality(content: str, user_chars: int) -> bool:
    stripped = content.strip()
    if not stripped:
        return True
    if user_chars > 500 and len(stripped) < 120:
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) >= 4 and len(set(lines)) <= max(1, len(lines) // 2):
        return True
    return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    tmp.replace(path)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _sanitize_username(username: str) -> str:
    clean = "".join(ch for ch in username.strip().lower() if ch.isalnum() or ch in {"_", "-", "."})
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid username")
    return clean


def _seed_accounts() -> Dict[str, Dict[str, Any]]:
    now = _utc_now_iso()
    return {
        "famatyyk": {
            "username": "famatyyk",
            "display_name": "Famatyyk",
            "role": "owner",
            "password_hash": _hash_password("ctoa-owner"),
            "created_at": now,
        },
        "strategos": {
            "username": "strategos",
            "display_name": "Strategos",
            "role": "operator",
            "password_hash": _hash_password("ctoa-ops"),
            "created_at": now,
        },
        "recruit": {
            "username": "recruit",
            "display_name": "Community Recruit",
            "role": "member",
            "password_hash": _hash_password("ctoa-community"),
            "created_at": now,
        },
    }


def _load_auth_store() -> Dict[str, Any]:
    if AUTH_STORE_FILE.exists():
        try:
            payload = json.loads(AUTH_STORE_FILE.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("users", {})
                payload.setdefault("invites", [])
                payload.setdefault("activity", [])
                return payload
        except (OSError, json.JSONDecodeError):
            pass

    seeded = {
        "users": _seed_accounts(),
        "invites": [],
        "activity": [
            {
                "id": secrets.token_hex(8),
                "type": "bootstrap",
                "actor": "system",
                "target": "community",
                "at": _utc_now_iso(),
                "meta": {"seeded_users": 3},
            }
        ],
    }
    _atomic_write_json(AUTH_STORE_FILE, seeded)
    return seeded


def _save_auth_store(store: Dict[str, Any]) -> None:
    _atomic_write_json(AUTH_STORE_FILE, store)


def _append_activity(store: Dict[str, Any], *, event_type: str, actor: str, target: str, meta: Optional[Dict[str, Any]] = None) -> None:
    activity = store.setdefault("activity", [])
    activity.insert(
        0,
        {
            "id": secrets.token_hex(8),
            "type": event_type,
            "actor": actor,
            "target": target,
            "at": _utc_now_iso(),
            "meta": meta or {},
        },
    )
    store["activity"] = activity[:200]


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padded = data + "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _jwt_encode(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    head = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{head}.{body}".encode("ascii")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{head}.{body}.{_b64url_encode(signature)}"


def _jwt_decode(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    provided = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    exp = int(payload.get("exp", 0))
    if exp <= int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")

    return payload


def _issue_token(user: Dict[str, Any]) -> str:
    now = int(time.time())
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "iat": now,
        "exp": now + max(300, JWT_TTL_SECONDS),
    }
    return _jwt_encode(payload)


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _current_user(authorization: Optional[str], *, required: bool = True) -> Optional[Dict[str, Any]]:
    token = _extract_bearer(authorization)
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        return None

    payload = _jwt_decode(token)
    username = str(payload.get("sub", "")).strip().lower()
    store = _load_auth_store()
    user = store.get("users", {}).get(username)
    if not user:
        raise HTTPException(status_code=401, detail="Unknown account")
    return {
        "username": user["username"],
        "display_name": user.get("display_name", user["username"]),
        "role": user["role"],
        "created_at": user.get("created_at"),
    }


def _require_roles(user: Dict[str, Any], allowed: List[str]) -> None:
    if user.get("role") not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient role")


def _select_models(req: ChatRequest) -> Dict[str, Any]:
    route_mode = (req.route_mode or ROUTE_DEFAULT or "auto").lower()
    route_info: Dict[str, Any] = {
        "mode": route_mode,
        "reason": [],
        "primary": None,
        "secondary": None,
        "backend_url": None,
        "backend_key": None,
        "secondary_backend_url": None,
        "secondary_backend_key": None,
    }

    if req.model and req.model not in {"auto", "small", "large"}:
        route_info["mode"] = "explicit"
        route_info["reason"].append("explicit_model")
        route_info["primary"] = req.model
        return route_info

    if req.model in {"small", "large"}:
        route_mode = req.model
        route_info["mode"] = req.model

    if route_mode == "small":
        route_info["primary"] = MODEL_SMALL
        route_info["backend_url"] = SMALL_BACKEND_URL
        route_info["backend_key"] = SMALL_API_KEY
        route_info["secondary"] = MODEL_LARGE if MODEL_LARGE != MODEL_SMALL else None
        route_info["secondary_backend_url"] = LARGE_BACKEND_URL
        route_info["secondary_backend_key"] = LARGE_API_KEY
        route_info["reason"].append("forced_small")
        return route_info

    if route_mode == "large":
        route_info["primary"] = MODEL_LARGE
        route_info["backend_url"] = LARGE_BACKEND_URL
        route_info["backend_key"] = LARGE_API_KEY
        route_info["secondary"] = MODEL_SMALL if MODEL_LARGE != MODEL_SMALL else None
        route_info["secondary_backend_url"] = SMALL_BACKEND_URL
        route_info["secondary_backend_key"] = SMALL_API_KEY
        route_info["reason"].append("forced_large")
        return route_info

    chars = _estimate_chars(req.messages)
    turns = len(req.messages)
    complex_prompt = _is_complex(req.messages)

    if chars >= ROUTER_LONG_CHARS:
        route_info["reason"].append("long_prompt")
    if turns >= ROUTER_LONG_TURNS:
        route_info["reason"].append("long_history")
    if complex_prompt:
        route_info["reason"].append("complexity")

    if route_info["reason"]:
        route_info["primary"] = MODEL_LARGE
        route_info["backend_url"] = LARGE_BACKEND_URL
        route_info["backend_key"] = LARGE_API_KEY
        route_info["secondary"] = MODEL_SMALL if MODEL_LARGE != MODEL_SMALL else None
        route_info["secondary_backend_url"] = SMALL_BACKEND_URL
        route_info["secondary_backend_key"] = SMALL_API_KEY
    else:
        route_info["primary"] = MODEL_SMALL
        route_info["backend_url"] = SMALL_BACKEND_URL
        route_info["backend_key"] = SMALL_API_KEY
        route_info["secondary"] = MODEL_LARGE if MODEL_LARGE != MODEL_SMALL else None
        route_info["secondary_backend_url"] = LARGE_BACKEND_URL
        route_info["secondary_backend_key"] = LARGE_API_KEY
        route_info["reason"].append("default_small")

    return route_info


async def _call_model(
    model_name: str,
    backend_url: str,
    backend_key: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float],
    max_tokens: Optional[int],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {"Content-Type": "application/json"}
    if backend_key:
        headers["Authorization"] = f"Bearer {backend_key}"

    async with httpx.AsyncClient(timeout=180, headers=headers) as client:
        response = await client.post(f"{backend_url}/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()


async def _execute_chat(req: ChatRequest) -> Dict[str, Any]:
    route = _select_models(req)
    quality_retry = req.quality_retry if req.quality_retry is not None else QUALITY_RETRY_DEFAULT

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    start = time.time()
    used_fallback = False
    low_quality_retry = False

    try:
        data = await _call_model(
            route["primary"],
            route["backend_url"],
            route["backend_key"],
            messages,
            req.temperature,
            req.max_tokens,
        )
    except Exception as first_error:
        secondary = route.get("secondary")
        if not secondary:
            _sc, _msg = _friendly_model_error(first_error)
            raise HTTPException(status_code=_sc, detail=_msg) from first_error
        used_fallback = True
        try:
            data = await _call_model(
                secondary,
                route["secondary_backend_url"],
                route["secondary_backend_key"],
                messages,
                req.temperature,
                req.max_tokens,
            )
            route["reason"].append("fallback_error")
            route["primary"] = secondary
            route["backend_url"] = route["secondary_backend_url"]
            route["backend_key"] = route["secondary_backend_key"]
        except Exception as second_error:
            _sc2, _msg2 = _friendly_model_error(second_error)
            raise HTTPException(status_code=_sc2, detail=_msg2) from second_error

    content = _sanitize_assistant_content(data["choices"][0]["message"]["content"])

    if quality_retry and route["primary"] == MODEL_SMALL and route.get("secondary"):
        user_chars = _estimate_chars([m for m in req.messages if m.role == "user"])
        if _low_quality(content, user_chars):
            low_quality_retry = True
            retry_data = await _call_model(
                route["secondary"],
                route["secondary_backend_url"],
                route["secondary_backend_key"],
                messages,
                req.temperature,
                req.max_tokens,
            )
            content = _sanitize_assistant_content(retry_data["choices"][0]["message"]["content"])
            route["reason"].append("fallback_quality")
            route["primary"] = route["secondary"]
            route["backend_url"] = route["secondary_backend_url"]
            route["backend_key"] = route["secondary_backend_key"]

    latency_ms = int((time.time() - start) * 1000)
    route_info = {
        "requested_mode": req.route_mode or ROUTE_DEFAULT,
        "mode": route["mode"],
        "model": route["primary"],
        "backend_url": route["backend_url"],
        "backend_kind": _backend_kind(route["backend_url"]),
        "fallback_model": route.get("secondary"),
        "fallback_backend_url": route.get("secondary_backend_url"),
        "reason": route["reason"],
        "fallback_used": used_fallback,
        "quality_retry_used": low_quality_retry,
        "latency_ms": latency_ms,
    }

    if ROUTER_LOG:
        print(f"[router] {route_info}")

    return {"content": content, "route": route_info}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "vps": "116.202.96.250"}


@app.get("/api/status")
def status() -> Dict[str, Any]:
    return {
        "runner": "active",
        "model": MODEL_SMALL,
        "model_small": MODEL_SMALL,
        "model_large": MODEL_LARGE,
        "route_default": ROUTE_DEFAULT,
        "small_backend_url": SMALL_BACKEND_URL,
        "large_backend_url": LARGE_BACKEND_URL,
        "auth_required": AUTH_REQUIRED,
    }


@app.post("/api/auth/register")
def register(req: RegisterRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    username = _sanitize_username(req.username)
    password = req.password.strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    store = _load_auth_store()
    users = store.setdefault("users", {})
    if username in users:
        raise HTTPException(status_code=409, detail="Username already exists")

    requested_role = req.role or "member"
    if users and requested_role != "member":
        current = _current_user(authorization, required=True)
        _require_roles(current, ["owner"])

    users[username] = {
        "username": username,
        "display_name": (req.display_name or username).strip() or username,
        "role": requested_role,
        "password_hash": _hash_password(password),
        "created_at": _utc_now_iso(),
    }
    _append_activity(store, event_type="register", actor=username, target="account", meta={"role": requested_role})
    _save_auth_store(store)

    token = _issue_token(users[username])
    return {
        "token": token,
        "user": {
            "username": username,
            "display_name": users[username]["display_name"],
            "role": requested_role,
            "created_at": users[username]["created_at"],
        },
    }


@app.post("/api/auth/login")
def login(req: LoginRequest) -> Dict[str, Any]:
    username = _sanitize_username(req.username)
    store = _load_auth_store()
    users = store.setdefault("users", {})
    user = users.get(username)
    if not user or not _verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _append_activity(store, event_type="login", actor=username, target="session")
    _save_auth_store(store)

    token = _issue_token(user)
    return {
        "token": token,
        "user": {
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "role": user["role"],
            "created_at": user.get("created_at"),
        },
    }


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _current_user(authorization, required=True)
    return {"user": user}


@app.post("/api/community/invite")
def create_invite(req: InviteRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _current_user(authorization, required=True)
    _require_roles(actor, ["owner", "operator"])

    username = _sanitize_username(req.username)
    store = _load_auth_store()
    users = store.setdefault("users", {})
    if username not in users:
        raise HTTPException(status_code=404, detail="Target account not found")

    invite = {
        "code": secrets.token_urlsafe(12),
        "username": username,
        "role": req.role,
        "created_by": actor["username"],
        "created_at": _utc_now_iso(),
        "accepted_at": None,
        "accepted_by": None,
    }
    invites = store.setdefault("invites", [])
    invites.insert(0, invite)
    store["invites"] = invites[:200]

    _append_activity(
        store,
        event_type="invite_created",
        actor=actor["username"],
        target=username,
        meta={"role": req.role, "code": invite["code"]},
    )
    _save_auth_store(store)
    return {"invite": invite}


@app.post("/api/community/invite/accept")
def accept_invite(req: AcceptInviteRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _current_user(authorization, required=True)
    store = _load_auth_store()
    invites = store.setdefault("invites", [])
    users = store.setdefault("users", {})

    invite = next((i for i in invites if i.get("code") == req.code and not i.get("accepted_at")), None)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or already accepted")

    if invite.get("username") != actor["username"]:
        raise HTTPException(status_code=403, detail="Invite does not belong to this account")

    users[actor["username"]]["role"] = invite["role"]
    invite["accepted_at"] = _utc_now_iso()
    invite["accepted_by"] = actor["username"]

    _append_activity(
        store,
        event_type="invite_accepted",
        actor=actor["username"],
        target=actor["username"],
        meta={"role": invite["role"], "code": invite["code"]},
    )
    _save_auth_store(store)

    refreshed = users[actor["username"]]
    return {
        "token": _issue_token(refreshed),
        "user": {
            "username": refreshed["username"],
            "display_name": refreshed.get("display_name", refreshed["username"]),
            "role": refreshed["role"],
            "created_at": refreshed.get("created_at"),
        },
    }


@app.get("/api/community/members")
def community_members(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _current_user(authorization, required=True)
    store = _load_auth_store()
    users = store.setdefault("users", {})
    members = [
        {
            "username": u["username"],
            "display_name": u.get("display_name", u["username"]),
            "role": u["role"],
            "created_at": u.get("created_at"),
        }
        for u in users.values()
    ]
    members.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"members": members}


@app.post("/api/community/members/{username}/role")
def set_member_role(username: str, req: RoleUpdateRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    actor = _current_user(authorization, required=True)
    _require_roles(actor, ["owner"])

    clean_username = _sanitize_username(username)
    store = _load_auth_store()
    users = store.setdefault("users", {})
    target = users.get(clean_username)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    if clean_username == actor["username"] and req.role != "owner":
        owners = [u for u in users.values() if u.get("role") == "owner"]
        if len(owners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    target["role"] = req.role
    _append_activity(
        store,
        event_type="role_updated",
        actor=actor["username"],
        target=clean_username,
        meta={"role": req.role},
    )
    _save_auth_store(store)

    return {
        "member": {
            "username": target["username"],
            "display_name": target.get("display_name", target["username"]),
            "role": target["role"],
            "created_at": target.get("created_at"),
        }
    }


@app.get("/api/community/feed")
def community_feed(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _current_user(authorization, required=True)
    store = _load_auth_store()
    return {"events": store.setdefault("activity", [])[:100]}


@app.get("/api/community/invites")
def community_invites(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _current_user(authorization, required=True)
    _require_roles(user, ["owner", "operator"])
    store = _load_auth_store()
    invites = store.setdefault("invites", [])
    return {"invites": invites[:100]}


@app.get("/api/release-evidence")
def release_evidence() -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    if not RELEASE_EVIDENCE_FILE.exists():
        return {
            "ok": False,
            "state": "NO_EVIDENCE",
            "evidence_path": str(RELEASE_EVIDENCE_FILE),
            "updated_at": now_iso,
            "message": "No release evidence file found.",
        }

    try:
        payload = json.loads(RELEASE_EVIDENCE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": str(RELEASE_EVIDENCE_FILE),
            "updated_at": now_iso,
            "message": f"Failed to read release evidence: {exc}",
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": str(RELEASE_EVIDENCE_FILE),
            "updated_at": now_iso,
            "message": "Release evidence payload must be a JSON object.",
        }

    return {
        "ok": True,
        "state": str(payload.get("state", "UNKNOWN")),
        "evidence_path": str(RELEASE_EVIDENCE_FILE),
        "updated_at": now_iso,
        "evidence": payload,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    user = _current_user(authorization, required=AUTH_REQUIRED)
    result = await _execute_chat(req)
    body: Dict[str, Any] = {"role": "assistant", "content": _sanitize_assistant_content(result["content"])}
    if user:
        body["account"] = {"username": user["username"], "role": user["role"]}
    if req.debug_route:
        body["route"] = result["route"]
    return body


@app.post("/v1/chat/completions")
async def chat_completions(req: OpenAIChatRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _current_user(authorization, required=AUTH_REQUIRED)

    internal = ChatRequest(
        messages=req.messages,
        route_mode=req.route_mode,
        quality_retry=req.quality_retry,
        debug_route=req.debug_route,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    result = await _execute_chat(internal)

    response: Dict[str, Any] = {
        "id": f"chatcmpl-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result["route"]["model"],
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": _sanitize_assistant_content(result["content"])},
            }
        ],
    }

    if req.debug_route:
        response["route"] = result["route"]

    return response
