"""Tests for structured logging — OPT-42."""

from __future__ import annotations

import logging

from security.structured_logging import (
    sanitize_log_value,
    StructuredFormatter,
    request_id_ctx,
    _extract_actor,
)


class TestSanitizeLogValue:
    def test_bearer_token_sanitized(self):
        result = sanitize_log_value("Bearer sk-abc123secret")
        assert "sk-abc123secret" not in result
        assert "[REDACTED]" in result

    def test_service_token_sanitized(self):
        result = sanitize_log_value("X-Service-Token: my-secret-token")
        assert "my-secret-token" not in result
        assert "[REDACTED]" in result

    def test_api_key_sanitized(self):
        result = sanitize_log_value('api_key="super-secret-key"')
        assert "super-secret-key" not in result

    def test_password_sanitized(self):
        result = sanitize_log_value('password: hunter2')
        assert "hunter2" not in result

    def test_normal_text_unchanged(self):
        text = "GET /api/runs -> 200 in 45ms"
        assert sanitize_log_value(text) == text

    def test_empty_string(self):
        assert sanitize_log_value("") == ""


class TestStructuredFormatter:
    def test_includes_request_id(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        token = request_id_ctx.set("abc1234")
        try:
            output = formatter.format(record)
            assert "request_id=abc1234" in output
        finally:
            request_id_ctx.reset(token)

    def test_includes_extra_fields(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        record.path = "/api/connectors"
        record.method = "POST"
        record.status_code = 200
        record.duration_ms = 42.5
        output = formatter.format(record)
        assert "path=/api/connectors" in output
        assert "method=POST" in output
        assert "status_code=200" in output
        assert "duration_ms=42.5" in output

    def test_sanitizes_sensitive_values_in_message(self):
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Got Bearer sk-secret123token", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "sk-secret123token" not in output
        assert "[REDACTED]" in output


class TestExtractActor:
    def test_service_token(self):
        class FakeReq:
            headers = {"X-Service-Token": "some-token"}
        assert _extract_actor(FakeReq()) == ("service", "service")

    def test_bearer_token(self):
        class FakeReq:
            headers = {"Authorization": "Bearer jwt-token"}
        assert _extract_actor(FakeReq()) == ("authenticated", "jwt-user")

    def test_header_role(self):
        class FakeReq:
            headers = {"X-User-Role": "operator"}
        assert _extract_actor(FakeReq()) == ("header", "operator")

    def test_anonymous(self):
        class FakeReq:
            headers = {}
        assert _extract_actor(FakeReq()) == ("anonymous", "")
