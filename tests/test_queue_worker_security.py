from pathlib import Path

from runner import queue_worker


def test_queue_worker_redacts_redis_url_credentials_and_query() -> None:
    value = queue_worker._redis_url_for_log(
        "redis://worker:super-secret-pass@redis.internal:6379/0?token=also-secret"
    )

    assert "super-secret-pass" not in value
    assert "also-secret" not in value
    assert value == "redis://worker:[redacted]@redis.internal:6379/0?[redacted]"


def test_queue_worker_redacts_password_only_redis_url() -> None:
    value = queue_worker._redis_url_for_log("redis://:super-secret-pass@127.0.0.1:6379/0")

    assert "super-secret-pass" not in value
    assert value == "redis://:[redacted]@127.0.0.1:6379/0"


def test_queue_worker_parse_invalid_payload_drops_raw_secret() -> None:
    job = queue_worker._parse_job_payload("{not-json token=secret-value")

    assert job == {"action": "unknown"}
    assert "raw" not in job


def test_queue_worker_source_does_not_log_raw_redis_url() -> None:
    source = Path(queue_worker.__file__).read_text(encoding="utf-8")

    assert 'logging.info("queue-worker started queue=%s redis=%s", QUEUE_KEY, REDIS_URL)' not in source
    assert "_redis_url_for_log(REDIS_URL)" in source
    assert "except Exception" not in source
