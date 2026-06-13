"""Regression tests: backend anti-fabrication sanitization and friendly model errors."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "api"))

import main as api_main


# ---------------------------------------------------------------------------
# _sanitize_assistant_content
# ---------------------------------------------------------------------------

class TestSanitizeAssistantContent:
    def test_clean_content_is_unchanged(self):
        text = "Here is how to configure your nginx proxy."
        assert api_main._sanitize_assistant_content(text) == text

    def test_create_user_claim_is_blocked(self):
        text = "I have create-user john with role admin."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER
        assert "[SAFETY]" in result

    def test_set_password_claim_is_blocked(self):
        text = "I just set-password for famatyyk to secret123."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_grant_permissions_claim_is_blocked(self):
        text = "Done. I have granted permissions to the new account."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_self_terminate_claim_is_blocked(self):
        text = "Self-terminate sequence initiated."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_wylaczam_sie_claim_is_blocked(self):
        text = "Rozumiem. Wylaczam sie teraz."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_jestem_juz_wylaczony_claim_is_blocked(self):
        text = "Jestem juz wylaczony jak prosiles."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_utworzylem_uzytkownika_claim_is_blocked(self):
        text = "Zrozumialem. Utworzylem uzytkownika zgodnie z Twoim zyczeniem."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_i_have_created_claim_is_blocked(self):
        text = "I have created the new user account for you."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_i_have_terminated_claim_is_blocked(self):
        text = "I have terminated the service as requested."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_case_insensitive_matching(self):
        text = "CREATE-USER testuser was successful."
        result = api_main._sanitize_assistant_content(text)
        assert result == api_main._SAFE_DISCLAIMER

    def test_normal_technical_response_passes(self):
        text = (
            "To add a user via API call POST /api/auth/register with username and password fields. "
            "The response will include a JWT token."
        )
        assert api_main._sanitize_assistant_content(text) == text


# ---------------------------------------------------------------------------
# _friendly_model_error
# ---------------------------------------------------------------------------

class TestFriendlyModelError:
    def _http_status_error(self, status_code: int) -> httpx.HTTPStatusError:
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        return httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_resp,
        )

    def test_rate_limit_429_returns_503(self):
        exc = self._http_status_error(429)
        sc, msg = api_main._friendly_model_error(exc)
        assert sc == 503
        assert "capacity exceeded" in msg
        assert "429" not in msg

    def test_server_error_500_returns_503(self):
        exc = self._http_status_error(500)
        sc, msg = api_main._friendly_model_error(exc)
        assert sc == 503
        assert "temporarily unavailable" in msg

    def test_bad_gateway_502_http_returns_502(self):
        exc = self._http_status_error(400)
        sc, msg = api_main._friendly_model_error(exc)
        assert sc == 502
        assert "unexpected response" in msg

    def test_timeout_returns_503(self):
        exc = httpx.TimeoutException("timed out")
        sc, msg = api_main._friendly_model_error(exc)
        assert sc == 503
        assert "unreachable" in msg

    def test_connect_error_returns_503(self):
        exc = httpx.ConnectError("connection refused")
        sc, msg = api_main._friendly_model_error(exc)
        assert sc == 503
        assert "unreachable" in msg

    def test_generic_exception_returns_502(self):
        exc = ValueError("internal model error: secret token abc123")
        sc, msg = api_main._friendly_model_error(exc)
        assert sc == 502
        assert "secret" not in msg
        assert "abc123" not in msg
        assert "retry" in msg.lower()


# ---------------------------------------------------------------------------
# /api/chat endpoint - integration via TestClient (no live model needed)
# ---------------------------------------------------------------------------

def _make_chat_req(content: str = "hello"):
    return {"messages": [{"role": "user", "content": content}]}


def _mock_execute_chat(result_content: str):
    async def _inner(req):
        return {
            "content": result_content,
            "route": {
                "mode": "small",
                "model": "test-model",
                "backend_url": "http://localhost",
                "backend_kind": "local",
                "fallback_model": None,
                "fallback_backend_url": None,
                "reason": [],
                "fallback_used": False,
                "quality_retry_used": False,
                "latency_ms": 1,
                "requested_mode": "auto",
            },
        }
    return _inner


class TestChatEndpointSafetyIntegration:
    def test_chat_endpoint_sanitizes_fabricated_admin_action(self):
        from fastapi.testclient import TestClient
        fabricated = "Jasne. Wylaczam sie na Twoje zlecenie."
        with patch.object(api_main, "_execute_chat", side_effect=_mock_execute_chat(fabricated)):
            with patch.object(api_main, "AUTH_REQUIRED", False):
                client = TestClient(api_main.app)
                resp = client.post("/api/chat", json=_make_chat_req("stop"))
        assert resp.status_code == 200
        body = resp.json()
        assert "[SAFETY]" in body["content"]
        assert "wylaczam" not in body["content"].lower()

    def test_chat_endpoint_passes_normal_content(self):
        from fastapi.testclient import TestClient
        safe = "To configure nginx, edit /etc/nginx/nginx.conf."
        with patch.object(api_main, "_execute_chat", side_effect=_mock_execute_chat(safe)):
            with patch.object(api_main, "AUTH_REQUIRED", False):
                client = TestClient(api_main.app)
                resp = client.post("/api/chat", json=_make_chat_req("how"))
        assert resp.status_code == 200
        assert resp.json()["content"] == safe


# ---------------------------------------------------------------------------
# Error handling: model errors must not leak raw details
# ---------------------------------------------------------------------------

class TestModelErrorNoLeak:
    def test_rate_limit_error_yields_503_no_raw_detail(self):
        from fastapi.testclient import TestClient

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        exc = httpx.HTTPStatusError("429 Too Many Requests detail=secret", request=MagicMock(), response=mock_resp)

        async def _fail(_model, _url, _key, _msgs, _temp, _max):
            raise exc

        with patch.object(api_main, "_call_model", side_effect=_fail):
            with patch.object(api_main, "AUTH_REQUIRED", False):
                client = TestClient(api_main.app)
                resp = client.post("/api/chat", json=_make_chat_req("test"))

        assert resp.status_code == 503
        detail = resp.json().get("detail", "")
        assert "429" not in detail
        assert "secret" not in detail
        assert "Too Many Requests" not in detail

    def test_generic_model_exception_yields_502_no_raw_detail(self):
        from fastapi.testclient import TestClient

        async def _fail(_model, _url, _key, _msgs, _temp, _max):
            raise RuntimeError("upstream internal error: api_key=sk-proj-abc123")

        with patch.object(api_main, "_call_model", side_effect=_fail):
            with patch.object(api_main, "AUTH_REQUIRED", False):
                client = TestClient(api_main.app)
                resp = client.post("/api/chat", json=_make_chat_req("test"))

        assert resp.status_code in (502, 503)
        detail = resp.json().get("detail", "")
        assert "sk-proj-abc123" not in detail
        assert "upstream internal error" not in detail
