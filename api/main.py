from typing import Any, Dict, List, Literal, Optional
from pathlib import Path
from datetime import datetime, timezone
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import sys
import threading
import time
import uuid

from api import startup_guard as _startup_guard  # noqa: F401
import bcrypt
import httpx
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from runner import http_safety


app = FastAPI(title="CTOAi API", version="1.3.0")
ROOT = Path(__file__).resolve().parents[1]


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


def _is_production_env() -> bool:
    values = (
        os.getenv("CTOA_ENV", "").strip().lower(),
        os.getenv("ENV", "").strip().lower(),
    )
    return any(value in {"prod", "production"} for value in values)


def _is_weak_secret(secret: str) -> bool:
    normalized = (secret or "").strip()
    lowered = normalized.lower()
    if not normalized or len(normalized) < 32:
        return True
    if lowered.startswith("change-me") or lowered.startswith("changeme"):
        return True
    if lowered in {"default", "secret", "jwt-secret", "ctoa-jwt-secret"}:
        return True
    return False


cors_origins = [origin.strip() for origin in os.getenv("CTOA_CORS_ORIGINS", "*").split(",") if origin.strip()]
if _is_production_env() and (not cors_origins or "*" in cors_origins):
    raise RuntimeError(
        "Refusing to start in production with wildcard CORS. "
        "Set CTOA_CORS_ORIGINS to explicit origins."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
RELEASE_EVIDENCE_MAX_BYTES = max(
    1024, _env_int("CTOA_RELEASE_EVIDENCE_MAX_BYTES", 1024 * 1024)
)

AUTH_STORE_FILE = Path(
    os.getenv("CTOA_AUTH_STORE_FILE", "runtime/state/auth_store.json")
)
AUTH_STORE_MAX_BYTES = max(4096, _env_int("CTOA_AUTH_STORE_MAX_BYTES", 1024 * 1024))
AUTH_REQUIRED = _env_bool("CTOA_AUTH_REQUIRED", True)
ALLOW_SEED_ACCOUNTS = _env_bool("CTOA_ALLOW_SEED_ACCOUNTS", False)
AUTH_BOOTSTRAP_CODE = os.getenv("CTOA_AUTH_BOOTSTRAP_CODE", "").strip()
JWT_SECRET = os.getenv("CTOA_JWT_SECRET", "").strip()
JWT_TTL_SECONDS = _env_int("CTOA_JWT_TTL_SECONDS", 86400)

if _is_weak_secret(JWT_SECRET):
    if _is_production_env():
        raise RuntimeError(
            "Refusing to start in production with missing or weak CTOA_JWT_SECRET."
        )
    JWT_SECRET = secrets.token_urlsafe(48)
    print(
        "[security] WARNING: using ephemeral JWT secret in non-production. "
        "Set CTOA_JWT_SECRET to a strong value.",
        file=sys.stderr,
    )


def _api_self_register_enabled() -> bool:
    return _env_bool("CTOA_API_SELF_REGISTER_ENABLED", not _is_production_env())


def _api_self_register_code() -> str:
    return os.getenv("CTOA_API_SELF_REGISTER_CODE", "").strip()


def _validate_api_security_config() -> None:
    if (
        _is_production_env()
        and _api_self_register_enabled()
        and not _api_self_register_code()
    ):
        raise RuntimeError(
            "CTOA_API_SELF_REGISTER_CODE must be set when API self registration is enabled in production"
        )


_validate_api_security_config()

CTOA_RATE_LIMIT_ENABLED = _env_bool("CTOA_RATE_LIMIT_ENABLED", True)
CTOA_TRUST_PROXY_HEADERS = _env_bool("CTOA_TRUST_PROXY_HEADERS", False)
CTOA_CHAT_RATE_LIMIT_PER_MIN = max(1, _env_int("CTOA_CHAT_RATE_LIMIT_PER_MIN", 24))
CTOA_AUTH_RATE_LIMIT_PER_MIN = max(1, _env_int("CTOA_AUTH_RATE_LIMIT_PER_MIN", 20))
CTOA_READ_RATE_LIMIT_PER_MIN = max(1, _env_int("CTOA_READ_RATE_LIMIT_PER_MIN", 120))
CTOA_AUDIT_LOG_FILE = Path(
    os.getenv("CTOA_AUDIT_LOG_FILE", "runtime/state/http_audit.log")
)

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

_SAFETY_STARTUP_TIME: str = datetime.now(timezone.utc).isoformat()
SAFETY_METRICS: Dict[str, int] = {
    "sanitizer_interventions": 0,
    "model_errors_masked": 0,
}
_METRICS_LOCK = threading.Lock()


SAFETY_ALERT_THRESHOLD = max(1, _env_int("CTOA_SAFETY_ALERT_THRESHOLD", 1))


def _safety_telemetry_snapshot() -> Dict[str, Any]:
    with _METRICS_LOCK:
        sanitizer_interventions = int(SAFETY_METRICS.get("sanitizer_interventions", 0))
        model_errors_masked = int(SAFETY_METRICS.get("model_errors_masked", 0))

    total_events = sanitizer_interventions + model_errors_masked
    alert_active = sanitizer_interventions >= SAFETY_ALERT_THRESHOLD
    return {
        "startup_time": _SAFETY_STARTUP_TIME,
        "sanitizer_interventions": sanitizer_interventions,
        "model_errors_masked": model_errors_masked,
        "total_events": total_events,
        "alert_threshold": SAFETY_ALERT_THRESHOLD,
        "alert_active": alert_active,
        "alert_level": "warning" if alert_active else "normal",
    }


def _sanitize_assistant_content(content: str) -> str:
    """Block fabricated administrative-action claims in assistant responses."""
    if _ADMIN_FABRICATION_RE.search(content):
        with _METRICS_LOCK:
            SAFETY_METRICS["sanitizer_interventions"] += 1
        print(
            json.dumps(
                {
                    "event": "safety_intervention",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": "admin_fabrication",
                }
            ),
            file=sys.stderr,
        )
        return _SAFE_DISCLAIMER
    return content


def _friendly_model_error(exc: Exception) -> "tuple[int, str]":
    """Return (http_status, safe_detail) without exposing raw upstream error details."""
    _http_status: Optional[int] = None
    if isinstance(exc, httpx.HTTPStatusError):
        sc = exc.response.status_code
        _http_status = sc
        if sc == 429:
            _sc, _msg = (
                503,
                "Service temporarily unavailable: model capacity exceeded. Please retry shortly.",
            )
        elif sc >= 500:
            _sc, _msg = (
                503,
                "Model backend is temporarily unavailable. Please retry shortly.",
            )
        else:
            _sc, _msg = 502, "Model backend returned an unexpected response."
    elif isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        _sc, _msg = 503, "Model backend is unreachable. Please retry shortly."
    else:
        _sc, _msg = 502, "Model call failed. Please retry shortly."
    with _METRICS_LOCK:
        SAFETY_METRICS["model_errors_masked"] += 1
    print(
        json.dumps(
            {
                "event": "model_error_masked",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "http_status": _http_status,
            }
        ),
        file=sys.stderr,
    )
    return _sc, _msg


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
    registration_code: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class BootstrapRequest(BaseModel):
    username: str
    password: str
    bootstrap_code: str


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
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


_SECRET_FIELD_RE = re.compile(
    r"(?i)(access[_-]?token|refresh[_-]?token|id[_-]?token|token|password|secret|api[_-]?key|apikey|client[_-]?secret)"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(access[_-]?token|refresh[_-]?token|id[_-]?token|token|password|secret|api[_-]?key|apikey|client[_-]?secret)\s*=\s*([^\s,;}\]]+)"
)
_JSON_SECRET_RE = re.compile(
    r'(?i)("?(?:access[_-]?token|refresh[_-]?token|id[_-]?token|token|password|secret|api[_-]?key|apikey|client[_-]?secret)"?\s*:\s*")([^"]+)(")'
)
_AUTH_HEADER_RE = re.compile(
    r"\b((?:Bearer|Basic)\s+)[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE
)
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?:\\\\\?\\)?[A-Za-z]:\\[^\s\"'<>|]+")
_POSIX_LOCAL_PATH_RE = re.compile(
    r"(?<![\w])/(?:home|Users|tmp|opt|var|mnt|workspace|root)/[^\s\"'<>]+"
)


def _display_path(path_value: Path | str) -> str:
    raw = str(path_value or "").strip().replace("\\\\?\\", "")
    if not raw:
        return ""
    if re.match(r"^[A-Za-z]:\\", raw):
        normalized = raw.replace("\\", "/")
        root_normalized = str(ROOT.resolve()).replace("\\", "/").rstrip("/")
        if normalized.casefold().startswith(root_normalized.casefold() + "/"):
            return normalized[len(root_normalized) + 1 :]
        name = raw.rstrip("\\/").replace("\\", "/").rsplit("/", 1)[-1]
        return f"[external]/{name or 'path'}"
    path_obj = Path(raw)
    if not path_obj.is_absolute():
        return raw.replace("\\", "/").lstrip("./")

    try:
        resolved = path_obj.resolve(strict=False)
        relative = resolved.relative_to(ROOT.resolve())
        return relative.as_posix()
    except (OSError, ValueError):
        return f"[external]/{path_obj.name or 'path'}"


def _redact_release_evidence_text(value: str) -> str:
    redacted = str(value or "")
    redacted = _AUTH_HEADER_RE.sub(r"\1[redacted]", redacted)
    redacted = _JSON_SECRET_RE.sub(r"\1[redacted]\3", redacted)
    redacted = _SECRET_ASSIGNMENT_RE.sub(r"\1=[redacted]", redacted)
    redacted = _WINDOWS_ABSOLUTE_PATH_RE.sub(
        lambda match: _display_path(match.group(0)), redacted
    )
    redacted = _POSIX_LOCAL_PATH_RE.sub(
        lambda match: _display_path(match.group(0)), redacted
    )
    return redacted[:4000]


def _public_release_evidence_value(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            _redact_release_evidence_text(str(item_key)): _public_release_evidence_value(
                item_value, str(item_key)
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_public_release_evidence_value(item, key) for item in value]
    if isinstance(value, str):
        if _SECRET_FIELD_RE.search(key):
            return "[redacted]"
        return _redact_release_evidence_text(value)
    return value


def _public_audit_value(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            _redact_release_evidence_text(str(item_key)): _public_audit_value(
                item_value, str(item_key)
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_public_audit_value(item, key) for item in value[:20]]
    if isinstance(value, str):
        if _SECRET_FIELD_RE.search(key):
            return "[redacted]"
        return _redact_release_evidence_text(value)[:1000]
    return value


def _read_release_evidence_payload(path: Path) -> Dict[str, Any]:
    if path.is_symlink():
        raise ValueError("unsafe_symlink")
    file_size = path.stat().st_size
    if file_size > RELEASE_EVIDENCE_MAX_BYTES:
        raise ValueError("too_large")
    with path.open("rb") as handle:
        raw = handle.read(RELEASE_EVIDENCE_MAX_BYTES + 1)
    if len(raw) > RELEASE_EVIDENCE_MAX_BYTES:
        raise ValueError("too_large")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("not_object")
    return payload


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _sanitize_username(username: str) -> str:
    clean = "".join(
        ch for ch in username.strip().lower() if ch.isalnum() or ch in {"_", "-", "."}
    )
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid username")
    return clean


def _seed_password(env_name: str) -> str:
    password = os.getenv(env_name, "").strip()
    if not password:
        raise RuntimeError(f"{env_name} must be set when CTOA_ALLOW_SEED_ACCOUNTS=true")
    return password


def _seed_accounts() -> Dict[str, Dict[str, Any]]:
    now = _utc_now_iso()
    return {
        "famatyyk": {
            "username": "famatyyk",
            "display_name": "Famatyyk",
            "role": "owner",
            "password_hash": _hash_password(
                _seed_password("CTOA_SEED_FAMATYYK_PASSWORD")
            ),
            "created_at": now,
        },
        "strategos": {
            "username": "strategos",
            "display_name": "Strategos",
            "role": "operator",
            "password_hash": _hash_password(
                _seed_password("CTOA_SEED_STRATEGOS_PASSWORD")
            ),
            "created_at": now,
        },
        "recruit": {
            "username": "recruit",
            "display_name": "Community Recruit",
            "role": "member",
            "password_hash": _hash_password(
                _seed_password("CTOA_SEED_RECRUIT_PASSWORD")
            ),
            "created_at": now,
        },
    }


def _default_account_seed_blocked() -> bool:
    return _is_production_env() or not _env_bool("CTOA_ALLOW_SEED_ACCOUNTS", False)


def _read_auth_store_payload(path: Path) -> Dict[str, Any]:
    if path.is_symlink():
        raise RuntimeError("Invalid CTOA_AUTH_STORE_FILE; refusing to load auth store")
    try:
        with path.open("rb") as handle:
            raw = handle.read(AUTH_STORE_MAX_BYTES + 1)
    except OSError as exc:
        raise RuntimeError("Invalid CTOA_AUTH_STORE_FILE; refusing to load auth store") from exc
    if len(raw) > AUTH_STORE_MAX_BYTES:
        raise RuntimeError("Invalid CTOA_AUTH_STORE_FILE; refusing to load auth store")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Invalid CTOA_AUTH_STORE_FILE; refusing to load auth store") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Invalid CTOA_AUTH_STORE_FILE; refusing to load auth store")
    return payload


def _load_auth_store() -> Dict[str, Any]:
    if AUTH_STORE_FILE.exists() or AUTH_STORE_FILE.is_symlink():
        payload = _read_auth_store_payload(AUTH_STORE_FILE)
        payload.setdefault("users", {})
        payload.setdefault("invites", [])
        payload.setdefault("activity", [])
        return payload

    if _default_account_seed_blocked():
        raise RuntimeError(
            "Refusing to seed default auth accounts; provision CTOA_AUTH_STORE_FILE before startup"
        )

    seeded_users: Dict[str, Dict[str, Any]] = {}
    if ALLOW_SEED_ACCOUNTS:
        seeded_users = _seed_accounts()
        print(
            "[security] WARNING: legacy seed accounts are enabled (CTOA_ALLOW_SEED_ACCOUNTS=true).",
            file=sys.stderr,
        )

    seeded = {
        "users": seeded_users,
        "invites": [],
        "activity": [
            {
                "id": secrets.token_hex(8),
                "type": "bootstrap",
                "actor": "system",
                "target": "community",
                "at": _utc_now_iso(),
                "meta": {
                    "seeded_users": len(seeded_users),
                    "seed_mode": "enabled" if ALLOW_SEED_ACCOUNTS else "disabled",
                },
            }
        ],
    }
    _atomic_write_json(AUTH_STORE_FILE, seeded)
    return seeded


def _save_auth_store(store: Dict[str, Any]) -> None:
    _atomic_write_json(AUTH_STORE_FILE, store)


def _append_activity(
    store: Dict[str, Any],
    *,
    event_type: str,
    actor: str,
    target: str,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
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
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{head}.{body}.{_b64url_encode(signature)}"


def _jwt_decode(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = hmac.new(
        JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
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


_RATE_LIMIT_LOCK = threading.Lock()
_AUDIT_LOCK = threading.Lock()
_RATE_LIMIT_BUCKETS: Dict[str, Dict[str, int]] = {}


def _first_forwarded_ip(value: str) -> str:
    first = str(value or "").split(",", 1)[0].strip()
    if not first:
        return ""
    try:
        return ipaddress.ip_address(first).compressed
    except ValueError:
        return ""


def _client_ip_from_request(request: Request) -> str:
    if CTOA_TRUST_PROXY_HEADERS:
        forwarded = _first_forwarded_ip(request.headers.get("x-forwarded-for", ""))
        if forwarded:
            return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit_group(path: str) -> Optional[str]:
    if path.startswith("/api/chat") or path.startswith("/v1/chat/completions"):
        return "chat"
    if path.startswith("/api/auth") or path.startswith("/api/community"):
        return "auth"
    if path.startswith("/api/"):
        return "read"
    return None


def _rate_limit_for_group(group: str) -> int:
    if group == "chat":
        return CTOA_CHAT_RATE_LIMIT_PER_MIN
    if group == "auth":
        return CTOA_AUTH_RATE_LIMIT_PER_MIN
    return CTOA_READ_RATE_LIMIT_PER_MIN


def _consume_rate_limit(
    ip: str, group: str, now_ts: Optional[float] = None
) -> Dict[str, int]:
    now = now_ts if now_ts is not None else time.time()
    bucket = int(now // 60)
    retry_after = max(1, 60 - int(now % 60))
    limit = _rate_limit_for_group(group)
    key = f"{group}:{ip}"

    with _RATE_LIMIT_LOCK:
        record = _RATE_LIMIT_BUCKETS.get(key)
        if not record or record.get("bucket") != bucket:
            record = {"bucket": bucket, "count": 0}

        count = int(record.get("count", 0))
        if count >= limit:
            _RATE_LIMIT_BUCKETS[key] = record
            return {
                "allowed": 0,
                "retry_after": retry_after,
                "limit": limit,
                "remaining": 0,
            }

        count += 1
        record["count"] = count
        _RATE_LIMIT_BUCKETS[key] = record

        if len(_RATE_LIMIT_BUCKETS) > 5000:
            stale = [
                k
                for k, v in _RATE_LIMIT_BUCKETS.items()
                if int(v.get("bucket", -1)) != bucket
            ]
            for stale_key in stale[:2000]:
                _RATE_LIMIT_BUCKETS.pop(stale_key, None)

        return {
            "allowed": 1,
            "retry_after": retry_after,
            "limit": limit,
            "remaining": max(0, limit - count),
        }


def _audit_actor_from_request(request: Request) -> str:
    token = _extract_bearer(request.headers.get("authorization"))
    if not token:
        return "anonymous"
    try:
        payload = _jwt_decode(token)
    except HTTPException:
        return "invalid_token"
    except Exception:
        return "invalid_token"
    actor = str(payload.get("sub", "")).strip()
    return actor or "anonymous"


def _append_audit_http(
    request: Request, status: int, actor: str, meta: Optional[Dict[str, Any]] = None
) -> None:
    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "method": _redact_release_evidence_text(request.method)[:20],
        "path": _redact_release_evidence_text(request.url.path)[:500],
        "status": int(status),
        "actor": _redact_release_evidence_text(actor)[:128],
        "ip": _redact_release_evidence_text(_client_ip_from_request(request))[:128],
        "ua": _redact_release_evidence_text(
            request.headers.get("user-agent", "")
        )[:500],
        "meta": _public_audit_value(meta or {}),
    }
    try:
        CTOA_AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=True)
        with _AUDIT_LOCK:
            with CTOA_AUDIT_LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except OSError:
        pass


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path
    is_api_request = path.startswith("/api/")
    actor = _audit_actor_from_request(request) if is_api_request else "anonymous"
    status_code = 500
    meta: Dict[str, Any] = {}

    if is_api_request and CTOA_RATE_LIMIT_ENABLED:
        group = _rate_limit_group(path)
        if group:
            limit = _consume_rate_limit(_client_ip_from_request(request), group)
            meta.update(
                {
                    "rate_group": group,
                    "rate_limit": limit["limit"],
                    "rate_remaining": limit["remaining"],
                }
            )
            if not bool(limit["allowed"]):
                retry_after = int(limit["retry_after"])
                status_code = 429
                meta["rate_limited"] = True
                _append_audit_http(request, status_code, actor, meta)
                return JSONResponse(
                    {
                        "detail": "Rate limit exceeded. Please retry shortly.",
                        "code": "RATE_LIMITED",
                        "retry_after": retry_after,
                    },
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )

    try:
        response = await call_next(request)
        status_code = int(response.status_code)
        return response
    finally:
        if is_api_request:
            _append_audit_http(request, status_code, actor, meta)


def _current_user(
    authorization: Optional[str], *, required: bool = True
) -> Optional[Dict[str, Any]]:
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
    safe_backend_url = http_safety.require_model_backend_url(
        backend_url,
        allow_remote=http_safety.env_enabled("CTOA_ALLOW_REMOTE_MODEL_BACKENDS"),
    )
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
        response = await client.post(
            f"{safe_backend_url}/chat/completions", json=payload
        )
        response.raise_for_status()
        return response.json()


async def _execute_chat(req: ChatRequest) -> Dict[str, Any]:
    route = _select_models(req)
    quality_retry = (
        req.quality_retry if req.quality_retry is not None else QUALITY_RETRY_DEFAULT
    )

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
            content = _sanitize_assistant_content(
                retry_data["choices"][0]["message"]["content"]
            )
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
        print(f"[router] {_safe_chat_route_info(route_info)}")

    return {"content": content, "route": route_info}


def _safe_chat_route_info(route_info: Dict[str, Any]) -> Dict[str, Any]:
    """Return chat routing evidence without internal backend URLs or keys."""
    allowed = {
        "requested_mode",
        "mode",
        "model",
        "backend_kind",
        "fallback_model",
        "reason",
        "fallback_used",
        "quality_retry_used",
        "latency_ms",
    }
    return {key: value for key, value in route_info.items() if key in allowed}


def _require_chat_debug_route_user(user: Optional[Dict[str, Any]]) -> None:
    if not user:
        raise HTTPException(
            status_code=403,
            detail="Operator role required for chat route debug metadata",
        )
    _require_roles(user, ["owner", "operator"])


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "vps": "116.202.96.250"}


@app.get("/api/status")
def status() -> Dict[str, Any]:
    safety = _safety_telemetry_snapshot()
    return {
        "runner": "active",
        "model": MODEL_SMALL,
        "model_small": MODEL_SMALL,
        "model_large": MODEL_LARGE,
        "route_default": ROUTE_DEFAULT,
        "small_backend_url": SMALL_BACKEND_URL,
        "large_backend_url": LARGE_BACKEND_URL,
        "auth_required": AUTH_REQUIRED,
        "safety": {
            "alert_active": safety["alert_active"],
            "alert_level": safety["alert_level"],
            "sanitizer_interventions": safety["sanitizer_interventions"],
            "model_errors_masked": safety["model_errors_masked"],
        },
    }


@app.post("/api/auth/bootstrap")
def bootstrap(req: BootstrapRequest) -> Dict[str, Any]:
    expected_code = AUTH_BOOTSTRAP_CODE
    if not expected_code:
        raise HTTPException(status_code=503, detail="Bootstrap is not configured")

    provided_code = req.bootstrap_code.strip()
    if not hmac.compare_digest(provided_code, expected_code):
        raise HTTPException(status_code=403, detail="Invalid bootstrap code")

    username = _sanitize_username(req.username)
    password = req.password.strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    store = _load_auth_store()
    users = store.setdefault("users", {})
    if users:
        raise HTTPException(status_code=409, detail="Bootstrap is already completed")

    users[username] = {
        "username": username,
        "display_name": username,
        "role": "owner",
        "password_hash": _hash_password(password),
        "created_at": _utc_now_iso(),
    }
    _append_activity(
        store,
        event_type="bootstrap_owner_created",
        actor=username,
        target="account",
        meta={"role": "owner"},
    )
    _save_auth_store(store)

    token = _issue_token(users[username])
    return {
        "token": token,
        "user": {
            "username": username,
            "display_name": users[username]["display_name"],
            "role": users[username]["role"],
            "created_at": users[username]["created_at"],
        },
    }


@app.post("/api/auth/register")
def register(
    req: RegisterRequest, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    username = _sanitize_username(req.username)
    password = req.password.strip()
    if len(password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    requested_role = req.role or "member"
    if requested_role != "member":
        current = _current_user(authorization, required=True)
        _require_roles(current, ["owner"])
    elif not _api_self_register_enabled():
        raise HTTPException(
            status_code=403, detail="Public self-registration is disabled"
        )
    elif _is_production_env():
        expected_code = _api_self_register_code()
        provided_code = (req.registration_code or "").strip()
        if (
            not expected_code
            or not provided_code
            or not hmac.compare_digest(provided_code, expected_code)
        ):
            raise HTTPException(status_code=403, detail="Invalid registration code")

    store = _load_auth_store()
    users = store.setdefault("users", {})
    if username in users:
        raise HTTPException(status_code=409, detail="Username already exists")

    requested_role = req.role or "member"
    if requested_role != "member":
        current = _current_user(authorization, required=True)
        _require_roles(current, ["owner"])
    users[username] = {
        "username": username,
        "display_name": (req.display_name or username).strip() or username,
        "role": requested_role,
        "password_hash": _hash_password(password),
        "created_at": _utc_now_iso(),
    }
    _append_activity(
        store,
        event_type="register",
        actor=username,
        target="account",
        meta={"role": requested_role},
    )
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
def create_invite(
    req: InviteRequest, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
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
def accept_invite(
    req: AcceptInviteRequest, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    actor = _current_user(authorization, required=True)
    store = _load_auth_store()
    invites = store.setdefault("invites", [])
    users = store.setdefault("users", {})

    invite = next(
        (i for i in invites if i.get("code") == req.code and not i.get("accepted_at")),
        None,
    )
    if not invite:
        raise HTTPException(
            status_code=404, detail="Invite not found or already accepted"
        )

    if invite.get("username") != actor["username"]:
        raise HTTPException(
            status_code=403, detail="Invite does not belong to this account"
        )

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
def community_members(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
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
def set_member_role(
    username: str,
    req: RoleUpdateRequest,
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
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
def community_feed(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _current_user(authorization, required=True)
    store = _load_auth_store()
    return {"events": store.setdefault("activity", [])[:100]}


@app.get("/api/community/invites")
def community_invites(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = _current_user(authorization, required=True)
    _require_roles(user, ["owner", "operator"])
    store = _load_auth_store()
    invites = store.setdefault("invites", [])
    return {"invites": invites[:100]}


@app.get("/api/release-evidence")
def release_evidence() -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    evidence_path = _display_path(RELEASE_EVIDENCE_FILE)
    if not RELEASE_EVIDENCE_FILE.exists():
        return {
            "ok": False,
            "state": "NO_EVIDENCE",
            "evidence_path": evidence_path,
            "updated_at": now_iso,
            "message": "No release evidence file found.",
        }

    try:
        payload = _read_release_evidence_payload(RELEASE_EVIDENCE_FILE)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": evidence_path,
            "updated_at": now_iso,
            "message": "Release evidence payload is invalid JSON.",
        }
    except ValueError as exc:
        if str(exc) == "too_large":
            return {
                "ok": False,
                "state": "TOO_LARGE",
                "evidence_path": evidence_path,
                "updated_at": now_iso,
                "message": "Release evidence file is too large to display safely.",
            }
        if str(exc) == "unsafe_symlink":
            return {
                "ok": False,
                "state": "ERROR",
                "evidence_path": evidence_path,
                "updated_at": now_iso,
                "message": "Release evidence file could not be read safely.",
            }
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": evidence_path,
            "updated_at": now_iso,
            "message": "Release evidence payload is invalid.",
        }
    except UnicodeDecodeError:
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": evidence_path,
            "updated_at": now_iso,
            "message": "Release evidence payload is not valid UTF-8.",
        }
    except OSError:
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": evidence_path,
            "updated_at": now_iso,
            "message": "Release evidence file could not be read.",
        }
    except TypeError:
        return {
            "ok": False,
            "state": "ERROR",
            "evidence_path": evidence_path,
            "updated_at": now_iso,
            "message": "Release evidence payload must be a JSON object.",
        }

    return {
        "ok": True,
        "state": str(payload.get("state", "UNKNOWN")),
        "evidence_path": evidence_path,
        "updated_at": now_iso,
        "evidence": _public_release_evidence_value(payload),
    }


@app.post("/api/chat")
async def chat(
    req: ChatRequest, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    user = _current_user(authorization, required=AUTH_REQUIRED)
    if req.debug_route:
        _require_chat_debug_route_user(user)
    result = await _execute_chat(req)
    body: Dict[str, Any] = {
        "role": "assistant",
        "content": _sanitize_assistant_content(result["content"]),
    }
    if user:
        body["account"] = {"username": user["username"], "role": user["role"]}
    if req.debug_route:
        body["route"] = _safe_chat_route_info(result["route"])
    return body


@app.post("/v1/chat/completions")
async def chat_completions(
    req: OpenAIChatRequest, authorization: Optional[str] = Header(default=None)
) -> Dict[str, Any]:
    user = _current_user(authorization, required=AUTH_REQUIRED)
    if req.debug_route:
        _require_chat_debug_route_user(user)

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
                "message": {
                    "role": "assistant",
                    "content": _sanitize_assistant_content(result["content"]),
                },
            }
        ],
    }

    if req.debug_route:
        response["route"] = _safe_chat_route_info(result["route"])

    return response


@app.get("/api/safety/metrics")
async def safety_metrics(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = _current_user(authorization, required=True)
    _require_roles(user, ["owner", "operator"])
    snapshot = _safety_telemetry_snapshot()
    return {
        "sanitizer_interventions": snapshot["sanitizer_interventions"],
        "model_errors_masked": snapshot["model_errors_masked"],
        "since": snapshot["startup_time"],
    }


@app.get("/api/safety/telemetry")
async def safety_telemetry(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    user = _current_user(authorization, required=True)
    _require_roles(user, ["owner", "operator"])
    return _safety_telemetry_snapshot()


@app.get("/api/safety/status")
async def safety_status() -> Dict[str, Any]:
    with _METRICS_LOCK:
        interventions = SAFETY_METRICS["sanitizer_interventions"]
    if interventions >= 10:
        return {"status": "elevated", "interventions": interventions}
    return {"status": "ok"}
