import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / "scripts" / "ops" / "gs-api-validator.py"
    spec = importlib.util.spec_from_file_location("gs_api_validator_security", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fetch_json_rejects_unsafe_urls_before_urlopen(monkeypatch):
    module = _load_module()
    calls = []

    def fail_urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("urlopen must not run for unsafe GS validator URLs")

    monkeypatch.setattr(module.urllib.request, "urlopen", fail_urlopen)

    unsafe_urls = [
        "https://api.example.com/health",
        "http://127.0.0.1:8890/health?token=secret",
        "http://user:secret@127.0.0.1:8890/health",
        "http://127.0.0.1:8890/../health",
        "http://127.0.0.1:8890/health#fragment",
        "file:///tmp/health",
    ]

    for url in unsafe_urls:
        assert module.fetch_json(url) is None

    assert calls == []


def test_fetch_json_allows_loopback_url(monkeypatch):
    module = _load_module()
    calls: list[tuple[str, int]] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(url: str, timeout: int):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    assert module.fetch_json("http://127.0.0.1:8890/health") == {"ok": True}
    assert calls == [("http://127.0.0.1:8890/health", module.TIMEOUT_SEC)]


def test_normalize_base_requires_local_origin():
    module = _load_module()

    assert module.normalize_base("http://127.0.0.1:8890/") == "http://127.0.0.1:8890"
    assert module.normalize_base("http://localhost:8890") == "http://localhost:8890"

    unsafe_bases = [
        "https://api.example.com",
        "http://127.0.0.1:8890/api",
        "http://127.0.0.1:8890?token=secret",
        "http://user:secret@127.0.0.1:8890",
        "http://127.0.0.1:8890#fragment",
    ]

    for base in unsafe_bases:
        try:
            module.normalize_base(base)
        except ValueError:
            continue
        raise AssertionError(f"unsafe GS API base accepted: {base}")


def test_detect_module_root_rejects_remote_base_before_urlopen(monkeypatch):
    module = _load_module()
    module.API_BASE_URL = "https://api.example.com"

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("urlopen must not run for unsafe GS API base URLs")

    monkeypatch.setattr(module.urllib.request, "urlopen", fail_urlopen)

    assert module.detect_module_root() is None
