import importlib
import logging

import pytest


def _load_db_module(monkeypatch):
    import runner.agents.db as db

    module = importlib.reload(db)
    monkeypatch.setattr(module, "_pool", None)
    return module


def test_agent_db_pool_uses_keyword_config_instead_of_password_dsn(monkeypatch):
    module = _load_db_module(monkeypatch)
    monkeypatch.setenv("DB_PASSWORD", "super-secret-db-pass")
    monkeypatch.setenv("DB_HOST", "db.local")
    monkeypatch.setenv("DB_PORT", "15432")
    monkeypatch.setenv("DB_NAME", "ctoa_db")
    monkeypatch.setenv("DB_USER", "ctoa_user")
    monkeypatch.setattr(module, "_HAS_PSYCOPG2", True)

    captured = {}

    class FakePool:
        closed = False

    class FakePgPool:
        @staticmethod
        def SimpleConnectionPool(minconn, maxconn, **kwargs):
            captured["minconn"] = minconn
            captured["maxconn"] = maxconn
            captured["kwargs"] = kwargs
            return FakePool()

    monkeypatch.setattr(module, "pg_pool", FakePgPool)

    pool = module.get_pool()

    assert isinstance(pool, FakePool)
    assert captured["minconn"] == 1
    assert captured["maxconn"] == 4
    assert captured["kwargs"] == {
        "host": "db.local",
        "port": "15432",
        "dbname": "ctoa_db",
        "user": "ctoa_user",
        "password": "super-secret-db-pass",
        "connect_timeout": 10,
    }
    assert "dsn" not in captured["kwargs"]
    assert "password=super-secret-db-pass" not in repr(captured["kwargs"])


def test_agent_db_missing_password_error_does_not_echo_secret(monkeypatch):
    module = _load_db_module(monkeypatch)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="DB_PASSWORD env var is required"):
        module._connect_config()


def test_agent_db_log_run_redacts_secret_bearing_db_errors(monkeypatch, caplog):
    module = _load_db_module(monkeypatch)

    def fail_execute(sql, params=()):
        raise RuntimeError(
            "connect failed password=super-secret-db-pass "
            "postgresql://ctoa:url-secret-pass@db.local/ctoa"
        )

    monkeypatch.setattr(module, "execute", fail_execute)

    with caplog.at_level(logging.ERROR, logger=module.__name__):
        module.log_run("agent", "failed", "message")

    assert "Failed to write agent_runs" in caplog.text
    assert "super-secret-db-pass" not in caplog.text
    assert "url-secret-pass" not in caplog.text
    assert "password=[redacted]" in caplog.text
    assert "postgresql://ctoa:[redacted]@db.local/ctoa" in caplog.text
