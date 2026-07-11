from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GS_RESET = ROOT / "scripts" / "ops" / "gs-reset.sh"


def _script_text() -> str:
    return GS_RESET.read_text(encoding="utf-8")


def test_gs_reset_validates_env_provided_api_urls_before_curl() -> None:
    script = _script_text()
    validation_start = script.index("is_local_api_health_url()")
    curl_start = script.index("HTTP_CODE=$(curl")
    validation_block = script[validation_start:curl_start]

    assert "is_local_api_health_url()" in script
    assert "is_local_api_base_url()" in script
    assert 'if ! is_local_api_health_url "$API_HEALTH_URL"; then' in validation_block
    assert 'if ! is_local_api_base_url "$API_BASE_URL"; then' in validation_block
    assert (
        "must be a local HTTP(S) URL without credentials, query, or fragment"
        in validation_block
    )
    assert (
        "must be a local HTTP(S) origin without credentials, path, query, or fragment"
        in validation_block
    )
    assert "127\\.0\\.0\\.1|localhost|\\[::1\\]" in validation_block
    assert "file://" not in validation_block


def test_gs_reset_validates_numeric_wait_and_retry_env_values() -> None:
    script = _script_text()
    validation_start = script.index("is_positive_int()")
    phase_start = script.index("PHASE 1")
    validation_block = script[validation_start:phase_start]

    assert 'if ! is_positive_int "$API_CHECK_RETRIES"; then' in validation_block
    assert 'if ! is_positive_int "$GS_TIMEOUT_WAIT"; then' in validation_block
    assert "API_CHECK_RETRIES must be a positive integer" in validation_block
    assert "GS_TIMEOUT_WAIT must be a positive integer" in validation_block
