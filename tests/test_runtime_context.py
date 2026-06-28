from scripts.ops.runtime_context import is_production_env


def test_is_production_env_uses_ctoa_env_only(monkeypatch):
    monkeypatch.delenv("CTOA_ENV", raising=False)
    monkeypatch.setenv("ENV", "production")
    assert is_production_env() is False

    monkeypatch.setenv("CTOA_ENV", "prod")
    assert is_production_env() is True
