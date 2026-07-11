#!/usr/bin/env python3
import os
import re
import shutil
import shlex
import json
import time
import hmac
import ipaddress
import secrets
import sys as _sys
import uuid
import bcrypt
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from runner import process_safety
from runner.generated_manifest_safety import (
    iter_safe_manifest_files,
    resolve_latest_manifest_path,
)

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    import psycopg2
except Exception:
    psycopg2 = None

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, REGISTRY, generate_latest
except Exception:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    Counter = None
    Histogram = None
    REGISTRY = None

    def generate_latest() -> bytes:
        return b""
try:
    from redis import Redis
except Exception:
    Redis = None

if TYPE_CHECKING:
    from redis import Redis as RedisClient

ROOT = Path(__file__).resolve().parent.parent

_sys.path.insert(0, str(ROOT))
from runtime_context import (
    default_generated_dir,
    is_production_env,
    is_windows_host,
    mobile_console_enabled,
)
from runner.alert_rules import check_generation_failed_spike
from mobile_console.services.admin_settings_service import AdminSettingsService
from mobile_console.services.ideas_service import IdeasService

STATIC_DIR = ROOT / "mobile_console" / "static"
SITE_DIR = ROOT / "docs" / "site"
SITE_ASSETS_DIR = SITE_DIR / "assets"
SITE_INDEX_HTML = SITE_DIR / "index.html"
LIVE_DASHBOARD_HTML = ROOT / "docs" / "site" / "live-dashboard.html"
AUDIT_LOG = ROOT / "logs" / "mobile-console-audit.log"
AUTO_TRAINER_DIR = Path(os.environ.get("CTOA_TRAINING_REPORT_DIR", str(ROOT / "runtime" / "training-reports")))
AUTO_TRAINER_MARKDOWN_MAX_BYTES = 50_000
AUTO_TRAINER_JSON_MAX_BYTES = 200_000
ADMIN_SETTINGS_MAX_BYTES = 50_000
IDEA_PARKING_MAX_BYTES = 1_000_000
LOG_TAIL_MAX_BYTES = 200_000
LOCAL_JSON_MAX_BYTES = 200_000
GENERATED_MANIFEST_JSON_MAX_BYTES = 1_000_000
CLIENT_SYNC_INIT_MAX_BYTES = 200_000
CLIENT_SYNC_LUA_MAX_BYTES = 2_000_000
_DEFAULT_GENERATED_DIR = default_generated_dir(ROOT)
GENERATED_DIR = Path(os.environ.get("CTOA_GENERATED_DIR", str(_DEFAULT_GENERATED_DIR)))
GENERATED_MANIFESTS_DIR = GENERATED_DIR / "manifests"
ADMIN_SETTINGS_FILE = Path(os.environ.get("CTOA_ADMIN_SETTINGS_FILE", str(ROOT / "runtime" / "admin-panel-settings.json")))
IDEA_PARKING_FILE = Path(os.environ.get("CTOA_IDEA_PARKING_FILE", str(ROOT / "runtime" / "idea-parking.json")))
PRODUCT_MANIFEST_FILE = ROOT / "product" / "ctoa-toolkit.manifest.json"
PRODUCT_STATE_DIR = Path(os.environ.get("CTOA_PRODUCT_STATE_DIR", str(ROOT / ".ctoa-local")))
PRODUCT_USER_CONFIG_FILE = Path(os.environ.get("CTOA_PRODUCT_USER_CONFIG", str(PRODUCT_STATE_DIR / "user-config.json")))
COMMAND_DICTIONARY_FILE = ROOT / "schemas" / "ctoa-command-dictionary.json"


def _is_production_env() -> bool:
    values = (
        os.getenv("CTOA_ENV", "").strip().lower(),
        os.getenv("ENV", "").strip().lower(),
    )
    return any(value in {"prod", "production"} for value in values)


def _is_windows_host() -> bool:
    return os.name == "nt"
def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _read_orchestrator_loop_pid() -> int | None:
    pid_file = ROOT / "runtime" / "orchestrator-loop.pid"
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _windows_orchestrator_state() -> str:
    pid = _read_orchestrator_loop_pid()
    if not pid:
        return "inactive"

    try:
        probe = _run_argv(["tasklist", "/FI", f"PID eq {pid}"], timeout=4)
    except (OSError, process_safety.ExecutableUnavailableError, process_safety.ProcessExecutionError):
        return "active"

    output = f"{probe['stdout']}\n{probe['stderr']}"
    return "active" if str(pid) in output else "stale"


def _service_is_active(unit: str) -> str:
    if _command_exists("systemctl"):
        res = _run(f"systemctl is-active {unit}", timeout=5)
        return res["stdout"].strip() or res["stderr"].strip() or "unknown"

    if is_windows_host() and "ctoa-agents-orchestrator" in unit:
        state = _windows_orchestrator_state()
        if unit.endswith(".timer"):
            return "manual" if state == "active" else "inactive"
        return state

    return "unsupported"


def _disk_probe() -> dict:
    if _command_exists("df"):
        return _run("df -h /", timeout=10)

    try:
        usage = shutil.disk_usage(ROOT)
        payload = {
            "path": _public_artifact_path(ROOT, fallback="."),
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round((usage.total - usage.free) / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
        }
        return {
            "code": 0,
            "stdout": json.dumps(payload, ensure_ascii=True),
            "stderr": "",
        }
    except Exception as exc:
        return {"code": 1, "stdout": "", "stderr": str(exc)[:200]}


def _lab_tasks_probe() -> dict:
    task_file = ROOT / "labs" / "tasks" / "intel-projects.yaml"
    if not task_file.exists():
        return {"code": 0, "stdout": "LAB_TASKS_MISSING", "stderr": ""}

    try:
        text = task_file.read_text(encoding="utf-8")
        rough_count = text.count("- id:")
        return {
            "code": 0,
            "stdout": f"LAB_TASKS_PRESENT rough_count={rough_count}",
            "stderr": "",
        }
    except Exception as exc:
        return {"code": 1, "stdout": "", "stderr": str(exc)[:200]}



def _require_http_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http:// or https:// and include a host")
    return url


def _require_local_runtime_api_base_url(url: str, label: str) -> str:
    value = _require_http_url(url).strip().rstrip("/")
    parsed = urlparse(value)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{label} URL port is invalid") from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"{label} URL must not include credentials, query, or fragment")
    if "\\" in parsed.path:
        raise ValueError(f"{label} URL path must not include backslashes")
    path_parts = [unquote(part) for part in parsed.path.split("/")]
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError(f"{label} URL path must not contain traversal")

    host = (parsed.hostname or "").strip().lower().rstrip(".")
    allowed_hosts = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
    if host not in allowed_hosts:
        raise ValueError(f"{label} URL must target a local runtime API host")
    return value


def _require_local_runtime_proxy_path(path: str, label: str) -> str:
    raw_value = str(path or "").strip()
    raw_parsed = urlparse(raw_value)
    if raw_parsed.scheme or raw_parsed.netloc:
        raise ValueError(f"{label} path must be a relative API path")
    value = raw_value
    if not value.startswith("/"):
        value = f"/{value}"
    parsed = urlparse(value)
    if parsed.query or parsed.fragment:
        raise ValueError(f"{label} path must not include query or fragment")
    if "\\" in parsed.path:
        raise ValueError(f"{label} path must not include backslashes")
    path_parts = [unquote(part) for part in parsed.path.split("/")]
    if any(part in {".", ".."} for part in path_parts):
        raise ValueError(f"{label} path must not contain traversal")
    if any(not part for part in path_parts[1:]):
        raise ValueError(f"{label} path must not contain empty segments")
    if any("/" in part or "\\" in part for part in path_parts):
        raise ValueError(f"{label} path must not contain encoded separators")
    if parsed.path != "/api" and not parsed.path.startswith("/api/"):
        raise ValueError(f"{label} path must stay under /api")
    return parsed.path


def _private_intel_targets_allowed() -> bool:
    return os.getenv("CTOA_ALLOW_PRIVATE_INTEL_TARGETS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _is_private_or_local_intel_host(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return True
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return True
    if "." not in host:
        return True

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False

    return not address.is_global


def _safe_proxy_error(exc: BaseException | str) -> str:
    return _redact_audit_text(str(exc), max_length=400)


def _intel_api_health_probe() -> dict:
    url = "http://127.0.0.1:8890/health"
    if _is_windows_host() and os.getenv("CTOA_INTEL_API_EXPECTED", "false").lower() not in {"1", "true", "yes", "on"}:
        payload = {"ok": False, "url": url, "state": "not_configured_local"}
        return {"code": 0, "stdout": json.dumps(payload, ensure_ascii=True), "stderr": ""}

    payload: dict[str, Any] = {"ok": False, "url": url}
    try:
        safe_url = _require_http_url(url)
        # _require_http_url enforces http/https with host before this network call.
        with urlopen(safe_url, timeout=5) as response:  # nosec B310
            body = response.read().decode("utf-8")
            payload["status"] = int(getattr(response, "status", 200))
            try:
                payload["body"] = json.loads(body)
            except Exception:
                payload["body_raw"] = body[:800]
            payload["ok"] = True
    except HTTPError as exc:
        payload["error"] = f"http_{exc.code}"
    except URLError as exc:
        payload["error"] = _safe_proxy_error(exc.reason)
    except Exception as exc:
        payload["error"] = _safe_proxy_error(exc)

    code = 0 if payload.get("ok") else 1
    return {
        "code": code,
        "stdout": json.dumps(payload, ensure_ascii=True),
        "stderr": "" if code == 0 else str(payload.get("error", "probe_failed"))[:200],
    }


def _intel_api_proxy(path: str = "/api/intel/status", timeout: int = 5) -> dict[str, Any]:
    try:
        suffix = _require_local_runtime_proxy_path(path, "Intel API proxy")
    except ValueError as exc:
        return {
            "ok": False,
            "url": "[invalid-local-runtime-api]",
            "path": "[invalid-local-runtime-path]",
            "error": str(exc),
        }
    raw_base_url = os.getenv("CTOA_INTEL_API_BASE_URL", "http://127.0.0.1:8890")
    try:
        base_url = _require_local_runtime_api_base_url(raw_base_url, "Intel API base")
    except ValueError as exc:
        return {
            "ok": False,
            "url": "[invalid-local-runtime-api]",
            "path": suffix,
            "error": str(exc),
        }
    url = f"{base_url}{suffix}"

    if _is_windows_host() and os.getenv("CTOA_INTEL_API_EXPECTED", "false").lower() not in {"1", "true", "yes", "on"}:
        return {
            "ok": False,
            "url": url,
            "path": suffix,
            "state": "not_configured_local",
        }

    payload: dict[str, Any] = {
        "ok": False,
        "url": url,
        "path": suffix,
    }

    try:
        # _require_local_runtime_api_base_url keeps proxy requests on local APIs.
        with urlopen(url, timeout=timeout) as response:  # nosec B310
            body = response.read().decode("utf-8")
            payload["status"] = int(getattr(response, "status", 200))
            try:
                payload["body"] = json.loads(body)
            except Exception:
                payload["body_raw"] = body[:800]
            payload["ok"] = True
    except HTTPError as exc:
        payload["status"] = int(exc.code)
        payload["error"] = f"http_{exc.code}"
    except URLError as exc:
        payload["error"] = _safe_proxy_error(exc.reason)
    except Exception as exc:
        payload["error"] = _safe_proxy_error(exc)

    return payload


def _ctoa_api_proxy(path: str = "/api/status", timeout: int = 5) -> dict[str, Any]:
    try:
        suffix = _require_local_runtime_proxy_path(path, "CTOA API proxy")
    except ValueError as exc:
        return {
            "ok": False,
            "url": "[invalid-local-runtime-api]",
            "path": "[invalid-local-runtime-path]",
            "error": str(exc),
        }
    raw_base_url = os.getenv("CTOA_API_BASE_URL", "http://127.0.0.1:8001")
    try:
        base_url = _require_local_runtime_api_base_url(raw_base_url, "CTOA API base")
    except ValueError as exc:
        return {
            "ok": False,
            "url": "[invalid-local-runtime-api]",
            "path": suffix,
            "error": str(exc),
        }
    url = f"{base_url}{suffix}"

    payload: dict[str, Any] = {
        "ok": False,
        "url": url,
        "path": suffix,
    }

    try:
        # _require_local_runtime_api_base_url keeps proxy requests on local APIs.
        with urlopen(url, timeout=timeout) as response:  # nosec B310
            body = response.read().decode("utf-8")
            payload["status"] = int(getattr(response, "status", 200))
            try:
                payload["body"] = json.loads(body)
            except Exception:
                payload["body_raw"] = body[:800]
            payload["ok"] = True
    except HTTPError as exc:
        payload["status"] = int(exc.code)
        payload["error"] = f"http_{exc.code}"
    except URLError as exc:
        payload["error"] = _safe_proxy_error(exc.reason)
    except Exception as exc:
        payload["error"] = _safe_proxy_error(exc)

    return payload


def _load_json_file(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        return {}
    try:
        with path.open("rb") as handle:
            raw = handle.read(LOCAL_JSON_MAX_BYTES + 1)
    except OSError:
        return {}
    if len(raw) > LOCAL_JSON_MAX_BYTES:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_production_env() -> bool:
    return is_production_env()


def _read_generated_manifest_json(path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        return None
    try:
        with path.open("rb") as handle:
            raw = handle.read(GENERATED_MANIFEST_JSON_MAX_BYTES + 1)
    except OSError:
        return None
    if len(raw) > GENERATED_MANIFEST_JSON_MAX_BYTES:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_local_state_temp_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")


def _remove_local_state_temp(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _atomic_write_local_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _atomic_local_state_temp_path(path)
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        _remove_local_state_temp(tmp)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _atomic_local_state_temp_path(path)
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        _remove_local_state_temp(tmp)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _atomic_local_state_temp_path(path)
    try:
        with tmp.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)
    finally:
        _remove_local_state_temp(tmp)


def _read_local_json_bounded(path: Path, max_bytes: int) -> Any | None:
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError:
        return None
    if len(raw) > max_bytes:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _read_text_bounded(path: Path, max_bytes: int) -> tuple[str, bool]:
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    text = raw.decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n... [truncated]"
    return text, truncated


def _read_tail_text_bounded(path: Path, lines: int, max_bytes: int = LOG_TAIL_MAX_BYTES) -> tuple[str, bool]:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        start = max(0, size - max_bytes)
        handle.seek(start)
        raw = handle.read(max_bytes)

    tail = "\n".join(raw.decode("utf-8", errors="replace").splitlines()[-lines:])
    if tail:
        tail += "\n"
    if start > 0:
        tail = f"... [truncated to last {max_bytes} bytes]\n{tail}"
    return tail, start > 0


def _read_json_bounded(path: Path, max_bytes: int) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError:
        return {"parse_error": "read_failed"}
    if len(raw) > max_bytes:
        return {"parse_error": "report_json_too_large", "max_bytes": max_bytes}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"parse_error": "invalid_json"}
    return payload if isinstance(payload, dict) else {"parse_error": "invalid_json_object"}


def _normalize_package_tier(value: str) -> str:
    tier = str(value or "").strip().lower()
    if tier in {"core", "pro", "studio"}:
        return tier
    return "studio"


def _is_windows_host() -> bool:
    return is_windows_host()

app = FastAPI(title="CTOA Mobile Console", version="1.0.0")

_PROM_METRICS_ENABLED = Counter is not None and Histogram is not None


def _prom_get_or_create_counter(name: str, documentation: str, labels: list[str]):
    if not _PROM_METRICS_ENABLED:
        return None
    try:
        counter_ctor = Counter
        if counter_ctor is None:
            return None
        return counter_ctor(name, documentation, labels)
    except ValueError:
        registry_map = getattr(REGISTRY, "_names_to_collectors", {}) if REGISTRY is not None else {}
        return registry_map.get(name) or registry_map.get(name.removesuffix("_total"))


def _prom_get_or_create_histogram(name: str, documentation: str, labels: list[str]):
    if not _PROM_METRICS_ENABLED:
        return None
    try:
        histogram_ctor = Histogram
        if histogram_ctor is None:
            return None
        return histogram_ctor(name, documentation, labels)
    except ValueError:
        registry_map = getattr(REGISTRY, "_names_to_collectors", {}) if REGISTRY is not None else {}
        return registry_map.get(name)


HTTP_REQUEST_TOTAL = _prom_get_or_create_counter(
    "ctoa_http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
HTTP_REQUEST_LATENCY_SECONDS = _prom_get_or_create_histogram(
    "ctoa_http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)
REDIS_URL = os.getenv("CTOA_REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_QUEUE = os.getenv("CTOA_REDIS_QUEUE", "ctoa:jobs")
REDIS_RESULTS = os.getenv("CTOA_REDIS_RESULTS", "ctoa:jobs:results")

cors_origins = [o.strip() for o in os.getenv("CTOA_CORS_ORIGINS", "*").split(",") if o.strip()]
if is_production_env() and (not cors_origins or "*" in cors_origins):
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


@app.middleware("http")
async def enforce_mobile_console_capability(request: Request, call_next):
    path = request.url.path
    gated = (
        path == "/console"
        or path == "/live-dashboard"
        or path.startswith("/api/")
        or path.startswith("/static/")
    )
    if gated and not mobile_console_enabled(PRODUCT_MANIFEST_FILE, PRODUCT_USER_CONFIG_FILE):
        detail = "mobile_console capability requires Pro or Studio package"
        if path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"ok": False, "detail": detail})
        return PlainTextResponse(detail, status_code=403)
    return await call_next(request)

@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    if not _PROM_METRICS_ENABLED:
        return await call_next(request)

    started = time.perf_counter()
    path = request.url.path
    status = "500"
    try:
        response = await call_next(request)
        status = str(getattr(response, "status_code", 500))
        return response
    finally:
        elapsed = time.perf_counter() - started
        if HTTP_REQUEST_TOTAL is not None:
            HTTP_REQUEST_TOTAL.labels(request.method, path, status).inc()
        if HTTP_REQUEST_LATENCY_SECONDS is not None:
            HTTP_REQUEST_LATENCY_SECONDS.labels(request.method, path).observe(elapsed)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(SITE_ASSETS_DIR)), name="site-assets")


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
    confirm: bool = False
    reason: str = Field(default="", max_length=500)


class GuardedActionRequest(BaseModel):
    confirm: bool = False
    reason: str = Field(default="", max_length=500)


class QueueJobRequest(BaseModel):
    action: str = Field(default="orchestrator.tick", min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    payload: dict[str, Any] = Field(default_factory=dict)
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
    role: str = Field(default="operator", pattern="^(member|operator|owner)$")


class SelfRegisterPayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    registration_code: str = Field(default="", max_length=128)


class ChangePasswordPayload(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class ChangeRolePayload(BaseModel):
    role: str = Field(pattern="^(member|operator|owner)$")


ROLE_WEIGHT = {"member": 0, "operator": 1, "owner": 2}
SESSION_TTL_SECONDS = int(os.getenv("CTOA_SESSION_TTL_SECONDS", "1800"))
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_SESSIONS_LOCK = Lock()
_ADMIN_SETTINGS_LOCK = Lock()
_IDEA_PARKING_LOCK = Lock()
_USER_PROFILES_LOCK = Lock()
_USER_PROFILES_TABLE_READY = False
_ACCOUNTS_TABLE_READY = False

REASON_CODE_TAXONOMY: dict[str, str] = {
    "ARTIFACTS_READY": "Generated artifacts are available and publish gate can proceed.",
    "MANIFEST_PENDING": "Manifest is not yet available after trigger.",
    "ARTIFACTS_PENDING": "Manifest exists but no generated artifacts are visible yet.",
    "GENERATION_FAILED": "Manifest reports failed generation items.",
}


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
        payload = _read_local_json_bounded(ADMIN_SETTINGS_FILE, ADMIN_SETTINGS_MAX_BYTES)
        if not isinstance(payload, dict):
            return _default_admin_settings()
        return _normalize_admin_settings(payload)


def _write_admin_settings(payload: dict[str, Any]) -> dict[str, Any]:
    data = _normalize_admin_settings(payload)
    with _ADMIN_SETTINGS_LOCK:
        _atomic_write_local_json(ADMIN_SETTINGS_FILE, data)
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
        payload = _read_local_json_bounded(IDEA_PARKING_FILE, IDEA_PARKING_MAX_BYTES)

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
        _atomic_write_local_json(IDEA_PARKING_FILE, normalized)
    return normalized


_ADMIN_SETTINGS_SERVICE = AdminSettingsService(
    read_settings=_read_admin_settings,
    write_settings=_write_admin_settings,
)
_IDEAS_SERVICE = IdeasService(
    read_items=_read_idea_parking,
    write_items=_write_idea_parking,
    normalize_item=_normalize_idea_item,
)

def _mobile_token() -> str:
    # Legacy static token is optional when session auth is used.
    return os.getenv("CTOA_MOBILE_TOKEN", "").strip()


def _full_access() -> bool:
    return os.getenv("CTOA_MOBILE_FULL_ACCESS", "false").lower() == "true"


def _self_register_enabled() -> bool:
    return os.getenv("CTOA_SELF_REGISTER_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _self_register_code() -> str:
    return os.getenv("CTOA_SELF_REGISTER_CODE", "").strip()


def _session_cookie_secure() -> bool:
    override = os.getenv("CTOA_SESSION_COOKIE_SECURE", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    return _is_production_env()


def _safe_command_specs() -> dict[str, dict[str, Any]]:
    vps_root = "/opt/ctoa"
    return {
        "systemctl status ctoa-runner.timer --no-pager -l": {
            "args": ["systemctl", "status", "ctoa-runner.timer", "--no-pager", "-l"],
        },
        "systemctl status ctoa-report.timer --no-pager -l": {
            "args": ["systemctl", "status", "ctoa-report.timer", "--no-pager", "-l"],
        },
        "systemctl status ctoa-health-live.service --no-pager -l": {
            "args": ["systemctl", "status", "ctoa-health-live.service", "--no-pager", "-l"],
        },
        "systemctl status ctoa-intel-news-api.service --no-pager -l": {
            "args": ["systemctl", "status", "ctoa-intel-news-api.service", "--no-pager", "-l"],
        },
        "systemctl status ctoa-intel-news-watcher.timer --no-pager -l": {
            "args": ["systemctl", "status", "ctoa-intel-news-watcher.timer", "--no-pager", "-l"],
        },
        "tail -n 80 /opt/ctoa/logs/runner.log": {
            "args": ["tail", "-n", "80", "/opt/ctoa/logs/runner.log"],
        },
        "tail -n 80 /opt/ctoa/logs/health-live.log": {
            "args": ["tail", "-n", "80", "/opt/ctoa/logs/health-live.log"],
        },
        "tail -n 80 /opt/ctoa/logs/intel-news-api.log": {
            "args": ["tail", "-n", "80", "/opt/ctoa/logs/intel-news-api.log"],
        },
        "tail -n 80 /opt/ctoa/logs/intel-news-watcher.log": {
            "args": ["tail", "-n", "80", "/opt/ctoa/logs/intel-news-watcher.log"],
        },
        "cd /opt/ctoa; CTOA_BACKLOG_FILE=/opt/ctoa/workflows/backlog-sprint-004.yaml python3 runner/runner.py report": {
            "args": ["python3", "runner/runner.py", "report"],
            "cwd": vps_root,
            "env": {"CTOA_BACKLOG_FILE": "/opt/ctoa/workflows/backlog-sprint-004.yaml"},
        },
        "cd /opt/ctoa; python3 runner/drift_checker.py": {
            "args": ["python3", "runner/drift_checker.py"],
            "cwd": vps_root,
        },
        "df -h": {
            "args": ["df", "-h"],
        },
    }


def _allowed_commands() -> List[str]:
    return list(_safe_command_specs().keys())


def _normalize_user(username: str) -> str:
    return username.strip().lower()


def _admin_credentials() -> dict[str, dict[str, str]]:
    owner_user = _normalize_user(os.getenv("CTOA_OWNER_USER", "CTO"))
    operator_user = _normalize_user(os.getenv("CTOA_OPERATOR_USER", "ctoa-bot"))
    owner_pass = os.getenv("CTOA_OWNER_PASSWORD", "").strip()
    operator_pass = os.getenv("CTOA_OPERATOR_PASSWORD", "").strip()

    creds: dict[str, dict[str, str]] = {}
    if owner_pass:
        creds[owner_user] = {"role": "owner", "password": owner_pass}
    if operator_pass:
        creds[operator_user] = {"role": "operator", "password": operator_pass}
    return creds


def _validate_security_config() -> None:
    if not is_production_env():
        return

    required_env = [
        "CTOA_OWNER_PASSWORD",
        "CTOA_OPERATOR_PASSWORD",
        "CTOA_MOBILE_TOKEN",
        "DB_PASSWORD",
    ]
    missing = [name for name in required_env if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError(
            "Missing required secrets in production: " + ", ".join(missing)
        )

    if _full_access():
        raise RuntimeError(
            "Refusing to start in production with CTOA_MOBILE_FULL_ACCESS=true"
        )

    if _self_register_enabled() and not _self_register_code():
        raise RuntimeError(
            "CTOA_SELF_REGISTER_CODE must be set when self registration is enabled in production"
        )


_validate_security_config()


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        return ""
    auth = authorization.strip()
    if not auth.lower().startswith("bearer "):
        return ""
    return auth[7:].strip()


def _create_session(username: str, role: str) -> tuple[str, int, str]:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    with _SESSIONS_LOCK:
        _SESSIONS[token] = {
            "username": username,
            "role": role,
            "expires_at": expires_at,
            "csrf_token": csrf_token,
        }
    return token, expires_at, csrf_token


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


def _delete_sessions_for_user(username: str) -> int:
    target = _normalize_user(username)
    removed = 0
    with _SESSIONS_LOCK:
        for token, session in list(_SESSIONS.items()):
            session_user = _normalize_user(str(session.get("username", "")))
            if session_user == target:
                _SESSIONS.pop(token, None)
                removed += 1
    return removed


def _try_auth_context(
    x_ctoa_token: Optional[str] = None,
    authorization: Optional[str] = None,
    x_ctoa_session: Optional[str] = None,
    ctoa_session: Optional[str] = None,
) -> dict[str, Any] | None:
    # Backward-compatible owner auth using static token.
    expected = _mobile_token()
    if expected and x_ctoa_token and hmac.compare_digest(x_ctoa_token, expected):
        legacy_context = {
            "username": os.getenv("CTOA_OWNER_USER", "CTO"),
            "role": "owner",
            "auth_mode": "legacy_token",
        }
        legacy_context["session_" + "token"] = None
        return legacy_context

    bearer_token = _extract_bearer(authorization)
    session_token = x_ctoa_session or bearer_token or ctoa_session
    session = _get_session(session_token)
    if session:
        auth_transport = "cookie" if ctoa_session and not (x_ctoa_session or bearer_token) else "header"
        return {
            "username": session["username"],
            "role": session["role"],
            "auth_mode": "session",
            "auth_transport": auth_transport,
            "session_token": session_token,
            "csrf_token": session.get("csrf_token", ""),
        }

    return None


def _token_valid(
    x_ctoa_token: Optional[str],
    authorization: Optional[str],
    x_ctoa_session: Optional[str],
    ctoa_session: Optional[str],
) -> bool:
    return _try_auth_context(
        x_ctoa_token=x_ctoa_token,
        authorization=authorization,
        x_ctoa_session=x_ctoa_session,
        ctoa_session=ctoa_session,
    ) is not None


def _csrf_required(request: Request, ctx: dict[str, Any]) -> bool:
    return (
        request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
        and ctx.get("auth_mode") == "session"
        and ctx.get("auth_transport") == "cookie"
    )


def _verify_csrf(request: Request, ctx: dict[str, Any], x_csrf_token: Optional[str]) -> None:
    if not _csrf_required(request, ctx):
        return
    expected = str(ctx.get("csrf_token") or "")
    provided = (x_csrf_token or "").strip()
    if not expected or not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")


def require_authenticated(
    request: Request,
    x_ctoa_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_ctoa_session: Optional[str] = Header(default=None),
    x_csrf_token: Optional[str] = Header(default=None),
    ctoa_session: Optional[str] = Cookie(default=None),
) -> dict[str, Any]:
    ctx = _try_auth_context(
        x_ctoa_token=x_ctoa_token,
        authorization=authorization,
        x_ctoa_session=x_ctoa_session,
        ctoa_session=ctoa_session,
    )
    if not ctx:
        raise HTTPException(status_code=401, detail="Unauthorized")
    _verify_csrf(request, ctx, x_csrf_token)
    return ctx


def require_operator(ctx: dict[str, Any] = Depends(require_authenticated)) -> dict[str, Any]:
    role = str(ctx.get("role", ""))
    if ROLE_WEIGHT.get(role, -1) < ROLE_WEIGHT["operator"]:
        raise HTTPException(status_code=403, detail="Operator role required")
    return ctx


def require_owner(ctx: dict[str, Any] = Depends(require_operator)) -> dict[str, Any]:
    role = str(ctx.get("role", "operator"))
    if ROLE_WEIGHT.get(role, 0) < ROLE_WEIGHT["owner"]:
        raise HTTPException(status_code=403, detail="Owner role required")
    return ctx


def _slice_command_output(value: str) -> str:
    return (value or "")[-20000:]


def _redact_audit_text(value: str, max_length: int = 2000) -> str:
    redacted = str(value or "")
    redacted = re.sub(r"\b(Bearer\s+)[A-Za-z0-9._~+/=-]{12,}", r"\1[redacted]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"\b(Basic\s+)[A-Za-z0-9+/=]{12,}", r"\1[redacted]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(
        r"\b(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|glpat-[A-Za-z0-9_-]{12,})\b",
        "[redacted]",
        redacted,
    )
    redacted = re.sub(
        r"\b((?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|token|secret|password|passwd|pwd|pgpassword)\s*[:=]\s*)([^&\s\"'`,;{}\[\]]{4,})",
        r"\1[redacted]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"(\s--(?:api-key|access-token|auth-token|refresh-token|token|secret|password|passwd|pwd)\s+)([^\s\"'`,;}\]]{4,})",
        r"\1[redacted]",
        redacted,
        flags=re.IGNORECASE,
    ).strip()
    return redacted[:max_length]


def _redact_command_output(value: str) -> str:
    return _redact_audit_text(_slice_command_output(value), max_length=20000)


def _run(cmd: str, timeout: int = 20, cwd: Optional[str] = None) -> dict:
    args = shlex.split(cmd, posix=not _is_windows_host())
    if not args:
        return {"code": 1, "stdout": "", "stderr": "Empty command"}
    return _run_argv(args, timeout=timeout, cwd=cwd, redact_output=True)


def _run_argv(
    args: list[str],
    timeout: int = 20,
    cwd: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    redact_output: bool = False,
) -> dict:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    executable = process_safety.resolve_executable(args[0])
    proc = process_safety.run_trusted(
        [executable, *args[1:]],
        text=True,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
        env=merged_env,
    )
    return {
        "code": proc.returncode,
        "stdout": _redact_command_output(proc.stdout) if redact_output else _slice_command_output(proc.stdout),
        "stderr": _redact_command_output(proc.stderr) if redact_output else _slice_command_output(proc.stderr),
    }


def _run_safe_command(cmd: str, timeout: int = 20) -> dict:
    spec = _safe_command_specs().get(cmd)
    if not spec:
        raise HTTPException(
            status_code=403,
            detail="Command not allowed. Use one of /api/presets.",
        )
    return _run_argv(
        list(spec["args"]),
        timeout=timeout,
        cwd=spec.get("cwd"),
        env=spec.get("env"),
        redact_output=True,
    )


def _trigger_orchestrator_start(timeout: int = 8) -> dict:
    if _command_exists("systemctl"):
        return _run("systemctl start --no-block ctoa-agents-orchestrator.service", timeout=timeout)

    if _is_windows_host():
        script_path = ROOT / "scripts" / "ops" / "orchestrator-loop.ps1"
        if not script_path.exists():
            return {"code": 1, "stdout": "", "stderr": f"Missing script: {script_path}"}

        return _run_argv(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-Action",
                "start",
            ],
            timeout=max(timeout, 15),
            cwd=str(ROOT),
            redact_output=True,
        )

    return {"code": 1, "stdout": "", "stderr": "No orchestrator trigger available on this host"}


def _audit_actor_fields(actor: Optional[dict[str, Any]]) -> dict[str, str]:
    if not actor:
        return {
            "actor": "anonymous",
            "actor_role": "anonymous",
            "auth_mode": "unknown",
            "auth_transport": "unknown",
        }
    return {
        "actor": _redact_audit_text(str(actor.get("username") or "anonymous"), max_length=128),
        "actor_role": _redact_audit_text(str(actor.get("role") or "anonymous"), max_length=64),
        "auth_mode": _redact_audit_text(str(actor.get("auth_mode") or "unknown"), max_length=64),
        "auth_transport": _redact_audit_text(str(actor.get("auth_transport") or "unknown"), max_length=64),
    }


def _audit(request: Request, command: str, code: int, actor: Optional[dict[str, Any]] = None) -> None:
    entry = {
        "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "ip": request.client.host if request.client else "unknown",
        "path": request.url.path,
        "command": _redact_audit_text(command),
        "code": code,
        **_audit_actor_fields(actor),
    }
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError:
        # Best-effort auditing: auth and API flows must remain available even
        # when host/container log paths are not writable in test or CI envs.
        return


def _require_guarded_action_confirmation(
    req: GuardedActionRequest | IntelMissionRequest | None,
    *,
    action_id: str,
    request: Request,
    actor: dict[str, Any],
) -> str:
    reason = _redact_audit_text(str(getattr(req, "reason", "") or "").strip(), max_length=500)
    if not bool(getattr(req, "confirm", False)) or not reason:
        _audit(request, f"{action_id}:denied:missing_confirmation", 403, actor=actor)
        raise HTTPException(
            status_code=403,
            detail=f"{action_id} requires explicit confirmation and audit reason",
        )
    return reason


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(SITE_INDEX_HTML), headers={"Cache-Control": "no-store"})


@app.get("/console")
def legacy_console() -> FileResponse:
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-store", "X-CTOAi-UI-Status": "legacy; canonical=control-center"},
    )


@app.get("/style.css")
def site_style() -> FileResponse:
    return FileResponse(str(SITE_DIR / "style.css"))


@app.get("/script.js")
def site_script() -> FileResponse:
    return FileResponse(str(SITE_DIR / "script.js"))


@app.get("/live-dashboard")
def live_dashboard() -> FileResponse:
    """Serve the login-based live dashboard (username/password auth)."""
    return FileResponse(
        str(LIVE_DASHBOARD_HTML),
        headers={"Cache-Control": "no-store", "X-CTOAi-UI-Status": "legacy; canonical=control-center"},
    )


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    if not _PROM_METRICS_ENABLED:
        raise HTTPException(status_code=503, detail="prometheus metrics disabled")
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
@app.get("/api/health")
def health(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    return {
        "ok": True,
        "full_access": False,
        "command_mode": "presets",
        "role": ctx["role"],
        "username": ctx["username"],
    }


@app.post("/api/auth/login")
def auth_login(req: AuthLoginRequest, request: Request, response: Response) -> dict:
    username = _normalize_user(req.username)

    # 1. Try env-based credentials first for backward compatibility.
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
        _audit(request, f"auth_login:{username}", 401, actor={"username": username, "role": "unknown", "auth_mode": "login"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token, expires_at, csrf_token = _create_session(username=username, role=matched_role)
    response.set_cookie(
        key="ctoa_session",
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_is_production_env(),
        path="/",
    )

    # Best-effort profile bootstrap so each authenticated user has a DB profile.
    try:
        _load_live_dashboard_profile(username=username, role=matched_role)
    except Exception as exc:
        print(f"[mobile-console] profile bootstrap failed for {username}: {exc}")

    _audit(request, f"auth_login:{username}", 0, actor={"username": username, "role": matched_role, "auth_mode": "login"})
    bearer_label = "bearer"
    return {
        "ok": True,
        "token": token,
        "token_type": bearer_label,
        "expires_in": SESSION_TTL_SECONDS,
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        "csrf_token": csrf_token,
        "role": matched_role,
        "username": username,
    }


@app.get("/api/auth/me")
def auth_me(ctx: dict[str, Any] = Depends(require_authenticated)) -> dict:
    return {
        "ok": True,
        "username": ctx["username"],
        "role": ctx["role"],
        "auth_mode": ctx["auth_mode"],
        "csrf_token": ctx.get("csrf_token", ""),
    }


@app.post("/api/auth/logout")
def auth_logout(response: Response, ctx: dict[str, Any] = Depends(require_authenticated)) -> dict:
    token = str(ctx.get("session_token") or "")
    if token:
        _delete_session(token)
    response.delete_cookie(key="ctoa_session", path="/")
    return {"ok": True}

@app.post("/api/auth/register")
def auth_register(req: SelfRegisterPayload, request: Request) -> dict:
    if not _self_register_enabled():
        raise HTTPException(status_code=403, detail="Self registration is disabled")

    expected_code = _self_register_code()
    if not expected_code:
        raise HTTPException(status_code=503, detail="Self registration code is not configured")
    provided_code = req.registration_code.strip()
    if not hmac.compare_digest(provided_code, expected_code):
        _audit(request, f"self_register_code_invalid:{_normalize_user(req.username)}", 403)
        raise HTTPException(status_code=403, detail="Invalid registration code")

    username = _normalize_user(req.username)

    # Prevent overwriting env-based accounts.
    env_creds = _admin_credentials()
    if username in env_creds:
        raise HTTPException(status_code=409, detail="Username reserved by system configuration")

    try:
        result = _db_create_account(
            username=username,
            password=req.password,
            role="member",
            created_by="self-register",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _audit(request, f"self_register:{username}", 0, actor={"username": username, "role": "member", "auth_mode": "self_register"})
    return {"ok": True, "account": result}

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

    _audit(request, f"account_register:{username}:role={req.role}", 0, actor=ctx)
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
    db_accounts_with_source = [{**a, "source": "db"} for a in db_accounts]
    for entry in env_entries:
        entry["source"] = "env"

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

    revoked_sessions = _delete_sessions_for_user(target)
    _audit(request, f"account_password_change:{target}:by={caller}", 0, actor=ctx)
    return {"ok": True, "username": target, "revoked_sessions": revoked_sessions}


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

    revoked_sessions = _delete_sessions_for_user(target)
    _audit(request, f"account_role_change:{target}:role={req.role}:by={caller}", 0, actor=ctx)
    return {"ok": True, "username": target, "role": req.role, "revoked_sessions": revoked_sessions}


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

    revoked_sessions = _delete_sessions_for_user(target)
    _audit(request, f"account_deactivate:{target}:by={caller}", 0, actor=ctx)
    return {"ok": True, "username": target, "active": False, "revoked_sessions": revoked_sessions}


@app.get("/api/auth/auto-check")
def auth_auto_check(
    x_ctoa_token: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_ctoa_session: Optional[str] = Header(default=None),
    ctoa_session: Optional[str] = Cookie(default=None),
) -> dict:
    ctx = _try_auth_context(
        x_ctoa_token=x_ctoa_token,
        authorization=authorization,
        x_ctoa_session=x_ctoa_session,
        ctoa_session=ctoa_session,
    )
    valid = ctx is not None
    payload = {
        "ok": valid,
        "token_present": bool(x_ctoa_token or authorization or x_ctoa_session or ctoa_session),
        "token_valid": valid,
        "full_access": False,
        "command_mode": "presets",
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if ctx:
        payload["username"] = ctx["username"]
        payload["role"] = ctx["role"]
        payload["auth_mode"] = ctx["auth_mode"]
        payload["csrf_token"] = ctx.get("csrf_token", "")
    if valid:
        payload["orchestrator_timer"] = _service_is_active("ctoa-agents-orchestrator.timer")
    else:
        payload["hint"] = "Uzyj loginu /api/auth/login i przeslij Authorization: Bearer <token>"
    return payload


@app.get("/api/presets")
def presets(ctx: dict[str, Any] = Depends(require_operator)) -> dict:
    return {"commands": _allowed_commands(), "role": ctx["role"]}


@app.get("/api/status")
def status(_: dict[str, Any] = Depends(require_operator)) -> dict:
    out = {
        "runner_timer": _service_is_active("ctoa-runner.timer"),
        "report_timer": _service_is_active("ctoa-report.timer"),
        "health_service": _service_is_active("ctoa-health-live.service"),
        "intel_watcher_timer": _service_is_active("ctoa-intel-news-watcher.timer"),
        "intel_api_service": _service_is_active("ctoa-intel-news-api.service"),
    }

    report = _run_argv(
        [_sys.executable, "runner/runner.py", "report"],
        timeout=20,
        cwd=str(ROOT),
        env={"CTOA_BACKLOG_FILE": str(ROOT / "workflows" / "backlog-sprint-004.yaml")},
        redact_output=True,
    )
    intel_api_health = _intel_api_health_probe()
    intel_status_proxy = _intel_api_proxy("/api/intel/status")

    return {
        "services": out,
        "disk": _disk_probe(),
        "report": report,
        "lab": _lab_tasks_probe(),
        "intel_api_health": intel_api_health,
        "intel_status_proxy": intel_status_proxy,
    }


@app.get("/api/intel/status")
def intel_status_proxy(_: dict[str, Any] = Depends(require_operator)) -> dict:
    return _intel_api_proxy("/api/intel/status")


@app.get("/api/intel/state")
def intel_state_proxy(_: dict[str, Any] = Depends(require_operator)) -> dict:
    return _intel_api_proxy("/api/intel/state")


@app.get("/api/intel/diff")
def intel_diff_proxy(_: dict[str, Any] = Depends(require_operator)) -> dict:
    return _intel_api_proxy("/api/intel/diff")


@app.get("/api/admin/settings")
def get_admin_settings(_: dict[str, Any] = Depends(require_operator)) -> dict:
    return {
        "ok": True,
        "settings": _ADMIN_SETTINGS_SERVICE.get(),
        "path": _public_artifact_path(ADMIN_SETTINGS_FILE, fallback=ADMIN_SETTINGS_FILE.name),
    }


@app.put("/api/admin/settings")
def put_admin_settings(
    req: AdminSettingsPayload,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    saved = _ADMIN_SETTINGS_SERVICE.save(req.model_dump())
    _audit(request, f"admin_settings_save:{ctx.get('username','unknown')}", 0, actor=ctx)
    return {
        "ok": True,
        "settings": saved,
        "saved_by": ctx.get("username"),
        "saved_role": ctx.get("role"),
    }


@app.get("/api/ideas")
def get_ideas(_: dict[str, Any] = Depends(require_operator)) -> dict:
    ideas = _IDEAS_SERVICE.list_items()
    return {
        "ok": True,
        "ideas": ideas,
        "count": len(ideas),
        "path": _public_artifact_path(IDEA_PARKING_FILE, fallback=IDEA_PARKING_FILE.name),
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

    idea, saved_count = _IDEAS_SERVICE.add(
        text=text,
        author=str(ctx.get("username", "")),
    )
    if not idea:
        raise HTTPException(status_code=422, detail="Invalid idea payload")
    _audit(request, f"idea_add:{ctx.get('username', 'unknown')}", 0, actor=ctx)
    return {
        "ok": True,
        "idea": idea,
        "count": saved_count,
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

    deleted, remaining_count = _IDEAS_SERVICE.delete(idea_id)
    if deleted <= 0:
        raise HTTPException(status_code=404, detail="Idea not found")
    _audit(request, f"idea_delete:{ctx.get('username', 'unknown')}:{idea_id}", 0, actor=ctx)
    return {
        "ok": True,
        "deleted": deleted,
        "count": remaining_count,
    }


@app.delete("/api/ideas")
def clear_ideas(
    request: Request,
    ctx: dict[str, Any] = Depends(require_operator),
) -> dict:
    remaining_count = _IDEAS_SERVICE.clear()
    _audit(request, f"idea_clear_all:{ctx.get('username', 'unknown')}", 0, actor=ctx)
    return {
        "ok": True,
        "count": remaining_count,
    }


@app.get("/api/logs")
def logs(
    target: str = Query(
        default="runner",
        pattern="^(runner|health|report|intel_api|intel_watcher"
                "|agent_orchestrator|agent_scout|agent_brain|agent_generator"
                "|agent_validator|agent_publisher)$",
    ),
    lines: int = Query(default=120, ge=10, le=500),
    _: dict[str, Any] = Depends(require_operator),
) -> dict:
    if _is_windows_host():
        base_logs = ROOT / "logs"
        mapping = {
            "runner": base_logs / "runner.log",
            "health": base_logs / "health-live.log",
            "report": base_logs / "runner.log",
            "intel_api": base_logs / "intel-news-api.log",
            "intel_watcher": base_logs / "intel-news-watcher.log",
            "agent_orchestrator": base_logs / "agents-orchestrator.log",
            "agent_scout": base_logs / "agents-orchestrator.log",
            "agent_brain": base_logs / "agents-orchestrator.log",
            "agent_generator": base_logs / "agents-orchestrator.log",
            "agent_validator": base_logs / "agents-orchestrator.log",
            "agent_publisher": base_logs / "agents-orchestrator.log",
        }
    else:
        mapping = {
            "runner": Path("/opt/ctoa/logs/runner.log"),
            "health": Path("/opt/ctoa/logs/health-live.log"),
            "report": Path("/opt/ctoa/logs/runner.log"),
            "intel_api": Path("/opt/ctoa/logs/intel-news-api.log"),
            "intel_watcher": Path("/opt/ctoa/logs/intel-news-watcher.log"),
            "agent_orchestrator": Path("/opt/ctoa/logs/agents-orchestrator.log"),
            "agent_scout": Path("/opt/ctoa/logs/agents-orchestrator.log"),
            "agent_brain": Path("/opt/ctoa/logs/agents-orchestrator.log"),
            "agent_generator": Path("/opt/ctoa/logs/agents-orchestrator.log"),
            "agent_validator": Path("/opt/ctoa/logs/agents-orchestrator.log"),
            "agent_publisher": Path("/opt/ctoa/logs/agents-orchestrator.log"),
        }

    path = mapping[target]

    if path.is_symlink():
        return {"code": 0, "stdout": "(log unavailable)", "stderr": ""}

    if _command_exists("tail"):
        tail_result = _run_argv(["tail", "-n", str(lines), str(path)], timeout=10, redact_output=True)
        if int(tail_result.get("code", 1)) != 0:
            return {"code": 0, "stdout": "(log not found)", "stderr": ""}
        return tail_result

    if not path.exists():
        return {"code": 0, "stdout": "(log not found)", "stderr": ""}

    try:
        tail, _truncated = _read_tail_text_bounded(path, lines, LOG_TAIL_MAX_BYTES)
        return {"code": 0, "stdout": _redact_command_output(tail), "stderr": ""}
    except OSError:
        return {"code": 1, "stdout": "", "stderr": "log read failed"}


@app.post("/api/command")
def command(req: CommandRequest, request: Request, ctx: dict[str, Any] = Depends(require_owner)) -> dict:
    cmd = req.command.strip()

    if is_production_env() and _full_access():
        raise HTTPException(
            status_code=403,
            detail="Full shell access is disabled in production.",
        )

    result = _run_safe_command(cmd, timeout=req.timeout)
    _audit(request, cmd, int(result.get("code", -1)), actor=ctx)
    return result

def _validate_url(url: str) -> str:
    """Normalise and basic-validate a game server URL."""
    url = url.strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Invalid URL format. Must start with http:// or https://")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid URL port") from exc
    if parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="URL credentials are not allowed")
    if parsed.query or parsed.fragment:
        raise HTTPException(status_code=422, detail="URL query strings and fragments are not allowed")
    if "\\" in parsed.path:
        raise HTTPException(status_code=422, detail="URL path must not contain backslashes")
    path_parts = [unquote(part) for part in parsed.path.split("/")]
    if any(part in {".", ".."} for part in path_parts):
        raise HTTPException(status_code=422, detail="URL path must not contain traversal")
    hostname = parsed.hostname or ""
    if _is_production_env() and not _private_intel_targets_allowed():
        if _is_private_or_local_intel_host(hostname):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Private or local intel target URLs are disabled in production. "
                    "Set CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true only for a trusted private target."
                ),
            )
    return url


def _db_exec(sql: str, params: tuple = (), timeout: int = 15) -> dict:
    """Run SQL via psycopg2 first, then psql/docker fallbacks."""
    psycopg2_error = ""
    if psycopg2 is not None:
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME", "ctoa"),
                user=os.getenv("DB_USER", "ctoa"),
                password=os.getenv("DB_PASSWORD", ""),
                host=os.getenv("DB_HOST", "127.0.0.1"),
                port=os.getenv("DB_PORT", "5432"),
                connect_timeout=timeout,
            )
            conn.autocommit = True
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    if cur.description:
                        rows = cur.fetchall()
                        lines = ["|".join("" if v is None else str(v) for v in row) for row in rows]
                        stdout = "\n".join(lines)
                    else:
                        stdout = ""
                return {"code": 0, "stdout": stdout, "stderr": ""}
            finally:
                conn.close()
        except Exception as exc:
            psycopg2_error = f"psycopg2 error: {exc}"
    else:
        psycopg2_error = "psycopg2 unavailable"

    def quote(v: object) -> str:
        if v is None:
            return "NULL"
        return "'" + str(v).replace("'", "''") + "'"

    filled = sql
    for p in params:
        filled = filled.replace("%s", quote(p), 1)

    db_password = os.getenv("DB_PASSWORD", "")
    db_env = {"PGPASSWORD": db_password} if db_password else None
    if _command_exists("psql"):
        return _run_argv(
            [
                "psql",
                "-h",
                os.getenv("DB_HOST", "127.0.0.1"),
                "-p",
                os.getenv("DB_PORT", "5432"),
                "-U",
                os.getenv("DB_USER", "ctoa"),
                "-d",
                os.getenv("DB_NAME", "ctoa"),
                "-t",
                "-A",
                "-c",
                filled,
            ],
            timeout=timeout,
            env=db_env,
        )

    if _command_exists("docker"):
        args = ["docker", "exec", "-i"]
        if db_password:
            args.extend(["-e", "PGPASSWORD"])

        args.extend(
            [
                "ctoa-db",
                "psql",
                "-U",
                os.getenv("DB_USER", "ctoa"),
                "-d",
                os.getenv("DB_NAME", "ctoa"),
                "-t",
                "-A",
                "-c",
                filled,
            ]
        )
        return _run_argv(args, timeout=timeout, env=db_env)

    return {
        "code": 1,
        "stdout": "",
        "stderr": f"{psycopg2_error}; no psql executable and docker fallback unavailable.",
    }


def _redis_client() -> "RedisClient | None":
    if Redis is None:
        return None
    try:
        return Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _enqueue_worker_job(action: str, payload: dict[str, Any], requested_by: str) -> dict[str, Any]:
    if action not in {"orchestrator.tick", "orchestrator.report"}:
        return {"ok": False, "detail": f"Unsupported action: {action}"}

    cli = _redis_client()
    if cli is None:
        return {"ok": False, "detail": "Redis unavailable or redis package missing"}

    job = {
        "id": f"job-{secrets.token_hex(6)}",
        "action": action,
        "payload": payload or {},
        "requested_by": requested_by,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        cli.lpush(REDIS_QUEUE, json.dumps(job, ensure_ascii=True))
        raw_depth = cli.llen(REDIS_QUEUE)
        depth = int(raw_depth) if isinstance(raw_depth, int) else 0
        return {
            "ok": True,
            "queue": REDIS_QUEUE,
            "results": REDIS_RESULTS,
            "depth": depth,
            "job": job,
        }
    except Exception as exc:
        return {"ok": False, "detail": f"Redis enqueue failed: {exc}"}

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
    ctx: dict[str, Any] = Depends(require_owner),
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
    _trigger_orchestrator_start(timeout=5)

    _audit(request, f"server_register:{url}", 0, actor=ctx)
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


def _resolve_client_sync_path(
    client_root: Path,
    configured_path: str,
    label: str,
    *,
    reject_symlink: bool = False,
) -> Path:
    root = client_root.resolve(strict=False)
    candidate = Path(configured_path)
    if not candidate.is_absolute():
        candidate = client_root / candidate
    if reject_symlink and candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside CTOA_CLIENT_SCRIPTS_DIR") from exc
    return resolved


def _read_client_sync_init_text(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("CTOA_CLIENT_INIT_FILE must not be a symlink")
    try:
        with path.open("rb") as handle:
            raw = handle.read(CLIENT_SYNC_INIT_MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError("CTOA_CLIENT_INIT_FILE cannot be read") from exc
    if len(raw) > CLIENT_SYNC_INIT_MAX_BYTES:
        raise ValueError("CTOA_CLIENT_INIT_FILE is too large")
    return raw.decode("utf-8", errors="replace")


def _read_client_sync_lua_source(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("Client sync source Lua must not be a symlink")
    try:
        with path.open("rb") as handle:
            raw = handle.read(CLIENT_SYNC_LUA_MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError("Client sync source Lua cannot be read") from exc
    if len(raw) > CLIENT_SYNC_LUA_MAX_BYTES:
        raise ValueError("Client sync source Lua is too large")
    return raw


def _lua_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sync_intel_to_client(source_dir: Path) -> dict:
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
            "detail": f"Source dir not found: {_public_artifact_path(source_dir, fallback=source_dir.name)}",
        }

    try:
        client_root = Path(client_scripts).resolve(strict=False)
        target_slug = os.getenv("CTOA_CLIENT_TARGET_SLUG", "intel_target").strip() or "intel_target"
        target_dir = _resolve_client_sync_path(
            client_root,
            target_slug,
            "CTOA_CLIENT_TARGET_SLUG",
            reject_symlink=True,
        )
        autoload_name = os.getenv("CTOA_CLIENT_AUTOLOADER_NAME", "ctoa_intel_autoload.lua").strip()
        if not autoload_name:
            autoload_name = "ctoa_intel_autoload.lua"
        autoload_path = _resolve_client_sync_path(
            client_root,
            autoload_name,
            "CTOA_CLIENT_AUTOLOADER_NAME",
            reject_symlink=True,
        )
        init_file = os.getenv("CTOA_CLIENT_INIT_FILE", "").strip()
        init_path = (
            _resolve_client_sync_path(
                client_root,
                init_file,
                "CTOA_CLIENT_INIT_FILE",
                reject_symlink=True,
            )
            if init_file
            else None
        )
        include_line = f"dofile({_lua_string(autoload_path.as_posix())})"
        init_body = _read_client_sync_init_text(init_path) if init_path and init_path.exists() else None
        lua_sources = [
            (src.name, _read_client_sync_lua_source(src))
            for src in sorted(source_dir.glob("*.lua"))
        ]

        target_dir.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        for name, data in lua_sources:
            dst = target_dir / name
            if dst.is_symlink():
                raise ValueError("Client sync destination Lua must not be a symlink")
            _atomic_write_bytes(dst, data)
            copied.append(name)

        target_posix = target_dir.as_posix()
        lines = [
            "-- CTOA auto-generated intel autoloader",
            f"local BASE = {_lua_string(target_posix)}",
            "",
        ]
        for name in copied:
            lines.append(f"dofile(BASE .. {_lua_string('/' + name)})")
        autoload_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(autoload_path, "\n".join(lines) + "\n")

        init_updated = False
        if init_path and init_body is not None and include_line not in init_body:
            if not init_body.endswith("\n"):
                init_body += "\n"
            init_body += include_line + "\n"
            _atomic_write_text(init_path, init_body)
            init_updated = True

        return {
            "enabled": True,
            "ok": True,
            "target_dir": _public_artifact_path(target_dir, fallback=target_dir.name),
            "autoload": _public_artifact_path(autoload_path, fallback=autoload_path.name),
            "copied_files": copied,
            "copied_count": len(copied),
            "init_updated": init_updated,
        }
    except ValueError as exc:
        return {
            "enabled": True,
            "ok": False,
            "detail": str(exc),
        }
    except Exception:
        return {
            "enabled": True,
            "ok": False,
            "detail": "Client sync failed",
        }


def _public_artifact_path(value: Any, *, fallback: str = "") -> str:
    raw = str(value or "").strip()
    if not raw:
        return fallback

    candidate = Path(raw)
    if not candidate.is_absolute():
        raw_normalized = raw.replace("\\", "/")
        if ".." not in Path(raw_normalized).parts:
            return raw_normalized
        return Path(raw_normalized).name or fallback

    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return candidate.name or fallback

    known_roots = [
        ("generated", GENERATED_DIR),
        ("repo", ROOT),
    ]
    for prefix, root in known_roots:
        try:
            rel = resolved.relative_to(root.resolve(strict=False))
        except ValueError:
            continue
        if prefix == "repo":
            return rel.as_posix()
        return (Path(prefix) / rel).as_posix()

    return resolved.name or fallback


def _latest_manifest_payload() -> dict[str, Any] | None:
    latest_file = GENERATED_MANIFESTS_DIR / "latest.json"
    if not latest_file.exists():
        return None
    latest = _read_generated_manifest_json(latest_file)
    if latest is None:
        return None

    manifest_path = resolve_latest_manifest_path(GENERATED_MANIFESTS_DIR, latest)
    if manifest_path is None:
        return None

    manifest = _read_generated_manifest_json(manifest_path)
    if manifest is None:
        return None

    return {
        "run_id": latest.get("run_id") or manifest.get("run_id"),
        "manifest_path": _public_artifact_path(manifest_path),
        "manifest": manifest,
    }


def _scan_generated_files(limit: int) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not GENERATED_DIR.exists():
        return files

    for p in GENERATED_DIR.rglob("*.lua"):
        try:
            st = p.stat()
        except OSError:
            continue
        files.append(
            {
                "output_path": _public_artifact_path(p),
                "output_file": p.name,
                "server_slug": p.parent.name,
                "generated_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                "size": int(st.st_size),
            }
        )
    files.sort(key=lambda item: str(item.get("generated_at", "")), reverse=True)
    return files[:limit]


def _latest_manifest_summary() -> dict[str, Any] | None:
    payload = _latest_manifest_payload()
    if not payload:
        return None

    manifest = payload.get("manifest")
    if not isinstance(manifest, dict):
        return None

    generated = manifest.get("generated")
    failed = manifest.get("failed")
    generated_count = len(generated) if isinstance(generated, list) else 0
    failed_count = len(failed) if isinstance(failed, list) else 0

    return {
        "run_id": payload.get("run_id"),
        "manifest_path": payload.get("manifest_path"),
        "generated_count": generated_count,
        "failed_count": failed_count,
    }


def _execution_trend_from_manifests(limit_runs: int = 5) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    if not GENERATED_MANIFESTS_DIR.exists():
        return {
            "runs": runs,
            "summary": {
                "runs_count": 0,
                "ready_runs": 0,
                "failed_runs": 0,
                "empty_runs": 0,
            },
        }

    manifest_files = iter_safe_manifest_files(
        GENERATED_MANIFESTS_DIR,
        limit=max(1, limit_runs),
    )

    for manifest_path in manifest_files:
        manifest = _read_generated_manifest_json(manifest_path)
        if manifest is None:
            continue

        generated = manifest.get("generated")
        failed = manifest.get("failed")
        generated_count = len(generated) if isinstance(generated, list) else 0
        failed_count = len(failed) if isinstance(failed, list) else 0

        if generated_count > 0:
            status = "ready"
        elif failed_count > 0:
            status = "failed"
        else:
            status = "empty"

        runs.append(
            {
                "run_id": manifest.get("run_id") or manifest_path.parent.name,
                "generated_count": generated_count,
                "failed_count": failed_count,
                "status": status,
            }
        )

    return {
        "runs": runs,
        "summary": {
            "runs_count": len(runs),
            "ready_runs": sum(1 for r in runs if r["status"] == "ready"),
            "failed_runs": sum(1 for r in runs if r["status"] == "failed"),
            "empty_runs": sum(1 for r in runs if r["status"] == "empty"),
        },
    }


_SLO_MAX_FAILS = int(os.getenv("CTOA_SLO_MAX_FAILS", "3"))
_SLO_SUCCESS_RATE_THRESHOLD = float(os.getenv("CTOA_SLO_SUCCESS_RATE_THRESHOLD", "0.90"))

_STATUS_TO_REASON_CODE: dict[str, str] = {
    "ready": "ARTIFACTS_READY",
    "failed": "GENERATION_FAILED",
    "empty": "ARTIFACTS_PENDING",
}

_REASON_CODE_SEVERITY: dict[str, str] = {
    "ARTIFACTS_READY": "ready",
    "MANIFEST_PENDING": "warning",
    "ARTIFACTS_PENDING": "warning",
    "GENERATION_FAILED": "critical",
}

_DASHBOARD_STATUS_MESSAGES: dict[str, str] = {
    "healthy": "All systems operational",
    "degraded": "Non-critical query degraded \u2014 core functions available",
    "error": "Critical error detected \u2014 dashboard data may be incomplete",
}

_DASHBOARD_STATUS_SEVERITY: dict[str, str] = {
    "healthy": "info",
    "degraded": "warning",
    "error": "critical",
}

_DASHBOARD_STATUS_ACTIONS: dict[str, list[str]] = {
    "healthy": [
        "Monitor SLO trend and keep current rollout cadence.",
    ],
    "degraded": [
        "Review query_diagnostics for affected sections.",
        "Retry dashboard refresh after validating DB responsiveness.",
    ],
    "error": [
        "Prioritize critical query recovery (servers/modules).",
        "Validate database health and rerun dashboard query set.",
    ],
}


def _build_dashboard_status_context(
    *,
    status: str,
    sections: dict[str, dict[str, Any]],
    errors: dict[str, str],
) -> dict[str, Any]:
    degraded_sections = [name for name, payload in sections.items() if payload["code"] != 0]
    critical_sections = [
        name
        for name, payload in sections.items()
        if payload["critical"] and payload["code"] != 0
    ]

    message = _DASHBOARD_STATUS_MESSAGES.get(status, status)
    if status == "healthy":
        detail = "All dashboard queries returned successfully."
    elif status == "degraded":
        if degraded_sections:
            detail = (
                "Some non-critical sections are degraded: "
                + ", ".join(degraded_sections)
                + ". Core sections remain available."
            )
        else:
            detail = "Some non-critical dashboard sections are degraded."
    else:
        if critical_sections:
            detail = (
                "Critical sections failed: "
                + ", ".join(critical_sections)
                + ". Dashboard data may be incomplete."
            )
        else:
            detail = "Critical dashboard queries failed. Dashboard data may be incomplete."

    actions = list(_DASHBOARD_STATUS_ACTIONS.get(status, []))
    if errors and status != "healthy":
        actions.append("Inspect recent section errors and clear query blockers.")

    error_preview = [f"{name}: {reason}" for name, reason in errors.items() if reason][:3]

    return {
        "message": message,
        "detail": detail,
        "severity": _DASHBOARD_STATUS_SEVERITY.get(status, "warning"),
        "impacted_sections": degraded_sections,
        "critical_sections": critical_sections,
        "recommended_actions": actions,
        "error_preview": error_preview,
    }


def _iter_manifest_observations(limit_runs: int = 20) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    if not GENERATED_MANIFESTS_DIR.exists():
        return observations

    manifest_files = iter_safe_manifest_files(
        GENERATED_MANIFESTS_DIR,
        limit=max(1, limit_runs),
    )

    for manifest_path in manifest_files:
        manifest = _read_generated_manifest_json(manifest_path)
        if manifest is None:
            continue

        generated = manifest.get("generated")
        failed = manifest.get("failed")
        generated_count = len(generated) if isinstance(generated, list) else 0
        failed_count = len(failed) if isinstance(failed, list) else 0

        if generated_count > 0:
            status = "ready"
        elif failed_count > 0:
            status = "failed"
        else:
            status = "empty"

        reason_code = _STATUS_TO_REASON_CODE.get(status, "ARTIFACTS_PENDING")
        try:
            mtime = manifest_path.stat().st_mtime
        except OSError:
            mtime = 0.0

        observations.append(
            {
                "run_id": manifest.get("run_id") or manifest_path.parent.name,
                "manifest_path": _public_artifact_path(manifest_path),
                "generated_count": generated_count,
                "failed_count": failed_count,
                "status": status,
                "reason_code": reason_code,
                "severity": _REASON_CODE_SEVERITY.get(reason_code, "warning"),
                "timestamp": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                "mtime": mtime,
            }
        )

    return observations


def _build_reason_code_groups(by_reason_code: dict[str, int]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "ready": [],
        "warning": [],
        "critical": [],
    }
    for code, count in sorted(by_reason_code.items(), key=lambda item: (-int(item[1]), str(item[0]))):
        severity = _REASON_CODE_SEVERITY.get(code, "warning")
        groups.setdefault(severity, []).append(
            {
                "code": code,
                "count": int(count),
                "severity": severity,
            }
        )
    return groups


def _build_slo_timeline(observations: list[dict[str, Any]], window_seconds: int = 86400) -> list[dict[str, Any]]:
    window_start = time.time() - window_seconds
    timeline_source = [item for item in observations if float(item.get("mtime", 0.0)) >= window_start]

    failed_seen = 0
    timeline: list[dict[str, Any]] = []
    for item in timeline_source:
        reason_code = str(item.get("reason_code", "ARTIFACTS_PENDING"))
        if reason_code == "GENERATION_FAILED":
            failed_seen += 1

        if reason_code == "GENERATION_FAILED" and failed_seen >= _SLO_MAX_FAILS:
            event = "threshold_crossed"
        elif reason_code == "GENERATION_FAILED":
            event = "failure"
        elif reason_code == "ARTIFACTS_READY":
            event = "recovered"
        else:
            event = "pending"

        timeline.append(
            {
                "run_id": item.get("run_id"),
                "timestamp": item.get("timestamp"),
                "reason_code": reason_code,
                "severity": item.get("severity", "warning"),
                "generated_count": item.get("generated_count", 0),
                "failed_count": item.get("failed_count", 0),
                "event": event,
                "within_slo": reason_code != "GENERATION_FAILED",
            }
        )

    return timeline


def _compute_execution_metrics(limit_runs: int = 20) -> dict[str, Any]:
    observations = _iter_manifest_observations(limit_runs=limit_runs)
    by_reason_code: dict[str, int] = {}
    window_24h = time.time() - 86400
    runs_24h_total = 0
    runs_24h_success = 0

    for item in observations:
        reason_code = str(item.get("reason_code", "ARTIFACTS_PENDING"))
        by_reason_code[reason_code] = by_reason_code.get(reason_code, 0) + 1
        if float(item.get("mtime", 0.0)) >= window_24h:
            runs_24h_total += 1
            if reason_code == "ARTIFACTS_READY":
                runs_24h_success += 1

    success_rate_24h = (runs_24h_success / runs_24h_total) if runs_24h_total > 0 else 1.0
    failed_24h = sum(
        1
        for item in observations
        if float(item.get("mtime", 0.0)) >= window_24h and item.get("reason_code") == "GENERATION_FAILED"
    )
    spike = check_generation_failed_spike({"GENERATION_FAILED": failed_24h}, max_fails=_SLO_MAX_FAILS)
    error_budget_remaining = max(0, _SLO_MAX_FAILS - failed_24h)
    dominant_reason_code = None
    if by_reason_code:
        dominant_reason_code = sorted(by_reason_code.items(), key=lambda item: (-int(item[1]), str(item[0])))[0][0]

    return {
        "by_reason_code": by_reason_code,
        "success_rate_24h": round(success_rate_24h, 4),
        "success_rate_target": round(_SLO_SUCCESS_RATE_THRESHOLD, 4),
        "success_rate_met": success_rate_24h >= _SLO_SUCCESS_RATE_THRESHOLD,
        "runs_24h_total": runs_24h_total,
        "runs_24h_success": runs_24h_success,
        "error_budget_remaining": error_budget_remaining,
        "alert_active": spike["alert_active"],
        "alert_reason": spike["alert_reason"],
        "dominant_reason_code": dominant_reason_code,
    }


@app.post("/api/agents/intel/launch")
def launch_intel_mission(
    req: IntelMissionRequest,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    audit_reason = _require_guarded_action_confirmation(
        req,
        action_id="intel_launch",
        request=request,
        actor=ctx,
    )
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
        trigger = _trigger_orchestrator_start(timeout=8)

    _audit(request, f"intel_launch:{len(sanitized)}:reason={audit_reason}", int(trigger.get("code", 0)), actor=ctx)
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
            trainer_actions.append("Dostrajaj prompty pod stabilnosc i redukcje TODO/FIXME")
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
            "path": _public_artifact_path(AUTO_TRAINER_DIR, fallback=AUTO_TRAINER_DIR.name),
        }

    md_text = ""
    md_truncated = False
    if latest_md.exists():
        try:
            md_text, md_truncated = _read_text_bounded(
                latest_md, AUTO_TRAINER_MARKDOWN_MAX_BYTES
            )
        except OSError:
            md_text = ""
            md_truncated = False

    js_payload: dict = {}
    if latest_json.exists():
        js_payload = _read_json_bounded(latest_json, AUTO_TRAINER_JSON_MAX_BYTES)

    latest_mtime = None
    if latest_md.exists():
        latest_mtime = datetime.fromtimestamp(latest_md.stat().st_mtime, tz=timezone.utc).isoformat()

    return {
        "ok": True,
        "exists": True,
        "updated_at": latest_mtime,
        "markdown": md_text,
        "markdown_truncated": md_truncated,
        "json": js_payload,
    }


@app.post("/api/agents/execution/enqueue")
def agent_execution_enqueue(
    req: QueueJobRequest,
    request: Request,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    requested_by = str(ctx.get("username", "unknown"))
    queued = _enqueue_worker_job(req.action, req.payload, requested_by=requested_by)
    if not queued.get("ok"):
        raise HTTPException(status_code=503, detail=str(queued.get("detail", "Queue enqueue failed")))
    _audit(request, f"execution_enqueue:{req.action}:by={requested_by}", 0, actor=ctx)
    return queued

@app.post("/api/agents/execution/run")
@app.post("/api/agents/intel/run")
def agent_execution_one_click(
    request: Request,
    req: GuardedActionRequest | None = None,
    ctx: dict[str, Any] = Depends(require_owner),
) -> dict:
    audit_reason = _require_guarded_action_confirmation(
        req,
        action_id="agent_execution_one_click",
        request=request,
        actor=ctx,
    )
    target_url = _validate_url(os.getenv("CTOA_INTEL_TARGET_URL", "https://tibiantis.online"))
    res = _db_exec(
        "INSERT INTO servers (url, status) VALUES (%s, 'NEW') "
        "ON CONFLICT (url) DO UPDATE SET status='NEW', updated_at=now() "
        "RETURNING id, status",
        (target_url,),
    )
    if res["code"] != 0:
        raise HTTPException(status_code=503, detail=f"DB error: {res['stderr'][:200]}")

    trig = _trigger_orchestrator_start(timeout=8)
    if trig["code"] != 0:
        raise HTTPException(status_code=503, detail=f"Orchestrator error: {trig['stderr'][:200]}")

    # Give systemd one-shot a moment to produce outputs.
    time.sleep(3)

    slug = _slug(target_url)
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

    manifest_summary = _latest_manifest_summary()
    execution_trend = _execution_trend_from_manifests(limit_runs=5)

    srv_state = _db_exec(
        "SELECT id, url, status, game_type, coalesce(scout_error,'') "
        "FROM servers WHERE url=%s ORDER BY id DESC LIMIT 1",
        (target_url,),
    )

    sync = _sync_intel_to_client(out_dir)

    ready_for_publish = bool(files) or bool(manifest_summary and manifest_summary.get("generated_count", 0) > 0)
    warnings: list[str] = []
    if not files:
        warnings.append("No Lua outputs detected yet; orchestrator may still be processing.")
    if not manifest_summary:
        warnings.append("Generated-output manifest not available yet.")
    if sync.get("enabled") and not sync.get("ok"):
        warnings.append(f"Client sync not ready: {sync.get('detail', 'unknown')}")

    quality_gate = {
        "passed": ready_for_publish,
        "ready_for_publish": ready_for_publish,
        "checks": [
            {
                "id": "orchestrator_triggered",
                "ok": True,
                "severity": "error",
                "detail": "systemd accepted one-click execution trigger",
            },
            {
                "id": "generated_files_detected",
                "ok": bool(files),
                "severity": "warn",
                "detail": "Lua outputs detected in generated directory" if files else "Outputs not visible yet",
            },
            {
                "id": "manifest_contract_present",
                "ok": bool(manifest_summary),
                "severity": "warn",
                "detail": "Generated manifest is available" if manifest_summary else "Manifest contract pending",
            },
            {
                "id": "client_sync_ready",
                "ok": bool(sync.get("ok")) if sync.get("enabled") else True,
                "severity": "warn",
                "detail": "Client sync completed" if sync.get("ok") else str(sync.get("detail", "sync skipped")),
            },
        ],
    }
    execution_status = "artifacts_ready" if ready_for_publish else "triggered_pending_artifacts"
    if ready_for_publish:
        reason_code = "ARTIFACTS_READY"
    elif manifest_summary and manifest_summary.get("failed_count", 0) > 0:
        reason_code = "GENERATION_FAILED"
    elif not manifest_summary:
        reason_code = "MANIFEST_PENDING"
    else:
        reason_code = "ARTIFACTS_PENDING"

    _audit(request, f"agent_execution_one_click:reason={audit_reason}", 0, actor=ctx)
    return {
        "ok": True,
        "execution_status": execution_status,
        "reason_code": reason_code,
        "reason_code_taxonomy": REASON_CODE_TAXONOMY,
        "url": target_url,
        "generated_dir": _public_artifact_path(out_dir, fallback=slug),
        "files": files,
        "files_count": len(files),
        "manifest": manifest_summary,
        "execution_trend": execution_trend,
        "server_state": srv_state.get("stdout", "").strip(),
        "quality_gate": quality_gate,
        "warnings": warnings,
        "trigger_result": {
            "code": trig.get("code", -1),
            "stdout": (trig.get("stdout", "") or "").strip(),
            "stderr": (trig.get("stderr", "") or "").strip(),
        },
        "client_sync": sync,
    }


@app.get("/api/agents/execution/trend")
def execution_trend(
    limit_runs: int = Query(default=5, ge=1, le=30),
    _: dict[str, Any] = Depends(require_operator),
) -> dict:
    trend = _execution_trend_from_manifests(limit_runs=limit_runs)
    return {
        "ok": True,
        "limit_runs": limit_runs,
        "reason_code_taxonomy": REASON_CODE_TAXONOMY,
        "runs": trend.get("runs", []),
        "summary": trend.get("summary", {}),
    }


@app.get("/api/agents/execution/metrics")
def agent_execution_metrics(
    limit_runs: int = Query(default=20, ge=1, le=100),
    _: dict[str, Any] = Depends(require_operator),
) -> dict:
    metrics = _compute_execution_metrics(limit_runs=limit_runs)
    return {
        "ok": True,
        "limit_runs": limit_runs,
        "reason_code_taxonomy": REASON_CODE_TAXONOMY,
        "reason_code_groups": _build_reason_code_groups(metrics.get("by_reason_code", {})),
        "slo_timeline": _build_slo_timeline(_iter_manifest_observations(limit_runs=limit_runs)),
        **metrics,
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
                    "output_path": _public_artifact_path(
                        entry.get("output_path"),
                        fallback=str(entry.get("output_file") or ""),
                    ),
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

@app.get("/api/dashboard")
def dashboard(_: dict[str, Any] = Depends(require_operator)) -> dict:
    def parse_rows(raw: str) -> list[list[str]]:
        rows = []
        for line in raw.strip().splitlines():
            if line.strip():
                rows.append(line.split("|"))
        return rows

    def fetch_rows(name: str, sql: str, timeout: int = 4, critical: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        try:
            res = _db_exec(sql, timeout=timeout)
        except Exception as exc:
            res = {
                "code": 1,
                "stdout": "",
                "stderr": str(exc)[:200],
            }

        code = int(res.get("code", 1))
        rows = parse_rows(res.get("stdout", ""))
        stderr = (res.get("stderr", "") or "")[:200]
        duration_ms = int((time.monotonic() - started) * 1000)

        return {
            "name": name,
            "critical": critical,
            "code": code,
            "rows": rows,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "row_count": len(rows),
            "status": "ok" if code == 0 else ("critical_error" if critical else "degraded"),
        }

    servers_res = fetch_rows(
        "servers",
        "SELECT id, url, status, created_at FROM servers ORDER BY id DESC LIMIT 20",
        timeout=4,
        critical=True,
    )
    modules_res = fetch_rows(
        "modules",
        "SELECT status, COUNT(*) AS n FROM modules GROUP BY status ORDER BY status",
        timeout=4,
        critical=True,
    )
    stats_res = fetch_rows(
        "stats",
        "SELECT dt, modules_generated, programs_generated, avg_quality, launcher_day "
        "FROM daily_stats ORDER BY dt DESC LIMIT 7",
        timeout=4,
    )
    top_res = fetch_rows(
        "top",
        "SELECT task_id, output_file, quality_score, status "
        "FROM modules WHERE quality_score IS NOT NULL ORDER BY quality_score DESC LIMIT 10",
        timeout=4,
    )

    sections = {
        "servers": servers_res,
        "modules": modules_res,
        "stats": stats_res,
        "top": top_res,
    }

    errors = {
        name: payload["stderr"]
        for name, payload in sections.items()
        if payload["code"] != 0
    }

    critical_ok = all(payload["code"] == 0 for payload in sections.values() if payload["critical"])
    degraded = any(payload["code"] != 0 for payload in sections.values())
    status = "healthy" if critical_ok and not degraded else ("degraded" if critical_ok else "error")

    health_timeline: list[dict[str, Any]] = []
    for row in stats_res["rows"]:
        if len(row) < 5:
            continue
        try:
            modules_generated = int(row[1]) if str(row[1]).strip() else 0
        except Exception:
            modules_generated = 0
        try:
            programs_generated = int(row[2]) if str(row[2]).strip() else 0
        except Exception:
            programs_generated = 0
        try:
            avg_quality = float(row[3]) if str(row[3]).strip() else 0.0
        except Exception:
            avg_quality = 0.0

        launcher_value = str(row[4]).strip().lower()
        launcher_released = launcher_value in {"t", "true", "1", "yes"}

        health_timeline.append(
            {
                "date": str(row[0]),
                "modules_generated": modules_generated,
                "programs_generated": programs_generated,
                "avg_quality": avg_quality,
                "launcher_released": launcher_released,
            }
        )

    timeline_avg_quality = 0.0
    if health_timeline:
        timeline_avg_quality = sum(item["avg_quality"] for item in health_timeline) / len(health_timeline)

    execution_observations = _iter_manifest_observations(limit_runs=20)
    execution_metrics = _compute_execution_metrics(limit_runs=20)
    by_reason_code = execution_metrics.get("by_reason_code", {})
    top_reason_codes = [
        {"code": code, "count": int(count)}
        for code, count in sorted(
            by_reason_code.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
    ]
    reason_code_groups = _build_reason_code_groups(by_reason_code)
    slo_timeline = _build_slo_timeline(execution_observations)
    dominant_signal = top_reason_codes[0] if top_reason_codes else None
    if dominant_signal:
        dominant_signal = {
            **dominant_signal,
            "severity": _REASON_CODE_SEVERITY.get(str(dominant_signal.get("code")), "warning"),
        }

    status_context = _build_dashboard_status_context(
        status=status,
        sections=sections,
        errors=errors,
    )

    return {
        "servers": servers_res["rows"],
        "modules": modules_res["rows"],
        "stats": stats_res["rows"],
        "top": top_res["rows"],
        "health_timeline": health_timeline,
        "top_reason_codes": top_reason_codes,
        "reason_code_groups": reason_code_groups,
        "dominant_signal": dominant_signal,
        "slo_timeline": slo_timeline,
        "slo_summary": {
            "success_rate_24h": execution_metrics.get("success_rate_24h", 1.0),
            "success_rate_target": execution_metrics.get("success_rate_target", _SLO_SUCCESS_RATE_THRESHOLD),
            "success_rate_met": execution_metrics.get("success_rate_met", True),
            "error_budget_remaining": execution_metrics.get("error_budget_remaining", _SLO_MAX_FAILS),
            "alert_active": execution_metrics.get("alert_active", False),
            "dominant_reason_code": execution_metrics.get("dominant_reason_code"),
        },
        "ok": critical_ok,
        "degraded": degraded,
        "status": status,
        "status_message": status_context["message"],
        "status_context": status_context,
        "errors": errors,
        "query_diagnostics": {
            name: {
                "status": payload["status"],
                "critical": payload["critical"],
                "code": payload["code"],
                "duration_ms": payload["duration_ms"],
                "row_count": payload["row_count"],
            }
            for name, payload in sections.items()
        },
        "summary": {
            "critical_sections_ok": critical_ok,
            "degraded_sections": [name for name, payload in sections.items() if payload["code"] != 0],
            "healthy_sections": [name for name, payload in sections.items() if payload["code"] == 0],
        },
        "timeline_summary": {
            "days": len(health_timeline),
            "avg_quality": round(timeline_avg_quality, 2),
            "latest_day": health_timeline[0]["date"] if health_timeline else None,
        },
    }


@app.get("/api/agents/status")
def agents_status(_: dict[str, Any] = Depends(require_operator)) -> dict:
    units = {
        "orchestrator": "ctoa-agents-orchestrator.service",
        "orchestrator_timer": "ctoa-agents-orchestrator.timer",
        "db": "ctoa-db",
    }
    out: dict[str, str] = {}

    for key, unit in units.items():
        if key == "db":
            if _command_exists("docker"):
                inspect = _run_argv(
                    ["docker", "inspect", "--format", "{{.State.Status}}", "ctoa-db"],
                    timeout=5,
                )
                if inspect.get("code", 1) == 0:
                    out[key] = inspect.get("stdout", "").strip() or "unknown"
                else:
                    combined = f"{inspect.get('stdout','')} {inspect.get('stderr','')}".lower()
                    if "no such object" in combined:
                        out[key] = "missing"
                    else:
                        probe = _db_exec("SELECT 1", timeout=5)
                        out[key] = "reachable" if probe.get("code", 1) == 0 else "unreachable"
            else:
                probe = _db_exec("SELECT 1", timeout=5)
                out[key] = "reachable" if probe.get("code", 1) == 0 else "missing"
            continue

        out[key] = _service_is_active(unit)

    last_runs = _db_exec(
        "SELECT agent, status, finished_at FROM agent_runs ORDER BY id DESC LIMIT 12",
    )
    out["last_runs_raw"] = last_runs.get("stdout", "")
    return out


@app.get("/api/commands/dictionary")
def commands_dictionary(_: dict[str, Any] = Depends(require_operator)) -> dict:
    payload = _load_json_file(COMMAND_DICTIONARY_FILE)
    raw_commands = payload.get("commands")
    commands = raw_commands if isinstance(raw_commands, list) else []
    return {
        "ok": True,
        "version": str(payload.get("version", "unknown")),
        "source": str(payload.get("source", "shared-cli-web")),
        "count": len(commands),
        "commands": commands,
    }

























@app.get("/api/dashboard/release-evidence")
def dashboard_release_evidence(_: dict[str, Any] = Depends(require_operator)) -> dict:
    status_payload = _ctoa_api_proxy("/api/status")
    release_payload = _ctoa_api_proxy("/api/release-evidence")

    release_body = release_payload.get("body") if isinstance(release_payload.get("body"), dict) else {}
    release_state = str(release_body.get("state", "UNKNOWN")) if release_body else "UNKNOWN"

    return {
        "ok": bool(status_payload.get("ok")) and bool(release_payload.get("ok")),
        "status": status_payload,
        "release_evidence": release_payload,
        "release_state": release_state,
        "source": {
            "status_endpoint": "/api/status",
            "release_evidence_endpoint": "/api/release-evidence",
        },
    }
