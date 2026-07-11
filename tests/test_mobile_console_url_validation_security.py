import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException


def _load_app(
    monkeypatch, tmp_path: Path, *, env: str = "production", allow_private: bool = False
):
    monkeypatch.setenv("CTOA_ENV", env)
    monkeypatch.setenv("CTOA_CORS_ORIGINS", "https://ctoa.example")
    monkeypatch.setenv("CTOA_MOBILE_TOKEN", "test-mobile-token")
    monkeypatch.setenv("CTOA_OWNER_PASSWORD", "test-owner-pass")
    monkeypatch.setenv("CTOA_OPERATOR_PASSWORD", "test-operator-pass")
    monkeypatch.setenv("DB_PASSWORD", "test-db-pass")
    monkeypatch.setenv("CTOA_SELF_REGISTER_ENABLED", "false")
    monkeypatch.setenv(
        "CTOA_ADMIN_SETTINGS_FILE", str(tmp_path / "admin-settings.json")
    )
    monkeypatch.setenv("CTOA_IDEA_PARKING_FILE", str(tmp_path / "idea-parking.json"))
    monkeypatch.setenv("CTOA_PRODUCT_STATE_DIR", str(tmp_path / ".ctoa-local"))
    monkeypatch.setenv(
        "CTOA_PRODUCT_USER_CONFIG", str(tmp_path / ".ctoa-local" / "user-config.json")
    )
    if allow_private:
        monkeypatch.setenv("CTOA_ALLOW_PRIVATE_INTEL_TARGETS", "true")
    else:
        monkeypatch.delenv("CTOA_ALLOW_PRIVATE_INTEL_TARGETS", raising=False)

    import mobile_console.app as mobile_app

    return importlib.reload(mobile_app)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000",
        "http://10.0.0.10/game",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost:8787",
        "http://service.local:8787",
        "http://internal:8787",
    ],
)
def test_intel_url_validation_rejects_private_or_local_targets_in_production(
    monkeypatch,
    tmp_path,
    url: str,
) -> None:
    module = _load_app(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as exc:
        module._validate_url(url)

    assert exc.value.status_code == 422
    assert "Private or local intel target URLs are disabled" in exc.value.detail


def test_intel_url_validation_allows_public_targets_in_production(
    monkeypatch, tmp_path
) -> None:
    module = _load_app(monkeypatch, tmp_path)

    assert (
        module._validate_url("https://example.com/game/") == "https://example.com/game"
    )


@pytest.mark.parametrize(
    ("url", "detail"),
    [
        ("https://user:pass@example.com/game", "URL credentials are not allowed"),
        (
            "https://example.com/game?token=secret-token-value",
            "URL query strings and fragments are not allowed",
        ),
        (
            "https://example.com/game#token",
            "URL query strings and fragments are not allowed",
        ),
        ("https://example.com/game\\secret", "URL path must not contain backslashes"),
        ("https://example.com/game/../admin", "URL path must not contain traversal"),
        (
            "https://example.com/game/%2e%2e/admin",
            "URL path must not contain traversal",
        ),
    ],
)
def test_intel_url_validation_rejects_secret_bearing_or_unsafe_url_parts(
    monkeypatch,
    tmp_path,
    url: str,
    detail: str,
) -> None:
    module = _load_app(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as exc:
        module._validate_url(url)

    assert exc.value.status_code == 422
    assert exc.value.detail == detail


def test_intel_url_validation_allows_private_targets_with_explicit_production_opt_in(
    monkeypatch,
    tmp_path,
) -> None:
    module = _load_app(monkeypatch, tmp_path, allow_private=True)

    assert module._validate_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"


def test_intel_url_validation_keeps_local_targets_available_outside_production(
    monkeypatch,
    tmp_path,
) -> None:
    module = _load_app(monkeypatch, tmp_path, env="development")

    assert module._validate_url("http://localhost:8787") == "http://localhost:8787"


def test_intel_url_validation_rejects_invalid_ports(monkeypatch, tmp_path) -> None:
    module = _load_app(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as exc:
        module._validate_url("https://example.com:99999")

    assert exc.value.status_code == 422
    assert exc.value.detail == "Invalid URL port"


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.com/data", "https:///missing-host"]
)
def test_http_proxy_url_guard_rejects_non_http_or_hostless_urls(
    monkeypatch, tmp_path, url: str
) -> None:
    module = _load_app(monkeypatch, tmp_path, env="development")

    with pytest.raises(ValueError) as exc:
        module._require_http_url(url)

    assert "URL must use http:// or https:// and include a host" in str(exc.value)


@pytest.mark.parametrize(
    ("url", "detail"),
    [
        (
            "https://api.example.com:8001",
            "CTOA API base URL must target a local runtime API host",
        ),
        (
            "http://user:secret@127.0.0.1:8001",
            "CTOA API base URL must not include credentials, query, or fragment",
        ),
        (
            "http://127.0.0.1:8001?token=secret",
            "CTOA API base URL must not include credentials, query, or fragment",
        ),
        (
            "http://127.0.0.1:8001#token",
            "CTOA API base URL must not include credentials, query, or fragment",
        ),
        (
            "http://127.0.0.1:8001/api\\status",
            "CTOA API base URL path must not include backslashes",
        ),
        (
            "http://127.0.0.1:8001/api/%2e%2e/admin",
            "CTOA API base URL path must not contain traversal",
        ),
    ],
)
def test_local_runtime_api_base_url_rejects_unsafe_values(
    monkeypatch,
    tmp_path,
    url: str,
    detail: str,
) -> None:
    module = _load_app(monkeypatch, tmp_path, env="development")

    with pytest.raises(ValueError) as exc:
        module._require_local_runtime_api_base_url(url, "CTOA API base")

    assert str(exc.value) == detail


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8001/",
        "http://localhost:8001/api",
        "http://[::1]:8001",
        "http://host.docker.internal:8001",
    ],
)
def test_local_runtime_api_base_url_allows_local_runtime_hosts(
    monkeypatch,
    tmp_path,
    url: str,
) -> None:
    module = _load_app(monkeypatch, tmp_path, env="development")

    assert module._require_local_runtime_api_base_url(url, "CTOA API base") == url.rstrip("/")
