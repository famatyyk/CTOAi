import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runner.http_safety import require_loopback_http_url  # noqa: E402

base = require_loopback_http_url(
    os.getenv("CTOA_RUNTIME_SMOKE_BASE", "http://127.0.0.1:8001").rstrip("/")
)
smoke_user = os.getenv("CTOA_RUNTIME_SMOKE_USER", "").strip()
smoke_password = os.getenv("CTOA_RUNTIME_SMOKE_PASSWORD", "").strip()

if not smoke_user or not smoke_password:
    raise SystemExit(
        "Set CTOA_RUNTIME_SMOKE_USER and CTOA_RUNTIME_SMOKE_PASSWORD before running this smoke."
    )


def req(path, method="GET", token=None, payload=None):
    if not str(path).startswith("/"):
        raise ValueError("Smoke request paths must start with /")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request_url = require_loopback_http_url(base + path)
    request = urllib.request.Request(
        request_url, data=data, headers=headers, method=method
    )
    # require_loopback_http_url keeps credentials and bearer tokens on local API targets.
    with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310
        return response.status, json.loads(response.read().decode("utf-8"))


status, data = req(
    "/api/auth/login",
    "POST",
    payload={"username": smoke_user, "password": smoke_password},
)
if status != 200:
    raise SystemExit(f"login failed: {data}")
token = data["token"]

status, data = req("/api/auth/me", token=token)
if status != 200 or data["user"]["role"] != "owner":
    raise SystemExit(f"auth check failed: {data}")

status, data = req("/api/community/invites", token=token)
if status != 200:
    raise SystemExit(f"invites check failed: {data}")

print("RUNTIME_SMOKE_E2E_OK")
