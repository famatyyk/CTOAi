import importlib
import json
import tempfile
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient


def _load_app_module(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    *,
    package_tier: str = "studio",
    mobile_console_enabled: bool | None = None,
):
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_USER", "CTO")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "asdzxc12")
    monkeypatch.setenv("CTOA_OPERATOR_USER", "ctoa-bot")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "jakpod22")
    monkeypatch.setenv("CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json"))
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_GENERATED_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv("CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json"))
    monkeypatch.setenv("CTOA_PACKAGE_TIER", package_tier)
    if mobile_console_enabled is not None:
        monkeypatch.setenv("CTOA_CAPABILITY_MOBILE_CONSOLE", "true" if mobile_console_enabled else "false")

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


def _extract_api_route_map(app) -> dict[str, list[str]]:
    route_map: dict[str, set[str]] = {}
    allowed = {"GET", "POST", "PUT", "DELETE", "PATCH"}

    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if not path.startswith("/api/"):
            continue
        selected = {method for method in methods if method in allowed}
        if not selected:
            continue
        route_map.setdefault(path, set()).update(selected)

    return {path: sorted(methods) for path, methods in route_map.items()}


def test_mobile_console_contract_snapshot_required_routes(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        module = _load_app_module(monkeypatch, tmp_path)
        route_map = _extract_api_route_map(module.app)

        snapshot_path = Path(__file__).resolve().parents[1] / "schemas" / "mobile_console_api_contract.snapshot.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

        missing_paths: list[str] = []
        method_mismatch: list[str] = []

        for item in snapshot.get("required_routes", []):
            path = str(item.get("path", "")).strip()
            expected = sorted(set(item.get("methods", [])))
            actual = route_map.get(path)
            if actual is None:
                missing_paths.append(path)
                continue
            if not set(expected).issubset(set(actual)):
                method_mismatch.append(f"{path}: expected {expected}, got {actual}")

        assert not missing_paths, "Missing API paths in app contract: " + ", ".join(missing_paths)
        assert not method_mismatch, "API method mismatch: " + "; ".join(method_mismatch)


def test_mobile_console_critical_endpoints_keep_security_regressions(monkeypatch: MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmp:
        core_module = _load_app_module(
            monkeypatch,
            Path(tmp),
            package_tier="core",
            mobile_console_enabled=False,
        )
        core_client = TestClient(core_module.app)

        blocked_login = core_client.post("/api/auth/login", json={"username": "CTO", "password": "asdzxc12"})
        assert blocked_login.status_code == 403

        blocked_console = core_client.get("/console")
        assert blocked_console.status_code == 403

    with tempfile.TemporaryDirectory() as tmp:
        module = _load_app_module(monkeypatch, Path(tmp), package_tier="pro", mobile_console_enabled=True)
        client = TestClient(module.app)

        login = client.post("/api/auth/login", json={"username": "CTO", "password": "asdzxc12"})
        assert login.status_code == 200
        token = login.json()["token"]

        health = client.get("/api/health", headers={"Authorization": f"Bearer {token}"})
        assert health.status_code == 200
        assert health.json()["ok"] is True
